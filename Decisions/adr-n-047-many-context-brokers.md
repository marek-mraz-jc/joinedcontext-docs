---
sidebar_position: 48
title: "ADR-N-047: Many Context Brokers, One Space on One Broker"
---

# ADR-N-047: Many Context Brokers, One Space on One Broker

Date: 2026-10-12  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-11, T-3841: "in the future there can be many more context brokers in the platform, so the design must account for that"); the shape below was decided by the supervisor and written by worker-7, owner may override

## 1. Context

Today the platform runs one Antares broker, and every component that talks to it reads one address from its own configuration. A search of `main` on 2026-10-12 (`git grep -niE 'broker_url|antares[-_.]?(url|host|svc|base)'` over the Rust sources and the Helm values; the code graph was not built in that clone, and a configuration key is a string, which a text search finds as well) gives every place:

| Where | What reads the one broker | Line |
|---|---|---|
| Context gateway | `JC_GATEWAY_BROKER_URL`, required; "the gateway forwards to exactly one upstream, chosen before the first request arrives" | platform `crates/context-gateway/src/config.rs:6`, `:125`; `crates/context-gateway/src/main.rs:16`, `:19` |
| Portal configuration | `JC_PORTAL_BROKER_URL`, optional, for registrations, the space usage counter and the view writer | portal `src/config.rs:120`, `:1287` |
| Portal view writer | `ViewSync::new(broker, token_file)`, one broker for every space's views (T-3802) | portal `src/reconciler/views.rs:1251`, `src/state.rs:782`, `:797` |
| Portal space usage | `space_usage::Counter::new(config.broker_url)` counts every space on that broker | portal `src/space_usage.rs:51`, `src/state.rs:156` |
| Deployment | both variables point at the one Service `context-broker.{namespace}.svc` | deployment `components/context-gateway/values/gateway/base-values.yaml.gotmpl:70`, `components/portal/values/portal/base-values.yaml.gotmpl:319` |
| Broker size | requests 100m CPU and 128 Mi, limit 1 CPU (development); requests 200m and 256 Mi, limits 2 CPU and 1 Gi (production) | deployment `components/context-broker/values/broker/development-values.yaml.gotmpl:12`, `production-values.yaml.gotmpl:16` |

Nothing above keys the broker by space. The gateway already resolves a space for every request (Architecture/05, stage 2) and pins the tenant from it (stage 3); the broker address is the one input it still takes from the environment. The MCP hub (ADR-N-025) and the named servers (ADR-N-043) call the gateway, so they inherit the same single upstream.

## 2. Decision

### 2.1 Kind `ContextBroker`

An organization-scoped kind names each broker instance, one file per broker at `brokers/{name}.yaml` of the organization repository:

```yaml excerpt
apiVersion: joinedcontext.com/v1alpha1
kind: ContextBroker
metadata:
  name: main
spec:
  default: true            # exactly one per organization
  image: ghcr.io/…/antares@sha256:…
  size: small              # small | medium | large, a resource preset of the chart
  storageClass: local-path
  features: [temporal, ogc, odata, mcp, csr]
status:
  version: 0.14.2
  phase: Live
  spaces: 7
```

- `image` is pinned by digest, like every image of the platform. `size` picks a preset rather than raw resources, so a manifest cannot ask the node for more than an operator sized.
- `features` switches surfaces of that instance on; an Endpoint whose representation needs a feature its space's broker lacks is refused at admission, naming the broker.
- Exactly one broker carries `default: true`. An organization without a `ContextBroker` manifest has the implicit `main`, which is today's deployment, so no repository written before this decision changes.

### 2.2 A space lives on one broker

`ContextSpace.spec.brokerRef` names the broker; absent means the organization's default. A space never spans two brokers. Its entities keep their identity (space, URN) of ADR-N-041: a URN says nothing about the broker, and nothing derives a broker from it.

### 2.3 Routing by space, never by configuration

Every component resolves the broker from the space it already resolved:

- The gateway keeps a map from space to broker address, built from the `ContextBroker` manifests and the spaces' `brokerRef` in the same cache as the Endpoints. `JC_GATEWAY_BROKER_URL` stays only as the address of the implicit `main`.
- The Portal's view writer, space usage counter and registrations look the broker up per space in the mirror; `JC_PORTAL_BROKER_URL` becomes the implicit `main`'s address, the same way.
- APISIX routes nothing to a broker directly: every data path goes through the gateway, so the edge does not change.
- The MCP hub lists the Endpoints of every broker the caller may reach, each labelled with its broker (`broker` in each `list_endpoints` entry and in `GET /api/endpoints`); a call runs as that Endpoint's own call, on that Endpoint's broker (ADR-N-025 §2, ADR-N-043).

After the build, no caller reads a single broker address. The check is a code-graph query in the build task (T-3842), its result pasted there.

### 2.4 Across brokers: federation, never a hidden fan-out

A space on broker 1 reads a space on broker 2 only through a registration (Antares CSR, T-3520, T-3700). Broker 2 decides with its own Policy and the caller's own token, forwarded only to broker 2's audience. The gateway never merges two brokers' answers on its own. A grant on a space is checked by the broker that holds the space.

How the caller's token reaches broker 2 (amended 2026-10-12, T-3999; decided by the supervisor, owner may override). The gateway keeps the caller's original token off every broker hop (K36). For a read over a space whose registrations ask for `identity: caller`, it exchanges that token (RFC 8693, Keycloak standard token exchange V2, as the gateway's own client, which alone holds the exchange permission) for one whose subject is the caller and whose only audiences are the clients of the brokers those members live on. It sends that token as `Authorization` on this one hop to broker 1, and the registration copies it to the member (`contextSourceInfo` `{"key": "Authorization", "value": "urn:ngsi-ld:request"}`), whose endpoint is the gateway's URL for the member space's Endpoint. Broker 2's gateway admits it on an Endpoint whose space lives on a broker the token names, and refuses a token naming only another broker (PF-114); that Endpoint's Policy then decides on the caller. An exchange that fails answers `502` or `503` with the problem type `federation-exchange-failed` and forwards nothing: there is no fallback to the caller's original token or to a service account. The exchanged token is never logged, and it never leaves the platform: a member registered by an outside address does not get it. The token only reads entities: a write, a conditional write and every subscription request carrying it are refused (`403`), because a subscription would outlive it; a write on the hub asks for no exchange at all. Its audience is per broker, not per Endpoint, so for its lifetime it reads as the person on every Endpoint whose space lives on a broker it names, with each Endpoint's Policy still deciding; a per-Endpoint audience would need one client per Endpoint.

### 2.5 Each broker is its own island

Each `ContextBroker` gets its own CNPG database and credentials (`secretRef`), its own Keycloak client and audience, its own NetworkPolicy and ServiceMonitor. Broker 1 cannot reach broker 2's database; no broker accepts a token minted for another broker's audience.

### 2.6 Upgrades and moves

- `just upgrade` (T-3794) takes a broker name and upgrades one instance at a time. A non-default broker goes first as the canary; the default follows when the canary's smoke is green.
- Moving a space to another broker is an explicit job, never a side effect of editing `brokerRef`: the space goes read-only (writes answer `503` with `Retry-After`), the job exports it, imports it on the target, compares the entity count and a hash over (URN, `modifiedAt`) read from both sides, switches `brokerRef`, and ends read-only. A mismatch leaves the space on the source broker, read-write, and the job failed with both counts. The job holds the space read-only by committing the annotation `joinedcontext.com/moving-to: {broker}` on its `ContextSpace` and removes it when it ends. While the annotation is set, the gateway answers every request that could write the space with `503`, problem type `space-moving` and `Retry-After: 30`, and lets reads through: `GET`, `HEAD`, and `POST` to `entityOperations/query`. An MCP call is answered `503` as well, because a `tools/call` may write.
- A `ContextBroker` that a space names cannot be deleted; the refusal lists the spaces.

### 2.7 Sizing

The dev node (`cpx42`, 16 GB) fits a second broker at the development preset (100m CPU and 128 Mi requested, its own CNPG instance of about 256 Mi). A third instance or the production preset needs a second node; the reconciler does not schedule a broker whose requests the node cannot meet, and says which.

## 3. Consequences

- The gateway and the Portal gain a per-space lookup where they read one variable today. The variables stay, as the implicit `main`, so a single-broker installation configures nothing new.
- The Brokers page in the Portal shows version, spaces, health and load per instance; a space's page names its broker.
- A cross-broker query is slower than a local one and says so: it is federation, with the registration visible in the space.
- Requirements PF-110…PF-116 carry this decision.

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| One broker per project | Too many instances for one node; projects with one small space would each pay for a database. |
| Shard one space over several brokers | Breaks (space, URN) as one owner's identity and every query that is not a key lookup. |
| The gateway fans out a query to every broker and merges | A hidden fan-out bypasses the owning broker's Policy and makes every answer as slow as the slowest broker. |
| Broker addresses in the gateway's environment, one variable per broker | A new broker would need a gateway redeploy; the manifests already reach the gateway's cache. |

## Related

- [ADR-N-025](adr-n-025-one-mcp-connector-several-endpoints.md) — the MCP hub that lists Endpoints across brokers.
- [ADR-N-041](adr-n-041-entity-identity-is-space-and-urn.md) — identity is (space, URN), never the broker.
- [ADR-N-043](adr-n-043-named-mcp-servers.md) — named servers call each member on its own broker.
- [Architecture/05](../Architecture/05-context-gateway.md) — the gateway's space resolution this routing extends.
- [Requirements: platform](../Requirements/platform.md) — PF-110…PF-116.
