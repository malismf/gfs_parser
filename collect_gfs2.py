"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"


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


def get_complete_cycles(run_date=None, timeout=10):
    if run_date is None:
        run_date = datetime.now(timezone.utc)
    run_date = format_run_date(run_date)

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


if __name__ == "__main__":
    print(get_complete_cycles())
    print(build_gfs_params(date(2026, 6, 13), 0, 384))