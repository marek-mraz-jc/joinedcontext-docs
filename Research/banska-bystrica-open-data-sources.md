---
sidebar_position: 5
title: "Open Data Sources: Banská Bystrica Region"
description: Every candidate feed for the two Banská Bystrica projects and the public assistant, fetched on 2026-09-20 and again on 2026-10-15, with status codes, counts, quality problems and the ingestion plan.
---

# Open data sources of the Banská Bystrica region

Which published feeds the `bbsk` and `banskabystrica` projects can ingest, and which they cannot.
Read this before building a pipeline or naming a KPI: a KPI computed from a feed that does not
answer is a fabricated number on a dashboard shown to a region. Sections 1 to 5 were fetched with
`curl` on 2026-09-20 from the build sandbox. Sections 6 to 9 were fetched on 2026-10-15 for the
public assistant (`tasks/GOAL-assistant.md`) and correct what changed since. Nothing here is
quoted from a catalogue page without the endpoint itself answering.

## 1. Who publishes what

Four levels of publisher appear, and they are not interchangeable.

| level | body | territory | people |
|---|---|---|---|
| `region` | Banskobystrický samosprávny kraj (BBSK), IČO 37828100 | the whole kraj, NUTS `SK032`, 13 okresy | 607 581 at the end of 2025 |
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

**The region publishes nothing in NKOD.** A query for IČO 37828100 against the national catalogue returns
zero triples: BBSK has no dataset, no distribution and no publisher record in NKOD. It does publish
103 datasets on its own ArcGIS Hub, found on 2026-10-15 (section 6). The `bbsk`
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
| `om7102rr` | `SK032`, end of 2023, 2024 then 2025, both sexes | 614 356, 611 124, then 607 581 |
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
| BBSK open data | `https://www.bbsk.sk/` | 000, connection timed out after 25 s | the host did not answer. On 2026-10-15 it answers, with an incomplete certificate chain (section 7), and the region's data sits on `opendata.bbsk.sk` (section 6). BBSK also publishes nothing in NKOD (zero triples for IČO 37828100), so there is nothing behind it to ingest even when it answers. |
| City open data portal | `https://opendata.banskabystrica.sk/` | 000, connection timed out after 25 s | the host did not answer. The city's data is reachable through `egov.banskabystrica.sk` instead, which is what the catalogue records as the download URL. |
| Old national portal | `https://data.gov.sk/` | 000, connection timed out after 25 s | superseded by `data.slovensko.sk`. The `data.gov.sk` hostname survives only as the IRI namespace inside the catalogue's RDF, where it is an identifier and not an address. |
| SHMÚ air quality and hydrology | `https://www.shmu.sk/` | 000, connection timed out after 25 s | the publisher of the region's real air-quality observations did not answer. On 2026-10-15 `https://opendata.shmu.sk/` answers (section 6), which closes the gap of section 5. |
| ŽSR train timetable, GTFS | `https://www.zsr.sk/files/pre-cestujucich/cestovny-poriadok/gtfs/gtfs.zip` | 200, but `text/html` | the declared download URL serves an HTML page titled "ŽSR \| GTFS info", not the archive. The catalogue's own mirror below does serve the ZIP. |
| City open-data endpoint, licence check | the 43 datasets of IČO 00313271 | n/a | none of them carries `dct:license`. The licence is in the Slovak `legislation:termsOfUse` node instead, and it names the same licence for authors' work, original database and the database maker's special right: CC-BY-4.0 on the 21 tables and website feeds, CC-BY-SA-4.0 on the 22 DTM map datasets (re-read 2026-10-15, T-4151). A reader who looks only for `dct:license` will conclude, wrongly, that the city's data is unlicensed. |

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

## 6. Sources for the public assistant, 2026-10-15

The assistant needs two kinds of source: text it can quote with a link (the RAG index) and data it
can answer with current values and a dataset link (the data portal, reached through MCP). Every
row was fetched on 2026-10-15; every count is the field named in the `count from` column.

| source | publisher | API | URL fetched | status | count | count from | formats | licence | last update |
|---|---|---|---|---|---|---|---|---|---|
| City datasets in NKOD | `city` IČO 00313271 | SPARQL (DCAT-AP) | `https://data.slovensko.sk/api/sparql` | 200 | 43 datasets, 49 distributions | `COUNT(DISTINCT ?ds)` for publisher `legal-subject/00313271` | JSON (19 on `egov.banskabystrica.sk`, 2 on the website), ZIP of DBF/SHP (28 on `dtm-banskabystrica.tmapserver.sk`) | CC-BY-4.0 (21 datasets) and CC-BY-SA-4.0 (the 22 DTM map datasets) in `legislation:termsOfUse` (section 4) | `dct:modified` 2023-11-24 to 2026-01-15 |
| City website | `city` | WordPress REST | `https://www.banskabystrica.sk/wp-json/wp/v2/{type}?per_page=1` | 200 (the bare host 301s to `www.`) | 419 pages, 1 701 office announcements, 1 557 news, 6 162 events, 389 documents, 237 agendas, 233 regulations, 283 subsidies, 99 projects, 96 urban plans, 94 sessions, 55 office sections, 34 city documents, 24 procurements, 22 life situations, 6 emergency contacts, 30 830 media files | `X-WP-Total` header per type | JSON with HTML `content.rendered` | not stated; quoted with a link, never republished as a dataset | per item `modified` |
| BBSK open data | `region` IČO 37828100 | ArcGIS Hub (OGC API Records, DCAT feeds) | `https://opendata.bbsk.sk/api/search/v1/collections/dataset/items` | 200 | 103 datasets (98 Feature Service, 5 Shapefile) of 260 Hub items | `numberMatched` | CSV, GeoJSON, KML, Shapefile ZIP, ArcGIS REST; XLSX, GPKG, GDB on 53 | CC-BY-SA-4.0 83, CC-BY-4.0 6, CC-BY-NC-4.0 2, none 12 | `modified` 2024-07-22 to 2026-10-15 |
| BBSK DCAT feeds | `region` | DCAT-US 1.1, DCAT-AP 2.1.1 | `https://opendata.bbsk.sk/api/feed/dcat-us/1.1.json`, `.../dcat-ap/2.1.1.json` | 200 | 472 entries (one per layer) | `len(dataset)` | JSON-LD | per entry, 232 entries without one | `modified` years 2024: 23, 2025: 92, 2026: 357 |
| BBSK ArcGIS organization | `region` | ArcGIS REST | `https://services-eu1.arcgis.com/ODrCBoJHlKVMl3Cg/arcgis/rest/services?f=json` | 200 | 449 services | `len(services)` | Esri JSON, GeoJSON (`f=geojson`) | as the Hub item | per layer |
| BBSK website | `region` | sitemap | `https://www.bbsk.sk/sitemap.xml` | 200 with the intermediate certificate added (section 7) | 766 URLs, 758 allowed by `robots.txt` | `<loc>` elements | HTML | not stated; quoted with a link | not in the sitemap |
| SHMÚ weather, 1-minute stations | `national` SHMÚ | file server | `https://opendata.shmu.sk/meteorology/climate/now/data/{yyyymmdd}/aws1min - {timestamp}.json` | 200 with the intermediate added | 95 stations, 442 rows in the 2026-10-15 21:25 file | distinct `ind_kli` | JSON, one file per 5 minutes | CC-BY-4.0 (`README.txt`) | the newest file |
| SHMÚ air quality | `national` SHMÚ | EEA Air Quality Download Service | `https://opendata.shmu.sk/airQuality/recent/data/` names `https://eeadmz1-downloads-webapp.azurewebsites.net/` | 200 | not counted here | | Parquet, CSV | CC-BY-4.0 | hourly |
| Other publishers in NKOD | MV SR 6, GKÚ 2, MIRRI 2, MK SR 1, NPPC 1 | SPARQL | as above, titles matching Banská Bystrica or Banskobystrický | 200 | 12 datasets | `COUNT(DISTINCT ?ds)` per publisher | mixed | per dataset | |
| RÚVZ Banská Bystrica | `national` IČO 00606979 | SPARQL, files on `www.uvzsr.sk` | as above | 200 | 12 datasets, CSV invoices and orders 2021 to 2026 | `COUNT(DISTINCT ?ds)` | CSV | as NKOD | 2025-11-18 to 2026-03-19 |
| sensor.community | volunteers | REST | `https://data.sensor.community/airrohr/v1/filter/area=48.736,19.146,8` | 200 | 2 sensors (SDS011, DS18B20) within 8 km | distinct `sensor.id` | JSON | ODbL | live |

What the 2026-09-20 survey could not see: the region publishes 103 datasets of its own, the
city's website exposes all its content through an unauthenticated REST API, and SHMÚ answers. The
city portal `opendata.banskabystrica.sk` still times out (25 s, 2026-10-15). BBSK's Hub holds an
item titled "DCAT publikovanie NKOD", and none of its datasets reaches NKOD.

## 7. Quality problems, with the URL that shows each

| source | problem | evidence | correction at ingestion |
|---|---|---|---|
| City NKOD | four datasets serve another dataset's file | "Ulice" and "Počet občanov podľa dňa narodenia" share `…NavigationState=945:0::plac2174:_144154_5_8` (732 rows of `Deň, Pohlavie, Počet`); "Počet občanov podľa mena" and "Počet občanov podľa veku" share `…920:0::plac1140:_144053_5_8` (105 rows of ages); "Členovia orgánov samosprávy" and "Evidencia psov" share `…803:0::plac2114:_272000_5_8` (3 299 dog records); "Počet občanov podľa ulíc BB" and "Prírastky a úbytky občanov" share `…890:0::plac1400:_144057_5_8` (27 rows of years) | ingest each file once under the title that matches its columns; list the four mislinked titles as `not ingested, link points to <dataset>` and report them to the city |
| City NKOD | five datasets declared JSON link to an HTML landing page | "Faktúry BB", "Úradná tabuľa", "Školstvo", "Petície", "Zoznam daňových dlžníkov" all point at `https://egov.banskabystrica.sk/default.aspx?NavigationState=1100:0:` (`text/html`) | not ingested; the website's `office_announcements` type carries the official board instead |
| City NKOD | "Počty občanov v jednotlivých rokoch" links a PDF schema of another dataset | `https://egov.banskabystrica.sk/XSD/07_prirastky_a_ubytky_obcanov_za_jednotlive_roky.pdf` (`application/pdf`) | not ingested |
| City NKOD | 35 of 43 datasets unchanged since 2023 | `dct:modified` 2023-11-24 to 2023-12-01 | ingested with `modified` shown, so an answer can say how old the value is |
| City NKOD | no `dct:license` on any distribution | 61 of 61 distributions of the city and RÚVZ | licence taken per distribution from `legislation:termsOfUse` (CC-BY-4.0 or CC-BY-SA-4.0) |
| City website | news and events behind a redirect | `https://banskabystrica.sk/wp-json/…` answers 301 to `https://www.banskabystrica.sk/…`; NKOD records the bare host | fetch the `www.` host |
| BBSK Hub | every DCAT entry names its publisher `{{source}}` | DCAT-US `publisher.name` on 472 of 472 entries | publisher set to Banskobystrický samosprávny kraj, IČO 37828100 |
| BBSK Hub | 14 titles appear twice, 28 datasets in all: 9 census titles "Obyvateľstvo podľa …" each name an okres layer (13 rows, 26 for "vekovej štruktúry (2011, 2021)") and an obec layer (516 rows, 1 032), all CC-BY-SA-4.0; 5 "Bystrianska/Bystrinská dolina" titles are true repeats, all without a licence | `title` in the search API; rows from `<layer>/0/query?where=1%3D1&returnCountOnly=true&f=json` per item | both census layers ingested, titles ending `, okresy` and `, obce`; the 5 dolina repeats not ingested (no licence) |
| BBSK Hub | one name spelled two ways | "Bystrinská dolina" beside "Bystrianska dolina" | title corrected to "Bystrianska" |
| BBSK Hub | 12 datasets without a licence, 2 under CC-BY-NC-4.0 | `license` in the search API | not ingested: open licence or out (Open data integration rules §1) |
| BBSK Hub | 232 of 472 DCAT-US entries without a licence | `license` in the feed | licence read from the search API item, which carries it for 91 of the 103 datasets |
| `www.bbsk.sk`, `opendata.shmu.sk` | incomplete certificate chain | `openssl s_client`: only the leaf, `Verify return code: 21`; issuers GeoTrust TLS RSA CA G1 and Sectigo Public Server Authentication CA DV R36, fetched from each leaf's AIA URL | the fetcher completes the chain from AIA or a pinned intermediate; verification stays on |
| `www.bbsk.sk` | contracts, orders, invoices, documents and PDFs closed to crawlers | `robots.txt` disallows 7 paths and 7 file types | not crawled; the same contracts, orders and invoices come from the BBSK Hub as data |

## 8. Personal data found in published datasets

These are findings, not ingestion candidates. Open data integration rules §1 skips a dataset that
names or locates a person.

| dataset | what it holds | count | decision |
|---|---|---|---|
| City "Evidencia psov" | street, house number, flat number and floor of each registered dog, with breed, tag number and colour | 3 299 rows, 28 with a flat number, 5 with a floor | skipped; an aggregate per street at most |
| BBSK "Zoznam poskytovateľov pre APS v BBK" | name, seat, e-mail and phone of personal-assistance providers | 1 272 rows; 283 names carry no organization marker, 277 of them with an e-mail or phone | skipped; a count per okres at most |
| City "Objednávky BB", "Zmluvy BB", "Dotácie" | supplier or applicant names, published under Act 211/2000 | rows without an IČO: 560 of 27 422 orders, 9 of 19 890 contracts, 17 of 1 320 subsidies | ingested without the rows that carry no IČO, which are the ones that can name a natural person |

## 9. Ingestion plan per source family

Four families, each one task in group `assistant-rebuild` under the umbrella T-4143. The data
families follow [Open data integration rules](../Development/12-open-data-integration.md) §3:
CKAN publication under the project's organization, licence and original publisher kept.

| family | sources | method | lands in | corrections | first answers it enables |
|---|---|---|---|---|---|
| City catalogue harvest | the 43 city datasets of section 6 | SPARQL to DCAT, then ckanext-dcat into CKAN organization `banskabystrica`; JSON resources fetched and stored as CSV beside the original | data portal, `banskabystrica` | section 7 rows for City NKOD, section 8 rows | contracts, orders, subsidies, population by age, addresses, streets, council sessions |
| BBSK Hub harvest | the 103 BBSK datasets less 14 without an open licence (88 ingested in the live harvest, T-4152) | DCAT-AP 2.1.1 feed into ckanext-dcat, organization `bbsk`; each Feature Service also as GeoJSON and CSV resources | data portal, `bbsk` | publisher, census layer titles, spelling, licence from the search API, APS list skipped | schools, health facilities, pharmacies, social services, culture, roads and bridges, cycling counters, census 2021, emissions and air pollution trends |
| Live weather and air | SHMÚ 1-minute stations near Banská Bystrica, SHMÚ air quality through the EEA service | pipeline every 5 minutes (weather) and hourly (air) into `WeatherObserved` and `AirQualityObserved`, with the station id resolved from SHMÚ's INSPIRE station datasets in NKOD | Context Space of `banskabystrica`, published to CKAN | certificate chain completed, units from `aws1min_metadata.json` | "what is the temperature now", "how is the air today" |
| Web content for RAG | city website types of section 6, `www.bbsk.sk` sitemap (758 URLs) | city: WordPress REST per type, `modified` as the change cursor; region: sitemap with `robots.txt` honoured | the assistant's RAG index, as admin sources (T-4142) | `www.` host, certificate chain, robots paths | life situations, regulations, office announcements, events, news, how-to pages |

Left out on purpose: sensor.community (two sensors are not a city reading), RÚVZ invoices (a
state office's accounting, no resident question needs them), and the 12 other-publisher datasets
until a question in T-4144's set asks for one.

## 10. Provenance of every claim on this page

| claim | where it was read |
|---|---|
| status codes, content types and byte counts | `curl -L --max-time 25` from the build sandbox, 2026-09-20 |
| licences | the national catalogue's SPARQL endpoint, `https://data.slovensko.sk/api/sparql`, through `legislation:termsOfUse` and its `authorsWorkType` |
| BBSK publishes nothing | the same endpoint: `SELECT ?p ?o WHERE { <https://data.gov.sk/id/legal-subject/37828100> ?p ?o }` returned no rows |
| the catalogue holds 22 543 datasets | the same endpoint, `SELECT (COUNT(*) AS ?n) WHERE { ?s a dcat:Dataset }` |
| the 13 okres codes | `https://data.statistics.sk/api/v2/dimension/om7102rr/om7102rr_vuc?lang=sk` |
| update rates | the `update` field each cube carries in `https://data.statistics.sk/api/v2/collection` |
| sections 6 to 9 | `curl -L --max-time 30` from the build sandbox, 2026-10-15; one request per URL, a pause between requests |
| city and RÚVZ dataset lists | the SPARQL endpoint: `dct:publisher <https://data.gov.sk/id/legal-subject/00313271>` (and `00606979`), with `dcat:distribution`, `dcat:downloadURL`, `dct:modified` |
| mislinked and HTML distributions | the `Content-Type` and the columns of each download, compared with the dataset title |
| BBSK counts and licences | `https://opendata.bbsk.sk/api/search/v1/collections/dataset/items?limit=100` (`numberMatched`, `license`, `modified`) |
| certificate chains | `openssl s_client -connect {host}:443 -servername {host}`, then the leaf's `CA Issuers` URI |
| personal data counts | the downloaded rows: non-empty `Č._bytu` and `Č._poschodia`; provider names without a legal-form or public-body marker |

No key, token or credential was needed for any row, and none is written here. A source that comes
to need one is named with a `secretRef:` and the secret is filed separately, never in this page or
in a task body.

## Related

- [The Banská Bystrica contract](../Development/10-banska-bystrica-contract.md) — the projects, spaces, URNs and KPI entity these feeds are ingested into.
- [Ingestion examples](../Development/06a-ingestion-examples.md) — how a pipeline reads a feed like these.
- [Data models](../Architecture/11-data-models.md) — what has to exist before a table becomes a typed entity.
- [Open data integration rules](../Development/12-open-data-integration.md) — the five things each dataset of section 9 becomes, and the personal-data rule section 8 applies.
- [Pipelines](../Architecture/08-pipelines.md) — where the fetch, the mapping and the write live.
