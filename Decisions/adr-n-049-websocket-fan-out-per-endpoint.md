---
sidebar_position: 50
title: "ADR-N-049: WebSocket Fan-out per Endpoint, Filters Matched in the Gateway"
---

# ADR-N-049: WebSocket Fan-out per Endpoint, Filters Matched in the Gateway

Date: 2026-10-12  
Status: Accepted  
Amended: 2026-10-22 (T-5182): the table is read at the first filter, not at the upstream's start (§8)  
Decision Makers: product owner (order of 2026-10-12T23:05Z, T-4133: "one subscription that would already carry the data notification ... a filter between WebSocket and the live entities that live in the endpoint, not from Postgres ... 1,000 custom WebSocket filters in that endpoint"); the shape below was decided by worker-6, owner may override

## 1. Context

An Endpoint that serves `websocket` answers `{endpointUrl}/ws` (EP-106, [API/07](../API/07-websocket.md)). Before this decision, the gateway relayed each client connection to the broker view's `/x/views/{view}/ws` (Antares ADR-0026). Each `x-subscribe` became a broker Subscription of its own, stored under the caller, and the broker matched every change against every Subscription of the tenant. The broker then ran `pre_notify` under the stored caller for each delivery.

That shape fails the owner's case in three ways:

- **Cost per change grows with the number of sockets.** 1,000 sockets with one filter each means 1,000 stored Subscriptions. Every change on the Endpoint's types is matched against all of them, and every match is a policy decision and a rendered message inside the broker.
- **Two hops per socket.** Each client connection holds one gateway-to-broker connection beside it, so one client is two sockets, two queues and two lifetimes. A drop on the inner hop (T-4131) kills the client.
- **The Subscription store as a session table.** A socket's Subscriptions are written to the broker's store and deleted 30 s after a close, so the store pays for connection churn.

What already exists and is reused:

| Piece | Where | What it gives |
|---|---|---|
| `antares-matcher` | Antares `crates/antares-matcher` | The broker's own CIM 009 5.8.6 predicates against one in-memory entity: `selector_match` (entities, `idPattern`), `conditions_match` (`q`, `scopeQ`, `geoQ` with linked-entity lookup), `is_active`, `throttled`, `geo_params`. It was written so that "a gateway or an edge component can answer 'would this change notify subscription X' with the broker's own semantics". |
| `antares-ql`, `antares-jsonld` | already gateway dependencies | Parse `q`, expand an entity to the stored form. |
| `pdp::grants::shown` | `context-gateway/src/pdp/grants.rs` | One entity judged against each of the caller's grants (types, id patterns, `q`, `scopeQ`, area). The answer is the union of the attribute lists of the grants that match it, or nothing (T-3530). |
| Endpoint caller roles | joinedcontext-policy README §1 | `endpoint:{project}/{name}`, set by the gateway only, stripped from every client request. |

## 2. Decision

The gateway serves an Endpoint's WebSocket itself. It opens **one** broker subscription per Endpoint, keeps the Endpoint's live entities in memory, and matches the clients' filters there through an index. It cuts each delivery to the caller's own grant before the filter sees it.

1. **One upstream per Endpoint and gateway replica.** The gateway opens one WebSocket to the broker view `/x/views/{slug}/ws` the first time a client connects to an Endpoint's `/ws`. The upstream carries one `x-subscribe` for every entity type the view serves, in `format: normalized`. The view is the union of the types and attributes the Endpoint's permits grant, less its hidden attributes (EP-61, [ADR-N-042](adr-n-042-data-views.md)). The broker therefore sends each change once per Endpoint, already cut to that Endpoint ("only cars").
   - The upstream speaks as its caller, with the tenant and identity headers a REST read through the view carries (T-4755), and the gateway keeps one upstream per Endpoint and caller identity. The broker decides the socket's own Subscription as a read (Antares ADR-0026 rule 4), so the gateway's own account (`x-jc-client: context-gateway`, T-3767) creates no subscription: its permit carries no clause 5.8.1 and no view lists it (T-5339).
   - No client can speak as that account. The gateway sets `x-jc-*` only from a verified token and strips every client copy first (`tenancy::strip_client_headers`), and the account's Keycloak client is the gateway's own.
   - The upstream closes 60 s after the Endpoint's last client leaves.
   - It reconnects with `x-resume` when the broker ends it with `x-closing: lifetime`, and with backoff (1 s doubling to 30 s) on a drop.
   - An `x-gap`, or a resume that fails, reloads the snapshot (item 2), and every client of the Endpoint then receives `x-gap`.
   - Each replica holds its own upstream. N replicas need N upstreams per Endpoint and no shared bus.
2. **Live state in memory.** At the upstream's start the gateway reads the Endpoint's entities once, through the same view over REST, paged, and then keeps the latest entity per id from the notifications. Nothing per message reads Postgres or the broker.
   - The table is bounded by `JC_GATEWAY_WS_ENTITIES` (default 50,000 entities per Endpoint) and evicts the least recently changed entity first.
   - An evicted entity that changes again counts as new: a `watchedAttributes` filter fires once on it, and that is the only effect of the bound.
   - `/metrics` reports the table size per Endpoint and the evictions.
   - A deleted entity (the broker's deletion notification) leaves the table.
3. **Client filters compiled once.** An `x-subscribe` is validated as an NGSI-LD Subscription (TS 104 175 §5.2.12) and compiled once into the stored form `antares-matcher` reads. The compiled form covers:
   - `entities` (type, `id`, `idPattern`);
   - `q`, `scopeQ` and `geoQ`;
   - `watchedAttributes` and `notification.attributes`;
   - `throttling`, `expiresAt` and `isActive`.

   A filter that does not compile answers `x-result` with `x-status: 400` and the parser's ProblemDetails, the same answer REST would give. A filter is local to its connection and is no broker Subscription. Its id is `urn:ngsi-ld:Subscription:ws:{connection}:{n}`, and REST does not list it.
4. **Matching by index, not by loop.** Per Endpoint, the gateway indexes the compiled filters. Each change collects candidates from four indexes:
   - a **type map**, from type IRI to the filters that select the type and carry no indexed term below;
   - an **equality index**, from (attribute, canonical value) to filters, for a filter whose `q` is a conjunction with an `==` term (one term per filter is indexed);
   - **numeric bounds**, per attribute a sorted map of each range filter's interval, for a `q` conjunction with `<`, `<=`, `>` or `>=` on a number;
   - a **geo grid**, a fixed grid of cells (0.01°, about 1 km at 60° N) mapping each cell to the filters whose `geoQ` area touches it. A filter whose area touches more than 4,096 cells stays in the type map instead.

   Only the candidates run the full `antares-matcher` predicate, and a candidate's match is decided by the predicate, never by the index. A filter with `id`, an `idPattern` alone, or a `q` with no indexable term sits in the type map and is a candidate for every change of its types. The grid needs no new crate, since `antares-ql` already evaluates the geometry.
5. **Deltas against the previous state.** The table holds each entity's previous form, so `watchedAttributes` fires only when a watched attribute's value, or one of its sub-properties, differs from the previous one. A change that rewrites the same value sends nothing. An entity that enters a filter's `geoQ` or `q` matches. An entity that leaves sends nothing (API/07 §2: such a message would reveal a hidden change).
6. **Per-client delivery.** Each connection has a queue of at most 256 unread notifications, coalesced per entity: a newer change of an entity still queued replaces the older one in its place, so per-entity order holds. Throttling is per filter, as the broker applies it (`throttled`). A queue that stays full answers `x-gap`, then `x-closing: overflow`. `x-seq` counts per connection. `x-resume` within 30 s reaches the replica that held the connection and replays what that replica still holds. On another replica the resume fails with `x-status: 404`, and the client reads again over REST (API/07 §4).
7. **Security: each delivery is cut to the caller's own grant before any filter sees it.** The upstream reads the union of the Endpoint's grants, which is more than most callers may read. Every connection therefore holds its caller's grant views (`GrantView`, the same the REST path judges an answer with), re-resolved on every policy reload (R48). For each change, before any filter of that connection is consulted:
   1. `grants::shown` decides whether the caller may see the entity at all and which attributes. An entity no grant of the caller matches is invisible to every filter of that connection.
   2. The entity is projected to those attributes.
   3. The connection's candidate filters run on the projected entity, and the delta of item 5 compares projected forms.

   So a `q`, `geoQ` or `watchedAttributes` naming an attribute the caller cannot read evaluates as if the attribute were absent, and the timing of a notification cannot reveal a hidden value. This holds for public Endpoints and one-audience Endpoints alike, so there is no second mode. Per-client broker subscriptions are not kept.
8. **Limits.** The caps of API/07 §3 stay as they are: 10 connections per caller, 64 filters per connection, 64 KiB per message, 256 queued, and 1,000 connections per space. The space cap is now the gateway's alone, because the broker holds one connection per Endpoint and replica. The number of sockets one replica serves is measured by the rig (item 9) and written into [API/07](../API/07-websocket.md) §3 with the gateway's memory request.
9. **Validated by a rig, not by belief.** The platform repository gains the `ws-fanout` rig (`crates/context-gateway/tests/ws_fanout_rig.rs`, workflow `ws-fanout-rig`), run on a GitHub runner and never on the shared host. It runs the gateway in process against a stub broker, so it measures the fan-out and not the network:
   - **Change stream:** a recorded or generated Vehicle-like stream (type, id, speed, transportMode, location).
   - **Sockets:** N sockets with random filters drawn from the grammar of item 3.
   - **Ground truth:** computed offline from the same stream by running `antares-matcher` on every (filter, change) pair, the loop the index replaces.
   - **Assertion:** every socket receives exactly its expected notifications, with no miss, no extra, and per-entity order kept. A socket the gateway coalesced for (item 6) receives, per entity, a subsequence of them ending with the entity's last admitted state.
   - **Report:** p50 and p99 change-to-socket latency, CPU and memory at N = 100, 1,000 and 5,000.
   - **Live smoke:** 20 sockets on `dev`'s transport Endpoint, in the conformance repository. It is also the regression check for T-4131 and T-4132.

   Inside the gateway, a property test holds the index to the same loop: for random filters and changes, the candidate set filtered by the predicate equals the full scan.
10. **A refused upstream is an error for every client, never a silent `201`** (T-4133). When the broker answers the upstream's `x-subscribe` with a status that is not 2xx (dev, apply 67: `403 no policy grants this operation`, because the view's listing lacked the gateway's account), the hub turns refused:

    - every open connection of the Endpoint ends with close code 1011 and the reason "the context broker refuses this Endpoint's fan-out", with no `x-closing` (no new `x-reason`);
    - every later `x-subscribe` or `x-update` is answered `x-status: 503` with the platform's `service-unavailable` ProblemDetails, whose `detail` names the broker's status and detail;
    - the upstream retries after 30 s, and the first accepted `x-subscribe` clears the state.

    A connection that subscribed before the broker answered may have received `201`; the 1011 close follows it. The upstream speaks as its caller (item 1), so a caller the view's listed policies do not grant sees this refusal, and the gateway logs it; it is never a quiet socket.

## 3. Security Analysis

| Threat | Control |
|---|---|
| A caller receives an entity or attribute its grant does not read | Item 7: `grants::shown` and projection run per connection before the filter; the test subscribes a caller without the grant with a filter on a hidden attribute and asserts that nothing arrives, and asserts that a caller with a narrower grant gets the narrower projection. |
| A filter on a hidden attribute leaks it by timing | Filters run on the projected entity, so the hidden attribute is absent for them (item 7.3). |
| A client speaks as the gateway's account | The gateway strips `x-jc-*` from every client request and sets `x-jc-client: context-gateway` only on its own hops; the broker is reachable from the gateway and the Portal only (NetworkPolicy). |
| The upstream's wide read leaks through a bug in matching | The upstream reads through the Endpoint's view, so it holds at most what the Endpoint already serves to some caller; the cut per caller is the same code REST answers with. A view's temporal window (T-3632) narrows the bound permits, not the gateway's account: a live change is newer than any window's start, and a snapshot read at the upstream's start goes through the window like a REST read. |
| A revoked grant keeps streaming | Grant views are re-resolved on every policy reload (R48), so a revoked grant stops the next delivery, and the caller's connection still ends at its token's lifetime (API/07 §1). |
| A token in a URL | Unchanged: refused with `400` (EP-107). |
| Memory exhaustion by many filters or entities | The caps of item 8, the entity bound of item 2 and the 4,096-cell geo ceiling bound the memory per Endpoint. |

## 4. Alternatives Considered

| Alternative | Why not |
|---|---|
| Keep one broker Subscription per socket (ADR-0026 relay) | Cost per change grows with sockets inside the broker, and every client holds two sockets; it is what fails today. |
| One upstream per distinct grant instead of per Endpoint | The same per-caller cut (item 7) is needed anyway for areas and `q` grants; one upstream with a cut per caller is one code path. |
| Filters matched by a loop over all filters | 1,000 predicates per change at 20 changes/s is 20,000 evaluations/s per Endpoint, each with a JSON-LD expansion; the index reduces that to the candidates. |
| A shared bus (NATS) between gateway replicas | Not needed: each replica holds its own upstream; the broker sends a change once per replica. |
| An R-tree crate for the geo index | A fixed grid is enough for the "near the city centre" filters the owner names and needs no dependency; an R-tree is the upgrade when the rig shows grid misses dominate. |
| Reading Postgres for the previous state | The owner's order rules it out, and it costs one read per change. |

## 5. Consequences

- **The gateway** owns the WebSocket session: the upstream per Endpoint, the entity table, the filter index, the per-connection queues, `x-seq`, and `x-resume` (T-4133). The ADR-0026 relay code in `handlers/ws.rs` goes away.
- **The reconciler** grants the gateway's own account nothing for the fan-out: no clause 5.8.1 and no listing on a view (T-5339, after T-4755).
- **The broker** is unchanged: it serves one view socket per Endpoint and replica with ADR-0026 as it stands.
- **[API/07](../API/07-websocket.md)**: a socket's Subscriptions are no longer listed over REST, a resume holds within one replica, and the measured sockets per replica go into §3.
- **The platform repository** gains the `ws-fanout` rig and **the conformance repository** the 20-socket dev smoke (EP-115).

## 6. Requirements

Landed with this decision:

- `Requirements/endpoints.md`: **EP-106** reworded; **EP-114**, **EP-115**.

## 7. Amendment: the Upstream Speaks as the Caller (T-4755, 2026-10-19)

The broker view and its policy engine decide context data (ADR-N-050 decision 1), and item 7 kept a second decision in the gateway: `grants::shown` cut each delivery from an upstream that read the union of the Endpoint's grants. That cut did not see what a Policy narrows beyond types and attributes as the broker compiles it, and it was one more filter to keep equal to the broker's. T-4755 removes it:

1. **One upstream per Endpoint and caller identity.** The hub is keyed by the Endpoint and the verified identity the gateway pins on a REST request (`tenancy::pin_caller`: subject, client, roles, audience). Its upstream carries those headers, so the broker's view and policy engine decide it as they decide the same caller's REST read, and `pre_notify` cuts every notification under that caller (Antares ADR-0026 rule 8). Every anonymous caller of a public Endpoint shares one upstream, and so does every connection of one signed-in caller.
2. **Watching is a read.** The broker decides a Subscription whose endpoint is the socket making it as Query Entities (Antares ADR-0026 rule 4, amended by T-4755), so a Policy that grants `queryEntity` lets its caller watch over WebSocket without a Create Subscription grant. The gateway's account no longer opens any upstream.
3. **Item 7 is withdrawn.** The gateway keeps the client's filters, the index, the deltas and the queues of items 3 to 6, and matches them on what the broker already cut. It holds no grant view per connection. A grant revoked by a policy reload stops the next notification at the broker.
4. **Item 10 holds per upstream.** A refusal now names the caller's own Policy: a caller who may not read the Endpoint's types gets the 1011 close, and other callers of the same Endpoint keep streaming.

Decided (worker-4, owner may override): one upstream per Endpoint and identity, because one decision point (ADR-N-050) leaves no second filter to drift and the shared anonymous upstream keeps the owner's case of 1,000 public sockets on one broker connection. Options: per identity (chosen); per Endpoint under the gateway's account with the gateway's own cut (item 7 as written); one broker Subscription per socket (the ADR-0026 relay).

## 8. Amendment: the Table Is Read at the First Filter (T-5182, 2026-10-22)

Item 2 read the view into the table when the upstream started. On dev a sweep that opened and closed `/ws` on every Endpoint, with no `x-subscribe`, started one upstream per Endpoint, and each held its whole view for the 60 s linger. The gateway reached 1.3 GiB and was OOMKilled 14 times in 80 minutes. The table serves only the deltas of item 5, and nothing reads it while no filter exists, so:

1. **No filter, no table.** A hub reads the view at its first filter, then again after a gap or a failed resume. A hub with connections but no filter keeps no entity, and a notification it receives then is dropped.
2. **The table leaves with the last filter.** When the last filter of a hub goes (`x-unsubscribe`, a close, a reload), the table is dropped, and the next filter reads it again.
3. **Two reads at a time.** At most two hubs of a replica read their views at once; the others wait their turn, so a sweep that subscribes on many Endpoints holds at most two pages in flight.

A filter's first change on an entity the read has not reached yet counts as new, as an evicted entity does (item 2). The bound `JC_GATEWAY_WS_ENTITIES` is unchanged.

Decided (worker-t5182, owner may override): read at the first filter, because the probe and the anonymous sweeps open sockets without filters, and a measured sweep over 20 Endpoints of 3,000 entities fell from 843 MiB to 5 MiB held. Options: lazy read (chosen); one shared, capped table across hubs (it still holds every Endpoint a sweep touches); a smaller `JC_GATEWAY_WS_ENTITIES` (it cuts real subscribers' deltas and leaves the sweep's cost per Endpoint).

## Related

- [API/07-websocket.md](../API/07-websocket.md): the client's view of the WebSocket.
- [Architecture/05-context-gateway.md](../Architecture/05-context-gateway.md): §6 notification egress, the per-subscription delivery path for HTTP subscribers.
- [ADR-N-042](adr-n-042-data-views.md): the broker view an Endpoint is served from.
- [Requirements/endpoints.md](../Requirements/endpoints.md): EP-106, EP-107, EP-114, EP-115.
