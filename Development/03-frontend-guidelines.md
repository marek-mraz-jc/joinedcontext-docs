---
sidebar_position: 4
title: "Frontend Development Guidelines (React & TypeScript)"
---

# Frontend Development Guidelines (React & TypeScript)

The Portal UI is a single-page application in `joinedcontext-portal/ui`: **React 19**, **Vite**, **TypeScript** in strict mode, **Tailwind CSS 4**, TanStack Query and TanStack Router, MapLibre GL and deck.gl for maps, and RJSF for the generated forms. `pnpm lint`, `pnpm test` and `pnpm build` (which runs `tsc -b` first) are the gate.

## 1. Generated API Client

The frontend never writes ad-hoc `fetch` or Axios request calls. The API client is generated automatically from the backend OpenAPI definition:

```bash
# Regenerate the types from the backend's OpenAPI document (ui/openapi.json)
pnpm generate:api
```

The generator is `openapi-typescript`, and it writes types, not functions, to `src/api/schema.d.ts`. The client is `openapi-fetch` typed by those paths, in `src/api/client.ts`. A path the OpenAPI document does not describe simply does not typecheck, which is the point.

Use it inside TanStack Query hooks, with the URL scheme the backend declares:

```typescript
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export function useSpace(project: string, name: string) {
  return useQuery({
    queryKey: ["resource", project, "spaces", name],
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/projects/{project}/{plural}/{name}",
        { params: { path: { project, plural: "spaces", name } } },
      );
      if (error) throw error;
      return data;
    },
    staleTime: 30_000,
  });
}
```

Mutations go through the same client: `csrfMiddleware` in `src/api/client.ts` echoes the `jc_csrf` double-submit cookie on every method that is not GET, HEAD or OPTIONS, so a hand-rolled `fetch` is a write the backend refuses.

## 2. Form Generation with `react-jsonschema-form` (RJSF)

Forms are generated declaratively from JSON Schema **draft-07** definitions with `@rjsf/core` and `@rjsf/validator-ajv8` (stack verdict S4). Do not hand-code input forms for blueprints or manifests: a hand-written form drifts from the schema the backend validates against, and the mismatch surfaces as a refusal the person cannot act on.

### Live Entity-Picker Widget

A picker reads the Context Gateway through the person's own session, so it can only offer entities that person is allowed to see. `src/components/forms/widgets/EntityPicker.tsx` is the widget and `src/api/gateway.ts` is the call it makes; the search term is escaped before it goes into an NGSI-LD `q`, because a quote or a backslash in it would end the pattern early.

```typescript
import type { WidgetProps } from "@rjsf/utils";
import { useQuery } from "@tanstack/react-query";
import { searchEntities } from "../../../api/gateway";

export function EntityPicker({ value, onChange, schema, id }: WidgetProps) {
  const space = schema.extra?.space as string;
  const type = schema.extra?.entityType as string;

  const { data: entities = [], isLoading } = useQuery({
    queryKey: ["entities", space, type],
    queryFn: ({ signal }) => searchEntities({ space, type, signal }),
    enabled: Boolean(space && type),
  });

  return (
    <select
      id={id}
      value={value ?? ""}
      onChange={(event) => onChange(event.target.value || undefined)}
      disabled={isLoading}
    >
      <option value="">{/* the empty option carries a translated label */}</option>
      {entities.map((entity) => (
        <option key={entity.id} value={entity.id}>
          {entity.name ?? entity.id}
        </option>
      ))}
    </select>
  );
}
```

## 3. Map Visualizations (MapLibre & deck.gl)

Map visualizations follow the threshold performance rule:

- **< 50,000 Features**: Render using native **MapLibre GL JS** vector and GeoJSON source layers.
- **≥ 50,000 Features or Hexagonal / Heatmap Aggregation**: Render using **deck.gl** layers via the `@deck.gl/mapbox` `MapboxOverlay`.

## 4. Accessibility and Language

Neither is optional and neither is a later pass:

- Every control is reachable and operable from the keyboard, and announces itself to a screen reader. A `div` with an `onClick` is not a button.
- Every string a person reads comes from the locale files in `src/locales`; the UI ships Slovak, English, German and Czech. A literal in a component is a string that cannot be translated and that the locale checks will refuse.

## 5. Buttons

One shared `Button` carries four variants and three sizes, and which one a page reaches for used
to be the author's taste. These are the rules, and `ui/tests/button_rules.test.tsx` is where they
are held:

- **One `primary` per view.** A page, and each dialog on it, offers at most one primary *action*:
  the one thing a person came to do. The same action offered twice — in the page header and again
  in the empty list — is one action and stays primary in both; a second, different primary is two
  answers to the same question. Everything else is `secondary` or `ghost`. The shell around the
  page is not the view: the assistant's bubble is the Portal's own affordance on every page.
- **A label is a verb and its object.** "Propose the change", "Remove the role", "Ask the
  assistant" — never "OK", "Submit", "Yes", "Done" or a bare noun, in any of the four languages.
  A label key lives under the page's own namespace and reads as an action in all of them. A bare
  verb is allowed where its object is the thing beside it, as "Send" is beside a message box.
- **`danger` is for what cannot be undone, and it asks first.** A destructive button opens a
  `ConfirmDialog`; the confirmation is never the focused control when the dialog opens, and never
  the button `Enter` presses by default. Removing a resource asks for its name typed back.
- **A button that starts a request shows `loading` and refuses the second click.** The spinner is
  the button's own (`loading`), not a sentence beside it, and the request is sent once.
- **A button a caller may not use stays, disabled, with the reason** (UI-44). `Button` renders the
  reason only when it is both `disabled` and given a `disabledReason`; `PermissionGuard` passes
  both. A reason alone leaves the button live, which is not a refusal.
- **An icon-only button has a name and a tooltip.** `aria-label` for the screen reader, `title`
  for the pointer, and the two say the same thing.
- **The hit area is at least 24 × 24 CSS px** (WCAG 2.5.8), which is what the `xs` and `sm` sizes
  are measured against.
- **In a dialog, Cancel comes before the action**, in that order, in every dialog on every page.

A control that is not one of these is not a hand-made `<button>`: it is a missing prop on the
shared component, and that is where it is added.

## Related

- [00-intro](00-intro.md) — the repositories and the toolchain.
- [02-backend-guidelines](02-backend-guidelines.md) — the OpenAPI document this client is generated from.
- [../Architecture/09-portal.md](../Architecture/09-portal.md) — what the Portal is and what it serves.
- [../Requirements/portal-and-ui.md](../Requirements/portal-and-ui.md) — UI-44, the disabled-with-a-reason rule the button rules build on.
- [../Architecture/10-dashboards-and-visualization.md](../Architecture/10-dashboards-and-visualization.md) — the map and dashboard rules in full.
