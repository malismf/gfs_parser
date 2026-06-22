"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request
from urllib.parse import urlencode
import os
import requests
from tqdm import tqdm
import psycopg

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"

HOURLY_UNTIL = 120 # GFS 0.25 прогноз является почасовым до 120
MAX_FHOUR = 384 # макс. горизонт прогноза GFS

TODAY = date.today()

# сервис серверной подвыборки NOMADS и квадрат сбора (Иркутская область)
GFS_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
BBOX = {"north": 64.52, "south": 50.5, "west": 95.5, "east": 119.55}

# === database ===
def get_connection():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="tourist-climate-assessment",
        user="postgres",
        password="123123"
    )


def insert_to_forecast_run(product, run_date, cycle, collected_at):
    """Вставляет или обновляет запись о прогноне. Возвращает id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO forecast_run (product, run_date, cycle, collected_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_date, cycle) 
                DO UPDATE SET product = EXCLUDED.product, collected_at = EXCLUDED.collected_at
                RETURNING id
            """, (product, run_date, cycle, collected_at))
            return cur.fetchone()[0]

# === utilities ===
def format_run_date(run_date):
    if isinstance(run_date, (date, datetime)):
        return run_date.strftime("%Y%m%d")
    return str(run_date)


def forecast_hours(max_fhour, hourly_until):
    hours = list(range(0, hourly_until + 1))
    hours += list(range(hourly_until + 3, max_fhour + 1, 3))
    return hours

def local_path(file, dest):
    parts = file["url"].split("/")
    date_dir, cc, filename = parts[-4], parts[-3], parts[-1]
    return f"{dest}/{date_dir}/{cc}/{filename}"


def tci_vars_levels(fhour):
    """Список переменных и уровней под TCI для конкретного шага прогноза."""
    variables = ["TMP", "RH", "UGRD", "VGRD"] # мгновенные — есть на всех шагах
    levels = ["2_m_above_ground", "10_m_above_ground"]

    if fhour > 0:                      # на f000 накопительных полей нет
        variables += ["APCP", "SUNSD"]
        levels += ["surface"]

    if fhour > HOURLY_UNTIL:           # шаг стал 3-часовым — берём экстремумы за 3 часа
        variables += ["TMAX", "TMIN"]

    return variables, levels

def build_gfs_url(run_date, cycle, fhour):
    ymd = format_run_date(run_date)
    cc = f"{cycle:02d}"
    fff = f"{fhour:03d}"
    filename = f"gfs.t{cc}z.{PRODUCT}.f{fff}"
    return f"{NOMADS_BASE}/gfs.{ymd}/{cc}/atmos/{filename}"

# собирает ссылку на серверную подвыборку: только переменные под TCI и только по квадрату
def build_filter_url(run_date, cycle, fhour, bbox):
    ymd = format_run_date(run_date)
    cc = f"{cycle:02d}"
    fff = f"{fhour:03d}"

    variables, levels = tci_vars_levels(fhour)

    params = {
        "file": f"gfs.t{cc}z.{PRODUCT}.f{fff}",
        "subregion": "",
        "leftlon": bbox["west"],
        "rightlon": bbox["east"],
        "toplat": bbox["north"],
        "bottomlat": bbox["south"],
        "dir": f"/gfs.{ymd}/{cc}/atmos",
    }
    for v in variables:
        params[f"var_{v}"] = "on"
    for lev in levels:
        params[f"lev_{lev}"] = "on"

    return f"{GFS_FILTER_URL}?{urlencode(params)}"


# === pre-downloading ===
# анализ доступных прогонов дня: цикл готов, если на сервере есть f384 — сразу пишем его в forecast_run
def get_available_runs(run_date, timeout=10):
    product = f"gfs.{format_run_date(run_date)}"
    collected_at = datetime.now(timezone.utc)
    run_ids = {}
    for cycle in (0, 6, 12, 18):
        url = build_gfs_url(run_date, cycle, fhour=384)
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    run_ids[cycle] = insert_to_forecast_run(product, format_run_date(run_date), cycle, collected_at)
        except Exception:
            pass
    return run_ids


def build_to_download_list(run_date, cycles, forecast_cycle, bbox):
    files = []
    for cycle in cycles:
        hours = forecast_hours(MAX_FHOUR, HOURLY_UNTIL) if cycle == forecast_cycle else [0]
        for fhour in hours:
            files.append({
                "cycle": cycle,
                "fhour": fhour,
                "run_date": run_date,
                "product": f"gfs.{format_run_date(run_date)}",
                "url": build_gfs_url(run_date, cycle, fhour),
                "download_url": build_filter_url(run_date, cycle, fhour, bbox)
            })
    return files

# === downloading ===
def download_file(url, path):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return False

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as f:
        for chunk in response.iter_content():
            if chunk:
                f.write(chunk)
    return True


def download(files, dest, mode="default"):
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    pbar = tqdm(total=len(files), unit="файл")
    
    for file in files:
        if mode == "grib":
            url = file["download_url"]   # серверная подвыборка по квадрату (фильтр)
        if mode == "default":
            url = file["url"]            # обычное скачивание — файл целиком
        path = local_path(file, dest)
        if os.path.exists(path):
            summary["skipped"] += 1
        elif download_file(url, path):
            summary["downloaded"] += 1
        else:
            summary["failed"] += 1
        
        pbar.update(1)
        pbar.set_description(f"Загружено: {summary['downloaded']}, Пропущено: {summary['skipped']}, Ошибки: {summary['failed']}")
    
    pbar.close()
    return summary


def main():
    PATH = "gfs_data"

    # === pre-downloading gfs variables ===
    run_date = datetime.now(timezone.utc) # текущий день
    run_ids = get_available_runs(run_date) # доступные прогоны + запись в forecast_run
    if not run_ids:                        # полных прогонов на день ещё нет
        return
    forecast_cycle = min(run_ids) # цикл, для которого качаем полный прогноз

    to_download_list = build_to_download_list(run_date, list(run_ids), forecast_cycle, BBOX)
    download(to_download_list, PATH, mode="grib")


if __name__ == "__main__":
    main()