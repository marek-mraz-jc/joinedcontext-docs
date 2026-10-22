---
sidebar_position: 17
title: "Release Runbook"
description: "The exact steps of a production release and of its rollback, per component: pre-checks, apply, smoke, rollback of the Portal, the platform images and the Antares broker with a migration, and who decides."
---

# Release Runbook

This page is the one the operator follows for a production release of the instance `smartcity` ([14-production-smartcity](14-production-smartcity.md)). It joins the promotion of [15-gitops](15-gitops.md), the upgrade checks of [06-updating](06-updating.md) and the restore of [07-backup-restore](07-backup-restore.md) into one sequence. Run every step and paste its output into the release's task. A step that refuses stops the release.

## 1. Who decides

| Decision | Who | Rule |
|---|---|---|
| Promote a commit | the prod-deployer | only a commit in `dev-green` (`just promote` refuses any other) |
| Roll back | the prod-deployer, without asking | `prod-smoke` red, or a component unhealthy for 10 minutes after the sync |
| Restore a backup | the owner | a restore loses every write since the backup; the prod-deployer prepares it and asks |
| Hold every sync | anyone on the board | `gitops/hold-smartcity.yaml` `hold: true`, with a reason and an end time |

A rollback is never the moment for a schema or Policy change: the rollback carries the previous tree only.

## 2. Pre-checks

From `joinedcontext-deployment`, with the production kubeconfig named per command:

1. **The candidate is green on dev.** `git merge-base --is-ancestor <sha> origin/dev-green` answers 0, and the `dev-smoke` of that sync is in the board's notes.
2. **The previous promotion is known.** `git tag -l 'prod-*' --sort=-creatordate | head -1` names the tag a rollback returns to. Write it into the task.
3. **The diff is read.** `git diff <prod tag> <sha> --stat`, then for each component the image pins: `git diff <prod tag> <sha> -- components/*/images.yaml`.
4. **The broker's migrations are known.** For a new Antares digest, list the migrations between the two images: `git diff --name-only <old broker sha> <new broker sha> -- crates/antares-sql/migrations/` in the broker repository, and read each one's entry in the broker repository's rollback manifest, `migrations.rollback.toml` beside the migrations. A `breaking` entry means the rollback of this release is a restore (§5.3): the owner agrees before the promotion.
5. **No Policy widens and no secret goes back.** `git diff --name-only <prod tag> <sha> | xargs -r grep -l 'kind: Policy'` lists every file holding a Policy; read those hunks. A rollback re-applies the old version of each, so a Policy the release narrowed is widened again by the rollback: fix forward instead (§5.4). Secrets are created in the cluster by the secrets generator and are not in the tree, so a rollback never restores an older secret; a release that renames a `secretRef` is fixed forward too.
6. **A backup is fresh.** Each CNPG cluster has a completed `Backup` younger than one hour (`kubectl get backups -A --sort-by=.metadata.creationTimestamp`); otherwise take one ([07-backup-restore](07-backup-restore.md) §2) and wait for `completed`.
7. **The counts are recorded.** Before the sync, record the row counts the rollback must keep: `SELECT count(*) FROM entities` and `SELECT count(*) FROM attr_instances` in the broker database, `SELECT count(*) FROM <table>` for each table of the Portal database. Paste them into the task.

## 3. Apply

1. `just promote <sha>`. It prints the new tag `prod-<UTC>`; write it into the task.
2. Argo CD syncs `release` within minutes. Watch `scripts/gitops-status.sh` until every Application is `Synced` and `Healthy`. A broker image with a migration sits at 0 ready replicas while it migrates; its startup probe allows one hour.
3. Note the time from the push to the last `Healthy`.

## 4. Smoke

1. `just prod-smoke`. Green closes the release: the counts of step 2.7 are taken again and must not drop.
2. Red: roll back (§5) at once, then read the logs. Never fix forward on a red production instance unless §5 says so.

## 5. Rollback

Every rollback starts the same way: `just rollback <prod tag of step 2.2>` commits that tag's tree on top of `release`, and Argo CD syncs it. No branch is force-pushed. Take the counts of step 2.7 again after the sync and run `just prod-smoke`.

### 5.1 Portal

The Portal image goes back with its pin. Its migrations follow the broker's rule (§5.3): the previous Portal boots on the newer schema and logs `the database holds migrations [...] of a newer release, none marked breaking: serving it as a rollback`, unless a migration of the release starts with `breaking_`. A Portal built before T-5105 refuses every newer migration: treat it as breaking. Check `GET /api/health` and one sign-in.

### 5.2 Platform images (gateway, jcctl jobs, pipeline runner)

Stateless: the previous digests go back with the tree. Check the gateway's `/healthz` through the edge and one NGSI-LD read per public Endpoint.

### 5.3 Antares broker with a migration

Migrations are forward-only: no down step ships, and nothing undoes a schema change. What a rollback does depends on the newest migration the release applied, as `migrations.rollback.toml` states:

- **compatible:** the previous broker boots on the newer schema and logs `the database holds migrations [...] of a newer release, all marked compatible: serving it as a rollback`. Its `note` names what the previous release does not maintain while it runs. Roll forward again soon, with no other schema change in between.
- **breaking:** the previous broker refuses to boot (`migration <n> is newer than the latest applied migration <m>`). The owner decides the restore of the backup of step 2.6 ([07-backup-restore](07-backup-restore.md) §3), or a fix forward.
- **A previous broker older than the rollback-tolerant boot** (Antares T-5105) refuses every newer migration the same way: treat it as breaking.

### 5.4 Fix forward instead

Fix forward, with a new promotion through dev, when the rollback would widen a Policy, bring back a renamed `secretRef`, or restore a backup the owner did not agree to.

## 6. Rehearsal record

Every rollback path above is rehearsed on `dev` (release N, then N+1, then back to N) before it is used on production, and again after a change to `just promote`, `just rollback` or the broker's boot. The record holds, per component: the two versions, the time of each step, the counts before and after, and the smoke result. The first rehearsal is recorded in the task T-5105.

## Related

- [06-updating](06-updating.md) — the upgrade order and the broker's blue/green update.
- [07-backup-restore](07-backup-restore.md) — the backup step 2.6 checks and the restore §5.3 may need.
- [14-production-smartcity](14-production-smartcity.md) — the instance, `just promote`, `just rollback` and the hold rules.
- [15-gitops](15-gitops.md) — how Argo CD syncs `release` and the hold switch.
