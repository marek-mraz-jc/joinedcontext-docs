---
sidebar_position: 4
title: "Frontend Development Guidelines (React & TypeScript)"
---

# Frontend Development Guidelines (React & TypeScript)

The Portal UI is a modern, single-page web application built with **React 19**, **Vite**, **TypeScript** (strict mode), and **Tailwind CSS**.

## 1. Generated API Client

The frontend never writes ad-hoc `fetch` or Axios request calls. The API client is generated automatically from the backend OpenAPI definition:

```bash
# Generate TypeScript types and client functions
pnpm run codegen:api
```

Use the client within TanStack Query hooks:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

export function useContextSpace(id: string) {
  return useQuery({
    queryKey: ['spaces', id],
    queryFn: () => api.getSpace({ params: { id } }),
    staleTime: 30_000,
  });
}
```

## 2. Form Generation with `react-jsonschema-form` (RJSF)

Forms are generated declaratively from JSON Schema **draft-07** definitions (stack verdict S4). Do not hand-code input forms for blueprints or manifests.

### Live Entity-Picker Widget

Dynamic pickers query the Context Gateway PEP using the user's active session token, ensuring the user can only select resources they are authorized to view:

```typescript
import { WidgetProps } from '@rjsf/utils';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';

export const GatewayEntityPickerWidget = ({ value, onChange, schema }: WidgetProps) => {
  const entityType = schema.extra?.entityType;
  
  const { data: entities, isLoading } = useQuery({
    queryKey: ['entities', entityType],
    queryFn: () => api.queryEntities({ type: entityType }),
  });

  return (
    <select 
      value={value || ''} 
      onChange={(e) => onChange(e.target.value)}
      disabled={isLoading}
      className="portal-input"
    >
      <option value="">Select an entity...</option>
      {entities?.map((e) => (
        <option key={e.id} value={e.id}>{e.name || e.id}</option>
      ))}
    </select>
  );
};
```

## 3. Map Visualizations (MapLibre & deck.gl)

Map visualizations follow the threshold performance rule:

- **< 50,000 Features**: Render using native **MapLibre GL JS** vector and GeoJSON source layers.
- **≥ 50,000 Features or Hexagonal / Heatmap Aggregation**: Render using **deck.gl** layers via the `@deck.gl/mapbox` `MapboxOverlay`.

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
