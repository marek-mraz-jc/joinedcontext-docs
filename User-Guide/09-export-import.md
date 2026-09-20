---
sidebar_position: 10
title: Export, Portability & Project Duplication
description: One-click project archiving, template duplication, and full disaster recovery procedures.
---

# Export, Portability & Project Duplication

joinedcontext ensures zero vendor lock-in. All platform configurations can be exported, cloned, or restored with full fidelity ([CC-49](../Requirements/city-as-code.md#8-export-portability-and-upgrade)).

---

## 1. Exporting a Project Archive

1. Navigate to your project and open **Project Settings**.
2. Select **Export & Portability**.
3. Click **Download Full Project Archive**.
4. The platform packages:
   - All LinkML Data Models and compiled schemas.
   - All Context Space and Policy manifests.
   - Bento pipeline stream configurations.
   - Dashboard and layer definitions.
   - Audit trail metadata.
5. The downloaded `.zip` archive represents a standalone, self-describing project repository.

---

## 2. Project Duplication (Templating)

To replicate an existing project configuration (e.g. rolling out an identical *Smart Parking* setup to a new organisational district):

1. In the Projects overview, click the menu on the source project and select **Duplicate Project**.
2. Enter the new Project Name: `Smart Parking - District West`.
3. Enter the new Slug: `smart-parking-west`.
4. Review parameter substitutions (e.g. updating geographic scope prefix from `/geo/FI/HKI/Keskusta` to `/geo/FI/HKI/Lansi`).
5. Click **Confirm Duplication**. The platform clones the manifest tree and opens a single merge request initializing the new project.

---

## 3. Importing Manifests or a Bundle

1. Open the project (or the organization) and choose **Import**.
2. Drop a `.yaml` file, a multi-document YAML, a `.zip` bundle, or paste a URL.
3. Pick the target: this project, or **Create new project from bundle**. The wizard shows how names, references and URN prefixes will be rewritten.
4. Pick what happens on name collisions: **Fail** (default), **Skip**, **Replace**, or **Rename**.
5. Review the **Preview**: what will be created, updated or deleted, and which approval lane it lands in.
6. Click **Import**. A single change is created; green-lane content is live in seconds, everything else waits for the approver named in the preview.

Secrets are never inside a bundle. After import, open **Secrets** and provide the values the imported `secretRef`s point to.

## 4. Keeping a Project in Sync with an External Source

Use **Sync** when a project should follow something maintained elsewhere: a regional data-model repository, a published bundle, or a partner city's instance.

1. Project → **Sync** → **Add source**.
2. Choose the source type: **Git repository** (URL, branch, folder), **Bundle URL**, or **Another platform instance** (URL and project).
3. Choose credentials (a secret reference), the schedule (every N minutes or on webhook), and the mode: **Mirror** (the source is authoritative for this subtree; local edits show as drift) or **One-shot**.
4. Leave **Prune** off unless deletions in the source should be proposed here too; they still need approval.
5. Save. Each run creates a change only when something differs; the project page shows `Synced`, `Out of sync`, `Pending approval` or `Error`, with **Sync now**, **Pause** and **Detach**.

Everything you do here can also be done with `jcctl export | import | sync` or by an AI agent through the configuration tools; the same validation and approvals apply.

## 5. Disaster Recovery Restoration

To restore an entire organisational deployment onto a clean, empty cluster ([CC-50](../Requirements/city-as-code.md#8-export-portability-and-upgrade)):

1. Deploy baseline infrastructure via Helmfile:

   ```bash
   helmfile -f deployment/helmfile.yaml apply -e production
   ```

2. Clone the authoritative City Git Repository:

   ```bash
   git clone https://gitea.joinedcontext.com/helsinki/city-repo.git
   ```

3. Execute `jcctl apply`:

   ```bash
   jcctl apply --repo-dir ./city-repo --gateway-url http://context-gateway:9090
   ```

All spaces, schemas, policies, pipelines and dashboards are recreated; a following `jcctl plan` must be empty (CC-18).

## Related

- [CC-49](../Requirements/city-as-code.md) — referenced above.
- [00-intro](00-intro.md) — user guide overview.
- [01-getting-started](01-getting-started.md) — first steps in the Portal.
