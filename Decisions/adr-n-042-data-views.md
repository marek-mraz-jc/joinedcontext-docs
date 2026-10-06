---
sidebar_position: 43
title: "ADR-N-042: Data Views Are Portal Views over Context-Space Entities"
---

# ADR-N-042: Data Views Are Portal Views over Context-Space Entities

Date: 2026-10-06  
Status: Accepted  
Decision Makers: product owner (orders of 2026-10-06, T-3094; study T-3093)

## 1. Context

The owner asked for Baserow-class data views in the Portal: a grid to edit a space's entities,
gallery, kanban, calendar, timeline and form views, saved views, real-time editing, comments,
history, trash and undo, public and password-protected links, import and export, API docs,
webhooks and an AI field. The study ([Research/data-views-comparison](../Research/data-views-comparison.md))
compared six tools. The owner's rules bind the answer: rows are NGSI-LD entities in a Context
Space, read and written through the gateway; tables are entity types of LinkML DataModels, Smart
Data Models first; history is NGSI-LD temporal; webhooks are subscriptions. Extra information
around the data may live in its own Postgres, referencing entities by (space, URN)
([ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md)).

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Filters are NGSI-LD queries, history is temporal, live updates and webhooks are subscriptions, fields are LinkML slots. |
| Technological consistency | **Full** | React in the Portal, the SDK's grid, the Portal's own database for its records. |
| Security by design | **Full** | Every read and write goes through the gateway with the person's session; a public view is an Endpoint and its Policy, reviewed as a Change. |
| Modular design | **Full** | One view model; each view kind is a renderer over it. |
| Multi-tenancy | **Full** | Every Portal record names its project, space and (space, URN). |

## 3. Decision

### 3.1 Where each record lives

| Record | Lives in | Why |
|---|---|---|
| A row | an NGSI-LD entity in the space | the data; every door reads it |
| A table and its fields | the entity type in a LinkML DataModel; a field change is a DataModel Change | the definition other systems compile from (JSON Schema, `@context`, SHACL) |
| The value of a formula or AI field | a Property of the entity | consumers read the value, not the Portal's computation |
| A row's history | NGSI-LD temporal | the standard history every door serves |
| A personal or collaborative view | the Portal's database, table `data_views` | only the Portal UI reads it; a filter tweak is not a reviewed Change |
| A published view, public form or embed | an Endpoint (and its Policy) in the configuration repository, plus a `data_views` row pointing at it | it opens data beyond the project, so it is reviewed and enforced by the gateway |
| A share password | the Portal's database, Argon2 hash on the `data_views` row | only the Portal checks it |
| Comments, mentions, notifications | the Portal's database, `entity_comments`, `notifications` | only the Portal UI reads them |
| The undo journal and trash | the Portal's database, `entity_journal` | session-scoped UI state; the restore is a write through the gateway |

"The Portal's database" is the database the Portal already owns on the CloudNativePG cluster, with
its own role; the tables come in the Portal's migrations. No other component writes them. Every
row that refers to an entity carries `(project, space, urn)`.

### 3.2 The view model

One `data_views` row per view: project, space, entity type, `kind` (`grid`, `gallery`, `kanban`,
`calendar`, `timeline`, `form`), `mode` (`personal`, `collaborative`, `locked`), owner, title and a
JSON `config`:

- `q` (an NGSI-LD query), `sort`, `group`, `hidden` attributes, per-attribute `width`;
- `colour`: rules of the form `{when: <q>, colour: <token>}`, evaluated on the page;
- kind-specific settings: the card's image and summary attributes (gallery), the enum attribute
  (kanban), the date or date-range attributes (calendar, timeline), the fields, conditions and
  prefill (form).

A view reads through the space's Endpoint the person uses, so the view can narrow and never widen:
its query is sent as the person's own NGSI-LD query. `personal` is the owner's alone;
`collaborative` everyone of the project who may read the type sees and edits; `locked` everyone
sees and only its owner or a steward edits.

### 3.3 Editing

Every edit is an NGSI-LD write through the gateway with the person's session, so the Endpoint's
Policy decides it. One edit (a cell, a pasted range, a drag on a kanban) writes one journal entry
per entity: who, `(space, urn)`, attributes, values before and after, session and window. Undo
replays the inverse as a write through the gateway, refused like any write when the grant no
longer allows it; redo replays the entry. Delete moves the entity's last state into the journal
as trash for 30 days; restore re-creates it under the same URN. Concurrent edits: the last write
wins per attribute, which is what `PATCH …/attrs` is; the grid says when a cell changed under the
person (§3.4).

### 3.4 Live updates

The Portal holds one NGSI-LD subscription per space that has an open view, created through the
space's own Endpoint with the Portal's ServiceAccount, and fans each notification out over the
SSE it serves (the stream the Activity feed uses), to the windows that show that space and type,
skipping the window that wrote. A notification carries the attributes after the change; the
window keeps the value before. A reconnecting window replays from its last event id. The
subscription is removed when the last view of the space closes or after a day without one.

### 3.5 Public views, embeds and forms

Publishing a view proposes an Endpoint whose Policy grants the `public` role exactly the view's
type, attributes and filter (`retrieveOps` for a view, `createEntity` for a form, nothing else),
and an embed's allowed origins. The view is served at `/v/{slug}` from the Endpoint, so the gateway
enforces what the link shows. A password-protected view is an unlisted Endpoint the Portal reads
with its ServiceAccount after checking the password; the visitor gets a short-lived cookie for that
view alone. Public views and forms follow the channel rules of the public assistant (T-3058): no
session cookie of the Portal, a per-IP rate limit on the APISIX route, origins checked for embeds.

### 3.6 What is reused

The SDK's `EntityGrid` with its edit mode, relation and enum pickers, `EntityHistory` (temporal),
`GridMap`, `EntityCompare` and `filters.ts`; the template's `EntityForm`; the Portal's
`PortalEntityGrid` on the space and Explore pages; the Activity SSE; the DataModel editor and its
Change flow for fields. Import is the existing upload path (a file profiled into a DataSource and a
Pipeline); export is the Endpoint's representations (CSV, XLSX, GeoJSON, …); API docs are the
Endpoint's OpenAPI; webhooks are NGSI-LD subscriptions; automations are pipelines. The AI field
runs as an agent run under the daily caps of AG-97 and writes through the gateway.

## 4. Consequences

- The data-views tasks T-3097 to T-3111 and T-3133 build on §3; each names the section it uses.
- The Portal gains three tables (`data_views`, `entity_comments` with `notifications`,
  `entity_journal`) and one subscription per space with an open view.
- Nothing about the data changes: a space edited in a view is the same space every Endpoint, MCP
  client and CKAN dataset reads.

## Related

- [Research/data-views-comparison](../Research/data-views-comparison.md) — the study this decision follows.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — entities referenced by space and URN.
- [Architecture/09-portal.md](../Architecture/09-portal.md) — the Portal the views are part of.
- [Architecture/11-data-models.md](../Architecture/11-data-models.md) — the LinkML models every table is.
