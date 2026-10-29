---
sidebar_position: 5
title: Data Protection Impact Assessment for AI Connectors
description: What personal data an AI client reaches through a connector, who receives it, how long it is kept, which controls bound it and how a data subject's rights are answered.
---

# Data Protection Impact Assessment for AI Connectors

The assessment a data protection officer reads before the organization lets people connect claude.ai, Claude Desktop, Claude Code, ChatGPT or the Portal assistant to the platform (GDPR Art. 35). It covers the processing a connector adds: an answer the platform sends to an AI client, which the client passes to a model its vendor runs. Fill in the bracketed parts for your organization, keep the filled copy with your records of processing, and repeat the assessment when section 9 says so.

## 1. The processing

A person creates a connector on the My connectors page ([API/14](../API/14-connectors.md)), adds its address to an AI client and signs in. From then on the client calls the connector's tools: it lists and reads manifests of the projects the connector names, and reads entities of their Endpoints. Each answer leaves the platform for the client's vendor, where a model reads it beside the person's prompt.

| Item | Value |
|---|---|
| Controller | [the organization that runs the platform] |
| Platform operator | [the team or contractor that runs the cluster] |
| Data subjects | the person who uses the connector; people whose data sits in an Endpoint the connector reads (citizens who reported something, applicants, staff) |
| Systems | the Portal (connector check at `/c/{id}`), the Context Gateway, the broker, the AI client and the vendor's model service |
| Volume | one answer per tool call, at most 1,000 entities per page |

## 2. Purposes and legal basis

| Purpose | Legal basis | Note |
|---|---|---|
| Let a person work with the platform's data and configuration through an AI client of their choice | Art. 6(1)(e) for a public body's task, or 6(1)(f) for a company: [state which] | the connector does what the person may do in the Portal, never more |
| Keep an audit of every connector call | Art. 6(1)(c) or (e), security of processing (Art. 32) | identifiers only, section 5 |

A purpose recorded on a class of the model (`purpose`, `legalBasis`, `maxRetention`, Architecture/11 §9) is the purpose of that data. An AI client reading it is a further use: tick a connector's `personalData` only when that use fits the recorded purpose.

## 3. What reaches the AI client

| Data | Reaches the client | Control |
|---|---|---|
| Attributes the model marks `personalData` (an e-mail, a name, a phone number of a citizen) | no, by default | the connector check removes them from every answer and names what it removed (AG-158) |
| The same attributes, with `personalData` ticked on a scope item | yes, for that item's project or Endpoint | the tick needs a DelegationPolicy with `personalData: true`, written by an organization administrator |
| Other entity attributes, manifests, model files | yes, within the connector's scope | scope, segments, expiry and the person's live rights decide each call (AG-144) |
| Secrets | no | manifests carry `secretRef` names only (AG-155) |
| The person's name, e-mail and sign-in | the vendor holds the person's own account; the platform sends the Keycloak user id in no answer | |

A model marks nothing by itself. Before you allow connectors on a project, list the classes that hold personal data and check that each carries the annotation; in the project's repository the models that mark something are:

```bash
grep -rln "personalData" --include="*.linkml.yaml" .
```

A slot that holds personal data without the mark goes to the AI client like any other value.

## 4. Recipients and processors

| Recipient | When | Role under the GDPR | What to check |
|---|---|---|---|
| Anthropic (claude.ai, Claude Desktop, Claude Code) | a person connects one of them | processor under a business plan with a data processing addendum; under a consumer plan the vendor's own terms apply | an organization plan with a DPA; whether conversations train models; the vendor's retention setting; the transfer mechanism to the US |
| OpenAI (ChatGPT) | a person connects ChatGPT | processor under a business plan with a DPA; under a consumer plan the vendor's own terms apply | the same as above |
| The model provider of the Portal assistant | the assistant reads data for a conversation | processor of the platform operator, reached through `jc-agent-proxy` with the deployment's key | the provider named in the deployment ([Architecture/19](../Architecture/19-agent-runner.md)) and its DPA |

Decide which clients the organization allows and put them in each DelegationPolicy's `allowedClients`: claude.ai and ChatGPT bind by their published client ids; Claude Code cannot be bound (AG-153), so allow it only where the people who use it are covered by the vendor's business terms.

## 5. Retention

| Where | What | How long |
|---|---|---|
| Portal database | the connector record (owner, name, scope, expiry) | until the owner revokes or the person is removed; a revoked record is kept for the audit |
| Portal database | one audit row per call: connector, person, client, tool, target, verdict, duration; never a value, a withheld name or a token | 30 days |
| Portal memory | the answer | the length of the call; nothing is stored |
| The vendor | the conversation with the answer in it | the vendor's setting for the plan: [fill in per vendor] |

## 6. Controls that bound the risk

- Deny by default: the organization default ceiling is `data-read`, reads only, 30 days, no `personalData` (AG-150).
- Minimisation: attributes marked `personalData` leave every answer unless a ticked item allows them; an answer whose models cannot be read is refused (AG-158).
- Rights read live: every call rechecks the owner's bindings, so a role the person lost or a revoked connector holds from the next call (AG-144).
- Writes are plans a person approves in the Portal; a read-only connector cannot write below the tools (AG-148, AG-149).
- Entity text reaches the model inside an untrusted-data fence, so a value in the data is not read as an instruction (AG-20).
- Calls are limited per connector and person (AG-156) and audited without values (AG-147).

## 7. The data subjects' rights

| Right | How it is answered |
|---|---|
| Information (Art. 13, 14) | the privacy notice of the service that collects the data names AI clients as recipients when a project allows the tick; this page is the source for that text |
| Access and portability (Art. 15, 20) | the space owner runs the export ([API/01 §46](../API/01-portal-api.md#46-personal-data-of-a-space-dm-124dm-127-dm-142)) |
| Erasure and rectification (Art. 16, 17) | the space owner runs the erasure on the platform; copies a vendor holds in a person's conversations are outside it, so the controller asks the vendor under its DPA, and the person who ran the conversation deletes it |
| Objection (Art. 21) | an organization administrator removes `personalData: true` from the DelegationPolicy; the next call through every connector of the people it names answers without the attributes |
| The connector user's own rights | the person reads their connectors and each call on the My connectors page and revokes any of them |

## 8. Risks

| Risk | Likelihood after the controls | Severity | Residual measure |
|---|---|---|---|
| A citizen's contact data ends up in a vendor's logs or training data | low: off by default, an administrator allows it per group | high | allow the tick only for business plans with training off; list the groups in the DelegationPolicy |
| A slot holds personal data without the mark | medium on imported models | high | the grep in section 3 before a project gets connectors; the model review |
| A person pastes an answer into another tool | possible | medium | the person's own duty as staff; the audit shows which data they read |
| A vendor stores conversations longer than the purpose needs | depends on the plan | medium | the plan's retention setting, recorded in section 5 |

[Conclusion: whether the residual risk is acceptable, signed by the data protection officer, with the date.]

## 9. When to assess again

- A new AI client or model provider is allowed.
- A DelegationPolicy starts allowing `personalData` for a group.
- A project with special category data (Art. 9) gets connectors.
- A vendor changes its retention or training terms.
- Every year, with the routine reviews of [Operations/03 §5](03-governance.md#5-routine-reviews).

## Related

- [API/14 §4.6](../API/14-connectors.md#46-personal-data-in-answers): how the connector check withholds personal attributes.
- [Architecture/11 §9](../Architecture/11-data-models.md#9-personal-data-in-a-model): the `personalData` annotation and the other privacy marks of a model.
- [Decisions/adr-n-064](../Decisions/adr-n-064-scoped-connectors.md): scoped connectors and their threat model.
- [User-Guide/21](../User-Guide/21-connect-ai-clients.md): the page a person follows to connect a client.
