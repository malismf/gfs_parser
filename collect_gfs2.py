"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request
from urllib.parse import urlencode
import os
import requests
from tqdm import tqdm

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"

HOURLY_UNTIL = 120 # GFS 0.25 прогноз является почасовым до 120
MAX_FHOUR = 384 # макс. горизонт прогноза GFS

# сервис серверной подвыборки NOMADS и квадрат сбора (Иркутская область)
GFS_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
BBOX = {"north": 64.52, "south": 50.5, "west": 95.5, "east": 119.55}

# === utilities ===
def format_run_date(run_date):
    if isinstance(run_date, (date, datetime)):
        return run_date.strftime("%Y%m%d")
    return str(run_date)


def build_gfs_params(run_date, cycle, fhour):
    ymd = format_run_date(run_date)
    cc = f"{cycle:02d}"
    fff = f"{fhour:03d}"
    filename = f"gfs.t{cc}z.{PRODUCT}.f{fff}"
    return f"{NOMADS_BASE}/gfs.{ymd}/{cc}/atmos/{filename}"


def forecast_hours(max_fhour, hourly_until):
    hours = list(range(0, hourly_until + 1))
    hours += list(range(hourly_until + 3, max_fhour + 1, 3))
    return hours

def get_complete_cycles(run_date, timeout=10):
    complete = []
    for cycle in (0, 6, 12, 18):
        url = build_gfs_params(run_date, cycle, fhour = 384)
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    complete.append(cycle)
        except Exception:
            pass
    return complete

def local_path(file, dest):
    parts = file["url"].split("/")
    date_dir, cc, filename = parts[-4], parts[-3], parts[-1]
    return f"{dest}/{date_dir}/{cc}/{filename}"


# собирает ссылку на серверную подвыборку: все переменные и уровни, но только по квадрату
def build_filter_url(run_date, cycle, fhour, bbox):
    ymd = format_run_date(run_date)
    cc = f"{cycle:02d}"
    fff = f"{fhour:03d}"
    query = urlencode({
        "file": f"gfs.t{cc}z.{PRODUCT}.f{fff}",
        "all_var": "on",
        "all_lev": "on",
        "subregion": "",
        "leftlon": bbox["west"],
        "rightlon": bbox["east"],
        "toplat": bbox["north"],
        "bottomlat": bbox["south"],
        "dir": f"/gfs.{ymd}/{cc}/atmos",
    })
    return f"{GFS_FILTER_URL}?{query}"


# === pre-downloading ===
def build_to_download_list(run_date, cycles, forecast_cycle, bbox):
    files = []
    for cycle in cycles:
        hours = forecast_hours(MAX_FHOUR, HOURLY_UNTIL) if cycle == forecast_cycle else [0]
        for fhour in hours:
            files.append({
                "cycle": cycle,
                "fhour": fhour,
                "url": build_gfs_params(run_date, cycle, fhour),
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
    total = int(response.headers.get("Content-Length", 0))

    with open(path, "wb") as f, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=os.path.basename(path),
        leave=False,
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))

    return True


def download(files, dest, mode="default"):
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    for file in tqdm(files, desc="Скачивание GFS", unit="файл"):
        if mode == "grib":
            url = file["download_url"]   # серверная подвыборка по квадрату (фильтр)
        if mode == "default":
            url = file["url"]            # обычное скачивание — файл целиком
        print(url)
        path = local_path(file, dest)
        if os.path.exists(path):
            summary["skipped"] += 1
            continue
        if download_file(url, path):
            summary["downloaded"] += 1
        else:
            summary["failed"] += 1
    return summary


def main():
    PATH = "gfs_data"

    # === pre-downloading gfs variables ===
    run_date = datetime.now(timezone.utc) # текущий день
    complete_cycles = get_complete_cycles(run_date) # доступные циклы на день
    forecast_cycle = min(complete_cycles) # цикл, для которого качаем полный прогноз

    to_download_list = build_to_download_list(run_date, complete_cycles, forecast_cycle, BBOX)
    download(to_download_list, PATH, mode="grib")


if __name__ == "__main__":
    main()