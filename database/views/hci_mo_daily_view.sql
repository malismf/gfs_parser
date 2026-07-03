 SELECT g.mo_id,
    h.run_id,
    h.date_local,
    h.forecast_day,
    sum(h.hci * g.weight) / sum(g.weight) AS hci,
    sum(h.et * g.weight) / sum(g.weight) AS et,
    sum(h.tc * g.weight) / sum(g.weight) AS tc,
    sum(h.a * g.weight) / sum(g.weight) AS a,
    sum(h.r * g.weight) / sum(g.weight) AS r,
    sum(h.w * g.weight) / sum(g.weight) AS w,
    count(*) AS n_points
   FROM hci_daily h
     JOIN mo_grid_weight g ON g.point_id = h.point_id
  GROUP BY g.mo_id, h.run_id, h.date_local, h.forecast_day;