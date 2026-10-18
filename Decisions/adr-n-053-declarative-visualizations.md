---
sidebar_position: 54
title: "ADR-N-053: Declarative Visualizations on an Endpoint, Rendered Without Code on Their Own Host"
---

# ADR-N-053: Declarative Visualizations on an Endpoint, Rendered Without Code on Their Own Host

Date: 2026-10-18  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-18 via the supervisor: "create something standardized, so also really complex visualization can be done within ckan dataset for the users", "and make that safe"); format chosen by the supervisor, recorded by worker-2 (T-4640), owner may override

This record lets the publisher of an Endpoint attach charts to its open-data dataset: simple bars and lines up to layered, faceted and linked views. A chart is a published JSON grammar, never code, and it renders where it can reach nothing of CKAN, the Portal or the visitor. Maps on a basemap stay with MapLibre (T-4639).

## 1. Context

A CKAN dataset today shows a table preview and a map. A city that wants to show the temperature of each weather station over a day, or the share of each district in a budget, has two ways out: a custom page with its own JavaScript, or a CKAN extension per chart type. A custom page runs a publisher's code on the catalogue's origin, beside the visitor's session. An extension per chart type covers the charts someone thought of and no others.

The data a chart shows already has a home: the Endpoint, its Policy and the representations it serves (EP-104). A chart that fetched from anywhere else would be a second, unreviewed way out of the platform.

## 2. Decision

### 2.1 The format: Vega-Lite 5 and Vega 5

A visualization is a Vega-Lite 5 or Vega 5 specification: the open, BSD-licensed declarative grammar published at vega.github.io. It covers bar, line, area and point charts, layers, facets and small multiples, heatmaps, `geoshape` thematic maps, and interactive selections with linked brushing. It is JSON, so it is reviewed, diffed and stored in Git like every manifest, and the Portal and the assistant validate it against the published JSON Schema of the pinned version.

### 2.2 The contract: a list on the Endpoint

`spec.catalog.visualizations` on an Endpoint holds the list ([Architecture/04 §3a](../Architecture/04-context-spaces-and-endpoints.md#visualizations-ep-130ep-132)). Each item has a `name`, a `title` and a `description` per language, a `spec`, and a `data` block that names one of the Endpoint's own sources, never a URL:

| `data.source` | Reads | Parameters |
|---|---|---|
| `csv` | `file.csv` of the Endpoint | `type`, the entity type |
| `ogc` | the items of one OGC API Features collection | `collection`; optional `filter` (CQL2 text) and `properties` |
| `odata` | one OData entity set | `entitySet`; optional `$filter`, `$select`, `$apply`, `$orderby` |
| `temporal` | NGSI-LD Query Temporal Evolution of Entities | `type`, `attrs`, `last` (an ISO 8601 duration up to `P31D`); optional `aggrMethod` and `aggrPeriod` |

The view holds the Endpoint slug beside the spec; the renderer resolves the source against that Endpoint's URL on `api.{domain}`, fetches it, and hands the rows to the spec as its one named dataset `source`. A spec reads `{"data": {"name": "source"}}`; it never states where the rows come from.

Decided (worker-2, owner may override): `temporal` joins the three sources the task named, because OData and OGC read the current snapshot of each entity (Antares' `antares-odata` reads no history), so a line over the last 24 hours, which the task asks for as its example, has no other source on the Endpoint. It reads the same Endpoint, under the same Policy, as an NGSI-LD client would.

### 2.3 No code

The Portal, `jcctl validate` and the reconciler accept a spec only when it validates against the pinned Vega-Lite or Vega JSON Schema and passes our refusal list:

1. no `url` anywhere under `data` (and no `data` other than `{"name": "source"}` or inline `values`), because the rows come only from the declared source;
2. no `usermeta`, no `config.loader` and no loader options;
3. no `href` encoding channel and no `href` mark property, unless every value it can take is a literal URL on one of our hosts (`{domain}` and its subdomains);
4. no `image` mark and no `url` channel whose values are not `data:` URIs or URLs on our hosts;
5. at most 200 KB per spec and at most 20 visualizations per Endpoint.

A refusal names the JSON pointer of the member and the rule. Expressions (`calculate`, `filter`, signals) stay allowed: §2.4 makes them harmless.

### 2.4 No eval

The renderer parses every spec with Vega's CSP-safe expression interpreter (`vega-interpreter`, with `ast: true`), so an expression is evaluated by an interpreter over Vega's own expression language and never compiled into JavaScript. An expression reaches no JavaScript global, no `window`, no `fetch` and no prototype. The renderer page's Content-Security-Policy has no `unsafe-eval` and no `unsafe-inline` for scripts, so a bypass of the interpreter would fail in the browser too.

### 2.5 An isolated origin

Two documents on a host of their own, `viz.{domain}` (`viz.dev.joinedcontext.com` on `dev`, `viz.joinedcontext.com` in production, T-4641), split the work so the code that runs a spec owns nothing and can call nothing:

1. **The host page** (`https://viz.{domain}/#{viewId}`) is our code and runs no spec. It reads the view, checks the spec, fetches the declared rows within §2.6, and hands both to the renderer. The catalogue frames it with `sandbox="allow-scripts allow-same-origin allow-downloads"`: the page is on another site than the catalogue, so `allow-same-origin` gives it its own origin, never the catalogue's, and its requests carry `Origin: https://viz.{domain}`, which the gateway's CORS rule admits. A frame with an opaque origin would send `Origin: null`, which the gateway refuses, and opening the gateway to `null` would open it to every sandboxed page on the web.
2. **The renderer** (`/render.html`) runs the spec. The host page frames it with `sandbox="allow-scripts allow-downloads"` and without `allow-same-origin`, so it runs in an opaque origin: it reads no cookie, no storage and no DOM of any host, and a hostile spec that escaped §2.3 and §2.4 would still be stuck in a frame that owns nothing. It takes one message, from a parent on `viz.{domain}` only, and `allow-downloads` is there for the PNG and SVG export alone.

The pages send:

- host page: `Content-Security-Policy: default-src 'none'; script-src https://viz.{domain}; style-src https://viz.{domain}; img-src https://viz.{domain} data:; connect-src https://api.{domain} https://data.{domain}; frame-src https://viz.{domain}; base-uri 'none'; form-action 'none'; frame-ancestors *`. Any page may frame it, because it holds no secret: that is what lets a city put a chart on its own site (the "Embed on a website" snippet, as the map widget does, T-4639);
- renderer: `Content-Security-Policy: default-src 'none'; script-src https://viz.{domain}; style-src https://viz.{domain} 'unsafe-inline'; img-src https://viz.{domain} data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors *`. It connects nowhere. Styles may be inline because `vega-embed` writes its tooltip and menu styles at run time, and a style runs no script. `frame-ancestors` checks every ancestor, the site that embeds the host page too, so it cannot be narrower than the host page's;
- both: `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `Cross-Origin-Opener-Policy: same-origin`, and no cookie set or read.

The page that embeds the host page passes it one CKAN resource view id in the fragment, never a spec or a URL. The host page reads that view anonymously through CKAN's action API (`resource_view_show` on `data.{domain}`, which answers CORS for `https://viz.{domain}` alone), so it renders only what an editor published through the reconciler (§2.7), and CKAN refuses a view of a private dataset to an anonymous caller. The host page checks the spec against §2.3 before it fetches a row and the renderer checks it again before it draws: the publisher's check is not trusted alone. Decided (worker-2, owner may override): the spec comes from CKAN's API by view id rather than in the fragment, because a spec in the fragment would let anyone craft a link that draws any chart on our host; options: the CKAN view (chosen), the spec in the fragment, the Endpoint's DCAT-AP record (would need a gateway change for no gain). Decided (worker-2, owner may override): two frames, because one sandboxed frame cannot both run in an opaque origin and read the gateway, whose CORS rule admits only the platform's own hosts (T-4641, measured on `dev` 2026-10-18: `Origin: null` gets no `Access-Control-Allow-Origin`).

### 2.6 Data limits

The renderer fetches only the declared source of that Endpoint, anonymously (no token reaches the frame), with a timeout of 15 seconds, and stops at 50,000 rows or 20 MB, whichever comes first. Above that it shows a message and draws nothing: a spec over more rows aggregates on the server (OData `$apply`, an OGC filter, `temporal` with `aggrMethod`). A non-public Endpoint's visualizations are not rendered on `viz.{domain}`; the frame would see nothing anyway, and the catalogue lists the dataset as private (EP-69).

### 2.7 Who publishes

Only the Endpoint's editors publish a visualization, through the Portal or `jcctl`: it is a manifest change, reviewed like every manifest change and audited. The reconciler publishes each item into CKAN as a resource view of type `jc_visualization` on the dataset of the Endpoint (EP-63) and removes the views the list no longer names in the same run. CKAN's own UI does not offer `jc_visualization` among the view types, so a CKAN user cannot create one there, and a view created through CKAN's API with a spec of its own is replaced by the reconciler's on the next run.

### 2.8 The assistant drafts

The assistant may draft a spec from a question and the Endpoint's schema. A human saves it in the Portal; no drafted spec is published without that save, and a drafted spec meets §2.3 like any other.

## 3. Alternatives

- **Custom JavaScript or HTML per dataset.** Any chart, and any script on the catalogue's origin. Rejected: the publisher's code would run next to the visitor's session.
- **Apache ECharts option objects.** Rich charts, but formatters are JavaScript functions and the options leak into code. Rejected.
- **Plotly JSON.** Declarative, weaker on linked interaction, and a heavier bundle. Rejected.
- **A CKAN extension per chart type.** Safe, not standard, and limited to the types someone wrote. Rejected.
- **Render on the server to SVG.** No script in the visitor's browser at all, and no interaction either: brushing and tooltips are half of why a complex chart is worth having. Kept in mind for a static export, not chosen.

## 4. Consequences

- The Endpoint kind gains `spec.catalog.visualizations` with its validation in `jc-core` and `jcctl validate`, and the reconciler publishes the views (EP-130, EP-132).
- The deployment adds the `viz` component: a static renderer page on `viz.{domain}`, with the headers of §2.5, its route and its certificate name (T-4641).
- The CKAN theme gains the `jc_visualization` view plugin, which embeds the frame and is hidden from the view-type list.
- A visualization shows nothing a visitor could not read with `curl` from the same Endpoint. The risks left are a bug in the interpreter, which the sandbox and the CSP contain, and a heavy spec, which the limits of §2.6 bound.

## Related

- [Requirements/endpoints.md](../Requirements/endpoints.md) — EP-130, EP-131 and EP-132 state this decision as requirements.
- [Architecture/04 §3a](../Architecture/04-context-spaces-and-endpoints.md#visualizations-ep-130ep-132) — the manifest member and a complete example.
- [Architecture/04 §7](../Architecture/04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) — what an Endpoint becomes in CKAN.
- [ADR-N-052](adr-n-052-anonymous-oauth-public-mcp.md) — the `api.{domain}` host the renderer reads from.
