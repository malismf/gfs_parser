"""
util_gfs — извлечение прогнозов GFS (GRIB2) в плоскую таблицу.
Берёт скачанные collect_gfs.py файлы и собирает значения по шагам прогноза.
"""

import glob
import os
import re
import warnings
import cfgrib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

PATH = "gfs_data" # каталог, куда collect_gfs.py складывает GRIB2-файлы

# имя переменной в cfgrib -> имя колонки в таблице
RENAME = {
    "t2m": "T",       # мгновенная температура 2 м, K
    "tmax": "TMAX",   # максимум за бакет, K (только fhour > 120)
    "tmin": "TMIN",   # минимум за бакет, K (только fhour > 120)
    "r2": "RH",       # отн. влажность 2 м, %
    "u10": "U",       # U-компонента ветра 10 м, м/с
    "v10": "V",       # V-компонента ветра 10 м, м/с
    "tp": "APCP",     # накопленные осадки, kg/m^2 (= мм)
    "SUNSD": "SUNSD", # продолжительность солнечного сияния, с
}

COORDS = ["latitude", "longitude", "time", "step", "valid_time"]


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


# === извлечение ===
# из датасета берём только нужные переменные + общие координаты
def group_frame(ds):
    wanted = [v for v in RENAME if v in ds.data_vars]
    if not wanted:
        return None
    df = ds[wanted].to_dataframe().reset_index()
    idx = [c for c in COORDS if c in df.columns]
    return df[idx + wanted].set_index(idx)


# один GRIB2-файл -> плоская таблица: строка на точку сетки за один шаг прогноза
def extract_file(path):
    datasets = cfgrib.open_datasets(path, backend_kwargs={"indexpath": ""})
    frames = [g for g in (group_frame(ds) for ds in datasets) if g is not None]
    df = pd.concat(frames, axis=1).reset_index().rename(columns=RENAME)

    # единый набор колонок (на ранних шагах нет TMAX/TMIN/APCP/SUNSD)
    for col in RENAME.values():
        if col not in df.columns:
            df[col] = np.nan

    order = COORDS + list(RENAME.values())
    return df[[c for c in order if c in df.columns]]


def main():
    sample = find_sample_file()
    df = extract_file(sample)
    print(sample)
    print("колонки:", list(df.columns))
    print("строк:", len(df))
    print(df.head())


if __name__ == "__main__":
    main()