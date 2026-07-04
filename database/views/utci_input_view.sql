CREATE OR REPLACE VIEW utci_input AS
SELECT
    point_id,
    run_id,
    fhour,
    valid_time,
    (valid_time + INTERVAL '8 hours')::timestamp AS local_time, -- сутки по UTC+8
    temp       AS temp,        -- Ta, °C   -> tdb
    rel_hum    AS rel_hum,     -- RH, %    -> rh
    wind_speed AS wind_speed,  -- v, м/с @10м -> v
    -- mrt из 4 потоков радиации; результат в °C -> tr
    power(
        ( (lw_down_step + lw_up_step) / 2.0
          + (0.7 / 0.97) * (sw_down_step + sw_up_step) / 2.0 )
        / 5.67e-8,
        0.25
    ) - 273.15 AS mrt
FROM gfs_step;