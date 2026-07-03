CREATE EXTENSION IF NOT EXISTS postgis;

-- grid_point — узлы сетки 0.25°
CREATE TABLE grid_point (
    id        SERIAL PRIMARY KEY,
    latitude  DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom      GEOMETRY(POINT, 4326) NOT NULL,
    CONSTRAINT uq_grid_point UNIQUE (latitude, longitude)
);
CREATE INDEX idx_grid_point_geom ON grid_point USING GIST(geom);

-- forecast_run — прогон модели (дата + цикл)
CREATE TABLE forecast_run (
    id           SERIAL PRIMARY KEY,
    product      TEXT NOT NULL,        -- 'gfs.20260622'
    run_date     DATE NOT NULL,
    cycle        SMALLINT NOT NULL,     -- 0 / 6 / 12 / 18
    collected_at TIMESTAMPTZ,
    CONSTRAINT uq_forecast_run UNIQUE (run_date, cycle),
    CONSTRAINT chk_cycle CHECK (cycle IN (0, 6, 12, 18))
);

-- gfs_file — метаданные одного GRIB2-файла
CREATE TABLE gfs_file (
    id         SERIAL PRIMARY KEY,
    run_id     INTEGER NOT NULL REFERENCES forecast_run(id) ON DELETE CASCADE,
    fhour      SMALLINT NOT NULL,     -- 0 … 384
    filename   TEXT NOT NULL,         -- 'gfs.t00z.pgrb2.0p25.f096'
    init_time  TIMESTAMP NOT NULL,    -- time из метаданных GRIB
    valid_time TIMESTAMP NOT NULL,
    step       INTERVAL NOT NULL,
    subregion  GEOMETRY(POLYGON, 4326),   -- bbox области
    CONSTRAINT uq_gfs_file UNIQUE (run_id, fhour)
);
CREATE INDEX idx_gfs_file_run       ON gfs_file(run_id);
CREATE INDEX idx_gfs_file_subregion ON gfs_file USING GIST(subregion);

-- gfs_vars — переменные GFS в узле сетки
CREATE TABLE gfs_vars (
    id       BIGSERIAL PRIMARY KEY,
    file_id  INTEGER NOT NULL REFERENCES gfs_file(id)   ON DELETE CASCADE,
    point_id INTEGER NOT NULL REFERENCES grid_point(id) ON DELETE RESTRICT,
    u10   REAL,   -- U-ветер 10 м, м/с
    v10   REAL,   -- V-ветер 10 м, м/с
    t2m   REAL,   -- температура 2 м, K
    r2    REAL,   -- отн. влажность 2 м, %
    t     REAL,   -- темп. поверхности, K
    tp    REAL,   -- накопл. осадки, kg/m²
    tcdc  REAL,   -- облачность, % (GRIB: TCDC)
    sunsd REAL,   -- сол. сияние, с (GRIB: SUNSD)
    tmax  REAL,   -- макс. темп., K (fhour > 120)
    tmin  REAL,   -- мин. темп., K (fhour > 120)
    sdswrf REAL,   -- downward shortwave radiation flux, W/m²
    suswrf REAL,   -- upward shortwave radiation flux, W/m²
    sdlwrf REAL,   -- downward longwave radiation flux, W/m²
    sulwrf REAL,   -- upward longwave radiation flux, W/m²
    CONSTRAINT uq_gfs_vars UNIQUE (file_id, point_id)
);
CREATE INDEX idx_gfs_vars_file  ON gfs_vars(file_id);
CREATE INDEX idx_gfs_vars_point ON gfs_vars(point_id);