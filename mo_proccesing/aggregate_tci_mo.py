"""
aggregate_tci_mo.py — агрегация TCI по МО через взвешенное среднее.
"""

import pandas as pd
from database_connection import get_connection, fetch_forecast_run
from datetime import date


def aggregate_tci_mo(run_id):
    q = """
        SELECT
            w.mo_id,
            mo.name,
            t.date_local,
            ROUND((SUM(t.tci * w.weight) / NULLIF(SUM(w.weight), 0))::numeric, 2) AS tci_mo,
            COUNT(*) AS n_nodes
        FROM tci_daily t
        JOIN mo_grid_weight w  ON w.point_id = t.point_id
        JOIN mo_boundary    mo ON mo.id = w.mo_id
        WHERE t.run_id = %s
        GROUP BY w.mo_id, mo.name, t.date_local
        ORDER BY w.mo_id, t.date_local
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, (run_id,))
            cols = [d.name for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)


def main():
    run_date = date.fromisoformat("2026-06-26")
    run = fetch_forecast_run(run_date, 0)
    if run is None:
        print(f"Прогон не найден: {run_date}")
        return

    df = aggregate_tci_mo(run["id"])
    out = f"tci_mo_{run_date.strftime('%Y%m%d')}.csv"
    df.to_csv(out, index=False)
    print(f"Сохранено: {out} ({len(df)} строк, {df['mo_id'].nunique()} МО)")


if __name__ == "__main__":
    main()