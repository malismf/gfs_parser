 SELECT b.id AS mo_id,
    b.name,
    EXTRACT(month FROM e.month)::integer AS mnum,
    sum(e.tci * g.weight) / sum(g.weight) AS tci_norm
   FROM era5_tci_monthly e
     JOIN mo_grid_weight g ON g.point_id = e.point_id
     JOIN mo_boundary b ON b.id = g.mo_id
  GROUP BY b.id, b.name, (EXTRACT(month FROM e.month)::integer);