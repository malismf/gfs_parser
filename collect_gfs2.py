"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request

NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"
PRODUCT = "pgrb2.0p25"


def format_run_date(run_date):
    """Привести дату прогона к формату GFS-URL (YYYYMMDD).

    run_date : строка 'YYYYMMDD', datetime.date или datetime.
    """
    if isinstance(run_date, (date, datetime)):
        return run_date.strftime("%Y%m%d")
    return str(run_date)


def build_gfs_params(run_date, cycle, fhour):
    """Собрать прямую ссылку на один GRIB2-файл GFS 0.25°.

    run_date : дата прогона — строка 'YYYYMMDD' либо datetime.date / datetime
    cycle    : час цикла (0, 6, 12 или 18)
    fhour    : час прогноза (0..384); f000 = анализ, "момент старта"
    """
    ymd = format_run_date(run_date)
    cc = f"{cycle:02d}"
    fff = f"{fhour:03d}"
    filename = f"gfs.t{cc}z.{PRODUCT}.f{fff}"
    return f"{NOMADS_BASE}/gfs.{ymd}/{cc}/atmos/{filename}"


def get_complete_cycles(run_date=None, timeout=10):
    """Вернуть список циклов GFS (из 00, 06, 12, 18), полностью
    опубликованных на NOMADS для заданной даты.

    Цикл считается полным, когда доступен файл последнего часа прогноза
    (f384) — он загружается на NOMADS последним.

    run_date : дата прогона; по умолчанию — сегодня по UTC.
    timeout  : таймаут HTTP-запроса в секундах.
    """
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