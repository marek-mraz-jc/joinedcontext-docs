---
sidebar_position: 23
title: "Public Assistant for Banská Bystrica"
description: How the public chat, its widget, the retrieval loop, data answers through MCP, the public MCP connectors and the admin tool are built on the existing jc-assistant, scoped to Banská Bystrica and BBSK, inside a fixed token budget.
---

# Public Assistant for Banská Bystrica

A resident of Banská Bystrica opens a chat on the city's website, asks in Slovak, and gets a short answer with links to the pages and datasets it came from. This chapter maps what the platform already has for that on 2026-10-15 and names, piece by piece, what the goal of 2026-10-15 (`tasks/GOAL-assistant.md`) keeps, changes or adds. Nothing here starts a second assistant: the service is [jc-assistant](22-knowledge-assistant.md), and every change below lands in it, in its manifest kinds, or in the gateway's MCP surfaces. File references are to `origin/main` of each repository on 2026-10-15 (platform `d1b8f7f`, portal `7fc3df50`, deployment `ed9ef76`).

## 1. What exists today

Two assistants exist, and only one of them is the public one.

| Piece | Where | State on dev |
|---|---|---|
| Portal assistant (builder dock, workbench) | portal `ui/src/assistant/AssistantDock.tsx:186`, `src/agents/oneshot/mod.rs:181` | Signed-in only. Builds Endpoints and pipelines through agent runs. Out of scope for the public chat. |
| Knowledge assistant `jc-assistant` | platform `crates/assistant/` | Serves `https://assistant.dev.joinedcontext.com/d/helsinki-catalogue/widget` (200); no Banská Bystrica deployment is public (`/d/banskabystrica-knowledge/widget` answers 404). |
| Store and hybrid search | platform `crates/assistant/migrations/0001_store.up.sql:92-97` (pgvector 384 + HNSW, `tsvector` GIN), `crates/assistant/src/lib.rs:211` (`hybrid_search`, RRF `k = 60` at `lib.rs:44`) | Built (T-3050, T-3053). |
| Sources | crawler `src/crawl/`, extraction `src/extract.rs`, CKAN `src/ckan.rs` (anonymous `package_search`, `ROWS = 100` at `ckan.rs:23`), catalogue `src/catalogue.rs`, User Guide `src/guide.rs` | Built. Passages of 1 200 characters with 200 overlap (T-3052); embeddings `multilingual-e5-small` int8 at index time (`src/embed.rs`). |
| Chat API | `src/chat/mod.rs:132`, `POST /api/v1/d/{publicId}/chat`, SSE events `tool`, `answer`, `citations`, `status` (`chat/mod.rs:460-485`) | Built. The answer arrives in one `answer` event, not as tokens. |
| Agent loop | `src/chat/agent.rs:269`: up to `MAX_CALLS = 6` model calls (`agent.rs:18`), `PASSAGES = 8` per search (`agent.rs:21`), `MAX_CALLS_PER_REPLY = 4` tool calls (`agent.rs:27`), `MAX_ANSWER_TOKENS = 3 000` (`chat/model.rs:65`) | Built. The model decides each search; no router, no round limit below 6. |
| Widget | `src/chat/widget.rs:1`, `widget/render.js`, `widget/widget.js` | An iframe page per deployment. Safe Markdown, `[n]` citations (T-3325). No full chat page, no launcher script, no suggestions, no disclaimer. |
| Connectors (MCP) | `src/chat/mcp.rs` (results cut at `MAX_RESULT_CHARS = 20 000`, `mcp.rs:12`); calls `/api/endpoint/{slug}/mcp` without a token on public channels | Built. A connector names an Endpoint of the deployment's own project only (platform `crates/jc-core/src/kinds/assistant.rs:468-472`). |
| Model path | `jc-assistant` → `jc-agent-proxy` `/v1/llm/*` → OpenRouter, model from env `JC_ASSISTANT_LLM` (`src/bin/jc-assistant.rs:145`), today `google/gemini-3.8-flash` | **Down on dev**: the proxy runs with `replicaCount: 0` (deployment `components/agent-runner/values/proxy/development-values.yaml.gotmpl:9`) since the spend guard tripped on 2026-10-08; only the owner sets it back. |
| Admin | portal `ui/src/pages/knowledge/KnowledgePage.tsx:55`, `SourcePage.tsx`, deployment form `ui/src/schemas/knowledge.ts:91-182` | Sources, page tree, include/exclude, recrawl, usage, embed snippet. No model field, no suggestions, no disclaimer, no file upload; the form offers only `website` and `ckan` sources (`knowledge.ts:21`). |
| Banská Bystrica seeds | deployment `components/context-gateway/seed/banskabystrica/banskabystrica-assistant-knowledge.yaml` (`channel: internal`, `publicId: banskabystrica-knowledge`), `banskabystrica-knowledge-web.yaml` (start URL `https://www.banskabystrica.sk/`), `banskabystrica-knowledge-catalogue-ngsi.yaml` | Internal channel only. BBSK (project `bbsk`) has no assistant seed. |
| Open data portal (CKAN) | `https://data.dev.joinedcontext.com`, deployed by `components/ckan` | Public, 12 datasets in 5 organizations: `bbsk` (2), `banskabystrica` (2), `hel-fi` (4), `praha` (1), `zilina` (3) (`/api/3/action/package_search`, 2026-10-15). |

## 2. Public surfaces today

| Surface | Path | Who reaches it | Limit |
|---|---|---|---|
| Assistant chat and widget | `assistant.{domain}/api/v1/d/*`, `/d/*` | Anyone, on `public`, `ckan` and `iframe` channels, Origin checked against `allowedOrigins` | APISIX 30/60 s per IP (deployment `components/assistant/apisix-plugins.yaml:26-30`), plus the deployment's limits |
| Per-Endpoint MCP | `/api/endpoint/{slug}/mcp` | Anyone when the Endpoint's audience is public (platform `crates/context-gateway/src/app.rs:3069-3075`) | Gateway limit only when the Endpoint sets `rateLimits` (`middleware/rate_limit.rs:207-218`); APISIX 5 000/60 s |
| MCP hub | `/api/mcp` | Anyone; without a token it lists every project's public Endpoints (`mcp/hub.rs:101-119`): 42 on dev, from Helsinki, Praha, Žilina, BBSK and Banská Bystrica spaces | 600/min per subject or IP |
| Named MCP servers | `/api/mcp/{project}/{name}` | Anyone when the server's audience is public (`mcp/server.rs:75-84`) | Hub limit per server |
| Context Space MCP | `/cs/{space}/mcp` | Per the space's audience | No gateway limit (`rate_limit.rs:250-255`); APISIX keyed on `Authorization`, so every anonymous caller shares one bucket |
| DCAT-AP catalogue | `/catalog.jsonld`, `/catalog.ttl` | Anyone | 300/60 s per IP |
| CKAN | `data.{domain}` | Anyone | 300/60 s per IP |

The anonymous hub's `tools/list` on dev includes `create_subscription`, `update_subscription` and `delete_subscription`. Whether a call succeeds depends on each Endpoint's Policy (`app.rs:3319-3325`), not on the route, so a public surface is read-only only when every member's Policy is. Section 7 turns each gap into a task.

## 3. Target: one request, end to end

```text
browser ── widget or /d/{publicId} ── POST /api/v1/d/{publicId}/chat (SSE)
   jc-assistant
     1. limits: per-IP and per-chat counters, daily cost cap        (T-4149)
     2. cache: same normalized question + same index digest → stored answer
     3. router call, cheap model, JSON out: route rag|data|both,
        up to 3 search queries in the question's language and in
        each language the sources are written in                    (T-4139, T-4259)
     4. retrieval rounds, server-run, at most 3:
          rag  → hybrid_search per query, top passages by RRF
          data → read-only MCP tools on the deployment's Endpoints    (T-4140)
        after each round but the last, a follow-up call reads the
        first 300 characters of the top 5 passages as quoted data:
        {"answers": true} answers now; {"answers": false,
        "queries": [...]} runs the next round in the sources'
        language; any other reply answers with what was found       (T-4259)
        the first round is the question as asked, searched and
        judged while the router call (3) runs; when it answers, the
        router's queries are added and nothing more is judged       (T-4293)
        a first round whose top passage is in the first three of
        both the word and the meaning ranking (fused score at least
        2/63) answers without the judge call                        (T-4360)
     5. answer call, once, streamed token by token, top passages
        and data rows as quoted data, citations from what was found
     6. SSE: delta… , data (rows, dataset link, download link),
        citations, done (tokens in/out, latency, stagesMs)
```

Decided (worker-1, owner may override): the server runs the rounds and the model never calls `search` itself, because the goal fixes the answering model to one call per answer and the injection rules want the tool allowlist enforced by code; options: keep today's model-driven loop with a lower `MAX_CALLS` (fewer code changes, but every round costs a full answering-model call with all passages again).

The sources' languages are the distinct `chunks.lang` of the deployment's sources, most passages first, at most 4, kept for 10 minutes like an Endpoint's type list. Full-text search uses the configuration of each passage's own language (`jc_fts_config`), so an English query never matches a Slovak page by its words: only the vectors would find it, and the round's best passages would rank in one list alone. The router therefore writes each query once in the question's language and once in every source language that differs; the `searching` stage event shows each one, so a person reads "hľadám: …" for the Slovak search of an English question.

Decided (supervisor, owner may override; T-4259): no RAG framework, because LangChain, LlamaIndex and Haystack are Python (no new languages) and the Rust agent crates add a large dependency for a loop this crate already has; the multi-query rewrite with a relevance judge is two prompts and one JSON field; options: a framework, a translation service (another outbound host and key). The answer still streams once: the judgment runs before it, never as an answer-then-retry loop.

Decided (worker-1, owner may override): the public chat page is served by jc-assistant at `assistant.{domain}/d/{publicId}` beside the existing widget, from the same `render.js`, plus a one-line launcher `assistant.{domain}/d/{publicId}/embed.js` that a city site includes, because every Portal route needs a login and the widget already has the Origin checks, the limits and the renderer; options: a public Portal route (a second renderer and a second set of limits).

## 4. Token budget at runtime

| Step | Model | Input | Output |
|---|---|---|---|
| Router, round 1 | cheap | system 300 + question and last 2 turns ≤ 400 | ≤ 120 (JSON) |
| Follow-up, after rounds 1-2 (until the passages answer) | cheap | 350 + question, searches and 5 passage starts of 300 characters ≤ 500 | ≤ 80 |
| Answer | chosen by T-4144 | system 400 + top 6 passages (about 300 tokens each, 1 800) + data rows ≤ 600 + question 250 | ≤ 700 (owner limit) |

A typical answer is one router call, one follow-up and one answer call: about 820 + 930 + 3 750 tokens (T-4259 adds the follow-up to every searched question), so the median target of 4 000 for the answer call alone is tight and 4 000 for both is reachable only with 5 passages. Decided (worker-1, owner may override): count the goal's 4 000-token median over the answer call plus the router calls, and cut passages to the top 5 (`PASSAGES` 8 → 5) when the T-4144 run shows the median above it, because the owner's target is per answer, and passages are the one input that scales. The 12 000 ceiling holds by construction: the router and two follow-up calls (≤ 2 680) plus one answer call (≤ 3 750 + 700).

The numbers are read, never estimated: every model response through `jc-agent-proxy` carries the OpenAI-compatible `usage` object (`prompt_tokens`, `completion_tokens`), and jc-assistant sums it over the router and answer calls of one question into the final SSE event `done`, which today carries `tokens` alone and gains `tokensIn`, `tokensOut`, `modelCalls`, `firstTokenMs`, `totalMs` and `cached` ([API/05 §1.3](../API/05-knowledge-assistant.md#13-answer-server-sent-events)). T-4144 reads exactly these fields per answer; a cached answer reports `tokensIn: 0`. Each answer also leaves one row in `answer_timings`: deployment, time, `firstTokenMs`, `totalMs`, `stagesMs`, model calls, whether it was cached and whether the judge call was skipped (T-4360), with no question or answer text, kept 30 days; the latency eval reads p50 and p95 per stage from the `done` events it receives (T-4293).

Embeddings stay at index time (`embed.rs`). The answer cache is keyed by the normalized question, the deployment and the index digest, so a re-index invalidates it.

## 5. Data answers through MCP

The CKAN source already indexes one page per dataset (`ckan.rs`), so "which datasets exist about schools?" is a RAG answer whose citation is the dataset's CKAN page. Live values ("what do the temperature sensors show?") use the connectors: the router names a type from the catalogue source's passages, and the server calls `query_entities` with a small `limit` on the deployment's Endpoints. The rows go to the answer call as a compact table and to the browser as a `data` event, which the widget shows as a table (and a chart for a numeric time series) with the dataset link and a download link taken from the Endpoint's DCAT record.

A question that needs more than the router's reads (a filter, a second step, history, the schema first) runs the data loop (T-4294): the router's reads are its first steps, then the answering model is offered the connectors' read-only tools, `{endpoint}__{tool}` with `/` of a scoped Endpoint written `--`, and calls them until it has what the answer needs, at most `answer.maxDataSteps` tool calls (default 10, up to 25) and `answer.maxDataSeconds` (default 20, up to 60) per question. A reply without a tool call is the answer; at either bound the last call is told to answer from what it read and offers no tool. Each tool result reaches the model as JSON numbered `[n]`, cut at 8,000 characters, after the rule that it is data. Each step is logged as tool, Endpoint, status, rows and milliseconds, never a value. The owner set both as settings (2026-10-16 08:48Z): raise the defaults to what the eval measures when 8 of 10 multi-step questions need more; the per-question token cap and the cost caps still bind.

Read-only by allowlist: `list_types`, `get_type`, `list_attributes`, `query_entities`, `get_entity`, `get_attribute_value`, `query_temporal`, `retrieve_temporal`, `describe_schema`, `describe_access`; the gateway holds an anonymous temporal read to 31 days and `lastN` 100 (T-4261). Any other tool name is refused by jc-assistant before a request leaves it.

## 6. Scope: Banská Bystrica and BBSK only

The city (`banskabystrica`) and the region (`bbsk`) are two projects on dev, each with its own spaces and public Endpoints (`banskabystrica-verejne` 4, `ovzdusie` 1, `bbsk-registre` 3, `bbsk-kraj` 1, `bbsk-kpi` 1 on the hub list). Today a deployment's connectors may name Endpoints of its own project only (`assistant.rs:468-472`), so one public assistant cannot read the region's Endpoints.

Decided (worker-1, owner may override): one public deployment `banskabystrica` in project `banskabystrica`, whose spec names the other projects it may read (`bbsk`) explicitly; the reconciler admits only public Endpoints of the listed projects, and the CKAN source takes an organization filter (`banskabystrica`, `bbsk`); because the scope is then fixed server-side in a manifest, and Helsinki, Praha and Žilina stay unreachable by construction; options: two deployments and two widgets (the resident would have to know which body answers), or a deployment that reads any public Endpoint (Helsinki reachable).

Web sources: `https://www.banskabystrica.sk/` and `https://www.bbsk.sk/` (approved in T-3067; the BBSK server's missing intermediate certificate is handled since T-3298). Links in answers go only to these domains, `data.{domain}` and the platform's own Endpoint URLs.

## 7. Keep, change, add

| Piece | Verdict | Task |
|---|---|---|
| jc-assistant store, crawler, extraction, embedder, hybrid search | keep | none |
| Agent loop (`chat/agent.rs`) | change: router call, server-run rounds (≤ 3), one streamed answer call, answer cache, token and latency counts in the `done` event | T-4139 |
| Model client (`chat/model.rs`) | change: streaming from the proxy, per-call model (router vs answer) | T-4139 |
| Widget | change: full-page mode, launcher script, suggestions, disclaimer, new chat, copy, thumbs, `data` event rendering, SK first | T-4138 |
| Connectors (`chat/mcp.rs`) | change: read-only allowlist, data rows event, cross-project scope | T-4140, new task (scope) |
| `AssistantDeployment` kind | add: `model` (router, answer), `suggestions`, `disclaimer`, `enabled`, `limits`, `scope.projects`; CKAN source `organizations`; `upload` source | new task (kinds, docs first) |
| Portal knowledge admin | change: fields above, file upload, index status per source | T-4142 |
| Public MCP connectors | add: public named servers for `banskabystrica` and `bbsk`, anonymous read-only tool allowlist in the gateway, default anonymous rate limit on every MCP surface, a public page with copy-paste setup | T-4141, new tasks (gateway allowlist, page) |
| Banská Bystrica public deployment | add: seed with `channel: public`, web + CKAN + catalogue sources, `allowedOrigins` | new task |
| `jc-agent-proxy` on dev | change: back to 1 replica, after the deployer frees memory (node at 96 % on 2026-10-15) and refreshes the model key; the values file says only the owner lifts the spend-guard hold | new task, `@user` |
| Portal assistant (builder) | keep, untouched | none |
| Data ingestion | add: the inventory's datasets into CKAN under both organizations | T-4143 |
| Evaluation | add: 30 questions, scope, injection, model table | T-4144 |
| Security | attack today's surfaces, then the new ones | T-4147, T-4148 |

## 8. Admin tool

The administrator works in the Portal's existing knowledge pages for the `banskabystrica` project. A source is a `KnowledgeSource` (website with start URLs and include/exclude, CKAN with organizations, catalogue, guide, and the new `upload`); the assistant is the `AssistantDeployment` (prompt, router and answer model, greeting, suggestions, disclaimer, languages, connectors, scope, limits, on/off). Index status per source (pages, documents, passages, last crawl, job state, errors) already comes from `GET .../knowledge/sources` (portal `src/api/knowledge.rs:254-263`). Steering a source needs `propose` on `KnowledgeSource`; changing the deployment needs the same right on `AssistantDeployment`. Uploaded files go through the same extraction as crawled PDFs and never become instructions: every passage reaches the model as quoted data (AG-105).

## Related

- [Knowledge Assistant](22-knowledge-assistant.md): the service this chapter changes, its kinds, database and threats.
- [ADR-N-040](../Decisions/adr-n-040-knowledge-assistant.md): why one Rust service, Postgres retrieval and models only through the proxy.
- [Agents and MCP](07-agents-and-mcp.md): the gateway's MCP surfaces the connectors and the public page use.
- [Open data catalogue](21-open-data-catalogue.md): where the datasets the assistant links come from.
- [Knowledge assistant API](../API/05-knowledge-assistant.md): the chat route and SSE events the widget reads.
