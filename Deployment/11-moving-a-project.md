---
sidebar_position: 13
title: "Moving a Project Between Instances"
description: Export a project from one instance, import it under another's overlay, verify every checksum, and only then delete the source.
---

# Moving a Project Between Instances

A project moves as a bundle: you export it at the source, import it at the target, read the
per-file verification the import answers, and delete the source only when every file is equal.
Nothing about the move is automatic. Each step is a change somebody approves, and the order
below is the one that never loses a manifest (MF-42, PF-77, PF-78).

## 1. Before you start

- You hold `read` on every kind of the project at the source and `propose` on every kind at the
  target; the target's approver holds `approve` on them.
- Both instances run the same `apiVersion`. An import refuses an `apiVersion` it does not serve,
  before anything is written (MF-24).
- The target's `environments/{name}.yaml` overlay carries its own `orgDomain`, so every URN of
  the imported manifests is rendered for the target and nothing carries the source's domain
  (CC-73, CC-74).
- Context **data** does not travel in the bundle. The bundle is configuration. Export each
  space's entities separately if they are to be kept (CC-07).

## 2. Export at the source

```bash
curl -fsS -b "$SESSION" \
  "https://portal.source.example/api/v1/projects/$PROJECT/export?format=zip" \
  -o "$PROJECT.zip"
```

The archive holds `projects/$PROJECT/`, a `README.md`, `schemas/` and `bundle.yaml`. The index
carries `spec.sourceRevision`, the commit the export was taken at, and `spec.files`, the
SHA-256 of every file as exported. That list is what the target verifies against.

`format` is `yaml`, `json` or `zip`, and `yaml` is the default; only `zip` carries the whole
bundle with its index, so a move uses `zip`. Three more parameters narrow the export:
`revision` takes it at a commit other than the tip, and `kinds` and `names` take comma-separated
lists when you are moving part of a project rather than all of it.

Check it is the revision you meant:

```bash
unzip -p "$PROJECT.zip" bundle.yaml | grep -E "sourceRevision|exportedAt"
```

## 3. Import at the target

```bash
curl -fsS -b "$SESSION" -X POST \
  -H "x-csrf-token: $CSRF" \
  -F "file=@$PROJECT.zip" \
  "https://portal.target.example/api/v1/projects/$PROJECT/import?dryRun=All"
```

Read the dry run first. The report carries `created`, `replaced`, `skipped`, `renamed`,
`nativeFiles`, the `lane` the bundle lands in, and any refusal. Then run it again without
`dryRun`; the answer is `202` and a `Change`, one merge request for the whole bundle, in the
riskiest lane of the resources it holds (CC-63).

The report also carries `needs`: what a copy cannot bring with it (CC-84). Each entry has a
`kind` of `secret`, `person`, `host` or `credential` and a `location` of the form
`Kind/name spec.path`. It never carries a secret value, only where one has to be set. Work
through that list at the target before the project is expected to run: a `secretRef` resolves
against the target's own store, a person is a target account, a host is the target's domain,
and a feed credential is issued again by whoever owns the feed. An empty `needs` means nothing
has to be provided.

`dryRun` is spelled in camel case and nothing else. The handler renames the field, so `dry_run`
is not read and the import commits (T-1226).

## 4. Verify before you delete anything

The import report carries `verified`: one entry per file, `path` and `equal`, comparing the
SHA-256 of what was written with the index after the namespace mapping is undone. The `Change`
body says the same thing in one line, `n of m files equal`.

- **Every file equal.** The transfer is complete; go on to step 5.
- **A file unequal.** Something was rewritten on the way: read that path in the merge request,
  fix the source manifest or the mapping, and import again. Do not delete the source.
- **No `verified` at all.** The bundle came from an exporter older than MF-42 and carries no
  checksums. Re-export from a current source instance; an unverifiable transfer is not a
  verified one.

Approve the merge request at the target, wait for the reconciler, and open the project's pages:
the spaces, the endpoints and the apps are the source's.

## 5. Delete the source

Only now, and only with every file equal:

```bash
curl -fsS -b "$SESSION" -X DELETE \
  -H "x-csrf-token: $CSRF" \
  "https://portal.source.example/api/v1/projects/$PROJECT"
```

That is one red-lane `Change` removing the project's whole tree and every binding and project
role written for it (PF-77). Approving it drops each space's broker tenant, so export the data
first if it is to be kept. The name then stays reserved at the source for
`Organization.spec.projects.nameCooldownDays`, 30 days by default, and `0` frees it at once
(PF-78). The commit that removed `projects/{name}/project.yaml` starts the period, so the
reservation survives a restart of the Portal.

## 6. If the move has to be undone

Before the source is deleted, there is nothing to undo: reject the target's merge request and the
target is as it was. After the source is deleted, the project is recreated by importing the same
bundle back. The archive you downloaded in step 2 is the record, so keep it until the move is
settled.

## Related

- [API/01-portal-api.md §10](../API/01-portal-api.md#10-export-import-revisions-and-sync-mf-16mf-32-cc-49) — the export, import and verification fields this runbook calls.
- [Architecture/03-domain-model.md#project](../Architecture/03-domain-model.md#project) — what a project holds and what deleting one takes with it.
- [Deployment/07-backup-restore.md](07-backup-restore.md) — the backups that cover the instance, not one project.
- [Requirements/manifests.md](../Requirements/manifests.md) — MF-17, MF-24 and MF-42, the bundle rules this follows.
