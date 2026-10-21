---
sidebar_position: 3
title: "Capacity Planning & Autoscaling"
description: What scales, what the charts declare today, and which numbers an operator sets before traffic arrives.
---

# Capacity Planning & Autoscaling

How to size the platform's workloads, where each number is declared, and what the deployment does when a component runs out of room. Read this before an instance takes production traffic; the values quoted here are the ones in `joinedcontext-deployment`, not targets.

---

## 1. Horizontal scaling of the stateless components

The Context Gateway, APISIX and Keycloak scale on an autoscaler. The number is a value in the component's production values file, which the workload chart turns into a `HorizontalPodAutoscaler`; nobody writes that object by hand (OPS-06, OPS-08).

| Component | File (`components/…/production-values.yaml.gotmpl`) | `replicaCount` | HPA | Target |
|---|---|---|---|---|
| Context Gateway | `context-gateway/values/gateway/` | 2 | 2…5 | CPU 70% |
| APISIX | `apisix/values/apisix/` | 2 | 2…10 | CPU 80%, memory 80% |
| Keycloak | `keycloak/values/app/` | 2 | 2…5 | the chart's default target |
| Portal | `portal/values/portal/` | 2 | none | fixed at two replicas |

The `production` profile is the one that carries these; the `dev` profile runs one replica of each, which is what the single-node cluster holds today. `replicaCount` stays in the file although the HPA manages the running count: the workload chart omits `spec.replicas` when autoscaling is on, so the value is the floor a fresh rollout starts from.

The broker does not scale this way. `ANTARES_BUS: "local"` allows exactly one broker process (`components/context-broker/values/broker/base-values.yaml.gotmpl`), so the broker's replica count stays at one until a bus component lands.

## 2. Pipeline runner budgeting

Bento runs in Streams Mode, one resident pod per project runner pool, `replicaCount: 1`. A pool does not get more replicas: horizontal scaling is more pools, because two replicas of one pool would consume the same streams twice.

- Per runner, the chart requests 100m CPU and 256Mi memory and limits 1000m and 1024Mi (PL-11, `components/pipeline-runner/values/runner/production-values.yaml.gotmpl`).
- One pool hosts at most 50 concurrent resident streams (PL-12). Beyond that the streams are partitioned across pools, which today is a decision written into the repository, not something the platform does by itself.
- A single pipeline may ask for more than the pool default with `spec.quotas.maxMemoryMb` and `spec.quotas.cpuMillicores` on its `Pipeline` manifest.
- A project's structural ceilings live on the `Project` manifest under `spec.quotas`: `contextSpaces`, `residentPipelines`, `publicEndpoints`, `ingestEventsPerSecond` and `apps` (PF-17), and Conftest enforces them in CI (PF-18).

Measure before you raise a limit. Bento serves `/metrics` on port 4195, the same port as its stream API, and the monitoring component renders the `ServiceMonitor` that scrapes it.

## 3. Temporal history and storage

Context history grows until something deletes it, and in this deployment nothing does.

The broker drops whole weekly partitions older than `ANTARES_TEMPORAL_RETENTION_DAYS` days as part of its maintenance tick. The variable is unset in every environment of `joinedcontext-deployment` today, and unset means history is kept forever. Set it on the broker's environment when an instance has a retention rule to enforce:

```yaml
# components/context-broker/values/broker/<env>-values.yaml.gotmpl
env:
  ANTARES_TEMPORAL_RETENTION_DAYS: "365"
```

Two things this is not. It is not per entity type: the broker drops partitions by age for the whole database, so a type that needs a different rule needs its own space. And it is not what bounds a caller's reads: a `Policy` may carry a temporal window, and the Context Gateway clamps every temporal query to it (GW26), which limits what is answered rather than what is stored.

Storage itself is a CloudNativePG `Cluster`; growing the volume is Runbook 9 in [01-runbooks.md](01-runbooks.md).

## 4. Single-node budget and growth

Both clusters are one k3s node each, and both render the `development` values profile, so one memory request in `components/*/values/*/development-values.yaml.gotmpl` sizes dev and prod together. Each request is the higher of the two clusters' measured use; each limit stays where its OOM history put it, and a limit is only ever raised (OPS-05).

Measured 2026-10-21 21:55-22:25Z (`kubectl top` once a minute and the kubelet's `/stats/summary`; neither cluster runs Prometheus, so there is no 7-day history to read):

| | dev (`cpx42`) | prod (`cpx52`) |
|---|---:|---:|
| Allocatable memory | 13.5 GiB | 21.1 GiB |
| Node working set | 12.4 GiB (92-94 %) | 16.5 GiB (77 %) |
| of it: pods | 7.8 GiB | 10.6 GiB |
| of it: k3s server and containerd | 3.9 GiB (2.8 GiB resident) | 7.9 GiB (3.3 GiB resident) |
| Sum of memory requests | 10.3 GiB (76 %) | 10.2 GiB (48 %) |
| Disk used | 232 of 305 GB, 64 GB images | 108 of 457 GB, 58 GB images |

The largest consumers, and where each one is fixed:

- `pipeline-runner`: 560-760 Mi on dev, 2.6-2.7 GiB of its 3 GiB limit on prod. The runner grows over days with no new streams; T-4936 finds the cause, and its request stays at 896 Mi until then, because a request sized to a leak only hides it.
- `postgres-cluster-1`: 1.6-1.8 GiB of a 2 GiB limit, two thirds of it shared buffers and page cache; the Antares database is 132 GB on dev, almost all temporal history (section 3, T-4906, T-5056, T-5057). The limit is not raised: dev has no node memory to give it.
- k3s itself: 2.8-3.3 GiB resident, outside every chart. Helm keeps three revisions per release (`defaults/helm-defaults.yaml` `historyMax`), down from ten, which removes about 2,200 release Secrets per cluster from the datastore and the API server's watch cache.
- `context-gateway`: 210-310 Mi at rest, OOMKilled at its 1 GiB limit on prod under load; T-4782 bounds its buffers before the limit moves.
- Keycloak (720-770 Mi), Solr (590-760 Mi with a 256m heap) and the assistant worker (620-640 Mi, its embedding model) are steady: requests match them.
- Kyverno and Traefik come from kube-hetzner (`hetzner-kit/`), not from this repository; Kyverno's admission controller holds 190 Mi against a 128 Mi request on prod.

What growth costs, from the same measurements:

- One more source (a resident Bento stream): about 5 MB of runner memory idle (Bento 1.22.0, section 2) plus one page of the source while a run is in flight; disk is its history, `entities x attributes x updates per day x about 1.25 KB` until T-5057 compacts a row. A source of 1,000 entities with 10 attributes every 5 minutes writes 2.9 million rows, about 3.6 GB a day, so set its type's history duration (T-5056) before it lands.
- Ten more sources: about 50 MB idle and up to a few hundred MB while several runs overlap; CPU stays under 100m at rest.
- One more city: its sources as above, about 128 Mi request per App pod it publishes, and 256 Mi for a site database where it has one. Keycloak, CKAN, Solr, the Portal and the broker are shared, so a city adds rows to them, not pods.
- Two more cities with 20 sources each: about 1 GiB of requests and 0.5-1 GiB of working set, plus their history on disk.

Prod has about 0.6 GiB to its 80 % line today and gains 1.7 GiB once T-4936 holds the runner at dev's size, so it takes the two cities after that fix. Dev has no headroom at all and takes neither.

Add a node, or move the instance to the next server size, when any of these holds for an hour:

1. The node's working set is over 80 % of allocatable memory (`kubectl top nodes`).
2. The sum of memory requests is over 85 % of allocatable (`kubectl describe node`, Allocated resources): the next rollout cannot schedule its surge pod.
3. The node's disk is over 75 %, or Postgres's volume grows faster than retention drops it.
4. Postgres is throttled at its CPU limit in more than 20 % of its periods.

Dev meets rule 1 today. Moving dev to a `cpx52`, the size prod runs, costs money, so the owner decides it; until then dev stays at its present load and takes no new city.

## Related

- [01-runbooks.md](01-runbooks.md) — what to do when a component runs out of memory or disk.
- [Requirements/pipelines.md](../Requirements/pipelines.md) — PL-11 and PL-12, the runner's resources and the 50-stream ceiling.
- [Requirements/operations.md](../Requirements/operations.md) — OPS-05…OPS-08, the resource and availability rules these values implement.
- [Deployment/05-monitoring-logging.md](../Deployment/05-monitoring-logging.md) — where the metrics behind these decisions come from.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
