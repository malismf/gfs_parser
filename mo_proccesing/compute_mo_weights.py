"""
compute_mo_grid_weight.py — предрасчёт весов пересечений ячеек узлов с полигонами МО.
Запускать один раз после load_mo_boundary.py и после добавления сетки grid_point.
"""

from database_connection import get_connection

CELL = 0.125   # полуразмер ячейки узла, градусы


def compute():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE mo_grid_weight")

            # ST_Intersection ячейки узла с полигоном МО → площадь на сфероиде
            cur.execute("""
                INSERT INTO mo_grid_weight (mo_id, point_id, weight)
                SELECT
                    mo.id AS mo_id,
                    gp.id AS point_id,
                    ST_Area(
                        ST_Intersection(
                            ST_MakeEnvelope(
                                gp.longitude - %s, gp.latitude - %s,
                                gp.longitude + %s, gp.latitude + %s,
                                4326
                            ),
                            mo.geom
                        )::geography
                    ) AS weight
                FROM grid_point gp
                JOIN mo_boundary mo
                  ON ST_Intersects(
                       ST_MakeEnvelope(
                           gp.longitude - %s, gp.latitude - %s,
                           gp.longitude + %s, gp.latitude + %s,
                           4326
                       ),
                       mo.geom
                     )
                WHERE ST_Area(
                    ST_Intersection(
                        ST_MakeEnvelope(
                            gp.longitude - %s, gp.latitude - %s,
                            gp.longitude + %s, gp.latitude + %s,
                            4326
                        ),
                        mo.geom
                    )::geography
                ) > 0
            """, [CELL] * 12)

            cur.execute("SELECT COUNT(*) FROM mo_grid_weight")
            n = cur.fetchone()[0]
    print(f"Весов рассчитано: {n}")


if __name__ == "__main__":
    compute()