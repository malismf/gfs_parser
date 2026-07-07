CREATE TABLE IF NOT EXISTS era5_tci_monthly 
        point_id  INTEGER NOT NULL
                    REFERENCES grid_point(id) ON DELETE CASCADE,
        month     DATE    NOT NULL,   -- первое число месяца
        cid       REAL,               -- субиндекс дневного комфорта CId
        cia       REAL,               -- субиндекс суточного комфорта CIa
        r         REAL,               -- субиндекс осадков
        s         REAL,               -- субиндекс инсоляции
        w         REAL,               -- субиндекс ветра
        tci       REAL,               -- итоговый TCI
        t_max     REAL,               -- ср. месячная максимальная T (°C)
        rh_min    REAL,               -- ср. месячная минимальная RH (%)
        t_mean    REAL,               -- среднемесячная T (°C)
        rh_mean   REAL,               -- среднемесячная RH (%)
        ws        REAL,               -- среднемесячная скорость ветра (м/с)
        tp        REAL,               -- месячная сумма осадков (мм)
        sun_hours REAL,               -- ср. суточное солнечное сияние (ч)
        utci      REAL,               -- UTCI
        PRIMARY KEY (point_id, month)
