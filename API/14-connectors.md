---
sidebar_position: 15
title: "Connectors API and the Generic Tool Set"
---

# Connectors API and the Generic Tool Set

A connector is a grant one person gives one AI client over part of the platform ([ADR-N-064](../Decisions/adr-n-064-scoped-connectors.md), [Architecture/07 §11](../Architecture/07-agents-and-mcp.md#11-scoped-connectors)). This page is the contract: the Connector record, the routes that manage it, the MCP server at `/c/{id}` and every tool it serves (AG-142…AG-157). The administrator's ceiling, `kind: DelegationPolicy`, is a Git manifest described in [Development/04](../Development/04-manifest-kinds.md#delegationpolicy).

## 1. The Connector record

The Portal stores connectors in its database, one owner each, never in Git (AG-142). The resource API's `{project}` path does not apply: a connector belongs to a person and may span projects.

```json
{
  "id": "c7m2q4x5k3w5r7t2v6y4n7p3ha",
  "name": "air-pipelines-in-claude-code",
  "owner": "3f1c9a52-6b1e-4d0a-9a4e-0c8d1b7e2f10",
  "segments": ["pipeline"],
  "scope": [
    { "project": "air", "pipeline": "*", "access": "write" },
    { "project": "air", "endpoint": "air-quality-sensors-2026-public", "access": "read" }
  ],
  "writes": true,
  "expiresAt": "2026-11-27T00:00:00Z",
  "allowedClients": ["https://claude.ai/oauth/claude-code-client-metadata"],
  "clientIsBoundary": false,
  "state": "active",
  "createdAt": "2026-10-28T19:00:00Z",
  "lastUsedAt": null,
  "url": "https://portal.{domain}/c/c7m2q4x5k3w5r7t2v6y4n7p3ha",
  "limits": { "callsPerMinute": 60, "parallelCalls": 4, "resultBytes": 1048576 }
}
```

| Field | Rule |
|---|---|
| `id` | 26 random base32 characters (`a-z`, `2-7`), set by the Portal. Not a secret; useless without the owner's token. |
| `name` | DNS-1123 label, unique per owner, at most 63 characters. |
| `segments` | One or more of `data-read`, `context`, `pipeline`, `access`, `publish`, `apps`, `operate`, `admin` (Architecture/07 §11). |
| `scope[]` | Each item names a `project` and at most one of `space`, `endpoint`, `pipeline`, the item's name or `*` for every one of that kind the owner may reach in the project; `access` is `read` or `write`. A `write` item requires `writes: true`. An empty scope is refused. |
| `writes` | `false` by default. While false the token is read-only below the tools (AG-148). |
| `expiresAt` | Required; at most the DelegationPolicy's `maxExpiry` from now, and never more than 365 days. |
| `allowedClients` | Optional list of OAuth client ids (a CIMD URL or a realm client id). Absent: any client of the realm. |
| `clientIsBoundary` | Read-only. `true` only when every allowed client is one whose redirect URIs no local program can use (claude.ai, ChatGPT); `false` for Claude Code and `mcp-local`, which the Portal labels "intended for", never "only" (AG-153). |
| `state` | Read-only: `active`, `pending` (above the ceiling, waiting for an administrator, AG-150), `expired`, `revoked`. |
| `aboveCeiling` | Read-only, present on a request that was queued: one line per field it asked above the owner's ceiling, such as `writes: DelegationPolicy analysts-doprava lets a connector read only`. |
| `approval` | Read-only, `{by, at}` once an administrator approved the request: the approver's Keycloak user id and the time. |
| `narrowedBy` | Read-only, on an `active` connector: what the owner's ceiling takes from it today, one line per part (`segment pipeline`, `project skolstvo`, `client mcp-local`). Calls run without those parts; the Portal shows each as a "narrowed by policy" mark. Empty when the connector fits. |
| `limits` | Read-only: what the connector may spend (§3.1). |

A connector above the person's DelegationPolicy ceiling is either refused with `403` naming the field or, when the policy queues requests, stored as `pending` until an administrator approves it in the Portal.

The ceiling is read on every call, not stored with the connector: a policy an administrator narrows (a segment, a project, an Endpoint, a client, a shorter `maxExpiry` counted from the connector's creation) narrows every existing connector of the people it binds at their next call. An approved request keeps what it asked only while a DelegationPolicy binding its owner still has `aboveCeiling: queue`; a policy turned to `refuse`, or one that no longer names the owner, takes the approval back at the next call (Decided, worker-t5953, owner may override: the administrator's lever over an approval is the policy itself; options: approvals held forever until revoked, or re-approval per policy change).

## 2. Managing connectors

Contract for T-5950 and T-5951. The routes are not in the Portal's published OpenAPI yet, so they are listed here as a table; the branch that builds them turns the table into a route block, which `verify-openapi-snippets.py` then holds to the specification.

| Method | Path | What it does |
|---|---|---|
| `GET` | `/api/v1/connectors` | the caller's connectors; an administrator adds `?owner=` to read one person's |
| `POST` | `/api/v1/connectors` | create; `?dryRun=All` validates only |
| `GET` | `/api/v1/connectors/{id}` | one of the caller's connectors |
| `PATCH` | `/api/v1/connectors/{id}` | edit segments, scope, writes, expiresAt, allowedClients (JSON merge patch) |
| `DELETE` | `/api/v1/connectors/{id}` | revoke: state `revoked`, the next call through it is refused |
| `GET` | `/api/v1/connectors/{id}/activity` | the audit rows of this connector (AG-147) |
| `GET` | `/api/v1/connectors/pending` | an administrator reads every `pending` connector, oldest first |
| `POST` | `/api/v1/connectors/{id}/approve` | an administrator approves a `pending` connector |

Every route takes the person's Portal session or a bearer whose audience is the Portal. A connector token is refused on every one of them with `403`: a connector cannot create, widen, approve or revoke connectors (AG-151). An administrator here is a person who administers the organization (`approve` and `delete` on `RoleBinding`, PF-03) or may approve a `DelegationPolicy` change. `approve` requires the approver to hold every right the connector asks for (`within_own_rights`, PF-51: `read` on each kind its segments reach in each scope project, `propose` where an item writes) and refuses the owner approving their own request; `pending` and `approve` refuse an AI client's token (`mcp-local`, `mcp-hub`, `mcp-mobile`) with `403`.

Another person's connector answers `404`, the same body as an id that does not exist.

## 3. The MCP server at `/c/{id}`

| Method | Path | What it does |
|---|---|---|
| `POST` | `/c/{id}` | Streamable HTTP, MCP protocol `2026-07-28` |
| `GET` | `/c/{id}/.well-known/oauth-protected-resource` | RFC 9728 metadata, `resource` = `https://portal.{domain}/c/{id}` |

An unauthenticated call answers `401` with `WWW-Authenticate: Bearer resource_metadata="https://portal.{domain}/c/{id}/.well-known/oauth-protected-resource"`. The metadata names the organization's realm as the authorization server; the client asks for a token with `resource=https://portal.{domain}/c/{id}` (RFC 8707).

Each call is judged in this order, and the first failure answers (AG-143, AG-144):

| Check | Failure |
|---|---|
| token signature, issuer = the organization's realm, not expired | `401` |
| audience = this connector's address | `401` |
| connector exists and `sub` = its owner | `404`, the body of an unknown id |
| connector `active` (not pending, expired or revoked) | `403` naming the state |
| `azp` in `allowedClients`, when set | `403` naming the client |
| the tool is in the effective rights | `403` naming the tool |
| the call's target (project, space, Endpoint, pipeline, kind) is in the effective rights | `403` naming the target |
| per-connector and per-person limits | `429` with `Retry-After` |

The effective rights are the DelegationPolicy ceiling ∩ the owner's live rights ∩ the connector's segments and scope, computed on every call; `tools/list` lists exactly the tools they reach. Every call, allowed or refused, writes one audit row: connector, person, client, tool, target, verdict, duration. The row never holds a token, a header or a tool's input values.

A tool error answers `isError: true` with the problem document as structured content, so a model can correct its input and call again (AG-146).

### 3.1 Limits

The Portal counts each call on the verified token's `sub` and the connector id of the path, never on a header. The person's budget holds over all their connectors and `/api/v1/mcp` together, so a second connector adds no calls.

| Limit | Per connector | Per person | Past it |
|---|---|---|---|
| calls a minute | 60 | 120 | `429` problem+json, `Retry-After` = seconds until the window opens, `detail` naming whose limit |
| calls answered at once | 4 | 8 | `429` problem+json, `Retry-After: 1` |
| bytes of one tool answer | 1 MiB | 4 MiB (the route) | tool error with status `413`, `detail` naming what to narrow (`limit`, `attrs`, one name) |

A DelegationPolicy may lower these (AG-150); `limits` on the record shows the values in force. Each refusal is an audit row (`refused: rate limit`, `refused: parallel calls`, `refused: result size`), so the My connectors page shows it. The Portal assistant's model spend is capped per person per day by the agent proxy (`JC_DAILY_TOKENS_PER_PERSON`, AG-97).

## 4. The tool contract

Every tool's input is a JSON Schema 2020-12 object with `additionalProperties: false`; every output is structured content beside a short text summary. `kind` is a kind of the platform registry (Development/04 §2) and `project` a project slug. Names are DNS-1123 labels.

### 4.1 Errors

Every tool answers its errors as `application/problem+json` (API/09) with these types:

| Status | `type` slug | When |
|---|---|---|
| 400 | `invalid-request` | the input breaks the tool's schema; `errors[]` names each `path` |
| 403 | `forbidden` | the tool, kind or target is outside the effective rights; `detail` names which |
| 404 | `resource-not-found` | the object does not exist or the caller may not read it (one answer for both) |
| 409 | `conflict` | `apply_change` on a plan whose base moved, or a plan already applied |
| 422 | `unprocessable` | the manifest is well-formed but fails a check; `errors[]` holds `{path, message}` per finding |
| 429 | `too-many-requests` | a limit was reached; `Retry-After` set |

### 4.2 Reading

| Tool | Input | Output | Notes |
|---|---|---|---|
| `get_schema` | `{kind}` | `{kind, schema}`: the kind's JSON Schema | Every kind of the registry; no rights needed beyond the connector's. |
| `list` | `{kind, project?, space?, q?, limit? (1-200, default 50), cursor?}` | `{items[{kind, name, project, title, state}], nextCursor?}` | Only objects in the effective scope. `q` matches name and title. |
| `get` | `{kind, project, name}` | `{manifest, etag, status}` | `secretRef` names only, never a resolved value (AG-155). |
| `query_data` | `{project, endpoint, type?, id?, q?, attrs?, georel?, geometry?, coordinates?, temporal? {timerel, timeAt, endTimeAt?, lastN?}, count?, limit? (1-1000), cursor?}` | `{entities[], total?, nextCursor?}` | Reads one Endpoint through the gateway as the owner, with the connector's token; the query language is the Data MCP's (AG-84). Entity text arrives inside the untrusted-data fence (AG-20). |

### 4.3 Writing: plan, then apply

| Tool | Input | Output | Notes |
|---|---|---|---|
| `plan_change` | `{project, changes[1..50]{op: create\|replace\|patch\|delete, kind, name, manifest?, patch?}, workspace?}` | `{planId, baseEtag, expiresAt, diff, verdict {ok, findings[{level, path, message}]}}` | The resource API's `?dryRun=All` for each change (AG-62): every check, nothing saved. A failing check answers `422` with every finding. A plan holds `secretRef` names only. |
| `apply_change` | `{planId}` | `{changeRequest {id, url, lane, state}}` or `{workspaceChange {workspace, id, url}}` | Only a plan this connector made, unchanged, within 30 minutes, with `write` on every item. Never approves: a person approves at `url` (AG-149, AG-151). |

`plan_change` is offered whenever a segment proposes; `apply_change` only when `writes` is true. With writes off a person still sees the plan and applies it in the Portal.

### 4.4 Pipelines

| Tool | Input | Output | Notes |
|---|---|---|---|
| `sample_source` | `{project, datasource \| source {…}, limit? (1-50, default 10)}` | `{rows[], contentType, bytes, truncated}` | Reads through the outbound allow-list; never writes Git, never stores the sample. |
| `try_mapping` | `{project, mapping, input[1..50] \| datasource}` | `{outputs[], errors[{index, message}], verdict}` | Runs the mapping in the pipeline test sandbox (PL-43); writes nothing. |
| `run_pipeline` | `{project, pipeline}` | `{runId, state, url}` | Requires `run` on the pipeline (segments `pipeline`, `operate`); the run writes through its own Endpoint and Policy, never as the connector. |
| `pipeline_logs` | `{project, pipeline, runId?, limit? (1-500, default 100)}` | `{lines[{at, level, step, message}], state}` | Masked as the activity pipeline masks them (OPS-48). |

### 4.5 The Portal assistant's own tools

A Portal conversation is a connector of its person (AG-152) and gets the tools above plus UI actions the browser runs: `navigate {page, params}`, `open_form {kind, project, prefill}`, `highlight {field, message}`, `show_diff {planId}`, `filter_table {query}`. The page validates each against its page list and the kind's form schema and refuses an unknown page or field; none submits, proposes or approves (AG-154).

## Related

- [ADR-N-064](../Decisions/adr-n-064-scoped-connectors.md) — the decision and its threat model.
- [Architecture/07 §11](../Architecture/07-agents-and-mcp.md#11-scoped-connectors) — segments, the per-call check, client binding.
- [API/01 §21](01-portal-api.md#21-operations-and-the-portal-mcp-ag-59-ag-60-ag-61-ag-62-ag-77) — the operation registry and the Portal MCP the tools adapt.
- [API/09](09-errors.md) — the problem document.
- [API/13](13-api-conventions.md) — the list, paging and etag conventions the tools follow.
- [Requirements/agents.md](../Requirements/agents.md) — AG-142…AG-157.
