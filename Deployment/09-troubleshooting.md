---
sidebar_position: 10
title: Troubleshooting Guide
description: Diagnostic matrices, root-cause analyses, and concrete fixes for platform issues.
---

# Troubleshooting Guide

This guide provides troubleshooting tables and remediation steps categorized by system component.

---

## 1. APISIX & Ingress Routing

| Symptom / Error | Probable Root Cause | Verification Command | Remediation |
|---|---|---|---|
| Route updates in Git are ignored by APISIX | `conf/apisix.yaml` missing `#END` terminal marker | `kubectl exec -it deployment/apisix -c apisix -- tail -n 2 conf/apisix.yaml` | Add `#END` marker to the end of `apisix.yaml`. APISIX fails silently if this marker is missing ([stack verdict S7](../Research/city-as-code-stack.md#8-s7-gateway-declarative-mode)). |
| 1-second route reload delay | Expected behavior of standalone file-polling mode | Check logs for `file changed, reloading` | Normal operation. APISIX polls the mounted ConfigMap every 1 second. |
| HTTP 502 Bad Gateway on public routes | Upstream service DNS unreachable or Linkerd policy blocking ingress | `kubectl logs -l app.kubernetes.io/name=apisix -c apisix` | Verify upstream service exists. Ensure Ingress controller namespace has Linkerd injection enabled ([Deployment/10-edge-routing-apisix.md](../Deployment/10-edge-routing-apisix.md#5-upstream-transport-security-and-service-mesh-policy)). |
| HTTP 504 on a route whose pod is Running and Ready, with `Failed to connect error=Connection refused` in the gateway's Linkerd proxy | The network plugin has not programmed the new pod's ingress rules yet. Seen on k3s with the embedded controller: the policies are live in the API and their selectors match, and the packets still never reach the pod | `kubectl logs -l app.kubernetes.io/name=apisix -c linkerd-proxy \| grep <upstream>` — refused connections to the pod address, and nothing at all in the destination pod's own proxy log | Force the controller to reprogram: `helmfile -f deployment/helmfile.yaml -e <env> sync --selector component=networkpolicies`. Before blaming a policy, ask the pod itself: `kubectl exec deploy/<name> -- wget -qO- http://<its own pod IP>:<port>/<health path>` answers when the process is listening. |

---

## 2. Context Gateway & Authorization

| Symptom / Error | Probable Root Cause | Verification Command | Remediation |
|---|---|---|---|
| HTTP 404 on existing entity | Security existence-masking active; user lacks read grant | Check gateway logs: `kubectl logs -l app.kubernetes.io/name=context-gateway` | Verify user's group assignments. If user should have access, grant read permissions in a `Policy` entity ([R20](../Requirements/access-control.md#5-requesting-extra-data)). |
| HTTP 403 Forbidden | Request operation or attribute set not covered by policy grants | Inspect returned RFC 7807 problem document | Check matching policy URN in gateway decision logs. Adjust policy constraints. |
| Token Audience Mismatch (`-32001`) | Client token lacks required RFC 8707 audience | Inspect JWT `aud` claim via `jwt.io` | Ensure client requests token with `audience=https://{host}/api/endpoint/{endpointSlug}`. |
| AST Rewriter Parser Error (HTTP 400) | Invalid syntax in incoming `q` expression | Check gateway logs for `antares-ql::parse_error` | Ensure query adheres to ETSI GS CIM 009 clause 4.9 syntax. |

---

## 3. Reconciler (`jcctl`) & GitOps

| Symptom / Error | Probable Root Cause | Verification Command | Remediation |
|---|---|---|---|
| `jcctl plan` non-empty after apply | Unmanaged telemetry attributes flagged as drift | Run `jcctl plan --diff` | Declare telemetry attributes in `metadata.managedAttributes` to exclude from GitOps diffing ([CC-69](../Requirements/city-as-code.md#11-interaction-lanes-and-sandboxes)). |
| Apply stalls on Wave 4 | Prerequisite Context Space in Wave 1 failed to initialize | Run `jcctl status --detailed` | Check Context Broker logs. Verify database storage quota has not been exceeded. |
| Merge request auto-merge fails | CI Conftest policy check failed or branch protection blocked merge | Check Gitea Actions pipeline log | Review Conftest violation (e.g. quota exceeded or unapproved role). |

---

## 4. Pipeline Runners (Bento)

| Symptom / Error | Probable Root Cause | Verification Command | Remediation |
|---|---|---|---|
| Runner Pod OOMKilled | Stream processing excessive in-memory batch size | `kubectl describe pod -l app.kubernetes.io/name=pipeline-runner` | Tune Bento `batching` buffer sizes or increase runner memory request in `platform-settings.yaml`. |
| MQTT Ingestion Times Out | NetworkPolicy blocking egress from pipeline runner | `kubectl logs -l app.kubernetes.io/name=pipeline-runner` | Add external MQTT broker IP/port to runner's egress NetworkPolicy allowlist. |
| Scheduled CronJob fails to start | Previous execution still running with `Forbid` concurrency | `kubectl get cronjob,pods -n joinedcontext` | Check for stalled connections; set appropriate `activeDeadlineSeconds` in `pipeline.yaml`. |

---

## 5. CloudNativePG & Database

| Symptom / Error | Probable Root Cause | Verification Command | Remediation |
|---|---|---|---|
| Read-only database error | Disk utilization exceeded 95% threshold | `kubectl get pvc -n joinedcontext` | Expand PVC storage size in Helmfile values ([Operations Runbook 9](../Operations/01-runbooks.md#9-runbook-9-disk-full-on-cloudnativepg-cluster)). |
| Standby replica lagging | High write volume or network congestion between pods | `kubectl cnpg status postgres-cluster -n joinedcontext` | Check PostgreSQL replication lag metrics via Prometheus. |

## Related

- [stack verdict S7](../Research/city-as-code-stack.md) — referenced above.
- [03-deployment-requirements.md#security](../Deployment/01-prerequisites.md) — referenced above.
- [R20](../Requirements/access-control.md) — referenced above.
- [CC-69](../Requirements/city-as-code.md) — referenced above.
- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
