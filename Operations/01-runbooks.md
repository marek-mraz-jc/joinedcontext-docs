---
sidebar_position: 2
title: Operational Runbooks
description: Step-by-step diagnostic and remediation procedures for platform alerts, outages, and emergency operations.
---

# Operational Runbooks

Step by step procedures for the nine failures an operator of a joinedcontext instance meets. Each one names what you see, what to look at, what to change and how to know it worked.

Two things to fix before you need them. Prometheus scraping is off unless an environment sets `global.metrics.enabled: true`, and the only alert rules this deployment ships are the two APISIX ones in `components/monitoring/values/monitoring/base-values.yaml.gotmpl`; every other symptom below is something a person notices, not something that pages them. And the namespace in the commands is the instance's own: `global.instanceSlug` (`dev` by default) with `global.singleNamespace: true`, or `<instanceSlug>-<component>` when it is false. The examples write `-n dev`.

---

## 1. Runbook 1: Configuration Drift Detected

### Symptoms

- `jcctl drift` reports resources whose live state no longer matches the repository.
- A Context Space in the Portal shows a drift warning.
- Somebody changed something through a door that does not write the repository.

### Diagnosis

1. Ask the repository what it expects, against live state:

   ```bash
   jcctl drift --repo-dir ./<organization-repo> \
     --gateway-url http://context-gateway.dev.svc.cluster.local:8080 \
     --token-file .secrets/jcctl-token --json
   ```

2. Identify the modified resources:
   - If an entity property modified by a live pipeline is flagged as drift, check whether the attribute is declared in `metadata.managedAttributes` ([CC-69](../Requirements/city-as-code.md#11-interaction-lanes-and-sandboxes)).
   - If an unauthorized out-of-band edit was made directly to the Context Broker (e.g. via internal listener), note the user and timestamp from audit logs.

### Remediation

- **Revert to what the repository says.** Re-apply the manifests; the live change is gone.

  :::danger
  This discards every live change the repository does not describe. Write the drift out first
  (below) if anyone might still need it.
  :::

  ```bash
  jcctl apply --repo-dir ./<organization-repo> \
    --gateway-url http://context-gateway.dev.svc.cluster.local:8080 \
    --token-file .secrets/jcctl-token
  ```

- **Adopt the live change.** Write the drifted resources out as manifests and open a merge request with them:

  ```bash
  jcctl drift --repo-dir ./<organization-repo> \
    --gateway-url http://context-gateway.dev.svc.cluster.local:8080 \
    --token-file .secrets/jcctl-token \
    --adopt-dir ./patches/drift-adopt
  # commit what it wrote, open the merge request, let its lane decide who approves
  ```

### Verification

`jcctl drift` prints no drifted resource, and `jcctl plan` against the same checkout reports nothing to change.

---

## 2. Runbook 2: Apply Failed Mid-Wave

### Symptoms

- `jcctl apply` in CI exited non-zero part way through.
- A resource in the Portal is stuck short of Live.

### Diagnosis

1. Retrieve reconciler failure logs:

   ```bash
   # the reconciler runs inside the Portal process, so its lines are the Portal's
   kubectl logs -n dev -l app.kubernetes.io/name=portal --tail=200
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

- Callers of one Endpoint receive `429` with a `Retry-After` header.
- `APISIXHigh5xxRate` fires, or latency on the public route rises.

### Diagnosis

1. Inspect APISIX access logs filtered by endpoint slug:

   ```bash
   kubectl logs -n dev -l app.kubernetes.io/name=apisix -c apisix --tail=500 \
     | grep "/api/endpoint/<slug>"
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

   The gateway keys one bucket per Endpoint and caller, the caller being the presented credential or, without one, the client address the edge saw. An anonymous flood from one address is bounded by the address bucket; a flood from many addresses is bounded per Endpoint only by what you set here.

2. **Block an address at the edge.** There is no platform command for this. APISIX carries the rule: add the `ip-restriction` plugin to the route in `components/<component>/apisix-routes.yaml` in `joinedcontext-deployment` and apply the component. Write down why and when to remove it.

3. Commit and merge the updated Endpoint manifest; the gateway re-reads it within a second.

### Verification

The endpoint answers `429` with `RateLimit-Limit`, `RateLimit-Remaining` and `Retry-After` while the flood lasts, and the broker's load falls. With metrics on, `apisix_http_status{status="429"}` counts it.

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

## 5. Runbook 5: Rotating the SOPS age key and other secrets

### Scope

The age key that decrypts the deployment repository's `secrets.enc.yaml`, Keycloak client secrets, and PostgreSQL passwords.

### The age key never enters the cluster

Encrypted values are resolved by `vals` while `helmfile` templates or applies, so the plaintext exists only in that process's memory and the private key belongs to whoever runs it (`SOPS_AGE_KEY_FILE`, or a workflow secret in CI). There is no Kubernetes Secret holding it, and rotating it changes nothing inside the cluster until the next apply.

### Procedure

1. Generate the new keypair and read its recipient:

   ```bash
   age-keygen -o .secrets/age-<env>-new.key     # mode 600, never committed
   recipient=$(age-keygen -y .secrets/age-<env>-new.key)
   ```

2. Add the new recipient beside the old one in `.sops.yaml` of `joinedcontext-deployment`, so both keys decrypt while the rotation is in progress.

3. Re-encrypt every file to both recipients:

   ```bash
   find deployment/environments -name 'secrets.enc.yaml' -exec sops updatekeys -y {} +
   ```

4. Hand the new key to everybody and everything that applies: the operators' `.secrets/`, and the repository secret the CI workflow reads.

5. Render with the new key alone, then remove the old recipient from `.sops.yaml` and re-encrypt once more:

   ```bash
   SOPS_AGE_KEY_FILE=.secrets/age-<env>-new.key \
     scripts/render.sh <env> /tmp/rendered.yaml
   ```

### Keycloak client secrets and database passwords

A generated secret is rotated by the platform rather than by hand: delete the Kubernetes Secret the component owns and apply the component again, which generates a new value and rolls the workloads that mount it. A client secret a department holds is rotated with `scripts/emergency-revoke.sh --service-account <client>`, which is Runbook 4.

### Verification

`scripts/render.sh` with only the new key set renders without a `sops` error, the components that mount a rotated secret come back up, and a login through the Portal still works.

---

## 6. Runbook 6: CloudNativePG Database Failover & Restore

### Symptoms

- The PostgreSQL primary pod is gone or its node failed.
- `kubectl cnpg status postgres-cluster` shows no healthy primary, or reads and writes fail at the Endpoint.

### Diagnosis

1. Inspect CloudNativePG cluster status:

   ```bash
   kubectl cnpg status postgres-cluster -n dev
   ```

2. Verify if automatic failover promoted a healthy standby replica.

### Remediation (Manual Failover)

If primary is unresponsive and operator promotion has stalled:

```bash
kubectl cnpg promote postgres-cluster <healthy-replica-pod> -n dev
```

### Remediation (Point-In-Time Recovery from S3)

If data was corrupted or deleted, the cluster is bootstrapped again from the WAL archive at the
last good instant (OPS-10). It keeps its name — every component connects to
`postgres-cluster-rw` — so the damaged `Cluster` object has to be gone before the restored one
is applied, and the restored one must archive somewhere else than it reads from.

1. Choose the instant, inside the 30-day retention window, and write it down as an ISO 8601
   string in UTC: `2026-08-15T14:30:00Z`. `kubectl cnpg status postgres-cluster -n dev`
   shows the oldest and newest backup the archive holds.

2. Stop the writers so nothing reconnects into a half-recovered database:

   ```bash
   kubectl scale deploy/portal deploy/context-gateway --replicas=0 -n dev
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
   (`kubectl cnpg backup postgres-cluster -n dev`): it is the only copy of that
   window.
   :::

   ```bash
   kubectl delete cluster postgres-cluster -n dev
   ```

5. Apply the restore and watch the recovery job replay the WAL:

   ```bash
   helmfile apply -e <env> --selector component=postgres
   kubectl cnpg status postgres-cluster -n dev
   ```

6. Once the data is verified, set `recovery.enabled` back to `false` and keep the new
   `backups.destinationPath`. Left on, it restores the same old instant again the next time the
   `Cluster` object is recreated.

The `recovery-test` environment of `joinedcontext-deployment` is this values change, rendered
and asserted on every push (`tests/test_postgres_recovery.py`), so the manifest above is known
to be valid before an incident needs it.

### Verification

`kubectl cnpg status postgres-cluster -n dev` reports one healthy primary and every
replica streaming, and a read through an Endpoint returns the entity written before the incident.

---

## 7. Runbook 7: Pipeline Runner Out-Of-Memory (OOMKilled)

### Symptoms

- Pods matching `pipeline-runner-*` restart, with `OOMKilled` as the last state.
- Ingestion stops and the pipeline's Live status in the Portal goes stale.

### Diagnosis

1. Identify crashing container:

   ```bash
   kubectl describe pod -n dev -l app.kubernetes.io/name=pipeline-runner \
     | grep -A3 "Last State"
   ```

2. Read what the runner itself reports. Bento serves `/metrics` on port 4195, the same port as its stream API:

   ```bash
   kubectl exec -n dev <pod-name> -- wget -qO- http://localhost:4195/metrics | head -40
   ```

### Remediation

1. **Give the pipeline more room.** A `Pipeline` manifest carries its own ceiling, which is a merge request like any other change:

   ```yaml
   # projects/mobility/pipelines/traffic-sensor/pipeline.yaml
   spec:
     quotas:
       maxMemoryMb: 2048 # the runner default is a 1024Mi limit (PL-11)
   ```

2. **Raise the pool's own limit** when every stream in it grew, in `components/pipeline-runner/values/runner/<env>-values.yaml.gotmpl` of `joinedcontext-deployment`, and apply the component. The default is a 256Mi request and a 1024Mi limit.
3. **Split the pool.** A pool holds at most 50 resident streams (PL-12). Past that, move streams to a second pool in the repository; nothing partitions them by itself ([Architecture chapter 08](../Architecture/08-pipelines.md)).

### Verification

The runner pod stays `Running` across a full ingest window with no new `OOMKilled` restarts
(`kubectl get pods -n dev -l app.kubernetes.io/name=pipeline-runner`), and the stream lag
metric returns to its pre-incident level.

---

## 8. Runbook 8: Forge (Gitea) Outage (Handling Config Freeze)

### Symptoms

- The Gitea pod is unavailable, or its database is.
- Proposing or approving a change in the Portal fails; reading data does not.

### Operational Posture (CC-55)

Per architecture invariant **CC-55**, platform serving is completely decoupled from the configuration plane:

- **Broker & Gateway:** Continue serving live queries and accepting IoT writes unaffected.
- **Bento Pipelines:** Continue streaming data unaffected.
- **Configuration Changes:** Creating new spaces, modifying pipelines, and approving MRs are paused.

### Remediation

1. Check Gitea pod status:

   ```bash
   kubectl get pods -n dev -l app.kubernetes.io/name=gitea
   ```

2. Inspect Gitea database status in CloudNativePG.
3. If necessary, restart Gitea deployment:

   ```bash
   kubectl rollout restart deployment/gitea -n dev
   ```

### Verification

A `git push` to the org repository succeeds, the reconciler picks the commit up within one poll
interval, and the config freeze notice is removed from the Portal.

---

## 9. Runbook 9: Disk Full on CloudNativePG Cluster

### Symptoms

- Writes fail and PostgreSQL logs a full volume.
- The cluster's PVC is above 95% used.

### Diagnosis

Check PVC capacity:

```bash
kubectl get pvc -n dev -l cnpg.io/cluster=postgres-cluster
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

`kubectl get pvc -n dev` shows the new capacity bound, the cluster leaves read-only mode,
and a write through an Endpoint succeeds.

## Related

- [CC-69](../Requirements/city-as-code.md) — referenced above.
- [R48](../Requirements/policy-firewall.md) — referenced above.
- [OPS-45](../Requirements/operations.md) — the 5-second revocation bound Runbook 4 measures.
- [Architecture Chapter 05](../Architecture/08-pipelines.md) — referenced above.
- [00-intro](00-intro.md) — operations overview.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
