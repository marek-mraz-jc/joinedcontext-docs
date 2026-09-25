---
sidebar_position: 7
title: Security Testing & Penetration Verification
description: The scans, the policy-bypass suites, the agent and proxy isolation checks, and the attack register that gates the first production apply.
---

# Security Testing & Penetration Verification

This page is for whoever has to show that a defence holds: which suite replays which attack, what it asserts, and what is still unproven. The register in section 6 is the gate on the first production apply, and `tasks/compliance gate` is what reads it. Read off the code on 2026-09-20.

---

## 1. Scans in the lanes

| Scan | Where it runs | What fails it |
|---|---|---|
| `gitleaks` | the fast lane of every repository, over the whole history | a private key, a high-entropy secret, an OAuth client secret |
| `scripts/check-rendered-secrets.py`, `scripts/check-secrets.py`, `gitleaks` over the render | the deployment fast lane, per environment | a secret that appears in a rendered manifest rather than behind a `secretRef` |
| `cargo audit` | the hourly `ci-full` of both Rust repositories | a crate with a published RustSec advisory |
| `cargo deny check advisories bans licenses sources` | the same lane | an unapproved licence, a banned duplicate, an unknown source |
| Trivy filesystem | the same lane | a CRITICAL or HIGH vulnerability in the tree |
| Trivy on the image | `image.yml`, before the image is published | the same, in the image that would be deployed |
| `scripts/ci/check-workflow-pins.py` | the fast lane of the platform and the Portal | an action that is not pinned to a commit, or a job holding publish permissions it does not need |

Images are signed by digest in `image.yml` and a bill of materials is uploaded beside them. `pnpm audit` and `npm audit` run nowhere: [TS-24](../Requirements/testing.md) asks for them and they are open.

---

## 2. Policy bypass and privilege escalation

Every attack of this kind is a permanent case, in the crate that enforces the rule or in the conformance suite that replays it against a deployment.

| Attack | Asserted in |
|---|---|
| a caller reads a space their grants do not reach | `crates/context-gateway/tests/edge_app_space_record_tests.rs`, `tests/security/test_tenant_isolation.py` |
| a caller widens what a Policy allows | `crates/context-gateway/tests/attack_policy_widening_tests.rs`, `tests/security/test_policy_bypass.py` |
| an entity id or tenant header of another space | `crates/context-gateway/tests/attack_foreign_space_ids_tests.rs`, `tests/security/test_tenancy_injection.py` |
| a grant that narrows is applied silently and the caller is not told | `tests/security/test_silent_narrowing.py` |
| one representation shows what another hides | `tests/security/test_representation_parity.py` |
| a token from the wrong realm, client, audience or algorithm | `crates/context-gateway/tests/attack_identity_token_tests.rs` |
| notifications as an amplifier or a way out | `crates/context-gateway/tests/attack_notification_amplifier_tests.rs`, `attack_notification_targets_tests.rs` |
| a file or bulk surface as a resource bomb | `crates/context-gateway/tests/attack_resource_bomb_tests.rs` |
| the edge as the decision point instead of the enforcement point | `joinedcontext-deployment/tests/test_edge_attack_surface.py` |

### An existing resource the caller may not read

The gateway answers the `404` a resource nobody created answers, byte for byte: the same status, the same media type and the same body ([R20](../Requirements/access-control.md#5-requesting-extra-data)). A `403` would confirm that the name is real, and that is the whole attack. The case that proves it takes the answer for a name nobody created as its baseline and asserts every other spelling equal to it.

### A query that crosses two grants

A caller holding one grant on a scope and another grant on a different attribute cannot combine them: the rewritten query narrows to each grant on its own, and the cross product is never served ([R57](../Requirements/policy-firewall.md#33-correctness--verification-the-actual-blockers), [Architecture 05](../Architecture/05-context-gateway.md)). A query naming a hidden attribute answers empty rather than confirming the attribute exists, and the broker is not asked at all.

### A write that smuggles policy into data

A write carrying `owner`, `acl`, `visibility` or `allowedRoles` is refused: policy is not data, and a payload cannot grant itself anything ([GW29](../Requirements/gateway-firewall.md#7-separation-of-policy-and-data)).

### Token forgery, and the edge that must not decide

Four calls carry a token the enforcement point must refuse and one carries a token it must accept. Every call goes through the edge, because the point of the case is that the edge is not what decides ([PF-46](../Requirements/platform.md), [ADR-N-018](../Decisions/adr-n-018-token-verification-in-the-peps.md)).

| Call | Token | Assertion |
|---|---|---|
| 1 | none | **401**, `application/problem+json`, answered by the Portal or the Context Gateway |
| 2 | valid signature, `aud` naming a different endpoint or space | **401**; an audience for one resource is not an audience for another |
| 3 | correct claims, signed with a key that is not in the realm JWKS | **401**; a forged ES256 signature must not pass because the header says ES256 |
| 4 | correct claims and signature, `exp` in the past | **401** |
| 5 | correct claims, signature and audience | **200**, and the answer is the one the policy decision point allows |

Calls 1 to 4 never reach the upstream's data path, and none of the five is decided by APISIX: taking the edge out of the path and calling the service in-cluster gives the same five answers. A deployment whose edge answers `200` for call 3 has a verifier that ignores the signature algorithm.

---

## 3. The edge, without a cluster

There is no dynamic scanner in any lane: OWASP ZAP runs nowhere, and neither does a semgrep pass. What exists instead is a suite that reads the edge configuration itself, `joinedcontext-deployment/tests/test_edge_attack_surface.py`, over every component's `apisix-routes.yaml` and `apisix-plugins.yaml` rather than over one environment's render. Five vectors:

1. a header the edge should own arriving from outside (GW12, AG-38),
2. a route without the authentication its sibling has (OPS-31),
3. TLS, HSTS and the security headers on every host (OPS-27),
4. request smuggling and oversized requests (GW26),
5. an admin surface reachable from the internet (OPS-31).

Walking the committed route files rather than a render is deliberate: a render carries only the components one environment switches on, and `ckan-redirect` shipped with no header sanitisation because CKAN is in `dev` while the edge tests read the `local` render. A route is now checked on the day it is written.

The live half of each vector, sending the header and the oversized body at a running edge, belongs to the conformance repository and runs against a throwaway environment, never against `dev`. `joinedcontext-deployment/tests/test_apisix_429_contract.py` is the one that starts the pinned APISIX image with the repository's own configuration and reads the answers back.

### One origin per App (AP-133…AP-135)

Apps on one origin read each other's storage and send requests carrying each other's sessions (T-2477), so each App has a host of its own (ADR-N-037). The render test of the edge suite holds the route file to it: every `app-{name}` and `app-{name}-endpoint` route is bound to `{name}.apps.{domain}`, an endpoint route names only the App's own slugs, and no apex route serves an App except the `308` of `app-{name}-moved`. A unit test of the reconciler holds each App pod's NetworkPolicy to DNS, the Linkerd control plane, the gateway and the App's declared destinations with the private ranges excepted, and `jcctl validate` refuses `0.0.0.0/0`, `::/0` and a host name in `spec.egress`.

The live half runs in the conformance repository's e2e suite against two published Apps, A and B (AP-135):

1. a page on A's host reads nothing of B's `localStorage`;
2. `fetch` from A's host to `/git/`, `/api/v1/` and one of B's endpoint slugs answers `404` at the edge;
3. A's session cookie is not sent to B's host, and `/apps/A/` on the apex redirects without a `Set-Cookie`;
4. a connection from A's pod to an address outside its NetworkPolicy fails, while its endpoint answers.

---

## 4. MCP authorization and isolation

The MCP surfaces are checked by `tests/mcp/` in the conformance repository, against a deployment: the RFC 9728 challenge and its metadata document, an audience for one space refused on another, the tool annotations, and read parity between a tool and the REST surface it stands for. See [02-conformance-tests.md](02-conformance-tests.md#4-model-context-protocol) for the whole list.

Inside the gateway, the token and audience rules those cases exercise are asserted in the `edge_auth_*` files, and the registry's person-only operations in the Portal's `tests/attack_person_only_operations_tests.rs`.

---

## 5. Agent sandboxes, the credential proxy, and prompt injection

An autonomous run happens in a pod that must hold no credential of its own (AG-34, AG-35, [ADR-N-020](../Decisions/adr-n-020-agent-runner-and-credential-proxy.md)).

### The sandbox manifest

`tests/security/sandbox.py` reads the rendered runner manifests and asserts privilege isolation, egress, credential scoping and workspace ephemerality (AG-22, AG-26, AG-27, AG-28): no `GATEWAY_TOKEN`, `KUBECONFIG`, `AWS_*` or `*_ADMIN_*` in the environment, and no container runtime socket mounted. `test_agent_sandbox_isolation.py` runs it, and `selftest_agent.py` proves it goes red on a leaky manifest.

### The credential proxy

`tests/security/proxy_matrix.py` is the refusal matrix, one case per route, each naming the requirement it proves and what is wrong with the call. Its structural half runs anywhere and holds the table to its own shape, so a new route without a case fails; its live half replays the same table against a running proxy with a real run's ticket, and skips with the name of the missing variable rather than passing quietly.

| Case | Call | Expected |
|---|---|---|
| `prx-001`, `prx-002` | no ticket, or a ticket belonging to no run | 401 |
| `prx-003` | a run id that is not the ticket's run | 401 or 403 |
| `prx-010` | a path that climbs out of the endpoint | refused |
| `prx-011` | a write from a run that declared no write rights | refused |
| `prx-020`, `prx-021` | a write to the default branch, or outside the run's own prefix | refused |
| `prx-030`…`prx-034` | a host the profile does not allow, an address inside the cluster, the node metadata service, a credential in the URL's userinfo, an unlisted registry | refused |
| `prx-040` | an event larger than the route reads | 413 |
| `prx-045` | a model call carrying a key of its own | the proxy's own key is used instead |
| `prx-046` | another run's inbox, asked for by id | refused |

`crates/agent-proxy/tests/attack_credential_targeting.rs` asserts the same pinning inside the crate: the target comes from the run, never from a header the client sends.

### Prompt injection

`tests/security/injection_corpus.yaml` carries the adversarial payloads and `test_prompt_injection.py` puts them into entity values an agent reads: an instruction in a manifest, a tool call written by the data, a role override in a sensor reading. The invariants are that data reaches the model as data, that a call the data wrote is refused and the person is told why, and that a tool result is never executable. The Portal asserts the same three in `tests/attack_assistant_tests.rs`, in the fast lane, along with the call ceiling and the daily quota that stop a looping model.

---

The register below is the platform's go-live gate. One row per attack vector, each owned by a
task, each naming the requirements it proves and the test that replays the attack. It is the
record an auditor and the owner read, and the BSI TR-03187 matrix in
[Architecture 13](../Architecture/13-security.md) links to it.

`joinedcontext-conformance/scripts/security_gate.py` turns the table into a gate, and `tasks/compliance gate` runs it. It fails when a
row names a requirement `Requirements/` does not define, when a `proven` row names a test that no
repository holds or that is switched off, and when a row that is not `proven` names a test anyway.
Test names resolve through the index `scripts/compliance.py` builds, so renaming a test in a
repository turns the gate red instead of quietly ending the proof
([compliance matrix](../Requirements/compliance-matrix.md)). The `compliance` workflow runs it
after the compliance check; an agent runs `tasks/compliance check` and the gate script from a
sandbox, where all five clones are present.

A row is `proven` only when a named test replays the attack and goes red when the defence is
switched off. Every row here is a priority 1 defence, so while any row is `open` the gate is red
and the platform is not ready for its first production apply. The owner signs this table before
that apply; "Never forced" applies to the signature as much as to the work.

State of the register on 2026-09-20: 50 vectors, 5 proven, 45 open.

| Surface | Vector | Task | Requirements | Test | State |
|---|---|---|---|---|---|
| apps | A generated app attacks the person, the platform or another app | T-1706 | AP-19, AP-63 |  | open |
| apps | The build lane runs untrusted code | T-1707 | AP-13, AP-72 |  | open |
| assistant | Prompt injection through data the assistant reads | T-1691 | AG-46, AG-11 | `joinedcontext-portal/tests/attack_assistant_tests.rs::an_instruction_a_manifest_carries_reaches_the_model_as_data_and_is_never_called`, `joinedcontext-portal/tests/attack_assistant_tests.rs::a_call_the_data_wrote_is_refused_and_the_person_is_told_why`, `joinedcontext-portal/tests/attack_assistant_tests.rs::an_instruction_the_persons_message_carries_is_never_a_call_the_portal_runs` | proven |
| assistant | The assistant acts with the platform's rights instead of the person's | T-1692 | AG-70 | `joinedcontext-portal/tests/attack_assistant_tests.rs::a_run_mints_no_key_for_a_person_who_may_not_read_service_accounts`, `joinedcontext-portal/tests/attack_assistant_tests.rs::a_conversation_starts_no_run_of_its_own_and_cancels_none`, `joinedcontext-portal/tests/agent_runs_tests.rs::a_second_person_neither_reads_nor_steers_a_run_that_is_not_theirs` | proven |
| assistant | Exfiltration through the assistant's outputs | T-1693 | AG-52, AP-63 | `joinedcontext-portal/tests/attack_assistant_tests.rs::a_route_outside_the_portal_never_becomes_a_navigate_event`, `joinedcontext-portal/tests/attack_assistant_tests.rs::a_draft_is_written_in_the_runs_own_project_and_in_no_other`, `joinedcontext-portal/src/apps/static_host.rs::a_plain_app_may_not_be_framed_and_talks_only_to_the_platform` | proven |
| assistant | Cost and loop exhaustion of the model key | T-1694 | AG-14 | `joinedcontext-portal/tests/attack_assistant_tests.rs::a_model_that_keeps_calling_one_tool_stops_at_the_call_ceiling_and_says_so`, `joinedcontext-portal/tests/agent_runs_tests.rs::a_conversation_above_the_daily_quota_is_refused_like_any_run` | proven |
| availability | One anonymous caller takes the single node down | T-1715 | GW26, OPS-16 |  | open |
| availability | A slow or dead dependency stalls everything | T-1716 | OPS-51 |  | open |
| cluster | A compromised pod moves sideways | T-1710 | OPS-29, PL-23 |  | open |
| cluster | Kyverno, Pod Security and admission in enforce | T-1711 | OPS-29 |  | open |
| cluster | Secrets at rest, in Git and in the cluster | T-1712 | CC-06 |  | open |
| edge | A header the edge should own arrives from outside | T-1672 | GW12, AG-38 |  | open |
| edge | A route without the auth plugin its sibling has | T-1673 | OPS-31 |  | open |
| edge | TLS, HSTS and the security headers on every host | T-1674 | OPS-27 |  | open |
| edge | Request smuggling and oversized requests at the edge | T-1675 | GW26 |  | open |
| edge | The admin surfaces are reachable from the internet | T-1676 | OPS-31 |  | open |
| forge | The forge as a side door to the configuration | T-1703 | CC-41, PF-51, PF-105, PF-106 |  | open |
| gateway | A caller widens what a Policy allows | T-1696 | EP-74, GW33 |  | open |
| gateway | A tenant header or an entity id of another space | T-1697 | EP-01, PF-84 |  | open |
| gateway | The JSON-LD context and other URLs the gateway fetches for a caller | T-1698 | R46 |  | open |
| gateway | Notifications as an amplifier or a leak | T-1699 | R46, PL-23 |  | open |
| gateway | File and bulk surfaces as a resource bomb | T-1700 | GW26 |  | open |
| identity | A token from the wrong realm, client, audience or algorithm | T-1677 | PF-46 | `joinedcontext-platform/crates/context-gateway/tests/attack_identity_token_tests.rs::an_algorithm_the_key_is_not_of_is_refused_however_plausible_the_header_looks`, `joinedcontext-platform/crates/context-gateway/tests/attack_identity_token_tests.rs::the_published_verification_key_signs_nothing_when_it_comes_back_as_an_hmac_secret` | proven |
| identity | Session fixation, theft and logout | T-1678 | PF-46 |  | open |
| identity | A write without the CSRF token, or from another origin | T-1679 | PF-46 |  | open |
| identity | Password guessing and the demo accounts in production | T-1680 | PF-46 |  | open |
| identity | Open redirect and code interception at login | T-1681 | PF-46 |  | open |
| import | Archives, bundles and YAML as the attack | T-1704 | CC-08, MF-05 |  | open |
| import | SyncSource, import by URL and peer schema mirrors as SSRF | T-1705 | MF-28, DM-49 |  | open |
| operate | Data loss: a database, a volume, the forge, the cluster | T-1717 | OPS-44 |  | open |
| operate | Nobody notices an attack | T-1718 | CC-44, CC-58 |  | open |
| operate | A credential is leaked and must be rotated today | T-1719 | OPS-45 |  | open |
| operate | Production is dev with another name | T-1720 | CC-73, CC-75 | `joinedcontext-deployment/tests/test_production_is_not_dev.py::test_production_renders_nothing_of_dev`, `joinedcontext-deployment/tests/test_production_is_not_dev.py::test_the_detector_finds_the_defect_it_is_named_for`, `joinedcontext-deployment/tests/test_production_is_not_dev.py::test_the_dev_render_is_what_the_detector_is_for` | proven |
| operate | An outside tester has not looked at it | T-1721 | OPS-27 |  | open |
| pipelines | A pipeline as a way out: Bloblang, processors, URLs and secrets | T-1701 | PL-18, PL-23, MF-39 |  | open |
| pipelines | Pipelines of two projects share a process | T-1702 | PL-07 |  | open |
| portal | A person of project A reads or writes project B | T-1682 | PF-59, R20 |  | open |
| portal | The check is made on one value and the action taken on another | T-1683 | PF-57 |  | open |
| portal | Privilege escalation through a grant | T-1684 | PF-52, PF-58 |  | open |
| portal | A secret in a manifest, a log, an error, a Change or an export | T-1685 | MF-24 |  | open |
| portal | Mass assignment and unknown fields | T-1686 | MF-05 |  | open |
| portal | Stored and reflected script in anything a person types | T-1687 | AG-46 |  | open |
| portal | Paging, filters and sort as an injection or a scan | T-1688 | CC-24 |  | open |
| proxy | The credential proxy hands a token to the wrong host, path or run | T-1695 | AG-52, AG-38 |  | open |
| registry | An MCP client or an agent reaches an operation a person must perform | T-1689 | AG-11, AG-82 |  | open |
| registry | The MCP endpoint without a token, with another audience, or as a confused deputy | T-1690 | AG-64, PF-46 |  | open |
| supply | A poisoned dependency or image | T-1713 | OPS-27 |  | open |
| supply | The CI as an attacker's foothold | T-1714 | OPS-27 |  | open |
| tenancy | Organisation and project isolation, end to end | T-1708 | PF-32, PF-59 |  | open |
| workspaces | A copy or a preview as a way around review | T-1709 | PF-82, PF-83, CC-81 |  | open |

## Related

- [00-strategy.md](00-strategy.md) — the lanes these scans and suites run in.
- [02-conformance-tests.md](02-conformance-tests.md) — the MCP and access suites in full.
- [R20](../Requirements/access-control.md) — the masking rule section 2 asserts.
- [13-security.md](../Architecture/13-security.md) — the trust zones and the BSI TR-03187 matrix that links to the register.
- [compliance matrix](../Requirements/compliance-matrix.md) — every requirement and the tests that name it.
