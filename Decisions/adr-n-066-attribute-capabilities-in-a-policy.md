---
sidebar_position: 67
title: "ADR-N-066: Attribute Capabilities in a Policy"
---

# ADR-N-066: Attribute Capabilities in a Policy

Date: 2026-11-01  
Status: Proposed  
Decision Makers: product owner (2026-11-01, supervisor session: "I can specify what attributes are allowed, for example, for public temporal or version, because also this version can be public, and also specify what attributes can be shared with these endpoints, and also what attributes can be edited"); drafted by worker-t6336 (T-6336), owner may override

This record decides where the platform says, per attribute, what a caller may do with it: read its current value, read its history, read or keep its versions, see which metadata members, and edit it. It moves that answer into the Policy grant and supersedes the per-Endpoint `spec.audit` and `spec.metadata` of [ADR-N-054 §2.8](adr-n-054-history-versions-provenance-gdpr.md#28-audit-mode-and-the-change-log). Requirements DM-147…DM-153 in [data-models.md §19](../Requirements/data-models.md#19-attribute-capabilities-in-a-policy).

## 1. Context

A Policy grant names a type, its operations (CIM 009 names, [Architecture/04 §1b](../Architecture/04-context-spaces-and-endpoints.md#1b-access-surface-of-an-endpoint-access)) and its attributes. Every capability is decided at a different grain:

- **Current value**: the grant's attribute list, per attribute.
- **History**: per grant, only when the grant names `queryTemporal` or `retrieveTemporal`; every listed attribute or none.
- **Versions**: per Endpoint. The gateway sends `jc-read-versions: true` when any grant gives the caller `readVersions`, with no attribute list, and ADR-N-054 DM-140 refuses versions' actor and provenance on a public Endpoint.
- **Metadata members**: per Endpoint, `spec.metadata` (DM-139), designed and never built in jc-core.
- **Keeping versions**: per Endpoint, `spec.audit: changes` (DM-136), or per request, `JC-Record: version` ([ADR-N-054 §2.9](adr-n-054-history-versions-provenance-gdpr.md#29-versions-on-request)).
- **Editing**: per grant, the write operations it names, for every attribute it lists.

The owner wants one matrix: a public Endpoint that shows the history and the versions of `name` but only the current value of `pm10`, and an internal grant that edits `name` but not `pm10`. Today that takes two Endpoints, and a public version chain cannot be served at all.

## 2. Decision

### 2.1 One block per grant: `information[].attributes`

Each `information` entry of a Policy grant (and of each rule of `rules[]`, ADR-N-057) MAY carry `attributes`, a map from an attribute name, or `*` for every attribute the entry reaches, to that attribute's capabilities:

```yaml
apiVersion: joinedcontext.com/v1
kind: Policy
metadata: { name: public-air }
spec:
  contextSpaceRef: { name: air }
  assigner: did:web:banskabystrica.sk
  assignee: { kind: role, id: public }
  operations: [retrieveOps, queryTemporal, retrieveTemporal]
  actions: [readVersions]
  information:
    - entities: [{ type: AirQualityObserved }]
      propertyNames: [name, pm10, location]
      attributes:
        "*": { history: false }
        name: { history: true, versions: [read] }
```

| Capability | Values | Default when unset | Enforced by |
|---|---|---|---|
| `read` | `true`, `false` | `true` | Antares view rule, attributes per operation |
| `history` | `true`, `false` | `true` when the grant names `queryTemporal` or `retrieveTemporal`, else `false` | Antares view rule |
| `versions` | list of `read`, `keep` | `[read]` when the grant lists the action `readVersions`, else none | gateway header, broker (2.3) |
| `metadata` | list of members (2.4) | the audience's default set (2.4) | gateway strips the rest |
| `write` | list of `update`, `append`, `delete` | each kind the grant's write operations name | Antares view rule |

An attribute's entry falls back field by field: a field it leaves unset takes the `*` entry's field, then the default above. A grant without `attributes` behaves exactly as today, so no seed and no existing Policy changes reach (DM-147).

### 2.2 The block narrows, never widens

Operations and actions still grant; the block only takes away, per attribute. A capability the grant's operations do not give is refused when the Policy is planned, naming the field: `history: true` without a temporal retrieve operation, `versions: [read]` without the action `readVersions`, `versions: [keep]` or any `write` without a write operation (DM-148). Deny by default holds per capability: nothing the grant does not name is reachable through the block.

A caller holding several grants on one type gets the union per attribute and per capability; a prohibition takes away per capability the same way (GW4).

An attribute key MUST be one the entry lists in `propertyNames` or `relationshipNames` (any name when both lists are empty) or `*`. The plan-time lint (Portal, `jcctl lint`) also refuses a key the space's model does not declare for any type of the entry, because only it holds the model.

### 2.3 Versions per attribute, readable and enforceable

**Reading.** The gateway sends `jc-read-versions` with the list of attributes whose `versions` holds `read` (or `*`), instead of `true`. The broker answers `versions=all` only for the attributes the list names; a read asking versions of any other attribute answers `403` naming the attribute (DM-149). The gateway strips `jc-read-versions` from every client request, as it does today.

**Keeping.** `versions: [keep]` makes the gateway mark every allowed write that touches that attribute with its audit mark (`JC-Provenance-Audit: changes`, ADR-N-054 §2.8), whatever the client sends. An audit the writer can skip is no audit. `JC-Record: version` (§2.9) stays as an extra request on top (DM-150).

**Public versions.** A grant to `role: public` MAY hold `versions: [read]`. A public version answer carries the value, `instanceId`, `supersededAt`, `provenance.writtenAt`, `provenance.operation`, `provenance.organization` and `provenance.actorKind`. It carries `provenance.reason` only where the attribute's `metadata` lists `reason`, because the free text a steward typed can name a person. It never carries `provenance.actor` or any other provenance member: an actor is a person's Keycloak `sub` or a client id (DM-140 kept, DM-151). The versions of an attribute the model classifies as personal data (ADR-N-054 §2.6) are never public.

### 2.4 Metadata members per attribute

`metadata` lists the members passed for that attribute on every read, current, history and versions alike: `observedAt`, `unitCode`, `createdAt`, `modifiedAt`, `modifiedBy.organization`, `modifiedBy.actorKind`, `modifiedBy.actor`, `provenance`, `reason`. Defaults: a public grant passes `observedAt`, `unitCode` and `modifiedAt`; any other grant also `modifiedBy.organization` and `modifiedBy.actorKind`. A member not listed is stripped from answers, notifications and exports, and a `q` or `orderBy` on it answers `400` (DM-139). A public grant listing `modifiedBy.actor` or `provenance` is refused (DM-140).

### 2.5 What this supersedes

- **`spec.audit` of an Endpoint** (ADR-N-054 §2.8, DM-136) becomes `versions: [keep]` on the `*` entry of the Endpoint's write grants. The Portal migrates an Endpoint with `spec.audit: changes` by writing that entry into its grants in the same Change; the gateway reads `spec.audit` for one release more, then the field is refused.
- **`spec.metadata` of an Endpoint** (ADR-N-054 §2.8, DM-139) was never built; this block replaces it and the field is not added.
- **`readVersions` as an Endpoint-wide switch** ends: the action stays the ceiling, the block decides per attribute.

There is one place per question: the Policy grant. The Endpoint keeps its audience, its representations and its projection (`projection.hiddenAttributes`, EP-61), which still removes an attribute for every grant.

### 2.6 The Portal editor

The Policy form shows the block as a table per `information` entry: one row per attribute the model declares for the entry's types, plus `*`; columns read, history, versions, metadata and edit. A cell the grant's operations cannot give is disabled with the reason ("needs retrieveTemporal"), and each column header carries a hint with an example.

Decided (worker-t6336, owner may override): the block lives in `information[]`, beside the attribute lists it qualifies, because a grant reaching two types can then give them different capabilities; options: a top-level `attributes` on the grant (one matrix for every type the grant reaches), capabilities on the Endpoint (two places again).

## 3. Alternatives considered

- **Keep per-Endpoint settings and add more of them.** Rejected: one space has several Endpoints and several grants per Endpoint; the same attribute would need the same answer in each, and a mismatch is a leak.
- **A capability that widens the grant** (`history: true` alone grants temporal reads of that attribute). Rejected: two places then grant, and a reader of the operations list no longer knows the ceiling.
- **A separate `AttributePolicy` kind.** Rejected: a second kind needs its own lifecycle, approval lane and access-document section for what is a property of one grant.

## 4. Consequences

- jc-core: `RegistrationInfo.attributes` with its validation and JSON schema (T-6336).
- Gateway and Antares: the view compiler turns the block into per-operation attribute rules; `jc-read-versions` carries an attribute list; the gateway strips metadata per attribute and marks writes of `keep` attributes (T-6338).
- Portal: the matrix editor, the plan-time model check and the `spec.audit` migration (T-6339).
- The access document (Architecture/04 §1b) lists the capabilities per attribute in each grant entry, so an App or an agent knows before asking whether a history or a version read will pass.

## Related

- [ADR-N-054 §2.4, §2.8, §2.9](adr-n-054-history-versions-provenance-gdpr.md) — versions, audit mode and versions on request; §2.8's `spec.audit` and `spec.metadata` are superseded here.
- [ADR-N-057](adr-n-057-policy-rules-policy-refs-authzen.md) — `rules[]` of a Policy, which carry the block per rule.
- [Architecture/04 §1b](../Architecture/04-context-spaces-and-endpoints.md#1b-access-surface-of-an-endpoint-access) — the access document.
- [Requirements/data-models.md §19](../Requirements/data-models.md#19-attribute-capabilities-in-a-policy) — DM-147…DM-153.
