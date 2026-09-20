---
sidebar_position: 5
title: "Open Data Sources: Banská Bystrica Region"
description: Every candidate feed for the two Banská Bystrica projects, each one fetched on 2026-09-20 with its status code recorded.
---

# Open data sources of the Banská Bystrica region

Which published feeds the `bbsk` and `banskabystrica` projects can ingest, and which they cannot.
Read this before building a pipeline or naming a KPI: a KPI computed from a feed that does not
answer is a fabricated number on a dashboard shown to a region. Every URL below was fetched once
with `curl` on 2026-09-20 from the build sandbox and its status code is in the table beside it.
Nothing here is quoted from a catalogue page without the endpoint itself answering.

## 1. Who publishes what

Four levels of publisher appear, and they are not interchangeable.

| level | body | territory | people |
|---|---|---|---|
| `region` | Banskobystrický samosprávny kraj (BBSK), IČO 37828100 | the whole kraj, NUTS `SK032`, 13 okresy | 611 124 at the end of 2024 |
| `city` | Mesto Banská Bystrica, IČO 00313271 | the city, LAU `SK0321508438` | 72 123 in the city's own register |
| `national` | ŠÚ SR, MIRRI (the NKOD catalogue), SHMÚ, NCZI | the whole state, broken down to kraj and okres | |
| `operator` | ŽSR, SAD, a utility | a network, not a territory | |

Both population figures were read from the feeds in section 3, not from a press page. The kraj
figure is the end-of-2024 stock in `om7102rr`; a rounded "640 000" that circulates for BBSK is
about 5 % high, and the kraj lost 3 232 people between the end of 2023 and the end of 2024. The
city figure is the sum of the 105 age rows the city itself publishes, and the ŠÚ SR okres figure
for the same territory is 106 604, because an okres is not a city. A city
number presented as a regional one is wrong by a factor of eight in population alone, and that
error is invisible on a dashboard, so every row below says which project it belongs to.

**The region publishes nothing.** A query for IČO 37828100 against the national catalogue returns
zero triples: BBSK has no dataset, no distribution and no publisher record in NKOD. The `bbsk`
project therefore has no feed of its own. It is fed from national sources filtered to `SK032` and
its 13 okresy, which is what the `covers` column records.

## 2. What the demonstration uses

Four feeds, two per body, all answering, all licensed. This is the set T-2305 ingests.

| name | publisher | covers | project | URL | status | format | licence | update rate | NGSI-LD type | KPI it feeds |
|---|---|---|---|---|---|---|---|---|---|---|
| Počet obyvateľov podľa pohlavia (`om7102rr`) | `national` ŠÚ SR | kraj `SK032` and its 13 okresy | `bbsk` | `https://data.statistics.sk/api/v2/dataset/om7102rr/SK032,SK0321/2023,2024/IN010115/SPOLU?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, last 2026-03-31 | none, needs a decision (see section 5) | the denominator of every per-capita KPI |
| Emisie základných znečisťujúcich látok (`zp3803rs`) | `national` ŠÚ SR | kraj and okresy, large and medium sources | `bbsk` | `https://data.statistics.sk/api/v2/dataset/zp3803rs/SK032,SK0321/2022,2023/PROD_TONY/1,3?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, last 2025-10-31 | none, needs a decision | emissions per square kilometre, per okres |
| Počet občanov podľa veku | `city` Mesto Banská Bystrica | the city only | `banskabystrica` | `https://egov.banskabystrica.sk/Default.aspx?NavigationState=920:0::plac1140:_144053_5_8` | 200 | JSON, 105 rows | CC-BY-4.0 | not declared by the publisher | none, needs a decision | the city's age structure and its per-capita denominator |
| Spotreba pitnej vody (`vh5003rr`) | `national` ŠÚ SR | down to the municipality, `SK0321508438` | `banskabystrica` | `https://data.statistics.sk/api/v2/dataset/vh5003rr/SK0321508438,SK032/2022,2023/U03084?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, last 2026-09-07 | none, needs a decision | drinking water per inhabitant per day |

Two more answer and are worth having, and neither is needed for the story to be real:

| name | publisher | covers | project | URL | status | format | licence | update rate | NGSI-LD type | KPI it feeds |
|---|---|---|---|---|---|---|---|---|---|---|
| Nezamestnaní podľa veku (`pr3117qr`) | `national` ŠÚ SR | kraj only, no okres breakdown | `bbsk` | `https://data.statistics.sk/api/v2/dataset/pr3117qr/SK032/2025/*/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | quarterly, last 2026-09-09 | none, needs a decision | unemployment, kraj window only |
| DTM register verejnej zelene | `city` Mesto Banská Bystrica | the city only | `banskabystrica` | `https://dtm-banskabystrica.tmapserver.sk/opendata/bb_pazel_t_dbf.zip` | 200 | ZIP of DBF and PDF | CC-BY-4.0 | not declared by the publisher | none, needs a decision | context only, until the DBF is read |

### How the ŠÚ SR API is called

One cube, one slice, one request. The path is
`/api/v2/dataset/{cube}/{territory}/{period}/{indicator}/{…}`, every segment a comma-separated
list of codes or `*` for all of them, and the answer is JSON-stat: `value` is a flat array in the
row-major order of `size`, and `dimension.{name}.category.label` names each code. The codes come
from `/api/v2/dimension/{cube}/{dimension}?lang=sk`, and `/api/v2/collection` lists all 678 cubes
with the date each was last updated. Territories are NUTS and LAU codes, so `SK032` is the kraj,
`SK0321` the okres and `SK0321508438` the city.

```bash
curl -s 'https://data.statistics.sk/api/v2/dimension/om7102rr/om7102rr_vuc?lang=sk'
```

**Read the index, never the order.** `value` is flat and row-major over `size`, and the position
of a code inside a dimension is `dimension.{name}.category.index`, which is **not** sorted.
`om7102rr_obd` comes back `["2024", "2023"]` and `vh5003rr_rok` comes back `["2023", "2022"]`:
newest first. A reader who assumes the years ascend reports every number against the wrong year,
and the value is real, so nothing about it looks wrong. Every consumer of these feeds decodes by
the index, and `tests/test_bystrica_pipelines.py` in the deployment repository fails on a mapping
that does not.

## 3. What the feeds actually returned

The numbers below came out of the requests in section 2 on 2026-09-20. They are here so that the
first pipeline has something to be checked against.

| feed | slice | value |
|---|---|---|
| `om7102rr` | `SK032`, end of 2023 then 2024, both sexes | 614 356, then 611 124 |
| `om7102rr` | `SK0321` (okres Banská Bystrica), same window | 107 199, then 106 604 |
| `zp3803rs` | `SK032`, 2022 then 2023, solid emissions in tonnes | 5 354.3, then 4 037.7 |
| `zp3803rs` | `SK032`, same years, nitrogen oxides in tonnes | 6 523.9, then 5 560.0 |
| `vh5003rr` | city `SK0321508438`, 2022 then 2023, total drinking water | 3 991, then 3 868 |
| `vh5003rr` | `SK032`, same years | 22 337, then 21 589 |
| `pr3117qr` | `SK032`, 2025, unemployed by age, thousands of persons | 11.7 in the first quarter, 12.7 in the second |
| city age register | all 105 rows summed | 72 123 inhabitants, ages 0 to 104 |

`vh5003rr` carries its own provenance and it is not ŠÚ SR: the cube's note names Výskumný ústav
vodného hospodárstva as the source and the unit as thousands of cubic metres of **invoiced**
drinking water, metered where a meter is fitted and estimated from consumption norms where one is
not. A per-inhabitant KPI built on it is therefore water sold, not water used, and its name has to
say so.

## 4. Candidates that were refused, and why

A source that does not answer is written down, not dropped. Each of these was fetched on the same
day from the same sandbox.

| candidate | URL | status | why it is not used |
|---|---|---|---|
| BBSK open data | `https://www.bbsk.sk/` | 000, connection timed out after 25 s | the host did not answer. BBSK also publishes nothing in NKOD (zero triples for IČO 37828100), so there is nothing behind it to ingest even when it answers. |
| City open data portal | `https://opendata.banskabystrica.sk/` | 000, connection timed out after 25 s | the host did not answer. The city's data is reachable through `egov.banskabystrica.sk` instead, which is what the catalogue records as the download URL. |
| Old national portal | `https://data.gov.sk/` | 000, connection timed out after 25 s | superseded by `data.slovensko.sk`. The `data.gov.sk` hostname survives only as the IRI namespace inside the catalogue's RDF, where it is an identifier and not an address. |
| SHMÚ air quality and hydrology | `https://www.shmu.sk/` | 000, connection timed out after 25 s | the publisher of the region's real air-quality observations did not answer. This is the one gap that matters, see section 5. |
| ŽSR train timetable, GTFS | `https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip` | 200, but `text/html` | the declared download URL serves an HTML page titled "ŽSR \| GTFS info", not the archive. The catalogue's own mirror below does serve the ZIP. |
| City open-data endpoint, licence check | the 43 datasets of IČO 00313271 | n/a | none of them carries `dct:license`. The licence is in the Slovak `legislation:termsOfUse` node instead, and it resolves to CC-BY-4.0 for authors' work, original database and the database maker's special right alike. A reader who looks only for `dct:license` will conclude, wrongly, that the city's data is unlicensed. |

The catalogue mirror that does work, kept as a candidate rather than used, because the
demonstration needs no timetable:

| name | publisher | covers | project | URL | status | format | licence | update rate |
|---|---|---|---|---|---|---|---|---|
| Grafikon vlakovej dopravy, GTFS | `operator` ŽSR | the whole network, stations inside the kraj | `bbsk` | `https://data.slovensko.sk/download?id=c4cc7f26-a5ce-4416-b2e7-96983d01cc33` | 200, a ZIP served as `text/csv` | GTFS in a ZIP | CC-BY-1.0 on the mirror, CC0 on the publisher's own copy | with the timetable |

## 5. The two decisions this survey leaves open

**Air quality has no regional source that answers.** `banskabystrica`/`ovzdusie` holds thirteen
seeded `AirQualityObserved` entities from T-0945 and nothing refreshes them, because SHMÚ, who
measures the region's air, did not answer. The annual emission totals in `zp3803rs` are a
different quantity: they are what large and medium plants reported over a year, not what a
station measured this hour, and presenting one as the other would be the fabrication this survey
exists to prevent. Either the air-quality KPI is built on the annual emission totals and says so
in its name and its window, or the demonstration reaches SHMÚ through a route this sandbox does
not have. T-2306 decides which, and this page does not.

**None of the six feeds is a Smart Data Model.** Every one is a statistical table: a territory
code, a period, an indicator code and a number. There is no `AirQualityObserved`, no
`WaterConsumption`, no entity type to map onto, so the `NGSI-LD type` column above says "none,
needs a decision" for all of them. Section 2 of the contract page settles what the raw spaces
hold, and T-2306 settles which Smart Data Model type, if any, each table becomes.

## 6. Provenance of every claim on this page

| claim | where it was read |
|---|---|
| status codes, content types and byte counts | `curl -L --max-time 25` from the build sandbox, 2026-09-20 |
| licences | the national catalogue's SPARQL endpoint, `https://data.slovensko.sk/api/sparql`, through `legislation:termsOfUse` and its `authorsWorkType` |
| BBSK publishes nothing | the same endpoint: `SELECT ?p ?o WHERE { <https://data.gov.sk/id/legal-subject/37828100> ?p ?o }` returned no rows |
| the catalogue holds 22 543 datasets | the same endpoint, `SELECT (COUNT(*) AS ?n) WHERE { ?s a dcat:Dataset }` |
| the 13 okres codes | `https://data.statistics.sk/api/v2/dimension/om7102rr/om7102rr_vuc?lang=sk` |
| update rates | the `update` field each cube carries in `https://data.statistics.sk/api/v2/collection` |

No key, token or credential was needed for any row, and none is written here. A source that comes
to need one is named with a `secretRef:` and the secret is filed separately, never in this page or
in a task body.

## Related

- [The Banská Bystrica contract](../Development/10-banska-bystrica-contract.md) — the projects, spaces, URNs and KPI entity these feeds are ingested into.
- [Ingestion examples](../Development/06a-ingestion-examples.md) — how a pipeline reads a feed like these.
- [Data models](../Architecture/11-data-models.md) — what has to exist before a table becomes a typed entity.
- [Pipelines](../Architecture/08-pipelines.md) — where the fetch, the mapping and the write live.
