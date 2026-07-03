CREATE OR REPLACE VIEW gfs_step AS
 SELECT v.point_id,
    f.run_id,
    f.fhour,
    f.valid_time,
    v.t2m - 273.15::double precision AS temp,
    v.t - 273.15::double precision AS temp_surf,
    v.tmax - 273.15::double precision AS temp_max,
    v.tmin - 273.15::double precision AS temp_min,
    v.r2 AS rel_hum,
    v.tcdc AS cloud_cover,
    sqrt((v.u10::double precision ^ 2::double precision) + (v.v10::double precision ^ 2::double precision)) AS wind_speed,
        CASE
            WHEN lag(v.tp) OVER w IS NULL THEN v.tp
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.tp
            ELSE GREATEST(v.tp - lag(v.tp) OVER w, 0::real)
        END AS precip_step,
        CASE
            WHEN lag(v.sunsd) OVER w IS NULL THEN v.sunsd
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.sunsd
            ELSE GREATEST(v.sunsd - lag(v.sunsd) OVER w, 0::real)
        END AS sun_dur_step,
    -- радиация: stepType=avg -> де-осреднение (среднее * длину окна, потом разность), h0 = 6*floor((fhour-1)/6)
        (CASE
            WHEN lag(v.sdswrf) OVER w IS NULL THEN v.sdswrf
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.sdswrf
            ELSE GREATEST(
                (v.sdswrf * (f.fhour - 6 * floor((f.fhour - 1)::numeric / 6.0))
                 - lag(v.sdswrf) OVER w * (lag(f.fhour) OVER w - 6 * floor((f.fhour - 1)::numeric / 6.0)))
                / (f.fhour - lag(f.fhour) OVER w), 0)
        END)::double precision AS sw_down_step,
        (CASE
            WHEN lag(v.suswrf) OVER w IS NULL THEN v.suswrf
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.suswrf
            ELSE GREATEST(
                (v.suswrf * (f.fhour - 6 * floor((f.fhour - 1)::numeric / 6.0))
                 - lag(v.suswrf) OVER w * (lag(f.fhour) OVER w - 6 * floor((f.fhour - 1)::numeric / 6.0)))
                / (f.fhour - lag(f.fhour) OVER w), 0)
        END)::double precision AS sw_up_step,
        (CASE
            WHEN lag(v.sdlwrf) OVER w IS NULL THEN v.sdlwrf
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.sdlwrf
            ELSE GREATEST(
                (v.sdlwrf * (f.fhour - 6 * floor((f.fhour - 1)::numeric / 6.0))
                 - lag(v.sdlwrf) OVER w * (lag(f.fhour) OVER w - 6 * floor((f.fhour - 1)::numeric / 6.0)))
                / (f.fhour - lag(f.fhour) OVER w), 0)
        END)::double precision AS lw_down_step,
        (CASE
            WHEN lag(v.sulwrf) OVER w IS NULL THEN v.sulwrf
            WHEN floor((f.fhour - 1)::numeric / 6.0) <> floor((lag(f.fhour) OVER w - 1)::numeric / 6.0) THEN v.sulwrf
            ELSE GREATEST(
                (v.sulwrf * (f.fhour - 6 * floor((f.fhour - 1)::numeric / 6.0))
                 - lag(v.sulwrf) OVER w * (lag(f.fhour) OVER w - 6 * floor((f.fhour - 1)::numeric / 6.0)))
                / (f.fhour - lag(f.fhour) OVER w), 0)
        END)::double precision AS lw_up_step
   FROM gfs_vars v
     JOIN gfs_file f ON f.id = v.file_id
  WINDOW w AS (PARTITION BY v.point_id, f.run_id ORDER BY f.fhour);