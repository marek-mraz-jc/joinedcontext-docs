---
sidebar_position: 7
title: "Data Views: Baserow and Its Alternatives"
---

# Data Views: Baserow and Its Alternatives Compared with the Portal

Status: Study for ADR-N-042 (T-3093)  
Date: 2026-10-06  
Scope: Baserow, NocoDB, Teable, Grist, Mathesar and APITable, read from their source in
`/workspace/reference/` (inspiration only, never code or a runtime of the platform), against the
owner's feature list of 2026-10-06 and the Portal and CKAN as they are in the code today.

The owner's rule decides what is taken: every row is an NGSI-LD entity in a Context Space, every
table an entity type of a LinkML DataModel (Smart Data Models first), history is NGSI-LD temporal,
webhooks are NGSI-LD subscriptions. Extra information around the data (view definitions,
per-person state, comments, notifications, trash and undo journals, caches) may live in its own
Postgres database on the CloudNativePG cluster, referencing entities by (space, URN)
([ADR-N-041](../Decisions/adr-n-041-entity-identity-is-space-and-urn.md)).

## 1. Method

Each tool's repository was read for how it stores rows and fields, synchronises editors, keeps
history and undo, evaluates formulas, enforces permissions, models views and generates its API.
Every statement below names what the source shows; one marked *unverified* was not confirmed in
the code. The tools were not started: the source answers the architecture questions, and the
server's memory is shared with four agents and a 16 GB cluster node. The Portal and CKAN column
is read from the platform's code (`joinedcontext-portal/sdk/src/grid`, `ui/src/pages`, the
gateway's representations, `jcctl publish ckan`); a pass on dev confirms it with the views of
T-3097 onwards.

## 2. Feature matrix

`●` built, `◐` partly or in a paid edition only, `○` absent.

| Feature | Baserow | NocoDB | Teable | Grist | Mathesar | APITable | Portal + CKAN today |
|---|---|---|---|---|---|---|---|
| Rows in a real store, fields as columns | ● table per table | ● on any SQL source | ● table per table | ● SQLite per document | ● the user's own Postgres | ◐ JSON row per record | ● NGSI-LD entities in a space, types in LinkML |
| Explicit primary field | ● | ● display value | ● | ○ row id | ● record summary | ◐ first column of the first view | ○ (the grid pins `id`) |
| Grid with inline edit | ● | ● | ● | ● | ● | ● | ● EntityGrid edit mode, batch apply |
| Gallery / kanban / calendar / timeline | ● (kanban, calendar, timeline premium) | ● incl. map, gantt | ● gallery, kanban, calendar | ◐ card, chart, calendar | ○ | ● incl. gantt, org chart | ○ (map beside the grid ●) |
| Form view, conditional fields, prefill | ● | ● | ◐ no conditions | ● | ● nested records | ● | ◐ manifest forms; App forms via SDK |
| Per-view filter, sort, group, hidden fields | ● | ● | ● | ● | ◐ not saved | ● | ◐ filters and hidden by Endpoint; not saved per view |
| Row colouring | ● | ● | ○ | ◐ | ○ | ◐ | ○ |
| Personal vs collaborative views | ● (personal premium) | ● personal, locked, collaborative | ◐ personal client-side | ○ | ○ | ● lock | ○ |
| Real-time co-editing | ● websocket, replay after reconnect | ◐ paid edition | ● push after commit | ● action broadcast | ○ | ● OT | ◐ activity feed live; rows not |
| Row history | ● before/after | ● audit rows | ● per field | ● action log | ○ | ● from changesets | ● NGSI-LD temporal (EntityHistory) |
| Undo / redo | ● action log, per session | ◐ paid edition | ● per window | ● inverse actions | ○ | ● 50 steps | ○ |
| Trash | ● 72 h | ◐ meta only | ● with snapshots | ◐ snapshots | ○ | ● | ○ |
| Audit log | ◐ enterprise | ● separate store | ● | ● | ○ | ● | ● gateway audit + Activity |
| Roles at several levels | ◐ enterprise | ● | ● | ● access rules per row/column | ● Postgres roles | ● node, field, view | ● Roles, Policies down to type, attribute, scope, area |
| Comments, @mentions, notifications | ◐ premium | ● | ● | ● cell comments | ○ | ● | ○ |
| Public read-only link, password, embed | ● | ● bcrypt | ● | ● shares | ○ | ● | ◐ public Endpoints and CKAN; no password-protected view |
| Public forms | ● | ● | ● | ● | ● token URL | ● | ○ |
| Import CSV/Excel/JSON | ● (+XML, Airtable) | ● (+Airtable) | ● (+Airtable, Sheets) | ● (+Sheets) | ◐ CSV | ● | ● DataSource + pipeline; file upload path |
| Export CSV/Excel/JSON | ◐ beyond CSV premium | ● | ◐ CSV | ● | ◐ CSV | ● | ● Endpoint representations (CSV, XLSX, GeoJSON, …), CKAN |
| Generated API docs, scoped tokens | ● | ● Swagger | ● | ● | ◐ JSON-RPC | ● | ● OpenAPI, ServiceAccount tokens per Policy |
| Webhooks | ● | ● | ◐ closed source | ● | ○ | ◐ automation | ● NGSI-LD subscriptions |
| Formulas | ● to SQL, stored | ● to SQL per dialect | ● to SQL + computed graph | ● Python, sandboxed | ○ | ● | ◐ KPI pipelines, `inverseOf`; no formula field |
| AI field per row | ◐ premium | ● | ● | ○ | ○ | ○ | ○ (assistant and app builder ●) |
| Application builder, app-user login | ● | ○ | ◐ plugins | ◐ custom widgets | ○ | ◐ widgets | ● Apps by conversation, Keycloak login per App |
| Snapshot / duplicate | ● | ● | ● | ● forks, proposals | ○ | ◐ | ● Copies of projects, workspaces |

## 3. Architecture worth copying, mapped onto the platform

1. **One action record per change feeds undo, row history and audit (Baserow, Grist,
   APITable).** Every Portal write to entities becomes one journal row in the extra Postgres (who,
   space, URN, attribute, before, after, session); undo replays the inverse through the gateway, so
   the Policy decides the undo like any write. Row history stays NGSI-LD temporal; the journal is
   what undo needs and temporal does not hold (the session, the grouping of one person's edit).
   → T-3107.
2. **Write over REST, push after commit (Teable).** The Portal never merges edits: the gateway
   applies a write, an NGSI-LD subscription on the space notifies the Portal, and the Portal fans
   it out over the SSE it already serves for Activity, skipping the writer's own window and carrying
   the before-state so an open cell can say it changed under the person. No OT, no CRDT: last write
   wins per attribute, which NGSI-LD `PATCH …/attrs` already is. Replay after reconnect from the
   last event id (Baserow). → T-3105.
3. **Views as configuration rows over the data (NocoDB, Baserow, Teable).** A view is a row in the
   extra Postgres: space, entity type, kind, a JSON config (filter as an NGSI-LD `q`, sort, group,
   hidden attributes, colour rules, per-field width), owner and mode (personal, collaborative,
   locked). One table with a JSON config, not one table per view kind (NocoDB's lesson). Filters
   compile to the NGSI-LD query the grid already sends, so a view reads nothing a direct query
   could not. → T-3099, T-3104.
4. **Field types as a registry, each type owning its editor, filter, sort and export (Baserow).**
   Here a type is a LinkML range with its NGSI-LD kind (Property, GeoProperty, LanguageProperty,
   Relationship), and adding a field is a DataModel Change, never `ALTER TABLE`. → T-3098.
5. **Comments and notifications as their own records keyed by the row (Baserow, Teable).** A
   comment row (space, URN, author, rich text, mentions); a notification row per recipient, read
   and email state; delivery over the Portal's SSE and the existing mail path. → T-3106.
6. **Shared-view links with a hashed password and a narrowed answer (NocoDB, Baserow, Teable).** A
   share is a view row with a slug and an Argon2 hash; the public read goes through a public
   Endpoint whose Policy is the view's columns and filter, so the gateway enforces what the link
   shows. → T-3108.
7. **Formulas compiled where the data is (Baserow, Teable, NocoDB).** A formula field becomes a
   LinkML slot with `equals_expression`, computed by the space's derived pipeline and written as a
   Property, so every consumer (API, MCP, CKAN) reads the value and not only the grid; the
   dependency graph is the model's. → the new task in §6.
8. **A primary field stored explicitly (Teable, Baserow; APITable's derived one is the warning).**
   The DataModel names it, by an annotation ADR-N-042 fixes, `name` when it names none. → T-3097.

## 4. Not taken

- **A table per user table and live `ALTER TABLE` (Baserow, Teable, NocoDB).** Rows are entities;
  the broker and LinkML are the schema.
- **A whole document in memory per tab, a Python process per document (Grist).** Neither fits a
  16 GB node or a broker of 44 000 entities.
- **Operational transform with a global lock per resource (APITable).** Last write wins per
  attribute through the gateway is the platform's write model.
- **Formulas in a sandboxed general-purpose language (Grist).** A formula is a LinkML expression a
  pipeline evaluates, no new runtime.
- **Role passwords or token secrets in the application's database (Mathesar, Teable).** Identity
  stays Keycloak; secrets stay secretRef.
- **Three API versions and paid-edition stubs that services still call (NocoDB).** One API, every
  feature whole or absent.

## 5. The owner's features against the filed tasks

| Owner's feature | Task |
|---|---|
| tables, primary field, row expansion | T-3097 grid, T-3098 field types |
| views and per-view filters, sort, group, hidden, colouring | T-3099, T-3100 gallery, T-3101 kanban, T-3102 calendar and timeline |
| form view, conditional fields, prefill, public forms | T-3103 |
| personal vs collaborative views | T-3104 |
| real-time editing | T-3105 |
| comments, @mentions, notifications | T-3106 |
| row history, trash, undo/redo | T-3107 |
| public links, embed, password-protected views | T-3108 |
| import and export | T-3109 |
| API docs, scoped tokens, webhooks | T-3110 |
| AI field per row | T-3111 |
| roles at workspace/database/table level, audit log | built: Roles and Policies per project, space, type and attribute; gateway audit and Activity |
| snapshots, duplicate | built: Copies of projects and workspaces |
| application builder, app-user login | built: Apps by conversation, Keycloak per App |
| automations, n8n/Zapier/Make | built: subscriptions and pipelines; T-3110 adds the per-table view of them |
| formulas, AI formula assistant | **gap** → §6 |

## 6. Filed from this study

- **Formula fields** (T-3133): a LinkML slot with `equals_expression` over the type's own attributes,
  edited in the grid's field dialog, computed by the space's derived pipeline and written as a
  Property; the assistant drafts the expression from a sentence; depends on T-3094 and T-3098.

## Related

- [ADR-N-041](../Decisions/adr-n-041-entity-identity-is-space-and-urn.md) — entities are referenced by space and URN, which every extra record uses.
- [Architecture/11-data-models.md](../Architecture/11-data-models.md) — the LinkML models every table is.
- [Architecture/08-pipelines.md](../Architecture/08-pipelines.md) — the derived pipelines a formula field runs in.
- [Architecture/09-portal.md](../Architecture/09-portal.md) — the Portal the views are built in.
