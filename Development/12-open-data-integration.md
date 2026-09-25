---
sidebar_position: 14
title: "Open Data Integration Rules"
description: The rules every city integration follows, from the verified inventory to the published CKAN dataset, and the checklist a city task carries.
---

# Open data integration rules

The rules a city integration follows when it brings a public dataset into a project: Banská
Bystrica into `banskabystrica`, the region into `bbsk`, Prague into `praha`, Helsinki into
`helsinki`. Read this before adding a DataSource, a pipeline or a type for open data. All four
cities are projects of the one Organization (owner decision, 2026-09-24), so their entity ids
carry the same `{orgDomain}` and differ in the `{space}` segment, and each project publishes into
its own CKAN organization ([Open data catalogue §1](../Architecture/21-open-data-catalogue.md#1-one-organization-per-project)).
[Open data sources of the Banská Bystrica region](../Research/banska-bystrica-open-data-sources.md)
is the worked example of the inventory this page asks for.

## 1. The inventory comes first

Every city keeps one inventory table, in its task and later in a `Research/` page, before any
manifest is written. One row per dataset:

| column | what goes in it |
|---|---|
| dataset | the publisher's own name, and its code when it has one (`om7102rr`) |
| publisher | the body, and its level: `city`, `region`, `national`, `operator` |
| URL | the API or file URL that was fetched, not the catalogue page that describes it |
| status | the HTTP status and content type of that fetch, with its date |
| format | JSON, JSON-stat, CSV, GeoJSON, GTFS, GTFS-RT, WFS, … |
| licence | the licence as the publisher states it (CC-BY-4.0, CC0-1.0, ODbL-1.0, …), and where it was read |
| update rate | what the publisher declares, else "not declared" |
| size | rows or bytes of the fetch |
| key | `none`, or the key's issuer; never the key |
| value | one line: who cares about it and why |

Three rules hold the table honest:

- **Fetched, not remembered.** A row exists only after its URL answered once with `curl -L
  --max-time 25` from the build sandbox. A URL that did not answer is written in a "refused" table
  with its status, as the Banská Bystrica survey does, never silently dropped.
- **Open licence or out.** A row whose licence is not an open one, or cannot be found, is left
  out. The licence can hide: the Slovak national catalogue states it in
  `legislation:termsOfUse`, not in `dct:license`.
- **No personal data.** A dataset that names or locates a person is skipped, or taken only as an
  aggregate the publisher already computed. Complaints, permits and decisions are read as counts
  per district and type, never per applicant.

## 2. Which datasets to take

Rank the inventory by value first and freshness second, and take at least ten per city where ten
open ones exist. Fewer is correct when the inventory proves there are fewer, and the task says so
with the table as its evidence. Cover the themes a resident meets:

| theme | examples |
|---|---|
| real time | public transport vehicles, air quality, weather, traffic, parking, shared bikes |
| city services | schools, libraries, health centres, social services, culture |
| finance | budget, contracts, subsidies |
| demography | population by age and district, housing, unemployment |
| environment | waste and recycling points, green areas, noise, water |
| geography | districts, addresses, municipality boundaries |

## 3. What each dataset becomes

Each chosen dataset becomes five things in its project, in this order.

1. **A `DataSource`** (MF-35) holding the connection. Its manifest comment names the publisher,
   the licence and where the licence was read, as `seed/banskabystrica/datasource-obyvatelia.yaml`
   does. A key goes in `http.authorization.headerRef` or `secrets`, as a `secretRef` (PL-14).
2. **Types in the space's one data model** (DM-61). A space has one
   `datamodel.linkml.yaml`, and a new dataset adds classes to it rather than a second model.
   Reuse a Smart Data Models class where one fits (`AirQualityObserved`, `WeatherObserved`,
   `ParkingSpot`, `PointOfInterest`); otherwise write the class with slot descriptions, units
   (`unit` on the slot) and enums for every closed list. A reference to another entity is a
   relationship slot (`range` a class of the same model), so a school belongs to a district and a
   stop is served by several routes.
3. **Entity ids** `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`, with `{space}` rendered by
   PF-84 and `{localId}` taken from the publisher's own stable key. An id built from a row number
   changes when the publisher reorders the file, and every relationship to it breaks.
4. **A pipeline** that fetches, maps and writes through the space's Endpoint, declared with
   `spec.quotas` (`maxMemoryMb`, `cpuMillicores`) so its cost is known before it runs (PL-11
   gives the runner's default). Its schedule follows the source: a real-time feed every one to
   five minutes, a daily file nightly, an annual table monthly. Only rows that validate against the
   space's model are written; the rest are rejected with the reason, which the runner enforces
   once T-2708 lands ([Pipelines](../Architecture/08-pipelines.md)).
5. **A CKAN publication** on the Endpoint (`spec.publish.ckan`, EP-62…EP-69) with the source's
   licence in `publish.ckan.license` and the original publisher and URL in the Endpoint's
   description, so a harvester sees both the republisher and the source.

**Attribution travels with the data.** Each entity carries `dataProvider` (the publisher) and
`source` (the URL it was read from), the two Smart Data Models common properties for it, and the
space's model states the licence in its schema-level `license`. An application that shows the
data shows the publisher and the licence beside it.

## 4. Capacity on one node

`dev` is one `cpx42` with 16 GB that already runs the whole platform. Before a city is added,
the integrator reads `kubectl top nodes` and the broker's volume use, and the task body records
both numbers.

- Every pipeline declares `spec.quotas`. A pipeline without them takes the runner default and
  hides its cost.
- A real-time feed polls no faster than its value needs; a vehicle feed that nobody replays is
  read every minute, not every second.
- History is the broker's largest cost. The broker keeps one retention horizon for every type
  (`ANTARES_TEMPORAL_RETENTION_DAYS`), and `dev` leaves it unset, so history is kept forever.
  There is no retention per type yet, so a real-time type writes only the attributes a KPI or an
  application reads, and the task records the broker's volume use after its first day.
- When the numbers say the node is full, the task is set `blocked` with those numbers and asks the
  owner for a larger node. Nothing is scaled up without that answer.

## 5. Keys

Some sources need a key: Golemio in Prague, Digitransit for Helsinki's routes. The owner registers
the key with the publisher, and the integrator stores it as a Kubernetes Secret that the manifest
names by `secretRef`. The key is never in Git, in a task body, in a log line or in an
application. A dataset whose key does not exist yet is set `blocked` with `@user`, and the rest
of the city goes ahead.

## 6. The checklist a city task carries

Copy this list into the city's task and tick it there:

- [ ] Inventory table in the task, every row fetched, with status and date.
- [ ] Refused sources listed with the reason.
- [ ] Licence of each chosen row read from the publisher, open only.
- [ ] No row with personal data, or only as a published aggregate.
- [ ] At least ten datasets chosen, or the inventory proving fewer.
- [ ] Per dataset: `DataSource`, classes in the space's one model, ids by PF-84, pipeline with
      `spec.quotas` and a schedule that matches the source, CKAN publication with the licence.
- [ ] `dataProvider` and `source` on every entity, the licence in the model's `license`.
- [ ] Every key a `secretRef`, and `blocked` with `@user` until it exists.
- [ ] Each pipeline's sample test green, and one test showing a bad row rejected.
- [ ] Node and broker numbers recorded before the city is applied.
- [ ] Count and freshness per dataset on `dev` recorded after the first green run.

## Related

- [Open data sources of the Banská Bystrica region](../Research/banska-bystrica-open-data-sources.md) — a finished inventory, with its refused sources.
- [The Banská Bystrica contract](10-banska-bystrica-contract.md) — spaces, ids and the KPI entity the two Slovak projects already use.
- [Ingestion recipes](06a-ingestion-examples.md) — pipelines for HTTP, CSV and GTFS-realtime sources.
- [Open data catalogue](../Architecture/21-open-data-catalogue.md) — how a published Endpoint becomes a CKAN dataset.
- [Data models](../Architecture/11-data-models.md) — the one model per space and how a class is written.
