"""
util_gfs — извлечение сырых переменных GFS (GRIB2) для записи в gfs_vars.
"""

import glob
import os
import re
import warnings
import cfgrib
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

PATH = "gfs_data"   # каталог, куда collect_gfs2.py складывает GRIB2-файлы

# координаты узла сетки
GRID = ["latitude", "longitude"]

# сырые переменные GFS (имена cfgrib); в gfs_vars пишутся как есть, без конвертаций
GFS_VARS = ["u10", "v10", "t2m", "r2", "t", "tp", "tcc", "SUNSD", "tmax", "tmin"]


# === utilities ===
def fhour(path):
    m = re.search(r"\.f(\d{3})$", path)
    return int(m.group(1)) if m else -1


# === files ===
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


# === extraction ===
# сырые значения нужных переменных по узлам сетки из одного GRIB-файла
def extract_file(path):
    datasets = cfgrib.open_datasets(path, backend_kwargs={"indexpath": ""})
    var_tables = []
    for ds in datasets:
        found_vars = [v for v in GFS_VARS if v in ds.data_vars]
        if found_vars:
            var_tables.append(ds[found_vars].to_dataframe().reset_index()[GRID + found_vars].set_index(GRID))
    df = pd.concat(var_tables, axis=1)
    df = df.loc[:, ~df.columns.duplicated()]   # tp двоится (накопление 0-N и 6-часовой бакет) — оставляем одно вхождение
    return df.reset_index()


def main():
    df = extract_file(find_sample_file())
    print(df.columns.tolist())
    print(df.shape)
    print(df.head())

if __name__ == "__main__":
    main()