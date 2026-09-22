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

Sections 2 to 6 move a project of a layout 1 repository, where the project is a directory of the
organization's one repository. A project in a repository of its own (layout 2,
[ADR-N-029](../Decisions/adr-n-029-one-repository-per-project.md)) moves as Git, with its whole
history, and section 7 is that procedure.

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

## 7. A project in its own repository (layout 2)

The project is a repository and a registry entry, so it moves as `git bundle`s and is verified
by head commit, not per file (MF-45, MF-46). The order is the same: nothing at the source is
archived until every head at the target is equal.

1. **Export at the source.** One bundle for the project repository and one per application
   repository of the project, each with every branch and tag, and the head each one carries:

   ```bash
   git clone --mirror "https://gitea.source.example/$ORG/$PROJECT.git" "$PROJECT.git"
   git -C "$PROJECT.git" bundle create "../$PROJECT.bundle" --all
   git -C "$PROJECT.git" rev-parse HEAD > "$PROJECT.head"
   ```

   The Portal's export writes the same bundles, the registry entry with its values reset to the
   parameter defaults, and a `kind: Bundle` index listing each bundle with its head commit.
2. **Import at the target.** The import creates each repository from its bundle, shows the
   parameter form generated from `project.yaml`'s `spec.parameters`, and writes the registry
   entry with the values you set: the target's hosts, counts and the names of its secrets. A
   parameter of type `secret` takes a `secretRef` name, and the value is set in the target's
   secret store, never in the form. A bundle of an older `.jc/layout` or `apiVersion` is migrated
   by `jcctl migrate` on the way in and lands as the Change; a newer one is refused (MF-47).
3. **Verify every head.** For each repository, the head at the target equals the head of its
   bundle:

   ```bash
   test "$(git ls-remote "https://gitea.target.example/$ORG/$PROJECT.git" HEAD | cut -f1)"         = "$(cat "$PROJECT.head")" && echo "$PROJECT equal"
   ```

   A head that differs means the repository was written after the export or the bundle was cut
   short. Export again; do not archive the source.
4. **Go live at the target.** Approve the registry entry's Change at the target (red lane,
   CC-87). The reconciler assembles the project at the pinned ref and its spaces, endpoints and
   apps come up under the target's slug and values.
5. **Archive the source.** Only now: the source's red-lane delete archives its repositories,
   keeps the name for `nameCooldownDays` and removes the registry entry (PF-77, PF-78). An
   archived repository is still readable to its owners, so until it is removed by hand both
   sides hold the whole history.

Undoing the move before step 5 is rejecting the target's Change and deleting the repositories
the import created there. After step 5, unarchive the source repository and restore its registry
entry from the organization repository's history.

## Related

- [API/01-portal-api.md §10](../API/01-portal-api.md#10-export-import-revisions-and-sync-mf-16mf-32-cc-49) — the export, import and verification fields this runbook calls.
- [Architecture/03-domain-model.md#project](../Architecture/03-domain-model.md#project) — what a project holds and what deleting one takes with it.
- [Deployment/07-backup-restore.md](07-backup-restore.md) — the backups that cover the instance, not one project.
- [Requirements/manifests.md](../Requirements/manifests.md) — MF-17, MF-24 and MF-42, the bundle rules this follows.
