---
sidebar_position: 12
title: "UX Photo Audit, October 2026"
description: The screenshots of the Portal, the open data portal and the public surfaces taken on dev in October 2026, their findings ranked, and the shared patterns that the fix tasks address.
---

# UX photo audit, October 2026

This page merges the seven UX photo audits (T-4157 to T-4163) of 2026-10-15 into one ranked list. Read it before you fix a page the audit names: most findings repeat across pages and close with one fix in a shared component, so the fix tasks follow the patterns first and single pages second. The audits photographed dev at 375, 768 and 1440 px, in Slovak and English, as `demo.steward`, `demo.viewer` and an anonymous visitor.

## 1. Method and data sources

Each audit wrote its screenshots, a contact sheet `index.html` and a `findings.json` into `/workspace/evidence/<agent>/<task id>/` on the build sandbox. Only `findings.json` contents reach this page; the screenshots stay on the sandbox, and every path below points there.

| Value | Source |
|---|---|
| PNGs per audit | `*.png` files in the audit's folder |
| Non-blank screenshots | PNGs over 25 KB; a white page saved as PNG is smaller, and the audits checked every smaller file by eye |
| Findings by area and severity | the entries of the folder's `findings.json`, by its `severity`; the area is the audit's, named in `scripts/ux-photo-audit-triage.json` |
| Pattern of a finding | `scripts/ux-photo-audit-triage.json`, matched on the audit and the start of the finding's description |
| Top 20 | severity first, then the size of the finding's pattern, then the audit |

`python3 scripts/ux-photo-audit.py <audit folders>` rewrites section 2. Nothing in it is typed.

## 2. Counts, patterns and the top 20

<!-- generated: scripts/ux-photo-audit.py -->

### Screenshots and findings per audit

| Audit | Area | PNGs | Non-blank (> 25 KB) | Findings |
|---|---|---:|---:|---:|
| T-4157 | Portal shell | 156 | 144 | 20 |
| T-4158 | Portal forms: access | 502 | 502 | 15 |
| T-4159 | Portal forms: data | 177 | 177 | 12 |
| T-4160 | Portal explore and Apps | 370 | 370 | 135 |
| T-4161 | open data portal | 135 | 129 | 16 |
| T-4162 | public surfaces | 405 | 264 | 25 |
| T-4163 | Portal states | 123 | 102 | 15 |
| **total** | | **1868** | **1688** | **238** |

### Findings by area and severity

| Area | blocker | major | minor |
|---|---:|---:|---:|
| Portal shell | 0 | 6 | 14 |
| Portal forms: access | 1 | 10 | 4 |
| Portal forms: data | 0 | 6 | 6 |
| Portal explore and Apps | 0 | 34 | 101 |
| open data portal | 0 | 6 | 10 |
| public surfaces | 4 | 13 | 8 |
| Portal states | 0 | 5 | 10 |
| **total** | **5** | **80** | **153** |

### Patterns

| Pattern | Shared fix | Findings | Worst | Areas |
|---|---|---:|---|---|
| Raw machine text reaches a visitor: problem JSON, HTTP codes, API names, enum codes | One shared problem renderer per surface (Portal, SDK, assistant host, edge) that turns a problem into a sentence and a way on; enum codes through the label catalogue | 29 | blocker | Portal shell, Portal forms: access, Portal forms: data, Portal explore and Apps, public surfaces |
| At 375 px rows, tables and long values run off the screen or get cut | Tables scroll inside their own frame with a scroll hint; long values wrap or truncate with the full value on focus; header text shortens before it cuts | 24 | major | Portal shell, Portal forms: access, Portal forms: data, Portal explore and Apps, open data portal, public surfaces |
| A viewer is shown what only a builder can do | Checklists, hints and actions render from the caller's verbs (`/me/permissions`), not from the page | 14 | major | Portal shell, Portal forms: access, Portal explore and Apps |
| Ids and schema names stand where people expect names | Lists, breadcrumbs and switchers print `title`/`name` and fall back to the id only when no name exists | 13 | major | Portal shell, Portal forms: access, Portal explore and Apps, open data portal |
| The visitor's language is ignored: a Slovak visit gets English text, dates or pages | Every surface takes the language from `?lang=`/`ui_locales`/`Accept-Language` before its config default, and its error and empty texts come from the same catalogue | 11 | major | Portal shell, Portal forms: access, Portal forms: data, Portal explore and Apps, open data portal, public surfaces |
| A failed read drops the shell or tells the wrong story: a first-run checklist, 'you may not create', bare 'Internal Server Error' | One error state inside the shell that says the server failed, in words, with Retry; checklists and create-hints wait for a successful read | 10 | major | Portal forms: access, Portal explore and Apps, Portal states |
| The floating assistant button or panel covers page content | Reserve the button's space at the page end, and open the panel full screen under 640 px | 6 | major | Portal shell, Portal forms: data, Portal explore and Apps, open data portal, public surfaces |
| A schema form prints each field error twice, and one 'Neplatná hodnota' per allowed shape | Each field error shown once; a field whose allowed shapes all fail gets one message that says what to enter (T-4207) | 6 | blocker | Portal forms: access, Portal forms: data |
| A dead end: a 404 or refusal with no way on | Not-found and refusal pages keep the header and name the next step (who to ask, where to go) | 5 | minor | Portal shell, Portal explore and Apps, public surfaces |
| An App's first view is a read error or empty, with no data | Apps read through the SDK's retrying reader and show sample-free empty states that say what is missing; a published App needs data before it is listed | 4 | blocker | public surfaces |
| The per-address rate limit breaks pages: white Portal, Apps that 429 themselves | Exempt fingerprinted assets from the per-IP limit and cache them immutably; a chunk-load error boundary with words and a Reload button; Apps batch their reads | 4 | blocker | open data portal, public surfaces |
| Another city's name, domain or font on a city's pages | Organization name, catalogue name and URN domain come from the project or publisher, never from the demo organization's config; a font with Slovak and Czech letters | 4 | major | Portal shell, open data portal |
| Keycloak pages are the stock product: unstyled, English, no way back | A joinedcontext Keycloak theme for login, forgot-password and account with sk messages and a link back to the Portal | 4 | major | Portal shell, public surfaces |
| (page only) | one fix per page | 104 | | |

### Top 20

| # | Severity | Area | Route | Finding | Screenshot |
|---:|---|---|---|---|---|
| 1 | blocker | public surfaces | `apps/helsinki/bike-weather-demand` | Two red banners on arrival: 'ResourceNotFound / the resource does not exist' (a raw problem type) and 'Weather data could not be read.' | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-bike-weather-demand-first-view-anonymous-en-1440.png` |
| 2 | blocker | Portal forms: access | `/projects/helsinki/settings/service-accounts/new` | An empty Rola under Oprávnenie prints "Neplatná hodnota" about thirty times in a column, one per enum branch of the schema, pushing the form a screen down. | `/workspace/evidence/worker-8/T-4158/access-projects-helsinki-settings-service-accounts-new-project-serviceaccount-new-validation-steward-sk-375.png` |
| 3 | blocker | public surfaces | `apps/helsinki/air-weather-explorer` | The App opens on 'The measurements could not be read (HTTP 404). Try again later.' and 'No measurements in the chosen period': its first view shows no data. | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-air-weather-explorer-first-view-anonymous-en-1440.png` |
| 4 | blocker | public surfaces | `/projects/helsinki/home` | When the per-IP limit of the Portal host is reached, its JavaScript chunks (/assets/*.js) answer 429 too and the signed-in Portal is a white page with no message; people behind one address (an office, a school, this audit's server) reach it within a minute. | `/workspace/evidence/worker-4/T-4162/public-portal-home-assets-rate-limited-steward-en-1440.png` |
| 5 | blocker | public surfaces | `data/assistant` | Every question to the data portal's assistant ends in 'The assistant's model did not answer. Try again in a minute.' (chat 200, model call failed); the visitor has no answer and no fallback. | `/workspace/evidence/worker-4/T-4162/public-data-assistant-answered-anonymous-en-1440.png` |
| 6 | major | Portal shell | `/projects/helsinki/activity` | Activity's "What happened" prints raw problem JSON, HTTP status codes, CKAN API names (datastore_upsert, resource_view_list) and full endpoint URLs as the message. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-activity-page-steward-en-1440.png` |
| 7 | major | Portal forms: access | `/organization/roles/new` | The organization's new-role form says "Rola projektu org.": the internal namespace `org` is read out as a project's name. | `/workspace/evidence/worker-8/T-4158/access-organization-roles-new-org-role-new-open-steward-sk-375.png` |
| 8 | major | Portal forms: access | `/projects/helsinki/policies/new` | Each operation group lists its raw API names as body text (retrieveEntity, queryBatch, retrieveEntityTypeDetails…, up to 22 per group), which fills two screens on a phone. | `/workspace/evidence/worker-8/T-4158/policies-projects-helsinki-policies-new-policy-new-open-steward-sk-375.png` |
| 9 | major | Portal forms: access | `/projects/helsinki/settings/service-accounts/new` | After Skontrolovať on the empty form the box at the top shows the server's raw refusal: "invalid metadata.name … must match DNS-1123 label regex '^[a-z0-9]…'". | `/workspace/evidence/worker-8/T-4158/access-projects-helsinki-settings-service-accounts-new-project-serviceaccount-new-validation-steward-sk-375.png` |
| 10 | major | Portal forms: data | `/projects/helsinki/datasources/$name/edit` | The data source edit form shows a developer warning to the steward: "This form's arrangement manifest asks for something the form cannot do: the schema has no field 'tls.caCertRef.name', so nothing was arranged for it". | `/workspace/evidence/worker-6/T-4159/forms-data-projects-helsinki-datasources-name-edit-datasources-edit-steward-en-375.png` |
| 11 | major | Portal forms: data | `/projects/helsinki/pipelines/$name/edit` | The pipeline's Sample step shows the engine's raw error: "failed assignment (line 1): function content: failed to parse value as JSON: invalid character '<' looking for beginning of value". It is English in the Slovak form and does not say that the source answered HTML or what to do. | `/workspace/evidence/worker-6/T-4159/forms-data-projects-helsinki-pipelines-name-edit-pipelines-edit-tab-1-steward-sk-768.png` |
| 12 | major | Portal explore and Apps | `/projects/bbsk/spaces/new` | Every create form's header prints the raw kind and a machine-built sentence, sk and en: 'Read about ContextSpace in the User Guide' and 'Will be approved when you propose: you hold approve and delete on ContextSpace.'; the same on KnowledgeSource, AssistantDeployment and 'Read about App'. | `/workspace/evidence/worker-2/T-4160/spaces-projects-bbsk-spaces-new-form-open-steward-sk-375.png` |
| 13 | major | Portal explore and Apps | `/projects/bbsk/knowledgesources/new` | The create-form headings show the kind name in CamelCase, sk and en: 'Nový KnowledgeSource' / 'New KnowledgeSource' and 'Nový AssistantDeployment' / 'New AssistantDeployment' (also on the validated-empty shots). | `/workspace/evidence/worker-2/T-4160/knowledge-projects-bbsk-knowledgesources-new-form-open-steward-sk-375.png` |
| 14 | major | Portal explore and Apps | `/catalogue` | The Area/Územie filter lists raw NUTS codes (FI1B1, SK032, SK031, CZ010), and the dataset page shows the area as the URI '<http://data.europa.eu/nuts/code/CZ010>'; sk and en. | `/workspace/evidence/worker-2/T-4160/catalogue-catalogue-list-steward-sk-375.png` |
| 15 | major | Portal explore and Apps | `/projects/bbsk/explore` | Explore's 'Your access' card lists raw API operation names (queryEntity, retrieveAttrTypeInfo, retrieveEntityTypeDetails…) and the chips read 'Smiete queryEntity Hospital' / 'Nesmiete updateAttrs Hospital'; sk and en. | `/workspace/evidence/worker-2/T-4160/explore-projects-bbsk-explore-table-steward-sk-375.png` |
| 16 | major | Portal explore and Apps | `/projects/bbsk/explore` | A query that matches nothing ends in a red English parser error on the Slovak page, 'Nenačítané, skúste znova: invalid q expression "qzxwv-nothing-is-called-this"…', telling the person to retry, and the Filters hint wrongly says the query uses '\|' or brackets; there is no empty state. | `/workspace/evidence/worker-2/T-4160/explore-projects-bbsk-explore-empty-result-steward-sk-375.png` |
| 17 | major | public surfaces | `apps/banskabystrica/banskabystrica-mapa` | An unknown path on an App host answers the raw problem JSON ({"type":…,"detail":"app 'banskabystrica-mapa' not found"}), in English, with the browser's pretty-print box; and the App itself exists. | `/workspace/evidence/worker-4/T-4162/public-apps-banskabystrica-banskabystrica-mapa-unknown-path-anonymous-sk-375.png` |
| 18 | major | public surfaces | `apps/banskabystrica/banskabystrica-data` | 'Kind of event' shows the raw codes museumsGalleriesLibraries, musicDanceTheatre, other. | `/workspace/evidence/worker-4/T-4162/public-apps-banskabystrica-banskabystrica-data-first-view-anonymous-en-1440.png` |
| 19 | major | public surfaces | `apps/* unknown path` | 23 of 24 App hosts answer an unknown path with raw problem JSON 'app … not found' (only hsl-transport falls back to the App). | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-helsinki-kartta-unknown-path-anonymous-en-1440.png` |
| 20 | major | Portal shell | `/projects/helsinki/activity` | On a phone the activity table runs off the right edge: the "What happened" column shows three letters per line and "Who says so" is out of view. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-activity-page-steward-sk-375.png` |

<!-- end generated -->

## 3. Status and fix tasks

The block above covers six of the seven audits. T-4160 (explore and Apps) was still shooting when T-4164 closed; when it lands, its owner adds its findings to `scripts/ux-photo-audit-triage.json` and runs the script again.

Each pattern and its fix tasks, as of 2026-10-16:

| Pattern | Fix tasks |
|---|---|
| `lang` | T-4199 (Apps, assistant, Keycloak, catalogue), T-4212 (form list buttons), T-4228 (Keycloak account console); the Flow wizard's English blueprints stay with T-4165 |
| `raw` | T-4200 (App hosts, assistant host, edge, Activity), T-4208, T-4209, T-4210, T-4211 (access forms); the data source form's developer warning and raw keys, the import page's design note and the pipeline Sample step's engine error stay with T-4165 |
| `phone` | T-4213 (role checkboxes), T-4214 (endpoints row); tables wider than their card (activity, pipelines, the model editor) stay with T-4165 |
| `failed-read` | T-4165: one error state inside the shell |
| `form-errors` | T-4207 |
| `ids` | T-4165 |
| `viewer` | T-4165 |
| `dead-end` | T-4165 (Portal); T-4200 (App hosts) |
| `first-view` | T-4195 |
| `limit` | T-4201; the chunk-load error boundary with words and a Reload button stays with T-4165 |
| `helsinki` | T-4202 |
| `keycloak` | T-4203, T-4228 |
| `float` | T-4204 |

Page-only findings with their own task: T-4215 (empty Policy summary), T-4216 (breadcrumbs), T-4217 (Topics), T-4218 (hyphenated search), T-4219 (pipeline naming, Activity lead), T-4220 (publisher naming), T-4221 (Policies list filter), T-4222 (App grid filters), T-4223 (Administration breadcrumb), T-4225 (Context Spaces counts), T-4233 (Slovak stemming in the catalogue search). The remaining page-only minor findings go to T-4165 when a shared fix touches their page.

One finding waits on the owner: the public assistant's model call, which T-4170 ("proxy on") turns on.

## Related

- [UI writing rules](../User-Guide/ui-writing.md): rules 1 to 8 that the findings cite.
- [Open data sources of the Banská Bystrica region](banska-bystrica-open-data-sources.md): why some Apps open on empty data.
