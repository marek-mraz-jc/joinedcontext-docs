---
sidebar_position: 58
title: "ADR-N-057: Several Rules per Policy, Several Policies per Endpoint, AuthZEN Evaluation and ODRL Input"
---

# ADR-N-057: Several Rules per Policy, Several Policies per Endpoint, AuthZEN Evaluation and ODRL Input

Date: 2026-10-21  
Status: Accepted  
Decision Makers: product owner (2026-10-21: "how does the policy looks like for read everything and updating just one entity from the same endpoint"; "can it be optimatize check open authorization, ODRL, etc.."); recorded by worker-t5035 (T-5035), owner may override

This record changes the authored shape of `Policy` and `Endpoint`. The decision point stays where [ADR-N-050](adr-n-050-broker-views-decide-context-data.md) put it, and the output representations of the access surface ([04-context-spaces-and-endpoints](../Architecture/04-context-spaces-and-endpoints.md)) stay as they are.

## 1. Context

On platform main `d8a5697e` a `Policy` carries one rule: one `assignee`, one `operations` list, one `information` list and one set of residual constraints ([03-domain-model](../Architecture/03-domain-model.md#policy)). An `Endpoint` evaluates the one Policy its `policyRef` names or, without one, every Policy of its space (`crates/context-gateway/src/store.rs` `bound_policy`; the Portal's `reconciler/views.rs` `bound` agrees).

The owner's case, "the public reads everything and one account updates one entity on the same Endpoint", needs two Policies. One `policyRef` cannot name two, so the Endpoint must drop `policyRef` and then evaluates every Policy of the space, including each one written later. The narrowing that `policyRef` gave is lost.

The reverse failure happened on dev: the bbsk podujatia pipelines (T-5033) wrote through `bbsk-podujatia-slovensko`, whose `policyRef` binds only the public read Policy. Each pipeline's derived write Policy (PL-20) was bound by no Endpoint, every upsert answered 404, and `jcctl validate` said nothing.

The output side already speaks the standards: `…/access` serves an AuthZEN-shaped permissions document, ODRL 2.2 in the `ngsi-ld:` profile and a UCAST grant AST; `POST …/access/check` answers one AuthZEN-shaped decision ([API/02](../API/02-endpoint-representations.md), R51, R52).

## 2. Comparison

| Concept | ODRL 2.2 | AuthZEN Authorization API 1.0 | Cedar, XACML 3.0 | Ours today |
|---|---|---|---|---|
| Rules in one policy | `permission[]`, `prohibition[]`, `obligation[]` | not a policy language | Cedar: one statement per policy, many per set; XACML: `Rule` in `Policy` | one rule per `Policy` |
| Conflict | `conflict`: `perm`, `prohibit` or `invalid` | not defined | Cedar: `forbid` wins; XACML: combining algorithm, e.g. deny-overrides | a prohibition wins (GW4), default deny (GW5) |
| Policy types | `Set`, `Offer`, `Agreement` | none | none | grants are a `Set`; the catalogue offer is an `Offer` (EP-69) |
| Who | `assignee`, `assigner`, party refinement | `subject {type, id, properties}` | principal | `assignee`, `assigner` |
| What | `target` with asset refinement | `resource {type, id, properties}` | resource | `information[]` (types, ids, attributes) |
| Action | `action` with refinement | `action {name, properties}` | action | CIM 009 `operations`, platform `actions` |
| Conditions | `constraint[]` (leftOperand, operator, rightOperand) | `context` | Cedar `when`/`unless`; XACML `Condition` | `q`, `scopeQ`, `geoQ`, `temporalQ`, `validity` |
| Duties | `duty` on a permission | none | XACML obligations and advice | the offer's duties (attribution, EP-57) |
| Decision call | none | `POST /access/v1/evaluation`, `/evaluations` (batch), `/search/{subject,resource,action}` | Cedar `isAuthorized`; XACML request/response | `POST …/access/check` (single), `GET …/access` (whole grant) |

Gaps: a Policy holds one rule where ODRL and Cedar hold many; an Endpoint binds one Policy or all of them, where ODRL lets an offer name several; there is no batch decision, so a page that filters ten dropdowns asks ten times; and ODRL is an output only, so a partner's ODRL Set cannot become a Policy without hand translation. Our conflict rule already equals ODRL's `prohibit` and Cedar's `forbid`; nothing changes there.

## 3. Decision

1. **A Policy holds `rules[]`** (T-5036). Each rule carries `effect` (default `permission`), `assignee`, `operations`, `actions`, `information` and the residual constraints `q`, `scopeQ`, `geoQ`, `temporalQ`; `assigner`, `contextSpaceRef` and `validity` stay on the Policy. The single-rule shape stays valid and means a `rules[]` of one; a Policy with both shapes, or with an empty `rules[]`, is refused when validated. Every rule is its own grant in the PDP, explained as `{policy}#{n}` by `access/simulate` (EP-103). ODRL renders each permission rule as one `permission[]` entry and each prohibition rule as one `prohibition[]` entry of the same `Set`, with `conflict: prohibit`. The owner's case becomes one Policy:

   ```yaml
   kind: Policy
   metadata: { name: kiosks, namespace: bbsk }
   spec:
     contextSpaceRef: { kind: ContextSpace, name: kiosks }
     assigner: did:web:bbsk.sk
     rules:
       - assignee: { kind: role, id: public }
         operations: [retrieveOps]
       - assignee: { kind: serviceAccount, id: kiosk-editor }
         operations: [updateAttrs]
         information:
           - entities: [{ type: Kiosk, id: "urn:ngsi-ld:Kiosk:bbsk.sk:kiosks:hlavne-namestie" }]
   ```

2. **An Endpoint names `policyRefs[]`** (T-5037). The Endpoint evaluates exactly the Policies listed, in any order; `policyRef: X` stays valid and means `policyRefs: [X]`. Both fields together, or an empty list, are refused, because an empty list would read either as "nothing" or as "everything". Without either field the Endpoint still evaluates every Policy of its space. The derived Policies of a Pipeline (PL-20) are no files, so no reference can name them; a Pipeline writes through an Endpoint without references, as T-5033 set up for bbsk.

3. **AuthZEN evaluation on each Endpoint** (T-5038). The gateway answers `POST /api/endpoint/{endpointSlug}/access/v1/evaluation` and `POST …/access/v1/evaluations` with AuthZEN 1.0 request and response bodies, decided by the same view and engine as a real request (EP-06 parity); `access/check` stays as the single-decision alias. `evaluations` takes up to 100 items with the `execute_all` semantic, so a form asks once for every dropdown option it shows and the server checks the submitted value again. The subject is always the caller's token: a request whose `subject` names anyone else answers 403, and only `access/simulate` (EP-103) evaluates another subject. The AuthZEN search APIs are not adopted: `GET …/access` already answers "what may I reach" as a whole.

4. **ODRL JSON-LD as manifest input** (T-5039). `jcctl policy import` and the Portal's Policy form read an ODRL 2.2 `Set` in the `ngsi-ld:` profile and write the Policy manifest; the YAML file stays the only source (config as code). SHACL shapes of the profile validate the input first. Anything the profile does not map (a duty on a grant, an unknown `leftOperand`, a `conflict` other than `prohibit`, an `Offer` or `Agreement`) is refused with the member named, never dropped. A round-trip test holds that every seeded Policy rendered to ODRL imports back to the same manifest.

5. **`jcctl validate` refuses a write nobody can make** (T-5035, this task). It reports as errors (a) every permission that grants a write operation and is bound by no Endpoint of its project, and (b) every Pipeline output whose `targetEndpoint` does not exist in the Pipeline's project or does not bind that output's derived write Policy. Binding follows the gateway's rule: same space, and the Endpoint names the Policy by reference or names none, and an App's generated Endpoint takes only its own grants and the prohibitions. Both are errors, not warnings, because `validate` is the CI gate of every deployment repository and a warning nobody read is how the bbsk defect reached dev. The Portal's change review runs the same check on a proposal (T-5040).

## 4. Performance Budgets

The owner asked on 2026-10-21 that these Endpoints stay fast. On dev from the swarm host, `…/access` answered in 113-127 ms and an NGSI-LD query of 10 or 100 entities in 119-131 ms, of which an edge 404 already takes 106 ms; the server side is about 5-20 ms. Each change of section 3 holds these budgets, measured before and after (T-5042):

| Measure | Budget |
|---|---|
| PDP decision in process, 50 Policies of 5 rules on one space | p99 < 1 ms (criterion bench in ci-full, fails on a 20 % regression) |
| `…/access`, server time | p95 < 20 ms |
| `…/access/v1/evaluations` with 100 items, server time | p95 < 30 ms |
| an NGSI-LD or OGC read through a Policy with `idPattern`, `q` and `geoQ` | within 10 % of the same read without residual constraints |

The k6 script runs against dev at 1, 10 and 50 concurrent clients, never the full ETS, and against production only inside the night window of T-4877, read-only. A read over 200 ms p95 becomes its own task.

## 5. Security

- Deny by default holds per rule: a rule grants only what it lists, and a Policy whose rules grant nothing grants nothing.
- A prohibition rule wins over every permission of every Policy an Endpoint binds, wherever it is written, which is ODRL's `conflict: prohibit` and today's GW4.
- `policyRefs[]` narrows exactly as `policyRef` does: a reference to a Policy of another space or domain binds nothing and is logged, as today.
- The AuthZEN calls disclose no more than `…/access`: a decision about the caller alone, no Policy names, and a denied type answers `false`, not why (R20).
- ODRL input cannot widen a grant: what does not map is refused.

## 6. Alternatives Considered

- **Keep one rule per Policy and allow several `policyRef` only.** Rejected: the owner's case then needs two files that change together and one review per file.
- **Adopt Cedar as the policy language.** Rejected: a second language beside the NGSI-LD query strings the broker's engine already evaluates (EP-56), and Cedar has no geo or temporal operand.
- **Lint as a warning, an error only with a strict flag.** Rejected: the bbsk seed passed CI with a warning-free run; a second mode is a second behaviour to test.
- **Bind a Pipeline's derived Policies past `policyRef`.** Rejected in T-5033: a public read Endpoint would then list writes.

## 7. Consequences

- jc-core's `PolicySpec` gains `rules`, `EndpointSpec` gains `policyRefs`; the gateway, the broker's view compiler and the Portal read the normalized list, so each has one code path.
- The access documents of §1b gain one entry per rule; consumers of the AuthZEN and ODRL shapes see no new member.
- Seed repositories pass `jcctl validate` unchanged after T-5033; a repository with a write Policy no Endpoint binds fails until the Endpoint or the Policy is fixed.

## 8. Requirements

- **EP-14**, **GW4**, **GW5**, **GW8**: binding and conflict, unchanged in meaning.
- **EP-117**: the shape of every `policyRefs` entry, and the refusal of both fields or an empty list.
- **R51**, **R52**, **EP-06**, **EP-103**: the AuthZEN and ODRL shapes and their parity.
- **PL-19**, **PL-20**: the derived write Policy the lint follows.
- **PL-111**: the lint of decision 5.

## Related

- [ADR-N-050](adr-n-050-broker-views-decide-context-data.md) — the decision point the rules compile into.
- [03-domain-model](../Architecture/03-domain-model.md#policy) — the Policy manifest.
- [04-context-spaces-and-endpoints](../Architecture/04-context-spaces-and-endpoints.md) — the access representations.
- [00-register](00-register.md) — all decisions and their status.
