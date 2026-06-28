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
        END AS sun_dur_step
   FROM gfs_vars v
     JOIN gfs_file f ON f.id = v.file_id
  WINDOW w AS (PARTITION BY v.point_id, f.run_id ORDER BY f.fhour);