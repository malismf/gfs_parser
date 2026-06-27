-- hci_daily — дневные значения HCI по узлу сетки
CREATE TABLE hci_daily (
    id           BIGSERIAL PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES forecast_run(id) ON DELETE CASCADE,
    point_id     INTEGER NOT NULL REFERENCES grid_point(id)   ON DELETE RESTRICT,
    date_local   DATE    NOT NULL,
    forecast_day SMALLINT NOT NULL,  -- date_local - forecast_run.run_date (1–16)
    et           REAL,   -- эффективная температура EF, °C
    tc           REAL,   -- thermal comfort (1–10)
    a            REAL,   -- aesthetics / облачность (0–10)
    r            REAL,   -- осадки (0–5)
    w            REAL,   -- ветер (0–5)
    hci          REAL,   -- итог 4·TC + A + 3·R + 2·W (0–100)
    CONSTRAINT uq_hci_daily UNIQUE (run_id, point_id, date_local)
);

CREATE INDEX idx_hci_daily_point ON hci_daily(point_id);
CREATE INDEX idx_hci_daily_date  ON hci_daily(date_local);

-- tci_daily — дневные значения TCI по узлу сетки
CREATE TABLE tci_daily (
    id           BIGSERIAL PRIMARY KEY,
    run_id       INTEGER NOT NULL REFERENCES forecast_run(id) ON DELETE CASCADE,
    point_id     INTEGER NOT NULL REFERENCES grid_point(id)   ON DELETE RESTRICT,
    date_local   DATE    NOT NULL,
    forecast_day SMALLINT NOT NULL,  -- date_local - forecast_run.run_date (1–16)
    cid          REAL,   -- дневной комфорт по Tmax/RHmin (0–10)
    cia          REAL,   -- комфорт суточный (0–10)
    r            REAL,   -- осадки (0–5)
    s            REAL,   -- солнце (0–10)
    w            REAL,   -- ветер (0–5)
    tci          REAL,   -- итог 8·CId + 2·CIa + 4·R + 4·S + 2·W (0–100)
    CONSTRAINT uq_tci_daily UNIQUE (run_id, point_id, date_local)
);

CREATE INDEX idx_tci_daily_point ON tci_daily(point_id);
CREATE INDEX idx_tci_daily_date  ON tci_daily(date_local);