---
sidebar_position: 1
title: "Next Platform: Analysis of Today"
description: What today's joinedcontext platform runs, what it costs per organization and per deployment, where tenancy rests on configuration, and why it fails.
---

# Next Platform: Analysis of Today

This report describes the joinedcontext platform as built and running on 2026-11-05, as the baseline for the many-organization design in the pages that follow. It is written for the owner and for the agents that will build the next platform. Each claim about today's system names its source: a part of the supervisor's pack (`supervisor/packs/tenancy-goal`, Parts A to F), a docs page, a code path, or a measurement on dev with the command that produced it.

## 1. Method and sources

- The pack `joinedcontext-next-platform-pack.md`: Part A (ARCHITECTURE.md), Part B (Architecture pages 01, 02, 03, 12, 13, 14), Part C (requirement bullets), Part D (decision register), Part E (inventory), Part F (KNOWLEDGE.md).
- Decision records read whole: [ADR-N-058](../../Decisions/adr-n-058-several-organizations-per-installation.md), [ADR-N-059](../../Decisions/adr-n-059-departments-and-the-unit-of-tenancy.md), [ADR-N-063](../../Decisions/adr-n-063-one-api-style-no-graphql.md).
- Code read in the shared graph checkouts (`/workspace/.cache/cg-main`, platform and Portal on main, Antares on dev).
- Incident records on the board: T-6000 and T-6182 (prod broker pool leak), T-6581 (dev disk pressure).
- Measurements on dev, read-only, on 2026-11-05 between 06:50Z and 07:10Z, with `KUBECONFIG` set to the dev kubeconfig. No write, restart or apply was made.

## 2. Components today

Part A §3 lists the runtime components. Grouped by job:

| Job | Component | Language | Per-organization state |
|---|---|---|---|
| Edge | APISIX standalone, Traefik (k3s ingress) | Lua/OpenResty, Go | routes rendered per Endpoint by jcctl |
| Identity | Keycloak, one realm per installation | Java | one group subtree per Organization (ADR-N-058 §2.5), groups `{slug}-readers`/`-writers` per project (PF-87), a static `{project}-pipelines` client per ingesting project (ADR-N-059 §1) |
| Policy edge | Context Gateway | Rust | in-memory mirror of every Endpoint and Policy |
| Data | Antares NGSI-LD broker on PostgreSQL | Rust | one broker Tenant per Context Space (PF-06), RLS on `tenant_id` |
| Configuration | Portal (API, UI, reconciler), Gitea forge and runners | Rust, Go | one repository per project (ADR-N-029), one organization repository |
| Pipelines | Bento runner, pipeline token sidecar | Go, Rust | streams per pipeline in one runner |
| Apps | jc-wasm-host, jc-functions (QuickJS), per-project apps namespace with pods, oauth2-proxy | Rust, C | a namespace per project, a 1 GiB build cache volume per App |
| Catalogue | CKAN with Solr and Redis | Python, Java | one CKAN organisation per Organization (PF-124) |
| AI | jc-assistant, agent proxy, agent runner (OpenHands) | Rust, Python | RLS per project in the `assistant` database |
| MQTT | RMQTT broker per `MqttBroker` | Rust | one pod per broker |
| Mesh and policy | Linkerd, Kyverno, NetworkPolicies, cert-manager | Rust proxy, Go | per-namespace annotations |
| Observability | OpenTelemetry Collector, Prometheus Operator, Grafana | Go | none per organization |
| Models | Model Tools (LinkML generators) | Python | none (stateless) |

Part E counts 37 deployment components, 15 platform crates and 32 Antares crates.

## 3. Measured on dev

All numbers from 2026-11-05, dev node `cpx42` (16 GB, 8 vCPU).

### Node and pods

```sh
kubectl top nodes
kubectl top pods -A --no-headers | awk '{c+=$3; m+=$4} END {print NR, c, m}'
```

| Measure | Value |
|---|---|
| Node CPU | 5188m (69 %) |
| Node memory | 13706 MiB (99 %) |
| Pods running (metrics) / pods listed | 67 / 75 |
| Sum of pod CPU | 3946m |
| Sum of pod memory | 9729 MiB |
| Deployments and StatefulSets in `dev` | 42, every one at 1 replica |

Largest pods (`kubectl top pods -A`, each figure includes its Linkerd proxy):

| Pod | CPU | Memory |
|---|---:|---:|
| postgres-cluster-1 | 1973m | 1765 MiB |
| context-broker (Antares) | 510m | 966 MiB |
| jc-assistant | 62m | 705 MiB |
| pipeline-runner (Bento) | 74m | 695 MiB |
| keycloak | 77m | 630 MiB |
| artifact-store (RustFS) | 91m | 603 MiB |
| portal | 164m | 569 MiB |
| context-gateway | 279m | 519 MiB |
| ckan-solr | 8m | 514 MiB |
| ckan | 57m | 311 MiB |
| gitea | 40m | 203 MiB |
| grafana | 4m | 187 MiB |
| apisix | 9m | 119 MiB |

Java and Python components that serve no request of their own at rest (Keycloak, Solr, CKAN, Grafana) hold 1642 MiB, 17 % of all pod memory.

### PostgreSQL

```sh
kubectl exec -n dev postgres-cluster-1 -c postgres -- psql -X -A -t -U postgres -c \
  "select coalesce(application_name,''), usename, datname, state, count(*)
     from pg_stat_activity where backend_type='client backend' group by 1,2,3,4 order by 5 desc"
kubectl exec -n dev postgres-cluster-1 -c postgres -- psql -X -A -t -U postgres -c "show max_connections"
kubectl exec -n dev postgres-cluster-1 -c postgres -- psql -X -A -t -U postgres -c \
  "select datname, pg_size_pretty(pg_database_size(datname)) from pg_database order by 2 desc"
```

| Client (user) | Active | Idle |
|---|---:|---:|
| antares | 10 | 3 |
| portal | 1 | 4 |
| ckan (ckan + ckan_datastore) | 0 | 6 |
| assistant | 0 | 3 |
| keycloak (JDBC) | 0 | 3 |
| gitea | 0 | 2 |

33 client connections of `max_connections` 55. Each backend costs about 19 MiB (KNOWLEDGE, Deployment and catalogue, T-4933): the 18 idle connections hold about 340 MiB.

| Database | Size |
|---|---:|
| antares | 29 GB |
| assistant | 5338 MB |
| portal | 2687 MB |
| ckan_datastore | 2295 MB |
| keycloak | 1142 MB |
| gitea | 106 MB |

Antares tables (`pg_class.relpages * 8192`, lock-free per KNOWLEDGE T-6204):

| Table | Size | Rows (estimate) |
|---|---:|---:|
| entity_values | 6187 MB | 24 980 538 |
| entities | 3231 MB | 1 838 214 |
| attr_instances_2026w43 | 3104 MB | 4 059 626 |
| attr_instances_2026w44 | 2056 MB | 2 991 272 |
| attr_rows_short | 968 MB | 1 386 643 |
| attr_instances_2026w45 | 502 MB | 750 505 |

`select count(*) from (select distinct tenant_id from entity_types) t` gives 93 broker Tenants. `relrowsecurity` and `relforcerowsecurity` are true on `entities`, `entity_values`, `attr_instances` and `temporal_entities`; `pg_roles` shows `rolsuper` and `rolbypassrls` false for every application role (antares, portal, assistant, ckan, keycloak, gitea, app). The data volume (`df -h /var/lib/postgresql/data`) is the node disk: 306 GB, 149 GB used (50 %) after T-6581 dropped four history partitions.

### Persistent volumes

`kubectl get pvc -n dev` lists 27 claims: 15 App build caches of 1 GiB each, Gitea 20 GiB, RustFS 10 GiB, Prometheus 10 GiB, the local dump 10 GiB, basemap tiles 12 GiB, CKAN 5 GiB and Solr 5 GiB.

## 4. Cost per organization and per deployment at rest

The fixed cost dominates. A deployment with three Organizations (`hel`, `zilina` and the installation's, ADR-N-059 §1: 10 Projects, 71 Context Spaces, 163 Endpoints) needs 9.7 GiB of pod memory before anyone signs in, because every component runs one warm replica whatever the load.

What one more Organization adds today, each item from the source named:

| Item | Cost at rest | Source |
|---|---|---|
| Keycloak group subtree | rows in the `keycloak` database, warm in Keycloak's caches | ADR-N-058 §2.5 |
| CKAN organisation | rows, Solr index documents | PF-124 |
| Project repository per project | a Gitea repository, Actions runs on change | ADR-N-029 |
| Keycloak groups and forge teams per project | 2 groups, 2 teams | PF-87, `joinedcontext-portal/src/reconciler/groups.rs` |
| Pipeline client per ingesting project | 1 static Keycloak client and its secret | ADR-N-059 §1 |
| Apps namespace per project | a namespace, NetworkPolicies, Kyverno evaluation | ADR-N-030 |
| Each App | one pod (1-2 MiB measured for static apps) and a 1 GiB build cache | `kubectl top pods -n dev-helsinki-apps`, `kubectl get pvc -n dev` |
| Each MqttBroker | one RMQTT pod, 12-17 MiB measured | `kubectl top pods -n dev` (`mqtt-*`) |
| Each Context Space | a broker Tenant, rows in every Antares table, history partitions shared by all | PF-06 |
| Gateway and Portal mirrors | every Endpoint and Policy held in memory by both | Part A §3 |

An unused Organization therefore costs a few MiB of pods and the warm caches of Keycloak, CKAN and the gateway. The marginal cost is small; the problem is that nothing shrinks below the 9.7 GiB floor, and that a busy organization's history grows the one shared disk until the node fails (§6.2).

## 5. Single-organization assumptions

Places where the code or the requirements assume one organization per deployment:

1. **One installation Organization.** Exactly one Organization sets `spec.installation` and owns the configuration repository, the gateway's `{orgDomain}`, the brokers and the platform settings (`joinedcontext-platform/crates/jc-core/src/kinds/organization.rs`, ADR-N-058 §2.2).
2. **One minting domain.** Ids are minted over the installation Organization's domain for every project (ADR-N-058 §2.2, PF-44 via `JC_ORG_DOMAIN` in rendered Bento configs).
3. **One repository for all Organizations.** "The Organizations of an Instance share its one Git repository" (PF-02); a second repository per Organization was refused in ADR-N-058 §4.
4. **One realm.** PF-01 keeps a single Keycloak realm; Organizations differ only by group subtree.
5. **One catalogue Endpoint.** The gateway's public catalogue cache holds one list per catalogue slug, with one read lock for every catalogue, and its own comment says per-slug locks are needed "if an installation ever serves more than one" (`joinedcontext-platform/crates/context-gateway/src/mcp/catalog.rs`).
6. **Org-domain fallback.** `org_domain()` with several Organizations and no `installation: true` answers the first by name (KNOWLEDGE, Tests that need setup, T-6435).
7. **Globally unique names.** Context Space names are unique in an Instance (PF-09) and CKAN dataset names are global, so two Endpoints with one `metadata.name` overwrite one package (KNOWLEDGE T-6071, T-6079).
8. **Shared Bento runner and run queue.** One pipeline-runner process runs every project's streams, and the Portal run queue is in memory (KNOWLEDGE, Bento entry, T-5824).

## 6. Recurring operational failures and root causes

### 6.1 Prod broker pool leak (T-6000, T-6182)

Prod lost every Postgres pool slot ("13 of 13 sessions idle after ROLLBACK") and every read answered "database overloaded", five times in two days. Root cause (T-6000, Antares crate antares-sql, file src/store/pg/mod.rs): sqlx 0.9 over rustls runs `close_hard()` through rustls `complete_io`, which reads when nothing is left to write, so a connection closed after a failed release ping waits forever for bytes from an idle server and keeps its slot. Test PostGIS ran without TLS, so the existing pool test passed vacuously (KNOWLEDGE T-6000). Prod stayed broken after the fix because prod ran an Antares release pinned before the fix (T-6182: `git merge-base --is-ancestor 76d1cb3f a376b65` = no). Contributing design fault: one pool shared by every tenant, so one failure mode starves all organizations at once.

### 6.2 History tables fill the disk (T-6581)

On 2026-11-04 the dev node went into DiskPressure, the kubelet evicted every pod outside kube-system and the public home answered 000. The PostgreSQL data held about 123 GB, of which Antares 105 GB, on the node's only disk. Recovery dropped the weekly history partitions `attr_instances_2026w39` to `w42` (82.4 GB freed). Root cause: history recording has no default retention and no per-tenant storage quota, the database shares the node disk with images and logs, and the only off-node copy is a nightly local dump (KNOWLEDGE, Deployment and catalogue, "Prod (smartcity) has only a nightly local dump").

### 6.3 Memory at 93-100 %

Dev measured 99 % (§3); the brief states 82-100 % for both nodes. Root causes: one warm replica of every component whatever the load (§4), three JVM or Python services holding about 1.6 GiB at rest, Keycloak sizing its heap from the container limit (KNOWLEDGE T-5892), per-backend Postgres memory of about 19 MiB times every idle pool (T-4933), and per-view router memory in the broker of about 246 KiB per view per surface (KNOWLEDGE T-5896). Under pressure the OOM killer takes Chromium renderers and cargo builds on the host and broker pods in the cluster (KNOWLEDGE T-5993, T-6033).

### 6.4 Merge latency across repositories

A change to a shared type crosses four repositories and three pins before it reaches dev: platform crate, Portal `Cargo.toml` pin, deployment `components/portal/images.yaml`, then an hourly apply; "merged on main is hours from on dev" (KNOWLEDGE T-5066). KNOWLEDGE records the costs: a Portal pin bump's gate takes about 12 minutes and carries every platform change since the last pin (T-6129, T-6292); a jc-core interface pushed before its Portal half turns `cg-dead-code` red until both land (T-5987); a new Antares grant signal needs three halves in three repositories (T-6419). Root cause: the contract types live in one repository, the consumers in three others, and each hop has its own CI, image build and pin.

### 6.5 Shared limits that leak load between organizations

The edge rate limit is per client address, shared by every agent of a host (KNOWLEDGE T-5903, T-6540); the gateway cuts every read at 10 s with its own 503 (T-5349); a project's daily assistant budget and one person's MCP minute are shared by every caller of that key (T-5962, T-5968). None of these is a per-organization fair share.

## 7. Isolation that depends on configuration

Today's isolation holds, and part of it holds only because a value is set right:

| Property | Holds because | What breaks it | Source |
|---|---|---|---|
| Broker rows stay in their Tenant | RLS on `tenant_id`, set per transaction by `set_tenant` | an application role with `BYPASSRLS` or superuser; RLS is "a belt only when the role wears it" and the broker only warns at start | Antares crate antares-sql, src/store/pg/mod.rs (`role_bypasses_rls`) |
| Assistant chunks stay in their project | RLS policies in the assistant migrations | the same role attribute | `joinedcontext-platform/crates/assistant/migrations` |
| A data read is narrowed | the Endpoint's view rule document in Antares | a Policy with no `policyRef` binds every Endpoint of its space (KNOWLEDGE T-6455) | ADR-N-050 |
| Organization admins stop at their Organization | `RoleBinding` scope checks in the Portal | a binding or Group naming people across organizations; nested groups matched by bare name before T-6408 | `joinedcontext-portal/src/permissions.rs`, PF-123 |
| A realm-level scope reaches only intended clients | client scope lists | a realm `defaultOptionalClientScopes` entry is linked to every Portal-made client | KNOWLEDGE T-6301 |
| Workloads reach only their peers | NetworkPolicies, four halves per peer | a missing half or an `ipBlock` with its own except list | KNOWLEDGE T-5314, T-6218 |
| MQTT clients stay on their broker | Linkerd Server policies | an opaque listener sees every client at the pod's address | KNOWLEDGE T-5893 |
| Shared caches serve only what the caller may read | each cache keyed by its author | a cache keyed without `jc_org`/`jc_groups` served one member's reach to another | KNOWLEDGE T-6414 (`joinedcontext-platform/crates/context-gateway/src/mcp/hub.rs`) |
| Secrets stay in their project | resolver scoped to `projects/{namespace}/` | the SOPS resolver walked the whole tree before T-6227 | KNOWLEDGE T-6227 |

The pattern: tenancy is a string (`tenant_id`, a group path, a namespace prefix) checked at each component in its own way, and several leaks of the past month were a check one component made and another forgot.

## 8. Verdict

Today's platform isolates data well at the storage layer and decides every data read in one place (ADR-N-050). It does not scale to many organizations because the deployment floor is about 10 GiB of warm pods whatever the number of organizations, because per-project resources (repositories, namespaces, clients, MQTT pods, App pods) grow with configuration rather than with use, because one pool and one disk are shared without a per-organization budget, and because tenancy is re-implemented per component. The next platform fixes these by design, not by more configuration: [02](02-architecture.md) and [04](04-isolation-threat-model.md).

## Related

- [02-architecture.md](02-architecture.md) — the target architecture that answers §4 to §7.
- [04-isolation-threat-model.md](04-isolation-threat-model.md) — each §7 row as a threat with a control and a test.
- [06-rust-components.md](06-rust-components.md) — the decision per component of §2.
- [ADR-N-058](../../Decisions/adr-n-058-several-organizations-per-installation.md) — today's several-organization model.
- [ADR-N-059](../../Decisions/adr-n-059-departments-and-the-unit-of-tenancy.md) — the seed counts and the cost of a project.
