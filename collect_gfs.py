"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timedelta, timezone
import urllib.request
from urllib.parse import urlencode
import os
import requests
import cfgrib
import pandas as pd
from tqdm import tqdm
from util_gfs import extract_file, GFS_VARS, GRID
import warnings
from database_connection import insert_to_forecast_run, insert_to_gfs_file, upsert_grid_points, insert_gfs_vars, cleanup_old_runs
from date_config import RUN_DATE

# Подавляем предупреждение от cfgrib о будущих изменениях xarray
warnings.filterwarnings('ignore', category=FutureWarning, module='cfgrib')

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"

HOURLY_UNTIL = 120 # GFS 0.25 прогноз является почасовым до 120
MAX_FHOUR = 384 # макс. горизонт прогноза GFS

TODAY = date.today()

# сервис серверной подвыборки NOMADS и квадрат сбора (Иркутская область)
GFS_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
BBOX = {"north": 64.52, "south": 50.5, "west": 95.5, "east": 119.55}


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
        variables += ["TCDC"]
        levels += ["entire_atmosphere"]

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
# анализ доступных прогонов дня: цикл готов, если на сервере есть f384
def get_available_cycles(run_date, timeout=10):
    product = f"gfs.{format_run_date(run_date)}"
    collected_at = datetime.now(timezone.utc)
    available_cycles = []
    for cycle in (0, 6, 12, 18):
        url = build_gfs_url(run_date, cycle, fhour=384)
        request = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status == 200:
                    available_cycles.append(cycle)
        except:
            return available_cycles
    return available_cycles

def insert_forecast_run(run_date, cycle):
    product = f"gfs.{format_run_date(run_date)}"
    collected_at = datetime.now(timezone.utc)
    run_id = insert_to_forecast_run(product, format_run_date(run_date), cycle, collected_at)
    return run_id



def build_to_download_list(run_date, forecast_cycle, bbox):
    files = []
    hours = forecast_hours(MAX_FHOUR, HOURLY_UNTIL)
    run_id = insert_forecast_run(run_date, forecast_cycle)
    for fhour in hours:
        url = build_gfs_url(run_date, forecast_cycle, fhour)
        files.append({
            "cycle": forecast_cycle,
            "fhour": fhour,
            "run_date": run_date,
            "product": f"gfs.{format_run_date(run_date)}",
            "url": url,
            "download_url": build_filter_url(run_date, forecast_cycle, fhour, bbox),
            "run_id": run_id,                # FK forecast_run
            "filename": url.split("/")[-1],  # gfs.t00z.pgrb2.0p25.f096
            "subregion": bbox,               # bbox области под gfs_file
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

def extract_file(path, file):
    datasets = cfgrib.open_datasets(path, backend_kwargs={"indexpath": ""})
    ds1 = cfgrib.open_datasets(path, backend_kwargs={"indexpath": ""})[0]
    file["init_time"] = pd.Timestamp(ds1["time"].values).to_pydatetime()
    file["valid_time"] = pd.Timestamp(ds1["valid_time"].values).to_pydatetime()
    file["step"] = pd.Timedelta(ds1["step"].values).to_pytimedelta()
    var_tables = []
    for ds in datasets:
        found_vars = [v for v in GFS_VARS if v in ds.data_vars]
        if found_vars:
            var_tables.append(ds[found_vars].to_dataframe().reset_index()[GRID + found_vars].set_index(GRID))
    df = pd.concat(var_tables, axis=1)
    df = df.loc[:, ~df.columns.duplicated()]   # tp двоится (накопление 0-N и 6-часовой бакет) — оставляем одно вхождение
    return df.reset_index()

# скачанный файл -> gfs_file + gfs_vars; point_ids кэшируется между файлами (сетка одна на прогон)
def store_file(file, path, point_ids):
    df = extract_file(path, file)
    file_id = insert_to_gfs_file(file, path)
    if not point_ids:
        point_ids.update(upsert_grid_points(df[GRID].itertuples(index=False, name=None)))
    insert_gfs_vars(file_id, df, point_ids)


def download(files, dest, mode="default"):
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    point_ids = {}
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
            store_file(file, path, point_ids)   # метаданные + сырые переменные в БД
        else:
            summary["failed"] += 1
        
        pbar.update(1)
        pbar.set_description(f"Загружено: {summary['downloaded']}, Пропущено: {summary['skipped']}, Ошибки: {summary['failed']}")
    
    pbar.close()
    return summary


def main():
    PATH = "gfs_data"
    run_date = date.fromisoformat(RUN_DATE)

    cleanup_old_runs(run_date) 

    # === pre-downloading gfs variables ===
    available_cycles = get_available_cycles(run_date) # доступные циклы
    print(available_cycles)
    
    if not available_cycles:                        # полных прогонов на день ещё нет
        return
    forecast_cycle = min(available_cycles) # цикл, для которого качаем полный прогноз

    to_download_list = build_to_download_list(run_date, forecast_cycle, BBOX)
    download(to_download_list, PATH, mode="grib")



if __name__ == "__main__":
    main()