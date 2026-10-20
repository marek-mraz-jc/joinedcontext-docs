---
sidebar_position: 16
title: Retention & Expiry
description: How long a context space keeps current values and history, every way data is removed, which one wins, and recipes for buses, alerts, sensors and imported files.
---

# Retention & Expiry

Data in a context space has two parts that age differently: the *current value* of each entity (where bus 1234 is now) and its *history* (every position it reported). This page lists every way the platform removes either part, which one wins when several apply, what a new space does when you set nothing, and gives a recipe to copy for live vehicles, alerts, air-quality sensors and data imported from a file. It is written for data stewards and integration engineers who build pipelines and spaces.

## 1. What a New Space Does

A space you create keeps:

| Part | Kept | Until you change it with |
|---|---|---|
| Current values | for ever: nothing removes an entity on its own | an end time on the entity (`expiresAt`), a space rule **Current values**, or pipeline expiry |
| History | 28 days, the platform default | a space rule **History**, the **All other types** row, or an entity's own `historyRetention` |
| Pipeline expiry | off | **Remove entities the source no longer sends** on the pipeline |

The Helsinki sample project also carries an older settings file that says history is kept 90 days. Nothing reads that value: the 28 days above are what the platform applies, and the stale value is being removed.

## 2. Every Way Data Is Removed

| Mechanism | Removes | Where you set it |
|---|---|---|
| Entity `expiresAt` | the whole entity at that moment; reads stop showing it at once | in the data the pipeline writes, one value per entity |
| Attribute `expiresAt` | one attribute of an entity | in the data, on that attribute |
| Space rule **Current values** | an entity of that type not updated for the duration, unless it has its own `expiresAt` | space, **Retention**, per type |
| Pipeline expiry | entities of the named types not updated for the window, checked once an hour | the pipeline, **Remove entities the source no longer sends** |
| Space rule **History** | history rows of that type older than the duration; `off` records none, **Keep forever** keeps all and asks why | space, **Retention**, per type |
| **All other types** row | history of every type without its own rule | space, **Retention** |
| Platform default | history of everything nothing else rules, after 28 days | the platform, not per space |
| Entity `historyRetention` | history of that one entity, a duration or `off` | in the data, on the entity |
| Recording on change | nothing: it writes fewer history rows, only when a value moves | the space manifest, per type or attribute |
| Delete and erasure | what a person deletes; an erasure removes a data subject's values everywhere | a person's action, approved |

### Which one wins

For current values, an `expiresAt` on the entity wins over the space rule: the space rule only touches entities without one. Pipeline expiry is a separate sweep and removes what it names regardless of the space rule.

For history, the most specific setting wins, in this order:

1. an erasure;
2. the entity's own `historyRetention`;
3. the space rule of the entity's type (**Keep forever** there holds back every level below);
4. the space's **All other types** row;
5. the platform default of 28 days.

Personal data adds a limit of its own. A data model that marks an attribute as personal must state its maximum retention, and the Portal refuses the model without it. The platform does not yet delete personal values when that maximum passes: until it does, give a type that holds personal data a space rule for **History** no longer than its stated maximum, and use erasure for a person's request.

## 3. Which One Do I Pick

Start from what the source tells you:

- *The source says when an item ends* (a vehicle position is stale after minutes, an alert has a valid-to time, a permit has an end date): set `expiresAt` in the pipeline mapping. Every write renews it, and the entity goes the moment it passes.
- *The source sends the whole list every run and stops listing an item* (stations, a register, a catalogue export): switch on pipeline expiry with a window a few runs long.
- *Every entity of a type goes stale after a fixed time without an update, whoever wrote it*: a space rule **Current values** for that type.
- *History grows too large*: shorten the type's **History**, set it to **Off** for types where only now matters, or record on change so a sensor that reads the same value all night writes one row an hour.

Two settings that look alike behave differently. A space rule **Current values** removes an entity because nothing updated it. Pipeline expiry removes it because the pipeline stopped sending it. For a feed that only sends what changed, a sensor reading or a change stream, use neither: a quiet entity there is not gone, it has nothing new to say.

### Set a space's rules

#### By hand

1. Open the space at `/projects/helsinki/spaces/air-quality`.
2. In the **Retention** section, click **Change retention**.
3. For each type, set **Current values** and **History** as a number and a unit, or pick **Off: no history** or **Keep forever**. The **All other types** row sets history for every type without a rule of its own.
4. Click **Propose**. When the new rules would delete data at once, the dialog **Delete data of air-quality for good?** lists how many current values and history records go; confirm with **Propose and delete**.
5. An approver merges the proposal in Approvals; the rules apply from then on.

Recording on change has no form field: set it in the space manifest as the recipes below show, and propose the file as a change.

## 4. Recipe: Buses and Live Vehicles

A vehicle feed sends a position every second while the vehicle runs and nothing when it parks. Give each position an end time ten minutes after it was observed, so a bus that stopped reporting is gone ten minutes later, and keep a light history.

Add one line to the pipeline's mapping, after it builds the entity. `tst` is the observation time the high-frequency positioning feed sends:

```coffee title="bento.yaml, the mapping of the vehicle pipeline"
root.expiresAt = (this.tst.ts_unix() + 600).ts_format("2006-01-02T15:04:05Z", "UTC")
```

A position observed at `2026-10-20T15:00:00.123Z` gets `expiresAt` `2026-10-20T15:10:00Z`. A separate cleanup pipeline that reads the vehicles back and deletes the old ones is no longer needed.

For the history, record a position only when the vehicle moved 50 metres, and at least every five minutes while it stands, and keep a week:

```yaml title="projects/helsinki/spaces/transit-live/space.yaml"
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: transit-live
  namespace: helsinki
  title: { en: "Live vehicles" }
spec:
  isSandbox: false
  dataModelRef: { kind: DataModel, name: transit }
  defaultLocale: en
  retention:
    - entityType: Vehicle
      history: P7D
      record: onChange
      heartbeat: PT5M
      minDistance: 50
```

When only the live map matters, write `history: "off"` instead and leave out the three recording lines: the space then keeps no history of vehicles at all.

## 5. Recipe: Alerts and Roadworks

An alert or a roadwork carries the time it stops applying. Use it as the entity's end time, and leave entities without one alone:

```coffee title="bento.yaml, the mapping of the alerts pipeline"
root.expiresAt = this.validTo.ts_format("2006-01-02T15:04:05Z", "UTC").catch(deleted())
```

`2026-10-21T06:00:00+03:00` becomes `2026-10-21T03:00:00Z`. An alert without `validTo`, or with a value that is not a time, gets no end time and stays until the source withdraws it. An alert whose `validTo` already passed is written and disappears at once. This replaces a cleanup pipeline that deleted ended alerts.

When the source withdraws alerts by leaving them out of its list instead, use pipeline expiry as in the next section.

## 6. Recipe: A Full List Such as Stations

A station list arrives whole every five minutes. A station missing from it for two days has closed:

```yaml title="projects/helsinki/pipelines/city-bike-stations/pipeline.yaml"
apiVersion: joinedcontext.com/v1alpha1
kind: Pipeline
metadata:
  name: city-bike-stations
  namespace: helsinki
  title: { en: "City-bike stations, every five minutes" }
spec:
  class: auto
  period: 5m
  source:
    dataSourceRef: { kind: DataSource, name: city-bike-stations }
  targetEndpoint: urn:ngsi-ld:Endpoint:hel.fi:helsinki:helsinki-all
  expiry:
    after: 2d
    types: [BikeHireDockingStation]
```

The window is whole hours or days, from `1h` to `365d`, for one to twenty types. Make it several runs long, so one failed run does not empty the space. The Portal refuses expiry while a second pipeline writes into the same space, and while no Policy lets the pipeline delete those types. The steps in the Portal are in [Pipelines & Ingestion](./04-pipelines.md#7-removing-entities-the-source-dropped).

## 7. Recipe: Air-Quality Sensors

A sensor's current value stays until the next reading, so set no current-value rule. Keep 30 days of history, write a row only when a value moves, and still write one row an hour so a flat line is visible:

```yaml title="projects/helsinki/spaces/air-quality/space.yaml"
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: air-quality
  namespace: helsinki
  title: { en: "Air quality" }
spec:
  isSandbox: false
  dataModelRef: { kind: DataModel, name: air-quality }
  defaultLocale: en
  retention:
    - entityType: AirQualityObserved
      history: P30D
      record: onChange
      heartbeat: PT1H
      attributes:
        pm10: { deadband: 1 }
        no2: { deadband: 2 }
    - entityType: "*"
      history: P90D
```

`deadband` is in the attribute's own unit: here a PM10 reading is recorded when it moves by more than 1 µg/m³. An attribute the rule does not name records on any change. The last rule is the **All other types** row: every other type in this space keeps 90 days of history instead of the platform's 28.

## 8. Recipe: Data Imported From a File

To load a CSV or JSON file into a space, complete the space from the file (see [Organizations, Projects & Context Spaces](./02-organizations-projects-spaces.md#4-completing-a-space-from-a-sample)): the Portal drafts a data source and a pipeline that read it. The **Import** page under Export does something else: it imports configuration bundles, never entity data.

Imported entities never expire on their own, and the space's history setting applies to them like to any other write. When rows of the file have an end, add a column, for example `validUntil` with dates such as `2027-12-31`, and set it as the end time in the pipeline's mapping:

```coffee title="bento.yaml, the mapping of the import pipeline"
root.expiresAt = this.validUntil.ts_parse("2006-01-02").ts_format("2006-01-02T15:04:05Z", "UTC").catch(deleted())
```

A row with an empty `validUntil` stays. Pipeline expiry does not suit a one-off file: the file is read once, so after the window every entity would look abandoned and be deleted.

## 9. Recipe: Personal Data

Mark the attribute as personal in the data model, with its legal basis, purpose and maximum retention; the Portal refuses the model without them. Until the platform deletes personal values by that maximum on its own, set the type's **History** in the space no longer than the maximum, and send a person's erasure request through erasure, which removes their values from the current state, the history and every copy.

## Related

- [Pipelines & Ingestion](./04-pipelines.md): building the pipeline and its mapping that sets `expiresAt`.
- [Organizations, Projects & Context Spaces](./02-organizations-projects-spaces.md): creating the space whose rules this page sets.
- [Data Modeling](./03-data-models.md): the types a retention rule names, and personal attributes.
- [Users, Roles & Approvals](./07-users-roles-approvals.md): approving a retention or expiry change.
- [Export, Portability & Project Duplication](./09-export-import.md): what the Import page imports.
