---
sidebar_position: 4
title: Frontend, UI & End-to-End Testing
description: The Portal UI test suites, the browser journeys, the accessibility audit and the locale checks.
---

# Frontend, UI & End-to-End Testing

This page is for whoever changes a screen: which suite covers it, how a journey reaches the view, and what has to hold before the change lands. The Portal UI is Vite, React 19, TypeScript, TanStack Query and Router, `@rjsf/core` forms, MapLibre GL and deck.gl, and i18next with ICU. Everything named here was read off the trees on 2026-09-20.

Three suites cover the frontend, in two repositories:

| Suite | Where | Runs |
|---|---|---|
| Component and hook tests | `joinedcontext-portal`, `ui/tests/`, over 200 files | every push, in the fast lane |
| Playwright specs against a built UI | `joinedcontext-portal`, `ui/e2e/` | the hourly `ci-full` lane |
| Browser journeys against a live deployment | `joinedcontext-conformance`, `e2e/journeys/`, 18 specs | dispatched at a deployment |

---

## 1. Component tests with Vitest

`pnpm test` in `ui/` runs Vitest over `ui/tests/` in `jsdom`, with `@testing-library/react` and `@testing-library/user-event`. One file per screen, hook or mapper, named after it.

What the files assert:

- **Schema-driven forms.** The `@rjsf/core` widgets render from the JSON Schema the API publishes, refuse what the schema refuses, and show the help text of the UiSchema. `ui/tests/form_help.test.ts` holds that help to one sentence in each of the four shipped locales, which is why adding a schema field breaks a test you did not write.
- **State and URL.** Filters, pagination cursors and sort order survive a round trip through the URL search parameters.
- **The API client.** The generated `openapi-typescript` client is exercised against a stubbed `fetch`; there is no Mock Service Worker in the tree.
- **Accessibility of a component.** `ui/tests/a11y.test.tsx` runs `axe-core` over rendered components, ahead of the browser audit.

`pnpm lint` and `pnpm typecheck` are the other two gates. `pnpm typecheck` is `tsc -b`, which type checks `ui/tests` as well; `tsc -p` alone misses them. There is no Prettier in this repository and no coverage report: `eslint` and `tsc -b` are the format and type gate.

---

## 2. Playwright, twice

### Against a built UI, in `joinedcontext-portal`

`pnpm e2e` in `ui/` starts the built UI through Playwright's `webServer` and drives Chromium only. `ui/e2e/` covers the screens a person clicks (dashboards, pipelines, sharing, approvals, the pipeline editor, the preview bridge) and `ui/e2e/live/` holds the journeys that need a real deployment behind the UI: the assistant reading and creating, a workspace copy, secrets never echoed, refusals for a viewer, hostile names, and the forms checklist. Visual baselines live in `ui/e2e/visual.spec.ts-snapshots` and are only ever regenerated from a CI artifact, never from a developer's machine, because a different font renders a different picture.

### Against a live deployment, in `joinedcontext-conformance`

`e2e/journeys/` is 18 specs run against `BASE_URL` with Keycloak OIDC login. Chromium by default; `E2E_ALL_BROWSERS` adds Firefox and WebKit.

```text
01-onboarding-login      07-endpoints-manager     13-dashboard-live
02-blueprint-flow        08-service-account-key   14-drift-revert-adopt
03-approval-review       09-pipelines             15-session
04-map-dashboard         10-approval-round-trip   16-role-permissions
05-deckgl-visualization  11-access-matrix         17-assistant-navigation
06-drift-management      12-localization          18-generate-application
```

Two rules make these journeys worth their runtime:

1. **No shortcut URLs.** A journey reaches a view by clicking what a person clicks, through `getByRole` and `getByLabel`. A view unreachable for a keyboard user fails here instead of passing an audit nobody can open.
2. **A missing fixture skips, a missing credential fails.** `PORTAL_DENSE_DASHBOARD` unset skips the deck.gl journey, because an absent dataset is not a defect of the Portal; `PORTAL_USER` unset fails the run and names the variable, because a silent anonymous run would look like a broken Portal. `JC_DRIFT_TOKEN` is the scoped ServiceAccount that writes the drift for journey 14, never an admin credential.

`e2e/README.md` lists every variable and what an unset one does. Reports land under `JC_REPORTS_DIR`.

---

## 3. The accessibility audit

`e2e/accessibility/wcag.spec.ts` runs `@axe-core/playwright` with the WCAG 2.1 A and AA tags over the nine core views, each opened by clicking: the landing dashboard, the flow gallery, approvals, data models, context spaces, pipelines, endpoints, data access and dashboards. A tenth case opens a generated blueprint form and audits it, because a form built from a schema at runtime is where a label goes missing ([TS-13](../Requirements/testing.md), UI-15, UI-16).

A serious or critical violation fails the case, and the report names the view. Keyboard paths are asserted in the journeys themselves: a control a journey cannot reach with `Tab` and `Enter` fails the journey.

---

## 4. Locale completeness

Four locales ship: Slovak (`sk`), English (`en`), German (`de`) and Czech (`cs`), all under `ui/src/locales/`. `scripts/check-i18n.py` in the conformance repository makes three checks, and its `--selftest` proves each one goes red on a bundle that breaks it:

1. **Key parity.** Every key of the reference bundle exists in every other locale, and no locale carries a key the reference dropped.
2. **Placeholder parity.** Every ICU argument a message uses exists in its translation, so a translated string never renders `{name}` or drops the value.
3. **ICU syntax.** Braces balance, and every `plural`, `select` and `selectordinal` block declares the `other` category ICU requires.

With `--sources ui/src` it also asserts that every key used in the code as `t('…')` exists in the reference bundle, because a mistyped key renders the key itself to the reader.

```bash
python3 scripts/check-i18n.py --locales ui/src/locales --sources ui/src
```

Inside the Portal repository the same ground is held by `ui/tests/i18n.test.tsx` and `ui/tests/locale_style.test.ts`, which run in the fast lane. There is no `pnpm i18n:validate` script; the checker above is the CI form.

## Related

- [00-strategy.md](00-strategy.md) — the lanes these suites run in.
- [02-conformance-tests.md](02-conformance-tests.md) — the standards suites beside the journeys.
- [TS-13](../Requirements/testing.md) — the accessibility requirement this page is verified against.
- [User Guide 07](../User-Guide/07-users-roles-approvals.md) — the approval flow journeys 3 and 10 walk.
- [User Guide 06](../User-Guide/06-dashboards.md) — the dashboards journeys 4, 5 and 13 open.
