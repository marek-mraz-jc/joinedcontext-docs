---
sidebar_position: 5
title: "Defining Manifest Kinds"
---

# Defining Manifest Kinds

The platform configuration plane treats all resources as versioned declarative manifests. Manifests are Kubernetes-style resources (`apiVersion`, `kind`, `metadata`, `spec`, server-side `status`) governed by CC-09 and [MF-01…MF-15](../Requirements/manifests.md). The resource API at `/api/v1/projects/{project}/{plural}` and `jcctl validate|plan|apply|export|import|drift` follow kubectl conventions; the one difference is that writes become merge requests (MF-12). (`jcctl` with no arguments prints its whole subcommand list; there is no bare `get` and no bare `diff`, only `workspace diff` and `model diff`.)

## 1. Manifest Envelope Schema

Every manifest adheres to the base envelope contract:

```yaml excerpt
kind: ContextSpace               # Resource type name
apiVersion: joinedcontext.com/v1alpha1
metadata:
  name: mobility-traffic         # DNS-1123 label, unique per kind in the namespace
  namespace: mobility            # project slug ("org" for organization-level kinds)
  labels: { joinedcontext.com/domain: mobility }
  annotations: {}                # provenance (blueprint, imported-from, sync-source, managed-attributes)
  title:                         # Multilingual human titles
    en: "Mobility & Traffic Space"
    fi: "Liikenteen ja liikkumisen tila"
  description:
    en: "Live traffic telemetry and sensor observations"
    fi: "Liikenteen reaaliaikainen telemetria"
spec:
  # Resource-specific desired state (pure NGSI-LD payload for NGSI-LD kinds)
# status: never in Git — computed by jcctl, served by the Portal API (phase, conditions, observedRevision)
```

Typed references (`{kind, name, namespace?}`) instead of paths or ids keep bundles importable into another namespace (MF-07). Multi-document YAML and `kind: List` are accepted everywhere a manifest is (MF-05).

## 2. Standard Kind Catalog

| Kind | Target Directory | Engine Consumer | Description |
|---|---|---|---|
| `Organization` | Root `org.yaml` | Portal / Keycloak | Organization root settings, branding, default locales |
| `Project` | `projects/{p}/project.yaml`; in layout 2 also the registry entry `projects/{p}.yaml` of the organization repository | Portal API | Project container and team governance boundary; the registry entry names its repository, ref and parameter values (PF-86) |
| `ContextSpace` | `projects/{p}/spaces/{s}/` | Antares Broker | Context space tenant, storage, and persistence rules |
| `DataModel` | `.../spaces/{s}/datamodels/` | Gateway / Broker | LinkML schema definition & compiled JSON-LD contexts |
| `Policy` | `.../spaces/{s}/policies/` | Context Gateway | PEP access control policy (ADR 002) |
| `Endpoint` | `.../spaces/{s}/endpoints/` | Context Gateway | Multi-representation public/shared access facade |
| `ModelProjection` | `.../spaces/{s}/projections/` | Context Gateway | Named subset of the space's model (classes, slots, residual filter) that Endpoints reference and the schema surface renders from (MP-01…MP-03) |
| `Pipeline` | `projects/{p}/pipelines/` | Bento Runner | Bento ingestion/transformation stream configuration |
| `DataSource` | `projects/{p}/datasources/` | `jcctl` / Bento Runner | Connection of one external feed (MQTT, HTTP, WebSocket, GTFS-RT) with `secretRef` credentials, referenced by pipelines (MF-35) |
| `Dashboard` | `projects/{p}/dashboards/` | Portal UI | Visual map and chart layout definition |
| `SyncSource` | `projects/{p}/sync/`, `sync/` | the sync loop, in the Portal or `jcctl sync` | Continuous import from an external Git repo, bundle URL or other instance (MF-27) |
| `Mapping` | `.../spaces/{s}/datamodels/mappings/` | Model Tools / Gateway | LinkML-Map model-to-model transformation compiled to Bloblang and gateway IR (DM-35) |
| `Subscription` | `.../spaces/{s}/subscriptions/` | Antares Broker | NGSI-LD subscription reconciled in wave 4 |
| `Layer` | `projects/{p}/dashboards/` | Portal UI | One map, table or chart layer bound to an Endpoint |
| `App` | `projects/{p}/apps/` | Portal static host / App reconciler | App on Demand with its `dataNeeds`, build and login front (AP-01) |
| `Blueprint` | `blueprints/{name}/blueprint.yaml` | `jcctl` expansion / Portal UI | Parameterized template: parameter schema, templates, risk class and allowed roles (CC-23, CC-24, CC-25) |
| `AgentProfile` | `agentprofiles/{name}.yaml` | Portal agent runner / `jc-agent-proxy` | One agent runtime profile: role (`steward` or `builder`), image digest, model, limits, egress allow-list and tools (AG-47, AG-48) |
| `ServiceAccount` | `projects/{p}/access/serviceaccounts/` | Keycloak / Gateway | Workload identity with audience-bound tokens and scoped roles (PF-45) |
| `Environment` | `environments/{name}.yaml` | every loader (`JC_ENVIRONMENT`) | The overlay one environment renders the repository with: org domain, hosts, digests, secret backend, flags (CC-73…CC-75) |
| `Group` | `users/groups/{name}.yaml` | reconciler → Keycloak | One named set of people by e-mail; the reconciler is the only writer of the Keycloak group it manages and reports drift (PF-62, PF-63) |
| `Role` | `users/roles/{name}.yaml` or `projects/{p}/roles/{name}.yaml` (PF-68) | `jcctl` roles / Keycloak | One named set of verbs on kinds, with constraints; compiled into CODEOWNERS, `policies/roles.json` and the organization repository's Rego gate (PF-51, CC-41) |
| `RoleBinding` | `users/assignments/{name}.yaml` | `jcctl` roles / Keycloak | Assignment of one `Role` to a subject over a scope, with a validity window (PF-52, CC-42) |
| `ScopeDefinition` | `projects/{p}/policies/` | Antares Broker | Node of the hierarchical scope tree (`isRoot`, `isChildOf`, `scopeString`, ADR 005); served as `scopedefinitions`, a plural of its own, although its file sits beside the project's other access files (R19) |
| `SharedSpaceReference` | `projects/{p}/shares/` | Context Gateway | Cross-project or cross-instance mount of another Endpoint (EP-15, DS-17) |
| `ContextSourceRegistration` | `.../spaces/{s}/registrations/` | Antares Broker | Where part of a space's data actually lives, so the broker can forward and merge; a hub space holds only these (MF-36, EP-70, PF-48) |
| `CkanInstance` | `projects/{p}/ckan/` | `jcctl` publisher / Portal API | One open-data portal an Endpoint may publish to: base URL, default organization and the API token `secretRef` (EP-62, EP-67) |
| `UiSchema` | `portal/forms/{name}.uischema.yaml` | Portal UI | Form arrangement for one kind: order, widgets, help, grouping; `metadata.name` is `spec.for` lowercased (UI-02) |
| `List`, `Bundle`, `Change`, `ChangeList` | not stored | all / import / resource API | Envelopes for download, import and write results (MF-05, MF-17, MF-12) |

### Paths under layout 2

In layout 2 ([ADR-N-029](../Decisions/adr-n-029-one-repository-per-project.md), CC-85) a project's kinds sit at the root of the project's own repository: the path of every `projects/{p}/…` row above loses its `projects/{p}/` prefix there, so a pipeline is `pipelines/{name}/pipeline.yaml` of the project repository. The organization-level rows stay in the organization repository, which gains the registry, `projects/{p}.yaml`, one `kind: Project` entry per project. Every loader assembles the two into the tree of the table (CC-86), which is why a kind's `PATH_TEMPLATE` in `jc-core` keeps the `projects/{project}/` prefix: it addresses the assembled tree, and a checkout of one project repository is mounted at that prefix.

```yaml excerpt
# projects/air.yaml, the registry entry in the organization repository (PF-86)
kind: Project
apiVersion: joinedcontext.com/v1alpha1
metadata: { name: air, namespace: org }
spec:
  repository: { name: air }
  ref: v1.4.0
  parameters: { stationCount: 12 }
```

A new kind therefore needs no second path: it declares the `PATH_TEMPLATE` it would have in layout 1, organization-level or under `projects/{project}/`, and the assembly places it.

### Schema not published yet

`jcctl schema export` writes one draft-07 schema per kind to `schemas/kinds/{Kind}.json`, and the documentation checks manifests against the schemas of one pinned platform tag, not against `main`. Every kind in the table above has a schema in the pinned tag; a kind whose `jc-core` type lands before its schema is listed here, checked structurally and against the kind table only, until the tag carries it:

Nothing is on this list: the pinned tag carries a schema for every kind of the table above.

The list is checked as strictly as the manifests are: once the pinned tag carries a schema, the entry here is reported until it is removed.

## 3. Adding a New Kind

1. **Implement the Rust Serde Model**: add the typed definition to `crates/jc-core/src/kinds/{kind}.rs`, with `#[serde(deny_unknown_fields)]`, and register it in `crates/jc-core/src/registry.rs`. The JSON Schema is derived from the type, never written beside it, so the two cannot drift.
2. **Export the Schema**: `jcctl schema export` writes `schema/kinds/{Kind}.json` in **draft-07**; the committed file is checked against a fresh export in CI.
3. **Give it a sync wave**: the order a plan converges in comes from the kind alone, in `crates/jcctl/src/waves.rs` (research verdict P4 rejects a free-form dependency DAG). A kind with no wave is a kind the reconciler does not know when to apply. Kinds that drive a live system get their converger beside the others in `crates/jcctl/src` (`pipelines.rs`, `service_accounts.rs`, `roles.rs`, `apisix.rs`, …); there is no `reconcilers/` directory and no `Reconcile` trait.
4. **Publish UI Schema**: add the form arrangement to `portal/forms/{kind}.uischema.yaml` in the configuration repository, whose `metadata.name` is `spec.for` lowercased (UI-02). Without it the Portal renders the raw JSON Schema.
5. **Register the resource API**: add the plural and the `utoipa` paths so the kind answers under `/api/v1/projects/{project}/{plural}` **and appears in `ui/openapi.json`** (MF-11, MF-14). A route with no `#[utoipa::path]`, or one missing from the ApiDoc's `paths(...)`, is served but undescribed, so no generated client can call it. Download and import come free from the envelope.
6. **Tests**: schema golden files, one proptest that `import(export(x)) == x` for the kind (MF-17), and a loader case for each way two files can claim one identity.

## Related

- [MF-01…MF-15](../Requirements/manifests.md) — referenced above.
- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
