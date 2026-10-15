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
| T-4161 | open data portal | 135 | 129 | 16 |
| T-4162 | public surfaces | 405 | 264 | 25 |
| **total** | | **696** | **537** | **61** |

### Findings by area and severity

| Area | blocker | major | minor |
|---|---:|---:|---:|
| Portal shell | 0 | 6 | 14 |
| open data portal | 0 | 6 | 10 |
| public surfaces | 4 | 13 | 8 |
| **total** | **4** | **25** | **32** |

### Patterns

| Pattern | Shared fix | Findings | Worst | Areas |
|---|---|---:|---|---|
| At 375 px rows, tables and long values run off the screen or get cut | Tables scroll inside their own frame with a scroll hint; long values wrap or truncate with the full value on focus; header text shortens before it cuts | 8 | major | Portal shell, open data portal, public surfaces |
| The visitor's language is ignored: a Slovak visit gets English text, dates or pages | Every surface takes the language from `?lang=`/`ui_locales`/`Accept-Language` before its config default, and its error and empty texts come from the same catalogue | 6 | major | Portal shell, open data portal, public surfaces |
| Raw machine text reaches a visitor: problem JSON, HTTP codes, API names, enum codes | One shared problem renderer per surface (Portal, SDK, assistant host, edge) that turns a problem into a sentence and a way on; enum codes through the label catalogue | 6 | blocker | Portal shell, public surfaces |
| Ids and schema names stand where people expect names | Lists, breadcrumbs and switchers print `title`/`name` and fall back to the id only when no name exists | 4 | major | Portal shell, open data portal |
| An App's first view is a read error or empty, with no data | Apps read through the SDK's retrying reader and show sample-free empty states that say what is missing; a published App needs data before it is listed | 4 | blocker | public surfaces |
| The per-address rate limit breaks pages: white Portal, Apps that 429 themselves | Exempt fingerprinted assets from the per-IP limit and cache them immutably; a chunk-load error boundary with words and a Reload button; Apps batch their reads | 4 | blocker | open data portal, public surfaces |
| Another city's name, domain or font on a city's pages | Organization name, catalogue name and URN domain come from the project or publisher, never from the demo organization's config; a font with Slovak and Czech letters | 4 | major | Portal shell, open data portal |
| Keycloak pages are the stock product: unstyled, English, no way back | A joinedcontext Keycloak theme for login, forgot-password and account with sk messages and a link back to the Portal | 4 | major | Portal shell, public surfaces |
| A dead end: a 404 or refusal with no way on | Not-found and refusal pages keep the header and name the next step (who to ask, where to go) | 4 | minor | Portal shell, public surfaces |
| The floating assistant button or panel covers page content | Reserve the button's space at the page end, and open the panel full screen under 640 px | 3 | major | Portal shell, open data portal, public surfaces |
| A viewer is shown what only a builder can do | Checklists, hints and actions render from the caller's verbs (`/me/permissions`), not from the page | 2 | major | Portal shell |
| (page only) | one fix per page | 12 | | |

### Top 20

| # | Severity | Area | Route | Finding | Screenshot |
|---:|---|---|---|---|---|
| 1 | blocker | public surfaces | `apps/helsinki/bike-weather-demand` | Two red banners on arrival: 'ResourceNotFound / the resource does not exist' (a raw problem type) and 'Weather data could not be read.' | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-bike-weather-demand-first-view-anonymous-en-1440.png` |
| 2 | blocker | public surfaces | `apps/helsinki/air-weather-explorer` | The App opens on 'The measurements could not be read (HTTP 404). Try again later.' and 'No measurements in the chosen period': its first view shows no data. | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-air-weather-explorer-first-view-anonymous-en-1440.png` |
| 3 | blocker | public surfaces | `/projects/helsinki/home` | When the per-IP limit of the Portal host is reached, its JavaScript chunks (/assets/*.js) answer 429 too and the signed-in Portal is a white page with no message; people behind one address (an office, a school, this audit's server) reach it within a minute. | `/workspace/evidence/worker-4/T-4162/public-portal-home-assets-rate-limited-steward-en-1440.png` |
| 4 | blocker | public surfaces | `data/assistant` | Every question to the data portal's assistant ends in 'The assistant's model did not answer. Try again in a minute.' (chat 200, model call failed); the visitor has no answer and no fallback. | `/workspace/evidence/worker-4/T-4162/public-data-assistant-answered-anonymous-en-1440.png` |
| 5 | major | Portal shell | `/projects/helsinki/activity` | On a phone the activity table runs off the right edge: the "What happened" column shows three letters per line and "Who says so" is out of view. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-activity-page-steward-sk-375.png` |
| 6 | major | Portal shell | `/projects/helsinki/activity` | Activity's "What happened" prints raw problem JSON, HTTP status codes, CKAN API names (datastore_upsert, resource_view_list) and full endpoint URLs as the message. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-activity-page-steward-en-1440.png` |
| 7 | major | Portal shell | `idm/login` | A visitor who opens a Portal link with lang=sk is sent by the edge straight to Keycloak, which answers in English: the redirect carries no ui_locales, and kc_locale=sk did not switch it either. | `/workspace/evidence/worker-6/T-4157/shell-idm-login-form-anonymous-sk-768.png` |
| 8 | major | open data portal | `/sk/` | The catalogue offers English only: /sk/ answers 404, every page is served lang="en" and the footer's language menu lists English alone, while the publishers and their data are Slovak. | `/workspace/evidence/worker-6/T-4161/data-portal-sk-slovak-anonymous-sk-375.png` |
| 9 | major | public surfaces | `apps/banskabystrica/banskabystrica-ovzdusie` | A Slovak visitor (?lang=sk, browser sk-SK) gets the App wholly in English: title, help, table headers, buttons; the App manifest carries sk titles. | `/workspace/evidence/worker-4/T-4162/public-apps-banskabystrica-banskabystrica-ovzdusie-first-view-anonymous-sk-375.png` |
| 10 | major | public surfaces | `apps/banskabystrica/banskabystrica-mapa` | An unknown path on an App host answers the raw problem JSON ({"type":…,"detail":"app 'banskabystrica-mapa' not found"}), in English, with the browser's pretty-print box; and the App itself exists. | `/workspace/evidence/worker-4/T-4162/public-apps-banskabystrica-banskabystrica-mapa-unknown-path-anonymous-sk-375.png` |
| 11 | major | public surfaces | `apps/banskabystrica/banskabystrica-data` | 'Kind of event' shows the raw codes museumsGalleriesLibraries, musicDanceTheatre, other. | `/workspace/evidence/worker-4/T-4162/public-apps-banskabystrica-banskabystrica-data-first-view-anonymous-en-1440.png` |
| 12 | major | public surfaces | `apps/* unknown path` | 23 of 24 App hosts answer an unknown path with raw problem JSON 'app … not found' (only hsl-transport falls back to the App). | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-helsinki-kartta-unknown-path-anonymous-en-1440.png` |
| 13 | major | public surfaces | `data/assistant` | On the Slovak page the new assistant panel (T-4138) keeps the English greeting and shows the model failure in English ('The assistant's model did not answer…'). | `/workspace/evidence/worker-4/T-4162/public-data-assistant-answered-anonymous-sk-375.png` |
| 14 | major | Portal shell | `/projects/helsinki/home` | On a Slovak page the organization's name stays English: "City of Helsinki (demo instance, not affiliated)" in the breadcrumb, the footer and the sign-in page. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-home-first-run-steward-sk-1440.png` |
| 15 | major | Portal shell | `/projects/helsinki/home` | The project switcher and the breadcrumb list project ids (banskabystrica, bbsk, helsinki-mobility) instead of the projects' names. | `/workspace/evidence/worker-6/T-4157/shell-projects-helsinki-home-project-switcher-steward-sk-375.png` |
| 16 | major | open data portal | `/` | The footer and /about name the catalogue "the open data catalogue of City of Helsinki (demo instance, not affiliated)" on a catalogue whose publishers are Banská Bystrica, BBSK, Žilina, Praha and Helsinki. | `/workspace/evidence/worker-6/T-4161/data-portal-root-page-anonymous-en-1440.png` |
| 17 | major | open data portal | `/dataset/banskabystrica-verejne` | Banská Bystrica's rows carry Helsinki's domain in their identifier (urn:ngsi-ld:AirQualityObserved:hel.fi:banskabystrica-verejne:eea-SK0263A), shown as the first column of the preview and of the CSV. | `/workspace/evidence/worker-6/T-4161/data-portal-dataset-banskabystrica-verejne-page-anonymous-en-1440.png` |
| 18 | major | public surfaces | `apps/helsinki/data-quality-inspector` | 'The published schema could not be read; validity is not checked' on arrival; three type cards say 'Data could not be read.'; the card labels (Completeness, Valid, Median age) overlap at 1440 px. | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-data-quality-inspector-interaction-anonymous-en-1440.png` |
| 19 | major | public surfaces | `apps/helsinki/kpi-forecast` | 'The indicators' history could not be read (HTTP 404)'; every indicator says 'No history in the last 30 days'; indicators are listed by raw ids (bikes-available-avg-0026). | `/workspace/evidence/worker-4/T-4162/public-apps-helsinki-kpi-forecast-first-view-anonymous-en-1440.png` |
| 20 | major | public surfaces | `apps/zilina/zilina-ukazovatele` | A published App whose only content is 'The city has not published an indicator yet.' while its description promises six numbers. | `/workspace/evidence/worker-4/T-4162/public-apps-zilina-zilina-ukazovatele-first-view-anonymous-en-1440.png` |

<!-- end generated -->

## 3. Status

The block above covers the audits that were finished when the script last ran. T-4164 runs it again over all seven folders, then files the fix tasks: one per pattern with a blocker or major finding, plus one per page-only blocker, at most 15, each named here and in T-4165.

Two findings stay out of the fix tasks because the owner decides them: the public assistant's model call (the proxy that T-4170 turns on) and whether fingerprinted assets leave the per-address rate limit. The chunk-load error boundary, with words and a Reload button, is a Portal fix either way and belongs to the `limit` pattern.

## Related

- [UI writing rules](../User-Guide/ui-writing.md): rules 1 to 8 that the findings cite.
- [Open data sources of the Banská Bystrica region](banska-bystrica-open-data-sources.md): why some Apps open on empty data.
