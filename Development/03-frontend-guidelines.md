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

## Related

- [00-intro](00-intro.md) — the repositories and the toolchain.
- [02-backend-guidelines](02-backend-guidelines.md) — the OpenAPI document this client is generated from.
- [../Architecture/09-portal.md](../Architecture/09-portal.md) — what the Portal is and what it serves.
- [../Architecture/10-dashboards-and-visualization.md](../Architecture/10-dashboards-and-visualization.md) — the map and dashboard rules in full.
