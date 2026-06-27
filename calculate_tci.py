import numpy as np
import pandas as pd
from database_connection import fetch_forecast_run, fetch_daily_weather
from datetime import date

# === CI lookup table (Mieczkowski 1985) ===
# строки: T °C (≥36 … ≤-5), столбцы: RH % (<20, 20-39, 40-59, 60-79, ≥80)
CI_TABLE = np.array([
    [ 1,  0, -1, -2, -3],   # ≥ 36
    [ 4,  3,  2,  1,  0],   # 32–35
    [ 5,  5,  4,  3,  2],   # 28–31
    [ 5,  5,  5,  4,  3],   # 24–27
    [ 5,  5,  5,  5,  4],   # 20–23
    [ 4,  5,  5,  5,  5],   # 16–19
    [ 3,  4,  4,  5,  5],   # 12–15
    [ 2,  3,  3,  4,  4],   # 8–11
    [ 1,  2,  2,  3,  3],   # 4–7
    [-1,  0,  1,  1,  2],   # 0–3
    [-2, -1,  0,  0,  1],   # -4 – -1
    [-3, -3, -2, -2, -1],   # ≤ -5
], dtype=float)


# === sub-index functions ===

def ci_lookup(t, rh):
    # T → строка
    if   t >= 36: row = 0
    elif t >= 32: row = 1
    elif t >= 28: row = 2
    elif t >= 24: row = 3
    elif t >= 20: row = 4
    elif t >= 16: row = 5
    elif t >= 12: row = 6
    elif t >= 8:  row = 7
    elif t >= 4:  row = 8
    elif t >= 0:  row = 9
    elif t >= -4: row = 10
    else:         row = 11
    # RH → столбец
    if   rh < 20: col = 0
    elif rh < 40: col = 1
    elif rh < 60: col = 2
    elif rh < 80: col = 3
    else:         col = 4
    return CI_TABLE[row, col]


def precip_to_r(precip_mm):
    # суточные осадки (мм) → балл R; пороги Mieczkowski / 30
    if precip_mm < 0.1:  return  5.0
    if precip_mm < 1.7:  return  4.0
    if precip_mm < 3.4:  return  3.0
    if precip_mm < 5.0:  return  2.0
    if precip_mm < 6.7:  return  1.0
    if precip_mm < 10.0: return  0.0
    return -1.0


def sun_to_s(sun_hours):
    # суточные часы солнца → балл S; пороги Mieczkowski / 30
    # GFS SUNSD = астрономическая продолжительность дня, не реальное сияние
    if sun_hours > 10.0: return  5.0
    if sun_hours > 8.4:  return  4.0
    if sun_hours > 6.7:  return  3.0
    if sun_hours > 5.0:  return  2.0
    if sun_hours > 3.4:  return  1.0
    if sun_hours > 1.7:  return  0.0
    return -1.0


def wind_to_w(wind_kmh):
    # средний ветер (км/ч) → балл W (Mieczkowski 1985)
    if wind_kmh < 10: return  5.0
    if wind_kmh < 19: return  4.0
    if wind_kmh < 28: return  3.0
    if wind_kmh < 38: return  2.0
    if wind_kmh < 48: return  1.0
    if wind_kmh < 59: return  0.0
    return -1.0


# === scoring ===

def score_row(row):
    # CId: дневной комфорт (Tmax × RHmin), CIa: среднесуточный (Tmean × RHmean)
    cid = ci_lookup(row["temp_max"],  row["rel_hum_min"])
    cia = ci_lookup(row["temp_mean"], row["rel_hum_mean"])
    r   = precip_to_r(row["precip_sum"])
    s   = sun_to_s(row["sun_hours"])
    w   = wind_to_w(row["wind_speed_mean"] * 3.6)   # м/с → км/ч
    tci = 8*cid + 2*cia + 4*r + 4*s + 2*w           # Mieczkowski 1985; max = 100
    return pd.Series({"cid": cid, "cia": cia, "r_score": r, "s_score": s, "w_score": w, "tci": tci})


# === main ===

def main():
    run_date = date.fromisoformat("2026-06-25")
    run = fetch_forecast_run(run_date, 0)
    if run is None:
        print(f"Прогон не найден: {run_date} цикл 0")
        return

    df = fetch_daily_weather(run["id"])

    scores = df.apply(score_row, axis=1)
    result = pd.concat([df[["point_id", "date_local"]], scores], axis=1)

    out = f"tci_{run_date.strftime('%Y%m%d')}.csv"
    result.to_csv(out, index=False, float_format="%.2f")
    print(f"Сохранено: {out} ({len(result)} строк)")


if __name__ == "__main__":
    main()