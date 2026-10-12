---
sidebar_position: 47
title: "ADR-N-046: Data Lifecycle and Quality, Retention per Space and Type, Rules with Three Outcomes"
---

# ADR-N-046: Data Lifecycle and Quality, Retention per Space and Type, Rules with Three Outcomes

Date: 2026-10-12  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-11: "a workflow that checks whether data is correct and decides what data is removed, e.g. public transport kept only 5 minutes or 8 hours, temporal records deleted after 5 minutes"); the shape below was decided by worker-3, owner may override

## 1. Context

The owner wants two things for context data: rules that say when data is wrong, and rules that say when data goes away. Both exist today only in pieces:

| Piece | What it does on 2026-10-12 | Where |
|---|---|---|
| Model shape on pipeline writes | a validation stage before every pipeline output refuses a record that breaks the model (class, id, required, datatype, enum, closed shape, kind); the refusal goes to the pipeline's rejected list | PL-59…PL-61; portal `src/pipeline_validation.rs` |
| Model shape on API writes | DM-27 says the gateway validates writes against the space's JSON Schema; it does not: the conformance case is an expected failure | conformance `tests/security/test_steward_note.py::test_dm27_a_note_the_model_refuses_never_reaches_the_row` |
| Stored data held to its model | once a day the Portal re-reads every space with a model and reports invalid entities and pipeline freshness | DM-74; [API/01 §27](../API/01-portal-api.md#27-data-quality-of-a-space-dm-74); portal `src/quality.rs` |
| Stale-entity expiry | a Pipeline's `spec.expiry` deletes entities of its types not modified for 1 h…365 d, swept hourly through its Endpoint | PL-64, PL-65; [Architecture/08 §Stale-entity expiry](../Architecture/08-pipelines.md#stale-entity-expiry-pl-64-pl-65) |
| Current-state expiry in the broker | Antares honours NGSI-LD `expiresAt` on entities and attribute instances (memory and Postgres stores) | Antares `crates/antares-sql` store maintenance; ETSI GS CIM 009 / TS 104 175 4.22 |
| History retention in the broker | one broker-wide `ANTARES_TEMPORAL_RETENTION_DAYS`, whole days, every tenant and type alike; unset on dev, so history is kept forever | Antares `docs/src/configuration.md`; deployment `components/context-broker` (no retention variable) |
| Sandbox lifetime | `spec.ttlDays` (1…14) removes a whole sandbox space | PF-19 |

Missing: value rules beyond the model's shape (a speed over a limit, a position outside the city), freshness as a rule, an outcome other than refusal, history retention in minutes or hours per space and type, quality numbers anyone outside the Portal can read, and a single place where a space says what it deletes.

### 1.1 How others do it

Each cell comes from the product's own documentation or source, read for T-3899 (2026-10-12); "none found" means a search of that documentation and repository found nothing.

| Product | Current state | History | Granularity | Mechanism | Quality checks | Quality publication |
|---|---|---|---|---|---|---|
| FIWARE Orion | transient entities through `dateExpires`, removal irreversible ([Orion API](https://fiware-orion.readthedocs.io/en/master/orion-api.html)) | none | per entity | MongoDB TTL index, `expireAfterSeconds(0)`, a thread waking about every 60 s ([connectionOperations.cpp](https://github.com/FIWARE/context.Orion-LD/blob/develop/src/lib/mongoBackend/connectionOperations.cpp)) | input validation only: forbidden characters, ids, DateTime, `400` ([Orion API](https://fiware-orion.readthedocs.io/en/master/orion-api.html)) | none found |
| FIWARE Orion-LD (TROE) + Mintaka | `expiresAt` found only for subscriptions and registrations ([orionld source](https://github.com/FIWARE/context.Orion-LD/tree/develop/src/lib/orionld)) | TimescaleDB partitions "make retention easier" ([troe.md](https://github.com/FIWARE/context.Orion-LD/blob/develop/doc/manuals-ld/troe.md)); Mintaka only reads ([Mintaka](https://github.com/FIWARE/mintaka)) | per hypertable | `add_retention_policy` drops whole time chunks on a schedule ([TimescaleDB](https://www.tigerdata.com/docs/api/latest/data-retention/add_retention_policy)) | none found | none found |
| FIWARE QuantumLeap | — | no automatic retention, a roadmap proposal ([roadmap](https://github.com/orchestracities/ngsi-timeseries-api/blob/master/docs/roadmap.md)) | per entity or type, optional time window | manual `DELETE` endpoints ([using.md](https://github.com/orchestracities/ngsi-timeseries-api/blob/master/docs/manuals/user/using.md)) | none found | none found |
| Stellio | `expiresAt` on entities and attributes, purged per tenant ([TransientDataGarbageCollectionJob](https://github.com/stellio-hub/stellio-context-broker/blob/develop/search-service/src/main/kotlin/com/egm/stellio/search/entity/job/TransientDataGarbageCollectionJob.kt)) | no purge found; TimescaleDB hypertables ([persistence rules](https://github.com/stellio-hub/stellio-context-broker/blob/develop/.claude/rules/persistence.md)) | per tenant, per entity or attribute | cron, daily at 04:00 by default ([configuration tips](https://github.com/stellio-hub/stellio-context-broker/blob/develop/docs/admin/misc_configuration_tips.md)) | none found | none found |
| Scorpio | entity `expiresAt` not found; only registrations and subscriptions ([source](https://github.com/ScorpioBroker/ScorpioBroker)) | none found | — | — | none found | none found |
| NGSI-LD (TS 104 175) | `expiresAt` on an Entity or Attribute "may be automatically removed", local storage only, clean-up lags ([clause 5](https://forge.etsi.org/rep/data/specifications/ts-104-175)) | not specified | entity, attribute | implementation-defined periodic clean-up; on conflict the earlier `expiresAt` wins (clause 8.5.2) | — | — |
| CKAN ckanext-validation | — | — | per resource | — | Frictionless validation of CSV/XLSX on resource create or update, asynchronous by default, blocking only in sync mode ([README](https://github.com/frictionlessdata/ckanext-validation)) | a status badge and a report per resource |
| W3C DQV, DCAT-AP, ckanext-dcat | — | — | dataset or distribution | — | — | `dqv:hasQualityMeasurement` links a dataset to measurements ([DQV](https://www.w3.org/TR/vocab-dqv/)); DCAT-AP 3.0.x does not use DQV ([DCAT-AP](https://github.com/SEMICeu/DCAT-AP)); ckanext-dcat maps only `dqv:hasQualityAnnotation`, in its Health-DCAT-AP profile ([health_dcat_ap.yaml](https://github.com/ckan/ckanext-dcat/blob/master/ckanext/dcat/schemas/health_dcat_ap.yaml)) |
| Great Expectations | — | — | per batch and suite | a Checkpoint run in Python where the user triggers it ([overview](https://docs.greatexpectations.io/docs/core/introduction/gx_overview)) | not null, between, regex, column max; no dedicated freshness; outcome `success` plus actions (mail, chat), no quarantine ([Checkpoint](https://docs.greatexpectations.io/docs/reference/learn/terms/checkpoint)) | Data Docs |
| Soda | — | — | per dataset or contract | a scan against the data source ([SodaCL](https://docs.soda.io/soda-cl/soda-cl-overview.html)) | missing, validity, regex, freshness (age of the newest row, [freshness](https://docs.soda.io/soda-cl/freshness.html)), row count, schema, duplicates; pass, warn, fail; no quarantine | Soda Cloud |
| CIVITAS/CORE | none found | none found; the design-doc template has an empty Retention column | — | — | "Data Quality Monitoring" and "Data Assurance Management" are capabilities without an implementing system (`civitas-core-docs_v2/Architecture/Capabilities/capabilities.md`) | none found |

What this says for the decision: retention of current state in NGSI-LD is `expiresAt` everywhere it exists (Orion's `dateExpires`, Stellio, Antares), executed by the broker; retention of history is either missing or a whole-store job (TimescaleDB chunks), never per tenant and type in minutes. Quality tools check after the fact and report; none quarantines on an NGSI-LD write, and DQV is the only standard way to publish the numbers in a catalogue, used by no DCAT-AP profile we deploy.

## 2. Decision

### 2.1 Retention is declared on the Context Space, per entity type

A ContextSpace MAY carry `spec.retention`, a list of rules, one per entity type of the space's model (DM-81):

```yaml
spec:
  retention:
    - entityType: Vehicle
      current: PT5M        # an entity not written for 5 minutes expires
      history: PT8H        # temporal instances older than 8 hours are deleted
    - entityType: GtfsStop # no durations: kept forever, stated explicitly
```

- Durations are ISO 8601 in days, hours, minutes and seconds (`PT5M`, `PT8H`, `P30D`, `P1DT12H`), from one minute to 3650 days, the form the broker's `/q/retention` reads (years and months have no fixed length, so they are refused); the Portal form writes them from plain units ("keep current values 5 minutes", "keep history 8 hours", "keep forever").
- A type without a rule, and a space without `spec.retention`, loses nothing to retention. Deletion is opt-in per space and per type (DM-81).
- Decided (worker-3, owner may override): the rule lives on the Space, because retention is an operational choice of the place that holds the data. The same organization model (DM-75) is imported by several spaces that keep data for different lengths; a LinkML annotation on the class would force one length on all of them. A new kind was rejected as one more file for two numbers.

### 2.2 Current state expires in the broker, by `modifiedAt`

The Portal's reconciler pushes each space's rules to the broker (`PUT /q/retention/{tenant}`, admin token, like the views and rule documents of ADR-N-042). The broker matches stored types, which are expanded IRIs, so the reconciler writes each rule under every IRI the class is written as: the NGSI-LD core context's (`https://uri.etsi.org/ngsi-ld/default-context/{Class}`) and the one the space's model `@context` gives it; a space whose rules are gone has its document deleted. Once a minute the broker removes, per tenant and ruled type, the entities whose `modifiedAt` is older than `current` and that carry no `expiresAt` of their own, so a bus that keeps reporting keeps living and one that stops disappears `current` after its last report (at most a minute later). An `expiresAt` the writer sends wins and the broker's existing expiry handles it (DM-82).

Decided (worker-3, owner may override): the broker removes, not the pipeline and not the gateway, because every write path ends in the broker (Endpoints, pipelines through Endpoints, the Portal), and a stamp made anywhere earlier misses the path that forgot it. Decided (worker-3, T-3900): a sweep by `modifiedAt` rather than an `expiresAt` stamped at write time, because one bounded maintenance query covers every write path (create, update, upsert, append, batch, merge) where a stamp needs a hook in each, and the price is a lag of at most one sweep. A pipeline that knows better (an alert's end of validity) writes its own `expiresAt`.

PL-64 stays: it is a pipeline's hourly sweep in hours and days, run under the pipeline's own account. A space that wants minutes uses `spec.retention`; T-3904 moves Helsinki's vehicles from the `vehicles-reaper` pipeline to a space rule.

### 2.3 History is deleted by the broker per tenant and type

The same rule's `history` is executed by the broker's maintenance job: temporal instances of that type in that tenant older than `history` are deleted in bounded batches, at least once a minute while any rule is under an hour (DM-83). `ANTARES_TEMPORAL_RETENTION_DAYS` stays the broker-wide fallback for a deployment that sets it; the platform's deployment leaves it unset, so a space that declares nothing keeps its history. Each sweep logs, per tenant and type, the count it deleted, never ids of history instances and never values, and counts in `antares_retention_deleted_total{tenant,type,kind}` (`kind` = `entity` or `history`).

### 2.4 Quality rules: the model's constraints plus three rule kinds

Two sources, one evaluation:

1. **The model.** Every slot constraint the LinkML model declares (`required`, `minimum_value`, `maximum_value`, `pattern`, `equals_string_in`/enum, `range`) is a rule named after its SHACL component (`sh:minInclusive`, `sh:pattern`, …), as PL-59 already names them. Outcome: reject, always; a model is a contract (DM-85).
2. **The space.** A ContextSpace MAY carry `spec.quality`, a list of at most 64 rules (DM-86):

```yaml
spec:
  quality:
    - name: speed-plausible
      entityType: Vehicle
      kind: range
      attribute: speed
      max: 33.4            # m/s, in the attribute's unitCode
    - name: inside-hsl-area
      entityType: Vehicle
      kind: area
      attribute: location
      bbox: [24.5, 60.0, 25.3, 60.45]   # minLon, minLat, maxLon, maxLat
    - name: position-current
      entityType: Vehicle
      kind: freshness
      attribute: location
      maxAhead: PT30S      # observedAt in the future: checked on write
      maxAge: PT5M         # observedAt older than this: checked by the sweep
      outcome: quarantine
```

| Kind | Checks | When | Default outcome |
|---|---|---|---|
| `range` | a number Property's value against `min` and/or `max` | on write | flag |
| `area` | a GeoProperty's coordinates inside `bbox` (every point of a geometry) | on write | flag |
| `freshness` | `observedAt` of the attribute not later than now + `maxAhead` | on write | reject |
| `freshness` | `observedAt` of the attribute not earlier than now − `maxAge` | by the sweep | quarantine |

A rule's `outcome` overrides the default. An attribute the entity does not carry passes every rule but the model's `required`.

### 2.5 Where the rules run

- **Pipeline writes**: the PL-60 validation stage, already rendered from the model, gains the space's rules compiled to Bloblang (the way DM-80 formula fields are compiled), so a pipeline's record is judged before the write and a rejected one lands in the rejected list with the rule's name (PL-61).
- **API writes**: the gateway checks every create, update, upsert and append through an Endpoint against the same compiled model and rules before forwarding to the broker, which implements DM-27 at last.
- **The sweep**: the Portal's leading replica, which already re-reads spaces as its own client for DM-74, reads every type with a `freshness` rule at least once a minute and writes or lifts the quarantine mark.

One compiler in the Portal turns model and rules into the artifact both the stage and the gateway read, so a person, the runner and the gateway reach the same verdict on the same entity (PL-59's rule, extended).

Evaluation is bounded: at most 64 rules per space, patterns compiled with a linear-time engine under a 64 KiB size limit, no network and no store access on the write path (DM-91).

### 2.6 Three outcomes

- **reject**: the write is refused with `400` and an RFC 7807 problem of type `https://joinedcontext.com/problems/quality-rule` naming the rule and the attribute, never the value (DM-87). A pipeline's record goes to its rejected list.
- **flag**: the entity is stored; the attribute carries a sub-Property `qualityFlags` listing the broken rules' names. A later write that passes stores no flag (DM-88).
- **quarantine**: the entity is stored with the Properties `quarantinedAt` (DateTime) and `quarantineRules` (names). Every permit the Portal compiles into the space's rule document for a role other than the space's `owner` and `steward` gets the condition `!quarantinedAt` added to its `q`, so the broker's engine hides a quarantined entity from every public and member Endpoint, while the owner's and steward's views still show it (DM-89). The sweep lifts the mark when the rule holds again.

Decided (worker-3, owner may override): quarantine is a mark plus a narrower permit, not a move to another tenant, because the engine already narrows by `q` (ADR-N-042 rule documents, NGSI-LD `!attr` existence test), a move would cost a delete and a create per entity and break its history, and the mark is visible to the steward who has to act on it.

### 2.7 Publication

- The gateway, the runner's stage and the sweep count every check in `jc_quality_checks_total{space,type,rule,outcome}` with `outcome` = `pass`, `reject`, `flag` or `quarantine` (DM-92).
- The Portal's space quality page (API/01 §27, extended) shows per type and rule the checks and pass rate over 24 hours and 7 days, the stale and quarantined counts, the latest rejected writes by rule and attribute without values, and the retention deletions, to whoever may read the space (DM-93).
- `jcctl publish` adds W3C DQV measurements to each dataset of the DCAT-AP record: `dqv:hasQualityMeasurement` for the pass rate and for the freshness (age of the newest `observedAt`), and the CKAN dataset shows them (DM-94).

### 2.8 Deletion is data loss

Every automatic removal, current state or history, is declared in a manifest of the space (`spec.retention`) or of a pipeline (PL-64), visible on the space page, applied only to the space that declared it, and logged per sweep with counts (DM-95). Shortening a retention asks the space's owner to confirm with the count the broker reports it will delete (DM-84).

## 3. Security Analysis

- **Retention never widens access.** A rule is pushed to one tenant by the Portal with the broker's admin token; the broker applies it only to that tenant. Only the space's owner role sets or shortens it (DM-84).
- **Quarantine only narrows.** The `!quarantinedAt` condition is added to permits; nothing is granted. The owner and steward see what they saw before.
- **No values leak.** A rejection names rule and attribute; the quality page, the metrics and the deletion log carry names, counts and ids, never values.
- **Bounded evaluation.** A pattern is linear-time with a size limit, a space holds at most 64 rules, and the write path evaluates without I/O (DM-91), so a rule cannot stall the gateway.
- **A rule cannot reach another tenant.** Rules are compiled per space and the sweep reads each space through its own surface as its own client.

## 4. Alternatives Considered

- **Retention on the DataModel class** (a LinkML annotation): one length for every space importing the model; rejected (2.1).
- **A new `RetentionPolicy` kind**: one more file and reconciler for a list of two durations; rejected.
- **The broker stamps `expiresAt` at write time**: needs a hook in every write path of both stores; rejected for the sweep by `modifiedAt` (2.2).
- **The gateway stamps `expiresAt`**: misses writes that do not cross the gateway's write path (the Portal's own writes, a future internal writer); rejected for the broker (2.2).
- **Quarantine as a separate tenant**: a delete and a create per entity, history split in two; rejected (2.6).
- **Great Expectations or Soda as the rule engine**: both check tables in batch after the fact (Python, a warehouse connection); the platform needs a verdict on each NGSI-LD write in the gateway and the runner. Their check kinds (ranges, patterns, freshness) shaped the three kinds here.
- **Only flag, never reject**: leaves the model's own constraints unenforced, which is the DM-27 gap this decision closes.

## 5. Consequences

- T-3900 (Antares): a retention table per tenant and type under `/q/retention/{tenant}`, the current-state sweep by `modifiedAt`, the history sweep and its metric.
- T-3901 (jc-core, Portal): `spec.retention` with its form, confirmation and the reconciler push.
- T-3902 (Portal compiler, gateway, runner stage, sweep): `spec.quality`, the model constraints on API writes (DM-27), the three outcomes, the metric.
- T-3903 (Portal, jcctl): the quality page and the DQV measurements.
- T-3904 (deployment): the Helsinki rules, replacing the `vehicles-reaper` pipeline.
- The DM-27 conformance case loses its expected-failure marker when T-3902 lands.

## 6. Requirements

- DM-81…DM-95: retention, the current-state sweep, the history sweep, the rules, the outcomes, the sweep, the bounds, the metric, the page, DQV, and deletion as declared data loss.

## Related

- [Requirements/data-models.md](../Requirements/data-models.md#15-data-lifecycle-and-quality) — the normative rules this decision is written down as.
- [ADR-N-042](adr-n-042-data-views.md) — the views and rule documents the quarantine condition narrows.
- [ADR-N-034](adr-n-034-pipeline-workbench.md) — the validation stage the space's rules join.
- [API/01 §27](../API/01-portal-api.md#27-data-quality-of-a-space-dm-74) — the quality report the page extends.
- [Architecture/08 §Stale-entity expiry](../Architecture/08-pipelines.md#stale-entity-expiry-pl-64-pl-65) — the pipeline expiry that stays beside the space rule.
