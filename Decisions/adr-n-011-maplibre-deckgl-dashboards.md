---
sidebar_position: 12
title: "ADR-N-011: MapLibre and deck.gl In-Portal Visualization Engine"
---

# ADR-N-011: MapLibre and deck.gl In-Portal Visualization Engine

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 relied on multiple disparate, heavy external applications for data visualization: Apache Superset for analytical dashboards (ADR 008), Masterportal for geospatial maps (ADR 019), and Grafana for metrics and second-tier reporting (ADR 033).

This caused severe architectural and UX fragmentation:

1. **Multiple Web Applications**: Users were forced to navigate three distinct web portals with inconsistent authentication flows, navigation headers, and styling.
2. **Massive Deployment Footprint**: Running Superset (Python/Celery/Redis/PostgreSQL), Masterportal, and Grafana required substantial cluster memory and multi-container coordination.
3. **Complex Cross-Origin Permissions**: Enforcing multi-tenant dataset permissions inside Superset and Masterportal required complex database synchronizations and gateway proxy rewrites.

We require a unified, accessible visualization engine embedded directly within the Portal UI.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | Dashboards and layers defined as declarative `kind: Dashboard` manifests. |
| Distributed architecture with unified UX | **Full** | Map and analytics dashboards rendered directly inside the single Portal SPA. |
| Modular design | **Full** | Visual layer engine decoupled from underlying data queries. |
| Integrability via defined interfaces | **Full** | Queries data exclusively through standard Endpoints (`file.geojson`, NGSI-LD). |
| Open source as default | **Full** | MapLibre GL JS (BSD-3-Clause) and deck.gl (MIT) are 100% open source. |
| Cloud-native architecture | **Full** | Zero backend server footprint; visual rendering executes entirely on client WebGL. |
| Standard solutions before custom code | **Full** | Leverages established open-source mapping and visualization libraries. |
| Self-contained deployment | **Full** | Bundled within the Portal UI web assets; requires no standalone pods. |
| Technological consistency | **Full** | Pure React 19 component ecosystem. |
| Multi-tenancy | **Full** | Dashboard queries execute under the user's token against policy-guarded Endpoints. |
| Security by design | **Full** | Public dashboards strictly validated in CI to reference only public-audience Endpoints. |

## 3. Decision

1. **Embedded Portal Dashboard Engine**:
   - Dashboards are authored declaratively as `kind: Dashboard` and `kind: Layer` manifests stored in Project directories.
   - Dashboards render directly within the Portal UI SPA, providing a unified user experience.
2. **MapLibre GL JS + deck.gl for Map Visualizations**:
   - Map visualizations integrate **MapLibre GL JS** combined with **deck.gl** via `@deck.gl/mapbox` (`MapboxOverlay`).
   - **Rendering Engine Threshold Rule (UI-21)**:
     - Datasets with **< 50,000 features**: Rendered using native MapLibre GL vector styling.
     - Datasets with **≥ 50,000 features** or requiring spatial aggregation (hexbins, grid clusters): Rendered using deck.gl WebGL layers.
3. **Move Superset, Masterportal, and Grafana to Optional Addons**:
   - Apache Superset, Masterportal, and Grafana are completely removed from the platform core.
   - They are maintained as optional addons (`addons/`) for advanced, specialized enterprise BI or legacy organisational workflows.
   - When deployed, addons access platform data strictly via external Endpoints (`/api/endpoint/{endpointSlug}/...`) like any other client application.

## 4. Consequences

### Positive

- **Unified User Experience**: Users explore maps, charts, and tables in one cohesive, localized interface without tab switching or separate logins.
- **Massive RAM Savings**: Removing Superset and its workers saves ~1.5–3 GB RAM in default platform deployments.
- **Strict Authorization**: Dashboard queries execute through Endpoints; the PEP's policy firewall automatically filters features and attributes without custom BI permissions logic.

### Negative / Trade-offs

- The in-portal chart engine provides essential analytical charts (timeseries, bar, pie, scatter) but does not match the hundreds of specialized visualization widgets available in Superset.

## 5. See Also

- Supersedes: CIVITAS ADR 008, ADR 019, ADR 033.
- Requirements: [UI-17…UI-22 (Dashboards)](../Requirements/portal-and-ui.md), [EP-09 (GeoJSON)](../Requirements/endpoints.md).

## Related

- [UI-17…UI-22 (Dashboards)](../Requirements/portal-and-ui.md) — referenced above.
- [EP-09 (GeoJSON)](../Requirements/endpoints.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
