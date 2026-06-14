"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request
import os
import shutil
import time
import requests
from tqdm import tqdm

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"

HOURLY_UNTIL = 120 # GFS 0.25 прогноз является почасовым до 120
MAX_FHOUR = 384 # макс. горизонт прогноза GFS

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


# === pre-downloading ===
def build_to_download_list(run_date, cycles, forecast_cycle):
    files = []
    for cycle in cycles:
        hours = forecast_hours(MAX_FHOUR, HOURLY_UNTIL) if cycle == forecast_cycle else [0]
        for fhour in hours:
            files.append({
                "cycle": cycle,
                "fhour": fhour,
                "url": build_gfs_params(run_date, cycle, fhour)
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
 
 

def download(files, dest):
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    for file in tqdm(files, desc="Скачивание GFS", unit="файл"):
        path = local_path(file, dest)
        if os.path.exists(path):
            summary["skipped"] += 1
            continue
        print(f"качаю c{file['cycle']:02d} f{file['fhour']:03d}")
        if download_file(file["url"], path):
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
    
    to_download_list = build_to_download_list(run_date, complete_cycles, forecast_cycle)
    download(to_download_list, PATH)


if __name__ == "__main__":
    main()