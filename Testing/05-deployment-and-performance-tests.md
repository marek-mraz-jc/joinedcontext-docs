---
sidebar_position: 6
title: Deployment & Performance Testing
description: Rendering and policy gates, the k3d variant matrix, the recovery drill, the smoke test, and the k6 budgets.
---

# Deployment & Performance Testing

This page is for whoever changes a chart, a value or the edge: what renders and gates it, how a whole instance is brought up in CI, how a recovery drill is run, and which performance budgets a benchmark has to keep. The deployment lives in `joinedcontext-deployment` as Helmfile components. Read off the code on 2026-09-20.

---

## 1. Render, then gate the rendering

Nothing reaches a cluster before its rendered manifests pass. One environment at a time:

```bash
scripts/render.sh dev rendered-dev.yaml          # helmfile template, one file
kubeconform -strict -ignore-missing-schemas -summary rendered-dev.yaml
conftest test --all-namespaces -p policies rendered-dev.yaml
python3 scripts/ci/check-image-digests.py rendered-dev.yaml
```

`--deployed` drops Helm test hooks, which `helmfile sync` never applies: what is not applied must not be judged as if it were.

The fast lane runs that sequence for every environment, then two secret scans over the rendered output (`scripts/check-rendered-secrets.py`, `gitleaks detect` with `.ci/gitleaks-rendered.toml`, `scripts/check-secrets.py`) and compares the object list with the golden one in `.ci/golden/local.txt`. A new object in the diff is not a failure by itself; leaving the golden list unchanged is.

### Kyverno

`kyverno test .ci/policies` runs the policy unit tests in the fast lane. The hourly `ci-full` lane applies the policies to the rendered `local` and `production` environments through `.ci/policies/verify-kyverno-policies.sh`, which is the admission answer rather than the shift-left copy. The same four workload properties are asserted twice on purpose: `policies/workloads.rego` fails a pull request, Kyverno fails a rollout.

| Asserted | Where it comes from |
|---|---|
| `runAsNonRoot`, no uid 0 | `policies/workloads.rego`, Kyverno restricted profile |
| `capabilities.drop: [ALL]` | the same two |
| a memory limit on every container | the same two |
| a ServiceAccount of its own, never the namespace `default` | the same two |
| every image pinned by digest | `scripts/ci/check-image-digests.py` |

---

## 2. The k3d variant matrix

`scripts/test-deployment-variants.sh` brings a whole instance up in a fresh k3d cluster, one variant after another, and asserts after each deployment that every pod is Running and Ready or Completed and that every Deployment, StatefulSet and DaemonSet rolled out. A variant is a triplet of toggles:

| Axis | Value written into the scratch `testing` environment |
|---|---|
| multi-namespace | `global.singleNamespace` |
| multi-instance | two-layer operators plus instance, against an all-in-one helmfile |
| service mesh | `global.serviceMesh.enable`, with the Linkerd control plane |

```bash
./scripts/test-deployment-variants.sh --list      # the matrix
./scripts/test-deployment-variants.sh 0,0,0       # one variant
./scripts/test-deployment-variants.sh             # all eight
```

The hourly `ci-full` lane runs `0,0,0` as the `k3d-deploy` job and the whole matrix as `deployment-variants`, each with a 900 second budget per variant, and uploads the cluster's state when a variant fails. `--state-values-set` is not forwarded to the components, which is why the harness owns the scratch environment and writes the toggles into its values file.

---

## 3. The recovery drill

`scripts/dr-drill.sh` is the restore half of the drill (OPS-11, OPS-12, [CC-50](../Requirements/city-as-code.md#8-export-portability-and-upgrade)), in the order Runbook 6 gives it:

1. back the database up into the object store the instance carries,
2. lose the database, the way an incident loses it,
3. bring it back from the archive at an instant inside the retention window (OPS-10),
4. replay the repository's seed entities through the gateway (CC-72), and
5. ask `jcctl plan` for a diff, and assert there is none.

Steps 4 and 5 are the point. A drill that stops at step 3 proves the database came back; these two prove the platform came back, because every component reads its manifests from Git and the seed entities are the one state the repository cannot project by itself.

```bash
scripts/dr-drill.sh --check                  # preconditions only, writes nothing
scripts/dr-drill.sh --env local --slug local
```

The deployment half is deliberately not in this script: the k3d lane above already brings a whole instance up, and a second harness for the same thing would drift from the first.

---

## 4. The smoke test of a live instance

`just dev-smoke` runs `scripts/smoke.sh <base-url> <idm-url>` from outside the cluster and then `scripts/smoke-forge-login.sh`, because the forge login button can fail with everything else green. Every check asserts an exact status over a valid TLS chain, with no `-k`, so an expired certificate fails the run. A check whose subject is not deployed in this instance is reported as skipped rather than passed: it never ran.

Applying and smoking `dev` belong to the hourly batch, not to a push.

---

## 5. The k6 budgets

`tests/k6/budgets.js` in `joinedcontext-conformance` is the single place the thresholds live, shared by the benchmark scripts and by `selftest.js`, which feeds them synthetic samples so that a budget nobody can fail is caught.

| Budget | Threshold | Requirement |
|---|---|---|
| gateway overhead against the broker on the same entity, p99 | under 5 ms | EP-28 |
| gateway read, p95 | under 50 ms | OPS-18 |
| sustained reads | at least 95 % of `rate × duration`, counted | TS-22 (5000 rps per replica) |
| iterations the arrival rate could not start | none | TS-22 |
| failed requests | under 0.1 % | TS-22 |
| checks | all of them pass | TS-22 |
| endurance: failed requests, memory growth | under 0.01 %, no growth verdict | TS-22 |
| export: time to first byte, p95 | under 1 s | EP-44 |
| export: whole download | under 300 s, no timeout | EP-44 |
| endpoint: `file.geojson` time to first byte, p95 | under 1 s | EP-05 |
| endpoint: answers missing the `RateLimit` field | none | EP-20 |
| endpoint: 429s | none under the limit, at least one in a deliberate burst | EP-20 |

Two decisions in that file are worth knowing. The 5 ms is the gateway's own overhead, measured against the broker on the same entity: a 5 ms budget on the total read would be a budget on the broker, the network and the dataset size instead of on anything this platform controls. And the sustained rate is asserted as a counter rather than as a rate, because k6 divides a metric rate by the whole run, setup and graceful stop included, which understates the plateau.

Memory growth is a least-squares slope of the resident set over the run, expressed as a percentage of the mean per minute, so a soak reports the number the gate used rather than a verdict alone.

### Running one

```bash
GATEWAY_URL=https://{host}/cs/{space}/ngsi-ld/v1 \
  BROKER_URL=http://antares.joinedcontext.svc:8080/ngsi-ld/v1 \
  JC_K6_SCRIPT=gateway-latency-load.js JC_K6_RATE=5000 JC_K6_DURATION=1m \
  jc-conformance k6
```

The four scripts are `gateway-latency-load.js` (latency and throughput), `gateway-endurance.js` (a 30 minute soak), `bulk-export.js` (streaming export, needs `EXPORT_URL`) and `transport_endpoint_load.js` (one endpoint's representations, needs `ENDPOINT_URL`). `run.sh` refuses to start without the URL its script needs, and says on stderr which budget an unset variable leaves unmeasured: without `BROKER_URL` there is no EP-28 overhead, without `JC_K6_BURST_RATE` the EP-20 limiter is never proven. `scripts/compare-latency.py` compares a run's summary with the rolling seven-day history in `benchmarks/latency-history.json` and fails a regression over 5 %; its `--selftest` proves it flags a degradation and respects a baseline.

No benchmark runs by itself today: the `k6` and `nightly-benchmarks` workflows are `workflow_dispatch` only while the private repositories' Actions minutes are metered, and there is no `criterion` microbenchmark in the Rust repositories at all.

---

## 6. Scale: 10,000 Endpoints

The platform has to serve 10,000 Endpoints (CC-54). `crates/context-gateway/examples/scale_bench.rs` in `joinedcontext-platform` measures what that costs offline, with no cluster. `jcctl::bench_org` writes a layout 2 organization of N public Endpoints over N/100 projects. Each Endpoint has its own ContextSpace and read Policy, each project one DataModel, and every tenth Endpoint a Pipeline. The bench loads it the way the gateway does and measures:

- the store load;
- the reaper's idle tick, and its tick after one Policy edit;
- a slug lookup;
- `jcctl validate` over the tree;
- the peak resident set.

One size runs per process. The `scale-bench` workflow runs 100, 1,000 and 10,000 three times each, on demand only; it is never a gate.

```bash
cargo run --release -p context-gateway --example scale_bench -- 10000
```

Medians of three on the sandbox host (12 cores), platform branch of T-4443:

| Endpoints | load | idle tick | tick after one Policy | slug lookup | `jcctl validate` | peak RSS |
|---|---|---|---|---|---|---|
| 100 | 83 ms | 4.7 ms | 98 ms | 0.031 µs | 115 ms | 15 MiB |
| 1,000 | 880 ms | 53 ms | 1.09 s | 0.035 µs | 1.24 s | 35 MiB |
| 10,000 | 8.99 s | 533 ms | 11.2 s | 0.075 µs | 13.1 s | 239 MiB |

Every cost but the request path grows linearly with the tree. At 10,000 the three largest are:

1. the layout 2 assembly, which copies, re-renders and re-parses every file of every project on each load (T-4457);
2. a reload of everything for any change (T-4444);
3. an idle tick that stats every file once a second (T-4444).

A request does not pay any of these: the slug table is a hash map swapped whole, so a lookup costs the same at 10 and at 10,000. Before T-4443 the load at 10,000 took 14.4 s. Two costs were removed: a scan of every resource for each space, and a second parse of the assembled tree.

### 6.1 Finding one dataset among 10,000

`mod scale` in `crates/context-gateway/tests/mcp_hub_catalog_tests.rs` generates a catalogue a person would search, seeded so a seed gives the same catalogue each run (T-4497). Each Dataset has one public Endpoint and is built from:

- one of 14 Smart Data Model topics, with titles and descriptions in Slovak and English;
- one of 518 places: the names of dev's AdministrativeArea entities, in `tests/fixtures/places-dev.txt`;
- a year from 2023 to 2026;
- a publisher.

Near-duplicates differ by a year or a place only. The measurement asks 200 questions through the in-process hub:

- a third in Slovak with diacritics;
- a third in Slovak without them;
- a third in English.

It does not run in CI:

```bash
cargo test --release -p context-gateway --test mcp_hub_catalog_tests ten_thousand_generated -- --ignored --nocapture
```

Sandbox host (12 cores), 10,000 Datasets, seed 4497:

| path | p50 | p95 | target p95 |
|---|---|---|---|
| MCP `search` | 47 ms | 52 ms | < 100 ms |
| `list_endpoints`, first page | 41 ms | 44 ms | < 100 ms |
| `list_endpoints`, cursor 9,000 and on | 41 ms | 45 ms | < 100 ms |
| catalog `query_entities`, `searchText` | 65 ms | 73 ms | < 200 ms |
| catalog `query_entities`, `theme` | 61 ms | 67 ms | < 200 ms |

The target Dataset ranks in the first three hits for 30 of 30 known-target questions. About 41 ms of each call is the hub's per-caller reach over 10,000 Endpoints. Before T-4542, `list_endpoints` described every Endpoint it reached on every call, so its first page took 264 ms at p95. Section 6.2 measures CKAN `package_search` and the Portal's Endpoint list.

### 6.2 Finding one of 10,000 datasets in CKAN and the Portal

T-4544 measures the paths a person searches with outside the gateway, offline and never on `dev`. The catalogue comes from T-4497's generator: seed 4497, the 14 SDM topics, the 518 place names read from dev, and the years 2023 to 2026. Three measurements read it:

- `tests/scale/ckan-rig.sh all` in `joinedcontext-conformance` starts CKAN, Solr, Redis and Postgres in docker from the chart's pinned images. It loads the 10,000 packages that `tests/scale/catalogue.py` exports, then asks `package_search` 200 questions: a third sk, a third sk folded to ASCII, a third en. Each question carries two facets and a type filter.
- `tests/endpoint_list_scale_bench.rs` in `joinedcontext-portal` (ignored, release) asks the Endpoint list 200 times through the whole router.
- `ui/e2e/endpoints_scale.spec.ts` times the built Endpoints page with the same 10,000 Endpoints answered in the browser.

Sandbox host (12 cores), 2026-10-18:

| path | p50 | p95 | target |
|---|---|---|---|
| CKAN `package_search` with facets | 21.6 ms | 26.5 ms | p95 < 300 ms |
| Portal Endpoint list, first page of 50 | 34.9 ms | 55.3 ms | p95 < 200 ms |
| Portal Endpoint list, deep page of 50 | 33.8 ms | 54.2 ms | p95 < 200 ms |
| Portal Endpoint list, all 10,000 | 54.3 ms | 74.3 ms | p95 < 200 ms |
| Endpoints page, first row on screen | 16.5 s | | < 1 s |

In CKAN, a dataset about the asked topic, place and year is among the first three for 200 of 200 questions. The Endpoints page misses its target: it fetches the whole list and mounts every row (T-4545).

## Related

- [00-strategy.md](00-strategy.md) — which lane each of these runs in.
- [04-configuration-and-pipeline-tests.md](04-configuration-and-pipeline-tests.md) — the policies behind the render gate.
- [CC-50](../Requirements/city-as-code.md) — the portability the drill proves.
- [TS-22](../Requirements/testing.md) — the load requirement the budgets carry.
- [06-security-tests.md](06-security-tests.md) — the scans that run beside these lanes.
- [CC-54](../Requirements/city-as-code.md) — the scale the bench measures.
