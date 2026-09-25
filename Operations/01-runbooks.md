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

The endpoint answers `429` with `RateLimit-Limit`, `RateLimit-Remaining` and `Retry-After` while the flood lasts, and the broker's load falls. With metrics on, `apisix_http_status{code="429"}` counts it.

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
   For a client the platform declares (edge, portal-api, the gateway, Grafana, Gitea …) the
   script also writes the new secret into every copy of the generated Secret
   `keycloak-client-<client>` and restarts the workloads that read it, because
   keycloak-config-cli imports the secret from that Secret on every apply and would otherwise
   write the revoked one back. Apply the platform afterwards: the forge's login source takes
   the new secret only then. A client the Portal created is rotated in Keycloak alone.
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

The age key that decrypts the deployment repository's `secrets.enc.yaml`, and every other credential the platform holds or uses, by class, with who rotates it (OPS-45).

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

### Every credential class, who rotates it and how the old one is refused

The generator writes a Secret only where no copy exists and copies the first copy it finds to every namespace, and nothing restarts a pod when a Secret changes. Deleting one copy and applying therefore changes nothing. `scripts/rotate-secret.sh` in `joinedcontext-deployment` does the whole rotation for every class the platform generates (OPS-45, T-1719):

1. It deletes every copy.
2. It applies the release that makes the Secret again, and the release that hands it to the other side.
3. It restarts every Deployment, StatefulSet and DaemonSet whose pods read the Secret.
4. It measures that the old value is refused and the new one accepted, within `--bound` seconds (60 by default), and exits `1` when it is not.

The value is never printed and never put on a command line. A Secret that carries no Helm release, and the classes the table names for another procedure, are refused before anything is deleted.

| Class | Secrets | Who rotates it | How | How the old one is refused |
|---|---|---|---|---|
| Platform OIDC client secrets | `keycloak-client-<client>` | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret keycloak-client-<client> --idm https://idm.<domain> --realm <realm>`: the generator makes a new secret and keycloak-config-cli writes it to the client | a `client_credentials` grant with the old secret answers `401` |
| Database passwords | `db-portal`, `db-keycloak`, `db-gitea`, `db-ckan`, `db-ckan-datastore-read`, `db-antares` | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret db-<name>`: CloudNativePG applies the new role password from the Secret | a login with the old password on the primary fails, and one with the new password succeeds |
| Forge tokens | `gitea-token-portal`, `gitea-token-gateway`, `gitea-token-lane-secret` | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret gitea-token-<name> --forge https://<domain>/git`: the forge bootstrap deletes the old token in Gitea by name and mints one | `/api/v1/user` answers `401` to the old token |
| The Portal's session key | `portal-cookie-key` | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret portal-cookie-key`: the old key stays in the Secret as `previous`, which the Portal reads as `JC_PORTAL_COOKIE_KEY_PREVIOUS`, so nobody is signed out (T-2842). Once the session lifetime has passed, `--drop-previous` removes it and restarts the Portal (Deployment/08, *Rotating the Portal's session key*). The next rotation replaces `previous`, so one retired key at most is held. | nothing outside the cluster to ask; the script checks that every copy changed |
| Session and signing keys | `apisix-oidc-session`, `ckan-session`, `artifact-store-root` | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret <name>`, then every reader restarts. Rotating these ends every session they signed: the edge sessions, CKAN's sessions and API tokens (its token Job mints a new one). A new artifact-store root re-derives every organization's keys. | nothing outside the cluster to ask; the script checks that every copy changed |
| Demo people | `keycloak-user-<name>` (development profile only) | the platform operator | `scripts/rotate-secret.sh --instance <env> --secret keycloak-user-<name>`: keycloak-config-cli writes the new password | the person's next login needs the new password |
| Department ServiceAccount keys | the ServiceAccount's keys in the Portal | the project's steward | the Portal's ServiceAccount page: add a key, move the caller, revoke the old one (both keys work in between) | revocation ends the old key at once; `service_account_api_tests.rs::rotation_keeps_both_keys_alive_and_revocation_ends_one_now` |
| A compromised credential, now | any of the above | whoever holds the cluster | Runbook 4, `scripts/emergency-revoke.sh`, then the row of its class | measured by the script within 5 s |
| Administrators | `gitea-admin-credentials`, `keycloak-admin-user` | the platform operator | written once at install and never reset by an apply (`initialOnlyNoReset`): change the password in Gitea or Keycloak first, then write the same value into every copy of the Secret, since keycloak-config-cli and the forge bootstrap log in with it. The script refuses them. | the old password fails the application's own login |
| Runner registration | `gitea-runner-registration` | the platform operator | reset the registration token in Gitea (site administration, runners), delete every copy of the Secret, apply `gitea-bootstrap`, restart the runner | the runner registers with the new token only |
| SOPS age key | the operators' `.secrets/` and the CI secret | the platform operator | the procedure above | a render with the new key alone succeeds |
| Model key | `agent-runner-model-key` | the owner, in the OpenRouter account | create a new key, write it with `kubectl create secret generic agent-runner-model-key --from-file=key=<file> --dry-run=client -o yaml \| kubectl apply -f -`, restart the agent proxy, then delete the old key in OpenRouter | the provider answers `401` to the deleted key |
| GitHub token of the board and the mirror | `.secrets/` and `github-app-mirror` | the owner, in the GitHub account | create the new token, replace the file and the Secret, restart the mirror, revoke the old token | GitHub answers `401` to the revoked token |
| Image signing | none | nobody | signing is keyless (GitHub OIDC in `reusable-container-sign.yml`), so there is no key to rotate; the trust is the workflow identity | not applicable |

`tests/test_rotate_secret.py` holds the script to this table against stubs. Proving each class on a running cluster is the ci-full `k3d-deploy` case: rotate, see the old value refused and the new one accepted.

### Verification

For the age key, `scripts/render.sh` with only the new key set renders without a `sops` error. For every other class, `scripts/rotate-secret.sh` ends with "the old value is refused" or names what failed; after it, a login through the Portal still works.

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

## 10. Runbook 10: Migrating an Organization from Layout 1 to Layout 2

Layout 2 moves every project of the organization's one repository into a repository of its own,
with its history, and leaves the organization repository with the project registry in its place
([ADR-N-029](../Decisions/adr-n-029-one-repository-per-project.md), CC-85, PF-85). `jcctl migrate`
is the only writer of the change; this runbook is the order around it.

### Symptoms

- The organization repository has no `.jc/layout`, or it says `1`, and a project has to be cloned,
  versioned or moved on its own (PF-87, CC-88, MF-45).

### Diagnosis

Read what will move, without writing anything:

```bash
git clone "https://gitea.<host>/<org>/city-config.git" city-config
cat city-config/.jc/layout 2>/dev/null || echo "no .jc/layout: layout 1"
ls city-config/projects/
jcctl validate --repo-dir city-config
```

A repository that does not validate is fixed first: the migration moves files and never repairs
them.

### Remediation

1. **Freeze the organization.** Announce the window and stop approving Changes until step 5, so
   no merge lands in a subtree while it is split. Take the mirror backup of
   [Deployment/07 Step 3](../Deployment/07-backup-restore.md#step-3-restore-the-configuration-repository-into-the-forge-cc-49-ops-11).
2. **Split.** `jcctl migrate` writes the organization repository in layout 2 and one repository per
   project, each the `git subtree split` of `projects/{slug}/`, so every commit that touched the
   project is in its own history:

   ```bash
   jcctl migrate --repo-dir city-config --out-dir migrated
   ls migrated/org migrated/projects
   ```

   Each `migrated/projects/{slug}` carries `.jc/layout` `2` and `project.yaml` at its root; the
   forge bootstrap adds the CI workflow of CC-90 and `CODEOWNERS` when it creates the repository.
   `migrated/org` carries `projects/{slug}.yaml`, each entry tracking its project's `main`, and no
   `projects/{slug}/` directory. `jcctl migrate` prints each repository and the commit it ends
   at; keep that list for the verification.
3. **Create and push the project repositories.** The forge bootstrap creates each repository with
   its teams (PF-87, PF-88); push each split to its `main`:

   ```bash
   for dir in migrated/projects/*/; do
     slug=$(basename "$dir")
     git -C "$dir" push "https://gitea.<host>/<org>/$slug.git" HEAD:main
   done
   ```

4. **Land the organization change.** `migrated/org` goes to the organization repository as one
   red-lane Change that an `org-admin` approves: the registry entries in, the project subtrees
   out, `.jc/layout` set to `2`.

   **Warning:** the organization Change removes every `projects/{slug}/` subtree from the
   organization repository's `main`. Push it only after step 3 answered for every project, and
   keep the mirror of step 1 until the verification below is green; the removed files stay in the
   organization repository's history, and the mirror restores the whole repository if the
   migration has to be abandoned.

   ```bash
   git -C migrated/org push "https://gitea.<host>/<org>/city-config.git" HEAD:migrate/layout-2
   ```

5. **Unfreeze.** Approve the Change; the reconciler assembles the organization from the
   registry (CC-86) and Changes open against the project repositories from now on (CC-87).

### Verification

Every project's `main` at the forge is the head `jcctl migrate` wrote, and the assembled render
declares the same resources as before, so nothing is created or deleted:

```bash
for dir in migrated/projects/*/; do
  slug=$(basename "$dir")
  test "$(git ls-remote "https://gitea.<host>/<org>/$slug.git" main | cut -f1)" \
       = "$(git -C "$dir" rev-parse HEAD)" && echo "$slug equal"
done
jcctl plan --repo-dir migrated/org
```

`jcctl plan` reports no change, every Endpoint keeps its slug and every space its `{space}`
segment (PF-84), and each project's registry entry shows `status` at its pinned ref.

## Related

- [CC-69](../Requirements/city-as-code.md) — referenced above.
- [R48](../Requirements/policy-firewall.md) — referenced above.
- [OPS-45](../Requirements/operations.md) — the 5-second revocation bound Runbook 4 measures.
- [Architecture Chapter 05](../Architecture/08-pipelines.md) — referenced above.
- [00-intro](00-intro.md) — operations overview.
- [08-security-hardening](../Deployment/08-security-hardening.md) — the baseline these procedures keep intact.
