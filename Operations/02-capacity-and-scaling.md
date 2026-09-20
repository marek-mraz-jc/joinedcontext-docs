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

## Related

- [01-runbooks.md](01-runbooks.md) — what to do when a component runs out of memory or disk.
- [Requirements/pipelines.md](../Requirements/pipelines.md) — PL-11 and PL-12, the runner's resources and the 50-stream ceiling.
- [Requirements/operations.md](../Requirements/operations.md) — OPS-05…OPS-08, the resource and availability rules these values implement.
- [Deployment/05-monitoring-logging.md](../Deployment/05-monitoring-logging.md) — where the metrics behind these decisions come from.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
