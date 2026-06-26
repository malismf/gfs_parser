CREATE OR REPLACE VIEW daily_weather AS
SELECT
    run_id,
    point_id,
    (valid_time + INTERVAL '8 hours')::date AS date_local,   -- сутки по UTC+8

    avg(temp)                       AS temp_mean,
    max(greatest(temp, temp_max))   AS temp_max,   -- tmax null -> = temp
    min(least(temp, temp_min))      AS temp_min,
    avg(rel_hum)                    AS rel_hum_mean,
    min(rel_hum)                    AS rel_hum_min,
    avg(wind_speed)                 AS wind_speed_mean,
    sum(precip_step)                AS precip_sum,
    sum(sun_dur_step) / 3600.0      AS sun_hours

FROM gfs_step
GROUP BY run_id, point_id, date_local;