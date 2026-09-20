---
sidebar_position: 15
title: "Policy Firewall (R44…, I)"
---

# Policy Firewall, Consolidated Platform Requirements

Status: Draft (consolidated 2026-08-14, ngsi-ld session)
Scope: everything the platform must satisfy and build to have a WORKING
policy firewall (PEP + PDP + policy store + identity) in front of NGSI-LD
context brokers, standardized on NGSI-LD wherever the spec offers a hook.
Sources: `access-control.md` (R1–R43 + MIM Part II),
`gateway-firewall.md` (GW1–GW31), ADR 001/002/003/006, the 2026-08-14 design
doc (gap list 1–14), and two research notes that were never committed to this
repository: the firewall results (L1–L16, U1–U8, grant-as-registration §6–§9)
and the WebSocket binding (WS-45/WS-47). Citations to
`../research/firewall-results.md`, `../specs/websocket-binding.md` and
`../registers/requirements-atlas.md` below name files that do not exist here;
resolve a cited ID through [00-index](00-index.md) instead.
This document is canonical for **R44–R60** (extending the R-numbering of
`access-control.md`) and for **I1–I4** (identity stack). All other IDs
are cited, never restated, resolve them via [00-index](00-index.md).

Keywords MUST / SHOULD / MAY per RFC 2119.

---

## 1. Normative baseline and the standardization ladder

The firewall is standardized to the degree that each grant class is
enforced by the most spec-native mechanism that can express it.

**R44, Standardization ladder (governing rule).** For every grant class,
enforcement MUST use the highest applicable rung; dropping a rung MUST be
justified in an ADR:

1. **CSR narrowing (grant-as-registration)**, structure-shaped grants
   (tenant, operation, type, id/idPattern, attribute names, `datasetId`,
   `scope`, geo area, absolute time interval) compile to Context Source
   Registrations on per-role view tenants; enforcement is ETSI GS CIM 009
   clause 4.3.6.1 mandatory narrowing, executed by conformance-tested
   broker code. (firewall-results §6/§9.)
2. **NGSI-LD QL AST rewriting at the gateway**, value-shaped grants
   (`q` conditions), identity-parameterized grants (`q=owner=="<did>"`),
   rolling time windows needing continuous clamping. (R10–R15, ADR 006.)
3. **Gateway post-filtering / response masking**, only what the QL
   cannot express: id-pattern intersection (R47), attribute projection of
   responses (R9), result-count recomputation.
4. **Broker-native extension**, only where no request-side mechanism is
   sound: conditional writes (R45), native constraint passing (GW24).
   Every rung-4 mechanism MUST be written up as a candidate ETSI ISG CIM
   change request so it can migrate down the ladder.

Component roles **as built**: the Context Gateway is the PEP and carries
the PDP in its own process (`crates/context-gateway/src/pdp/`, `PolicyPdp`),
APISIX routes, rate-limits and strips forgeable inbound headers but decides
nothing (OPS-33, PF-46), Keycloak is the only identity provider (PF-45), the
configuration repository is the policy store (`kind: Policy` manifests, CC-72),
and Antares is the policy-free data plane.

> The design doc this page consolidates named APISIX as the PEP and an external
> OPA as the PDP over its Compile API. [ADR-N-003](../Decisions/adr-n-003-context-gateway-in-rust.md)
> refused that arrangement: the `APISIX → OPA → AuthZ Adapter → PostgreSQL` hop
> cost 30 to 80 ms per request and could not rewrite an NGSI-LD query AST, which
> is what rung 2 of the ladder above requires. No OPA runs in any environment
> (`joinedcontext-deployment/components/` has no such component), and neither
> FIWARE VCVerifier nor the Trusted Issuers Registry is deployed. Read every
> "OPA" below as the in-process PDP, and I2 and I3 as designed and not built.

---

## 2. Requirement families this document builds on

The normative texts of R1–R43 (+ MIM Part II) live in
`access-control.md` and of GW1–GW31 in `gateway-firewall.md`; they are
deliberately NOT restated here. Resolve any cited ID via the generated
index `../registers/requirements-atlas.md`.

MIM Part II (MIM0–MIM10) applies platform-wide; the firewall-facing
subset is: structured errors + rate-limit headers mandatory (MIM0-R8),
effective permissions/dry-run as the agent surface (MIM0-R11), ODRL
contracts feed the R21 flow (MIM3-R10), DPV consent gates personal data
(MIM4-R10, MIM4-R15), agents are auditable assignees (MIM5-R9).

### 2.1 Identity stack (I1–I4), canonical here

- **I1** — Keycloak = OIDC + OID4VCI issuance only; never Keycloak
  Authorization Services/UMA for policies.
- **I2** — VCVerifier exchanges OID4VP presentations for plain JWTs
  consumed by the Portal and the Context Gateway like any other realm token.
- **I3** — Peer FDTs never get Keycloak accounts; identity = did:web,
  trust = Trusted Issuers Registry.
- **I4** — Tokens carry identity only (`sub`, did), never permissions;
  short-lived; RFC 8693 exchange for service hops; DPoP at the edge.

---

## 3. What is MISSING, new requirements R45–R60

These close the 14 gaps of the design doc and the U1–U8 unsolvable
combinations, each on the most standard mechanism available. Status of
every item in §3 today: **designed here, not built.**

### 3.1 Structural gaps

**R45, Conditional writes via HTTP conditional requests (gap 3, U1).**
The broker SHALL emit a strong `ETag` per entity (RFC 9110 §8.8) and
support `If-Match` on all write operations, rejecting with 412 on
mismatch (RFC 9110 §13.1.1). The gateway SHALL enforce write policies
with `q`/geo conditions as read → evaluate → conditional write, making
TOCTOU a detectable 412 instead of a race. Standard: RFC 9110; filed as a
candidate ETSI CR (per R44 rung 4). Modelling rule first: partition write
authority by URN prefix (ADR 001) wherever possible, an id never
changes, so prefix-partitioned grants need no condition at all
(firewall-results §9.1 change 3). Genuinely mobile/stateful entities are
the only R45 consumers.

**R46, Notification egress enforcement (gap 1, L4).** No standard
filters notification payloads per recipient; the platform closes this
itself, on two rungs: (a) grants enforced as CSRs, forwarded
subscriptions are registration-narrowed by clause 5.8.1.4 and severed by
CSR deletion (spec-native, preferred); (b) gateway-rewritten grants, the
gateway SHALL rewrite `notification.endpoint.uri` at subscription
creation to route delivery through an egress path of the same PEP, which
applies the same masking projection and `q` re-check before
forwarding to the original endpoint. MQTT (ADR 011) and WS (`../specs/websocket-binding.md`
WS-45) deliveries SHALL pass the same egress path. The broker stays
policy-free.

**R47, idPattern intersection (gap 2).** Fleet grants SHALL be
expressed as `scope` (hierarchical, natively intersectable) or URN-prefix
`idPattern`, never arbitrary regex. Where a caller pattern and a grant
pattern must both hold, the gateway SHALL forward the grant pattern and
post-filter returned ids against the caller pattern (safe: only
narrows), recomputing `NGSILD-Results-Count`. Long-term: ETSI CR for an
id-prefix operator in the QL.

**R48, Revocation reaches derived state (gap 4, U6).** On `Policy`
change/deletion the platform SHALL, within a bounded propagation time:
invalidate the PEP policy cache (existing), re-narrow or deactivate
stored subscriptions (GW27), delete/renarrow derived CSRs on view
tenants, and invalidate the assignee's EntityMaps. View-tenant
`cacheDuration` SHALL be ≤ the accepted revocation lag. Cross-domain:
revocation events SHALL be emitted and consumed as OpenID Shared Signals
Framework / CAEP events on Security Event Tokens (RFC 8417), so peer
FDTs can kill derived state too. "Instant" revocation is explicitly not
promised (U6); the bound is the requirement.

**R49, Meta-governance of the policy store (gap 5).** Writing `Policy`
entities SHALL itself be governed by meta-policies in the same model:
(a) bootstrap meta-policy, any authenticated identity reads own
policies (`q=assignee=="<did>"` injected); (b) assigner authority, an
identity may create/modify only policies whose `information` falls
entirely inside resources its own did:web domain minted (the ADR 001
`{Razidlo}` admission rule applied to policy writes); (c) platform-admin
prohibition rule guards everything else. Delegation chains (UCAN/ZCAP
class) are OUT of v1, no ratified standard exists; revisit only for
offline cross-FDT delegation. R21 approval stays a manual ticket.

**R50, VC revocation wired end-to-end (gap 11).** Issued credentials
SHALL carry `credentialStatus` per W3C Bitstring Status List v1.0;
Keycloak publishes the status list; VCVerifier config sets
`requireStatus: true` and `acceptedPurposes: [revocation, suspension]`
per credential type (the verifier already supports this). The IETF OAuth
Token Status List draft SHOULD be tracked for the exchanged JWT.

### 3.2 Standard API surfaces

**R51, Discovery API shaped after OpenID AuthZEN (R16/R17 refinement).**
`POST /access/check` request/response SHALL follow the AuthZEN
Authorization API 1.0 evaluation shape (subject/action/resource/context;
decision + optional reason), and `GET /access/permissions` SHALL be
expressible as AuthZEN subject-search/resource-search, keeping the
partial-evaluation implementation. This makes the PDP swappable and the
agent surface (MIM0-R11) a standard one.

**R52, ODRL profile pinned to the data-space dialect (gap 10, ADR 003
refinement).** The `ngsi-ld:` ODRL profile SHALL be published as a
formal ODRL 2.2 profile (own `@context`, IRI, term definitions for the
clause 4.20 actions and `entities`/`propertyNames`/`relationshipNames`/
`q`/`scopeQ`/`geoQ`/`temporalQ`/`datasetId` leftOperands) authored as an
extension of the IDSA Data Space Protocol ODRL profile subset, so MIM3
contract negotiation (Eclipse EDC / FIWARE data-space connector) needs
no second mapper. Round-trip property (R26) verified by tests over the
profile, not by inspection.

**R53, `datasetId` granularity (gap 13).** The `information` block
SHALL support a `datasetIds` array with CSR semantics (Table 5.2.9-1
`datasetId` member): grants scoped to specific attribute instances;
intersection per GW11; enforcement on rung 1 via the CSR member where
grants are registrations, else by response projection.

**R54, Obligations are contracts, never firewall (U5).** ODRL duties
(delete-after, attribution, purpose binding per MIM4/DPV) SHALL be
carried in the ODRL/contract layer (MIM3) and monitored by audit; the
PEP SHALL NOT advertise or fake request-time enforcement of duties. DPV
terms ride the R52 profile as constraint/duty leftOperands.

**R55, Sub-attribute privacy is publication, not filtering (U3).**
Anything below attribute granularity (metadata stripping, precision
degradation, bucketing) SHALL be produced as derived entities/tenants at
publication time (ADR 010), never by rewriting response bodies in
flight.

### 3.3 Correctness & verification (the actual blockers)

**R56, One grammar everywhere (gap 9, §6.1 made normative).** The
UCAST → NGSI-LD-QL translator and all gateway parsing of `q`/`scopeQ`
SHALL use the broker's own antares-ql crate compiled to Wasm inside the
APISIX plugin; the gateway SHALL NOT contain a second hand-written
NGSI-LD grammar. New spec parameters unknown to the parser ⇒ deny (R5).

**R57, Property-based rewriter verification (gap 14; build FIRST).**
A property-based test suite SHALL assert, for arbitrary user query ×
policy set: (a) soundness, no returned entity/attribute falls outside
the union of grants; (b) write soundness, no accepted write payload
falls outside every single policy; (c) 404/403/empty-narrowing semantics
(R20/GW12); plus an adversarial corpus of known bleed shapes (ADR 006
cross-product, @context aliasing, idPattern tricks). CI SHALL gate every
rewriter/translator change on it. The ETSI suite covers the broker only;
this suite is the firewall's equivalent.

**R58, @context expansion at the trust boundary (L1).** All policy
matching (types, attribute names) SHALL happen on fully expanded URIs;
the gateway SHALL perform JSON-LD expansion using an allow-listed,
integrity-checked `@context` cache (poisoned-context hardening); client
`@context` values are untrusted input.

**R59, Existence side-channel budget (L3, U7).** `NGSILD-Results-Count`
SHALL be recomputed after post-filtering; type/attribute discovery
responses narrowed to grants (worked example g); error bodies for
cross-grant probes byte-identical to not-found (same rule as WS-47.3).
Timing channels are accepted and documented, not denied.

**R60, Scale proof before scale promises (gaps 6–8, R41 extension).**
Before production rollout the platform SHALL measure and record:
(1) R41 regex-fold vs native `scopeQ` at 10 M rows; (2) residual-filter
explosion, 10k per-id policies OR-ed: OPA partial-eval latency, filter
size vs body limits; (3) response-masking throughput on 1000-entity
pages; (4) the federated path per firewall-results §7.4 (loopback hop,
`cacheDuration` hit ratio, notification latency). Numbers gate which
ladder rung serves which grant class; audit portability: OPA decision
logs (decision_id → matched policy) SHALL be exportable in a documented
schema so R42 evidence survives a PDP swap.

---

## 4. Definition of done, what must exist for a WORKING firewall

Build order per the design doc's order of attack; ✅ = exists today.

| # | Deliverable | Covers | Status |
|---|---|---|---|
| 1 | Property-test harness + bleed corpus (R57) | makes everything else safe to change | missing |
| 2 | antares-ql Wasm plugin: parse + AST merge + UCAST→QL (R56, R10–R13) | the security-critical piece | missing |
| 3 | PEP wiring: authn, tenant pin, verdicts, POST-query forwarding, response projection, restricted header | R1–R15, GW1–GW22 | built in the Context Gateway, not in APISIX (ADR-N-003); APISIX carries the header strip and the rate-limit classes only |
| 4 | OPA data-push consumer + Compile-API integration (`maskRule`, decision logs) | §5 of design doc, R40, R42 | missing |
| 5 | Policy tenant + bootstrap meta-policy + assigner-authority rule (R49) | gap 5 | missing |
| 6 | Policy-change notification consumer → cache invalidation + revocation reaper (R48) | gaps 4 | missing |
| 7 | Notification egress path, all three bindings (R46) | gap 1 | HTTP binding built (gateway rewrite + egress projection, geo and scope grants narrowed, TLS delivery); MQTT and WS missing |
| 8 | Grant-as-registration tooling: role→view-tenant CSR compiler, seed scripts in git, `observationInterval` cron | firewall-results §9 (the 80 %) | missing |
| 9 | ETag/If-Match in Antares + gateway conditional-write flow (R45) | gap 3 | gateway flow built; Antares emits no `ETag` yet, so every `If-Match` answers 412 |
| 10 | ODRL profile document + round-trip mapper with tests (R52, R26) | gap 10 | mapper built (`crates/context-gateway/src/federation/odrl_compiler.rs`, `handlers/access_odrl.rs`, tested by `access_odrl_tests.rs` and the conformance suite `tests/security/test_odrl_mapping.py`); the published profile document is missing |
| 11 | AuthZEN-shaped `/access/*` endpoints (R51, R16–R17) | discovery | built: `GET /api/endpoint/{slug}/access` and `POST …/access/check` (`crates/context-gateway/src/app.rs:247`), with `handlers/access.rs`, `access_ucast.rs`, and `tests/security/test_authzen_access.py` |
| 12 | VC status lists: Keycloak issuance + VCVerifier `requireStatus` (R50) | gap 11 | verifier ready, issuer + config missing |
| 13 | @context expansion + hardened context cache at the PEP (R58) | L1 | missing |
| 14 | Benchmark suite + recorded numbers (R60) | gaps 6–8, R41 | missing (5-broker Scorpio compose can host it today) |
| 15 | Trusted Issuers Registry + CSR admission check (R24) | federation trust | ✅ design + components chosen, wiring missing |

Nothing in this table modifies the broker's policy-free stance except
rows 9 and GW24 (both rung-4, both candidate ETSI CRs).

## 5. Standardization statement

- **Spec-native (no invention):** CSR narrowing, `tenant` member, EntityMap
  pagination, `Via` loops, `management.*` budgets, `observationInterval`/
  `managementInterval` temporal axes, scope taxonomy, operation
  vocabulary, ProblemDetails errors, all CIM 009.
- **Standards adopted at the edges:** OIDC/OID4VCI/OID4VP, did:web,
  RFC 8693, DPoP, RFC 9110 conditional requests (R45), RFC 8417 SET +
  OpenID SSF/CAEP (R48), W3C Bitstring Status List (R50), OpenID AuthZEN
  (R51), W3C ODRL 2.2 profile over the IDSA DSP subset (R52), W3C DPV
  (R54), RFC 2119/7807/9325 throughout.
- **Profiled extensions (documented, additive):** the `ngsi-ld:` ODRL
  profile terms, `NGSILD-Results-Restricted` header, `/access/*`
  endpoints, WS binding options.
- **Deliberately non-standard (no standard exists; tracked as ETSI CR
  candidates):** notification egress filtering (R46), id-prefix QL
  operator (R47), entity ETags (R45), native constraint passing (GW24).
- **Explicitly refused:** Keycloak Authorization Services/UMA for
  policies, permissions in JWTs, XACML, Kafka exposed across trust
  boundaries, deny rules in the policy algebra.

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| I1–I4 | [Architecture/12-identity-and-access.md#1-identity-stack-specification-i1i4](../Architecture/12-identity-and-access.md#1-identity-stack-specification-i1i4) | [Testing/01-backend-tests.md#4-portal-api-integration--database-testing](../Testing/01-backend-tests.md#4-portal-api-integration--database-testing) |
| R44–R50 | [Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48](../Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |
| R51–R55 | [Architecture/12-identity-and-access.md#4-authzen-discovery-endpoints-r51-r16-r17](../Architecture/12-identity-and-access.md#4-authzen-discovery-endpoints-r51-r16-r17) | [Testing/02-conformance-tests.md#6-dataspace-protocol-conformance](../Testing/02-conformance-tests.md#6-dataspace-protocol-conformance) |
| R56–R60 | [Architecture/05-context-gateway.md#1-execution-pipeline-stages](../Architecture/05-context-gateway.md#1-execution-pipeline-stages) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |

## Related

- [00-index](00-index.md) — all requirement families.
- [traceability](traceability.md) — requirement to chapter and test mapping.
