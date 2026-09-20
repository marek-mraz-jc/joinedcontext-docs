---
sidebar_position: 8
title: "Backup, Disaster Recovery & Restore"
---

# Backup, Disaster Recovery & Restore

Disaster recovery is based on the separation of **declarative configuration** (persisted in Git), **secrets** (managed in OpenBao or SOPS), and **transactional state** (persisted in PostgreSQL).

## 1. Data Classification & Storage Matrix

| Data Class | Component | Persistent Store | Criticality | Recovery Objective |
|---|---|---|---|---|
| **Platform Configuration** | City Repo (`jcctl`) | Gitea Git Storage (PVC / Remote Git Mirror) | Critical | RPO = 0 (every commit is permanent)<br/>RTO ≤ 5 min |
| **Secrets & Keys** | Secrets Component | OpenBao / Encrypted SOPS in Git | Critical | RPO = 0<br/>RTO ≤ 10 min |
| **Context History & Entities** | Antares Broker / Portal | PostgreSQL (CNPG) | Critical | RPO ≤ 5 min (PITR)<br/>RTO ≤ 15 min |
| **Git Repositories & PRs** | Gitea | PostgreSQL (Metadata) + PV (Git bare repos) | High | RPO ≤ 1 hour<br/>RTO ≤ 30 min |
| **Pipelines & Streams** | Bento Runners | Stateless (Config mounted from ConfigMap) | Low | RPO = 0 (Instant re-creation from Git) |

## 2. Automated PostgreSQL Backups via CNPG

CloudNativePG manages continuous physical base backups and WAL archiving to S3-compatible object storage:

An operator turns it on per environment; the component values render the CNPG `Cluster` from it,
with gzip and AES256 on both the WAL and the base backups and a daily base backup at 03:00:

```yaml title="deployment/environments/<env>/global.yaml.gotmpl"
postgres:
  cluster:
    backups:
      enabled: true
      endpointURL: 'https://s3.region.example.com'
      destinationPath: 's3://city-backups-bucket/postgres'
      region: 'eu-central-1'
      bucket: 'city-backups-bucket'
      retentionPolicy: '30d'
      # The keys are never in these values: the Secret carries ACCESS_KEY_ID and
      # ACCESS_SECRET_KEY and is supplied by the operator (ADR-N-012).
      existingSecret: 'postgres-backup-s3'
```

Trigger an on-demand snapshot:

```bash
kubectl apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: backup-manual-$(date +%Y%m%d%H%M)
  namespace: prod
spec:
  cluster:
    name: postgres-cluster
EOF
```

## 3. Disaster Recovery Procedure

To restore an entire organisational instance from scratch on a blank Kubernetes cluster:

### Step 1: Provision Base Infrastructure & Restore Secrets

Deploy cluster operators (Linkerd, CNPG, cert-manager) and inject the root SOPS/OpenBao decryption key into the namespace.

### Step 2: Bootstrap PostgreSQL via Point-in-Time Recovery (PITR)

Point the same environment file at the archive and at the instant to recover to (OPS-10). The
cluster keeps its name, so the restored one archives to a fresh path instead of writing over the
history it is reading:

```yaml title="deployment/environments/<env>/global.yaml.gotmpl"
postgres:
  cluster:
    backups:
      destinationPath: 's3://city-backups-bucket/postgres-restored-2026-08-20'
    recovery:
      enabled: true
      sourceCluster: 'postgres-cluster'
      targetTime: '2026-08-20T12:00:00Z'
      destinationPath: 's3://city-backups-bucket/postgres'
```

`helmfile apply -e <env> --selector component=postgres` bootstraps the cluster from the object
store: CNPG downloads the physical snapshot and replays WAL segments up to `targetTime`, an ISO
8601 instant inside the retention window. The step-by-step procedure, including what to do with
the damaged cluster and how to leave the restore behind afterwards, is
[Runbook 6](../Operations/01-runbooks.md).

### Step 3: Restore the configuration repository into the forge (CC-49, OPS-11)

The organization's configuration is the repository, at whatever revision you restore; there is no
separate organization archive to build or import. Back it up as a mirror, on the schedule the
matrix above gives it, and restore it the same way:

```bash
# Backup, from anywhere that may read the forge:
git clone --mirror https://gitea.<host>/<org>/city-config.git city-config.git
# Restore, into the empty forge of the fresh instance:
git -C city-config.git push --mirror https://gitea.<new-host>/<org>/city-config.git
```

A mirror carries every branch, tag and commit, so the organization-scoped manifests — `org.yaml`,
`users/roles/`, `users/groups/`, `users/assignments/`, the blueprints — come back with the
projects, and each is reviewed again by the same lanes on its next change (PF-49, PF-52). Gitea's
own metadata (merge requests, issues, comments) is not in the mirror; it comes back with the
PostgreSQL cluster of Step 2, and losing it loses history, not configuration.

Project-scoped export and import (`Download` and `Import` in the Portal) exist for moving or
duplicating one project between instances (PF-22, MF-20…MF-26), not for disaster recovery.

### Step 4: Reconcile Platform State via `jcctl` (CC-50, CC-72)

Once the broker and gateway pods are healthy, the platform components load their declarative configuration directly from the Git repository: the gateway's in-memory store reads context spaces, endpoints, policies, and registrations from the repository and reloads every second; Bento runners mount pipeline streams; and the Portal reconciler watches the repository. There is no live configuration API.

The one state that the repository cannot project into the broker on its own is seed entity data. Replay seed entities from Git into the empty broker through the gateway:

```bash
jcctl apply \
  --repo-dir ./city-config-repo \
  --token-file /var/run/secrets/joinedcontext/token \
  --gateway-url http://context-gateway.prod.svc.cluster.local:9090
```

The gateway is the only address the reconciler takes. `jcctl` reads seed entities from `projects/{p}/spaces/{s}/entities/seed/*.json` (NGSI-LD normalized entities, one file per entity or an array) and upserts them via `POST /cs/{space}/ngsi-ld/v1/entityOperations/upsert` using the ServiceAccount's audience-bound token (CC-04, CC-72). The restore runs through the same policy layer as every other client rather than around it.

Verifying parity:

```bash
jcctl plan \
  --repo-dir ./city-config-repo \
  --token-file /var/run/secrets/joinedcontext/token \
  --gateway-url http://context-gateway.prod.svc.cluster.local:9090
```

`jcctl plan` compares declared seed entities in Git with the live entities returned by the broker for those identifiers. An unchanged repository reports zero changes and issues no write calls.

## 4. Artifact store

The artifact store (RustFS, ADR-N-015) holds only rendered objects. Back it up last: after a loss, `jcctl artifacts rebuild --repo-dir {checkout} --out-dir {dir} [--space {s}] --revision {sha}` writes every object the repository declares — each model's LinkML source and generated artifacts under `schemas/{org}/{project}/{space}/{model}/v{major}/`, each mapping's compiled Bloblang under `mappings/…`, with an `index.json` naming the bytes, the SHA-256 and the commit — and the store's own client mirrors that directory into the bucket with the scoped credential (PF-32); the CLI never holds a store key. An artifact the repository does not hold is named on stderr, not invented: run `jcctl model generate` first. RDF dumps under `dumps/` are the one prefix worth mirroring to the CNPG backup bucket when their retention matters (`artifactStore.mirrorDumpsTo`).

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
