# gfs_parser

Сбор прогноза GFS 0.25° (NOMADS) по Иркутской области, запись в PostgreSQL/PostGIS и расчёт климатических индексов: **TCI**, **HCI**, **UTCI**.

## Что делает проект

1. Скачивает GRIB2 через серверную подвыборку NOMADS (квадрат `50.5–64.52°N`, `95.5–119.55°E`).
2. Извлекает поля (температура, влажность, ветер, осадки, облачность, радиация, SUNSD и т.д.) и пишет их в `gfs_vars`.
3. По суточным агрегатам из представлений БД считает индексы и сохраняет результаты в таблицы `tci_daily`, `hci_daily`, `utci_daily`.
4. Опционально агрегирует индексы по муниципальным образованиям (МО).

Горизонт прогноза: почасово до 120 ч, далее шаг 3 ч до 384 ч.

## Требования

- Python 3.11+
- PostgreSQL с расширением **PostGIS**
- Библиотека **ecCodes** (ECMWF) — нужна `cfgrib` для чтения GRIB2

На Windows ecCodes удобнее ставить через [conda-forge](https://anaconda.org/conda-forge/eccodes) или готовый бинарный пакет; пакет `eccodes` из `requirements.txt` — Python-обёртка, без системной библиотеки GRIB не откроется.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

**Дата прогона** задаётся в `date_config.py`:

```python
RUN_DATE = "2026-11-25"
```

**Подключение к БД** — в `database_connection.py` (`host`, `port`, `dbname`, `user`, `password`). По умолчанию база `tourist-climate-assessment` на `localhost:5432`.

**Схема БД** (порядок важен: сначала таблицы, потом представления):

```text
database/tables/forecast.sql
database/tables/tci_hci_daily.sql
database/tables/utci_daily.sql
database/tables/mo_tables.sql
database/tables/era5_tci_monthly.sql

database/views/gfs_step_view.sql
database/views/daily_weather_view.sql
database/views/utci_input_view.sql
database/views/tci_mo_daily_view.sql
database/views/hci_mo_daily_view.sql
database/views/utci_mo_daily_view.sql
database/views/mo_tci_monthly_era5_norm_view.sql
```

Пример:

```bash
psql -d tourist-climate-assessment -f database/tables/forecast.sql
```

## Запуск

Полный цикл (скачивание GFS + TCI + HCI + UTCI):

```bash
python run.py
```

Отдельно:

```bash
python collect_gfs.py
python -m index_calculation.calculate_tci
python -m index_calculation.calculate_hci
python -m index_calculation.calculate_utci
```

`collect_gfs.py` берёт самый ранний доступный цикл модели за `RUN_DATE` (обычно 00 UTC), чистит старые прогоны и пишет данные в БД. Файлы GRIB во временный каталог, на диск не сохраняются (`dest=None`).

Если на NOMADS ещё нет полного прогона на выбранную дату, сборщик завершится без загрузки.

## Муниципальные образования

Скрипты в `mo_proccesing/` (порядок запуска):

1. `load_mo_boundary.py` — полигоны МО из GeoJSON (`MO_Irk_region_4326.geojson`) в `mo_boundary`.
2. `compute_mo_weights.py` — веса пересечения ячеек сетки с полигонами (`mo_grid_weight`). Запускать после появления узлов в `grid_point`.
3. `aggregate_tci_mo.py` — взвешенное среднее TCI по МО, CSV `tci_mo_YYYYMMDD.csv`.

Индексы по МО также доступны через SQL-представления `*_mo_daily_view.sql`.

## Структура

```text
run.py                      — точка входа пайплайна
collect_gfs.py              — загрузка GFS и запись в БД
util_gfs.py                 — разбор GRIB2
database_connection.py      — PostgreSQL
date_config.py              — дата прогона
index_calculation/          — TCI, HCI, UTCI
mo_proccesing/              — границы МО и агрегация
database/tables/            — DDL таблиц
database/views/             — представления
```

## Индексы

| Индекс | Источник | Что считается |
|--------|----------|----------------|
| TCI | Mieczkowski (1985) | комфорт, осадки, солнце, ветер; шкала до 100 |
| HCI | de Freitas et al. (2004) | эффективная температура и субиндексы |
| UTCI | `pythermalcomfort` | полином UTCI, суточный максимум |

Вход для TCI/HCI — представление `daily_weather`; для UTCI — `utci_input` (температура, влажность, ветер, средняя радиационная температура).
