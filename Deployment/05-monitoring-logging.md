---
sidebar_position: 6
title: "Monitoring, Logging & Observability"
---

# Monitoring, Logging & Observability

Observability across the platform is built on standard Prometheus metrics scraping, OpenTelemetry distributed tracing, and structured JSON logging.

## 1. Metrics Architecture

Platform components export Prometheus metrics on dedicated endpoints. When `global.metrics.enabled: true` is set, `PodMonitor` and `ServiceMonitor` resources are created automatically.

| Component | Metric Endpoint | Key Exposed Metrics |
|---|---|---|
| **Context Gateway** | `:8080/metrics` | `jc_gateway_requests_total{route,method,endpoint,status}`<br/>`jc_gateway_request_duration_seconds{route,method,endpoint}`<br/>`jc_gateway_pdp_decisions_total{operation,verdict}`<br/>`jc_gateway_broker_request_duration_seconds{reached}` |
| **Portal** | `:8080/metrics` | `jc_portal_requests_total{route,method,status}`<br/>`jc_portal_request_duration_seconds{route,method}`<br/>`jc_portal_changes_total{lane,kind}` |
| **Antares Broker** | `:8080/q/metrics` | `antares_http_requests_total`<br/>`antares_http_request_duration_seconds`<br/>`antares_notifications_sent_total`<br/>`antares_pg_pool_timeouts_total` |
| **APISIX Standalone** | `:9091/apisix/prometheus/metrics` | `apisix_http_status`<br/>`apisix_latency_bucket`<br/>`apisix_bandwidth` |
| **Bento Runners** | `:4195/metrics` | `bento_processor_latency`<br/>`bento_input_received_total`<br/>`bento_output_sent_total` |
| **PostgreSQL (CNPG)** | `:9187/metrics` | `cnpg_pg_stat_database_xact_commit`<br/>`cnpg_pg_replication_lag` |

Three things about that table are load-bearing:

- **The scrape port is the service port.** The Gateway and the Portal answer `/metrics` on the
  same `http` port they answer everything else on, so the `ServiceMonitor` names the port and
  not a number. `/metrics` is never published at the edge: APISIX terminates the Portal's
  scrape path with a 404, and the Gateway's routes are `/cs/*` and `/api/endpoint/*` only.
- **The Broker's path is `/q/metrics`,** beside `/q/health` and `/q/ready`, and Antares builds
  no recorder at all unless `ANTARES_TELEMETRY` is set in its environment. A Broker started
  without it answers 404 on a path that is otherwise correct.
- **Every `_duration_seconds` above is a Prometheus histogram, not a summary.** A summary
  exports a quantile that is already computed inside one replica, and quantiles from several
  replicas cannot be combined — the p95 of a Gateway that the HPA has scaled to three pods is
  not the average of three p95s. Buckets can be summed, so a dashboard reads latency as
  `histogram_quantile(0.95, sum(rate(<series>_bucket[5m])) by (le, route))` and stays correct
  however many replicas are running.

## 2. Service Level Objectives (SLOs)

Production environments must be monitored against the following performance budgets:

- **Context Gateway Overhead**: p95 ≤ 3ms, p99 ≤ 8ms (excluding underlying broker execution time).
- **Broker Entity Retrieval**: p95 ≤ 15ms, p99 ≤ 50ms for point queries (`GET /entities/{id}`).
- **CaC Sync Latency (Green Lane)**: Form save to active broker state ≤ 5 seconds.
- **Pipeline Processing**: Ingestion to context availability ≤ 100ms for resident streams.

## 3. Centralized Logging

All custom components (Context Gateway, Portal API, `jcctl`, Bento) emit structured JSON to `stdout`.

### JSON Log Schema Example

```json
{
  "timestamp": "2026-08-20T10:15:30.123Z",
  "level": "INFO",
  "component": "context-gateway",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "tenant": "mobility",
  "endpoint_slug": "d8a1f9e2c3b4",
  "action": "queryEntity",
  "verdict": "REWRITE",
  "matched_policy": "urn:ngsi-ld:Policy:hel.fi:parking:parking-read-v1",
  "duration_ms": 2.45
}
```

:::caution Log Redaction Rules
Headers containing authentication secrets (`Authorization`, `X-API-KEY`, `Cookie`) and payload attributes flagged with privacy markers (`DPV:PersonalData`) are automatically scrubbed by the Context Gateway logger.
:::

### The audit trail sink (OPS-42, R42, AG-19)

`stdout` is where a component writes; it is not where an auditor reads. The `audit-logging` component runs a Vector daemonset on every node. It reads the container logs of three components, parses the JSON above, annotates each record with the pod, namespace and node it came from, and writes the result to object storage:

| | |
|---|---|
| Read from | the pods of `context-gateway`, `keycloak` and `gitea` |
| Written to | `s3://{bucket}/audit/{component}/{date}/`, gzipped newline-delimited JSON |
| Retention | 90 calendar days, Object Lock in compliance mode |

Everything else keeps writing to `stdout` for whatever the operator scrapes; the audit stream is the one this component owns. A record joins it because of the pod it came from, never because of what it says, so no component can drop itself out of the trail by changing what it logs. The gateway's `trace_id` is what correlates a denied request, the MCP tool call that made it and the policy that matched (R42, AG-19).

The audit bucket carries S3 Object Lock in compliance mode with a 90 day default retention (OPS-42). Compliance mode is the point: governance mode lets a sufficiently privileged account shorten a lock, and an audit trail an administrator can shorten is not one. The collector's credential grants `PutObject` alone and arrives by `secretRef` like every other credential, so the collector cannot read, overwrite or delete what it has already shipped.

Timestamps are parsed as RFC 3339 and stored in UTC. A record whose `timestamp` does not parse keeps its ingest time and is tagged rather than dropped, because a malformed audit record is still evidence.

## 4. Recommended Alert Rules

Deploy these rules via `PrometheusRule` in your monitoring stack:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: joinedcontext-platform-alerts
  namespace: prod
spec:
  groups:
    - name: platform-health
      rules:
        - alert: GatewayHighLatency
          expr: histogram_quantile(0.99, sum(rate(gateway_request_duration_seconds_bucket[5m])) by (le)) > 0.05
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "Context Gateway p99 latency exceeded 50ms"

        - alert: CityctlReconciliationFailure
          expr: increase(jcctl_reconcile_errors_total[15m]) > 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "jcctl failed to converge Git state to cluster"

        - alert: APISIXConfigReloadFailed
          expr: apisix_yaml_configuration_load_status == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "APISIX standalone failed to reload apisix.yaml (check #END marker)"
```

## 5. The activity pipeline

Metrics answer "how much" and logs answer "what exactly"; the Activity stream
([Architecture/09 §6](../Architecture/09-portal.md#6-activity-what-is-happening)) answers "what
is happening in my project" for a person who will not open either. This section is the plumbing
that fills it.

### Shape

```text
Antares broker  ┐
context-gateway ├─ OTLP logs ─→ OpenTelemetry Collector ─→ OTLP/HTTP ─→ Portal ─→ activity table
Bento runners   ┘  (one record    (allow-list, batching)     (ingest route)
                    per event)

reconciler     ┐
               ├──────── direct INSERT (both run inside the Portal) ─────────→ activity table
CKAN publisher ┘
```

The collector runs in `components/observability/`, from the contrib image pinned by digest. It
does three things and is asked for no fourth: it accepts OTLP, it deletes every attribute that is
not on the allow-list, and it forwards what is left to the Portal. It holds no database
credential, writes no row, and decides nothing about what an event means.

### An emitter names its own events

Each source emits an activity event as an OTLP **log record** whose attributes are the fields of
[Architecture/09 §6](../Architecture/09-portal.md#6-activity-what-is-happening), beside the span
and the log line it already writes. Nothing asks the collector to infer `federation.error` from a
span name.

Two reasons, and the first is the one that would still hold on a collector that could do
anything. The component that knows what happened is the one it happened to: a broker knows a
forward was cut off by the loop guard, and a collector rule reconstructing that from a span's
status code is a guess with a configuration file around it. The second is arithmetic about a
released image. The contrib distribution has no connector that turns a span into a log and no
exporter that writes to SQL — its whole SQL surface is the `sqlquery` receiver, which reads — so
a pipeline built on either could not be pinned to a digest, and an unpinnable image is not a
deployment (OPS-28).

| Emitter | Emits |
|---|---|
| Antares broker | `federation.forward`, `federation.error` |
| context-gateway | `endpoint.traffic` once a minute per endpoint, `access.denied`, `mcp.tool` |
| Bento runners | `pipeline.throughput` once a minute per stream, `pipeline.error`, `pipeline.restarted` |
| reconciler, CKAN publisher | `config.*`, `change.merged`, `catalogue.published`, straight to the table |
| Portal | `mcp.tool` for an answered elicitation, `agent.answer` for an answered `jc_ask` question, straight to the table |

The per-minute records carry counters the emitter already keeps for its Prometheus endpoint
(OPS-16). One line a minute is cheaper than teaching a collector to aggregate, and it keeps the
number in the Activity stream and the number on the dashboard the same number.

`project`, `space` and `correlationId` ride on the record; `correlationId` is the W3C trace id of
the span the event belongs to (OPS-17), so one event still opens the whole trace. A record
carrying no `project` is dropped rather than filed under a guess.

### The attribute allow-list

The collector keeps the named attributes and deletes every other one (OPS-48). It is an
allow-list and not a deny-list on purpose: a deny-list is a promise to have thought of every
attribute anyone will ever add, and the first forgotten one is a request body in a UI a citizen
can open. An attribute that is not on the list does not reach the Portal, so a new span attribute
is invisible until somebody adds it deliberately, which is the failure mode to prefer.

The list is the event's own fields and nothing besides: `project`, `space`, `kind`, `source`,
`summary`, `severity`, `correlationId`, `details`. None of them is a body, a header, a cookie, a
token or an entity attribute value. The one sample that does reach an event, the failing message
of a `pipeline.error`, is masked by the Data Model's own rules inside `details` before the runner
emits it, so the collector never sees the raw form.

### How the collector reaches the Portal

The ingest route ([API/01 §14](../API/01-portal-api.md#14-activity-ui-31-ops-48-ops-49)) belongs
to the Portal, so the collector authenticates like every other workload: a Keycloak
ServiceAccount client, the client-credentials grant, an audience-bound token it refreshes itself.
No static key crosses the cluster. The Portal validates each record it is handed, because the
collector is the redaction hop and not a trusted one, and rejects a record whose `kind` is
outside the vocabulary instead of storing a word the UI cannot filter on.

### Retention

The Portal trims its own table on a timer: events older than seven days go, and the per-minute
counters they aggregate into are kept ninety days. Both are derived (OPS-49), so the trim deletes
rather than archives. It runs inside the Portal rather than as a CronJob because the schema has
one owner, and a scheduled pod would need a second database credential to delete rows the process
that wrote them can delete for free.

### Isolation

A NetworkPolicy names the workloads that may reach the collector, which is the broker, the
gateway and the Bento runners and nobody else. The collector has one egress that carries data,
the Portal, plus DNS and the identity provider it fetches its token from. No APISIX route
publishes it, so nothing outside the cluster can reach it at all: it reads telemetry from the
whole platform and writes nothing a browser sees without the Portal having validated it first.

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
