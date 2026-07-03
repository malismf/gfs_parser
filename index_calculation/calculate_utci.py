"""
Расчёт UTCI по GFS: temp/rel_hum/wind_speed/mrt/local_time уже готовы в utci_input,
здесь сам полином UTCI (pythermalcomfort) и суточный max.
"""
import numpy as np
import pandas as pd
from datetime import date
from pythermalcomfort.models import utci
from database_connection import fetch_forecast_run, fetch_utci_input, insert_utci_daily
from date_config import RUN_DATE

# === utci calculation ===
def compute_utci(df):
    df["tdb"] = df["temp"].to_numpy(float)
    df["tr"]  = df["mrt"].to_numpy(float)
    df["rh"]  = np.clip(df["rel_hum"].to_numpy(float), 0, 100)
    df["v"]   = np.clip(df["wind_speed"].to_numpy(float), 0.5, 17.0)

    res = utci(tdb=df["tdb"].to_numpy(), tr=df["tr"].to_numpy(), v=df["v"].to_numpy(), rh=df["rh"].to_numpy(), limit_inputs=True)
    res = res.utci if hasattr(res, "utci") else res        
    df["utci"] = np.asarray(res, float)
    return df

# суточный максимум по местной дате + вход целиком на момент пика 
def daily_max(df):
    df["date_local"] = pd.to_datetime(df["local_time"]).dt.date
    valid = df.dropna(subset=["utci"])
    idx = valid.groupby(["point_id", "date_local"])["utci"].idxmax()
    result = valid.loc[idx, ["point_id", "date_local", "tdb", "tr", "rh", "v", "utci"]]
    return result.rename(columns={
        "tdb": "tdb_max", "tr": "tr_max", "rh": "rh_max", "v": "v_max", "utci": "utci_max",
    })

# === main ===
def main():
    run_date = date.fromisoformat(RUN_DATE)
    run = fetch_forecast_run(run_date, 0)
    if run is None:
        print(f"Прогон не найден: {run_date} цикл 0")
        return

    df = fetch_utci_input(run["id"])
    if df.empty:
        print(f"run {run['id']}: нет данных в utci_input")
        return

    df = compute_utci(df)
    result = daily_max(df)
    insert_utci_daily(run["id"], run["run_date"], result)

if __name__ == "__main__":
    main()