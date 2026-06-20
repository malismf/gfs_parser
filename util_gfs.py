"""
util_gfs — извлечение прогнозов GFS (GRIB2) в плоскую таблицу.
Берёт скачанные collect_gfs.py файлы и собирает значения по шагам прогноза.
"""

import glob
import os
import re
import math
import warnings
import cfgrib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

PATH = "gfs_data" # каталог, куда collect_gfs.py складывает GRIB2-файлы

# координаты/метаданные, общие для всех групп
INFO_COLUMNS = ["latitude", "longitude", "time", "step", "valid_time"]

# имя переменной в cfgrib -> имя колонки в таблице
FORECAST_COLUMNS = {
    "t2m": "temp",       # мгновенная температура 2 м, K
    "tmax": "temp_max",  # максимум за бакет, K (только fhour > 120)
    "tmin": "temp_min",  # минимум за бакет, K (только fhour > 120)
    "r2": "rel_hum",     # отн. влажность 2 м, %
    "u10": "wind_u",     # U-компонента ветра 10 м, м/с
    "v10": "wind_v",     # V-компонента ветра 10 м, м/с
    "tp": "precip",      # накопленные осадки, kg/m^2 (= мм)
    "SUNSD": "sun_dur",  # продолжительность солнечного сияния, с
}


# === поиск файлов ===
def fhour(path):
    m = re.search(r"\.f(\d{3})$", path)
    return int(m.group(1)) if m else -1


def find_sample_file(path=PATH):
    files = [
        f for f in glob.glob(os.path.join(path, "**", "*"), recursive=True)
        if os.path.isfile(f) and not f.endswith(".idx")
    ]
    if not files:
        raise FileNotFoundError(f"GRIB2-файлы не найдены в {path}")
    return max(files, key=fhour)


# === расчёты ===
# скорость и направление ветра из компонент U/V
def find_wind_speed_and_direction(u, v):
    if u == 0 and v == 0:
        return 0, 0
    wind_speed = math.sqrt(u ** 2 + v ** 2)
    wind_direction = (math.atan2(u / wind_speed, v / wind_speed)) * (180 / math.pi) + 180
    return wind_speed, wind_direction


# температура из Кельвинов в Цельсии
def kelvin_to_celsius(t):
    return t - 273.15


# === извлечение ===
# из датасета берём только нужные переменные + общие координаты
def group_frame(ds):
    info = [c for c in INFO_COLUMNS if c in ds.coords]
    forecast = [v for v in FORECAST_COLUMNS if v in ds.data_vars]
    if not forecast:
        return None
    df = ds[forecast].to_dataframe().reset_index()
    return df[info + forecast].set_index(info)


# один GRIB2-файл -> плоская таблица: строка на точку сетки за один шаг прогноза
def extract_file(path):
    datasets = cfgrib.open_datasets(path, backend_kwargs={"indexpath": ""})
    frames = [g for g in (group_frame(ds) for ds in datasets) if g is not None]
    df = pd.concat(frames, axis=1).reset_index()

    # единый набор и порядок колонок: инфо + переменные прогноза
    # (на ранних шагах нет tmax/tmin/tp/SUNSD — добиваем NaN)
    final_cols = INFO_COLUMNS + list(FORECAST_COLUMNS)
    for col in final_cols:
        if col not in df.columns:
            df[col] = np.nan
    df = df[final_cols].rename(columns=FORECAST_COLUMNS)

    # температуры из Кельвинов в Цельсии
    for c in ["temp", "temp_max", "temp_min"]:
        df[c] = kelvin_to_celsius(df[c])

    # ветер: модуль и направление из U/V, сами компоненты убираем
    df[["wind_speed", "wind_dir"]] = df[["wind_u", "wind_v"]].apply(
        lambda x: find_wind_speed_and_direction(*x), axis=1, result_type="expand"
    )
    df = df.drop(columns=["wind_u", "wind_v"])

    return df


def main():
    sample = find_sample_file()
    df = extract_file(sample)
    print(sample)
    print("колонки:", list(df.columns))
    print("строк:", len(df))
    print(df.head())


if __name__ == "__main__":
    main()