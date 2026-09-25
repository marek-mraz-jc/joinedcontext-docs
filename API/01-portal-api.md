---
sidebar_position: 2
title: "Portal REST API"
---

# Portal REST API

The Portal REST API provides administrative and platform management capabilities. OpenAPI 3.1 definitions are available at `https://portal.<domain>/api/v1/openapi.json`.

## 1. Standard Headers

- `Authorization: Bearer <jwt>` (Required for all non-public endpoints)
- `Accept-Language: sk, en;q=0.8` (Requests translated titles and descriptions)
- `Content-Type: application/json`

## 2. Error Response Format (RFC 7807)

An error answers `application/problem+json` (`joinedcontext-portal/src/error.rs`):

```json
{
  "type": "https://joinedcontext.com/errors/resource-not-found",
  "title": "Resource Not Found",
  "status": 404,
  "detail": "ContextSpace 'mobility-traffic' does not exist in project 'city-center'"
}
```

`type`, `title` and `status` are always there; `detail` is the one sentence a page shows as it is.
No route sets `instance`: the member stays absent rather than repeating the URL the caller just
called.

One optional member is added to RFC 7807's own: `errors`, a list of strings, present when a single
request violated more than one rule and the caller can act on all of them at once. A form marks
every bad field from it in one pass instead of sending the user round the loop once per mistake
(CC-24). `detail` stays the one-sentence summary, so a client that ignores `errors` still has
something to show.

```json
{
  "type": "https://joinedcontext.com/errors/invalid-request",
  "title": "Invalid Request",
  "status": 400,
  "detail": "the parameters do not match blueprint 'threshold-alert': \"title\" is a required property; \"webhookUrl\" is a required property",
  "errors": [
    "\"title\" is a required property",
    "\"webhookUrl\" is a required property"
  ]
}
```

`type` is `https://joinedcontext.com/errors/{slug}`, and the slug is what a client branches on:

| Slug | Status | What it means |
|---|---|---|
| `invalid-request` | 400 | the body or a parameter is wrong; `errors` carries every violation at once |
| `unauthorized` | 401 | no live session and no accepted bearer token |
| `forbidden` | 403 | the verb the caller's bindings lack, named in `detail` (PF-50) |
| `self-approval` | 403 | the author of a proposal approving their own (CC-41) |
| `resource-not-found` | 404 | not there, or not readable by this caller: one answer for both (R20) |
| `conflict` | 409 | the state moved under the request, or a name is taken |
| `unsupported-media-type` | 415 | a `PATCH` whose content type is neither patch type of section 4 |
| `not-implemented` | 501 | the route exists and this form of it does not, such as an import from a URL |
| `service-unavailable` | 503 | a tier the route needs did not answer: the forge, the database, Model Tools, a runner |
| `internal-error` | 500 | anything else; `detail` says nothing about the cause |
| `rate-limit-exceeded` | 429 | the basemap proxy's own bucket, with the limit in `detail` |

Three answers carry a JSON document of their own instead of a problem, all `application/json`:

- the verdict gate's `409` (sections 4 and 21): `error`, `check`, `reason`, `detail`;
- the routes the operations registry answers directly, `POST …/ops/{name}` and the draft routes
  of section 4: `403 {"error": "forbidden", "role": …}`,
  `422 {"error": "invalid_input", "path": …, "message": …}` and
  `409 {"error": "draft_conflict", "current": …}` (`joinedcontext-portal/src/ops/mod.rs`);
- `POST /api/v1/mcp`, which answers JSON-RPC errors because its clients read that shape
  (section 21).

A client that reads the status code and then `type` or `error` handles all of them.

## 3. Session and Identity (CC-40, CC-42)

Humans reach the portal through the browser, never with a bearer token of their own. The
authorization code flow with PKCE runs server-side and the result is an encrypted session cookie
(`jc_session`, `Secure`, `HttpOnly`, `SameSite=Lax`); a second, deliberately readable cookie
(`jc_csrf`) carries the double-submit token the SPA echoes in `x-csrf-token` on every mutation.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/auth/login?redirect_to=<in-app path>` | starts the code flow; `redirect_to` is honoured only when it is a same-origin path |
| `GET` | `/api/v1/auth/callback` | consumes the code, verifies the ID token against the stored nonce, issues the session |
| `GET` | `/api/v1/auth/me` | the signed-in identity, or `401` `application/problem+json` when there is no live session |
| `POST` | `/api/v1/auth/logout` | clears the session and answers `{ "endSessionUrl": "…" }`; the SPA navigates there itself, because a cross-origin 302 to Keycloak is unreadable to `fetch` |
| `POST` | `/api/v1/auth/backchannel-logout` | Keycloak-initiated logout; revokes every session issued at or before the token's mark |

`GET /api/v1/auth/me` answers with the identity:

```json
{
  "subject": "b7c1e0f4-2c17-4b7c-9a2f-8f0b0f6b3d21",
  "username": "jana.kovacova",
  "email": "aino.virtanen@example.org",
  "name": "Aino Virtanen",
  "roles": ["portal-viewer", "space-editor"]
}
```

- **CC-42** [portal, identity] — `roles` carries the realm roles Keycloak asserts in the ID token
  (`realm_access.roles`), in the order the token lists them, and is `[]` when the token asserts
  none. The UI MUST use it to decide what it renders and enables; it is defence in depth only, and
  the forge and the resource API enforce the same boundaries independently, so a bypassed UI can
  never exceed a user's Git rights.
- **CC-40** [portal, identity] — `subject` is the Keycloak `sub` and is the only durable user key;
  `username`, `email` and `name` are display data and MUST NOT be used for authorization.
- No token is ever returned to the browser and none is written to a log line.

## 4. Resource API (MF-11…MF-15)

Every configuration kind is also served as a resource collection under the same `/api/v1` prefix as the rest of the Portal API (no Kubernetes-style group path in URLs; `apiVersion`/`kind` live only inside the manifest body):

```text
GET    /api/v1/projects/{project}/{plural}            list (labelSelector, fieldSelector, limit, continue)
GET    /api/v1/projects/{project}/{plural}/{name}     one manifest incl. status
POST   /api/v1/projects/{project}/{plural}            create  → 202 + Change (merge request)
PUT    /api/v1/projects/{project}/{plural}/{name}     replace → 202 + Change
PATCH  /api/v1/projects/{project}/{plural}/{name}     application/merge-patch+json or
                                                      application/apply-patch+yaml → 202 + Change
DELETE /api/v1/projects/{project}/{plural}/{name}     → 202 + Change (explicit deletion lane)
POST   /api/v1/projects/{project}/{plural}?dryRun=All validate + plan, no change created
GET    /api/v1/projects                                 the projects this caller may read
GET    /api/v1/blueprints                               the Blueprint catalogue of the organization
GET    /api/v1/endpoints                                every Endpoint of every project the caller may read, each with its project (PF-60, PF-61)
GET    /api/v1/organization/datamodels?search=          every DataModel the caller may read, and matching Smart Data Models entries: what the model and type pickers list (DM-63)
POST   /api/v1/projects                                 open a project → 202 + Change: project.yaml and the creator's steward binding in one merge request (PF-65, PF-66)
GET    /api/v1/projects/{project}                       the project and `status.usage`: what it holds of each quota (PF-73, PF-75)
DELETE /api/v1/projects/{project}                       delete a project → 202 + red-lane Change over everything it holds (PF-77, PF-78)
POST   /api/v1/projects/{project}/duplicate             duplicate a project into a new slug → 202 + Change: its registry entry and the caller's steward binding (PF-89)
GET    /api/v1/projects/{project}/permissions/me        the caller's effective rules here (PF-51, PF-61)
GET    /api/v1/projects/{project}/apps/{name}/me        the caller's roles in one published App, for a fullstack backend (AP-109)
```

`DELETE /api/v1/projects/{project}` proposes one red-lane `Change` whose merge request removes
`projects/{project}/` entirely and, with it, every `RoleBinding` and project `Role` under
`users/` whose scope is the project or one of its spaces: no grant outlives the project it was
written for (PF-77). The `Change` body lists every file, so the approver reads the cascade before
approving it, and the approval is held to `approve` and `delete` on every kind in that list. A
`SharedSpaceReference` in another project pointing at one of this project's Endpoints refuses the
deletion with `409` and names the referencing manifests; removing the reference is that project's
own change. On merge the reconciler drops each space's broker tenant last, after the export the
`Change` body offers (CC-07), retires the endpoint slugs and removes the app builds.

`DELETE /api/v1/projects/org/groups/{name}` works the same way for a `Group` (PF-95): the one
red-lane `Change` removes the group's manifest and, in the same commit, takes the group out of
every `RoleBinding` subject list and every `App.spec.access` entry naming it. A binding left with
no subject is removed, and so is an access entry left with none; a removal that would leave the
organization without an administrator is `409` (PF-03). A binding or an App in a project with a
repository of its own (layout 2) cannot ride in that `Change`, so it refuses the deletion with
`409` naming it; removing the group there is that project's own change.

The name is then reserved for `Organization.spec.projects.nameCooldownDays` (30 days by default,
`0` for none) counted from the commit that removed it, and `POST /api/v1/projects` answers `409`
with the date it becomes free (PF-78).

`POST /api/v1/projects/{project}/duplicate` takes `{name, displayName?, parameters?}` and answers
what `POST /api/v1/projects` answers for `name`: the same checks on the new slug (a DNS-1123 label,
not taken, not proposed, past its cooldown) and the same `202` with the organization's `Change`,
which carries the registry entry `projects/{name}.yaml` (`spec.repository.name` the new slug, `ref`
`main`, the `parameters` given) and the caller's steward binding for the new project. It is held to
`read` on the origin and to what opening a project needs (`Organization.spec.projects.creation`).
Before the `Change`, the Portal copies the origin's repository with its whole history into a new
private repository named after the slug, with `main` protected; that copy is PF-89's fork, made
through the forge's migration from its own address because the forge refuses a fork into the
owner that already holds the origin. A repository of that name already there is `409`, never
adopted, and a failed `Change` removes the copy again, as opening does (CC-85). The origin is only
read: the copy's teams and bindings are its own and grant nothing in the origin (PF-83), and its
ids render from the new slug (PF-79). Layout 1 answers `409`, because a project there has no
repository to copy; its duplicate is an import of its export under the new name (MF-45).

`GET /api/v1/endpoints` is the organization-level Endpoints page (PF-61): an `org-admin` bound at
organization scope reads every project's, a project's steward their own projects', a binding
scoped to one context space that space's alone, and a caller no binding names an empty list,
never a `403` — nothing the caller may not `read` is in it, and a project they may not read is
not disclosed by refusing it (R20).

`GET /api/v1/organization/datamodels` is the one list behind the data model and type pickers
(DM-63, ADR-N-033). `items` holds every `DataModel` of every project whose manifest the caller may
`read` by the rule of `GET /api/v1/endpoints`, a retired version excepted (DM-26), each as
`{name, project, space, version, lifecycle, classes}`, sorted by project, space and name.
`smartDataModels` holds up to 50 entries of the Smart Data Models catalogue index (DM-12) as
`{id, name, subject, description}`, and only when `search` has two characters or more: the index
holds about a thousand models, and a picker lists the organization's own first. `search` matches
case-insensitively on a model's name, project, space and classes, and on a catalogue entry's name,
id and description; longer than 100 characters is `400`. A catalogue that Model Tools cannot
answer leaves `smartDataModels` empty and sets `catalogueUnavailable` to the reason a person can
act on, and the organization's own models are still listed. A caller no binding names gets empty
`items`, never a `403` (R20).

Every list and get answers under `read` of a binding whose scope covers the project (PF-59, PF-60):
a project the caller may not read is `404` on every route of this section, on `export`,
`/revisions`, `permissions/me` and the MCP resources alike, the one answer for "missing" and
"not yours". A write answers `403` with the missing verb (PF-50).

A list takes `labelSelector`, `fieldSelector`, `limit` and `continue`. A list and a get both take
`revision={commit}` (MF-11, MF-16): the project's subtree of the repository at that commit id, read
from the forge the way `GET …/export?revision={commit}` of section 10 reads it, with no `status`,
because status is what the Portal computes now. Only a commit id (7 to 40 lowercase hex digits) is
a revision; a branch name is `400`, because it would read a workspace's unmerged edits past the
workspace's own door (CC-76), and so is `revision` beside `workspace`. A commit the repository does
not know is the caller's own `404`, the same as a resource the commit did not hold (R20). The read
grants are the caller's current ones.

`GET /api/v1/projects` answers a `kind: List` whose items carry `name` and nothing else, the
projects the caller may read (PF-59). A project no binding covers is not in it, which is the same
answer as `404` on its routes and discloses no department's project list to a session that may not
see it.

`{plural}` is the kind's plural from the catalogue in
[Development/04-manifest-kinds.md §2](../Development/04-manifest-kinds.md#2-standard-kind-catalog),
so a new kind is served the moment it is registered and needs no route of its own. `datasources`
is the newest of them: the connection of one external feed, described in
[Architecture/08-pipelines.md §6](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39).
A write carrying a credential as a literal string rather than a `secretRef` is refused with `400`
before any merge request exists (MF-24, CC-06), whatever the kind.

Portability operations:

```text
GET  /api/v1/projects/{project}/export?format=yaml|json|zip|git&revision={commit}&kinds=…&names=…   section 10
GET  /api/v1/projects/{project}/revisions?limit=20                                            section 10
POST /api/v1/projects/{project}/import        multipart (file) or JSON manifests; fields: targetNamespace, conflictPolicy, dryRun; {"url": …} is 501
GET  /api/v1/projects/{project}/syncsources/{name}/status   what the loop reports (section 10)
POST /api/v1/projects/{project}/syncsources/{name}/sync     trigger a run now
POST /api/v1/projects/{project}/syncsources/{name}/pause    switch the loop off or back on
POST /api/v1/projects/{project}/syncsources/{name}/detach   stop syncing: a merge request removing the source
```

Export and import are per project. There is no organization-wide pair: moving a whole
organization is every project exported in turn, and a route that took one archive for all of
them would also take one conflict policy for all of them, which is a decision per project.

`GET /api/v1/projects/{project}` carries the count and the limit of every countable quota
dimension, so a person sees the limit before the verdict does (PF-75). The limit is the one in
force: the project's own `spec.quotas` when it has one, else `Organization.spec.projects.quota`
(PF-73). A dimension no quota limits carries its count and no `limit`.

The answer is the `Project` manifest as the resource API serves it, with one `status` the stored
manifest does not carry:

```json
{
  "status": {
    "usage": {
      "apps": { "used": 0 },
      "contextSpaces": { "used": 2, "limit": 3 },
      "publicEndpoints": { "used": 1, "limit": 4 },
      "residentPipelines": { "used": 3, "limit": 3 }
    }
  }
}
```

A write that would put the project over one of them is refused before a `Change` exists, on every
door, naming the count and the limit — `quota: residentPipelines 4 of 3 in project ovzdusie` —
and the dry run of the same manifest answers the same refusal (PF-74).

`apps/{name}/me` answers `{id, name, email, roles}` for the caller, the same object the static
host writes into `#jc-config` (AP-95), with `roles` computed from the published App's
`spec.access` as AP-92 computes them. A `fullstack` backend calls it with the edge's
`X-Access-Token` as `Authorization: Bearer` (Architecture/16 §13). It is the one
route of this section answered without `read` on the project: an `organization` App admits
people who hold no rule in its project, the answer is only about the caller, and it names no
other resource. An App that
is not published, or does not exist, is `404`; no valid token is `401`.

`permissions/me` answers the rules in force for the caller in one project, each grant naming the
scope it was inherited from, and what the organization's own settings let them do that no rule
expresses (PF-61, PF-65, UI-44):

```json
{
  "project": "helsinki",
  "bootstrap": false,
  "grants": [
    {
      "role": "steward",
      "binding": "hel-stewards",
      "scope": "organization",
      "rule": { "kinds": ["Endpoint", "Pipeline"], "verbs": ["read", "propose"] }
    }
  ],
  "projects": { "creation": { "allowed": false, "reason": "opening a project here needs propose on Project, which org-admin holds (PF-65)" } }
}
```

`scope` is `organization`, `project:{name}` or `contextSpace:{name}`, so a page can say "steward,
inherited from the organization" rather than making an inherited grant look local. `projects.creation`
is the answer `POST /api/v1/projects` would give this caller, with the refusal in the API's own
words: the "New project" control is rendered disabled with that reason, never hidden (UI-44).

### Files beside the manifest (DM-39)

Some kinds are incomplete as one file. A `Mapping` names golden tests it cannot be accepted
without (DM-39), and the examples that satisfy them are two more files in the repository. A
`POST`, `PUT` or `PATCH` body may therefore carry a `files` member beside the manifest, taken
out of the body the way `draft` is, and the Change commits them to the same branch and the same
merge request as the manifest (a request body, so the manifest is shown in excerpt):

```json excerpt
{ "apiVersion": "joinedcontext.com/v1alpha1", "kind": "Mapping", "metadata": { "name": "sdm-airquality-to-bb" },
  "spec": { "tests": [{ "input": "./tests/sdm-airquality-to-bb.input.json",
                        "expect": "./tests/sdm-airquality-to-bb.expect.json" }], "…": "…" },
  "files": { "./tests/sdm-airquality-to-bb.input.json": "{ \"id\": \"urn:ngsi-ld:AirQualityObserved:…\" }",
             "./tests/sdm-airquality-to-bb.expect.json": "{ \"id\": \"urn:ngsi-ld:BBAirQuality:…\" }" } }
```

Every path is relative to the manifest's own folder and stays under it: an absolute path, a
`..` segment, a path outside the kind's folder, an empty path and a duplicate are `400`, naming
the path. A body may carry at most 16 files and 256 KiB of them together; more is an import
(`POST …/import`), which is the route for a repository's worth of files. The files are written
before the manifest, so a reviewer opening the merge request never reads a manifest that points
at a file the change does not carry, and one refusal leaves nothing behind. A file the manifest
does not name is written as sent and reviewed like any other: the plan lists it.

Example dry-run result (`?dryRun=All`; `probe` only for an `http` DataSource, MF-39). The
`verdict` is recorded under the manifest's own kind and name, and it is what the proposal of the
same manifest needs under `strict` (PF-57):

```json
{
  "valid": true,
  "lane": "yellow",
  "plan": { "summary": "create hsl-citybikes-free", "fields": [ { "path": "spec.http.url", "to": "https://…/free_bike_status.json" } ] },
  "probe": { "records": 1, "bytes": 512034, "sample": { "last_updated": 1789314850, "data": { "bikes": [] } } },
  "verdict": { "ok": true, "findings": [], "checkedAt": "2026-09-18T12:00:00Z", "inputDigest": "sha256:…" }
}
```

Under `strict`, a `POST`, `PUT` or `PATCH` that carries no `draft` and whose manifest has no
fresh green verdict is refused after the manifest's own checks and before anything reaches the
forge, with the gate's own document (`reason` is `verdict_absent`, `verdict_failed` or `stale`;
`check` names the check of the kind):

```json
409 { "error": "verdict_required", "check": "jc_manifest_dry_run", "reason": "verdict_absent",
      "detail": "The manifest has not been checked; check it, then propose it." }
```

A manifest naming a resource of its project that is not merged yet but that an open change creates
checks as waiting (MF-48): `valid: true`, and the verdict adds the change it waits on and says so:

```json
"verdict": { "ok": true, "waitsOn": ["chg-0000002a"],
             "findings": [ { "level": "warning", "path": "spec.sources[0].dataSourceRef",
                             "message": "DataSource 'hsl-bikes' resolves once chg-0000002a is approved" } ],
             "checkedAt": "2026-09-25T12:00:00Z", "inputDigest": "sha256:…" }
```

The proposal is let through and its merge request records the change it waits on; a reference
nothing holds, or one whose change was rejected in the meantime, is refused naming the field.

The check is the same request with `?dryRun=All`, so a client sends the manifest twice: first to
check it, then, unchanged, to propose it. A proposal that became a Change forgets the draft its
check created; a person's draft of the same resource with other content stays.

A DataSource with an `authorization` answers `"probe": { "skipped": "the source declares a credential; a dry run resolves none (MF-38)" }`.

Example write result:

```json
{
  "apiVersion": "joinedcontext.com/v1alpha1",
  "kind": "Change",
  "metadata": { "name": "chg-7f3a", "namespace": "helsinki" },
  "status": {
    "lane": "yellow",
    "mergeRequest": "https://git.example.fi/hel/org/pulls/412",
    "plan": { "create": 1, "update": 0, "delete": 0 },
    "phase": "PendingApproval"
  }
}
```

### Drafts of a manifest (AG-61, UI-47, UI-48)

A form saves what a person has typed before anything is proposed. A draft is shared, not
per-browser: the window, an assistant run and an MCP client see the same one, so a person who asks
the assistant to fill a field watches it appear in the open form
(`joinedcontext-portal/src/api/drafts.rs`).

```text
GET    /api/v1/projects/{project}/drafts                       one line per draft
GET    /api/v1/projects/{project}/drafts/{kind}/{name}         one draft with its manifest and verdict
PUT    /api/v1/projects/{project}/drafts/{kind}/{name}         save it; body { "manifest": …, "expectedVersion": n }
DELETE /api/v1/projects/{project}/drafts/{kind}/{name}         discard it → { "dropped": true }
GET    /api/v1/projects/{project}/drafts/events                the same changes as Server-Sent Events
```

```json
{
  "project": "helsinki",
  "kind": "DataSource",
  "name": "hsl-citybikes-free",
  "manifest": { "…": "the manifest as the form holds it, whole" },
  "verdict": { "ok": true, "findings": [], "checkedAt": "2026-09-18T12:00:00Z", "inputDigest": "sha256:…" },
  "touchedBy": "jana.kovacova",
  "touchedKind": "person",
  "version": 7,
  "updatedAt": "2026-09-18T12:00:04Z"
}
```

- Writing or discarding a draft needs `propose` on its kind, the verb the proposal itself needs:
  a draft is the proposal before it is sent, and a caller who may not propose an `Endpoint` may not
  park one either. Reading one asks what reading the manifest asks, so a draft of a space the
  caller may not read is `404` like the manifest would be (PF-59, R20).
- `version` counts up on every save. Send the version you read as `expectedVersion` and a save
  against a newer draft is refused with `409 {"error": "draft_conflict", "current": 9}` instead of
  overwriting what the other window wrote; omit it and the last save wins.
- `touchedBy` is the caller's username and `touchedKind` is how they reached it: `person`,
  `api-key`, `mcp` or `run`, so a form can say the assistant wrote this, not you.
- A literal secret under one of the secret keys of section 5 is `400` here as it is on a write
  (MF-24): a draft is a manifest on its way to Git.
- `?workspace={name}` addresses the drafts of one workspace (section 22). A draft of a workspace is
  not a draft of the project, and the query is absent for the project's own.
- `/drafts/events` streams `put`, `verdict` and `drop` events, each carrying `kind`, `name`,
  `version`, `touchedBy`, `touchedKind` and `updatedAt`, with the SSE id set to the version. Every
  event is checked against the reader's bindings as it passes, so a revoked binding stops the flow
  without a reconnect. A keep-alive comment goes every fifteen seconds and the answer carries
  `Cache-Control: no-cache` and `X-Accel-Buffering: no`, so no proxy buffers the stream.
- A draft never becomes a resource by itself. A proposal names it
  (`{"draft": {"kind": …, "name": …}}`, section 21) or carries the manifest; the Change that
  results forgets the draft its check created.

## 5. Change Proposals and Approvals (CC-34, CC-41, CC-63, UI-23…UI-25)

A write answers with a `Change` and leaves a merge request open. These endpoints are the Portal's
view of those merge requests, so that an approver never has to open the forge to do their job:

```text
GET  /api/v1/projects/{project}/changes                  open proposals, newest first
GET  /api/v1/projects/{project}/changes/{id}             one proposal with its plan diff
POST /api/v1/projects/{project}/changes/{id}/approve     review + merge
POST /api/v1/projects/{project}/changes/{id}/reject      review "request changes" + close
```

A write is judged against the Portal's copy of the repository and cut from the default branch.
When the default branch already holds the resource otherwise than that copy (another `spec`,
labels, annotations, title or description at the path the write goes to), the write is `409
conflict`, "changed on main after the Portal last read it", and nothing is committed or published:
the caller reads the resource again and sends the change once more, so no Change ever sets back
what main moved to (T-2674).

`{id}` is the `metadata.name` a write returned: `chg-` plus the merge request number in eight
lowercase hex digits. A Change targets one repository (CC-87), which `status.repository` names. In
layout 2 ([ADR-N-029](../Decisions/adr-n-029-one-repository-per-project.md)) a project's own
kinds land in the project repository and the organization kinds in the organization repository, so
under `/projects/{project}/changes` `chg-{hex}` is a merge request of the project repository and
`chg-org-{hex}` one of the organization repository; the two number their merge requests apart. A
layout 1 organization has one repository and only the first form.

A listed proposal carries what a reviewer decides on, not what the forge stores:

```json
{
  "apiVersion": "joinedcontext.com/v1alpha1",
  "kind": "ChangeList",
  "items": [
    {
      "apiVersion": "joinedcontext.com/v1alpha1",
      "kind": "Change",
      "metadata": { "name": "chg-0000019c", "namespace": "helsinki" },
      "status": {
        "lane": "red",
        "repository": "helsinki",
        "mergeRequest": "https://git.example.fi/hel/helsinki/pulls/412",
        "plan": { "create": 0, "update": 1, "delete": 0 },
        "phase": "PendingApproval"
      },
      "summary": { "key": "change.summary.update", "params": { "kind": "Endpoint", "name": "public-air", "fields": 1 } },
      "author": { "name": "Aino Virtanen", "email": "aino.virtanen@example.org" },
      "createdAt": "2026-09-06T09:14:22Z"
    }
  ]
}
```

`summary` is a message key and its parameters, derived from the plan and never from the raw diff
(CC-34). The sentence is composed in the UI, which already carries the sk/en/de/cs catalogues; the
API stays language-free so a second set of translations never has to be kept in step with the
first. `author` is read from the commit, so a proposal always names the human who made it and never
a shared bot identity (CC-44). `GET …/changes/{id}` adds `plan.fields`, the field-level
diff of `PlanDiff`, with any value under a `password`, `token`, `secret`, `clientSecret` or
`apiKey` key replaced by `"[REDACTED]"` (CC-06).
It also lists `files`, every file of the merge request (`path`, `kind`, `operation`, `lane`), and
each manifest among them carries `fields`: its own field-level diff, base against head, redacted the
same way, so an approver reads what each file of a bundle changes and not only the headline
manifest's. A native file (a LinkML source, a `bento.yaml`) carries no `fields`.

Approval rules, enforced by the API and not only by the UI:

- the caller needs the `portal-approver` realm role; anyone else gets `403` (CC-41);
- the author of a proposal may not approve it — `403` with `type: ".../self-approval"`;
- a proposal a person sends with a Portal session (the cookie or the edge's), when a binding
  covering the project grants them both `approve` and `delete` on every kind of every file it
  touches (an administrator, PF-58), is approved as it is proposed: the propose route answers
  `202` with the `Change` already `Deploying`, and the merge commit says `Approved in the Portal
  by {email}, its author, as an administrator of {kind}`. The same holds for `jc_resource_propose`
  and the other propose operations when the form calls them with that session. A red-lane
  proposal is approved so only with `?confirm=<resource name>` on the propose or `DELETE` route
  (the `confirm` of `jc_resource_delete`); without it the `Change` stays `PendingApproval` and
  its author approves it on the approval page with the name typed. Anyone else's proposal
  answers `202` `PendingApproval`. A bearer caller, MCP and an agent run never approve on
  propose, whoever runs them (AG-11, AG-82), and the bootstrap administrators' group does not
  count;
- a proposal in the `red` lane needs the `portal-approver` role **and** an explicit
  `{"confirm": "<resource name>"}` body, so a destructive merge is never one click (CC-19, CC-39);
- a change that waits on another (MF-48) lists it in `waitsOn`, one `{ "name": "chg-…", "phase":
  "PendingApproval" | "Merged" | "Rejected" }` each, on the list and on the detail;
  approving it is `409 conflict` while one of them is not merged, and a `Rejected` one flags the
  change: what it names will not be created, so it is rejected or proposed again;
- approving answers `202` with the `Change`, its `phase` moved to `Deploying`; the reconciler
  moves it to `Live` when the merge lands on the default branch and the mirror sync observes it.

## 6. Core Endpoint Examples

### List Context Spaces

```http
GET /api/v1/projects/{project}/spaces?limit=20 HTTP/1.1
Host: portal.example.joinedcontext.com
Authorization: Bearer eyJhbGciOiJSUzI1Ni...
```

A collection answers with a `List` envelope whose `items` are whole manifests; paging is a
`continue` token, not a page number, so a page stays stable while the collection changes.

```json
{
  "apiVersion": "joinedcontext.com/v1alpha1",
  "kind": "List",
  "metadata": {
    "continue": "eyJhZnRlciI6Im1vYmlsaXR5LWxpdmUifQ",
    "remainingItemCount": 3
  },
  "items": [
    {
      "apiVersion": "joinedcontext.com/v1alpha1",
      "kind": "ContextSpace",
      "metadata": {
        "name": "mobility-live",
        "namespace": "helsinki",
        "title": { "sk": "Živá mobilita", "en": "Live Mobility Feed" }
      },
      "spec": { "orgDomain": "hel.fi" },
      "status": {
        "phase": "Live",
        "observedRevision": "9c1f0ab",
        "sourceUrl": "https://git.example.fi/hel/org/src/branch/main/projects/helsinki/spaces/mobility-live/space.yaml"
      }
    }
  ]
}
```

`metadata.continue` and `metadata.remainingItemCount` appear only while more items follow.

`status.sourceUrl` is the forge page of the very file the manifest was read from, computed by the
Portal during the mirror sync and never read from Git (MF-04). It lets every view link "Source"
without teaching the browser where a kind lives in the repository; it is absent when the manifest
has not been mirrored yet or no forge is configured.

## 7. Pipeline Runtime Metrics (PL-24, CC-35)

A pipeline manifest says what should run; the numbers come from the Bento runner, which serves
Prometheus text on port 4195 (PL-24). The Portal reads that port on the browser's behalf, so the
UI never talks to a workload and the runner never needs an ingress:

```text
GET /api/v1/projects/{project}/pipelines/{name}/metrics    counters of one running stream
```

```json
{
  "pipeline": "aq-mqtt-ingest",
  "scrapedAt": "2026-09-06T16:20:11Z",
  "received": 128401,
  "sent": 128390,
  "errors": 3,
  "bufferDepth": 11,
  "latencyP99Ms": 42.5
}
```

- Counters are cumulative since the runner started, exactly as the runner reports them. The view
  samples them to show a rate; the Portal keeps no history, that is Prometheus' job (OPS-16).
- A field is absent when the runner does not export it. Absent is not zero.
- Only series carrying `stream="{name}"` are read, so one pipeline's view never discloses the
  traffic of its neighbours in the same runner.
- `503` with `problem+json` when the project has no runner configured or its metrics port does not
  answer within the scrape timeout. The view then shows the pipeline without numbers, not as
  failed: a runner that is down is an operational fact, not a manifest error.
- The body carries counters only. Runner logs, stream configuration and secret values are never
  part of it (PL-17).

### 7a. Testing a candidate pipeline (PL-43, MF-38)

```text
POST /api/v1/projects/{project}/pipelines/test
```

```json
{
  "pipeline": { "apiVersion": "joinedcontext.com/v1alpha1", "kind": "Pipeline", "metadata": { "name": "shmu-air-quality" }, "spec": { "class": "resident", "source": { "dataSourceRef": { "kind": "DataSource", "name": "shmu-csv" } }, "compute": { "kind": "bloblang", "bloblang": "root.id = `urn:ngsi-ld:AirQualityObserved:hel.fi:air-quality:%v`.format(this.station_id)" }, "targetEndpoint": "urn:ngsi-ld:Endpoint:hel.fi:helsinki:helsinki-all" } },
  "sample": { "text": "station_id,pm10,timestamp\n01,18.2,2026-09-13T07:00:00Z\n", "format": "csv" }
}
```

- `sample.text` is at most 5 MiB and never leaves memory; `sample.url` instead makes the runner fetch it under its own egress policy. `format` is `csv`, `json` or `text` (the default, one message as it is).
- The answer is the trace of Architecture/08 §7: `input`, `mapping`, `validation`, `errors`. A manifest the kind refuses is `400` (MF-37); no runner, or a runner that does not answer within three seconds, is `503`; a second test while one runs in the project is `409`.
- A mapping that yields an array is one entity per element in `mapping` and `validation`, at most 20 (PL-48).
- An error of stage `mapping` carries `step`, the index into `spec.steps` of the step it failed at (PL-52); `lint` and `runner` errors have no step and leave it absent.
- A derived pipeline (`spec.source.endpointRef`, the studio's `kpi` preset, PL-45) is tested on a page of its source endpoint: `sample.url` is that endpoint's `…/ngsi-ld/v1/entities?type=…&attrs=…` URL (the runner fetches it with the pipeline's read grant) or `sample.text` is such a page, `format: json`; the page reaches the mapping as one message, so a fold yields one entity in `mapping` and `validation` checks it as an indicator (PF-43): `calculationFormula`, `derivedFrom` and `computedBy` missing are `problems`, not a `200` that admission then refuses.
- Nothing is written, no `secretRef` is resolved, the stream is deleted whatever happened.

## 8. User Preferences (UI-09, UI-10)

Preferences are the one thing the Portal stores for itself: how a person likes the UI, never how the
platform is configured. They live in the Portal's PostgreSQL preferences tier, keyed by the Keycloak
`sub` of the session (CC-40), and a change takes effect on the answer, with no commit, no merge
request and no approval (UI-10):

```text
GET /api/v1/preferences      the caller's preferences; an empty object before the first save
PUT /api/v1/preferences      replaces them whole; answers 200 with what is now stored
```

```json
{
  "theme": "system",
  "locale": "sk",
  "defaultProject": "air-quality",
  "dashboardLayouts": { "air-quality-overview": { "collapsedLegend": true } },
  "advancedMode": false
}
```

- `theme` is `light`, `dark` or `system`; `locale` an ISO 639-1 code; `defaultProject` a DNS-1123
  name. `dashboardLayouts` is free JSON per dashboard name, capped at 64 KiB in total: it is the
  browser's saved state, the Portal does not interpret it.
- Every field is optional; a `PUT` with a field absent clears it. Unknown fields are a `400`.
- A caller only ever reads or writes their own row: there is no path parameter and no admin view
  over other people's preferences.
- `advancedMode` shows the form fields a `UiSchema` marks `advanced` (CC-29): the commit message,
  the branch, the target revision. Absent means off. It changes what a form shows, never what a
  write may do.
- `503` with `problem+json` when the Portal runs without a preferences database. The UI then works
  from browser defaults; nothing else depends on this tier (UI-09).

### 8a. Form arrangements (UI-02, CC-29)

```text
GET /api/v1/forms            every UiSchema manifest of portal/forms/, as a List
```

- One unpaged `List` of the organization's `UiSchema` manifests, read from the same mirror as every
  other resource; a form dialog indexes it by `spec.for`. An instance with no manifests answers an
  empty `List`, never `404`.
- The session is the only gate, as for every resource read; there is no path parameter.
- A dialog for a kind with a manifest renders the manifest's order, groups, widgets and help; a
  kind without one renders its built-in form. What a manifest asks for and the form cannot do (a
  field the schema lacks, a widget the Portal does not register, two manifests for one kind) is
  listed in the dialog itself, and the dialog's footer carries the `advancedMode` switch.

## 9. ServiceAccounts and API keys (PF-34…PF-40)

A `ServiceAccount` manifest declares that a credential exists; the secret itself never enters Git
(PF-36). The manifest is read and written through the resource API like every other kind
(`/api/v1/projects/{project}/serviceaccounts`). The keys behind an `api-key` credential live in the
Portal's PostgreSQL tier, and these routes are the only way to mint, rotate and revoke them:

```text
GET    /api/v1/projects/{project}/serviceaccounts/{name}/keys                  the account's keys, metadata only
POST   /api/v1/projects/{project}/serviceaccounts/{name}/keys                  mint a key → 201, the token once
POST   /api/v1/projects/{project}/serviceaccounts/{name}/keys/{keyId}/rotate   mint a successor, the old key keeps working for the overlap window → 201
DELETE /api/v1/projects/{project}/serviceaccounts/{name}/keys/{keyId}          revoke now → 204
```

Minting takes the credential name from the manifest and, optionally, an expiry:

```json
{ "credential": "legacy-push", "expiresAt": "2027-03-01T00:00:00Z" }
```

The `201` answer is the only place the secret ever appears:

```json
{
  "keyId": "3f9c2a7b1d4e8f06",
  "token": "jc_3f9c2a7b1d4e8f06_Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MGFiY2RlZg",
  "credential": "legacy-push",
  "expiresAt": "2027-03-01T00:00:00Z"
}
```

A listed key carries what an operator decides on and nothing that opens a door:

```json
{
  "items": [
    {
      "keyId": "3f9c2a7b1d4e8f06",
      "credential": "legacy-push",
      "createdAt": "2026-09-06T18:20:11Z",
      "createdBy": "jana.kovacova",
      "expiresAt": "2027-03-01T00:00:00Z",
      "lastUsedAt": null,
      "revokedAt": null
    }
  ]
}
```

- `token` is `jc_{keyId}_{secret}` (PF-37): `keyId` is 16 lowercase hex characters, the secret 32
  random bytes in URL-safe base64 without padding. The Portal stores the Argon2id PHC string of the
  secret, the key id, the expiry and the audit timestamps, never the secret (PF-36); a listed key
  therefore has no `token`, and a lost token means a new key.
- `credential` MUST name an `api-key` credential of the manifest; an `oauth-client` credential is
  provisioned in Keycloak by the reconciler and has no key here (`400`).
- `expiresAt` defaults to the credential's `expiresAt` in the manifest; without either the key does
  not expire. It MUST NOT be in the past (`400`).
- Rotation (PF-38) mints a successor with the same credential and expiry and moves the old key's
  expiry to `now + overlap`, `{ "overlapHours": 24 }` in the body, default 24, at most 168; an old key
  that already expires sooner keeps its earlier expiry. Both keys are listed while both work.
- Revocation is immediate: the key row is kept with `revokedAt` set for the audit trail and the
  gateway refuses it on the next request (PF-38).
- The caller MUST be the account's `spec.owner.user` or hold the `portal-approver` realm role
  (CC-60); anyone else is `403`. An account the caller may not see is `404`, whether it exists or
  not (R20).
- `503` with `problem+json` when the Portal runs without its PostgreSQL tier, as for section 8.

## 10. Export, import, revisions and sync (MF-16…MF-32, CC-49)

The repository at any revision is the complete configuration export (CC-49). These routes hand it
out without Git knowledge, always read from the forge and never from the live mirror, so what is
downloaded is byte-for-byte what a `git archive` of that path would hold:

```text
GET /api/v1/projects/{project}/export?format=yaml|json|zip|git&revision={commit}&kinds={plurals}&names={names}
GET /api/v1/projects/{project}/revisions?limit=20
```

- `format=yaml` (default) is one multi-document YAML stream, one manifest per document; with
  `kinds=endpoints&names=public-air` it is a single manifest file. `format=json` is a `kind: List`
  with the same items. `format=zip` is the archive of `projects/{project}/` at the revision: the
  manifests, the native files next to them (`bento.yaml`, LinkML, committed schema artifacts) and a
  `bundle.yaml` index at the archive root. The index is the platform's own `kind: Bundle`
  (namespace `org`, name the project), so `jcctl validate` accepts what the Portal wrote: `spec`
  carries `exportedAt`, `exportedBy`, `sourceRevision` (the commit the export was taken at, never
  a branch name), `items` (`kind`, `namespace`, `name`, `path` per manifest), `nativeFiles`,
  `files` (`path` and `sha256` of every file the bundle holds, over the bytes as exported, so a
  transfer can be verified before the source is deleted, MF-42) and `omitted`. An export whose filters select no manifest carries no index, because a Bundle lists
  at least one resource. Media types: `application/yaml`, `application/json`, `application/zip`,
  with a `Content-Disposition: attachment` filename that names the project and the short revision.
- A whole-project export (no `names` filter) is complete and self-describing (MF-41). The archive
  adds, at its root, `README.md` (what each kind it holds is, how many resources, where the schema
  is, the revision and the exporter) and `schemas/`: `schemas/kinds/{Kind}.schema.json`, the JSON
  Schema (draft-07) of every kind in the archive with its field descriptions, and
  `schemas/models/{name}/{name}.linkml.yaml` and `{name}.schema.json` for every `DataModel`, read
  from the repository or generated by Model Tools when the repository has no JSON Schema; a model
  whose files cannot be had is listed under "Missing" in the README. `format=yaml` ends the stream
  with the same `kind: Bundle` index as its last document, whose `spec` carries `readme` (the README
  text) and `schemas` (`kinds`: kind → schema, `models`: name → `{linkml, jsonSchema}`) beside the
  members above; `format=json` carries `readme` and `schemas` beside `items`. A `kinds` filter keeps
  the schemas of the kinds it selects. With `names`, the answer is the manifests alone. Import skips
  `README.md`, `schemas/` and the index, so none of them is written into a project.
- `format=git` exports a project of layout 2, which lives in a repository of its own (MF-45).
  The archive (`application/zip`, `{project}-git-{short}.zip`) holds `{project}.bundle`, the
  forge's `git bundle` of the project repository's default branch with that branch's whole
  history; `{app}.bundle` for every App of the project whose `source.git` names a repository of
  the forge's organization, under the App's name; `{name}.tags` beside a bundle whose repository
  has tags, one `{commit} refs/tags/{tag}` line per tag, because the forge bundles one ref and
  the import sets the tags again; `projects/{project}.yaml`, the registry entry with no
  parameter values, so the target sets its own (CC-88); and the `kind: Bundle` index
  `bundle.yaml`, whose `spec.repositories` lists each bundle with its `role` and the `head`
  commit it ends at and whose `spec.files` carries every file's SHA-256 (MF-42). `project.yaml`
  at the archive root is the project's own file at that head, the one an import reads the
  parameter declarations from without unpacking a bundle. Other branches
  and the annotation of an annotated tag do not travel; `git bundle create --all` of a mirror
  clone (Deployment/11 §7) carries them. A bundle that ends elsewhere than the head read in the
  same export is `409` (export again), and so is an App whose repository is outside the forge's
  organization, named. A git export is the whole repository, so it answers `403` to a caller
  who may not read every manifest of the project (MF-18), where `format=zip` leaves those out;
  it takes no `revision`, `kinds` or `names` (`400`), and a project of layout 1 answers `409`.
- `revision` is a commit sha or branch name; absent means the default branch head. A revision the
  forge does not know is `404`.
- `kinds` and `names` are comma-separated filters on the manifests; the archive format keeps native
  files regardless. Filters that match nothing answer an empty stream, list or archive, not `404`.
- `status` is stripped from every manifest and string values under the secret keys of section 5
  (`password`, `token`, `secret`, `clientSecret`, `apiKey`) are removed, so a bundle is re-importable
  and carries no credential (MF-17). Native files are copied as they are; MF-24 keeps literal
  secrets out of them at write time.
- Grants apply as on the resource API: the bundle holds the kinds the caller may `read` in the
  project (PF-59), a project they may not read is `404`, and `omitted` in the index counts what
  was withheld without naming it (MF-18). Live entities and histories are
  never part of a bundle (MF-19); they are the endpoint's `file.{json|csv|geojson}` representation.
- `/revisions` is the history of `projects/{project}/` on the default branch, newest first, for the
  revision picker (Architecture/06 section 6): `sha`, `message`, `author`, `date`. `limit` is 1…100,
  default 20.

```json
{
  "items": [
    { "sha": "8c56954a1f0e2b3c4d5e6f708192a3b4c5d6e7f8", "message": "Endpoint public-air: add csv", "author": "Aino Virtanen", "date": "2026-09-06T16:30:00Z" }
  ]
}
```

- `503` with `problem+json` when no forge is configured (CC-03): a Portal that cannot read the
  repository has nothing to export.

Import is the same bundle read back, into a project that is not the one it left (MF-20…MF-26):

```text
POST /api/v1/projects/{project}/import?dryRun=All
```

- The body is either `multipart/form-data` with the archive or manifest as the `file` part and the
  options beside it as fields, or `application/json` with the options and `manifests` holding one
  manifest, a `kind: List`, or an array of them. Options are the same in both: `targetNamespace`,
  `orgDomain`, `conflictPolicy`, `dryRun`. `?dryRun=All` is the query form of the last one.
  `orgDomain` is the organisation every imported id is rewritten to; absent, it is the domain of
  the instance's own `Organization`. The `{orgDomain}` segment of an id, and of an anchored
  `idPattern`, is rewritten for the spaces the bundle carries, so a moved project stops claiming
  the ids of the city it came from and a federated registration that named another city keeps
  naming it (MF-22, PF-43). The `{space}` segment moves only when the conflict policy renames that
  ContextSpace. An organization-scoped kind is written in namespace `org` whatever project imported
  it, and a `Project` manifest inside the bundle is dropped: the destination project is the one in
  the path.
- An upload is at most 32 MiB and 2 000 archive entries, and an entry whose path leaves the archive
  root is refused before it is read.
- `bundle.yaml` describes the bundle and is never imported as a resource. Its `project` and
  `revision` become `joinedcontext.com/imported-from` on every manifest that lands, so an imported
  object says where it came from (MF-20); an upload with no index is annotated `upload`.
- Every manifest is remapped into the project: the namespace, the typed and string references
  between the manifests, and the `{space}` segment of every `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`
  in the spec (MF-22). `targetNamespace` may only name the project itself, because the repository
  path of every kind starts `projects/{project}/`.
- A Policy's `spec.assigner` lands as `did:web:{orgDomain}`, the placeholder the loader renders
  for the organisation that owns the file (CC-82): a Policy grants over a space of this project,
  so the organisation that may give that data away is this one, whatever DID the bundle carried.
  Every assigner the import rewrote is listed in the report's `reassigned` (`Policy/{name}`, the
  DID the bundle carried, the placeholder it became), so the person who approves the Change sees
  that the grant is now signed by this organisation (R6).
- `conflictPolicy` is `fail` (the default: `409` naming the first collision, and nothing is
  written), `skip`, `replace` or `rename`. A rename is `{name}-{origin}`, the origin being the
  project the manifest came from, then `-2`, `-3` while the name is taken; every reference to the
  renamed resource inside the bundle follows it, so a duplicated project does not import and then
  dangle (MF-26).
- The gates run over the whole bundle before anything is written, and any one of them refuses all
  of it with `400` (MF-24): a kind this platform does not serve, an unsupported `apiVersion`, a
  `status` block (MF-04), a literal secret under one of the secret keys of section 5, or a
  reference that neither the bundle nor the project resolves.
- The answer is `202` and a `Change`: one branch, one merge request for the whole bundle, and the
  lane is the riskiest of the resources in it (CC-63). Native files travel with their manifests and
  keep their path under the new project.
- `dryRun` answers `200` with the report instead: `created`, `replaced`, `skipped`, `renamed`
  (old name → new), `reassigned` (Policy → the assigner it carried, when one was rewritten),
  `nativeFiles`, `lane` and `source`. The `Change` body lists the same reassignments. Nothing is written and no branch is made.
- The dry run is the bundle's check (PF-57, every door): it records a verdict over the bundle as
  sent (its SHA-256) and the options that decide what it writes (`conflictPolicy`, `orgDomain`,
  `targetNamespace`), for the caller and the project. Under `strict` an import without `dryRun`
  needs that verdict, green and fresh. Nothing reaches the forge otherwise, and the answer is the
  gate's own `409` with `"check": "jc_project_import"` (run it with `dryRun`) and `reason`
  `verdict_absent`, or `stale` when the bundle or an option differs from the checked one. An
  import that became a `Change` forgets its verdict; `lax` lets an unchecked bundle through.
- A bundle carrying `spec.files` is verified as it is written (MF-42): the report gains
  `verified` (`path`, `equal` per file), the SHA-256 of what the import wrote compared with the
  index after the namespace mapping is undone, and the `Change` body says "n of m files equal".
  A bundle from an older exporter carries no `spec.files`, and the report then carries no
  `verified`: an unverifiable transfer says so rather than claiming every file is equal.
- Both answers, the dry run's report and the `Change`, carry `needs`: what the bundle cannot carry
  and must be provided where it lands (CC-84). Each item is `{kind, where, why, link}` with `kind`
  one of `secret` (a `secretRef` whose value is set in the target), `person` (a user named in a
  RoleBinding or a Policy), `host` (an Environment host or certificate) and `credential` (a feed's
  authorization); `where` is the manifest path, and `link` the Portal page that sets it. An empty
  list means nothing is to be provided. No item ever holds a secret value, and a caller who may
  not read the target project gets no list. Nothing in it blocks the import; each item keeps the
  resource it belongs to from going Live with a plain reason. Save as across projects and a
  workspace's answers carry the same list. Values the loader renders stay in their placeholder or
  local form on both sides (`{orgDomain}`, `endpointRef`, no `{space}` literal, MF-43).
- `?format=git` imports the archive of a `format=git` export as a new project, the `{project}`
  of the path, in an organization of layout 2 (MF-45, MF-46). The body is `multipart/form-data`
  with the archive as `file`, `parameters` (a JSON object of values for what `project.yaml`
  declares, CC-88; a `secret` parameter takes a `secretRef` name, never a value) and an optional
  `displayName`. Who may open a project may import one (PF-65), and the name passes the checks of
  `POST /api/v1/projects`. Before anything is created the archive is checked: the index is a
  valid `kind: Bundle` with one `project` repository and no `organization` one, every file's
  SHA-256 equals the index (MF-42), `project.yaml` loads at this release's `apiVersion` (an older
  one is migrated with `jcctl migrate` first and a newer one is refused, MF-47), and the
  parameters resolve against its declarations; each failure is `400` naming it. Every repository
  it would create (`{project}`, and `{project}_{app}` per application, AP-75) must not exist yet
  (`409`). Then each repository is created empty and private, its bundle is pushed as its default
  branch `main` with the tags of `{name}.tags` (the Portal speaks git's receive-pack; it holds no
  git), and its head is read back: a head that is not the index's removes every repository the
  import created and answers `409`. When the slug differs from the one the bundle left, one
  commit on `main` of the project repository remounts it (every manifest that names the old slug
  names the new one; an Endpoint slug another project of this organization serves is drawn
  anew; `CODEOWNERS` names the new writers; an App's `source.git.url` names its new
  repository), so the head after the import is that commit and the answer names both. `main` is
  then protected, and the answer is `202` and the organization's `Change`: the registry entry
  with the given values and the caller's steward binding, as opening a project proposes it. A
  `Change` that cannot be opened removes the repositories again (CC-85). The report in the
  `Change` body carries `verified`, one `{path, equal}` per bundle with its head. `dryRun` answers
  `200` with the checks alone and the parameters `project.yaml` declares, which the Portal's
  import form is drawn from; nothing is created. As for every import, that dry run is the check
  PF-57 holds the import to under `strict`, over the archive's SHA-256, the slug and the
  parameters.
- The `{"url": …}` source of MF-20 answers `501`. Fetching a host the caller names is an egress
  decision the Portal has no policy behind, and the upload form carries the same bundle; see
  `OPEN-QUESTIONS.md`.

### Sync sources (MF-27…MF-32)

A `SyncSource` is a manifest like any other, written and read through the resource API of section
4. What these four routes address is the loop around it: the run, the switch, and the way out.

```text
GET  /api/v1/projects/{project}/syncsources/{name}/status
POST /api/v1/projects/{project}/syncsources/{name}/sync
POST /api/v1/projects/{project}/syncsources/{name}/pause     {"paused": true|false}
POST /api/v1/projects/{project}/syncsources/{name}/detach
POST /api/v1/webhooks/sync/{project}/{name}                  signed, no session
```

- `/status` is what the project page shows (MF-30): `phase`
  (`Synced | OutOfSync | PendingApproval | Error | Paused`), `observedRevision` — the source
  revision this repository carries — `lastRunAt`, `mergeRequest` for the proposal a run opened and
  nobody has answered, `lastError` when the last run did not finish, `paused`, and `durable`, which
  is `false` on a Portal with no database, where a restart forgets where each source stood.
- `/sync` runs the loop once whatever the schedule says and answers `200` with `proposed` (the
  `kind: Change` envelope of each merge request the run opened, carrying its URL), `unchanged`,
  `flags` — what the run could not do, in sentences — and the `status` that follows it. A paused
  source answers with its status and runs nothing: the switch is not overridden by the button.
- `/pause` records an operator's decision about a running loop. It writes nothing to the repository
  and opens no merge request, because nothing about the configuration changed.
- `/detach` stops syncing for good, and that *is* a change to the repository: it answers `202` with
  the merge request that removes the `SyncSource` manifest. Syncing pauses at once, so a source
  cannot keep proposing while its own removal waits for review, and stays paused if the merge
  request is closed rather than merged. The resources the source brought into the project stay
  where they are — detaching a source is not deleting what it published.
- The webhook route is what a `schedule: { webhook: true }` source runs on. It carries no session
  and is authenticated by an HMAC-SHA256 of the request body in `x-gitea-signature`, against **that
  source's own** secret — `spec.webhook.secretRef`, resolved like every other credential, and
  `spec.webhook.previousSecretRef` while one is being rotated (MF-44). The signature covers the
  body and not the path, so a shared secret would make every path reachable by whoever holds it:
  the origin of one project's source could force a run of another project's. Each source therefore
  carries its own, and the secret a department is given opens their door and nothing else.
- One `401`, with one body, for every refusal at that door: a signature that does not verify, a
  source that is not there, a source with no `spec.webhook`, and a source whose reference this
  instance cannot resolve. The route answers the same to all four on purpose — it is unauthenticated
  until the signature verifies, so a `404` would make it an existence oracle over the sources of
  every project (PF-59, R20), and a `503` would say which instances have no secret backend. The
  source's own `/status` is where an operator reads that its webhook secret does not resolve; the
  value itself never appears in an answer, a log line or the status.
- Every run reaches its origin over `https` and nothing else, follows a redirect only to another
  `https` address, and refuses an origin whose `source.*.secretRef` this instance cannot resolve
  rather than fetching it anonymously (MF-31). A `platformApi` origin is read through the partner's
  own `/revisions` and `/export` of this section and through nothing else (MF-32).

### The mirror itself (MF-04, CC-08, OPS-51)

Four routes are about the Portal's own copy of the repository rather than about any project
(`joinedcontext-portal/src/api/sync.rs`, `joinedcontext-portal/src/api/webhook.rs`,
`joinedcontext-portal/src/api/health.rs`):

```text
GET  /api/v1/sync              how the background mirror sync stands; a session, no project
POST /api/v1/webhooks/gitea    the forge's own hook: signed, no session
GET  /api/v1/health            liveness; public
GET  /api/v1/ready             readiness; public
```

- `/sync` answers `lastSync` (a Unix instant), `revision`, `manifests`, `lastError` and `leader`,
  which is the replica that reconciles. It never carries the repository URL, the branch or a
  token: a browser reads it, and none of those is the browser's business.
- `/webhooks/gitea` is what makes a merged change visible without waiting for the next tick. The
  body is authenticated by an HMAC-SHA256 in `x-gitea-signature` against the configured webhook
  secret, and the previous one while a rotation runs, so a rotation never closes the door
  (T-0982). A push to the default branch or a merged pull request answers `202` and starts a sync;
  any other event answers `204`; a body that is not JSON is `400`, a missing or wrong signature
  `401`, and an instance with no webhook secret configured `503`, because a hook nobody can
  authenticate is refused rather than trusted.
- `/health` answers `{"name": …, "version": …, "status": "ok"}` whenever the process serves, and
  it is the liveness probe. `/ready` is the readiness probe (OPS-51): `503 {"status": "loading"}`
  until this replica's mirror holds the repository, `200 {"status": "ready"}` afterwards. A Portal
  configured without a forge has no repository to wait for and is ready at once. Both are public,
  because a probe has no session.

## 11. Model Tools preview (DM-10, DM-17, DM-18, DM-19)

The LinkML editor needs a compiled preview on every keystroke, and the compilation runs in Model
Tools: a stateless, versioned image holding `linkml`, `schema-automator`, `pysmartdatamodels` and
the `ngsi_ld_kind` post-processor (DM-18). The Portal calls it for the browser, so the editor never
reaches a third-party host itself and Model Tools needs no ingress:

```text
GET  /api/v1/tools/sdm-catalog   the Smart Data Models catalogue index: subjects, their models
                                 and each model's attribute names (?refresh=true refills the cache)
POST /api/v1/tools/generate      LinkML source  → JSON Schema, @context, SHACL, OWL, example
POST /api/v1/tools/import-sdm    a Smart Data Models model id → the same artifacts as LinkML
POST /api/v1/tools/infer-schema  a sample file (multipart, ≤ 10 MiB: CSV, XLSX, JSON, PDF)
                                 → a draft LinkML model and the editor operations that build it
```

The source of a model is a file of the repository, read and saved through one route scoped to it
(DM-56, Architecture/11 §6.8): `GET` answers the text at the manifest's `spec.linkml`, `PUT` with
the new text answers `202` and a `Change` whose commit carries the source, the manifest and the
generated artifacts, in the lane DM-24 assigns.

A name the project does not hold yet is created by the same `PUT` when it names the space the
model belongs to (DM-57): the Change then carries the new manifest as well, and without `space`
the answer is `400`.

```text
GET /api/v1/projects/{project}/datamodels/{name}/source          → 200 text/yaml, the LinkML document
PUT /api/v1/projects/{project}/datamodels/{name}/source           text/yaml body → 202 Change (MF-12)
PUT /api/v1/projects/{project}/datamodels/{name}/source?space=s   text/yaml body → 202 Change, the model created (DM-57)
```

```json
{
  "refreshedAt": "2026-09-06T04:00:00Z",
  "stale": false,
  "subjects": [
    {
      "name": "dataModel.Environment",
      "title": "Environment",
      "models": [
        {
          "id": "dataModel.Environment/AirQualityObserved",
          "name": "AirQualityObserved",
          "description": "An observation of air quality conditions.",
          "attributes": ["pm10", "pm25", "dateObserved"]
        }
      ]
    }
  ]
}
```

```json
{ "source": "id: https://example.org/aq\nname: aq\nclasses:\n  AirQualityObserved:\n    slots: [temperature]\n" }
```

```json
{
  "linkml": "id: https://github.com/smart-data-models/dataModel.Environment/AirQualityObserved\nname: AirQualityObserved\n",
  "jsonSchema": { "$schema": "http://json-schema.org/draft-07/schema#", "title": "AirQualityObserved" },
  "context": { "@context": { "temperature": "https://example.org/aq/temperature" } },
  "docs": "# AirQualityObserved\n\n| Attribute | NGSI-LD kind | Range |\n",
  "shacl": "@prefix sh: <http://www.w3.org/ns/shacl#> .",
  "owl": "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
  "example": { "id": "urn:ngsi-ld:AirQualityObserved:hel.fi:air-quality:sensor-01", "type": "AirQualityObserved" },
  "generatorVersion": "linkml-1.8.0",
  "errors": []
}
```

The inference answer (DM-54): the model as source and as the operations the visual editor applies, the slots it typed and the ones it could not.

```json
{
  "linkml": "id: https://hel.fi/models/air-quality\nname: air_quality\nclasses:\n  AirQuality:\n    slots: [station_id, pm10, timestamp]\n",
  "operations": [
    { "op": "addClass", "name": "AirQuality" },
    { "op": "addSlot", "name": "station_id", "class": "AirQuality", "range": "string" },
    { "op": "addSlot", "name": "pm10", "class": "AirQuality", "range": "float", "slot_uri": "https://smartdatamodels.org/dataModel.Environment/pm10" },
    { "op": "setSlot", "name": "pm10", "field": "unit", "value": "GQ" },
    { "op": "setSlot", "name": "pm10", "field": "minimum_value", "value": 0 },
    { "op": "addSlot", "name": "timestamp", "class": "AirQuality", "range": "datetime" }
  ],
  "detectedTypes": { "station_id": "string", "pm10": "float", "timestamp": "datetime" },
  "matches": { "pm10": "dataModel.Environment/AirQualityObserved" },
  "untyped": [],
  "rows": 240
}
```

The editor's operations (DM-13) are `addClass`, `removeClass`, `renameClass`, `setClass`, `addSlot`, `removeSlot`, `renameSlot`, `attachSlot`, `detachSlot`, `setSlot`, `setTitle`, `addEnum` and `addEnumValue`, applied in order and all or nothing. A rename carries `to` and follows the element through the model: a renamed class is renamed in every `is_a` and every slot `range` that names it, a renamed slot in every class's slot list. An operation naming an element the model does not have, or a new name it already has, is refused with its index and the reason.

- `sdm-catalog` is the index the import wizard browses (DM-07): the subjects and their models, with
  the attribute names and descriptions the wizard searches. Model Tools caches it and refreshes it
  daily; `?refresh=true` asks for a refresh now, and an index Model Tools could not refresh is
  answered from the cache with `stale: true` rather than withheld (DM-12). The index carries no
  URLs: a model is named by its catalogue identifier, and fetching it is `import-sdm`.
- `refresh` is the only parameter the route takes, and the only thing a caller may steer: which
  catalogue is fetched is Model Tools' own allowlist (DM-10), never the request
  (`joinedcontext-portal/src/tools/model_tools.rs`). The index is passed through as Model Tools
  wrote it, so `attributes` is there for every model whose schema that build read and `[]` for the
  rest; the wizard narrows by subject and searches by attribute in the browser, over the one index
  it already holds.
- `linkml` is the LinkML source itself. `import-sdm` answers with it, because an import produces
  the document the editor then edits, and its `annotations` carry `spec.source.repository`,
  `spec.source.path` and `spec.source.commit` so the import is reproducible and its provenance
  reaches the manifest (DM-08). `generate` is given a source and does not echo one back.
- `import-sdm` takes a model **identifier** (`dataModel.Environment/AirQualityObserved`), never a
  URL. The allowlist that limits fetching to the Smart Data Models organisation lives in Model
  Tools (DM-10); the Portal refuses `400` for anything that is not an identifier so no caller can
  steer the fetch at all.
- Every artifact field is optional and absent when this Model Tools version does not render it. A
  compilation that fails is `200` with the messages in `errors[]`: a half-written model is the
  normal state of an editor, not a server error.
- `jsonSchema`, `context`, `docs` and `example` are the four artifacts DM-02 commits beside the
  source, and `jcctl model generate` writes exactly these (see [API/03 §4](03-jcctl.md)); `shacl`
  and `owl` are rendered in the same run for the artifact store (DM-44). `docs` is one Markdown
  page for the whole model, not a directory, and `example` is one entity in the key-value form the
  JSON Schema describes, validated against that schema and against the `@context` before it is
  answered (DM-21). An import answers with the catalogue's own example instead of a generated one:
  real data beats a value derived from a range.
- `generatorVersion` is the version that produced the artifacts. CI invokes the same image version
  as the preview (DM-19), so a preview and a committed artifact set can be compared.
- A source over 512 KiB is `413`, and a sample over 10 MiB the same. The routes are session routes
  and carry the CSRF token like every other mutating Portal call.
- `503` with `problem+json` when no Model Tools URL is configured or the container does not answer
  within the compile timeout. The editor then shows the source without a preview, not an error.

## 12. Static apps host (AP-12, AP-14, AP-17)

A `static` app is served by the Portal on its own host, `https://{name}.apps.{domain}/`
(AP-14, AP-133). The edge rewrites a request on that host to these paths of the static host,
which nothing else routes to:

```text
GET  /apps/{name}/                      the app's index.html
GET  /apps/{name}/{path}                any asset of the built bundle
POST /apps/{name}/api/functions/{fn}    one function of the served build, run in jc-functions (AP-84)
```

The app's data calls go to `/api/endpoint/{slug}/…` on its own host. The Portal does not serve
them: the edge route `app-{name}-endpoint` sets the App's session as the bearer and proxies them
to the Context Gateway, for the App's own endpoints only (Deployment/10, AP-133).

- Only an app whose manifest is `lifecycle: published` is reachable. A draft, a preview or a
  retired app is `404` — the same answer as a name that does not exist, so the host never
  discloses which apps are being worked on.
- Every response carries the app's own Content Security Policy, built from `spec.csp`:
  `default-src 'self'; connect-src 'self'; frame-ancestors {portal origin}` by default, with
  `connect-src` extended by `spec.csp.connectSrc`, `connect-src` and `img-src` by the project's
  basemap route prefix when the platform configures a basemap (its style URL is `basemap` in
  `#jc-config`, AP-67), and the origins of `spec.csp.frameAncestors`
  added to `frame-ancestors` only when `spec.embeddable: true` (AP-12). The Portal's own origin
  is always there, since "Open app" frames the App under the Portal's header (AP-122), unless
  Apps have no origin of their own (`JC_PORTAL_APPS_URL` unset): an App on the Portal's origin
  would reach into the Portal's page, so it keeps `frame-ancestors 'none'` (`'self'` when
  embeddable). It
  replaces the Portal's own CSP for these paths, and no `X-Frame-Options` is sent: its
  `SAMEORIGIN` would refuse the Portal, whose host is not the apps origin.
- The bundle is served from the app artifact root, one directory per app, and each directory
  carries an `integrity.json` written by the build lane: a map of bundle-relative path to the
  `sha384-…` Subresource Integrity digest of that file. The host verifies the digest of every
  file it serves and refuses `502` on a mismatch, so a modified artifact is never served under a
  published app's name. An app directory without `integrity.json` serves nothing (`404`): the
  integrity manifest is what makes the bundle publishable, not an optional extra.
- Paths are resolved inside the app's own directory. A traversal attempt (`..`, an absolute path,
  a symlink leaving the root) is `404`, never a read outside the root.
- Unknown paths inside a published app answer `404` rather than the app's `index.html`: a static
  app that wants client-side routing declares it in its build, and the host does not invent a
  fallback that would mask a missing asset.
- `POST /apps/{name}/api/functions/{fn}` runs the function `fn` of the served build's
  `functions.js`, integrity-checked like every other file, in `jc-functions`, with the caller's
  `X-Access-Token` as the one credential its data calls carry; an anonymous caller of a `public`
  app sends none (AP-84, SDK-23). The answer is the function's own status and JSON body, `500`
  with `{error: {message, file, line}}` when it throws. A name outside `[a-z][a-z0-9-]{0,39}`, an
  app that is not published or not the caller's to read, and a build with no such function are
  `404`; a body that is not JSON is `400`, one over 256 KiB `413`, a full runtime `429` with
  `Retry-After`. A call that carries the edge's token also carries `X-CSRF-Token` matching the
  `jc_csrf` cookie, or it is `403`: the edge sets the token from a cookie a cross-site form would
  send too. The host sets that cookie on the apps origin with a signed-in person's first index.

### 12a. The build of an application (AP-100, AP-103, ADR-N-028)

A `static` App whose source is its own repository on the forge (`spec.source.git`, AP-75) is
built there, by the repository's `.gitea/workflows/build.yml`. The App page reads where that
build is and asks for another one through two routes:

```text
GET  /api/v1/projects/{project}/apps/{name}/build      the repository, the latest run, the package
POST /api/v1/projects/{project}/apps/{name}/rebuild    dispatches build.yml on the default branch
```

`GET …/build` answers `200` for a person who may read the App:

```json
{
  "repositoryUrl": "https://forge.example/user/oauth2/keycloak?redirect_to=%2Fjoinedcontext%2Fhelsinki_city-bikes",
  "run": { "status": "completed", "conclusion": "success", "commit": "3f1c…", "url": "https://forge.example/user/oauth2/keycloak?redirect_to=…" },
  "packageUrl": "https://forge.example/user/oauth2/keycloak?redirect_to=%2Fjoinedcontext%2F-%2Fpackages%2Fgeneric%2Fapp-city-bikes%2F3f1c…",
  "rebuild": { "allowed": false, "reason": "Rebuild needs propose on App in project helsinki" }
}
```

- Every link carries the forge's sign-in, so a person without a forge session is offered the
  Keycloak button and lands on the page (PF-79, PF-81).
- The repository is `{project}_{app}` of the organization of the configuration repository
  (AP-75), derived from the names in the path and never read from the manifest's `url`.
- `run` is the newest run of the repository's workflows, or `null` before the first one;
  `packageUrl` names the package of `status.build.commit`, or is `null` while the App has no build.
- An App without `spec.source.git` has no build here: `repositoryUrl`, `run` and `packageUrl`
  are `null`, and `rebuild.reason` says the App is not built on the forge.
- `rebuild.allowed` is `true` for a person holding `propose` on `App` in the project; otherwise
  `reason` says what is missing (PF-50, UI-44).
- `404` for an App the caller may not read, the same answer as a name that does not exist
  (PF-59); `503` when no forge is configured.

`POST …/rebuild` takes no body and answers `202` once the forge accepted the dispatch of
`build.yml` on the repository's default branch; the run then appears in `GET …/build`. It is
refused `403` without `propose` on `App`, `404` as above, `409` for an App that is not built on
the forge, and `503` with the forge's reason when there is no forge or it refuses the dispatch.

## 13. Flows: running a blueprint (CC-24, CC-30, CC-31, CC-32, CC-59)

A flow is one instantiation of a Blueprint. The gallery lists the blueprints an organisation
publishes and the wizard turns the chosen one's parameter schema into a form; saving the form is
what produces the repository change, so the user never sees YAML or a merge request (CC-29).

```text
GET  /api/v1/blueprints                          the gallery (organization-level kind, section 4)
POST /api/v1/projects/{project}/flows            parameters in → 202 + Change
```

The gallery list is the ordinary organization-level collection, so it carries no new response
shape. What it does carry is a filter: the Portal returns only the blueprints whose
`spec.allowedRoles` intersect the caller's roles (CC-59). A blueprint a role may not run is
absent, not greyed out, and the same check runs again on `POST /flows`, because a list that
merely hides a card is not an authorisation.

```json
{
  "blueprint": "threshold-alert",
  "version": "1.2.0",
  "parameters": { "entityType": "AirQualityObserved", "thresholdValue": 50 }
}
```

- `blueprint` names an organization-level Blueprint; `version` is the version the form was
  generated from. A mismatch with the blueprint's current `spec.version` is `409`: the parameters
  were filled against a schema that has since changed, and silently expanding them against the new
  one is how a form produces a manifest nobody reviewed (CC-26).
- `parameters` is validated against `spec.parameterSchema` before anything is rendered. A
  violation is `400` with every failure listed at once in `problem.errors[]`, each naming its
  instance path, so the form can mark all its fields in one pass rather than one per round trip
  (CC-24). The wizard validates the same schema in the browser; the server check is the one that
  counts.
- On success the response is the usual `202` with a `Change` (section 4). All the manifests of one
  flow go into a single merge request, so they are reviewed and merged together or not at all
  (CC-32).
- The lane is the stricter of what the blueprint's `spec.riskClass` declares and what the rendered
  kinds are on their own terms (CC-59, CC-63). A Green blueprint whose template renders a `Policy`
  therefore lands in the Red lane; declaring a lane can narrow nothing that section 4 already
  calls Red.
- Every rendered manifest passes the same checks a hand-written one does. A template that renders
  a namespace other than the project the flow runs in is `400`, and so is a literal secret
  (MF-04, MF-24): a blueprint is authored once and run in many projects, so a namespace in a
  template is a way out of the project the caller chose.
- Expansion is `jcctl`'s, the same code the reconciler runs, never a second engine in the Portal
  (CC-25). Every rendered manifest carries `joinedcontext.com/blueprint`,
  `joinedcontext.com/blueprint-version` and `joinedcontext.com/blueprint-parameters`, which is
  what lets the Portal re-open a flow as the form that created it (CC-27, CC-32).
- `503` with `problem+json` when the Git forge is not configured. Everything the Portal can check
  on its own has passed by then, so a deployment without a forge fails loudly rather than
  reporting a change it never opened.

## 14. Activity (UI-31, OPS-48, OPS-49)

What is happening in a project, as one paged list and one live tail of the same query. The shape
of an event and where it comes from are
[Architecture/09 §6](../Architecture/09-portal.md#6-activity-what-is-happening).

```text
GET /api/v1/projects/{project}/activity            the list, newest first, paged
GET /api/v1/projects/{project}/activity/stream     the same filter, as Server-Sent Events
```

Both take the same query parameters, so a view switches between them without rewriting anything:

| Parameter | Meaning |
|---|---|
| `space` | one Context Space |
| `kind` | one or more event kinds, repeated or comma-separated |
| `source` | `reconciler`, `pipeline`, `gateway`, `broker`, `ckan`, `portal` |
| `severity` | `info`, `warning`, `error`; a value includes everything above it |
| `since` | RFC 3339 instant, the oldest event to return |
| `object` | one object the events belong to, as `{plural}/{name}`, for an object page |
| `limit`, `cursor` | page size and the opaque cursor of the previous answer |

```json
{
  "apiVersion": "joinedcontext.com/v1alpha1",
  "kind": "List",
  "items": [
    {
      "time": "2026-09-06T16:21:03Z",
      "project": "helsinki",
      "space": "air-quality",
      "kind": "access.denied",
      "source": "gateway",
      "summary": "An anonymous caller was refused a write to AirQualityObserved.",
      "severity": "warning",
      "correlationId": "4bf92f3577b34da6a3ce929d0e0e4736",
      "details": { "endpoint": "public-air", "operation": "updateAttrs", "rule": "public-read" }
    }
  ],
  "next": "b3RoZXItcGFnZQ"
}
```

The stream sends the same objects as `data:` lines of named events, one per activity kind, so a
browser subscribes to the kinds it draws:

```text
event: access.denied
data: {"time":"2026-09-06T16:21:03Z","project":"helsinki", … }

: keep-alive
```

- A viewer of the project reads it and nobody else; there is no cross-project activity route.
- `summary` is localised to the request's `Accept-Language`, the rest of the record is not: an
  event kind and an endpoint slug are identifiers, not prose.
- `details` never carries a request body, a header, a token or an entity attribute value
  (OPS-48). A field that would have carried one is absent, not empty.
- Events live seven days and their per-minute counters ninety (OPS-49), so `since` older than the
  retention window returns what is left rather than an error.
- The stream sends a comment line as a keep-alive every twenty seconds and closes on the
  Portal's shutdown; a client reconnects with `since` set to the last event it saw, which is why
  `time` is part of every record.
- `404` with `problem+json` when the project does not exist or the caller is not a member of it,
  never `403`: an activity route that distinguishes the two says which projects exist (R20).

### Ingest, for the collector only

```text
POST /api/v1/activity        OTLP log records, application/json
```

The OpenTelemetry Collector ([Deployment/05 §5](../Deployment/05-monitoring-logging.md#5-the-activity-pipeline))
posts here, one batch a request, as an OTLP `ExportLogsServiceRequest` whose every log record
carries the event's fields as its attributes. The route sits outside the project API on purpose:
a record names its own project in its attributes, and the collector is a member of no project and
must not be given one.

- The caller is a Keycloak ServiceAccount client whose token is bound to this audience; a human
  token is refused. A caller that is neither gets `401`, a caller with the wrong audience `403`.
- No APISIX route publishes it, so it is reachable only from inside the cluster (OPS-48).
- A record whose `project` is unknown, whose `kind` is outside the vocabulary of
  [Architecture/09 §6](../Architecture/09-portal.md#6-activity-what-is-happening), or whose
  attributes fail validation is rejected on its own. The batch still succeeds: one malformed
  record must not cost the other four hundred.
- The answer is the OTLP `ExportLogsServiceResponse`, so the collector reads rejections with the
  code it already has rather than a shape invented here:

  ```json
  { "partialSuccess": { "rejectedLogRecords": 2, "errorMessage": "kind not in the vocabulary" } }
  ```

- The Portal validates what it is handed. The collector strips attributes, which is a redaction
  step and not a trust boundary; the boundary is this route.

## 15. Branding (UI-30, OPS-46)

One image serves every installation. The deployment renders `global.branding`
([Deployment/12](../Deployment/12-branding-and-naming.md)) into a ConfigMap, mounts it and names
it in `JC_BRANDING_FILE`; the Portal reads that file and answers:

```text
GET /api/v1/branding             the block, public and cacheable
GET /api/v1/branding/logo        the logo file, from the same mount
GET /api/v1/branding/favicon     the favicon file, from the same mount
```

```json
{
  "instanceName": "Banská Bystrica Context",
  "shortName": "BB Context",
  "organisation": "Mesto Banská Bystrica",
  "contactEmail": "opendata@example.org",
  "logo": "logo.svg",
  "colours": { "primary": "#0000bf", "secondary": "#0072c6", "accent": "#ffe977", "background": "#ffffff", "text": "#1a1a1a" },
  "fonts": { "heading": "HelsinkiGrotesk, system-ui, sans-serif", "body": "system-ui, sans-serif" },
  "languages": { "default": "sk", "offered": ["sk", "en"] },
  "primaryForeground": "#ffffff",
  "primaryDark": "#3666d7",
  "primaryForegroundDark": "#ffffff"
}
```

- All three routes are unauthenticated on purpose: the login page needs the name and the logo
  before anyone has signed in, and the block holds no secret. They answer `Cache-Control: public,
  max-age=300`, the only API answers a browser may keep.
- Every colour is validated as a hex triplet or sextet; anything else is replaced by the neutral
  default before it is served, because the UI writes these values into CSS custom properties
  (OPS-46). `primaryForeground` is computed from the primary colour rather than authored, so text
  on a light brand colour stays readable.
- `primaryDark` and `primaryForegroundDark` are the same pair for the dark theme, and are computed
  too. A dark page cannot paint a button in the brand colour as it was configured — a navy button
  on a navy page is not a button — so the theme lightens it, and the readable text is then the
  readable text on *that* colour, not on the configured one. Both are computed in one place, here,
  because the choice needs the contrast ratio of the lightened colour: the UI wrote a near-black
  label on it by rule instead, which left an installation branded `#111827` at 2.31:1 and one
  branded `#0000bf` at 3.43:1 (T-2324, UI-30). A value for either in the file is overwritten.
- The logo and the favicon are file names, never URLs. A value carrying a scheme, a host or `..`
  is dropped, and the file is read from the branding file's own directory: the two assets the
  ConfigMap carries are the only files those routes can reach.
- A branding file that is missing, unreadable or not valid YAML is not an error: the Portal logs
  the reason and answers the neutral defaults, so an installation whose ConfigMap has not been
  rendered looks plain rather than failing to load. The two asset routes have nothing to fall back
  to and answer `404` with `problem+json` when the block names no logo or favicon, or the file
  behind the name is not readable (`joinedcontext-portal/src/api/branding.rs`); a page renders its
  own mark then, and never a broken image.

## 16. Open-data catalogue status (EP-62…EP-67)

A `CkanInstance` is a manifest, so a catalogue is configured through the resource API like
everything else (`POST /api/v1/projects/{project}/ckaninstances`), which makes it a change
proposal a steward approves rather than a setting somebody flips. What needs a route of its own is
the picture across both kinds:

```text
GET /api/v1/projects/{project}/ckan/status    catalogues, and what each endpoint publishes
```

```json
{
  "instances": [
    {
      "name": "open-data",
      "url": "https://data.banskabystrica.sk",
      "organizationDefault": "mesto-banska-bystrica",
      "apiTokenRef": "ckan-open-data"
    }
  ],
  "publications": [
    {
      "endpoint": "ovzdusie-public",
      "phase": "Live",
      "instance": "open-data",
      "instanceMissing": false,
      "organization": "mesto-banska-bystrica",
      "dataset": "kvalita-ovzdusia",
      "datasetUrl": "https://data.banskabystrica.sk/dataset/kvalita-ovzdusia",
      "resources": [
        { "name": "NGSI-LD API", "url": "https://{host}/api/endpoint/{endpointSlug}/ngsi-ld/v1/", "format": "NGSI-LD" },
        { "name": "CSV", "url": "https://{host}/api/endpoint/{endpointSlug}/file.csv", "format": "CSV" }
      ],
      "datastore": { "representation": "csv", "refresh": "onChange" }
    }
  ]
}
```

- The dataset shown is the dataset the reconciler would write: both are rendered by the same code,
  so the monitor cannot drift from the publisher (EP-63, EP-64).
- `apiTokenRef` is the name of the secret, never its value. No CKAN call is made to build this
  answer and no credential is read (EP-67).
- An endpoint whose `instanceRef` names a catalogue this project does not have is reported with
  `instanceMissing: true` and no dataset URL, because a dangling reference is the misconfiguration
  a steward has to see.
- The route needs a session, like every other project route.

## 16a. The catalogue (EP-81, EP-82)

The platform-wide catalogue page of [Architecture/21 §6](../Architecture/21-open-data-catalogue.md#6-the-portals-catalogue-page)
reads these routes. They need no session and answer `Cache-Control: public, max-age=60`: what
they carry is what the public catalogue already shows.

```text
GET /api/v1/catalogue                          search, facets and one page of datasets
GET /api/v1/catalogue/datasets/{name}          one dataset
GET /api/v1/catalogue/datasets/{name}/sample   up to ten rows, read through its Endpoint
```

`GET /api/v1/catalogue` takes `q` (full text, passed to CKAN), the facet filters `publisher`,
`theme`, `format`, `licence`, `spatial` and `year` (each repeatable; values of one filter are
alternatives, filters combine with AND) and `page` (from 1, twenty datasets a page):

```json
{
  "total": 1,
  "page": 1,
  "pageSize": 20,
  "datasets": [
    {
      "name": "bbsk-kpi",
      "title": "Ukazovatele kraja",
      "notes": "Ukazovatele Banskobystrického samosprávneho kraja…",
      "publisher": { "name": "bbsk", "title": "Banskobystrický samosprávny kraj" },
      "licence": { "id": "cc-by", "title": "Creative Commons Attribution" },
      "formats": ["CSV", "JSON", "NGSI-LD"],
      "themes": ["ECON"],
      "modified": "2026-09-21T05:52:34Z"
    }
  ],
  "facets": {
    "publisher": [{ "value": "bbsk", "label": "Banskobystrický samosprávny kraj", "count": 1 }],
    "theme": [{ "value": "ECON", "label": "Economy and finance", "count": 1 }],
    "format": [{ "value": "CSV", "label": "CSV", "count": 1 }],
    "licence": [{ "value": "cc-by", "label": "Creative Commons Attribution", "count": 1 }],
    "spatial": [],
    "year": []
  },
  "unavailable": []
}
```

- The Portal calls `package_search` on the distinct `spec.url` of every `CkanInstance` of the
  installation, with no API token, and drops any dataset marked `private`: an anonymous CKAN
  caller sees public datasets only, so the answer cannot list a restricted one (EP-67, EP-69).
- Facet counts are over the datasets that match `q` and every other facet's filter.
- A catalogue that does not answer is named in `unavailable` and the others still answer; when
  none answers, the route answers `503` with `problem+json`, as every Portal route whose upstream is down does. No `CkanInstance` at all is an empty
  catalogue, `200` with `total: 0`.

`GET /api/v1/catalogue/datasets/{name}` answers the dataset page:

```json
{
  "name": "bbsk-kpi",
  "title": "Ukazovatele kraja",
  "notes": "…",
  "keywords": ["ukazovatele", "kraj"],
  "publisher": { "name": "bbsk", "title": "Banskobystrický samosprávny kraj" },
  "licence": { "id": "cc-by", "title": "Creative Commons Attribution", "url": "https://creativecommons.org/licenses/by/4.0/" },
  "frequency": "http://publications.europa.eu/resource/authority/frequency/MONTHLY",
  "themes": [{ "code": "ECON", "label": "Economy and finance" }],
  "spatial": ["SK032"],
  "temporal": { "start": "2020-01-01", "end": null },
  "contact": { "name": "Open data desk", "email": "opendata@example.org" },
  "modified": "2026-09-21T05:52:34Z",
  "catalogueUrl": "https://data.{host}/dataset/bbsk-kpi",
  "resources": [
    { "name": "CSV", "format": "CSV", "url": "https://{host}/api/endpoint/{endpointSlug}/file.csv", "description": "…", "previewUrl": "https://data.{host}/dataset/bbsk-kpi/resource/{id}" }
  ],
  "endpoint": { "url": "https://{host}/api/endpoint/{endpointSlug}/", "representations": ["ngsi-ld", "csv", "mcp"] },
  "model": {
    "name": "key-performance-indicator",
    "classes": [{ "name": "KeyPerformanceIndicator", "description": "…" }],
    "docsUrl": "https://{host}/api/endpoint/{endpointSlug}/schema/1/key-performance-indicator.v1.md"
  }
}
```

- `previewUrl` is set on a resource with an active DataStore sheet (§3 of Architecture/21).
- `endpoint` and `model` are set only when the dataset's `endpoint` extra names an Endpoint of this
  installation whose audience is `public`: the Portal parses the slug out of the extra, finds the
  Endpoint in its mirror and builds the URL on its own host. `docsUrl` is the dataset's Markdown
  schema resource. A dataset whose extra names another host, or no Endpoint, has neither.
- `representations` are the Endpoint's `enabledRepresentations`; the "Use this data" snippets
  offer only what it serves.
- An unknown or private dataset answers `404`: a caller cannot tell the two apart. When no
  catalogue answers at all, `503`.

`GET /api/v1/catalogue/datasets/{name}/sample` answers up to ten entities of the Endpoint's first
model class, read anonymously through its NGSI-LD representation with `options=keyValues`, as
`{ "type": "KeyPerformanceIndicator", "columns": ["id", "name", "value"], "rows": [["urn:…", "…", "12"]] }`.
A dataset with no Endpoint of this installation, or one that does not serve `ngsi-ld`, answers
`404`; an Endpoint that does not answer, `503`. Nested values are written as compact JSON.

## 16b. Publish a dataset in one step (EP-83)

```text
POST /api/v1/projects/{project}/catalogue/drafts    {"endpoint": "bbsk-kpi"}
```

Drafts what the publish flow of [Architecture/21 §7](../Architecture/21-open-data-catalogue.md#7-publish-a-dataset-in-one-step)
proposes; it writes nothing. The caller needs `propose` on `Endpoint` in the project.

```json
{
  "endpoint": "bbsk-kpi",
  "makesPublic": false,
  "catalog": {
    "license": "CC_BY_4_0",
    "themes": ["ECON"],
    "keywords": { "sk": ["ukazovateľ", "hodnota"] },
    "temporal": { "start": "2020-01-01" },
    "publisher": { "name": { "sk": "Banskobystrický samosprávny kraj" } },
    "contactPoint": { "name": "Open data desk", "email": "opendata@example.org" }
  },
  "publish": { "ckan": { "instanceRef": { "kind": "CkanInstance", "name": "bbsk" } } },
  "missing": ["spatial", "frequency"]
}
```

- `catalog` is the drafted `spec.catalog` (EP-78) and `publish` the drafted `spec.publish`
  (EP-62); a block the Endpoint already declares is returned as it is, so re-running the flow
  never overwrites what a steward wrote. `missing` names the catalogue fields nothing could fill;
  `spatial`, `temporal` and `frequency` are never drafted.
- `makesPublic` is `true` when the Endpoint's audience is not `public`: the UI then says so before
  the proposal, and the Change the UI proposes with `spec.audience: public` takes the red lane
  with a publisher's approval (EP-76, PF-72).
- The UI proposes the Change through the resource API (`PUT …/endpoints/{name}`, §4) with the two
  blocks merged into the Endpoint's manifest.
- `404` for an unknown Endpoint; `409` naming `CkanInstance` when the project has none to publish to.

## 17. Federation registrations and the graph (MF-36, UI-27, UI-28, EP-71, PF-48)

A `ContextSourceRegistration` is a manifest, so it is listed, created and removed through the
resource routes every kind shares. Its plural is `csrs`:

```text
GET    /api/v1/projects/{project}/csrs            every registration in the project
GET    /api/v1/projects/{project}/csrs/{name}     one registration
POST   /api/v1/projects/{project}/csrs            propose a new one
PUT    /api/v1/projects/{project}/csrs/{name}     propose a change to one
DELETE /api/v1/projects/{project}/csrs/{name}     propose its removal
```

A write answers `202` with a `Change` like any other manifest, and a federation edge always
takes the Red lane: it makes one tenant's data answerable in another, which is a decision a
steward signs (CC-63). The manifest lands at `projects/{project}/spaces/{space}/registrations/{name}.yaml`.

What needs a route of its own is the picture across five kinds at once:

```text
GET /api/v1/projects/{project}/federation-graph   who reads whose data, as nodes and edges
```

```json
{
  "nodes": [
    { "id": "ContextSpace/hub", "kind": "ContextSpace", "name": "hub", "health": "ok", "phase": "Live" },
    {
      "id": "ContextSourceRegistration/zvolen-ovzdusie",
      "kind": "ContextSourceRegistration",
      "name": "zvolen-ovzdusie",
      "health": "degraded",
      "phase": "Error",
      "registration": {
        "mode": "inclusive",
        "identity": "caller",
        "types": ["AirQualityObserved", "WeatherObserved"],
        "external": true
      }
    },
    {
      "id": "ExternalSource/zvolen-ovzdusie",
      "kind": "ExternalSource",
      "name": "zvolen-ovzdusie",
      "health": "unknown"
    }
  ],
  "edges": [
    {
      "from": "ContextSourceRegistration/zvolen-ovzdusie",
      "to": "ContextSpace/hub",
      "kind": "registers",
      "manifest": "ContextSourceRegistration/zvolen-ovzdusie"
    }
  ]
}
```

- A node id is `kind/name`, so a selection survives a refetch and two manifests naming the same
  object produce one node.
- `kind` is a manifest kind, or `ExternalSource` for a source outside this platform. A `CkanInstance`
  is a node when an Endpoint of the project publishes to it (Architecture/04 §7); its card carries no
  URL and no token. An external
  node is named after the registration that reaches it and never after its address, which is the
  rule provenance already follows (EP-71).
- `health` is `ok`, `degraded` or `unknown`, read off the phase the object last reported. Anything
  still converging is `unknown` rather than `ok` (UI-27).
- `phase` is the lifecycle phase the object last reported (`Draft`, `Pending`, `Deploying`, `Live`,
  `Error`), what the card's status chip shows (UI-25). It is absent for an external source and for
  an object that has reported nothing.
- `kind` on an edge is `registers`, `serves`, `feeds`, `consumes` or `publishes`, and `manifest`
  names the file the edge was read from so a reader can open it. `publishes` leaves an Endpoint for
  the `CkanInstance` its `spec.publish.ckan.instanceRef` names.
- A registration whose target has left the repository still draws its edge, with no node at the
  other end: a dangling reference is what this view exists to make visible.
- Nothing secret is in the answer by construction rather than by filtering. A card says that a
  registration authenticates and how, never with what: no token, no resolved `secretRef` and no
  `serviceAccountRef` name (PF-48).
- The graph is a projection of the manifests plus reported health. It holds no state and is not a
  second opinion about who talks to whom.
- Every route of this section needs a session, like every other project route.

## 18. Assistant catalog search (AG-58, UI-46)

The question a person asks the assistant, answered from the mirror (Architecture/09 §9). The same
call is the assistant's `search_catalog` tool, so a run and a person get the same answer:

```text
GET /api/v1/projects/{project}/assistant/catalog?q=bike%20availability&scope=Endpoint
```

```json
{
  "q": "bike availability",
  "items": [
    {
      "kind": "Endpoint",
      "name": "helsinki-bikes",
      "space": "helsinki",
      "owner": "helsinki",
      "title": "Helsinki city bikes",
      "endpointSlug": "si6epqkx364lprho5uaigutk274r5grb",
      "matchReason": ["title", "description"],
      "access": { "verdict": "allowed", "reason": "audience public" },
      "freshness": { "pipeline": "hsl-bikes", "scrapedAt": "2026-09-13T07:41:02Z", "received": 1200, "errors": 0 }
    },
    {
      "kind": "ContextSpace",
      "name": "helsinki",
      "space": "helsinki",
      "owner": "helsinki",
      "matchReason": ["endpoint helsinki-bikes"],
      "access": { "verdict": "allowed", "reason": "endpoint helsinki-bikes admits you" },
      "freshness": null
    }
  ]
}
```

- `q` is required and is split into words of two characters or more, less the function words of a
  request (`the`, `a`, `to`, `and`, `new`, …); an empty `q` is `400`. A word matches a field when one
  of the field's own words begins with it: `bike` matches "city bikes", `the` does not match
  "weather". `scope` narrows to one kind. At most twenty items are returned, the best matches first.
- `matchReason` names the fields that matched (`name`, `title`, `description`, `labels`, `slug`,
  `classes`) or the endpoint through which a space or a model matched.
- `access.verdict` is `allowed` or `restricted` with the reason beside it; a restricted item carries
  its `kind`, `name`, `space` and `owner` only. The verdict comes from the endpoint's audience; the
  data's own grants are `GET …/access` on the endpoint (EP-55).
- `freshness` is the runner's counters for the pipeline that feeds the endpoint (§7), read when the
  search runs, or `null` when nothing feeds it or the runner does not answer within the scrape
  timeout. It is never a guess.
- A run publishes the same body as the `output` of a `tool` event named `search_catalog`
  (04-agent-runs §4), which the conversation renders as cards (UI-46).

## 19. Assistant endpoint proposal (EP-72)

The share request, rendered but not written: the same call the assistant's `propose_endpoint`
tool makes (Architecture/04 §5). The caller must be allowed to propose an Endpoint in the project
(PF-50), or the answer is `403`.

```text
POST /api/v1/projects/{project}/assistant/propose-endpoint
```

```json
{
  "contextSpace": "helsinki",
  "name": "bikes-regional-transport",
  "audience": "project-list",
  "allowedProjects": ["regional-transport"],
  "representations": ["ngsi-ld", "geojson"],
  "hiddenAttributes": ["maintenanceNote"],
  "entityTypes": ["BikeHireDockingStation"]
}
```

```json
{
  "lane": "yellow",
  "slug": "k7m2p9q4r6s8t3v5w7x2y4z6a8b3",
  "endpoint": { "apiVersion": "joinedcontext.com/v1alpha1", "kind": "Endpoint", "metadata": { "name": "bikes-regional-transport", "namespace": "helsinki" }, "spec": { "contextSpaceRef": "helsinki", "slug": "k7m2p9q4r6s8t3v5w7x2y4z6a8b3", "audience": "project-list", "allowedProjects": ["regional-transport"], "enabledRepresentations": ["ngsi-ld", "geojson"], "projection": { "hiddenAttributes": ["maintenanceNote"] } } },
  "policies": [ { "apiVersion": "joinedcontext.com/v1alpha1", "kind": "Policy", "metadata": { "name": "bikes-regional-transport-regional-transport", "namespace": "helsinki" }, "spec": { "contextSpaceRef": { "kind": "ContextSpace", "name": "helsinki" }, "assigner": "did:web:hel.fi", "assignee": { "kind": "group", "id": "regional-transport" }, "operations": ["retrieveOps"], "information": [ { "entities": [ { "type": "BikeHireDockingStation" } ] } ] } } ],
  "prefill": { "name": "bikes-regional-transport", "contextSpaceRef": "helsinki", "slug": "k7m2p9q4r6s8t3v5w7x2y4z6a8b3", "audience": "project-list", "allowedProjects": ["regional-transport"], "enabledRepresentations": ["ngsi-ld", "geojson"], "hiddenAttributes": ["maintenanceNote"] }
}
```

- `audience` defaults to `project-list`; `project-list` needs at least one project in
  `allowedProjects`; `representations` defaults to `ngsi-ld` and `geojson`; every name is a
  DNS-1123 label and every attribute an identifier, or the answer is `400`.
- The slug is minted here and is read-only in the form; a slug in the request is ignored.
- `lane` is what the Endpoint's Change would be classified as (§5): `red` for `public`.
- Nothing is written. A run publishes this body as the `output` of a `tool` event named
  `propose_endpoint` and follows it with a `navigate` to `/projects/{project}/endpoints`
  carrying `prefill` (04-agent-runs §4); the person's submission is the Change.

## 20. Drift: what the platform holds and Git does not declare (CC-21, CC-38, UI-25, UI-26)

Configuration cannot drift: every component reads it from the repository, so the repository is
what it is running (CC-72). What can drift is the one live state Git describes and nothing
reloads by itself — a space's seed entities. The Portal compares them on its own tick, the same
comparison `jcctl drift` makes, and serves the result per project.

```text
GET  /api/v1/projects/{project}/drift                         what drifted, with the two resolutions
POST /api/v1/projects/{project}/drift/{space}/{id}/revert     write Git's entity back into the broker
POST /api/v1/projects/{project}/drift/{space}/{id}/adopt      propose the live entity as the declared one
```

`{id}` is the entity's URN, percent-encoded. The list answers what the last tick found, with the
instant it ran at, so a page renders without waiting on the broker:

```json
{
  "apiVersion": "joinedcontext.com/v1alpha1",
  "kind": "List",
  "metadata": { "observedAt": "2026-09-17T09:12:03Z" },
  "items": [
    {
      "space": "ovzdusie",
      "id": "urn:ngsi-ld:AirQualityObserved:banskabystrica.sk:ovzdusie:stanica-1",
      "drift": "MODIFIED",
      "diff": [{ "path": "airQualityIndex.value", "declared": 42, "live": 7 }],
      "resolutions": ["revert", "adopt"],
      "source": "projects/mesto/spaces/ovzdusie/entities/seed/stanice.json"
    }
  ]
}
```

`drift` is `MODIFIED` when the broker holds the entity and an attribute the file declares
differs, and `MISSING` when the broker does not hold it at all. There is no `UNEXPECTED`: a space
holds what its pipelines and its devices write, and an entity nobody seeded is data, not drift
(CC-07, CC-69). Which attributes Git owns is the same answer: the ones the seed file declares,
and no others — live telemetry beside a seeded entity never drifts.

**Revert** upserts the declared entity through the space surface under the Portal's own
ServiceAccount and answers `204`; it writes only the attributes the file declares and never
deletes an entity or an attribute (CC-19).

**Revert** and **adopt** are the two resolutions UI-26 puts on the screen, and **adopt** is the
only way an out-of-band value becomes durable: it answers `202` and an ordinary `Change`
proposing the live entity as the seed file's content, reviewed in the lane its content earns like
any other change (CC-38). An entity the broker no longer holds cannot be adopted, and the answer
says so rather than proposing an empty file.

Both refuse with `403` unless the caller may `propose` `Entity` in that project; revert is a
write to the live space and adopt is a write to the repository, so neither is a read.

## 21. Operations and the Portal MCP (AG-59, AG-60, AG-61, AG-62, AG-77)

One registry behind every door (ADR-N-021). An operation lets through whom the REST route of the same action lets through (PF-50, AG-77): `jc_resource_list` and `jc_resource_get` any signed-in person, `jc_resource_propose` and `jc_resource_delete` a binding with `propose` or `delete` on the kind, `jc_change_approve` and `jc_change_reject` a binding with `approve`, on the change's kind once the change is read; any other operation its verb on its kind, or a grant in the project when it names no verb. A refusal is `403` naming the verb and the kind, the same words as the route's, except that a removal of a resource the caller may not read answers the `404` of a name that does not exist, so a removal never tells whether something is there (R20, PF-59); input is validated against the operation's schema with unknown fields refused (`422`, the schema path). `GET …/ops` lists exactly the operations the caller would be let through. A `verdict_required` refusal names the check to run and why in `reason` (`verdict_absent`, `verdict_failed` or `stale`) and says it in `detail`, one sentence a page shows as it is; a form writes the draft it shows before it proposes that draft, so a proposal never takes an older manifest than the one on screen.

```text
GET  /api/v1/projects/{project}/ops
  → 200 [{ "name": "jc_datasource_check", "title": "…", "description": "…",
           "inputSchema": {…}, "outputSchema": {…},
           "annotations": { "readOnlyHint": true, "destructiveHint": false, "idempotentHint": true },
           "lane": "green" }, …]          # only what this caller may run

POST /api/v1/projects/{project}/ops/{name}
  body: the operation's input; a draft may be named instead of a manifest:
        { "draft": { "kind": "DataSource", "name": "hsl-citybikes-free" } }
  → 200 the operation's output (a check answers a Verdict)
  → 202 a proposal: { "changeId": "…", "lane": "yellow", "url": "…" }
  → 409 { "error": "verdict_required", "check": "jc_datasource_check", "reason": "stale",
          "detail": "The draft changed since its check; check it again, then propose it." }
  → 403 { "error": "forbidden", "role": "steward" }
  → 422 { "error": "invalid_input", "path": "/spec/http/url", "message": "…" }

Verdict:
  { "ok": false, "findings": [{ "level": "error", "path": "/spec/http/url", "message": "…" }],
    "trace": {…}, "checkedAt": "2026-09-13T10:00:00Z", "inputDigest": "sha256:…" }

Drafts (also operations: jc_draft_put, jc_draft_get, jc_draft_drop):
  { "project": "helsinki", "kind": "DataSource", "name": "hsl-citybikes-free",
    "manifest": {…}, "verdict": {…} | null, "version": 7,
    "touchedBy": "jana.kovacova", "touchedKind": "person" | "api-key" | "mcp" | "run",
    "updatedAt": "…" }                                 # the REST routes are §4
  Draft changes are `draft` events on the activity stream (§7 of Architecture/09).
  jc_draft_list (GET /projects/{project}/drafts) answers one line per draft and never the
  manifest or the verdict's trace, the way jc_resource_list answers a line per resource:
  { "items": [{ "kind": "DataSource", "name": "hsl-citybikes-free", "version": 7,
                "touchedBy": "jana.kovacova", "touchedKind": "person", "updatedAt": "…",
                "verdict": { "ok": true, "findings": 0, "checkedAt": "…" } | null }] }
  A caller that needs a draft reads it with jc_draft_get. A project holding 44 drafts answered
  2.3 MB of manifests and verdict traces, which is more than one model call can carry, so the
  assistant could answer nothing at all while those drafts existed (T-2248).

Resources (AG-77): one operation per action for every kind the resource API serves, the
function behind the REST route of that action. A proposal, a deletion and a rejection answer
the Change the route answers, wrapped with its id, lane and merge request; a refusal is the
route's problem document.
  jc_resource_list     { "kind": "Pipeline", "space": "helsinki" }            # space optional
    → 200 { "items": [{ "kind": "Pipeline", "name": "bikes-hsl", "space": "helsinki",
                        "title": "…", "phase": "Ready", "sourceUrl": "…" }] }
    → 422 { "error": "invalid_input", "path": "/kind", "message": "'Bikes' is not a kind …; the kinds are …" }
  jc_resource_get      { "kind": "Endpoint", "name": "helsinki-bikes" }
    → 200 the manifest with its status; secret values never, `secretRef` names only
    → 404 problem: "Endpoint 'helsinki-bike' not found in project 'helsinki'; it has helsinki-bikes, …"
  jc_resource_propose  { "manifest": { "apiVersion": "…", "kind": "Pipeline",
                                       "metadata": { "name": "bikes-hsl" }, "spec": { … } } }
                                                             # or { "draft": { "kind", "name" } }
                       { "manifest": {…}, "files": { "./tests/x.input.json": "…" } }   # §4 rules
    → 202 { "changeId": "chg-00000081", "lane": "yellow", "url": "…/pulls/81",
            "change": { "kind": "Change", "status": { "plan": { "create": 0, "update": 1, "delete": 0 }, … } } }
    → 409 { "error": "verdict_required", "check": "jc_manifest_dry_run", "reason": "stale",
            "detail": "The draft changed since its check; check it again, then propose it." }   # a named draft, strict
    → 409 { "error": "verdict_required", "check": "jc_manifest_dry_run", "reason": "verdict_absent",
            "detail": "The manifest has not been checked; check it, then propose it." }   # a bare manifest never checked, strict
    → 400 problem: "literal secret in field 'token' is forbidden; use secretRef instead (MF-24)"
    → 403 problem naming the kind and the verb the caller lacks (PF-50)
  jc_resource_delete   { "kind": "Endpoint", "name": "helsinki-bikes-ops", "confirm": "helsinki-bikes-ops" }
    → 202 { "changeId": "chg-00000082", "lane": "red", "url": "…", "change": { … "plan": { "delete": 1 } } }
    → 409 { "error": "referenced", "detail": "2 dependent resources block deletion: Pipeline bikes-hsl and 1 in other projects",
            "by": [{ "kind": "Pipeline", "name": "bikes-hsl" }], "elsewhere": 1 }
    → 400 problem: "confirm must be the resource's name, 'helsinki-bikes-ops' (CC-39)"
  jc_change_reject     { "id": "chg-00000081", "reason": "The schedule stays hourly." }
    → 202 { "changeId": "chg-00000081", "lane": "yellow", "url": "…", "change": { … "phase": "Rejected" } }
  An assistant or application run calling jc_change_approve or jc_change_reject is refused
  (AG-11): 403 problem "an agent never approves or rejects a change; a person does (AG-11)".
  Five more operations are the person's in the same way, refused for a run whatever its profile
  names and so absent from its `GET …/ops` and its `tools/list`: jc_run_create, jc_run_cancel and
  jc_run_publish (a run does not drive another run), jc_run_answer (a run does not answer the
  question a run asked the person it acts for, AG-45), and jc_service_account_key_mint,
  jc_service_account_key_rotate and jc_service_account_key_revoke (a run does not mint or retire
  the credentials the platform authenticates with). Each refusal names its own act. Proposing a
  deletion is not among them: jc_resource_delete and jc_project_delete stay open to a run and to
  an MCP client, because a deletion is a Red change a person still approves (AG-77, CC-39).
  The rejection's reason is written on the merge request beside who rejected it; the REST route
  takes it as `{ "reason": "…" }` too.
  A run reaches this registry through the proxy's `/v1/mcp`, which the Portal serves on its
  internal listener as `POST /internal/agent-runs/{run}/mcp`: the call runs as the person who
  started the run and is narrowed again by the run's `AgentProfile` (AG-70), so `tools/list`
  answers only what both halves allow and a `tools/call` outside the profile is refused naming
  it. A profile never widens: an operation the person may not run stays refused whether the
  profile names it or not.

Example, an MCP client removing an endpoint:
  POST /api/v1/mcp
  { "jsonrpc": "2.0", "id": 7, "method": "tools/call",
    "params": { "name": "jc_resource_delete",
                "arguments": { "project": "helsinki", "kind": "Endpoint",
                               "name": "helsinki-bikes-ops", "confirm": "helsinki-bikes-ops" } } }
  → { "jsonrpc": "2.0", "id": 7, "result": { "isError": false, "structuredContent": {
      "changeId": "chg-00000082", "lane": "red", "url": "…", "change": { … } } } }

MCP (Streamable HTTP, protocol 2026-07-28):
  POST /api/v1/mcp                         # server/discover, tools/*, resources/*, prompts/*, tasks/*
  GET  /.well-known/oauth-protected-resource/api/v1/mcp   # RFC 9728
  Bearer only, aud = the Portal; 401 + WWW-Authenticate: Bearer resource_metadata="…" otherwise.
  The revisions this server speaks are `2026-07-28`, `2025-11-25`, `2025-06-18` and `2025-03-26`.
  `initialize` and `server/discover` answer the client's own revision when it names one of them
  and `2026-07-28` otherwise — never the client's string for a revision the server does not
  implement, which would move the disagreement from the handshake to the first unknown method.
  tools/list = the registry as GET …/ops shows it to this caller.
  resources/list and resources/read serve, for the caller's own bindings (AG-60):
    jc://schemas/{Kind}                       the kind's JSON Schema
    jc://{project}/{plural}/{name}            one manifest
    jc://{project}/drafts/{Kind}/{name}       one draft
    jc://{project}/changes/{changeId}         one change with its plan, redacted as the route
                                              redacts it (CC-06)
    jc://{project}/datamodels/{name}/linkml   the model's LinkML source. The JSON Schema and the
                                              `@context` are the endpoint façade's renderings of
                                              it and are read there (EP-47).
  A URI the caller may not read answers `-32002 resource not found`, the same as one that names
  nothing.
  Grounding (AG-12, CC-47): every `tools/call` result — an answer, a conflict, a refusal, an
  elicitation and a task's `tasks/result` — carries in `_meta` the state of the configuration it
  was evaluated against, so an agent can tell a fresh answer from a stale one without asking again:
    "_meta": { "joinedcontext.com/grounding": {
      "revision": "<the commit the Portal's mirror holds, null before the first sync>",
      "syncedAt": "<UTC RFC 3339 of that sync, null before the first>",
      "evaluatedAt": "<UTC RFC 3339 of this answer>",
      "drift": "none" | "sync-failed" | "unsynced" } }
  `drift` is the mirror against the repository: `unsynced` before the first sync, `sync-failed`
  when the last sync did not complete (the answer is from `revision`, which may be behind the
  repository), `none` otherwise. It never carries the repository's URL, a branch or a token.
  Elicitation (AG-63): a call whose operation takes the Yellow or Red lane, or carries
  `destructiveHint`, never runs on the agent's word. The first `tools/call` runs nothing and
  answers
    { "isError": false, "status": "input_required",
      "structuredContent": { "elicitation": {
        "elicitationId": "eli-…", "mode": "url", "url": "https://portal…/projects/{project}/…",
        "message": "<what this call would do, in one sentence>",
        "expiresIn": 600 } } }
  A proposal whose check has not run carries the route's own refusal beside the question
  (PF-57, ADR-N-021): `structuredContent` gains `"error": "verdict_required"`, `"check": "<the
  operation to run>"`, `"reason": "verdict_absent" | "verdict_failed" | "stale"` and the same
  one-sentence `detail`, at its top level where the REST route puts them, with `elicitation`
  beside them. A client that reads `verdict_required` on the route reads it here too and knows
  which check to run, and the person still has the URL to run it at. The door refuses either
  way: nothing is proposed without a fresh Verdict.
  The host shows it to the person, who opens the URL and decides; the client then repeats the
  same `tools/call` with `params.elicitation = { "elicitationId": "eli-…", "action": "accept" }`
  and the operation runs. `"action": "decline"` (or `"cancel"`) answers a refusal and nothing
  runs. An id is one-shot, belongs to the token's subject, expires in ten minutes and is bound to
  the operation and the arguments it was asked for: different arguments need a new answer. Every
  answer is written to the project's activity as `mcp.tool` from `portal`, naming the operation,
  the person and what they decided.
  Tasks (AG-60): `jc_pipeline_test`, `jc_model_infer`, `jc_space_complete` and
  `jc_datasource_check` wait on the runner, on Model Tools or on somebody's feed, so `tools/call`
  answers `{ "task": { "taskId", "status": "working", "pollInterval", "ttl" } }` at once and the
  client follows it with `tasks/get`, `tasks/result` (the tool's own result), `tasks/list` and
  `tasks/cancel`; `tools/list` marks them `execution.taskSupport: "required"` and every other tool
  `"forbidden"`. A task belongs to the token's subject: another caller's `tasks/get` answers
  `unknown task`, the same as one that never existed. A finished task is kept ten minutes.
  Limits (AG-60), counted by the token's subject in the Portal itself, so an in-cluster caller
  is bounded too: 120 requests a minute → 429 with `Retry-After`, a request body over 1 MiB and
  an answer over 4 MiB → 413 naming what to narrow. The edge's own bucket stays on top of them.
```

## 22. Workspaces (CC-76…CC-81, PF-82, PF-83, AG-82, UI-61…UI-63)

A workspace is a branch of the Organization repository with a record beside the drafts ([ADR-N-024](../Decisions/adr-n-024-workspaces-branch-and-preview.md), Architecture/06 §7). The same actions are operations of the registry (§21), so the Portal, REST, MCP and the assistant reach one implementation: `jc_workspace_open`, `jc_workspace_list`, `jc_workspace_get`, `jc_workspace_compare`, `jc_workspace_update_from_main`, `jc_workspace_propose`, `jc_workspace_discard`, and in the second phase `jc_workspace_preview_start`, `jc_workspace_preview_get` and `jc_workspace_preview_stop`. Opening, writing into and proposing a workspace need `propose` in the project; reading one needs `read`, and only its owner writes into it or brings it back. An agent may open, write, compare and update, and is refused `jc_workspace_propose` and every approval (AG-82, AG-11); an MCP client is not offered it. A comparison lists a file both sides changed under `conflicts` even when its fields do not collide (`fields` empty): bringing back waits until the workspace is updated from main.

```text
POST   /api/v1/projects/{project}/workspaces
  body: { "name": "bikes-cleanup", "title": "Bike stations cleanup",
          "scope": { "kind": "project" },              # or { "kind": "space", "name": "helsinki" }
                                                       # or { "kind": "resources", "items": [{ "kind": "Pipeline", "name": "bikes-ingest" }] }
          "ttlDays": 7 }
  → 201 the workspace
  → 409 a workspace of that name exists in the project

GET    /api/v1/projects/{project}/workspaces            → 200 { "items": [ workspace, … ] }
GET    /api/v1/projects/{project}/workspaces/{name}     → 200 the workspace, or 404

POST|PUT|PATCH|DELETE /api/v1/projects/{project}/{plural}[/{name}]?workspace={name}
  the ordinary resource routes (§4), committed to the workspace's branch instead of a Change
  of their own: the same checks (PF-82), and a 200 with the workspace in place of a 202 Change

GET    /api/v1/projects/{project}/workspaces/{name}/compare
  → 200 { "files": [ ChangeFile, … ],                  # §5, each with its fields, lane and operation
          "conflicts": [ { "path": "…", "fields": [ { "path": "spec.period", "ours": "30s",
                                                      "theirs": "60s", "base": "10s" } ] } ] }

POST   /api/v1/projects/{project}/workspaces/{name}/update
  body: { "resolutions": [ { "path": "…", "field": "spec.period", "keep": "ours" } ] }   # "theirs"; field "" is the whole file
  → 200 { "taken": [ "…" ], "merged": [ "…" ], "baseRevision": "…", "comparison": { … } }
       main merged into the branch: a file only main changed is taken, a file both changed is
       merged field by field and checked again before it is written; the base moves to main (CC-80)
  → 409 a conflicting field without a resolution; nothing is written

POST   /api/v1/projects/{project}/workspaces/{name}/propose
  → 202 the Change: the pull request of the branch, lane the riskiest file's (CC-79)
  → 409 a conflict not resolved, or a touched file without a fresh green Verdict (CC-80, PF-57)

DELETE /api/v1/projects/{project}/workspaces/{name}     → 204; the branch and any preview go (CC-81)

POST   /api/v1/projects/{project}/workspaces/{name}/preview   → 202 the preview (CC-78)
  → 200 { "state": "running", "prefix": "ws-bikes-cleanup-",
          "endpoints": [ { "name": "bikes-ops", "slug": "q3v7…",         # minted, Architecture/06 §7.2
                           "url": "https://…/api/endpoint/q3v7…",
                           "originSlug": "zt4q…" } ],                  # main's, absent for a new Endpoint
          "pausedPipelines": [ "bikes-ingest" ] }                  # the same body as the 202
  → 409 a preview of this workspace runs already, or two run on the node (ADR-N-024 §10),
        or the loader refuses the render: the preview is then `error` with that reason (CC-78)
GET    /api/v1/projects/{project}/workspaces/{name}/preview   → 200 the preview, as above
DELETE /api/v1/projects/{project}/workspaces/{name}/preview   → 204; stopping a stopped one is a no-op
```

The gateway reads the running previews from the Portal's internal listener, which the edge does not route and a NetworkPolicy opens to the gateway alone: the path `/internal/previews` answers `{ "items": [ { "prefix": "ws-bikes-cleanup-", "files": { "<path>": "<manifest>" } } ] }`, without the repository's encrypted secrets and without another project's files. The gateway presents its own Keycloak ServiceAccount token on that call — `client_credentials`, audience `portal-internal`, `azp` its own client — and the route refuses a call without one: the NetworkPolicy is the second control and never the only one (PF-46, [Architecture 13 §6](../Architecture/13-security.md)). A page of manifests is what the route answers, so a pod that reached the port through a policy mistake would otherwise read every project's configuration. The answer carries an `ETag`, a SHA-256 over the body: the gateway sends it back as `If-None-Match` on its next fetch, every ten seconds, and a list that did not change answers `304` with no body, so an idle instance moves no manifests (CC-78). Authentication comes first, so a call without the token learns nothing from a `304` either.

The gateway reads the domain verification of every Organization from the same listener, with the same token, the same `ETag` and the same ten-second fetch: `GET /internal/domain-verifications` answers `{ "items": [ { "organization": "hel", "domain": "hel.fi", "state": "verified" } ] }`, one item per Organization manifest of the repository, `state` one of `pending`, `verified`, `failed` and `pending` for an Organization the Portal has not checked yet. The challenge, the record and the reason stay off this route: the gateway decides on the state alone ([Architecture/03 §3](../Architecture/03-domain-model.md#3-identity-and-urn-specification)). Under `JC_GATEWAY_DOMAIN_VERIFICATION=enforce` a write to a space of an Organization that is not `verified`, or whose state the gateway does not know, answers `403` with the problem type `https://joinedcontext.com/errors/domain-not-verified` and a detail naming the Organization and its domain.

Only the owner starts or stops a preview; an agent may, as it may open and write the workspace. Real data reaches a preview only when the person copies it from the Try it panel (PF-83): the browser reads at most 1 000 entities per type through the origin's Endpoint and writes them through the preview's, both on the person's own session at the edge, with every id moved to the preview's space segment. The Portal holds no token of the person's for the gateway, so no operation of the registry copies data, and an agent never does. The operations are `jc_workspace_preview_start`, `jc_workspace_preview_get` and `jc_workspace_preview_stop`.

A workspace:

```json
{
  "name": "bikes-cleanup",
  "title": "Bike stations cleanup",
  "project": "helsinki",
  "owner": "jana@example.org",
  "branch": "workspace/bikes-cleanup",
  "baseRevision": "9c1f0ab",
  "scope": { "kind": "project" },
  "createdAt": "2026-09-18T09:00:00Z",
  "expiresAt": "2026-09-25T09:00:00Z",
  "changes": 3,
  "preview": { "state": "stopped" }
}
```

A write the owner's rights do not cover is refused as it is outside a workspace:

```json
{
  "type": "https://joinedcontext.com/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "Proposing a Pipeline needs a role with propose on Pipeline in helsinki."
}
```

## 23. Routes outside the resource API

The OpenAPI document describes `/api/v1` and nothing else, so these routes are in it only where
noted. An integrator meets the first three before any resource: the login, the MCP discovery and
the MCP endpoint itself.

| Method | Path | Who calls it | What it answers | Authentication |
|---|---|---|---|---|
| `GET` | `/api/v1/auth/login` | a browser | a redirect into the realm's code flow (§3) | none: it is how a session starts |
| `GET` | `/api/v1/auth/callback` | the realm, through the browser | the session cookie and a redirect to the page asked for (§3) | the code and the stored nonce |
| `POST` | `/api/v1/auth/backchannel-logout` | Keycloak | revokes the sessions the logout token names (§3) | the logout token, verified against the realm's keys |
| `GET` | `/.well-known/oauth-protected-resource` | an MCP client | the RFC 9728 metadata naming the Portal's MCP resource and its realm | none: RFC 9728 makes it public, and it names no secret |
| `GET` | `/.well-known/oauth-protected-resource/api/v1/mcp` | an MCP client | the same document, at the path RFC 9728 derives from the resource | none, as above |
| `POST` | `/api/v1/mcp` | an MCP client, the assistant | JSON-RPC over Streamable HTTP (§21); in the OpenAPI document | a Bearer token whose audience is the Portal; `401` with `WWW-Authenticate` otherwise |
| `GET` | `/api/v1/mcp` | an MCP client probing for a stream | `405`: the server opens no server-initiated stream | none needed to learn that |
| `GET` | `/api/v1/openapi.json` | a client generator, the docs lane | this API's OpenAPI 3.1 document | none: it describes the API, not a project |
| `GET` | `/apps/{name}/`, `/apps/{name}/{path}` | a browser | a published static app's `index.html` and assets (§12) | a `public` app is served to anyone; any other visibility needs a session, and what the app then reads is its endpoints' authorization |
| `POST` | `/apps/{name}/api/functions/{fn}` | a published app's SDK | the function's own answer from `jc-functions` (§12) | as the app's pages; with the edge's token, also the CSRF double-submit |
| `GET` | `/metrics` | the cluster's Prometheus | the Portal's counters in the Prometheus text format | none, and the edge refuses the path, so only a caller inside the cluster reaches it (OPS-16) |

A route here that needs no authentication says so because of what it carries, never for
convenience: none of them answers anything of a project.

## 24. People (PF-90…PF-94)

A person is a user of the organization's Keycloak realm and never a manifest
([ADR-N-031](../Decisions/adr-n-031-people-groups-and-app-groups.md)). The Portal manages people
through the realm's admin API with its admin client, which holds `manage-users` and
`query-groups` of `realm-management` and nothing else (PF-63). Membership stays as code: a person
joins a group through the `Group` manifest, and deleting a person is a Change.

```text
GET    /api/v1/organization/people                          search and page → 200
POST   /api/v1/organization/people                          create → 201
GET    /api/v1/organization/people/{id}                     one person, their groups and roles → 200
PATCH  /api/v1/organization/people/{id}                     edit the name, the e-mail, the language → 200
POST   /api/v1/organization/people/{id}/disable             disable and end every session → 200
POST   /api/v1/organization/people/{id}/enable              enable → 200
POST   /api/v1/organization/people/{id}/reset-password      send a password reset → 202, or 200 with a temporary password
POST   /api/v1/organization/people/{id}/remove-second-factor  remove every OTP and WebAuthn credential → 204
POST   /api/v1/organization/people/{id}/sign-out            end every session → 204
DELETE /api/v1/organization/people/{id}                     remove → 202 with the Change, or 204
```

`{id}` is the Keycloak user id. `GET` takes `search` (a substring of the name or e-mail), `first`
(default 0) and `max` (default 50, at most 100), and answers the page with `next`, the `first` of
the following page, when there is one:

```json
{
  "items": [
    {
      "id": "7d1f0c9e-4b8a-4f63-9a51-2c0d8e3b6f14",
      "email": "jana.kovacova@example.org",
      "firstName": "Jana",
      "lastName": "Kováčová",
      "locale": "sk",
      "enabled": true,
      "emailVerified": true,
      "requiredActions": [],
      "createdAt": "2026-09-24T09:12:40Z",
      "lastSeen": "2026-09-25T07:02:11Z",
      "pendingDeletion": null
    }
  ],
  "next": 50
}
```

- `lastSeen` is the last access of the person's newest open session, `null` when none is open. The
  realm keeps no login history the Portal's client may read, so there is no "last login".
- `pendingDeletion` names the Change a deletion waits for, `null` otherwise.

`GET {id}` answers the person with where they are granted something, each item naming the
manifest that grants it (PF-94):

```json
{
  "person": { "id": "7d1f0c9e-…", "email": "jana.kovacova@example.org", "…": "as above" },
  "groups": [{ "name": "helsinki-stewards" }],
  "platformRoles": [
    { "role": "steward", "binding": "stewards", "scope": { "project": "helsinki" }, "via": { "group": "helsinki-stewards" } }
  ],
  "appRoles": [
    { "project": "helsinki", "app": "helsinki-alerts", "role": "steward", "via": { "user": "jana.kovacova@example.org" } }
  ]
}
```

Creating takes the e-mail, the name and the language, and nothing else
(`deny_unknown_fields`):

```json
{ "email": "jana.kovacova@example.org", "firstName": "Jana", "lastName": "Kováčová", "locale": "sk" }
```

The e-mail is also the username, the name members and subjects name the person by (PF-04). The
realm sends its execute-actions e-mail, `VERIFY_EMAIL` and `UPDATE_PASSWORD` (PF-92), and the
answer is `201` with `{ "person": {…}, "emailSent": true }`. When the realm cannot send mail, the
Portal sets a temporary password with `UPDATE_PASSWORD` required instead and answers it once, as
`{ "person": {…}, "emailSent": false, "temporaryPassword": "…" }`. A password reset works the same
way: `202` when the e-mail went, `200` with `temporaryPassword` when it could not. The Portal never
stores, logs or returns that password again, and nothing else ever carries it.

`PATCH` takes any of `firstName`, `lastName`, `email` and `locale`. A changed e-mail is set
unverified and `VERIFY_EMAIL` is required again.

`DELETE` proposes one Change, in the organization repository, that takes the person's e-mail out
of every `Group` member list and every `RoleBinding` subject list naming it, and removes a binding
left with no subject. The person is disabled at once and marked with the Change; the reconciler
deletes the Keycloak user once that Change is on `main`, and clears the mark, leaving the person
disabled, when the Change is rejected. A person no manifest names is deleted at once: `204`.
An App's `spec.access` entry naming the e-mail then matches nobody, and the App page lists it.

- Every route needs a binding at organization scope whose role grants the verb on `Person`
  (PF-91): `read` for the two `GET`s, `create` for `POST`, `update` for `PATCH` and
  `reset-password`, `disable` for `disable`, `enable`, `remove-second-factor` and `sign-out`, and
  `delete` for `DELETE`. Anyone else gets `403` naming the verb.
- A person who holds a right the caller does not hold (an `org-admin`, for a caller who is only
  `people-admin`) is refused every write above with `403` naming that right, so a reset's temporary
  password never opens a stronger account; disabling or deleting yourself, or the last Organization
  Administrator, is `409` (PF-93, PF-03).
- An e-mail another person already has is `409` naming it. A malformed e-mail, a name longer than
  255 characters, a locale outside the Portal's languages or an unknown field is `400`.
- An `{id}` the realm does not know is `404`.
- Without the admin client every route answers `503`.
- Every action writes one `person.changed` event of the project `org` to the activity feed (§14):
  who, what, and the person's id, never an e-mail body, a password or a token (PF-90).
- The registry offers the same actions as operations (§21, AG-77, T-2732): `jc_person_list`,
  `jc_person_get`, `jc_person_create`, `jc_person_edit`, `jc_person_disable`, `jc_person_enable`
  and `jc_person_sign_out`. Each calls its route's function, so the check and the answers are the
  route's. `jc_person_create` never answers a temporary password: when the realm sends no e-mail
  its answer carries `handOver`, which says that a person gives one with `reset-password` on the
  person's page. Resetting a password, removing a second factor and deleting a person have no
  operation: the first two hand over or take away a way in, and a deletion is a Change a person
  proposes on the page (PF-92, PF-94).

## 25. Organization setup (PF-90, UI-82)

What a new organization still lacks, in one answer, for the page that walks an Organization
Administrator through it (`/organization/setup`, T-2748). The Portal reads it from what it already
holds and writes nothing: every step links to the page that proposes that change the normal way.

```text
GET    /api/v1/organization/setup                           the steps and the operator's part → 200
```

```json
{
  "complete": false,
  "steps": [
    { "id": "organization", "done": true },
    { "id": "domain", "done": false },
    { "id": "people", "done": false },
    { "id": "project", "done": true },
    { "id": "publishers", "done": false },
    { "id": "policies", "done": false }
  ],
  "operator": [
    { "id": "branding", "done": true },
    { "id": "loginTheme", "done": true },
    { "id": "smtp", "done": false },
    { "id": "backups", "done": false }
  ]
}
```

- `steps`, in the order the page shows them, each `done` when:
  - `organization`: the `Organization` manifest names a domain and at least one locale;
  - `domain`: that domain is verified (PF-41);
  - `people`: the realm holds a second person besides the one reading, so the organization does
    not hang on one account; `done` is `false`, never an error, when no admin client is configured;
  - `project`: a project holds a `ContextSpace` that names a data model;
  - `publishers`: a `CkanInstance` is declared, the catalogue the projects publish to (EP-62);
  - `policies`: the `Organization` manifest sets `spec.projects` (ADR-N-035).
- `operator` is what the installation provides and the Portal cannot change: `branding` is `true`
  when `global.branding` names the installation (an `instanceName` other than `joinedcontext`, or a
  logo); `loginTheme`, `smtp` and `backups` are the deployment's own statements,
  `JC_SETUP_LOGIN_THEME`, `JC_SETUP_SMTP` and `JC_SETUP_BACKUPS`, rendered from the values that
  switch those on ([Deployment/13](../Deployment/13-configuration-reference.md)). An unset
  statement is `false`: the page never claims what nobody said.
- `complete` is `true` when every step and every operator item is done.
- The route needs `approve` on `Organization` at organization scope, which `org-admin` holds (PF-56);
  anyone else gets `403`.

## Related

- [00-intro](00-intro.md) — all API surfaces.
- [04-context-spaces-and-endpoints](../Architecture/04-context-spaces-and-endpoints.md) — the model behind the endpoints.
