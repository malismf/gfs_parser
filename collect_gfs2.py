"""
GFS collector — сборщик GRIB2-файлов GFS 0.25° (pgrb2) с NOMADS.
"""

from datetime import date, datetime, timezone
import urllib.request

# Корень продакшен-каталога GFS на NOMADS
NOMADS_BASE = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod"

# Продукт: общие поля, разрешение 0.25°
PRODUCT = "pgrb2.0p25"


def build_gfs_params(run_date, cycle, fhour):
    """Собрать прямую ссылку на один GRIB2-файл GFS 0.25°.

    Параметры
    ---------
    run_date : дата прогона — строка 'YYYYMMDD' либо datetime.date / datetime
    cycle    : час цикла (0, 6, 12 или 18)
    fhour    : час прогноза (0..384); f000 = анализ, "момент старта"

    Возвращает
    ----------
    str : полный URL файла на NOMADS
    """

    cc = f"{cycle:02d}"     
    fff = f"{fhour:03d}"    
    filename = f"gfs.t{cc}z.{PRODUCT}.f{fff}"

    return f"{NOMADS_BASE}/gfs.{run_date}/{cc}/atmos/{filename}"




def cycle_is_ready(session, date_str, cycle):
    """Цикл считаем полным, если на сервере уже есть последний шаг f384."""
    url = (f'{BASE_PUB}/gfs.{date_str}/{cycle}/atmos/'
           f'gfs.t{cycle}z.pgrb2.{RESOLUTION}.f{MAX_FHOUR:03d}.idx')
    try:
        r = session.head(url, timeout=30, allow_redirects=True)
        return r.status_code == 200
    except urllib.request.RequestException:
        return False


def get_complete_cycles(run_date=None, timeout=10):
    """Вернуть список циклов GFS (из 00, 06, 12, 18), которые полностью
    опубликованы на NOMADS для заданной даты.

    Цикл считается полным, когда доступен файл последнего часа прогноза (f384) —
    он загружается на NOMADS последним.

    Параметры
    ---------
    run_date : дата прогона — строка 'YYYYMMDD', datetime.date или datetime.
               По умолчанию — сегодня по UTC.
    timeout  : таймаут HTTP-запроса в секундах.

    Возвращает
    ----------
    list[int] : отсортированный список полных циклов, например [0, 6].
                Пустой список — если ни один цикл ещё не готов.
    """
    if run_date is None:
        run_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    elif isinstance(run_date, (date, datetime)):
        run_date = run_date.strftime("%Y%m%d")

    complete = []
    for cycle in (0, 6, 12, 18):
        url = build_gfs_params(run_date, cycle, fhour=384)
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    complete.append(cycle)
        except Exception:
            pass  # файл недоступен — цикл ещё не завершён

    return complete

if __name__ == "__main__":
    print(get_complete_cycles())
    print(build_gfs_params(date(2026, 6, 13), 0, 384))