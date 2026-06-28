"""
load_mo_boundary.py — загружает полигоны МО из GeoJSON в таблицу mo_boundary.
"""

import json
import psycopg
from database_connection import get_connection

GEOJSON_PATH = "MO_Irk_region_4326.geojson"


def load(path=GEOJSON_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for feat in data["features"]:
        p = feat["properties"]
        rows.append((
            p["name"],
            p.get("name_MO") or p["name"],      # у городов name_MO пустой → подставляем name
            p.get("code"),
            json.dumps(feat["geometry"]),       # GeoJSON geometry → ST_GeomFromGeoJSON
        ))
    return rows


def insert(rows):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE mo_boundary RESTART IDENTITY CASCADE")
            cur.executemany("""
                INSERT INTO mo_boundary (name, name_mo, code, geom)
                VALUES (
                    %s, %s, %s,
                    ST_Multi(ST_MakeValid(ST_GeomFromGeoJSON(%s)))
                )
            """, rows)
    print(f"Загружено МО: {len(rows)}")


def main():
    rows = load()
    insert(rows)


if __name__ == "__main__":
    main()