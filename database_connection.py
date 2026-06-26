import psycopg
from util_gfs import extract_file, GFS_VARS, GRID
import pandas as pd
import cfgrib

# === database ===
def get_connection():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="tourist-climate-assessment",
        user="postgres",
        password="123123"
    )


def insert_to_forecast_run(product, run_date, cycle, collected_at):
    """Вставляет или обновляет запись о прогноне. Возвращает id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO forecast_run (product, run_date, cycle, collected_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_date, cycle) 
                DO UPDATE SET product = EXCLUDED.product, collected_at = EXCLUDED.collected_at
                RETURNING id
            """, (product, run_date, cycle, collected_at))
            return cur.fetchone()[0]


# метаданные файла в БД: init_time/valid_time/step из GRIB, run_id/filename/subregion из file. возвращает id
def insert_to_gfs_file(file, path):
    bbox = file["subregion"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO gfs_file (run_id, fhour, filename, init_time, valid_time, step, subregion)
                VALUES (%s, %s, %s, %s, %s, %s, ST_MakeEnvelope(%s, %s, %s, %s, 4326))
                ON CONFLICT (run_id, fhour) DO UPDATE SET filename = EXCLUDED.filename
                RETURNING id
            """, (
                file["run_id"], file["fhour"], file["filename"],
                file["init_time"], file["valid_time"], file["step"],
                bbox["west"], bbox["south"], bbox["east"], bbox["north"]
            ))
            return cur.fetchone()[0]



# сырые переменные файла в gfs_vars по узлам сетки (SUNSD идёт в столбец sunsd по позиции)
def insert_gfs_vars(file_id, df, point_ids):
    values = df.set_index(GRID).reindex(columns=GFS_VARS)   # фиксируем набор и порядок столбцов, отсутствующие -> NaN
    rows = []
    for (lat, lon), record in zip(values.index, values.to_numpy()):
        point_id = point_ids.get((float(lat), float(lon)))
        if point_id is None:
            continue
        cells = [None if pd.isna(x) else float(x) for x in record]   # NaN -> NULL, numpy -> python float
        rows.append((file_id, point_id, *cells))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO gfs_vars (file_id, point_id, u10, v10, t2m, r2, t, tp, sunsd, tmax, tmin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_id, point_id) DO NOTHING
            """, rows)


# upsert узлов сетки, возвращает {(lat, lon): point_id}
def upsert_grid_points(points):
    rows = [(float(lat), float(lon)) for lat, lon in points]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO grid_point (latitude, longitude, geom)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ON CONFLICT (latitude, longitude) DO NOTHING
            """, [(lat, lon, lon, lat) for lat, lon in rows])
            cur.execute("SELECT latitude, longitude, id FROM grid_point")
            return {(lat, lon): pid for lat, lon, pid in cur.fetchall()}
        

def cleanup_old_runs(cutoff_date):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Выполняем удаление. Каскадное удаление (ON DELETE CASCADE) сработает автоматически
            cur.execute("DELETE FROM forecast_run WHERE run_date < %s", (cutoff_date,))
            print(f"Очистка завершена. Удалено прогонов старше {cutoff_date}: {cur.rowcount}")

# === fetching ===

def fetch_forecast_run(run_date, cycle):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, product, run_date, cycle, collected_at
                FROM forecast_run
                WHERE run_date = %s AND cycle = %s
            """, (run_date, cycle))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "product": row[1],
                    "run_date": row[2],
                    "cycle": row[3],
                    "collected_at": row[4]
                }
            else:
                return None

def fetch_daily_weather(run_id):
    # все агрегированные поля за сутки по run_id; point_ids — опциональный фильтр списком
    q = """
        SELECT
            point_id,
            date_local,
            temp_max,
            temp_mean,
            temp_min,
            rel_hum_min,
            rel_hum_mean,
            wind_speed_mean,
            precip_sum,
            sun_hours
        FROM daily_weather
        WHERE run_id = %s
    """
    params: list = [run_id]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params)
            cols = [d.name for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
