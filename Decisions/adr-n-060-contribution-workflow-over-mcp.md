---
sidebar_position: 61
title: "ADR-N-060: The Contribution Workflow for People Improving the Platform over MCP"
---

# ADR-N-060: The Contribution Workflow for People Improving the Platform over MCP

Date: 2026-10-24  
Status: Proposed  
Decision Makers: product owner (2026-10-24: "a few of them will have an MCP connector to this platform and try to improve this platform"); drafted by worker-t5545 (T-5545), owner may override

This record amends AG-17, AG-18 and AG-82 ([Requirements/agents.md](../Requirements/agents.md)), adds AG-137 to AG-141, and extends [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) (one registry behind every door), [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md) (workspaces) and [ADR-N-035](adr-n-035-organization-policies-and-limits.md) (Organization policies and limits).

## 1. Context

An employee with an MCP connector ([Architecture/07 §1](../Architecture/07-agents-and-mcp.md#1-dual-mcp-surfaces)) can "improve the platform" in two senses the documentation did not separate:

1. **The configuration of their project**: Endpoints, Policies, spaces, pipelines, models. The Portal MCP offers this through the operation registry.
2. **The platform's own code or behaviour**: a missing feature, a confusing page, a slow query. The only path is the Portal's feedback form (API/01 §38), kept without an author.

Measured read-only on portal `origin/main` b6273ddb (the lines are the same as on bc0e8158, where the task measured them) and platform `origin/main` 2281f692:

| # | What the code does today | Where |
|---|---|---|
| E1 | Each `jc_*_propose` operation opens one Change per resource. The registry's proposals (`mutate_manifest`) take no workspace, so an MCP proposal always targets `main`. | portal `src/ops/proposals.rs:199`, `src/api/mutate.rs:462` `propose`, `:689` `propose_gated` |
| E2 | Only the REST doors write into a workspace branch (`?workspace=`). An MCP client can open a workspace, keep drafts in it, compare it and preview it, but no operation commits a draft onto the branch. | `src/api/mutate.rs:707` `propose_gated_in`, `:1088-1097`; `src/api/delete.rs:572`; drafts per workspace `src/ops/drafts.rs:1026` |
| E3 | An MCP client never brings a workspace back or discards it (AG-82), and never approves (AG-11). The tools are not offered. | `src/ops/workspaces.rs:1327-1355`, `src/ops/mod.rs:140-144`, `src/ops/resources.rs:398-402` |
| E4 | A Change opened over MCP looks like a person's: title `"{op} {kind} {name}"`, body "via joinedcontext Portal". `ChangeStatus` holds lane, repository, merge request, plan and phase only. Commits carry the person's name and e-mail. | `src/api/mutate.rs:1211-1215`, `src/change.rs:73-83`, `src/api/mutate.rs:402-418` |
| E5 | AG-17 (agent as author) and AG-18 (`Co-Proposed-By`) hold only for agent runs, in the agent proxy. | platform `crates/agent-proxy/src/routes/forge.rs:95-110` |
| E6 | The channel is recorded only on a draft (`touched_kind` `mcp`) and in activity (`mcp.tool`). | portal `src/ops/mod.rs:71-80` |
| E7 | Feedback is anonymous, 10 per person per hour, with no link to a Change. | `src/api/feedback.rs:1-3`, `:33` |
| E8 | One MCP subject may make 120 calls a minute (a constant). No limit bounds open Changes or open workspaces per person; a workspace lives at most 14 days. | `src/mcp/mod.rs:55`, `src/ops/workspaces.rs:20` |

The walkthrough T-5538 ran the protocol half on dev and added two findings this record relies on. The REST API accepts the connector's token (`azp` `mcp-mobile`) as a person, so an AI client reaches the bring-back route that MCP refuses (T-5610). MCP calls leave no activity row an approver can find (T-5609). Its step 5 opened no workspace and the person's part waits on T-5612, so the counts in §3 come from the code path.

## 2. Decision

### 2.1 A contribution of more than one resource is a workspace, and the agent asks for review

1. A registry proposal (`jc_resource_propose`, `jc_endpoint_propose` and the other `jc_*_propose` operations) takes an optional `workspace`. With it, the proposal commits onto the workspace branch through the same engine as the REST `?workspace=` door (`propose_gated_in`): the same verdict gate (PF-57), the same `within_workspace` check (CC-76), the same owner check. A write inside a workspace changes nothing on `main`, so it runs in the Green lane and asks no elicitation; the decision the person makes is at the bring-back.
2. A new operation `jc_workspace_request_review` (Green, not destructive) records a review request on the workspace: the head commit of its branch, the comparison digest, a summary of at most 500 characters, and the client that sent it. It opens no Change. The Portal notifies the workspace owner: the bell, and e-mail when the person opted in.
3. The notification opens the workspace's comparison with **Bring back** as its primary action. The person's click calls the existing bring-back (`workspaces::propose`) as `Via::Session`. The request pins the head commit: if the branch moved after the request, the button is replaced by "The copy changed after the request: compare again", so the person brings back exactly what they read.
4. The agent still never brings back, discards or approves (AG-82, AG-11). `refuse_agent_bring_back` and `refuse_agent_decision` stay as they are. The REST doors decide `Via` from the token's client, not from the transport, so the connector's token is `Via::Mcp` on every route (T-5610).

A single-resource proposal keeps today's path: one Change on `main`, one elicitation.

### 2.2 A Change records its channel and client

1. A Change carries `proposedVia: {channel, client}`. `channel` is `person` (the Portal session or the person's own bearer token), `mcp` (a token issued to an MCP connector client) or `agent` (an agent or assistant run, `Via::Agent`). `client` is the OAuth client id, plus the display name the client registered when it has one. A registered name is self-asserted: the Portal stores at most 64 printable characters, renders it as text, and always shows the client id beside it.
2. The approver sees it on the Change page, in the approvals list and in the notification: a badge "Proposed with an AI client (claude.ai, client `mcp-mobile`)". A bring-back from a review request (§2.1) carries `channel: mcp` with the client of the request, even though the person clicked.
3. Commits keep the person as author for `person` and `mcp`: the person confirmed the proposal (AG-63) or clicked the bring-back, and answers for it. The Portal adds a trailer:

   ```text
   Update Endpoint helsinki-bikes-ops

   Proposed-Via: mcp; client=mcp-mobile; name=claude.ai
   ```

4. An agent run keeps AG-17 and AG-18 as the agent proxy does today: author `agent:{agent}@{project}`, trailer `Co-Proposed-By: {person}`. The pull request body names the channel in its first line for every channel.

### 2.3 Who may contribute over MCP

`spec.policies.agents.mcp.propose` on the Organization (ADR-N-035) lists the Roles whose holders may propose over MCP. Absent, it is every Role that may propose in the Portal. `spec.policies.agents.mcp.projects.{project}.propose` narrows it for one project; an empty list stops MCP proposals there. The setting only narrows: a person still needs `propose` on the kind through their own bindings, so it never grants a right. Reads over MCP are not affected.

```yaml
spec:
  policies:
    agents:
      mcp:
        propose: [project-admin, endpoint-editor]
        projects:
          finance:
            propose: []
```

A refused proposal answers 403 naming `spec.policies.agents.mcp.propose` and the person's Roles, and `tools/list` leaves the proposal tools out for that person (with T-5608).

### 2.4 Contributions to the platform's behaviour

Feedback (API/01 §38) gains two optional fields, and a registry operation:

1. `signed: true` keeps the person's subject and display name with the feedback, visible to the organization's administrators only. Absent or `false` keeps today's anonymous record.
2. `changeRef` names a Change that showed the need. The Portal checks that the person may read it, else 422 naming `changeRef`; the administrators' list links to it.
3. `jc_feedback_send` sends feedback over MCP. It is Yellow: the elicitation shows the person the exact text before it leaves, because a model wrote it. It records `channel: mcp` and the client, and counts against the person's feedback limit (§2.5).

Feedback stays untrusted text that reaches the board as a blocked proposed task (API/01 §38). No agent takes it as work by itself.

### 2.5 Limits per contributor

`spec.limits.contributions` (ADR-N-035 catalogue, per person across every channel):

| Field | Default | Operator ceiling | Enforced by |
|---|---|---|---|
| `openChangesPerPerson` | 20 | 200 | every propose door, 429 naming the field |
| `openWorkspacesPerPerson` | 5 | 50 | `jc_workspace_open` and `POST .../workspaces`, 429 |
| `mcpCallsPerMinute` | 120 | 1200 | the Portal MCP route (replaces `MAX_CALLS_PER_MINUTE`) |
| `reviewRequestsPerDay` | 20 | 200 | `jc_workspace_request_review` |
| `feedbackPerHour` | 10 | 100 | `POST /api/v1/feedback`, `jc_feedback_send` (replaces `PER_HOUR`) |

A connector in a loop can then open at most 20 Changes and 5 workspaces in the person's name before a person closes some, and the approver's list stays readable.

## 3. Steps and Clicks: a Two-Resource Contribution from MCP to Applied

Counted from the code path on portal b6273ddb: an Endpoint and its Policy in one project, both Yellow. A "click" is one action of a person in the client or the Portal; the approver may be the same person or another.

| Path | MCP calls | Contributor clicks | Approver clicks | Changes | Atomic |
|---|---|---|---|---|---|
| Today A: two proposals on `main` | 4: each proposal asked, then answered | 2 confirmations | 4: open and approve each Change | 2 | no: the first can apply alone |
| Today B: a workspace (AG-82) | 5: open, `jc_draft_put` x2 into the workspace, compare, preview, and the branch is still empty (E2) | 9: open the workspace, open and save each draft into it (4), compare, **Bring back**, confirm, plus the hand-over by chat | 2 | 1 | yes |
| After this record | 6: open, `jc_*_propose` x2 with `workspace` (Green), compare, preview, `jc_workspace_request_review` | 2: open the notification, **Bring back** | 2 | 1 | yes |

After the decision a contribution takes 4 clicks from both people instead of 6 (path A) or 11 (path B), reaches the approver as one Change marked as AI-proposed, and the contributor reviews the whole comparison before anything reaches `main`.

## 4. Consequences

- The MCP door gains one write path (into a workspace branch) without gaining a decision: nothing an MCP client does reaches `main` until a person clicks, and approval stays with a person (AG-11, AG-133).
- An approver can tell a person's Change from an AI client's on every surface, and Git history keeps it in the trailer.
- An Organization can keep MCP to reading, or to some Roles or projects, without touching bindings.
- The feedback list can carry a name and a Change when the person wants that, and stays anonymous by default.
- Three constants move into Organization limits; the defaults equal today's values, so an installation that sets nothing behaves as before, apart from the new open-Change and workspace caps.

## 5. Options Considered

1. **Let an MCP client bring a workspace back after an elicitation.** Rejected: AG-82 and the owner decision of T-1005 keep both ways out of a workspace with a person, and an elicitation answered in a model's chat is weaker than a click on the comparison itself.
2. **Batch proposals: one Change holding several resources, proposed directly over MCP.** Rejected: it duplicates the workspace (one branch, one Change) without the comparison and preview a person reviews.
3. **Make the MCP client the commit author (AG-17 as for agent runs).** Rejected: the connector has no identity of its own (one shared client, self-asserted names), and the person confirmed each proposal. The trailer and `proposedVia` attribute the channel without moving accountability off the person.
4. **A per-person MCP opt-in instead of a Role list.** Rejected: an administrator needs one place to see who can propose over MCP; a Role list in `spec.policies` is that place and goes through a Change itself.

## 6. Code Follow-ups (for the owner to admit)

| # | Change | Where |
|---|---|---|
| F1 | `workspace` argument on the registry proposals, routed to `propose_gated_in`; Green inside a workspace | portal `src/ops/proposals.rs:199` `mutate_manifest`, `:695` `propose_with_optional_draft`; `src/ops/resources.rs:453` |
| F2 | `jc_workspace_request_review`, the review request record (head commit, digest, client), the notification and the stale-head refusal | portal `src/ops/workspaces.rs:1776` beside `jc_workspace_propose`; UI workspace comparison page |
| F3 | `Via` from the token's client on REST | portal `src/ops/mod.rs:63-80`; existing task T-5610 |
| F4 | `proposedVia` on the Change, the badge, the PR body and the `Proposed-Via` trailer | portal `src/change.rs:73`, `src/api/mutate.rs:1211-1215`, `:402` `author_credentials`; existing task T-5609 |
| F5 | `spec.policies.agents.mcp` in jc-core and its check on every MCP proposal and in `tools/list` | platform `crates/jc-core/src/kinds/org_settings.rs` `AgentsPolicy`; portal `src/mcp/mod.rs:651-656`; with T-5608 |
| F6 | `signed`, `changeRef` and `jc_feedback_send` | portal `src/api/feedback.rs`, API/01 §38 |
| F7 | `spec.limits.contributions` and the five checks | platform `org_settings.rs` `OrganizationLimits`; portal `src/mcp/mod.rs:55`, `src/api/feedback.rs:33`, `src/ops/workspaces.rs` open, the propose doors |
| F8 | The walkthrough's step 5 with a person, which measures §3 on dev | T-5612 |

## Related

- [Architecture/07 §10](../Architecture/07-agents-and-mcp.md#10-contribution-workflow) — the workflow as built on this record.
- [ADR-N-021](adr-n-021-one-operation-registry-behind-ui-api-assistant-and-mcp.md) — the operation registry every door shares.
- [ADR-N-024](adr-n-024-workspaces-branch-and-preview.md) — workspaces, their branch and preview.
- [ADR-N-035](adr-n-035-organization-policies-and-limits.md) — Organization policies and limits.
- [Requirements/agents.md](../Requirements/agents.md) — AG-17, AG-18, AG-82 and AG-137 to AG-141.
