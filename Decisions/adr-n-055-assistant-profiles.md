---
sidebar_position: 56
title: "ADR-N-055: Assistant Profiles: Endpoints by Selector, Themes, an MCP Server and a Context Page per Assistant, Public Clients Outside"
---

# ADR-N-055: Assistant Profiles: Endpoints by Selector, Themes, an MCP Server and a Context Page per Assistant, Public Clients Outside

Date: 2026-10-18  
Status: Accepted  
Decision Makers: product owner (2026-10-18 21:48Z, "okay implement that": assistant profiles with RAG and Endpoint selectors, categories, MCP per assistant, context page, public UI outside the platform); shape recorded by worker-5 (T-4689), owner may override

This record says how one organization runs any number of assistants on the one assistant engine: what each assistant reads (its knowledge sources, the Endpoints a selector picks, or both), how a person sees and reuses that reach (a context page and an MCP server of the assistant's own), and what a public chat page built outside the platform may hold. It amends [ADR-N-040](adr-n-040-knowledge-assistant.md) and reuses the selector of [ADR-N-043 §7](adr-n-043-named-mcp-servers.md#7-amendment-2026-10-17-connector-profiles-t-4504). It binds `jc-core` (T-4690), the gateway (T-4691), `jc-assistant` (T-4692), the Portal (T-4693) and the public client (T-4694). Requirements MF-52, MF-58…MF-61, AG-121…AG-125, EP-136…EP-138.

## 1. Context

On 2026-10-18 an `AssistantDeployment` (MF-52) answers from up to its listed `KnowledgeSource`s and from the Endpoints its `connectors` name one by one, each with its tools and timeout, or from the reach of one `McpServer` (MF-56). Four things are missing:

| Need | Today | Why it matters |
|---|---|---|
| An assistant for "transport in Banská Bystrica" | each Endpoint listed by hand; a new transport Endpoint stays unknown to it until someone edits the deployment | a city with 100 Endpoints keeps ten deployments in sync by hand |
| A person asks "what does this assistant know?" | nothing answers that; the system prompt and the manifest are the only record | visitors cannot judge an answer, and the operator cannot check a deployment before it goes live |
| The same reach in Claude, ChatGPT or Gemini | a person builds an `McpServer` with the same Endpoints again | two lists for one reach drift apart |
| A city's own chat page in its own design | the widget on `assistant.{domain}` is the only face; a page elsewhere must frame it | the owner wants the assistant's look and placement on the city's site, outside the platform |

The platform already has the parts: the EU data-theme table on every Endpoint (`catalog.themes`, or the classification of its types, T-4498), the `select` grammar of named MCP servers (MF-55), the anonymous OAuth server for public MCP (ADR-N-052), and the chat API with its challenge and visitor token (API/05 §1).

## 2. Decision

Decided (worker-5, owner may override): an assistant profile is the existing `AssistantDeployment` with the McpServer's `select` grammar, the 13 EU data themes as the one category list, and two read-only surfaces derived from it; options: a new `AssistantProfile` kind (a second kind for what the deployment already holds), a free category list per organization (labels drift between CKAN, the catalogue and the assistants, and DCAT-AP harvesters understand only the EU table), a selector evaluated by the model at question time (the model would choose what it may read).

### 2.1 One engine inside, any number of assistants

`jc-assistant` stays the one engine: retrieval over knowledge sources, the data loop over Endpoints through the gateway, Policy, budgets, rate limits, transcripts and their retention (AG-99). An assistant is an `AssistantDeployment`; an organization declares as many as it needs, each with its own `publicId`, channel, prompt, sources, Endpoints, limits and look. Data, rights, model keys and transcripts never leave the platform: a client outside holds only the `publicId` and the short-lived visitor token of API/05 §1.2.

### 2.2 What an assistant reads

A deployment reads from zero or more knowledge sources and zero or more Endpoints, and from at least one of the two (MF-52):

- `sources` stays the list of `KnowledgeSource`s; none makes a data-only assistant.
- `connectors` stays the explicit list of Endpoints with their tools and timeout; none is allowed.
- `select` (new, MF-58) picks Endpoints by the McpServer grammar of MF-55, with one more field, `types` (MF-61): `projects` (the publisher: one project is one CKAN organization, EP-81), `spaces`, `domains`, `themes`, `types` and `accessLevel`. An Endpoint matches when it matches every field given, one value of a field being enough. `select: {}` matches every Endpoint the bound of §2.3 admits.
- `exclude` (new, MF-59) names Endpoints that never join, whatever the selector, the connectors or the server says.
- `mcpServer` (MF-56) stays: that server's reach joins as before.

The deployment's Endpoints are **(connectors ∪ select ∪ mcpServer) − exclude**, then bounded by §2.3. A connector keeps its own `tools` and `timeoutSeconds`; an Endpoint that joins only by the selector or the server is offered its read tools with `timeoutSeconds: 20`.

### 2.3 A selector only narrows

`jc-core` holds the one resolver, `resolve_connectors(deployment, catalog, grants)`, and every reader calls it: `jcctl validate`, `jc-assistant` at load and on every reload of the Endpoint table, the gateway for §2.5, and the Portal's preview (AG-121). Its candidates are the Endpoints the deployment's project may read under Policy, never more:

- the Endpoints of the deployment's own project, every audience on the `internal` channel and `audience: public` alone on every other;
- the `audience: public` Endpoints of the projects in `scope.projects`, on every channel (as MF-52 already requires of a connector).

A selector names no Endpoint, so it cannot add one outside these candidates. `accessLevel` on a channel other than `internal` admits `public` alone, and validation refuses any other value (MF-58). On the `internal` channel the person's own token still decides each call at the gateway (AG-115): resolution bounds what is offered, the token what is read. The output is sorted by Endpoint slug, so the same inputs give the same list. At most 50 Endpoints resolve: `jcctl validate` refuses a deployment above that, naming the count; one that grows past it later is served the first 50 by slug, and the Portal names the rest on the deployment's page (AG-122).

### 2.4 One category list: the EU data themes

The categories are the 13 codes of the EU data-theme table (`AGRI`, `ECON`, `EDUC`, `ENER`, `ENVI`, `GOVE`, `HEAL`, `INTR`, `JUST`, `REGI`, `SOCI`, `TECH`, `TRAN`), the same codes `dcat:theme` carries in every catalogue record (EP-78). A selector names them in `select.themes` (MF-55). A deployment and a source tag themselves with them in `categories`, because a deployment's `theme` already means the chat's look (title, colour, greeting) and `themes` beside it would be misread; the Portal and the public pages label both "Kategórie" / "Categories".

- An Endpoint's themes are those of EP-78: `catalog.themes`, or the classification of its types when that is empty (T-4498). Nothing new is declared on the Endpoint.
- A `KnowledgeSource` and an `AssistantDeployment` gain an optional `categories` (MF-60): the source's for the context page and the selector of a later amendment, the deployment's for display.
- `jc-core` keeps one table of the codes with their labels in sk, en, cs, hu, de, fi and uk (AG-124): the EU Vocabularies labels for the EU languages, a reviewed translation for uk. A code never changes; a label may.
- The CKAN publisher puts each dataset into one CKAN group per theme, named by the lower-case code and titled in the catalogue's language (EP-138), so CKAN's groups and the assistant's categories are one list.

### 2.5 An MCP server per assistant

The gateway serves every enabled deployment at `https://api.{domain}/api/mcp/d/{publicId}` (EP-136): exactly the read tools of the deployment's resolved Endpoints (§2.3), `search_documents` over its knowledge sources when it has one (EP-133, scoped to those sources), and one resource, `context`, holding the context of §2.6. A person adds the address to Claude, ChatGPT or Gemini and gets the reach the assistant has, with their own model.

- A deployment of the `public`, `ckan` or `iframe` channel answers anonymous callers and the tokens of ADR-N-052, and resolves `public` Endpoints alone. Its own `rateLimit` buckets count per caller as on the chat; its model budget is not touched, since the caller's model does the asking.
- An `internal` deployment answers a Keycloak token of a member of the organization, and each call reads with that token (EP-137).
- `enabled: false`, an unknown `publicId` and one two deployments declare answer as an unknown server does (EP-137). The segment `d` is reserved and is never a project name (PF-67 is amended to say so).

### 2.6 The context page

`GET https://assistant.{domain}/api/v1/d/{publicId}/context` answers what the assistant knows, as JSON; `https://assistant.{domain}/d/{publicId}/context` is the same as a page, in the deployment's languages, keyboard and screen-reader operable (AG-123). Both list:

- the deployment's title (`theme.title`), languages, categories and its visitor limits (`perClientPerHour`, `perClientPerDay`, `messagesPerConversation`, `questionChars`);
- per theme, the resolved Endpoints with their title, publisher, entity types, entity count and last update, and their catalogue page;
- the knowledge sources with their kind, sites or catalogue, page and document counts, and last crawl.

The page holds only what a visitor of that channel may read: the resolved list of §2.3, counts computed after it, never the system prompt, the model, the budget in money, a `secretRef`, an internal source, or an Endpoint the visitor's channel does not reach. An `internal` deployment's page answers a signed-in member of the organization alone, through the Portal. The Portal's editor previews the same document before a save, from the manifest being edited (AG-121, T-4693).

### 2.7 Public clients outside the platform

A public assistant's page may live anywhere, on the city's own site in its own design (T-4694). It is a thin client of API/05 §1 and holds nothing else (AG-125):

- it calls only the routes of one `publicId` on `assistant.{domain}`: `challenge`, `token`, `chat`, `feedback` and `context`;
- its origin is one of the deployment's `allowedOrigins`, the only way the chat answers a browser on another host;
- it holds no model key, no ServiceAccount, no secret and no copy of the data; the visitor token lives in memory for the conversation;
- theme, greeting, suggestions, languages and the docked, floating or full-screen mode come from the deployment's `GET …/context` answer and the widget settings already in MF-52, so a change is a Change to the manifest, never a redeploy of the client.

## 3. Security Analysis

| Threat | Control |
|---|---|
| A selector reaches data the project may not read | The resolver starts from the project's candidates (§2.3) and only filters; a selector names no Endpoint. Test: for every selector, the resolution is a subset of the candidates (T-4690). |
| A public assistant resolves an internal Endpoint | Candidates on a non-`internal` channel are `audience: public` alone; `accessLevel` wider than `public` is refused by validation; the gateway checks again per call (EP-136). |
| A second path around the resolver | One function in `jc-core`; the cg query that proves `jc-assistant`, the gateway and the Portal call it is written in T-4690. |
| The context page leaks an Endpoint, a count or a source | It is computed from the resolved list after the bound; internal sources and the prompt never appear; an internal deployment's page sits behind the Portal's login (AG-123). |
| The per-assistant MCP server spends the platform's model budget | It runs no model; the caller's model asks. Its calls count against the deployment's `rateLimit` buckets and the gateway's own (EP-136). |
| A client outside holds a credential | Only the `publicId` and a visitor token that expires with the conversation; `allowedOrigins` limits which page may call the chat (AG-125). |
| A theme label edited into something misleading | Keys are fixed codes; labels live in one reviewed table in `jc-core` (AG-124). |

## 4. Alternatives Considered

1. **A new `AssistantProfile` kind.** Rejected: every field it would hold already lives on `AssistantDeployment`, and two kinds per assistant would need a join rule and two reviews.
2. **Organization-defined categories.** Rejected: the DCAT-AP catalogue, CKAN and national harvesters already use the EU data themes; a second list would need a mapping kept by hand, and its labels would drift.
3. **The model picks Endpoints from the whole catalogue per question.** Rejected: what an assistant may read would depend on a model's choice instead of a reviewed manifest.
4. **The context page from the system prompt.** Rejected: a prompt is prose a reviewer writes; the resolved list is what the assistant reads.
5. **A public client with its own backend holding a service account.** Rejected: a key outside the platform; the chat API with `allowedOrigins` and the visitor token already serves a browser on another host.

## 5. Consequences

- `AssistantDeployment` gains `select`, `exclude` and `categories`; `KnowledgeSource` gains `categories`; the shared `Select` gains `types`, which an McpServer accepts too (MF-58…MF-61). Existing manifests stay valid.
- One resolver in `jc-core` replaces the per-reader connector lists; `jc-assistant` keeps serving the explicit connectors exactly as today.
- The gateway gains `/api/mcp/d/{publicId}`; the assistant gains `/api/v1/d/{publicId}/context` and its page; the Portal's editor gains the selector and the preview (T-4691…T-4693).
- The CKAN theme groups (EP-138) and a source selector by theme are follow-ups outside this group; until EP-138 ships, CKAN shows no groups and the assistants' categories come from the catalogue records alone.

## 6. Requirements

- [Requirements/manifests.md](../Requirements/manifests.md): MF-52 (amended), MF-58…MF-61.
- [Requirements/agents.md](../Requirements/agents.md): AG-121…AG-125.
- [Requirements/endpoints.md](../Requirements/endpoints.md): EP-136…EP-138.
- [Requirements/platform.md](../Requirements/platform.md): PF-67 (amended, the reserved `d`).

## Related

- [ADR-N-040](adr-n-040-knowledge-assistant.md) — the assistant engine this record extends.
- [ADR-N-043 §7](adr-n-043-named-mcp-servers.md#7-amendment-2026-10-17-connector-profiles-t-4504) — the selector grammar reused here.
- [ADR-N-052](adr-n-052-anonymous-oauth-public-mcp.md) — anonymous tokens on the per-assistant MCP server.
- [API/05-knowledge-assistant.md](../API/05-knowledge-assistant.md) — §1.9 the context, §5 the MCP server.
- [Architecture/22-knowledge-assistant.md](../Architecture/22-knowledge-assistant.md) — the two manifest kinds and the channels.
