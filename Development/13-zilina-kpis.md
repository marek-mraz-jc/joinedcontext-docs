---
sidebar_position: 15
title: "The Žilina Indicators"
description: Every indicator the zilina project computes, with the cube field it reads, its formula, its window and its unit; all six are context indicators without a threshold.
---

# The Žilina indicators

Six indicators of one body, the city of Žilina (`SK031B517402`, 79 617 people on 30 June 2026),
each read from the ŠÚ SR rows the `zilina` project keeps in `zilina-mesto` and written as one
`KeyPerformanceIndicator` into `zilina-kpi` by the pipeline `ukazovatele`. The entity, the "not
measured" value and the territory token follow
[the Banská Bystrica contract](10-banska-bystrica-contract.md) unchanged; the sources are in
[the Žilina survey](../Research/zilina-open-data-sources.md).

## 1. One territory, one space read

Every indicator declares the territory `mesto`, so its id ends in `-mesto`. The pipeline reads
`zilina-mesto` through its Endpoint and nothing else: one pipeline writes `zilina-kpi`, which is
what lets it expire an indicator the city stopped publishing (PL-64).

The air of the city is not an indicator here. `zilina-verejne` keeps the latest hour of station
`SK0020A` and no history, so no 24-hour or annual mean can be computed from it, and a single
hour has no limit value for PM10 or PM2.5 in Directive 2008/50/EC. The application shows the
station's readings as readings, with their hour.

## 2. The indicators

Each value is the publisher's own number for the city, taken as published, not recomputed, from
the newest period the cube carries, except the visitors, which add up the months of one year.

### `obyvatelstvo-stav-mesto`

| | |
|---|---|
| Slovak | Stav trvale bývajúceho obyvateľstva na konci obdobia |
| English | Resident population at the end of the quarter |
| Reads | cube `om7101qr`, indicator `IN010115`, sex `SPOLU` |
| Window | the newest quarter the cube carries |
| Unit | persons, `unitCode: C62` |
| Refresh | quarterly |

### `index-starnutia-mesto`

| | |
|---|---|
| Slovak | Index starnutia |
| English | Ageing index: people of post-productive age per 100 children |
| Reads | cube `om7052rr`, indicator `IN010087`, sex `SPOLU` |
| Window | the newest calendar year |
| Unit | percent, `unitCode: P1` |
| Refresh | annual |

### `priemerny-vek-mesto`

| | |
|---|---|
| Slovak | Priemerný vek obyvateľa |
| English | Mean age of a resident |
| Reads | cube `om7052rr`, indicator `IN010089`, sex `SPOLU` |
| Window | the newest calendar year |
| Unit | years, `unitCode: ANN` |
| Refresh | annual |

### `celkovy-prirastok-mesto`

| | |
|---|---|
| Slovak | Celkový prírastok obyvateľstva |
| English | Total population change: births less deaths plus net migration |
| Reads | cube `om7105rr`, indicator `IN010082`, sex `SPOLU` |
| Window | the newest calendar year |
| Unit | persons, `unitCode: C62`; a loss is negative |
| Refresh | annual |

### `uchadzaci-mesto`

| | |
|---|---|
| Slovak | Počet evidovaných uchádzačov o zamestnanie |
| English | Registered jobseekers |
| Reads | cube `pr5001rr`, indicator `U15061` |
| Window | the newest calendar year |
| Unit | persons, `unitCode: C62` |
| Refresh | annual |

ŠÚ SR publishes no municipal unemployment rate: the cube counts people, and dividing them by the
population would mix registered jobseekers with children and pensioners. The count is the number.

### `navstevnici-rok-mesto`

| | |
|---|---|
| Slovak | Počet návštevníkov ubytovacích zariadení za rok |
| English | Visitors staying in the city's accommodation over a year |
| Reads | cube `cr3803mr`, indicator `U_CR_0005`, visitors `VISIT_TOTAL`, months 1 to 12 |
| Formula | the sum of the twelve months of the newest year that carries all twelve |
| Window | that calendar year |
| Unit | persons, `unitCode: C62` |
| Refresh | monthly, changing once a year |

The current year is never summed while months are missing: eight months of 2026 next to twelve
of 2025 would read as a collapse in tourism.

## 3. No threshold, no colour

None of the six has a limit value or a published target of the city to cite. They are context
indicators, as section 3 of [the Banská Bystrica indicators](11-banska-bystrica-kpis.md)
defines them: the application shows the value, its unit, its window and the formula, never a
colour or a word that judges it. The entity holds one window, so no direction is shown: a
previous value would be a second number this page does not define.

## 4. When a cube stops

A run whose read brings no row of any of the five cubes writes nothing (the endpoint refused the
pipeline, or answered something else). An indicator whose cube drops out alone is written as
`not measured` with the window it looked at. An indicator unseen for three weekly runs is deleted
by the pipeline's expiry, never shown with a stale value.

## Related

- [The Banská Bystrica contract](10-banska-bystrica-contract.md): the KPI entity and "not measured".
- [The Banská Bystrica indicators](11-banska-bystrica-kpis.md): what a context indicator is.
- [Open data sources of Žilina](../Research/zilina-open-data-sources.md): where every cube was fetched.
- [Open data integration rules](12-open-data-integration.md): the rules the project follows.
