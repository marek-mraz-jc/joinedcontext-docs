---
sidebar_position: 3
title: "Manifest Model, Import, Sync & Download"
description: Kubernetes-style resource envelope, resource API, and download, import, and sync operations.
---

# Manifest Model, Import, Sync & Download

Family **MF** (MF-01…MF-44). Owning chapter: [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md). Verified by: [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md).

## 1. Resource Envelope

- **MF-01** — Every configuration resource MUST be a Kubernetes-style object consisting of `apiVersion`, `kind`, `metadata`, `spec`, and server-computed `status`.
  > Note: Native artifacts (`bento.yaml`, `*.linkml.yaml`) are referenced from resources rather than wrapped.
- **MF-02** — Manifest `metadata` MUST contain a DNS-1123 `name` and target `namespace` matching the project slug or `org`.
  > Note: `labels`, `annotations`, `title` and `description` are optional; `metadata` carries no other field, because the envelope refuses unknown ones. `title` and `description` are one string in the author's language (UI-50) or the legacy `{locale: text}` map, which still parses and resolves per PF-28. Nothing rewrites the legacy form today and no version rejects it.
- **MF-03** — Manifest `spec` MUST declare the complete desired resource state and serve as a valid payload for its underlying service API (CC-09).
- **MF-04** — Resource `status` MUST NOT be stored in Git and is served strictly by the Portal API.
  > Note: Status reflects observed revision, phase, and transition conditions; download and import operations strip status.
- **MF-05** — Multi-document YAML manifests and `kind: List` resource collections MUST be accepted on import and produced on export.
  > Note: Reconciler execution order is determined by sync waves rather than document order.
- **MF-06** — Resource identity MUST be determined uniquely by `(group, kind, namespace, name)` from which repository file paths are derived (CC-10).
- **MF-07** — Cross-resource references MUST use typed reference objects `{kind, name, namespace?}` rather than hard-coded file paths or database keys.
- **MF-08** — Well-known annotations for attribute ownership, blueprint provenance, sync sources, and import origins MUST be supported and preserved verbatim.
- **MF-09** — Every resource kind MUST publish a JSON Schema draft-07 specification and corresponding OpenAPI resource endpoints (MF-12).
  > Note: `jcctl schema export --out <dir>` writes one draft-07 document per catalogued kind, and the KPI entity type beside them; a whole-project export writes the same documents at `schemas/kinds/{Kind}.schema.json` (MF-41).
- **MF-10** — Manifest labels MUST support standard Kubernetes set-based and equality-based selector filtering in API and UI views.

## 2. Resource API

- **MF-11** [P][A] — The Portal API MUST expose all resource kinds under `/api/v1/projects/{project}/{plural}` with support for selectors and historical revision queries.
  > Note: Today `labelSelector` and `fieldSelector` filter, and `revision` is accepted and answered `501 Not Implemented` because the route does not read Git (T-2375).
- **MF-12** — Write operations against the resource API MUST NOT mutate live state directly, creating a Git merge request and returning HTTP 202 Accepted with a `Change` resource (CC-03).
  > Note: This preserves declarative GitOps review invariants across all administrative mutations.
- **MF-13** [P][A] — Dry-run validation via `POST …?dryRun=All` MUST evaluate schema and Conftest constraints and return the plan diff without committing changes.
- **MF-14** [A][S] — The `jcctl` CLI MUST provide kubectl-shaped subcommands against the Portal resource API (API/01 §4), called with an OIDC access token read from a file and never from an argument: `get` (with `-o name|yaml|json`) and `describe` read live state; `apply -f`, `diff -f` and `delete -f` take a file of manifests, where `apply -f` proposes each as a `Change` (create or replace), `delete -f` proposes each deletion as a `Change` on the deletion lane, and `diff -f` compares the file with the live manifests and writes nothing. No verb writes live state directly (MF-12), a bearer caller's `Change` waits for a person's approval (CC-41), and output prints the manifest as the API serves it, which carries `secretRef` names and never a resolved secret (CC-06). `export` and `import` are the repository verbs of MF-16…MF-24 (API/03).
  > Note: Today `jcctl` reads a repository checkout and ships `validate`, `plan`, `apply`, `drift`, `export`, `import`, `schema export`, `workspace render|diff`, `roles`, `model`, `pipeline test`, `artifacts rebuild`, `sync` and `publish ckan`, each taking `--repo-dir`. `get`, `describe`, `delete` and the `-f` forms are not built, and what they should mean when there is no configuration API to ask (CC-72) is an open decision (T-2374).
- **MF-15** — Server-side field ownership for NGSI-LD attributes MUST be enforced using `joinedcontext.com/managed-attributes` (CC-69).

## 3. Download

- **MF-16** [H][P][A] — The Portal UI MUST provide one-click download actions exporting resources as single manifests, List bundles, or complete repository archives at current or historical revisions (CC-49).
- **MF-17** — Exported bundles MUST be immediately re-importable, including native files, committed schema artifacts, and a `kind: Bundle` index with stripped status and secret values. The index MUST be the registered `Bundle` kind, so the platform's own validation accepts the document the export wrote.
- **MF-18** — Configuration downloads MUST enforce the caller's read grants, recording counts of omitted resources without disclosing unauthorized names (R20).
- **MF-19** — Configuration exports MUST NOT bundle dynamic context entities or temporal histories, delegating state exports to Endpoint file representations (CC-07).
- **MF-41** [H][A] — An export of a project that names no single resource (no `names` filter) MUST be complete and self-describing: every manifest and native file of the project at the revision; the JSON Schema (draft-07) of every kind it holds, with the field descriptions of the manifest model, at `schemas/kinds/{Kind}.schema.json`; for every `DataModel`, its LinkML source and its JSON Schema at `schemas/models/{name}/{name}.linkml.yaml` and `schemas/models/{name}/{name}.schema.json`, taken from the repository or generated by Model Tools when the repository holds none, and named as missing when neither is possible; and a `README.md` saying, for each kind it holds, what the kind is, how many resources it holds and where its schema is. Import MUST NOT write `README.md` or `schemas/` into the project, so the complete export stays re-importable (MF-17, CC-49, DM-02, DM-03).
- **MF-42** — The `kind: Bundle` index of a whole-project download MUST carry the SHA-256 of every file it holds, and an import MUST report, per file, whether the manifest it wrote equals the index's checksum after the namespace mapping is undone, so a transfer between instances can be verified before the source is deleted (PF-78, MF-17). A git-native bundle verifies by head commit instead (MF-46).

## 4. Import

- **MF-20** [H][P][A] — The Portal UI MUST provide an import wizard supporting manifests, archives, and remote URLs, tagging imported objects with provenance annotations.
- **MF-21** — Import workflows MUST execute schema validation, reference checks, Conftest gates, and plan generation before creating a lane-classified merge request (CC-63).
- **MF-22** — Namespace mapping MUST be configured explicitly during import, rewriting target namespaces, typed references, and URN prefix segments (PF-22).
- **MF-23** — Imports MUST enforce a user-selected conflict resolution policy (`fail`, `skip`, `replace`, `rename`).
- **MF-24** — Manifest imports MUST reject plaintext secrets, unresolvable references, unsupported API versions, and unauthorized resource kinds.
- **MF-25** — Bundles exported from external instances MUST be importable offline without network connectivity to the originating instance.
- **MF-26** — Project duplication MUST execute through the unified download and import workflow configured with namespace remapping and rename conflict policies.

## 5. Sync

- **MF-27** [H][P][A] — The platform MUST support `kind: SyncSource` manifests defining continuous synchronization against Git repositories, bundle URLs, or remote platform APIs.
- **MF-28** — Each scheduled synchronization run MUST evaluate changes through standard import gates, generating an automated merge request when differences are detected.
- **MF-29** — Merge requests produced by sync sources MUST follow standard risk-lane classifications, requiring red-lane approvals to enable automated merging.
- **MF-30** — `SyncSource` status MUST report current synchronization state, observed revisions, and active merge requests with options to trigger manual runs or pause syncing.
- **MF-31** — Remote sync connections MUST authenticate using scoped secret references and execute with permissions restricted to the sync source owner's grants.
- **MF-32** — Cross-instance synchronization MUST interact exclusively through the target instance's public resource API and Endpoint surfaces.
- **MF-44** [S] — A `SyncSource` that runs on a webhook MUST carry its own inbound credential as `spec.webhook.secretRef` (with `spec.webhook.previousSecretRef` for a rotation window) and MUST be refused at admission when `spec.schedule.webhook` is `true` and no such reference is given; the webhook route MUST authorise a run against that source's own resolved secret and against no shared or platform-wide secret, MUST answer one and the same `401` for an unknown source, a source with no `spec.webhook` and a signature that does not verify, and MUST never carry the secret in an answer, a log line or the source's `status` (MF-24, MF-31, PF-51, PF-59).

## 6. UI and Parity

- **MF-33** [H] — Download, import, and sync workflows MUST be accessible through non-technical UI wizards while concealing raw Git mechanics in default views (CC-29).
- **MF-34** [P][A] — All manifest operations MUST maintain functional parity across the Portal UI, `jcctl` CLI commands, and Configuration MCP tools (CC-48).

## 7. External Feed Connections

- **MF-35** [S] — A `DataSource` manifest MUST declare one connection: a typed one (`mqtt`, `http`, `websocket`, `gtfs-rt`, each with its own block) or any input the pinned runner ships named in `spec.type` with its configuration in `spec.input` (PL-50); it MUST express every credential as a `secretRef` (`passwordRef`, `caCertRef`, `authorization.headerRef` on the typed blocks; `spec.secrets` entries referenced by `${VAR}` interpolation from the runner input's secret fields), the schema carrying no field a plaintext credential could be written into and a literal in a runner-documented secret field being refused (CC-06).
  > Note: The connection blocks, their Bento inputs and the reference rules are in [Architecture/08-pipelines.md §6](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39); a `DataSource` moves no data on its own and is referenced by a Pipeline (PL-39).

## 8. Federation Registrations

- **MF-36** [S] — A `ContextSourceRegistration` manifest MUST name the Context Space whose broker learns of the source (`spec.contextSpaceRef`), exactly one target (`spec.endpointRef` on this platform or `spec.endpoint` elsewhere), and its coverage claim in CIM 009's own `information` shape; it MUST declare the identity the forward carries (`spec.federation.identity`) and MUST express every credential as a `secretRef`. The reconciler MUST project it onto the broker's `POST /ngsi-ld/v1/csourceRegistrations` in that space's tenant, carrying the tenant only on that internal hop (SP-08, SP-09), and MUST treat every change to one as a red lane change (CC-63).
  > Note: The manifest, the hub pattern it enables and the federation graph read from it are in [Architecture/04 §5a](../Architecture/04-context-spaces-and-endpoints.md#5a-federation-registrations-and-the-hub-endpoint). A registration grants nothing on its own (PF-48).

## 9. Validation at write time

- **MF-37** [S] — Every write through the Portal API MUST run the kind's own parse and invariants (unknown fields refused, cross-field rules) before a `Change` is created, answering `400` (RFC 7807) with the failing field, so that a manifest the reconciler would refuse never reaches `main` with an approval on it; the reconciler MUST report, not silently skip, a manifest on `main` that fails them; a kind without a typed model is checked against the envelope only, and the list of such kinds is published (Development/04).

## 10. A manifest under test

- **MF-38** [S] — A pipeline test (PL-43) MUST never resolve a `secretRef` and MUST never reach the pipeline's target: the harness the Portal renders replaces the `DataSource` input by the sample and the output by the Portal's capture, keeps the processors byte for byte, and is produced by the same code that renders the runner's stream, so what is tested is what would run; a manifest that fails the kind's own parse (MF-37) is refused with `400` before any stream exists.
- **MF-39** [H] — A dry run (`?dryRun=All`) of an `http` DataSource MUST also fetch its URL once on the project's pipeline runner (the PL-43 harness with no compute, so nothing is written and no `secretRef` is resolved, MF-38) and answer `probe` beside the plan: `records` (messages after the format split), `bytes` and the first record as `sample`; a DataSource that declares an `authorization` is not probed and the answer carries `probe.skipped` with the reason, never the credential.
- **MF-40** [S] — An `AgentProfile` manifest declaring a `spec.access` block MUST validate on admission that every operation name matches `^jc_[a-z0-9_]+$` and corresponds to a registered Portal operation, every kind refers to a known resource kind, kind verbs are confined to `read` and `propose`, endpoint verbs are confined to `read` and `write`, endpoint names conform to DNS-1123 labels, and no wildcard characters appear in any access field (MF-37, AG-70).

## 11. Copies keep rendered values rendered

- **MF-43** [P] — Import and export MUST keep every rendered value as its placeholder or local form, so a bundle of one endpoint, one project or one organization applies unchanged elsewhere (sharpens MF-17, CC-74).

## 12. Git-native export and import

- **MF-45** — Exporting a whole project MUST be git-native: a `git bundle` of the project repository with its whole history and tags, one bundle per application repository of the project, and the registry entry with its parameter schema and this deployment's values reset to the defaults; the `kind: Bundle` index MUST list each bundle with its head commit. The YAML bundle of MF-16 stays for parts of a project.
- **MF-46** [H] — Importing a git-native bundle MUST create the repositories at the target forge from the bundles, show the parameter form generated from the schema, write the registry entry, and verify the transfer by head-commit equality per repository (the per-file checksums of MF-42 stay for YAML bundles). The source MUST be deleted only after every head is equal (the order of PF-78).
- **MF-47** — An import from an older `.jc/layout` or an older `apiVersion` MUST run `jcctl migrate` and land the migrated tree as the Change; a newer one MUST be refused (CC-53).
- **MF-49** [S] — A whole-project export (MF-45) MUST carry a copy of every organization model a space of the project imports, at the pinned version, and the `kind: Bundle` index MUST list each copy with its name, version, the SHA-256 of its LinkML source and its origin (organization, name); the bundle MUST hold schema files only, no secret, credential or entity data ([ADR-N-039](../Decisions/adr-n-039-organization-and-project-data-models.md)).
- **MF-50** [S] — Importing a bundle (MF-46) MUST map each carried model onto a destination organization model of the same name whose published version of that major has a byte-identical source, or land it as a project model at `projects/{slug}/datamodels/{name}/` with `spec.origin` and rewrite the spaces' imports to it in the same Change; the preview MUST show which happens to each model, the import MUST NOT write into the destination's organization repository or replace an organization model, and a model neither mapped nor landed MUST refuse the import naming it.

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| MF-37 | [Architecture/06-configuration-as-code.md#3-the-reconciler-engine](../Architecture/06-configuration-as-code.md#3-the-reconciler-engine) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-01…MF-10 | [Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12](../Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-11…MF-15 | [Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12](../Architecture/06-configuration-as-code.md#2-manifest-envelope--kinds-catalogue-cc-09-cc-12) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| MF-16…MF-19 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| MF-41 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| MF-20…MF-26 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| MF-27…MF-32 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency](../Testing/04-configuration-and-pipeline-tests.md#4-plan-and-idempotency) |
| MF-33…MF-34 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/03-frontend-and-e2e-tests.md#2-playwright-twice](../Testing/03-frontend-and-e2e-tests.md#2-playwright-twice) |
| MF-35 | [Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39](../Architecture/08-pipelines.md#6-external-feeds-the-datasource-kind-mf-35-pl-39) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-36 | [Architecture/04 §5a](../Architecture/04-context-spaces-and-endpoints.md#5a-federation-registrations-and-the-hub-endpoint) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-38 | [Architecture/08-pipelines.md#7-testing-a-pipeline-before-proposing-it](../Architecture/08-pipelines.md#7-testing-a-pipeline-before-proposing-it) | [Testing/04-configuration-and-pipeline-tests.md#5-bento-pipelines](../Testing/04-configuration-and-pipeline-tests.md#5-bento-pipelines) |
| MF-39 | [Architecture/08-pipelines.md#7-testing-a-pipeline-before-proposing-it](../Architecture/08-pipelines.md#7-testing-a-pipeline-before-proposing-it) | [Testing/04-configuration-and-pipeline-tests.md#5-bento-pipelines](../Testing/04-configuration-and-pipeline-tests.md#5-bento-pipelines) |
| MF-42 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository](../Testing/04-configuration-and-pipeline-tests.md#2-the-gate-on-an-organization-repository) |
| MF-40 | [Architecture/07-agents-and-mcp.md#8-what-an-agent-may-reach](../Architecture/07-agents-and-mcp.md#8-what-an-agent-may-reach) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-43 | [Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes](../Architecture/06-configuration-as-code.md#8-identity-local-names-and-rendered-prefixes) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-44 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync--defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/01-backend-tests.md#3-jcctl](../Testing/01-backend-tests.md#3-jcctl) |
| MF-45…MF-47 | [Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34](../Architecture/06-configuration-as-code.md#6-download-import-and-sync-defined-by-the-user-in-the-ui-cc-49cc-53-mf-16mf-34) | [Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation](../Testing/04-configuration-and-pipeline-tests.md#1-manifest-validation) |
| MF-49…MF-50 | [ADR-N-039](../Decisions/adr-n-039-organization-and-project-data-models.md) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |

## Related

- [Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) — Configuration as Code architecture, sync waves, and lanes.
- [Development/04-manifest-kinds.md](../Development/04-manifest-kinds.md) — developer guide for implementing manifest serde models and schemas.
- [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) — manifest validation and reconciler idempotency suites.
- [User-Guide/09-export-import.md](../User-Guide/09-export-import.md) — user guide for UI export, import, and sync workflows.
