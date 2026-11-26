"""Создаёт БД из database_connection.DB_CONFIG и применяет SQL из database/."""

from pathlib import Path

import psycopg
from psycopg import sql
from database_connection import DB_CONFIG

ROOT = Path(__file__).resolve().parent

SQL_FILES = [
    ROOT / "database" / "tables" / "forecast.sql",
    ROOT / "database" / "tables" / "tci_hci_daily.sql",
    ROOT / "database" / "tables" / "utci_daily.sql",
    ROOT / "database" / "tables" / "mo_tables.sql",
    ROOT / "database" / "tables" / "era5_tci_monthly.sql",
    ROOT / "database" / "views" / "gfs_step_view.sql",
    ROOT / "database" / "views" / "daily_weather_view.sql",
    ROOT / "database" / "views" / "utci_input_view.sql",
    ROOT / "database" / "views" / "tci_mo_daily_view.sql",
    ROOT / "database" / "views" / "hci_mo_daily_view.sql",
    ROOT / "database" / "views" / "utci_mo_daily_view.sql",
    ROOT / "database" / "views" / "mo_tci_monthly_era5_norm_view.sql",
]


def connect_kwargs(dbname=None):
    cfg = dict(DB_CONFIG)
    if dbname is not None:
        cfg["dbname"] = dbname
    if cfg.get("host") == "localhost":
        cfg["host"] = "127.0.0.1"
    cfg["connect_timeout"] = 10
    return cfg


def split_statements(script: str) -> list[str]:
    statements = []
    buf = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def ensure_database():
    target = DB_CONFIG["dbname"]
    last_error = None
    for admin_db in ("postgres", "template1"):
        try:
            with psycopg.connect(**connect_kwargs(admin_db), autocommit=True) as conn:
                exists = conn.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (target,),
                ).fetchone()
                if not exists:
                    conn.execute(
                        sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target))
                    )
                    print(f"Создана база: {target}")
                else:
                    print(f"База уже есть: {target}")
                return
        except Exception as exc:
            last_error = exc
            print(f"Не удалось подключиться к {admin_db}: {exc}")

    raise RuntimeError(
        f"Не удалось создать базу {target}: нет доступа к postgres/template1"
    ) from last_error


def apply_sql():
    with psycopg.connect(**connect_kwargs(), autocommit=True) as conn:
        for path in SQL_FILES:
            if not path.exists():
                raise FileNotFoundError(path)
            rel = path.relative_to(ROOT)
            print(f"apply {rel}", flush=True)
            for stmt in split_statements(path.read_text(encoding="utf-8")):
                conn.execute(stmt)


if __name__ == "__main__":
    cfg = DB_CONFIG
    print(f"Подключение: {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['dbname']}", flush=True)
    ensure_database()
    apply_sql()
    print("Таблицы и представления созданы.")
