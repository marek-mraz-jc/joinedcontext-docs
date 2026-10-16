---
sidebar_position: 13
title: "Banská Bystrica and BBSK Datasets in NGSI-LD"
description: Every dataset of the CKAN organizations banskabystrica and bbsk on data.dev, read through the CKAN API and probed resource by resource on 2026-10-16, with the NGSI-LD type each one becomes or the reason it cannot.
---

# Banská Bystrica and BBSK datasets in NGSI-LD

The public assistant answers from the context data, so a dataset it should know has to be in
NGSI-LD first. This page lists every dataset the data portal holds for the city of Banská Bystrica
(`banskabystrica`) and the Banská Bystrica Self-Governing Region (`bbsk`). For each one it gives
the type, the entity id rule, the space and the refresh interval. A dataset left out carries its
reason. The seed generator of T-4255 reads the machine form of this page,
`Research/bb-bbsk-ngsi-ld-mapping.yaml`. Read this page before you change that generator or ask
why the assistant cannot answer about a dataset.

## 1. How the numbers were made

`scripts/bb-bbsk-ngsi-ld-mapping.py` builds everything here in three steps, and CI repeats the
check offline.

| step | what it reads | what it writes |
|---|---|---|
| `snapshot` | `package_search?fq=organization:{org}&rows=1000` on `https://data.dev.joinedcontext.com` | `Research/data/bb-bbsk-ckan.json` |
| `probe` | one request per resource: the Esri layer's `?f=json` and its count, the CKAN DataStore's fields and total, a ZIP's central directory (a ranged GET), a JSON feed's first page | `Research/data/bb-bbsk-probe.json` |
| `draft` | both snapshots and the rules at the top of the script (`TYPES`, `DROP`, `ROWS`, `EXISTING`) | the mapping file and every table on this page |

`check` runs in the docs `ci` lane. It fails when the mapping misses a dataset id of the snapshot,
names one the snapshot lacks, refuses a dataset without a reason, or when a table on this page
differs from what the mapping gives. The `fetched` member of each snapshot holds its time. To
refresh them, run the three steps in order and commit the five files together.

The probe read the Hub's CSV and GeoJSON exports of a BBSK layer through the layer itself, not
through the export URL. The Hub builds an export on its first request, and the layer answers the
same rows.

## 2. Totals

<!-- totals -->
| organization | datasets | mapped | already NGSI-LD | not ingestible | removed (no model) | source rows of the mapped |
|---|---:|---:|---:|---:|---:|---:|
| banskabystrica | 34 | 5 | 2 | 22 | 5 | 23930 |
| bbsk | 90 | 57 | 2 | 0 | 31 | 59501 |
| all | 124 | 62 | 4 | 22 | 36 | 83431 |
<!-- /totals -->

"Already NGSI-LD" are the four datasets the platform publishes from its own public Endpoints
(`generated_by: jcctl/ckan-publisher`). They need nothing. "Source rows" is the row count the
probe read from each mapped source, before any row filter of section 5.

## 3. Types

<!-- types -->
| NGSI-LD type | Smart Data Model (the schema read) | datasets | source rows |
|---|---|---:|---:|
| `KeyPerformanceIndicator` | [`dataModel.KeyPerformanceIndicator/KeyPerformanceIndicator`](https://raw.githubusercontent.com/smart-data-models/dataModel.KeyPerformanceIndicator/ec7f3b642faf3f807d3c8549ccc9e0b743e05f26/KeyPerformanceIndicator/schema.json) | 37 | 43640 |
| `Organization` | [`dataModel.Organization/Organization`](https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/77a4911e7cbc72bf87bf202ade282c1bc41a36a4/Organization/schema.json) | 9 | 7415 |
| `PointOfInterest` | [`dataModel.PointOfInterest/PointOfInterest`](https://raw.githubusercontent.com/smart-data-models/dataModel.PointOfInterest/7e5e24963a142b9bf6fd15b144a0e24588217608/PointOfInterest/schema.json) | 9 | 5827 |
| `PublicOrganization` | [`dataModel.CPSV-AP/PublicOrganization`](https://raw.githubusercontent.com/smart-data-models/dataModel.CPSV-AP/a05d1663475fc0f79361bc9bc2550c3f24df1ba0/PublicOrganization/schema.json) | 2 | 231 |
| `RoadAccident` | [`dataModel.Transportation/RoadAccident`](https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/b83ede9d3db29be1365cc272eb535f46af83bed2/RoadAccident/schema.json) | 2 | 3127 |
| `Address` | [`dataModel.CPSV-AP/Address`](https://raw.githubusercontent.com/smart-data-models/dataModel.CPSV-AP/a05d1663475fc0f79361bc9bc2550c3f24df1ba0/Address/schema.json) | 1 | 16902 |
| `Event` | [`dataModel.TourismDestinations/Event`](https://raw.githubusercontent.com/smart-data-models/dataModel.TourismDestinations/6d78cb4ff0c1a7d16dc0c1bab7266e40d4b3a00c/Event/schema.json) | 1 | 6164 |
| `Person` | [`dataModel.Organization/Person`](https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/77a4911e7cbc72bf87bf202ade282c1bc41a36a4/Person/schema.json) | 1 | 125 |
<!-- /types -->

Every mapped dataset is in a published FIWARE Smart Data Model, or it leaves data.dev (owner,
2026-10-16, T-4319). A model is named only after its `schema.json` was opened at the commit the
link pins. The type is the model's entity type, and a column the model has an attribute for takes
the model's name:

- `name`: the place's, school's or office's own name.
- `legalName`: the registered name.
- `preferredLabel` and `spatial` of CPSV-AP's `PublicOrganization`.
- `thoroughfare`, `addressArea` and `postName` of CPSV-AP's `Address`.
- `url` and `description` of an `Event`.

The census, migration, age-structure, climate-risk and payment-per-district tables become
`KeyPerformanceIndicator`, one entity per area and year. The other columns keep their own names
beside the model's: every one of these schemas allows additional properties. A CPSV-AP list
attribute, or a `PointOfInterest`'s `category` (`range: string-list`), carries the column as a
one-item list. An attribute a model requires that no column holds is the same on every entity
of the type, under `constants`: a `RoadAccident` is `status: archived`, an accident the police
closed and published. The tourism portal's charging-and-stop layer has no socket, capacity or
vehicle column, which `EVChargingStation` requires, so its rows are `PointOfInterest`. A model
attribute whose column is empty in some rows names the columns read next under `otherwise`: a
health facility without a name of its own takes its provider's, a tourism-portal place without
`PRIM_NAME` its category.

A type no published model holds is `status: removed` in section 6. Its reason names the models
opened and why none fits, so the dataset can come back when one is published. We do not write
our own models: "smart data model" means one published in smart-data-models.

Each mapped entry lists its `properties`: the attribute name, in ASCII lowerCamelCase, the
column it reads and its `range` (`integer`, `float`, `date`, `datetime`, `uri`, `string` or `string-list`),
taken from the source's own field type. Two columns that fold to one name take a number after
the second. A column named like an NGSI-LD core member (`id`, `type`, `location`, ...)
keeps its value as `source<Name>`. Esri bookkeeping columns (`OBJECTID`, `GlobalID`,
`Shape__Area`, `Shape__Length`) are left out. A layer's geometry becomes `location`.

## 4. Entity ids

<!-- ids -->
| entity id from | datasets |
|---|---:|
| a key column | 43 |
| a key column and its year | 8 |
| a row hash | 11 |
<!-- /ids -->

A key column is one whose distinct count, asked of the source, equals the row count. The probe
pages through the Esri layer's distinct values (`returnDistinctValues=true`) and counts them,
and asks the CKAN DataStore (`datastore_search?distinct=true`) or the loaded GeoJSON. ArcGIS
Online answers `returnCountOnly=true` with the plain row count even when distinct values are
asked for. That once passed `Číslo` and `Rok` of the BBSK grants as a key, although 4775 rows
held 3905 values. When no single column is unique, the
probe tries each id-like column with the table's year column. A WordPress post's `id` is unique
by definition. The rest have no stable key, and the mapping says `rowHash: true`.

A row hash changes whenever a value in the row changes, so a corrected row arrives as a new
entity and the old one stays. Expiry (PL-64) cannot clear it, because several pipelines write
the same space. Most row-hash datasets are registers and tables their publisher seldom revises.
A stale copy stays until a person removes it, and the entity's `dataset` property names where
the current rows are.

## 5. Personal data kept out

<!-- personal -->
| dataset | kept out | why |
|---|---|---|
| `bbsk-clenovia-samospravy-efc2f3` | columns `Telefonický_kontakt`, `Emailový_kontakt` | office holders' own phones and e-mails |
| `bbsk-dodavatelia-825cd0` | rows outside `ICO IS NOT NULL AND ICO <> ''`, or rows whose `ICO` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a row without an IČO, or with a name where the IČO belongs, can name a natural person |
| `bbsk-kontakty-na-miestne-samospravy-v-bbk-fc5ecb` | columns `Starosta`, `Telefónne_číslo___starosta`, `E_mail___starosta`, `Zástupca_primátora`, `E_mail___zástupca_primátora` | mayors' own contacts; the offices' general ones stay |
| `bbsk-nabijacky-a-zastavky-937210` | rows outside `Categ IS NOT NULL AND Categ <> ''` | three rows of the layer hold nothing but a point, no name and no category |
| `bbsk-organizacna-struktura-40329b` | columns `Priezvisko`, `Meno`, `Titul_pred_menom`, `Titul_za_menom`, `Telefon`, `Mobil`, `Email` | employees' names and contacts; the units and functions stay |
| `bbsk-zoznam-poskytovatelov-socialnych-sluzieb-v-bbk-9ab090` | rows outside `Typ_poskytovateľa <> 'neverejný poskytovateľ'` | a private provider can be a natural person; bbsk-datasource-socialne-sluzby applies the same filter |
| `bbsk-zoznam-zdravotnickych-zariadeni-v-bbk-701db2` | columns `Odborný_zástupca` | the named physician of each facility |
<!-- /personal -->

Office holders keep their name and function, which Act 211/2000 makes public. Their own phones and
e-mails stay out, and so does every employee's or appointed citizen's name. The city's
`Objednávky`, `Zmluvy` and `Dotácie` were filtered by the harvest itself (T-4151): their
DataStore tables already hold only the rows with an IČO. A row filter is written as an Esri
`where` clause, so the generator can send it with the layer query and the rows never leave the
source. The `Evidencia psov` and `Zoznam poskytovateľov pre APS` datasets never reached CKAN
([sources §8](banska-bystrica-open-data-sources.md#8-personal-data-found-in-published-datasets)).

## 6. Not ingestible, removed, and already in NGSI-LD

<!-- refused -->
| dataset | organization | status | reason |
|---|---|---|---|
| Banská Bystrica — verejné údaje (`banskabystrica-verejne`) | banskabystrica | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Aktuality (`bb-aktuality`) | banskabystrica | removed | no smart data model: no subject of the official list (2026-07-19) holds news articles |
| Dotácie (`bb-dotacie`) | banskabystrica | removed | no smart data model: no subject of the official list (2026-07-19) holds grants or subsidies |
| DTM_BB-funkcne-vyuzitie-uzemia (`bb-dtm-bb-funkcne-vyuzitie-uzemia`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (201 KiB): a PDF map sheet, no data |
| DTM_BB-Polohopis_a_vyskopis_bodoveho_pola (`bb-dtm-bb-polohopis-a-vyskopis-bodoveho-pola`) | banskabystrica | not-ingestible | 240636 Point features in S-JTSK (EPSG:5514): NGSI-LD locations are WGS 84 and no pipeline step reprojects; without the geometry the rows carry little (the city's address list without points is bb-adresy) |
| DTM_BB-Register-adries (`bb-dtm-bb-register-adries`) | banskabystrica | not-ingestible | 15769 Point features in S-JTSK (EPSG:5514): NGSI-LD locations are WGS 84 and no pipeline step reprojects; without the geometry the rows carry little (the city's address list without points is bb-adresy) |
| DTM_BB-register-chodnikov-a-verejnych-priestranstiev (`bb-dtm-bb-register-chodnikov-a-verejnych-priestranstiev`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-register-miestnych-komunikacii-a-vyssich-tried (`bb-dtm-bb-register-miestnych-komunikacii-a-vyssich-tried`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-register-statickej-dopravy (`bb-dtm-bb-register-statickej-dopravy`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-register-stavby (`bb-dtm-bb-register-stavby`) | banskabystrica | not-ingestible | 16534 MultiPolygon features in S-JTSK (EPSG:5514): NGSI-LD locations are WGS 84 and no pipeline step reprojects; without the geometry the rows carry little (the city's address list without points is bb-adresy) |
| DTM_BB-register-stlpov-VO (`bb-dtm-bb-register-stlpov-vo`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (185 KiB): a PDF map sheet, no data |
| DTM_BB-register-ulic (`bb-dtm-bb-register-ulic`) | banskabystrica | not-ingestible | 6338 MultiLineString features in S-JTSK (EPSG:5514): NGSI-LD locations are WGS 84 and no pipeline step reprojects; without the geometry the rows carry little (the city's address list without points is bb-adresy) |
| DTM_BB-register-verejnej-zelene-1 (`bb-dtm-bb-register-verejnej-zelene-1`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (43 KiB): a PDF map sheet, no data |
| DTM_BB-register-verejnej-zelene-2 (`bb-dtm-bb-register-verejnej-zelene-2`) | banskabystrica | not-ingestible | a ZIP of 3 .atr, 3 .cpg, 3 .dbf, 3 .shp, 3 .shx (732 KiB): Esri shapefiles; no ingestion path reads a shapefile today |
| DTM_BB-register-verejnej-zelene-3 (`bb-dtm-bb-register-verejnej-zelene-3`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (194 KiB): a PDF map sheet, no data |
| DTM_BB-register-vodorovneho-dopravneho-znacenia (`bb-dtm-bb-register-vodorovneho-dopravneho-znacenia`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-register-zvisleho-dopravneho-znacenia (`bb-dtm-bb-register-zvisleho-dopravneho-znacenia`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-regulativy-a-limity-funkcneho-vyuzitia-uzemia (`bb-dtm-bb-regulativy-a-limity-funkcneho-vyuzitia-uzemia`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (205 KiB): a PDF map sheet, no data |
| DTM_BB-tvorba-krajiny-a-ochrana-prirody (`bb-dtm-bb-tvorba-krajiny-a-ochrana-prirody`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-verejne-dopravne-a-technicke-vybavenie (`bb-dtm-bb-verejne-dopravne-a-technicke-vybavenie`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (198 KiB): a PDF map sheet, no data |
| DTM_BB-verejnoprospesne-stavby (`bb-dtm-bb-verejnoprospesne-stavby`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (197 KiB): a PDF map sheet, no data |
| DTM_BB-vodne-toky-a-plochy (`bb-dtm-bb-vodne-toky-a-plochy`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, no data |
| DTM_BB-vyskopis-teran (`bb-dtm-bb-vyskopis-teran`) | banskabystrica | not-ingestible | a ZIP of 1 .geojson (65889 KiB): larger than the 10 MiB this round loads into the one broker |
| DTM_BB-vyuzitie-pody-na-nepolnohospodarske-ucely (`bb-dtm-bb-vyuzitie-pody-na-nepolnohospodarske-ucely`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (197 KiB): a PDF map sheet, no data |
| DTM_BB-zaujmove-uzemie-a-sirsie-vztahy (`bb-dtm-bb-zaujmove-uzemie-a-sirsie-vztahy`) | banskabystrica | not-ingestible | a ZIP of 1 .pdf (24 KiB): a PDF map sheet, no data |
| Objednávky BB (`bb-objednavky-bb`) | banskabystrica | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Zasadnutia orgánov samosprávy (`bb-zasadnutia-organov-samospravy`) | banskabystrica | removed | no smart data model: no subject holds council meetings, votes, petitions or regulations; CPSV-AP has PublicService, BusinessEvent and LifeEvent |
| Zmluvy BB (`bb-zmluvy-bb`) | banskabystrica | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Kvalita ovzdušia v Banskej Bystrici (`public-air`) | banskabystrica | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Cykloturistické trasy - línie (`bbsk-cykloturisticke-trasy-linie-e6a1a7`) | bbsk | removed | no smart data model: OpenStreetMap/OSMCycleRoute requires osmId and osmType; Transportation/BikeLane is a lane, not a touring route |
| Cykloturistické trasy - línie - povrchy (`bbsk-cykloturisticke-trasy-linie-povrchy-2ec670`) | bbsk | removed | no smart data model: OpenStreetMap/OSMCycleRoute requires osmId and osmType; Transportation/BikeLane is a lane, not a touring route |
| Dilatačné celky v Banskobystrickom kraji (public view) (`bbsk-dilatacne-celky-v-banskobystrickom-kraji-public-view-6ff77a`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads, not underpasses, culverts, expansion joints or level crossings |
| Dotácie (`bbsk-dotacie-bada80`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds grants or subsidies |
| Ekologický potenciál vodných útvarov (`bbsk-ekologicky-potencial-vodnych-utvarov-672eca`) | bbsk | removed | no smart data model: WaterQuality/WaterQualityObserved and Environment/WaterObserved require dateObserved and location and hold measured parameters; these rows are ecological status classes |
| Ekologický stav vodných útvarov (`bbsk-ekologicky-stav-vodnych-utvarov-48bbbd`) | bbsk | removed | no smart data model: WaterQuality/WaterQualityObserved and Environment/WaterObserved require dateObserved and location and hold measured parameters; these rows are ecological status classes |
| Faktúry (`bbsk-faktury-422b35`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Hlasovania poslancov (`bbsk-hlasovania-poslancov-ba7ca6`) | bbsk | removed | no smart data model: no subject holds council meetings, votes, petitions or regulations; CPSV-AP has PublicService, BusinessEvent and LifeEvent |
| Komisie zastupiteľstva Banskobystrického samosprávneho kraja (`bbsk-komisie-zastupitelstva-banskobystrickeho-samospravneho-kraja-59b9e4`) | bbsk | removed | no smart data model: Organization/Person is a person; a seat whose holder's name is kept out is none |
| Ukazovatele kraja (`bbsk-kpi`) | bbsk | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Kraj BBK - hranica (`bbsk-kraj-bbk-hranica-a05568`) | bbsk | removed | no smart data model: OpenStreetMap/OSMBoundary requires osmId and osmType; these boundaries come from the region's register, not OpenStreetMap |
| Mosty v Banskobystrickom kraji (public view) (`bbsk-mosty-v-banskobystrickom-kraji-public-view-3b4675`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads; RoadSegment requires refRoad, startPoint and endPoint, which a bridge register has not |
| Mosty v správe BBRSC (public view) (`bbsk-mosty-v-sprave-bbrsc-public-view-d3252c`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads; RoadSegment requires refRoad, startPoint and endPoint, which a bridge register has not |
| Obce BBK - centroidy (`bbsk-obce-bbk-centroidy-cbd19f`) | bbsk | removed | no smart data model: OpenStreetMap/OSMBoundary requires osmId and osmType; these boundaries come from the region's register, not OpenStreetMap |
| Obce BBK - hranice (`bbsk-obce-bbk-hranice-ec7ac6`) | bbsk | removed | no smart data model: OpenStreetMap/OSMBoundary requires osmId and osmType; these boundaries come from the region's register, not OpenStreetMap |
| Objednávky (`bbsk-objednavky-a97e8a`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Okresy BBK - hranice (`bbsk-okresy-bbk-hranice-17725f`) | bbsk | removed | no smart data model: OpenStreetMap/OSMBoundary requires osmId and osmType; these boundaries come from the region's register, not OpenStreetMap |
| Petície (`bbsk-peticie-f80530`) | bbsk | removed | no smart data model: no subject holds council meetings, votes, petitions or regulations; CPSV-AP has PublicService, BusinessEvent and LifeEvent |
| Plán verejného obstarávania (`bbsk-plan-verejneho-obstaravania-48b7e9`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Podjazdy v Banskobystrickom kraji (public view) (`bbsk-podjazdy-v-banskobystrickom-kraji-public-view-e6fb8f`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads, not underpasses, culverts, expansion joints or level crossings |
| Povodia Banskobystrického kraja (`bbsk-povodia-banskobystrickeho-kraja-067504`) | bbsk | removed | no smart data model: OpenStreetMap/OSMWater requires osmId and osmType; the basins come from the region's register |
| PPA platby (`bbsk-ppa-platby-f3c509`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds grants or subsidies |
| Priepusty v Banskobystrickom kraji (public view) (`bbsk-priepusty-v-banskobystrickom-kraji-public-view-a9ed8e`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads, not underpasses, culverts, expansion joints or level crossings |
| Projekty Banskobystrického kraja ITMS21 (`bbsk-projekty-banskobystrickeho-kraja-itms21-c8bfea`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds public investment projects |
| Realizované verejné obstarávania (`bbsk-realizovane-verejne-obstaravania-754eee`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Register investícií - bodová vrstva (`bbsk-register-investicii-bodova-vrstva-e0b3b4`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds public investment projects |
| Register investícií - polygónová vrstva (`bbsk-register-investicii-polygonova-vrstva-e902a9`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds public investment projects |
| Registre kraja (`bbsk-registre`) | bbsk | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Úradné hodiny (`bbsk-uradne-hodiny-c912ed`) | bbsk | removed | no smart data model: a row is one office's hours on one weekday; no model holds an opening slot as an entity |
| Zasadnutia samosprávy (`bbsk-zasadnutia-samospravy-9a27f2`) | bbsk | removed | no smart data model: no subject holds council meetings, votes, petitions or regulations; CPSV-AP has PublicService, BusinessEvent and LifeEvent |
| Železničné priecestia v Banskobystrickom kraji (public view) (`bbsk-zeleznicne-priecestia-v-banskobystrickom-kraji-public-view-89feb8`) | bbsk | removed | no smart data model: Transportation/Road and RoadSegment describe roads, not underpasses, culverts, expansion joints or level crossings |
| Zmluvy (`bbsk-zmluvy-cafee6`) | bbsk | removed | no smart data model: no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement |
| Zoznam účinných všeobecne záväzných nariadení (VZN) (`bbsk-zoznam-ucinnych-vseobecne-zavaznych-nariadeni-vzn-80db50`) | bbsk | removed | no smart data model: no subject holds council meetings, votes, petitions or regulations; CPSV-AP has PublicService, BusinessEvent and LifeEvent |
<!-- /refused -->

Most DTM ZIPs of the city hold one PDF map sheet and no data. `DTM_BB-register verejnej zelene 2`
holds shapefiles, and no ingestion path reads a shapefile today. The GeoJSON registers of
addresses, buildings, streets and survey points are drawn in S-JTSK, and no pipeline step
reprojects to the WGS 84 that NGSI-LD requires. The terrain model is the largest source of both organizations.
It waits for a later round, after the integrator has read the broker's volume use with the rest
loaded
([integration rules §4](../Development/12-open-data-integration.md#4-capacity-on-one-node)).

Decided (worker-8, owner may override): a source over 100 000 rows or a GeoJSON over 10 MiB is
not loaded in this round, because one broker on one 16 GB node holds every project. Options: load
the terrain model now, or as one aggregate per cadastral area.

A `removed` dataset is mapped to nothing and leaves data.dev: its catalogue row is hidden by the
publish gate (T-4318), the seed generator writes no pipeline for it, and its entities are deleted
from the open-data space once no pipeline writes them (T-4319). A `not-ingestible` dataset leaves
data.dev through the same gate, because the catalogue lists only data in NGSI-LD.

## 7. Datasets a seed already reads

<!-- existing -->
| dataset | seed that already reads it | covers |
|---|---|---|
| `bb-podujatia` | `banskabystrica/datasource-podujatia.yaml` | whole |
| `bbsk-organizacie-v-zriadovatelskej-posobnosti-bbsk-bc762a` | `bbsk/bbsk-datasource-organizacie.yaml` | whole |
| `bbsk-zoznam-poskytovatelov-socialnych-sluzieb-v-bbk-9ab090` | `bbsk/bbsk-datasource-socialne-sluzby.yaml` | whole |
| `bbsk-zoznam-zdravotnickych-zariadeni-v-bbk-701db2` | `bbsk/bbsk-datasource-nemocnice.yaml` | hospitals only |
<!-- /existing -->

T-4255 extends these DataSources or leaves them as they are, and never adds a second reader of
the same source. `bbsk-datasource-nemocnice` reads only the hospitals of the facilities layer.
The facilities of every kind are a new mapping onto `PointOfInterest`.

## 8. What the generator has to handle

- A BBSK layer is read with `outSR=4326`, so its geometry arrives in WGS 84, and in pages of the
  layer's `maxRecordCount` where it holds more rows.
- Every entity carries `dataProvider` (the CKAN `publisher_name`), `source` (the resource URL) and
  `dataset` (the CKAN dataset URL). The mapping holds all three per dataset
  ([integration rules §3](../Development/12-open-data-integration.md#3-what-each-dataset-becomes)).
- `refresh` follows the dataset's last change, because no harvested dataset carries a frequency.
  A dataset changed in the last 31 days is read daily (`P1D`), a yearly statistic monthly
  (`P1M`), anything else weekly (`P1W`). The city's two WordPress feeds are read daily.
- The space is a new public one per project, `banskabystrica-otvorene-data` and
  `bbsk-otvorene-data`. Each has one public Endpoint, which joins the project's public
  `otvorene-data` MCP server.

Decided (worker-8, owner may override): the mapped datasets go to a new space per project, not
into `banskabystrica-verejne` or `bbsk-registre`. A space has one closed model (DM-61). Several
mapped types share a name with a curated class there (`Bridge`, `School`, `AdministrativeArea`,
`StatisticalObservation`, `Event`), and a generated class of the same name would replace the
curated one's slots. Options: rename every generated type, or merge the columns into the curated
classes by hand.

## Related

- [Open data sources: Banská Bystrica region](banska-bystrica-open-data-sources.md) — the survey these two CKAN organizations were harvested from, and the personal-data findings of §8.
- [Open data integration rules](../Development/12-open-data-integration.md) — the five things a dataset becomes, the attribution rule and the capacity limit this mapping follows.
- [The Banská Bystrica contract](../Development/10-banska-bystrica-contract.md) — the projects, spaces and types the mapped datasets join.
- [Data models](../Architecture/11-data-models.md) — where the new project types are declared before a pipeline writes them.
- [Pipelines](../Architecture/08-pipelines.md) — how the generated DataSources and Pipelines fetch, map and write.
