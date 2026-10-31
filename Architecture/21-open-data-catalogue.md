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
| Resource | the representation's own title | one resource per served surface with its usage description (EP-108), plus the schema index and one resource per schema artifact; what each kind keeps current is [API/02 §10](../API/02-endpoint-representations.md#10-in-the-open-data-portal) (EP-109) |
| DataStore table | the entity type (`AirQualityObserved`) | one table per entity type the Endpoint serves, keyed by `entity_id`; a resource of the dataset named by the type |

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
| `tags` | `dcat:keyword` | one tag per distinct keyword in any language, written the way CKAN holds a tag: a character outside letters, digits, space, `-`, `_` and `.` becomes a space (`P+R` is the tag `P R`), spaces collapse, the tag is cut to 100 characters, and a keyword shorter than 2 characters after that is no tag; the record keeps the keyword as written (EP-63, T-2982) |
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

The mapping lives in `crates/jcctl/src/publish/ckan.rs` and is asserted against the official DCAT-AP shapes by the conformance suite, so a harvester reading the dataset finds every field it needs in the rows above; the feed a national portal harvests is the gateway's own catalogue (§8). A record that carries no publisher produces a dataset without one rather than with an invented one, so a harvester's own validation says what is missing instead of accepting a guess. The licence is the one term the gateway's record does not carry, and the only one the publication block may state: `spec.publish.ckan.license` is the licence the organization chose for the dataset, used when the record names none. Without either, the dataset has no licence, and a licence set by hand in CKAN does not survive the next run, because every run writes the whole dataset (CC-18).

## 3. Rows, links and dumps

A dataset carries three kinds of resource, and the choice is the Endpoint's, not the catalogue's.

- **A link per representation** is always written. The resource URL is that representation's own URL under the Endpoint, so a download passes the gateway and its policy set, and a restricted dataset's links are useless without a token. This is what makes the catalogue safe to publish at all.
- **A DataStore sheet** is no longer written by an Endpoint. CKAN holds no rows of an Endpoint: the catalogue reads the Endpoint live, and jc-core refuses an Endpoint that still declares `spec.publish.ckan.datastore` with a message that says to delete the block (`crates/jc-core/src/kinds/ckan.rs`). The preview and SQL tables of harvested source datasets (§9) are the only DataStore tables left.
- **A file dump** is not written. The `csv` representation is already a download of the same data, served through the policy set, and a third copy in CKAN's file store would be the one nobody rebuilds.

The cadence a person reads on the dataset page is the `frequency` extra, which comes from the Endpoint's own record. A sheet says the same thing in the resource description, so a preview that is a day old does not read as live.

## 4. The catalogue carries the installation's identity

One CKAN image serves every installation and the identity is mounted, not built in. `components/ckan/values/catalogue/base-values.yaml.gotmpl` passes `global.branding` into the chart unchanged, which is the same block the Portal serves at `/api/v1/branding`: instance name, organization, colours, logo and favicon. A rebrand is a values edit and an apply, with no image rebuild, and the catalogue, the Portal and a generated application cannot end up with three different logos.

Login is Keycloak's. The catalogue runs the OIDC extension against the installation's realm, so who may open a private dataset is a realm membership and the platform creates no CKAN-local accounts. The public landing page is the catalogue's own, under `opendata.<domain>` at the edge.

## 5. What the demo publishes

The Helsinki project publishes four datasets into the `hel-fi` organization of the catalogue at `opendata.<domain>`, declared by the seed manifests in `components/context-gateway/seed/helsinki/`:

| Dataset | Endpoint | Representations | Sheet |
|---|---|---|---|
| `helsinki-all` | Helsinki city context, everything | the list of [§9](#9-what-every-dataset-lists) | CSV, on reconcile |
| `helsinki-bikes` | Helsinki city bike stations | the same | CSV, on reconcile |
| `helsinki-transport` | Helsinki trunk-line buses | the same | CSV, on reconcile |
| `helsinki-events` | Helsinki events | the same | CSV, on reconcile |

All four Endpoints are `audience: public`, so all four datasets are public, and the catalogue is not empty on a fresh installation. The instance itself is `helsinki-ckan-hel-fi.yaml`, whose `apiTokenRef` is resolved at run time and never held in the manifest.

The region publishes one dataset into its own organization of the same catalogue, declared by `components/context-gateway/seed/bbsk/`:

| Dataset | Organization | Endpoint | Slovak title in the manifest | Representations | Sheet |
|---|---|---|---|---|---|
| `bbsk-kpi` | `bbsk` (Banskobystrický samosprávny kraj) | `bbsk/bbsk-kpi` | Ukazovatele kraja | NGSI-LD, CSV, JSON | CSV, on reconcile |

Each body carries its own `CkanInstance` (`bbsk-ckan.yaml`, `ckan-banskabystrica.yaml`) whose `organizationDefault` is the project's name, so a body's dataset can only land under that body. The dataset name is the Endpoint's name, because the publication sets no `publish.ckan.name`. The owner cleared the region's indicators and the city's air quality on 2026-09-21 with the licence CC-BY 4.0, which the publication states as `publish.ckan.license: cc-by` ([04 §7](04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal)). The dataset takes its title and notes in its space's language, so the region's dataset reads "Ukazovatele kraja", and a new organization takes the instance's own title (T-2465).

The city's air quality, `banskabystrica/public-air`, is cleared and held: its space `ovzdusie` holds the thirteen seeded test stations, which sit in Helsinki and carry no PM10 or PM2.5 reading, and publishing them under the city's name and an open licence would put test data in a harvested catalogue as the city's air. Its `publish` block is written in the seed and commented out; it is restored when the space holds the city's own measurements or the owner decides otherwise.

The three other Endpoints of the two bodies stay out of the catalogue: `banskabystrica/banskabystrica-kpi` (`project-list`), `banskabystrica/banskabystrica-mesto` and `bbsk/bbsk-kraj` (both `organization`). EP-69 would publish each of them as a private dataset that a person browsing the catalogue cannot open, and none of the three has been reviewed by its body for publication, so they declare no `publish` block.

### What runs the publication

The publisher is a library and a command. The Portal's reconciler holds the library and runs it on every sync (`src/reconciler/ckan.rs`, T-2405): each Endpoint that declares `spec.publish.ckan` is published, and an Endpoint that stopped declaring one has its dataset withdrawn, which is the cadence `refresh: onReconcile` names. `jcctl publish ckan` publishes one Endpoint or a whole repository from a shell with the same code, which is how a catalogue is filled before a Portal runs against it.

## 6. The Portal's catalogue page

`data.{host}` is CKAN's own site, and a person working in the Portal should not have to leave it to find what the installation publishes. The Portal therefore carries one catalogue page, `/catalogue`, linked from the sidebar and readable without signing in, so a link to it can be handed to a citizen (EP-81).

**Source.** The page reads CKAN, never the manifests: what it lists is what the catalogue holds, and the two views cannot disagree. The Portal collects the distinct `spec.url` of every `CkanInstance` of the installation and calls `package_search` on each as an anonymous caller, with no API token. CKAN answers an anonymous caller with public datasets only, and the Portal drops any dataset still marked `private`, so a restricted dataset can only be absent from the page (EP-67, EP-69). Several catalogues are merged into one list.

**Search and facets.** The text a person types goes to CKAN's own full-text search (`q`). Facets are computed by the Portal over the datasets that search returns, because the extras the publisher writes (§2) are free text to CKAN's Solr and cannot be faceted there:

| Facet | Read from | Shown as |
|---|---|---|
| Publisher | `organization.name` | the organization's title |
| Theme | extra `theme`, the EU data-theme IRIs | the theme's label (EP-78) |
| Format | `resources[].format` | the format as written |
| Licence | `license_id` | `license_title` |
| Spatial | extra `spatial_uri`, else `spatial` | the NUTS code or the last segment of the location IRI |
| Temporal | extras `temporal_start`, `temporal_end` | one value per calendar year covered; an open end runs to the current year |

Values in one facet are alternatives and facets combine with AND. The Portal keeps one answer per catalogue for 60 seconds, so a burst of anonymous visitors costs CKAN one search a minute, and reads at most 1000 datasets per catalogue.

**The dataset page** (EP-82) shows the description, keywords, publisher, licence, update frequency and themes from `package_show`, every resource with its format and URL, and the DataStore preview link where the dataset has a sheet (§3). When the dataset's `endpoint` extra is an Endpoint of this installation, the page adds three things the catalogue does not hold:

- the classes of the space's data model, each with its description, and a link to the Endpoint's schema documentation;
- a sample of up to ten rows, read anonymously through the Endpoint's NGSI-LD representation (`options=keyValues`), so the sample passes the Endpoint's policy set like any other read (EP-66);
- "Use this data": a curl command, the App SDK call and the MCP client configuration, all against the Endpoint's own URLs.

The Portal derives the Endpoint from the slug in that extra and builds every URL it fetches itself on the installation's own host. A dataset edited by hand in CKAN to point elsewhere gets no sample and no model, never a request to the address it names.

## 7. Publish a dataset in one step

Declaring `spec.publish.ckan` by hand asks a steward to know CKAN's vocabulary. The Portal offers one flow instead (EP-83), started from an Endpoint's page, from a space, or from the catalogue's **Publish** button:

1. **Pick the Endpoint** the person can propose changes to.
2. **Describe it.** The Portal drafts the DCAT-AP block of the Endpoint (`spec.catalog`, EP-78) from what the platform already knows: title and description from the Endpoint, else from the model's classes; keywords from the model's class and slot names, in the space's language; themes mapped from the model's class and slot IRIs where the vocabulary is known (Smart Data Models domains to EU data themes); the licence from a picker, CC BY 4.0 unless the person picks another; the publisher from the project's title (its CKAN organization, §1) and the contact point from the organization's `open-data` contact (EP-80). Spatial and temporal coverage and the update frequency are the person's to state: the draft names them in `missing` rather than reading the data to guess them. Every drafted field is editable, and a field the platform cannot know is left empty rather than guessed.
3. **Preview** the catalogue entry exactly as the dataset page of §6 will show it.
4. **Propose.** The flow writes one `Change` on the Endpoint: `spec.publish.ckan` naming the project's `CkanInstance` and `spec.catalog`. When the Endpoint is not `public` yet, the flow says, before the proposal, that publishing makes it public, and the Change takes the red lane with a publisher's approval (EP-76, PF-72). An Endpoint that stays non-public would publish a private dataset nobody browsing can open, so the flow offers the public audience and never publishes a restricted Endpoint silently.
5. **Approve.** A public publication is approved by a person other than its proposer who may approve Endpoints in the project, typing the Endpoint's name (EP-142). The proposer, a ServiceAccount token, the assistant and an MCP tool are refused with `403`, whatever role they hold: making data public is a person's decision, taken by a second person.
6. **After approval** the reconciler publishes the dataset on its next run (§5, What runs the publication), and it appears on the catalogue page.

The flow writes nothing to CKAN and needs no CKAN credential: the Change is the only write, and the publication stays the reconciler's.

## 8. The organization's DCAT-AP feed

A national portal (data.gov.sk, data.europa.eu) harvests a catalogue, not a list of endpoints. The context gateway serves the installation's catalogue as one `dcat:Catalog` at `https://api.{domain}/catalog.jsonld` and `https://api.{domain}/catalog.ttl` (EP-84): its datasets are the records of EP-27 of every Endpoint whose audience is `public`, each as the anonymous caller would read it, except an App's own door and an Endpoint with `spec.catalog.harvest: false`, a door over data other datasets already publish (EP-139), so the feed carries nothing a public read would not. The same pinned SEMIC shapes that check each record check the feed in the fast CI lane. The catalogue host serves the same records a second time, as CKAN holds them (EP-91): `https://opendata.{domain}/catalog.ttl` and `/dataset/{id}.ttl`, written by `ckanext-dcat`'s `euro_dcat_ap_3` profile with the catalogue theme's own profile on top, which turns CKAN's strings into the vocabulary IRIs the shapes ask for and adds the catalogue's publisher from `global.branding`. That is the address another CKAN's DCAT RDF harvester is given, because it harvests a catalogue host and its dataset pages, and it carries the DataStore download the gateway's record does not. A harvester takes one of the two, never both: the datasets of the two feeds have different URIs and the same `dct:identifier`, the Endpoint's slug. A national catalogue registers one local catalogue per publisher, so the gateway also serves a catalogue per Project that names its publisher, `https://api.{domain}/catalog/{project}.jsonld` and `.ttl` (EP-127), in DCAT-AP or a national profile ([API/08 §6](../API/08-dcat-profiles.md#6-one-catalogue-per-publisher)); data.slovensko.sk and data.gov.cz are given that URL, not the installation's. The deployment repository's DCAT-AP check, which the `ckan` component README names for an operator, validates the catalogue host's feed against the pinned 3.0.1 shapes.

## 9. What every dataset lists

The owner set one rule for every dataset of the catalogue on 2026-10-16 (EP-118). A dataset is NGSI-LD data the platform serves, so its page lists the platform's own doors to it, and a dataset that cannot list them is not in the catalogue.

| Distribution | When | CKAN format label |
|---|---|---|
| NGSI-LD API | always | `NGSI-LD` |
| Model Context Protocol | always | `MCP` |
| WebSocket | always | `WebSocket` |
| CSV | always; a whole-file download up to 50 MB, a paged API link (`limit` and `offset`) above it | `CSV` |
| The data model: JSON Schema, JSON-LD `@context`, LinkML, Markdown, OWL, RDF, SHACL | always | `JSON Schema`, `JSON-LD`, `LinkML`, `Markdown`, `OWL`, `RDF`, `SHACL` |
| OGC API - Features | when the rows carry a location | `OGCFEAT` |
| OData | optional | `OData` |
| ZIP, Esri REST, and `file.json`, `file.geojson`, `file.xlsx`, `file.parquet` | never: an Endpoint publishes one file, `file.csv` (T-4597) | |

A map reads a located dataset's GeoJSON from OGC API - Features or from the NGSI-LD API with `Accept: application/geo+json` ([API/02](../API/02-endpoint-representations.md)), so the catalogue lists no GeoJSON file. Decided (worker-3, owner may override): EP-118 follows T-4597 and lists CSV as the one file, because a listed `file.json`, `file.geojson` or `file.xlsx` now answers 404 and would break the rule that every listed link answers 200; options: keep JSON and GeoJSON as API links under their old labels, which would name one surface twice.

The labels are the ones `jcctl`'s publisher writes for an Endpoint's own dataset (`crates/jcctl/src/publish/ckan.rs`, `distribution`), so the format facet counts a harvested dataset and a published one under the same name. Every listed link answers 200 to an anonymous GET, because the catalogue lists public data only.

Beside the distributions, a dataset shows the views CKAN offers (the table and, for located rows, the map, T-4639) and one visualization view per chart its Endpoint lists in `spec.catalog.visualizations`. An Endpoint that lists none gets one line chart per numeric Property of each type that carries a `dateObserved` date-time, the history of every entity over the last seven days (`temporal` source, `P7D`, at most 20 charts; `series_charts` in `crates/jcctl/src/publish/ckan.rs`, T-4742), as hourly averages when the window is longer than a day (`aggrMethod: avg`, `aggrPeriod: PT1H`, T-6171) and drawn as lines whose points stay transparent, so each reading keeps its tooltip: a WaterQualityObserved's temperature is a chart, a register without `dateObserved` has its table and, when located, its map only. A chart is a Vega-Lite or Vega spec, never code, rendered in a sandboxed frame on `viz.{domain}` from the Endpoint's own rows; the frame reads only once it scrolls into view, starts a history window on the whole hour so one hour's page views ask the same URL, and draws on canvas past 2,000 rows (T-6171) ([ADR-N-053](../Decisions/adr-n-053-declarative-visualizations.md), EP-130…EP-132). A view is not a distribution: it adds no link and no format to the facet. The publisher sends a view only the fields its view type declares (EP-144): a field CKAN does not know makes it refuse the whole view with `409 __extras`. Beside the distributions, the dataset links the Endpoint's own DCAT-AP record, the record it was made from (EP-143). Revoking a publication, by removing `spec.publish.ckan` or the Endpoint, withdraws the dataset on the next reconcile (EP-62).

A harvested source dataset (`charts/ckan/files/harvest-hub.py`, `harvest-nkod.py`) lists none of its source's links: its rows reach the catalogue as an NGSI-LD Endpoint's distributions and the data model that Endpoint's `schema/index.json` names (`od-standards.py`, from `od-datasets.json`), or the dataset is withdrawn. A DataStore table of its rows, the dataset page's preview and SQL, stays when it holds 50 MB or less. Every listed dataset the publish gate does not hide holds a table: a dataset whose source files hold none (ZIP, a map service) gets the rows its Endpoint serves anonymously as `file.csv`, filtered to the dataset as its CSV distribution is, in a table named by the entity type, so it carries no attribute the Endpoint's Policy hides and the theme draws the dataset's map from it when the rows are located (T-4742). Each table has CKAN's table view, written again when it is missing. A read the edge refuses for load (429) or an outage fails the run and leaves the live table as it was; a file the Endpoint refuses for good (too large) leaves the dataset without one and says so in the run's log. A run in which no dataset is converted at all withdraws nothing, since that is a missing gateway or mapping rather than an empty catalogue. The harvest withdraws it with `package_delete` on the next run, and its row in the mapping (`scripts/open-data/bb-bbsk-ngsi-ld-mapping.yaml`) carries `status: removed` with the reason. The source stays public and is imported again by mapping it. The publish gate's hidden list in the catalogue values is generated from the gate's evidence by `scripts/ckan-hidden-list.py` in the deployment repository, never typed (EP-145): a package the gate hides comes back only through a `passedBack` entry with its reason. Decided (worker-3, owner may override): withdraw rather than purge, because the harvest finds a withdrawn dataset by its fixed id and revives it the night its rows are mapped, and a purge would only lose that link.

## 10. The catalogue as an NGSI-LD Endpoint

An agent asks the catalogue first and the dataset second (T-4500, ADR-N-025). The catalogue it asks is one more public Endpoint: the Endpoint named `catalog` on the space named `catalog`, read with the normal NGSI-LD tools (`type=Dataset`, `q=searchText~="bystrica"`, `georel=near`). Nothing in it is authored: the Portal reconciler writes it from CKAN and from the feed of §8, which is built by the same function as each Endpoint's own record (EP-27).

The catalogue mirrors the open-data catalogue a person browses (owner, 2026-10-19, T-4746): one `Dataset` per public CKAN dataset, with the same name, one `Organization` per CKAN organization that publishes one, and one `DataService` per public Endpoint, all Smart Data Models DCAT-AP and organization subject types. It replaces the dataset per context space of 2026-10-17, so a count, a title or a citation from the catalogue is the one CKAN shows. "List all organizations" is one query (`type=Organization`), and "the datasets of hel-fi" is one more (`type=Dataset&q=refPublisher=="urn:ngsi-ld:Organization:hel-fi"`).

The set is read, never listed in code: the Portal reads the CKAN instance's `package_search` and `organization_list` anonymously on each run, so it holds only public datasets, and the gateway's feed of §8 for the Endpoints. A CKAN dataset names its Endpoint through its resources (`/api/endpoint/{slug}/…`, the same slug for every resource of a dataset), and a harvested one also names the rows that are its own, the `type` and `q` of its NGSI-LD resource URL (§3). A CKAN dataset whose Endpoint has no `DataService` here (not public, or `harvest: false`, EP-139) is left out, so no Relationship points at nothing. A dataset added, renamed or withdrawn in CKAN appears, moves or disappears at the next run, and an organization whose last dataset went leaves no entity.

| Entity | Id | Attribute | Type | Source |
|---|---|---|---|---|
| `Organization` | `urn:ngsi-ld:Organization:{name}`, the CKAN organization's name | `name` | Property | the organization's `title` |
| | | `identifier` | Property | the organization's `name` |
| | | `url` | Property | `https://opendata.{domain}/organization/{name}` |
| | | `datasetCount` | Property | the `Dataset` entities of this catalogue that name it |
| | | `searchText` | Property | name and title, lowercased, diacritics folded |
| `Dataset` | `urn:ngsi-ld:Dataset:{name}`, the CKAN dataset's name | `name`, `description` | Property | CKAN `title` and `notes`, as CKAN shows them |
| | | `title` | LanguageProperty | `dct:title` per `@language` of the Endpoint's record, when the dataset is that Endpoint's own (its `identifier` extra is the slug) |
| | | `identifier` | Property | the CKAN name, the slug of the dataset page |
| | | `url` | Property | `https://opendata.{domain}/dataset/{name}` |
| | | `keyword` | Property, a list | CKAN tags |
| | | `theme`, `spatial` | Property, a list of IRIs | the `theme` and `spatial_uri` extras |
| | | `license` | Property | `license_url` |
| | | `issued`, `modified` | Property | the `issued` and `modified` extras, else `metadata_created` and `metadata_modified` |
| | | `source` | Property | the `source_url` extra of a harvested dataset |
| | | `location` | GeoProperty, a polygon | the `area` rule of its Endpoint's space (DM-87), when it declares one |
| | | `refPublisher` | Relationship | its `Organization` |
| | | `refDataService` | Relationship | the `DataService` of its Endpoint |
| | | `nextQuery` | Property | `{tool: query_entities, arguments: {endpoint, type, q, limit}}`: the call that reads its rows, `type` and `q` those of its NGSI-LD resource, absent when the dataset is the whole Endpoint |
| | | `searchText` | Property | name, description, tags, organization and the record's titles, lowercased, diacritics folded |
| `DataService` | `urn:ngsi-ld:DataService:{slug}` | `title`, `description` | LanguageProperty | `dct:title`, `dct:description` per `@language` |
| | | `accessLevel` | Property | the Endpoint's audience: `public`, `organization`, `project-list` |
| | | `visibleBecause` | Property | why this caller sees it: `public`, `organization`, `project`, `grant`; `public` in the public catalogue |
| | | `entityTypes` | Property | `[{type, count}]`, most first, read by the Portal as the anonymous caller from the Endpoint's `/types` and `count=true&limit=0`, once an hour (T-4526); absent while unread |
| | | `nextQuery` | Property | `{tool: query_entities, arguments: {endpoint, type, limit}}`: the second call, on the largest type (T-4526) |
| | | `identifier` | Property | `dct:identifier`, the slug a tool call names |
| | | `endpointURL` | Property | the `dcat:DataService`'s `dcat:endpointURL` |
| | | `accessURL` | Property, one object per distribution | `dcat:distribution`: `dcat:accessURL`, `dct:conformsTo`, `dcat:mediaType`; the access paths only, not the schema artifacts under `/schema/` |
| | | `accessRights`, `license` | Property | `dct:accessRights`, `dct:license` |
| | | `refDataset` | ListRelationship | every `Dataset` that names it, in name order; absent when none does |

Each organization also publishes its own slice (owner addendum, 2026-10-19): a project that declares a public Endpoint named `catalog` on its space `{project}-catalog` gets, written by the same run, its CKAN organization's `Organization`, that organization's `Dataset` entities and the `DataService` entities they name, the same entities as in the installation's catalogue. An agent that knows the publisher asks it with `type=Dataset` alone. That Endpoint is published to CKAN like any other (`{organization}-katalog`, "{title}: katalóg dát / data catalogue"), so the catalogue lists it too; it names itself in `refDataService` and is the one dataset not counted in `datasetCount`.

An Endpoint that no CKAN dataset names is a dataset of its own: `urn:ngsi-ld:Dataset:{slug}`, built from its record (`title`, `description`, `keyword`, `theme`, `spatial`, `location`, `temporal`, `frequency`, the record's `publisher {id, name}`, `refDataService`, `searchText`) with no `refPublisher`, so it never adds to an organization's count. That holds a non-public Endpoint, which no CKAN dataset can name and which a caller that reaches it finds on the MCP hub (below), and an installation without CKAN, whose catalogue is then one Dataset per Endpoint. Once a CKAN dataset names the Endpoint, its own Dataset goes.

Attributes the record does not carry are left out, never written empty. The ids never carry a title, so a renamed Endpoint changes its entities in place.

The reconciler reads the feed once per run and writes only the entities that changed, through the `catalog` Endpoint as the Portal's own client, in batches of 100; an entity it wrote whose CKAN dataset, organization or Endpoint is gone or no longer public is deleted in the same run. After a restart, and once an hour, it lists what the catalogue holds instead of trusting its memory, so an entity left by a run that stopped halfway is still removed. The `catalog` Endpoint's Policy grants reads to everyone and writes only to the Portal's ServiceAccount: every write to context data goes through an Endpoint and its Policy, this one included.

On the MCP hub and on every named server, `endpoint: catalog` is the caller's own catalogue (T-4503, ADR-N-025). The gateway builds the `DataService` entities and the Datasets of non-public Endpoints per request from the Endpoints the request reaches, by the same function (`jc_core::ngsi_catalog`) from the same records. The CKAN-shaped `Dataset` and `Organization` entities exist only where the Portal wrote them, so the gateway reads those two types from the public catalogue, at most once a minute, and keeps a `Dataset` only when the caller reaches its `refDataService`, and an `Organization` only when it keeps one of its Datasets, its `datasetCount` counted again from those. That is the one broker read of the hub. The anonymous caller's catalogue is the public one entity for entity; a signed-in caller's adds the organization and granted Endpoints it reads, each saying why in `visibleBecause`; a named server's holds only its members. The catalogue answers `query_entities` (`type`, `id`, `idPattern`, `q`, `georel`, `geometry`, `coordinates`, `attrs`, `pick`, `format`, `count`, `limit`, `cursor`), `get_entity` and `list_types`; every other tool belongs to the Endpoint a Dataset names in `refDataService`. An Endpoint outside the caller's reach gives no entity, no word of `searchText` and no count.

Not yet in the entities: the entity types an Endpoint holds with their counts, first and last `observedAt`, and the ready-to-run second call per type (`nextQuery`, T-4486). They need one broker read per Endpoint and land in a follow-up task.

## Related

- [../Decisions/adr-n-053-declarative-visualizations.md](../Decisions/adr-n-053-declarative-visualizations.md) — the charts a dataset shows and why they cannot run code.
- [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) — the publication contract, the manifest fields and what one Endpoint becomes.
- [../Requirements/endpoints.md](../Requirements/endpoints.md) — EP-62 to EP-69 and EP-118, the normative rules this chapter designs around.
- [../Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md) — the `ckan` add-on, what it deploys and what it costs to run.
- [../Deployment/12-branding-and-naming.md](../Deployment/12-branding-and-naming.md) — the branding block the catalogue mounts.
- [09-portal.md](09-portal.md) — the Portal, which holds the reconciler the publication belongs to and the catalogue page of §6.
- [../API/01-portal-api.md](../API/01-portal-api.md#16a-the-catalogue-ep-81-ep-82) — the catalogue and publication routes of §6 and §7.
