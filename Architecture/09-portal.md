---
sidebar_position: 9
title: "Portal Architecture (UI & API)"
---

# Portal Architecture (UI & API)

The joinedcontext Portal is **one application** (repository `joinedcontext-portal`): a single Rust binary that serves the embedded React build, the REST and resource APIs, and runs the reconciler loop (the `jcctl` library) in-process. The two layers below are parts of that binary, not separate deployables:

- **Portal API:** the stateless backend layer in **Rust** (`axum`, `sqlx`, `utoipa`).
- **Portal UI:** the web layer in **React 19**, **Vite**, and **TypeScript**, built in `ui/` and embedded into the binary at build time.

```text
+---------------------------------------------------------------------------------------------------+
|                                      PORTAL ARCHITECTURAL STACK                                   |
|                                                                                                   |
|  Portal UI (Vite / React 19 / TanStack Query & Router / Tailwind CSS / rjsf Draft-07)             |
|         |                                                                                         |
|         v (REST JSON / OpenAPI Typed Client via openapi-typescript)                              |
|  Portal API (Rust / axum / sqlx / utoipa OpenAPI Generator)                                       |
|         |                                      |                                  |               |
|         v (Mirror Read)                        v (Git Operations)                 v (Preferences) |
|    +------------------------+             +---------------+                  +------------------+ |
|    | Read-Only Live DB      |             | Gitea Git API |                  | PostgreSQL       | |
|    | Mirror (from jcctl)  |             | (PRs, Commits)|                  | (User Prefs DB)  | |
|    +------------------------+             +---------------+                  +------------------+ |
+---------------------------------------------------------------------------------------------------+
```

## 1. Portal API Specification

The Portal API operates as a thin, stateless coordinator. It exposes administrative endpoints, user preference stores, and high-level project queries while maintaining zero direct write access to context data.

### Technical Stack

- **Framework:** `axum` with `tower` middleware (compression, tracing, CORS, security headers).
- **Database Layer:** `sqlx` connecting to PostgreSQL using connection pooling and compile-time SQL query verification.
- **API Documentation:** `utoipa` generates OpenAPI 3.1 specifications directly from Rust structs and controller handlers.
- **Typing Integrity:** The `openapi.json` contract is exported to the frontend build pipeline, which compiles TypeScript definitions using `openapi-typescript`.

### Database Architecture

The Portal API connects to four database schemas:

1. **Live State Mirror (Read-Only):** Maintained by `jcctl apply` and context broker change notifications. Allows rapid querying of organizations, projects, context spaces, active endpoints, and pipeline execution states without querying Git.
2. **User Preferences (Read-Write):** Stores non-configuration Tier 2 user state (UI themes, language selections, favorite projects, table layout settings, saved map views).
3. **Logout marks (Read-Write):** One row per subject whose sessions a back-channel logout ended, and the moment it ended them: every session of that subject issued at or before it is refused. They live in the process for the request path and in the database so a restart does not re-accept a session somebody logged out (T-0980). A mark is kept 48 hours, which is longer than any session can live, and is read back when the process starts. A Portal deployed without a database keeps the marks of its own run only, and says so in its log.
4. **Reconciler Memory (Read-Write):** What a scheduled loop has to remember between two runs and across a restart — for a `SyncSource` (MF-30): the source revision the repository carries, when the last run happened, the proposal a run opened and nobody has answered, why the last run failed, and whether an operator paused it. No credential and no copy of a source is here; the manifests stay in Git. A Portal deployed without a database still runs the loops and keeps this in memory, at the cost of one duplicate proposal per source with a run in flight when it restarts.

### Liveness and readiness

`GET /api/v1/health` answers `ok` whenever the process serves, and it is the liveness probe. `GET /api/v1/ready` is the readiness probe (OPS-51): 503 until this replica's mirror holds the repository, 200 afterwards, with `{"status": "ready"}` or `{"status": "loading"}` and nothing else. Every replica loads the repository. The leader runs the whole sync (the mirror, then streams, apps and roles); a follower, which cannot take the reconciler lock because another replica holds it, stages the default branch and swaps in the mirror without converging anything, so a new pod of a rolling update becomes ready while the old pod still holds the lock. A follower shows a stream pipeline as `pending` with the condition `StreamDeployed` reason `Follower`, because only the leader knows what the runner accepted. A Portal without a forge has no repository to wait for and is ready at once.

---

## 2. Portal UI Architecture

The Portal UI delivers an enterprise-grade experience for domain stewards, platform engineers, and administrators.

### Core Technologies

- **Application Shell:** Vite + React 19 + TypeScript (strict mode enabled).
- **Routing & State:** TanStack Router (type-safe routing) and TanStack Query (server-state synchronization, caching, and optimistic updates).
- **Component Primitives:** Radix UI headless primitives styled with Tailwind CSS.
- **Tabular Data:** AG Grid Community for high-performance sorting, filtering, and row virtualization on large datasets.
- **Geospatial Presentation:** MapLibre GL JS combined with deck.gl (`@deck.gl/mapbox`).

### Schema-Driven Form Generation (CC-31)

Administrative forms are never hard-coded. They are dynamically generated from LinkML-compiled **JSON Schema draft-07** definitions using `react-jsonschema-form` (RJSF):

- **Parameter Forms:** Instantiating a Blueprint loads the blueprint's `params.schema.json` and renders corresponding fields (text, number, enums, dates).
- **UI Schemas:** Layout properties (widget types, grid columns, order, field grouping) are loaded from declarative `*.uischema.yaml` files committed in the `portal/forms/` directory (UI-02).
- **Asynchronous Pickers:** Custom RJSF widgets query live Endpoints via the Context Gateway to populate entity selection dropdowns (e.g. selecting an existing sensor).

#### The `kind: UiSchema` manifest (UI-02)

One manifest per kind, at `portal/forms/{name}.uischema.yaml`. It arranges a form; it never
declares a field. Everything renderable comes from the JSON Schema, so a manifest naming a
field the schema does not have arranges nothing, and a field the manifest does not mention is
still rendered in schema order after the ones that are.

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: UiSchema
metadata:
  name: endpoint
spec:
  for: Endpoint                      # the kind whose form this arranges
  order: [name, slug, audience, enabledRepresentations, caching]
  groups:                            # visual grouping of a flat schema
    - title: Basics
      fields: [name, slug]
    - title: Access
      description: Who may read
      fields: [audience, enabledRepresentations]
  fields:
    slug:
      widget: text
      help: The unguessable address other people use; the Portal makes it, you never type it
      placeholder: "dhiw4735mzyvwkrmszljpxcvvgv32q33"
      columns: 6                     # of twelve
      readOnly: false
      advanced: false
    enabledRepresentations:
      widget: checkboxes
    commitMessage:
      advanced: true                 # hidden outside the advanced mode (CC-29)
```

`columns` is a twelfth of the row, so `6` is half.

**A field is named by its path in the schema.** `http.url`, `caching.maxAgeSeconds` and
`pages[].widgets[].widgetType` are arranged like a top-level field: a dot enters an object and `[]`
enters an array's items, and the Portal turns the path into the nested `uiSchema` RJSF wants. The
fields a person understands least are the nested ones, so an arrangement that reached only the top
level reached almost nothing (T-1612). A path the schema does not have is still refused with its
reason, as a top-level name is.

**The words are translated, the resource titles are not.** `help` and a group's `title` and
`description` are the Portal's own interface text and MUST be complete in the four shipped locales
(UI-11, UI-12), so in a UiSchema manifest they are either one plain string or a map of locale to
string, resolved to the person's locale with Slovak as the fallback:

```yaml
    audience:
      help:
        en: Who may read this endpoint. Public means anyone with the address.
        sk: Kto smie tento endpoint čítať. public znamená ktokoľvek s adresou.
```

This is not the per-language `title` UI-50 refuses: UI-50 governs a human label **authored for a
resource** — a space's or an endpoint's own `title` — and keeps it one plain string in the author's
language, out of the creation form. The help beside an input is chrome, translated like the rest of
the chrome, and an organization that writes its own help writes it as one string in its own language.

**A group may be folded.** `folded: true` shuts a group when the form opens, with its title and its
one-line description as the handle a person clicks or tabs to. Every field of a folded group is in the
page, so nothing is hidden from a search, from the keyboard or from a screen reader — it is shut, not
removed. A group that holds a **required** field is never folded, whatever the manifest says: a form
that insists on a field it does not show is a dead end, and the Portal unfolds it instead of arguing.
The first group is never folded either.

Beside the form's buttons the Portal says how much of what it insists on is in: *"2 of 3 required
fields filled"*, counted from the schema's `required` — the object's own and every required object
inside it, whose inputs the form renders straight away. An optional object is not counted until
somebody opens it. Without the count, folding a group would hide the reason Propose is off.

**`about` is what the kind is for, and the form says it before it asks anything.** Two sentences at
the top of the dialog, in the four shipped locales: what this kind does for the person and what it
needs from them. It is written for someone who has not met the kind before — the first thing a person
reads on a form they opened by mistake tells them so. A form whose arrangement has no `about` opens
with its title alone, as before.

```yaml
spec:
  for: DataSource
  about:
    en: A data source is where the platform fetches from — a feed, a broker, an API. It brings
      nothing in by itself; a pipeline reads it and writes into a space.
    sk: …
```

**`guide` is where to read more, and it appears only when there is somewhere to read it.** An
arrangement names the kind's page inside the User Guide as a path, never as an address:

```yaml
spec:
  for: Endpoint
  guide: User-Guide/05-endpoints-and-sharing
```

The address is the installation's, not the manifest's: `documentationBaseUrl` in the branding block
([Deployment/12](../Deployment/12-branding-and-naming.md)) says where that installation serves the
guide, and the form builds the link by joining the two. Both halves are needed. An installation that
serves no guide leaves `documentationBaseUrl` empty and every form shows `about` and no link, which
is the state of `dev` today: nothing serves the User Guide to a browser that can reach the Portal
(measured 2026-09-19, and again 2026-09-20 — the private `docs-build` workflow publishes nowhere),
and a dead link is worse than none.

Splitting it this way is what keeps a manifest from becoming an address the Portal sends a person
to. `guide` is a relative path: a value with a scheme, an authority, a leading slash or a `..`
segment is dropped with the arrangement's other problems, so an organization that commits a
`portal/forms/*.uischema.yaml` cannot point the link at a site of its own. `documentationBaseUrl`
is validated as an absolute `http` or `https` URL the same way a branding colour is validated as
hex, and for the same reason: it reaches the page as an attribute a browser acts on. The link opens
in a new tab with `rel="noreferrer"` and names the page it opens, so a screen reader announces the
destination rather than "link".

**The Portal ships a default arrangement for every kind that has a form.** They are
`kind: UiSchema` manifests like any other, bundled with the UI, so a fresh install has help and an
example on every field before anything is committed to `portal/forms/`. A manifest in the
configuration repository then overrides the default **field by field**: an organization that writes
`help` for one field keeps the shipped help on the others, and `order` or `groups` it writes replace
the shipped ones whole, because a half-replaced order is not an order. The forms with a shipped
default are ContextSpace, Endpoint, DataSource, SyncSource, Pipeline, Dashboard and Layer — the seven
the Portal renders `ResourceFormDialog` for.

**`metadata.name` is `spec.for` lowercased**, which is why the example above is `endpoint` and
not `Endpoint`. Every `metadata.name` on this platform is a DNS-1123 label (MF-02) and a label
has no capitals, so the file for the `Endpoint` form is `portal/forms/endpoint.uischema.yaml`.
The two are not merely conventionally related: a manifest whose name is not its `for` lowercased
is refused, because the path a reader predicts from the kind has to be the path the file is at.

**The widget vocabulary is the Portal's, not the manifest's.** `widget` names a widget the
Portal has registered: an RJSF built-in (`text`, `textarea`, `select`, `checkboxes`, `radio`,
`range`, `color`, `date`, `date-time`, `password`, `updown`, `hidden`) or one of the Portal's
own (`entityPicker` today). A name outside that set is dropped with the reason rather than
passed through, because RJSF throws on an unknown widget and a form that does not render is a
worse answer than a form with a default input.

**`advanced` is CC-29.** Git mechanics — the commit message, the branch, the target
revision — are fields of the form like any other, and marking them `advanced: true` is what
keeps them out of the default view. The Portal renders them when the user asks for the
advanced mode, and never silently drops the value.

**What a person reads beside a field.** In order: the label, one sentence of `help` in their
own language, the value in the empty input, and `required`. `help` is written for the person who
fills the form; the JSON Schema's `description` is the field's rustdoc, written for an engineer and
carried into the API and MCP, so it is the fallback and never the first thing shown — a form that
says "the reconciler renders it as the last `mapping` processor of the generated `bento.yaml`" has
answered a question nobody asked (T-1604). A field with no `help` still shows the description, so a
kind whose manifest is not written yet gets no worse.

**`placeholder` is the example, and the form offers to use it.** The Portal shows it in the empty
input and, beside it, one action that writes it into the field, so a person facing
`spec.source.query.q` starts from something that works instead of from a blank. It must therefore be
a value the field accepts — `600`, `https://opendata.example.org/aq.json`, `availableBikeNumber==0` —
and never a hint about one ("26 characters"). An example never carries a real credential or a real
person's address (MF-24).

**How a form gets its manifest.** Every manifest dialog fetches `GET /api/v1/forms` once
(API/01 §8a) and arranges the kind it edits. The manifest decides the arrangement of the fields it
names; the dialog's own settings stay for what a manifest cannot know, such as a name that is
read-only once the resource exists. The advanced mode is the person's `advancedMode` preference,
switched from the dialog's footer.

---

## 3. Localization (i18n)

The Portal UI provides complete internationalization support:

- **Shipped Locales:** Slovak (`sk`, default), English (`en`), German (`de`), and Czech (`cs`).
- **Message Format:** Bundles are stored in standard **ICU MessageFormat** JSON files in `portal/locales/`.
- **Manifest Multi-Language Support:** Entity metadata titles and descriptions in repository manifests are defined as language maps:

  ```yaml
  metadata:
    title:
      fi: "Ilmanlaadun mittaus"
      en: "Air Quality Monitoring"
      de: "Luftqualitätsüberwachung"
  ```

  The UI dynamically displays the string matching the active user locale with fallback to Slovak.

---

## 4. Accessibility & UI Quality Standards

- **WCAG Conformance:** The Portal UI conforms to **WCAG 2.1 Level AA** standards. All components enforce proper ARIA semantics, full keyboard navigation, and contrast ratios ≥ 4.5:1.
- **Automated Verification:** The frontend test pipeline runs `vitest` unit tests, `axe-core` accessibility scans, and `playwright` end-to-end integration tests on every pull request.
- **Disabled with a reason (UI-44):** a control the caller's effective permissions deny stays visible, disabled (`disabled`, `aria-disabled="true"`), with the missing verb and kind as its reason, reachable by pointer and by keyboard; the `PermissionGuard` wraps every primary action of the management views and reads `permissions/me` (PF-51); the API decides (PF-50), the guard only says so first.

## 5. Branding at runtime

The Portal image is the same everywhere. What differs between installations is one file: the deployment renders `global.branding` ([Deployment/12](../Deployment/12-branding-and-naming.md)) into a ConfigMap, mounts it, and names it in `JC_BRANDING_FILE`. The API reads that file and answers `GET /api/v1/branding`, which is public and cached: a branding block holds no secret, and the login page needs it before anyone has signed in.

The React shell applies the answer as it boots. The instance name becomes the document title and the login heading, the logo goes into the sidebar and the login page from `/api/v1/branding/logo`, each colour becomes a CSS custom property on the root element (`--portal-color-primary` and its siblings, the same tokens the theme already reads, so no component has to know about branding at all), the font stacks become `--portal-font-heading` and `--portal-font-sans`, the offered languages fill the language switcher and the default one is the initial locale unless the visitor has already chosen a language, and the organisation and contact fill the footer.

`documentationBaseUrl` is the one field that is not about how the Portal looks: it is the root of
the installation's copy of this documentation, and it is empty on an installation that serves none.
A form's link to the User Guide is built from it (section 2); nothing else reads it, and nothing
follows it — it becomes an `href` a person may click and never a request the Portal makes.

Two rules keep this safe and dull. Colours are validated as hex before they are written into a style, because a custom property is a value a browser evaluates and an unvalidated one is an injection point; the readable foreground for the brand colour is computed from it rather than authored, so a light primary does not end up with white text on it. And a missing, unreadable or invalid file is not an error: the Portal serves neutral joinedcontext defaults and logs the reason, because an instance whose ConfigMap has not been rendered yet should look plain rather than fail to load (UI-30, OPS-46).

## 6. Activity: what is happening

A project is a set of moving parts a person did not start and cannot see: a reconciler applying
a merge request, a pipeline dropping a malformed reading, a broker forwarding a query to another
space, an anonymous caller being refused. The Activity stream is the one place all of that is
readable, per project and per object, so that "is it working" has an answer that is not a
Grafana login.

### One event, whoever emits it

Every source writes the same record. A reader learns the shape once and every producer is
obliged to fit it rather than invent a variant:

| Field | Meaning |
|---|---|
| `time` | when it happened, RFC 3339 in UTC |
| `project` | the project it belongs to; the only key the read API filters on by default |
| `space` | the Context Space, when the event has one |
| `kind` | what happened, from the closed vocabulary below |
| `source` | which component said so: `reconciler`, `pipeline`, `gateway`, `broker`, `ckan`, `portal` |
| `summary` | one sentence a person reads, already localised into the request's locale |
| `severity` | `info`, `warning` or `error` |
| `correlationId` | the W3C trace id (OPS-17), so one event opens the whole trace |
| `details` | a small object of named values, never a payload (OPS-48) |

The vocabulary is closed because a filter over free text is not a filter:

| `kind` | Emitted by | When |
|---|---|---|
| `config.planned`, `config.applied`, `config.drifted` | reconciler | a plan, an apply, a difference between Git and the cluster |
| `change.merged` | reconciler | a merge request became the desired state |
| `pipeline.throughput` | pipeline | one minute of messages, as a count |
| `pipeline.error` | pipeline | a mapping or output failure, with the failing sample redacted |
| `pipeline.restarted` | pipeline | the runner restarted a stream |
| `endpoint.traffic` | gateway | one minute of requests for one endpoint and representation |
| `access.denied` | gateway | the PDP refused, naming the rule that refused |
| `mcp.tool` | gateway, portal | an MCP tool call (AG-19); from the Portal, the person's answer to an elicitation before a Yellow or Red call proceeds (AG-63) |
| `agent.answer` | portal | a person answered a question an assistant run asked with `jc_ask` (AG-80): the run, the question and who answered, never the words they typed (OPS-48) |
| `federation.forward` | broker | a query forwarded to a Context Source, with latency |
| `federation.error` | broker | a forward that failed or was cut off by the loop guard |
| `catalogue.published` | CKAN publisher | a dataset created or updated, with the row count |

### Where it comes from, and what it is not

The activity store is derived. The reconciler and the CKAN publisher write their own events
because they already run inside the Portal process; every other source emits the same record as
an OpenTelemetry log line, which the collector redacts and hands to the Portal
([Deployment/05 §5](../Deployment/05-monitoring-logging.md#5-the-activity-pipeline)). Nothing
emits an activity event *instead of* logging, tracing or writing to the audit trail. It is a
projection of the three logs of [13 §4](13-security.md#4-end-to-end-audit-trail-cc-44-cc-58) and
of the traces, built for reading, and a disagreement between it and them is settled in their
favour (OPS-49).

Two consequences are worth stating. Losing activity loses nothing that is not still in its
sources, so retention is short: seven days of events, ninety days of the per-minute counters they
aggregate into. And an event carries no payload: the `details` of a `pipeline.error` name the
stream, the processor and the reason, and the offending sample only after the data model's own
masking rules have run over it (OPS-48). A stream of "what is happening" that quotes a citizen's
record is a data leak with a friendly name.

### Who sees it

Activity follows project membership: a viewer of a project reads its activity and nobody else
does. There is no instance-wide activity view, because an event names a project and a person who
is not in that project has no business knowing that it is busy.

### In the UI

The project page carries the stream with filters for kind, space, severity and time, and a live
tail that follows the SSE route. Every object page shows its own slice of the same data, filtered
to itself: a space, an endpoint, a pipeline, a Context Source Registration (UI-31). The tail is
the same query as the list, so what a person sees live and what they see on reload cannot differ.

## 7. Pipeline studio

The pipeline dialog is one form and its YAML, validated by the same schema (UI-01). The studio sits above the form and fills it: the author picks the source (a `DataSource` of the project, or a Context Space and the Endpoint the Portal reads it through, the same endpoint the space's look-inside column uses), the entities (the space's DataModel gives the types and, for an inline LinkML model, the attributes of the chosen class; a live sample of twenty `keyValues` rows is read through the endpoint with the signed-in user's session, and ticked rows become `source.query.ids`, PL-42), the processing (a `compute.kind`, with sum, average and count snippets that write `compute.bloblang`, PL-41) and the output. Every choice is form data: the fields below show it, the YAML view shows the manifest, and either can override it. The write is the ordinary POST or PUT of the pipeline, so it lands in Approvals (CC-35). Aggregates need the whole page in one message, so the snippets set `class: scheduled` with a query; a subscription trigger delivers one entity per notification and has nothing to sum. Spaces shared through a `SharedSpaceReference` are read-only for the studio until `source.endpointRef` may name one (a contract change).

The studio also draws the manifest as a flow (UI-49): a source node, the compute node and the output node, left to right, on an SVG canvas beside the YAML view. The canvas is a projection of the manifest and the manifest stays the source of truth, so the file in Git is what a reviewer reads and no node position is stored; the stage order is the edge order, and a compute kind dropped from the palette sets `compute.kind` the way the form does. A Test paints the same flow with its trace: the input node carries the events read, the compute node the events mapped and the first Bloblang error, the output node the rows that validated; the node whose stage failed turns red and the nodes after it grey, and a click on a node shows the sample that entered it beside the sample that left it.

The studio's test runs on a dropped file or, for an `http` DataSource, on the source's own URL (PL-48), and its green answer is what unlocks Propose for a `bloblang` mapping (PL-49): edit the mapping and the gate closes until the next green test. The data source dialog's Check does the same for the feed: the plan of the manifest and, for `http`, what one fetch returned (MF-39).

## 8. Data explorer

The explorer is the Portal's window on what a space holds (UI-33): pick a space and one of its endpoints, and the page reads a page of entities through that endpoint with the signed-in session, the way the look-inside column and the pipeline studio do. The endpoint's Policy decides what the page shows; the explorer adds nothing to it. The filters are not hand-written: the space's DataModel gives the entity types, and the chosen class's slots give one filter row each, typed by the slot's LinkML range. A number or a date offers `==`, `!=`, `<`, `<=`, `>`, `>=` and a typed input with the slot's minimum and maximum; a string offers equality and the `~=` pattern; a boolean and an enum offer their values; a relationship takes a URN. The rows compose into the NGSI-LD `q` and parse back from it, so the `q` string stays the only truth: a `q` typed by hand, or one the YAML view carries, shows as rows when it fits the simple grammar (`attr op value` joined by `;`) and as a text field when it does not. The page shows the count the broker reports in `NGSILD-Results-Count`, pages with `limit` and `offset`, and opens one entity in full. One component (`EntityFilters` in the UI) renders these filters for the explorer and for the pipeline studio's entities step (§7), so the query an author previews is the query the pipeline manifest carries.

## 9. The assistant finds data

"Where is the transport data?" is answered from the mirror, not from the model's memory (AG-58). The Portal's catalog search reads the project's `ContextSpace`, `Endpoint` and `DataModel` manifests, matches the words of the question against each manifest's name, title in every language, description, labels, slug and, for a model, its classes, and ranks by how many words hit; the item says which fields matched (`matchReason`), so a person can see why it is there. Two things are added to what the manifest says. The access verdict comes from the endpoint's `spec.audience`: `public` and `organization` admit every signed-in caller, `projectList` admits the project it names; a space is `allowed` when one of its endpoints is, a model when its space is, and a restricted item shows its name and kind and nothing else. The gateway's own policy decision (`…/access`, EP-55) stays the last word for the data itself: the verdict says whether the door is open to the caller, not what the room holds. The freshness is the runner's counters for the pipeline whose `targetEndpoint` names the endpoint (§7 of API/01), read when the search runs; an endpoint nothing feeds, or a runner that does not answer, gives `null` rather than a guess.

The same search is the assistant's `search_catalog` tool (Architecture/07 §2). A kit run (Architecture/19 §1.2) runs it over the person's message before the model sees the message, publishes the result as a `tool` event named `search_catalog` (AG-56) and hands the items to the model as context, so what the model builds on is what the search found; the conversation renders the event as cards with the access badge, the freshness chip and an "Explore" action that opens the data explorer on the item's space and endpoint (UI-46, §8). A person who never starts a run gets the same answer from `GET /api/v1/projects/{project}/assistant/catalog?q=…` (API/01 §18).

**Asking the data itself (AG-75).** Finding where data lives is one question; what the data says is another. Beside the text box the assistant has an endpoint picker: the person chooses one or more endpoints of the project, the way an MCP client is pointed at a connector. The conversation run then carries those endpoints and offers the model the data-plane MCP tools of each one (`describe_access`, `describe_schema`, `query_entities`, `get_entity`, Architecture/07 §1). A call is a `query_endpoint` JSON block naming the endpoint, the tool and its arguments; the Portal sends it as `tools/call` through `jc-agent-proxy` (`/v1/data/endpoints/{slug}/mcp`) with the run's ticket, so the gateway answers with exactly what the person may read, puts the call and its result on the conversation as a `tool` event, and hands the result back to the model, up to six calls for one message. The answer names the entities it used. Write tools of the façade are never offered and the proxy refuses them on a read-only run.

**Working the data as an agent (AG-76).** A question is rarely one call. The model may open any endpoint of the project the person can read, not only the chosen ones: the Portal adds it to the conversation first (the data bar shows it), and `jc-agent-proxy` re-reads the run once when a slug is new to its cache, so the call does not wait. One answer may carry several `query_endpoint` blocks, on one endpoint or several; the Portal runs them at once and hands every result back together, up to twelve calls a message. A request for a KPI pipeline is worked the same way: the model reads the types and a page of entities, drafts the Bento pipeline, and the Portal tests it on a page of the source; a refused plan or a red verdict returns to the model, which looks at the data again and drafts it anew (three drafts at most), and only a green draft opens the Pipeline form.

**Changing entities with the person's hand (AG-78).** "Set station 001 to out of service" is a write, and a write is the person's. The model answers with a `write_entities` call naming the endpoint and the attributes that change; the Portal reads the person's grants on that endpoint and the entities as they are, through the proxy like any read, and the conversation shows a card with every attribute before and after. Nothing is written until the person presses Apply: the browser then sends one NGSI-LD attribute update per entity through the endpoint with the person's own session, and the gateway's policy decides each one, so the card shows a refusal in the gateway's words. A grant that does not cover the change is refused before the card is drawn, and the run never holds a write tool.

## 10. Operations, drafts and verdicts

Every action the Portal offers is an operation of one registry (AG-59, ADR-N-021): a `jc_`-prefixed name, a JSON Schema for its input and its output (the same `ToSchema` types the OpenAPI document publishes), MCP annotations, the roles it needs and the lane it takes. One function implements it; the REST route (`POST /api/v1/projects/{project}/ops/{name}`, and the kind routes that remain), the assistant's tool, the agent proxy's tool and the MCP tool (`/api/v1/mcp`, Architecture/07 §1.2) parse, resolve the caller, call that function and format its answer. A route that does not name its operation is a defect the tests catch.

A form edits a draft, not the tab's memory (AG-61, UI-47): the Portal keeps, per project, kind and name, the manifest being worked on, its last verdict, who touched it last (a person, an assistant run, an MCP client, an API key) and a version. The draft's changes travel on the activity stream (§6), so a second window, a second Portal instance, the assistant that filled the form and the MCP client that checked it show the same state, and the person picks the work up wherever it is. An assistant's `navigate` opens a draft (UI-45). A draft ends when its change is proposed, or at the instance's idle ceiling.

Every check answers one `Verdict` (AG-62): `ok`, `findings[{level, path, message}]`, an optional `trace` (the pipeline test's stages, the dry run's plan), `checkedAt` and the digest of the input it judged. A dry run, a pipeline test (PL-43), a LinkML validation (DM-55), a schema validation and an endpoint access check are the same shape, so the form, the assistant's card and the MCP client's structured result read the same. Propose refuses a draft whose verdict is absent, red or older than the draft (`409`, the check to run named); the button is disabled with that reason (UI-44, UI-48). An installation says `platform.validation: strict` or `lax` (PF-57): strict has no override and no author approves their own Yellow or Red change (CC-34); lax lets a Green-lane draft through with a warning.

An external feed is integrated from one message (AG-73). A person gives the assistant the feed's URL, and may add what the data is and a specification of it, pasted as text: a field list, a JSON Schema, a vendor's documentation. The assistant calls `jc_space_complete` with the URL, the context space, the entity type the description or the specification names (`typeName`, PascalCase) and the description in one paragraph (`description`). The operation probes the URL the way a data source Check does, infers the LinkML model from the sample under that type, carries the description onto the model, the space and the source, and drafts the `DataSource`, the `Pipeline` and its `Endpoint`, each with its verdict. The drafts follow the feed's records, not its envelope (AG-79): the operation finds the array of records in the sample (`data.stations` of a GBFS feed, a FeatureCollection's features, or the sample itself), infers the model from one page of them, and writes a mapping that turns each record into one entity, its id from the field that identifies a record, its `location` from the latitude and longitude, the other fields under the model's slot names. When the records carry a position, a `Layer` over the new endpoint and a `Dashboard` with one map page are drafted too, so one message ends in a map. The assistant then opens the Complete this space page on those drafts, where the person reads what was inferred and proposes the set as one change. Nothing is proposed without that click.

## 11. The assistant workbench

The assistant workbench provides an interactive copilot available on every page and a central workbench for past conversations and autonomous agent tasks (UI-51…UI-56, AG-67…AG-71).

### The bubble and the docked panel

A round button labelled "Assistant" is fixed at the bottom right of every Portal page for a signed-in user (UI-51). It sits above page content and is accessible by keyboard navigation. Activating the bubble toggles the assistant panel docked to the right edge of the viewport.

On viewports of 1024 px and wider, the panel occupies a width of 24 rem, and the main page content reflows so that no controls or data tables are obscured. On viewports narrower than 1024 px, the panel expands to full width. The panel drives UI navigation by processing `navigate` events (UI-45) across any active route without triggering a full page reload. The assistant operates exclusively from this right-docked panel or in full-screen mode; it never renders as a left column.

The panel header contains accessible icon buttons with explicit tooltips and ARIA labels (UI-52):

- **Stop the assistant:** cancels an active run (`POST /api/v1/projects/{project}/agent-runs/{id}/cancel`), halting answer generation and transitioning the run to `cancelled`.
- **Full screen:** expands the conversation across the entire content area; pressing Escape or clicking the control again returns to the 24 rem side panel.
- **Hide the assistant:** closes the panel while keeping the active conversation and state intact in the browser tab. The floating bubble remains visible at the bottom right and displays an active indicator dot while the assistant is processing.
- **Close the assistant:** lets go of the conversation without stopping its run (it stays on the Assistant page) and returns the panel to its empty state.

When the panel is hidden, reopening it from the bubble restores the active thread. Tab reloading preserves the current conversation identity for the session.

### Starting and continuing conversations

When opened without an active conversation, the panel renders a clean composer accompanied by a concise summary of platform capabilities and three clickable prompt suggestions: finding catalog data, sharing an endpoint, and building a dashboard (UI-53). A file drop area beneath the composer accepts CSV, Excel, JSON, and PDF files to scaffold draft data models automatically.

Submitting an initial prompt calls `POST /api/v1/projects/{project}/assistant/conversations` (UI-53, AG-67). The server creates an agent run with `kind: conversation` and returns HTTP 202 Accepted with a `CreatedRun` envelope. A conversation run is not tied to a specific application, context space endpoint, or Git branch, and it generates no preview frame until a specific tool produces one.

The model responds in prose or by invoking registered operations from the Portal registry (AG-59, AG-64), such as `jc_catalog_search`, endpoint proposals, KPI computations, or schema completions. If a conversation requests an application or dashboard build, the assistant does not run an in-process dashboard pass; it initiates a dedicated work run (AG-69) or navigates the user directly to the corresponding authoring form (UI-45). Initiating an assistant conversation requires the `propose` permission on `App` within the project. The composer view also offers quick resumption of the user's three most recent live conversations in the project.

A conversation run respects the standard run lease and timeout rules (AG-66). Sending a message to an ended run fails with HTTP 409 Conflict. To continue an ended thread, the client creates a new conversation run specifying `continues: <runId>` (AG-68). The Portal injects the prior run's conversation history (user messages, assistant responses, and tool outcomes, pruned from the earliest events if token limits require) into the model context. The UI threads the prior and new runs together seamlessly based on the `continues` reference.

### The Assistant page

The route `/projects/{project}/assistant` is exposed in the primary navigation as "Assistant" (UI-54). It lists all agent runs the caller is authorized to view (AG-71), sorted newest first.

Each table row displays:

- Run kind (`conversation`, `application`, `dashboard`, `analysis`).
- Title, derived from the initial prompt or message and truncated to 80 characters.
- Current lifecycle state (`queued`, `building`, `previewing`, `awaitingApproval`, `published`, `failed`, `cancelled`, `expired`).
- Creation timestamp and last activity timestamp.
- Performance metrics, including `firstFrameMs` and `firstVersionMs` where applicable.
- Parent continuation link (`continues`) when the run extends an earlier conversation.

Interactive filters allow narrowing the view by kind, status, and ownership ("mine"). Clicking **Open** on an active run loads it into the assistant panel or full-screen view. An ended run opens in read-only mode with full event replay, offering a **Continue** action for conversation runs. The view subscribes to the Portal activity stream (UI-31), updating run status, token counters, and completion states in real time without manual page refreshes.

From the Assistant page, authorized users can click **New work** to trigger autonomous, unattended agent runs (UI-55, AG-69). The page also provides an access inspector and editor for configuring `AgentProfile` permissions and network egress rules (UI-56, AG-70).

## 12. Channel parity

Whatever a person can read, change or remove in a project, they can do through any of four doors, and the four are one (AG-77, ADR-N-021): the Portal's lists and forms, the REST routes of each kind, the operations registry (so every MCP client, §10) and the assistant. Each door parses its input, resolves the caller and calls the same function for the action; that function runs the same dry run, answers the same Verdict and opens the same Change. Two doors given one manifest produce the same plan, byte for byte.

| Kinds | Portal | REST | Operations and MCP | Assistant |
|---|---|---|---|---|
| ContextSpace, DataModel | list, create and edit (Spaces, Models, Complete this space) | list, get, create, update, delete | search, `jc_space_propose`, `jc_model_propose`, `jc_model_infer`, `jc_space_complete` | `space_complete`, catalog search |
| DataSource, Pipeline, Endpoint | list, create, edit | list, get, create, update, delete | `jc_*_propose`, `jc_datasource_check`, `jc_pipeline_test`, `jc_endpoint_propose` | `propose_endpoint`, `edit_endpoint`, `draft_kpi_pipeline` |
| Dashboard, App | list, create, edit; apps through runs | list, get, create, update, delete | none | application runs |
| RoleBinding, Role, ServiceAccount, AgentProfile | Access page: who holds which role (Grant a role, Edit, Remove), effective permissions, API keys, agent access | list, get, create, update, delete | `jc_resource_*` | `grant_role`, `change_resource` |
| SyncSource, CkanInstance, Blueprint, Mapping, ModelProjection, ScopeDefinition, SharedSpaceReference, ContextSourceRegistration, Layer, UiSchema, Bundle, DataSpaceParticipant, DataOffer, DataAgreement, Project | a page for sync sources, CKAN and flows; a generic list for the rest | list, get, create, update, delete | none | none |
| Every kind above, the target | list, Edit, Delete (typed name) | unchanged | `jc_resource_list`, `jc_resource_get`, `jc_resource_propose`, `jc_resource_delete`, `jc_change_reject` | `change_resource`: change or remove by name |

Deleting a resource is a Change in the Red lane (CC-19): the name is typed back before the proposal and again at approval (CC-39), and a resource another one still references (an Endpoint a Pipeline targets, a ContextSpace with endpoints) is refused with `409` and the names of those references. A proposal carries secrets as `secretRef` only; a literal secret is refused before a branch exists (MF-24). A grant is bounded by its proposer: a RoleBinding, Role or ServiceAccount asking for more than the proposer holds on that scope is refused with the verbs it lacks.

The assistant never proposes (AG-73). `change_resource` names a kind and a resource and says what changes as a JSON merge patch of the manifest, or asks to remove it; a new resource is drafted by the kind's own tool (`propose_endpoint`, `draft_kpi_pipeline`, `space_complete`, and `grant_role` for a RoleBinding, which opens the Access page's grant form). The Portal reads the manifest from the mirror, applies the patch, runs the dry run (and, for a Pipeline or a DataSource, its test or its check) and hands a red verdict back to the model with the findings; a green one opens the kind's form prefilled through `navigate` (UI-45), or the deletion's confirmation, and the person proposes. An unknown name is answered with the names the project has. Approval stays with people: an operation called by an agent run never approves or rejects (AG-11); a person's own MCP session approves someone else's change, and an administrator approves their own change only at the Portal's button (PF-58), never through an operation.

Entities are not resources: writing them stays with the endpoint's own write tools and the person's grant (AG-49).

## 13. The entity grid

One component lists entities wherever the Portal shows them (UI-64…UI-72): the data explorer of an Endpoint, a whole Context Space, the two side by side, a Dashboard view and a generated application. It lives in the App SDK and the Portal uses it unchanged (UI-71, SDK-29), so a fix reaches every place at once.

**What a cell is.** The grid reads the normalized representation with `options=sysAttrs`, never `keyValues`, so every attribute arrives with what a person needs to trust it: `observedAt`, `unitCode`, `datasetId`, `createdAt` and `modifiedAt` (UI-64, UI-65). A cell shows the value with its unit; the metadata are columns the person turns on. A Relationship is a link to its object, a GeoProperty its geometry type with a map, a LanguageProperty the value in the person's language.

**How it reads.** The filter row builds an NGSI-LD query (`q`, `attrs`, `idPattern`, `scopeQ`, `georel` from a drawn box) and sends it to the Endpoint, whose Policy narrows it like any read; the query is shown and copyable (UI-66). Sorting applies to the loaded page and says so. Where the Endpoint serves the temporal API a cell offers its history, read with `timerel`, `timeAt`, `endTimeAt` and `lastN`, as a table and a small chart (UI-68).

**The comparison.** The space on the left, an Endpoint of it on the right, one type, rows aligned by id: what the Endpoint filters out or projects away is marked on the left, so a steward sees what a grant hides before anyone asks (UI-69).

**How it writes.** In edit mode a changed cell joins a list of pending changes. The review shows entity, attribute, old and new, and Apply sends each as a partial attribute update through the same Endpoint with the signed-in person's session, the path the assistant's write card already uses (AG-78, EP-55). The Endpoint's Policy decides each one; a refused cell keeps the person's value, shows the gateway's sentence and stays pending. The grid never writes with the Portal's rights and never batches around the Policy (UI-67). A geometry is edited on the map with the same pending-change path (UI-72).

**Access.** The grid is a keyboard grid (`role="grid"`, arrows, Enter, Escape, Tab) that announces coordinates and edits, and at 400 px it pins the id column and scrolls the rest (UI-70).

## Related

- [01-overview](../Architecture/01-overview.md) — where this chapter sits in the whole.
- [00-index](../Requirements/00-index.md) — the normative requirements behind it.
- [Deployment/05 §5](../Deployment/05-monitoring-logging.md#5-the-activity-pipeline) — the collector that fills the activity store.
- [API/01 §14](../API/01-portal-api.md#14-activity-ui-31-ops-48-ops-49) — the two routes that read it.
