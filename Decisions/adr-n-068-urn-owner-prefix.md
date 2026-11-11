---
sidebar_position: 69
title: "ADR-N-068: The URN Owner Prefix"
---

# ADR-N-068: The URN Owner Prefix

Date: 2026-11-11  
Status: Accepted  
Decision Makers: product owner (order of 2026-11-11, supervisor session: "urn:ngsi-ld:KeyPerformanceIndicator:sk_bbsk ... is mandatory ... is the owner of the data"; "for the single deployment it is not mandatory"); drafted by worker-t6769 (T-6769)

Every entity URN names the Organization that owns the data: `urn:ngsi-ld:{Type}:{orgId}:{rest}`. This record states the grammar, the map from a domain to the id, who the owner is, and where the prefix is minted and checked. It supersedes the "prefix optional" part of [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) and keeps the rest of it: an entity is still its Context Space and its URN, and nothing derives a space, an Organization or a right from the URN.

## 1. Context

[ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) made every URN shape valid, with `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}` minted on request. With several Organizations on one installation (ADR-N-058) and data shared between them and between platforms (Architecture §26, §45), a reader of a URN cannot tell whose data it is. The owner's order of 2026-11-11 makes the owner part of the id. The Organization id is the verified domain with its labels reversed and joined by `_` ([API/15](../API/15-addresses-v1.md#the-organization-id), EP-186).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | NGSI-LD (CIM 009) asks only for a URI; `{orgId}` sits in the namespace-specific string the standard leaves to the platform. |
| Security by design | **Full** | The prefix is input, validated on write; it never selects a space, an Organization or a right (TEN-02). |
| Multi-tenancy | **Full** | Two Organizations cannot mint the same id: the owner segment differs. |
| Modular design | **Full** | One function maps a domain to an id (`jc_core::names::org_id`); minting and the write check both call it. |

## 3. Decision

### 3.1 Grammar

```text
urn:ngsi-ld:{Type}:{orgId}:{rest}
orgId = the owning Organization's id, [a-z][a-z0-9_-]{1,62} containing "_"
rest  = a non-empty RFC 8141 namespace-specific string
```

Example: `urn:ngsi-ld:KeyPerformanceIndicator:sk_bbsk:bbsk-otvorene-data:kpi-17`. The owner segment is the text between the `{Type}` and the next `:`.

### 3.2 Domain and id

| Domain | Organization id |
|---|---|
| `bbsk.sk` | `sk_bbsk` |
| `bratislava.sk` | `sk_bratislava` |
| `praha.eu` | `eu_praha` |
| `hel.fi` | `fi_hel` |
| `banskabystrica.sk` | `sk_banskabystrica` |

A hostname holds no `_`, so the map is one-to-one in both directions.

### 3.3 The owner

The owner of an entity is the Organization of the Context Space it is written to: the space's Project names it in `spec.organizationRef`, and a Project naming none belongs to the installation's Organization. A shared or federated entity keeps its owner's prefix wherever it is read or copied: a copy into another Organization's space is a new entity of that Organization, minted with its id.

### 3.4 Minting

Every writer that mints ids writes the owner's id:

- a Pipeline mapping reads it with `env("JC_ORG_ID")`, which the runner sets from the project's Organization beside `JC_ORG_DOMAIN`;
- the mappings the Portal generates (space completion, feed shapes, KPI pipelines, the assistant's examples) use `env("JC_ORG_ID")`;
- an Endpoint with `creates.mintIds` mints `urn:ngsi-ld:{Type}:{orgId}:{uuid}` when the check of §3.5 runs.

### 3.5 The write check

A create, an upsert, a batch create or upsert and a temporal upsert through an Endpoint answers `422` with the problem type `urn-owner` and `field: id` when an entity's owner segment is neither the owning Organization's id nor its domain. A batch with one such member is refused whole, as a malformed id refuses it (PF-42). The broker is never asked. The check runs before the broker and after the Policy: a caller the Policy refuses learns that alone. An update, a merge or a delete names an entity that exists already and is not checked.

The domain form (`bbsk.sk:` in the owner segment) is accepted because it names the same Organization one-to-one and every entity minted before this decision carries it; nothing mints it any more.

### 3.6 The deployment setting

`JC_GATEWAY_URN_OWNER_PREFIX` is `enforce` (the default) or `off`. On a deployment whose repository holds one Organization the operator may write `off`: a foreign or missing owner is then accepted. With two or more Organizations the check runs whatever the setting says. Minting writes the prefix in both cases, so a single deployment can grow without re-minting.

### 3.7 What the prefix is not

The prefix is checked, never trusted. The space still comes from the address or the Endpoint, and the Policy of that space decides the write (TEN-02, ADR-N-041 §3.2, §3.5). A URN naming Organization A written by a member of A into a space of Organization B is refused by B's Policy, never accepted because the URN names A.

## 4. Consequences

- `jc-core` gains `names::org_id` and `Urn::owner`; the gateway gains the `urn-owner` problem type and the setting.
- Entities written before this decision keep their ids; their domain-form prefix stays valid. Prefix-less ids already stored stay readable and updatable; a new create of one is refused where the check runs.
- Pipelines in the configuration repositories that mint with `env("JC_ORG_DOMAIN")` keep working; their owners move them to `env("JC_ORG_ID")`.

## Related

- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — identity is (space, URN); its "prefix optional" is superseded here.
- [ADR-N-058](adr-n-058-several-organizations-per-installation.md) — several Organizations per installation.
- [API/15-addresses-v1.md](../API/15-addresses-v1.md) — the Organization id.
- [API/09-errors.md](../API/09-errors.md#urn-owner) — the `urn-owner` problem type.
