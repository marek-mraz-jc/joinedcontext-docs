---
sidebar_position: 8
title: "Backup, Disaster Recovery & Restore"
---

# Backup, Disaster Recovery & Restore

Disaster recovery rests on three stores that fail independently: the **declarative configuration**, which is a Git repository in the forge; the **secrets**, which are SOPS-encrypted in a repository and decrypted at render time; and the **transactional state**, which is PostgreSQL. Restore them in that order.

## 1. Data Classification & Storage Matrix

| Data Class | Component | Persistent Store | Criticality | Recovery Objective |
|---|---|---|---|---|
| **Platform configuration** | The configuration repository in Gitea | Gitea's PVC, plus a Git mirror wherever you keep one | Critical | RPO = 0 (every commit is permanent)<br/>RTO ≤ 5 min |
| **Secrets & keys** | `secrets` component | SOPS-encrypted in a repository, with the age key outside it. OpenBao is named as an add-on and has no component to deploy today ([04-components-and-addons.md](04-components-and-addons.md) §1) | Critical | RPO = 0<br/>RTO ≤ 10 min |
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

### The monthly restore drill

The CronJob `postgres-cluster-dr-drill` (04:00 UTC on the 1st, `postgres.databases.drDrill`)
proves the archive restores, in every environment with backups on, the production one
included (OPS-11, OPS-12):

1. It counts every table of every database on the primary and notes the instant after the last
   count.
2. It restores the latest base backup and WAL into a throwaway `Cluster`, compares each
   database's total rows with the source, and checks that the realm holds an enabled person and
   that the Portal's schema sits at the source's last migration.
3. It deletes that copy and restores to the instant of step 1. Every table must hold the count
   step 1 read, within `tolerancePercent` (5 %) and at least one row.
4. It writes RTO (each restore's time to Ready) and RPO (now minus the last transaction the
   latest restore replayed) into the ConfigMap `postgres-cluster-dr-drill`, deletes the copy
   and fails the Job when a count or a check is short.

The copy has no ingress (its NetworkPolicy admits only the CNPG operator; the drill counts through
`kubectl exec`), reads the bucket through the same `existingSecret`, and is deleted however the drill ends. A
production RTO and RPO are those the drill measured; until the production instance archives to
object storage, the drill there records `no-backup` and no number exists.

### The nightly local dump and its restore check

An instance without object storage (production until its S3 keys exist) keeps a nightly
`pg_dumpall --clean --if-exists | gzip` instead: the CronJob `postgres-cluster-local-backup`
(02:30 UTC, `postgres.databases.localBackup`) writes `/backup/<date>.sql.gz` to a node volume of
`size` (10Gi) and keeps `keepDays` (7) days. It covers a dropped table or a broken migration, not
the loss of the node. Just before each dump the job counts every table of every database into
`<date>.sql.gz.counts` beside it; `excludeDatabases` (empty by default) leaves named databases
out of both. The job fails when pg_dumpall fails or when one dump exceeds 80 % of the volume
(that dump is kept; the fix is a larger `localBackup.size`), and `PostgresBackupStale` fires
once no dump has succeeded for 26 hours.

local-path does not enforce `size`, and the volume sits on the disk Postgres runs on, so the
job holds itself to it:

- Retention runs first, so a dump gets the room the expired ones leave.
- The dump stops at what is left of `size` and is deleted when it reaches that; the error names
  `localBackup.size` and `excludeDatabases`.
- The dump does not start when writing up to that much would leave the node's disk under 10 %
  free.
- The Job `postgres-cluster-local-backup-now` that each apply creates (it binds the volume) dumps
  only when no dump of the last 20 hours is on the volume, so an hourly apply adds no dump.

Dev dumps without `antares` and `ckan_datastore` (81 GB and 1.9 GB on 2026-10-25) and keeps one
day.

With `localBackup.enabled` the monthly drill restores the newest dump first, before any
archive restore, in an init container of its own Job pod:

1. The init container `dump` runs the cluster's image, with the dump volume mounted read-only
   and an `emptyDir` of `drDrill.storageSize` for the data. It starts a Postgres of its own.
2. It tests the gzip whole, then feeds it to `psql -v ON_ERROR_STOP=1`. A truncated file or the
   first refused statement fails the stage.
3. It counts every table of the copy and holds it to the dump's `.counts` file, within
   `tolerancePercent` and at least one row. A table the copy lacks fails the stage by name.
4. It stops Postgres, deletes the copy's files and hands its verdict to the drill container,
   which writes `localDump` (`local-dump-passed`, `failed`, `skipped` when the node had no
   room, `off` without the dump), `localDumpRtoSeconds` (database start to restored),
   `localDumpBytes` and `localDumpDetail` into the ConfigMap `postgres-cluster-dr-drill`.

A failed dump restore fails the drill (`result: failed`, the Job red). A passed one leaves
`result: no-backup` on an instance without object storage: the dump does not survive the node,
so `PostgresRestoreDrillStale` keeps reporting the missing off-site backup. The restored copy
holds production data: Postgres in the init container listens on no port (a Unix socket in its
`emptyDir` only), the container gets no API token (the pod mounts the ServiceAccount token into
the drill container alone), and an error in `localDumpDetail` is cut at its first quote so no
row value reaches the ConfigMap. The drill creates no pod: its Role grants no `pods` verb, so
it cannot start a pod under another ServiceAccount or with another Secret. Dev runs the
dump beside its archive to rehearse the stage; read the measured numbers with:

```bash
kubectl -n dev get configmap postgres-cluster-dr-drill \
  -o jsonpath='{.data.localDump} {.data.localDumpRtoSeconds}s {.data.localDumpBytes} bytes{"\n"}'
```

## 3. Disaster Recovery Procedure

To restore an entire organisational instance from scratch on a blank Kubernetes cluster:

### Step 1: Provision Base Infrastructure & Restore Secrets

Deploy the cluster operators (Linkerd, CloudNativePG, cert-manager) and put the age key that decrypts the SOPS files where whoever runs `helmfile` can read it (`SOPS_AGE_KEY_FILE`). Without it the render fails before anything is installed, which is the intended order: no cluster comes up half-configured with generated stand-ins for real secrets.

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

A mirror carries every branch, tag and commit, so the organization-scoped manifests (`org.yaml`,
`users/roles/`, `users/groups/`, `users/assignments/`, the blueprints) come back with the
projects, and each is reviewed again by the same lanes on its next change (PF-49, PF-52). Gitea's
own metadata (merge requests, issues, comments) is not in the mirror; it comes back with the
PostgreSQL cluster of Step 2, and losing it loses history, not configuration.

In layout 2 ([ADR-N-029](../Decisions/adr-n-029-one-repository-per-project.md)) the configuration is
N+1 repositories: the organization repository and one repository per project its registry names
(`projects/{slug}.yaml`, PF-86), plus each application's own repository (AP-72). Mirror every one of
them on the same schedule, and restore the organization repository first, then each repository its
registry entries name:

```bash
# Every repository of the forge organization, one mirror each:
for repo in $(curl -fsS -H "Authorization: token $FORGE_TOKEN" \
    "https://gitea.<host>/api/v1/orgs/<org>/repos?limit=50" | jq -r '.[].name'); do
  git clone --mirror "https://gitea.<host>/<org>/$repo.git" "$repo.git"
done
# Restore: the organization repository, then every other mirror.
git -C city-config.git push --mirror https://gitea.<new-host>/<org>/city-config.git
for mirror in *.git; do git -C "$mirror" push --mirror "https://gitea.<new-host>/<org>/$mirror"; done
```

Each registry entry pins its ref, so once the mirrors are pushed the reconciler assembles the same
render as before the loss (CC-86). A registry entry whose repository is missing at the new forge
renders nothing for that project and says so on the entry's `status`; push the missing mirror and
the next render picks it up. The forge's teams (`{slug}-readers`, `{slug}-writers`) are compiled
from the bindings by the reconciler again, not restored from the mirror (PF-87). The forge API
answers at most 50 repositories per page, so page with `&page=2` and on beyond that.

Project-scoped export and import (`Download` and `Import` in the Portal) exist for moving or
duplicating one project between instances (PF-22, MF-20…MF-26), not for disaster recovery.

### Step 4: Reconcile Platform State via `jcctl` (CC-50, CC-72)

Once the broker and gateway pods are healthy, the platform components load their declarative configuration directly from the Git repository: the gateway's in-memory store reads context spaces, endpoints, policies, and registrations from the repository and reloads every second; Bento runners mount pipeline streams; and the Portal reconciler watches the repository. There is no live configuration API.

The one state that the repository cannot project into the broker on its own is seed entity data. Replay seed entities from Git into the empty broker through the gateway:

```bash
jcctl apply \
  --repo-dir ./city-config-repo \
  --token-file /var/run/secrets/joinedcontext/token \
  --gateway-url http://context-gateway.prod.svc.cluster.local:8080
```

The gateway is the only address the reconciler takes. `jcctl` reads seed entities from `projects/{p}/spaces/{s}/entities/seed/*.json` (NGSI-LD normalized entities, one file per entity or an array) and upserts them via `POST /cs/{space}/ngsi-ld/v1/entityOperations/upsert` using the ServiceAccount's audience-bound token (CC-04, CC-72). The restore runs through the same policy layer as every other client rather than around it.

Verifying parity:

```bash
jcctl plan \
  --repo-dir ./city-config-repo \
  --token-file /var/run/secrets/joinedcontext/token \
  --gateway-url http://context-gateway.prod.svc.cluster.local:8080
```

`jcctl plan` compares declared seed entities in Git with the live entities returned by the broker for those identifiers. An unchanged repository reports zero changes and issues no write calls.

## 4. Artifact store

The artifact store (RustFS, ADR-N-015) holds only rendered objects. Back it up last: after a loss, `jcctl artifacts rebuild --repo-dir {checkout} --out-dir {dir} [--space {s}] --revision {sha}` writes every object the repository declares (each model's LinkML source and generated artifacts under `schemas/{org}/{project}/{space}/{model}/v{major}/`, each mapping's compiled Bloblang under `mappings/…`, with an `index.json` naming the bytes, the SHA-256 and the commit), and the store's own client mirrors that directory into the bucket with the scoped credential (PF-32); the CLI never holds a store key. An artifact the repository does not hold is named on stderr, not invented: run `jcctl model generate` first. Nothing in it needs its own backup: a space's dump is generated per request and never stored (SP-13).

## 5. Backups and erasure

A backup cannot be edited, so an erasure of personal data ([ADR-N-054 §2.6](../Decisions/adr-n-054-history-versions-provenance-gdpr.md#26-personal-data)) reaches it in two ways:

1. **Expiry.** Keep `postgres.cluster.backups.retentionPolicy` at `30d` or shorter; that period is the one the city states to a data subject as the time an erased value can survive in a backup.
2. **Re-apply after a restore.** The broker keeps a content-free record of each erasure beside its data and applies every record again when it starts; the Portal keeps the erasure log (keyed hash of the subject, the space, the Entities, the counts per store, never a value) in its own database and, when it starts and every hour after, sends again each erasure whose record a broker no longer holds. After Step 4 of the recovery procedure, before you open the edge again, restart the Portal and check the line:

```bash
kubectl -n <env> rollout restart deploy/portal
kubectl -n <env> logs deploy/portal | grep 'erasure log re-applied'
```

The line names how many logged erasures were sent again (`resent`) of how many the log holds (`logged`). Without it, keep the edge closed and read [09-troubleshooting.md](09-troubleshooting.md). A restore of the Portal's own database to a point before an erasure loses that erasure's log row: restore the two databases to the same point, or erase again from the request's record.

Audit metadata, the erasure log and the read log of personal data are kept for the audit retention, two years by default (ADR-N-054 §2.7), and hold no personal value.

## Related

- [01-runbooks](../Operations/01-runbooks.md) — Runbook 6 is the step-by-step PITR this page summarises.
- [03-configuration](03-configuration.md) — where the `postgres.cluster.backups` values live.
- [06-updating](06-updating.md) — take a backup before the upgrade sequence, not after.
- [11-moving-a-project](11-moving-a-project.md) — project export and import, which is not disaster recovery.
- [13-security](../Architecture/13-security.md) — why the restore goes through the gateway and not around it.
