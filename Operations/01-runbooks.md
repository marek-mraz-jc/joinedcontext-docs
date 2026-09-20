---
sidebar_position: 2
title: Operational Runbooks
description: Step-by-step diagnostic and remediation procedures for platform alerts, outages, and emergency operations.
---

# Operational Runbooks

This document contains standard operating procedures (SOPs) for responding to alerts, mitigating service interruptions, and conducting emergency administrative tasks.

---

## 1. Runbook 1: Configuration Drift Detected

### Symptoms

- Prometheus alert `CityConfigurationDriftDetected` firing.
- Portal UI displays a warning chip: **"Configuration Drift Detected"** on a Context Space.
- `jcctl drift` returns non-zero status with field diffs.

### Diagnosis

1. Execute drift inspection via `jcctl`:

   ```bash
   jcctl plan --repo-dir ./helsinki-repo --gateway-url http://context-gateway:9090
   ```

2. Identify the modified resources:
   - If an entity property modified by a live pipeline is flagged as drift, check whether the attribute is declared in `metadata.managedAttributes` ([CC-69](../Requirements/city-as-code.md#11-interaction-lanes-and-sandboxes)).
   - If an unauthorized out-of-band edit was made directly to the Context Broker (e.g. via internal listener), note the user and timestamp from audit logs.

### Remediation

- **Option A (Revert to Git Truth):** Overwrite live state with authoritative repository manifests:

  :::danger
  `--revert` discards every live change the repository does not describe. Export the drift first
  (Option B) if anyone might still need it.
  :::

  ```bash
  jcctl apply --revert --repo-dir ./helsinki-repo
  ```

- **Option B (Adopt Live State):** If the live change is legitimate, export the live state into a pull request:

  ```bash
  jcctl export --space <space-id> --out ./patches/drift-adopt.yaml
  # Create branch, commit patch, and open Yellow-Lane Merge Request
  ```

### Verification

Execute `jcctl plan --assert-empty`. The command must return zero diff.

---

## 2. Runbook 2: Apply Failed Mid-Wave

### Symptoms

- CI deployment job failed during `jcctl apply`.
- Portal UI flow status shows **"Error (Partial Apply)"**.
- Alert `CityReconcilerApplyFailed` firing.

### Diagnosis

1. Retrieve reconciler failure logs:

   ```bash
   kubectl logs -n joinedcontext -l app.kubernetes.io/name=jcctl --tail=200
   ```

2. Determine failing wave:
   - *Wave 1 (Spaces) / Wave 2 (Models) / Wave 3 (Seeds) / Wave 4 (Registrations) / Wave 5 (Subscriptions) / Wave 6 (Pipelines)*.
3. Common causes:
   - Target Context Space was deleted or unreachable.
   - Invalid JSON-LD `@context` URL returned HTTP 404 or timed out.
   - Resource quota reached on Context Broker backend.

### Remediation

1. The platform reconciler is designed to fail safe without corrupting preceding waves ([CC-18](../Requirements/city-as-code.md#3-reconciler-jcctl)).
2. Fix root cause in the repository (e.g. fix broken context URL or adjust quotas).
3. Push a commit to the merge request or re-run the failed CI apply pipeline.
4. `jcctl` will skip already-converged resources and resume reconciliation.

### Verification

Check flow status in Portal UI: status must transition from *Error* to *Live*.

---

## 3. Runbook 3: Endpoint Abuse & Rate-Limit Saturation

### Symptoms

- Influx of HTTP 429 Too Many Requests errors.
- Alert `GatewayRateLimitExceededHigh` firing.
- Latency spike on public endpoint route.

### Diagnosis

1. Inspect APISIX access logs filtered by endpoint slug:

   ```bash
   kubectl logs -n joinedcontext -l app.kubernetes.io/name=apisix -c apisix --tail=500 | grep "/api/endpoint/<slug>"
   ```

2. Identify abusive client IP addresses or compromised API tokens.

### Remediation

1. **Temporarily Tighten Rate Limit:** Update endpoint manifest with emergency limit:

   ```yaml
   # projects/mobility/spaces/parking/endpoints/public-feed.yaml
   spec:
     rateLimits:
       requestsPerMinute: 60 # Throttle from 1000
   ```

2. **Apply IP Blacklist in APISIX:** If an individual IP is conducting a denial-of-service attack, inject an emergency drop rule:

   ```bash
   jcctl emergency-block-ip --ip 198.51.100.24
   ```

3. Commit and merge the updated endpoint manifest.

### Verification

Monitor Prometheus metric `apisix_http_status{status="429"}`: rate limit enforcement drops backend load to safe thresholds.

---

## 4. Runbook 4: Emergency Revocation of Policy or Agent Identity

### Symptoms

- Security breach detected, credential leak, or AI agent hallucinating destructive actions.
- Immediate shutdown of access required.

### Diagnosis

Identify compromised identity did:web identifier, Keycloak service account, or `Policy` ID.

### Remediation

One script does all of it, in the only order that revokes anything, and it measures the
result ([OPS-45](../Requirements/operations.md),
[R48](../Requirements/policy-firewall.md#31-structural-gaps)):

:::warning
This bypasses the review lane and takes access away immediately. Everyone holding the policy
loses it in the same second, and step 4 is what stops the reconciler putting it back.
:::

```bash
scripts/emergency-revoke.sh --instance dev --policy public-read \
  --service-account helsinki-air-quality-conformance --idm https://idm.example.org \
  --verify-url "https://portal.example.org/api/endpoint/<slug>/ngsi-ld/v1/entities?type=X" \
  --verify-token-file .secrets/compromised-token
```

1. **The `Policy` leaves the repository the gateway reads.** An access token already issued
   stays cryptographically valid until it expires, so logging the subject out of Keycloak
   revokes nothing on its own: only the PDP can stop honouring the token. The script removes
   the manifest from the gateway's repository first.
2. **The gateway replicas re-read the repository.** The endpoint and policy table is read
   once at start-up and there is no invalidation endpoint yet, so the restart *is* the cache
   flush. A rollout that does not finish inside the bound is reported as a failed revocation,
   never as a success.
3. **Keycloak stops issuing new tokens.** Sessions are logged out for a user, the client
   secret is rotated for a service account. The script prints no token and no secret.
4. **Commit the revocation to Git.** Delete the manifest in the configuration repository as
   well, so the next reconcile does not bring the policy back.

### Verification

The script performs it: with `--verify-url` and `--verify-token-file` it calls the endpoint
with the compromised token until the answer is `401` or `403`, prints how long that took, and
exits non-zero when it is over the bound (5 seconds by default, per
[OPS-45](../Requirements/operations.md)).

---

## 5. Runbook 5: Secret Key Rotation

### Scope

Rotating the repository SOPS age encryption key, Keycloak client secrets, or PostgreSQL passwords.

### Procedure: SOPS age Master Key Rotation

1. Generate new age keypair:

   ```bash
   age-keygen -o new_key.txt
   ```

2. Add new public key to `.sops.yaml` alongside existing key.
3. Re-encrypt all secrets across the repository:

   ```bash
   find projects/ -name "*.enc.yaml" -exec sops updatekeys {} +
   ```

4. Update Kubernetes Secret holding the private key in cluster:

   ```bash
   kubectl create secret generic sops-age-key \
     --from-file=key.txt=new_key.txt \
     -n joinedcontext --dry-run=client -o yaml | kubectl apply -f -
   ```

5. Remove old public key from `.sops.yaml` and re-encrypt repository files once deployed.

### Verification

Decrypt one rotated file with the new key only (`sops -d projects/<p>/secrets/<file>.enc.yaml`), and
confirm the reconciler pod restarted cleanly and reports no `sops: no matching keys` error.

---

## 6. Runbook 6: CloudNativePG Database Failover & Restore

### Symptoms

- PostgreSQL primary pod crashed or node failure.
- Alert `PostgresClusterDegraded` or `CNPGFailoverTriggered`.

### Diagnosis

1. Inspect CloudNativePG cluster status:

   ```bash
   kubectl cnpg status postgres-cluster -n joinedcontext
   ```

2. Verify if automatic failover promoted a healthy standby replica.

### Remediation (Manual Failover)

If primary is unresponsive and operator promotion has stalled:

```bash
kubectl cnpg promote postgres-cluster <healthy-replica-pod> -n joinedcontext
```

### Remediation (Point-In-Time Recovery from S3)

If data was corrupted or deleted, the cluster is bootstrapped again from the WAL archive at the
last good instant (OPS-10). It keeps its name — every component connects to
`postgres-cluster-rw` — so the damaged `Cluster` object has to be gone before the restored one
is applied, and the restored one must archive somewhere else than it reads from.

1. Choose the instant, inside the 30-day retention window, and write it down as an ISO 8601
   string in UTC: `2026-08-15T14:30:00Z`. `kubectl cnpg status postgres-cluster -n joinedcontext`
   shows the oldest and newest backup the archive holds.

2. Stop the writers so nothing reconnects into a half-recovered database:

   ```bash
   kubectl scale deploy/portal deploy/context-gateway --replicas=0 -n joinedcontext
   ```

3. Set the restore in `deployment/environments/<env>/global.yaml.gotmpl`. The new
   `backups.destinationPath` is what keeps the restored cluster from writing its own WAL over
   the history it is reading, which would leave nothing to restore from a second time:

   ```yaml
   postgres:
     cluster:
       backups:
         destinationPath: 's3://<bucket>/postgres-restored-2026-08-15'
       recovery:
         enabled: true
         sourceCluster: 'postgres-cluster'
         targetTime: '2026-08-15T14:30:00Z'
         destinationPath: 's3://<bucket>/postgres'
   ```

4. Delete the damaged cluster.

   :::danger
   Deleting the `Cluster` destroys its volumes, and everything written after the target time
   with them. If the instance still answers at all, take a final backup first
   (`kubectl cnpg backup postgres-cluster -n joinedcontext`): it is the only copy of that
   window.
   :::

   ```bash
   kubectl delete cluster postgres-cluster -n joinedcontext
   ```

5. Apply the restore and watch the recovery job replay the WAL:

   ```bash
   helmfile apply -e <env> --selector component=postgres
   kubectl cnpg status postgres-cluster -n joinedcontext
   ```

6. Once the data is verified, set `recovery.enabled` back to `false` and keep the new
   `backups.destinationPath`. Left on, it restores the same old instant again the next time the
   `Cluster` object is recreated.

The `recovery-test` environment of `joinedcontext-deployment` is this values change, rendered
and asserted on every push (`tests/test_postgres_recovery.py`), so the manifest above is known
to be valid before an incident needs it.

### Verification

`kubectl cnpg status postgres-cluster -n joinedcontext` reports one healthy primary and every
replica streaming, and a read through an Endpoint returns the entity written before the incident.

---

## 7. Runbook 7: Pipeline Runner Out-Of-Memory (OOMKilled)

### Symptoms

- Pods matching `pipeline-runner-*` in `CrashLoopBackOff`.
- Alert `PodOOMKilled` firing for a project pipeline runner.
- Bento streams halting processing.

### Diagnosis

1. Identify crashing container:

   ```bash
   kubectl describe pod -n joinedcontext -l app.kubernetes.io/name=pipeline-runner
   ```

2. Check memory consumption per stream using Bento metrics endpoint:

   ```bash
   kubectl exec -it <pod-name> -n joinedcontext -- curl -s http://localhost:4195/metrics | grep bento_memory
   ```

### Remediation

1. **Immediate Relief:** Increase project runner memory limits in `platform-settings.yaml`:

   ```yaml
   quotas:
     projects:
       mobility:
         runnerMemoryLimit: 2Gi # Increased from 1Gi
   ```

2. **Split Streams:** If a project hosts >50 streams, configure the reconciler to deploy a second runner replica partitioned by stream name ([Architecture Chapter 05](../Architecture/08-pipelines.md)).
3. Merge change and verify runner stabilizes.

### Verification

The runner pod stays `Running` across a full ingest window with no new `OOMKilled` restarts
(`kubectl get pods -n joinedcontext -l app.kubernetes.io/name=pipeline-runner`), and the stream lag
metric returns to its pre-incident level.

---

## 8. Runbook 8: Forge (Gitea) Outage (Handling Config Freeze)

### Symptoms

- Gitea pod unavailable or database partition.
- Portal UI reports: **"Configuration service unavailable (Read-Only Mode)"**.
- Alert `GiteaServiceUnreachable` firing.

### Operational Posture (CC-55)

Per architecture invariant **CC-55**, platform serving is completely decoupled from the configuration plane:

- **Broker & Gateway:** Continue serving live queries and accepting IoT writes unaffected.
- **Bento Pipelines:** Continue streaming data unaffected.
- **Configuration Changes:** Creating new spaces, modifying pipelines, and approving MRs are paused.

### Remediation

1. Check Gitea pod status:

   ```bash
   kubectl get pods -n joinedcontext -l app.kubernetes.io/name=gitea
   ```

2. Inspect Gitea database status in CloudNativePG.
3. If necessary, restart Gitea deployment:

   ```bash
   kubectl rollout restart deployment/gitea -n joinedcontext
   ```

### Verification

A `git push` to the org repository succeeds, the reconciler picks the commit up within one poll
interval, and the config freeze notice is removed from the Portal.

---

## 9. Runbook 9: Disk Full on CloudNativePG Cluster

### Symptoms

- PostgreSQL enters read-only emergency mode.
- PVC utilization > 95%.
- Alert `DiskSpaceRunningCriticallyLow`.

### Diagnosis

Check PVC capacity:

```bash
kubectl get pvc -n joinedcontext -l cnpg.io/cluster=postgres-cluster
```

### Remediation (Online Volume Expansion)

1. CloudNativePG supports dynamic volume expansion on StorageClasses with `allowVolumeExpansion: true`.
2. Edit storage size in Helmfile environment values:

   ```yaml
   postgres:
     cluster:
       storage:
         size: 100Gi # Increased from 50Gi
   ```

3. Apply via Helmfile:

   ```bash
   helmfile apply -e <env> --selector component=postgres
   ```

4. Confirm PVC expands automatically without database restart.

### Verification

`kubectl get pvc -n joinedcontext` shows the new capacity bound, the cluster leaves read-only mode,
and a write through an Endpoint succeeds.

## Related

- [CC-69](../Requirements/city-as-code.md) — referenced above.
- [R48](../Requirements/policy-firewall.md) — referenced above.
- [OPS-45](../Requirements/operations.md) — the 5-second revocation bound Runbook 4 measures.
- [Architecture Chapter 05](../Architecture/08-pipelines.md) — referenced above.
- [00-intro](00-intro.md) — operations overview.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
