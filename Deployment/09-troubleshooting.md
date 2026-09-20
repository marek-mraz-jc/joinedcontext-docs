---
sidebar_position: 10
title: Troubleshooting Guide
description: Symptoms, the cause behind each, the command that confirms it, and the fix.
---

# Troubleshooting Guide

Symptoms an operator meets, grouped by the component that produces them. Every command below runs against a deployed instance; substitute the namespace your installation uses. With the shipped `global.singleNamespace: true` every component lives in one namespace named after `global.instanceSlug` (`dev` on the reference cluster); with `singleNamespace: false` each one is `{instanceSlug}-{component}`, for example `dev-postgres`.

## 1. APISIX & Ingress Routing

| Symptom | Cause | Command that confirms it | Fix |
|---|---|---|---|
| Route changes in Git are ignored by APISIX | `conf/apisix.yaml` has no `#END` terminal marker | `kubectl exec deployment/apisix -c apisix -- tail -n 2 conf/apisix.yaml` | Append `#END`. APISIX accepts the file and ignores it without the marker ([stack verdict S7](../Research/city-as-code-stack.md#8-s7-gateway-declarative-mode)). |
| A route takes about a second to appear | Standalone mode polls the mounted file | `kubectl logs -l app.kubernetes.io/name=apisix -c apisix` shows `file changed, reloading` | Nothing. This is the polling interval, not a fault. |
| `502 Bad Gateway` on a public route | The upstream Service does not resolve, or a Linkerd policy denies the connection | `kubectl logs -l app.kubernetes.io/name=apisix -c apisix` | Check the Service exists. Check the ingress controller's namespace is Linkerd-injected ([10-edge-routing-apisix.md](10-edge-routing-apisix.md#5-upstream-transport-security-and-service-mesh-policy)). |
| `504` on a route whose pod is Running and Ready, with `Failed to connect error=Connection refused` in the gateway's Linkerd proxy | The CNI has not programmed the new pod's ingress rules. Seen on k3s with the embedded controller: the policies are live and their selectors match, and packets still do not reach the pod | `kubectl logs -l app.kubernetes.io/name=apisix -c linkerd-proxy \| grep <upstream>` shows refused connections to the pod address, and the destination pod's own proxy log shows nothing at all | Make the controller reprogram: `helmfile -f helmfile-root.yaml.gotmpl -e <env> sync --selector component=networkpolicies`. Ask the pod first: `kubectl exec deploy/<name> -- wget -qO- http://<pod IP>:<port>/<health path>` answers when the process is listening. |

## 2. Context Gateway & Authorization

| Symptom | Cause | Command that confirms it | Fix |
|---|---|---|---|
| `404` on an entity that exists | Existence masking: the caller holds no read grant, and the gateway answers as if the entity were not there | `kubectl logs -l app.kubernetes.io/name=context-gateway` | Check the caller's groups, then grant the read in a `Policy` ([R20](../Requirements/access-control.md#5-requesting-extra-data)). |
| `403 Forbidden` | The operation or the attribute set is outside what the Policy grants | Read the RFC 7807 problem document in the response | Match the policy URN it names against the gateway's decision log, then widen the Policy's constraints. |
| Token audience mismatch | The token names none of the audiences this endpoint accepts | Decode the token's `aud` claim | Ask for a token whose audience is the endpoint's slug, which is what every client the deployment seeds uses. The gateway also accepts `{publicBaseUrl}/api/endpoint/{slug}` where the installation names a public base URL, and `context-gateway` for a session token from the edge (`crates/context-gateway/src/app.rs`, `audiences_of`). |
| `400` on a query | The `q` expression does not parse | `kubectl logs -l app.kubernetes.io/name=context-gateway` shows an `antares-ql` parse error | Write the query to ETSI GS CIM 009 clause 4.9 syntax. |

## 3. Reconciliation and the forge

The reconciler runs inside the Portal process; there is no separate reconciler workload, and `jcctl` is the command-line tool over the same manifests.

| Symptom | Cause | Command that confirms it | Fix |
|---|---|---|---|
| `jcctl plan` reports changes right after an apply | Attributes written by telemetry are read as drift | `jcctl drift --repo-dir <path> --gateway-url <url> --token-file <path>` names the entity and the attribute | Declare those attributes in `metadata.managedAttributes` so the comparison skips them ([CC-69](../Requirements/city-as-code.md#11-interaction-lanes-and-sandboxes)). |
| An apply stops part-way | A resource an earlier one depends on failed: usually a Context Space whose broker tenant was never created | `jcctl plan --repo-dir <path> --json` shows what is still outstanding; `kubectl logs -l app.kubernetes.io/name=context-broker` says why | Check the broker's logs and the database's free space. |
| A change's merge request never merges | The Conftest policy check failed, or nobody with `approve` has approved it | Read the Change in the Portal: it carries the verdict and the lane | Fix what the verdict names, or have a person with `approve` on that kind approve it. The forge runs no CI of its own: `components/gitea` sets Gitea Actions `ENABLED: false` and deploys no runner, so a workflow committed there would never start. |

## 4. Pipeline Runners (Bento)

| Symptom | Cause | Command that confirms it | Fix |
|---|---|---|---|
| A runner pod is OOMKilled | The stream holds too large a batch in memory | `kubectl describe pod -l app.kubernetes.io/name=pipeline-runner` | Reduce the Bento `batching` sizes in the Pipeline's `bento.yaml`, or raise the limit in `components/pipeline-runner/values/runner/<profile>-values.yaml.gotmpl` (the shipped limit is 1000m CPU and 1024Mi). |
| An MQTT or HTTP source times out | A NetworkPolicy denies the runner's egress | `kubectl logs -l app.kubernetes.io/name=pipeline-runner` | Add the host and port to the runner's egress policy in `components/pipeline-runner/networkpolicies.yaml`. |
| A scheduled pipeline does not start | The previous run has not finished, and the CronJob's `concurrencyPolicy` is `Forbid` | `kubectl get cronjob,pods` | Find what the previous run is waiting on. The run's own deadline is `activeDeadlineSeconds`, 300 by default, per pipeline in `components/pipeline-runner/values/scheduled/`. |

## 5. CloudNativePG & Database

| Symptom | Cause | Command that confirms it | Fix |
|---|---|---|---|
| The database refuses writes and reports read-only | The volume is nearly full | `kubectl get pvc` | Raise `cluster.storage.size` in `components/postgres/values/cluster/<profile>-values.yaml.gotmpl` and let CNPG expand the volume ([Operations Runbook 9](../Operations/01-runbooks.md#9-runbook-9-disk-full-on-cloudnativepg-cluster)). The shipped sizes are 1Gi for `development` and 50Gi for `production`. |
| A standby lags | Write volume, or the network between the instances | `kubectl cnpg status postgres-cluster`, the name every component dials as `postgres-cluster-rw` | Read the replication lag in Prometheus before resizing anything. |

## Related

- [00-intro](00-intro.md) — the chapter order and what each component is.
- [05-monitoring-logging](05-monitoring-logging.md) — where the metrics and logs these commands read come from.
- [10-edge-routing-apisix](10-edge-routing-apisix.md) — the route table and the mesh policy behind section 1.
- [01-runbooks](../Operations/01-runbooks.md) — the longer procedures these fixes point into.
- [R20](../Requirements/access-control.md#5-requesting-extra-data) — why a missing grant answers 404 and not 403.
