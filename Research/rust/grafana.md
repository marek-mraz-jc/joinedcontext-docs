---
sidebar_position: 7
title: "Grafana for controlroom"
description: Research input for controlroom, the Rust dashboard server that replaces Grafana 12.4.14 on the platform; capability inventory, internals, datasource plugins and expressions, security, tenancy, operations, Grafana JSON compatibility and import, test oracles, Portal embedding and the Argon pack plan, every claim with its source (T-6649).
---

# Grafana for controlroom

This page is the research input for controlroom: one Rust dashboard and panel server for every organization of an installation, replacing the Grafana 12.4.14 the deployment runs today. The owner's requirements (2026-11-07) are that controlroom reads and writes Grafana's JSON, so existing dashboards and provisioning files move over by import and stay exportable; that a dashboard or one panel shows inside a Portal page with no iframe and no second login; and that a panel can draw from several datasource plugins with a calculation step, as in Grafana. Readers: the worker who builds the controlroom pack, the reviewer of the generated code, the owner deciding the open points marked **Decided** below.

Sources and pins used on this page:

| Short | What | Pin |
|---|---|---|
| `GF` | github.com/grafana/grafana | tag `v12.4.14`, commit `3c98af3ba0773ad12a8a54b1faec7dc62d8d6725` (2026-10-27); deployed image `ghcr.io/marek-mraz-jc/joinedcontext-grafana:12.4.14@sha256:a7bf66f9…d53d` built `FROM docker.io/grafana/grafana:12.4.14@sha256:ae509d9a…cd7` (`DEP components/grafana/images.yaml:5-17`, `DEP images/grafana/Dockerfile:17`) |
| `GFD` | Grafana documentation for 12.4 | `https://grafana.com/docs/grafana/v12.4/` |
| `SDK` | github.com/grafana/grafana-plugin-sdk-go | `v0.287.0` (`GF go.mod:110`) |
| `NGP` | github.com/joinedcontext/Grafana-NGSI-LD-data-source | commit `2262d44dc7df597cc11e1cd26421d0abbc1a7284`, archive sha256 `4f43366b…` (`DEP images/grafana/Dockerfile:8-10`) |
| `DEP` | joinedcontext-deployment | `cee6ebcb9` (2026-11-07) |
| `POR` | joinedcontext-portal | `d7f91eb28` (2026-11-05) |
| `PLT` | joinedcontext-platform | `e59ceb9f0` (2026-11-05) |
| `CRR` | controlroom proposal, `marek-mraz-jc/joinedcontext crates/controlroom/README.md` | `af23f5a1362c` (2026-11-07), as read by T-6641 (docs branch `agent/worker-t6641/T-6641`, `Research/rust/code-factory.md` section 12) |
| `ADV` | `curl https://api.github.com/repos/grafana/grafana/security-advisories?per_page=100`, run 2026-11-07: 28 advisories, 2021-10-05 to 2023-03-01 (later ones are published only on `https://grafana.com/security/security-advisories/`) | |

`scripts/research/grafana-inventory.py` produces the inventory of section 1.2 from `DEP`; `scripts/research/grafana-sources.sh` clones `GF` sparsely at the tag and measures the pack groups of section 10.

## 1. Capability inventory

### 1.1 What we hold and run today

| Piece | Where | What it does |
|---|---|---|
| Grafana server, one replica, no persistence | `DEP components/grafana/values/grafana/base-values.yaml.gotmpl:33-43` | embedded SQLite in an emptyDir; everything authored is provisioned, a restart loses nothing committed |
| OIDC login, no login form, no sign-up | same file `:110-167`; client `DEP components/grafana/keycloak-clients.yaml:4-35` | `generic_oauth` with PKCE against the installation realm; `platform-admin` maps to Admin of org 1, project groups map to Viewer of their org |
| One Grafana organization per project | `DEP components/grafana/values/grafana/base-values.yaml.gotmpl:135-161`, `DEP components/grafana/charts/dashboards/provision.sh:1-65` | `org_mapping` by number (orgs are made in name order by the postStart hook); `role_attribute_strict` refuses a person with neither group nor role |
| Prometheus datasource, read-only | `base-values.yaml.gotmpl:183-197` | uid `prometheus`, `editable: false`, `timeInterval: 15s`, in-cluster `prometheus-operated:9090` (`DEP components/grafana/default-environment.yaml.gotmpl:23-30`) |
| NGSI-LD datasource per project Endpoint | `DEP components/grafana/charts/dashboards/templates/projects.yaml:28-37` | type `ngsild-grafana-datasource`, `access: proxy` to `context-gateway…/api/endpoint/{slug}`, `oauthPassThru: true`, `pageSize: 1000`; the person's own token reaches the gateway, so the Endpoint's Policy decides each read |
| Endpoint audiences in the Grafana client | `DEP components/grafana/keycloak-clients.yaml:36-67` | one `oidc-audience-mapper` per Endpoint slug, so the forwarded token is accepted by the gateway |
| NGSI-LD plugin, unsigned, baked into the image | `DEP images/grafana/Dockerfile:1-24`; `base-values.yaml.gotmpl:96-104` | frontend-only plugin (no backend executable in `NGP src/plugin.json`), allow-listed by id, `preinstall_disabled` |
| Platform dashboards, file provider | `base-values.yaml.gotmpl:199-221`, `DEP components/grafana/charts/dashboards/templates/configmap.yaml:1-19` | 7 JSON files under `files/` into org 1, `disableDeletion`, `editable: false` |
| Project dashboards, API provider | `projects.yaml:13-27`, `provision.sh:31-64` | one folder `project-{name}` and one dashboard per project, posted with `overwrite: true` |
| Portal-saved visualizations | `POR src/grafana.rs:1-7`, `:416-523`; table `POR migrations/0055_grafana_visualizations.sql:4-14` | the Portal builds a one-panel dashboard (timeseries, stat, table, geomap) and posts it with Grafana's local admin; a 300 s sweep puts back what a Grafana restart lost (`POR src/grafana.rs:26`, `:586-602`) |
| Portal page | `POR src/api/grafana.rs:228-560`, `POR ui/src/pages/grafana/GrafanaPage.tsx`, route `POR ui/src/router.tsx:548-556` | lists readable Endpoints, saves and removes visualizations, links out to `{public_url}/d/{uid}?orgId={org}` (`POR src/api/grafana.rs:214`) |
| Edge | `DEP components/grafana/apisix-routes.yaml:10`, `DEP components/grafana/apisix-plugins.yaml:15-75` | `uri: /grafana*` on the primary host; forged identity headers stripped; `frame-ancestors 'self'` when Grafana sets no CSP |
| Alerting | `DEP components/monitoring/values/monitoring/base-values.yaml.gotmpl:106-447` (31 alerts, 14 recording rules); `DEP components/prometheus/values/stack/base-values.yaml.gotmpl:227-236` | Prometheus rules and Alertmanager with the `null` receiver; delivery by the cluster-watch job. Grafana alerting holds nothing |
| Resources | dev `values/grafana/development-values.yaml.gotmpl:3-9` (50m/128Mi request, 500m/256Mi limit); prod `production-values.yaml.gotmpl:4-10` (100m/256Mi, 1 CPU/512Mi) | |

`components/ai` holds no dashboard and no Grafana reference (`grep -rli 'dashboard\|grafana' DEP components/ai` prints nothing); `components/prometheus` disables the stack's own Grafana (`DEP components/prometheus/values/stack/base-values.yaml.gotmpl:25-27`).

### 1.2 Inventory of our dashboard JSON

Output of `python3 scripts/research/grafana-inventory.py ../joinedcontext-deployment` (2026-11-07, `DEP cee6ebcb9`), quoted unchanged:

| File | uid | schemaVersion | Panels | Panel types | Variables | Transformations |
|---|---|---|---|---|---|---|
| `components/grafana/charts/dashboards/files/assistant.json` | `jc-assistant` | 39 | 6 | bargauge 2, timeseries 4 | - | - |
| `components/grafana/charts/dashboards/files/context-broker.json` | `jc-context-broker` | 39 | 7 | timeseries 7 | - | - |
| `components/grafana/charts/dashboards/files/context-gateway.json` | `jc-context-gateway` | 39 | 8 | timeseries 8 | - | - |
| `components/grafana/charts/dashboards/files/edge-apisix.json` | `jc-edge-apisix` | 39 | 7 | stat 1, timeseries 6 | - | - |
| `components/grafana/charts/dashboards/files/k6-load.json` | `jc-k6-load` | 39 | 9 | table 1, timeseries 8 | testid(query) | - |
| `components/grafana/charts/dashboards/files/portal.json` | `jc-portal` | 39 | 6 | timeseries 6 | - | - |
| `components/grafana/charts/dashboards/files/slo.json` | `jc-slo` | 39 | 6 | table 3, timeseries 3 | - | - |
| `components/grafana/charts/dashboards/projects/bbsk.json` | `project-bbsk` | 39 | 2 | table 2 | - | organize 2 |
| `components/grafana/charts/dashboards/projects/helsinki.json` | `project-helsinki` | 39 | 4 | table 2, timeseries 2 | - | organize 2 |

| Panel type | Count |
|---|---|
| `timeseries` | 44 |
| `table` | 8 |
| `bargauge` | 2 |
| `stat` | 1 |

| Datasource (per target) | Count |
|---|---|
| `prometheus` | 61 |
| `ngsild-grafana-datasource` | 6 |

| Query language (per target) | Count |
|---|---|
| `PromQL` | 61 |
| `NGSI-LD entity` | 4 |
| `NGSI-LD temporal` | 2 |

| Transformation | Count |
|---|---|
| `organize` | 4 |

| fieldConfig feature | Count |
|---|---|
| `unit:reqps` | 18 |
| `unit:s` | 12 |
| `override:byName` | 9 |
| `noValue` | 6 |
| `unit:short` | 6 |
| `unit:percentunit` | 5 |
| `decimals` | 2 |
| `unit:ms` | 2 |
| `unit:none` | 2 |
| `custom:fillOpacity,lineWidth,pointSize,showPoints,spanNulls` | 1 |
| `custom:fillOpacity,lineWidth,showPoints,spanNulls` | 1 |
| `unit:Bps` | 1 |
| `unit:bytes` | 1 |
| `unit:d` | 1 |
| `unit:locale` | 1 |

| Panel option | Count |
|---|---|
| `table.cellHeight` | 4 |
| `table.showHeader` | 4 |
| `table.sortBy` | 3 |
| `timeseries.legend` | 2 |
| `timeseries.tooltip` | 2 |

Beyond the script: the 61 PromQL expressions use `sum` 45, `rate` 41, `histogram_quantile` 17, `increase` 5, `time` 2, `topk` 1, `max` 1 and the `by` modifier 46 times; all 61 set `legendFormat` (`{{label}}` templates). The one variable is `label_values(k6_http_reqs_total, testid)`, multi-value with `includeAll` and `allValue: ".*"` (`DEP …/files/k6-load.json:20-35`). The NGSI-LD targets use `queryType` `entity` (with `format: table`, `idPattern`, `customQuery` as the NGSI-LD `q`, `lang`) and `temporal` (with `aggrMethod`, `aggrPeriodDuration`, `entityName`/`namePattern`) (`DEP …/projects/helsinki.json`, `DEP …/projects/bbsk.json`). No dashboard uses annotations, dashboard links, library panels, rows, repeats, time overrides, value mappings or thresholds. The Portal adds two kinds the files lack: `stat` with `reduceOptions.calcs: [lastNotNull]` and `geomap` with a `markers` layer over NGSI-LD `queryType: geo` (`POR src/grafana.rs:440-505`).

### 1.3 Grafana capabilities and verdicts

Verdicts: **used** (our file:line), **needed** (the platform or the owner asks for it, nothing uses it yet), **drop** (with the reason).

| Capability | Grafana source | Verdict |
|---|---|---|
| Dashboard JSON v1 (classic), schemaVersion 0 to 42 | `GF kinds/dashboard/dashboard_kind.cue:1-853`; migrations `GF apps/dashboard/pkg/migration/schemaversion/migrations.go:10-12` | used: 9 files at 39 (section 1.2) |
| Dashboard v2beta1 (layout kinds, elements) | `GF apps/dashboard/kinds/v2beta1/dashboard_spec.cue` (1087 lines) | needed for import only: Grafana 12 exports v2 when the `dashboardNewLayouts` flag is on; export stays v1 (section 7) |
| Panels timeseries, table, stat, bargauge | `GF public/app/plugins/panel/{timeseries,table,stat,bargauge}` | used (section 1.2) |
| Panel geomap | `GF public/app/plugins/panel/geomap` | used by the Portal (`POR src/grafana.rs:478-505`) |
| Panels gauge, barchart, piechart, text, logs, heatmap, histogram, state-timeline, status-history, nodeGraph, alertlist, dashlist, news, canvas, xychart, trend, flamegraph, traces | `GF public/app/plugins/panel/*` | needed: gauge, barchart, piechart, text, logs, heatmap, histogram, state-timeline (common in imported dashboards, T-6641 measured 20 grafana.com dashboards with 465 panels); nodeGraph (NGSI-LD `nodegraph` query, `NGP src/types.ts:4-9`); drop: news (outbound fetch), canvas, flamegraph, traces (no tracing backend here) until asked |
| Template variables query, custom, constant, interval, textbox, datasource, adhoc, groupby, switch | `GF kinds/dashboard/dashboard_kind.cue:381-382` | used: query (`k6-load.json:20-35`); needed: custom, constant, interval, textbox, datasource; adhoc and groupby need per-datasource support, refused with a warning at first |
| Annotations (built-in, query) | `dashboard_kind.cue:95`, `:147-180` | needed: deploy markers over Prometheus; none used today |
| Dashboard links, panel links, data links | `dashboard_kind.cue:98`, `:281-300`, `:645` | needed (links stay inside allow-listed hosts, section 4) |
| Library panels | `dashboard_kind.cue:696`, `:731-737` | needed: import resolves them inline (section 7) |
| Rows, repeat by variable | `dashboard_kind.cue:826-853`, `:648` | needed |
| Transformations (44 ids) | `GF packages/grafana-data/src/transformations/transformers/ids.ts` | used: organize; needed: the set in section 3.4 |
| Server-side expressions math, reduce, resample, classic_conditions, threshold, sql | `GF pkg/expr/query.go:14-28` | needed: the owner's "different calculation" step (section 3.4); sql as a restricted dialect only (section 4) |
| Datasource plugins, backend and frontend | `GF pkg/plugins/backendplugin/ifaces.go:15-31`; `SDK backend` | used: Prometheus (core, backend) and NGSI-LD (frontend, proxy routes); needed: the plugin contract of section 3 |
| App plugins, panel plugins from the catalogue | `GFD administration/plugin-management/` | drop: code from an outside catalogue running in a viewer's browser; panels come from the SDK, third-party code runs only as WASM datasources |
| Unified alerting (rules, contact points, policies, mute timings, templates) | `GF pkg/services/ngalert`; provisioning `GF pkg/services/provisioning/alerting/*.go` | needed per organization: organizations ask for alerts on their own data; the platform's own alerts stay in Prometheus rules (`DEP components/monitoring/…/base-values.yaml.gotmpl:106-447`) |
| Provisioning files: datasources, dashboards, alerting, plugins | `GF pkg/services/provisioning/{datasources,dashboards,alerting,plugins}` | used: datasources and dashboards file provider (`base-values.yaml.gotmpl:183-221`); import reads all four (section 7) |
| HTTP API: orgs, folders, datasources, dashboards/db, health | `GFD developers/http_api/` | used by `provision.sh:16-64` (`POST /orgs`, `GET /orgs/name/{n}`, `POST`/`PUT /datasources`, `POST /folders`, `POST /dashboards/db`, `GET /health`) and `POR src/grafana.rs:255-410` (`GET /orgs/name/{n}`, `GET`/`POST /datasources`, `POST /dashboards/db`, `GET`/`DELETE /dashboards/uid/{uid}`); controlroom serves the same paths for import tools (section 7) |
| Kubernetes-style APIs `/apis/dashboard.grafana.app/*` | `GF apps/dashboard` | needed read-only for v2 import tools; `CRR` lists them |
| OIDC generic OAuth, JWT auth, auth proxy, LDAP, SAML, basic auth, API keys, service accounts | `GF conf/defaults.ini:908`, `:975` | used: generic OAuth only; drop the rest: one identity (wardkeep) through jc-auth |
| Organizations, teams, folder and dashboard permissions, RBAC | `GF pkg/services/{org,team,folder,accesscontrol}` | used: organizations; mapped onto jc-core Organization, Project and RoleBinding (section 5) |
| Snapshots, public dashboards, reporting, playlists, kiosk | `GFD dashboards/share-dashboards-panels/` | needed: public dashboard maps to a jc-core Dashboard with `visibility: public` (`PLT crates/jc-core/src/kinds/dashboard.rs:20`); drop snapshots (stored data copies outside the Policy) and reporting (PDF renderer) |
| Explore, query history, starred, preferences | `GFD explore/` | needed: Explore is the query editor of section 3.3; starred and preferences live in Portal Preferences |
| Image renderer, PDF export | `GF pkg/plugins/backendplugin/pluginextensionv2/rendererv2.proto` | drop: headless Chromium per render; server-rendered SVG covers alert images later |
| Query caching, recorded queries, correlations, Scenes reporting | Enterprise or Cloud only (`GFD administration/data-source-management/#query-and-resource-caching`) | needed: a per-organization query cache (section 2.5) |
| Live (WebSocket push), streaming datasources | `SDK backend.StreamHandler`; `GFD setup-grafana/set-up-grafana-live/` | needed later: NGSI-LD subscriptions over the gateway WebSocket; first version polls at `refresh` |

## 2. Internals

### 2.1 Architecture

Grafana is one Go process (`GF pkg/server`) with a React frontend served from the same binary. State lives in a SQL database (SQLite default, MySQL or Postgres, `GF conf/defaults.ini:137`); 12.x moves dashboards and folders behind a Kubernetes-style "unified storage" API (`GF apps/dashboard`), still in the same database for an on-premises install. Backend plugins run as child processes over gRPC (HashiCorp go-plugin, `GF pkg/plugins/backendplugin/grpcplugin/grpc_plugin.go`); core datasources (Prometheus, Loki, Postgres) run in-process (`TargetInMemory`, `GF pkg/plugins/backendplugin/ifaces.go:33-39`). Frontend-only plugins such as `NGP` call their API through Grafana's datasource proxy (`/api/datasources/proxy/uid/{uid}/…`, routes declared in `NGP src/plugin.json:31`).

### 2.2 Data model

| Entity | Key columns | Notes |
|---|---|---|
| `org` | id, name | hard boundary for users' roles, datasources, folders, dashboards, alert rules |
| `user`, `org_user` | user id, org id, role Viewer/Editor/Admin; `is_grafana_admin` server-wide | one user, many orgs |
| `team`, `team_member` | org id | team sync from IdP groups is Enterprise (`DEP …/base-values.yaml.gotmpl:136-139` says the same) |
| `folder` (nested since 11) | org id, uid, parent uid | permissions per folder; nesting depth limit 4 (`GF pkg/services/folder/model.go:30` `MaxNestedFolderDepth`) |
| `dashboard`, `dashboard_version` | org id, uid, folder uid, data (JSON), version | the JSON document is stored whole; versions keep history |
| `library_element` | org id, uid, model | library panels |
| `data_source` | org id, uid, type, url, json_data, secure_json_data (encrypted) | `GF pkg/services/datasources/models.go` |
| `alert_rule`, `alert_rule_version`, `alert_configuration` | org id, rule uid, folder uid, queries, condition | Alertmanager config per org in `alert_configuration` |
| `permission`, `role`, `builtin_role` | RBAC (`GF pkg/services/accesscontrol/models.go`) | fine-grained scopes `dashboards:uid:x`, `datasources:uid:y` |

### 2.3 Query path

1. The panel's targets and expressions go to `POST /api/ds/query` (`GF pkg/api/ds_query.go`) as one request with `from`, `to`, `maxDataPoints`, `intervalMs`.
2. The query service (`GF pkg/services/query`) splits by datasource uid. A request that names the `__expr__` datasource goes to the expression service (`GF pkg/expr/service.go`), which builds a DAG of queries and expressions (`GF pkg/expr/graph.go`) and runs each datasource node first.
3. Each datasource node calls the plugin's `QueryData` (`SDK backend.QueryDataHandler`) with the decrypted settings; the answer is data frames per `refId` (Apache Arrow over gRPC, `SDK data.Frame`).
4. Transformations run in the browser after the answer (`GF packages/grafana-data/src/transformations`), except for alerting, which never sees them.
5. A frontend-only datasource (our NGSI-LD one) skips steps 1-3: its JavaScript calls the proxy, Grafana adds the forwarded OAuth token (`jsonData.oauthPassThru`, `DEP …/projects.yaml:35`) and the frames are built in the browser (`NGP src/frames.ts`). Consequence: alert rules and server-side expressions cannot use it.

### 2.4 Alerting engine

Unified alerting (`GF pkg/services/ngalert`): a scheduler ticks every 10 s (`SchedulerBaseInterval`, `GF pkg/setting/setting_unified_alerting.go:58`) and evaluates each rule at its interval, at least `min_interval = 10s` (`GF conf/defaults.ini:1475`; `GF pkg/services/ngalert/schedule`); evaluation runs the rule's queries and expressions through the same expression service (`GF pkg/services/ngalert/eval`), backend datasources only; the state manager keeps per-series state Normal, Pending, Alerting, NoData, Error, Recovering (`GF pkg/services/ngalert/state`); notifications go to an embedded Alertmanager per organization (`GF pkg/services/ngalert/notifier`), with contact points, notification policies (label routing tree), mute timings and templates. HA: several Grafana instances share the database and share Alertmanager state by gossip (`ha_listen_address`, `ha_peers`, `GF conf/defaults.ini:1415-1421`) or Redis (`ha_redis_*`, `:1348-1357`).

### 2.5 Caching and scaling

Dashboards and datasources are read from the database per request with an in-memory cache; query results are not cached in the open-source edition (query caching is Enterprise, `GFD administration/data-source-management/`). Sessions sit in the database or a remote cache. Horizontal scale needs a shared database and a remote cache; our deployment runs one replica on purpose (`DEP …/base-values.yaml.gotmpl:33-38`). The data proxy keeps an HTTP pool (`GF conf/defaults.ini:249-279`, `timeout = 30`, `max_idle_connections = 100`).

### 2.6 What controlroom keeps, changes, drops

| Topic | Grafana | controlroom |
|---|---|---|
| Process | own server, own login, own database | a module of the one `jc` binary behind jc-router, sharing the Portal's session, Postgres and policy engine |
| Storage | dashboard JSON whole in `dashboard.data` | the imported Grafana JSON whole (schemaVersion 42 after migration) in `cr_dashboard.model jsonb`, plus a normalized index (panels, datasource refs, variables) for search, authz and impact queries |
| Query execution | split between backend (core, backend plugins, expressions) and browser (frontend plugins, transformations) | server only: every query, expression and transformation runs in controlroom, so alerts, Portal panels and MCP reads get the same numbers and no datasource credential or token handling reaches a browser |
| Wire format | data frames (Arrow) | one frame type shared with the SDK grid and viz renderer (section 3.2), JSON to the browser, Arrow IPC between Rust parts |
| Alerting | per-org embedded Alertmanager | per-organization rule evaluation in the same scheduler crate; delivery through the platform's notification path; Prometheus rules of the platform stay where they are |
| Cache | none (OSS) | per-organization query cache keyed by (org, datasource, canonical query, aligned range), TTL from `refresh` or `queryCachingTTL` (`dashboard_kind.cue:702`) |

## 3. Plugin system, datasources, expressions and transformations

### 3.1 Grafana's plugin contract

| Plugin type | Contract | Source |
|---|---|---|
| Datasource, backend | `QueryData` (frames per refId), `CheckHealth` (status + message), `CallResource` (any HTTP under `/api/datasources/uid/{uid}/resources/*`, used by query editors for metric names, label values), `CollectMetrics`, `QueryChunkedData`, `RunStream`/`SubscribeStream`/`PublishStream`, `ValidateAdmission`/`MutateAdmission`, `ConvertObjects` | `GF pkg/plugins/backendplugin/ifaces.go:22-30`; `SDK backend/` |
| Datasource, frontend | a `DataSourceApi` class with `query()`, `testDatasource()`, `metricFindQuery()` (variables), `annotations`, plus React components `QueryEditor`, `ConfigEditor`, `VariableQueryEditor` | `GF packages/grafana-data/src/types/datasource.ts`; example `NGP src/datasource.ts:14-165` |
| Panel | React component + options builder | `GF public/app/plugins/panel/*` |
| App | pages, routes, bundled datasources and panels | `GFD developers/plugins/` |
| Mixed datasource | panel datasource `-- Mixed --` (uid `-- Mixed --`): each target names its own datasource | `GFD panels-visualizations/query-transform-data/#mixed` |
| Expressions | pseudo-datasource uid `__expr__`, type `__expr__`; targets with `type` math, reduce, resample, classic_conditions, threshold, sql | `GF pkg/expr/query.go:14-28` |

Plugin signing (`GFD administration/plugin-management/plugin-integrity/`) is Grafana's only control over plugin code; our image allow-lists one unsigned plugin by id (`DEP …/base-values.yaml.gotmpl:100-101`).

### 3.2 controlroom datasource interface

One Rust trait, implemented in-process by built-ins and by a WASM adapter for third-party plugins:

```rust
pub trait Datasource: Send + Sync {
    fn kind(&self) -> &'static str;                       // "prometheus", "ngsild", "postgres", "odata", "loki", "wasm:<id>"
    async fn query(&self, ctx: &QueryCtx, q: &[Query]) -> Result<Vec<FrameSet>, DsError>; // QueryData
    async fn health(&self, ctx: &QueryCtx) -> Health;     // CheckHealth
    async fn resource(&self, ctx: &QueryCtx, r: ResourceReq) -> Result<ResourceResp, DsError>; // CallResource: editor helpers only
    fn editor(&self) -> EditorSchema;                     // JSON Schema of the target + field hints, drives the Portal query editor
    fn import(&self, grafana_target: &serde_json::Value) -> ImportOutcome; // Grafana target -> Query, or a named warning
    fn export(&self, q: &Query) -> serde_json::Value;     // Query -> Grafana target, the inverse of import
}
```

`QueryCtx` carries organization id, instance id, the caller's jc-auth subject, time range, `maxDataPoints`, `intervalMs` and a deadline; it never carries a raw credential (credentials are resolved by secretRef inside the datasource at call time).

`FrameSet` is a list of frames, each with a name, fields (name, type `time|number|string|bool|json|geo`, unit, labels, values in columnar vectors) and `meta` (executed query string, notices, `preferredVisualisationType`). It is Grafana's data frame minus Arrow-only types, so import and export are lossless for every frame the built-ins emit, and the SDK grid (`POR sdk/src/grid`) and viz renderer (`DEP components/viz`) read the same JSON shape.

Built-ins:

| Datasource | Query language | Grafana target fields kept on import | Notes |
|---|---|---|---|
| Prometheus | PromQL to the HTTP API `query`, `query_range`, `labels`, `label/{n}/values`, `series` | `expr`, `legendFormat`, `instant`, `range`, `interval`, `intervalFactor`, `format` (`time_series`, `table`, `heatmap`), `exemplar` (warned, dropped) | used by 61 targets; `label_values()` variable query; the PromQL subset we use is 8 functions (section 1.2), the full language is passed through to Prometheus unparsed except for variable interpolation |
| NGSI-LD (Antares through the gateway) | the `NGP` query model: `queryType` entity, temporal, geo, nodegraph; `entityType`, `entityId`, `idPattern`, `attributes`, `customQuery` (q), `scopeQuery`, `georel`, `geometry`, `coordinates`, `geoproperty`, `geoLocation`, `timeProperty`, `aggrMethod`, `aggrPeriodDuration`, `lastN`, `format`, `lang`, `limit`, `entityName`, `namePattern`, `useLongEntityName`, `ngsildOptions`, node-graph fields | all of `NGP src/types.ts:67-124` | used by 6 targets plus the Portal's 4 kinds; misspelled `timseries` accepted as the plugin does (`NGP src/types.ts:17`); reads go to the Endpoint with the caller's own token, so the Endpoint's Policy and Antares views decide (KNOWLEDGE: reads are decided by Antares) |
| OData 4.01 (any jc module exposing OData, Antares `/x/views/{view}/odata/v4`) | `$filter`, `$select`, `$orderby`, `$apply` (aggregate, groupby) | none (Grafana has no core OData datasource) | new |
| Postgres (read-only SQL views granted to the organization) | SQL, single `SELECT`, parsed and checked against the allowed views before it runs | `rawSql`, `format`, `editorMode`; macros `$__timeFilter`, `$__timeGroup`, `$__interval` | no dashboard uses it today |
| Loki | LogQL | `expr`, `queryType`, `maxLines` | not deployed (`grep -rli loki DEP components` prints nothing); trait slot only, built when logs move to a queryable store |

### 3.3 Third-party datasources as WASM components

A third-party datasource is a WASM component on the platform wasm-host (`PLT crates/wasm-host`), with a WIT world `jc:controlroom/datasource@0.1.0` exporting `query`, `health`, `resource`, `editor-schema`, `import-target`, `export-target`, and importing only `jc:controlroom/http-out` (outbound HTTP through the host) and `jc:controlroom/secret` (resolve a secretRef the datasource config names, value never returned to the guest's caller or logged).

| Control | Value | Source / reason |
|---|---|---|
| Linear memory per instance | 64 MiB default, lower per plugin | `PLT crates/wasm-host/src/limits.rs:35` |
| Wall time per call | 5 s (request), 60 s for a background refresh job | `limits.rs:36`; KNOWLEDGE T-3579 |
| Fuel | 200 billion units backstop | `limits.rs:40` |
| Request and response size | 2 MiB in, 8 MiB out | `limits.rs:41-42` |
| Concurrency | 16 per plugin, 64 per organization | `limits.rs:43-44` |
| Network | none ambient; `http-out` only to hosts on the organization's egress allow-list for that datasource, resolved addresses checked against private and loopback ranges after DNS (jc-core outbound guard, KNOWLEDGE T-6027) | SSRF class, section 4 |
| Credentials | secretRef only, resolved by the host per call | CLAUDE.md non-negotiables |
| Signing | the component digest pinned in the organization's datasource manifest; an unknown digest does not load | replaces Grafana plugin signing |

### 3.4 Query editor, calculation step and the Grafana name table

Portal query editor per panel (section 9 places it): pick a source from a dropdown the server fills with the datasources the person may query in that organization; build the query in a form generated from `editor()` (PromQL text with metric and label completion from `resource()`, NGSI-LD form with type, attribute and filter dropdowns filled from the Endpoint's model, SQL text with the allowed views listed); preview the frames in the SDK grid; add a second or third source (each a `refId`); add calculation steps by name. Every submitted datasource uid, entity type and attribute is checked again on the server (403 or 422 naming the field), per the UI rule of the role.

Expressions and transformations keep Grafana's names and option shapes, so an imported dashboard's `targets` and `transformations` run unchanged:

| Grafana | Where Grafana runs it | controlroom function | First version |
|---|---|---|---|
| expression `math` (`$A + $B`; functions abs, log, round, ceil, floor, nan, inf, infn, null, is_nan, is_inf, is_null, is_number) | server, `GF pkg/expr/mathexp/funcs.go` | `expr::math`, same grammar | yes |
| expression `reduce` (mean, min, max, sum, count, last, median; modes strict, dropNN, replaceNN) | server, `GF pkg/expr/mathexp/reduce.go:18-28` | `expr::reduce` | yes |
| expression `resample` (window, downsampler, upsampler) | server | `expr::resample` | yes |
| expression `threshold` (gt, lt, within_range, outside_range; hysteresis) | server, `GF pkg/expr/threshold.go`, `hysteresis.go` | `expr::threshold` | yes, alerts need it |
| expression `classic_conditions` | server, `GF pkg/expr/classic` | `expr::classic` | yes, import of legacy alerts |
| expression `sql` (MySQL dialect over frames through Grafana's fork of go-mysql-server, `GF go.mod:59`, `:715`; DuckDB in 11.0 behind a flag) | server, `GF pkg/expr/sql` | `expr::sql` with a parsed `SELECT`-only subset over the input frames, no functions that read files, network or settings | after the others; see the CVE class in section 4 |
| `organize` | browser | `tx::organize` (exclude, index, rename) | yes, used 4 times |
| `reduce`, `calculateField`, `merge`, `joinByField` (seriesToColumns), `concatenate`, `filterFieldsByName`, `filterByValue`, `filterByRefId`, `sortBy`, `limit`, `groupBy`, `labelsToFields`, `convertFieldType`, `renameByRegex`, `seriesToRows`, `partitionByValues`, `formatTime`, `formatString`, `extractFields`, `rowsToFields`, `configFromData`, `fieldLookup`, `prepareTimeSeries`, `timeSeriesTable`, `transpose`, `histogram`, `groupingToMatrix`, `groupToNestedTable`, `joinByLabels`, `ensureColumns`, `convertFrameType`, `filterFrames`, `noop` | browser, `GF packages/grafana-data/src/transformations/transformers/*.ts` (44 ids in `ids.ts`) | `tx::<id>`, one Rust function per id with Grafana's option struct | the first 12 of this row, the rest by usage in imported dashboards |
| `heatmap`, `spatial`, `regression`, `smoothing`, `rotate`, `append` | browser | `tx::<id>` or a named import warning | warning first |

## 4. Security

### 4.1 Login, sessions, authorization

| Topic | Grafana as we run it | controlroom |
|---|---|---|
| Login | second login: Grafana's own OAuth client and cookie (`DEP …/base-values.yaml.gotmpl:115-167`) | none of its own: the Portal session (one `jc` binary) or a bearer token verified by jc-auth (`PLT crates/jc-core/src/auth/token.rs`) |
| Session | Grafana cookie, `cookie_samesite = lax` (`GF conf/defaults.ini:418`); token refresh for pass-through (`base-values.yaml.gotmpl:161`) | the Portal's session; no second cookie |
| Authorization | org role Viewer/Admin from groups; inside an org every viewer queries every datasource (datasource permissions are Enterprise) | jc-auth decides per (subject, organization, project, kind `Dashboard` or `Datasource`, verb); a datasource query is admitted only if the subject may read that datasource, and an NGSI-LD query is decided again by the Endpoint's Policy |
| Admin credential | Grafana local admin in a Secret, used by `provision.sh:16-19` and by the Portal (`POR src/config.rs:10-20`) | none: provisioning and Portal writes are calls inside the binary under the caller's or the reconciler's identity |
| Embedding | `frame-ancestors 'self'` (`DEP …/apisix-plugins.yaml:63-75`) | no frame: panels render inside Portal pages under the Portal CSP (section 9) |

### 4.2 Datasource credentials and the query proxy

Grafana stores `secure_json_data` encrypted with a key in `[security]` (`GF conf/defaults.ini:374-472`) and proxies frontend plugin calls with that credential or the forwarded user token. controlroom holds no datasource secret in its tables: a datasource manifest names a secretRef that the reconciler resolves (CLAUDE.md non-negotiables); NGSI-LD and OData datasources use the caller's own token, exchanged for the Endpoint audience (standard token exchange, KNOWLEDGE T-6063) instead of one Grafana client carrying every Endpoint audience (`DEP components/grafana/keycloak-clients.yaml:36-67`). Outbound calls go only to the allow-listed hosts of that datasource, with redirects off (Grafana's `data_source_proxy_whitelist`, `GF conf/defaults.ini:400`, is empty by default and allows everything), a timeout and a response size cap.

### 4.3 CVE history by class and the design answer

Counted from `ADV` (28 advisories: 3 critical, 7 high, 18 medium) plus the advisories on grafana.com named below.

| Class | Examples | controlroom answer |
|---|---|---|
| Stored XSS in panels and editors | CVE-2023-22462 (Text panel), CVE-2022-23552 (ResourcePicker), CVE-2022-31097 (alerting), CVE-2021-41174, CVE-2022-21702 (proxy) | panels are SDK React components with no HTML or Markdown passthrough; text panels render Markdown to a safe subset on the server; CSP with nonce (`POR src/csp.rs`) |
| Path traversal in static plugin files | CVE-2021-43798, CVE-2021-43813, CVE-2021-43815 | no plugin static files served; assets are embedded in the binary |
| Authorization bypass, IDOR, privilege escalation across orgs or folders | CVE-2021-39226 (snapshots), CVE-2022-21713 (teams), CVE-2022-36062 (folders), CVE-2021-41244 (org admin over other orgs), CVE-2022-39328 (race), CVE-2022-24812, CVE-2022-35957 | one policy engine, forced RLS per organization (section 5), no snapshots, isolation tests per route |
| Credential and token leak through the datasource proxy | CVE-2022-31130, CVE-2022-39201, CVE-2022-21673 | no browser-reachable proxy; tokens exchanged per Endpoint audience; a WASM plugin never sees the caller's token |
| SSRF and network restriction bypass | CVE-2022-29170 (redirects) | per-datasource allow-list, redirects off, post-DNS address check |
| OAuth account takeover, identity confusion | CVE-2022-31107, CVE-2022-39306, CVE-2022-39229, CVE-2023-3128 (grafana.com) | no login code: wardkeep and jc-auth |
| Plugin signature bypass, malicious plugin code | CVE-2022-31123 | WASM components pinned by digest, no ambient capabilities |
| CSRF | CVE-2022-21703 | Portal CSRF protection on every write |
| Expression engine code execution | CVE-2024-9264 (SQL expressions over DuckDB, grafana.com) | SQL expression is a parsed `SELECT` subset evaluated over in-memory frames, no embedded database engine, no file or network functions |
| Open redirect plus XSS through plugin routes | CVE-2025-4123, CVE-2025-6023 (grafana.com) | no plugin routes; redirects only to relative Portal paths |
| Sensitive cache | CVE-2022-23498 | query cache keyed by organization and subject class; `Cache-Control: private, no-store` on data answers |
| Container base CVEs | 7 fixable CRITICALs in 12.3.1, a CISA KEV row in 12.4.12 (`DEP components/grafana/images.yaml:9-15`) | no extra image: controlroom ships inside the `jc` binary |

## 5. Tenancy

### 5.1 Grafana's model and limits

| Question | Grafana 12.4 | Source |
|---|---|---|
| Unit of isolation | organization: dashboards, folders, datasources, alert rules, Alertmanager config, service accounts | `GFD administration/organization-management/` |
| Groups inside an org | teams; team sync from IdP groups is Enterprise | `DEP …/base-values.yaml.gotmpl:136-139` |
| Folder and dashboard permissions | yes in OSS | `GFD administration/roles-and-permissions/` |
| Datasource permissions (who may query) | Enterprise and Cloud only | `GFD administration/data-source-management/#data-source-permissions` |
| Org mapping from the IdP | `org_mapping` by name or id, read at start | KNOWLEDGE T-6504: names for newer orgs drop people into Main Org, so we map by number (`base-values.yaml.gotmpl:141-156`) |
| Several instances per organization | not modelled: one org holds everything | |
| Row-level isolation in the database | none: one schema, `org_id` columns, checked in Go | |

### 5.2 Platform today

One realm per installation; each Organization owns a group subtree and tokens carry full group paths (`docs Decisions/adr-n-058-several-organizations-per-installation.md`; KNOWLEDGE T-6408). Grafana today mirrors projects, not Organizations: one Grafana org per project (`provision.sh:1-6`), groups `/helsinki`, `/bbsk` (`DEP .ci/example-deployments/environments/dev/grafana.yaml.gotmpl:5-16`). jc-core already has a `Dashboard` kind with pages, widgets and `visibility` (`PLT crates/jc-core/src/kinds/dashboard.rs:20-93`), and the Portal treats saving a visualization as kind `Dashboard`, project-wide (`POR src/api/grafana.rs:25-27`).

### 5.3 controlroom design

| Requirement | Design |
|---|---|
| Ids in every table | `installation_id`, `org_id` (UUIDv7) on every row; `instance_id` for an organization running several controlroom instances (e.g. an operations room and a public room with different datasources and branding); `project_id` and `folder_uid` for placement |
| Forced RLS | `FORCE ROW LEVEL SECURITY` on `cr_dashboard`, `cr_dashboard_version`, `cr_folder`, `cr_datasource`, `cr_library_panel`, `cr_alert_rule`, `cr_alert_state`, `cr_query_cache`; policy `org_id = current_setting('cr.org')::uuid`; the app role is not BYPASSRLS; predicates on btree keys only (leakproof operators, KNOWLEDGE T-4852) |
| One identity, one policy engine | wardkeep issues the token, jc-auth decides; Grafana roles map at import: Viewer to read, Editor to propose, Admin to approve, per folder through RoleBindings |
| Folders | Grafana folder uid and path kept; a folder belongs to one project; nested to Grafana's limit |
| Datasource scope | a datasource belongs to an organization and is granted to projects; querying needs read on the datasource and, for NGSI-LD and OData, the Endpoint's own Policy |
| Quotas per organization | dashboards, panels per dashboard, datasources, WASM plugins, queries per minute, concurrent queries, cache bytes, alert rules, evaluations per minute; enforced in the write transaction (`SELECT … FOR UPDATE` on the quota row) and at the query door |
| Domains and services | a dashboard can be served on the organization's own host through jc-router; uids are unique per organization, so two organizations import the same Grafana uid (`jc-portal`) without collision |

Isolation tests (Rust integration tests over Postgres with forced RLS, organizations `a` and `b` holding dashboards with the same uid, folders with the same title, datasources with the same name):

1. A viewer of `a` lists dashboards, folders, datasources, library panels, alert rules: zero rows of `b`; `total` counts only `a`.
2. A viewer of `a` gets `b`'s dashboard by uid: the same 404 body as an unknown uid.
3. A viewer of `a` posts a query naming `b`'s datasource uid: 404, and no outbound call leaves the host (counted on a mock).
4. A dashboard of `a` imported with a datasource ref to a uid that exists only in `b`: import reports "datasource not found", never binds to `b`'s.
5. Query cache: the same PromQL from `a` and `b` never shares an entry (cache key test).
6. Alert evaluation of `a` never reads `b`'s datasources; alert state and history of `b` are invisible to `a`.
7. Search and MCP reads with a text that only `b`'s titles contain: no hit, and the response time class equals an empty search.
8. Export of `a`'s folder contains no `b` uid, datasource or library panel.

## 6. Operations

| Topic | Today | controlroom |
|---|---|---|
| Provisioning as code | file provider for 7 dashboards, postStart hook calling the admin API for project orgs, datasources, folders (`provision.sh`) | manifests in the forge (jc-core kinds `Dashboard`, `Datasource`, `AlertRule`, carrying the Grafana JSON as `spec.grafana`), applied by the reconciler; the same check, plan, apply path as every other kind |
| Migrations | Grafana migrates schemaVersion on load in the frontend and, since 12, in the backend (`GF apps/dashboard/pkg/migration/migrate.go`); database migrations on start | import migrates any schemaVersion 0 to 42 with a port of `GF apps/dashboard/pkg/migration/schemaversion/v*.go`; our files at 39 pass v40 (refresh to string), v41 (drop `timepicker.time_options`), v42 (`hideFrom.tooltip` when `hideFrom.viz`); sqlx migrations for the tables |
| Backups | nothing to back up: emptyDir, all state provisioned or swept back by the Portal | rows in the platform Postgres, covered by its nightly dump; the forge holds the source |
| Restart | org numbering must match `org_mapping`, hook refuses to go on otherwise (`provision.sh:41-45`); Portal sweep restores visualizations every 300 s | no derived copy to restore |
| Memory | 128-256 MiB dev, 256-512 MiB prod (section 1.1) | budget inside the whole-platform 2 GB target: 40 MiB resident idle, 120 MiB ceiling under 20 concurrent panel queries (frames streamed per series, cache capped per organization, WASM pool shared with wasm-host) |
| CPU | Grafana request 50-100m | queries are I/O bound; expression and transformation cost measured per panel in the oracle of section 8 |
| Prometheus dependency | dev runs Prometheus and Alertmanager at 0 replicas at times on owner order (AI_shared_folder 2026-11-03 06:35Z) | Prometheus datasource health shows "unreachable" on the panel with the source named; other panels keep drawing |

## 7. Grafana JSON compatibility and import

**Decided (worker-t6649, owner may override):** controlroom stores an imported or authored dashboard as Grafana classic JSON at schemaVersion 42 (the document Grafana itself stores), validated against `GF kinds/dashboard/dashboard_kind.cue`, plus a normalized index. Because the owner asks for read and write compatibility, a separate internal schema would make every export a translation that can lose fields; storing Grafana's document makes import, export, import a fixed point by construction. The presets that T-6641 proposes for agents (`line`, `bar`, `stat`, `table`, `logs`, `CRR` via code-factory.md section 12) expand into Grafana panel JSON on write; a Vega-Lite chart is a panel of type `jc-vegalite` with the spec in `options.spec`, which Grafana shows as "panel plugin not found" after export (named in the export report). Options: own schema with importer only (T-6641 D6), Perses as the store (`CRR`), Grafana JSON as the store (chosen).

### 7.1 Compatibility matrix

Verdicts: **supports** (kept and drawn), **maps** (kept in the document, drawn through a named equivalent), **refuses** (kept in the document, not drawn, import warning with the JSON pointer).

| JSON feature | Used by us | Verdict | Import warning or mapping |
|---|---|---|---|
| `uid`, `title`, `description`, `tags`, `editable`, `timezone`, `version` | all 9 files | supports | uid kept per organization |
| `time`, `refresh` | all 9 files | supports | v40 turns a non-string `refresh` into `""` |
| `graphTooltip` | 8 files | supports | Off, Crosshair, Tooltip shared across panels of one page |
| `schemaVersion` 39 | all 9 files | supports | migrated to 42 on import, original value in the import report |
| `panels[].gridPos` (24-column grid) | all | supports | SDK layout grid of 24 columns; at 400 px panels stack in `y`, `x` order |
| `panels[].type` timeseries | 44 | supports | SDK chart, legend and tooltip options kept |
| `panels[].type` table | 8 | supports | SDK grid; `cellHeight`, `showHeader`, `sortBy` kept |
| `panels[].type` stat | 1 (+ Portal) | supports | `reduceOptions.calcs` through `expr::reduce` names |
| `panels[].type` bargauge | 2 | maps | SDK bar list; gauge styling `displayMode` lcd and gradient drawn as basic, warning `bargauge.displayMode` |
| `panels[].type` geomap with `markers` layer | Portal only | maps | SDK map (maplibre), markers layer; other layer types refused with a warning |
| `panels[].datasource` and `targets[].datasource` `{type, uid}` | all | supports | uid resolved in the importing organization; missing uid reported, never guessed across organizations |
| PromQL `expr`, `legendFormat`, `refId` | 61 targets | supports | `{{label}}` legend templates kept |
| NGSI-LD target fields (`NGP src/types.ts:67-124`) | 6 targets + Portal | supports | through the NGSI-LD built-in |
| `templating.list[]` type query with `label_values()`, `multi`, `includeAll`, `allValue`, `refresh`, `sort` | 1 | supports | |
| `transformations[]` organize (`excludeByName`, `indexByName`, `renameByName`) | 4 | supports | `tx::organize` |
| `fieldConfig.defaults.unit` (reqps, s, short, percentunit, ms, none, Bps, bytes, d, locale) | 51 panels | supports | unit table ported from `GF packages/grafana-data/src/valueFormats` |
| `fieldConfig.defaults.decimals`, `noValue` | 8 | supports | |
| `fieldConfig.defaults.custom` (fillOpacity, lineWidth, pointSize, showPoints, spanNulls) | 2 | supports | |
| `fieldConfig.overrides[]` matcher `byName` | 9 | supports | properties `displayName`, `unit`, `color`, `custom.*` first; others warned |
| `options.legend`, `options.tooltip` | 2 | supports | |
| `annotations`, `links`, `libraryPanel`, rows, `repeat`, `timeFrom`, `timeShift`, value mappings, thresholds | 0 | supports (thresholds, mappings, links, rows, repeat, time overrides), maps (`libraryPanel` inlined, link to the library panel kept) | not in our files; common in imports (T-6641: overrides on 154 and mappings on 50 of 465 grafana.com panels) |
| Mixed datasource `-- Mixed --` | 0 | supports | |
| Expressions `__expr__` | 0 | supports (math, reduce, resample, threshold, classic_conditions), maps (sql to the restricted subset; a query outside it refused with the parse error) | |
| Panel types outside section 1.3 "needed" | 0 | refuses | warning `panel type X has no controlroom renderer`, panel kept for export |
| Datasource types without a built-in or WASM plugin (CloudWatch, Elasticsearch, InfluxDB) | 0 | refuses | warning names the datasource type; T-6641 found CloudWatch in 3 of 20 grafana.com dashboards |
| Dashboard v2beta1 (`elements`, `layout`) | 0 | maps | converted to v1 with Grafana's own conversion logic ported from `GF apps/dashboard/pkg/migration/conversion` |
| Provisioning YAML: dashboard providers, datasources, alerting (contact points, policies, rules, mute timings, templates) | datasources and dashboards (`base-values.yaml.gotmpl:183-221`) | maps | providers to forge manifests; datasource `secureJsonData` refused (a secretRef must be named instead); contact points carrying secrets refused the same way |

### 7.2 Import and export design

- Import takes a Grafana dashboard JSON, a folder tree (Grafana API export or `grafana-cli`-style directory), or provisioning YAML. It keeps dashboard uids, folder uids and folder paths, and maps datasource refs by uid, then by name, inside the importing organization only.
- Dry run returns a report per dashboard: migrations applied (from and to schemaVersion), each panel's verdict, each warning with its JSON pointer, datasources missing or unreadable for the caller, quota use. Nothing is written.
- Apply writes the manifests to the forge as a change (the same proposal and approval path as other kinds), then the reconciler loads them.
- Export returns Grafana classic JSON at schemaVersion 42, byte-stable key order, `id` removed, datasource refs by uid. Round trip test: for each of our 9 files, `export(import(f))` equals `migrate_to_42(f)` after canonical JSON ordering, and `import(export(import(f)))` equals `import(f)` (fixed point).
- The Grafana HTTP paths our scripts call (`POST /api/dashboards/db`, `GET /api/dashboards/uid/{uid}`, `GET`/`POST /api/datasources`, `POST /api/folders`) are served read and dry-run first, so `provision.sh` and the Portal's `src/grafana.rs` can be pointed at controlroom during migration and then deleted.

### 7.3 CI path

Offline check (no cluster, no network): `jc controlroom check <dir>` validates each JSON against the CUE-derived JSON Schema, runs the migrations and the import dry run, and fails on any refusal not listed in an allow file. Plan: the reconciler diff of dashboards, folders and datasources against the live state, printed in the change. Apply: the reconciler after approval. The same three steps the deployment uses for config as code (owner rule: files are the only source, validate before apply).

## 8. Test oracles

| Oracle | What it proves | Source |
|---|---|---|
| Grafana's migration fixtures: 56 input dashboards with expected outputs | schemaVersion migrations equal Grafana's backend migrator | `GF apps/dashboard/pkg/migration/testdata/input`, `…/output`; driver `GF apps/dashboard/pkg/migration/migrate_test.go` |
| Per-version migration unit tests | each step v2 to v42 | `GF apps/dashboard/pkg/migration/schemaversion/v*_test.go` |
| CUE schema | validation of stored documents | `GF kinds/dashboard/dashboard_kind.cue`, `GF apps/dashboard/kinds/v2beta1/dashboard_spec.cue` |
| Expression tests and request examples | math, reduce, resample, threshold, hysteresis, classic, sql results on fixed frames | `GF pkg/expr/*_test.go`, `GF pkg/expr/query.request.example.json`, `query.panel.example.json` |
| Transformation tests and snapshots | each `tx::<id>` on fixed frames | `GF packages/grafana-data/src/transformations/transformers/*.test.ts`, `__snapshots__` |
| Provisioning testdata | provisioning YAML parse and mapping | `GF pkg/services/provisioning/*/testdata` |
| Differential query run | for each of our 61 PromQL and 6 NGSI-LD targets, the frames controlroom returns equal the frames the pinned Grafana returns for the same range, fetched through `POST /api/ds/query` (Prometheus) and the plugin's frame builder (`NGP src/frames.ts`, run in Node) | a dind Grafana 12.4.14 from our image digest with the 9 dashboards provisioned and a Prometheus fed from a recorded TSDB block |
| Differential render | screenshots at 1440 and 400 px of each of our 9 dashboards in Grafana and in the Portal, compared per panel: same series count, same legend labels, same last value, same unit text (not pixel equality) | Playwright, the role's UI rule |
| Import fidelity | round trip and fixed point of section 7.2 on our 9 files and on T-6641's 20 grafana.com dashboards; the warning list compared with a committed expectation | `scripts/research/grafana-inventory.py` keeps the feature census current |

A worker proves import fidelity by running the oracle rows 1, 7, 8 and 9 in CI on every change to the importer, and attaching the import reports of the 9 files to the task.

## 9. Portal embedding

### 9.1 Today

The Portal never embeds Grafana: the Grafana page lists saved visualizations and opens each in a new tab at `{public_url}/d/{uid}?orgId={org}` (`POR src/api/grafana.rs:214`, `POR ui/src/pages/grafana/GrafanaPage.tsx:94-99`), where the person signs in a second time through Grafana's OAuth client (`DEP …/base-values.yaml.gotmpl:115-131`). Grafana refuses to be framed by other hosts (`DEP components/grafana/apisix-plugins.yaml:59-75`, `allow_embedding = false` default `GF conf/defaults.ini:421`). The page's preview draws rows with the Portal's own components, not Grafana (`GrafanaPage.tsx:191-202`). The Portal docs already name the Grafana login as a friction point (`docs Architecture/09-portal.md:277`).

### 9.2 Design

- controlroom is a module of the one `jc` binary, mounted by jc-router under `/api/v1/organizations/{org}/controlroom/*` (dashboards, panels, queries, imports) and served to the Portal UI in-process; the browser speaks only to the Portal origin with the Portal session.
- Panels render with shared SDK components: timeseries and bar charts with the SDK chart, tables with the SDK grid (`POR sdk/src/grid/EntityGrid.tsx`), stat as server HTML, maps with the SDK map; Portal theme tokens, the person's language (i18n keys for panel chrome; titles from the dashboard), light and dark.
- Two React components in `ui/src/components/controlroom/`: `<DashboardView uid>` and `<PanelView uid panelId>`, both reading `GET …/dashboards/{uid}/render?panel=&from=&to=&vars=`, which returns layout plus frames for the visible panels (first page server-rendered as data, no second round trip), then refreshes per `refresh`.
- At 400 px panels stack in grid order, each at full width with its own height; legends move below the chart; tables keep the SDK grid's phone rules.
- Permissions: the panel components ask the same render route; a panel whose datasource the person may not read shows a named empty state ("You cannot read the source of this panel: <datasource title>") instead of the data; keyboard focus moves panel by panel, each panel has an accessible name and a data table alternative.

### 9.3 Pages that should carry a dashboard or panel today

| Portal page | What to show | Source |
|---|---|---|
| `/projects/$project/grafana` (becomes Dashboards) | the project's dashboards and the query editor of section 3.4; replaces the link-out | `POR ui/src/router.tsx:548-556` |
| Health page | `jc-slo` panels (availability, latency budget) | `POR ui/src/pages/health/HealthLog.tsx`; `DEP …/files/slo.json` |
| Endpoint page | request rate and errors for that Endpoint, entity count over time | `POR ui/src/pages/endpoints`; gateway metrics in `DEP …/files/context-gateway.json` |
| Pipeline page | records in, out, failed over time | `POR src/api/pipelines.rs:442` (metrics), `:527` (stats) |
| Organization costs | cost over time per project | `POR src/api/costs.rs:53` |
| Assistant page | answers, latency, failures | `DEP …/files/assistant.json`; `POR ui/src/pages/assistant` |
| MQTT brokers page | connections and messages per broker | `POR ui/src/pages/mqttbrokers` |
| Dashboards (jc-core `Dashboard` kind) | a controlroom panel as a widget type beside `grid`, `temporal-chart`, `bar-chart` | `PLT crates/jc-core/src/kinds/dashboard.rs:30-70`, `POR ui/src/pages/dashboards/editors.tsx` |

Shared components needed: SDK chart (timeseries, bar), SDK grid (exists), SDK map (exists in the grid's map mode), stat tile, legend, time range picker, variable bar, query editor form generated from `editor()`, empty, loading and error states; each new Portal component exported and vitested (KNOWLEDGE T-5186).

## 10. Argon pack plan

Token counts measured 2026-11-07 by `scripts/research/grafana-sources.sh` (non-blank bytes / 4, tests, testdata, mocks and generated protobuf excluded), `GF` at `3c98af3`:

| Group | Paths | Files | Tokens |
|---|---|---|---|
| G1-dashboard-model | `kinds`, `apps/dashboard/kinds`, `apps/dashboard/pkg/migration/{schemaversion,conversion}`, `pkg/services/provisioning/{dashboards,datasources}`, `pkg/api/{dashboard,folder,datasources}.go`, `pkg/api/dtos` | 96 | 193 766 |
| G2-query-expr | `pkg/expr`, `pkg/services/query`, `pkg/api/pluginproxy`, `pkg/plugins/backendplugin`, `pkg/tsdb/grafanads` | 76 | 123 553 |
| G3-datasources | `pkg/promlib`, `pkg/tsdb/loki`, `pkg/tsdb/grafana-postgresql-datasource` | 80 | 68 584 |
| G4-transform-frames | `packages/grafana-data/src/{transformations,dataframe,field,valueFormats}` | 83 | 112 386 |
| G5-alerting | `pkg/services/ngalert/{api/tooling/definitions,models,eval,schedule,state,notifier}`, `pkg/services/provisioning/alerting` | 140 | 238 971 |
| G6-tenancy-authz | `pkg/services/{org,team,folder,accesscontrol,datasources}`, `pkg/services/dashboards/dashboardaccess` | 96 | 192 651 |
| G7-panels | `public/app/plugins/panel/{timeseries,table,stat,bargauge,geomap}` | 114 | 114 429 |

Our side, measured the same way: O1 deployment (`DEP components/grafana/**`, monitoring rules, `images/grafana/Dockerfile`) 35 405; O2 Portal and platform (`POR src/grafana.rs`, `src/api/grafana.rs`, `GrafanaPage.tsx`, `PLT jc-core/src/kinds/{dashboard,visualization}.rs`, `wasm-host/src/limits.rs`) 32 882; O3 SDK grid (`POR sdk/src/grid`, no tests) 123 241; O4 docs (this page, Architecture/09 and /10, ADR-N-053, ADR-N-058) about 45 000; `NGP src/*.ts` without tests about 25 000.

Contract file (shared by every run, about 15k tokens): crate layout `controlroom-model`, `-query`, `-expr`, `-tx`, `-alert`, `-import`, `-api`; the `Datasource` trait and `FrameSet` of section 3.2; the WIT world of 3.3; table DDL with RLS policies of 5.3; the verdict and warning codes of 7.1; jc-auth types.

| Run | Packs | Tokens | Output |
|---|---|---|---|
| 1 dashboard model and import | contract + G1 + O1 + O4 | about 289k | `controlroom-model` (serde types for v1, v2beta1 read), migrations v0 to v42, CUE-derived validation, `controlroom-import` (dry run, report, export, round trip); about 9k lines |
| 2 query and expressions | contract + G2 + G3 + O2 + `NGP` | about 290k | `controlroom-query` (trait, Prometheus, NGSI-LD, Postgres, OData, query cache, WASM adapter), `controlroom-expr` (math, reduce, resample, threshold, classic, sql subset); about 10k lines |
| 3 transformations and frames | contract + G4 + O3 | about 251k | `controlroom-tx` (44 ids, first 13 complete), `FrameSet`, units and formatting shared with the SDK; about 7k lines |
| 4 alerting | contract + G5 + O1 | about 289k | `controlroom-alert` (scheduler, state, rule and contact point model, provisioning import); about 8k lines |
| 5 tenancy, API and Portal | contract + G6 + G7 + O2 + O4 | about 400k | `controlroom-api` (routes, jc-auth checks, RLS, quotas, Grafana-compatible paths), Portal `DashboardView`, `PanelView`, query editor; about 9k lines |

Every run stays under 500k tokens. Expected output about 43k lines of Rust and TypeScript plus tests.

**Open points the owner may override:** (1) the store format of section 7 (Grafana JSON chosen over T-6641 D6's own schema); (2) `docs Research/next-platform/06-rust-components.md:52` keeps Grafana as an operator tool outside the tenant path, while the owner's order of 2026-11-07 asks for controlroom; this page assumes controlroom replaces Grafana for organizations and operators alike, with Prometheus rules staying for platform alerts; (3) the `CRR` README counts 10 dashboards and 49 panels, the deployment holds 9 and 55 (section 1.2, as T-6641 found).

## Related

- [Dashboards and visualization](../../Architecture/10-dashboards-and-visualization.md): the jc-core Dashboard kind the controlroom panel widget joins.
- [Portal](../../Architecture/09-portal.md): the pages of section 9 and today's Grafana login.
- [ADR-N-053](../../Decisions/adr-n-053-declarative-visualizations.md): Vega-Lite visualizations, the `jc-vegalite` panel of section 7.
- [ADR-N-058](../../Decisions/adr-n-058-several-organizations-per-installation.md): several organizations in one realm, the starting point for section 5.
- [Next platform Rust components](../next-platform/06-rust-components.md): the earlier "keep Grafana" decision this page revisits.
