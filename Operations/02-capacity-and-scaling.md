---
sidebar_position: 3
title: "Capacity Planning & Autoscaling"
---

# Capacity Planning & Autoscaling

Guidelines for scaling platform components to meet traffic and storage demands.

## 1. Horizontal Pod Autoscaling (HPA)

The Context Gateway and APISIX scale horizontally based on request volume and CPU utilization:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: context-gateway-hpa
  namespace: prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: context-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
```

## 2. Pipeline Runner Resource Budgeting

Bento runners execute in Streams Mode within a shared pod per project. Budget memory based on active stream concurrency:

- **Baseline Overhead**: 50 MiB per runner process.
- **Idle Stream**: ~15–30 MiB per stream.
- **Active Ingestion Stream (MQTT / HTTP)**: ~50–100 MiB per stream under load.
- **Quota Rule**: Configure a maximum of 50 streams per runner deployment; when a project exceeds 50 streams, `jcctl` schedules a second runner pool automatically.

## 3. Temporal Storage Pruning

PostgreSQL temporal history tables require automated partition pruning. Configure retention in `platform-settings.yaml`:

```yaml
temporalRetention:
  defaultDays: 90
  rules:
    - entityType: "AirQualityObserved"
      retentionDays: 365
    - entityType: "RawTelemetry"
      retentionDays: 14
```

## Related

- [00-intro](00-intro.md) — operations overview.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
