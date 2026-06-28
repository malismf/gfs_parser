-- mo_boundary — полигоны МО Иркутской области
CREATE TABLE IF NOT EXISTS mo_boundary (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY, 
    name    TEXT NOT NULL,       
    name_mo TEXT NOT NULL,       
    code    TEXT,
    geom    GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mo_boundary_geom ON mo_boundary USING GIST(geom);

-- mo_grid_weight — предрасчитанные веса ячеек узлов по МО
CREATE TABLE IF NOT EXISTS mo_grid_weight (
    mo_id    INTEGER NOT NULL REFERENCES mo_boundary(id),
    point_id INTEGER NOT NULL REFERENCES grid_point(id) ON DELETE RESTRICT,
    weight   DOUBLE PRECISION NOT NULL,   -- площадь пересечения, м²
    PRIMARY KEY (mo_id, point_id)
);