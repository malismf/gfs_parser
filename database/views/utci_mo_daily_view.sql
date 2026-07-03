CREATE OR REPLACE VIEW utci_mo_daily AS
SELECT
    u.run_id,
    u.date_local,
    w.mo_id,
    sum(u.tdb_max  * w.weight) / sum(w.weight) AS tdb_max,
    sum(u.tr_max   * w.weight) / sum(w.weight) AS tr_max,
    sum(u.rh_max   * w.weight) / sum(w.weight) AS rh_max,
    sum(u.v_max    * w.weight) / sum(w.weight) AS v_max,
    sum(u.utci_max * w.weight) / sum(w.weight) AS utci_max
FROM utci_daily u
JOIN mo_grid_weight w ON w.point_id = u.point_id
GROUP BY u.run_id, u.date_local, w.mo_id;