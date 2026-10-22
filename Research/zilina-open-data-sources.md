---
sidebar_position: 8
title: "Open Data Sources: Žilina"
description: Every candidate feed for the zilina project (the city of Žilina and the University of Žilina), each one fetched on 2026-10-06 with its status, licence and target model, and the city's own open data portal read on 2026-10-22.
---

# Open data sources of Žilina

Which published feeds the `zilina` project can ingest for the city of Žilina (space `mesto`) and
the University of Žilina (space `uniza`), and which it cannot. It follows
[Open data integration rules](../Development/12-open-data-integration.md) and has the shape of
[Open data sources of the Banská Bystrica region](banska-bystrica-open-data-sources.md). Every URL
below was fetched with `curl -L --max-time 25` on 2026-10-06 from the build sandbox. Its status
code is in the table beside it.

## 1. Who publishes what

| level | body | territory | what it publishes openly |
|---|---|---|---|
| `city` | Mesto Žilina, IČO 00321796 | the city, LAU `SK031B517402` | its own open data portal `opendata.zilina.sk` since 2026-05-04, ODbL (section 2.1); its GIS layers carry no licence (section 4) |
| `university` | Žilinská univerzita v Žiline (UNIZA), IČO 00397563 | its faculties | DREPO, its digital library, item by item under CC BY 4.0 |
| `national` | ŠÚ SR, EEA, MV SR, MK SR | the state, broken down to the municipality `SK031B517402` | statistics, air quality, the address register, the monument register |
| `operator` | ŽSR | the rail network, Žilina is one of its main nodes | the national train timetable as GTFS |

**Neither body publishes in the national catalogue** (the city's own portal of section 2.1 is not harvested into it). A SPARQL query of
`https://data.slovensko.sk/api/sparql` for `dct:publisher <https://data.gov.sk/id/legal-subject/{IČO}>`
returns 0 datasets for 00321796 (the city) and for 00397563 (UNIZA). The same query returns the
43 datasets of Banská Bystrica (00313271), so the query itself works. The Žilina publishers the
catalogue does hold are the regional road administration (Správa ciest ŽSK, 42054575, 151
datasets, section 4) and the regional public-health office (RÚVZ Žilina, 17335876, four files of
2016 and 2017 invoices and orders, left out as administrative records with no value for a
resident).

**The university keeps its own body.** UNIZA is a separate publisher with its own licence on
every item, but it holds one source. One project `zilina` holds it, and each Endpoint names its
own publisher in its catalogue block, so CKAN credits each dataset to the right body without a
second organization.

**Four spaces, not two.** A space holds one data model (DM-61), and the sources need four: the
ŠÚ SR rows (`zilina-mesto`, `KeyPerformanceIndicator`, T-4329), the city's public map data
(`zilina-verejne`: `AirQualityObserved`, `PointOfInterest`, `GtfsStop`), the university's works
(`zilina-uniza`, `Article`, the Smart Data Model extension of CPSV-AP Evidence, T-4338) and the indicators computed from the rows (`zilina-kpi`,
`KeyPerformanceIndicator`). This is Banská Bystrica's split (`-mesto`, `-verejne`, `-kpi`), and the
`zilina-` prefix keeps every space segment unique in the Organization's ids (PF-84).

## 2. What the project takes

Every row answered 200 and carries an open licence. `NGSI-LD type` is the type the feed lands as.

| dataset | publisher | space | URL | status | format | licence | update rate | size | NGSI-LD type | value |
|---|---|---|---|---|---|---|---|---|---|---|
| Počet obyvateľov podľa pohlavia, obce, štvrťročne (`om7101qr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/om7101qr/SK031B517402/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | quarterly, 1993Q1 to 2026Q2 | 1 185 values | `KeyPerformanceIndicator` | the city's population and its trend, the denominator of every per-capita KPI |
| Vekové skupiny, obce (`om7006rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/om7006rr/SK031B517402/*/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 6 274 values | `KeyPerformanceIndicator` | age structure, ageing index with `om7052rr` |
| Indexy vekového zloženia, obce (`om7052rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/om7052rr/SK031B517402/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 810 values | `KeyPerformanceIndicator` | the ageing index as published |
| Hustota obyvateľstva, obce (`om7014rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/om7014rr/SK031B517402/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 90 values | `KeyPerformanceIndicator` | density |
| Prírastok obyvateľov, obce (`om7105rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/om7105rr/SK031B517402/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1993 to 2025 | 495 values | `KeyPerformanceIndicator` | births, deaths and migration balance |
| Návštevnosť ubytovacích zariadení, obce (`cr3803mr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/cr3803mr/SK031B517402/*/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | monthly, 2017 to 2026 | 1 116 values | `KeyPerformanceIndicator` | visitors, domestic and foreign, per month |
| Návštevnosť, tržby a kapacity UZ, obce (`cr3809qr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/cr3809qr/SK031B517402/*/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | quarterly, 2017 to 2026 | 611 values | `KeyPerformanceIndicator` | beds, nights and revenue of accommodation |
| Materské, základné školy, gymnáziá, SOŠ (`sv5001rr`, `sv5002rr`, `sv5003rr`, `sv5004rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/sv5002rr/SK031B517402/*/*?lang=sk&type=json` (and the three others, same shape) | 200 each | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 348 / 518 / 515 / 783 values | `KeyPerformanceIndicator` | schools, classes, pupils and teachers per level |
| Knižnice (`ku5008rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/ku5008rr/SK031B517402/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 2015 to 2025 | 88 values | `KeyPerformanceIndicator` | libraries, loans, readers |
| Spotreba pitnej vody (`vh5003rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/vh5003rr/SK031B517402/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 60 values | `KeyPerformanceIndicator` | drinking water per inhabitant per day, as for Banská Bystrica |
| Evidovaní uchádzači o zamestnanie (`pr5001rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/pr5001rr/SK031B517402/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 60 values | `KeyPerformanceIndicator` | jobseekers in the city |
| Výmera územia, využitie pôdy (`pl5001rr`) | `national` ŠÚ SR | `mesto` | `https://data.statistics.sk/api/v2/dataset/pl5001rr/SK031B517402/*/*?lang=sk&type=json` | 200 | JSON-stat 2.0 | CC-BY-SA-4.0 | annual, 1996 to 2025 | 336 values | `KeyPerformanceIndicator` | land use: built-up, green, agricultural |
| Kvalita ovzdušia, stanica SK0020A (PM10, PM2.5, NO2, O3, CO, NOx, BaP) | `national` EEA (from SHMÚ) | `mesto` | `https://eeadmz1batchservice02.blob.core.windows.net/airquality-p/SK/SPO-SK0020A_00005_100.parquet` (PM10; `_06001_100` PM2.5, `_00008_500` NO2, `_00007_500` O3, `_00010_100` CO) | 200, `Last-Modified` 2026-10-06 18:51 to 19:00 UTC | Parquet, E2a up-to-date | CC-BY-4.0 (EEA) | hourly values, file refreshed daily | 270 to 335 kB per pollutant | `AirQualityObserved` | the city's one air-quality station, urban background, 2.6 km from the centre (EEA station metadata, `PanEuropean_metadata.csv`) |
| Adresy v obci Žilina | `national` MV SR (register of addresses) | `mesto` | `https://rageo.minv.sk/opendata/dataset/address_by_lau2_SK031B517402.geojson` | 200, `application/json` | GeoJSON | CC-BY-4.0 (`legislation:termsOfUse`) | daily, modified 2026-10-05 | 13 260 addresses, 10.4 MB | `Address` (LinkML, the address part of `PointOfInterest`) | locates everything that comes with an address, the monuments first |
| Ulice v obci Žilina | `national` MV SR | `mesto` | `https://rageo.minv.sk/opendata/dataset/street_by_lau2_SK031B517402.geojson` | 200 | GeoJSON | CC-BY-4.0 | daily, modified 2026-10-05 | 284 kB | none: a lookup | the street names a search offers; the file's geometry is a placeholder (`LINESTRING (30 10, 10 30, 40 40)`), so no street becomes an entity |
| Budovy v obci Žilina | `national` MV SR | `mesto` | `https://rageo.minv.sk/opendata/dataset/building_by_lau2_SK031B517402.geojson` | 200 | GeoJSON | CC-BY-4.0 | daily, modified 2026-10-05 | 6.2 MB | none: a lookup | building purpose and type per address; the features carry no geometry, so no building becomes an entity |
| Register nehnuteľných národných kultúrnych pamiatok, ŽSK | `national` MK SR (Pamiatkový úrad) | `mesto` | `https://data.slovensko.sk/download?id=dc413b1c-3c2e-454f-b986-d15e1c16093c` | 200, `text/csv` | CSV | CC-BY-4.0 | not declared; modified 2019-12-18 | 344 kB, 1 770 rows; 104 objects of 79 monuments in the city (the 281 of the first count were the district's) | `PointOfInterest` (category heritage) | the city's monuments, placed through the address register by cadastral area and súpisné číslo (83 of the 104 objects; a column or a statue has no address); ownership is only a category (church, state, private), no person is named |
| Grafikon vlakovej dopravy, GTFS | `operator` ŽSR | `mesto` | `https://data.slovensko.sk/download?id=a5503f2c-c7cc-4a9a-a713-511e7406800d` | 200, a ZIP served as `text/csv` | GTFS in a ZIP | CC-BY-1.0 on the catalogue's copy, CC0 by the publisher | with the timetable, modified 2026-10-05 | 291 kB | `GtfsStop` (Smart Data Models, UrbanMobility): the city's five stations and the trains leaving each that day; in this feed one route is one train number, so routes and trips stay in the file | the trains leaving Žilina, the node of four lines |
| DREPO, publikácie UNIZA | `university` UNIZA | `uniza` | `https://dspace.uniza.sk/server/api/discover/search/objects?dsoType=ITEM` (REST) and `https://dspace.uniza.sk/server/oai/request?verb=Identify` (OAI-PMH) | 200 and 200 | JSON (HAL), OAI-PMH XML | CC-BY-4.0 per item (`dc.rights.uri`); an item without an open `dc.rights.uri` is left out | continuous | 1 316 items, 787 with CC BY 4.0; 100 per page whatever `size` asks | `Article` (LinkML: title, type, year, deposit collection, publisher, licence, handle; **no author names**) | the university's open research by year, type and journal |

### 2.1 The city's open data portal (read 2026-10-22, T-5232)

`https://opendata.zilina.sk/sk/` is the city's own portal, run on Incinity's Invipo platform and live
since 2026-05-04. Its catalogue is HTML only (no CKAN API, no DCAT): 145 dataset pages on 15 list pages,
many of them the same data as JSON, CSV and XML. Every page was read once at one request a second;
`joinedcontext-deployment` `seeds/zilina-opendata/inventory.csv` records each page with its request,
parameters, response example, licence, whether it is live, and what the project did with it: 4 taken,
76 merged as a copy or an aggregate of a taken source, 65 skipped with the reason.

The API is `POST https://opendata.zilina.sk/api/datasets/{v1|v2}/...` with a JSON body, no key. A
POST without a body answers the whole list where the endpoint takes no parameter. Licence: ODbL on
104 pages, CC BY on 37, "povinné zverejňovanie" on 4; the terms (`/sk/page/detail/3`) ask the source be
named "Mesto Žilina" and give the data "as is". The project takes four live sources into the space
`zilina-doprava` (model `zilina-doprava`):

| dataset | portal page | API | update | NGSI-LD type | pipeline |
|---|---|---|---|---|---|
| Car parks with their current occupancy | 57 | `v1/city-dashboard/parking/list` | every 5 min | `OffStreetParking` | `parkovanie` |
| Public transport vehicles (DPMŽ), with delay | 124 | `v1/public-transport/vehicles/list` | every 5 min | `Vehicle` | `mhd-vozidla` |
| Vehicles per hour per traffic counter | 182 | `v1/core/geojson/items` (class `TrafficCounter`), then `v1/traffic-counters/vehicles/hourly` per counter | hourly | `TrafficFlowObserved` | `scitace` |
| Street lights | 102 | `v2/street-lights/items` | daily | `Streetlight` | `svietidla` |

What the portal answered on 2026-10-22: one car park (Antona Bernoláka, 62 spaces); 59 vehicles at
13:40 UTC with a deviation in minutes; 56 traffic counters, 52 active, 40 of them with a bucket for the
last full hour; 9 247 street lights (1.3 MB). `parking/items` answered 500 "Invalid Dataset". The 41
self-government pages point at `egov.zilina.sk`, which still times out from the build network (section
4); several of them name persons (dogs and their keepers, tax debtors), so a later read leaves those out.

## 3. What the feeds actually returned

- **ŠÚ SR.** Žilina is `SK031B517402` in every municipality cube (`/api/v2/dimension/om7101qr/om7101qr_obc`, `vh5003rr/nuts15` and `cr3803mr/cr3803mr_obecagr` all name it). Of the 678 cubes in `/api/v2/collection`, 26 break down to the municipality and were updated in 2025 or 2026. The table takes the sixteen a resident meets. `om7103mr` (monthly population movement) answered 400 to the all-periods request and needs its periods named. The pipeline asks for the last 24 months.
- **EEA.** `PanEuropean_metadata.csv` (26.9 MB) lists one Slovak station within 10 km of the centre (49.2231 N, 18.7394 E) with an open-ended observation period: `SK0020A`, `background`, `urban`, 2.6 km away. Its seven sampling points are PM10 (5), O3 (7), NO2 (8), NOx (9), CO (10), BaP (5029) and PM2.5 (6001). The download service's `ParquetFile/urls` call answered only its header line for `SK`, so the file URLs were built from the sampling-point names, as for Banská Bystrica, and each answered 200.
- **MV SR.** The register files are per LAU and carry `fulladdress`, street, numbers, postal code and the point. No field names an owner or a resident.
- **MK SR.** The CSV columns are district, municipality, cadastral area, the monument's names and number, address, numbers, parcels, century, style, author, protected area and ownership *form*. It has no coordinates.
- **DREPO.** Three sampled items carry `dc.rights.uri` `http://creativecommons.org/licenses/by/4.0/`, with type, year and publisher. The pipeline keeps the licence per item and drops the authors.

## 4. Candidates that were refused, and why

| name | publisher | URL | status | why it is out |
|---|---|---|---|---|
| The city's GIS layers on ArcGIS Online (about 100 public Feature Services: parking machines 45, AEDs 68, bike racks 198, Wi-Fi 41, waste bins 7 912, textile bins 151, cycle routes 82, events, terraces, trees 25 835, schools, sensors) | `city` Mesto Žilina, org `YbrKs9bCrNqe7yP4` | `https://services*.arcgis.com/YbrKs9bCrNqe7yP4/arcgis/rest/services/{name}/FeatureServer` | 200 | **no licence**: `licenseInfo` and `accessInformation` of every item are empty, every service's `copyrightText` is empty, and no city page states one. Public on ArcGIS is not an open licence (rules §1). Several layers also hold personal data or security detail (`podnety` citizen reports, `kamery_*` cameras, `zmluvy_*` contracts, `najomne_zmluvy` leases). This is the richest set and needs the city's licence: see section 5. |
| The city's open-data page | `city` Mesto Žilina | `https://egov.zilina.sk/default.aspx?NavigationState=1100:0:` (linked from `zilina.sk/…/transparentne-mesto/…open data`) | 000, connection timed out after 40 s, twice | the host does not answer from the build network, while `egov.banskabystrica.sk` on the same platform answers 200 from the same network. The zilina.sk page that links it holds no text. |
| Road weather and environmental stations of the Žilina region (100 weather, 50 environmental, the station list) | `region` Správa ciest ŽSK, 42054575 | `https://opendataapi.sczsk.sk/set/…/resource/…` | 000, TCP connect to port 443 timed out after 25 s | the API does not answer from the build network, though its NKOD record states CC-BY-4.0 / CC0 and no personal data. It answers nothing to a runner on the same network either. |
| ŽSR timetable on the publisher's site | `operator` ŽSR | `https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip` | 200 but `text/html` (219 kB page) | the file moved; the catalogue's copy (section 2) is the one taken |
| RÚVZ Žilina invoices and orders 2016–2017 | `region` RÚVZ Žilina | `http://www.ruvzza.sk/uradnew/fak2017_za.xml` and three more | not fetched | administrative records of 2016 and 2017, no value for a resident or a KPI |
| City transport (DPMŽ) timetable | `operator` DPMŽ | `https://www.dpmz.sk/` | 200, no GTFS or open-data link on the site | no published feed |

## 5. Decisions this survey leaves open

1. **The city's GIS layers (@user).** About 100 public layers, most of them what a resident looks
   for, and none licensed. Two ways: (a) ask the city of Žilina to state a licence, CC BY 4.0
   like Banská Bystrica's, on its ArcGIS organization or in NKOD, and take the layers once it does;
   (b) leave them out. Until then the `mesto` space holds the national feeds of section 2, which
   are enough for the KPI dashboard, the data grids and the map.
2. **The two hosts that do not answer (@integrator).** `egov.zilina.sk` and
   `opendataapi.sczsk.sk` time out from the build network. Fetch them once from the dev cluster.
   If they answer there, the region's road weather stations (CC-BY-4.0) become a real-time feed of
   the `zilina` project. If not, they stay in this table.

## 6. Provenance of every claim on this page

| claim | read from |
|---|---|
| the city portal's 145 datasets, their API and licence | each `https://opendata.zilina.sk/sk/dataset-list/detail/{id}` page and one POST per taken API, 2026-10-22 |
| no dataset of the city or UNIZA in NKOD | `https://data.slovensko.sk/api/sparql`, `dct:publisher` per IČO, 2026-10-06 |
| licences of MV SR, MK SR, ŽSR and Správa ciest ŽSK | the same endpoint, `legislation:termsOfUse` → `authorsWorkType` of each distribution |
| ŠÚ SR codes and periods | `/api/v2/collection`, `/api/v2/dimension/{cube}/{dim}`, the dataset fetches above |
| the air-quality station | EEA `PanEuropean_metadata.csv` and the HEAD of each Parquet file |
| the ArcGIS layers and their missing licence | `https://www.arcgis.com/sharing/rest/search?q=orgid:YbrKs9bCrNqe7yP4`, `…/content/items/{id}`, each `FeatureServer?f=json` and its `query?returnCountOnly=true` |
| DREPO | `/server/api/core/sites`, `/server/api/discover/search/objects`, `/server/oai/request?verb=Identify` |

## Related

- [Open data integration rules](../Development/12-open-data-integration.md) — the rules this inventory follows.
- [Open data sources of the Banská Bystrica region](banska-bystrica-open-data-sources.md) — the worked example.
- [Open data catalogue](../Architecture/21-open-data-catalogue.md) — how a project publishes into CKAN.
