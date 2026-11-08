---
sidebar_position: 69
title: "ADR-N-068: Catalogue Datasets of an Endpoint"
---

# ADR-N-068: Catalogue Datasets of an Endpoint

Date: 2026-11-08  
Status: Accepted  
Decision Makers: product owner (2026-11-08, supervisor session: "change it automatically: it can be one dataset to one endpoint, but there can be multiple datasets from one endpoint"); drafted by jc-datasets, the supervisor's details are marked "Decided (supervisor, owner may override)"

This record decides which catalogue datasets an Endpoint becomes. Every public Endpoint becomes one dataset without anyone writing a publication block, and an Endpoint MAY instead declare several datasets, each a narrowed slice of what it serves. It changes [EP-62](../Requirements/endpoints.md) ("exactly one dataset per declaring Endpoint"), keeps [EP-63](../Requirements/endpoints.md) (metadata from the record) and [EP-139](../Requirements/endpoints.md) (`harvest: false`), and adds EP-174…EP-178. It builds on the catalogue block of [Architecture/04 §3a](../Architecture/04-context-spaces-and-endpoints.md#the-catalogue-block-ep-78ep-80) and the publisher of [Architecture/21](../Architecture/21-open-data-catalogue.md).

## 1. Context

- **A dataset needs a block.** Today only an Endpoint with `spec.publish.ckan` becomes a CKAN dataset (EP-62). A public Endpoint without one is served, listed in the gateway feeds (EP-84, EP-127) and missing from the open-data catalogue, so the feeds and the catalogue disagree about what the installation publishes.
- **One Endpoint, one dataset.** A space holding several types (a region's schools, pharmacies and bridges) is one Endpoint, but a reader looks for "schools". T-4344 split such a space into one Endpoint per type, each published, and left the whole-space Endpoint public with `harvest: false` (EP-139) so the Apps that read it keep working. Every split costs an Endpoint, a slug, a Policy binding and a second door to keep in step.
- **Names are global.** A CKAN dataset name is one namespace per catalogue. The Portal refuses two Endpoints that claim one name (T-6079) at publish time only, and withdraws by the Endpoint's previous publication, so one Endpoint can only ever hold one name.

## 2. Decision

### 2.1 Every public Endpoint is one dataset, automatically

Decided (supervisor, owner may override): an Endpoint whose `audience` is `public` becomes exactly one catalogue dataset with no `spec.publish` block. The dataset is named after the Endpoint (`metadata.name`), and its metadata is its DCAT-AP record (EP-27, EP-63). It lands on:

1. the `CkanInstance` that `spec.publish.ckan.instanceRef` names, when the Endpoint names one;
2. else the project's only `CkanInstance`;
3. else the installation's catalogue, when the Portal is configured with one (the instance the first-start setup declares; `jc` fills it from its dataroom mount);
4. else nowhere: a project with several instances and no `instanceRef` publishes nothing and the reconciler reports the Endpoint once, naming `spec.publish.ckan.instanceRef` as the fix.

The organization is `spec.publish.ckan.organization`, else the instance's `organizationDefault`.

What stays out:

- `spec.catalog.harvest: false` opts the Endpoint out of the catalogue as it opts it out of the feeds (EP-139).
- An App's own Endpoint (`app-{name}` beside an `App` of that name in the project, written by the App reconciler) re-serves a space for that App and is no dataset, as the feeds already decide (API/08 §6).
- A non-public Endpoint is never published automatically. An explicit `spec.publish.ckan` on a closed Endpoint keeps its private dataset, readable only by the publisher's token (EP-69), because removing it would break a declared publication.

`spec.publish.ckan` keeps working as the explicit form: it names the instance, the organization, the dataset name and the licence, and it reads as the same one dataset.

### 2.2 Several datasets: `spec.catalog.datasets`

Decided (supervisor, owner may override): an Endpoint MAY list its datasets:

```yaml excerpt
spec:
  audience: public
  catalog:
    license: CC_BY_4_0
    datasets:
      - name: bbsk-skoly
        title: { sk: Školy kraja, en: Schools of the region }
        description: { sk: Stredné školy v zriaďovateľskej pôsobnosti kraja, en: Secondary schools the region runs }
        types: [School]
        keywords: { sk: [školy, vzdelávanie] }
      - name: bbsk-gymnazia
        title: { sk: Gymnáziá kraja }
        description: { sk: Gymnáziá v zriaďovateľskej pôsobnosti kraja }
        types: [School]
        q: 'schoolType=="gymnazium"'
        license: CC0
```

The list replaces the default single dataset: each entry is one dataset and the Endpoint's own name is no dataset while the list is there.

| Member | Required | Rule |
|---|---|---|
| `name` | yes | the CKAN dataset name: 2 to 100 characters of `a-z`, `0-9`, `-`, `_`; unique in the list, and unique in the catalogue across every Endpoint of the installation |
| `title` | yes | per language, at least one |
| `description` | yes | per language, at least one; DCAT-AP requires both |
| `types` | yes | 1 to 20 distinct NGSI-LD type names, each a type the Endpoint serves |
| `q` | no | an NGSI-LD query (CIM 009 clause 4.9) the dataset's rows match, at most 2,000 characters |
| `keywords` | no | per language, replaces `spec.catalog.keywords` for this dataset |
| `license` | no | an EU licence table code, replaces `spec.catalog.license` for this dataset |

Every other member of `spec.catalog` (publisher, contact point, themes, spatial, temporal, frequency, source, legislation, personal data) holds for each dataset. At most 50 datasets per Endpoint.

### 2.3 Each dataset has its own record

Each dataset is a `dcat:Dataset` of its own at `https://api.{domain}/api/endpoint/{slug}/datasets/{name}`, served as JSON-LD and Turtle beside the Endpoint's record, to the callers the Endpoint's record answers (EP-27):

- `@id` is that address and `dct:identifier` is the dataset name, so a re-harvest updates the dataset instead of duplicating it.
- `dct:title`, `dct:description`, `dcat:keyword` and `dct:license` come from the entry, every other term from the Endpoint's record.
- The distributions are the Endpoint's, narrowed to the slice: the NGSI-LD query `ngsi-ld/v1/entities?type={types}&q={q}`, the CSV `file.csv?type={types}&q={q}`, and per type, when there is no `q` and the Endpoint serves `ogc-features`, the OGC items `ogc/features/collections/{type}/items`. The schema artifacts stay as they are. The surfaces that cannot be narrowed by a URL (MCP, WebSocket, OData, SensorThings, feeds, iCalendar) are reached through the Endpoint's `dcat:DataService`, which every distribution names in `dcat:accessService`.
- The Endpoint's own record stays at its address and keeps describing the whole Endpoint, the `dcat:DataService` every dataset of it names.

The feeds of EP-84 and EP-127 hold one record per dataset: an Endpoint with `datasets` contributes each dataset's record and not its own, an Endpoint without contributes its own record, as today.

The CKAN dataset of a slice is built from the slice's record, as EP-63 builds one from the Endpoint's: its resources are the narrowed distributions, the schema index, the slice's record (EP-143) and the schema artifacts; its `endpoint` extra names the Endpoint, so the Portal's dataset page reads its sample through the Endpoint (EP-82). The declared visualizations go on the first dataset of the list and the automatic charts on the dataset whose types they chart.

### 2.4 A slice only narrows

Decided (supervisor, owner may override), each a refusal at validation that names the field:

- **Types.** Every `types` entry is a class of the space's model the Endpoint serves, as its ModelProjection narrows it (`jcctl validate`, the Portal's plan); a public dataset's types are also ones the Endpoint's bound Policies grant the public (the publisher). An unknown or withheld type is refused, so a slice never names data the Endpoint does not serve.
- **Query.** `q` is parsed with the broker's own grammar (`antares_ql::parse_q`) and refused when it does not parse, holds a character outside the query grammar that a URL reads as a separator (`&`, `#`, `?`, a control character), or is longer than 2,000 characters. The dataset's URLs percent-encode it. A `q` can only drop rows: every distribution is a read through the Endpoint, where its Policy and projection decide again for each caller, so a slice answers no row and no attribute its Endpoint would not.
- **Names.** A name another entry of the list holds, the name of another Endpoint's dataset in the same catalogue (its default, its `publish.ckan.name` or one of its `datasets`), and `publish.ckan.name` beside `datasets` are refused; the refusal names the other Endpoint as `{project}/{name}`.
- **Contradictions.** `datasets` beside `harvest: false` is refused, as `publish.ckan` beside it already is (EP-139).

### 2.5 Withdrawing keys by the dataset's global name

The reconciler computes, from the repository before and after a change, the set of `(catalogue, dataset name)` pairs the platform publishes. A pair that was published and is not any more is withdrawn; nothing else is. Removing one entry of `datasets` withdraws exactly that dataset, never a sibling and never another Endpoint's dataset of the same name. A name that moves from one Endpoint to another is never withdrawn on the way. The sweep that finds a platform-made dataset nobody declares (T-4461) keeps every pair of the current set, so it agrees.

### 2.6 Moving from the split to one Endpoint

A space split into one Endpoint per type (T-4344) moves to one Endpoint with `datasets` without a gap in the catalogue:

1. In one Change, add `datasets` to the whole-space Endpoint with one entry per split Endpoint, each entry named as that Endpoint's dataset was, and remove `harvest: false` from it.
2. The same Change takes the split Endpoints out of the catalogue: it removes their `spec.publish.ckan` blocks and sets `harvest: false` on each one that stays for its Apps, so none becomes a dataset of its own name automatically, or it deletes the split Endpoints no App reads.
3. On the next run the reconciler sees each name move from a split Endpoint to the whole-space Endpoint: the pair `(catalogue, name)` is in both sets, so nothing is withdrawn and the dataset is updated in place with the slice's resources. Only names that leave the set are withdrawn.

A city that prefers two Changes publishes the new names first and withdraws the old ones in a second Change; the catalogue then holds both for one run.

## 3. Alternatives considered

- **Keep one Endpoint per dataset (T-4344).** Works, and stays valid, but every dataset costs a door to keep in step with its Policy, and readers of the whole space get a second address.
- **A `Dataset` kind beside the Endpoint.** A dataset would have its own file, owner and review lane. Rejected: a dataset has no access rule of its own, and a second file would let it drift from the Endpoint it narrows.
- **Publish only on request, as today.** Rejected by the owner's order: the feeds already list every public Endpoint, the catalogue should too.

## 4. Consequences

- A public Endpoint without a publication block appears in the catalogue on the next run after this change merges. An installation that did not want that sets `harvest: false` on it.
- Two public Endpoints of one name in two projects publishing to one catalogue now collide at validation, where they used to collide only if both declared `publish.ckan`; one renames its dataset with `publish.ckan.name`.
- The NGSI-LD catalogue (EP-140) holds one `Dataset` per CKAN dataset, so an Endpoint with three datasets has three `Dataset` entities, each with `refDataService` to the one Endpoint.
- `publish.ckan.datastore` stays refused (T-5060).

## Related

- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-62, EP-139 and the new EP-174…EP-178.
- [Architecture/21 §11](../Architecture/21-open-data-catalogue.md#11-one-endpoint-several-datasets) — how the publisher builds each dataset.
- [Architecture/04 §3a](../Architecture/04-context-spaces-and-endpoints.md#the-catalogue-block-ep-78ep-80) — the catalogue block the list lives in.
- [ADR-N-053](adr-n-053-declarative-visualizations.md) — the visualization views a dataset carries.
