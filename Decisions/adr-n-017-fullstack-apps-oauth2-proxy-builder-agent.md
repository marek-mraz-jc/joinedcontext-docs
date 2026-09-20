---
sidebar_position: 18
title: "ADR-N-017: Full-Stack Apps behind oauth2-proxy, built by the Builder Agent"
---

# ADR-N-017: Full-Stack Apps behind oauth2-proxy, built by the Builder Agent

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

§3.2 (the oauth2-proxy sidecar) and the rejection of the `openid-connect` plugin are superseded by [ADR-N-019](adr-n-019-login-at-the-edge-apisix-openid-connect.md); the full-stack kind and the builder agent stand.

## 1. Context

Apps on Demand (ADR-N-009 lanes, [Architecture/16](../Architecture/16-apps-on-demand.md)) started as static React bundles served by the Portal. Two needs go beyond that:

1. Apps with server-side logic (aggregations, exports, scheduled work) need a backend, and the user wants the platform's own stack for it: Rust and React.
2. The user wants the whole build to run on the server without a person: an agent with coding tools and internet access writes, builds, tests, deploys and repairs the app, and a login in front of the app comes from Keycloak without the agent writing any authentication code.

Three login options were on the table: OIDC code in every generated app, the `openid-connect` plugin of APISIX per app route, or an oauth2-proxy sidecar per app.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | oauth2-proxy (MIT) does the OIDC login; generated apps carry no auth code. |
| Technological consistency | **Full** | App backend = Rust `axum`, UI = React, same as the Portal (ADR-N-001). |
| Security by design | **Full** | Sidecar is the only ingress; secrets reconciler-owned; builder workspace has no real-space token and egress only through a logged allow-list proxy. |
| Modular design | **Full** | An app image runs unchanged outside the platform with any Keycloak. |
| Multi-tenancy | **Full** | One OIDC client per app in the organization's realm; cookie scoped to the app path. |
| Open source as default | **Full** | oauth2-proxy MIT, OpenHands MIT. |

## 3. Decision

1. **`spec.kind: fullstack`** is the default app kind produced by `app-from-prompt`: one OCI image, Rust `axum` backend serving the embedded React build and the server-side logic (AP-25).
2. **oauth2-proxy sidecar** in every `service` and `fullstack` app pod is the only ingress; it is the confidential OIDC client `app-{name}` of the organization's Keycloak realm, forwards the user's access token to the app, and the app calls its endpoint with that token (AP-26…AP-29). APISIX routes `/apps/{name}/*` to the sidecar without its own `openid-connect` plugin.
3. **Builder profile of the Agent Runner** (ADR-N-014 addendum): coding tools in an ephemeral workspace, internet through the platform egress proxy with allow-list and logging, sandbox endpoint only, forge token scoped to `apps/{name}/` (AG-26…AG-28). It runs scaffold → implement → build/test → commit → CI → preview → smoke test → repair on its own; humans confirm `dataNeeds` and approve yellow/red publications (AP-30…AP-33).
4. **Rejected**: OIDC code inside each generated app (auth logic written by an agent, per app, is the worst place for it); APISIX `openid-connect` per app (would rewrite the shared `apisix.yaml` for each app login change and tie apps to the platform edge).

## 4. Consequences

### Positive

- Generated code is only application logic; login, sessions and logout are one standard component with one configuration per app.
- The app runs anywhere a Keycloak is reachable, which also gives the builder a way to test it in its workspace before CI.
- From prompt to tested preview no person is needed; the two human touch points are the grant (`dataNeeds`) and the lane approval.

### Negative / Trade-offs

- One more container per app pod (oauth2-proxy, about 30 MB RAM).
- A builder with internet access is a bigger attack surface than a steward; the egress proxy allow-list, workspace destruction and sandbox-only tokens are the compensating controls and must be tested (Testing/06).
- Rust compile times make the build loop slower than a static Vite app; the workspace keeps a warm `cargo` cache per organization to soften it.

## 5. See Also

- Architecture: [16-apps-on-demand §4, §5](../Architecture/16-apps-on-demand.md).
- Requirements: [AP-25…AP-33](../Requirements/apps.md), [AG-26…AG-28](../Requirements/agents.md).
- Decisions: [ADR-N-014](adr-n-014-agent-runner-openhands-optional.md), [ADR-N-009](adr-n-009-mcp-surfaces-and-agent-lanes.md), [ADR-N-007](adr-n-007-apisix-standalone-no-etcd.md).

## Related

- [16-apps-on-demand](../Architecture/16-apps-on-demand.md) — referenced above.
- [ADR-N-014](adr-n-014-agent-runner-openhands-optional.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
