CREATE VIEW utci_mo_daily AS
SELECT
    u.run_id,
    u.date_local,
    u.forecast_day,
    w.mo_id,
    sum(u.tdb_max  * w.weight) / sum(w.weight) AS tdb_max,   -- Ta в момент пика UTCI, °C
    sum(u.tr_max   * w.weight) / sum(w.weight) AS tr_max,    -- MRT в момент пика UTCI, °C
    sum(u.rh_max   * w.weight) / sum(w.weight) AS rh_max,    -- RH в момент пика UTCI, %
    sum(u.v_max    * w.weight) / sum(w.weight) AS v_max,     -- ветер в момент пика UTCI, м/с
    sum(u.utci_max * w.weight) / sum(w.weight) AS utci_max   -- суточный пик UTCI, °C
FROM utci_daily u
JOIN mo_grid_weight w ON w.point_id = u.point_id
GROUP BY u.run_id, u.date_local, u.forecast_day, w.mo_id;
 