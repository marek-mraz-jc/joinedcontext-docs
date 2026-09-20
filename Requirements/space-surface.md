---
sidebar_position: 17
title: "Space Surface (SP)"
---

# Context-Space Surface, URL Scheme, Representations, MCP

Status: Draft
Date: 2026-08-23
Scope: The public surface of one context space (tenant/dataset space):
its URL scheme, the representations exposed under it (NGSI-LD API, MCP,
WebSocket, schema artifacts, RDF dumps, DCAT record), tenancy without a
client-facing tenant header, and the per-space MCP instance model.
Decision rationale and rejected variants: ADR 013.
Related: ADR 001 (URN), ADR 007 (@context discovery), ADR 010 (LOD),
ADR 011 (MQTT), `access-control.md` (R1–R43), `gateway-firewall.md`
(GW20/GW23/GW25), `city-as-code.md` (CC-01…),
`../specs/websocket-binding.md` (WS-01, WS-05).

Keywords MUST / SHOULD / MAY per RFC 2119. This document is canonical
for the **SP-01…SP-21** family.

## 1. URL scheme

- **SP-01** — Every context space MUST be exposed under one stable base
  URL on the platform host: `https://{host}/cs/{space}`. `{space}` MUST
  be the evidencia code from the organisation's data dictionary
  (ADR 001); no second identifier scheme for spaces may be minted.
- **SP-02** — URL ↔ URN MUST be a pure function: the entity
  `urn:ngsi-ld:{Typ}:{Razidlo}:{Evidencia}:{Meno}` resolves at
  `/cs/{Evidencia}/ngsi-ld/v1/entities/{urn}`, and the ADR 001 resolver
  (`https://id.…/{urn}`) is a string rewrite onto this scheme, no
  lookup table.
- **SP-03** — Standard trees MUST appear intact under the space prefix:
  `/cs/{space}/ngsi-ld/v1/…` is byte-for-byte the CIM 009 resource tree
  (a stock NGSI-LD client pointed at the space base works unmodified,
  R15); `/cs/{space}/mcp` is a standard MCP Streamable HTTP endpoint;
  the WebSocket binding lives at `/cs/{space}/ngsi-ld/v1/ws` (the WS-01
  path under the prefix; `/cs/{space}/ws` MAY exist as a redirect).
- **SP-04** — The only child paths of a space are: `ngsi-ld/v1/`,
  `mcp`, `schema/`, `dump/`, and (private spaces)
  `.well-known/oauth-protected-resource`. No other invented segments;
  in particular there is no `endpoint/` intermediary and no
  per-representation ad-hoc naming.
  > Note: the gateway routes `ngsi-ld/v1/` and `mcp` today
  > (`context-gateway` `src/app.rs`). `schema/`, `dump/` and the protected-resource
  > document are the permitted set this requirement fixes, not a set that answers:
  > the schema artifacts are served on the Endpoint (EP-46…EP-52) and the dated dumps
  > (SP-13) are not built. The space record advertises what is routed and grows with it
  > (`handlers/space_surface.rs::children`, T-2379), so a discovery document never names
  > a path that answers 404.

## 2. Tenancy without a client-facing tenant header

- **SP-05** — The public API contract MUST NOT contain the
  `NGSILD-Tenant` header. Clients never send it, documentation and
  generated configs never mention it (restates GW20 for this surface).
- **SP-06** — The gateway MUST derive the tenant: from the `/cs/{space}`
  path segment for anonymous/public access, from the token claim for
  authenticated access. A path/token tenant mismatch MUST return the
  same 404 as a nonexistent space (no existence disclosure, R20).
- **SP-07** — The gateway MUST strip any inbound `NGSILD-Tenant`
  header, strip the `/cs/{space}` prefix, and inject `NGSILD-Tenant:
  {space}` on the internal hop only; the broker's internal listener is
  the only place the header is honoured (GW25).
- **SP-08** — The broker MUST stay path-unaware and vanilla (CC-01):
  space selection reaches it exclusively as the standard CIM 009 tenant
  header on the internal hop; the Antares RLS tenant pin (GW23) remains
  the second enforcement layer unchanged.
- **SP-09** — Spec machinery that carries tenancy internally is kept,
  not removed: the CSR `tenant` member (clause 4.14/4.3.6.5) in
  federation, and the WS-05 handshake tenant (gateway-injected). Both
  are invisible to external clients.

## 3. Space root and discovery

- **SP-10** — `GET /cs/{space}` MUST return a DCAT-AP dataset record,
  content-negotiated (HTML for humans; JSON-LD/Turtle for machines),
  whose distributions are exactly the space's children: the NGSI-LD
  API and MCP as `dcat:DataService`, dumps as downloadable
  distributions, and the ADR 011 MQTT topic namespace as an access
  service. One URL hands a human, a program, or an agent its entry
  point (MIM0/ADR 010 alignment).
- **SP-11** — `GET /cs` MUST return the catalog of spaces, narrowed to
  the caller's grants through the same policy layer: anonymous callers
  see public spaces only; the catalog never lists a space the caller
  cannot at least discover.
- **SP-12** — Format handling: each artifact has one canonical
  content-negotiated resource; extension-suffixed URLs
  (`model.linkml.yaml`, `latest.nq.gz`, …) MUST exist as direct-download
  aliases of the same resource, never as divergent copies.
- **SP-13** — Versioning: `schema/context.jsonld` and model artifacts
  MUST have stable versioned URLs (e.g. `schema/v3/context.jsonld`)
  with `latest` as a redirect, a subscription's `jsonldContext` must
  not change meaning under a live consumer. Dumps are dated and
  immutable; `dump/latest.*` is a pointer.

## 4. Per-space MCP instances

- **SP-14** — One MCP service serves all spaces; `/cs/{space}/mcp` is a
  per-space instance. The space is determined by the path (and, for
  authenticated callers, confirmed by the token per SP-06), never by a
  tool argument. A client on one instance physically cannot reach
  another space.
- **SP-15** — The tool surface MUST be rendered from the caller's
  effective permissions (R16, AuthZEN shape per R51): a generic tool
  set (`query_entities`, `get_entity`, `describe_schema`; temporal,
  write, and subscription tools only when the corresponding operations
  are granted). Per-space hand-written tool configurations are
  forbidden, a space's MCP surface is a projection of grants, not an
  artifact.
- **SP-16** — The MCP server is a façade: it forwards the caller's own
  token through the gateway and holds no privileged identity and no
  authorization logic of its own (same posture as CC-43). Enforcement
  and discovery therefore derive from the same `Policy` entities and
  cannot drift.
- **SP-17** — Public spaces admit anonymous MCP callers under the
  `public` role grant (GW22). Private spaces answer unauthenticated
  requests with 401 + RFC 9728 protected-resource metadata. Gateway
  denials surface as structured tool errors so an agent can distinguish
  "denied" from "empty" (MIM0-R8).
- **SP-18** — A public catalog instance (`/cs/catalog/mcp` or the `/cs`
  root's MCP) MUST offer space discovery (`search_datasets` → names +
  base URLs), narrowed per SP-11.
- **SP-19** — Grant changes MUST reach live MCP sessions within the
  bounded propagation time of R48: with stateless Streamable HTTP the
  next `tools/list` reflects them; long-lived sessions receive
  `notifications/tools/list_changed`.
- **SP-20** — Isolation seams (the WS-47 list transplanted): tenant
  from token/path only, tool arguments are data never selectors; all
  MCP-layer caches tenant-keyed; cross-space probes byte-identical to
  not-found; per-tenant rate limits on the same identity.

## 5. Provisioning

- **SP-21** — Gateway routes, DCAT records, schema artifacts, and MCP
  registry entries for a space MUST be rendered from the space's
  manifest in the city repository (the CC plane): adding space #1001 is
  a manifest merge, never a hand-written route, and the rendered
  `apisix.yaml` (standalone file mode) is the only gateway
  configuration surface.
- **SP-22** — The gateway MUST count every request to `/cs/{space}/…`
  against a token bucket per caller — the presented credential, or the
  client address when there is none — and MUST advertise it with the
  standard `RateLimit-*` fields, the same way it counts a published
  Endpoint (EP-20, MIM0-R7). A space declares no limit of its own, so
  the gateway's default applies (600 requests per minute, burst 50).
  The edge's bucket is not a substitute: it is one bucket for every
  anonymous caller of every space, so one client can spend the
  canonical surface for everybody.

## 6. Standardization statement

- **Spec-native**: the CIM 009 tree, tenant header (internal hop), CSR
  `tenant` member, WS-01/WS-05; DCAT-AP for the space record; RFC 9728
  for protected-resource metadata; MCP Streamable HTTP.
- **Profiled extensions (documented, additive)**: the `/cs/{space}`
  prefix and its fixed child set (SP-04), the grant-rendered MCP tool
  surface (SP-15), the catalog instance (SP-18).
- **Deliberately non-standard**: none, the broker and all clients see
  only standard interfaces; every invention lives in the gateway and
  the MCP façade.

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| SP-01–SP-04 | [Architecture/04-context-spaces-and-endpoints.md#1-context-space-canonical-surface-sp-01sp-04](../Architecture/04-context-spaces-and-endpoints.md#1-context-space-canonical-surface-sp-01sp-04) | [Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway](../Testing/01-backend-tests.md#1-property-based-testing-in-context-gateway) |
| SP-05–SP-09 | [Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09](../Architecture/04-context-spaces-and-endpoints.md#2-tenancy-without-client-headers-sp-05sp-09) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |
| SP-10–SP-13 | [Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model](../Architecture/04-context-spaces-and-endpoints.md#3-the-endpoint-model) | [Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance](../Testing/02-conformance-tests.md#1-etsi-gs-cim-009-ngsi-ld-conformance) |
| SP-14–SP-20 | [Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces](../Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces) | [Testing/06-security-tests.md#4-mcp-authorization--isolation-testing](../Testing/06-security-tests.md#4-mcp-authorization--isolation-testing) |
| SP-21 | [Architecture/06-configuration-as-code.md#3-the-reconciler-engine](../Architecture/06-configuration-as-code.md#3-the-reconciler-engine) | [Testing/04-configuration-and-pipeline-tests.md#3-pull-request-plan--reconciler-idempotency](../Testing/04-configuration-and-pipeline-tests.md#3-pull-request-plan--reconciler-idempotency) |
| SP-22 | [Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48](../Architecture/05-context-gateway.md#3-cache-architecture--revocation-propagation-r40-r48) | [Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite](../Testing/06-security-tests.md#2-policy-bypass--privilege-escalation-regression-suite) |

## Related

- [00-index](00-index.md) — all requirement families.
- [traceability](traceability.md) — requirement to chapter and test mapping.
