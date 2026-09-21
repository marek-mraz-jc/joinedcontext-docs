---
sidebar_position: 21
title: "Open Data Catalogue"
description: How a published Endpoint becomes a harvestable CKAN dataset, which organization it lands in, and what the demo installation publishes.
---

# Open Data Catalogue

An open-data catalogue is where a citizen, a journalist, a national portal's harvester and a partner's data scientist look first. The platform's catalogue is CKAN, and every record in it is a published Endpoint: nothing is authored in CKAN itself, so the catalogue cannot describe data the gateway would not serve. [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) states the publication contract, and this chapter answers the questions a catalogue raises around it: which organization a dataset lands in, how its metadata maps to DCAT-AP, when a dataset carries rows instead of a link, what the installation's own identity does to the portal, and what the demo publishes.

## 1. One organization per project

A CKAN organization is the unit a dataset belongs to and the unit membership is granted on. The platform maps one organization to one **project**, not to one context space.

A project is what a person is a steward of: the Access page grants roles inside it, a manifest carries its name as its namespace, and a Change is approved by somebody who holds `approve` there. A context space is internal tenancy. One space commonly backs several endpoints with different audiences, a space name is not a name a citizen would recognise, and nobody administers a space in CKAN. Mapping organizations to spaces would create a catalogue whose folders no person owns.

The slug comes from `spec.publish.ckan.organization`, and from the instance's `organizationDefault` when the Endpoint names none. The reconciler creates the organization when it is missing, with the title from the installation's branding (`branding.organisation`), so a fresh installation publishes into a folder that carries the city's name rather than a slug. An organization is never deleted by a publication run: withdrawing the last dataset of a project leaves the empty folder, because deleting it would also delete the membership a realm sync maintains.

### Naming

| Object | Name | Rule |
|---|---|---|
| Organization | `spec.publish.ckan.organization`, else `organizationDefault` | a DNS label, one per project; created, when CKAN has none, with the `CkanInstance`'s own `metadata.title`, else the branding `organisation` name, else the slug |
| Dataset | `spec.publish.ckan.name`, else the Endpoint's own name | one dataset per Endpoint; the name is what the dataset URL shows, so a rename is a new URL |
| Resource | the representation's own title | one resource per enabled representation, plus the schema index and one resource per schema artifact |
| DataStore table | the dataset's resource id | one table per dataset, keyed by `entity_id` |

CKAN groups are not used. A group is a second taxonomy that has to be maintained by hand beside the first, and the two drift; the keywords of the DCAT-AP record carry the subject of a dataset, and the organization carries its owner.

## 2. Metadata is the record, mapped

The dataset's metadata is the DCAT-AP record the Endpoint already answers with (EP-27, EP-63). The publisher maps it and writes nothing of its own except the provenance of the run:

| CKAN field | DCAT-AP term | Note |
|---|---|---|
| `title` | `dct:title` | in the language of the Endpoint's space (`ContextSpace.spec.defaultLocale`), else English, else the first the record carries; the dataset name when it carries none |
| `notes` | `dct:description` | in the same language as the title |
| `license_id` | `dct:license`, else `spec.publish.ckan.license` | a register id such as `cc-by` (CC-BY 4.0); an IRI goes to the `license_url` extra instead, because CKAN's register holds ids |
| `private` | `spec.audience` | private unless the Endpoint is `public`, closed by default |
| `url` | the Endpoint's public URL | the dataset points back at the surface it describes |
| `tags` | `dcat:keyword` | |
| extra `identifier` | `dct:identifier` | |
| extra `language` | `dct:language` | |
| extra `frequency` | `dct:accrualPeriodicity` | what the dataset page shows as the update cadence |
| extra `publisher` | `dct:publisher` | |
| extra `contact_point` | `dcat:contactPoint` | |
| extra `spatial` | `dct:spatial` | |
| extra `temporal` | `dct:temporal` | |
| extra `conforms_to` | `dct:conformsTo` | the formalisms of the model the Endpoint serves |
| extra `status` | `adms:status` | |
| extra `endpoint` | the Endpoint URL | so an edit made by hand in CKAN is visible as drift |
| extra `generated_by` | the publisher | `jcctl/ckan-publisher` |

The mapping lives in `crates/jcctl/src/publish/ckan.rs` and is asserted against the official DCAT-AP shapes by the conformance suite, which is what makes the catalogue harvestable: a national portal reads `catalog.rdf` from CKAN's DCAT extension, and every field it needs is one of the rows above. A record that carries no publisher produces a dataset without one rather than with an invented one, so a harvester's own validation says what is missing instead of accepting a guess. The licence is the one term the gateway's record does not carry, and the only one the publication block may state: `spec.publish.ckan.license` is the licence the organization chose for the dataset, used when the record names none. Without either, the dataset has no licence, and a licence set by hand in CKAN does not survive the next run, because every run writes the whole dataset (CC-18).

## 3. Rows, links and dumps

A dataset carries three kinds of resource, and the choice is the Endpoint's, not the catalogue's.

- **A link per representation** is always written. The resource URL is that representation's own URL under the Endpoint, so a download passes the gateway and its policy set, and a restricted dataset's links are useless without a token. This is what makes the catalogue safe to publish at all.
- **A DataStore sheet** is written when the Endpoint declares `spec.publish.ckan.datastore`. It gives the dataset page a preview, a filtered API and SQL over the rows, which a link alone cannot. The sheet is filled through the Endpoint's tabular representation as an ordinary consumer, one column per attribute and one row per entity, keyed by the entity's URN (`crates/jcctl/src/publish/ckan_datastore.rs`). `refresh: onChange` upserts the entities a notification named, re-read through the Endpoint; `refresh: onReconcile` reloads the table on the reconcile tick, for a space with no subscription. A row whose entity the Endpoint no longer answers for is deleted by the same rule, so a deletion behind the Endpoint propagates instead of leaving a public copy.
- **A file dump** is not written. The `zip` and `csv` representations are already downloads of the same data, served through the policy set, and a third copy in CKAN's file store would be the one nobody rebuilds.

The cadence a person reads on the dataset page is the `frequency` extra, which comes from the Endpoint's own record. A sheet says the same thing in the resource description, so a preview that is a day old does not read as live.

## 4. The catalogue carries the installation's identity

One CKAN image serves every installation and the identity is mounted, not built in. `components/ckan/values/catalogue/base-values.yaml.gotmpl` passes `global.branding` into the chart unchanged, which is the same block the Portal serves at `/api/v1/branding`: instance name, organization, colours, logo and favicon. A rebrand is a values edit and an apply, with no image rebuild, and the catalogue, the Portal and a generated application cannot end up with three different logos.

Login is Keycloak's. The catalogue runs the OIDC extension against the installation's realm, so who may open a private dataset is a realm membership and the platform creates no CKAN-local accounts. The public landing page is the catalogue's own, under `data.<domain>` at the edge.

## 5. What the demo publishes

The Helsinki project publishes four datasets into the `hel-fi` organization of the catalogue at `data.<domain>`, declared by the seed manifests in `components/context-gateway/seed/helsinki/`:

| Dataset | Endpoint | Representations | Sheet |
|---|---|---|---|
| `helsinki-all` | Helsinki city context, everything | NGSI-LD, GeoJSON, CSV, XLSX, ZIP, MCP | CSV, on reconcile |
| `helsinki-bikes` | Helsinki city bike stations | the same six | CSV, on reconcile |
| `helsinki-transport` | Helsinki trunk-line buses | the same six | CSV, on reconcile |
| `helsinki-events` | Helsinki events | the same six | CSV, on reconcile |

All four Endpoints are `audience: public`, so all four datasets are public, and the catalogue is not empty on a fresh installation. The instance itself is `helsinki-ckan-hel-fi.yaml`, whose `apiTokenRef` is resolved at run time and never held in the manifest.

The region publishes one dataset into its own organization of the same catalogue, declared by `components/context-gateway/seed/bbsk/`:

| Dataset | Organization | Endpoint | Slovak title in the manifest | Representations | Sheet |
|---|---|---|---|---|---|
| `bbsk-kpi` | `bbsk` (Banskobystrický samosprávny kraj) | `bbsk/bbsk-kpi` | Ukazovatele kraja | NGSI-LD, CSV, JSON | CSV, on reconcile |

Each body carries its own `CkanInstance` (`bbsk-ckan.yaml`, `ckan-banskabystrica.yaml`) whose `organizationDefault` is the project's name, so a body's dataset can only land under that body. The dataset name is the Endpoint's name, because the publication sets no `publish.ckan.name`. The owner cleared the region's indicators and the city's air quality on 2026-09-21 with the licence CC-BY 4.0; no manifest field can state that licence yet, so the dataset carries none until T-2465 gives the record one. The same task makes the space's locale choose the title: the publisher takes the English text of a language map today, so the dataset shows "Region indicators" until it lands.

The city's air quality, `banskabystrica/public-air`, is cleared and held: its space `ovzdusie` holds the thirteen seeded test stations, which sit in Helsinki and carry no PM10 or PM2.5 reading, and publishing them under the city's name and an open licence would put test data in a harvested catalogue as the city's air. Its `publish` block is written in the seed and commented out; it is restored when the space holds the city's own measurements or the owner decides otherwise.

The three other Endpoints of the two bodies stay out of the catalogue: `banskabystrica/banskabystrica-kpi` (`project-list`), `banskabystrica/banskabystrica-mesto` and `bbsk/bbsk-kraj` (both `organization`). EP-69 would publish each of them as a private dataset that a person browsing the catalogue cannot open, and none of the three has been reviewed by its body for publication, so they declare no `publish` block.

### What runs the publication

The publisher is a library and a command. The Portal's reconciler holds the library and runs it on every sync (`src/reconciler/ckan.rs`, T-2405): each Endpoint that declares `spec.publish.ckan` is published, and an Endpoint that stopped declaring one has its dataset withdrawn, which is the cadence `refresh: onReconcile` names. `jcctl publish ckan` publishes one Endpoint or a whole repository from a shell with the same code, which is how a catalogue is filled before a Portal runs against it.

## Related

- [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) — the publication contract, the manifest fields and what one Endpoint becomes.
- [../Requirements/endpoints.md](../Requirements/endpoints.md) — EP-62 to EP-69, the normative rules this chapter designs around.
- [../Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md) — the `ckan` add-on, what it deploys and what it costs to run.
- [../Deployment/12-branding-and-naming.md](../Deployment/12-branding-and-naming.md) — the branding block the catalogue mounts.
- [09-portal.md](09-portal.md) — the Portal, which holds the reconciler the publication belongs to.
