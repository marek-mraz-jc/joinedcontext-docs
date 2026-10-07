---
sidebar_position: 22
title: "Knowledge Assistant"
description: The jc-assistant service, which crawls websites, PDFs and the CKAN catalogue into Postgres, answers questions in four channels and calls the platform's Endpoints and chosen public MCP servers as tools.
---

# Knowledge Assistant

A city's people ask the same questions the city's websites, PDFs and open data already answer. The knowledge assistant reads those sources ahead of time and answers from them, with links to where each answer came from. It runs inside the Portal for staff, on the data platform, in the CKAN catalogue, and as an iframe on any public site. [ADR-N-040](../Decisions/adr-n-040-knowledge-assistant.md) records the choices and the verified versions; this chapter is the design the chain T-3050…T-3059 builds.

## 1. One service, three roles

`jc-assistant` is one Rust binary (`joinedcontext-platform/crates/assistant`) in one Deployment, memory limit 1 Gi:

| Role | What it does | Reads | Writes |
|---|---|---|---|
| Crawl worker | Claims a job, fetches pages and PDFs, extracts text, chunks it, embeds it | `KnowledgeSource` manifests, the public web, the CKAN API | `pages`, `documents`, `links`, `chunks`, `jobs` |
| Retrieval | One SQL statement: filter by sources, full-text rank, vector rank, reciprocal rank fusion | `chunks` | nothing |
| Chat API | Server-Sent Events; the agent loop calls the model through `jc-agent-proxy` and the tools | `AssistantDeployment` manifests, retrieval, MCP connectors | `conversations`, `usage` |

The embedding model is loaded once and shared. Crawling waits for an embedding slot, so it never slows a chat answer.

## 2. Two manifest kinds

Both are project manifests, proposed like every other one (MF-51, MF-52). A project's administrator decides what its assistant reads and where it answers; `jcctl validate` resolves every reference inside the project before a Change exists.

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: KnowledgeSource
metadata: { name: bb-web, namespace: banskabystrica }
spec:
  source: website               # website | ckan
  startUrls: [https://www.banskabystrica.sk/]
  sitemap: true
  include: ["/zivot-v-meste/**", "/samosprava/**"]
  exclude: ["/**/tlac/**"]
  maxDepth: 3
  maxPages: 2000
  pdf: { policy: include, maxBytes: 52428800, maxPages: 500 }
  offDomainDocuments: false     # a PDF on another host is skipped unless this is true
  schedule: "0 3 * * *"
  languages: [sk]
  visibility: public            # public | internal
---
apiVersion: joinedcontext.com/v1alpha1
kind: AssistantDeployment
metadata: { name: bb-public, namespace: banskabystrica }
spec:
  publicId: bb-public
  channel: public               # public | internal | ckan | iframe
  systemPrompt: Odpovedaj stručne a vždy uveď zdroj.
  sources: [bb-web]
  connectors:
    - { endpoint: mesto-verejne, tools: [query_entities], timeoutSeconds: 20 }
  allowedOrigins: [https://www.banskabystrica.sk]
  rateLimit: { requestsPerMinute: 60, perClientPerMinute: 10 }
  budget: { tokensPerDay: 2000000, tokensPerConversation: 40000 }
  theme: { primaryColor: "#0b5394", greeting: "Dobrý deň, s čím vám pomôžem?" }
  languages: [sk, en]
  sandbox: false
```

A `KnowledgeSource` of `source: ckan` names a `CkanInstance` of the project in `ckanInstanceRef` instead of `startUrls`. One of `source: catalogue` names neither: it is the project's own NGSI-LD catalogue, one page per Endpoint of the spaces it lists in `contextSpaces` (every space when the list is empty), written from the repository the worker already reads, so it needs no credential: the Endpoint's title, space, audience and address, its CKAN dataset when it publishes one, and per entity type of the space's model the class description and every attribute with its description and unit, as far as the Endpoint's projection and ModelProjection let it serve them. A public Endpoint's page also carries each type's entity count, which the worker reads anonymously through the gateway, as any visitor could, and the time it counted; a type a visitor finds no entity of is left off, so an Endpoint whose Policy grants bicycles is not described as serving buses. A `public` catalogue source indexes public Endpoints alone, so a private space never reaches a public channel; an `internal` one indexes every Endpoint of its spaces for the `internal` and `platform` channels. The worker reads the source again within a minute of a change to a manifest or model it is built from, and on its schedule for the counts; a page cites the CKAN dataset when the Endpoint publishes one, else the Endpoint's public address (AG-116, T-3225). A deployment's `public`, `ckan` and `iframe` channels answer people nobody signed in: each MUST list its origins explicitly (no `*`, no path, `https` only) and carry a rate limit and a budget, and it may name only `visibility: public` sources. A connector names an Endpoint of the same project and the tools of its MCP surface the assistant may call.

## 3. Database sketch

Database `assistant` on the platform's CloudNativePG cluster (`pgvector` 0.8.6 is already in its image), one schema, migrations in the crate (T-3050):

| Table | Key columns |
|---|---|
| `sites` | `id`, `org`, `source` (manifest name), `visibility`, `last_crawl` |
| `pages` | `id`, `site_id`, `url` unique per site, `etag`, `last_modified`, `content_hash`, `status`, `fetched_at` |
| `documents` | `id`, `page_id` (where it was linked), `url`, `mime`, `bytes`, `pages`, `content_hash` |
| `links` | `from_page`, `to_url`, `kind` (`page`, `pdf`, `external`), for the administration's page tree |
| `chunks` | `id`, `site_id`, `page_id` or `document_id`, `ordinal`, `text`, `lang`, `fts tsvector`, `embedding vector(384)`, `visibility` |
| `jobs` | `id`, `source`, `state`, `claimed_by`, `attempts`, `error`, `run_after` |
| `conversations` | `id`, `deployment`, `channel`, `created_at`; no personal data for the public channel |
| `usage` | `deployment`, `day`, `requests`, `tokens_in`, `tokens_out` |

Indexes: GIN on `chunks.fts`, HNSW on `chunks.embedding` (`vector_cosine_ops`), btree on `(visibility, site_id)`. The `fts` column uses `english` or `finnish` where Postgres has the stemmer, `simple` with `unaccent` for Slovak and Czech.

Retrieval is one statement: the candidate set is filtered by the deployment's sources and visibility, the top 50 of each ranking are fused by `Σ 1/(60 + rank)`, and the best 8 chunks go to the model with their URLs.

## 4. Channels

| Channel | Who | Identity | What it may read |
|---|---|---|---|
| `public` | anyone, in an iframe on an allowed origin | none; an anonymous session bound to the origin | public sources; Endpoints with `audience: public`, called without a token |
| `internal` | staff in the Portal's chat | Keycloak OIDC, the person's token exchanged as ADR-N-038 does | public and internal sources; Endpoints as the person |
| `ckan` | catalogue visitors | none | public sources, the CKAN source, public Endpoints |
| `platform` | the data platform's pages | the Portal session | as `internal` |

The widget is a small script that opens an iframe at `https://assistant.{domain}/w/{deployment}`. Its `frame-ancestors` is the deployment's `allowedOrigins`.

## 5. An answer, end to end

1. The channel posts the question with the deployment and the conversation.
2. `jc-assistant` asks `jc-agent-proxy` for a completion as its ServiceAccount, naming the deployment; the proxy checks the deployment's day and calls the model, and the assistant checks the conversation's budget before each call ([API/05](../API/05-knowledge-assistant.md) §2).
3. The model calls `search` (retrieval), an Endpoint's MCP tool, or an allowed external tool. Tool results are passed back as quoted data. A result over 20,000 characters goes to `jc-functions` with the model's short filter script, and only the script's output returns.
4. The answer streams back with numbered citations to the source URLs.

## 6. Memory

| Part | Budget |
|---|---|
| Embedding model in ONNX Runtime (int8, measured T-3053) | 165 MB |
| Tokenizer (XLM-R, 250,000 pieces, measured T-3053) | 290 MB |
| PDF extraction, one document at a time | 250 MB |
| Crawl fetches, concurrency 4 | 80 MB |
| Web server, agent loop, MCP clients, pool | 120 MB |
| Headroom | 95 MB |

The worker measured 490 MB resting with the model loaded and 679 MB at the peak of loading it (T-3053). The tokenizer is the large part: its piece table and trie, not its file, which is 17 MB. One embedding runs at a time and one text per call, so embedding adds nothing measurable.

T-3059 measures it on dev with a 500-page PDF and twenty concurrent chats.

## 7. Threats

ADR-N-040 §3.7 holds the table: prompt injection from crawled text, SSRF through the crawler, tool and cost abuse on public channels, internal knowledge reaching a public channel, connector credentials, clickjacking of the widget and memory on large documents. Each has its control and its task in the chain.

## Related

- [ADR-N-040](../Decisions/adr-n-040-knowledge-assistant.md): the decision and the verified versions.
- [API/05-knowledge-assistant.md](../API/05-knowledge-assistant.md): the chat route and the assistant's calls to the proxy (AG-98…AG-111).
- [19-agent-runner.md](19-agent-runner.md): `jc-agent-proxy`, through which every model call goes.
- [21-open-data-catalogue.md](21-open-data-catalogue.md): the CKAN catalogue the `ckan` channel and source use.
- [04-context-spaces-and-endpoints.md](04-context-spaces-and-endpoints.md): the Endpoints whose MCP surface the connectors call.
- [20-app-sdk.md](20-app-sdk.md): `jc-functions`, the script runtime.
