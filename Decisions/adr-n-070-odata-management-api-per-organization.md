---
sidebar_position: 71
title: "ADR-N-070: OData as the Management API, One Service per Organization"
---

# ADR-N-070: OData as the Management API, One Service per Organization

Date: 2026-11-12  
Status: Proposed  
Supersedes: [ADR-N-063](adr-n-063-one-api-style-no-graphql.md) for the control plane (its option B, §3.2 and the last bullet of §5); its data-plane, agent and no-GraphQL decisions stand  
Decision Makers: product owner (2026-11-08: "all APIs ... should be odata"; 2026-11-12 supervisor session: "one task ... based on the architecture and multi organization to rewrite professionally to odata, full frontend, backend, e2e test", "with proper policies"); drafted by worker-t6809 (T-6809), owner may override

This record makes OData 4.01 the one API of the control plane: every Organization is one OData service at `/{org}/api/v1/`, generated from the operation registry, read as entity sets and written only through actions that open, plan or decide a reviewed Change. [API/13](../API/13-api-conventions.md) carries the rules in detail and [API/15](../API/15-addresses-v1.md) the address. The research that compared OData with GraphQL is [Research/next-platform/08](../Research/next-platform/08-management-api-and-testing.md).

## 1. Context

- **Two query styles.** The Portal serves about 280 REST route strings and its UI calls about 400 distinct `/api/v1` paths (jc main `75e834b`, 2026-11-12). Lists page three ways and filter four ways (ADR-N-063 §1); API/13 unified the parameters but each route is still learned one by one.
- **OData is already built here.** Antares ships `odata-url` (a bounded URL parser), `odata-csdl`, `odata-json` and `odata-table` (one evaluator over memory, Postgres and Git sources, T-6642, T-6659). The Portal serves one OData service per project from the operation registry (`src/api/odata.rs`, T-6632, T-6655), the SDK grid reads it (T-6644) and the Endpoints list draws from it (T-6645). shako, the forge, answers every Portal call over OData (`crates/shako/PORTAL-ODATA.md`).
- **The reason ADR-N-063 gave.** It refused OData on configuration because "OData's metadata and batch model do not fit Git-backed reviewed writes". That holds for OData's direct writes (`POST` to a set, `PATCH`, `PUT`, `DELETE` of an entity, `$batch` change sets): each assumes the write lands when the request returns. A configuration write here is a Change that a person or a rule approves later. OData's actions fit it: an action is a named operation with typed parameters and a typed result, so `propose` returning a Change is an ordinary action.
- **Several Organizations per installation** ([ADR-N-058](adr-n-058-several-organizations-per-installation.md)). API/15 fixes `https://{host}/{org}/api/v1/` as the management API's root and its payload as OData.

## 2. Decision

1. **One service per Organization.** The service root is `/{org}/api/v1/` (API/15 §2): the service document there, the model at `$metadata` (CSDL XML, and CSDL JSON for `?$format=application/json` or `Accept: application/json`). The Organization comes from the `/{org}/` path segment or from the host row of a bound host, decided once per request; never from a header, a query option, a key value or a URN ([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md), ADR-N-058). The per-project service `/api/v1/projects/{project}/odata/` stays as an alias of the project's navigations until the API/10 notice ends.
2. **Reads are entity sets and singletons.** `projects` is an entity set keyed by `name`. Each project-scoped kind is a navigation of a project, `projects('{project}')/endpoints('{name}')`, which key-as-segment addressing writes as `projects/{project}/endpoints/{name}`, today's REST path. Each kind is also an organization-wide set keyed by `(project,name)`, `endpoints(project='air',name='counters')`, for the organization pages (PF-61). Organization-scoped kinds (`roles`, `rolebindings`, `groups`, `members`) are sets of the service; the Organization and the caller (`me`) are singletons. Set names are the kind's REST plural, so the path shape does not move.
3. **Writes are actions that open a Change.** There is no `POST` to a set, no `PATCH`, `PUT` or `DELETE` of an entity, and no deep insert: each answers `405` with an error that names the action to call. A write is an action whose name is the registry operation that runs it: bound to the entity it changes when one exists (`…/endpoints('counters')/JoinedContext.Portal.propose_update`, `…/propose_delete`, `changes('42')/JoinedContext.Portal.approve`, `…/reject`, `…/apply`), unbound for a create (`projects('air')/JoinedContext.Portal.propose_create`). Each returns the Change it opened or decided. `dryRun` is a parameter of each propose action and answers the plan without opening a Change (API/13 §5). Lanes, four-eyes and auto-approval run unchanged, inside the operation ([PF-52](../Requirements/platform.md), PF-58, PF-70, PF-71).
4. **Concurrency.** Every entity carries `@odata.etag`, the strong ETag REST answers today (SHA-256 of the manifest without `status`; a Change's ETag is its head commit). A bound action that changes an existing entity, or decides a Change, requires `If-Match`: absent is `428`, stale is `412` with the current ETag, and no Change is opened. A create takes none. The ETag is compared only against an entity the caller may read; otherwise the action answers `404` as an unknown key does.
5. **Query options.** Every entity set honours `$filter`, `$select`, `$orderby`, `$top`, `$skip`, `$count` (and `/$count`), a key, `$expand` of one level on a navigation `$metadata` declares, and server-driven paging. The server refuses, and never ignores:
   - `501`: `$search`, `$apply`, `$compute`, `$levels`, `$index`, `$schemaversion`, `$deltatoken`, delta links, `$batch` (the endpoint exists only to say so), function or action imports the model does not declare, and any OData feature outside this list;
   - `400`: `$expand` deeper than one level or on a property that is no navigation, `$top` above 1000, an unknown or repeated system query option, a property, function or type the caller's `$metadata` lacks (a hidden attribute is no property, so a `$filter` on it is the same `400` as a misspelt one and never an oracle), an expression past the parser's limits (length 4096, 128 nodes, depth 16, 100 values in `in`, 4 `$orderby` items);
   - `406`: a `$format` or `Accept` other than JSON for data, XML or JSON for `$metadata`.
6. **Paging cap.** A page holds at most 1000 rows; `Prefer: odata.maxpagesize` lowers it. `@odata.nextLink` carries a `$skiptoken` signed for the caller, the set and the query it was made for, so it cannot be edited into another query or replayed by another caller. One request evaluates at most 10,000 readable rows; past that the answer is `400` asking for a narrower `$filter`, never a cut set.
7. **Errors.** An OData request gets the OData error object, `Content-Type: application/json`, with the Problem Details members of [API/09](../API/09-errors.md) inside it: `{"error": {"code": "precondition-failed", "message": "…", "target": "spec.audience", "details": [ … ], "type": "…", "title": "…", "status": 412}}`. `code` is the problem type's last segment, so a client branches on it; `message` says what the caller can do next and never echoes a secret. A REST compat request keeps `application/problem+json` (RFC 9457) as today.
8. **Policies decide every set, property and action.** One authorization path serves OData, REST compat and MCP: the registry's `Caller::grants` and `Effective::may` / `Effective::may_read_manifest`, before any query option is read.
   - Roles and RoleBindings at installation, organization and project scope (PF-56), `projects.visibility` (PF-61), `projects.creation` (PF-65) and organization members' read of internal datasets ([ADR-N-067](adr-n-067-organization-members-read-internal-datasets.md)) decide which rows a set holds. A set never lists, counts or expands a row of another Organization or one the caller may not read: `$count` counts readable rows, an unreadable key is `404`.
   - An Endpoint Policy and its attribute capabilities ([ADR-N-066](adr-n-066-attribute-capabilities-in-a-policy.md)) decide what a set showing data or Endpoint metadata answers; the anonymous caller sees only what an Endpoint with `spec.audience: public` publishes (PF-71) and gets `401` on everything else, `$metadata` included.
   - A scoped connector token ([ADR-N-064](adr-n-064-scoped-connectors.md)) sees and calls only its project or segment.
   - People data is minimised ([ADR-N-061](adr-n-061-group-members-without-personal-data.md)): `members` carries no e-mail or personal property for a caller without `people-admin`, in `$metadata` and in rows.
   - `$metadata` is built per caller: it lists only the sets, properties, navigations and actions the caller may use, so a viewer's model holds no write action.
   - An action on `Role`, `RoleBinding`, `Policy` or the `Organization` opens a red-lane Change that an `org-admin` other than its author approves (PF-58).
9. **MCP calls the same operations.** A `tools/call` runs the registry operation the matching OData request runs, with the same Organization rule and the same checks.
10. **REST stays as compat, frozen.** Today's REST routes stay thin wrappers over the same operations and answer today's bodies until an [API/10](../API/10-api-change-policy.md) notice ends them. Under `/{org}/api/v1/` a request is OData when it sends `OData-Version` or `OData-MaxVersion`, any `$` system query option, or names `$metadata`, the service document or an action; otherwise it is a REST compat request. Answers carry `Vary: OData-Version, OData-MaxVersion`. No route, parameter or body is added to REST.

## 3. Alternatives considered

- **Keep ADR-N-063 (REST for configuration, OData for data only).** Two query languages for one client, and every new kind adds REST routes the UI learns by hand. Refused by the owner's order.
- **OData with direct writes** (`PATCH` merges the manifest, `$batch` change sets). Each direct write would have to return `202` and a Change in place of the entity the standard promises, so standard clients would misread every write, and a change set would mix approved and pending writes. Refused; actions say what happens.
- **One service per project** (T-6655's shape). An organization page (every Endpoint, every Change waiting for me) would need one call per project, and `$expand` could not cross a project. Kept only as an alias.
- **GraphQL.** Refused again for ADR-N-063's reasons: a second authorization layer per field, client-set query cost on one node, writes that are Git reviews.

## 4. Security

- No write outside a reviewed Change, and no OData verb that pretends otherwise.
- `$batch` off, `$expand` one level, `$top` and rows per request capped, parser limits fixed: a request's cost is set by the server.
- The Organization is decided once from the path or the host; a key, a URN or a header naming another Organization reaches nothing (`404`).
- Per-caller `$metadata` is the field-level control: a property the caller may not read does not exist for them, in `$select`, `$filter`, `$orderby` and `$expand` alike.
- Every OData route has its line in the Portal's `authz_matrix` and `route_coverage` tests; a new action without one fails CI.

## 5. Consequences

- API/13 §2a describes the service; API/15 §4 points here.
- The work is split in slices (T-6809 and its follow-ups): the per-project service ported into the jc monorepo and widened to `/{org}/api/v1/` with per-caller `$metadata`, the bound actions with `If-Match`, the policy parity tests (every PF-56 role × every set and action equals the REST answer), the typed SDK client generated from `$metadata`, every UI list, detail and form moved onto it, the REST fetches removed from `ui/src` (a gate test holds the count at 0 outside the compat tests), and the e2e journeys in host and path mode.
- The per-project `endpointList` set's `PATCH` and `DELETE` by key (T-6645) become `propose_update` and `propose_delete` actions; the old verbs stay until the UI moves.
- A request for a new REST route, for GraphQL or for OData direct writes is answered with this record.

## Related

- [ADR-N-063](adr-n-063-one-api-style-no-graphql.md): the record this one supersedes for the control plane.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md): the operation registry the service is generated from.
- [ADR-N-004](adr-n-004-configuration-as-code-and-gitea.md): configuration in Git, writes as reviewed Changes.
- [ADR-N-058](adr-n-058-several-organizations-per-installation.md): several Organizations per installation.
- [API/13](../API/13-api-conventions.md): the conventions, §2a the OData service.
- [API/15](../API/15-addresses-v1.md): the address of the service root.
