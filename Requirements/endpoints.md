---
sidebar_position: 4
title: "Endpoints & Representation Parity"
description: Universal ingress and egress multi-representation views, opaque slugs, and protocol parity.
---

# Endpoints & Representation Parity

Family **EP** (EP-01…EP-88). Owning chapter: [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md). Verified by: [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md).

## 1. Endpoint Identity and Opaque Slug

- **EP-01** [P][A] — Every Endpoint MUST be exposed under a unique base URL path formatted as `https://{host}/api/endpoint/{endpointSlug}/` with no intervening path segments.
- **EP-02** — The `endpointSlug` MUST be a cryptographically random string generated with at least 128 bits of entropy, encoded using lowercase RFC 4648 Base32 without padding (`^[a-z2-7]{26,}$`).
- **EP-03** — The `endpointSlug` MUST NOT reveal or encode the internal Context Space name, owning Project, Organization, or data schema.
- **EP-75** [H][S] — The `endpointSlug` MUST be minted by the platform when an Endpoint is proposed; a person gives an Endpoint one name (`metadata.name`) and never types the slug, because a typed slug is how a space name reaches a public URL (EP-03). An import MUST mint it too, and MUST NOT take the slug the bundle carries (CC-74): otherwise the destination answers at the source's capability URL, and two imports of one bundle answer at one address. The exception is the slug this instance already minted for the same Endpoint (same project and `metadata.name`), which an import MUST keep, so updating a project by re-importing its bundle does not move its endpoints under the people using them; a renamed Endpoint is a different Endpoint and is minted a slug of its own.
- **EP-76** [S][H] — A `Change` that gives an Endpoint `spec.audience: public`, on creation or by an update from another audience, MUST take the red lane and MUST be approved by a binding whose `approve` on `Endpoint` satisfies the constraint `spec.audience in [public]` (the `publisher` of PF-71 or `org-admin`); the Approvals page and the assistant MUST name `publisher` as the missing role when another approver tries (PF-72, CC-19).
- **EP-04** — Endpoint configuration state MUST be stored declaratively as a `kind: Endpoint` manifest in the owning Context Space directory.

## 2. Fixed Child Set and Representation Parity

- **EP-05** [P][A] — Every Endpoint MUST expose exclusively the standardized child paths: `ngsi-ld/v1/`, `mcp`, `file.{ext}`, `ogc/features/`, `sta/v1.1/`, `schema/`, and `.well-known/oauth-protected-resource`.
- **EP-06** — Every representation served under an Endpoint MUST be evaluated against the exact same Policy decision produced by the Policy Enforcement Point (PEP).
- **EP-07** — Attribute projection (R9), scope filtering (R13), geo filtering (GW11), and temporal clamping (GW11) MUST apply identically across all enabled representation child paths.

## 3. Representation Translation Mappings

- **EP-08** [P] — Tabular representations (`file.csv`, `file.xlsx`) MUST flatten NGSI-LD entity properties using dot-notation keys and serialize relationships as URN strings.
- **EP-09** [P] — GeoJSON representations (`file.geojson`) MUST map entities containing a valid `GeoProperty` to standard GeoJSON `Feature` objects.
- **EP-10** [P] — If an entity query directed to spatial representations targets types that lack a spatial `GeoProperty`, the gateway MUST reject the request with HTTP 400 Bad Request.
- **EP-11** [P] — OGC Features representations MUST expose each distinct NGSI-LD entity type within the space as an OGC Feature Collection.
- **EP-12** [P] — SensorThings representations (`sta/v1.1/`) MUST map Smart Data Models observation entities directly to STA entity sets.
- **EP-13** [P] — Inexpressible STA entities MUST return HTTP 404 Not Found, while non-temporal write operations MUST be rejected with HTTP 405 Method Not Allowed.

## 4. Audience and Authorization Scoping

- **EP-14** — An Endpoint manifest MUST explicitly declare an `audience` setting of `project-list`, `organization`, or `public`.
- **EP-15** — Cross-project access to an Endpoint MUST require the consumer Project to declare a `kind: SharedSpaceReference` manifest referencing the source Endpoint slug.
- **EP-16** — Requests reaching an Endpoint configured with `audience: public` MUST be authenticated under the synthetic `public` role identity and evaluated against public data policies (GW22).

## 5. Rate Limiting, Caching, and In-Memory Resolution

- **EP-17** — The Context Gateway MUST maintain an in-memory resolution table mapping `endpointSlug` to Context Space name, enabled representations, audience rules, and rate limits.
- **EP-18** — Slug resolution in memory MUST use concurrent read-optimized primitives ensuring resolution latency under 100 microseconds.
- **EP-19** — Endpoint updates deployed by the reconciler MUST invalidate the in-memory gateway resolution cache within 2 seconds (R48).
- **EP-20** — An Endpoint is not rate limited unless its manifest sets `spec.rateLimits`: a limit is an explicit choice of the person who configures the Endpoint, never a platform default (owner decision 2026-09-24). When `spec.rateLimits` is set, the gateway MUST count every request in a token bucket per authenticated identity or, without one, per consumer IP, and MUST advertise the thresholds via the standard `RateLimit-*` headers (MIM0-R7); without it the gateway MUST NOT count the Endpoint and its answers MUST NOT carry `RateLimit-*` fields. No Portal door (the form, the assistant, the KPI and share drafts, the seed) MAY write a limit the person did not ask for. The edge's anti-flood buckets (Deployment/10 §4) protect the node and are not an Endpoint limit.

## 6. Tenancy Stripping and Internal Hop

- **EP-21** — Incoming client requests to Endpoint paths MUST NOT include the `NGSILD-Tenant` header, and any client-supplied tenant header MUST be stripped at the gateway PEP (SP-07, GW20).
- **EP-22** — The Context Gateway MUST resolve the target Context Space from the in-memory slug mapping and inject `NGSILD-Tenant: {space}` exclusively on the internal hop (SP-07).
- **EP-23** — If an endpoint slug is invalid or deactivated, the gateway MUST return HTTP 404 Not Found without disclosing whether the underlying space exists (R20, SP-06).

## 7. Endpoint-Level MCP Façade

- **EP-24** [A] — Each Endpoint MUST serve an isolated MCP instance at `/api/endpoint/{endpointSlug}/mcp` conforming to SP-14 through SP-20.
- **EP-25** [A] — The tool list advertised by the Endpoint MCP instance MUST be dynamically rendered from the active Policy grants attached to the Endpoint and caller token (SP-15).
- **EP-26** [A] — Tool calls executed through the Endpoint MCP instance MUST forward the caller's verified OAuth 2.1 bearer token through the gateway PEP without ambient privileges.
- **EP-87** [A] — The gateway MUST serve a hub at `/api/mcp` ([ADR-N-025](../Decisions/adr-n-025-one-mcp-connector-several-endpoints.md)) whose `list_endpoints` answers only the Endpoints the token may read through it, and whose every data tool takes one required `endpoint` from that list and runs as a call to that Endpoint's own MCP (EP-24, EP-25): that Endpoint's PDP with the caller's token, its projection, its rate limit and its elicitation. A hub call MUST also spend one request of a per-subject bucket shared by every Endpoint, so a burst cannot be spread across Endpoints. `endpoint` is one string, never a list, and no tool, filter, join or subscription of the hub reads more than one Endpoint in a call. The per-Endpoint URL stays.
- **EP-88** [S] — A hub token MUST reach only the Endpoints its `endpoint:{slug}` scopes name, chosen by the person at connect time, or the one Endpoint its audience names (PF-45, PF-46); a token with no `endpoint:` scope reaches none. An `endpoint` outside that set MUST be refused with the same bytes as an unknown slug (SP-20). The allow-list narrows and never grants: each call is still decided by the Endpoint's own Policy.

## 8. Discovery and Performance Budgets

- **EP-27** [H][P][A] — `GET https://{host}/api/endpoint/{endpointSlug}/` MUST return a content-negotiated DCAT-AP v3.0 Dataset record describing available distributions (SP-10).
- **EP-28** — Under sustained loads up to 5,000 requests/second per replica, the gateway's overhead MUST NOT exceed a p99 latency of 5.0 milliseconds.

## 9. OGC API Features Representation

- **EP-29** [P] — OGC API Features MUST be served at `/api/endpoint/{endpointSlug}/ogc/features/` conforming to the standard Part 1 Core resource hierarchy.
  > Note: See architectural mapping in [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine).
- **EP-30** [P] — Conformance classes claimed MUST be exactly Part 1 Core, OpenAPI 3.0, GeoJSON, Part 2 CRS and basic CQL2 filtering on the OGC representation, and the NGSI-LD temporal API (query and retrieve the temporal evolution of entities, clamped by GW26) on the `ngsi-ld` representation, so reading is proven for current values and history alike.
- **EP-31** [P] — Each collection identifier MUST equal the NGSI-LD entity type short name, exposing only types that declare at least one `GeoProperty` (DM-05).
- **EP-32** [P] — Each collection MUST advertise spatial and temporal extents, coordinate reference systems, and multilingual descriptions in the requested locale.
- **EP-33** [P] — Feature identifiers MUST equal the entity URN, returning HTTP 404 for nonexistent or forbidden resources (R20).
- **EP-34** [P] — OGC query parameters (`bbox`, `datetime`, `limit`, `filter`) MUST map directly to NGSI-LD query AST constraints and intersect with caller grants (GW10–GW11).
- **EP-35** [P] — The supported CQL2 subset MUST cover basic comparison, logical, temporal, and spatial operators, rejecting unsupported constructs with HTTP 400.
- **EP-36** [P] — Feature pagination MUST use `limit` and an opaque `next` link encoding the NGSI-LD offset, reporting total matches via post-filtered counts (R47).
- **EP-37** [P] — Feature properties MUST contain flattened, policy-projected NGSI-LD attributes with unit codes, observation timestamps, and primary geometries separated (R9).
- **EP-38** [P] — Every feature MUST carry alternate links pointing to its canonical NGSI-LD entity and describedby links pointing to versioned schemas.
- **EP-39** — Write operations through the OGC Features representation MUST NOT exist, returning HTTP 405 Method Not Allowed on all non-safe methods.
- **EP-40** [P] — The endpoint's OpenAPI 3.0 document MUST be generated dynamically per endpoint and validate against the official OGC conformance test suite (TS-07).

## 10. File Downloads

- **EP-41** [P][H] — The `file.zip` endpoint MUST stream a multi-format bundle containing normalized data, tabular sheets, GeoJSON, schemas, and a DCAT-AP dataset record.
  > Note: See streaming export architecture in [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine).
- **EP-42** [P] — File representations MUST accept standard NGSI-LD entity query parameters and apply them under identical policy intersection rules (EP-06).
- **EP-43** [P] — File download responses MUST send attachment content-disposition headers, standard MIME types, strong ETags, and support cache validation.
- **EP-44** [P] — File generation MUST page through the context broker, streaming rows while enforcing per-endpoint row and byte size limits.
- **EP-45** [P] — Tabular export headers MUST format flattened property keys, appending unit symbols when human-readable headers are requested.

## 11. Schema Surface

- **EP-46** [P][A] — Every Endpoint MUST serve versioned schema artifacts including LinkML, JSON Schema, JSON-LD context, SHACL, OWL, RDF, and Markdown documentation under `schema/v{major}/`.
- **EP-47** [P] — Schema artifacts MUST represent the granted projection of the model, omitting classes and slots that the endpoint's policy set forbids the caller to read.
- **EP-48** [P] — The JSON Schema and the JSON-LD `@context` MUST be pre-rendered by Model Tools at publish time and stored in the artifact store (PF-29); the endpoint MUST serve them as the granted projection of those artifacts. SHACL, OWL, RDF, the LinkML source and the Markdown MUST be rendered by the gateway from that same projection, because a pre-rendered artifact cannot be narrowed to a caller. Every schema response MUST carry a strong ETag and revalidate: the document is a projection of the policy set, so a grant that changes changes the document.
- **EP-49** [P] — The unversioned `schema/v{n}/model` endpoint MUST support content negotiation across YAML, JSON Schema, JSON-LD, and Turtle formats.
- **EP-50** [P][H] — Data responses across all representations MUST include HTTP `Link` headers pointing to versioned JSON Schema and SHACL shape definitions.
- **EP-51** [P] — The `file.zip` export bundle MUST include the complete schema directory for every included entity type.
- **EP-52** [A] — The endpoint MCP server MUST expose schema artifacts as `describe_schema` tool outputs and as direct MCP resources (`schema://{slug}/v{n}/{artifact}`).

## 12. Published Mappings and View Endpoints

- **EP-53** [P][A] — An Endpoint MUST publish all approved LinkML-Map specifications, compiled Bloblang, and gateway IR files under `schema/v{n}/mappings/`.
- **EP-54** [P] — An Endpoint MAY configure a view mapping, transforming served entities into the target model and serving the target schema projection while disabling write operations.

## 13. Access surface (`access`)

- **EP-55** [A][S] — Every Endpoint and every space MUST answer `GET …/access` with the caller's effective grant document: the space's Policy set partially evaluated with subject, endpoint and time known and the resource unknown, produced by the same in-process PDP that enforces requests (EP-06).
- **EP-56** [A] — The default representation (`application/json`) MUST follow the AuthZEN resource-search shape (R51): `subject`, the `resource` the document is about, `permissions[]` and `prohibitions[]`. Each entry MUST name the entity type it reaches (`resource.type`, with `idPatterns`/`id` when the grant is narrowed to them), its allowed CIM 009 operations (`actions`), its attributes (`attributes`, `"*"` when the grant reaches every attribute of the type) and its residual `q`, `scopeQ`, `geoQ`, `temporalQ` as NGSI-LD query strings (`constraints`, empty when none applies). The document MUST carry the Endpoint's own `limits` when it has any, so a caller learns its rate before it hits it.
- **EP-57** [A] — `Accept: application/odrl+json` (and `text/turtle`) MUST return the same grants as an ODRL 2.2 policy in the `ngsi-ld:` profile (R52, ADR 003) with `permission[]`, `prohibition[]`, `assigner`, `assignee`, `target` refinements for attributes and `constraint[]` for scope, geo and time. The profile is `https://joinedcontext.com/odrl/ngsi-ld/v1/context.jsonld` in `@context` and `https://joinedcontext.com/odrl/ngsi-ld/v1#` as the namespace of its terms. `assignee` and `assigner` belong to the policy, where one caller and one author cover every rule; a rule carries its own `assigner` only when the rules disagree about who granted them. Every permission carries the duties of the Endpoint's licence (EP-79).
- **EP-58** [A] — `Accept: application/vnd.joinedcontext.grant-ast+json` MUST return the residual as a UCAST condition tree (`and`, `or`, `not`, `eq`, `in`, `gte`, `lte`, `geo_within`, `scope_under`, `time_between`) plus the attribute projection per type, so a client can compile it into its own filter.
- **EP-59** [S] — The grant document MUST omit every type, attribute and policy that does not apply to the caller (no existence disclosure, R20), MUST be cached per (subject, endpoint, policy digest) and MUST be invalidated together with the PDP cache (R40, R48).
- **EP-60** [A] — The endpoint MCP MUST expose the same document as `describe_access(format)` and as resource `access://{endpointSlug}`; App publication (AP-06) and the Portal "Data access" view MUST be computed from it rather than from a second implementation.

## 14. Endpoint-level publication narrowing

- **EP-61** [P][S] — An Endpoint MAY declare `spec.projection.hiddenAttributes`; the gateway MUST intersect that list with the caller's policy projection before any representation is encoded, so an Endpoint can only narrow and never widen what the Policy grants (EP-06, EP-07, R9); a write through the Endpoint that touches a hidden attribute MUST be refused whole like one outside the grant (GW17), so what an Endpoint does not show cannot be changed through it. A `hiddenAttributes` entry naming a member the gateway serves whatever the grants say — the identity members `id`, `type`, `@context`, `@id`, `@type` and `scope`, and the broker-set `createdAt`, `modifiedAt`, `deletedAt` and `expiresAt` (EP-71) — MUST be refused when the manifest is validated, with a reason naming the member: an entry that is accepted and then serves the member anyway is a narrowing the steward believes in and the gateway does not apply.

## 15. Publication to an open-data portal

- **EP-62** [H] — An Endpoint MAY declare `spec.publish.ckan` with the target instance reference, the CKAN organization slug, an optional dataset name and an optional CKAN licence id; the reconciler MUST create or update exactly one CKAN dataset per declaring Endpoint and MUST remove it through the explicit-deletion path when the block is withdrawn (CC-19).
- **EP-63** [H] — The dataset's metadata MUST be taken from the DCAT-AP record the Endpoint already serves (EP-27), so the catalogue entry and the endpoint's own description cannot disagree.
  > Note: The licence is the one exception. A record whose Endpoint declares no `spec.catalog.license` names none, so `spec.publish.ckan.license` states the licence the organization chose, and a `dct:license` in the record, when it carries one, wins (EP-78). Title and description are taken in the language of the Endpoint's space (`ContextSpace.spec.defaultLocale`), so a Slovak body's dataset is not published under its English title (T-2465).
- **EP-64** [H] — The reconciler MUST register one CKAN resource per enabled representation, each pointing at that representation's own URL under the Endpoint, and MUST remove a resource whose representation is no longer enabled (EP-05).
- **EP-65** [H] — An Endpoint MAY declare `spec.publish.ckan.datastore` to mirror rows into the CKAN DataStore; the mirror MUST be filled through the Endpoint's own tabular representation and refreshed by the Endpoint's subscription rather than by a full reload (EP-44).
- **EP-66** [S] — The publisher MUST read data and metadata exclusively through the Endpoint, authenticated as a ServiceAccount whose grants are the Endpoint's own, so a catalogue entry can never carry a class, attribute or row the Endpoint's policy set forbids (EP-06, PF-34).
- **EP-67** [S] — The CKAN API token MUST be resolved from a `secretRef` at reconcile time and MUST NOT appear in Git, in a manifest, in the published dataset or in any log line (CC-06).

## 16. What the Endpoint's own DCAT-AP record carries

- **EP-68** [P][A] — The DCAT-AP record of EP-27 MUST list every schema artifact the Endpoint serves as a `dcat:distribution` with its `dcat:accessURL`, `dcat:mediaType` and `spdx:checksum` (sha256 of the projected document), and MUST name the formalism of each in `dcterms:conformsTo`, so a catalogue harvesting the record finds the model in every formalism without reading the schema surface first (EP-46, EP-63).
- **EP-69** [P][S] — The record MUST carry `dcterms:accessRights` of `PUBLIC` for an Endpoint whose audience is `public` and `RESTRICTED` otherwise, and a restricted Endpoint's record MUST carry the `odrl:hasPolicy` pointer to its own `access` document (EP-55, DS-08); the record itself MUST be the granted projection, so a distribution the caller may not read is absent rather than listed and refused (EP-06, R20).
- **EP-78** [H][P][A] — An Endpoint MAY declare `spec.catalog`, and the record of EP-27 MUST then carry what it declares in DCAT-AP 3.0 terms: `dct:publisher` as a `foaf:Agent` with `foaf:name`, `dcat:contactPoint` as a `vcard:Kind` with `vcard:fn` and `vcard:hasEmail`, `dct:license` from the EU licence table on the dataset and on every distribution, `dcat:theme` from the EU data-theme table, `dcat:keyword` per language, `dct:spatial` (a NUTS code from the EU NUTS table, or a location IRI), `dct:temporal` as a `dct:PeriodOfTime`, `dct:accrualPeriodicity` from the EU frequency table, `dct:source` and `prov:wasGeneratedBy` for provenance, and `dcatap:applicableLegislation` where a law applies; the record MUST describe the Endpoint itself as a `dcat:DataService` with `dcat:endpointURL`, named by every representation distribution in `dcat:accessService`; both serializations MUST pass the SEMIC DCAT-AP 3.0 SHACL shapes pinned in the platform repository, in the fast CI lane (EP-63, DS-01).
- **EP-79** [A] — The licence of EP-78 MUST become ODRL duties on the policy of EP-57 and on the `odrl:Offer` the record carries in `odrl:hasPolicy`: `odrl:attribute` for CC BY and ODC-By, `odrl:attribute` and the share-alike duty for CC BY-SA and ODbL, and no duty for CC0 and PDDL. The offer permits `odrl:use` of the dataset; a non-public Endpoint's offer MUST constrain `odrl:recipient` to the organization and name its audience class, and MUST NOT name a project, a group or a person (EP-69, DS-03, DS-08).
- **EP-80** [S] — `spec.catalog.contactPoint` MUST be a role address (an open-data desk, a service mailbox), never a person: the Portal MUST refuse an address that is a member's own e-mail, naming the field, and MUST prefill publisher and contact from the organization's settings; the record MUST carry nothing of the catalogue block that the caller's grants would not already show (EP-69, R20).

## 16a. The platform's catalogue and one-step publication

- **EP-81** [H][S] — The Portal MUST offer one catalogue of every public dataset of the installation at `/catalogue`, readable without signing in and linked from the sidebar: full-text search, and facets for publisher (the CKAN organization, one per project), theme, format, licence, spatial and temporal coverage. It MUST be read from the catalogues the installation's `CkanInstance`s name (`package_search`), as an anonymous caller that holds no API token, so the Portal view and `data.{host}` cannot disagree and a private dataset can never be listed (EP-67, EP-69).
- **EP-82** [H][S] — Each dataset of EP-81 MUST have a page showing its description, keywords, publisher, licence, update frequency and themes, the data model's classes with a link to the model's documentation, every resource of the dataset (EP-64) with the DataStore preview where it has one, a sample of up to ten rows read anonymously through the Endpoint itself (EP-66), and "Use this data" snippets (curl, the App SDK, an MCP client) against the Endpoint's own URLs; the Portal MUST read a sample only from an Endpoint of this installation, derived from the dataset's `endpoint` extra and never fetched from a URL the catalogue supplies.
- **EP-83** [H][S] — A steward MUST be able to publish an Endpoint in one flow — pick the Endpoint, review a DCAT-AP description prefilled from the Endpoint and its space's data model, preview the catalogue entry, propose — and the flow MUST end in one `Change` that writes `spec.publish.ckan` and `spec.catalog` on that Endpoint; a flow that also makes the Endpoint public MUST say so before the proposal and MUST take the red lane with a publisher's approval (EP-76, PF-72). Nothing is written to CKAN by the flow itself: the dataset appears on the reconcile after the approval (EP-62).
- **EP-84** [H][P][A] — The installation MUST serve its catalogue for harvesters as one DCAT-AP 3.0 `dcat:Catalog` at `https://{host}/catalog.jsonld` and `https://{host}/catalog.ttl`, holding the record of EP-27 of every Endpoint whose audience is `public` and nothing of any other; both serializations MUST pass the SEMIC DCAT-AP 3.0 SHACL shapes pinned in the platform repository, in the fast CI lane (EP-78).

## 16b. The filter preview and its side-by-side proof

- **EP-85** [H][S] — The gateway MUST answer `POST /api/endpoint/{slug}/preview` (API/02 §7c) with what the Endpoint would serve if its filter were the draft in the body: a draft `ModelProjection` (classes, slots, `filter`) and a draft `hiddenAttributes` list take the place of the saved ones, and everything else (the Endpoint's own Policies, audience, view mapping) stays as saved, so the answer MUST equal the answer of a normal read once the draft is saved and MUST NOT include anything the Endpoint's Policies do not grant. The route MUST be refused like an unknown space (`404`) to a caller the space's canonical surface does not admit (SP-06, SP-11), because replacing a saved projection can show a steward what the Endpoint does not publish yet; a public Endpoint's preview MUST be evaluated as the anonymous caller and any other as the caller. It is outside the CIM 009 tree, so the NGSI-LD read surface stays conformant.
- **EP-86** [H] — The Portal's Endpoint page and form MUST hold the Endpoint's whole filter in one editor (entity types from the space's model, the row filter `q` as attribute/operator/value rows with enums as lists and a text mode, `geoQ` typed, hidden attributes per type) and MUST show beside it the proof: left, **Served by this endpoint**, the EP-85 preview of the draft; right, **Original in the space**, the same page of entities read from `/cs/{space}` with the person's own rights; rows aligned by entity id, a row the filter drops shown only on the right and marked "not served", a hidden attribute struck through on the right, and one summary line ("Serving 42 of 110 Events · 3 attributes hidden"). The left side MUST refresh within about a second of an edit (debounced), from pages of 50; a person who cannot read the space sees only the left side. On a narrow screen the two sides become tabs.

## 17. The hub endpoint

- **EP-70** [S] — An Endpoint on a Context Space that holds `ContextSourceRegistration`s MUST answer every read the specification defines — query, retrieve by id, `types`, `attributes` and temporal — over the union of the matching sources, by the broker's distributed operations (CIM 009 clause 4.3.6) and with no separate code path in the gateway; the same Endpoint's MCP surface MUST answer over the same union. A source that fails or times out MUST NOT fail the request: the answer MUST be `207` with `NGSILD-Warning` naming what did not answer and the body carrying what did, both passed through to the caller unchanged. A read carrying `NGSILD-EntityMap` (CIM 009 clause 5.14) MUST reach the broker unstripped, and the map URI the broker returns MUST be passed back to the caller, so pages are stabilised against the broker's own candidate map; the gateway MUST NOT keep an entity-id set of its own.
- **EP-71** [P][S] — A federated result MUST let its consumer tell which source it came from: the broker's registration details MUST be passed through when the caller asks for system attributes, and an MCP tool result over a space that federates MUST carry `jc:source`, the registrations that result is a union over. The names MUST be the registrations' `metadata.name` and MUST NOT be a source's URL or address (EP-70). A result over a space with no registration carries no `jc:source`, because there is no source to name; `jc:source` describes the answer and not one entity, since the broker merges without marking each entity with the part it came from (CIM 009 clause 4.3.6).

## 18. The assistant proposes an Endpoint

- **EP-72** [A][H][S] — The assistant's `propose_endpoint` tool (Architecture/07 §2, API/01 §19) MUST take `contextSpace`, `name`, `audience` (`public`, `organization` or `project-list`), `allowedProjects`, `representations`, `hiddenAttributes`, `entityTypes` and optional `rateLimits`, and MUST answer with a rendered `kind: Endpoint` manifest (a fresh 26-character base32 slug minted by the Portal, never by the model or the person, EP-02; `spec.projection.hiddenAttributes` for the masked attributes, EP-61) and the draft `kind: Policy` manifests granting `retrieveOps` on the named types (assignee `role: public` for a public audience, one `group` per listed project for `project-list`, the organization's group for `organization`), together with the change lane the Endpoint would take (`red` for `public`, CC-63). The proposal MUST NOT create anything: the Portal opens the Endpoint form with the manifest as untrusted prefill (`navigate`, UI-45) and the person's submission goes through the ordinary Change flow (CC-34); a proposal by a caller who may not `propose` an Endpoint is refused with `403` (PF-50). Audience defaults to `project-list`, never to `public`.

## 19. What an Endpoint reads and what it writes

- **EP-73** [H][S] — An Endpoint MUST define what may be read as a `ModelProjection` (MP-02: the classes and attributes of the space's model it exposes) and, separately, what may be written; the Portal's LinkML editor shows both as a read column and a write column per class and renders two Policies from them, a read grant over the projection and a write grant.
- **EP-74** [S] — The write set of an Endpoint MUST be narrowed by entity `id` or `idPattern`, by `type` or by `scopeQ` (the Policy's `information[].entities` and `scopeQ`, R6…R8, R24), and nothing outside that set is writable through the Endpoint.

## 20. A reference inside one organization

- **EP-77** [P] — A SharedSpaceReference inside one Organization repository MUST name its source as `endpointRef: {project, name}` and the loader MUST resolve it to the slug of this environment; `endpointSlug` remains for a source in another instance, and exactly one of the two MUST be present. Resolving a name MUST NOT widen access: the source Endpoint's audience and Policy decide as with a slug (EP-15).

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| EP-01…EP-04 | [Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model](../Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-05…EP-07 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-08…EP-13 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-14…EP-16 | [Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model](../Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| EP-17…EP-20 | [Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48](../Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48) | [Testing/01-backend-tests.md#6-what-the-requirements-ask-for-and-is-not-built-yet](../Testing/01-backend-tests.md#6-what-the-requirements-ask-for-and-is-not-built-yet) |
| EP-21…EP-23 | [Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09](../Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-24…EP-26 | [Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces](../Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces) | [Testing/02-conformance-tests.md#4-model-context-protocol](../Testing/02-conformance-tests.md#4-model-context-protocol) |
| EP-87…EP-88 | [Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces](../Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces) | [Testing/02-conformance-tests.md#4-model-context-protocol](../Testing/02-conformance-tests.md#4-model-context-protocol) |
| EP-27…EP-28 | [Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model](../Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model) | [Testing/05-deployment-and-performance-tests.md#5-the-k6-budgets](../Testing/05-deployment-and-performance-tests.md#5-the-k6-budgets) |
| EP-29…EP-40 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/02-conformance-tests.md#2-ogc-api---features-part-1](../Testing/02-conformance-tests.md#2-ogc-api---features-part-1) |
| EP-41…EP-45 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-46…EP-52 | [Architecture/04-context-spaces-and-endpoints.md#1a-schema-surface-of-an-endpoint-schema](../Architecture/04-context-spaces-and-endpoints.md#1a-schema-surface-of-an-endpoint-schema) | [Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld](../Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld) |
| EP-68…EP-69 | [Architecture/04-context-spaces-and-endpoints.md#3a-the-endpoints-own-dcat-ap-record](../Architecture/04-context-spaces-and-endpoints.md#3a-the-endpoints-own-dcat-ap-record) | [Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld](../Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld) |
| EP-78…EP-80 | [Architecture/04-context-spaces-and-endpoints.md#3a-the-endpoints-own-dcat-ap-record](../Architecture/04-context-spaces-and-endpoints.md#3a-the-endpoints-own-dcat-ap-record) | [Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld](../Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld) |
| EP-81…EP-84 | [Architecture/21-open-data-catalogue.md#6-the-portals-catalogue-page](../Architecture/21-open-data-catalogue.md#6-the-portals-catalogue-page) | [Testing/03-frontend-and-e2e-tests.md#1-component-tests-with-vitest](../Testing/03-frontend-and-e2e-tests.md#1-component-tests-with-vitest) |
| EP-85…EP-86 | [API/02-endpoint-representations.md#7c-filter-preview-preview](../API/02-endpoint-representations.md#7c-filter-preview-preview) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-70…EP-71 | [Architecture/04 §5a](../Architecture/04-context-spaces-and-endpoints.md#5a-federation-registrations-and-the-hub-endpoint) | [Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld](../Testing/02-conformance-tests.md#5-data-model-artifacts-and-json-ld) |
| EP-76 | [Architecture/12-identity-and-access.md#2a-roles-as-code](../Architecture/12-identity-and-access.md#2a-roles-as-code) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| EP-72 | [Architecture/04 §5](../Architecture/04-context-spaces-and-endpoints.md#5-cross-project-sharing-model) | [Testing/03-frontend-and-e2e-tests.md#1-component-tests-with-vitest](../Testing/03-frontend-and-e2e-tests.md#1-component-tests-with-vitest) |
| EP-53…EP-54 | [Architecture/11-data-models.md#7-mappings-with-linkml-map](../Architecture/11-data-models.md#7-mappings-with-linkml-map) | [Testing/02-conformance-tests.md#2-ogc-api---features-part-1](../Testing/02-conformance-tests.md#2-ogc-api---features-part-1) |
| EP-55…EP-60 | [Architecture/04-context-spaces-and-endpoints.md#1b-access-surface-of-an-endpoint-access](../Architecture/04-context-spaces-and-endpoints.md#1b-access-surface-of-an-endpoint-access) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| EP-61 | [Architecture/04-context-spaces-and-endpoints.md#4a-representation-parity-and-endpoint-configuration](../Architecture/04-context-spaces-and-endpoints.md#4a-representation-parity-and-endpoint-configuration) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| EP-62…EP-67 | [Architecture/04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal](../Architecture/04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) | [Testing/05-deployment-and-performance-tests.md#5-the-k6-budgets](../Testing/05-deployment-and-performance-tests.md#5-the-k6-budgets) |
| EP-73…EP-75 | [Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model](../Architecture/04-context-spaces-and-endpoints.md#3b-the-named-projection-of-a-model) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| EP-77 | [Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes](../Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |

## Related

- [Architecture/04-context-spaces-and-endpoints.md](../Architecture/04-context-spaces-and-endpoints.md) — Endpoint architecture and multi-representation translation engine.
- [model-projections.md](model-projections.md) — MP-01…MP-03: the named subset of a model an Endpoint reads.
- [API/02-endpoint-representations.md](../API/02-endpoint-representations.md) — HTTP wire protocol examples for each endpoint representation.
- [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) — OGC Features, SensorThings, and MCP conformance test suites.
- [User-Guide/05-endpoints-and-sharing.md](../User-Guide/05-endpoints-and-sharing.md) — user guide for creating and sharing endpoints.
