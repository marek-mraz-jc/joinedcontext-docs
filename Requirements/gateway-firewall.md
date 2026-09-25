---
sidebar_position: 14
title: "Gateway Firewall (GW)"
---

# Gateway Firewall Rule Model, NGSI-LD PEP & Antares Broker

Status: Draft
Date: 2026-08-07
Scope: The rule/verdict model of the NGSI-LD gateway ("firewall") and its enforcement in the Antares broker. Complements `access-control.md` (R1–R43: architecture, policy model, federation); this document specifies the rule chain, the three verdicts, and the request-intersection algebra.
Related: ADR 002 (Policy entity), ADR 004 (Scopes), ADR 006 (privilege bleed), `AntaresBroker/docs/src/storage.md` (shared-schema tenancy and the row-level-security belt).

Family **GW** (GW1…GW34). Owning chapter: [Architecture/05-context-gateway.md](../Architecture/05-context-gateway.md). Verified by: [Testing/01-backend-tests.md](../Testing/01-backend-tests.md).

Keywords MUST / SHOULD / MAY per RFC 2119.

## 1. Verdicts, the three levels

Every request resolves to exactly one verdict:

- **GW1, DENY**, the request is refused. Single-entity reads of a forbidden entity return 404 (no existence disclosure, R20); all other denies return 403 with an RFC 7807 ProblemDetails body.
- **GW2, REWRITE (insert rule)**, the request is forwarded only after the gateway injects constraints into it (tenant, `type`, `id`/`idPattern`, `attrs`, `q`, `scopeQ`, `geoQ`, `temporalQ`), so the broker can physically only return or accept what the caller's grants cover (R11–R14). This is the normal verdict for every authenticated non-admin caller and for the `public` role.
- **GW3, ALLOW**, forwarded unchanged. Reserved for internal service identities and platform admins on the internal listener. An ordinary user MUST never get plain ALLOW, at minimum the tenant is pinned (GW20), so their floor is REWRITE.

Verdict resolution:

- **GW4** — Precedence MUST be DENY > REWRITE > ALLOW. Explicit prohibitions are evaluated before permissions; any matching prohibition ends evaluation with DENY.
- **GW5** — Default verdict MUST be DENY: no matching rule, unreachable PDP, unparseable request, unknown operation ⇒ deny (fail closed, R5).
- **GW6** — The verdict and the matched rule id MUST be logged for every request (R42); DENY responses SHOULD carry the request id but MUST NOT reveal which rule denied.

## 2. Rule anatomy

- **GW7** — A rule = **match part** + **effect part**. Match part: caller (subject / role / group / tenant membership / `anonymous` ⇒ role `public`), operation (ETSI CIM 009 operation names only, R8), and resource selector (entity type incl. type-selection language, `id`/`idPattern`, attribute names, `scopeQ`, `geoQ`, `temporalQ`, `q` value conditions, `datasetId`). Effect part: verdict, and for REWRITE the constraint set to intersect in.
- **GW8** — Rules MUST be stored as NGSI-LD `Policy` entities (ADR 002) — the rule table is data, editable at runtime through the same API (guarded by its own policies), never gateway config requiring redeploy. DENY rules are policies with prohibition semantics; REWRITE/ALLOW derive from permissions.
- **GW9** — Rule changes MUST take effect within a bounded propagation time (cache invalidation on `Policy` change, R40) and MUST be auditable (who changed which rule when).

## 3. Request-intersection algebra (the core)

How "what the caller asked for" meets "what the caller is granted":

- **GW10** — Effective request = `userRequest ∧ (grant₁ ∨ grant₂ ∨ … ∨ grantₙ)`. AND inside one policy's constraint set, OR across policies, applied on the parsed AST (R10–R12) — never by naive query-parameter concatenation, so cross-policy privilege bleed is impossible (ADR 006).
- **GW11** — Per-dimension intersection MUST be:

| Dimension | Intersection rule |
|---|---|
| tenant | pinned by gateway (GW20); client value ignored |
| `type` | set intersection; requested type outside every grant ⇒ empty read / denied write |
| `id` / `idPattern` | conjunction; grant patterns MUST stay anchored `^…$` (R24) |
| `attrs` / `pick` | requested ∩ granted; if the caller requests none, the granted attribute set becomes the projection; response stripped accordingly (R9) |
| `q` | logical AND of caller `q` and grant `q` |
| `scopeQ` | hierarchical: grant on `/geo/SK/BB` covers descendants; folded into `q` as anchored regex on `scope` (R13, R30) |
| `geoQ` | both geometries must hold. NGSI-LD carries one `geoQ` per request, so: if one geometry contains the other, forward the smaller; otherwise forward the **grant** geometry (security-critical, enforced at the broker) and post-filter the caller's geometry at the gateway |
| `temporalQ` | time-interval intersection; e.g. grant "older than 7 days" clamps `endTimeAt` to `now − 7d`; degenerate/empty interval ⇒ empty result |
| `datasetId` | set intersection on granted dataset ids |

- **GW12** — Empty intersection on a **read** MUST yield HTTP 200 with an empty result (silent narrowing, R20), with the opt-in `NGSILD-Results-Restricted: true` header (R22). Empty intersection on a **write** MUST yield DENY.
- **GW13** — The computed intersection MUST be introspectable: effective-permissions endpoint (R16) returns the merged grant; the dry-run endpoint (R17) returns the verdict plus, for REWRITE, the constraints that would be injected — so a caller (human, program, or agent) can see the intersection before sending the real request.
- **GW14** — Merged queries that exceed URL limits MUST go via `POST /entityOperations/query` (R13), preserving pagination.

## 4. Reads vs writes

- **GW15** — Reads are **narrowed**, never errored: filters + projection shrink the result to the permitted subset.
- **GW31** — A read whose `type` is not an NGSI-LD name or type expression, or whose `q` is not made of the query language's tokens (unbalanced parentheses or strings, whitespace or a single quote outside a string), MUST be answered `400 BadRequestData` before it is narrowed, and the refusal MUST NOT repeat the value (AG-21). GW12's empty answer is for well-formed reads only. A query naming no selector at all (an `id` list or `idPattern` alone) MUST be answered `400 BadRequestData` as CIM 009 5.7.2.4 requires, not narrowed to the granted types (GW33, T-0780).
- **GW16** — Writes are **never narrowed**: the entire payload MUST fall inside at least one single policy's constraint set — entity type, URN prefix / dataset (ADR 001), `scope` values (R29, R31), and the entity's own `location` Property geometrically inside the granted area. The geo check applies to the **payload content**, not just query parameters: "user can edit only data in location X" means the gateway tests the entity's coordinates against the granted polygon on create/update.
- **GW17** — A partial write (PATCH/merge) touching any attribute not granted MUST be denied whole — no silent dropping of attributes from a write. "Whole" is the one entity the write names: an entity of a batch is judged whole by this rule, and the batch is divided per entity by GW18. The body of an addressed write MUST NOT name an `id` other than the one in its path, and a `type` it names MUST be the type that id carries (PF-44).
- **GW18** — Batch operations (`entityOperations/*`) MUST be evaluated per entity; mixed outcomes return 207 with per-entity ProblemDetails, permitted entities still applied. Only the permitted entities reach the broker; the answer is the CIM 009 `BatchOperationResult` (`success` lists the ids applied, `errors` one `{entityId, error}` per refused entity), and a batch with no permitted entity is answered 207 without asking the broker. A batch entry that names no entity id, or an id that is malformed or of another space (PF-42), makes the request malformed and refuses the batch whole (400), and a grant decided from the stored entity refuses a batch whole (R45).
- **GW32** — A batch that would **change or remove** stored entities (`entityOperations/upsert`, `update`, `merge`, `delete`) MUST be refused `403` whole when any matching policy decides from the stored entity — a `q` or a granted area — because such a batch addresses its entities in the payload, so there is nothing to read first and no entity tag to write under (R45). `entityOperations/create` is unaffected: a create has no stored state. The refusal MUST tell the caller to write one entity per request, and MUST NOT name the policy (GW6). Write authority that has to cover batches is partitioned by URN prefix (ADR 001) rather than by a condition.
- **GW33** [gateway, conformance] — The NGSI-LD read surface of an Endpoint answers as ETSI GS CIM 009 specifies. A grant narrows the result set of a well-formed read (GW10–GW12); it MUST NOT change a status code the specification fixes, and no deviation from it is recorded as accepted. Concretely: a query naming no selector (an `id` list or `idPattern` alone, 5.7.2.4) is `400 BadRequestData` even when the caller's grants would have selected a type for it. A client of ours that relied on the narrowing names its type instead; the conformance suite, not the client, fixes the surface.
- **GW19** — Deletes are writes: same containment rules as GW16.
- **GW34** [S] — A grant that names one of the five CIM 009 Table 4.20-2 operation groups (`federationOps`, `associationOps`, `updateOps`, `retrieveOps`, `redirectionOps`) MUST be evaluated as exactly the operations that table lists for it and as no others, and a name that is neither a Table 4.20-1 operation nor one of those groups MUST be refused when the `Policy` is validated rather than ignored (R8, Architecture/03 §Policy).

## 5. Tenants, pinning and chaining

- **GW20** — The `NGSILD-Tenant` header MUST be stripped from client input and injected by the gateway from the caller's grant. A caller never chooses a tenant; the tenant is a conclusion of authentication.
- **GW21** — A grant spanning several tenants MUST NOT be served by the gateway looping over tenants. Cross-tenant visibility = **federation**: tenant B is registered as a Context Source (CSR with anchored URN `idPattern`) in the caller-facing federation broker, and distributed operations resolve it (R32–R39). "Chaining tenants" is therefore CSR chaining, and each hop passes the target's own gateway policies (R23–R25).
- **GW22** — Anonymous / public access is the role `public` on a designated tenant, same machinery: REWRITE to the public grant (typically: one tenant, a geo bounding area, an attribute whitelist, and a temporal clamp). No separate "open data code path" exists; ADR 010 read-only publishing composes on top.

## 6. Antares-broker enforcement (defense in depth)

- **GW23** — Antares's shared-schema tenancy (one schema, `tenant_id` column + Postgres row-level security) is the **second** enforcement layer: the RLS session tenant is set from the gateway-pinned tenant on every pooled connection, so even a gateway bug cannot read or write across tenants.
- **GW24** — Antares SHOULD accept the gateway's computed constraint set natively on the internal listener (signed header or trusted body extension) instead of only the regex-folded query, so `scopeQ`/`geoQ` constraints hit native (GiST/ltree-style) indexes — this is the designed answer to the R41 performance concern with regex-folded scopes.
- **GW25** — Identity/constraint headers MUST be trusted only on the internal listener; the public listener (if any) MUST reject them. The broker MUST NOT be reachable except through the gateway (R1).
- **GW26** — Temporal API requests pass the same temporalQ clamping (GW11); Antares's temporal store MUST apply the clamped interval, enabling grants like "only data older than one week" or "only the last 24 h". A caller's `lastN` above 1000 MUST be cut to 1000 before the broker is asked, never refused, so one request cannot make the shared broker read an unbounded history.
- **GW27** — Subscriptions are standing queries: at creation time the subscription's `q`/`entities`/`geoQ`/`scopeQ`/`watchedAttributes` MUST be intersected with the caller's grants exactly like a query (GW10–GW11), and stored in the narrowed form; notification payloads pass the same attribute projection (R9). A later policy revocation MUST deactivate or re-narrow affected subscriptions: the gateway MUST store the subscriber's subject with the subscription, signed with its own delivery key and bound to the endpoint, the target and the granted areas, and MUST decide every delivery again against the policies in force, sending nothing a revoked grant no longer allows and projecting what it sends by the grant as it stands; a subscription whose stored subject is missing or does not verify MUST NOT be delivered.

## 7. Separation of policy and data

- **GW28** — Policy information MUST NOT be stored inside the guarded entities (restates R2). A `ParkingSpot` never carries `owner`, `acl`, `allowedRoles`, `visibility` or any other access-control attribute; every decision derives solely from `Policy` entities evaluated at the PDP. Entity payloads are data-plane: they get federated, notified, cached and exported — anything embedded in them leaks and rots.
- **GW29** — The gateway MUST reject writes that try to smuggle access-control attributes into guarded entities (attribute-name blocklist / policy-vocabulary namespace check at the PEP), the same way it rejects unknown scopes (R29).
- **GW30** — The only sanctioned touchpoint on the data plane is the `scope` attribute: it is classification (a label from the ADR 004 taxonomy), not policy. Entities say *what/where they are*; `Policy` entities say *who may do what with which labels*. `Policy` and `ScopeDefinition` entities live in their own guarded type/tenant (see the prohibition example below) and MUST NOT be exposed through federation CSRs.

## 8. Worked examples (rule sketches)

Public viewer, "public sees one tenant, one district, few attributes, data ≥ 1 week old":

```text
match:  role=public, op=queryEntity|retrieveEntity|queryTemporal
effect: REWRITE {
  tenant: "banskabystrica",
  geoQ:   within POLYGON(<district boundary>),
  attrs:  [temperature, airQualityIndex, location],
  temporalQ: before now-P7D,
  scopeQ: "/geo/SK/BB/#"
}
```

District editor, "user edits only Device entities of dataset X inside their district":

```text
match:  role=editor:sasova, op=createEntity|updateEntity|appendAttrs|deleteEntity
effect: REWRITE-check {
  tenant:    "banskabystrica",
  type:      Device,
  idPattern: "^urn:ngsi-ld:Device:bb:streetlights:.*$",
  scope:     "/geo/SK/BB/Sasova/#",
  payload.location: within POLYGON(<Sásová boundary>)
}
```

"Nobody but platform-admin touches Policy entities" needs no rule at all: the default
verdict is DENY (GW5), so granting the permission to `role: platform-admin` and to nobody
else already denies everyone else.

A prohibition is for taking something back out of a broader grant that stays in force,
"the reporting group reads every Device except the ones in the depot":

```yaml
spec:
  effect: prohibition                # permission (default) | prohibition
  assignee: { kind: group, id: reporting }
  operations: [queryEntity, retrieveEntity]
  information:
    - entities:
        - type: Device
          idPattern: "^urn:ngsi-ld:Device:banskabystrica\\.sk:doprava:depot-.*$"
```

Precedence makes the subtraction work: the prohibition is evaluated first and any match
ends the evaluation with DENY, whatever the group's other grants say (GW4).

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| GW1–GW6 | [Architecture/05-context-gateway.md#1-execution-pipeline-stages](../Architecture/05-context-gateway.md#1-execution-pipeline-stages) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| GW7–GW9 | [Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48](../Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| GW10–GW14 | [Architecture/05-context-gateway.md#1-execution-pipeline-stages](../Architecture/05-context-gateway.md#1-execution-pipeline-stages) | [Testing/01-backend-tests.md#2-the-context-gateway-harness](../Testing/01-backend-tests.md#2-the-context-gateway-harness) |
| GW15–GW19 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| GW20–GW22 | [Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09](../Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| GW23–GW27 | [Architecture/13-security.md#1-trust-zone-model--threat-assessment](../Architecture/13-security.md#1-trust-zone-model--threat-assessment) | [Testing/01-backend-tests.md#4-the-portal](../Testing/01-backend-tests.md#4-the-portal) |
| GW28–GW30 | [Architecture/13-security.md#1-trust-zone-model--threat-assessment](../Architecture/13-security.md#1-trust-zone-model--threat-assessment) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| GW31 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| GW33 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| GW32 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |
| GW34 | [Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19](../Architecture/05-context-gateway.md#2-reads-vs-writes-enforcement-gw15gw19) | [Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation](../Testing/06-security-tests.md#2-policy-bypass-and-privilege-escalation) |

## Related

- [00-index](00-index.md) — all requirement families.
- [traceability](traceability.md) — requirement to chapter and test mapping.
