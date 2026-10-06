---
sidebar_position: 42
title: "ADR-N-041: An Entity Is Its Context Space and Its URN; the URN Prefix Is Optional"
---

# ADR-N-041: An Entity Is Its Context Space and Its URN; the URN Prefix Is Optional

Date: 2026-10-06  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-06, T-3080)

## 1. Context

Until now every entity id had to be `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}` (PF-10,
PF-42, ADR-N-002 §3, the legacy ADR 001 "Razidlo/Evidencia" scheme). The gateway refused any
other id with 400, the URN was said to resolve to its space, a preview rewrote the `{space}`
segment of every URN, and an import into another project rewrote it again.

The owner's order of 2026-10-06: "the same URN can be in multiple context spaces and projects —
change this whole logic; there CAN be prefixes but they are NOT required." Real data arrives with
ids of its own (FIWARE `urn:ngsi-ld:WeatherObserved:Helsinki-001`, a publisher's station code),
the same entity is copied into several spaces and projects (a copy, a preview, a KPI space), and
an id that has to be rewritten every time it moves is an id nobody can keep.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | NGSI-LD (CIM 009) asks only that an id be a URI; the tenant scopes it. The platform stops adding a rule the standard does not have. |
| Technological consistency | **Full** | The broker already keeps one id space per tenant (NGSILD-Tenant); a space is a tenant (SP-05). |
| Security by design | **Full** | §3.5: the authority the prefix seemed to carry was never in the prefix; the space, the organization and every right come from the path and the Policy. |
| Modular design | **Full** | Minting moves to one place per writer (a mapping's or an app's mint option, §3.4). |
| Multi-tenancy | **Full** | Two spaces holding the same URN hold two entities; nothing done in one reaches the other. |

## 3. Decision

### 3.1 Identity

An entity's identity is the pair **(Context Space, URN)**. The URN is any NGSI-LD entity URN:
`urn:ngsi-ld:` followed by the entity's `{Type}` (the type it declares, as today), a colon, and a
non-empty RFC 8141 namespace-specific string of at most 256 characters. The
`{orgDomain}:{space}:{localId}` tail of the old scheme is one valid shape among others, still
minted when a writer asks for it (§3.4), never required. The same URN may exist in any number of
spaces and projects; each is its own entity, and a create, update or delete in one never touches
another. Existing prefixed data stays valid as it is: no migration.

### 3.2 Where the space comes from

Always from the address, never from the URN:

| Surface | The space is |
|---|---|
| `/cs/{space}/ngsi-ld/v1/…` | the path's `{space}` (SP-01) |
| `/api/endpoint/{slug}/…` and an Endpoint's MCP façade | the Endpoint's `contextSpaceRef` |
| the hub MCP (`endpoint` argument) | the named Endpoint's space |
| the Portal's entity views, the App SDK, exports | the space or Endpoint the request names; an entity reference carries `(space, urn)` |
| CKAN DataStore, the catalogue | the dataset's space; a row is keyed by `(space, urn)` |

The stable address of an entity is `/cs/{space}/ngsi-ld/v1/entities/{urn}` (SP-02). There is no
URN-only resolver: a URN without a space names no single entity.

### 3.3 Relationships into another space

A Relationship's `object` is a URN of the **same space** by default. A link into another space
says so with the relationship's sub-property `targetSpace` (a Property whose value is the target
Context Space name): `{"type":"Relationship","object":"urn:ngsi-ld:School:zs-hlinku","targetSpace":{"type":"Property","value":"skoly"}}`.
The gateway reads the target through that space's Policy like any other read (R-family rules);
a prefix in the target URN is not a space hint.

### 3.4 Minting

A writer that mints ids chooses one of three options, declared where it writes (a Mapping's or
Pipeline's `output.id`, an App's served configuration, a Blueprint):

- `prefixed` (the default, today's behaviour): `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`,
  with `{orgDomain}` from `JC_ORG_DOMAIN` (PF-44);
- `keep`: the source's own id, used as it is when it is already an NGSI-LD URN of the entity's
  type, else `urn:ngsi-ld:{Type}:{sourceId}` with the source id percent-encoded to RFC 8141;
- `template`: a template over the record's fields, the output a valid URN or the record refused.

A preview (CC-78) renders its own prefixed project and space names; the URNs inside stay as
written, because the preview space is a different space. An import into another project
(MF-22) keeps every URN as written for the same reason.

### 3.5 What replaces the prefix checks

PF-42/PF-43 made the gateway refuse an id naming another organization or another space. That
check protected nothing the address does not already protect: a writer reaches only the space
its path and Policy allow, and the URN gives it no other. The rule now is the stronger one that
was implicit: **no surface may derive a space, an organization or a right from URN segments**
(PF-42). The gateway still refuses an id that is not an NGSI-LD URN, or whose `{Type}` differs
from the entity's `type` (PF-43). A federated read keeps the remote URN as it is; a local copy is
a write into a local space through a Mapping, under that space's Policy.

A Policy may still name ids or an `idPattern` as its target inside its own space (GW16): that is a
target the steward writes, read against the URN as a string, not a space, organization or right
the platform infers from the URN's segments.

### 3.6 Registrations and subscriptions

A Context Source Registration routes by its Endpoint and space, not by an `idPattern` anchored to
a prefix; `idPattern` stays an optional filter (R33). `GET /entities/{id}` is answered from the
addressed space and its registrations, never routed by URN segments (R34). A relationship's
generated JSON Schema patterns `object` on the target's type only (DM-72). A declared subscription keeps its deterministic
id (`urn:ngsi-ld:Subscription:{orgDomain}:{space}:{name}`, the `prefixed` shape) because the
reconciler upserts it by that id.

### 3.7 Superseded

The URN paragraph of ADR-N-002 (§3, "The issuer segment of the entity URN…") and the legacy ADR
001 scheme as the rule. The rest of ADR-N-002 stands. Changed requirements: PF-10, PF-42,
PF-43, PF-44, SP-02, CC-10, CC-78, MF-22, SDK-05, GW16, R31, R33, R34.

## 4. Consequences

- `jc-core` validates the NGSI-LD shape only and parses the old prefix as optional; callers pass an
  entity reference `(space, urn)` (T-3081).
- The gateway and the broker paths stop reading space or rights from URN segments (T-3082);
  pipelines and mappings gain the mint option (T-3083); the Portal and the App SDK carry the space
  with every reference (T-3084); CKAN and exports key rows by `(space, urn)` (T-3085); one
  end-to-end proof holds the same URN in two spaces and two projects (T-3086).
- Tests that asserted the refusal of a foreign prefix now assert that the URN carries no
  authority: a write of `urn:ngsi-ld:Device:other.org:other-space:1` into a space the writer may write
  lands in that space and nowhere else.

## Related

- [ADR-N-002](adr-n-002-context-space-and-endpoint-model.md) — the space and Endpoint model whose URN paragraph this replaces.
- [Architecture/03-domain-model.md](../Architecture/03-domain-model.md#3-identity-and-urn-specification) — the identity section, rewritten to this decision.
- [Requirements/platform.md](../Requirements/platform.md) — PF-10, PF-42…PF-44.
- [Requirements/space-surface.md](../Requirements/space-surface.md) — SP-01, SP-02.
