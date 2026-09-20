---
sidebar_position: 13
title: "Access Control (R, MIM)"
---

# Requirements: Granular Access Control for NGSI-LD in Federated Digital Twins

Status: Draft
Date: 2026-08-02
Scope: Access-control layer (APISIX PEP + PDP) in front of NGSI-LD Context Brokers, and its behaviour across federated digital twins (FDT).
Related: ADR 001 (URN), ADR 002 (Policy entity), ADR 003 (ODRL mapping), ADR 004 (Scopes), ADR 005 (ScopeDefinition), ADR 006 (privilege bleed), ADR 007 (@context discovery), ADR 009 (secured subscriptions), ADR 010 (LOD read-only), ADR 011 (MQTT).

Keywords MUST / SHOULD / MAY per RFC 2119.

## 1. Architecture and enforcement point

- **R1** — Access to NGSI-LD entities MUST be enforced by a gateway (APISIX acting as PEP) in front of the Context Broker; the broker itself MUST NOT be reachable except through the gateway.
- **R2** — Access-control information MUST NOT be stored inside the guarded NGSI-LD entities themselves. Policies live outside the data plane, as `Policy` entities per ADR 002.
- **R3** — Policy decisions MUST be produced by a PDP (e.g. OPA) evaluating the NGSI-LD-native `Policy` model (ADR 002: `assignee`, `assigner`, `operations`, `information`/`RegistrationInfo`, root-level `q`, `scopeQ`, `geoQ`, `temporalQ`).
- **R4** — The gateway MUST authenticate the caller (token / VC / did:web) and resolve the set of policies assigned to that identity before forwarding any request.
- **R5** — The system MUST fail closed: no matching policy, unreachable PDP, or unparseable request ⇒ deny.

## 2. Granularity

- **R6** — Policies MUST support granularity at the level of: entity type (incl. Entity Type Selection Language), entity `id`, `idPattern`, individual Properties (`propertyNames`) and Relationships (`relationshipNames`).
- **R7** — Policies MUST support contextual conditions: value conditions (`q`), hierarchical scope (`scopeQ` per ADR 004 taxonomy), geographic (`geoQ`) and temporal (`temporalQ`) constraints.
- **R8** — Permitted actions MUST be expressed using the ETSI GS CIM 009 distributed-operation names (`queryEntity`, `createEntity`, `updateEntity`, …, `federationOps`), never a proprietary verb set.
- **R9** — Attribute-level filtering MUST apply to responses as well as requests: attributes not granted by any applicable policy MUST be stripped from returned entities (projection), and the stripped response MUST remain valid NGSI-LD.

## 3. Query rewriting (AST)

- **R10** — The gateway MUST parse incoming NGSI-LD query parameters (`q`, `scopeQ`, `type`, `attrs`, `id`, `idPattern`, `geoQ`, `temporalQ`) into an abstract syntax tree (AST) per the NGSI-LD Query Language (GS CIM 009 clause 4.9) and Scope Query Language (clause 4.19).
- **R11** — The gateway MUST rewrite the AST by combining the user's query with the constraints of each applicable policy, so that the forwarded query can only return entities the caller is allowed to see.
- **R12** — When multiple independent policies apply, they MUST be combined per policy as `(policy-constraints AND …)` joined with OR across policies — never by naive parameter concatenation. Cross-product privilege bleed between `scopeQ` of one policy and `q` of another MUST be impossible (ADR 006).
- **R13** — To achieve R12, scope constraints MUST be folded into the `q` expression as anchored regex on the `scope` attribute (`scope~="^/geo/…(/.*)?$"`) and the merged query MUST be sent via `POST /ngsi-ld/v1/entityOperations/query` (clause 6.23), preserving pagination (`limit`/`offset`) and avoiding HTTP 414.
- **R14** — Rewriting MUST be transparent: the caller sends a plain NGSI-LD request (e.g. `GET /entities?type=Device`) with no security parameters; the gateway injects scope/query filters itself. The caller MAY add own filters; these are AND-ed with the injected ones.
- **R15** — The rewritten request and its response MUST remain fully NGSI-LD compliant — a standard NGSI-LD client works unmodified against the gateway.

## 4. Access discovery (know before you ask)

- **R16** — A caller MUST be able to discover, in advance, what they have access to: an endpoint returning their effective policies (the `Policy` entities assigned to them, or an aggregated "effective permissions" view: types, id patterns, attributes, scopes, operations).
- **R17** — A caller MUST be able to ask, before issuing a request, whether a specific operation on a specific entity/attribute set would be permitted (dry-run / `access-check` endpoint), without touching the Context Broker.
- **R18** — "List all entities I can access" MUST work as an ordinary NGSI-LD query (e.g. `GET /entities?type=…` or type-less query where supported): the gateway's injected filters make the result exactly the accessible set. No special client behaviour is required.
- **R19** — The scope taxonomy MUST be discoverable through `ScopeDefinition` entities (ADR 005) so UIs can render the permission tree (`isRoot`, `isChildOf`, `scopeString`).

## 5. Requesting extra data

- **R20** — When a caller requests data beyond their grants, the gateway MUST NOT error the whole request by default: query results are silently narrowed to the permitted subset (filter + projection). Explicit single-entity retrieval (`GET /entities/{id}`) of a forbidden entity MUST return 404 (not 403) to avoid existence disclosure.
- **R21** — A caller MUST have a way to request additional access (extra entities, attributes, scopes or operations): an access-request flow that records the request against the `assigner` (data owner) and, on approval, results in a new/updated `Policy` entity. The mechanism MAY be manual (ticket) in the first iteration, but the policy model MUST NOT need changes to accommodate it.
- **R22** — A caller SHOULD be able to distinguish "empty result" from "narrowed result" via an opt-in response header (e.g. `NGSILD-Results-Restricted: true`) that does not break NGSI-LD compliance. The signal describes the **answer**, not the request: it MUST be set whenever the decision constrained what comes back — a granted type set narrower than the one asked for, a grant that whitelists attributes or relationships, a policy filter conjoined with the caller's, a clipped area or a clamped window — and not only when the caller named something the decision then removed. A read that names no `attrs` is the ordinary read, and it is the one that most needs telling: its entities come back with attributes missing and no other way to know why. The signal says that something was constrained and never what (R20), and it stays opt-in on the request, so a caller who did not ask learns nothing (GW12, AG-13).

## 6. Federation between digital twins

- **R23** — The same policy model MUST govern FDT-to-FDT traffic: forwarded distributed operations pass the peer's gateway and are evaluated against policies whose `assignee` is the peer FDT identity (did:web).
- **R24** — Context Source Registrations MUST be admitted only when the `{Razidlo}` (minted-by) segment of the registered `idPattern` matches the registrant's verified identity (ADR 001 admission rule); `idPattern` MUST be anchored `^…$`.
- **R25** — Federated read-only participation MUST use `operations: ["federationOps"]` in the CSR; a foreign FDT MUST never write into another tenant.
- **R26** — Policies exchanged across data-space boundaries MUST be translated to/from W3C ODRL by the bidirectional mapper of ADR 003 with round-trip integrity (no information loss for `q`, `scopeQ`, `entities`, `propertyNames`, `relationshipNames`, operations).
- **R27** — Subscriptions/notifications crossing FDT boundaries MUST carry authorization material per ADR 009 (`notification.endpoint.receiverInfo`, `contextSourceInfo` for CSR), and the receiving gateway MUST validate it.
- **R28** — Loop protection (`Via` header, clause 4.3.6.3) and pagination MUST survive gateway rewriting in distributed operations.

## 7. Scope filtering

- **R29** — Every guarded entity MUST carry `scope` values from the standardized multidimensional taxonomy (`/geo/…`, `/domain/…`, `/admin/…`, ADR 004); writes with unknown/non-standard scopes MUST be rejected at the gateway, validated against existing `ScopeDefinition` entities (ADR 005).
- **R30** — Scope-based restriction MUST be hierarchical: a grant on `/geo/FI/HKI` covers all descendants (`/geo/FI/HKI/#` semantics), implemented via the anchored-regex folding of R13.
- **R31** — Write operations (create/update) MUST be scope-checked too: the payload's `scope` (and entity URN prefix per ADR 001) must fall inside the caller's granted scopes, otherwise the write is rejected.

## 8. Federation fan-out control (broker routing)

With ~100 context brokers/tenants federated via Context Source Registrations, a naive "list all entities" would be broadcast to every source. The routing index that prevents this is the CSR registry itself: each CSR carries entity `type` and an anchored URN-prefix `idPattern`, and the distribution broker matches every request against the registrations before forwarding.

- **R32** — Each FDT MUST expose exactly one logical entry point (federation/distribution broker behind the gateway). Clients MUST NOT enumerate or address individual context brokers/tenants; broker topology is invisible to consumers.
- **R33** — Every federated source MUST be registered with a CSR that declares its entity types and an anchored `idPattern` covering only its own URN prefix (`^urn:ngsi-ld:{Typ}:{Razidlo}:{Evidencia}:.*$`, ADR 001). The CSR registry thereby functions as the distributed routing index: the broker MUST forward a request only to sources whose CSR matches the request's `type`, `id`/`idPattern`, and attributes — never to all sources.
- **R34** — `GET /entities/{id}` MUST route to exactly one source via URN-prefix matching against CSR `idPattern`. This is why random UUIDs are banned outside the last URN segment (ADR 001): they destroy prefix routing and force full-federation broadcast.
- **R35** — Unconstrained queries (no `type`, no `id`/`idPattern`, no scope) MUST NOT fan out to all sources. The gateway MUST either reject them (400 with guidance) or bound them: the policy filters injected per R11–R14 (types, id patterns, scopes) MUST also be used to prune the CSR candidate set before forwarding, so a caller's "list all entities" touches only the few brokers that can hold entities they may access.
- **R36** — CSR granularity MUST stay coarse: one CSR per evidencia/dataset (prefix `Typ:Razidlo:Evidencia`, or just `Razidlo`), not per entity or per type×dataset combination. The broker evaluates registrations on every request, so the registry MUST remain small (order of sources, not entities); the broker SHOULD hold it in an in-memory prefix-indexed structure invalidated on CSR change.
- **R37** — Distributed requests MUST have a fan-out budget: a cap on concurrent forwarded requests, a per-source timeout, and circuit breaking for dead/slow sources. Partial results MUST be returned with the standard partial-success semantics (207/`NGSILD-Warning`) rather than failing the whole query.
- **R38** — Distributed pagination MUST NOT amplify: the broker MUST NOT re-broadcast the query for every page. The standard EntityMap mechanism (GS CIM 009 clauses 4.3.6.7, 4.5.25, 5.2.39, 5.5.9.3) MUST be used: the first (CSR-pruned, per R33/R35) query builds an EntityMap of entity-id → contributing registrations; subsequent pages and repeated retrievals are served from the map, contacting only sources that actually hold the entities, with filters re-checked per page and expiry honoured (`expiresAt`). EntityMap complements — never replaces — URN-prefix CSR routing: the map only exists after a first query that the prefix index must already have bounded.
- **R39** — If the federation grows beyond what one CSR registry can prune efficiently, federation MUST be layered hierarchically (broker-of-brokers, each level registering aggregate prefixes such as `{Razidlo}`) instead of flattening hundreds of CSRs into one level — keeping per-request candidate evaluation bounded.

## 9. Non-functional

- **R40** — Policy evaluation and AST rewriting MUST add bounded latency at the gateway (target: single-digit ms at the PDP, excluding broker time); policy sets per identity SHOULD be cached with invalidation on `Policy` entity change.
- **R41** — The performance cost of regex-folded scope filtering (loss of native `scopeQ` indexes, ADR 006 consequence) MUST be measured on realistic entity counts before production rollout; if unacceptable, a broker-side native `scopeQ` path may be reconsidered per policy-count thresholds.
- **R42** — All deny decisions and policy changes MUST be auditable (who, what, which policy matched/failed).
- **R43** — The gateway MUST NOT break NGSI-LD content negotiation and `@context` discovery (ADR 007): `Link` headers and `application/ld+json` pass through unchanged.

---

## 10. Part II, MIM-derived requirements (OASC Minimal Interoperability Mechanisms)

Derived from the published OASC MIM texts (oasc/accessing-data-mim-0 repo; oasc/oasc-mims gitbook for MIM1–MIM10). Part I (R1–R43) specifies the ETSI/ADR access-control layer; Part II specifies what the platform must offer per MIM. Where a MIM defines its own requirement IDs (MIM0, MIM7), they are cited. MIM8, MIM9 and MIM10 have no published specification upstream (work-item stage; their standalone repos are empty), so their requirements reflect only the stated objectives.

*Numbering note:* the Slovak procurement templates in
`../procurement/mims.md` carry a second, upstream-derived numbering
(`MIMn.Cn.Rn.n`). The two schemes are mapped capability-level in that
file's header; this document is canonical for the platform-facing
`MIMn-Rn` IDs.

**Consumer classes**, every capability MUST serve three classes, tagged per requirement:

- **[H] Human**, usable through a portal/UI with human-readable names, descriptions and documentation; no API knowledge required.
- **[P] Program**, usable by conventional software through standard, formally described APIs and machine-readable formats.
- **[A] AI agent**, usable by an autonomous agent with no prior configuration: semantics discoverable at runtime (JSON-LD `@context`, type/attribute discovery), permissions introspectable before acting (Part I R16–R17), machine-readable policies/contracts (ODRL/DPV), structured errors and rate-limit signalling for self-throttling, and read-only-by-default federation access (agent tenants consume via CSR with `federationOps`, ADR 001).

## 11. MIM0, Accessing Data

C1: machine-readable data retrievable through the web.

- **MIM0-R1** [P][A] — Systems SHALL allow retrieval of data in at least one machine-readable format (CSV, JSON, XML, Parquet, Protobuf, …); formats CAN be specified through HTTP content negotiation. (MIM0 R1.1)
- **MIM0-R2** [H][P][A] — Data SHALL be retrievable via at least one standard web-based mechanism — download, REST API, subscription, stream or real-time feed as fits the use case; humans reach the same data through portal/open-data views. (R1.2)
- **MIM0-R3** [P][A] — Every access mechanism SHALL be formally described (OpenAPI for REST endpoints; the NGSI-LD specification for the broker API), and the description SHALL be fetchable at runtime so an agent can self-configure. (R1.3)
- **MIM0-R4** [P][A] — Data models used by payloads SHOULD be specified per MIM2. (R1.4)

C2: access is structured and queryable.

- **MIM0-R5** [P][A] — Systems SHALL provide data through a structured and consistent interface. (R2.1)
- **MIM0-R6** [H][P][A] — Systems SHALL support basic querying and/or filtering (e.g. by time, location, attributes). (R2.2)
- **MIM0-R7** [P][A] — APIs SHOULD, per the MIM0 best-practice list: support retrieval of current data; support retrieval of historical data when applicable; support geospatial querying when applicable (MIM7); support subscription to changes when applicable; expose the next expected update timestamp; version endpoints explicitly; provide example payloads and test queries ([H] documentation, [A] few-shot grounding); support standard HTTP caching headers; communicate rate-limit status via standard HTTP headers; return structured error bodies; and MAY support partial responses/projections and a standard health/status endpoint.
- **MIM0-R8** [A] — Structured errors and rate-limit headers (MIM0-R7) are mandatory ([P]→SHALL) on the gateway of this platform: an agent MUST be able to distinguish "denied" from "does not exist" (Part I R20) and to self-throttle without human intervention.

C3: changes can be subscribed to.

- **MIM0-R9** [P][A] — Where use cases require notifications, systems SHALL provide at least one mechanism to receive updates on data changes (NGSI-LD subscriptions internally; MQTT per ADR 011 or webhooks publicly; polling as fallback). (R3.1)
- **MIM0-R10** [P] — Systems MAY support multiple subscription mechanisms per use case (webhook, message queue, MQTT, polling). (R3.2)

C4: access can be restricted.

- **MIM0-R11** [H][P][A] — Access restrictions SHALL follow MIM3 (actor identification) and MIM6 (authorization, actor roles, data-asset-level policies) and are implemented by Part I R1–R43; the effective-permissions and dry-run endpoints (R16–R17) are the agent-facing surface — an agent can know what it may access before asking.

## 12. MIM1, Context Information Management

- **MIM1-R1** [P][A] — All context information SHALL be accessible through the ETSI NGSI-LD API as the single uniform interface, regardless of source (IoT devices, public and private data sources).
- **MIM1-R2** [H][P][A] — Context information SHALL describe real-world entities in a structured way with formal definitions (entities, properties, relationships) so status information is comprehensive and machine-interpretable.
- **MIM1-R3** [H][P][A] — Applications SHALL be able to discover information relevant to their context by specifying what is needed: runtime enumeration of entity types (`GET /types`), attributes (`GET /attributes`) and `@context` (ADR 007). An agent SHALL be able to learn what exists with zero prior knowledge; the portal SHALL render the same discovery for humans.
- **MIM1-R4** [H][P][A] — Both current and historical context information SHALL be queryable (temporal API), including geospatially.
- **MIM1-R5** [H][P][A] — Consumers SHALL be able to subscribe to changes of information so they always know the latest status (NGSI-LD subscriptions internally; ADR 010/011 channels for the public).
- **MIM1-R6** [P] — Cross-domain access SHALL be possible: information gathered by the city is available to applications across different domains through the same interface, subject to Part I access control.
- **MIM1-R7** [P] — The context broker SHALL be validated against the ETSI NGSI-LD Testing Task Force toolkit (test descriptions, test purposes, executable robot scripts).
- **MIM1-R8** [P][A] — Context information SHALL be analysable, e.g. for detecting events (in this platform: subscriptions with `q`/`watchedAttributes` conditions; MIM9 pipelines for heavier analytics).

## 13. MIM2, Shared Data Models

- **MIM2-R1** [P][A] — A catalogue of minimum common data models per vertical SHALL be adopted so applications and systems interoperate between cities: Smart Data Models (FIWARE/OASC/GSMA/TM Forum) first; a standard type SHALL NOT be re-invented (ADR 001 rule).
- **MIM2-R2** [P][A] — Harmonized representation formats and semantics SHALL be used both to consume and to publish data; every attribute SHALL resolve via `@context` to a fully qualified URI.
- **MIM2-R3** [H][P][A] — Data models SHALL capture the complete context they represent, so a consumer can request exactly the attributes it needs (`attrs`/`pick` projection); each model SHALL carry human-readable descriptions [H], machine-readable schema (JSON Schema / published `@context`) [P], and ontology mappings [A].
- **MIM2-R4** [P][A] — Existing ontologies SHALL be mappable rather than replaced: SAREF (+SAREF4Cities), oneM2M base ontology, ISA² Core Vocabularies (Core Person, Core Organization, CPSV-AP), and DTDL where digital-twin tooling requires it (schema.org additionally, per ADR 001) — by identifying entities, properties and relationships manageable via NGSI-LD.
- **MIM2-R5** [P] — Clear definitions SHALL enable transformation of data models between standards (harmonization); divergent shorthand vocabularies across federated twins SHALL be bridged by JSON-LD expansion/compaction (ADR 008), not bespoke ETL.
- **MIM2-R6** [P] — Data with an explicit geospatial (or spatio-temporal) dimension SHALL follow the MIM7 encoding provisions.
- **MIM2-R7** [H] — Custom types and their transformation functions SHALL be documented in the organisation's data dictionary (ADR 001), which is the human-browsable source of truth.

## 14. MIM3, Ecosystem Transactions (Contracts / Marketplace)

The marketplace SHALL provide the following management capabilities (module list per MIM3), each with its TM Forum API mapping where defined:

- **MIM3-R1 Catalogues** [H][P][A], Publish and search data-service offerings, organized hierarchically into groups/categories for navigation and discovery; technical description plus terms and conditions (price, SLA, license). (TMF620, TMF633, TMF634, TMF637, TMF638, TMF639; DCAT-AP for open data.)
- **MIM3-R2 Offers/Orders** [H][P][A], Ordering and acquisition of offerings and management of acquired rights: subscription, un-subscription, activation, deactivation, renewal. (TMF622, TMF641, TMF652.)
- **MIM3-R3 Revenue sharing** [P], Charging of consumers, usage-based business models, interface to external charging platforms (e.g. PayPal), collection of price/usage/consumer data per pricing model. (TMF670, TMF676; shopping cart cited as TMF633 in the MIM3 text, likely an upstream typo for TMF663, the actual TM Forum Shopping Cart API.)
- **MIM3-R4 SLAs and data licenses** [H][P], Providers define/customize SLAs and licenses per offering from predefined license templates.
- **MIM3-R5 Feedback and reputation** [H], User feedback, rating and reputation mechanisms per offering to guide consumer choice and promote honest behaviour.
- **MIM3-R6 Party management** [P], Identification and information of all parties (individuals or organizations, consumer and/or provider roles). (TMF632.)
- **MIM3-R7 Customer management** [H][P], Customer accounts, related legal entities, role assignment (data provider, data consumer, administrator) per marketplace governance. (TMF629.)
- **MIM3-R8 Transparency and accountability** [H], Auditing of orders (pricing model, license terms, SLAs) and tracking of SLA parameters, presented to humans.
- **MIM3-R9 Federation** [P][A], Marketplaces interact and expose each other's offerings, enabling aggregated services across twins per marketplace governance.
- **MIM3-R10** [P][A] — A concluded order SHALL produce an enforceable data-usage agreement expressed in W3C ODRL; the ADR 003 mapper translates it into the internal NGSI-LD `Policy` entity — the marketplace is the front door of the Part I access-request flow (R21).
- **MIM3-R11** [A] — An AI agent SHALL be able to discover offerings, negotiate and conclude contracts programmatically (data-space protocol / TMF APIs) and read the resulting ODRL to learn its rights without human interpretation.
- **MIM3-R12** [P][A] — All transacting actors SHALL be identified (did:web / VC, consistent with the ADR 001 admission rule) — MIM0 C4 depends on this (actor identification).

## 15. MIM4, Personal Data Management (Trust)

For individual citizens (MIM4 capabilities 1–8):

- **MIM4-R1** [H] — Citizens SHALL be able to choose the operator managing their data and to move between operators.
- **MIM4-R2** [H] — Citizens SHOULD be able to access their data through many different channels.
- **MIM4-R3** [H] — Citizens SHOULD be able to use the identity of their choosing — ideally a keychain of identities, chosen per service.
- **MIM4-R4** [H] — Citizens SHOULD have insight into what personal data is available, stored and shared by the providers of the applications/services they use.
- **MIM4-R5** [H] — Citizens SHOULD be able to request change or deletion of part or all of their personal data; providers comply unless legally justified otherwise (factual data affecting eligibility excepted).
- **MIM4-R6** [H] — Citizens SHOULD be able to indicate through a permission arrangement which personal data is free to use, in which circumstances, by which parties.
- **MIM4-R7** [H] — Citizens SHOULD be able to grant consent such that attribute-based, decentralised storage and selective revealing of attributes still provides full service access.
- **MIM4-R8** [H] — Citizens SHOULD be able to roam with their data between cities and internationally.

For cities and data-using services (capabilities 9–13):

- **MIM4-R9** [H][P] — Cities SHALL enable users to handle consent, allow and revoke access, with full transparency over their personal data.
- **MIM4-R10** [P][A] — Permission management SHALL be at attribute level; personal-data processing SHALL be described in a fine-grained, standardized, machine-readable manner covering purposes, processing and types of data (W3C DPV), so programs and agents can verify consent before processing; no consent record ⇒ no processing (fail closed, Part I R5).
- **MIM4-R11** [P] — Personal data management SHALL have an open API in line with MIM1 and standard data models per MIM2; sources open, documented and discoverable via MIM1. Operators MAY be grouped at the joint initiative of cities with close ties.
- **MIM4-R12** [P] — PDM systems SHALL manage personal data to a high level of security (detail delegated to MIM6).
- **MIM4-R13** [P] — PDM systems SHALL be flexible across methodologies: personal data pods, personal data spaces, or data remaining at the organisation with subject rights exercised over its use.
- **MIM4-R14** [P] — Interoperability between PDM operators SHALL follow the MIM4 two-pillar proposal: one connector for all PDM operators (any compliant operator accesses any MIM4-compliant source), under a legal framework governance (rulebook).
- **MIM4-R15** [A] — An AI agent touching personal data SHALL itself be a policy `assignee` whose grants derive from citizen consent; its access SHALL end when consent is withdrawn.

## 16. MIM5, Fair and Transparent AI

Supplier-facing requirements (the six Amsterdam areas):

- **MIM5-R1 Procedural transparency** [H], Full disclosure of the choices made, parties involved, risks and mitigation actions in creating an algorithmic model.
- **MIM5-R2 Technical transparency** [H][P], Disclosure of source code and model sufficient to explain the model to citizens/stakeholders; access to the learnings of the model, ideally structured per MIM2 (no vendor lock-in); clarity about optimisation goals and outcomes within the overall system.
- **MIM5-R3 Technical explainability** [H], Ability to explain, at the individual level, how the model produced a given outcome; with classification rules for who may see which explanation (public servants, experts, public).
- **MIM5-R4 Fairness** [H], The system SHALL NOT systematically disadvantage, bias against or discriminate against social groups and demographics.
- **MIM5-R5 Context** [H], Fairness assessment is situation/task-specific (e.g. deliberate positive discrimination to address historic imbalance) and SHALL be documented in scope of practice.
- **MIM5-R6 Accountability** [H], Suppliers accountable for respecting digital rights and anti-discrimination law; systems shielded from independent validation and public review by trade-secret/confidentiality claims SHOULD NOT be procured.

Platform-facing requirements:

- **MIM5-R7 Metadata API** [P][A], Every algorithmic decision-making system SHALL be queryable via a metadata API answering: (1) does the system use AI/automated decision-making, yes/no, which level, which schema; (2) what do the algorithms do, list of algorithms, schema used; (3) who certified the claim, link to certification, entry in a registry of certified algorithms, schema used.
- **MIM5-R8 Claim verification** [P], It SHALL be possible to check claims by comparing system results against a known reference (e.g. human decision-making), covering both the data sets used and the algorithms.
- **MIM5-R9 Algorithm register** [H][P][A], Algorithmic systems, including the platform's own autonomous AI agents, SHALL be tracked in an algorithmic register aligned with emerging register formats; every agent action is attributable (agent identity = policy `assignee`) and audited (Part I R42), and an agent's grants are inspectable from its register entry.

## 17. MIM6, Security Management

- **MIM6-R1** [H] — A methodology SHALL be applied to identify security risks and choose protective measures, per ISO/IEC 27005 information-security risk management.
- **MIM6-R2** [H] — A governance, risk-management and control framework for cybersecurity SHALL be in place, with a baseline of measures per NIST SP 800-53 rev 5 addressing the identified risks.
- **MIM6-R3** [H] — Regular cybersecurity maturity assessments SHALL be conducted.
- **MIM6-R4** [H][P] — Personal-data processing SHALL comply with GDPR (EU 2016/679); publicly exposed data SHALL pass the sanitization/anonymization layer of ADR 010.
- **MIM6-R5** [P][A] — Authorization, actor roles and data-asset-level policies (referenced by MIM0 C4) SHALL be enforced as specified in Part I R1–R43.
- **MIM6-R6** [P][A] — All cross-boundary channels — subscriptions, notifications, MQTT streams, federated queries — SHALL carry and validate authorization material (ADR 009; ADR 011 ACLs: anonymous = subscribe-only, publish restricted to internal services).

## 18. MIM7, Places (Geospatial)

Requirements (normative in MIM7 Part 1):

- **MIM7-R1** [P][A] — Geospatial data SHALL be exposed through a service interface: OGC WFS or OGC API Features — alongside the NGSI-LD `geoQ` path of MIM1. (MIM7 Part 1, Req. 1)
- **MIM7-R2** [P] — All published features SHALL have unique, persistent identifiers per the INSPIRE data specifications (D2.5 ch. 14, Identifier management) or W3C Data on the Web Best Practices. (Req. 2)

Recommendations (SHOULD, per MIM7 Part 1):

- **MIM7-R3** [P] — If data is shared through WFS, a proxy OGC API SHOULD be provided on top.
- **MIM7-R4** [H][P] — Standard-based encodings SHOULD be used: GeoJSON, GML, GeoPackage, CityGML; humans get map views of the same features.

Platform integration:

- **MIM7-R5** [P] — The link between an NGSI-LD entity and its SDI feature representation (identifier, existence, location) SHALL be established and maintained automatically over time (geospatial matching; digital-twin association), since Feature/Thing (OGC) and Entity (NGSI-LD) are the integration point of the two standard ecosystems.

## 19. MIM8, Ecosystem Indicators (work-item stage)

- **MIM8-R1** [H][P][A] — Consistent ecosystem-health measures SHALL be defined and governed so performance can be tracked, benchmarked against comparable peer cities, and improvement initiatives planned and monitored; indicators SHALL be modelled as NGSI-LD entities (ISO 37120-aligned, ADR 004 `/domain/iso37120/...` scopes) so they are queryable like any context data [P][A] and renderable as benchmarking dashboards [H].

## 20. MIM9, Data Analytics (work-item stage)

- **MIM9-R1** [P][A] — Complex data models used in analytics SHALL be interoperable: pipelines consume and produce data through MIM1 interfaces and MIM2 models, so analytics and expertise are portable between cities and usable as agent tools without custom adapters.

## 21. MIM10, Resource Impact Assessment (work-item stage)

- **MIM10-R1** [H][P] — Capabilities for management and assessment of scarcity and resources related to people, nature and investment SHALL be represented with the same MIM1/MIM2 mechanisms once MIM10 publishes its specification; no proprietary side-channel is introduced in the meantime.

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| R1–R5 | [Architecture/05-context-gateway.md#1-execution-pipeline-stages](../Architecture/05-context-gateway.md#1-execution-pipeline-stages) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |
| R6–R9 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |
| R10–R15 | [Architecture/05-context-gateway.md#1-execution-pipeline-stages](../Architecture/05-context-gateway.md#1-execution-pipeline-stages) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |
| R16–R19 | [Architecture/12-identity-and-access.md#4-authzen-discovery-endpoints-r51-r16-r17](../Architecture/12-identity-and-access.md#4-authzen-discovery-endpoints-r51-r16-r17) | [Testing/01-backend-tests.md#4-portal-api-integration--database-testing](../Testing/01-backend-tests.md#4-portal-api-integration--database-testing) |
| R20–R22 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |
| R23–R28 | [Architecture/04-context-spaces-and-endpoints.md#5-cross-project-sharing-model](../Architecture/04-context-spaces-and-endpoints.md#5-cross-project-sharing-model) | [Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance](../Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance) |
| R29–R31 | [Architecture/03-domain-model.md#4-scope-hierarchy-taxonomy](../Architecture/03-domain-model.md#4-scope-hierarchy-taxonomy) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |
| R32–R39 | [Architecture/04-context-spaces-and-endpoints.md#5-cross-project-sharing-model](../Architecture/04-context-spaces-and-endpoints.md#5-cross-project-sharing-model) | [Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance](../Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance) |
| R40–R43 | [Architecture/05-context-gateway.md#5-performance-budgets--fail-secure-design](../Architecture/05-context-gateway.md#5-performance-budgets--fail-secure-design) | [Testing/05-deployment-and-performance-tests.md#4-load--performance-testing-with-k6](../Testing/05-deployment-and-performance-tests.md#4-load--performance-testing-with-k6) |
| MIM0 | [Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model](../Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model) | [Testing/02-conformance-tests.md#5-json-ld-11-specification-conformance](../Testing/02-conformance-tests.md#5-json-ld-11-specification-conformance) |
| MIM1 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance](../Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance) |
| MIM2 | [Architecture/11-data-models.md#3-smart-data-models--external-standards-alignment](../Architecture/11-data-models.md#3-smart-data-models--external-standards-alignment) | [Testing/02-conformance-tests.md#5-json-ld-11-specification-conformance](../Testing/02-conformance-tests.md#5-json-ld-11-specification-conformance) |
| MIM3 | [Architecture/18-data-space-connector.md#2-provider-role-publishing-an-endpoint-into-a-data-space](../Architecture/18-data-space-connector.md#2-provider-role-publishing-an-endpoint-into-a-data-space) | [Testing/02-conformance-tests.md#6-dataspace-protocol-conformance](../Testing/02-conformance-tests.md#6-dataspace-protocol-conformance) |
| MIM4 | [Architecture/13-security.md#1-trust-zone-model--threat-assessment](../Architecture/13-security.md#1-trust-zone-model--threat-assessment) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |
| MIM5 | [Architecture/07-agents-and-mcp.md#4-agent-identity-attributability--audit-cc-44](../Architecture/07-agents-and-mcp.md#4-agent-identity-attributability--audit-cc-44) | [Testing/06-security-tests.md#5-ai-agent-red-teaming--prompt-injection-defense](../Testing/06-security-tests.md#5-ai-agent-red-teaming--prompt-injection-defense) |
| MIM6 | [Architecture/13-security.md#2-bsi-tr-03187-conformance-matrix](../Architecture/13-security.md#2-bsi-tr-03187-conformance-matrix) | [Testing/06-security-tests.md#1-automated-static--dependency-security-scans](../Testing/06-security-tests.md#1-automated-static--dependency-security-scans) |
| MIM7 | [Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine](../Architecture/04-context-spaces-and-endpoints.md#4-multi-representation-translation-engine) | [Testing/02-conformance-tests.md#2-ogc-api---features-part-1-conformance](../Testing/02-conformance-tests.md#2-ogc-api---features-part-1-conformance) |
| MIM8 | [Architecture/10-dashboards-and-visualization.md#3-datamodel-driven-filter-generation](../Architecture/10-dashboards-and-visualization.md#3-datamodel-driven-filter-generation) | [Testing/03-frontend-and-e2e-tests.md#2-playwright-end-to-end-user-journeys](../Testing/03-frontend-and-e2e-tests.md#2-playwright-end-to-end-user-journeys) |
| MIM9 | [Architecture/08-pipelines.md#3-pipeline-manifest-specification](../Architecture/08-pipelines.md#3-pipeline-manifest-specification) | [Testing/04-configuration-and-pipeline-tests.md#4-bento-pipeline-testing](../Testing/04-configuration-and-pipeline-tests.md#4-bento-pipeline-testing) |
| MIM10 | [Architecture/11-data-models.md#1-authoring-models-in-linkml](../Architecture/11-data-models.md#1-authoring-models-in-linkml) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-schema-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-schema-validation) |

## Related

- [00-index](00-index.md) — all requirement families.
- [traceability](traceability.md) — requirement to chapter and test mapping.
