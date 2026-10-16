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
| organization | datasets | mapped | already NGSI-LD | not ingestible | no data source | source rows of the mapped |
|---|---:|---:|---:|---:|---:|---:|
| banskabystrica | 34 | 30 | 2 | 1 | 1 | 302649 |
| bbsk | 90 | 88 | 2 | 0 | 0 | 252024 |
| all | 124 | 118 | 4 | 1 | 1 | 554673 |
<!-- /totals -->

"Already NGSI-LD" are the four datasets the platform publishes from its own public Endpoints
(`generated_by: jcctl/ckan-publisher`). They need nothing. "Source rows" is the row count the
probe read from each mapped source, before any row filter of section 5.

## 3. Types

<!-- types -->
| NGSI-LD type | Smart Data Model | datasets | source rows |
|---|---|---:|---:|
| `StatisticalObservation` | project type | 37 | 43640 |
| `LandUsePlanFeature` | project type | 7 | 118714 |
| `PointOfInterest` | `dataModel.PointOfInterest/PointOfInterest` | 6 | 4468 |
| `School` | project type | 6 | 1480 |
| `AdministrativeArea` | project type | 4 | 1053 |
| `RoadStructure` | project type | 4 | 8981 |
| `Grant` | project type | 3 | 19845 |
| `OrganizationUnit` | project type | 3 | 883 |
| `PublicInvestment` | project type | 3 | 6200 |
| `Bridge` | project type | 2 | 2682 |
| `Contract` | project type | 2 | 25045 |
| `CouncilMeeting` | project type | 2 | 1509 |
| `CouncilMember` | project type | 2 | 260 |
| `CycleRoute` | project type | 2 | 1005 |
| `PublicOrganization` | project type | 2 | 231 |
| `PublicProcurement` | project type | 2 | 10665 |
| `PurchaseOrder` | project type | 2 | 45758 |
| `RoadAccident` | `dataModel.Transportation/RoadAccident` | 2 | 3127 |
| `WaterBodyStatus` | project type | 2 | 612 |
| `Address` | project type | 1 | 16902 |
| `AddressPoint` | project type | 1 | 15769 |
| `Article` | project type | 1 | 1557 |
| `Building` | project type | 1 | 16534 |
| `CouncilVote` | project type | 1 | 89670 |
| `EVChargingStation` | `dataModel.Transportation/EVChargingStation` | 1 | 606 |
| `Event` | project type | 1 | 6164 |
| `Footway` | project type | 1 | 2615 |
| `GreenArea` | project type | 1 | 8546 |
| `GreenAreaBoundary` | project type | 1 | 9740 |
| `Invoice` | project type | 1 | 28844 |
| `ParkingArea` | project type | 1 | 535 |
| `Petition` | project type | 1 | 12 |
| `Regulation` | project type | 1 | 34 |
| `RiverBasin` | project type | 1 | 3 |
| `Road` | project type | 1 | 1050 |
| `RoadSegment` | project type | 1 | 6338 |
| `SocialService` | project type | 1 | 740 |
| `StreetlightPole` | project type | 1 | 1522 |
| `Supplier` | project type | 1 | 5066 |
| `TerrainFeature` | project type | 1 | 36062 |
| `TrafficFlowObservedSite` | project type | 1 | 13 |
| `TrafficSign` | project type | 1 | 1700 |
| `Tree` | project type | 1 | 8366 |
| `WaterBody` | project type | 1 | 127 |
<!-- /types -->

A Smart Data Model is named only where its attributes match the columns: `EVChargingStation`,
`RoadAccident` and `PointOfInterest`. The census, migration, age-structure,
climate-risk and payment-per-district tables become the `StatisticalObservation` type, named
like the class the `bbsk-kraj` model holds, one entity per area and year. `Bridge`,
`School`, `PublicOrganization`, `SocialService` and `AdministrativeArea` share their names with
the `bbsk-registre` classes, so an assistant that knows one knows the other. The other project types are new classes for the space's one model
(DM-61), each named after what one row is.

Each mapped entry lists its `properties`: the attribute name, in ASCII lowerCamelCase, the
column it reads and its `range` (`integer`, `float`, `date`, `datetime`, `uri` or `string`),
taken from the source's own field type. Two columns that fold to one name take a number after
the second. A column named like an NGSI-LD core member (`id`, `type`, `location`, ...)
keeps its value as `source<Name>`. Esri bookkeeping columns (`OBJECTID`, `GlobalID`,
`Shape__Area`, `Shape__Length`) are left out. A layer's geometry becomes `location`.

## 4. Entity ids

<!-- ids -->
| entity id from | datasets |
|---|---:|
| a key column | 77 |
| a key column and its year | 7 |
| a row hash | 34 |
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
| `bb-dtm-bb-register-adries` | columns `POINT_X`, `POINT_Y` | the point in S-JTSK; the location carries it in WGS 84 |
| `bb-dtm-bb-register-chodnikov-a-verejnych-priestranstiev` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-miestnych-komunikacii-a-vyssich-tried` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-statickej-dopravy` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-stlpov-vo` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-verejnej-zelene-1` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-verejnej-zelene-2` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-verejnej-zelene-3` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-register-zvisleho-dopravneho-znacenia` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-vodne-toky-a-plochy` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-dtm-bb-vyskopis-teran` | columns `ideditora`, `vkladosoba`, `zmenaosoba`, `created_user`, `last_edited_user` | who entered or edited a feature: an editor's name or account |
| `bb-zmluvy-bb` | rows whose `Zmluvné_strany_s_údajom_IČO` does not match `^IČO:[^\r]*(\rIČO:[^\r]*)*$` | a party without an IČO is a natural person, a social-service client among them |
| `bbsk-clenovia-samospravy-efc2f3` | columns `Telefonický_kontakt`, `Emailový_kontakt` | office holders' own phones and e-mails |
| `bbsk-dodavatelia-825cd0` | rows outside `ICO IS NOT NULL AND ICO <> ''`, or rows whose `ICO` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a row without an IČO, or with a name where the IČO belongs, can name a natural person |
| `bbsk-dotacie-bada80` | rows outside `IČO IS NOT NULL AND IČO <> ''`, or rows whose `IČO` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a row without an IČO, or with a name where the IČO belongs, can name a natural person |
| `bbsk-faktury-422b35` | rows outside `IČO IS NOT NULL AND IČO <> ''`, or rows whose `IČO` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a row without an IČO, or with a name where the IČO belongs, can name a natural person |
| `bbsk-komisie-zastupitelstva-banskobystrickeho-samospravneho-kraja-59b9e4` | columns `Meno` | committees seat citizens who hold no office; the seats stay, the names do not |
| `bbsk-kontakty-na-miestne-samospravy-v-bbk-fc5ecb` | columns `Starosta`, `Telefónne_číslo___starosta`, `E_mail___starosta`, `Zástupca_primátora`, `E_mail___zástupca_primátora` | mayors' own contacts; the offices' general ones stay |
| `bbsk-objednavky-a97e8a` | rows outside `IČO IS NOT NULL AND IČO <> ''`, or rows whose `IČO` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a row without an IČO, or with a name where the IČO belongs, can name a natural person |
| `bbsk-organizacna-struktura-40329b` | columns `Priezvisko`, `Meno`, `Titul_pred_menom`, `Titul_za_menom`, `Telefon`, `Mobil`, `Email` | employees' names and contacts; the units and functions stay |
| `bbsk-zmluvy-cafee6` | rows outside `IČO_dodávateľa IS NOT NULL AND IČO_dodávateľa <> ''`, or rows whose `IČO_dodávateľa` does not match `^[0-9]{6,8}( ?[0-9]{4})?$` | a contract whose supplier has no IČO, or a name where the IČO belongs, can name a natural person |
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

## 6. Not ingestible, and already in NGSI-LD

<!-- refused -->
| dataset | organization | status | reason |
|---|---|---|---|
| Banská Bystrica — verejné údaje (`banskabystrica-verejne`) | banskabystrica | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| DTM_BB-Polohopis_a_vyskopis_bodoveho_pola (`bb-dtm-bb-polohopis-a-vyskopis-bodoveho-pola`) | banskabystrica | not-ingestible | 240638 rows, more than the 100000 this round loads into the one broker |
| DTM_BB-register-vodorovneho-dopravneho-znacenia (`bb-dtm-bb-register-vodorovneho-dopravneho-znacenia`) | banskabystrica | no-data-source | a ZIP of 1 .pdf (193 KiB): a PDF map sheet, and no layer of the city's ArcGIS services holds its data |
| Kvalita ovzdušia v Banskej Bystrici (`public-air`) | banskabystrica | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Ukazovatele kraja (`bbsk-kpi`) | bbsk | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
| Registre kraja (`bbsk-registre`) | bbsk | already-ngsi-ld | published by the platform from its own public Endpoint (jcctl ckan-publisher) |
<!-- /refused -->

Most DTM ZIPs of the city hold one PDF map sheet, and the shapefile ZIP of `DTM_BB-register
verejnej zelene 2` has every member encrypted. The data behind them sits in the city's public
ArcGIS Server (`dtm-banskabystrica.tmapserver.sk/arcgis/rest/services`, found 2026-10-16, T-4317):
the DTM service `dtm/DTM_v_1_4_2_3_verejny` (247 layers) and 14 land-use plan (ÚPN) services
under `up/`. Each of these datasets reads the layers its sheet draws (`LAYERS` in the script,
`source.kind: esri-layers`). The server answers GeoJSON in WGS 84 itself (`outSR=4326`) in pages of
at most 2000 rows. The probe of those layers is `Research/data/bb-dtm-layers.json`. The cadastral
map that each ÚPN service draws underneath (`vnutorná kresba`, `hranice parcel`, 295 000 lines,
the ÚGKK's data and not the city's) is no layer of any dataset. A layer that two sheets draw is
read once. The terms of use of each dataset's record in the national catalogue
(`data.gov.sk/def/ontology/legislation/termsOfUse`) are CC BY-SA 4.0. The service states no terms
of its own, so the record's licence applies to the layers of that dataset. The registers of
addresses, buildings and streets keep their archive: its GeoJSON carries the register columns,
which the layers lack, and the pipeline reprojects it from S-JTSK. The horizontal road markings
have a sheet and no layer. The survey points (240 638 in layer 1) stay over the row limit below.

Decided (worker-8, owner may override): a source over 100 000 rows or a GeoJSON over 10 MiB is
not loaded in this round, because one broker on one 16 GB node holds every project. Options: load
the terrain model now, or as one aggregate per cadastral area.

## 7. Datasets a seed already reads

<!-- existing -->
| dataset | seed that already reads it | covers |
|---|---|---|
| `bb-podujatia` | `banskabystrica/datasource-podujatia.yaml` | whole |
| `bbsk-mosty-v-banskobystrickom-kraji-public-view-3b4675` | `bbsk/bbsk-datasource-mosty.yaml` | whole |
| `bbsk-obce-bbk-hranice-ec7ac6` | `bbsk/bbsk-datasource-obce.yaml` | whole |
| `bbsk-okresy-bbk-hranice-17725f` | `bbsk/bbsk-datasource-okresy.yaml` | whole |
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
