"""
util_gfs — извлечение прогнозов GFS (GRIB2) и суточная агрегация.
Берёт скачанные collect_gfs.py файлы, собирает значения по шагам прогноза
и агрегирует их по локальным суткам — один CSV на день.
"""

import glob
import os
import re
import math
import warnings
import cfgrib
import numpy as np
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings("ignore", category=FutureWarning)

PATH = "gfs_data"        # каталог, куда collect_gfs.py складывает GRIB2-файлы
DAILY_PATH = "gfs_daily" # каталог под суточные CSV (1 день — 1 файл)

# координаты/метаданные, общие для всех групп
INFO_COLUMNS = ["latitude", "longitude", "time", "step", "valid_time"]

# имя переменной в cfgrib -> имя колонки в таблице
FORECAST_COLUMNS = {
    "t2m": "temp",       # мгновенная температура 2 м, K
    "tmax": "temp_max",  # максимум температуры за период, K (только fhour > 120)
    "tmin": "temp_min",  # минимум температуры за период, K (только fhour > 120)
    "r2": "rel_hum",     # отн. влажность 2 м, %
    "u10": "wind_u",     # U-компонента ветра 10 м, м/с
    "v10": "wind_v",     # V-компонента ветра 10 м, м/с
    "tp": "precip",      # накопленные осадки, kg/m^2 (= мм)
    "SUNSD": "sun_dur",  # продолжительность солнечного сияния, с
}

# === utilities ===
def fhour(path):
    m = re.search(r"\.f(\d{3})$", path)
    return int(m.group(1)) if m else -1


# === поиск файлов ===
def list_files(path=PATH):
    return sorted(
        f for f in glob.glob(os.path.join(path, "**", "*"), recursive=True)
        if os.path.isfile(f) and not f.endswith(".idx")
    )


def find_sample_file(path=PATH):
    files = list_files(path)
    if not files:
        raise FileNotFoundError(f"GRIB2-файлы не найдены в {path}")
    return max(files, key=fhour)


# === calculation ===
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


# приращение накопленной величины за шаг: tp и SUNSD копятся до 6 часов и потом сбрасываются, поэтому берём разность, а на сбросе — само значение
def deaccumulate(df, col):
    s = df.sort_values(["latitude", "longitude", "time", "step"])
    diff = s.groupby(["latitude", "longitude", "time"])[col].diff()
    return diff.where(diff >= 0, s[col])


# === extraction ===
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
    df = pd.concat(frames, axis=1).reset_index().rename(columns=FORECAST_COLUMNS)

    # у tp две записи (сумма от старта прогона и накопление за 6 часов) — cfgrib может дать дубль колонки precip, оставляем не-повторные
    is_duplicate = df.columns.duplicated()
    df = df.loc[:, ~is_duplicate]

    # на ранних шагах нет temp_max/temp_min/precip/sun_dur — добиваем NaN
    for col in FORECAST_COLUMNS.values():
        if col not in df.columns:
            df[col] = np.nan

    # температуры из Кельвинов в Цельсии
    for c in ["temp", "temp_max", "temp_min"]:
        df[c] = kelvin_to_celsius(df[c])

    # ветер: модуль и направление из U/V
    df[["wind_speed", "wind_dir"]] = df[["wind_u", "wind_v"]].apply(
        lambda x: find_wind_speed_and_direction(*x), axis=1, result_type="expand"
    )

    # итоговый набор и порядок колонок (ветер уже как speed/dir, сырые U/V не берём)
    final_cols = INFO_COLUMNS + [
        "temp", "temp_max", "temp_min", "rel_hum",
        "wind_speed", "wind_dir", "precip", "sun_dur",
    ]
    return df[final_cols]


# все файлы каталога -> одна таблица по шагам прогноза
def extract_all(path=PATH):
    frames = [extract_file(f) for f in tqdm(list_files(path), desc="Извлечение GFS", unit="файл")]
    return pd.concat(frames, ignore_index=True)


# === aggregation ===
# суточная агрегация: одна строка на точку сетки за локальный день
def aggregate_daily(df):
    df = df.copy()
    # локальная дата (UTC+8, Иркутск) — по ней режем на сутки
    df["date_local"] = (pd.to_datetime(df["valid_time"]) + pd.Timedelta(hours=8)).dt.date

    # суточные экстремумы: мгновенная temp вместе с TMAX/TMIN за период
    df["t_hi"] = df[["temp", "temp_max"]].max(axis=1)
    df["t_lo"] = df[["temp", "temp_min"]].min(axis=1)

    # осадки и сияние накоплены -> деаккумулируем приращение за шаг (сияние сразу в часы)
    df["precip_step"] = deaccumulate(df, "precip")
    df["sun_hours_step"] = deaccumulate(df, "sun_dur") / 3600

    daily = df.groupby(["date_local", "latitude", "longitude"]).agg(
        temp_mean=("temp", "mean"),
        temp_max=("t_hi", "max"),
        temp_min=("t_lo", "min"),
        rel_hum_mean=("rel_hum", "mean"),
        rel_hum_min=("rel_hum", "min"),
        wind_speed_mean=("wind_speed", "mean"),
        precip_sum=("precip_step", "sum"),
        sun_hours=("sun_hours_step", "sum"),
    ).reset_index()

    return daily


# по одному CSV на каждый локальный день
def write_daily(daily, dest=DAILY_PATH):
    os.makedirs(dest, exist_ok=True)
    for day, group in daily.groupby("date_local"):
        group.to_csv(os.path.join(dest, f"{day}.csv"), index=False)
    return daily["date_local"].nunique()


def main():
    df = extract_all()
    daily = aggregate_daily(df)
    n = write_daily(daily)
    print(f"Готово: {n} дней записано в {DAILY_PATH}/")


if __name__ == "__main__":
    main()