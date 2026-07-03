create table utci_daily (
    utci_daily_id integer generated always as identity primary key,
    run_id        integer not null references forecast_run(run_id),
    point_id      integer not null references grid_point(point_id),
    date_local    date    not null,
    forecast_day  integer not null,  
    tdb_max       real,   -- Ta в момент суточного пика UTCI, °C
    tr_max        real,   -- MRT в момент суточного пика UTCI, °C
    rh_max        real,   -- RH в момент суточного пика UTCI, %
    v_max         real,   -- ветер в момент суточного пика UTCI, м/с
    utci_max      real,   -- суточный пик UTCI, °C
    unique (run_id, point_id, date_local)
);
 