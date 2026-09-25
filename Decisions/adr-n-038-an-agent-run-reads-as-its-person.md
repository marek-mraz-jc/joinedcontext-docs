---
sidebar_position: 39
title: "ADR-N-038: An Agent Run Reads as the Person Who Started It"
---

# ADR-N-038: An Agent Run Reads as the Person Who Started It

Date: 2026-09-25  
Status: Accepted  
Decision Makers: product owner (decision of 2026-09-24, T-1563)

## 1. Context

AG-01 asks every agent to act under an individual, auditable identity, "a Keycloak service account or an end-user delegated session via OAuth 2.1 Token Exchange (RFC 8693)", and never a shared bot account.

What a run presents to the Context Gateway today is one shared identity. `jc-agent-proxy` mints a `client_credentials` token of its own Keycloak client for every run and caches it by endpoint slug (`crates/agent-proxy/src/inject.rs`). Two runs of two people against one endpoint send the same token. The gateway maps that token's `azp` to the proxy's `ServiceAccount` (PF-46), whose role is `public`. So a run reads what an anonymous caller reads: its person's grants never reach the gateway, and the gateway's decision log cannot say whose run read what. The proxy's own log names the run (AG-42), and nothing else does.

The owner chose the delegated session: a run acts as the person who started it, by Keycloak's standard token exchange (V2), audience-bound to the endpoint. An unattended run holds a refresh grant for its own duration and no longer.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | RFC 8693 token exchange as Keycloak 26 ships it (standard token exchange V2, internal to internal), and RFC 7009 revocation. No token is minted by our code. |
| Security by design | **Full** | The run's reads are decided by the person's own grants and Policy. No run can read more than its person, and the gateway accepts a delegated token only from a client whose manifest declares it. |
| Least privilege | **Full** | The proxy's own account keeps its `public` role for what it does alone. A delegated token carries the person's rights only while the run lives, and the run's profile still narrows which endpoints it may address (AG-70, AP-44). |
| Operability | **Partial** | A run's data access ends with its person's Keycloak session, so an unattended run is bounded by the realm's session lifespan. A proxy restart loses the grants in memory, and the runs it held must be started again. |

## 3. Decision

1. **The person's token reaches the proxy once, at the start.** When the Portal starts a run for a person with a session, or a conversation's first turn, it hands the person's current access token to `jc-agent-proxy` on the proxy's internal route `POST /internal/runs/{run}/identity`. That route answers the Portal's own service token alone (AG-52). The Portal keeps no copy, and the token is never logged or written to the run record.
2. **The proxy exchanges it at once.** The proxy's confidential client calls the realm's token endpoint with `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`, the person's token as `subject_token` (`subject_token_type` access token) and `requested_token_type` refresh token. Keycloak answers an access token and a refresh token of the proxy's client whose subject is the person (standard token exchange V2, "same session" refresh). The realm enables the exchange on the proxy's client alone, and the edge client's tokens carry the proxy's client in their audience, which V2 requires of a subject token. V2 takes only client IDs as `audience`, and an endpoint's slug is a custom audience rather than a client, so the exchanged token's audience is the gateway's (`context-gateway`, the audience a person's own session already carries, Architecture/12 §4). The binding to endpoints is the run's own list of slugs, which the proxy enforces (AP-44), with each endpoint's Policy deciding the call. This is narrower than the owner's "audience-bound to the endpoint" can be with V2, and it is noted for the owner on T-1563.
3. **Every data call of the run uses the run's own token.** `/v1/data/…` and `/v1/data/mcp` send the run's delegated access token, refreshed from its refresh token, where they sent the shared `client_credentials` token. The cache is keyed by run, never by slug. A run without a delegated grant (no session started it, or the exchange was refused) reads nothing through the proxy and answers `401` with the reason, rather than falling back to the shared token.
4. **The gateway reads a delegated token as the person.** A token whose `azp` names a `ServiceAccount` that declares `spec.delegation: token-exchange`, and whose subject is a person rather than that client's own service-account user, is evaluated as the person: their `preferred_username`, their groups and their roles, as if they had called. The account's own roles do not apply to it. The decision log records the person and, beside them, the account the call came through. A person-subject token from a client whose account declares no delegation is `403`, as today.
5. **The grant lives as long as the run.** The refresh token is held in the proxy's memory, never on disk and never in the Portal. When the run ends (terminal state, cancel, lease expiry or the reaper) the proxy revokes it (RFC 7009) and drops it. Because it is a same-session grant, it also ends when the person signs out or their session expires, and the run's next read answers `401`. An unattended run therefore works for as long as its person's session lasts, and no longer (AG-69).
6. **Everything else stays.** The forge route keeps its per-request token and its `Co-Proposed-By` trailer (AG-17, AG-18). The registry route `/v1/mcp` keeps the Portal running each call as the person, narrowed by the profile (AG-70). The proxy's own client keeps its `client_credentials` token for its calls to the Portal's internal listener (AG-52).

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| An identity per run or per agent profile: a Keycloak client the reconciler mints for each | Realm churn and a cleanup duty for every run, and the client still has no person's rights, so the run would need grants of its own: a second authorization model beside the person's. |
| The Portal stores the person's refresh token and hands out access tokens | The Portal would hold a long-lived credential for every person with a run. Keycloak's same-session exchange gives the proxy the same thing for the run alone. |
| Keep the shared client and attribute from the proxy log | The gateway would still decide on the proxy's public role, so a run could never read a private endpoint its person may read, and the decision log would still not name the person. |
| Offline tokens (`offline_access`) for unattended runs | They survive the person's sign-out, so a run would outlive the session that authorised it. The owner asked for a grant held for the run's duration only. |

## 5. Consequences

- **Deployment (Keycloak):** the proxy's client gets `standard.token.exchange.enabled` and same-session refresh in exchange. The edge client (and the Portal's own client) gets an audience mapper naming the proxy's client, so the person's token is a valid subject token for it. No other client gets the exchange.
- **Portal:** hands the starting person's token to the proxy when a run starts, and never stores it.
- **Proxy:** one exchange per run, a per-run token cache with refresh, revocation when the run ends, and no fallback to the shared token.
- **Gateway and `jc-core`:** `ServiceAccount.spec.delegation` (`token-exchange`, absent by default), and the delegated subject rule of decision 4 in `subject_of`.
- **Requirements:** AG-01 names this path, AG-94 covers the proxy's grant and AG-95 the gateway's rule.

## Related

- [ADR-N-009](adr-n-009-mcp-surfaces-and-agent-lanes.md) — the MCP surfaces and agent lanes, whose identity line this completes.
- [Architecture/19-agent-runner.md](../Architecture/19-agent-runner.md) — §4, the proxy surface; §7, attribution.
- [Architecture/12-identity-and-access.md](../Architecture/12-identity-and-access.md) — tokens, audiences and `azp` (PF-45, PF-46).
- [Requirements/agents.md](../Requirements/agents.md) — AG-01, AG-94, AG-95.
