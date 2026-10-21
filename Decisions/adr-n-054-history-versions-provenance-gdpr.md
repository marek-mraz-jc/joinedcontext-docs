---
sidebar_position: 55
title: "ADR-N-054: History Recording Modes, Versions of a Measurement, Provenance per Write and Personal Data"
---

# ADR-N-054: History Recording Modes, Versions of a Measurement, Provenance per Write and Personal Data

Date: 2026-10-18  
Status: Accepted  
Amended: 2026-10-21, T-5056 (owner: "when I just update the values from another source it should not create temporal values"): history is opt-in, `observed` its default record mode, and `never` per attribute (2.2)  
Decision Makers: product owner (history design of 2026-10-18 17:58–18:02Z: "a new measurement without changes must be saved", "sometimes no new measurement and still updated", "sometimes i want to create a old value", "with every version, manualy, with pipeline, inserted", "GDPR compliance for certain records", "and also manually with UI", then "all that are proposed"); the shape proposed by the supervisor, recorded by worker-3 (T-4664), owner may override

This record says what the broker keeps when a value is written: which writes become history rows, how a corrected or late value relates to the one it replaces, who and what wrote each row, and how attributes that identify a person are kept, shown, exported and erased. It extends the retention rules of [ADR-N-046](adr-n-046-data-lifecycle-and-quality.md) and binds the broker (T-4665), the gateway and its Policy (T-4666), the Portal (T-4667) and every store that holds a copy of context data (T-4668). Requirements DM-104…DM-129.

## 1. Context

On 2026-10-18 the broker keeps one temporal instance per write of an attribute, whatever it carries, for the retention of [ADR-N-046 §2.3](adr-n-046-data-lifecycle-and-quality.md#23-history-is-deleted-by-the-broker-per-tenant-and-type). Four questions have no answer:

| Question | What happens today | Why it matters |
|---|---|---|
| A sensor sends the same value again with a new time | a row, correct for a measurement | a parking spot's `status` that changes twice a day still costs a row per minute |
| A source re-sends a reading it already sent | a second row with the same `observedAt` | counts and sums over history double |
| A reading was wrong, or arrives a day late | an update overwrites the current state, also with the late value | the map shows yesterday's value as now; nobody can see what the wrong value was |
| A row holds a person's identifier | kept like any other row, on any Endpoint the space has | the city is the controller under GDPR and must be able to minimise, export, rectify and erase it (Art. 5, 15, 16, 17) |

NGSI-LD gives part of the vocabulary: every temporal instance has an `instanceId`, a multi-instance attribute is told apart by `datasetId`, an attribute's `observedAt` is the time of the observation, and the temporal representation marks a deleted attribute with `deletedAt` (ETSI GS CIM 009 V1.8.1, 4.5.6 and 5.6.12). It says nothing about duplicates, corrections, who wrote a row, or personal data.

## 2. Decision

### 2.1 A measurement has an identity

A measurement is identified by **(Entity, attribute, `datasetId`, `observedAt`)** (DM-104). The broker compares a write with the instance of the same identity, the value in canonical JSON (keys sorted, numbers in their shortest form, `unitCode` and sub-Properties included):

| The write | What the broker does | Current state |
|---|---|---|
| new identity, `observedAt` at or after the current one | a new measurement: a row | becomes this value |
| same identity, same value | a duplicate re-send: no row, `modifiedAt` unchanged | unchanged |
| same identity, another value | a **correction**: a new version of that measurement, the one before kept as superseded (DM-105) | changes only when the corrected measurement is the current one |
| new identity, `observedAt` before the current one | a **backfill**: a row in history only (DM-106) | unchanged |

A write without `observedAt` has no identity to compare. A pipeline maps the source's own time into `observedAt` (the Portal's pipeline editor offers the mapping for every attribute of a time series type). When a write still arrives without one, the broker stamps the time it received the write and records `observedAtSource: received` in the row's provenance, so a chart can tell a measured time from a received one (DM-107).

Decided (worker-3, owner may override): `observedAt`, not `modifiedAt` or the instance's arrival, is the time a measurement belongs to, because a late or re-sent reading has the same observation time and a different arrival time, and only the former tells a re-send from a new reading.

### 2.2 How each type records history: `every`, `onChange`, `off`

The retention rule of a type gains `record`, and any attribute may override it (DM-108):

```yaml
spec:
  retention:
    - entityType: ParkingSpot
      history: P90D
      record: every                        # the default: every new observedAt is a row
      attributes:
        status:   { record: onChange, heartbeat: PT1H }
        occupancy: { record: onChange, deadband: 1, heartbeat: PT15M }
        location: { record: onChange, minDistance: 5, heartbeat: PT1H }
    - entityType: TrafficFlowObserved
      history: P30D                        # intensity is a count per interval: every
```

| `record` | A row is written when | Fits |
|---|---|---|
| `every` (default) | every write with a new `observedAt`, even with the same value: a new measurement is a fact | measurements, counts, sums |
| `onChange` | the value differs from the last recorded row of that attribute by more than `deadband` (numbers, in the attribute's `unitCode`) or `minDistance` (metres, a GeoProperty), or differs at all in canonical JSON (everything else), or `heartbeat` has passed since the last recorded row (DM-109) | states and levels: a spot's status, a door, a position at rest |
| `observed` | the write carries an `observedAt` newer than the one it replaces; a value re-sent or changed under its old `observedAt`, or sent without one, adds no row | readings a source re-sends between measurements |
| `never` | never, for one attribute | bookkeeping such as `dateModified` |
| `off` | never (`history: off`, ADR-N-046) | current state only |

History is opt-in (T-5056, DM-132): the platform broker runs `ANTARES_TEMPORAL_RECORD=ruled`, so a type records rows only when the space's retention gives it a `history` duration or `forever`, by its own rule or the space's `*` rule. Inside such a type `observed` is the default (owner 2026-10-21: "when observedAt is set, then it will create a historical value"); `onChange` stays for a type whose source sends no `observedAt`, `never` marks a bookkeeping attribute, and expiresAt stays the lifetime of the current Entity, never a history trigger. A type the retention does not name keeps its current state only, and a temporal read of one of its Entities answers with no Attribute rather than a 404. A writer cannot turn history on: only the retention the space owner edits on the Portal's Retention tab, or in Git, decides it.

A quantity per interval (a count of vehicles in five minutes, rain in an hour) is meaningless with rows left out. A model marks such a slot `annotations: { quantity: perInterval }`, and the Portal refuses `onChange` for it (DM-110). `heartbeat` is required with `onChange`, so a value that never changes still shows up in history at least once per heartbeat and a chart can tell "unchanged" from "the sensor went quiet".

### 2.3 Provenance on every write

Every row the broker keeps, every version and every tombstone included, carries six system fields beside the value (DM-111):

| Field | Values | Set by |
|---|---|---|
| `channel` | `pipeline`, `api`, `ui`, `import`, `backfill`, `mqtt` | the gateway, from the path the write came through: a Pipeline's ServiceAccount, an Endpoint call, the Portal, the CSV upload (DM-81), a backfill job, an MQTT edge broker |
| `actor` | the ServiceAccount client id or the person's `sub` | the gateway, from the verified Keycloak token |
| `operation` | `create`, `update`, `correct`, `backfill`, `delete`, `erase` | the broker, from §2.1 and the request |
| `reason` | text up to 500 characters | the caller, in the `JC-Reason` header |
| `requestId` | the request's id | the gateway (`X-Request-Id`) |
| `writtenAt` | when the broker stored the row | the broker |

The caller never types `actor` or `channel` (DM-112). The edge drops every inbound `JC-Provenance-*` header, the gateway sets them after it verified the token, and the broker reads them only from the gateway's mesh identity; a write that reaches the broker another way is stored with `channel: api` and the broker's own client as `actor`. `reason` is required for `correct`, `delete` and every write from the Portal's UI, and a write without one answers `400` with the problem type `reason-required` (DM-113). Provenance holds no value of the data and is never copied into a log line.

### 2.4 Versions

A query answers the latest version of each measurement, as NGSI-LD does today. `versions=all` on a temporal query returns the whole chain of each measurement, oldest first, each version with its provenance and `supersededAt`; only a role the space's Policy grants `readVersions` gets it, by default the steward and the auditor (DM-114).

```text
# {entityId} = urn:ngsi-ld:ParkingSpot:p-17, percent-encoded
GET /api/endpoint/{endpointSlug}/ngsi-ld/v1/temporal/entities/{entityId}?attrs=status&versions=all
```

```json
{
  "id": "urn:ngsi-ld:ParkingSpot:p-17",
  "type": "ParkingSpot",
  "status": [
    { "type": "Property", "value": "occupied", "observedAt": "2026-10-18T07:00:00Z",
      "instanceId": "urn:ngsi-ld:AttributeInstance:a1", "supersededAt": "2026-10-18T09:12:40Z",
      "provenance": { "channel": "pipeline", "actor": "pipeline-parking", "operation": "create", "requestId": "4f1c", "writtenAt": "2026-10-18T07:00:02Z" } },
    { "type": "Property", "value": "free", "observedAt": "2026-10-18T07:00:00Z",
      "instanceId": "urn:ngsi-ld:AttributeInstance:a2",
      "provenance": { "channel": "ui", "actor": "4b8e0d2c-0000-4000-8000-000000000000", "operation": "correct", "reason": "Sensor stuck, checked on site", "requestId": "9a07", "writtenAt": "2026-10-18T09:12:40Z" } }
  ]
}
```

A delete of an attribute or an Entity writes a tombstone version with `deletedAt` (CIM 009 5.6.12) and its provenance; history before it stays for its retention. A revert writes a new version with the older value and `operation: correct`, so nothing is ever rewritten in place (DM-115). Under `onChange`, a write that changes only provenance adds no row; a correction always adds one, whatever the deadband (DM-116).

### 2.5 What a temporal query means

- A temporal query over an `onChange` attribute includes the last row before `timeAt`, so a chart of a window starts at the level the attribute held when the window opened (DM-117).
- `aggrMethods` `avg`, `min` and `max` over an `onChange` attribute are weighted by the time each value held. `sum` and `totalCount` are refused with `400` and the problem type `aggregation-not-meaningful`, because a left-out row is not a zero (DM-118).
- `lastN` counts measurements, the latest version of each, never versions (DM-119).

### 2.6 Personal data

**Classification on the Data Model.** A LinkML class or slot of a space's model says whether it holds personal data (DM-120):

```yaml
classes:
  BikeTrip:
    annotations:
      personalData: true
      legalBasis: public-task             # GDPR Art. 6(1): consent, contract, legal-obligation, vital-interest, public-task, legitimate-interest
      purpose: { en: "Planning the bike network", sk: "Plánovanie siete cyklotrás" }
      maxRetention: P90D
      dataSubjectRef: rider               # the slot that names the person
    slots: [rider, startedAt, startStation, endStation, location]
slots:
  rider:
    annotations: { personalData: true, ingest: keyedHash }
  location:
    annotations: { personalData: true, ingest: drop }
```

The Portal refuses a model that marks personal data without `legalBasis`, `purpose` and `maxRetention`. The model's JSON Schema and SHACL carry the annotations, so the same file states them to a reader of the schema surface.

**Minimisation at ingest.** A slot's `ingest` says what reaches the broker: `keep` (the default), `drop` (never stored), or `keyedHash` (HMAC-SHA-256 of the value with the space's key, so equal values stay linkable and the value is gone). The key is the space's `spec.personalData.keyRef`, a `secretRef` the reconciler resolves; the gateway applies it before the write reaches the broker, on every channel (DM-121).

**Never public.** An Endpoint with `audience: public` whose projection exposes a personal slot is refused by the Portal and by the Policy compiler (DM-122).

**Retention.** The broker deletes every row of a personal attribute, current state and every version, whose `observedAt` is older than its class's `maxRetention`, and an Entity whose newest personal row went with it (DM-123).

**The data subject's rights.** Each runs against the space's `dataSubjectRef` slot, by the subject's value or its keyed hash, by a person the space's Policy grants `personalData` (by default the space's owner role):

| Right | What the platform does |
|---|---|
| Access (Art. 15) | an export of every Entity naming the subject: current state, every version with provenance, and the read log entries of those Entities, as JSON (DM-124) |
| Rectification (Art. 16) | a correction (§2.4), and the old personal value in the superseded version is replaced by `null` with `redacted: true`, its provenance kept (DM-125) |
| Erasure (Art. 17) | the values are removed from the current state, from every version and from audit payloads, leaving one content-free tombstone per Entity with `operation: erase`, actor, reason and time; the erasure reaches the CKAN DataStore copy, the CSV exports, the gateway's caches and the assistant's stored conversations (DM-126) |

Backups cannot be edited. The CNPG backups expire after their `retentionPolicy`, which the platform's deployment sets to 30 days and states to the data subject, and the Portal keeps an **erasure log** (the subject's keyed hash, the space, when, the counts per store, never a value); after a restore the reconciler re-applies every erasure in the log before the restored data is served (DM-127).

**Read log.** Every read of a personal attribute through an Endpoint is logged: who, when, which Endpoint, how many Entities, never values or ids beyond the Entities' URNs (DM-128).

### 2.7 Precedence

When two rules say how long a row lives, the first that applies wins (DM-129):

1. an erasure (§2.6);
2. the personal data `maxRetention` of the class (§2.6);
3. the type's history rule and its layers ([ADR-N-046](adr-n-046-data-lifecycle-and-quality.md#23-history-is-deleted-by-the-broker-per-tenant-and-type), DM-97);
4. the platform default, 28 days (`P28D`).

Audit metadata (provenance of tombstones, the erasure log, the read log) holds no personal value and has its own retention, two years by default (`P2Y`, the Portal's `JC_AUDIT_RETENTION`).

## 3. Alternatives considered

- **Deduplicate on value alone.** Rejected: the owner said a new measurement without a change is still a fact; a sensor that reports 21 °C every minute for an hour has 60 measurements, not one.
- **Keep only the last version of a corrected measurement.** Rejected: the owner asked for every version, and a correction nobody can trace is the record a regulator asks about first.
- **Provenance as NGSI-LD sub-Properties the caller writes.** Rejected: a writer would type its own `actor`. The gateway is the only place that has verified the token.
- **Personal data rules on the Endpoint.** Rejected: one space has several Endpoints, and the same person's row must be minimised before any of them reads it. The model is the one place every Endpoint, pipeline and export reads.
- **Erasure by deleting the Entity.** Rejected: the Entity often holds non-personal values the city must keep (a bike trip's stations), and a deleted Entity keeps its personal values in history until retention.

## 4. Consequences

- The broker stores per row a version number, `supersededAt` and the six provenance fields, and compares each write with the stored instance of its identity (T-4665). A write costs one indexed lookup more.
- The gateway sets provenance, hashes and drops personal slots, applies `JC-Reason`, and logs personal reads (T-4666). The Policy gains the actions `readVersions` and `personalData`.
- The Portal edits `record` per type and attribute, shows versions and their provenance, requires a reason on every edit, and runs the export, rectification and erasure (T-4667).
- Every copy of context data is reachable by an erasure: CKAN DataStore, exports, caches, stored conversations, restored backups (T-4668).
- Existing history has no provenance; the broker writes `channel: api`, `operation: create` and no actor for rows written before the migration.

## Related

- [ADR-N-046](adr-n-046-data-lifecycle-and-quality.md) — the retention rules this record extends.
- [Requirements/data-models.md §17](../Requirements/data-models.md#17-history-versions-provenance-and-personal-data) — DM-104…DM-129.
- [Architecture/11-data-models.md §9](../Architecture/11-data-models.md#9-personal-data-in-a-model) — the classification annotations in a model.
- [API/02 §2b](../API/02-endpoint-representations.md#2b-history-versions-and-provenance) — the query parameters and headers.
- [API/01 §46](../API/01-portal-api.md#46-personal-data-of-a-space-dm-124dm-127) — export, rectification and erasure.
- [Deployment/07 §5](../Deployment/07-backup-restore.md#5-backups-and-erasure) — backup expiry and the erasure log after a restore.
