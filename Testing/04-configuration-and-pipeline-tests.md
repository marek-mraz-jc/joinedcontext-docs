---
sidebar_position: 5
title: Configuration Plane & Pipeline Testing
description: What validates a manifest, what gates an organization repository's merge request, and how a Bento pipeline is linted and tested.
---

# Configuration Plane & Pipeline Testing

This page is for whoever writes or reviews a manifest: what refuses a bad one, which gate runs where, and how a pipeline is proven before it ingests anything. The platform configuration lives as manifests in the organization repository ([CC-02](../Requirements/city-as-code.md#1-architecture-and-source-of-truth)). Two separate gates exist, and mixing them up is the usual confusion: `jcctl` validates the manifests of an organization repository, while `conftest` gates the Kubernetes manifests the deployment renders. Read off the code on 2026-09-20.

---

## 1. Manifest validation

Every manifest carries the envelope from `crates/jc-core/src/envelope.rs`: `apiVersion: joinedcontext.com/v1alpha1`, and `joinedcontext.com/v1alpha2` for `Pipeline`, which still reads a `v1alpha1` document as the `v1alpha2` it means.

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: ovzdusie
  namespace: banskabystrica
  title:
    sk: Ovzdušie
spec:
  urnSegment: ovzdusie
```

One command validates a whole repository:

```bash
jcctl validate --repo-dir ./banskabystrica
```

It is stronger than a schema check, and it is worth knowing why. Each manifest is parsed into its typed kind by `jc-core` with `deny_unknown_fields`, so a misspelled field and a literal password beside a `secretRef` are both parse errors rather than ignored keys. The typed parse then runs the cross-field invariants a schema cannot express, and each manifest must sit at the path its kind prescribes (MF-06). A finding names the file, the document inside it, the line and the field. A manifest that writes the organization's domain where `{orgDomain}` belongs is a warning, because the same file could not then render two environments (CC-74).

The draft-07 schemas themselves are published by `jcctl schema export [--out <dir>]`; the Portal's forms are built from them. There is no `--schemas-dir` or `--schema-dir` option, and no separate schema directory to point at: the types are the schema.

---

## 2. The gate on an organization repository

`jcctl roles render --repo-dir <path>` writes four things into the organization repository from the `Role` and `RoleBinding` manifests under `users/`: `CODEOWNERS`, `policies/roles.json`, `policies/roles.rego` and the repository's own `.gitea/workflows/ci.yaml`. That workflow is the gate every merge request there passes, and it runs in the forge the organization uses, Gitea:

1. **Every manifest parses and sits where its kind prescribes.** `jcctl validate --repo-dir /repo` in the pinned platform image (MF-09).
2. **The rendered files are what `users/` says.** `jcctl roles render` is run again and `git diff --exit-code` compares `CODEOWNERS`, `policies/roles.json`, `policies/roles.rego`, `policies/tests` and the workflow itself. A hand-edited policy fails here (PF-51).
3. **The author's bindings allow every change.** `jcctl roles input` builds a document from the diff (the author's login, their groups, and one entry per changed manifest with its path, action, kind, name, project and the whole document), then `conftest verify -p policies` and `conftest test /tmp/input.json -p policies -d policies/roles.json` decide (PF-52).

`policies/roles.rego` denies a change no binding covers, and a rule may carry constraints on a manifest field: `equals`, `in` and `notIn`, evaluated against the document itself. That is how "this role may only publish endpoints whose audience is not public" is written today. There is no quota policy and no separate plaintext-secret policy: an inline credential is refused one step earlier, by the typed parse, and no quota is implemented anywhere in the code.

### Which changes need an approver

`crates/jcctl/src/lanes.rs` derives the approval lane from what a change does, never from what the author says about it: green is auto-approved by the policy bot, yellow needs one domain approver, red needs the full chain. A proposal takes the lane of its strictest change, so one deletion among twenty additions still needs the red chain. Deletion, public exposure, federation and identity kinds are red; raising an agent profile's limits or widening its egress is red as well ([CC-63](../Requirements/city-as-code.md), CC-70, AG-47). `crates/jcctl/tests/lanes_tests.rs` is where a new kind's lane is asserted.

---

## 3. Conftest in our own repositories

In `joinedcontext-deployment` the same tool gates the rendered Kubernetes manifests, per environment, in the fast lane: `conftest test --all-namespaces -p policies rendered-<env>.yaml` with conftest pinned to 0.69.0 by version and checksum. Three policies, all in package `main`:

| Policy | What it denies |
|---|---|
| `policies/workloads.rego` | a container that does not set `runAsNonRoot`, asks for uid 0, does not `drop: [ALL]`, declares no memory limit, or shares the namespace's `default` ServiceAccount |
| `policies/egress.rego` | a NetworkPolicy for a workload that fetches addresses somebody else chose (the pipeline runner, the gateway) whose egress leaves a private range reachable |
| `policies/edge.rego` | an edge configuration whose rate-limit answer is not `application/problem+json` with a `Retry-After` |

Kyverno asserts the workload properties again at admission; the Rego copy fails a pull request instead of a rollout. `kyverno test .ci/policies` runs the policy unit tests in the same lane.

---

## 4. Plan and idempotency

```bash
jcctl plan --repo-dir ./banskabystrica [--gateway-url <url>] [--token-file <path>] [--json]
jcctl apply --repo-dir ./banskabystrica [--prune] [--confirm-deletions]
jcctl drift --repo-dir ./banskabystrica [--json] [--adopt-dir <path>]
```

`plan` prints what the repository declares and, with `--gateway-url`, what the live side holds. Idempotency is asserted in `crates/jcctl/tests/apply_tests.rs`: apply, plan again, and the second plan is empty ([CC-18](../Requirements/city-as-code.md#3-reconciler-jcctl)). Drift is the same comparison in the other direction, and `--adopt-dir` writes the live state out as manifests to adopt.

There is no `--assert-empty` and no `--diff` flag, and no CI lane of ours posts a plan as a merge request comment: [TS-20](../Requirements/testing.md) is open, and the MVP has no pull requests to comment on. In the Portal the plan a person reads before approving is rendered from the same `ChangeSet`.

---

## 5. Bento pipelines

A pipeline folder holds the platform manifests and the Bento configuration side by side:

```text
examples/ingestion/csv-fetch/
├── pipeline.yaml            # the platform envelope: kind Pipeline
├── datasource.yaml          # kind DataSource: where the data comes from
├── bento.yaml               # the Bento stream configuration
└── bento_bento_test.yaml    # golden cases for bento.yaml
```

Bento pairs a test definition with the configuration of the same name in the same folder, which is why the tests for `bento.yaml` live in `bento_bento_test.yaml` beside it. A test under `tests/` is only found when it is named after a configuration in that folder, which is where binary fixtures and the decoder configurations that read them belong; `examples/ingestion/gtfs-rt/` is the example that needs both.

The fast lane in `joinedcontext-platform` lints and runs every one of the 15 examples under `examples/ingestion/`:

```bash
bento lint ./examples/ingestion/*/bento.yaml ./examples/ingestion/gtfs-rt/tests/decoder.yaml
bento test ./examples/ingestion/...
```

Two things to know before you run it. `bento lint` refuses a configuration whose environment interpolations are unset, so the lane exports a placeholder for each one; the runner gets the real value from its ServiceAccount. And lint only the Bento configurations: the platform manifests in the same folder are a different schema and are checked by `jcctl`.

One pipeline against one sample file, without a cluster:

```bash
jcctl pipeline test --pipeline examples/ingestion/csv-fetch/pipeline.yaml --sample sample.csv --format csv
```

It renders the manifest into a Bento configuration with an `http_client` input for the sample URL, so the fetch obeys the runner's own egress policy rather than a path that exists only in a test.

### What is not checked

A pipeline declares where it reads from, and the runner's NetworkPolicy declares where it may reach. No gate compares the two today: a manifest naming a host the policy does not allow validates here and fails at runtime, where the runner's log names the refused address. The egress policy above asserts the shape of that NetworkPolicy, not its agreement with a particular pipeline.

## Related

- [00-strategy.md](00-strategy.md) — the lanes these checks run in.
- [01-backend-tests.md](01-backend-tests.md) — the `jcctl` test files behind this page.
- [CC-02](../Requirements/city-as-code.md) — the repository as the source of truth.
- [ADR-N-004](../Decisions/adr-n-004-configuration-as-code-and-gitea.md) — why the configuration lives in a forge.
- [testing](../Requirements/testing.md) — the TS family this page is verified against.
