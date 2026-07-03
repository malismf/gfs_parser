 SELECT g.mo_id,
    t.run_id,
    t.date_local,
    t.forecast_day,
    sum(t.cid * g.weight) / sum(g.weight) AS cid,
    sum(t.cia * g.weight) / sum(g.weight) AS cia,
    sum(t.r * g.weight) / sum(g.weight) AS r,
    sum(t.s * g.weight) / sum(g.weight) AS s,
    sum(t.w * g.weight) / sum(g.weight) AS w,
    sum(t.tci * g.weight) / sum(g.weight) AS tci
   FROM tci_daily t
     JOIN mo_grid_weight g ON g.point_id = t.point_id
  GROUP BY g.mo_id, t.run_id, t.date_local, t.forecast_day
  ORDER BY g.mo_id, t.date_local;