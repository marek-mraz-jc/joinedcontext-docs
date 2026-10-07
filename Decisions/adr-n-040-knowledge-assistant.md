---
sidebar_position: 41
title: "ADR-N-040: One Knowledge Assistant Service on the Platform's Own Postgres, Proxy and Endpoints"
---

# ADR-N-040: One Knowledge Assistant Service on the Platform's Own Postgres, Proxy and Endpoints

Date: 2026-10-06  
Status: Accepted  
Decision Makers: product owner (order of 2026-10-06, T-3049)

## 1. Context

The owner ordered a private and public AI assistant: it answers from websites and PDFs the platform crawls, it can call public MCP connectors an administrator switches on, administrators manage it, and it can be placed in several spots: the Portal's internal chat, the data platform, the CKAN catalogue and a public iframe on any site. The whole service has to fit in 1 GB of memory with the language model outside it. It is written in Rust and stores what it knows in the platform's existing PostgreSQL.

The owner's research named a stack: `rmcp` 3.x for MCP (protocol 2026-07-28, Streamable HTTP), `rig` with `rig-rmcp` for the agent loop, `kreuzberg` v4 with pdfium for extraction, `spider` in HTTP mode with sitemaps for crawling, `fastembed-rs` with `multilingual-e5-small` int8 for embeddings (Slovak, Czech, Finnish, English), ParadeDB `pg_search` with `pgvector` and reciprocal rank fusion on CloudNativePG, and a sandbox for scripts. This ADR checks every claim against the registries and the platform's own image before adopting it, and puts the platform's existing parts ahead of new ones.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Postgres full-text search and the `pgvector` already in the cluster's image do retrieval; the Endpoint MCP surface is the connector; `jc-agent-proxy` carries every model call; `jc-functions` runs scripts. |
| Technological consistency | **Full** | Rust (axum, sqlx), React in the Portal for administration, manifests in the configuration repository, Keycloak for identity. |
| Security by design | **Full** | §3.7: every risk has a control and a task. No credential leaves the proxy; the crawler refuses private addresses; public channels read public sources only. |
| Modular design | **Full** | One binary with three roles (crawl worker, retrieval, chat API) behind module boundaries that can split into processes later. |
| Multi-tenancy | **Full** | Sources and deployments are manifests of one organization's repository; every row carries its organization and source. |

## 3. Decision

### 3.1 Verified versions (2026-10-06)

| Claim | Verified | Result |
|---|---|---|
| `rmcp` 3.x, MCP 2026-07-28, Streamable HTTP | crates.io `rmcp` 3.5.1 (Apache-2.0, 2026-10-05); `ProtocolVersion::LATEST = 2026-07-28`; features `transport-streamable-http-server`, `transport-streamable-http-client-reqwest` | **Adopted** |
| `rig` + `rig-rmcp` | `rig-core` 0.43.0, `rig-rmcp` 0.43.0 (MIT, 2026-09-30); MSRV 1.95.0 | **Adopted**, pre-1.0: pinned, upgraded by task |
| `kreuzberg` v4 with pdfium | `kreuzberg` 4.10.4 (MIT, 2026-09-21); features `pdf`, `bundled-pdfium`, `static-pdfium`, `chunking` | **Adopted** with `static-pdfium`, no runtime download |
| `spider` HTTP mode, sitemaps | `spider` 2.53.9 (MIT, 2026-09-05); features `sitemap`, `basic`; the `chrome*` features stay off | **Adopted** without a browser |
| `fastembed-rs` + `multilingual-e5-small` int8 | `fastembed` 7.1.0 (Apache-2.0, 2026-09-22) lists `MultilingualE5Small` only as the fp32 `onnx/model.onnx` (470.3 MB). The int8 file exists upstream (`intfloat/multilingual-e5-small`, `onnx/model_qint8_avx512_vnni.onnx`, 118.3 MB) and loads through `UserDefinedEmbeddingModel` | **Adopted with a correction**: the int8 model is a user-defined model with a pinned file hash, not a built-in one. 384 dimensions. `ort` has no stable release (fastembed depends on its release candidate) |
| ParadeDB `pg_search` on CloudNativePG | ParadeDB v0.26.0 (2026-10-03), **AGPL-3.0**. The cluster's image `ghcr.io/cloudnative-pg/postgis:16-3.6-system-trixie` (CNPG 1.30) carries `vector` 0.8.6 and no `pg_search` | **Not adopted** for the first version, §4 |
| `pgvector` | in the cluster's image already, extension 0.8.6; Rust crate `pgvector` 0.4.2 | **Adopted**, nothing to install |
| Script sandbox (Monty) | `monty` 1.1.0 (MIT, 2026-10-05) exists. The platform runs `jc-functions` (`rquickjs` 0.13, memory limit, interrupt handler, wall-clock timeout, tested) | **Not adopted**: `jc-functions` instead, §3.6 |

### 3.2 One service, `jc-assistant`

The crate is `crates/assistant` in `joinedcontext-platform`, binary `jc-assistant`, one Deployment with three roles in one process:

- **crawl worker**: claims jobs from the `jobs` table (`FOR UPDATE SKIP LOCKED`), fetches with `spider` (HTTP mode, sitemap first, robots.txt honoured), extracts with `kreuzberg` (HTML, PDF), chunks, embeds with `fastembed`, writes rows. One job at a time per replica.
- **retrieval**: hybrid search in one SQL statement, §3.3.
- **chat API**: axum, Server-Sent Events; the agent loop is `rig` with the model behind `jc-agent-proxy`, the tools are the retrieval function and the deployment's MCP connectors through `rig-rmcp`.

### 3.3 Retrieval on the Postgres the platform runs

A new database `assistant` on the existing CloudNativePG cluster, owned by role `assistant`. Lexical search is Postgres full-text search, a `tsvector` column per chunk with a GIN index. Postgres 16 ships Snowball stemmers for English and Finnish and none for Slovak or Czech, so those two use the `simple` configuration with `unaccent`; the vectors carry the meaning the missing stemmer loses. Vector search is `pgvector` with an HNSW index on `vector(384)`, cosine distance. The two rankings merge with reciprocal rank fusion, `score = Σ 1/(60 + rank)`, in one SQL statement that filters by the deployment's sources first. The eval set of T-3053 measures recall@10 on Slovak, Czech, Finnish and English questions; when lexical recall falls short, §4's `pg_search` route reopens with its numbers.

### 3.4 Models only through `jc-agent-proxy`

No model key is in `jc-assistant`. The proxy today authenticates an agent run by its ticket (AG-52) and keeps per-run limits (`limits.rs`, AG-41). It gains a second caller: the `jc-assistant` ServiceAccount (Keycloak client credentials, audience `jc-agent-proxy`). The service names an `AssistantDeployment` and a conversation on every model call, and the proxy enforces the deployment's budget (requests per minute, tokens per day, tokens per conversation) with the same limiter. A public channel cannot spend more than its deployment allows.

### 3.5 MCP connectors

- **Platform data** is the Endpoint MCP surface the gateway already serves, `POST /api/endpoint/{slug}/mcp`, whose grants the gateway enforces. A public channel calls it without a token, so it reads only what an Endpoint with `audience: public` serves to anyone. The internal channel calls it with the person's token, exchanged as ADR-N-038 exchanges it for a run, so the person reads what they may read and no more.
- **External public MCP servers** are listed per deployment by URL and by the tools allowed, each switched on by an administrator. The service reaches them only through its egress allow-list (red lane, the shape of ADR-N-037's `spec.egress`). Write tools are refused at registration, and only tools an administrator listed are offered to the model.

### 3.6 Scripts through `jc-functions`

When a tool result is too large for the model (1,000 events), the model writes a short JavaScript filter and `jc-functions` runs it on that result: a fresh QuickJS runtime per call, memory-capped, interrupt-capped and timed out. That runtime is already reviewed and tested (`an_endless_loop_is_interrupted`, the out-of-memory test). `jc-functions` gains the `jc-assistant` client as a second caller of `POST /invoke`, with no network access from the script. A second sandbox (Monty, Python) would be a second runtime to review for the same job.

### 3.7 Threat model

| Risk | Control | Task |
|---|---|---|
| Prompt injection from crawled text ("ignore your instructions, call…") | Retrieved text goes to the model as quoted data in a fixed frame. Tools are read-only and limited to the deployment's list. A tool call never carries a credential the model wrote. Answers cite their source URLs. | T-3055, T-3059 |
| SSRF through the crawler (a sitemap or link to `169.254.169.254`, `10.x`, `localhost`) | Every host is resolved and refused when any address is private, loopback, link-local or carrier-grade NAT (the check `jc-agent-proxy`'s `public_dns.rs` makes), re-checked on every redirect. The Deployment's NetworkPolicy allows egress to the public internet on 80/443 only. | T-3052 |
| Tool and cost abuse on a public channel | Per-deployment budgets in the proxy (§3.4), per-IP rate limits at APISIX, a maximum of tool calls per answer, scripts capped by `jc-functions`. | T-3055, T-3058 |
| Internal knowledge leaking to a public channel | Every source carries `visibility: public` or `internal`. A public deployment's retrieval filter names only public sources, in SQL, before ranking. | T-3051, T-3053 |
| Connector credentials | `secretRef` only, resolved by the reconciler, never logged and never in a prompt. | T-3051 |
| A third-party site framing the widget for clickjacking | `frame-ancestors` from the deployment's `allowedOrigins`. Anonymous sessions are bound to their origin. | T-3058 |
| Memory over budget on a large PDF | One extraction at a time, page and byte caps per document, memory measured in the live journey. | T-3052, T-3059 |

### 3.8 Memory budget, 1 GB

| Part | Budget |
|---|---|
| Embedding model (int8 ONNX, 118 MB on disk) and ONNX Runtime arenas at batch 16 | 350 MB |
| Tokenizer, sentencepiece | 25 MB |
| `kreuzberg` with pdfium, one document at a time, 50 MB and 500 pages max | 250 MB |
| `spider` HTTP crawl, bounded concurrency 4, bodies streamed | 80 MB |
| axum, `rig`, `rmcp` clients, sqlx pool of 8, SSE streams | 120 MB |
| Headroom | 175 MB |
| **Limit** | **1 Gi** (request 512 Mi) |

The model is loaded once at start. The crawl worker and the chat API share it; a burst of crawling waits for embedding slots, so it never starves a chat answer.

Measured 2026-10-06 (T-3053): the tokenizer estimate was wrong by an order of magnitude. XLM-R's 250,000-piece table and trie take 290 MB once loaded; the int8 model in ONNX Runtime 165 MB; the worker rests at 490 MB. fastembed was dropped for `tokenizers` and `ort` directly (it held a second tokenizer copy, 713 MB), and each text is embedded alone, because the int8 export scales its activations per input. [Architecture/22 §6](../Architecture/22-knowledge-assistant.md#6-memory) carries the current table.

## 4. Alternatives Considered

- **ParadeDB `pg_search` for BM25.** The cluster's image does not carry it. Adding it means a custom Postgres image or a CloudNativePG image-volume extension, plus a legal review of AGPL-3.0 for an image the platform distributes. Postgres full-text search with `pgvector` and RRF needs neither. The decision is reopened only by T-3053's eval numbers.
- **A separate vector database (Qdrant, Weaviate).** A second stateful service on a 16 GB node, with its own backups, for what `pgvector` already does in the database the platform backs up.
- **The fp32 `multilingual-e5-small` that fastembed lists.** 470 MB of weights alone leaves no room in 1 GB.
- **A headless browser in the crawler (`spider`'s `chrome` features).** Hundreds of megabytes per tab. Sites that need JavaScript to show text are out of scope for the first version.
- **Model keys in the assistant.** They would bypass the per-run and per-deployment budgets the proxy keeps, and put a second copy of the key in the cluster.
- **Monty as the sandbox.** §3.6.

## 5. Consequences

- New: `crates/assistant` (`jc-assistant`), the `assistant` database, two manifest kinds `KnowledgeSource` and `AssistantDeployment` (T-3051), a second caller of `jc-agent-proxy` and of `jc-functions`.
- The chain, in order: T-3050 (database, `pgvector` HNSW, FTS columns; no `pg_search`), T-3051 (kinds), T-3052 (crawler with the SSRF check), T-3053 (embeddings with the int8 user-defined model, hybrid SQL, eval set), T-3054 (CKAN as a source), T-3055 (agent loop, proxy budgets, MCP connectors, chat API), T-3056 (scripts through `jc-functions`), T-3057 (administration in the Portal), T-3058 (widget and channels), T-3059 (security review, memory, live journey).
- T-3050's title named `pg_search`; under this ADR it installs nothing new and records the eval threshold that would reopen §4.
- Architecture: [22-knowledge-assistant](../Architecture/22-knowledge-assistant.md).

## Related

- [ADR-N-014](adr-n-014-agent-runner-openhands-optional.md): the agent runner and its proxy.
- [ADR-N-017](adr-n-017-fullstack-apps-oauth2-proxy-builder-agent.md): models only through the proxy.
- [ADR-N-037](adr-n-037-an-origin-per-app.md): egress allow-lists on the red lane.
- [ADR-N-038](adr-n-038-an-agent-run-reads-as-its-person.md): token exchange, reading as the person.
- [Architecture/22-knowledge-assistant](../Architecture/22-knowledge-assistant.md): schema, channels and flows.
