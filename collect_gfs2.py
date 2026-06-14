"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request
import os
import shutil
import time

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"

HOURLY_UNTIL = 120 # GFS 0.25 прогноз является почасовым до
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


def forecast_hours(max_fhour=384, hourly_until=120):
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
def build_file_list(run_date, cycles, forecast_cycle=18, max_fhour=384):
    files = []
    for cycle in cycles:
        hours = forecast_hours(max_fhour) if cycle == forecast_cycle else [0]
        for fhour in hours:
            files.append({
                "cycle": cycle,
                "fhour": fhour,
                "url": build_gfs_params(run_date, cycle, fhour),
            })
    return files

# === downloading ===
def download_file(url, path, retries=3, timeout=60):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gfs-collector/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(tmp, "wb") as f:
                    shutil.copyfileobj(resp, f)
            os.replace(tmp, path)
            return True
        except Exception as exc:
            last_error = exc
            if os.path.exists(tmp):
                os.remove(tmp)
            if attempt < retries:
                time.sleep(2 * attempt)
    print(f"  ошибка: {url} ({last_error})")
    return False


def download(files, dest="gfs_data", retries=3, timeout=60):
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    for file in files:
        path = local_path(file, dest)
        if os.path.exists(path):
            summary["skipped"] += 1
            continue
        print(f"качаю c{file['cycle']:02d} f{file['fhour']:03d}")
        if download_file(file["url"], path, retries=retries, timeout=timeout):
            summary["downloaded"] += 1
        else:
            summary["failed"] += 1
    return summary


if __name__ == "__main__":
    run_date = datetime.now(timezone.utc)
    print(get_complete_cycles(run_date))
    gfs_link = build_gfs_params(date(2026, 6, 13), 0, 384)
    print(local_path({"url": gfs_link}, "path"))
