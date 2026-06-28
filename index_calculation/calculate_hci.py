import numpy as np
import pandas as pd
from database_connection import fetch_forecast_run, fetch_daily_weather
from datetime import date
from database_connection import fetch_forecast_run, fetch_daily_weather, insert_hci_daily

# === rating tables ===

# балл термокомфорта TC по ET (°C) — de Freitas et al. 2004, Table 3.7
TC_TABLE = np.array([
    1,   # ET < -5
    2,   # -5 ≤ ET ≤ -1
    3,   # 0 ≤ ET ≤ 6
    4,   # 7 ≤ ET ≤ 10
    5,   # 11 ≤ ET ≤ 14
    6,   # 15 ≤ ET ≤ 17
    7,   # 18 ≤ ET ≤ 19
    9,   # 20 ≤ ET ≤ 22
    10,  # 23 ≤ ET ≤ 25
    9,   # ET = 26
    8,   # 27 ≤ ET ≤ 28
    7,   # 29 ≤ ET ≤ 30
    6,   # 31 ≤ ET ≤ 32
    5,   # 33 ≤ ET ≤ 34
    4,   # 35 ≤ ET ≤ 36
    2,   # 37 ≤ ET ≤ 39
    0,   # ET ≥ 40
], dtype=float)


# === sub-index functions ===

def calculate_ET(tmax, rhmin):
    return tmax - 0.4 * (tmax - 10) * (1 - rhmin / 100)


def et_to_tc(et):
    # lookup ET (°C) - балл TC
    et = float(et)
    if et < -5:   return TC_TABLE[0]
    if et <= -1:  return TC_TABLE[1]
    if et <= 6:   return TC_TABLE[2]
    if et <= 10:  return TC_TABLE[3]
    if et <= 14:  return TC_TABLE[4]
    if et <= 17:  return TC_TABLE[5]
    if et <= 19:  return TC_TABLE[6]
    if et <= 22:  return TC_TABLE[7]
    if et <= 25:  return TC_TABLE[8]
    if et <= 26:  return TC_TABLE[9]
    if et <= 28:  return TC_TABLE[10]
    if et <= 30:  return TC_TABLE[11]
    if et <= 32:  return TC_TABLE[12]
    if et <= 34:  return TC_TABLE[13]
    if et <= 36:  return TC_TABLE[14]
    if et <= 39:  return TC_TABLE[15]
    if et >= 40:  return TC_TABLE[16]


def precip_to_r(precip_mm):
    # суточные осадки (мм) - балл R
    if precip_mm == 0:    return 10.0
    if precip_mm < 3:     return 9.0
    if precip_mm <= 5:    return 8.0
    if precip_mm <= 8:    return 5.0
    if precip_mm <= 12:   return 2.0
    if precip_mm <= 25:   return 0.0
    if precip_mm > 25:    return -1.0


def wind_to_w(wind_kmh):
    # скорость ветра (км/ч) - балл W
    if wind_kmh == 0:     return 8.0
    if wind_kmh <= 9:     return 10.0
    if wind_kmh <= 19:    return 9.0
    if wind_kmh <= 29:    return 8.0
    if wind_kmh <= 39:    return 6.0
    if wind_kmh <= 49:    return 3.0
    if wind_kmh <= 70:    return 0.0
    if wind_kmh > 70:     return -10.0


def cloud_to_a(cloud_pct):
    # суточная облачность (%) - балл A
    if cloud_pct == 0:    return 8.0
    if cloud_pct <= 10:   return 9.0
    if cloud_pct <= 20:   return 10.0
    if cloud_pct <= 30:   return 9.0
    if cloud_pct <= 40:   return 8.0
    if cloud_pct <= 50:   return 7.0
    if cloud_pct <= 60:   return 6.0
    if cloud_pct <= 70:   return 5.0
    if cloud_pct <= 80:   return 4.0
    if cloud_pct <= 90:   return 3.0
    if cloud_pct > 90:    return 2.0


# === scoring ===

def score_row(row):
    # все температуры в °C (конвертация в gfs_step); ветер м/с → км/ч
    et  = calculate_ET(row["temp_max"], row["rel_hum_min"])
    tc  = et_to_tc(calculate_ET(row["temp_max"], row["rel_hum_min"]))
    r   = precip_to_r(row["precip_sum"])
    w   = wind_to_w(row["wind_speed_mean"] * 3.6)
    a   = cloud_to_a(row["cloud_cover_mean"])
    hci = 4 * tc + a + 3 * r + 2 * w
    return pd.Series({"et": et, "tc": tc, "r": r, "w": w, "a": a, "hci": hci})


# === main ===

def main():
    run_date = date.fromisoformat("2026-06-26")
    run = fetch_forecast_run(run_date, 0)
    if run is None:
        print(f"Прогон не найден: {run_date} цикл 0")
        return

    df = fetch_daily_weather(run["id"])
    scores = df.apply(score_row, axis=1)
    result = pd.concat([df[["point_id", "date_local"]], scores], axis=1)
    insert_hci_daily(run["id"], run["run_date"], result)

if __name__ == "__main__":
    main()