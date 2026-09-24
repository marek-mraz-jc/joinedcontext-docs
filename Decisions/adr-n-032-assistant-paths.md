---
sidebar_position: 33
title: "ADR-N-032: The Assistant Starts from Paths the Person Picks"
---

# ADR-N-032: The Assistant Starts from Paths the Person Picks

Date: 2026-09-24  
Status: Accepted  
Decision Makers: product owner (decisions of 2026-09-24)

## 1. Context

The owner's direction of 2026-09-24: the empty assistant's example prompts "need to all just be options", the agents "should be able to choose their path", and choosing "Integrate pipeline" should make the agent "ask for data, or upload data, and automatically navigate in the UI, and be fast". Today the empty assistant offers three example sentences and "Generate your own app". A sentence starts a free conversation whose first answer waits for the model.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Built on what exists: the assistant's `navigate` event and prefill, LinkML `imports`, the shared pickers. |
| Technological consistency | **Full** | One propose function, one model format, one picker per kind. |
| Security by design | **Full** | Nothing widens a role; every write stays a Change the person sends; pickers list only what the caller may read. |
| Modular design | **Full** | Paths, steps and pickers are separate, testable parts. |
| Multi-tenancy | **Full** | Every list is filtered by the caller's read permission. |

## 3. Decision

1. **Paths.** The empty assistant lists the paths as options, each with an icon and one line: Integrate a pipeline, Upload data, Find data, Share data, Build an app, Build a dashboard, Create a data model and Define a KPI. A path the person's role cannot carry out is disabled with the reason (UI-44). The composer stays: the agent routes free text to a path with one short `choose_path` step, names the path it took and offers to switch.
2. **A path is a guided flow.** Each step is one of three things:
   - a question with options, plus free text;
   - a request for data: upload a file, give a URL, or pick a space or an Endpoint;
   - an action.

   The agent opens the page a step works on (the `navigate` event with its prefill), so the person watches the form fill.
3. **The agent chooses the next step.** Each path has its own tool set, narrowed to what the path needs. The agent picks the next step from the answers so far and may hand over to another path, which it tells the person.
4. **Fast.** A path's first step is deterministic, with no model call, and answers in under 300 ms. A step that needs the model streams its first token in under 2 s, and profiling an upload of up to 10 MB takes under 3 s. Every step event carries `elapsedMs`, and a live journey asserts the budgets.
5. **Nothing changes without the person.** A flow ends at "Review and propose" on the page it filled (AG-73).

## 4. Alternatives Considered

- **Keep example sentences.** They start conversations the person did not choose and make the first answer wait for the model.
- **A wizard without an agent.** A fixed form cannot adapt to the data it is given. The agent picks the next step inside the path.

## 5. Consequences

- New requirements AG-87…AG-91. Architecture/19 and Architecture/09 describe the dock.
- Work: T-2692…T-2697 and T-2703.

## Related

- [Requirements/agents](../Requirements/agents.md#assistant-paths) — AG-87…AG-91.
- [ADR-N-033](adr-n-033-one-data-model-per-space.md) — the pickers the steps use.
