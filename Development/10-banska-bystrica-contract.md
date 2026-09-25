---
sidebar_position: 12
title: "The Banská Bystrica Contract"
description: The two projects, their spaces, their entity ids and the shape of a KPI entity, frozen so ingestion, computation and the application can be built at the same time.
---

# The Banská Bystrica contract

What the region demonstration is allowed to write, spelled out once so that ingestion,
computation and the application are built against a fixed interface instead of against each
other. Read this before writing a pipeline, a KPI or a view for `bbsk` or `banskabystrica`.
Nothing here is research: every line is either a decision taken here or a rule already in force,
and a rule already in force is cited so it can be checked. The feeds these spaces hold are in
[the source survey](../Research/banska-bystrica-open-data-sources.md).

## 1. Two projects, two publishers

| | `bbsk` | `banskabystrica` |
|---|---|---|
| body | Banskobystrický samosprávny kraj | Mesto Banská Bystrica |
| `orgDomain` | the instance's Organization, `hel.fi` on dev | the same |
| territory | the kraj, NUTS `SK032`, 13 okresy | the city, LAU `SK0321508438` |
| people | 607 581 at the end of 2025 | 72 123 on 2026-09-20 |
| holds the application | yes | no |

They are two projects because they are two publishers with two mandates. A figure of one
presented as the other is wrong by a factor of eight in population, and no dashboard shows that.

They are two projects of **one** Organization, not two Organizations: an instance serves one
Organization (PF-01), so both bodies' ids carry the same `{orgDomain}`, and on dev that is
`hel.fi`. The domain therefore cannot say whose a figure is. The `{space}` segment can: every
space of a project is named with that project's prefix (section 2), a space name and its segment
are unique in the Organization (PF-44), and only a project's own pipeline writes into its
indicator space (section 7). A reader credits a `KeyPerformanceIndicator` by the space it sits in:

| `{space}` segment | publisher |
|---|---|
| `bbsk-kpi` | `bbsk`, the region |
| `banskabystrica-kpi` | `banskabystrica`, the city |

A KPI in any other space is no indicator of either body and is not shown, because section 2
puts indicators in these two spaces and nowhere else.

## 2. Spaces, and the segment each one writes into an id

A Context Space name is unique in the Organization, and the `{space}` segment of an entity id is
rendered as `{project}-{name}` (PF-44, PF-84). The names below are therefore what the manifests
carry, and the segments are what the ids carry. They are not the same string, and writing the
short name into an id is the mistake this table exists to prevent.

| project | space `metadata.name` | `{space}` segment | holds |
|---|---|---|---|
| `bbsk` | `bbsk-kraj` | `bbsk-kraj` | the national feeds filtered to `SK032` and its okresy, as fetched |
| `bbsk` | `bbsk-kpi` | `bbsk-kpi` | `KeyPerformanceIndicator` entities only |
| `bbsk` | `bbsk-registre` | `bbsk-registre` | the region's own registers from opendata.bbsk.sk: districts, municipalities, its organisations, hospitals, public social services, bridges (T-2783) |
| `banskabystrica` | `banskabystrica-mesto` | `banskabystrica-mesto` | the city's own feeds, as fetched |
| `banskabystrica` | `banskabystrica-kpi` | `banskabystrica-kpi` | `KeyPerformanceIndicator` entities only |
| `banskabystrica` | `banskabystrica-verejne` | `banskabystrica-verejne` | the city's events, the schools of the national school map in the city, and hourly PM10 and PM2.5 of station SK0263A from the EEA (T-2781) |
| `banskabystrica` | `ovzdusie` | `ovzdusie` | the thirteen seeded `AirQualityObserved` entities of T-0945 |

`ovzdusie` predates PF-84 and its entity ids are already published, so its space manifest pins
the old segment and no id changes:

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: ovzdusie
  namespace: banskabystrica
spec:
  urnSegment: ovzdusie      # predates PF-84; pinned so no published id changes
  defaultLocale: sk
```

A space name is unique in the whole Organization, not in its project (PF-44), so a space named
`kraj` or `kpi` in both projects would collide. Each name therefore carries its project, which
is also what PF-84 renders the segment as, and every space pins the segment so no published id
can move under anyone. That the name and the segment are the same string is deliberate: it is
one thing to get right instead of two, and it is what the seed's own check asserts.

## 3. Entity ids

Every id is `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}` with exactly four segments
(PF-42). A colon inside `{localId}` would make a fifth segment and fail the check, so a territory
is joined with a hyphen and never with a colon.

| space | one literal id |
|---|---|
| `bbsk-kraj` | `urn:ngsi-ld:StatisticalObservation:hel.fi:bbsk-kraj:zp3803rs-SK032-2023-PROD_TONY-1` |
| `bbsk-kpi` | `urn:ngsi-ld:KeyPerformanceIndicator:hel.fi:bbsk-kpi:emisie-tuhe-okres-brezno` |
| `banskabystrica-mesto` | `urn:ngsi-ld:StatisticalObservation:hel.fi:banskabystrica-mesto:vh5003rr-SK0321508438-2023-U03084` |
| `banskabystrica-kpi` | `urn:ngsi-ld:KeyPerformanceIndicator:hel.fi:banskabystrica-kpi:spotreba-vody-mesto` |
| `ovzdusie` | `urn:ngsi-ld:AirQualityObserved:hel.fi:ovzdusie:stanica-1` |

The `{localId}` of a raw observation is the publisher's own key, in the publisher's own spelling:
the cube code, the territory code, the period and the indicator code, joined by hyphens. Nothing
is renamed on the way in, so a row can always be traced back to the request that produced it.

**`StatisticalObservation` is a new type and this page mints it.** The six feeds the survey found
are statistical tables and none of them is a Smart Data Model: a territory code, a period, an
indicator code and a number. The raw spaces hold them under a type of ours whose LinkML model
each raw space declares, with the dimensions as slots and one `value` measure. It is deliberately
**not** a Data Structure Definition in the sense of DM-60: a declared DSD puts its observations
in the project's indicator space, and the raw space would then hold nothing. When a KPI needs
slicing by a dimension rather than one number per territory, DM-60 is the upgrade, and the
observations move to the indicator space at that moment.

## 4. The KPI entity

A `KeyPerformanceIndicator` is one number for one window with the provenance that makes it
auditable (PF-54, PF-55). The platform publishes the schema, `schemas/kinds/KeyPerformanceIndicator.json`,
it closes the object (`additionalProperties: false`), and it requires every attribute below. This
contract adds nothing to it.

| attribute | NGSI-LD form | type and unit | mandatory |
|---|---|---|---|
| `id` | the URN of section 3 | string | yes |
| `type` | `KeyPerformanceIndicator` | string | yes |
| `name` | Property | string, equal to the `{localId}` | yes |
| `currentValue` | Property | number or string, `unitCode` a UN/CEFACT common code, `observedAt` RFC 3339 | yes |
| `calculationPeriod` | Property | `{ start, end }`, RFC 3339 instants | yes |
| `calculationFormula` | Property | string, how the value is computed | yes |
| `derivedFrom` | Relationship | the Endpoint URN the sources were read through | yes |
| `computedBy` | Relationship | the Pipeline URN that computed it | yes |
| `updatedAt` | Property | `{ "@type": "DateTime", "@value": … }` | yes |

### Where the fields this demonstration asked for actually live

| asked for | where it is |
|---|---|
| `value` | `currentValue.value` |
| `unit` | `currentValue.unitCode`, a UN/CEFACT common code |
| `window` | `calculationPeriod.value.start` and `.end` |
| `computedAt` | `updatedAt.value["@value"]` |
| `sources` | `derivedFrom.object`, the Endpoint URN and the source entity URNs when they are few |
| `territory` | the `-{territory}` suffix of `{localId}`, and therefore of `name` |
| `state` | nowhere on the entity, see below |
| `threshold` | nowhere on the entity, see below |

**`state` and `threshold` are not entity attributes, and this is a decision, not an omission.**
PF-54 fixes the attribute set and the published schema closes the object, so an entity carrying
either one is rejected by `jc-core` and by the gateway before it is stored. A threshold is a
judgement of whoever reads the number, it changes without the number changing, and two
departments may hold different ones for the same indicator. It therefore lives in the
configuration of the view that shows the indicator, and the state, green, amber or red, is what
that view computes from the value and its own threshold. An indicator that has no number at all
is a different case and section 5 gives it a value of its own.

### One entity, literally

```json ngsi-ld-kpi
{
  "id": "urn:ngsi-ld:KeyPerformanceIndicator:hel.fi:bbsk-kpi:emisie-tuhe-okres-brezno",
  "type": "KeyPerformanceIndicator",
  "name": { "type": "Property", "value": "emisie-tuhe-okres-brezno" },
  "currentValue": {
    "type": "Property",
    "value": 4037.7,
    "unitCode": "TNE",
    "observedAt": "2026-09-20T06:00:00Z"
  },
  "calculationPeriod": {
    "type": "Property",
    "value": { "start": "2023-01-01T00:00:00Z", "end": "2023-12-31T23:59:59Z" }
  },
  "calculationFormula": {
    "type": "Property",
    "value": "sum(value) over StatisticalObservation where cube=zp3803rs, indicator=PROD_TONY, pollutant=1, refArea=SK032"
  },
  "derivedFrom": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Endpoint:hel.fi:bbsk-kraj:bbsk-kraj"
  },
  "computedBy": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Pipeline:hel.fi:bbsk-kpi:emisie-tuhe"
  },
  "updatedAt": {
    "type": "Property",
    "value": { "@type": "DateTime", "@value": "2026-09-20T06:00:00Z" }
  }
}
```

`TNE` is the UN/CEFACT common code for tonne. `C62` is the code for a plain count, `MTQ` for a
cubic metre. The value is the one `zp3803rs` returned for `SK032` in 2023, decoded by the cube's
own dimension index and not by assuming its years ascend, which they do not. A KPI whose number
was typed rather than read, or read against the wrong year, is the defect this whole chain exists
to prevent.

## 5. A window with no readings

An indicator whose window holds no source rows is written, not skipped, and it does not write a
zero. A zero is a measurement, and a dashboard cannot tell it apart from a real one.

```json ngsi-ld-kpi
{
  "id": "urn:ngsi-ld:KeyPerformanceIndicator:hel.fi:bbsk-kpi:emisie-tuhe-okres-poltar",
  "type": "KeyPerformanceIndicator",
  "name": { "type": "Property", "value": "emisie-tuhe-okres-poltar" },
  "currentValue": { "type": "Property", "value": "not measured" },
  "calculationPeriod": {
    "type": "Property",
    "value": { "start": "2026-01-01T00:00:00Z", "end": "2026-09-20T00:00:00Z" }
  },
  "calculationFormula": {
    "type": "Property",
    "value": "sum(value) over StatisticalObservation where cube=zp3803rs, indicator=PROD_TONY, pollutant=1, refArea=SK0327"
  },
  "derivedFrom": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Endpoint:hel.fi:bbsk-kraj:bbsk-kraj"
  },
  "computedBy": {
    "type": "Relationship",
    "object": "urn:ngsi-ld:Pipeline:hel.fi:bbsk-kpi:emisie-tuhe"
  },
  "updatedAt": {
    "type": "Property",
    "value": { "@type": "DateTime", "@value": "2026-09-20T06:00:00Z" }
  }
}
```

What changes and what does not:

- `currentValue.value` is the string `not measured`. The schema's value is a number **or** a
  string, "a grade or a state", so this validates and no arithmetic can consume it by accident.
- `currentValue.unitCode` is **absent**: there is no quantity, so there is no unit.
- `currentValue.observedAt` is **absent**: nothing was observed.
- everything else is present and unchanged, including the period and both relationships, because
  the question was asked of a real window through a real endpoint and that is worth recording.

A view renders this as "not measured" and never as a number, a colour or a trend point.

## 6. Territories

The allowed values of the `-{territory}` suffix. Anything else is a defect, because a territory
that no source covers cannot produce a number.

| token | covers | source code |
|---|---|---|
| `kraj` | the whole Banskobystrický kraj | `SK032` |
| `mesto` | the city of Banská Bystrica | `SK0321508438` |
| `okres-banska-bystrica` | okres Banská Bystrica | `SK0321` |
| `okres-banska-stiavnica` | okres Banská Štiavnica | `SK0322` |
| `okres-brezno` | okres Brezno | `SK0323` |
| `okres-detva` | okres Detva | `SK0324` |
| `okres-krupina` | okres Krupina | `SK0325` |
| `okres-lucenec` | okres Lučenec | `SK0326` |
| `okres-poltar` | okres Poltár | `SK0327` |
| `okres-revuca` | okres Revúca | `SK0328` |
| `okres-rimavska-sobota` | okres Rimavská Sobota | `SK0329` |
| `okres-velky-krtis` | okres Veľký Krtíš | `SK032A` |
| `okres-zvolen` | okres Zvolen | `SK032B` |
| `okres-zarnovica` | okres Žarnovica | `SK032C` |
| `okres-ziar-nad-hronom` | okres Žiar nad Hronom | `SK032D` |
| `cast-{name}` | one city district, when a city feed breaks down that far | none yet |

The tokens are the publisher's own names with diacritics folded to ASCII and spaces hyphenated,
which is what `{localId}` accepts. The codes are the ones
`https://data.statistics.sk/api/v2/dimension/om7102rr/om7102rr_vuc?lang=sk` returned on
2026-09-20, so the mapping is checkable rather than remembered. No `cast-` token exists yet: no
feed in the survey breaks the city down by district, and a token without a feed behind it would
be an invitation to invent one.

## 7. Endpoints, and which of them anybody may open

Every read and every write goes through an Endpoint and its Policy. Endpoints are addressed by a
minted slug, never by a name, so the paths below are the shape and not the literal URL
(`https://{host}/api/endpoint/{endpointSlug}/ngsi-ld/v1/entities`, EP-02, EP-22).

One door per space, and the Policies on it decide who may read and who may write. A second
endpoint for writing would be a second thing to keep in step with the first.

| project | endpoint | over | audience | who reaches it |
|---|---|---|---|---|
| `bbsk` | `bbsk-kraj` | `bbsk-kraj` | `organization` | the pipelines, reading and writing with the `pipelines` service account |
| `bbsk` | `bbsk-kpi` | `bbsk-kpi` | `public` | the application and anybody, reading; the computing pipeline, writing |
| `bbsk` | `bbsk-registre` | `bbsk-registre` | `public` | anybody, reading; the register pipelines, writing |
| `banskabystrica` | `banskabystrica-mesto` | `banskabystrica-mesto` | `organization` | the pipelines, reading and writing |
| `banskabystrica` | `banskabystrica-kpi` | `banskabystrica-kpi` | `project-list`, `[bbsk]` | the region's application, reading through the share of section 8; the city's pipeline, writing |
| `banskabystrica` | `banskabystrica-verejne` | `banskabystrica-verejne` | `public` | anybody, reading; the city's open-data pipelines, writing |

Three endpoints are `public`: `bbsk`'s `bbsk-kpi`, which is what the demonstration shows;
`bbsk-registre`, which republishes the region's own registers under the region's own CC BY-SA 4.0
licence to its own catalogue organization (T-2783); and `banskabystrica-verejne`, which
republishes open data under CC BY 4.0 with each publisher's credit (T-2781). Creating any of them
is a red-lane Change that a binding with `approve` on the kind and the public constraint has to
approve (PF-72), and that approval is part of the demonstration rather than a step around it.
The two raw spaces are never public: they are a copy of somebody else's published data, and
republishing it under our own name at our own URL is not ours to do. `banskabystrica-verejne` is
the exception by construction: every source in it is licensed for republication with credit, and
every entity carries that credit in `dataProvider`. The city's KPI space is not public either; it
reaches the region by a named share and by nothing else.

## 8. How the city's indicators reach the region's application

The application lives in `bbsk` and shows both bodies' indicators. Cross-project access requires
the consumer project to declare the reference (EP-15), and naming the source by project and name
rather than by slug keeps it readable and still cannot widen access: the source Endpoint's
audience and Policy decide, exactly as a slug would (EP-77).

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: SharedSpaceReference
metadata:
  name: mesto-kpi
  namespace: bbsk
  title: "Indicators of Mesto Banská Bystrica"
spec:
  alias: mesto-kpi                 # how bbsk addresses it locally
  endpointRef:
    project: banskabystrica
    name: banskabystrica-kpi       # audience project-list, [bbsk], see section 7
  schedule:
    interval: 24h                  # how often the peer's schema surface is mirrored (DM-49)
```

Two things follow and both are deliberate. The region reads the city's indicators and cannot
write them, because the city's grant to the group `bbsk` is `retrieveOps` on
`KeyPerformanceIndicator` and its write grant is bound to its own `pipelines` service account.
And the city revokes by changing one audience, without the region's application being rebuilt.

## 9. What each task may now assume

| task | may assume |
|---|---|
| T-2305 | the projects, domains, space names and rendered segments of sections 1 and 2 |
| T-2306 | the KPI attribute set of section 4 and the territory tokens of section 6 |
| T-2307 | the entity of section 4, the empty window of section 5, and the `bbsk-kpi` and `banskabystrica-kpi` endpoints |
| T-2308 | the same two entities, read through `bbsk-kpi` and the share of section 8 |
| T-2309 | that `state` and `threshold` are the view's, not the entity's |

The two examples in sections 4 and 5 are validated against the platform's published
`KeyPerformanceIndicator` schema by `scripts/check-kpi-entities.py` on every run of the fast CI
lane, which is what makes this page a contract and not a note. A change to either example that
the schema rejects turns the lane red.

## Related

- [Open data sources of the Banská Bystrica region](../Research/banska-bystrica-open-data-sources.md) — the feeds these spaces hold, each with the status code it answered with.
- [Manifest kinds](04-manifest-kinds.md) — where `ContextSpace`, `Endpoint` and `SharedSpaceReference` are declared.
- [Domain model](../Architecture/03-domain-model.md#when-one-number-is-not-the-indicator-dm-60) — when one number is the indicator and when a data cube is.
- [Context Spaces and Endpoints](../Architecture/04-context-spaces-and-endpoints.md) — audiences, slugs and the sharing model this page applies.
- [Pipelines](../Architecture/08-pipelines.md) — the mapping that writes an indicator, with its provenance.
