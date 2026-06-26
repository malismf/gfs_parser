import numpy as np
from database_connection import fetch_tmax_rhmin, fetch_forecast_run
from datetime import date

# балл термокомфорта HCI по эффективной температуре ET (°C)
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

# эффективная температура ET (°C) по формуле Миссенара
def calculate_ET(tmax, rhmin):
    return tmax - 0.4 * (tmax - 10) * (1 - rhmin / 100)



