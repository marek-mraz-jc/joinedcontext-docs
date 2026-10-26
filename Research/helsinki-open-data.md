---
sidebar_position: 14
title: "Open Data Sources: Helsinki (HRI)"
description: Every one of the 396 datasets that City of Helsinki units, HSL, Stara, Forum Virium Helsinki, Helen and Korkeasaari publish on hri.fi, read on 2026-10-22, with a decision (integrate, statistics or skip), the Smart Data Model it maps to, the outputs it gets and the batch task that builds it.
---

# Open data sources of Helsinki (HRI)

Which datasets of the Helsinki Region Infoshare catalogue (`hri.fi`) the `helsinki` project takes,
in which batch, as which Smart Data Model, and which it leaves out with the reason. It follows
[Open data integration rules](../Development/12-open-data-integration.md) and has the shape of
[Open data sources of Žilina](zilina-open-data-sources.md). The owner order of 2026-10-22 18:00Z
asks for every usable dataset, every format that makes sense, and models as close to Smart Data
Models as possible; task T-5252 built this page, tasks T-5253 to T-5259 and their splits T-5278 and T-5378 build the pipelines.

## 1. How the matrix was made

1. **Snapshot.** The supervisor's `package_search` snapshot of 2026-10-22 lists 396 datasets whose
   publisher is a City of Helsinki unit, HSL, Stara, Forum Virium Helsinki, Helen or Korkeasaari. It
   classed them by resource format only: 106 entity-like, 268 statistics, 22 imagery or 3D. A copy is
   in `Research/data/helsinki-hri-snapshot-2026-10-22.tsv`.
2. **Package read.** `package_show` of each of the 396 packages on 2026-10-22 gave the licence, the
   update frequency, the notes and the resource URLs. 394 packages are CC BY 4.0, one is CC0
   (`hri-verkkopalvelun-avoimen-datan-metatiedot`) and one says `other-open` (`helsinkikanava-open-data`).
   The attribution text "Source: <publisher>, Helsinki Region Infoshare, CC BY 4.0" goes into each
   catalogue entry.
3. **Probe.** One GET of each resource URL (at most six per package, 64 KiB read, 15 s timeout) from
   the build sandbox. The column `probe` holds the first 2xx/3xx answer, else `403`, `unreachable`
   or `no resource URL`. **`host timeout`** marks the 62 packages served only from `kartta.hel.fi`
   (the city WFS/WMS): that host accepted no TCP connection from the sandbox on 2026-10-22, while
   the dev cluster's seeds read it (T-0326, T-2787 fetched it with 200). Each batch task reruns the
   probe from the cluster before it builds a pipeline.
4. **Notes read.** A package note that says the service is withdrawn, not maintained or replaced
   (`HUOM`), or that its Excel copy ended in 2023, decides the row: 47 rows are skipped on such a
   note, marked "(package note)".
5. **Judgement.** Each entity-like and imagery row was read by hand; statistics rows follow one rule
   (section 2). The snapshot's format class put 11 rows in the wrong place; the `note` column says
   "moved from statistics" or "moved from entities" for those.

## 2. Decisions

- **integrate**: the dataset becomes NGSI-LD entities of one Smart Data Model (or a custom model
  that borrows the members of the named closest SDM class) through a pipeline of the named batch.
- **statistics**: a table of figures becomes `KeyPerformanceIndicator` series through the one PXWEB
  and table pipeline of T-5258, one indicator per table and dimension cut.
- **skip**: nothing is built; the reason is in the row and in section 7.

A statistics-class row is skipped when the package says its Excel copy ended in 2023 and the same
series is in Aluesarjat PXWEB (T-5258 reads that one), when it holds the raw answers of one survey,
or when it has no reachable resource. Imagery and 3D rows are skipped as rasters: a WMS or WMTS can
still serve as a basemap link in the catalogue.

| batch | domain | rows |
|---|---|---|
| T-5253 | parking and traffic | 12 |
| T-5254 | HSL network and maintenance | 7 |
| T-5255 | environment: street cleaning air pilot | 1 |
| T-5278 | heat vulnerability, property energy | 2 |
| T-5378 | environment layers of kartta.hel.fi, leftovers | 11 |
| T-5256 | buildings, addresses, land | 24 |
| T-5257 | services and culture | 2 |
| T-5258 | statistics as KeyPerformanceIndicator | 69 |
| T-5259 | already seeded, brought to SDM | 9 |
| - | skip | 259 |
| total | integrate 68, statistics 69, skip 259 | 396 |

## 3. Smart Data Models pinned

Every model name in the matrix is a directory of the subject repository at
`https://github.com/smart-data-models/dataModel.<subject>`, read at the commit below on 2026-10-22.
A custom model (`custom X; closest SDM Y`) exists only where no subject at these pins has a class
for the thing: land parcels, plan areas, streets, trees, fare zones and administrative areas.
`AdministrativeArea` and `Article` are the custom classes the helsinki seeds already define.

| subject | commit | classes used |
|---|---|---|
| `Alert` | `7e0d072ffd` | `Alert` |
| `Building` | `92aca4467c` | `Building` |
| `Consumption` | `754cbf3bea` | `ConsumptionPoint` |
| `Device` | `eb22fd87a9` | `DeviceMeasurement` |
| `Environment` | `2f048407cc` | `AirQualityObserved`, `FloodMonitoring`, `NoiseLevelObserved`, `NoisePollution`, `WaterObserved` |
| `IssueTracking` | `37cd76540e` | `IssueReporting` |
| `KeyPerformanceIndicator` | `ec7f3b642f` | `KeyPerformanceIndicator` |
| `Multimedia` | `621fad5ca2` | `MediaEvent` |
| `Parking` | `bac46424de` | `OnStreetParking` |
| `ParksAndGardens` | `88223ee898` | `FlowerBed`, `GreenspaceRecord` |
| `PointOfInterest` | `7e5e24963a` | `PointOfInterest` |
| `Streetlighting` | `e272fafc78` | `Streetlight` |
| `TourismDestinations` | `6d78cb4ff0` | `Event`, `TouristDestination` |
| `Transportation` | `b83ede9d3d` | `BikeHireDockingStation`, `BikeLane`, `CityWork`, `FareCollectionSystem`, `OriginDestinationFlow`, `RestrictedTrafficArea`, `Road`, `RoadAccident`, `RoadSegment`, `TrafficFlowObserved`, `TrafficViolation`, `Vehicle` |
| `UrbanMobility` | `81a052c84d` | `GtfsStation`, `GtfsStop`, `PublicTransportRoute` |
| `WasteWater` | `6abce4a129` | `WasteWaterJunction` |
| `WaterQuality` | `30ebc23186` | `WaterQualityObserved` |

The `UrbanPlanning` subject (`b59328809a`) holds no class yet, which is why plan areas are custom.

## 4. Outputs

The `outputs` column names the representations the batch configures on the dataset's Endpoint,
following the [representation contract](../API/11-representation-contract.md):

- `ngsi-ld`: the broker view, always.
- `temporal`: the NGSI-LD history, only where values change over time.
- `geojson` and `ogc-features`: where the entities carry a geometry.
- `csv`: points and tables a spreadsheet user wants.
- `ical`: events with a start time.
- `feed`: an Atom feed, only where items appear over time (events, alerts, permits); off by default.

## 5. Checks every batch runs

The owner order of 2026-10-22 18:10Z adds plausibility checks beside the SDM schema check. Each batch
task runs them on the real source data and writes the result into its own body:

- **Location**: every point or area inside the city's `AdministrativeArea` plus 1 km; no 0,0; no
  swapped latitude and longitude.
- **Values**: physical ranges per property (temperature -40 to 50 °C, percentages 0 to 100, counts
  at least 0, occupancy at most capacity, speeds 0 to 150 km/h) and the units the SDM names; dates no
  more than 1 day in the future and not older than the source claims.
- **Identity**: no two entities for one real object (same id, or same name within 20 m); every
  reference (`refDevice`, `refParkingSite`, area links) resolves to an existing entity.
- **Completeness**: the entity count matches the source record count (within 1 % for live feeds); a
  source that returns 0 records or data older than 3 update periods fails the run visibly and deletes
  nothing.
- **Human read**: 5 random entities per dataset compared with the source page or map, with the link.

Each pipeline fixture holds one out-of-area point, one out-of-range value and one duplicate, and the
pipeline drops or flags each with a counted reason.

## 6. The matrix

### 6.1 Usefulness score and the 100 target

The owner order of 2026-10-22 18:25Z asks the batches to build the useful rows first. Each integrate
and statistics row scores one point for each of:

- **live**: the package updates at least monthly (continuous, real time, hourly, daily, weekly, monthly,
  when changes);
- **city question**: it answers a citizen or city question: parking, traffic, transit, events, alerts,
  services, issue reports, air, noise or water sensors, or a statistic broken down by area or by
  service location;
- **joins**: it joins entities the space already holds or another row adds (stop ids, districts,
  service units, counters, buildings);

and loses one point when it is an invoice or grant ledger, a budget table or a plan index. A row
scoring 1 or more is **useful**; a batch builds its useful rows highest score first and leaves the
rest listed. A skip row has no score.

| batch | useful | not useful |
|---|---|---|
| T-5253 | 12 | 0 |
| T-5254 | 7 | 0 |
| T-5255 | 1 | 0 |
| T-5278 | 1 | 1 |
| T-5378 | 3 | 8 |
| T-5256 | 16 | 8 |
| T-5257 | 2 | 0 |
| T-5258 | 65 | 4 |
| T-5259 | 9 | 0 |

The owner order of 18:30Z sets a floor of 100 live Smart Data Models datasets per city (counted by
T-5275). Helsinki has 51 useful entity datasets and 65 useful statistics datasets (213 tables and series, section 6.3), so
the floor is reached from useful rows alone and no gap remains; the score-0 rows follow once the
useful ones are live (owner 18:40Z: 100 is a floor).

### 6.2 All rows

`dataset` links the HRI page. `source` is the resource formats HRI lists. `update` is the package's
own update frequency. `score` is the usefulness of section 6.1. Rows are ordered by batch, then by
name; a row keeps its number when a later batch changes its decision (T-5257 rows 66 to 80, 2026-10-23).

| # | dataset | title | class | decision | batch | model | outputs | source | update | licence | probe | note | score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [`datankeruukokeilu-helsingissa-liikennelaskenta-konenaon-avulla`](https://hri.fi/data/en_GB/dataset/datankeruukokeilu-helsingissa-liikennelaskenta-konenaon-avulla) | Data gatherin pilot in Helsinki: Traffic counting using machine vision | entities | integrate | T-5253 | `TrafficFlowObserved` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | JSON | not stated | CC-BY-4.0 | 200 | pilot camera counts; one import, the camera as `Device` | 1 |
| 2 | [`helsingin-kantakaupungin-ja-asukaspysakointivyohykkeiden-pysakointipaikat`](https://hri.fi/data/en_GB/dataset/helsingin-kantakaupungin-ja-asukaspysakointivyohykkeiden-pysakointipaikat) | Parking places in Helsinki | entities | integrate | T-5286 | `OnStreetParking` (Parking) | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | 200 | built by T-5286: 7873 places (the 881 no-parking areas left out), the parking class and place type as SDM categories, `paikat_ala` as totalSpotNumber, an estimate from the digitised area (package note) | 1 |
| 3 | [`helsingin-liikenne-ja-varoitusvaloliittymat`](https://hri.fi/data/en_GB/dataset/helsingin-liikenne-ja-varoitusvaloliittymat) | Intersections with traffic lights in Helsinki | entities | integrate | T-5286 | custom `TrafficSignalJunction`; closest SDM `Streetlight` | ngsi-ld, geojson, ogc-features, csv | WFS | not stated | CC-BY-4.0 | 200 | built by T-5286 as the extension `TrafficSignalJunction` (PointOfInterest base): 553 junctions with traffic lights and 12 crossings with warning lights, `Rakenteilla` as status underConstruction; no SDM traffic-signal class at the pin | 1 |
| 4 | [`helsingin-liikennemittausten-tilastorajapinta`](https://hri.fi/data/en_GB/dataset/helsingin-liikennemittausten-tilastorajapinta) | Statistical API for traffic measurement data of the city of Helsinki | entities | integrate | T-5253 | `TrafficFlowObserved` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | CSV/JSON | continuous | CC-BY-4.0 | 200 | counting stations as `Device`; daily aggregates | 2 |
| 5 | [`helsingin-liikennevaylat`](https://hri.fi/data/en_GB/dataset/helsingin-liikennevaylat) | City of Helsinki road map | entities | integrate | T-5286 | `RoadSegment` (Transportation) | ngsi-ld, geojson, ogc-features | WFS | continuous | CC-BY-4.0 | 200 | street network lines; T-5254 and T-5256 reference these segments; 111404 segments on 2026-10-26, more than one pipeline run holds (~10 KB per entity): left to batch B3, paged by area | 2 |
| 6 | [`helsingin-matkailuliikenteen-pysakit-ja-pysakointipaikat`](https://hri.fi/data/en_GB/dataset/helsingin-matkailuliikenteen-pysakit-ja-pysakointipaikat) | Tourist traffic stops and parking places in Helsinki | entities | integrate | T-5286 | `OnStreetParking` (Parking) | ngsi-ld, geojson, ogc-features, csv | WFS/WMS | not stated | CC-BY-4.0 | 200 | built by T-5286: 28 stops and 11 parking places, allowedVehicleType bus, shortTerm where the layer gives a time limit | 1 |
| 7 | [`helsingin-pyorailijamaarat`](https://hri.fi/data/en_GB/dataset/helsingin-pyorailijamaarat) | Number of cyclists in Helsinki | entities | integrate | T-5253 | `TrafficFlowObserved` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | CSV/WFS/XLSX | half years | CC-BY-4.0 | 200 | vehicleType bicycle; counter as `Device` | 1 |
| 8 | [`helsingin-pyoravaylat-2025`](https://hri.fi/data/en_GB/dataset/helsingin-pyoravaylat-2025) | Helsinki bicycle lanes 2025 | entities | integrate | T-5253 | `BikeLane` (Transportation) | ngsi-ld, geojson, ogc-features | SHP | ended | CC-BY-4.0 | 200 | SHP only; converted to WGS84 in the pipeline | 1 |
| 9 | [`helsingin-seudun-pyoralaskennat`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-pyoralaskennat) | Number of cyclists in Helsinki Region | entities | integrate | T-5253 | `TrafficFlowObserved` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | CSV/GEOJSON/GEOSERVICE/KML/SHP | not stated | CC-BY-4.0 | 200 | HSL counters; a counter within 20 m of a city counter is the same `Device` | 2 |
| 10 | [`liikennemaarat-helsingissa`](https://hri.fi/data/en_GB/dataset/liikennemaarat-helsingissa) | Traffic data from Helsinki | entities | integrate | T-5253 | `TrafficFlowObserved` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | CSV/JSON/WFS/WMS | yearly | CC-BY-4.0 | 200 | yearly volumes per point; joins the measurement API stations within 20 m | 2 |
| 11 | [`liikenneonnettomuudet-helsingissa`](https://hri.fi/data/en_GB/dataset/liikenneonnettomuudet-helsingissa) | Traffic Accidents in Helsinki | statistics | integrate | T-5286 | `RoadAccident` (Transportation) | ngsi-ld, geojson, ogc-features, csv | CSV | yearly | CC-BY-4.0 | 200 | moved here from the statistics class: one row per accident with coordinates; its coordinates are ETRS-GK25 (EPSG:3879), which a Bloblang mapping cannot project (no atan): left to batch B3 with a projection step | 1 |
| 12 | [`pysakointivirheet-helsingissa`](https://hri.fi/data/en_GB/dataset/pysakointivirheet-helsingissa) | Parking violations in Helsinki | entities | integrate | T-5253 | `TrafficViolation` (Transportation) | ngsi-ld, temporal, csv, geojson | CSV/SHP/WFS | half a year | CC-BY-4.0 | 200 | aggregated per street and month, no plate or person data | 1 |
| 13 | [`helsingin-ja-espoon-kaupunkipyorilla-ajatut-matkat`](https://hri.fi/data/en_GB/dataset/helsingin-ja-espoon-kaupunkipyorilla-ajatut-matkat) | City bike stations’ Origin-Destination (OD) data | statistics | integrate | T-5254 | `OriginDestinationFlow` (Transportation) | ngsi-ld, temporal, csv | CSV | yearly | CC-BY-4.0 | 403 | deferred (T-5254): the resource answered 403, and the space has no `OriginDestinationFlow` class; monthly CSVs of all trips need an aggregation design first | 1 |
| 14 | [`helsingin-jalankulun-ja-pyorailyn-talvihoidon-priorisoitu-reitisto`](https://hri.fi/data/en_GB/dataset/helsingin-jalankulun-ja-pyorailyn-talvihoidon-priorisoitu-reitisto) | The prioritised winter maintenance network for pedestrians and cyclists in the City of Helsinki | entities | integrate | T-5254 | `RoadSegment` (Transportation) | ngsi-ld, geojson, ogc-features | CSV/WFS/WMS | yearly | CC-BY-4.0 | host timeout | deferred (T-5254): kartta.hel.fi WFS timed out 4 times from the build host (TCP connect), so no real fixture; needs `RoadSegment` vendored | 1 |
| 15 | [`hsl-n-joukkoliikenteen-pysakit`](https://hri.fi/data/en_GB/dataset/hsl-n-joukkoliikenteen-pysakit) | Helsinki Region Transport public transport stations | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | duplicate: the transit-stops GTFS seed already writes every HSL stop (GtfsStop by stop_id) | - |
| 16 | [`hsl-n-joukkoliikenteen-risteyssolmut`](https://hri.fi/data/en_GB/dataset/hsl-n-joukkoliikenteen-risteyssolmut) | Helsinki Region Transport public transport knots | entities | skip | - | - | - | CSV/GEOJSON/GEOSERVICE/KML/SHP | half years | CC-BY-4.0 | 200 | HSL's planning network graph (16 724 nodes), nothing a passenger sees | - |
| 17 | [`hsl-n-linjat`](https://hri.fi/data/en_GB/dataset/hsl-n-linjat) | Helsinki Region Transport public transport lines | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | duplicate: the transit-routes and gtfs-shapes GTFS seeds already write the lines and their geometry | - |
| 18 | [`hsl-n-myyntipisteet`](https://hri.fi/data/en_GB/dataset/hsl-n-myyntipisteet) | Helsinki Region Transport sales points | entities | integrate | T-5254 | `PointOfInterest` (PointOfInterest) | ngsi-ld, geojson, ogc-features, csv | CSV/GEOJSON/GEOPACKAGE/KML/SHP/XLSX | not stated | CC-BY-4.0 | 200 | built (T-5254): sales-points pipeline, serviceCategory ticketSalesPoint/ServicePoint/Machine/ParkingMeter, in CKAN helsinki-places | 1 |
| 19 | [`hsl-n-nousijamaarat-pysakeittain`](https://hri.fi/data/en_GB/dataset/hsl-n-nousijamaarat-pysakeittain) | Helsinki Region Transport passengers by station | entities | integrate | T-5254 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | CSV/GEOJSON/GEOSERVICE/KML/SHP | ended | CC-BY-4.0 | 200 | built (T-5254): stop-boardings pipeline, Nov 2016 weekday average per stop; no CKAN entry yet: the helsinki-kpi Endpoint is harvest: false until its licence decision (T-2793) | 2 |
| 20 | [`hsl-n-pysakit-linjoittain`](https://hri.fi/data/en_GB/dataset/hsl-n-pysakit-linjoittain) | Helsinki Region Transport stations by line | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | duplicate: the stop sequence per line is GTFS stop_times, which transit-routes and transit-stops already read | - |
| 21 | [`hsl-n-taksavyohykkeet`](https://hri.fi/data/en_GB/dataset/hsl-n-taksavyohykkeet) | Helsinki Region Transport tariff zones | entities | integrate | T-5254 | `AdministrativeArea` (Administration), divisionLevel fareZone | ngsi-ld, geojson, ogc-features | CSV/GEOJSON/GEOSERVICE/KML/SHP | not stated | CC-BY-4.0 | 200 | built (T-5254): fare-zones pipeline, zones A-D, in CKAN helsinki-districts | 1 |
| 22 | [`hsl-n-terminaalit`](https://hri.fi/data/en_GB/dataset/hsl-n-terminaalit) | Helsinki Region Transport terminals | entities | skip | - | - | - | CSV/GEOJSON/GEOSERVICE/KML/SHP | not stated | CC-BY-4.0 | 200 | duplicate: TERMINAALI is the GTFS stop_id of a GtfsStation that transit-stops writes (Kamppi 1000001) | - |
| 23 | [`hsl-n-vuoromaarat`](https://hri.fi/data/en_GB/dataset/hsl-n-vuoromaarat) | Helsinki Region Transport shift frequencies | entities | skip | - | - | - | CSV/GEOJSON/GEOSERVICE/KML/SHP | half years | CC-BY-4.0 | 200 | HSL's planning network graph (8 067 links with departure counts), nothing a passenger sees | - |
| 24 | [`matkustaja-alusten-aikataulu-liikennointi-ja-sijaintitietoja-helsingin-ja-tallinnan-valilla`](https://hri.fi/data/en_GB/dataset/matkustaja-alusten-aikataulu-liikennointi-ja-sijaintitietoja-helsingin-ja-tallinnan-valilla) | Schedule and position data on passenger ferries trafficking between Helsinki and Tallinn | statistics | integrate | T-5254 | `Vehicle` (Transportation) | ngsi-ld, temporal, geojson | CSV | not stated | CC-BY-4.0 | 200 | deferred (T-5254): a closed 2018-2019 archive with no current position; one history import, not a live dataset | 1 |
| 25 | [`vantaan-kaupunkipyoraasemat`](https://hri.fi/data/en_GB/dataset/vantaan-kaupunkipyoraasemat) | City bicycle stations of Vantaa | entities | integrate | T-5254 | `BikeHireDockingStation` (Transportation) | ngsi-ld, geojson, ogc-features, csv | CSV/GEOJSON/GEOSERVICE/KML/SHP | yearly | CC-BY-4.0 | 200 | built (T-5254): vantaa-bikes pipeline, no live bike count in the source, in CKAN helsinki-bikes | 2 |
| 26 | [`datankeruukokeilu-helsingissa-ilmanlaatu-katujen-siivouksen-aikana`](https://hri.fi/data/en_GB/dataset/datankeruukokeilu-helsingissa-ilmanlaatu-katujen-siivouksen-aikana) | Data collection pilot in Helsinki: Air quality during street cleaning | entities | integrate | T-5255 | `AirQualityObserved` (Environment) | ngsi-ld, temporal, geojson, ogc-features, csv | JSON | ended | CC-BY-4.0 | 200 | pilot series, one import | 1 |
| 27 | [`helsingin-avouomat`](https://hri.fi/data/en_GB/dataset/helsingin-avouomat) | City of Helsinki riverbeds, streams and ditches | entities | integrate | T-5378 | custom `Watercourse`; closest SDM `WaterObserved` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | streams and ditches as lines | 0 |
| 28 | [`helsingin-ilmanlaadun-mittaukset-raitiovaunuihin-asennetuilla-mittalaitteilla`](https://hri.fi/data/en_GB/dataset/helsingin-ilmanlaadun-mittaukset-raitiovaunuihin-asennetuilla-mittalaitteilla) | Air quality measurements which are collected using devices installed on trams from Helsinki | statistics | integrate | T-5378 | `AirQualityObserved` (Environment) | ngsi-ld, temporal, geojson, csv | CSV | ended | CC-BY-4.0 | 200 | moved from statistics: summer 2019 tram-mounted sensors; deferred to T-5378: seven monthly gzip files of up to 27 MB (sporametri-movingsites-data0419.csv.gz), past what one Bento run holds in memory, so the import needs its own slicing | 1 |
| 29 | [`helsingin-kaukolammon-tuotantotarve`](https://hri.fi/data/en_GB/dataset/helsingin-kaukolammon-tuotantotarve) | District heat production in Helsinki | statistics | integrate | T-5378 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | CSV | yearly | 200 (helen_2015_2024_v2.csv, 2.2 MB) | 200 | moved from statistics: hourly district heat demand (Helen); deferred to T-5378: the file ends on 2025-01-23 (88,217 hourly rows from 2015), a one-off history import with its own KPI period, not a weekly read | 0 |
| 30 | [`helsingin-kaupungin-meluselvitys-2017`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017) | Traffic noise zones in Helsinki | entities | integrate | T-5378 | `NoisePollution` (Environment) | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | modelled noise zones (Lden bands) | 0 |
| 31 | [`helsingin-kaupungin-palvelukiinteistojen-energiankulutustietoja`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-palvelukiinteistojen-energiankulutustietoja) | Energy consumption data of city of Helsinki’s utility and service properties | entities | integrate | T-5278 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON | monthly | CC-BY-4.0 | 200 | built: Nuuka API Monthly/ListByProperty, one indicator per location and utility (electricity, heat kWh; water m3), the last complete month, history keeps every month; 1,050 indicators on 2026-10-22 | 2 |
| 32 | [`helsingin-kaupungin-puurekisteri`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-puurekisteri) | Urban tree database of the City of Helsinki | entities | integrate | T-5378 | custom `Tree`; closest SDM `FlowerBed` | ngsi-ld, geojson, ogc-features, csv | WFS/WMS | daily | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | one entity per tree; ParksAndGardens has no tree class at the pin | 1 |
| 33 | [`helsingin-lampohaavoittuvuusindeksi`](https://hri.fi/data/en_GB/dataset/helsingin-lampohaavoittuvuusindeksi) | Urban Heat Vulnerability Index of Helsinki | entities | integrate | T-5278 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, csv | CSV/GEOJSON/GEOTIFF/GPKG/SHP | not stated | CC-BY-4.0 | 200 | built: 6 indicators (Avg-UHVI, Avg-UHII, Avg-UHEI, Avg-UHAI, UHSI, HVP) per sub-district, 145 x 6 = 870, each linked to its AdministrativeArea | 0 |
| 34 | [`helsingin-luontotietojarjestelma`](https://hri.fi/data/en_GB/dataset/helsingin-luontotietojarjestelma) | Helsinki's nature information system | entities | integrate | T-5378 | `GreenspaceRecord` (ParksAndGardens) | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | nature sites and habitats | 0 |
| 35 | [`helsingin-maa-ja-vesialueet`](https://hri.fi/data/en_GB/dataset/helsingin-maa-ja-vesialueet) | Land and water areas of Helsinki | entities | integrate | T-5378 | custom `LandCoverArea`; closest SDM `GreenspaceRecord` | ngsi-ld, geojson, ogc-features | WFS/WMS | continuous | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | heavy geometry (package note): page the WFS | 1 |
| 36 | [`helsingin-tavoitteellinen-viher-ja-virkistysverkostokartta`](https://hri.fi/data/en_GB/dataset/helsingin-tavoitteellinen-viher-ja-virkistysverkostokartta) | Helsinki Open Space Plan (VISTRA) | entities | integrate | T-5378 | `GreenspaceRecord` (ParksAndGardens) | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | VISTRA open space plan | 0 |
| 37 | [`helsingin-teollisuusmeluvyohykkeet`](https://hri.fi/data/en_GB/dataset/helsingin-teollisuusmeluvyohykkeet) | Industry noise zones in Helsinki | entities | integrate | T-5378 | `NoisePollution` (Environment) | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | industry noise zones | 0 |
| 38 | [`helsingin-ulkoliikuntapaikkojen-laitteiden-kayttoasteet`](https://hri.fi/data/en_GB/dataset/helsingin-ulkoliikuntapaikkojen-laitteiden-kayttoasteet) | Utilization rates of outdoor gyms in Helsinki | entities | skip | - | - | - | JSON | ended | CC-BY-4.0 | 200 | source stopped 2025-03-10 | - |
| 39 | [`iot-meludataa-helsingista`](https://hri.fi/data/en_GB/dataset/iot-meludataa-helsingista) | Noise sensor data from Helsinki | statistics | skip | - | - | - | CSV | daily | CC-BY-4.0 | 404 | project end-of-life: the static files moved away | - |
| 40 | [`purkupisteet-ja-osavaluma-alueet`](https://hri.fi/data/en_GB/dataset/purkupisteet-ja-osavaluma-alueet) | Purkupisteet ja osavaluma-alueet | entities | integrate | T-5378 | custom `StormwaterCatchment`; closest SDM `WasteWaterJunction` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | discharge points and sub-catchments | 0 |
| 41 | [`turvalliset-rakentamiskorkeudet-ja-suurin-arvioitu-merkitseva-aallonkorkeus-helsingissa`](https://hri.fi/data/en_GB/dataset/turvalliset-rakentamiskorkeudet-ja-suurin-arvioitu-merkitseva-aallonkorkeus-helsingissa) | Safe heights for buildings and highest significant wave heights in Helsinki | entities | integrate | T-5378 | custom `FloodRiskArea`; closest SDM `FloodMonitoring` | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout, re-checked 2026-10-23 | safe building heights and wave heights | 0 |
| 42 | [`asemakaavoilla-suojellut-rakennukset-ja-alueet-helsingissa`](https://hri.fi/data/en_GB/dataset/asemakaavoilla-suojellut-rakennukset-ja-alueet-helsingissa) | Buildings and areas protected by detailed plans of the City of Helsinki | entities | integrate | T-5256 | `Building` (Building) | ngsi-ld, geojson, ogc-features | /WFS | yearly | CC-BY-4.0 | host timeout | protection class merged into the `Building` by building id; protected areas as LandUsePlanArea | 1 |
| 43 | [`helsingin-asemakaavahakemistokartta-asemakaavahakemisto`](https://hri.fi/data/en_GB/dataset/helsingin-asemakaavahakemistokartta-asemakaavahakemisto) | Detailed plans index map of Helsinki | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS/WMS | continuous | CC-BY-4.0 | host timeout | plan index | 0 |
| 44 | [`helsingin-kaavayksikot`](https://hri.fi/data/en_GB/dataset/helsingin-kaavayksikot) | Plan units of the city of Helsinki | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout | UrbanPlanning subject is empty at the pin | 0 |
| 45 | [`helsingin-kaupungin-peruskoulujen-oppilaaksiottoaluerajat`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-peruskoulujen-oppilaaksiottoaluerajat) | School and preschool admission areas of the City of Helsinki | entities | integrate | T-5256 | custom `AdministrativeArea` (helsinki seed model); closest SDM none | ngsi-ld, geojson, ogc-features | WFS/WMS | yearly | CC-BY-4.0 | host timeout | areaType school admission area | 1 |
| 46 | [`helsingin-kaupungin-yleisten-alueiden-rekisteri`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-yleisten-alueiden-rekisteri) | Register of public areas in the City of Helsinki | entities | integrate | T-5256 | `GreenspaceRecord` (ParksAndGardens) | ngsi-ld, geojson, ogc-features | WFS/WMS | daily | CC-BY-4.0 | host timeout | public areas register: parks, streets, squares | 1 |
| 47 | [`helsingin-kaupungin-yleisten-alueiden-tapahtuma-ja-maankayttolupajarjestelma`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-yleisten-alueiden-tapahtuma-ja-maankayttolupajarjestelma) | Land usage permission system for public areas in the City of Helsinki | entities | integrate | T-5256 | `CityWork` (Transportation) | ngsi-ld, geojson, ogc-features, feed | WFS/WMS | daily | CC-BY-4.0 | host timeout | the layers the area-events, excavation and traffic-arrangements seeds do not read yet (T-5259 keeps those three) | 1 |
| 48 | [`helsingin-kaupunkitilaohjealueet`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunkitilaohjealueet) | Design Manual of Helsinki | entities | integrate | T-5256 | custom `MaintenanceArea`; closest SDM `GreenspaceRecord` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | design manual area class | 0 |
| 49 | [`helsingin-kiinteistot-alueina`](https://hri.fi/data/en_GB/dataset/helsingin-kiinteistot-alueina) | Real Estates in the City of Helsinki | entities | integrate | T-5256 | custom `LandParcel`; closest SDM `PointOfInterest` | ngsi-ld, geojson, ogc-features | PNG/WFS/WMS | not stated | CC-BY-4.0 | host timeout | real estates | 1 |
| 50 | [`helsingin-korttelit`](https://hri.fi/data/en_GB/dataset/helsingin-korttelit) | Quarters of Helsinki | entities | integrate | T-5256 | custom `AdministrativeArea` (helsinki seed model); closest SDM none | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout | areaType block | 1 |
| 51 | [`helsingin-maaraalat-alueina`](https://hri.fi/data/en_GB/dataset/helsingin-maaraalat-alueina) | Unseparated parcels in the City of Helsinki | entities | integrate | T-5256 | custom `LandParcel`; closest SDM `PointOfInterest` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | unseparated parcels, parcelStatus unseparated | 1 |
| 52 | [`helsingin-nimisto`](https://hri.fi/data/en_GB/dataset/helsingin-nimisto) | Street Names of the City of Helsinki | entities | integrate | T-5256 | custom `Street`; closest SDM `Road` | ngsi-ld, geojson, ogc-features | WFS | daily | CC-BY-4.0 | host timeout | street and place names in fi/sv | 1 |
| 53 | [`helsingin-osayleiskaavahakemisto`](https://hri.fi/data/en_GB/dataset/helsingin-osayleiskaavahakemisto) | City of Helsinki Component Master plans Index | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | component master plan index | -1 |
| 54 | [`helsingin-osayleiskaavat`](https://hri.fi/data/en_GB/dataset/helsingin-osayleiskaavat) | City of Helsinki component master plans | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | component master plans | 0 |
| 55 | [`helsingin-osoiteluettelo`](https://hri.fi/data/en_GB/dataset/helsingin-osoiteluettelo) | Database of addresses of Helsinki | entities | integrate | T-5256 | custom `Address`; closest SDM `PointOfInterest` | ngsi-ld, geojson, ogc-features, csv | WFS/WMS | continuous | CC-BY-4.0 | host timeout | SDM keeps address as a property only; large layer | 2 |
| 56 | [`helsingin-paakatuverkon-paallysteiden-kuntomittaukset`](https://hri.fi/data/en_GB/dataset/helsingin-paakatuverkon-paallysteiden-kuntomittaukset) | Measurements of the pavement condition of the main street network in Helsinki | entities | integrate | T-5256 | `RoadSegment` (Transportation) | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout | pavement condition per segment of the main street network | 0 |
| 57 | [`helsingin-rakennukset`](https://hri.fi/data/en_GB/dataset/helsingin-rakennukset) | Buildings in Helsinki | entities | integrate | T-5256 | `Building` (Building) | ngsi-ld, geojson, ogc-features | PNG/TAB/WFS/WMS | daily | CC-BY-4.0 | host timeout | large layer: page the WFS, record the count and storage | 1 |
| 58 | [`helsingin-rakennuskiellot-alueina`](https://hri.fi/data/en_GB/dataset/helsingin-rakennuskiellot-alueina) | Building prohibitions map of the City of Helsinki | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | building prohibitions | 0 |
| 59 | [`helsingin-vapaat-yritystontit`](https://hri.fi/data/en_GB/dataset/helsingin-vapaat-yritystontit) | Available Plots for Business of the City of Helsinki | entities | integrate | T-5256 | custom `LandParcel`; closest SDM `PointOfInterest` | ngsi-ld, geojson, ogc-features | WFS/WMS | continuous | CC-BY-4.0 | host timeout | available business plots | 2 |
| 60 | [`helsingin-yleiskaava-2016`](https://hri.fi/data/en_GB/dataset/helsingin-yleiskaava-2016) | City of Helsinki Master Plan 2016 | entities | integrate | T-5256 | custom `LandUsePlanArea`; closest SDM `RestrictedTrafficArea` | ngsi-ld, geojson, ogc-features | WFS/WMS | not stated | CC-BY-4.0 | host timeout | master plan 2016 | 0 |
| 61 | [`helsingin-yleisten-alueiden-arvoymparistot`](https://hri.fi/data/en_GB/dataset/helsingin-yleisten-alueiden-arvoymparistot) | Valuable Environments in the Public Areas of the City of Helsinki | entities | integrate | T-5256 | `GreenspaceRecord` (ParksAndGardens) | ngsi-ld, geojson, ogc-features | WFS | daily | CC-BY-4.0 | host timeout | valuable environments | 1 |
| 62 | [`helsingin-yleisten-alueiden-kunnossapidon-vastuualueet`](https://hri.fi/data/en_GB/dataset/helsingin-yleisten-alueiden-kunnossapidon-vastuualueet) | Maintenance of Public Areas in Helsinki | entities | integrate | T-5256 | custom `MaintenanceArea`; closest SDM `GreenspaceRecord` | ngsi-ld, geojson, ogc-features | WFS/WMS | daily | CC-BY-4.0 | host timeout | maintainer per public area | 1 |
| 63 | [`helsingin-ymparistolupakohteet`](https://hri.fi/data/en_GB/dataset/helsingin-ymparistolupakohteet) | Environmental permits in Helsinki | entities | integrate | T-5256 | custom `EnvironmentalPermit`; closest SDM `PointOfInterest` | ngsi-ld, geojson, ogc-features, csv | WFS | yearly | CC-BY-4.0 | host timeout | permit sites | 1 |
| 64 | [`helsinkilaisten-rakennusten-historiatietoja`](https://hri.fi/data/en_GB/dataset/helsinkilaisten-rakennusten-historiatietoja) | History of buildings in Helsinki | statistics | integrate | T-5256 | `Building` (Building) | ngsi-ld, csv | XLSX | not stated | CC-BY-4.0 | 200 | moved from statistics: history attributes merged into the `Building` | 1 |
| 65 | [`paakaupunkiseudun-aanestysaluejako`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-aanestysaluejako) | Electoral districts in the Helsinki metropolitan area | entities | integrate | T-5256 | custom `AdministrativeArea` (helsinki seed model); closest SDM none | ngsi-ld, geojson, ogc-features | SHP/TAB/WFS/WMS | when changes | CC-BY-4.0 | host timeout | areaType electoral district | 2 |
| 66 | [`helsingin-ensimmaisen-maailmansodan-aikaiset-maalinnoitukset`](https://hri.fi/data/en_GB/dataset/helsingin-ensimmaisen-maailmansodan-aikaiset-maalinnoitukset) | Fortifications of First World War in Helsinki | entities | skip | - | - | - | WFS/WMS | not stated | CC-BY-4.0 | host timeout | WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host) | - |
| 67 | [`helsingin-kaupungin-palauterajapinta`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-palauterajapinta) | The Issue Reporting API of the City of Helsinki | entities | integrate | T-5257 | `IssueReporting` (IssueTracking) | ngsi-ld, temporal, geojson, feed | JSON/XML | continuous | CC-BY-4.0 | 200 | Open311 requests, public fields only | 2 |
| 68 | [`helsingin-kaupungin-palvelurekisterin-rest-rajapinta`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-palvelurekisterin-rest-rajapinta) | Helsinki Metropolitan Area service register REST API | entities | skip | - | - | - | JSON/XML | continuous | CC-BY-4.0 | 200 | same units as the Service Map API (tprek ids) that T-5257 integrates; one source per object, no duplicate PointOfInterest | - |
| 69 | [`helsingin-kaupungin-verkkosivustojen-kavijaanalytiikka`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-verkkosivustojen-kavijaanalytiikka) | Visitor analytics in city of Helsinki websites | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON | daily | CC-BY-4.0 | 200 | built: pipeline service-usage, visits and page views per site and month from the Matomo export (theme services) | 1 |
| 70 | [`helsingin-kaupunginorkesterin-konsertit`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginorkesterin-konsertit) | Concerts of Helsinki Philharmonic Orchestra 1882- | statistics | skip | - | - | - | XLSX | half years | CC-BY-4.0 | 200 | archive of past concerts, one row per work performed (61,267 rows, 1882 to 28.05.2026, checked 2026-10-23); no upcoming concert, so no live Event; archives score down (owner 18:25Z) | - |
| 71 | [`helsingin-kulttuurihistoriallisesti-merkittavat-porrashuoneet`](https://hri.fi/data/en_GB/dataset/helsingin-kulttuurihistoriallisesti-merkittavat-porrashuoneet) | Historically meaningful staircases in Helsinki | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | one-off 2014 inventory (zip of one XLSX, 349 staircases, checked 2026-10-23) of stairwells inside residential buildings, by property id and street address only, no coordinates and no update since | - |
| 72 | [`helsingin-taidemuseon-nayttelyt`](https://hri.fi/data/en_GB/dataset/helsingin-taidemuseon-nayttelyt) | The Helsinki Art Museum’s exhibitions | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | archive of past HAM exhibitions (1,139 rows, newest start 2022-09-09, checked 2026-10-23) in one XLSX; no upcoming exhibition, so no live Event; archives score down (owner 18:25Z) | - |
| 73 | [`helsingin-taidemuseon-prosenttirahahankkeet`](https://hri.fi/data/en_GB/dataset/helsingin-taidemuseon-prosenttirahahankkeet) | The Helsinki Art Museum’s acquisition appropriation projects | statistics | skip | - | - | - | XLS | yearly | CC-BY-4.0 | 200 | only resource is an Excel 97 .xls (BIFF8, saved 2025-09-16, checked 2026-10-23) listing works by artist and title with a building address and no coordinates; no seed pipeline reads Excel, and placing a work needs per-work geocoding the file does not support | - |
| 74 | [`helsingin_maisemakulttuurikartta`](https://hri.fi/data/en_GB/dataset/helsingin_maisemakulttuurikartta) | Helsinki landscape culture | entities | skip | - | - | - | WFS/WMS | no regular updates | CC-BY-4.0 | host timeout | WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host) | - |
| 75 | [`jalankulkijoiden-liukastumisvaroitukset-helsingissa`](https://hri.fi/data/en_GB/dataset/jalankulkijoiden-liukastumisvaroitukset-helsingissa) | Pedestrian slip warnings in Helsinki | entities | skip | - | - | - | JSON | real time | CC-BY-4.0 | 200 | liukasbotti.fi/api/warnings holds 3 rows in total, the newest real one 28.02.2026, two of them test rows, no geometry and only 'Helsinki' as area: nothing an Alert could locate | - |
| 76 | [`korkeasaaren-kavijamaarat`](https://hri.fi/data/en_GB/dataset/korkeasaaren-kavijamaarat) | Helsinki Zoo visitor count | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON/XLSX | daily | CC-BY-4.0 | 200 | built: pipeline service-usage, visitors per ended day and month (theme services) | 1 |
| 77 | [`paakaupunkiseudun-palvelukartan-rest-rajapinta`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-palvelukartan-rest-rajapinta) | Helsinki metropolitan area Service Map APIs | entities | integrate | T-5257 | `PointOfInterest` (PointOfInterest) | ngsi-ld, geojson, ogc-features, csv | JSON/WFS | continuous | CC-BY-4.0 | 200 | extends the services seed to every unit, no duplicate | 3 |
| 78 | [`rajapinta-paakaupunkiseudun-kansalais-ja-tyovaenopistojen-kurssitietoihin`](https://hri.fi/data/en_GB/dataset/rajapinta-paakaupunkiseudun-kansalais-ja-tyovaenopistojen-kurssitietoihin) | API to course information for adult education centers in the capital region | entities | skip | - | - | - | JSON | continuous | CC-BY-4.0 | 200 | the Ilmoapix API (api.ilmonet.fi) needs an API key issued by Grynos Oy in every request; the platform creates no account (supervisor rule); Linked Courses (api.hel.fi/linkedcourses) answers 301 to dev.hel.fi, retired | - |
| 79 | [`suomenlinnan-lautan-matkustajamaarat`](https://hri.fi/data/en_GB/dataset/suomenlinnan-lautan-matkustajamaarat) | Passenger numbers of Suomenlinna ferry | entities | skip | - | - | - | JSON | daily | CC-BY-4.0 | 200 | the LATI API answers only with an access key (LWSAccessKey); a key goes in a secretRef only the owner creates, so no anonymous read exists | - |
| 80 | [`uusien-toimintojen-paikat-helsingin-rantareitilla`](https://hri.fi/data/en_GB/dataset/uusien-toimintojen-paikat-helsingin-rantareitilla) | Locations for new services at the Helsinki waterfront | entities | skip | - | - | - | WFS/WMS | not stated | CC-BY-4.0 | host timeout | WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host) | - |
| 81 | [`helsingin-asukas-ja-yrityspysakointivyohykkeet`](https://hri.fi/data/en_GB/dataset/helsingin-asukas-ja-yrityspysakointivyohykkeet) | Residential and corporate parking zones in Helsinki | entities | integrate | T-5259 | `OnStreetParking` (Parking) | ngsi-ld, geojson, ogc-features | WFS | not stated | CC-BY-4.0 | host timeout | already the resident-parking-zones seed | 2 |
| 82 | [`helsingin-hel-fi-sivuston-avoin-rajapinta-uutisille`](https://hri.fi/data/en_GB/dataset/helsingin-hel-fi-sivuston-avoin-rajapinta-uutisille) | News on Helsinki’s hel.fi website | entities | integrate | T-5259 | custom `Article` (helsinki seed model); closest SDM `MediaEvent` | ngsi-ld, feed | XML | continuous | CC-BY-4.0 | 200 | already the news-rss seed; images only beside their article (package note) | 3 |
| 83 | [`helsingin-kaupunginosat`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginosat) | District Map of the City of Helsinki | entities | integrate | T-5259 | custom `AdministrativeArea` (helsinki seed model); closest SDM none | ngsi-ld, geojson, ogc-features | WFS/WMS | continuous | CC-BY-4.0 | host timeout | already the districts seed | 3 |
| 84 | [`helsingin-piirijako`](https://hri.fi/data/en_GB/dataset/helsingin-piirijako) | District division of the City of Helsinki | entities | integrate | T-5259 | custom `AdministrativeArea` (helsinki seed model); closest SDM none | ngsi-ld, geojson, ogc-features | GPKG/TAB/WFS/WMS | yearly | CC-BY-4.0 | host timeout | already the subdistricts seed | 2 |
| 85 | [`helsingin-pysakoinnin-maksuvyohykkeet`](https://hri.fi/data/en_GB/dataset/helsingin-pysakoinnin-maksuvyohykkeet) | Parking payment zones | entities | integrate | T-5259 | `OnStreetParking` (Parking) | ngsi-ld, geojson, ogc-features | WFS/WMS | daily | CC-BY-4.0 | host timeout | already the fee-parking-zones seed | 3 |
| 86 | [`hsl-n-kaupunkipyoraasemat`](https://hri.fi/data/en_GB/dataset/hsl-n-kaupunkipyoraasemat) | Helsinki Region Transport’s (HSL) city bicycle stations | entities | integrate | T-5259 | `BikeHireDockingStation` (Transportation) | ngsi-ld, temporal, geojson, ogc-features, csv | CSV/GEOJSON/GEOSERVICE/KML/SHP | yearly | CC-BY-4.0 | 200 | already the bikes seeds (GBFS) | 2 |
| 87 | [`linked-events-tapahtumarajapinta`](https://hri.fi/data/en_GB/dataset/linked-events-tapahtumarajapinta) | Linked Events Helsinki API | entities | integrate | T-5259 | `Event` (TourismDestinations) | ngsi-ld, geojson, ical, feed | JSON | hourly | CC-BY-4.0 | 200 | already the events seed | 3 |
| 88 | [`rajapinta-helsingin-pysakointipaikkojen-kaytosta`](https://hri.fi/data/en_GB/dataset/rajapinta-helsingin-pysakointipaikkojen-kaytosta) | Parking spot usage API of Helsinki | entities | integrate | T-5259 | `OnStreetParking` (Parking) | ngsi-ld, temporal, geojson, ogc-features, csv | JSON | continuous | CC-BY-4.0 | 200 | already the parking-areas seed (pubapi.parkkiopas.fi) | 3 |
| 89 | [`veden-reaaliaikainen-lampotila-helsingin-uimarannoilla`](https://hri.fi/data/en_GB/dataset/veden-reaaliaikainen-lampotila-helsingin-uimarannoilla) | Real-time swimming water temperature in Helsinki metropolitan area | entities | integrate | T-5259 | `WaterQualityObserved` (WaterQuality) | ngsi-ld, temporal, geojson, ogc-features, csv | JSON | hourly | CC-BY-4.0 | 200 | already the beach-water seed (iot.fvh.fi uiras); T-5259 brings it to SDM | 3 |
| 90 | [`a01hki_astuot_tp_hper_rahoitus_talotyyppi`](https://hri.fi/data/en_GB/dataset/a01hki_astuot_tp_hper_rahoitus_talotyyppi) | Helsinki: housing production by type of house, tenure status, financing and room type 2015-2024 | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | archive: `alu_astuo_009r` holds periods before 2000 only, no new periods | - |
| 91 | [`aluesarjat-a01s-hki-askan-2005`](https://hri.fi/data/en_GB/dataset/aluesarjat-a01s-hki-askan-2005) | Dwellings in Helsinki, Espoo, Vantaa and Kauniainen by type of building and year of completion 2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_askan_005l` (theme housing, to the basic districts), 225 indicators on 2026-10-23 | 2 |
| 92 | [`aluesarjat-a01s-hki-rakennuskanta`](https://hri.fi/data/en_GB/dataset/aluesarjat-a01s-hki-rakennuskanta) | Buildings in Helsinki, Espoo, Vantaa and Kauniainen 31.12.2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_rakan_005x` (theme housing, to the basic districts), 90 indicators on 2026-10-23 | 2 |
| 93 | [`aluesarjat-a01s-hki-tyovoima-sukupuoli`](https://hri.fi/data/en_GB/dataset/aluesarjat-a01s-hki-tyovoima-sukupuoli) | Labour force living in Helsinki, Espoo, Vantaa and Kauniainen by gender and age 31.12.1999- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyov_004d` (theme employment), 171 indicators on 2026-10-23 | 2 |
| 94 | [`aluesarjat-a02s-hki-askan-talotyyppi-hallintap-kotilanne`](https://hri.fi/data/en_GB/dataset/aluesarjat-a02s-hki-askan-talotyyppi-hallintap-kotilanne) | Dwellings in Helsinki, Espoo, Vantaa and Kauniainen by building type and tenure status 2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_askan_005q` (theme housing, to the basic districts), 135 indicators on 2026-10-23 | 2 |
| 95 | [`aluesarjat-a03s-hki-kuolleet`](https://hri.fi/data/en_GB/dataset/aluesarjat-a03s-hki-kuolleet) | Deaths in Helsinki, Espoo, Vantaa and Kauniainen 1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010o` (theme population), 172 indicators on 2026-10-23 | 2 |
| 96 | [`aluesarjat-hginseutu-ar-aa01-asuntokanta-rvuosi-talotyyppi`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-ar-aa01-asuntokanta-rvuosi-talotyyppi) | Dwellings in Uusimaa by type of building, tenure status and occupancy status 31.12.2003- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_askan_005q` (built, by area), every city value equal on 2026-10-23 | - |
| 97 | [`aluesarjat-hginseutu-ar-aa03-asuntokanta-halper-huoneistotyyppi`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-ar-aa03-asuntokanta-halper-huoneistotyyppi) | Dwellings in Uusimaa by tenure status and type of dwelling 31.12.2003- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_askan_005s` (theme housing), 7 indicators on 2026-10-23 | 2 |
| 98 | [`aluesarjat-hginseutu-ar-rr01-rakennukset-kayttark-rvuosi`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-ar-rr01-rakennukset-kayttark-rvuosi) | Buildings in Uusimaa by intended use, year of construction and floor area 31.12. | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_rakan_005v` (theme housing), 36 indicators on 2026-10-23 | 2 |
| 99 | [`aluesarjat-hginseutu-as-ak01-asuntokunnat-talotyp-henkiloluku`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-as-ak01-asuntokunnat-talotyp-henkiloluku) | Number of households in the Helsinki region by number of dwellers and type of building | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_asas_005f` (theme housing), 8 indicators on 2026-10-23 | 2 |
| 100 | [`aluesarjat-hginseutu-tt-tm03-koulutustaso`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-tt-tm03-koulutustaso) | Population of the Helsinki region by level of education, primary occupation, gender and native language | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyom_003x` (theme employment), 5 indicators on 2026-10-23 | 2 |
| 101 | [`aluesarjat-hginseutu-va-ve02-vaestoennuste-kehys`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-va-ve02-vaestoennuste-kehys) | Population of the Helsinki region 31.12.1990- and population projection -2040 | statistics | skip | - | - | - | PXWEB | 3 years | CC-BY-4.0 | 200 | projection, not an observation (`alu_vaenn_006q`; the observed population is `alu_vaerak_004r`) | - |
| 102 | [`aluesarjat-hginseutu-va-ve03-vaestoennuste-kieli`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-va-ve03-vaestoennuste-kieli) | Population of the Helsinki region by native language 31.12.1999- and population projections 2009- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | projection, not an observation (`alu_vaenn_010c`; the observed population is `alu_vaerak_004r`) | - |
| 103 | [`aluesarjat-hginseutu-va-vr03-vakiluku-ika-sukup-aidinkieli3-ssaaty`](https://hri.fi/data/en_GB/dataset/aluesarjat-hginseutu-va-vr03-vakiluku-ika-sukup-aidinkieli3-ssaaty) | Population of the Helsinki region by age, gender, language and marital status 31.12.2001- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23 | - |
| 104 | [`aluesarjat_a01hki_asunto_ohjelma`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01hki_asunto_ohjelma) | Housing production projection for Helsinki | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | projection, not an observation (`alu_asohj_006b`; the observed population is `alu_vaerak_004r`) | - |
| 105 | [`aluesarjat_a01hki_asuntokuntien_tulot`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01hki_asuntokuntien_tulot) | Household income and taxes in Helsinki by district 1993-2017 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 106 | [`aluesarjat_a01hki_raktuot_kayttotark_2003-`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01hki_raktuot_kayttotark_2003-) | Construction in Helsinki by intended use 2023- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | archive: `alu_ratuo_009u` holds periods before 2000 only, no new periods | - |
| 107 | [`aluesarjat_a01hkis_vaestotulot`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01hkis_vaestotulot) | Population of Helsinki, Espoo and Vantaa by taxable income 2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vatul_011r` (theme income), 170 indicators on 2026-10-23 | 2 |
| 108 | [`aluesarjat_a01s_hki_asuntokunnat`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01s_hki_asuntokunnat) | Dwelling households in Helsinki, Espoo, Vantaa and Kauniainen by number of occupants 31.12.1978- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_asas_005d` (theme housing, to the basic districts), 270 indicators on 2026-10-23 | 2 |
| 109 | [`aluesarjat_a01s_hki_muuttoliike`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01s_hki_muuttoliike) | Internal migration by area and age group in Helsinki, Espoo and Vantaa 1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010g` (theme population, to the major districts), 385 indicators on 2026-10-23 | 2 |
| 110 | [`aluesarjat_a01s_hki_perhetyypit`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01s_hki_perhetyypit) | Families in Helsinki, Espoo, Vantaa and Kauniainen by family type starting 31.12.1998 | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_005y` (theme population, to the basic districts), 315 indicators on 2026-10-23 | 2 |
| 111 | [`aluesarjat_a01s_hki_vaesto_koulutusaste`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01s_hki_vaesto_koulutusaste) | Population 15 years of age and over of Helsinki, Espoo and Vantaa by gender, age and educational level 31.12. | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_kou_005n` (theme education), 1032 indicators on 2026-10-23 | 2 |
| 112 | [`aluesarjat_a01s_hki_vakiluku`](https://hri.fi/data/en_GB/dataset/aluesarjat_a01s_hki_vakiluku) | Population of Helsinki, Espoo, Vantaa and Kauniainen by gender, age and language (Swedish) 31.12.1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vaerak_004q` (theme population, to the basic districts), 135 indicators on 2026-10-23 | 2 |
| 113 | [`aluesarjat_a02s_hki_perhevaesto`](https://hri.fi/data/en_GB/dataset/aluesarjat_a02s_hki_perhevaesto) | Families in Helsinki, Espoo, Vantaa and Kauniainen starting 31.12.1998 | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_006t` (theme population), 334 indicators on 2026-10-23 | 2 |
| 114 | [`aluesarjat_a02s_hki_syntyneet`](https://hri.fi/data/en_GB/dataset/aluesarjat_a02s_hki_syntyneet) | Births by area in Helsinki, Espoo, Vantaa and Kauniainen beginning from 1998 | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010h` (theme population), 192 indicators on 2026-10-23 | 2 |
| 115 | [`aluesarjat_a02s_hki_vakiluku1962`](https://hri.fi/data/en_GB/dataset/aluesarjat_a02s_hki_vakiluku1962) | Population of Helsinki, Espoo, Vantaa and Kauniainen by age groups 31.12.1961- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vaerak_004r` (theme population), 172 indicators on 2026-10-23 | 2 |
| 116 | [`aluesarjat_a03s_hki_askan_hallintaperuste_htyyppi`](https://hri.fi/data/en_GB/dataset/aluesarjat_a03s_hki_askan_hallintaperuste_htyyppi) | Dwellings in Helsinki, Espoo, Vantaa and Kauniainen by tenure status and dwelling type 31.12.2002- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_askan_005r` (theme housing), 177 indicators on 2026-10-23 | 2 |
| 117 | [`aluesarjat_a03s_hki_lapsiperheet_alle18`](https://hri.fi/data/en_GB/dataset/aluesarjat_a03s_hki_lapsiperheet_alle18) | Families with children in Helsinki, Espoo, Vantaa and Kauniainen by number of children (under 18-year-olds) 1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_007h` (theme population, to the basic districts), 225 indicators on 2026-10-23 | 2 |
| 118 | [`aluesarjat_a03s_hki_vakiluku_aidinkieli`](https://hri.fi/data/en_GB/dataset/aluesarjat_a03s_hki_vakiluku_aidinkieli) | Population of Helsinki, Espoo, Vantaa and Kauniainen by native language and age group 31.12.1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vaerak_004p` (theme population), 516 indicators on 2026-10-23 | 2 |
| 119 | [`aluesarjat_a04s_hki_lapsiperheet`](https://hri.fi/data/en_GB/dataset/aluesarjat_a04s_hki_lapsiperheet) | Families with children in Helsinki, Espoo, Vantaa and Kauniainen by number 1998- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_009k` (theme population, to the basic districts), 225 indicators on 2026-10-23 | 2 |
| 120 | [`aluesarjat_a04s_hkis_tyottomat_sukupuoli`](https://hri.fi/data/en_GB/dataset/aluesarjat_a04s_hkis_tyottomat_sukupuoli) | Unemployed and unemployment rate in Helsinki, Espoo, Vantaa and Kauniainen by gender 31.12.2000- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyom_003t` (theme employment), 338 indicators on 2026-10-23 | 2 |
| 121 | [`aluesarjat_hginseutu_ar_aa02_asuntokanta_talotyyppi_halper_kaytil`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_ar_aa02_asuntokanta_talotyyppi_halper_kaytil) | Dwellings in Uusimaa by type of building and year of completion 31.12.2003- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_askan_005k` (theme housing), 5 indicators on 2026-10-23 | 2 |
| 122 | [`aluesarjat_hginseutu_as_ak02_asuntokuntien_keskikoko`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_as_ak02_asuntokuntien_keskikoko) | Average size of households in the Helsinki region | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_asas_005g` (theme housing), 3 indicators on 2026-10-23 | 2 |
| 123 | [`aluesarjat_hginseutu_as_ak03_asumisvaljyys_hloluku`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_as_ak03_asumisvaljyys_hloluku) | Households in the Helsinki region by surface area, number of dwellers and dwelling density | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_asas_005h` (theme housing), 24 indicators on 2026-10-23 | 2 |
| 124 | [`aluesarjat_hginseutu_tt_tm01_tyottomyys_kk`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_tt_tm01_tyottomyys_kk) | Monthly unemployment figures for the Helsinki region provided by | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | monthly | CC-BY-4.0 | 200 | built: `alu_tyom_040k` (theme employment), 19 indicators on 2026-10-23 | 3 |
| 125 | [`aluesarjat_hginseutu_tt_tm02_paa_as_toiminta`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_tt_tm02_paa_as_toiminta) | Population of the Helsinki region by primary occupation, age, gender and native language | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_tyom_003v` (built), every value equal on 2026-10-23 | - |
| 126 | [`aluesarjat_hginseutu_tt_tv01_tyovoima_ika`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_tt_tv01_tyovoima_ika) | Employed work force in the Helsinki region by age and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyov_004f` (theme employment), 12 indicators on 2026-10-23 | 2 |
| 127 | [`aluesarjat_hginseutu_tt_tv02a_tyovoima_tol2008`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_tt_tv02a_tyovoima_tol2008) | Employed labour force in the Helsinki region by the industry classification, age and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyov_004g` (theme employment), 23 indicators on 2026-10-23 | 2 |
| 128 | [`aluesarjat_hginseutu_va_mt01a_tulomuuttajatkoulutussuku`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_mt01a_tulomuuttajatkoulutussuku) | Migration in the Helsinki region by educational level and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_mutau_009o` (theme population), 9 indicators on 2026-10-23 | 2 |
| 129 | [`aluesarjat_hginseutu_va_mt01b_lahtomuuttajatkoulutussuku`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_mt01b_lahtomuuttajatkoulutussuku) | Emigrants of the Helsinki region by educational level and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_mutau_009p` (theme population), 9 indicators on 2026-10-23 | 2 |
| 130 | [`aluesarjat_hginseutu_va_pe01_perheet_perhetyyppi`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_pe01_perheet_perhetyyppi) | Number of families in the Helsinki region by family type | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_009x` (theme population), 6 indicators on 2026-10-23 | 2 |
| 131 | [`aluesarjat_hginseutu_va_pe02_lapsiperheet_lapsiluku`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_pe02_lapsiperheet_lapsiluku) | Families with children in the Helsinki region by number of children | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_perh_007h` (built, by area), every value equal on 2026-10-23 | - |
| 132 | [`aluesarjat_hginseutu_va_pe03_lapsiperheet_perhetyyppi`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_pe03_lapsiperheet_perhetyyppi) | Children in the Helsinki region by age group and family type | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_009z` (theme population), 5 indicators on 2026-10-23 | 2 |
| 133 | [`aluesarjat_hginseutu_va_pe04_perhevaesto`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_pe04_perhevaesto) | Families in Helsinki region by age of children | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_010a` (theme population), 10 indicators on 2026-10-23 | 2 |
| 134 | [`aluesarjat_hginseutu_va_vm01_vaestonmuutosten_yhdistelma`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vm01_vaestonmuutosten_yhdistelma) | Vital statistics of the Helsinki region | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010v` (theme population), 14 indicators on 2026-10-23 | 2 |
| 135 | [`aluesarjat_hginseutu_va_vm02_muuttoliike_alueittain`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vm02_muuttoliike_alueittain) | Migration in the Helsinki region | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010w` (theme population), 66 indicators on 2026-10-23 | 2 |
| 136 | [`aluesarjat_hginseutu_va_vm03_muuttoliike_ikaryhmittain`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vm03_muuttoliike_ikaryhmittain) | Migration in the Helsinki region by age group | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010x` (theme population), 7 indicators on 2026-10-23 | 2 |
| 137 | [`aluesarjat_hginseutu_va_vm04_syntyneet`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vm04_syntyneet) | Births in the Helsinki region by age of the mother | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vamuu_010t` (built), every value equal on 2026-10-23 | - |
| 138 | [`aluesarjat_hginseutu_va_vm05_kuolleet`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vm05_kuolleet) | Deaths in the Helsinki region by age and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010z` (theme population), 19 indicators on 2026-10-23 | 2 |
| 139 | [`aluesarjat_hginseutu_va_vr01_vakiluku_ika`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vr01_vakiluku_ika) | Population of the Helsinki region by age and gender 31.12.1975- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23 | - |
| 140 | [`aluesarjat_hginseutu_va_vr02_vakiluku_aidinkieli3`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vr02_vakiluku_aidinkieli3) | Population of the Helsinki region by native language 31.12.1980- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vaerak_004s` (built), every value equal on 2026-10-23 | - |
| 141 | [`aluesarjat_hginseutu_va_vr04_vakiluku_aidinkieli_ika`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vr04_vakiluku_aidinkieli_ika) | Population of the Helsinki region by native language and age 31.12.1999- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its one Helsinki value is the city total of `alu_vaerak_004r` (built) | - |
| 142 | [`aluesarjat_hginseutu_va_vr05_vakiluku_kansalaisuus_s`](https://hri.fi/data/en_GB/dataset/aluesarjat_hginseutu_va_vr05_vakiluku_kansalaisuus_s) | Population of the Helsinki region by nationality and gender 31.12.1999- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23 | - |
| 143 | [`asunnontarkastuksen-toimenpidepyynnot-helsingissa`](https://hri.fi/data/en_GB/dataset/asunnontarkastuksen-toimenpidepyynnot-helsingissa) | Dwelling inspection requests in Helsinki | statistics | skip | - | - | - | XLS | finished | CC-BY-4.0 | 200 | series ended (package update: finished); last file 2024-05 | - |
| 144 | [`eduskuntavaalit-helsingissa-2011`](https://hri.fi/data/en_GB/dataset/eduskuntavaalit-helsingissa-2011) | Parliamentary elections in Helsinki 2011 | statistics | skip | - | - | - | XLS | not stated | CC-BY-4.0 | 200 | one past election (2011), no series; national results are Statistics Finland's | - |
| 145 | [`eduskuntavaalit-helsingissa-2015`](https://hri.fi/data/en_GB/dataset/eduskuntavaalit-helsingissa-2015) | Parliamentary elections in Helsinki 2015 | statistics | skip | - | - | - | XLS | ended | CC-BY-4.0 | 200 | one past election (2015), no series (package update: ended) | - |
| 146 | [`elinkustannusindeksi-ja-rahanarvonkerroin-keskimaaraisten-kuukausivuokrien-deflatoimiseksi`](https://hri.fi/data/en_GB/dataset/elinkustannusindeksi-ja-rahanarvonkerroin-keskimaaraisten-kuukausivuokrien-deflatoimiseksi) | Cost-of-living index and deflation-adjusted mean monthly rental prices | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolo_022s` holds periods before 2000 only, no new periods | - |
| 147 | [`helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1900`](https://hri.fi/data/en_GB/dataset/helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1900) | Mean monthly rent of dwelling units in Helsinki by number of rooms 1900 and 1910 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolo_022r` holds periods before 2000 only, no new periods | - |
| 148 | [`helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1932-1974`](https://hri.fi/data/en_GB/dataset/helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1932-1974) | Mean monthly rent of dwelling units in Helsinki by number of rooms 1932-1974 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolo_022p` holds periods before 2000 only, no new periods | - |
| 149 | [`helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1975-1980`](https://hri.fi/data/en_GB/dataset/helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1975-1980) | Mean monthly rent of dwelling units in Helsinki by number of rooms 1975-1980 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolo_022q` holds periods before 2000 only, no new periods | - |
| 150 | [`helsingin-asuinhuoneistot-asuntovaesto-ja-asumistiheys-huoneluvun-mukaan-1870-1998`](https://hri.fi/data/en_GB/dataset/helsingin-asuinhuoneistot-asuntovaesto-ja-asumistiheys-huoneluvun-mukaan-1870-1998) | Dwelling units, dwelling population, and dwelling density in Helsinki by number of rooms 1870-1998 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_askun_022m` holds periods before 2000 only, no new periods | - |
| 151 | [`helsingin-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995`](https://hri.fi/data/en_GB/dataset/helsingin-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995) | Dwelling-unit disposable money income by quintale rank per consumption unit in Helsinki 1995- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_astul_011y` (theme income, to the major districts), 243 indicators on 2026-10-23 | 2 |
| 152 | [`helsingin-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995`](https://hri.fi/data/en_GB/dataset/helsingin-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995) | Dwelling-unit income by stage of life and area in Helsinki, Espoo and Vantaa 1995- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_astul_006f` (theme income), 1018 indicators on 2026-10-23 | 2 |
| 153 | [`helsingin-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`](https://hri.fi/data/en_GB/dataset/helsingin-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005) | Dwelling-unit income, gini coefficients per consumption unit in Helsinki 2005-2019 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 154 | [`helsingin-asuntotuotanto-aloitetut-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-aloitetut-rakennushankkeet-2015) | Helsingin asuntotuotanto - Aloitetut rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_astuo_039g` (built) | - |
| 155 | [`helsingin-asuntotuotanto-keskeneraiset-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-keskeneraiset-rakennushankkeet-2015) | Helsingin asuntotuotanto - Keskeneräiset rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the year-end value of the quarterly `alu_astuo_039h` (built) | - |
| 156 | [`helsingin-asuntotuotanto-myonnetyt-rakennusluvat-2015`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-myonnetyt-rakennusluvat-2015) | Helsingin asuntotuotanto - Myönnetyt rakennusluvat 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_astuo_039f` (built) | - |
| 157 | [`helsingin-asuntotuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1) | Housing production in Helsinki by quarter - Started construction projects 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_astuo_039g` (theme housing), 384 indicators on 2026-10-23 | 2 |
| 158 | [`helsingin-asuntotuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1) | Housing production in Helsinki by quarter - Construction projects in progress 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_astuo_039h` (theme housing, to the major districts), 154 indicators on 2026-10-23 | 2 |
| 159 | [`helsingin-asuntotuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1) | Housing production in Helsinki by quarter - Building permits granted 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_astuo_039f` (theme housing), 384 indicators on 2026-10-23 | 2 |
| 160 | [`helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1) | Housing production in Helsinki by quarter - Completed construction projects 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_astuo_039i` (theme housing), 384 indicators on 2026-10-23 | 2 |
| 161 | [`helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-ml-rah-hal-ja-rak-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-ml-rah-hal-ja-rak-2015q1) | Housing production in Helsinki by quarter - Completed construction projects (incl. financing, administrative basis, and developer) 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_astuo_039j` (theme housing, to the basic districts), 270 indicators on 2026-10-23 | 2 |
| 162 | [`helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-2015) | Helsingin asuntotuotanto - Valmistuneet rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_astuo_039i` (built) | - |
| 163 | [`helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-rahoitus-hallintaperuste-ja-rakennuttaja-2015`](https://hri.fi/data/en_GB/dataset/helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-rahoitus-hallintaperuste-ja-rakennuttaja-2015) | Helsingin asuntotuotanto - Valmistuneet rakennushankkeet (ml. rahoitus, hallintaperuste ja rakennuttaja) 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_astuo_039j` (built) | - |
| 164 | [`helsingin-erilaisilla-mukavuuslaitoksilla-varustetut-huoneistot-kaupunginosittain-1920`](https://hri.fi/data/en_GB/dataset/helsingin-erilaisilla-mukavuuslaitoksilla-varustetut-huoneistot-kaupunginosittain-1920) | Dwellings units equipped with different creature comforts in Helsinki by district 1920 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolo_022o` holds periods before 2000 only, no new periods | - |
| 165 | [`helsingin-erisuuruisissa-huoneistoissa-asuvat-henkilot-kaupunginosittain-8-12-1920`](https://hri.fi/data/en_GB/dataset/helsingin-erisuuruisissa-huoneistoissa-asuvat-henkilot-kaupunginosittain-8-12-1920) | Persons living in different sized dwelling units in Helsinki by district 8.12.1920 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_askun_022n` holds periods before 2000 only, no new periods | - |
| 166 | [`helsingin-henkikirjoitettu-vaesto-kaupunginosittain-1-1-1875-1960`](https://hri.fi/data/en_GB/dataset/helsingin-henkikirjoitettu-vaesto-kaupunginosittain-1-1-1875-1960) | Helsinki census by district 1.1.1875-1960 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vaerak_023o` holds periods before 2000 only, no new periods | - |
| 167 | [`helsingin-historialliset-tilastot`](https://hri.fi/data/en_GB/dataset/helsingin-historialliset-tilastot) | Historical statistics of Helsinki | statistics | skip | - | - | - | JSON/PXWEB | not stated | CC-BY-4.0 | 200 | archive: historical series from 1811 that end in the 2000s, no new periods | - |
| 168 | [`helsingin-kaupungin-avustukset`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-avustukset) | City of Helsinki grants | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | a ledger of grants to named recipients, no indicator per period and area (score -1: grant ledger) | - |
| 169 | [`helsingin-kaupungin-henkilosto-1914-1998`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-henkilosto-1914-1998) | City of Helsinki personnel 1914-1998 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyov_023k` holds periods before 2000 only, no new periods | - |
| 170 | [`helsingin-kaupungin-henkiloston-koulutukset`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-henkiloston-koulutukset) | Trainings for the employees of the city of Helsinki | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | a ledger of courses for city staff, no city indicator | - |
| 171 | [`helsingin-kaupungin-kansakoulujen-luokat-lukuvuosina-1896-97-1976-77`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-kansakoulujen-luokat-lukuvuosina-1896-97-1976-77) | City of Helsinki grammar school classes | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_kansk_022y` holds periods before 2000 only, no new periods | - |
| 172 | [`helsingin-kaupungin-kansakoulujen-opettajat-lukuvuosina-1896-97-1976-77`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-kansakoulujen-opettajat-lukuvuosina-1896-97-1976-77) | City of Helsinki grammar school teachers | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_kansk_022z` holds periods before 2000 only, no new periods | - |
| 173 | [`helsingin-kaupungin-kansakoulujen-oppilaat-lukuvuosina-1896-97-1976-77`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-kansakoulujen-oppilaat-lukuvuosina-1896-97-1976-77) | City of Helsinki grammar school students | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_kansk_023a` holds periods before 2000 only, no new periods | - |
| 174 | [`helsingin-kaupungin-kansakoulujen-oppilaiden-vanhempien-tausta-lukuvuosina-1896-97-1968-69`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-kansakoulujen-oppilaiden-vanhempien-tausta-lukuvuosina-1896-97-1968-69) | Social background of parents of grammar school students in Helsinki | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_kansk_023b` holds periods before 2000 only, no new periods | - |
| 175 | [`helsingin-kaupungin-nuorisoasiainkeskuksen-avustukset`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-nuorisoasiainkeskuksen-avustukset) | City of Helsinki youth department subsidies | statistics | skip | - | - | - | CSV/XLSX | not stated | CC-BY-4.0 | 200 | a ledger of subsidies to named youth associations, no indicator per period and area (grant ledger) | - |
| 176 | [`helsingin-kaupungin-ostot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-ostot) | City of Helsinki procurements | statistics | skip | - | - | - | CSV | monthly | CC-BY-4.0 | 200 | a ledger of purchase invoices per supplier, no indicator per period and area (invoice ledger) | - |
| 177 | [`helsingin-kaupungin-peruskoulujen-kielivalinnat`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-peruskoulujen-kielivalinnat) | Language choices in basic education schools of the City of Helsinki | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2024-12 | - |
| 178 | [`helsingin-kaupungin-talousarviotiedot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-talousarviotiedot) | City of Helsinki budget information | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | a budget table per account, no indicator per period and area (budget table) | - |
| 179 | [`helsingin-kaupungin-tulot-ja-menot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-tulot-ja-menot) | Income and expenditure of the City of Helsinki | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | income and expenditure per account, no indicator per period and area (budget table) | - |
| 180 | [`helsingin-kaupungin-tyonvalitystoiminta-1903-1960`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-tyonvalitystoiminta-1903-1960) | City of Helsinki employment placement activity 1903-1960 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyom_023e` holds periods before 2000 only, no new periods | - |
| 181 | [`helsingin-kaupungin-ymparistoraportti`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-ymparistoraportti) | City of Helsinki environmental report | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; its emission and energy figures are the Ymparistotilasto tables `ymp_kaspa_003k` and `ymp_eneku_002z` (built) | - |
| 182 | [`helsingin-kaupungin-ymparistotilinpito`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-ymparistotilinpito) | City of Helsinki environmental accounts | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | duplicate: the environmental accounts are `ymp_tunlu_037j` of Ymparistotilasto (built) | - |
| 183 | [`helsingin-kaupunginkirjaston-kaynnit-toimipisteittain`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginkirjaston-kaynnit-toimipisteittain) | Visitors at the City of Helsinki library by location | statistics | skip | - | - | - | XLS | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 184 | [`helsingin-kaupunginkirjaston-lainausmaarat-1860`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginkirjaston-lainausmaarat-1860) | Number of loans at City of Helsinki library in 1860-2020 | statistics | skip | - | - | - | XLS | ended | CC-BY-4.0 | 200 | archive: loans 1860-2020, series ended | - |
| 185 | [`helsingin-kaupunginkirjaston-lainausmaarat-toimipisteittain`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginkirjaston-lainausmaarat-toimipisteittain) | Number of loans by location at the City of Helsinki library | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 186 | [`helsingin-kaupunginkirjastossa-kirjastokorttiaan-k-ytt-neet`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginkirjastossa-kirjastokorttiaan-k-ytt-neet) | Library card usage at the city library of Helsinki | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 187 | [`helsingin-keskivakiluku-ian-ja-sukupuolen-mukaan-1935-1961`](https://hri.fi/data/en_GB/dataset/helsingin-keskivakiluku-ian-ja-sukupuolen-mukaan-1935-1961) | Mean population of Helsinki by age and gender 1935-1961 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vaerak_023l` holds periods before 2000 only, no new periods | - |
| 188 | [`helsingin-kestavan-kehityksen-indikaattorit`](https://hri.fi/data/en_GB/dataset/helsingin-kestavan-kehityksen-indikaattorit) | Helsinki sustainable development indicators | entities | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON/PX | yearly | CC-BY-4.0 | 200 | built: `sdg_sdg_037b`, the 123 VLR indicators, newest ended year (theme environment) | 0 |
| 189 | [`helsingin-kulttuurikeskuksen-avustukset`](https://hri.fi/data/en_GB/dataset/helsingin-kulttuurikeskuksen-avustukset) | City of Helsinki art and culture subsidies | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | a ledger of grants to named arts groups, no indicator per period and area (grant ledger) | - |
| 190 | [`helsingin-lammitettavat-rakennukset-rakennusaineen-ja-kerrosluvun-mukaan-1880-1930`](https://hri.fi/data/en_GB/dataset/helsingin-lammitettavat-rakennukset-rakennusaineen-ja-kerrosluvun-mukaan-1880-1930) | Heated buildings in Helsinki by building material and number of storeys 1880-1930 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_rakan_022h` holds periods before 2000 only, no new periods | - |
| 191 | [`helsingin-lukioiden-sis-np-syrajat`](https://hri.fi/data/en_GB/dataset/helsingin-lukioiden-sis-np-syrajat) | Admission criteria for upper secondary schools in Helsinki | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | stale: a yearly package with no file since 2023-08, older than three update periods | - |
| 192 | [`helsingin-lukioiden-yhteishaun-tulokset`](https://hri.fi/data/en_GB/dataset/helsingin-lukioiden-yhteishaun-tulokset) | Application results for upper secondary schools in Helsinki | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | stale: a yearly package with no file since 2023-08, older than three update periods | - |
| 193 | [`helsingin-nuoret-alueittain`](https://hri.fi/data/en_GB/dataset/helsingin-nuoret-alueittain) | Youths of Helsinki by Area | statistics | skip | - | - | - | XLS | not stated | CC-BY-4.0 | 200 | one past edition (2023-01), no series; the young population by basic district is `hyv_alue_006g` (built) | - |
| 194 | [`helsingin-oppikoulujen-1-ja-2-luokalle-otetut-oppilaat-lukuvuosina-1925-26-1960-61`](https://hri.fi/data/en_GB/dataset/helsingin-oppikoulujen-1-ja-2-luokalle-otetut-oppilaat-lukuvuosina-1925-26-1960-61) | Admissions to the 1. and 2. classes of grammar school in Helsinki | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_oppik_023d` holds periods before 2000 only, no new periods | - |
| 195 | [`helsingin-oppikoulut-lukuvuosina-1894-95-1976-77`](https://hri.fi/data/en_GB/dataset/helsingin-oppikoulut-lukuvuosina-1894-95-1976-77) | Grammar schools in Helsinki | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_oppik_023c` holds periods before 2000 only, no new periods | - |
| 196 | [`helsingin-osallistuvan-budjetoinnin-aanestystulokset`](https://hri.fi/data/en_GB/dataset/helsingin-osallistuvan-budjetoinnin-aanestystulokset) | Voting results of participatory budgeting in Helsinki | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | votes per proposal of each participatory budgeting round, no period series | - |
| 197 | [`helsingin-perus-ja-2-asteen-opetuksen-oppilasmaarat-kouluittain`](https://hri.fi/data/en_GB/dataset/helsingin-perus-ja-2-asteen-opetuksen-oppilasmaarat-kouluittain) | Number of students in basic and upper secondary education in Helsinki by school | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2024-11 | - |
| 198 | [`helsingin-rakennetut-kiinteistot-ja-lammitettavat-rakennukset-kaupunginosittain-1900-1950`](https://hri.fi/data/en_GB/dataset/helsingin-rakennetut-kiinteistot-ja-lammitettavat-rakennukset-kaupunginosittain-1900-1950) | Constructed real estate in Helsinki and heated buildings by district 1900-1950 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_rakan_022j` holds periods before 2000 only, no new periods | - |
| 199 | [`helsingin-rakennetut-kiinteistot-seka-lammitettavat-rakennukset-ja-huoneet-kaupunginosittain-1870`](https://hri.fi/data/en_GB/dataset/helsingin-rakennetut-kiinteistot-seka-lammitettavat-rakennukset-ja-huoneet-kaupunginosittain-1870) | Constructed real estate in Helsinki as well as heated buildings and rooms by district 1870-1930 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_rakan_022i` holds periods before 2000 only, no new periods | - |
| 200 | [`helsingin-rakennustuotanto-aloitetut-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-aloitetut-rakennushankkeet-2015) | Helsingin rakennustuotanto - Aloitetut rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_ratuo_039l` (built) | - |
| 201 | [`helsingin-rakennustuotanto-keskeneraiset-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-keskeneraiset-rakennushankkeet-2015) | Helsingin rakennustuotanto - Keskeneräiset rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the year-end value of the quarterly `alu_ratuo_039m` (built) | - |
| 202 | [`helsingin-rakennustuotanto-myonnetyt-rakennusluvat-2015`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-myonnetyt-rakennusluvat-2015) | Helsingin rakennustuotanto - Myönnetyt rakennusluvat 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_ratuo_039k` (built) | - |
| 203 | [`helsingin-rakennustuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1) | Building production in Helsinki by quarter - Started construction projects 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_ratuo_039l` (theme housing, to the basic districts), 405 indicators on 2026-10-23 | 2 |
| 204 | [`helsingin-rakennustuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1) | Building production in Helsinki by quarter - Construction projects in progress 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_ratuo_039m` (theme housing, to the basic districts), 405 indicators on 2026-10-23 | 2 |
| 205 | [`helsingin-rakennustuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1) | Building production in Helsinki by quarter - Building permits granted 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_ratuo_039k` (theme housing, to the basic districts), 405 indicators on 2026-10-23 | 2 |
| 206 | [`helsingin-rakennustuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1) | Building production in Helsinki by quarter - Completed construction projects 2015Q1- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_ratuo_039n` (theme housing, to the basic districts), 405 indicators on 2026-10-23 | 2 |
| 207 | [`helsingin-rakennustuotanto-valmistuneet-rakennushankkeet-2015`](https://hri.fi/data/en_GB/dataset/helsingin-rakennustuotanto-valmistuneet-rakennushankkeet-2015) | Helsingin rakennustuotanto - Valmistuneet rakennushankkeet 2015- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: the yearly sum of the quarterly `alu_ratuo_039n` (built) | - |
| 208 | [`helsingin-seudun-aluesarjat-tilastotietokannan-tiedot-paikkatietona`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-aluesarjat-tilastotietokannan-tiedot-paikkatietona) | Aluesarjat statistical database data as spatial data | entities | skip | - | - | - | WFS | yearly | CC-BY-4.0 | host timeout | duplicate: the WFS key-figure layer republishes Aluesarjat figures by sub-district that the statistics pipeline reads at the source (`alu_vaerak_004r`, `alu_askan_005r`); the sub-district geometry is the districts seed | - |
| 209 | [`helsingin-seudun-kuntien-valisen-ja-ulkomaisen-muuttoliikkeen-ennakkotiedot-neljannesvuosittain-2010`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-kuntien-valisen-ja-ulkomaisen-muuttoliikkeen-ennakkotiedot-neljannesvuosittain-2010) | Preliminary migration between municipalities and countries in the Helsinki region 2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_ennak_006u` (theme population), 3 indicators on 2026-10-23 | 2 |
| 210 | [`helsingin-seudun-perheet-perhetyypin-mukaan`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-perheet-perhetyypin-mukaan) | Families in the Helsinki region by family type | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_perh_009x` (theme population), 6 indicators on 2026-10-23 | 2 |
| 211 | [`helsingin-seudun-sairastavuusindeksi`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-sairastavuusindeksi) | Helsinki morbidity index | statistics | skip | - | - | - | XLSX | every 2 years | CC-BY-4.0 | 200 | duplicate: the morbidity index by basic district is `hyv_teel_038k` of the welfare database (built) | - |
| 212 | [`helsingin-seudun-tyopaikat-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-tyopaikat-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008) | Workplaces (employees in the area) in the Helsinki region by the industry classification | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_tyop_004a` (built), every value equal on 2026-10-23 | - |
| 213 | [`helsingin-seudun-v-est-1-1-1980-2013-sek-ennuste-1-1-2014-2050`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-v-est-1-1-1980-2013-sek-ennuste-1-1-2014-2050) | Population in the Helsinki Metropolitan area and Helsinki Region from 31.12.1979 and population projection (basic) by age and sex | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | projection, not an observation (`alu_vaenn_006e`; the observed population is `alu_vaerak_004r`) | - |
| 214 | [`helsingin-seudun-vaesto-aidinkielen-mukaan`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-vaesto-aidinkielen-mukaan) | Population of Helsinki region by native language | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its Helsinki row equals `alu_vaerak_004s` (built), every value equal on 2026-10-23 | - |
| 215 | [`helsingin-seudun-vaestonmuutosten-ennakkotiedot-vuoden-alusta-neljannesvuosittain`](https://hri.fi/data/en_GB/dataset/helsingin-seudun-vaestonmuutosten-ennakkotiedot-vuoden-alusta-neljannesvuosittain) | Preliminary vital statistics of the Helsinki region | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | quarterly | CC-BY-4.0 | 200 | built: `alu_ennak_006r` (theme population), 15 indicators on 2026-10-23 | 2 |
| 216 | [`helsingin-sosiaalitoimen-suoritetietoja`](https://hri.fi/data/en_GB/dataset/helsingin-sosiaalitoimen-suoritetietoja) | Performance indicators of social services in Helsinki | statistics | skip | - | - | - | XLS/XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-05 | - |
| 217 | [`helsingin-tilastollinen-vuosikirja`](https://hri.fi/data/en_GB/dataset/helsingin-tilastollinen-vuosikirja) | Statistical Yearbook of Helsinki | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | a yearbook compiled from the Aluesarjat and welfare tables built above; XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API | - |
| 218 | [`helsingin-tulo-ja-lahtomuutto-laaneittain-1911-1994`](https://hri.fi/data/en_GB/dataset/helsingin-tulo-ja-lahtomuutto-laaneittain-1911-1994) | Migration in Helsinki by province 1911-1994 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | archive: `his_vamuu_023q` holds periods before 2000 only, no new periods | - |
| 219 | [`helsingin-tyovaeston-asunto-olot-vuonna-1900-asuntojen-varustelutaso`](https://hri.fi/data/en_GB/dataset/helsingin-tyovaeston-asunto-olot-vuonna-1900-asuntojen-varustelutaso) | Living conditions of workers in Helsinki in 1900; dwelling unit trim level | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolotut_022x` holds periods before 2000 only, no new periods | - |
| 220 | [`helsingin-tyovaeston-asunto-olot-vuonna-1900-terveydelliset-olot`](https://hri.fi/data/en_GB/dataset/helsingin-tyovaeston-asunto-olot-vuonna-1900-terveydelliset-olot) | Living conditions of workers in Helsinki in 1900; health conditions | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolotut_022w` holds periods before 2000 only, no new periods | - |
| 221 | [`helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asukkaiden-lukumaarasta`](https://hri.fi/data/en_GB/dataset/helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asukkaiden-lukumaarasta) | Living conditions of workers in Helsinki in 1900, information on number of tenants | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolotut_022v` holds periods before 2000 only, no new periods | - |
| 222 | [`helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asuntojen-lukumaarasta`](https://hri.fi/data/en_GB/dataset/helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asuntojen-lukumaarasta) | Living conditions of workers in Helsinki in 1900; information on number of dwelling units | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolotut_022v` holds periods before 2000 only, no new periods | - |
| 223 | [`helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-huoneiden-lukumaarasta`](https://hri.fi/data/en_GB/dataset/helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-huoneiden-lukumaarasta) | Living conditions of workers in Helsinki in 1900; information on number of rooms | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_asolotut_022u` holds periods before 2000 only, no new periods | - |
| 224 | [`helsingin-vaesto-elinkeinoryhmittain-1870-1930`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-elinkeinoryhmittain-1870-1930) | Population of Helsinki by occupation 1870-1930 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyov_023i` holds periods before 2000 only, no new periods | - |
| 225 | [`helsingin-vaesto-ja-asuntotuotantoennuste-alueittain`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ja-asuntotuotantoennuste-alueittain) | Population and housing production projections of Helsinki | statistics | skip | - | - | - | XLS/XLSX | yearly | CC-BY-4.0 | 200 | projection, not an observation (the observed population is `alu_vaerak_004r`) | - |
| 226 | [`helsingin-vaesto-ja-ruotsinkieliset-1-1-1992-alkaen-seka-vaestoennuste-alueittain`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ja-ruotsinkieliset-1-1-1992-alkaen-seka-vaestoennuste-alueittain) | Population and population projection for Helsinki by district | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | projection, not an observation (`alu_vaenn_006c`; the observed population is `alu_vaerak_004r`) | - |
| 227 | [`helsingin-vaesto-paaasiallisen-toiminnan-sukupuolen-ja-ian-mukaan-31-12-2000`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-paaasiallisen-toiminnan-sukupuolen-ja-ian-mukaan-31-12-2000) | Population of Helsinki, Espoo, Vantaa and Kauniainen by primary occupation, gender and age 31.12.2000- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyom_003s` (theme employment, to the basic districts), 360 indicators on 2026-10-23 | 2 |
| 228 | [`helsingin-vaeston-ammatissa-toimivuus-1870-1930`](https://hri.fi/data/en_GB/dataset/helsingin-vaeston-ammatissa-toimivuus-1870-1930) | Economic activity of the population of Helsinki 1870-1930 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyov_023j` holds periods before 2000 only, no new periods | - |
| 229 | [`helsingin-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`](https://hri.fi/data/en_GB/dataset/helsingin-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015) | Preliminary population of Helsinki by age group and area 31.12.2015–2023 | statistics | skip | - | - | - | PXWEB | quarterly | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 230 | [`helsingin-vakiluku-1-1-1875-1993-ja-vuodenvaihteissa-1993-94-2013-14`](https://hri.fi/data/en_GB/dataset/helsingin-vakiluku-1-1-1875-1993-ja-vuodenvaihteissa-1993-94-2013-14) | Population of Helsinki 1.1.1875-1993 and at the turn of the year 1993/94-2013/14 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vaerak_023o` holds periods before 2000 only, no new periods | - |
| 231 | [`helsingin-vakiluku-ian-ja-sukupuolen-mukaan-1900-1961`](https://hri.fi/data/en_GB/dataset/helsingin-vakiluku-ian-ja-sukupuolen-mukaan-1900-1961) | Population of Helsinki by age and gender 1900-1961 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vaerak_023n` holds periods before 2000 only, no new periods | - |
| 232 | [`helsingin-vanhojen-asunto-osakehuoneistojen-neliohinnat-postinumeroalueittain-vuodesta-2000`](https://hri.fi/data/en_GB/dataset/helsingin-vanhojen-asunto-osakehuoneistojen-neliohinnat-postinumeroalueittain-vuodesta-2000) | Price per square meter of old dwellings in Helsinki by postal code | statistics | skip | - | - | - | XLS | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2024-05 | - |
| 233 | [`helsingin-ymparistotilasto`](https://hri.fi/data/en_GB/dataset/helsingin-ymparistotilasto) | Helsinki environmental statistics | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON/PXWEB | yearly | CC-BY-4.0 | 200 | built: 77 tables of the Ymparistotilasto database (theme environment), 1 to 189 indicators each; 15 tables older than 2023 or without a period listed in evidence/T-5258/rework-skipped-database-tables.tsv | 0 |
| 234 | [`helsingissa-asuva-tyollinen-tyovoima-toimialan-tol-2008-mukaan`](https://hri.fi/data/en_GB/dataset/helsingissa-asuva-tyollinen-tyovoima-toimialan-tol-2008-mukaan) | Employed work force in Helsinki, Espoo, Vantaa and Kauniainen by the industry classification 2008- | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | duplicate: its totals by area are `alu_tyov_004d` (built) one year older (2023), its industry breakdown of the city is `alu_tyov_004g` (built) | - |
| 235 | [`helsinki-alueittain`](https://hri.fi/data/en_GB/dataset/helsinki-alueittain) | Helsinki by district | statistics | skip | - | - | - | XLS/XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); the district profiles repeat Aluesarjat tables built above | - |
| 236 | [`helsinki-s-2030-climate-technologies-city-performance-tool-2016`](https://hri.fi/data/en_GB/dataset/helsinki-s-2030-climate-technologies-city-performance-tool-2016) | Helsinki’s 2030 Climate Technologies – City Performance Tool data set | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | one modelling run of 2016, no series | - |
| 237 | [`helsinki-turvattomuutta-kokevien-osuudet-peruspiireitt-2003-2006-ja-2009`](https://hri.fi/data/en_GB/dataset/helsinki-turvattomuutta-kokevien-osuudet-peruspiireitt-2003-2006-ja-2009) | Helsinki: Safety survey by area in 2003, 2006 and 2009 | statistics | skip | - | - | - | CSV/XLS | ended | CC-BY-4.0 | 200 | three past surveys (2003, 2006, 2009), series ended | - |
| 238 | [`helsinkiin-ja-helsingista-muuttaneet-sukupuolen-mukaan-1881-1998`](https://hri.fi/data/en_GB/dataset/helsinkiin-ja-helsingista-muuttaneet-sukupuolen-mukaan-1881-1998) | Migration in Helsinki by gender 1881-1998 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023p` holds periods before 2000 only, no new periods | - |
| 239 | [`ikaryhmittaiset-hedelmallisyysluvut-helsingissa-1936-2013`](https://hri.fi/data/en_GB/dataset/ikaryhmittaiset-hedelmallisyysluvut-helsingissa-1936-2013) | Age-specific fertility rates in Helsinki 1936-2013 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023y` holds periods before 2000 only, no new periods | - |
| 240 | [`kirjastokaynnit-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa`](https://hri.fi/data/en_GB/dataset/kirjastokaynnit-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa) | Library visits by location and by month in the City of Helsinki library | statistics | skip | - | - | - | XLS | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 241 | [`kirjojen-lainaus-kielittain-helsingin-kaupunginkirjastossa`](https://hri.fi/data/en_GB/dataset/kirjojen-lainaus-kielittain-helsingin-kaupunginkirjastossa) | Book loans by language at the City of Helsinki library | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 242 | [`kokonaishedelmallisyysluku-ja-yleinen-hedelmallisyysluku-helsingissa-1936-2013`](https://hri.fi/data/en_GB/dataset/kokonaishedelmallisyysluku-ja-yleinen-hedelmallisyysluku-helsingissa-1936-2013) | Total fertility rate and crude fertility rate in Helsinki 1936-2013 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023z` holds periods before 2000 only, no new periods | - |
| 243 | [`kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1891-1950`](https://hri.fi/data/en_GB/dataset/kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1891-1950) | Deaths by underlying cause of death in Helsinki per 10000 residents 1891-1950 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023u` holds periods before 2000 only, no new periods | - |
| 244 | [`kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1951-1968`](https://hri.fi/data/en_GB/dataset/kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1951-1968) | Deaths by underlying cause of death in Helsinki per 10000 residents 1951-1968 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023v` holds periods before 2000 only, no new periods | - |
| 245 | [`kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1969-1985`](https://hri.fi/data/en_GB/dataset/kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1969-1985) | Deaths by underlying cause of death in Helsinki per 10000 residents 1969-1985 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023w` holds periods before 2000 only, no new periods | - |
| 246 | [`kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1988-1995`](https://hri.fi/data/en_GB/dataset/kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1988-1995) | Deaths by underlying cause of death in Helsinki per 10000 residents 1988-1995 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023x` holds periods before 2000 only, no new periods | - |
| 247 | [`kuuden-suurimman-kaupungin-kehitysvammahuollon-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-kehitysvammahuollon-vertailu) | Comparison of care for the mentally disabled in the six largest cities | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2024-05 | - |
| 248 | [`kuuden-suurimman-kaupungin-lastensuojelun-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-lastensuojelun-vertailu) | Comparison of child welfare between the six largest cities | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-10 | - |
| 249 | [`kuuden-suurimman-kaupungin-paihde-ja-mielenterveyspalvelujen-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-paihde-ja-mielenterveyspalvelujen-vertailu) | Kuuden suurimman kaupungin päihde- ja mielenterveyspalvelujen vertailu | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-10 | - |
| 250 | [`kuuden-suurimman-kaupungin-toimeentulotuen-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-toimeentulotuen-vertailu) | Comparison of adult social work and income support between the six largest cities | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-10 | - |
| 251 | [`kuuden-suurimman-kaupungin-vammaispalvelujen-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-vammaispalvelujen-vertailu) | Comparison of social welfare for the disabled in the six largest cities | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-10 | - |
| 252 | [`kuuden-suurimman-kaupungin-vanhustenpalvelujen-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-vanhustenpalvelujen-vertailu) | Comparison of elderly care between the six largest cities | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-10 | - |
| 253 | [`kuuden-suurimman-kaupungin-varhaiskasvatuspalvelujen-vertailu`](https://hri.fi/data/en_GB/dataset/kuuden-suurimman-kaupungin-varhaiskasvatuspalvelujen-vertailu) | Comparison of early childhood education and care between the six largest cities | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2025-12 | - |
| 254 | [`lainaus-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa`](https://hri.fi/data/en_GB/dataset/lainaus-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa) | Loans by location and by month in the City of Helsinki library | statistics | skip | - | - | - | XLS | yearly | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06 | - |
| 255 | [`lasten-ja-nuorten-hyvinvointi-helsingissa`](https://hri.fi/data/en_GB/dataset/lasten-ja-nuorten-hyvinvointi-helsingissa) | Helsinki: Health and welfare statistics | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON/PXWEB | not stated | CC-BY-4.0 | 200 | built: 71 tables of the Hyvinvointitilastot database (theme welfare), by basic district where the table has one; 14 tables listed with their reason in evidence/T-5258/rework-skipped-database-tables.tsv | 0 |
| 256 | [`naiset-ja-miehet-helsingissa`](https://hri.fi/data/en_GB/dataset/naiset-ja-miehet-helsingissa) | Women and men in Helsinki | statistics | skip | - | - | - | XLS | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2023-03 | - |
| 257 | [`naisten-ja-miesten-taydellinen-elinajantaulu-km-jaljella-oleva-elinaika-helsingissa-1941-2005`](https://hri.fi/data/en_GB/dataset/naisten-ja-miesten-taydellinen-elinajantaulu-km-jaljella-oleva-elinaika-helsingissa-1941-2005) | Survival table by gender, mean lifespan in Helsinki 1941-2005 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023s` holds periods before 2000 only, no new periods | - |
| 258 | [`nordstat-tilastoja-pohjoismaiden-suurimmista-kaupungeista-ja-kaupunkiseuduista`](https://hri.fi/data/en_GB/dataset/nordstat-tilastoja-pohjoismaiden-suurimmista-kaupungeista-ja-kaupunkiseuduista) | Nordstat: statistics on largest Nordic cities | statistics | skip | - | - | - | JSON/PXWEB | not stated | CC-BY-4.0 | 200 | duplicate: Helsinki's rows are the Aluesarjat figures built above (population 2024: 684,018 in `nor_popu_008b` and `alu_vaerak_004r`); the other Nordic cities are outside the helsinki space | - |
| 259 | [`paakaupunkiseudun-autonomistajuustiedot`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-autonomistajuustiedot) | Car ownership in the metropolitan area | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-09 | - |
| 260 | [`paakaupunkiseudun-vaestoennuste`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-vaestoennuste) | Population projection in the Helsinki metropolitan area by district | statistics | skip | - | - | - | CSV | yearly | CC-BY-4.0 | 200 | projection, not an observation (the observed population is `alu_vaerak_004r`) | - |
| 261 | [`paikalliset-ja-muualle-ulottuvat-tyonseisaukset-helsingissa-1907-1951`](https://hri.fi/data/en_GB/dataset/paikalliset-ja-muualle-ulottuvat-tyonseisaukset-helsingissa-1907-1951) | Local and outreaching strikes in Helsinki 1907-1951 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyom_023f` holds periods before 2000 only, no new periods | - |
| 262 | [`paikalliset-tyonseisaukset-1954-1970-ja-tyotaistelut-helsingissa-1971-1997`](https://hri.fi/data/en_GB/dataset/paikalliset-tyonseisaukset-1954-1970-ja-tyotaistelut-helsingissa-1971-1997) | Local strikes 1954-1970 and labor disputes in Helsinki 1971-1997 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyom_023g` holds periods before 2000 only, no new periods | - |
| 263 | [`pks-kuntien-taloudellisia-tunnuslukuja`](https://hri.fi/data/en_GB/dataset/pks-kuntien-taloudellisia-tunnuslukuja) | Financial key figures for the municipalities in the metropolitan region | statistics | skip | - | - | - | CSV/XLS | ended | CC-BY-4.0 | 200 | series ended (package update: ended); last file 2024-05 | - |
| 264 | [`seudullinen-tilastorajapinta`](https://hri.fi/data/en_GB/dataset/seudullinen-tilastorajapinta) | Helsinki region statistics API | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | JSON/PXWEB | yearly | CC-BY-4.0 | 200 | built: this is the Aluesarjat PXWEB API the statistics pipeline reads (62 tables) | 0 |
| 265 | [`solmitut-ja-purkautuneet-avioliitot-helsingissa-1896-1998`](https://hri.fi/data/en_GB/dataset/solmitut-ja-purkautuneet-avioliitot-helsingissa-1896-1998) | Changes in marital status in Helsinki 1896-1998 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023t` holds periods before 2000 only, no new periods | - |
| 266 | [`syntyneet-ja-kuolleet-helsingissa-1811-1998`](https://hri.fi/data/en_GB/dataset/syntyneet-ja-kuolleet-helsingissa-1811-1998) | Births and deaths in Helsinki 1811-1998 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_vamuu_023r` holds periods before 2000 only, no new periods | - |
| 267 | [`teollisuuden-tyopaikat-ja-tyontekijat-helsingissa-1884-1965`](https://hri.fi/data/en_GB/dataset/teollisuuden-tyopaikat-ja-tyontekijat-helsingissa-1884-1965) | Employment in manufacturing and employees in Helsinki 1884-1965 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_tyop_023h` holds periods before 2000 only, no new periods | - |
| 268 | [`tyopaikat-helsingissa-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008`](https://hri.fi/data/en_GB/dataset/tyopaikat-helsingissa-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008) | Workplaces (employees in the area) in Helsinki, Espoo, Vantaa and Kauniainen by the industry classification 2008- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyop_003y` (theme employment), 169 indicators on 2026-10-23 | 2 |
| 269 | [`tyopaikat-uudellamaalla-alueella-tyossakayvat-toimialan-tol-2008-mukaan`](https://hri.fi/data/en_GB/dataset/tyopaikat-uudellamaalla-alueella-tyossakayvat-toimialan-tol-2008-mukaan) | Jobs in Uusimaa (area employed) by industry (TOL 2008) 31.12.2007- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyop_004a` (theme employment), 23 indicators on 2026-10-23 | 2 |
| 270 | [`uudenmaan-asuntokunnat-henkiloluvun-ja-vanhimman-ian-mukaan`](https://hri.fi/data/en_GB/dataset/uudenmaan-asuntokunnat-henkiloluvun-ja-vanhimman-ian-mukaan) | Household-dwelling units in Uusimaa by number of persons and oldest age 31.12.1994- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_asas_005e` (theme housing), 18 indicators on 2026-10-23 | 2 |
| 271 | [`uudenmaan-kuntien-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995`](https://hri.fi/data/en_GB/dataset/uudenmaan-kuntien-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995) | Uusimaa municipalities household-dwelling unit disposable money income per consumption unit by decile rank 1995-2019 | statistics | skip | - | - | - | PXWEB | yearly | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 272 | [`uudenmaan-kuntien-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995`](https://hri.fi/data/en_GB/dataset/uudenmaan-kuntien-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995) | Uusimaa municipalities dwelling-unit income by stage of life and area | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 273 | [`uudenmaan-kuntien-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`](https://hri.fi/data/en_GB/dataset/uudenmaan-kuntien-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005) | Uusimaa municipalities household-dwelling unit incomes, income per consumption unit gini coefficients 2005-2019 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | archive or historical series, no new periods | - |
| 274 | [`uudenmaan-rakennukset-kayttotarkoituksen-lammitystavan-lammitysaineen-ja-kerrosalan-mukaan`](https://hri.fi/data/en_GB/dataset/uudenmaan-rakennukset-kayttotarkoituksen-lammitystavan-lammitysaineen-ja-kerrosalan-mukaan) | Buildings in Uusimaa by purpose of use, heating method, heating material and floor area 31.12.2010- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_rakan_005w` (theme housing), 36 indicators on 2026-10-23 | 2 |
| 275 | [`uudenmaan-seudullinen-tyopaikkaprojektio-1980-2060`](https://hri.fi/data/en_GB/dataset/uudenmaan-seudullinen-tyopaikkaprojektio-1980-2060) | Uusimaa Regional Job Projection 1980-2060 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | projection, not an observation (`alu_typroj_003i`; the observed population is `alu_vaerak_004r`) | - |
| 276 | [`uudenmaan-tyopaikkaprojektioissa-kaytetyt-vaestoprojektiot`](https://hri.fi/data/en_GB/dataset/uudenmaan-tyopaikkaprojektioissa-kaytetyt-vaestoprojektiot) | Population projections used in Uusimaa's workplace projections | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | projection, not an observation (`alu_typroj_004c`; the observed population is `alu_vaerak_004r`) | - |
| 277 | [`uudenmaan-vaesto-aidinkielen-sukupuolen-ja-ian-mukaan`](https://hri.fi/data/en_GB/dataset/uudenmaan-vaesto-aidinkielen-sukupuolen-ja-ian-mukaan) | Population of Uusimaa by native language, gender and age 31.12.1994- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vaerak_004s` (theme population), 4 indicators on 2026-10-23 | 2 |
| 278 | [`uudenmaan-vaesto-ian-mukaan`](https://hri.fi/data/en_GB/dataset/uudenmaan-vaesto-ian-mukaan) | Population of Uusimaa by age 31.12.1961- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vaerak_004t` (theme population), 14 indicators on 2026-10-23 | 2 |
| 279 | [`uudenmaan-vaesto-paaasiallisen-toiminnan-ian-ja-sukupuolen-mukaan`](https://hri.fi/data/en_GB/dataset/uudenmaan-vaesto-paaasiallisen-toiminnan-ian-ja-sukupuolen-mukaan) | Population of Uusimaa by main activity, age and sex 31.12.2001- | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_tyom_003v` (theme employment), 10 indicators on 2026-10-23 | 2 |
| 280 | [`uusimaa-kuolleet-ian-ja-sukupuolen-mukaan`](https://hri.fi/data/en_GB/dataset/uusimaa-kuolleet-ian-ja-sukupuolen-mukaan) | Uusimaa: Deaths by age and gender | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010u` (theme population), 3 indicators on 2026-10-23 | 2 |
| 281 | [`uusimaa-muuttoliike-lahto-tai-kohdealueen-aidinkielen-ja-ian-mukaan`](https://hri.fi/data/en_GB/dataset/uusimaa-muuttoliike-lahto-tai-kohdealueen-aidinkielen-ja-ian-mukaan) | Uusimaa: Migration by region of origin or destination, native language and age | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010r` (theme population), 27 indicators on 2026-10-23 | 2 |
| 282 | [`uusimaa-syntyneet-aidin-ian-mukaan`](https://hri.fi/data/en_GB/dataset/uusimaa-syntyneet-aidin-ian-mukaan) | Uusimaa: Born according to mother's age | statistics | statistics | T-5258 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld, temporal, csv | PXWEB | yearly | CC-BY-4.0 | 200 | built: `alu_vamuu_010t` (theme population), 8 indicators on 2026-10-23 | 2 |
| 283 | [`valmistuneet-asuinhuoneet-kivi-ja-puutaloissa-helsingissa-1939-1950`](https://hri.fi/data/en_GB/dataset/valmistuneet-asuinhuoneet-kivi-ja-puutaloissa-helsingissa-1939-1950) | Completed dwelling units in stone- and wooden- houses in Helsinki 1939-1950 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_raken_022l` holds periods before 2000 only, no new periods | - |
| 284 | [`valmistuneet-asuinhuoneistot-helsingissa-1921-1967`](https://hri.fi/data/en_GB/dataset/valmistuneet-asuinhuoneistot-helsingissa-1921-1967) | Completed dwelling units in Helsinki 1921-1967 | statistics | skip | - | - | - | PXWEB | not stated | CC-BY-4.0 | 200 | archive: `his_raken_022k` holds periods before 2000 only, no new periods | - |
| 285 | [`aarteeni-helsingissa-kyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/aarteeni-helsingissa-kyselyn-vastaukset) | Helsinki Treasures survey | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 286 | [`elintarvikevalvonnan-piiriin-kuuluvat-elintarvikehuoneistot-helsingissa`](https://hri.fi/data/en_GB/dataset/elintarvikevalvonnan-piiriin-kuuluvat-elintarvikehuoneistot-helsingissa) | Food establishments in Helsinki under food control supervision by the Food Safety Department | statistics | skip | - | - | - | CSV | not stated | CC-BY-4.0 | 200 | not maintained since 1/2019; the national VATI register replaced it (package note) | - |
| 287 | [`espoon-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`](https://hri.fi/data/en_GB/dataset/espoon-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005) | Dwelling-unit income, gini coefficients per consumption unit in Espoo 2005-2019 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | City of Espoo only, outside the helsinki space | - |
| 288 | [`espoon-kaupungin-resurssienvarausrajapinta`](https://hri.fi/data/en_GB/dataset/espoon-kaupungin-resurssienvarausrajapinta) | Resource reservation system for City of Espoo | entities | skip | - | - | - | JSON | continuous | CC-BY-4.0 | unreachable | City of Espoo resources, outside the helsinki space | - |
| 289 | [`espoon-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`](https://hri.fi/data/en_GB/dataset/espoon-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015) | Preliminary population of Espoo by age group and area 31.12.2015–2023 | statistics | skip | - | - | - | PXWEB | quarterly | CC-BY-4.0 | 200 | City of Espoo only, outside the helsinki space | - |
| 290 | [`etelasatama-virtual-3d-malli`](https://hri.fi/data/en_GB/dataset/etelasatama-virtual-3d-malli) | Virtual 3D Model of the South Harbour in Helsinki 2011 | imagery-or-3d | skip | - | - | - | DWG | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 291 | [`helmet-kirjastojen-aineistoluettelot`](https://hri.fi/data/en_GB/dataset/helmet-kirjastojen-aineistoluettelot) | Helmet-libraries’ catalog | entities | skip | - | - | - | /JSON | continuous | CC-BY-4.0 | 403 | bibliographic records; libraries come from the Service Map (T-5257) | - |
| 292 | [`helmet-kirjastojen-lainatuimmat-aikuistenkirjat`](https://hri.fi/data/en_GB/dataset/helmet-kirjastojen-lainatuimmat-aikuistenkirjat) | HelMet-libraries' most loaned adult books | statistics | skip | - | - | - | CSV/XLS/XLSX | monthly | CC-BY-4.0 | 200 | ranking of book titles, no city indicator | - |
| 293 | [`helmet-kirjastojen-lainatuimmat-lastenkirjat`](https://hri.fi/data/en_GB/dataset/helmet-kirjastojen-lainatuimmat-lastenkirjat) | HelMet-libraries' most loaned children's books | statistics | skip | - | - | - | XLS/XLSX | monthly | CC-BY-4.0 | 200 | ranking of book titles, no city indicator | - |
| 294 | [`helmet-kirjastojen-varatuimmat-kirjat`](https://hri.fi/data/en_GB/dataset/helmet-kirjastojen-varatuimmat-kirjat) | HelMet-libraries' most reserved books | statistics | skip | - | - | - | XLS | yearly | CC-BY-4.0 | 200 | ranking of book titles, no city indicator | - |
| 295 | [`helsingin-3d-kaupunkimalli`](https://hri.fi/data/en_GB/dataset/helsingin-3d-kaupunkimalli) | 3D models of Helsinki | entities | skip | - | - | - | /GML/NBT/OBJ/PNG/WFS/XLSX | not stated | CC-BY-4.0 | 200 | CityGML/mesh 3D model; buildings come from helsingin-rakennukset (T-5256), the model stays a catalogue link | - |
| 296 | [`helsingin-3d-rakennukset`](https://hri.fi/data/en_GB/dataset/helsingin-3d-rakennukset) | 3D-buildings of the City of Helsinki | entities | skip | - | - | - | KML/SKP | yearly | CC-BY-4.0 | host timeout | KML/SKP 3D buildings; same buildings as helsingin-rakennukset | - |
| 297 | [`helsingin-ajantasa-asemakaava`](https://hri.fi/data/en_GB/dataset/helsingin-ajantasa-asemakaava) | Combined Detailed Plan Map of The City of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS | continuous | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 298 | [`helsingin-asemakaavakartat`](https://hri.fi/data/en_GB/dataset/helsingin-asemakaavakartat) | Plan maps of the city of Helsinki | imagery-or-3d | skip | - | - | - | /DGN | continuous | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 299 | [`helsingin-asuntokunnat-henkilun-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-asuntokunnat-henkilun-mukaan-piireitt-ja-osa-alueittain-2004-alkaen) | Househoulds in Helsinki by number of persons and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 300 | [`helsingin-asuntokunnat-koon-ja-vanhimman-henkilon-ian-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-asuntokunnat-koon-ja-vanhimman-henkilon-ian-mukaan-suurpiireittain-2004-alkaen) | Households in Helsinki by size, oldest person and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 301 | [`helsingin-espoon-ja-vantaan-liikennevaloristeykset`](https://hri.fi/data/en_GB/dataset/helsingin-espoon-ja-vantaan-liikennevaloristeykset) | Intersections with traffic lights in Helsinki, Espoo, Vantaa and Kauniainen | imagery-or-3d | skip | - | - | - | KMZ | continuous | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 302 | [`helsingin-historialliset-asemakaavakartat`](https://hri.fi/data/en_GB/dataset/helsingin-historialliset-asemakaavakartat) | Historical detailed plan maps of the city of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 303 | [`helsingin-historialliset-kartat`](https://hri.fi/data/en_GB/dataset/helsingin-historialliset-kartat) | Historical maps of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS | not stated | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 304 | [`helsingin-historialliset-opaskartat`](https://hri.fi/data/en_GB/dataset/helsingin-historialliset-opaskartat) | Historical guide maps of the City of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 305 | [`helsingin-historialliset-yleiskaavat`](https://hri.fi/data/en_GB/dataset/helsingin-historialliset-yleiskaavat) | Historical general plan maps of the city of Helsinki | imagery-or-3d | skip | - | - | - | WMS | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 306 | [`helsingin-ja-vantaan-ymparistoasennekyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-ja-vantaan-ymparistoasennekyselyn-vastaukset) | Answers to Helsinki’s and Vantaa’s environment attitude survey | statistics | skip | - | - | - | CSV/XLS | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 307 | [`helsingin-johtamisen-uudistaminen-verkkokyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-johtamisen-uudistaminen-verkkokyselyn-vastaukset) | Reforming the governance system of Helsinki survey results | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 308 | [`helsingin-kansallinen-kaupunkipuisto-kyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-kansallinen-kaupunkipuisto-kyselyn-vastaukset) | Answers to the questionnaire about Helsinki's national city park | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 309 | [`helsingin-kantakartta`](https://hri.fi/data/en_GB/dataset/helsingin-kantakartta) | Base map of the City of Helsinki | imagery-or-3d | skip | - | - | - | PNG/WMS | continuous | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 310 | [`helsingin-katujen-puhdistussuunnitelmat`](https://hri.fi/data/en_GB/dataset/helsingin-katujen-puhdistussuunnitelmat) | Helsinki street cleaning plans | statistics | skip | - | - | - | - | daily | CC-BY-4.0 | no resource URL | service unavailable since 1/2026 (package note) | - |
| 311 | [`helsingin-kaupungin-chatbotien-koulutusdatat`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-chatbotien-koulutusdatat) | Training data for City of Helsinki chatbots | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | chatbot training text, no city entity | - |
| 312 | [`helsingin-kaupungin-koulurekisteri`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-koulurekisteri) | School history database of Helsinki | entities | skip | - | - | - | JSON | not stated | CC-BY-4.0 | 200 | API removed 1/2026 (package note) | - |
| 313 | [`helsingin-kaupungin-resurssienvarausrajapinta`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-resurssienvarausrajapinta) | Resource reservation API for City of Helsinki | statistics | skip | - | - | - | - | not stated | CC-BY-4.0 | no resource URL | API not in use since 12/2024 (package note) | - |
| 314 | [`helsingin-kaupungin-taloushallintopalvelun-tulot-ja-menot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-taloushallintopalvelun-tulot-ja-menot) | Income and expenditure of the financial administration service of the City of Helsinki | statistics | skip | - | - | - | CSV | ended | CC-BY-4.0 | unreachable | resource unreachable on 2026-10-22; recheck in T-5258 | - |
| 315 | [`helsingin-kaupungin-talvihoidon-kayttajatyytyvaisyyskyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-talvihoidon-kayttajatyytyvaisyyskyselyn-vastaukset) | Answers to the surveys regarding summer and winter maintenance of the City of Helsinki | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 316 | [`helsingin-kaupungin-tarkastuslautakunnan-arviointikertomuksissa-esitetyt-suositukset`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-tarkastuslautakunnan-arviointikertomuksissa-esitetyt-suositukset) | Assessments and recommendations made by the Audit Committee of the City of Helsinki | statistics | skip | - | - | - | XLS | 2 times a year | CC-BY-4.0 | 200 | audit recommendations as text, no entity or indicator | - |
| 317 | [`helsingin-kaupungin-yrityshaastattelututkimus`](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-yrityshaastattelututkimus) | Telephone survey data of Helsinki-based companies | statistics | skip | - | - | - | XLSX | every 2 years | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 318 | [`helsingin-kaupunginarkiston-aineistot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginarkiston-aineistot) | Materials of Helsinki City Archives | entities | skip | - | - | - | /JSON | continuous | CC-BY-4.0 | 403 | archive media catalogue (documents, photos); answered 403 to the probe | - |
| 319 | [`helsingin-kaupunginmuseon-aineistot`](https://hri.fi/data/en_GB/dataset/helsingin-kaupunginmuseon-aineistot) | Collections of Helsinki City Museum | entities | skip | - | - | - | JPEG/JSON | not stated | CC-BY-4.0 | 403 | museum media catalogue (Finna); answered 403 to the probe | - |
| 320 | [`helsingin-kiinteistokartta`](https://hri.fi/data/en_GB/dataset/helsingin-kiinteistokartta) | Cadastral Map of the City of Helsinki | imagery-or-3d | skip | - | - | - | PNG/WMS/WMTS | continuous | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 321 | [`helsingin-koko-vt-ulkomaalaistaustaiset-maan-ja-imukaan-suurpiireitt-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-koko-vt-ulkomaalaistaustaiset-maan-ja-imukaan-suurpiireitt-2004-alkaen) | Population and foreign people in Helsinki by place of birth, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 322 | [`helsingin-koko-vtkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-koko-vtkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-alkaen) | Population and foreign people in Helsinki by citizenship, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 323 | [`helsingin-korkeusmalli`](https://hri.fi/data/en_GB/dataset/helsingin-korkeusmalli) | Elevation model of the City of Helsinki | imagery-or-3d | skip | - | - | - | WCS | when changes | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 324 | [`helsingin-kuvakartta`](https://hri.fi/data/en_GB/dataset/helsingin-kuvakartta) | Pictorial map of the City of Helsinki | imagery-or-3d | skip | - | - | - | PNG/TIFF/WMS | not stated | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 325 | [`helsingin-laserkeilausaineistot`](https://hri.fi/data/en_GB/dataset/helsingin-laserkeilausaineistot) | Lidar datasets of the city of Helsinki | imagery-or-3d | skip | - | - | - | LAZ | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 326 | [`helsingin-liikenneturvallisuuskysely-asukkaille`](https://hri.fi/data/en_GB/dataset/helsingin-liikenneturvallisuuskysely-asukkaille) | Traffic safety survey for citizens of Helsinki | entities | skip | - | - | - | GPKG/SHP/XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 327 | [`helsingin-luontopalvelulinjauksen-asukaskyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-luontopalvelulinjauksen-asukaskyselyn-vastaukset) | Helsinki nature service policy resident survey responses | entities | skip | - | - | - | SHP/XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 328 | [`helsingin-mikroilmaston-simulaatiodemo`](https://hri.fi/data/en_GB/dataset/helsingin-mikroilmaston-simulaatiodemo) | Microclimate simulation demo of Helsinki | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | one-off 2023 simulation demo: modelled output, not an observation, never updated | - |
| 329 | [`helsingin-muu-kuin-suomen-ja-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-`](https://hri.fi/data/en_GB/dataset/helsingin-muu-kuin-suomen-ja-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-) | Other than Finnish- or Swedish-speaking population in Helsinki by age, marital status and sex in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 330 | [`helsingin-muun-kuin-suomen-tai-ruotsinkielinen-vtn-ja-sukupuolen-mukaan-suurpiireitt-2004-alkae`](https://hri.fi/data/en_GB/dataset/helsingin-muun-kuin-suomen-tai-ruotsinkielinen-vtn-ja-sukupuolen-mukaan-suurpiireitt-2004-alkae) | Other than Finnish- or Swedish-speaking population in Helsinki by age, sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 331 | [`helsingin-opaskartta`](https://hri.fi/data/en_GB/dataset/helsingin-opaskartta) | Guide Map of the City of Helsinki | entities | skip | - | - | - | TIFF/WFS/WMS/WMTS | yearly | CC-BY-4.0 | host timeout | cartographic guide map layers (labels, symbols) over data integrated elsewhere | - |
| 332 | [`helsingin-ortoilmakuvat`](https://hri.fi/data/en_GB/dataset/helsingin-ortoilmakuvat) | Orthophotographs of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS/WMTS | yearly | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 333 | [`helsingin-paivahoitotilastot`](https://hri.fi/data/en_GB/dataset/helsingin-paivahoitotilastot) | Statistics on day care in Helsinki | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | not maintained; superseded by the six-cities early education comparison (package note) | - |
| 334 | [`helsingin-perheet-ja-lapset-sekterherakennetta-kuvaavia-tunnuslukuja-piireitt-ja-osa-alueittain`](https://hri.fi/data/en_GB/dataset/helsingin-perheet-ja-lapset-sekterherakennetta-kuvaavia-tunnuslukuja-piireitt-ja-osa-alueittain) | Families and children in Helsinki and keyfigures which describe the familystructure of population by district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 335 | [`helsingin-pintamalli`](https://hri.fi/data/en_GB/dataset/helsingin-pintamalli) | 3D city model of the City of Helsinki | imagery-or-3d | skip | - | - | - | SKP | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 336 | [`helsingin-pyorailybarometrikyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-pyorailybarometrikyselyn-vastaukset) | Helsinki cyclist barometer survey answers | statistics | skip | - | - | - | XLSX | every 2 years | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 337 | [`helsingin-pyoravaylien-ongelmakohdekyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-pyoravaylien-ongelmakohdekyselyn-vastaukset) | Survey of problems in bicycle ways in Helsinki | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 338 | [`helsingin-raide-jokerin-linjaus-ja-pysakit`](https://hri.fi/data/en_GB/dataset/helsingin-raide-jokerin-linjaus-ja-pysakit) | Jokeri Light Rail Line lines and stations | entities | skip | - | - | - | WFS/WMS | not stated | CC-BY-4.0 | host timeout | duplicate: line 15 and its stops are in the HSL GTFS seeds | - |
| 339 | [`helsingin-rinnevarjosteet`](https://hri.fi/data/en_GB/dataset/helsingin-rinnevarjosteet) | Hillshading of the City of Helsinki | imagery-or-3d | skip | - | - | - | WMS | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 340 | [`helsingin-ruotsinkielinen-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-ruotsinkielinen-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen) | Swedish-speaking population in Helsinki by age, sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 341 | [`helsingin-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen) | Swedish-speaking population in Helsinki by age, marital status and sex in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 342 | [`helsingin-ruotsinkielinen-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-ruotsinkielinen-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen) | Swedish-speaking population in Helsinki by age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 343 | [`helsingin-suomenkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-suomenkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen) | Finnish-speaken population in Helsinki by age, marital status and sex in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 344 | [`helsingin-tuulivoimakysely-2015`](https://hri.fi/data/en_GB/dataset/helsingin-tuulivoimakysely-2015) | Wind power survey for Helsinki 2015 | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 345 | [`helsingin-ulkomaalaistaustainen-vaesto-sukupuolen-ja-taustamaan-mukaan-2017-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-ulkomaalaistaustainen-vaesto-sukupuolen-ja-taustamaan-mukaan-2017-alkaen) | Population with foreign background in Helsinki 2017-2023 according to gender and background country | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 346 | [`helsingin-vaesto-aidinkielen-ja-ian-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-aidinkielen-ja-ian-mukaan-suurpiireittain-2004-alkaen) | Population in Helsinki by language, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 347 | [`helsingin-vaesto-ian-1-v-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ian-1-v-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen) | Population in Helsinki by age (1 year), sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 348 | [`helsingin-vaesto-ian-5-v-aidinkielen-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ian-5-v-aidinkielen-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen) | Population in Helsinki by age (5-year), language, sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 349 | [`helsingin-vaesto-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen) | Population in Helsinki by age (5-year) and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 350 | [`helsingin-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen) | Population in Helsinki by age, sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 351 | [`helsingin-vaesto-piireittain-ja-osa-alueittain-ian-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-piireittain-ja-osa-alueittain-ian-mukaan-2004-alkaen) | Population in Helsinki by district and age in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 352 | [`helsingin-vaesto-sukupuolen-ja-sivilisaadyn-mukaan-2004-alkaen-piireittain-ja-osa-alueittain`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-sukupuolen-ja-sivilisaadyn-mukaan-2004-alkaen-piireittain-ja-osa-alueittain) | Population in Helsinki by sex and marital status and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 353 | [`helsingin-vaesto-syntymapaikan-sukupuolen-ja-ian-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-syntymapaikan-sukupuolen-ja-ian-mukaan-2004-alkaen) | Population in Helsinki by place of birth, sex and age in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 354 | [`helsingin-vaesto-uskonnollisen-yhdyskunnan-sukupuolen-ja-ian-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-uskonnollisen-yhdyskunnan-sukupuolen-ja-ian-mukaan-2004-alkaen) | Population in Helsinki by religious affiliation, sex and age in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 355 | [`helsingin-vaesto-viisivuotisikaryhmittain-sivilisaadyn-ja-sukupuolen-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vaesto-viisivuotisikaryhmittain-sivilisaadyn-ja-sukupuolen-mukaan-2004-alkaen) | Population in Helsinki by age, marital status and sex in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 356 | [`helsingin-vapaa-aikakyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsingin-vapaa-aikakyselyn-vastaukset) | Helsingin vapaa-aikakyselyn 2018 vastaukset | statistics | skip | - | - | - | CSV/XLS | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 357 | [`helsingin-vtdinkielen-ja-imukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vtdinkielen-ja-imukaan-2004-alkaen) | Population in Helsinki by language and age in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 358 | [`helsingin-vtn-1-v-kumulatiivinen-ja-sukupuolen-mukaan-suurpiireitt-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vtn-1-v-kumulatiivinen-ja-sukupuolen-mukaan-suurpiireitt-2004-alkaen) | Population in Helsinki by age (1 year, cumulative), sex and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 359 | [`helsingin-vtn-ja-sukupuolen-mukaan-sekaisten-osuus-piireitt-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vtn-ja-sukupuolen-mukaan-sekaisten-osuus-piireitt-ja-osa-alueittain-2004-alkaen) | Population in Helsinki by age, sex and district and the share of women in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 360 | [`helsingin-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen) | Population in Helsinki by age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 361 | [`helsingin-vtueittain-1962-alkaen`](https://hri.fi/data/en_GB/dataset/helsingin-vtueittain-1962-alkaen) | Population in Helsinki by district in 1962-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 362 | [`helsingin-yleiskaava-2002`](https://hri.fi/data/en_GB/dataset/helsingin-yleiskaava-2002) | City of Helsinki Master Plan 2002 | imagery-or-3d | skip | - | - | - | WMS | not stated | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 363 | [`helsingin-yleiskartta`](https://hri.fi/data/en_GB/dataset/helsingin-yleiskartta) | General guide map of the City of Helsinki | imagery-or-3d | skip | - | - | - | TIFF/WMS | yearly | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 364 | [`helsinki-2050-kyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsinki-2050-kyselyn-vastaukset) | Helsinki 2050 survey results | entities | skip | - | - | - | CSV/KML/XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 365 | [`helsinki-region-infoshare-palvelun-kayttoa-koskevan-kyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/helsinki-region-infoshare-palvelun-kayttoa-koskevan-kyselyn-vastaukset) | Answers to the survey regarding the use of the Helsinki Region Infoshare service | statistics | skip | - | - | - | XLSX | every 2 years | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 366 | [`helsinkikanava-open-data`](https://hri.fi/data/en_GB/dataset/helsinkikanava-open-data) | Helsinki Channel open data | entities | skip | - | - | - | JSON | continuous | other-open | 403 | video catalogue; licence other-open, page answered 403 to the probe | - |
| 367 | [`hri-verkkopalvelun-avoimen-datan-metatiedot`](https://hri.fi/data/en_GB/dataset/hri-verkkopalvelun-avoimen-datan-metatiedot) | Metadata of HRI datasets | entities | skip | - | - | - | JSON | continuous | CC0-1.0 | 200 | catalogue metadata of HRI itself; this page is built from it | - |
| 368 | [`hsl-bluetooth-majakat-api`](https://hri.fi/data/en_GB/dataset/hsl-bluetooth-majakat-api) | HSL Beacon API | entities | skip | - | - | - | JSON | continuous | CC-BY-4.0 | 200 | last update 2019; beacon ids serve on-vehicle apps, no city entity | - |
| 369 | [`hsl-n-asiakastyytyvaisyystutkimus`](https://hri.fi/data/en_GB/dataset/hsl-n-asiakastyytyvaisyystutkimus) | Helsinki Region Transport (HSL) customer satisfaction survey | statistics | skip | - | - | - | CSV | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 370 | [`hsl-n-liityntapysakointipaikat`](https://hri.fi/data/en_GB/dataset/hsl-n-liityntapysakointipaikat) | Parking facilities near public transportation hubs in Helsinki Region | imagery-or-3d | skip | - | - | - | - | not stated | CC-BY-4.0 | 200 | replaced by Fintraffic LIIPI (package note), which the liipi-facilities seed reads (T-5259) | - |
| 371 | [`hsl-n-reittioppaan-kohdetietokanta`](https://hri.fi/data/en_GB/dataset/hsl-n-reittioppaan-kohdetietokanta) | Helsinki Region Transport destination database | entities | skip | - | - | - | CSV/GEOJSON/GEOSERVICE/KML/SHP | ended | CC-BY-4.0 | 200 | no longer updated (package note); service points come from the Service Map (T-5257) | - |
| 372 | [`hsl-reittiopas-api`](https://hri.fi/data/en_GB/dataset/hsl-reittiopas-api) | HSL Journey Planner API | entities | skip | - | - | - | XML | continuous | CC-BY-4.0 | 200 | routing query service; its data is the GTFS the seeds already read | - |
| 373 | [`hsln-lipunmyyntirajapinta`](https://hri.fi/data/en_GB/dataset/hsln-lipunmyyntirajapinta) | HSL OpenMaaS sales API | entities | skip | - | - | - | JSON | continuous | CC-BY-4.0 | 200 | ticket sales API: transactions, not open data | - |
| 374 | [`kiva-keskusta-kavelijoille-kyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/kiva-keskusta-kavelijoille-kyselyn-vastaukset) | Nice city centre for visitors -survey results | statistics | skip | - | - | - | XLSX | not stated | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 375 | [`miehet--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al`](https://hri.fi/data/en_GB/dataset/miehet--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al) | Men - Population and foreign people in Helsinki by citizenship, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 376 | [`miehet-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/miehet-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen) | Men in Helsinki by age (5-year) and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 377 | [`muu-vaesto-helsingissa-eli-henkilot-joiden-asuinaluetta-ei-ole-maaritelty-ian-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/muu-vaesto-helsingissa-eli-henkilot-joiden-asuinaluetta-ei-ole-maaritelty-ian-mukaan-2004-alkaen) | Other Population in Helsinki or people whose resindential area has not defined by age in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 378 | [`muu-vtlsingissli-henkiloiden-asuinaluetta-ei-ole-mitelty-sukupuolen-mukaan-2004-alkaen`](https://hri.fi/data/en_GB/dataset/muu-vtlsingissli-henkiloiden-asuinaluetta-ei-ole-mitelty-sukupuolen-mukaan-2004-alkaen) | Other Population in Helsinki or people whose resindential area has not defined by sex in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 379 | [`naiset--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al`](https://hri.fi/data/en_GB/dataset/naiset--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al) | Women - Population and foreign people in Helsinki by citizenship, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 380 | [`naiset-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/naiset-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen) | Women in Helsinki by age (5-year) and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 381 | [`paakaupunkiseudun-avoimen-datan-palvelun-kayttajakyselyn-vastaukset`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-avoimen-datan-palvelun-kayttajakyselyn-vastaukset) | User survey results of the open data service of Helsinki Metropolitan Area | statistics | skip | - | - | - | XLSX | yearly | CC-BY-4.0 | 200 | raw survey answers of one past questionnaire, not a city indicator | - |
| 382 | [`paakaupunkiseudun-liikennemeluvyohykkeet`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-liikennemeluvyohykkeet) | Traffic noise zones in Helsinki metropolitan area | entities | skip | - | - | - | SHP | not stated | CC-BY-4.0 | 200 | region copy of the Helsinki noise zones (hk meluselvitys 2017), SHP only | - |
| 383 | [`paakaupunkiseudun-opaskartta`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-opaskartta) | Guide Map of Helsinki Metropolitan Area | imagery-or-3d | skip | - | - | - | HTML/WMS | yearly | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 384 | [`paakaupunkiseudun-yleiskartta`](https://hri.fi/data/en_GB/dataset/paakaupunkiseudun-yleiskartta) | General guide map of the Helsinki Metropolitan Area | imagery-or-3d | skip | - | - | - | TIFF/WMS | yearly | CC-BY-4.0 | host timeout | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 385 | [`rajapinta-staran-lumiaurojen-sijantitietoihin`](https://hri.fi/data/en_GB/dataset/rajapinta-staran-lumiaurojen-sijantitietoihin) | Stara Snowplow API | entities | skip | - | - | - | XML | continuous | CC-BY-4.0 | unreachable | API out of service since 10/2024 (package note); recheck when HRI lifts the note | - |
| 386 | [`semantic-hri-fi--paakaupunkiseutua-koskevaa-tilastotietoa-avoimena-linkitettyna-datana`](https://hri.fi/data/en_GB/dataset/semantic-hri-fi--paakaupunkiseutua-koskevaa-tilastotietoa-avoimena-linkitettyna-datana) | semantic.hri.fi | statistics | skip | - | - | - | - | ended | CC-BY-4.0 | no resource URL | not maintained since 1/2015 (package note) | - |
| 387 | [`seudullinen-osoiteluettelo`](https://hri.fi/data/en_GB/dataset/seudullinen-osoiteluettelo) | Helsinki metropolitan area Address Catalogue | entities | skip | - | - | - | WFS/WMS | continuous | CC-BY-4.0 | host timeout | region copy of helsingin-osoiteluettelo for the Helsinki part | - |
| 388 | [`signe-branderin-panoraamakuvat-1900-luvun-alun-helsingista`](https://hri.fi/data/en_GB/dataset/signe-branderin-panoraamakuvat-1900-luvun-alun-helsingista) | Panoramic photos of Helsinki in the early 1900s by Signe Brander | imagery-or-3d | skip | - | - | - | TIFF | not stated | CC-BY-4.0 | 200 | raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue | - |
| 389 | [`staran-tuotantoajoneuvojen-liikkeet-ja-toimenpiteet-helsingissa`](https://hri.fi/data/en_GB/dataset/staran-tuotantoajoneuvojen-liikkeet-ja-toimenpiteet-helsingissa) | Stara's urban environment departments maintenance fleet movements and actions in eastern Helsinki 2021/01 | entities | skip | - | - | - | GEOJSON/JSON | not stated | CC-BY-4.0 | unreachable | API not public (package note); only a 2021/01 sample | - |
| 390 | [`tietoa-suomesta-monella-eri-kielella`](https://hri.fi/data/en_GB/dataset/tietoa-suomesta-monella-eri-kielella) | Information about Finland in many languages | statistics | skip | - | - | - | - | not stated | CC-BY-4.0 | no resource URL | API withdrawn 1/2026 (package note) | - |
| 391 | [`ulkomaan-kansalaiset-helsingissa-kansalaisuuden-seka-syntymaalueen-ja-sukupuolen-mukaan-2017-alkaen`](https://hri.fi/data/en_GB/dataset/ulkomaan-kansalaiset-helsingissa-kansalaisuuden-seka-syntymaalueen-ja-sukupuolen-mukaan-2017-alkaen) | Foreign citizens in Helsinki in 2017-2023 according to nationality, birth area and gender | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 392 | [`uudenmaan-osoiterajapinta`](https://hri.fi/data/en_GB/dataset/uudenmaan-osoiterajapinta) | Address API of Uusimaa | entities | skip | - | - | - | JSON/XML | continuous | CC-BY-4.0 | 403 | address lookup service (answered 403 to the probe); T-5256 takes addresses from helsingin-osoiteluettelo | - |
| 393 | [`vaestonmuutokset-helsingissa-piireittain-ja-osa-alueittain-2004-alkaen`](https://hri.fi/data/en_GB/dataset/vaestonmuutokset-helsingissa-piireittain-ja-osa-alueittain-2004-alkaen) | Population changes in Helsinki by district in 2003-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |
| 394 | [`vantaan-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`](https://hri.fi/data/en_GB/dataset/vantaan-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005) | Dwelling-unit income, gini coefficients by consumption unit in Vantaa 2005-2019 | statistics | skip | - | - | - | PXWEB | ended | CC-BY-4.0 | 200 | City of Vantaa only, outside the helsinki space | - |
| 395 | [`vantaan-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`](https://hri.fi/data/en_GB/dataset/vantaan-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015) | Preliminary population of Vantaa by age group and area 31.12.2015–2023 | statistics | skip | - | - | - | PXWEB | quarterly | CC-BY-4.0 | 200 | City of Vantaa only, outside the helsinki space | - |
| 396 | [`yksinasuvat-yhden-hengen-asuntokunnat-helsingissukupuolen-ja-imukaan-peruspiireitt-2004-alkaen`](https://hri.fi/data/en_GB/dataset/yksinasuvat-yhden-hengen-asuntokunnat-helsingissukupuolen-ja-imukaan-peruspiireitt-2004-alkaen) | One person househoulds in Helsinki by sex, age and district in 2004-2023 | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note) | - |

### 6.3 Statistics as built (T-5258)

The `statistics` pipeline of the helsinki project reads 211 tables of four stat.hel.fi PXWEB
databases, one call a second, and writes one `KeyPerformanceIndicator` per indicator and area
with the newest ended period as the value (about 14,000 indicators on 2026-10-23):

| database | tables | areas | theme Endpoints |
|---|---|---|---|
| Aluesarjat | 62 | sub-districts for 16 series; the other 46 stop at the basic or major districts, or keep the Helsinki row of a region table | population, housing, employment, income, education |
| Hyvinvointitilastot | 71 | basic districts where the table has an area, else the city | welfare |
| Ymparistotilasto | 77 | the city | environment |
| SDG | 1 (123 indicators) | the city | environment |

The `service-usage` pipeline adds Korkeasaari zoo's visitors per day and month and the visits and
page views per city website and month (theme services).

A region table whose Helsinki row repeats another table is skipped as a duplicate only after its
city values were compared with every built table on 2026-10-23 (all equal). Two random indicators
per new Aluesarjat table and one per welfare, environment and SDG table were compared with a
single-cell query of the source: 241 of 241 equal (evidence/T-5258/human-read-rework.tsv on the
task board).

## 7. Nothing left: what is skipped and why

- `a01hki_astuot_tp_hper_rahoitus_talotyyppi`: archive: `alu_astuo_009r` holds periods before 2000 only, no new periods.
- `aarteeni-helsingissa-kyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `aluesarjat-hginseutu-ar-aa01-asuntokanta-rvuosi-talotyyppi`: duplicate: its Helsinki row equals `alu_askan_005q` (built, by area), every city value equal on 2026-10-23.
- `aluesarjat-hginseutu-va-ve02-vaestoennuste-kehys`: projection, not an observation (`alu_vaenn_006q`; the observed population is `alu_vaerak_004r`).
- `aluesarjat-hginseutu-va-ve03-vaestoennuste-kieli`: projection, not an observation (`alu_vaenn_010c`; the observed population is `alu_vaerak_004r`).
- `aluesarjat-hginseutu-va-vr03-vakiluku-ika-sukup-aidinkieli3-ssaaty`: duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23.
- `aluesarjat_a01hki_asunto_ohjelma`: projection, not an observation (`alu_asohj_006b`; the observed population is `alu_vaerak_004r`).
- `aluesarjat_a01hki_asuntokuntien_tulot`: archive or historical series, no new periods.
- `aluesarjat_a01hki_raktuot_kayttotark_2003-`: archive: `alu_ratuo_009u` holds periods before 2000 only, no new periods.
- `aluesarjat_hginseutu_tt_tm02_paa_as_toiminta`: duplicate: its Helsinki row equals `alu_tyom_003v` (built), every value equal on 2026-10-23.
- `aluesarjat_hginseutu_va_pe02_lapsiperheet_lapsiluku`: duplicate: its Helsinki row equals `alu_perh_007h` (built, by area), every value equal on 2026-10-23.
- `aluesarjat_hginseutu_va_vm04_syntyneet`: duplicate: its Helsinki row equals `alu_vamuu_010t` (built), every value equal on 2026-10-23.
- `aluesarjat_hginseutu_va_vr01_vakiluku_ika`: duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23.
- `aluesarjat_hginseutu_va_vr02_vakiluku_aidinkieli3`: duplicate: its Helsinki row equals `alu_vaerak_004s` (built), every value equal on 2026-10-23.
- `aluesarjat_hginseutu_va_vr04_vakiluku_aidinkieli_ika`: duplicate: its one Helsinki value is the city total of `alu_vaerak_004r` (built).
- `aluesarjat_hginseutu_va_vr05_vakiluku_kansalaisuus_s`: duplicate: its Helsinki row equals `alu_vaerak_004q` (built, by area), every city value equal on 2026-10-23.
- `asunnontarkastuksen-toimenpidepyynnot-helsingissa`: series ended (package update: finished); last file 2024-05.
- `eduskuntavaalit-helsingissa-2011`: one past election (2011), no series; national results are Statistics Finland's.
- `eduskuntavaalit-helsingissa-2015`: one past election (2015), no series (package update: ended).
- `elinkustannusindeksi-ja-rahanarvonkerroin-keskimaaraisten-kuukausivuokrien-deflatoimiseksi`: archive: `his_asolo_022s` holds periods before 2000 only, no new periods.
- `elintarvikevalvonnan-piiriin-kuuluvat-elintarvikehuoneistot-helsingissa`: not maintained since 1/2019; the national VATI register replaced it (package note).
- `espoon-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`: City of Espoo only, outside the helsinki space.
- `espoon-kaupungin-resurssienvarausrajapinta`: City of Espoo resources, outside the helsinki space.
- `espoon-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`: City of Espoo only, outside the helsinki space.
- `etelasatama-virtual-3d-malli`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helmet-kirjastojen-aineistoluettelot`: bibliographic records; libraries come from the Service Map (T-5257).
- `helmet-kirjastojen-lainatuimmat-aikuistenkirjat`: ranking of book titles, no city indicator.
- `helmet-kirjastojen-lainatuimmat-lastenkirjat`: ranking of book titles, no city indicator.
- `helmet-kirjastojen-varatuimmat-kirjat`: ranking of book titles, no city indicator.
- `helsingin-3d-kaupunkimalli`: CityGML/mesh 3D model; buildings come from helsingin-rakennukset (T-5256), the model stays a catalogue link.
- `helsingin-3d-rakennukset`: KML/SKP 3D buildings; same buildings as helsingin-rakennukset.
- `helsingin-ajantasa-asemakaava`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-asemakaavakartat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1900`: archive: `his_asolo_022r` holds periods before 2000 only, no new periods.
- `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1932-1974`: archive: `his_asolo_022p` holds periods before 2000 only, no new periods.
- `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1975-1980`: archive: `his_asolo_022q` holds periods before 2000 only, no new periods.
- `helsingin-asuinhuoneistot-asuntovaesto-ja-asumistiheys-huoneluvun-mukaan-1870-1998`: archive: `his_askun_022m` holds periods before 2000 only, no new periods.
- `helsingin-asuntokunnat-henkilun-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-asuntokunnat-koon-ja-vanhimman-henkilon-ian-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`: archive or historical series, no new periods.
- `helsingin-asuntotuotanto-aloitetut-rakennushankkeet-2015`: duplicate: the yearly sum of the quarterly `alu_astuo_039g` (built).
- `helsingin-asuntotuotanto-keskeneraiset-rakennushankkeet-2015`: duplicate: the year-end value of the quarterly `alu_astuo_039h` (built).
- `helsingin-asuntotuotanto-myonnetyt-rakennusluvat-2015`: duplicate: the yearly sum of the quarterly `alu_astuo_039f` (built).
- `helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-2015`: duplicate: the yearly sum of the quarterly `alu_astuo_039i` (built).
- `helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-rahoitus-hallintaperuste-ja-rakennuttaja-2015`: duplicate: the yearly sum of the quarterly `alu_astuo_039j` (built).
- `helsingin-ensimmaisen-maailmansodan-aikaiset-maalinnoitukset`: WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host).
- `helsingin-erilaisilla-mukavuuslaitoksilla-varustetut-huoneistot-kaupunginosittain-1920`: archive: `his_asolo_022o` holds periods before 2000 only, no new periods.
- `helsingin-erisuuruisissa-huoneistoissa-asuvat-henkilot-kaupunginosittain-8-12-1920`: archive: `his_askun_022n` holds periods before 2000 only, no new periods.
- `helsingin-espoon-ja-vantaan-liikennevaloristeykset`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-henkikirjoitettu-vaesto-kaupunginosittain-1-1-1875-1960`: archive: `his_vaerak_023o` holds periods before 2000 only, no new periods.
- `helsingin-historialliset-asemakaavakartat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-historialliset-kartat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-historialliset-opaskartat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-historialliset-tilastot`: archive: historical series from 1811 that end in the 2000s, no new periods.
- `helsingin-historialliset-yleiskaavat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-ja-vantaan-ymparistoasennekyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-johtamisen-uudistaminen-verkkokyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-kansallinen-kaupunkipuisto-kyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-kantakartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-katujen-puhdistussuunnitelmat`: service unavailable since 1/2026 (package note).
- `helsingin-kaupungin-avustukset`: a ledger of grants to named recipients, no indicator per period and area (score -1: grant ledger).
- `helsingin-kaupungin-chatbotien-koulutusdatat`: chatbot training text, no city entity.
- `helsingin-kaupungin-henkilosto-1914-1998`: archive: `his_tyov_023k` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-henkiloston-koulutukset`: a ledger of courses for city staff, no city indicator.
- `helsingin-kaupungin-kansakoulujen-luokat-lukuvuosina-1896-97-1976-77`: archive: `his_kansk_022y` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-kansakoulujen-opettajat-lukuvuosina-1896-97-1976-77`: archive: `his_kansk_022z` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-kansakoulujen-oppilaat-lukuvuosina-1896-97-1976-77`: archive: `his_kansk_023a` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-kansakoulujen-oppilaiden-vanhempien-tausta-lukuvuosina-1896-97-1968-69`: archive: `his_kansk_023b` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-koulurekisteri`: API removed 1/2026 (package note).
- `helsingin-kaupungin-nuorisoasiainkeskuksen-avustukset`: a ledger of subsidies to named youth associations, no indicator per period and area (grant ledger).
- `helsingin-kaupungin-ostot`: a ledger of purchase invoices per supplier, no indicator per period and area (invoice ledger).
- `helsingin-kaupungin-palvelurekisterin-rest-rajapinta`: same units as the Service Map API (tprek ids) that T-5257 integrates; one source per object, no duplicate PointOfInterest.
- `helsingin-kaupungin-peruskoulujen-kielivalinnat`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2024-12.
- `helsingin-kaupungin-resurssienvarausrajapinta`: API not in use since 12/2024 (package note).
- `helsingin-kaupungin-talousarviotiedot`: a budget table per account, no indicator per period and area (budget table).
- `helsingin-kaupungin-taloushallintopalvelun-tulot-ja-menot`: resource unreachable on 2026-10-22; recheck in T-5258.
- `helsingin-kaupungin-talvihoidon-kayttajatyytyvaisyyskyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-kaupungin-tarkastuslautakunnan-arviointikertomuksissa-esitetyt-suositukset`: audit recommendations as text, no entity or indicator.
- `helsingin-kaupungin-tulot-ja-menot`: income and expenditure per account, no indicator per period and area (budget table).
- `helsingin-kaupungin-tyonvalitystoiminta-1903-1960`: archive: `his_tyom_023e` holds periods before 2000 only, no new periods.
- `helsingin-kaupungin-ymparistoraportti`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; its emission and energy figures are the Ymparistotilasto tables `ymp_kaspa_003k` and `ymp_eneku_002z` (built).
- `helsingin-kaupungin-ymparistotilinpito`: duplicate: the environmental accounts are `ymp_tunlu_037j` of Ymparistotilasto (built).
- `helsingin-kaupungin-yrityshaastattelututkimus`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-kaupunginarkiston-aineistot`: archive media catalogue (documents, photos); answered 403 to the probe.
- `helsingin-kaupunginkirjaston-kaynnit-toimipisteittain`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `helsingin-kaupunginkirjaston-lainausmaarat-1860`: archive: loans 1860-2020, series ended.
- `helsingin-kaupunginkirjaston-lainausmaarat-toimipisteittain`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `helsingin-kaupunginkirjastossa-kirjastokorttiaan-k-ytt-neet`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `helsingin-kaupunginmuseon-aineistot`: museum media catalogue (Finna); answered 403 to the probe.
- `helsingin-kaupunginorkesterin-konsertit`: archive of past concerts, one row per work performed (61,267 rows, 1882 to 28.05.2026, checked 2026-10-23); no upcoming concert, so no live Event; archives score down (owner 18:25Z).
- `helsingin-keskivakiluku-ian-ja-sukupuolen-mukaan-1935-1961`: archive: `his_vaerak_023l` holds periods before 2000 only, no new periods.
- `helsingin-kiinteistokartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-koko-vt-ulkomaalaistaustaiset-maan-ja-imukaan-suurpiireitt-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-koko-vtkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-korkeusmalli`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-kulttuurihistoriallisesti-merkittavat-porrashuoneet`: one-off 2014 inventory (zip of one XLSX, 349 staircases, checked 2026-10-23) of stairwells inside residential buildings, by property id and street address only, no coordinates and no update since.
- `helsingin-kulttuurikeskuksen-avustukset`: a ledger of grants to named arts groups, no indicator per period and area (grant ledger).
- `helsingin-kuvakartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-lammitettavat-rakennukset-rakennusaineen-ja-kerrosluvun-mukaan-1880-1930`: archive: `his_rakan_022h` holds periods before 2000 only, no new periods.
- `helsingin-laserkeilausaineistot`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-liikenneturvallisuuskysely-asukkaille`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-lukioiden-sis-np-syrajat`: stale: a yearly package with no file since 2023-08, older than three update periods.
- `helsingin-lukioiden-yhteishaun-tulokset`: stale: a yearly package with no file since 2023-08, older than three update periods.
- `helsingin-luontopalvelulinjauksen-asukaskyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-mikroilmaston-simulaatiodemo`: one-off 2023 simulation demo: modelled output, not an observation, never updated.
- `helsingin-muu-kuin-suomen-ja-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-muun-kuin-suomen-tai-ruotsinkielinen-vtn-ja-sukupuolen-mukaan-suurpiireitt-2004-alkae`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-nuoret-alueittain`: one past edition (2023-01), no series; the young population by basic district is `hyv_alue_006g` (built).
- `helsingin-opaskartta`: cartographic guide map layers (labels, symbols) over data integrated elsewhere.
- `helsingin-oppikoulujen-1-ja-2-luokalle-otetut-oppilaat-lukuvuosina-1925-26-1960-61`: archive: `his_oppik_023d` holds periods before 2000 only, no new periods.
- `helsingin-oppikoulut-lukuvuosina-1894-95-1976-77`: archive: `his_oppik_023c` holds periods before 2000 only, no new periods.
- `helsingin-ortoilmakuvat`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-osallistuvan-budjetoinnin-aanestystulokset`: votes per proposal of each participatory budgeting round, no period series.
- `helsingin-paivahoitotilastot`: not maintained; superseded by the six-cities early education comparison (package note).
- `helsingin-perheet-ja-lapset-sekterherakennetta-kuvaavia-tunnuslukuja-piireitt-ja-osa-alueittain`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-perus-ja-2-asteen-opetuksen-oppilasmaarat-kouluittain`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2024-11.
- `helsingin-pintamalli`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-pyorailybarometrikyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-pyoravaylien-ongelmakohdekyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-raide-jokerin-linjaus-ja-pysakit`: duplicate: line 15 and its stops are in the HSL GTFS seeds.
- `helsingin-rakennetut-kiinteistot-ja-lammitettavat-rakennukset-kaupunginosittain-1900-1950`: archive: `his_rakan_022j` holds periods before 2000 only, no new periods.
- `helsingin-rakennetut-kiinteistot-seka-lammitettavat-rakennukset-ja-huoneet-kaupunginosittain-1870`: archive: `his_rakan_022i` holds periods before 2000 only, no new periods.
- `helsingin-rakennustuotanto-aloitetut-rakennushankkeet-2015`: duplicate: the yearly sum of the quarterly `alu_ratuo_039l` (built).
- `helsingin-rakennustuotanto-keskeneraiset-rakennushankkeet-2015`: duplicate: the year-end value of the quarterly `alu_ratuo_039m` (built).
- `helsingin-rakennustuotanto-myonnetyt-rakennusluvat-2015`: duplicate: the yearly sum of the quarterly `alu_ratuo_039k` (built).
- `helsingin-rakennustuotanto-valmistuneet-rakennushankkeet-2015`: duplicate: the yearly sum of the quarterly `alu_ratuo_039n` (built).
- `helsingin-rinnevarjosteet`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-ruotsinkielinen-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-ruotsinkielinen-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-seudun-aluesarjat-tilastotietokannan-tiedot-paikkatietona`: duplicate: the WFS key-figure layer republishes Aluesarjat figures by sub-district that the statistics pipeline reads at the source (`alu_vaerak_004r`, `alu_askan_005r`); the sub-district geometry is the districts seed.
- `helsingin-seudun-sairastavuusindeksi`: duplicate: the morbidity index by basic district is `hyv_teel_038k` of the welfare database (built).
- `helsingin-seudun-tyopaikat-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008`: duplicate: its Helsinki row equals `alu_tyop_004a` (built), every value equal on 2026-10-23.
- `helsingin-seudun-v-est-1-1-1980-2013-sek-ennuste-1-1-2014-2050`: projection, not an observation (`alu_vaenn_006e`; the observed population is `alu_vaerak_004r`).
- `helsingin-seudun-vaesto-aidinkielen-mukaan`: duplicate: its Helsinki row equals `alu_vaerak_004s` (built), every value equal on 2026-10-23.
- `helsingin-sosiaalitoimen-suoritetietoja`: series ended (package update: ended); last file 2023-05.
- `helsingin-suomenkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-taidemuseon-nayttelyt`: archive of past HAM exhibitions (1,139 rows, newest start 2022-09-09, checked 2026-10-23) in one XLSX; no upcoming exhibition, so no live Event; archives score down (owner 18:25Z).
- `helsingin-taidemuseon-prosenttirahahankkeet`: only resource is an Excel 97 .xls (BIFF8, saved 2025-09-16, checked 2026-10-23) listing works by artist and title with a building address and no coordinates; no seed pipeline reads Excel, and placing a work needs per-work geocoding the file does not support.
- `helsingin-tilastollinen-vuosikirja`: a yearbook compiled from the Aluesarjat and welfare tables built above; XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API.
- `helsingin-tulo-ja-lahtomuutto-laaneittain-1911-1994`: archive: `his_vamuu_023q` holds periods before 2000 only, no new periods.
- `helsingin-tuulivoimakysely-2015`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-tyovaeston-asunto-olot-vuonna-1900-asuntojen-varustelutaso`: archive: `his_asolotut_022x` holds periods before 2000 only, no new periods.
- `helsingin-tyovaeston-asunto-olot-vuonna-1900-terveydelliset-olot`: archive: `his_asolotut_022w` holds periods before 2000 only, no new periods.
- `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asukkaiden-lukumaarasta`: archive: `his_asolotut_022v` holds periods before 2000 only, no new periods.
- `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asuntojen-lukumaarasta`: archive: `his_asolotut_022v` holds periods before 2000 only, no new periods.
- `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-huoneiden-lukumaarasta`: archive: `his_asolotut_022u` holds periods before 2000 only, no new periods.
- `helsingin-ulkoliikuntapaikkojen-laitteiden-kayttoasteet`: source stopped 2025-03-10 (last reading of every gym device); a one-off history of a closed series, checked by T-5255.
- `helsingin-ulkomaalaistaustainen-vaesto-sukupuolen-ja-taustamaan-mukaan-2017-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-aidinkielen-ja-ian-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-elinkeinoryhmittain-1870-1930`: archive: `his_tyov_023i` holds periods before 2000 only, no new periods.
- `helsingin-vaesto-ian-1-v-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-ian-5-v-aidinkielen-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-ja-asuntotuotantoennuste-alueittain`: projection, not an observation (the observed population is `alu_vaerak_004r`).
- `helsingin-vaesto-ja-ruotsinkieliset-1-1-1992-alkaen-seka-vaestoennuste-alueittain`: projection, not an observation (`alu_vaenn_006c`; the observed population is `alu_vaerak_004r`).
- `helsingin-vaesto-piireittain-ja-osa-alueittain-ian-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-sukupuolen-ja-sivilisaadyn-mukaan-2004-alkaen-piireittain-ja-osa-alueittain`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-syntymapaikan-sukupuolen-ja-ian-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-uskonnollisen-yhdyskunnan-sukupuolen-ja-ian-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaesto-viisivuotisikaryhmittain-sivilisaadyn-ja-sukupuolen-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vaeston-ammatissa-toimivuus-1870-1930`: archive: `his_tyov_023j` holds periods before 2000 only, no new periods.
- `helsingin-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`: archive or historical series, no new periods.
- `helsingin-vakiluku-1-1-1875-1993-ja-vuodenvaihteissa-1993-94-2013-14`: archive: `his_vaerak_023o` holds periods before 2000 only, no new periods.
- `helsingin-vakiluku-ian-ja-sukupuolen-mukaan-1900-1961`: archive: `his_vaerak_023n` holds periods before 2000 only, no new periods.
- `helsingin-vanhojen-asunto-osakehuoneistojen-neliohinnat-postinumeroalueittain-vuodesta-2000`: series ended (package update: ended); last file 2024-05.
- `helsingin-vapaa-aikakyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsingin-vtdinkielen-ja-imukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vtn-1-v-kumulatiivinen-ja-sukupuolen-mukaan-suurpiireitt-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vtn-ja-sukupuolen-mukaan-sekaisten-osuus-piireitt-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-vtueittain-1962-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `helsingin-yleiskaava-2002`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin-yleiskartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `helsingin_maisemakulttuurikartta`: WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host).
- `helsingissa-asuva-tyollinen-tyovoima-toimialan-tol-2008-mukaan`: duplicate: its totals by area are `alu_tyov_004d` (built) one year older (2023), its industry breakdown of the city is `alu_tyov_004g` (built).
- `helsinki-2050-kyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsinki-alueittain`: series ended (package update: ended); the district profiles repeat Aluesarjat tables built above.
- `helsinki-region-infoshare-palvelun-kayttoa-koskevan-kyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `helsinki-s-2030-climate-technologies-city-performance-tool-2016`: one modelling run of 2016, no series.
- `helsinki-turvattomuutta-kokevien-osuudet-peruspiireitt-2003-2006-ja-2009`: three past surveys (2003, 2006, 2009), series ended.
- `helsinkiin-ja-helsingista-muuttaneet-sukupuolen-mukaan-1881-1998`: archive: `his_vamuu_023p` holds periods before 2000 only, no new periods.
- `helsinkikanava-open-data`: video catalogue; licence other-open, page answered 403 to the probe.
- `hri-verkkopalvelun-avoimen-datan-metatiedot`: catalogue metadata of HRI itself; this page is built from it.
- `hsl-bluetooth-majakat-api`: last update 2019; beacon ids serve on-vehicle apps, no city entity.
- `hsl-n-asiakastyytyvaisyystutkimus`: raw survey answers of one past questionnaire, not a city indicator.
- `hsl-n-joukkoliikenteen-pysakit`: duplicate: the transit-stops GTFS seed already writes every HSL stop (GtfsStop by stop_id).
- `hsl-n-joukkoliikenteen-risteyssolmut`: HSL's planning network graph (16 724 nodes), nothing a passenger sees.
- `hsl-n-liityntapysakointipaikat`: replaced by Fintraffic LIIPI (package note), which the liipi-facilities seed reads (T-5259).
- `hsl-n-linjat`: duplicate: the transit-routes and gtfs-shapes GTFS seeds already write the lines and their geometry.
- `hsl-n-pysakit-linjoittain`: duplicate: the stop sequence per line is GTFS stop_times, which transit-routes and transit-stops already read.
- `hsl-n-reittioppaan-kohdetietokanta`: no longer updated (package note); service points come from the Service Map (T-5257).
- `hsl-n-terminaalit`: duplicate: TERMINAALI is the GTFS stop_id of a GtfsStation that transit-stops writes (Kamppi 1000001).
- `hsl-n-vuoromaarat`: HSL's planning network graph (8 067 links with departure counts), nothing a passenger sees.
- `hsl-reittiopas-api`: routing query service; its data is the GTFS the seeds already read.
- `hsln-lipunmyyntirajapinta`: ticket sales API: transactions, not open data.
- `ikaryhmittaiset-hedelmallisyysluvut-helsingissa-1936-2013`: archive: `his_vamuu_023y` holds periods before 2000 only, no new periods.
- `iot-meludataa-helsingista`: Forum Virium's noise project is end-of-life (README of ForumViriumHelsinki/OpenDataSamples/Noise); the HRI resource is a GitHub folder holding only a notebook, and its static files at iot.fvh.fi/downloads/noise/ answered 404 on 2026-10-23.
- `jalankulkijoiden-liukastumisvaroitukset-helsingissa`: liukasbotti.fi/api/warnings holds 3 rows in total, the newest real one 28.02.2026, two of them test rows, no geometry and only 'Helsinki' as area: nothing an Alert could locate.
- `kirjastokaynnit-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `kirjojen-lainaus-kielittain-helsingin-kaupunginkirjastossa`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `kiva-keskusta-kavelijoille-kyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `kokonaishedelmallisyysluku-ja-yleinen-hedelmallisyysluku-helsingissa-1936-2013`: archive: `his_vamuu_023z` holds periods before 2000 only, no new periods.
- `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1891-1950`: archive: `his_vamuu_023u` holds periods before 2000 only, no new periods.
- `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1951-1968`: archive: `his_vamuu_023v` holds periods before 2000 only, no new periods.
- `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1969-1985`: archive: `his_vamuu_023w` holds periods before 2000 only, no new periods.
- `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1988-1995`: archive: `his_vamuu_023x` holds periods before 2000 only, no new periods.
- `kuuden-suurimman-kaupungin-kehitysvammahuollon-vertailu`: series ended (package update: ended); last file 2024-05.
- `kuuden-suurimman-kaupungin-lastensuojelun-vertailu`: series ended (package update: ended); last file 2023-10.
- `kuuden-suurimman-kaupungin-paihde-ja-mielenterveyspalvelujen-vertailu`: series ended (package update: ended); last file 2023-10.
- `kuuden-suurimman-kaupungin-toimeentulotuen-vertailu`: series ended (package update: ended); last file 2023-10.
- `kuuden-suurimman-kaupungin-vammaispalvelujen-vertailu`: series ended (package update: ended); last file 2023-10.
- `kuuden-suurimman-kaupungin-vanhustenpalvelujen-vertailu`: series ended (package update: ended); last file 2023-10.
- `kuuden-suurimman-kaupungin-varhaiskasvatuspalvelujen-vertailu`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2025-12.
- `lainaus-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-06.
- `miehet--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `miehet-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `muu-vaesto-helsingissa-eli-henkilot-joiden-asuinaluetta-ei-ole-maaritelty-ian-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `muu-vtlsingissli-henkiloiden-asuinaluetta-ei-ole-mitelty-sukupuolen-mukaan-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `naiset--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `naiset-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `naiset-ja-miehet-helsingissa`: series ended (package update: ended); last file 2023-03.
- `naisten-ja-miesten-taydellinen-elinajantaulu-km-jaljella-oleva-elinaika-helsingissa-1941-2005`: archive: `his_vamuu_023s` holds periods before 2000 only, no new periods.
- `nordstat-tilastoja-pohjoismaiden-suurimmista-kaupungeista-ja-kaupunkiseuduista`: duplicate: Helsinki's rows are the Aluesarjat figures built above (population 2024: 684,018 in `nor_popu_008b` and `alu_vaerak_004r`); the other Nordic cities are outside the helsinki space.
- `paakaupunkiseudun-autonomistajuustiedot`: XLS/XLSX only: the pipeline runner (Bento) has no spreadsheet reader and the package offers no CSV, JSON or API; last file 2026-09.
- `paakaupunkiseudun-avoimen-datan-palvelun-kayttajakyselyn-vastaukset`: raw survey answers of one past questionnaire, not a city indicator.
- `paakaupunkiseudun-liikennemeluvyohykkeet`: region copy of the Helsinki noise zones (hk meluselvitys 2017), SHP only.
- `paakaupunkiseudun-opaskartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `paakaupunkiseudun-vaestoennuste`: projection, not an observation (the observed population is `alu_vaerak_004r`).
- `paakaupunkiseudun-yleiskartta`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `paikalliset-ja-muualle-ulottuvat-tyonseisaukset-helsingissa-1907-1951`: archive: `his_tyom_023f` holds periods before 2000 only, no new periods.
- `paikalliset-tyonseisaukset-1954-1970-ja-tyotaistelut-helsingissa-1971-1997`: archive: `his_tyom_023g` holds periods before 2000 only, no new periods.
- `pks-kuntien-taloudellisia-tunnuslukuja`: series ended (package update: ended); last file 2024-05.
- `rajapinta-paakaupunkiseudun-kansalais-ja-tyovaenopistojen-kurssitietoihin`: the Ilmoapix API (api.ilmonet.fi) needs an API key issued by Grynos Oy in every request; the platform creates no account (supervisor rule); Linked Courses (api.hel.fi/linkedcourses) answers 301 to dev.hel.fi, retired.
- `rajapinta-staran-lumiaurojen-sijantitietoihin`: API out of service since 10/2024 (package note); recheck when HRI lifts the note.
- `semantic-hri-fi--paakaupunkiseutua-koskevaa-tilastotietoa-avoimena-linkitettyna-datana`: not maintained since 1/2015 (package note).
- `seudullinen-osoiteluettelo`: region copy of helsingin-osoiteluettelo for the Helsinki part.
- `signe-branderin-panoraamakuvat-1900-luvun-alun-helsingista`: raster or 3D imagery (TIFF/WMS/WMTS/WCS/LAZ/DWG/SKP), no features to map; a WMS/WMTS can serve as a basemap link in the catalogue.
- `solmitut-ja-purkautuneet-avioliitot-helsingissa-1896-1998`: archive: `his_vamuu_023t` holds periods before 2000 only, no new periods.
- `staran-tuotantoajoneuvojen-liikkeet-ja-toimenpiteet-helsingissa`: API not public (package note); only a 2021/01 sample.
- `suomenlinnan-lautan-matkustajamaarat`: the LATI API answers only with an access key (LWSAccessKey); a key goes in a secretRef only the owner creates, so no anonymous read exists.
- `syntyneet-ja-kuolleet-helsingissa-1811-1998`: archive: `his_vamuu_023r` holds periods before 2000 only, no new periods.
- `teollisuuden-tyopaikat-ja-tyontekijat-helsingissa-1884-1965`: archive: `his_tyop_023h` holds periods before 2000 only, no new periods.
- `tietoa-suomesta-monella-eri-kielella`: API withdrawn 1/2026 (package note).
- `ulkomaan-kansalaiset-helsingissa-kansalaisuuden-seka-syntymaalueen-ja-sukupuolen-mukaan-2017-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `uudenmaan-kuntien-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995`: archive or historical series, no new periods.
- `uudenmaan-kuntien-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995`: archive or historical series, no new periods.
- `uudenmaan-kuntien-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`: archive or historical series, no new periods.
- `uudenmaan-osoiterajapinta`: address lookup service (answered 403 to the probe); T-5256 takes addresses from helsingin-osoiteluettelo.
- `uudenmaan-seudullinen-tyopaikkaprojektio-1980-2060`: projection, not an observation (`alu_typroj_003i`; the observed population is `alu_vaerak_004r`).
- `uudenmaan-tyopaikkaprojektioissa-kaytetyt-vaestoprojektiot`: projection, not an observation (`alu_typroj_004c`; the observed population is `alu_vaerak_004r`).
- `uusien-toimintojen-paikat-helsingin-rantareitilla`: WFS layer only; kartta.hel.fi accepted no connection from the build sandbox on 2026-10-22 and again on 2026-10-23T05:22Z (20 s timeout), so no fixture can be recorded and no pipeline tested; re-admit with a fixture recorded on dev (dev reaches the host).
- `vaestonmuutokset-helsingissa-piireittain-ja-osa-alueittain-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).
- `valmistuneet-asuinhuoneet-kivi-ja-puutaloissa-helsingissa-1939-1950`: archive: `his_raken_022l` holds periods before 2000 only, no new periods.
- `valmistuneet-asuinhuoneistot-helsingissa-1921-1967`: archive: `his_raken_022k` holds periods before 2000 only, no new periods.
- `vantaan-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005`: City of Vantaa only, outside the helsinki space.
- `vantaan-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015`: City of Vantaa only, outside the helsinki space.
- `yksinasuvat-yhden-hengen-asuntokunnat-helsingissukupuolen-ja-imukaan-peruspiireitt-2004-alkaen`: Excel copy ended in 2023; the same series is in Aluesarjat PXWEB (T-5258) (package note).

## 8. Provenance

- Snapshot: `evidence/supervisor-2026-10-22-hri-inventory/helsinki-datasets.tsv` on the swarm board,
  copied to `Research/data/helsinki-hri-snapshot-2026-10-22.tsv`.
- Package records: `https://hri.fi/data/api/3/action/package_show?id=<name>`, all 396 read on
  2026-10-22 between 18:03Z and 18:10Z.
- Smart Data Models: the GitHub API listing of each subject repository at the commit in section 3.
- Existing helsinki sources: `components/context-gateway/seed/helsinki/` in the deployment repository
  at main `45d5718`.
- `scripts/check-helsinki-open-data.py check` proves the counts: 396 rows, every name in the
  snapshot, every integrate or statistics row with a batch and a model, every skip in section 7,
  and the section 9 re-score against the counts of sections 9.3 and 10.
- Re-score (T-5663): HRI `package_search` and `package_show` and one probe per resource on
  2026-10-25T14:50Z; the dev Endpoints' `/types`, counts and id prefixes at
  `https://api.dev.joinedcontext.com/api/endpoint/<slug>/ngsi-ld/v1/` at the same time; the
  Endpoint seeds at deployment main `691f99b`.

## 9. Re-score of 2026-10-25

The owner order of 2026-10-25T14:20Z asks for every usable Helsinki dataset on its NGSI-LD Endpoints,
at least 100, and nothing that is not usable (T-5663). This section re-scores all 396 rows of
section 6 against the portal and the dev cluster of 2026-10-25. Where it differs from section 6, this
section holds; the batch task that builds a row updates its section 6 row.

### 9.1 Rule set

A row is **usable** (`yes`) when all of these hold:

- a machine-readable download or API: CSV, JSON, GeoJSON, WFS, GTFS, PXWEB or another API;
- it answers today (from the dev cluster where the sandbox cannot reach the host, section 9.2);
- it is updated within its stated period, or it is a static reference set;
- an open licence and nothing behind a login or an issued key;
- at least one row inside the city's box;
- not a duplicate or a subset of another row or of a seeded source.

Every other row gets one reason word:

| reason | meaning |
|---|---|
| `dead` | the resource answers 4xx, does not answer, or the package note says the service is gone |
| `stale` | the series ended or stopped, or the last file is older than its stated period allows |
| `licence` | needs an API key, an access key or a contract; or the data is not public |
| `duplicate` | the same records are in another row or a seeded source |
| `format` | no format of the list above: raster or 3D imagery, XLS/XLSX or SHP only |
| `not-data` | answers no city question as records: raw survey answers, projections, rankings, ledgers, planning graphs |
| `outside` | another city's data only, no row inside Helsinki |

Decided (worker-t5663, owner may override): the task's reason list (`dead`, `stale`, `pdf-only`,
`licence`, `empty`, `duplicate`) gains `format`, `not-data` and `outside`, because 34, 47 and 6
rows fit none of its words; `pdf-only` and `empty` hold no row. Options were forcing those rows into
`stale` or `empty`, which would misstate why they are left out.

### 9.2 What was read

- **Portal.** `package_search` (rows=1000) on 2026-10-25T14:50Z: 592 packages on HRI, 396 of them
  from the publishers of section 1, the same 396 names as on 2026-10-22: none added, none removed.
  `package_show` of each: 394 CC BY 4.0, one CC0, one `other-open`, as before.
- **Probe.** One GET of each resource URL (at most six per package, 64 KiB read, 15 s timeout) on
  2026-10-25T14:50Z: 320 packages answer, 10 fail (403 or no answer), 4 have no resource URL, and 62
  are served only from `kartta.hel.fi`, which still accepts no TCP connection from the sandbox (15 s
  timeout). Of the failing rows only row 13 was a usable candidate; it answers 403 and is now `dead`.
- **kartta.hel.fi from dev.** The dev cluster reads the host today: the 59 `district-*` and 148
  `subdistrict-*` `AdministrativeArea` entities of `helsinki-districts`, whose source is the
  `avoindata:Kaupunginosajako` WFS layer, carry `modifiedAt` 2026-10-25T00:38Z. So no kartta row is
  `dead`; T-5256, T-5286 and T-5378 are blocked by the sandbox, not by the source.
- **Dev.** For each of the 34 seeded Helsinki Endpoints, `GET /api/endpoint/<slug>/ngsi-ld/v1/types`,
  then `entities?type=<t>&count=true&limit=0` per type, then the id prefixes per type
  (`format=keyValues&pick=id,modifiedAt&options=sysAttrs`, paged) to tell which source wrote which
  entities. 21 Endpoints hold entities, 11 list no type and 2 need a login.

### 9.3 Counts

| usable | rows |
|---|---|
| yes | 133 |
| stale | 83 |
| duplicate | 78 |
| not-data | 47 |
| format | 34 |
| dead | 11 |
| outside | 6 |
| licence | 4 |
| total | 396 |

133 rows are usable, so the target is 100 with room to spare. 18 of them have entities on dev now
(row 47 only for 3 of its layers); 115 are not live yet.

Changed against section 6: row 13 (`dead`, 403), rows 7, 8, 9, 12 and 24 (section 6 kept them in
a batch, T-5253 and T-5254 left them out: duplicate, SHP only, stale), row 25 (`outside`: all 120
Vantaa stations lie in Vantaa, live on dev as `vantaa-*` in `helsinki-bikes`), and rows 66, 74 and 80
(`yes`: skipped on 2026-10-22 only because the sandbox could not reach `kartta.hel.fi`).

### 9.4 Seeded but empty on dev

| Endpoint | rows | what dev holds | cause |
|---|---|---|---|
| `helsinki-statistics-education`, `-employment`, `-environment`, `-housing`, `-income`, `-population`, `-services`, `-welfare` | the 67 statistics rows of T-5258 | no type; `helsinki-all` holds 0 `KeyPerformanceIndicator` with a `stat-` id | the `statistics` pipeline (daily 05:35) has written no entity; T-5258 says `deployed: pending` |
| `helsinki-kpi`, `helsinki-statistics-services` | 69, 76 | no `service-usage` KPI | the `service-usage` pipeline has written no entity |
| `helsinki-heat-vulnerability` | 33 | no type | the `heat-vulnerability` pipeline has written no entity, although its source zip answers 200 |

Each Endpoint answers 200 with an empty type list, so the views and their Policies are in place and
the pipelines are the gap. The run logs are on the cluster, which only the deployer reads: fix task F1.
`helsinki-hub` and `catalog` hold no data rows by design; `helsinki-bikes-ops` and `app-bike-stations`
answer 401 without a login and count for nothing.

### 9.5 All rows

`usable` follows section 9.1. `dev` is what the dev cluster held on 2026-10-25T14:50Z: `live:` with
the Endpoint and the entity count (and id prefix where an Endpoint has several sources), `empty:` with
the cause, `not seeded`, or for a row that is not usable `-` or the fact behind its reason. `plan` is `live`, the batch or fix of
section 10, or `-`.

| # | dataset | usable | dev | plan |
|---|---|---|---|---|
| 1 | `datankeruukokeilu-helsingissa-liikennelaskenta-konenaon-avulla` | yes | not seeded | B1 |
| 2 | `helsingin-kantakaupungin-ja-asukaspysakointivyohykkeiden-pysakointipaikat` | yes | seeded by T-5286 (`helsinki-parking`, `parking-place-*`), live after the next dev apply | T-5286 |
| 3 | `helsingin-liikenne-ja-varoitusvaloliittymat` | yes | seeded by T-5286 (`helsinki-traffic-signals`), live after the next dev apply | T-5286 |
| 4 | `helsingin-liikennemittausten-tilastorajapinta` | yes | live: `helsinki-traffic-counts` 33, live: `helsinki-cycle-counts` 19 | live |
| 5 | `helsingin-liikennevaylat` | yes | not seeded: 111404 segments need a paged read (T-5286 left it) | B3 |
| 6 | `helsingin-matkailuliikenteen-pysakit-ja-pysakointipaikat` | yes | seeded by T-5286 (`helsinki-parking`, `tourist-stop-*`, `tourist-parking-*`), live after the next dev apply | T-5286 |
| 7 | `helsingin-pyorailijamaarat` | duplicate | same Eco-Counter stations as row 4 | - |
| 8 | `helsingin-pyoravaylat-2025` | format | SHP zips only, a planned 2025 network | - |
| 9 | `helsingin-seudun-pyoralaskennat` | stale | yearly means 2013-2017 only | - |
| 10 | `liikennemaarat-helsingissa` | yes | not seeded (its JSON API is row 4's LAM source) | B1 |
| 11 | `liikenneonnettomuudet-helsingissa` | yes | not seeded: EPSG:3879 needs a projection step (T-5286 left it) | B3 |
| 12 | `pysakointivirheet-helsingissa` | stale | half-yearly, no file since 2024-09 | - |
| 13 | `helsingin-ja-espoon-kaupunkipyorilla-ajatut-matkat` | dead | resource answers 403 | - |
| 14 | `helsingin-jalankulun-ja-pyorailyn-talvihoidon-priorisoitu-reitisto` | yes | not seeded: a `RoadSegment` layer beside row 5 (T-5286 left it) | B3 |
| 15 | `hsl-n-joukkoliikenteen-pysakit` | duplicate | - | - |
| 16 | `hsl-n-joukkoliikenteen-risteyssolmut` | not-data | - | - |
| 17 | `hsl-n-linjat` | duplicate | - | - |
| 18 | `hsl-n-myyntipisteet` | yes | live: `helsinki-places` 853 `hsl-sales-*` | live |
| 19 | `hsl-n-nousijamaarat-pysakeittain` | yes | live: `helsinki-kpi` 6708 `hsl-boardings-*` | live |
| 20 | `hsl-n-pysakit-linjoittain` | duplicate | - | - |
| 21 | `hsl-n-taksavyohykkeet` | yes | live: `helsinki-districts` 4 `hsl-zone-*` | live |
| 22 | `hsl-n-terminaalit` | duplicate | - | - |
| 23 | `hsl-n-vuoromaarat` | not-data | - | - |
| 24 | `matkustaja-alusten-aikataulu-liikennointi-ja-sijaintitietoja-helsingin-ja-tallinnan-valilla` | stale | closed 2018-2019 archive | - |
| 25 | `vantaan-kaupunkipyoraasemat` | outside | live: `helsinki-bikes` 120 `vantaa-*`; Vantaa stations, none in Helsinki | - |
| 26 | `datankeruukokeilu-helsingissa-ilmanlaatu-katujen-siivouksen-aikana` | yes | live: `helsinki-street-cleaning-air` 13712 `swarco-*` | live |
| 27 | `helsingin-avouomat` | yes | not seeded | T-5378 |
| 28 | `helsingin-ilmanlaadun-mittaukset-raitiovaunuihin-asennetuilla-mittalaitteilla` | yes | not seeded | T-5378 |
| 29 | `helsingin-kaukolammon-tuotantotarve` | yes | not seeded | T-5378 |
| 30 | `helsingin-kaupungin-meluselvitys-2017` | yes | not seeded | T-5378 |
| 31 | `helsingin-kaupungin-palvelukiinteistojen-energiankulutustietoja` | yes | live: `helsinki-service-property-energy` 1066 `energy-*` | live |
| 32 | `helsingin-kaupungin-puurekisteri` | yes | not seeded | T-5378 |
| 33 | `helsingin-lampohaavoittuvuusindeksi` | yes | empty: `helsinki-heat-vulnerability` lists no type; the heat-vulnerability pipeline wrote no KPI | F1 |
| 34 | `helsingin-luontotietojarjestelma` | yes | not seeded | T-5378 |
| 35 | `helsingin-maa-ja-vesialueet` | yes | not seeded | T-5378 |
| 36 | `helsingin-tavoitteellinen-viher-ja-virkistysverkostokartta` | yes | not seeded | T-5378 |
| 37 | `helsingin-teollisuusmeluvyohykkeet` | yes | not seeded | T-5378 |
| 38 | `helsingin-ulkoliikuntapaikkojen-laitteiden-kayttoasteet` | stale | - | - |
| 39 | `iot-meludataa-helsingista` | stale | - | - |
| 40 | `purkupisteet-ja-osavaluma-alueet` | yes | not seeded | T-5378 |
| 41 | `turvalliset-rakentamiskorkeudet-ja-suurin-arvioitu-merkitseva-aallonkorkeus-helsingissa` | yes | not seeded | T-5378 |
| 42 | `asemakaavoilla-suojellut-rakennukset-ja-alueet-helsingissa` | yes | not seeded | T-5256 |
| 43 | `helsingin-asemakaavahakemistokartta-asemakaavahakemisto` | yes | not seeded | T-5256 |
| 44 | `helsingin-kaavayksikot` | yes | not seeded | T-5256 |
| 45 | `helsingin-kaupungin-peruskoulujen-oppilaaksiottoaluerajat` | yes | not seeded | T-5256 |
| 46 | `helsingin-kaupungin-yleisten-alueiden-rekisteri` | yes | not seeded | T-5256 |
| 47 | `helsingin-kaupungin-yleisten-alueiden-tapahtuma-ja-maankayttolupajarjestelma` | yes | live: `helsinki-public-area-permits` 1160 `KP/TP/LJ-*` (3 layers) | T-5256 |
| 48 | `helsingin-kaupunkitilaohjealueet` | yes | not seeded | T-5256 |
| 49 | `helsingin-kiinteistot-alueina` | yes | not seeded | T-5256 |
| 50 | `helsingin-korttelit` | yes | not seeded | T-5256 |
| 51 | `helsingin-maaraalat-alueina` | yes | not seeded | T-5256 |
| 52 | `helsingin-nimisto` | yes | not seeded | T-5256 |
| 53 | `helsingin-osayleiskaavahakemisto` | yes | not seeded | T-5256 |
| 54 | `helsingin-osayleiskaavat` | yes | not seeded | T-5256 |
| 55 | `helsingin-osoiteluettelo` | yes | not seeded | T-5256 |
| 56 | `helsingin-paakatuverkon-paallysteiden-kuntomittaukset` | yes | not seeded | T-5256 |
| 57 | `helsingin-rakennukset` | yes | not seeded | T-5256 |
| 58 | `helsingin-rakennuskiellot-alueina` | yes | not seeded | T-5256 |
| 59 | `helsingin-vapaat-yritystontit` | yes | not seeded | T-5256 |
| 60 | `helsingin-yleiskaava-2016` | yes | not seeded | T-5256 |
| 61 | `helsingin-yleisten-alueiden-arvoymparistot` | yes | not seeded | T-5256 |
| 62 | `helsingin-yleisten-alueiden-kunnossapidon-vastuualueet` | yes | not seeded | T-5256 |
| 63 | `helsingin-ymparistolupakohteet` | yes | not seeded | T-5256 |
| 64 | `helsinkilaisten-rakennusten-historiatietoja` | yes | not seeded | T-5256 |
| 65 | `paakaupunkiseudun-aanestysaluejako` | yes | not seeded | T-5256 |
| 66 | `helsingin-ensimmaisen-maailmansodan-aikaiset-maalinnoitukset` | yes | not seeded (skipped on 2026-10-22 only because the sandbox cannot reach kartta.hel.fi) | B2 |
| 67 | `helsingin-kaupungin-palauterajapinta` | yes | live: `helsinki-feedback` 163 `open311-*` | live |
| 68 | `helsingin-kaupungin-palvelurekisterin-rest-rajapinta` | duplicate | - | - |
| 69 | `helsingin-kaupungin-verkkosivustojen-kavijaanalytiikka` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no service-usage KPI; the pipeline wrote none | F1 |
| 70 | `helsingin-kaupunginorkesterin-konsertit` | stale | - | - |
| 71 | `helsingin-kulttuurihistoriallisesti-merkittavat-porrashuoneet` | stale | - | - |
| 72 | `helsingin-taidemuseon-nayttelyt` | stale | - | - |
| 73 | `helsingin-taidemuseon-prosenttirahahankkeet` | format | - | - |
| 74 | `helsingin_maisemakulttuurikartta` | yes | not seeded (skipped on 2026-10-22 only because the sandbox cannot reach kartta.hel.fi) | B2 |
| 75 | `jalankulkijoiden-liukastumisvaroitukset-helsingissa` | not-data | - | - |
| 76 | `korkeasaaren-kavijamaarat` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no service-usage KPI; the pipeline wrote none | F1 |
| 77 | `paakaupunkiseudun-palvelukartan-rest-rajapinta` | yes | live: `helsinki-places` 12466 `servicemap-*` | live |
| 78 | `rajapinta-paakaupunkiseudun-kansalais-ja-tyovaenopistojen-kurssitietoihin` | licence | - | - |
| 79 | `suomenlinnan-lautan-matkustajamaarat` | licence | - | - |
| 80 | `uusien-toimintojen-paikat-helsingin-rantareitilla` | yes | not seeded (skipped on 2026-10-22 only because the sandbox cannot reach kartta.hel.fi) | B2 |
| 81 | `helsingin-asukas-ja-yrityspysakointivyohykkeet` | yes | live: `helsinki-parking` 16 `resident-zone-*` | live |
| 82 | `helsingin-hel-fi-sivuston-avoin-rajapinta-uutisille` | yes | live: `helsinki-news` 32 | live |
| 83 | `helsingin-kaupunginosat` | yes | live: `helsinki-districts` 59 `district-*` | live |
| 84 | `helsingin-piirijako` | yes | live: `helsinki-districts` 148 `subdistrict-*` | live |
| 85 | `helsingin-pysakoinnin-maksuvyohykkeet` | yes | live: `helsinki-parking` 2 `fee-zone-*` | live |
| 86 | `hsl-n-kaupunkipyoraasemat` | yes | live: `helsinki-bikes` 456 | live |
| 87 | `linked-events-tapahtumarajapinta` | yes | live: `helsinki-events` 137 | live |
| 88 | `rajapinta-helsingin-pysakointipaikkojen-kaytosta` | yes | live: `helsinki-parking` 1830 `parkkiopas-*` | live |
| 89 | `veden-reaaliaikainen-lampotila-helsingin-uimarannoilla` | yes | live: `helsinki-beach-water` 28 `uiras-*` | live |
| 90 | `a01hki_astuot_tp_hper_rahoitus_talotyyppi` | stale | - | - |
| 91 | `aluesarjat-a01s-hki-askan-2005` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 92 | `aluesarjat-a01s-hki-rakennuskanta` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 93 | `aluesarjat-a01s-hki-tyovoima-sukupuoli` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 94 | `aluesarjat-a02s-hki-askan-talotyyppi-hallintap-kotilanne` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 95 | `aluesarjat-a03s-hki-kuolleet` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 96 | `aluesarjat-hginseutu-ar-aa01-asuntokanta-rvuosi-talotyyppi` | duplicate | - | - |
| 97 | `aluesarjat-hginseutu-ar-aa03-asuntokanta-halper-huoneistotyyppi` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 98 | `aluesarjat-hginseutu-ar-rr01-rakennukset-kayttark-rvuosi` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 99 | `aluesarjat-hginseutu-as-ak01-asuntokunnat-talotyp-henkiloluku` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 100 | `aluesarjat-hginseutu-tt-tm03-koulutustaso` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 101 | `aluesarjat-hginseutu-va-ve02-vaestoennuste-kehys` | not-data | - | - |
| 102 | `aluesarjat-hginseutu-va-ve03-vaestoennuste-kieli` | not-data | - | - |
| 103 | `aluesarjat-hginseutu-va-vr03-vakiluku-ika-sukup-aidinkieli3-ssaaty` | duplicate | - | - |
| 104 | `aluesarjat_a01hki_asunto_ohjelma` | not-data | - | - |
| 105 | `aluesarjat_a01hki_asuntokuntien_tulot` | stale | - | - |
| 106 | `aluesarjat_a01hki_raktuot_kayttotark_2003-` | stale | - | - |
| 107 | `aluesarjat_a01hkis_vaestotulot` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 108 | `aluesarjat_a01s_hki_asuntokunnat` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 109 | `aluesarjat_a01s_hki_muuttoliike` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 110 | `aluesarjat_a01s_hki_perhetyypit` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 111 | `aluesarjat_a01s_hki_vaesto_koulutusaste` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 112 | `aluesarjat_a01s_hki_vakiluku` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 113 | `aluesarjat_a02s_hki_perhevaesto` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 114 | `aluesarjat_a02s_hki_syntyneet` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 115 | `aluesarjat_a02s_hki_vakiluku1962` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 116 | `aluesarjat_a03s_hki_askan_hallintaperuste_htyyppi` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 117 | `aluesarjat_a03s_hki_lapsiperheet_alle18` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 118 | `aluesarjat_a03s_hki_vakiluku_aidinkieli` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 119 | `aluesarjat_a04s_hki_lapsiperheet` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 120 | `aluesarjat_a04s_hkis_tyottomat_sukupuoli` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 121 | `aluesarjat_hginseutu_ar_aa02_asuntokanta_talotyyppi_halper_kaytil` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 122 | `aluesarjat_hginseutu_as_ak02_asuntokuntien_keskikoko` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 123 | `aluesarjat_hginseutu_as_ak03_asumisvaljyys_hloluku` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 124 | `aluesarjat_hginseutu_tt_tm01_tyottomyys_kk` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 125 | `aluesarjat_hginseutu_tt_tm02_paa_as_toiminta` | duplicate | - | - |
| 126 | `aluesarjat_hginseutu_tt_tv01_tyovoima_ika` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 127 | `aluesarjat_hginseutu_tt_tv02a_tyovoima_tol2008` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 128 | `aluesarjat_hginseutu_va_mt01a_tulomuuttajatkoulutussuku` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 129 | `aluesarjat_hginseutu_va_mt01b_lahtomuuttajatkoulutussuku` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 130 | `aluesarjat_hginseutu_va_pe01_perheet_perhetyyppi` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 131 | `aluesarjat_hginseutu_va_pe02_lapsiperheet_lapsiluku` | duplicate | - | - |
| 132 | `aluesarjat_hginseutu_va_pe03_lapsiperheet_perhetyyppi` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 133 | `aluesarjat_hginseutu_va_pe04_perhevaesto` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 134 | `aluesarjat_hginseutu_va_vm01_vaestonmuutosten_yhdistelma` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 135 | `aluesarjat_hginseutu_va_vm02_muuttoliike_alueittain` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 136 | `aluesarjat_hginseutu_va_vm03_muuttoliike_ikaryhmittain` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 137 | `aluesarjat_hginseutu_va_vm04_syntyneet` | duplicate | - | - |
| 138 | `aluesarjat_hginseutu_va_vm05_kuolleet` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 139 | `aluesarjat_hginseutu_va_vr01_vakiluku_ika` | duplicate | - | - |
| 140 | `aluesarjat_hginseutu_va_vr02_vakiluku_aidinkieli3` | duplicate | - | - |
| 141 | `aluesarjat_hginseutu_va_vr04_vakiluku_aidinkieli_ika` | duplicate | - | - |
| 142 | `aluesarjat_hginseutu_va_vr05_vakiluku_kansalaisuus_s` | duplicate | - | - |
| 143 | `asunnontarkastuksen-toimenpidepyynnot-helsingissa` | stale | - | - |
| 144 | `eduskuntavaalit-helsingissa-2011` | stale | - | - |
| 145 | `eduskuntavaalit-helsingissa-2015` | stale | - | - |
| 146 | `elinkustannusindeksi-ja-rahanarvonkerroin-keskimaaraisten-kuukausivuokrien-deflatoimiseksi` | stale | - | - |
| 147 | `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1900` | stale | - | - |
| 148 | `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1932-1974` | stale | - | - |
| 149 | `helsingin-asuinhuoneistojen-keskimaarainen-kuukausivuokra-huoneluvun-mukaan-1975-1980` | stale | - | - |
| 150 | `helsingin-asuinhuoneistot-asuntovaesto-ja-asumistiheys-huoneluvun-mukaan-1870-1998` | stale | - | - |
| 151 | `helsingin-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 152 | `helsingin-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 153 | `helsingin-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005` | stale | - | - |
| 154 | `helsingin-asuntotuotanto-aloitetut-rakennushankkeet-2015` | duplicate | - | - |
| 155 | `helsingin-asuntotuotanto-keskeneraiset-rakennushankkeet-2015` | duplicate | - | - |
| 156 | `helsingin-asuntotuotanto-myonnetyt-rakennusluvat-2015` | duplicate | - | - |
| 157 | `helsingin-asuntotuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 158 | `helsingin-asuntotuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 159 | `helsingin-asuntotuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 160 | `helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 161 | `helsingin-asuntotuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-ml-rah-hal-ja-rak-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 162 | `helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-2015` | duplicate | - | - |
| 163 | `helsingin-asuntotuotanto-valmistuneet-rakennushankkeet-rahoitus-hallintaperuste-ja-rakennuttaja-2015` | duplicate | - | - |
| 164 | `helsingin-erilaisilla-mukavuuslaitoksilla-varustetut-huoneistot-kaupunginosittain-1920` | stale | - | - |
| 165 | `helsingin-erisuuruisissa-huoneistoissa-asuvat-henkilot-kaupunginosittain-8-12-1920` | stale | - | - |
| 166 | `helsingin-henkikirjoitettu-vaesto-kaupunginosittain-1-1-1875-1960` | stale | - | - |
| 167 | `helsingin-historialliset-tilastot` | stale | - | - |
| 168 | `helsingin-kaupungin-avustukset` | not-data | - | - |
| 169 | `helsingin-kaupungin-henkilosto-1914-1998` | stale | - | - |
| 170 | `helsingin-kaupungin-henkiloston-koulutukset` | not-data | - | - |
| 171 | `helsingin-kaupungin-kansakoulujen-luokat-lukuvuosina-1896-97-1976-77` | stale | - | - |
| 172 | `helsingin-kaupungin-kansakoulujen-opettajat-lukuvuosina-1896-97-1976-77` | stale | - | - |
| 173 | `helsingin-kaupungin-kansakoulujen-oppilaat-lukuvuosina-1896-97-1976-77` | stale | - | - |
| 174 | `helsingin-kaupungin-kansakoulujen-oppilaiden-vanhempien-tausta-lukuvuosina-1896-97-1968-69` | stale | - | - |
| 175 | `helsingin-kaupungin-nuorisoasiainkeskuksen-avustukset` | not-data | - | - |
| 176 | `helsingin-kaupungin-ostot` | not-data | - | - |
| 177 | `helsingin-kaupungin-peruskoulujen-kielivalinnat` | format | - | - |
| 178 | `helsingin-kaupungin-talousarviotiedot` | not-data | - | - |
| 179 | `helsingin-kaupungin-tulot-ja-menot` | not-data | - | - |
| 180 | `helsingin-kaupungin-tyonvalitystoiminta-1903-1960` | stale | - | - |
| 181 | `helsingin-kaupungin-ymparistoraportti` | format | - | - |
| 182 | `helsingin-kaupungin-ymparistotilinpito` | duplicate | - | - |
| 183 | `helsingin-kaupunginkirjaston-kaynnit-toimipisteittain` | format | - | - |
| 184 | `helsingin-kaupunginkirjaston-lainausmaarat-1860` | stale | - | - |
| 185 | `helsingin-kaupunginkirjaston-lainausmaarat-toimipisteittain` | format | - | - |
| 186 | `helsingin-kaupunginkirjastossa-kirjastokorttiaan-k-ytt-neet` | format | - | - |
| 187 | `helsingin-keskivakiluku-ian-ja-sukupuolen-mukaan-1935-1961` | stale | - | - |
| 188 | `helsingin-kestavan-kehityksen-indikaattorit` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 189 | `helsingin-kulttuurikeskuksen-avustukset` | not-data | - | - |
| 190 | `helsingin-lammitettavat-rakennukset-rakennusaineen-ja-kerrosluvun-mukaan-1880-1930` | stale | - | - |
| 191 | `helsingin-lukioiden-sis-np-syrajat` | stale | - | - |
| 192 | `helsingin-lukioiden-yhteishaun-tulokset` | stale | - | - |
| 193 | `helsingin-nuoret-alueittain` | stale | - | - |
| 194 | `helsingin-oppikoulujen-1-ja-2-luokalle-otetut-oppilaat-lukuvuosina-1925-26-1960-61` | stale | - | - |
| 195 | `helsingin-oppikoulut-lukuvuosina-1894-95-1976-77` | stale | - | - |
| 196 | `helsingin-osallistuvan-budjetoinnin-aanestystulokset` | not-data | - | - |
| 197 | `helsingin-perus-ja-2-asteen-opetuksen-oppilasmaarat-kouluittain` | format | - | - |
| 198 | `helsingin-rakennetut-kiinteistot-ja-lammitettavat-rakennukset-kaupunginosittain-1900-1950` | stale | - | - |
| 199 | `helsingin-rakennetut-kiinteistot-seka-lammitettavat-rakennukset-ja-huoneet-kaupunginosittain-1870` | stale | - | - |
| 200 | `helsingin-rakennustuotanto-aloitetut-rakennushankkeet-2015` | duplicate | - | - |
| 201 | `helsingin-rakennustuotanto-keskeneraiset-rakennushankkeet-2015` | duplicate | - | - |
| 202 | `helsingin-rakennustuotanto-myonnetyt-rakennusluvat-2015` | duplicate | - | - |
| 203 | `helsingin-rakennustuotanto-neljannesvuosittain-aloitetut-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 204 | `helsingin-rakennustuotanto-neljannesvuosittain-keskeneraiset-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 205 | `helsingin-rakennustuotanto-neljannesvuosittain-myonnetyt-rakennusluvat-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 206 | `helsingin-rakennustuotanto-neljannesvuosittain-valmistuneet-rakennushankkeet-2015q1` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 207 | `helsingin-rakennustuotanto-valmistuneet-rakennushankkeet-2015` | duplicate | - | - |
| 208 | `helsingin-seudun-aluesarjat-tilastotietokannan-tiedot-paikkatietona` | duplicate | - | - |
| 209 | `helsingin-seudun-kuntien-valisen-ja-ulkomaisen-muuttoliikkeen-ennakkotiedot-neljannesvuosittain-2010` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 210 | `helsingin-seudun-perheet-perhetyypin-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 211 | `helsingin-seudun-sairastavuusindeksi` | duplicate | - | - |
| 212 | `helsingin-seudun-tyopaikat-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008` | duplicate | - | - |
| 213 | `helsingin-seudun-v-est-1-1-1980-2013-sek-ennuste-1-1-2014-2050` | not-data | - | - |
| 214 | `helsingin-seudun-vaesto-aidinkielen-mukaan` | duplicate | - | - |
| 215 | `helsingin-seudun-vaestonmuutosten-ennakkotiedot-vuoden-alusta-neljannesvuosittain` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 216 | `helsingin-sosiaalitoimen-suoritetietoja` | stale | - | - |
| 217 | `helsingin-tilastollinen-vuosikirja` | duplicate | - | - |
| 218 | `helsingin-tulo-ja-lahtomuutto-laaneittain-1911-1994` | stale | - | - |
| 219 | `helsingin-tyovaeston-asunto-olot-vuonna-1900-asuntojen-varustelutaso` | stale | - | - |
| 220 | `helsingin-tyovaeston-asunto-olot-vuonna-1900-terveydelliset-olot` | stale | - | - |
| 221 | `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asukkaiden-lukumaarasta` | stale | - | - |
| 222 | `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-asuntojen-lukumaarasta` | stale | - | - |
| 223 | `helsingin-tyovaeston-asunto-olot-vuonna-1900-tietoa-huoneiden-lukumaarasta` | stale | - | - |
| 224 | `helsingin-vaesto-elinkeinoryhmittain-1870-1930` | stale | - | - |
| 225 | `helsingin-vaesto-ja-asuntotuotantoennuste-alueittain` | not-data | - | - |
| 226 | `helsingin-vaesto-ja-ruotsinkieliset-1-1-1992-alkaen-seka-vaestoennuste-alueittain` | not-data | - | - |
| 227 | `helsingin-vaesto-paaasiallisen-toiminnan-sukupuolen-ja-ian-mukaan-31-12-2000` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 228 | `helsingin-vaeston-ammatissa-toimivuus-1870-1930` | stale | - | - |
| 229 | `helsingin-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015` | stale | - | - |
| 230 | `helsingin-vakiluku-1-1-1875-1993-ja-vuodenvaihteissa-1993-94-2013-14` | stale | - | - |
| 231 | `helsingin-vakiluku-ian-ja-sukupuolen-mukaan-1900-1961` | stale | - | - |
| 232 | `helsingin-vanhojen-asunto-osakehuoneistojen-neliohinnat-postinumeroalueittain-vuodesta-2000` | stale | - | - |
| 233 | `helsingin-ymparistotilasto` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 234 | `helsingissa-asuva-tyollinen-tyovoima-toimialan-tol-2008-mukaan` | duplicate | - | - |
| 235 | `helsinki-alueittain` | stale | - | - |
| 236 | `helsinki-s-2030-climate-technologies-city-performance-tool-2016` | stale | - | - |
| 237 | `helsinki-turvattomuutta-kokevien-osuudet-peruspiireitt-2003-2006-ja-2009` | not-data | - | - |
| 238 | `helsinkiin-ja-helsingista-muuttaneet-sukupuolen-mukaan-1881-1998` | stale | - | - |
| 239 | `ikaryhmittaiset-hedelmallisyysluvut-helsingissa-1936-2013` | stale | - | - |
| 240 | `kirjastokaynnit-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa` | format | - | - |
| 241 | `kirjojen-lainaus-kielittain-helsingin-kaupunginkirjastossa` | format | - | - |
| 242 | `kokonaishedelmallisyysluku-ja-yleinen-hedelmallisyysluku-helsingissa-1936-2013` | stale | - | - |
| 243 | `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1891-1950` | stale | - | - |
| 244 | `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1951-1968` | stale | - | - |
| 245 | `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1969-1985` | stale | - | - |
| 246 | `kuolleet-kuolemansyyn-mukaan-10000-asukasta-kohden-helsingissa-1988-1995` | stale | - | - |
| 247 | `kuuden-suurimman-kaupungin-kehitysvammahuollon-vertailu` | stale | - | - |
| 248 | `kuuden-suurimman-kaupungin-lastensuojelun-vertailu` | stale | - | - |
| 249 | `kuuden-suurimman-kaupungin-paihde-ja-mielenterveyspalvelujen-vertailu` | stale | - | - |
| 250 | `kuuden-suurimman-kaupungin-toimeentulotuen-vertailu` | stale | - | - |
| 251 | `kuuden-suurimman-kaupungin-vammaispalvelujen-vertailu` | stale | - | - |
| 252 | `kuuden-suurimman-kaupungin-vanhustenpalvelujen-vertailu` | stale | - | - |
| 253 | `kuuden-suurimman-kaupungin-varhaiskasvatuspalvelujen-vertailu` | format | - | - |
| 254 | `lainaus-toimipisteittain-ja-kuukausittain-helsingin-kaupunginkirjastossa` | format | - | - |
| 255 | `lasten-ja-nuorten-hyvinvointi-helsingissa` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 256 | `naiset-ja-miehet-helsingissa` | stale | - | - |
| 257 | `naisten-ja-miesten-taydellinen-elinajantaulu-km-jaljella-oleva-elinaika-helsingissa-1941-2005` | stale | - | - |
| 258 | `nordstat-tilastoja-pohjoismaiden-suurimmista-kaupungeista-ja-kaupunkiseuduista` | duplicate | - | - |
| 259 | `paakaupunkiseudun-autonomistajuustiedot` | format | - | - |
| 260 | `paakaupunkiseudun-vaestoennuste` | not-data | - | - |
| 261 | `paikalliset-ja-muualle-ulottuvat-tyonseisaukset-helsingissa-1907-1951` | stale | - | - |
| 262 | `paikalliset-tyonseisaukset-1954-1970-ja-tyotaistelut-helsingissa-1971-1997` | stale | - | - |
| 263 | `pks-kuntien-taloudellisia-tunnuslukuja` | stale | - | - |
| 264 | `seudullinen-tilastorajapinta` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 265 | `solmitut-ja-purkautuneet-avioliitot-helsingissa-1896-1998` | stale | - | - |
| 266 | `syntyneet-ja-kuolleet-helsingissa-1811-1998` | stale | - | - |
| 267 | `teollisuuden-tyopaikat-ja-tyontekijat-helsingissa-1884-1965` | stale | - | - |
| 268 | `tyopaikat-helsingissa-alueella-tyossakayvat-toimialan-tol-2008-2-3-nro-mukaan-31-12-2008` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 269 | `tyopaikat-uudellamaalla-alueella-tyossakayvat-toimialan-tol-2008-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 270 | `uudenmaan-asuntokunnat-henkiloluvun-ja-vanhimman-ian-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 271 | `uudenmaan-kuntien-asuntokuntien-kulutusyksikkokohtaiset-rahatulot-desiililuokittain-1995` | stale | - | - |
| 272 | `uudenmaan-kuntien-asuntokuntien-tulot-asuntokunnan-elinvaiheen-ja-alueen-mukaan-1995` | stale | - | - |
| 273 | `uudenmaan-kuntien-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005` | stale | - | - |
| 274 | `uudenmaan-rakennukset-kayttotarkoituksen-lammitystavan-lammitysaineen-ja-kerrosalan-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 275 | `uudenmaan-seudullinen-tyopaikkaprojektio-1980-2060` | not-data | - | - |
| 276 | `uudenmaan-tyopaikkaprojektioissa-kaytetyt-vaestoprojektiot` | not-data | - | - |
| 277 | `uudenmaan-vaesto-aidinkielen-sukupuolen-ja-ian-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 278 | `uudenmaan-vaesto-ian-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 279 | `uudenmaan-vaesto-paaasiallisen-toiminnan-ian-ja-sukupuolen-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 280 | `uusimaa-kuolleet-ian-ja-sukupuolen-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 281 | `uusimaa-muuttoliike-lahto-tai-kohdealueen-aidinkielen-ja-ian-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 282 | `uusimaa-syntyneet-aidin-ian-mukaan` | yes | empty: the `helsinki-statistics-*` and `helsinki-kpi` views hold no `stat-*` KPI; the pipeline wrote none | F1 |
| 283 | `valmistuneet-asuinhuoneet-kivi-ja-puutaloissa-helsingissa-1939-1950` | stale | - | - |
| 284 | `valmistuneet-asuinhuoneistot-helsingissa-1921-1967` | stale | - | - |
| 285 | `aarteeni-helsingissa-kyselyn-vastaukset` | not-data | - | - |
| 286 | `elintarvikevalvonnan-piiriin-kuuluvat-elintarvikehuoneistot-helsingissa` | stale | - | - |
| 287 | `espoon-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005` | outside | - | - |
| 288 | `espoon-kaupungin-resurssienvarausrajapinta` | outside | - | - |
| 289 | `espoon-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015` | outside | - | - |
| 290 | `etelasatama-virtual-3d-malli` | format | - | - |
| 291 | `helmet-kirjastojen-aineistoluettelot` | duplicate | - | - |
| 292 | `helmet-kirjastojen-lainatuimmat-aikuistenkirjat` | not-data | - | - |
| 293 | `helmet-kirjastojen-lainatuimmat-lastenkirjat` | not-data | - | - |
| 294 | `helmet-kirjastojen-varatuimmat-kirjat` | not-data | - | - |
| 295 | `helsingin-3d-kaupunkimalli` | not-data | - | - |
| 296 | `helsingin-3d-rakennukset` | duplicate | - | - |
| 297 | `helsingin-ajantasa-asemakaava` | format | - | - |
| 298 | `helsingin-asemakaavakartat` | format | - | - |
| 299 | `helsingin-asuntokunnat-henkilun-mukaan-piireitt-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 300 | `helsingin-asuntokunnat-koon-ja-vanhimman-henkilon-ian-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 301 | `helsingin-espoon-ja-vantaan-liikennevaloristeykset` | format | - | - |
| 302 | `helsingin-historialliset-asemakaavakartat` | format | - | - |
| 303 | `helsingin-historialliset-kartat` | format | - | - |
| 304 | `helsingin-historialliset-opaskartat` | format | - | - |
| 305 | `helsingin-historialliset-yleiskaavat` | format | - | - |
| 306 | `helsingin-ja-vantaan-ymparistoasennekyselyn-vastaukset` | not-data | - | - |
| 307 | `helsingin-johtamisen-uudistaminen-verkkokyselyn-vastaukset` | not-data | - | - |
| 308 | `helsingin-kansallinen-kaupunkipuisto-kyselyn-vastaukset` | not-data | - | - |
| 309 | `helsingin-kantakartta` | format | - | - |
| 310 | `helsingin-katujen-puhdistussuunnitelmat` | dead | - | - |
| 311 | `helsingin-kaupungin-chatbotien-koulutusdatat` | not-data | - | - |
| 312 | `helsingin-kaupungin-koulurekisteri` | dead | - | - |
| 313 | `helsingin-kaupungin-resurssienvarausrajapinta` | dead | - | - |
| 314 | `helsingin-kaupungin-taloushallintopalvelun-tulot-ja-menot` | dead | - | - |
| 315 | `helsingin-kaupungin-talvihoidon-kayttajatyytyvaisyyskyselyn-vastaukset` | not-data | - | - |
| 316 | `helsingin-kaupungin-tarkastuslautakunnan-arviointikertomuksissa-esitetyt-suositukset` | not-data | - | - |
| 317 | `helsingin-kaupungin-yrityshaastattelututkimus` | not-data | - | - |
| 318 | `helsingin-kaupunginarkiston-aineistot` | dead | - | - |
| 319 | `helsingin-kaupunginmuseon-aineistot` | dead | - | - |
| 320 | `helsingin-kiinteistokartta` | format | - | - |
| 321 | `helsingin-koko-vt-ulkomaalaistaustaiset-maan-ja-imukaan-suurpiireitt-2004-alkaen` | duplicate | - | - |
| 322 | `helsingin-koko-vtkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-alkaen` | duplicate | - | - |
| 323 | `helsingin-korkeusmalli` | format | - | - |
| 324 | `helsingin-kuvakartta` | format | - | - |
| 325 | `helsingin-laserkeilausaineistot` | format | - | - |
| 326 | `helsingin-liikenneturvallisuuskysely-asukkaille` | not-data | - | - |
| 327 | `helsingin-luontopalvelulinjauksen-asukaskyselyn-vastaukset` | not-data | - | - |
| 328 | `helsingin-mikroilmaston-simulaatiodemo` | not-data | - | - |
| 329 | `helsingin-muu-kuin-suomen-ja-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-` | duplicate | - | - |
| 330 | `helsingin-muun-kuin-suomen-tai-ruotsinkielinen-vtn-ja-sukupuolen-mukaan-suurpiireitt-2004-alkae` | duplicate | - | - |
| 331 | `helsingin-opaskartta` | duplicate | - | - |
| 332 | `helsingin-ortoilmakuvat` | format | - | - |
| 333 | `helsingin-paivahoitotilastot` | duplicate | - | - |
| 334 | `helsingin-perheet-ja-lapset-sekterherakennetta-kuvaavia-tunnuslukuja-piireitt-ja-osa-alueittain` | duplicate | - | - |
| 335 | `helsingin-pintamalli` | format | - | - |
| 336 | `helsingin-pyorailybarometrikyselyn-vastaukset` | not-data | - | - |
| 337 | `helsingin-pyoravaylien-ongelmakohdekyselyn-vastaukset` | not-data | - | - |
| 338 | `helsingin-raide-jokerin-linjaus-ja-pysakit` | duplicate | - | - |
| 339 | `helsingin-rinnevarjosteet` | format | - | - |
| 340 | `helsingin-ruotsinkielinen-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 341 | `helsingin-ruotsinkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen` | duplicate | - | - |
| 342 | `helsingin-ruotsinkielinen-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 343 | `helsingin-suomenkielinen-vtisivuotisikhmitt-sivilisyn-ja-sukupuolen-mukaan-2004-alkaen` | duplicate | - | - |
| 344 | `helsingin-tuulivoimakysely-2015` | not-data | - | - |
| 345 | `helsingin-ulkomaalaistaustainen-vaesto-sukupuolen-ja-taustamaan-mukaan-2017-alkaen` | duplicate | - | - |
| 346 | `helsingin-vaesto-aidinkielen-ja-ian-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 347 | `helsingin-vaesto-ian-1-v-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 348 | `helsingin-vaesto-ian-5-v-aidinkielen-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 349 | `helsingin-vaesto-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 350 | `helsingin-vaesto-ian-ja-sukupuolen-mukaan-suurpiireittain-2004-alkaen` | duplicate | - | - |
| 351 | `helsingin-vaesto-piireittain-ja-osa-alueittain-ian-mukaan-2004-alkaen` | duplicate | - | - |
| 352 | `helsingin-vaesto-sukupuolen-ja-sivilisaadyn-mukaan-2004-alkaen-piireittain-ja-osa-alueittain` | duplicate | - | - |
| 353 | `helsingin-vaesto-syntymapaikan-sukupuolen-ja-ian-mukaan-2004-alkaen` | duplicate | - | - |
| 354 | `helsingin-vaesto-uskonnollisen-yhdyskunnan-sukupuolen-ja-ian-mukaan-2004-alkaen` | duplicate | - | - |
| 355 | `helsingin-vaesto-viisivuotisikaryhmittain-sivilisaadyn-ja-sukupuolen-mukaan-2004-alkaen` | duplicate | - | - |
| 356 | `helsingin-vapaa-aikakyselyn-vastaukset` | not-data | - | - |
| 357 | `helsingin-vtdinkielen-ja-imukaan-2004-alkaen` | duplicate | - | - |
| 358 | `helsingin-vtn-1-v-kumulatiivinen-ja-sukupuolen-mukaan-suurpiireitt-2004-alkaen` | duplicate | - | - |
| 359 | `helsingin-vtn-ja-sukupuolen-mukaan-sekaisten-osuus-piireitt-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 360 | `helsingin-vtn-mukaan-piireitt-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 361 | `helsingin-vtueittain-1962-alkaen` | duplicate | - | - |
| 362 | `helsingin-yleiskaava-2002` | format | - | - |
| 363 | `helsingin-yleiskartta` | format | - | - |
| 364 | `helsinki-2050-kyselyn-vastaukset` | not-data | - | - |
| 365 | `helsinki-region-infoshare-palvelun-kayttoa-koskevan-kyselyn-vastaukset` | not-data | - | - |
| 366 | `helsinkikanava-open-data` | dead | - | - |
| 367 | `hri-verkkopalvelun-avoimen-datan-metatiedot` | not-data | - | - |
| 368 | `hsl-bluetooth-majakat-api` | not-data | - | - |
| 369 | `hsl-n-asiakastyytyvaisyystutkimus` | not-data | - | - |
| 370 | `hsl-n-liityntapysakointipaikat` | duplicate | - | - |
| 371 | `hsl-n-reittioppaan-kohdetietokanta` | duplicate | - | - |
| 372 | `hsl-reittiopas-api` | duplicate | - | - |
| 373 | `hsln-lipunmyyntirajapinta` | licence | - | - |
| 374 | `kiva-keskusta-kavelijoille-kyselyn-vastaukset` | not-data | - | - |
| 375 | `miehet--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al` | duplicate | - | - |
| 376 | `miehet-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 377 | `muu-vaesto-helsingissa-eli-henkilot-joiden-asuinaluetta-ei-ole-maaritelty-ian-mukaan-2004-alkaen` | duplicate | - | - |
| 378 | `muu-vtlsingissli-henkiloiden-asuinaluetta-ei-ole-mitelty-sukupuolen-mukaan-2004-alkaen` | duplicate | - | - |
| 379 | `naiset--helsingin-koko-vt-ulkomaiden-kansalaiset-kansalaisuuden-ja-imukaan-suurpiireitt-2004-al` | duplicate | - | - |
| 380 | `naiset-helsingissa-ian-5-v-mukaan-piireittain-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 381 | `paakaupunkiseudun-avoimen-datan-palvelun-kayttajakyselyn-vastaukset` | not-data | - | - |
| 382 | `paakaupunkiseudun-liikennemeluvyohykkeet` | duplicate | - | - |
| 383 | `paakaupunkiseudun-opaskartta` | format | - | - |
| 384 | `paakaupunkiseudun-yleiskartta` | format | - | - |
| 385 | `rajapinta-staran-lumiaurojen-sijantitietoihin` | dead | - | - |
| 386 | `semantic-hri-fi--paakaupunkiseutua-koskevaa-tilastotietoa-avoimena-linkitettyna-datana` | stale | - | - |
| 387 | `seudullinen-osoiteluettelo` | duplicate | - | - |
| 388 | `signe-branderin-panoraamakuvat-1900-luvun-alun-helsingista` | format | - | - |
| 389 | `staran-tuotantoajoneuvojen-liikkeet-ja-toimenpiteet-helsingissa` | licence | - | - |
| 390 | `tietoa-suomesta-monella-eri-kielella` | dead | - | - |
| 391 | `ulkomaan-kansalaiset-helsingissa-kansalaisuuden-seka-syntymaalueen-ja-sukupuolen-mukaan-2017-alkaen` | duplicate | - | - |
| 392 | `uudenmaan-osoiterajapinta` | dead | - | - |
| 393 | `vaestonmuutokset-helsingissa-piireittain-ja-osa-alueittain-2004-alkaen` | duplicate | - | - |
| 394 | `vantaan-asuntokuntien-tulot-kulutusyksikkokohtaiset-ginikertoimet-2005` | outside | - | - |
| 395 | `vantaan-vaeston-ennakollinen-ikarakenne-neljannesvuosittain-ja-alueittain-31-12-2015` | outside | - | - |
| 396 | `yksinasuvat-yhden-hengen-asuntokunnat-helsingissukupuolen-ja-imukaan-peruspiireitt-2004-alkaen` | duplicate | - | - |

## 10. Plan to 100

Usable 133, live 18, target 100: 82 more rows have to go live. Batches in the order that reaches 100
soonest:

| plan | rows | live after | shape | SDM types | LinkML classes added | rows by # |
|---|---|---|---|---|---|---|
| F1 | 70 | 88 | fix: the three built KPI pipelines write nothing on dev | `KeyPerformanceIndicator` | none | 33, 69, 76 and the 67 T-5258 statistics rows |
| T-5286 | 3 | 91 | `kartta.hel.fi` WFS GetFeature, points and areas | `OnStreetParking`, custom `TrafficSignalJunction` | `TrafficSignalJunction` | 2, 3, 6 |
| T-5378 | 11 | 102 | `kartta.hel.fi` WFS GetFeature and two files, parked | `NoisePollution`, `GreenspaceRecord`, `AirQualityObserved`, `KeyPerformanceIndicator`, custom `Watercourse`, `Tree`, `LandCoverArea`, `StormwaterCatchment`, `FloodRiskArea` | `NoisePollution`, `GreenspaceRecord` and the five custom classes | 27, 28, 29, 30, 32, 34, 35, 36, 37, 40, 41 |
| T-5256 | 24 | 125 | `kartta.hel.fi` WFS GetFeature, paged, and one CSV, parked | `Building`, `GreenspaceRecord`, `CityWork`, `RoadSegment`, custom `AdministrativeArea`, `LandUsePlanArea`, `LandParcel`, `Street`, `Address`, `MaintenanceArea`, `EnvironmentalPermit` | `Building`, `GreenspaceRecord`, `LandUsePlanArea`, `LandParcel`, `Street`, `Address`, `MaintenanceArea`, `EnvironmentalPermit` | 42 to 65 (47 already live for 3 layers) |
| B2 | 3 | 128 | `kartta.hel.fi` WFS GetFeature, points and areas | `PointOfInterest`, custom `HeritageArea` (closest SDM `GreenspaceRecord`) | `HeritageArea` | 66, 74, 80 |
| B1 | 2 | 130 | one-shot file import: a JSON pilot dump and a yearly CSV per counting point | `TrafficFlowObserved` | none | 1, 10 |
| B3 | 3 | 133 | `kartta.hel.fi` WFS GetFeature paged by area, and one CSV with a projection step | `RoadSegment`, `RoadAccident` | `RoadSegment`, `RoadAccident` | 5, 11, 14 |

- **F1** is a fix, not a build: one cause per pipeline, so it is one task whatever its row count.
  It needs the deployer (pipeline run logs on dev), then a fix in the deployment repository.
- **T-5286, T-5378, T-5256** are kept as they are, with one addition: row 14 (winter maintenance
  network, a `kartta.hel.fi` `RoadSegment` layer, deferred by T-5254) joins T-5286 beside row 5.
  All three stay blocked until each layer has a fixture recorded from the cluster:
  one `GetFeature ... &count=20` per layer, run by the deployer from a dev pod and committed under
  `tests/fixtures/helsinki/kartta/`, as T-5286 already describes. Section 9.2 shows the host answers dev.
- **B3** takes what T-5286 left (2026-10-26): the road map (row 5, 111404 segments) and the winter
  maintenance network (row 14) need a WFS read paged by area, more than one pipeline run holds at
  ~10 KB per entity; the accident CSV (row 11) is in ETRS-GK25 (EPSG:3879), which a Bloblang mapping
  cannot project. Fixtures of rows 5 and 14 are recorded (T-5668).
- **B2** and **B1** are new; the supervisor files them. B2 has the same fixture need as the three
  parked batches.

The batch list goes to the supervisor as a note (T-5663); every row id above is in section 9.5.
`scripts/check-helsinki-open-data.py check` proves the counts of sections 9.3 and 10 from the table,
and `scripts/check-helsinki-open-data.py probe` re-reads 10 sampled usable rows and fails on a dead one.

## Related

- [Open data integration rules](../Development/12-open-data-integration.md) — the rules this inventory follows.
- [Open data sources of Žilina](zilina-open-data-sources.md) — the same survey for Žilina.
- [Representation contract](../API/11-representation-contract.md) — what each output in section 4 is.
- [Open data catalogue](../Architecture/21-open-data-catalogue.md) — how a project publishes into CKAN.
