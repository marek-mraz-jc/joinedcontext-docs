---
sidebar_position: 3
title: "Rust Rewrite Research: CKAN to dataroom"
description: CKAN 2.11.6 inventoried against what the platform uses, its internals, plugin system, security record and tenancy limits, and the Rust design and Argon pack plan for dataroom.
---

# Rust Rewrite Research: CKAN to dataroom

This page is the research input for dataroom (T-6635), the Rust open-data catalogue that replaces CKAN. It is written for the Argon generation pack and for the workers who prove parity afterwards. Every claim names its source: an upstream file at the pinned tag, a doc URL, a file and line of ours at the recorded commit, or a command with its output. Task: T-6638.

## 1. Pins, sources and method

| Source | Pin | How read |
|---|---|---|
| CKAN | tag `ckan-2.11.6` (a22d245, 2026-08-26) | `git clone --depth 1 --branch ckan-2.11.6 https://github.com/ckan/ckan` |
| ckanext-dcat | `v2.4.4` (b059fb3), the version our image installs | `images/ckan/Dockerfile:23` |
| ckanext-oidc-pkce | `v0.4.1` (df740e3, DataShades), the version our image installs | `images/ckan/Dockerfile:18` |
| ckanext-harvest, -scheming, -spatial, -xloader, -showcase, -pages, -fluent, -validation, -geoview, -pdfview, -report, -archiver, -qa, -googleanalytics, -dashboard, -issues; keitaroinc/ckanext-s3filestore | default branch heads of 2026-11-07, commit per repo in `scripts/research/ckan-sources.sh` | shallow clones |
| joinedcontext-deployment | cee6ebcb9 | `/workspace/agents/worker-t6638/joinedcontext-deployment` |
| joinedcontext-platform | e59ceb9f | same |
| joinedcontext-portal | d7f91eb28 | same |
| joinedcontext-docs | 149d9b1 (branch base) | same |
| Live dev catalogue | `https://opendata.dev.joinedcontext.com`, read anonymously 2026-11-07 | `curl .../api/3/action/status_show` |

Measured on dev (anonymous, through the edge, 2026-11-07):

| Command | Answer |
|---|---|
| `status_show` | `ckan_version 2.11.6`, extensions `jc_theme envvars image_view text_view datatables_view datastore oidc_pkce dcat` |
| `package_search?rows=0&facet.field=["organization"]` | 622 datasets, 8 organizations |
| `package_search?q=doprava&rows=20` | 200, 391 405 B, 0.31 s |
| `package_show?id=helsinki-transport` | 200, 23 151 B, 0.21 s |
| `GET /catalog.ttl` | 200, 2 623 341 B, 4.20 s |

Correction to the task text: dev runs neither `ckanext-harvest` nor `ckanext-pages`. The live plugin list above is the whole list. Harvesting is our own CronJob scripts (`charts/ckan/files/harvest-nkod.py`, `harvest-hub.py`, rendered by `charts/ckan/templates/harvest.yaml:17-26`), and the static pages are a blueprint in our theme (`charts/ckan/files/jc_theme/plugin.py:3055-3073`).

Extension usage evidence (`gh api repos/<repo>` stars and last push; `https://pypistats.org/api/packages/<pkg>/recent` downloads in the last month; both read 2026-11-07). PyPI undercounts CKAN extensions: most installs are `pip install -e git+...`.

| Package | Stars | Last push | PyPI/month |
|---|---:|---|---:|
| ckan/ckan | 5 152 | 2026-11-06 | 3 930 |
| ckanext-envvars | 16 | 2024-09-13 | 9 736 (ships in the official image) |
| ckanext-dcat | 195 | 2026-11-03 | 2 640 |
| ckanext-scheming | 102 | 2026-11-04 | 2 487 |
| ckanext-xloader | 58 | 2026-10-25 | 934 |
| ckanext-geoview | 48 | 2026-10-02 | 913 |
| ckanext-harvest | 143 | 2026-11-01 | 649 |
| ckanext-pdfview | 27 | 2026-09-17 | 611 |
| ckanext-oidc-pkce | 5 | 2026-10-29 | 344 |
| ckanext-saml2auth (keitaroinc) | 24 | 2026-08-31 | 261 |
| ckanext-googleanalytics | 36 | 2026-07-02 | 246 |
| ckanext-fluent | 28 | 2026-07-24 | 139 |
| ckanext-spatial | 136 | 2026-11-06 | 131 |
| ckanext-validation | 30 | 2026-10-02 | 86 |
| ckanext-hierarchy | 33 | 2026-10-02 | 78 |
| datapusher-plus (dathere) | 49 | 2026-10-29 | 40 |
| ckanext-s3filestore (keitaroinc) | 9 | 2026-08-18 | 34 |
| ckanext-showcase | 47 | 2026-08-10 | 24 |
| ckanext-pages | 58 | 2026-06-26 | n/a (git installs) |
| ckanext-qa / -archiver / -report | 27 / 21 / 18 | 2026-07 / 2026-07 / 2026-03 | n/a |
| ckanext-dashboard | 29 | 2022-11-07 | n/a |
| ckanext-issues | 14 | 2021-09-16, archived | n/a |

## 2. Capability inventory

"Ours" names the file and line that uses the capability today. Paths without a repo prefix are in joinedcontext-deployment.

### 2.1 Core model and Action API

CKAN 2.11.6 registers 134 core actions (`grep -cE "^def [a-z]" ckan/logic/action/{get,create,update,patch,delete}.py`: 65, 20, 20, 5, 24) and 145 auth functions (`ckan/logic/auth/*.py`).

| Capability (upstream) | Ours today | dataroom |
|---|---|---|
| Datasets (`package_*`: create, show, update, patch, delete, purge, search, autocomplete, revise) `ckan/logic/action/{create,get,update,patch,delete}.py` | jcctl `package_show/create/update/delete` (joinedcontext-platform `crates/jcctl/src/publish/ckan.rs:578-603`, `:994-999`); Portal `package_show/search` (joinedcontext-portal `src/api/catalogue.rs:923`, `:1190`; `src/reconciler/catalog.rs:441`); harvest jobs `package_*` (`charts/ckan/files/harvest-nkod.py`, `harvest-hub.py`) | needed: create, show, update, patch, delete, search; `purge` as an admin op; `revise` and `autocomplete` not needed (no caller) |
| Resources (`resource_*`) inside a dataset | jcctl `resource_patch`, `resource_delete` (fake in `ckan.rs:1845-1866`); resources are written inside `package_update` | needed (as dataset members), standalone `resource_create` kept for API compatibility |
| Resource views (`resource_view_*`) | jcctl `resource_view_list/create/update/delete` (`ckan.rs:746-773`); custom view `jc_visualization` (`plugin.py:3031-3053`) | needed: views are typed plugin outputs (section 4) |
| Organizations (`organization_*`, `organization_member_*`) | Portal reconciler `organization_show/create/patch` (`src/reconciler/ckan.rs:563-577`, `:655`); jcctl the same (`ckan.rs:547-570`); `api-token.py` `organization_create`, `organization_member_create` | needed as **publishers** under a catalogue; membership is not stored (jc-auth decides, section 6) |
| Groups (`group_*`) | none: groups stay empty, the Topic facet replaces them (`plugin.py:3110-3125`) | not needed as stored objects; themes (EU data themes) replace them |
| Tags and vocabularies (`tag_*`, `vocabulary_*`) | tags only, written inside the dataset | tags needed; vocabularies replaced by fixed EU authority lists |
| Users (`user_*`), API tokens (`api_token_*`) | `api-token.py` `api_token_create/list/revoke` keeps one admin and one harvest token in Secrets; users are created by the OIDC login | not needed: identity is wardkeep, tokens are platform tokens (PF-37 forbids API keys) |
| Members, collaborators (`member_*`, `package_collaborator_*`) | none | not needed: jc-auth roles |
| Activity streams (`ckanext/activity`, tables `activity`, `activity_detail`) | none read by our code; the theme shows created and updated dates (`jc_created`, `jc_updated`) | needed as a write into the one platform activity log (shared foundation, T-6635) |
| Following, dashboard (`follow_*`, `user_following_*`, `dashboard`) | none | not needed |
| Feeds (`/feeds/*.atom`), `IFeed` | theme overrides the feed class to fix the broken 2.11 paging (`plugin.py:2926-2944`) | needed: Atom per catalogue, publisher, theme; paging by keyset |
| `status_show`, `site_read`, `config_option_*` | `api-token.py` reads `status_show` | `status_show` kept (health, version); config options are config as code |
| `package_relationship_*` | none | not needed |
| `task_status_*`, `term_translation_*` | none | not needed (`term_translation` is replaced by per-language fields) |
| Jobs (`job_*`, RQ on Redis, `ckan/lib/jobs.py:128`) | none of ours enqueue | background work uses the platform job runner (section 3.4) |
| Licences (`license_list`) | jc-core `CkanPublication.license` (joinedcontext-platform `crates/jc-core/src/kinds/ckan.rs:96-100`) | needed, list from SPDX + EU licence authority |

### 2.2 Search

| Capability | Ours today | dataroom |
|---|---|---|
| `package_search` over Solr 9 (`ckan/lib/search/query.py:371`), `q`, `fq`, `sort`, `rows`, `start`, `facet.field`, `include_private`, `include_drafts` | Portal reads pages of 1000 (`src/reconciler/catalog.rs:38-42`); the theme rewrites `q` into stems and switches to `edismax` (`plugin.py:3075-3085`, `jc_search_words` `:2140`), hides packages (`jc_hide` `:187`), adds facets `vocab_jc_format`, `vocab_jc_topic` (`plugin.py:3099-3108`) | needed: Postgres full-text (section 3.3); the `fq` subset callers send (`organization:x`, `tags:x`, `res_format:x`, `license_id:x`, `vocab_*`) parsed by a fixed grammar, never passed through |
| Solr field set (`ckan/config/solr/schema.xml`): `title`, `notes`, `tags`, `groups`, `organization`, `res_format`, `license_id`, `capacity`, `permission_labels`, `metadata_modified`, `text`, dynamic `extras_*`, `res_extras_*`, `vocab_*` | indexed through `before_dataset_index` | columns and generated `tsvector`; `extras_*` as a jsonb with a declared key list per catalogue |
| `permission_labels` filter (`ckan/lib/plugins.py:651-677`, `query.py:424`) | default labels | replaced by RLS + a `ListObjects` set from jc-auth (section 6) |
| Spatial search (`ckanext-spatial`, Solr bbox) | none; the theme draws maps from NGSI-LD live (`plugin.py` `jc_map`, T-4639) | not built in: a bbox column + PostGIS index is a later plugin if asked |
| Rebuild (`ckan search-index rebuild`) | startup script `charts/ckan/files/startup/03-search-index.sh` | not needed: the index is a generated column in the same transaction |

### 2.3 DCAT, feeds and federation

| Capability | Ours today | dataroom |
|---|---|---|
| ckanext-dcat RDF endpoints `/catalog.{rdf,ttl,jsonld,xml}`, `/dataset/{id}.{fmt}` (`ckanext/dcat/blueprints.py:28-50`), profiles `euro_dcat_ap_2`, `_3`, `dcat_us_3`, `schemaorg`, `croissant` (`ckanext/dcat/profiles/`) | `euro_dcat_ap_3` + our `jc_dcat_ap` (`charts/ckan/files/jc_theme/dcat_profile.py:1-10`, enabled `charts/ckan/templates/ckan.yaml:252-256`) | built in: DCAT-AP 3 serializer reusing joinedcontext-platform `crates/jc-dcat` (2 375 lines today, `crates/jc-dcat/src/lib.rs:1-17`); Turtle, RDF/XML, JSON-LD; paging by `hydra:PartialCollectionView` |
| DCAT RDF harvester (`ckanext/dcat/harvesters/`, `IDCATRDFHarvester` `ckanext/dcat/interfaces.py:72`) | none; our harvests read NKOD SPARQL and ArcGIS Hub with own scripts | built in: DCAT-AP harvester (one source kind), plus the NKOD SPARQL and ArcGIS Hub kinds as built-in source plugins |
| Schema.org JSON-LD in pages (`structured_data` plugin) | theme helper `jc_schema_org` | built in |
| Croissant (ML dataset metadata) | none | not needed now |
| data.europa.eu harvesting our feed | goal of `dcat_profile.py` (DCAT-AP 3.0.1 shapes) | built in: feed valid against the EU SHACL shapes (section 8) |

### 2.4 Data, files and previews

| Capability | Ours today | dataroom |
|---|---|---|
| DataStore (`ckanext/datastore`, `datastore_create/upsert/search/search_sql/delete/info`, its own database, read-only role) | written only by the NKOD harvest and `od-standards.py:274-276` for files with no Endpoint; Endpoint row mirror removed (T-5060, `crates/jc-core/src/kinds/ckan.rs:90-95`) | **not built in.** Endpoint data is read live (no copies). Harvested outside files stay as links plus a cached preview (decision D3) |
| `datastore_search_sql` | reachable through the edge; protected by the read-only role (`components/ckan/README.md` "The DataStore read role") | not needed: never ship caller-written SQL |
| Uploads (`ckan/lib/uploader.py`, `IUploader`), `ckan.max_resource_size` | none used by our flows (resources are links) | built in: object-store upload for small attachments only, with type sniffing and size cap |
| xloader / DataPusher / datapusher-plus | none | not needed (they fill the DataStore) |
| Views `datatables_view`, `text_view`, `image_view` | enabled (`charts/ckan/values.yaml:26`), DataTables patched (`images/ckan/Dockerfile:45-49`), templates overridden in the theme | built in as view plugins that read the Endpoint live (table, text, image, map, chart) |
| `webpage_view`, `video_view`, `audio_view`, `recline` | none | not needed |
| Resource proxy (`ckanext/resourceproxy`) | none | not needed (SSRF surface) |
| Tracking (`ckanext/tracking`) and stats (`ckanext/stats`) | none | usage counts come from gateway metrics (T-6616) |

### 2.5 Site, UI and i18n

| Capability | Ours today | dataroom |
|---|---|---|
| Jinja2 templates, webassets, `ckan.site_*`, themes (`doc/theming/`) | `jc_theme` overrides 48 templates and serves its own JS and CSS (`charts/ckan/files/jc_theme/templates__*`, `public__*`); branding from `branding.json` (`plugin.py:2946-2972`) | built in: one server-rendered theme with tokens per catalogue (section 6.4) |
| Locales (`ckan.locales_offered`, `/sk/...` prefixes, Babel catalogues) | `CKAN__LOCALES_OFFERED` (`charts/ckan/templates/ckan.yaml:140`), sk/en/cs/fi/ca titles | built in: per-language fields (fluent model), UI strings per locale |
| Static pages | own blueprint: `/connector`, `/privacy`, `/terms`, `/support`, `/accessibility`, `/assistants`, `/map/{id}`, `/sitemap.xml`, `/robots.txt` (`plugin.py:3055-3073`) | built in: pages as Markdown rows per catalogue (replaces ckanext-pages) |
| CSP nonce per answer | `jc_csp_header` (`plugin.py:1802`) | built in |
| Login (`/user/login`, Flask-Login, `IAuthenticator`) | `oidc_pkce` (`charts/ckan/files/startup/01-oidc.sh:19-25`) | wardkeep OIDC, section 5 |
| Edge cache of anonymous actions | `ckan-action-cache` 60 s (`components/ckan/apisix-routes.yaml:91-117`, `CKAN__CACHE_EXPIRES` `ckan.yaml:126`) | built in: `Cache-Control: public, max-age=60` + ETag on anonymous reads |

## 3. Internals

### 3.1 Architecture and request flow (upstream)

One Python process type serves everything: a Flask app (`ckan/config/middleware/flask_app.py`) under uWSGI (our image: 2 processes, 1 thread each, `charts/ckan/values.yaml:109`), plus optional RQ workers (`ckan jobs worker`). State lives in PostgreSQL (catalogue DB), a second PostgreSQL DB for the DataStore, Solr for search, Redis for sessions, cache and jobs, and a file volume for uploads.

Request `GET /api/3/action/package_search`:

1. `ckan_before_request` (`flask_app.py:445`): CSRF check for unsafe methods (Flask-WTF), then `identify_user` (`ckan/views/__init__.py:73`): API token from the `Authorization` header (`_get_user_for_apitoken` `:125`, JWT decoded by `ckan/lib/api_token.py:75`), else the Flask-Login session cookie, else the `IAuthenticator.identify` plugins.
2. `ckan/views/api.py:221` `action()` parses the body or query (`_get_request_data` `:143`), looks up the function by name with `get_action` (`ckan/logic/__init__.py:446`). The registry merges core actions with `IActions` plugins; `chained_action` (`:408`) wraps an existing one.
3. The action calls `check_access` (`ckan/logic/__init__.py:329`), which runs the auth function of the same name, possibly chained by `IAuthFunctions`. Auth functions ask `ckan/authz.py` (`has_user_permission_for_group_or_org` `:299`, roles `ROLE_PERMISSIONS` `:248`: admin, editor, member).
4. `package_search` builds a Solr query (`ckan/lib/search/query.py:371`), adds `+permission_labels:(...)` from `IPermissionLabels` (`ckan/lib/plugins.py:668-677`), runs `IPackageController.before_dataset_search`, queries Solr, and returns `data_dict` JSON stored in the index, filtered through `after_dataset_search`.
5. Writes (`package_update`) validate against the dataset schema (`IDatasetForm`), dictize into SQLAlchemy objects (`ckan/lib/dictization/`), commit, then index synchronously in Solr (`ckan/lib/search/index.py:107`), then emit `IPackageController.after_dataset_update` and the activity row.

Our extra hops: APISIX edge (CSP, cache, 429), Linkerd, then CKAN. Writers: the Portal reconciler on the replica holding the lock (`components/ckan/README.md`), jcctl, and the harvest CronJobs.

### 3.2 Data model (upstream tables)

Catalogue DB tables (`ckan/model/*.py`, `ckanext/activity/model`): `package`, `package_extra`, `package_tag`, `package_member`, `package_relationship`, `resource`, `resource_view`, `group` (organizations are groups with `is_organization`), `group_extra`, `member` (user or package in group, with `capacity`), `tag`, `vocabulary`, `user`, `api_token`, `system_info`, `task_status`, `term_translation`, `dashboard`, `user_following_{dataset,group,user}`, `activity`, `activity_detail`, plus `alembic_version`. Core migrations: 106 files in `ckan/migration/versions`. Extras are key/value rows (`package_extra`), which is why scheming stores fields there and why search needs `extras_*` dynamic fields.

dataroom tables (prefix `cat_`, after next-platform [02](../next-platform/02-architecture.md) section 3 "Row"):

| Table | Key | Holds |
|---|---|---|
| `cat_catalogue` | `(org_id, id)`; `host` unique | one catalogue instance: host, theme tokens, languages, publish rules, licence default |
| `cat_publisher` | `(org_id, catalogue_id, id)`; `name` unique per catalogue | CKAN organization equivalent: title per language, logo, contact |
| `cat_dataset` | `(org_id, catalogue_id, id)`; `name` unique per catalogue | title/notes per language (jsonb), tags, themes, licence, `state` (draft, active, withdrawn), `visibility`, `source` (endpoint ref or harvest source), `modified`, generated `search tsvector` |
| `cat_distribution` | `(org_id, catalogue_id, dataset_id, id)` | resource: kind (endpoint representation, link, attachment), URL, media type, format |
| `cat_view` | `(org_id, catalogue_id, distribution_id, id)` | view plugin name + validated config |
| `cat_page` | `(org_id, catalogue_id, slug, lang)` | static page Markdown |
| `cat_harvest_source`, `cat_harvest_run` | `(org_id, catalogue_id, id)` | source kind + config, run log and counts |
| `cat_plugin` | `(org_id, catalogue_id, name)` | enabled plugin, version, config, capability grant |

No `user`, `member`, `api_token` or activity table: identity is wardkeep, rights are jc-auth, activity goes to the shared log.

### 3.3 Search without Solr: measured

Prototype (`scripts/research/fts.sql`, `fts-q.sql`): PostgreSQL 17.11, 20 organizations x 2 catalogues x 1 250 datasets (50 000 rows), forced RLS on `(org_id, catalogue_id)`, query as a non-owner role:

```sql
-- PostgreSQL ships no Slovak or Czech snowball config (pg_ts_config lists catalan, finnish, english, ...):
-- 'simple' + unaccent, and prefix terms for inflected words (what jc_search_words does in the theme today).
CREATE TEXT SEARCH CONFIGURATION jc_simple (COPY = simple);
ALTER TEXT SEARCH CONFIGURATION jc_simple ALTER MAPPING FOR hword, hword_part, word WITH unaccent, simple;
WITH q AS (SELECT to_tsquery('jc_simple', 'ovzdus:* & mesto') AS q),
hit AS (SELECT d.* FROM cat_dataset d, q
        WHERE d.search @@ q.q AND d.state = 'active' AND (NOT d.private OR d.owner_group = ANY($1)))
SELECT (SELECT count(*) FROM hit) AS total,
       (SELECT jsonb_object_agg(f, n) FROM (SELECT unnest(formats) f, count(*) n FROM hit GROUP BY 1) x) AS format_facet,
       (SELECT jsonb_agg(name) FROM (SELECT name FROM hit, q ORDER BY ts_rank_cd(search, q.q) DESC, modified DESC LIMIT 20) p) AS page;
```

Result: total, one facet and a ranked page of 20 in 6.5 ms execution, 1.0 ms planning; RLS left 1 250 visible rows of 50 000. The plan uses the `(org_id, catalogue_id, name)` btree and applies `@@` as a filter, because `ts_match_vq` is not leakproof and cannot run before the RLS qual (same finding as KNOWLEDGE for `@@` in the assistant store). Ceiling: cost grows with the catalogue's own size, never with other tenants'. At 622 datasets on dev today that is far inside budget; above ~50 000 datasets in one catalogue, measure, then partition `cat_dataset` by `catalogue_id` (runtime pruning on the setting). A generated column needs an immutable expression: `array_to_string` is stable, so the prototype wraps it in an `IMMUTABLE` SQL function.

Facets are `GROUP BY` over the hit set (one statement, no second count query); `fq` maps to `WHERE` clauses from a closed grammar.

### 3.4 Background work, caching, scaling

| Upstream | Ours | dataroom |
|---|---|---|
| RQ workers on Redis (`ckan/lib/jobs.py:103-128`) for DataPusher, xloader, harvest stages, emails | none in use; harvest is CronJobs | harvest runs, feed rebuilds and link checks as jobs of the platform runner (ekiben jobs, T-6622 line), per organization queue and quota |
| Solr commit per write (`ckan.search.solr_commit`, `config_declaration.yaml:875`) | default | none: index in the write transaction |
| Beaker/Flask cache, `ckan.cache_expires` | 60 s at the edge | ETag (hash of `modified` + catalogue theme version) and `max-age=60` on anonymous reads |
| Scaling: one pod per RWO volume (`components/ckan/README.md` "What it deploys") | 1 replica | stateless, N replicas; attachments in object storage |

## 4. Plugin and extension system

### 4.1 Upstream mechanism

A plugin is a class registered under the `ckan.plugins` entry point and named in the `ckan.plugins` config key (`config_declaration.yaml:1012`). `plugins.implements(IFoo)` declares which interfaces it serves; `PluginImplementations(IFoo)` iterates them in config order (the first plugin's templates win: `components/ckan/README.md` "Branding"). Plugins run in the CKAN process with full access: database session, config, Flask app, filesystem, network. There is no isolation, no capability model and no resource limit. Load order and `chained_action`/`chained_auth_function` decide overrides.

### 4.2 Every interface (CKAN 2.11.6 and the extensions we rank)

Core, `ckan/plugins/interfaces.py`:

| Interface (line) | Methods | Hooks | dataroom equivalent |
|---|---|---|---|
| `IMiddleware` (69) | make_middleware, make_error_log_middleware | WSGI stack | none (no request middleware from plugins) |
| `IDomainObjectModification` (109) | notify, notify_after_commit | every object write | `on_change` event (WASM, read-only payload) |
| `IFeed` (136) | get_feed_class, get_item_additional_fields | Atom feed | feed item fields (WASM, pure) |
| `IResourceUrlChange` (182) | notify | resource URL changed | `on_change` |
| `IResourceView` (196) | info, can_view, setup_template_variables, view_template, form_template | preview plugins | `view` plugin: config schema + render to HTML fragment (WASM, sandboxed frame) |
| `ITagController` (332) | before_view | tag page | none |
| `IGroupController` (347), `IOrganizationController` (384) | read, create, edit, delete, before_view | group and org lifecycle | `on_change` on publisher |
| `IPackageController` (424) | read, create, edit, delete, after_dataset_create/update/delete/show, before_dataset_search, after_dataset_search, before_dataset_index, before_dataset_view | dataset lifecycle, search, index | `validate` (before write), `on_change` (after commit), `index_terms` (extra search words), `show_transform` (pure) |
| `IResourceController` (546) | before/after resource create/update/delete, before_resource_show | resource lifecycle | same as dataset, per distribution |
| `IPluginObserver` (667) | before/after load/unload | plugin loading | host only |
| `IConfigurable` (697), `IConfigDeclaration` (723), `IConfigurer` (777) | configure, declare_config_options, update_config(_schema) | config | plugin manifest declares its config schema |
| `IActions` (823) | get_actions | add or chain API actions | `action` plugin: new namespaced op `x_<plugin>_<op>` registered in the operation registry; core ops cannot be replaced |
| `IValidators` (854) | get_validators | named validators | `validate` |
| `IAuthFunctions` (879) | get_auth_functions | authorization per action | **not offered**: authorization is jc-auth only; a plugin op declares the permission it needs |
| `ITemplateHelpers` (963) | get_helpers | template helpers | theme tokens + `view` render; no arbitrary helpers |
| `IDatasetForm` (1007) | package_types, schemas, templates, blueprints, validate | dataset types and schemas | dataset schema per catalogue (scheming-style YAML, built in) |
| `IGroupForm` (1314) | group types, schemas, templates | group types | publisher schema (built in) |
| `IFacets` (1559) | dataset_facets, group_facets, organization_facets | search facets | facet list per catalogue (config) |
| `IAuthenticator` (1680) | identify, login, logout, abort, authenticate | login | none: wardkeep only |
| `ITranslation` (1768) | i18n_directory, i18n_locales, i18n_domain | translations | plugin ships its strings in its manifest |
| `IUploader` (1792) | get_uploader, get_resource_uploader | storage backends | host storage trait (built-in crates: local, S3) |
| `IBlueprint` (1882) | get_blueprint | new routes | `page` plugin: GET routes under `/x/<plugin>/` returning HTML or JSON |
| `IPermissionLabels` (1894) | get_dataset_labels, get_user_dataset_labels | search visibility | **not offered** (RLS + jc-auth) |
| `IForkObserver` (1938) | before_fork | uWSGI fork | none |
| `IApiToken` (1948) | token schema, encode/decode, pre/postprocess | API tokens | none (platform tokens) |
| `IClick` (2087) | get_commands | CLI | CLI is generated from the op registry (T-6640) |
| `ISignal` (2114) | get_signal_subscriptions | blinker signals | `on_change` |

Extension interfaces:

| Interface (file:line) | Methods | dataroom |
|---|---|---|
| `IDatastore` (`ckan/ckanext/datastore/interfaces.py:9`), `IDatastoreBackend` (`:165`), `IDataDictionaryForm` (`:190`) | datastore query hooks and backends | not needed (no DataStore) |
| `IColumnTypes`, `IColumnConstraints` (`ckan/ckanext/tabledesigner/interfaces.py:11`, `:35`) | table designer | not needed |
| `IDataPusher` (`ckan/ckanext/datapusher/interfaces.py:9`), `IXloader` (`ckanext-xloader/ckanext/xloader/interfaces.py:4`) | DataStore loaders | not needed |
| `IHarvester` (`ckanext-harvest/ckanext/harvest/interfaces.py:4`) | info, validate_config, get_original_url, gather_stage, fetch_stage, import_stage | `harvest_source` plugin: `gather` (list ids), `fetch` (one record), `import` (map to a dataset draft); host does the HTTP with an allow-list |
| `IDCATRDFHarvester` (`ckanext-dcat/ckanext/dcat/interfaces.py:72`) | before/after download, after parsing, before/after create/update, schema updates | hook points of the built-in DCAT harvester |
| `IDCATURIGenerator` (`ckanext-dcat/ckanext/dcat/interfaces.py:4`) | catalog/dataset/resource/publisher URI | config: URI template per catalogue |
| `ISpatialHarvester` (`ckanext-spatial/ckanext/spatial/interfaces.py:4`) | CSW/WAF harvest hooks | later, as a harvest plugin |
| `IDataValidation`, `IPipeValidation` (`ckanext-validation/ckanext/validation/interfaces.py:4`, `:44`) | Frictionless validation | `validate` plugin |
| `IPagesSchema` (`ckanext-pages/ckanext/pages/interfaces.py:4`) | page schema | built-in pages |
| `IOidcPkce` (`ckanext-oidc-pkce/ckanext/oidc_pkce/interfaces.py:19`) | user lookup and creation | none |
| `IReport` (`ckanext-report/ckanext/report/interfaces.py:4`), `IPipe` (`ckanext-archiver/ckanext/archiver/interfaces.py:9`), `IGoogleAnalytics` (`ckanext-googleanalytics/.../interfaces.py:4`) | reports, archiver pipeline, analytics | see 4.3 |

### 4.3 Extension decisions

| Extension | What it does | Decision | Why |
|---|---|---|---|
| ckanext-dcat | DCAT RDF serializer, profiles, RDF harvester, schema.org, Croissant | **built in** (serializer, DCAT-AP 3 profile, harvester); Croissant not needed | the EU feed is the catalogue's reason to exist; we run it today with our profile on top |
| ckanext-harvest | harvest sources, jobs, objects, gather/fetch/import stages on Redis queues | **built in** core (sources, runs, withdrawal) + `harvest_source` WASM plugins for formats | our two harvesters already prove the rules (allow-list, licence filter, withdrawal on complete read: `components/ckan/README.md` "Catalogue harvests") |
| ckanext-scheming | dataset/org schemas in YAML/JSON, presets, form rendering | **built in** | one schema per catalogue is the core of "publish rules"; no WASM needed |
| ckanext-fluent | multilingual fields (`fluent_text`, `fluent_tags`) | **built in** | sk/en/cs/fi/ca titles exist today; every text field is per language |
| ckanext-spatial | spatial search (bbox, Solr/PostGIS), CSW/WAF/ISO 19139 harvest | spatial search **not needed now**; ISO/CSW harvest as a **WASM example** later | maps read NGSI-LD live; no caller searches by bbox |
| ckanext-xloader, DataPusher, datapusher-plus | load files into the DataStore | **not needed** | no data copies (owner, T-5059..T-5061) |
| ckanext-showcase | showcases (apps using datasets) | **WASM example** (`action` + `page`) | small, self-contained, good first third-party plugin |
| ckanext-pages | CMS pages and blog | **built in** (pages); blog not needed | we run five pages today in our blueprint |
| ckanext-validation | Frictionless table validation reports | **WASM example** (`validate`) | useful for harvested CSV, CPU-bounded by fuel |
| ckanext-geoview | map previews (OpenLayers, Leaflet) of GeoJSON/WMS | **built in** as the map view over the Endpoint | the theme already draws MapLibre maps (`plugin.py` `jc_map`, T-4639) |
| ckanext-pdfview | PDF preview | **WASM example** (`view`) or not needed | no PDF resources today; cheap to add as a view plugin |
| ckanext-report, -archiver, -qa | broken-link archive, openness score, reports | link check **built in** (job); archiver copies **not needed**; QA score as **WASM example** | archiving copies files (no copies); a link check is a few lines |
| ckanext-s3filestore / cloudstorage | uploads in S3 | **built in** storage trait (S3 crate behind a feature) | stateless replicas need object storage |
| ckanext-googleanalytics | GA tracking | **not needed** | no third-party trackers under our CSP; usage from gateway metrics |
| ckanext-issues | dataset issues | **not needed** (archived 2021) | feedback goes to the publisher contact |
| ckanext-dashboard, following | per-user dashboards | **not needed** | Portal is the person's page |
| ckanext-oidc-pkce, saml2auth, ldap | login | **not needed** | wardkeep is the one identity |
| ckanext-hierarchy | nested organizations | **built in** as jc-core Organization > Project | the platform already has the hierarchy |
| ckanext-envvars | env to config | **not needed** | config as code (section 7) |
| ckanext-security (data-govt-nz) | lockout, password rules, MFA | **not needed** | wardkeep owns login security |
| ckanext-datajson (GSA) | Project Open Data JSON | **WASM example** (feed format) | US-only format, good feed-plugin sample |

### 4.4 Rust equivalent

- Built-in plugins: crates behind Cargo features (`dcat`, `harvest-dcat`, `harvest-nkod`, `harvest-arcgis`, `view-table`, `view-map`, `view-text`, `view-image`, `pages`, `storage-s3`), each implementing the same traits the WASM host implements, so a built-in and a component are interchangeable.
- Third-party plugins: WASM components on the platform wasm-host (joinedcontext-platform `crates/wasm-host`), WIT world `jc:catalogue-plugin` next to today's `crates/wasm-host/wit/jc-app.wit`. Limits come from `crates/wasm-host/src/limits.rs:33-46` (64 MiB memory, fuel 200 G, 2 MiB request, 8 MiB response, 16 per App and 64 per tenant concurrency); a catalogue plugin gets a smaller profile: 16 MiB, fuel per call 1 G, 1 s wall time for `validate`/`index_terms`/`show_transform`, 30 s for a harvest `import`.
- Capabilities are explicit imports: `catalogue-read` (datasets of the caller's catalogue, already filtered by the host), `http-fetch` (only hosts in the plugin's granted allow-list, https, size cap, no redirects off-list), `kv` (plugin's own rows under `(org_id, catalogue_id, plugin)`). No SQL, no filesystem, no env, no clock beyond a monotonic counter.
- Lifecycle: install = a `cat_plugin` row through a Change (review lane), signed component digest pinned; enable per catalogue; the host instantiates per call from a pooled pre-compiled component; a trap or limit hit fails that call with a named error and an activity row, never the request of another plugin.
- Hook semantics: `validate` may refuse (field path + message), `index_terms` returns words, `show_transform` returns a JSON patch limited to plugin-owned keys (`x_<plugin>`), `on_change` is fire-and-forget after commit, `view` returns sanitized HTML (host runs an allow-list sanitizer) shown in a sandboxed iframe without same-origin.

## 5. Security

### 5.1 Login flows

CKAN 2.11 with our plugins (Flask-Login session, `ckan/views/__init__.py:73`; ckanext-oidc-pkce `views.py:42-115`):

1. Browser `GET /user/login/oidc-pkce` -> CKAN stores a PKCE verifier and `state` in the session (`views.py:44-47`) -> 302 to the realm `auth` endpoint with `code_challenge` (S256, `utils.py:31-34`).
2. Realm login -> 302 `.../callback?code&state` -> CKAN pops verifier and state, compares state (`views.py:80-93`), posts code + verifier to the token endpoint, reads userinfo.
3. `sync_user` (`utils.py:41-50`) -> `get_oidc_user` finds the user by `plugin_extras.oidc_pkce.sub`, else by `email ILIKE` (`interfaces.py:23-39`), else creates one -> `login_user` (Flask-Login), session cookie.

API: `Authorization: <JWT API token>` (HS256 by default, `api_token.jwt.algorithm`, `config_declaration.yaml:813`; secret = `SECRET_KEY` unless set, `:773-793`), looked up by `jti` in `api_token` (`ckan/lib/api_token.py:118`). Cookie auth in the API is off by default (`ckan.auth.enable_cookie_auth_in_api`, `:634`).

dataroom flows:

1. Browser: wardkeep OIDC code + PKCE, `state` and `nonce` checked, user keyed only on `(iss, sub)` (never email), session = signed, encrypted cookie with a server-side revocation stamp, `SameSite=Lax`, `Secure`, `HttpOnly`, rotated on login.
2. API: wardkeep access token (JWT, audience `dataroom` or the catalogue host), verified by jc-auth (jc-core `Verifier::identify`, KNOWLEDGE "Key a quota ..."), no API keys (PF-37).
3. Machine writers (Portal reconciler, harvest jobs): ServiceAccount client credentials, audience-bound, decided by jc-auth like a person.
4. Anonymous reads: no session, cacheable.

### 5.2 Authorization

Upstream: sysadmin flag on `user`; per-organization roles admin/editor/member (`ckan/authz.py:248-253`); dataset collaborators; 145 auth functions each deciding one action; search visibility through permission labels (`ckan/lib/plugins.py:651-677`). Each action and its auth function are separate code paths, which is where the advisories below come from (an action that forgets a check, a search parameter that bypasses the label filter).

dataroom: one decision call per operation through jc-auth (`Check(subject, permission, object)`, `ListObjects` for lists; next-platform [03](../next-platform/03-identity-and-authz.md) section 3); verbs `read`, `propose`, `approve`, `delete` on kinds `Catalogue`, `Publisher`, `Dataset`, `HarvestSource`, `CataloguePlugin`; RLS on `(org_id, catalogue_id)` as the second wall; private and draft datasets filtered in SQL by the `ListObjects` set before count and paging.

### 5.3 Secrets, crypto, limits

| Area | Upstream / ours today | dataroom |
|---|---|---|
| Session secret | `SECRET_KEY` (`config_declaration.yaml:155`); written by our startup script from a Secret (`charts/ckan/files/startup/00-secret-key.sh`); the shared-secret Docker image advisory CVE-2023-22746 | key from the secrets mount, rotation with `SECRET_KEY_FALLBACKS`-style key list |
| API token secret | JWT HS256 with the same secret | none (no own tokens) |
| Admin and harvest tokens | `api-token.py` keeps two tokens in Secrets, never prints them | none: workloads use ServiceAccounts |
| DB credentials | env from Secrets (`ckan.yaml` `PGPASSWORD`) | secrets mount, role per module without BYPASSRLS |
| CSRF | Flask-WTF on forms (`config_declaration.yaml:651-713`) | double-submit token on every unsafe browser request; API with bearer tokens only |
| Input limits | `ckan.max_resource_size`; form size (CVE-2023-50248 OOM) | body cap 1 MiB per write, field caps from the schema, 1 000 rows per page, query term cap |
| Outbound | harvests: allow-listed hosts, https, TLS on (`components/ckan/README.md`) | host-side fetcher with allow-list per source, private ranges refused after DNS, timeouts, size caps |
| Output | Jinja2 autoescape + Markdown sanitizer (`markdown_extract` advisory) | askama/minijinja autoescape, Markdown through an allow-list sanitizer, CSP nonce |

### 5.4 Upstream advisories by class

Source: `gh api repos/ckan/ckan/security-advisories` (2026-11-07). The six of 2026-10-28 are fixed in 2.11.7; **our 2.11.6 is affected** (filed as T-6643, priority 1).

| Class | Advisories (date) | Rust design answer |
|---|---|---|
| SQL injection in DataStore search/create/SQL endpoint | GHSA-34rr-qrr4-397f high (2026-10-28), CVE-2026-104771 high, CVE-2026-104770 high (2026-08), CVE-2026-42031, CVE-2026-42032 (2026-04) | no DataStore, no caller SQL; sqlx bound parameters only; `fq` parsed by a closed grammar to typed clauses |
| Search parameter bypass of visibility (Solr local params, nested QParser) | CVE-2026-115577 high (2026-08), GHSA-xj2r-hpg6-375c (2026-10), CVE-2024-41674 Solr credential leak in errors | no search engine to pass parameters to; visibility in SQL + RLS; errors never echo backend text |
| Missing or wrong authorization on one action | GHSA-hr6p-cwrr-4gg2 `resource_view_update`, GHSA-gc3w-w5vv-w2vc `member_list`, CVE-2026-84986 follow actions | one registry: an op without a declared permission does not compile; isolation test per op (section 8) |
| Stored and reflected XSS in views and Markdown | GHSA-wg5m-39wv-h9q4, GHSA-8frv-ccr7-4m2p, CVE-2026-115579, CVE-2026-104772, CVE-2026-84985, CVE-2025-54384, CVE-2025-24372, CVE-2024-41675 | autoescape, sanitizer allow-list, view plugins in sandboxed iframes, uploads served with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff` |
| Session fixation, forgeable login | CVE-2026-104773, CVE-2025-64100, GHSA-3h7g-fpc6-9vc9 | session id rotated on login, OIDC only, user keyed on `(iss, sub)` |
| CSRF | CVE-2026-41255 (exemption primed by anonymous requests) | no exemption list; bearer API is not cookie-authenticated |
| SSRF through extensions | CVE-2024-43371 | host-side fetcher with allow-list; no resource proxy |
| RCE / file access through crafted ids | CVE-2023-32321 critical | ids are UUIDs or validated slugs; no path built from an id |
| Shared secrets in images | CVE-2023-22746 | no default secret; refuse to start without one |
| TLS not verified (SMTP) | CVE-2026-41132 | rustls with webpki roots everywhere; no SMTP in dataroom |
| Log injection, DoS by large forms | CVE-2024-27097, CVE-2023-50248 | structured logs (fields, not text), body and field caps |

Plugin-level classes seen in this research: ckanext-oidc-pkce falls back to `email ILIKE` user matching (`interfaces.py:34-39`), so an IdP that lets a person set an unverified e-mail could link to another account; dataroom keys on `(iss, sub)` only.

## 6. Tenancy

### 6.1 Upstream model and limits

CKAN is one site per process and database: `ckan.site_id` names the site in a shared Solr core (`config_declaration.yaml:831`), organizations are groups inside that site, and a sysadmin sees everything. Two catalogues means two CKAN deployments (two databases, two Solr cores or `site_id`s, two Redis prefixes). There is no per-organization domain, theme, quota or isolation below the site; the advisories in 5.4 show that one missed check leaks across organizations of a site.

### 6.2 Today on the platform

| Fact | Source |
|---|---|
| `kind: CkanInstance` is project-scoped, many per project, each with its own URL and token ref | joinedcontext-platform `crates/jc-core/src/kinds/ckan.rs:19-38` |
| An Endpoint publishes to one instance and one CKAN organization | `crates/jc-core/src/kinds/ckan.rs:81-101` |
| Dev runs one CKAN for every CkanInstance; two Endpoints with one `metadata.name` overwrite one package | KNOWLEDGE (T-6071) |
| A CkanInstance's `metadata.title` renames the CKAN organization each pass | KNOWLEDGE (T-6098), `crates/jcctl/src/publish/ckan.rs:547-570` |
| The CKAN organization is a name string, not a jc-core Organization | `ckan.rs` `CkanPublication.organization` |
| Branding is one block per deployment | `components/ckan/README.md` "Branding" |

So today "two catalogues for one organization" needs two CKAN releases, and the tenant boundary is only the CKAN organization name chosen by whoever writes the manifest.

### 6.3 dataroom design

- Keys: every table leads with `org_id uuid NOT NULL` (jc-core Organization), then `catalogue_id uuid NOT NULL` (instance). Project and space live on the dataset's `source` reference and in jc-auth objects, not in the key.
- RLS: `ENABLE` + `FORCE ROW LEVEL SECURITY`; policy `org_id = current_setting('jc.org')::uuid AND catalogue_id = current_setting('jc.catalogue')::uuid`; the app role has no `BYPASSRLS`; settings are `SET LOCAL` per transaction from the resolved host, never from a header or body.
- Host resolution: `Host` -> `cat_catalogue.host` (unique) -> `(org_id, catalogue_id)`; unknown host 404 before any query. A cross-catalogue admin view runs through a separate admin role and op, audited.
- One organization, several catalogues: rows in `cat_catalogue`, each with host, TLS (cert-manager HTTP-01 per host today; no wildcard on dev), theme, languages, publisher list, dataset schema, publish rules (which Endpoints may appear: audience public, licence required, DCAT-AP shape check, approver lane).
- Identity and policy: wardkeep tokens, jc-auth decisions; catalogue roles map to jc-core RoleBinding verbs on kind `Catalogue` and `Dataset`; no per-catalogue user table.
- Quotas per organization and per catalogue: datasets, distributions, attachments bytes, harvest runs per day, plugin fuel per day, requests per minute per anonymous address and per token (edge + in-process limiter keyed on the verified token).
- Federation: each catalogue serves DCAT-AP at `https://<host>/catalog.ttl` (and JSON-LD, RDF/XML) with paging; harvest sources point at other catalogues (ours or external, data.europa.eu, NKOD) with `source` ids that keep provenance; a harvested dataset is read-only in the target catalogue and withdrawn when the source stops listing it.

### 6.4 Isolation tests

1. Two organizations, each with two catalogues; same publisher and dataset names in all four.
2. As org A anonymous and as an org A editor on host A1: `package_search`, `package_show` by name and by id of an A2 and a B1 dataset, facet counts, feed, sitemap, DCAT `catalog.ttl`, `status_show`: every B and A2 object is absent; totals equal A1's own; "not found" answers are byte-identical to an id that never existed; timing within noise (same query plan, RLS filter first).
3. A harvest source in B1 that injects a dataset named like an A1 dataset never changes A1.
4. A WASM plugin enabled in A1 calls `catalogue-read` and gets only A1 rows; its `http-fetch` to a non-granted host fails.
5. An SQL-level test as the app role without settings returns zero rows from every `cat_*` table.

## 7. Operations

| Area | CKAN today | dataroom |
|---|---|---|
| Config | env through ckanext-envvars and ini edited at start (`charts/ckan/templates/ckan.yaml:96-200`, `charts/ckan/files/startup/*.sh`) | one TOML/env set with typed config and unknown keys fatal; catalogues, publishers, schemas, pages, plugins and harvest sources as jc-core manifests (kinds `Catalogue`, `HarvestSource`, `CataloguePlugin`) reconciled from Git |
| Migrations | Alembic, 106 core files + extension migrations, `ckan db upgrade` at start | sqlx migrations, forward-only, checked at boot, one advisory lock |
| Backups | CNPG dumps of two databases + RWO volume | one schema in the shared Postgres (CNPG backups) + object-store bucket versioning |
| Upgrades | rebuild image, patch `datatablesview.js` by sed (`images/ckan/Dockerfile:45-49`), rebuild Solr image | one static binary per release |
| Observability | uWSGI logs, no metrics | OpenTelemetry traces, Prometheus metrics with `org_id`/`catalogue_id` labels for operators only, structured logs with tenant ids at write time (T-6640 rule) |
| Footprint | CKAN + Solr + Redis + two databases; chart resources unset (`charts/ckan/values.yaml:57,78,88`) | one process |

Budget at 100 req/s (whole platform target under 2 GB without the embedder): dataroom **96 MiB RSS, 0.25 vCPU** at 100 req/s of mixed anonymous reads (80 % cached by the edge, 20 % search at ~7 ms DB time each as measured in 3.3), 2 DB connections steady, 6 at peak. The figure is a budget for the generated code to meet, not a measurement; the parity task measures it with k6 against a seeded copy of dev's 622 datasets.

## 8. Test oracles

| Oracle | What it proves | How a worker runs it |
|---|---|---|
| Action API differential | the compatible subset answers like CKAN 2.11.7 (after T-6643): `package_show`, `package_search` (q, fq subset, facets, rows/start, sort), `organization_show`, `status_show`, `license_list` | load the same datasets into a pinned CKAN (docker `ckan/ckan-base:2.11.7` + Solr + Postgres) and dataroom; replay the calls our code makes (jcctl `ckan.rs`, Portal `catalogue.rs`, `reconciler/catalog.rs`, harvest scripts) and a recorded dev log; diff JSON after a declared normalization (ids, timestamps, ordering of equal ranks) |
| jcctl fake as contract | the writer side | joinedcontext-platform `crates/jcctl/src/publish/ckan.rs:1730-1895` (in-memory fake) and `crates/jcctl/tests/it/ckan_http_tests.rs` run against dataroom instead of the fake |
| DCAT-AP 3.0.1 SHACL | feeds valid for EU harvesters | pyshacl against the EU shapes (`https://github.com/SEMICeu/DCAT-AP` release 3.0.1 shapes) on `catalog.ttl` and each `dataset/{id}.ttl`; zero violations |
| data.europa.eu | the real harvester accepts the feed | MQA validator run on the published feed URL (owner action to register the catalogue) |
| Upstream tests | behaviour reference | `ckan/tests/logic/action/test_get.py` (package_search, package_show cases) and `ckanext-dcat/ckanext/dcat/tests/profiles/dcat_ap_3/` read as case lists, ported as Rust tests for the kept surface |
| Isolation suite | section 6.4 | Rust integration tests against Postgres with two app roles |
| Advisory regressions | each class in 5.4 | one test per class (SQL meta-characters in `q` and `fq`, Solr local params text, XSS payload in every text field rendered, session id rotation, CSRF without token) |
| UI journeys | catalogue pages | Playwright journeys (search, dataset, map, feed links) with 1440 + 400 screenshots, UI judge |
| 100 % | | every call in the usage inventory (section 2) has a passing differential or a documented intended difference |

## 9. MCP mapping

Rules (T-6640): every UI operation is one tool in the shared operation registry (`ops::call`), the same jc-auth decision and review lane, results inside the untrusted-data fence, counts after filtering. Today the Portal offers `jc_catalog_search` (segment data-read, joinedcontext-portal `src/connectors.rs:59`), `jc_ckan_status` (`src/ops/views.rs:602`) and `jc_catalogue_draft` (`src/ops/access_tools.rs:30`), both in segment publish (`src/connectors.rs:128-145`); the public hub serves the DCAT catalog as the `catalog` Endpoint.

| Tool | Input | Output | Permission (jc-auth) | Segment |
|---|---|---|---|---|
| `jc_catalogue_list` | org? | catalogues the caller may read: id, host, languages | `read Catalogue` (ListObjects) | publish |
| `jc_catalogue_get` | catalogue | settings, schema, publish rules, plugins | `read Catalogue` | publish |
| `jc_catalogue_propose` | manifest | Change id | `propose Catalogue` (review lane) | publish |
| `jc_dataset_search` | catalogue, q, filters, page | datasets + facets + total | `read Dataset` (visibility set) | data-read |
| `jc_dataset_get` | catalogue, name | dataset with distributions and views | `read Dataset` | data-read |
| `jc_dataset_propose` / `jc_dataset_withdraw` | catalogue, Endpoint ref or draft | Change id | `propose Dataset` / `delete Dataset` | publish |
| `jc_publisher_list` / `jc_publisher_propose` | catalogue | publishers / Change id | `read` / `propose Publisher` | publish |
| `jc_harvest_source_list` / `_propose` | catalogue | sources / Change id | `read` / `propose HarvestSource` | publish |
| `jc_harvest_run_start` | source | run id | `approve HarvestSource` | operate |
| `jc_harvest_run_get` | run | counts per state, skipped items with reasons | `read HarvestSource` | operate |
| `jc_harvest_run_logs` | run, level?, cursor | log lines with fingerprints | `read HarvestSource` | operate |
| `jc_catalogue_plugin_list` / `_propose` | catalogue | plugins, digests, grants / Change id | `read` / `propose CataloguePlugin` | admin |
| `jc_catalogue_activity` | catalogue, object?, cursor | activity rows | `read Catalogue` | operate |
| `jc_catalogue_feed_check` | catalogue | SHACL result summary | `read Catalogue` | publish |

Logs and events carry `org_id`, `catalogue_id`, object id and plugin name at write time. Isolation tests for tools: an org A connector calls every tool with ids, names and hosts of org B and of A's other catalogue when the connector is narrowed to one catalogue; answers are empty or the same refusal as for an unknown id; `jc_harvest_run_logs` never shows a line written by a B plugin.

## 10. Argon pack plan

Measured with repomix 1.18.1 (`scripts/research/ckan-sources.sh`, rerunnable; it clones the pins and prints the table). Tests, migrations, i18n, minified and asset files are excluded from upstream slices.

| Slice | Paths (at the pin) | Files | Tokens |
|---|---|---:|---:|
| core-logic | `ckan/logic/**/*.py`, `ckan/authz.py`, `ckan/lib/api_token.py` | 18 | 97 164 |
| core-model | `ckan/model/**/*.py`, `ckan/lib/dictization/**/*.py` | 29 | 44 594 |
| core-search | `ckan/lib/search/**/*.py`, `ckan/config/solr/schema.xml` | 5 | 14 339 |
| core-plugins | `ckan/plugins/**/*.py`, `ckan/lib/plugins.py` | 8 | 32 396 |
| core-views-api | `ckan/views/{api,__init__,dataset,resource,group,user,feed}.py`, `ckan/config/middleware/flask_app.py` | 8 | 50 918 |
| core-config | `ckan/config/config_declaration.yaml` | 1 | 15 437 |
| ext-activity | `ckanext/activity/**/*.py` | 14 | 36 010 |
| ext-datastore | `ckanext/datastore/**/*.py` + config (read for the API shape only) | 15 | 43 435 |
| doc-api | `doc/api/**/*.rst`, `doc/maintaining/{authorization,configuration}.rst` | 4 | 12 193 |
| doc-extensions | `doc/extensions/**/*.rst` | 15 | 22 623 |
| ext-views | `ckanext/{datatablesview,textview,imageview,multilingual}/**/*.py` | 10 | 7 423 |
| dcat | ckanext-dcat `ckanext/dcat/**/*.py`, `docs/**/*.md`, `ckanext/dcat/schemas/*.yaml` | 59 | 121 810 |
| harvest | ckanext-harvest `ckanext/harvest/**/*.py`, `README.rst` | 32 | 59 538 |
| scheming | ckanext-scheming py, yaml, json, README | 20 | 25 291 |
| fluent | ckanext-fluent py, README | 5 | 4 764 |
| pages-showcase | ckanext-pages + ckanext-showcase py | 29 | 26 591 |
| validation | ckanext-validation py, README | 19 | 22 768 |
| oidc-pkce | ckanext-oidc-pkce py, README (login reference) | 9 | 5 436 |
| spatial | ckanext-spatial py, `doc/**/*.rst` | 25 | 42 106 |
| doc-theming | `doc/theming/**/*.rst` | 17 | 20 290 |
| core-templates | `ckan/templates/{package,organization,home,snippets}/**`, `page.html`, `base.html` | 109 | 41 907 |
| ours-deployment | `components/ckan/README.md`, `apisix-routes.yaml`, `charts/ckan/values.yaml`, `templates/{ckan,harvest}.yaml`, `files/*.py`, `files/startup/*`, `files/jc_theme/*.py`, `images/ckan/Dockerfile` | 17 | 94 226 |
| ours-theme-ui | `charts/ckan/files/jc_theme/templates__*.html`, `public__jc-*.js`, `public__jc-theme.css` | 48 | 55 429 |
| ours-jcctl | joinedcontext-platform `crates/jcctl/src/publish/**`, `crates/jc-core/src/kinds/{ckan,catalog}.rs` | 5 | 32 255 |
| ours-portal | joinedcontext-portal `src/reconciler/{ckan,catalog}.rs`, `src/api/catalogue.rs` | 3 | 41 206 |

Plus in every run: this page (16 317 tokens measured by repomix), the contract file (~15 000), next-platform [02](../next-platform/02-architecture.md) and [03](../next-platform/03-identity-and-authz.md) (~20 000), `crates/wasm-host/src/limits.rs` and `wit/jc-app.wit` (~4 000).

| Run | Slices | Tokens in | Output |
|---|---|---:|---|
| 1 contract + core | core-logic, core-model, core-search, core-plugins, core-views-api, core-config, ext-activity, ext-datastore, doc-api, ours-jcctl, ours-portal + shared (55 000) | 475 000 | contract file (types, op registry entries, SQL schema, plugin WIT) and crates `dataroom-model`, `dataroom-store` (sqlx, RLS), `dataroom-search`, `dataroom-api` (Action API v3 subset + op registry), `dataroom-auth` (jc-auth calls): ~18 000 lines |
| 2 plugins + federation | doc-extensions, ext-views, dcat, harvest, scheming, fluent, pages-showcase, validation, oidc-pkce, ours-deployment + shared + run 1 contract | 445 000 | crates `dataroom-plugin` (host + WIT `jc:catalogue-plugin`), `dataroom-dcat` (on jc-dcat), `dataroom-harvest` (DCAT, NKOD, ArcGIS sources), `dataroom-schema` (scheming/fluent), `dataroom-pages`, two WASM examples (showcase, validation): ~16 000 lines |
| 3 UI + views | spatial, doc-theming, core-templates, ours-theme-ui + shared + contract | 215 000 | server-rendered UI (askama), view plugins (table, map, text, image, chart), theme tokens per catalogue, Playwright journeys: ~10 000 lines |

Each run stays under 500 000 tokens. Total expected output ~44 000 lines, inside T-6635's 40-55k estimate. ext-datastore goes into run 1 only so the API layer refuses `datastore_*` with a clear "not supported" answer instead of 404.

## 11. Decisions and owner questions

Decided (worker-t6638, owner may override):

- D1: dataroom keeps an Action API v3 **subset** (the calls in section 2 that our code and harvesters send) beside its own REST/OData/MCP ops, because jcctl, the Portal and outside harvesters speak it today; options: full Action API, none (breaks jcctl until rewritten).
- D2: no Solr, no Redis: PostgreSQL full-text with `simple` + `unaccent` + prefix terms, because the measured query is 6.5 ms and Slovak/Czech have no snowball config either way; options: Tantivy in process (adds a second index to keep consistent), Meilisearch (another service).
- D3: no DataStore; NKOD and Hub files stay links plus a cached first-page preview (bounded, per catalogue quota), because of the no-data-copies rule; options: keep a DataStore for harvested files only (keeps the SQL surface of 5.4).
- D4: `IAuthFunctions`, `IPermissionLabels`, `IAuthenticator`, `IApiToken`, `IMiddleware` have no plugin equivalent, because authorization and identity are platform-wide (jc-auth, wardkeep); options: allow plugin auth (reopens the per-action bypass class).
- D5: organization in CKAN maps to `cat_publisher` under a catalogue, and the tenant is the jc-core Organization in `org_id`, because CKAN's organization is a display publisher, not a security boundary; options: one catalogue per jc-core Organization only (drops "two catalogues per organization").
- D6: harvest built in with WASM source plugins, because both of our harvesters need the same withdrawal and allow-list rules; options: harvest as ekiben pipelines writing through the dataroom API.
- D7: plugin limits 16 MiB / 1 G fuel / 1 s per hook, 30 s per harvest import, because hooks run on the request path; options: the App profile of `limits.rs` (64 MiB, 200 G).

Questions only the owner can answer:

- Q1: register the dataroom feed with data.europa.eu (needs the publisher account), and for which catalogue host first.
- Q2: may a catalogue of organization A harvest a catalogue of organization B on the same installation without B's consent when B's feed is public, or does cross-organization harvest need B's grant?

## Related

- [Next platform: target architecture](../next-platform/02-architecture.md) — the `org_id` row key and `cat_*` tables this design follows.
- [Next platform: identity and authorization](../next-platform/03-identity-and-authz.md) — the jc-auth `Check` and `ListObjects` calls dataroom makes.
- [Next platform: Rust components](../next-platform/06-rust-components.md) — the earlier verdict to drop CKAN, Solr and Redis.
- [Architecture/04](../../Architecture/04-context-spaces-and-endpoints.md) — Endpoints, the source of every published dataset.
