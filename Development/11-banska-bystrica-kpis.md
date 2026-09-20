---
sidebar_position: 13
title: "The Banská Bystrica Indicators"
description: Every indicator the region demonstration shows, with the field it reads, its formula, its window, its unit and the published threshold it is judged against.
---

# The Banská Bystrica indicators

Five indicators, two bodies, one definition each. A KPI is a claim about a region and the formula
is the thing that can be wrong, so this page is written before the pipeline that computes it and
before the application that shows it. Read it with
[the contract](10-banska-bystrica-contract.md), which fixes the entity these indicators are
written as, and [the source survey](../Research/banska-bystrica-open-data-sources.md), which is
where every input below was fetched from and found to answer.

## 1. Two bodies, never one label

| project | indicators of | territory each one declares |
|---|---|---|
| `bbsk` | Banskobystrický samosprávny kraj, 614 356 people | `kraj`, or `okres-{name}` for one of the 13 |
| `banskabystrica` | Mesto Banská Bystrica, 72 123 people | `mesto`, or `cast-{name}` |

An indicator of `bbsk` reads the `kraj` space and nothing else; an indicator of
`banskabystrica` reads `mesto` and `ovzdusie` and nothing else. An indicator that would need both
is two indicators in two projects. The region has roughly eight times the city's population, so
the same question gives two very different answers and only the territory separates them: a
number labelled "Banská Bystrica" with no territory is a number a viewer has to guess about.

The territory token is the suffix of the indicator's `{localId}`, so it is in the entity's id and
in its `name`. The allowed values are in
[the contract, section 6](10-banska-bystrica-contract.md#6-territories).

## 2. Air quality, where a limit value exists

Both indicators read `banskabystrica`/`ovzdusie`, the space whose `AirQualityObserved` entities
carry `pm10` and `pm25` as Properties in µg/m³ (UN/CEFACT `GQ`).

### `pm10-24h-mesto`

| | |
|---|---|
| Slovak | Priemerná 24-hodinová koncentrácia PM10 |
| English | Mean 24-hour PM10 concentration |
| Question | Is the air the city breathes over a day within the European limit? |
| Reads | `AirQualityObserved.pm10.value`, every entity of `ovzdusie` whose `dateObserved` falls in the window |
| Formula | arithmetic mean over the stations that reported |
| Window | rolling 24 hours, ending at the run |
| Unit | µg/m³, `unitCode: GQ` |
| Refresh | hourly |
| Source row | `ovzdusie`, the seeded stations of T-0945 (survey §5) |
| Territory | `mesto` |

### `pm25-rok-mesto`

| | |
|---|---|
| Slovak | Priemerná ročná koncentrácia PM2,5 |
| English | Mean calendar-year PM2.5 concentration |
| Question | Is the city's year-round fine particulate exposure within the European limit? |
| Reads | `AirQualityObserved.pm25.value` |
| Formula | arithmetic mean over the calendar year to date |
| Window | 1 January to the run |
| Unit | µg/m³, `unitCode: GQ` |
| Refresh | daily |
| Source row | `ovzdusie`, the seeded stations of T-0945 |
| Territory | `mesto` |

### What makes them red

Every number below is from Directive 2008/50/EC on ambient air quality, fetched from
`https://eur-lex.europa.eu/eli/dir/2008/50/oj` on 2026-09-20. None of them is a number somebody
liked.

| indicator | green | amber | red | where the numbers are |
|---|---|---|---|---|
| `pm10-24h-mesto` | below 35 | 35 to below 50 | 50 or above | Annex XI B: 24-hour limit value 50 µg/m³, not to be exceeded more than 35 times a calendar year. Annex II A.3: upper assessment threshold 70 % of the limit value, 35 µg/m³. |
| `pm25-rok-mesto` | below 17 | 17 to below 25 | 25 or above | Annex XIV E: Stage 1 calendar-year limit value 25 µg/m³. Annex II A.3: upper assessment threshold 70 % of the limit value, 17 µg/m³. |

Amber is the directive's own upper assessment threshold, the level above which a zone has to
measure rather than model. It is the published step between "clean" and "over the limit", which
is why it is the amber here instead of a round fraction chosen for the dashboard.

**A threshold is not the entity's.** The three states above are computed by the application from
the value and the limits on this page, not stored on the indicator: PF-54 fixes the
`KeyPerformanceIndicator` attribute set and the published schema closes it
([the contract, section 4](10-banska-bystrica-contract.md#4-the-kpi-entity)). A threshold changes
without the number changing, and two departments may hold different ones, so it belongs to
whoever reads the number.

**Both are comparable to a regional pair the moment one exists, and one does not.** The survey
found no air-quality source for the kraj that answers: SHMÚ, who measures it, did not answer, and
the annual emission totals in section 3 are a different quantity. Until one exists, the air
indicators are the city's alone and the application shows them under the city, never under a
heading that could be read as the region's.

**These two read a seeded snapshot, and say so.** `ovzdusie` holds the thirteen stations T-0945
seeded and nothing refreshes them. `calculationPeriod` is the window the values were observed in,
`updatedAt` is when the pipeline ran, and the two diverging is the visible fact that the source is
static. No value is carried forward and relabelled as current.

## 3. The region's indicators, which have no published threshold

### `emisie-tuhe-km2-{territory}`

| | |
|---|---|
| Slovak | Emisie tuhých znečisťujúcich látok na km² |
| English | Solid particulate emissions per square kilometre |
| Question | How much particulate matter do large and medium sources release per square kilometre of this territory? |
| Reads | `StatisticalObservation.value`, cube `zp3803rs`, indicator `ODPAD_TONY_KM2`, pollutant `1` (tuhé emisie) |
| Formula | the publisher's own value for the territory, taken as published, not recomputed |
| Window | one calendar year, the latest the cube carries |
| Unit | tonnes per km², `unitCode: TNE` with the per-km² divisor named in `calculationFormula` |
| Refresh | annual |
| Source row | `zp3803rs`, survey §2 |
| Territory | `kraj`, and `okres-{name}` for each of the 13 |

### `obyvatelstvo-stav-{territory}`

| | |
|---|---|
| Slovak | Stav trvale bývajúceho obyvateľstva na konci obdobia |
| English | Resident population at the end of the period |
| Question | How many people does this territory have, and which way is it moving? |
| Reads | `StatisticalObservation.value`, cube `om7102rr`, indicator `IN010115`, sex `SPOLU` |
| Formula | the publisher's own value for the territory |
| Window | one calendar year, the latest the cube carries |
| Unit | persons, `unitCode: C62` |
| Refresh | annual |
| Source row | `om7102rr`, survey §2 |
| Territory | `kraj`, and `okres-{name}` for each of the 13 |

### `spotreba-vody-obyvatel-mesto`

| | |
|---|---|
| Slovak | Fakturovaná spotreba pitnej vody na obyvateľa za deň |
| English | Invoiced drinking water per inhabitant per day |
| Question | How much drinking water does the city buy per person per day? |
| Reads | `StatisticalObservation.value`, cube `vh5003rr`, indicator `U03084`, territory `SK0321508438`; and the city's own age register for the divisor |
| Formula | `value × 1 000 000 ÷ population ÷ days(window)`, the cube being in thousands of m³ and a m³ being 1 000 litres |
| Window | one calendar year, the latest the cube carries |
| Unit | litres per inhabitant per day, `unitCode: LTR` with the per-inhabitant-per-day divisor named in `calculationFormula` |
| Refresh | annual |
| Source row | `vh5003rr` and the city age register, survey §2 |
| Territory | `mesto` |

It is **invoiced** water, not water used: the cube's own note says it is the quantity billed to
direct customers, metered where a meter is fitted and estimated from consumption norms where one
is not, and the underlying data is the Výskumný ústav vodného hospodárstva's, not ŠÚ SR's own.
The name says `fakturovaná` for that reason, and the application shows that word.

### Why these three have no state

None of the three has a published limit, in legislation or as a regional target, that this
demonstration could fetch and cite:

| indicator | what was looked for and not found |
|---|---|
| `emisie-tuhe-km2-*` | Directive (EU) 2016/2284 sets Slovakia national emission reduction commitments against a 2005 baseline, and `zp3803rs` carries only 2019 to 2023, so the baseline the commitment is measured from is not in the feed. A regional per-km² limit does not exist. |
| `obyvatelstvo-stav-*` | a population count has no limit value. BBSK's own development plan may carry a demographic target; `bbsk.sk` did not answer, so there is nothing to cite. |
| `spotreba-vody-obyvatel-mesto` | vyhláška 684/2006 Z. z. sets indicative consumption figures, and `slov-lex.sk` serves the page as an application shell whose text could not be read from here, so the figure is not quoted. |

They are therefore **context indicators**: the application shows the value, its unit, its window
and the direction it moved since the previous window, and no colour and no word implying a
judgement. A number with no threshold shown as green or red is a judgement nobody made, which is
worse than a number with no threshold. When a citation is found, the threshold is added here
first and the application reads it from here.

## 4. Every indicator, in one table

| id | project | territory | unit | window | refresh | thresholded |
|---|---|---|---|---|---|---|
| `pm10-24h-mesto` | `banskabystrica` | `mesto` | µg/m³ | rolling 24 h | hourly | yes |
| `pm25-rok-mesto` | `banskabystrica` | `mesto` | µg/m³ | calendar year to date | daily | yes |
| `spotreba-vody-obyvatel-mesto` | `banskabystrica` | `mesto` | l/person/day | calendar year | annual | no, context |
| `emisie-tuhe-km2-{territory}` | `bbsk` | `kraj` + 13 okresy | t/km² | calendar year | annual | no, context |
| `obyvatelstvo-stav-{territory}` | `bbsk` | `kraj` + 13 okresy | persons | calendar year | annual | no, context |

Fourteen territories each for the two regional indicators, three indicators for the city: 31
`KeyPerformanceIndicator` entities in all, 28 in `bbsk-kpi` and 3 in `banskabystrica-kpi`.

## 5. What is not defined, and why

- **No indicator derived from the city's DTM registers** (green space, street lighting, parking).
  They answer and they are licensed, but they are ZIP archives of DBF tables whose reading is a
  piece of work of its own, and the survey recorded them as context only.
- **No unemployment indicator.** `pr3117qr` answers and is licensed, and it carries the kraj
  only, in thousands of persons and not as a rate. A rate needs the economically active
  population for the same window from a second cube, which is a join this demonstration does not
  need, and an absolute count of unemployed people beside a population count invites the reader
  to divide two numbers with different windows.
- **No indicator that could identify a person or a household.** Every input above is an
  aggregate over a territory: the smallest published unit is one municipality with 72 123
  inhabitants, and the city age register is a count per year of age with no name and no address.

## Related

- [The Banská Bystrica contract](10-banska-bystrica-contract.md) — the entity these indicators are written as, and the territories they may declare.
- [Open data sources of the region](../Research/banska-bystrica-open-data-sources.md) — where every input was fetched from, with its status code.
- [Pipelines](../Architecture/08-pipelines.md) — the mapping that computes an indicator and writes it with its provenance.
- [Domain model](../Architecture/03-domain-model.md#when-one-number-is-not-the-indicator-dm-60) — when one number is the indicator and when it is a data cube.
