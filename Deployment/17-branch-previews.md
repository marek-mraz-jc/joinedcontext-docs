---
sidebar_position: 18
title: "Branch Previews on dev"
description: "What a code-branch preview runs on the dev node, what it costs in memory, how many fit today and on each node option, how it is isolated from dev, how it is reached and reaped, and why it never promotes anything."
---

# Branch Previews on dev

A branch preview runs the code of one branch of `joinedcontext-portal`, `joinedcontext-platform` or the Antares broker on the `dev` node, so a person can open the change in a browser before it is merged. This page records the shape decided in [ADR-N-062](../Decisions/adr-n-062-branch-previews-on-the-dev-node.md), the memory it costs and the isolation the preview tests check. Workspace previews ([ADR-N-024](../Decisions/adr-n-024-workspaces-branch-and-preview.md)) are a different thing: they render a configuration branch inside the shared Portal and gateway and run no workload of their own.

## 1. What a preview runs

A preview runs only the services its branch changed, plus the ones they cannot start without, each with one replica, in a namespace of its own, `pv-{slug}`. `{slug}` is the branch name as a DNS-1123 label of at most 40 characters (T-5547 computes it).

| Branch changes | The preview runs | It does not run |
|---|---|---|
| Portal (`joinedcontext-portal`) | `portal` and `portal-ui`, both from the branch | gateway, broker, pipeline runner, assistant, CKAN, model tools, functions, WASM host, mail catcher |
| Gateway (`joinedcontext-platform`) | `context-gateway` from the branch, `portal` and `portal-ui` from dev's pinned digests | broker and the rest above |
| Portal and gateway | both from the branch | broker and the rest above |
| Antares broker | `context-broker` from the branch, `context-gateway`, `portal` and `portal-ui` from dev's pinned digests | the rest above |

The Portal starts without the services it does not run: each of `JC_PORTAL_GATEWAY_URL`, `JC_PORTAL_PIPELINE_RUNNER_URL`, `JC_PORTAL_KNOWLEDGE_URL` and the catalogue URLs is optional (`joinedcontext-portal` `src/config.rs`), and the route that needs one answers 503 while it is unset. A service the Portal refuses to start without, found by the first preview (T-5548), joins the table above in the same branch that finds it.

Each preview holds four things of its own and nothing of dev's:

1. **A database** `pv_{slug}` in the shared CNPG cluster `postgres-cluster`, owned by the role `pv_{slug}` with `CONNECTION LIMIT 4`, no grant on any other database, and a `pg_hba` line that refuses every role whose name starts `pv_` on any database but its own. Postgres grants `CONNECT` to `PUBLIC` on every new database, and dev's databases never revoke it, so the `pg_hba` refusal is the control a grant alone is not.
2. **Keycloak clients** `pv-{slug}-portal` (and `pv-{slug}-gateway` when the gateway runs) in one realm `preview` that every preview shares. The realm holds the fixture people only; no dev person can sign in to a preview, so nobody types a dev password into branch code. The Portal's admin client holds the `realm-management` roles of `preview` alone.
3. **A forge organization** `pv-{slug}` in dev's Gitea, whose one repository is loaded from a committed fixture (one Organization, one Project, two Context Spaces, three Endpoints, two people). The Portal's Gitea user is a member of that organization only. No dev data is copied into a preview, and the bounded copy ADR-N-024 allows a workspace preview (PF-83) does not exist here: a branch preview has no route to dev's Endpoints to copy through.
4. **Its own Secrets**: the database password CNPG generates for `pv_{slug}`, the client secrets of its Keycloak clients, its Gitea token and the Portal's session key, all created in `pv-{slug}` by the preview recipe. No `secretRef` of a preview names a Secret of the `dev` namespace.

## 2. Memory

dev is one `cpx42`: 13,805 Mi allocatable (`kubectl get node -o jsonpath='{.items[0].status.allocatable.memory}'`, 14,136,272 Ki). At 2026-10-24T19:37Z the node used 12,990 Mi (94 %), and the sum of memory requests is 78 % of allocatable, about 10.5 GiB ([Operations/02](../Operations/02-capacity-and-scaling.md) section 4). The largest pods were `pipeline-runner` 1,888 Mi, `postgres-cluster-1` 1,090 Mi, `jc-assistant` 819 Mi, `keycloak` 759 Mi, `context-gateway` 672 Mi, `context-broker` 659 Mi and `portal` 288 Mi (`kubectl top pods -n dev`).

A preview starts with dev's request and a lower limit: a preview holds the fixture, not dev's 2,364-file repository, and lives at most 48 hours, so it never reaches the growth dev's limits were raised for. The working set is the dev pod's measured use, an upper bound for a pod that serves one person and a fixture; the first preview of T-5548 measures the real number and moves the request to it.

| Container | Request | Measured working set on dev | Preview limit | dev limit |
|---|---|---|---|---|
| `portal` | 576 Mi | 288 Mi on 2026-10-24; 276-474 Mi over a day (T-5282) | 1 Gi | 1536 Mi |
| `portal-ui` | 32 Mi | under 32 Mi | 128 Mi | 128 Mi |
| `context-gateway` | 384 Mi | 672 Mi under dev's load; 210-310 Mi at rest | 768 Mi | 1 Gi |
| `context-broker` | 448 Mi | 659 Mi with dev's 132 GB history | 1 Gi | 1536 Mi |
| Linkerd proxy, per pod | 64 Mi | 20-40 Mi | 128 Mi | chart default |
| Postgres backends, in `postgres-cluster-1` | none | 10-40 Mi per connection, 4 at most | none | none |

Requests come from the `development` values (`components/*/values/*/development-values.yaml.gotmpl` in the deployment repository); working sets from T-4473, T-5282 and the 2026-10-24 sample.

That makes three preview sizes. "At rest" adds the at-rest figures; "at most" adds dev's measured peaks and four busy database connections, and the counts in section 3 use it.

| Preview | Requests | Working set, Postgres backends included | Limits |
|---|---|---|---|
| Portal | 736 Mi | about 0.45 GiB at rest, 0.75 GiB at most | 1.4 GiB |
| Portal and gateway | 1,184 Mi | about 0.75 GiB at rest, 1.45 GiB at most | 2.3 GiB |
| Portal, gateway and broker | 1,696 Mi | about 1.1 GiB at rest, 2.15 GiB at most | 3.4 GiB |

## 3. How many fit

Two lines from [Operations/02](../Operations/02-capacity-and-scaling.md) section 5 decide it: the node's working set stays under 80 % of allocatable, and the sum of requests under 85 %. The count below keeps 1 GiB beside the previews for one rolling update's surge pod. The `cpx42` and `cpx52` figures are measured (prod runs a `cpx52`: 21.1 GiB allocatable); the other two are estimates from the same reserve, about 2.5 to 3 GiB per node, and are marked so.

| Node | Allocatable | Room under 80 % after dev's 12.4 GiB and 1 GiB surge | Portal previews | Portal and gateway | With the broker |
|---|---|---|---|---|---|
| `cpx42` today (16 GB) | 13.5 GiB | none: dev is at 94 % | 0 | 0 | 0 |
| `cpx42` after T-4936 (runner back at about 700 Mi) | 13.5 GiB | none under 80 %; under the recipe's 90 % refusal, about 0.6 GiB | 1 at its at-rest size, by owner exception to the 80 % line | 0 | 0 |
| `cpx52` (24 GB) | 21.1 GiB | 3.5 GiB | 4 | 2 | 1 |
| `cpx62` (32 GB), estimate | about 28.7 GiB | about 9.6 GiB | 12 | 6 | 4 |
| `cpx42` plus a `cpx32` agent node (8 GB) tainted for previews, estimate | about 6.5 GiB on the agent | about 4.2 GiB on the agent | 5 | 2 | 1 |

Today no preview fits. The recipe (T-5548) refuses to start one while the node is above 90 % of allocatable, and the cap of concurrent branch previews is 2 on any node, the same cap ADR-N-024 set for workspace previews, so that a larger node goes first to the cities Operations/02 plans for. A larger node or an agent node is the owner's money: this page names the options and orders none. Of the three, the tainted agent node is the one whose previews can never evict a dev pod, because they never share its memory.

A full second instance was measured and refused. `.ci/golden/dev.txt` (deployment `531cc78c`) holds 642 objects, 60 of them cluster-scoped; 46 of those have fixed names (11 CNPG CRDs, the CNPG webhooks, 17 Kyverno ClusterPolicies, `jc-drift-reader`, the `prometheus-*` roles), so a second render collides with the first unless it is split by `deployLayer: instance` (`defaults/deployment/helmfile-instance.yaml.gotmpl`), which dev does not run. Even split, a second instance costs about as much memory as dev does now: more than the node has.

## 4. Host and certificate

A preview answers on `preview-{slug}.dev.joinedcontext.com` through a Traefik `Ingress` of its own namespace, beside APISIX and not through it, with a cert-manager `Certificate` for that one host from `letsencrypt-prod` by HTTP-01. No wildcard certificate and no DNS API token are added (CLAUDE.md, cluster rules).

`dev` and prod share the registered domain `joinedcontext.com`, so they share Let's Encrypt's limits: 50 new certificates per registered domain per 7 days, 5 for the same set of names per 7 days, and 5 failed validations per host per hour ([14-production-smartcity](14-production-smartcity.md)). The recipe therefore:

- issues at most 10 preview certificates per 7 days, counted from the `Certificate` objects labelled `sandbox.joinedcontext.com/lifecycle: preview` and their creation times, which leaves 40 for dev's edge certificate and prod;
- keeps a branch's slug, and so its host, the same on every start, and refuses a sixth start of one host within 7 days;
- requests the certificate only after `http://preview-{slug}.dev.joinedcontext.com/.well-known/acme-challenge/` reaches the preview's Ingress, and never retries an order in a loop.

## 5. Lifetime and cleanup

The namespace carries the label `sandbox.joinedcontext.com/lifecycle: preview` and the annotation `sandbox.joinedcontext.com/ttl: 48h`. The sandbox reaper (`components/sandbox-reaper/charts/reaper/files/reap.sh`) lists namespaces with that label once an hour and deletes each one older than its `ttl`, or older than the 14-day ceiling when the annotation is missing or unreadable (OPS-44, PF-19). The reaper is not deployed on dev today: it is absent from `.ci/golden/dev.txt` while prod renders it. T-5548 adds it to dev before the first preview starts.

Deleting the namespace removes the workload, its Secrets, Ingress and Certificate. The database, its role, the Keycloak clients and the Gitea organization live outside it, so `just dev-preview-down {slug}` (T-5548) removes those four by name, and the reaper's deletion of an expired namespace is followed by the same cleanup on the recipe's next run.

## 6. The preview namespace

What the recipe creates first, before any workload. The ResourceQuota is the largest preview size of section 2; the LimitRange gives a container that names nothing the Portal's preview limit. The NetworkPolicy lets in only Traefik and lets out only DNS and the three dev services a preview needs: Keycloak, the preview's own database in `postgres-cluster` (the `pg_hba` line keeps it there) and Gitea, each on its service port and on the Linkerd inbound port 4143. Each of the three callees needs the matching ingress half naming `pv-*` namespaces, which T-5548 adds to their NetworkPolicies. dev's gateway, broker and Portal are not in the list, and the internet is not either.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pv-example
  labels:
    sandbox.joinedcontext.com/lifecycle: preview
    pod-security.kubernetes.io/enforce: restricted
  annotations:
    sandbox.joinedcontext.com/ttl: 48h
    linkerd.io/inject: enabled
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: preview
  namespace: pv-example
spec:
  hard:
    pods: '6'
    requests.cpu: '1'
    limits.cpu: '6'
    requests.memory: 1696Mi
    limits.memory: 3584Mi
    services.loadbalancers: '0'
    services.nodeports: '0'
---
apiVersion: v1
kind: LimitRange
metadata:
  name: preview
  namespace: pv-example
spec:
  limits:
    - type: Container
      default:
        cpu: 500m
        memory: 1Gi
      defaultRequest:
        cpu: 50m
        memory: 128Mi
      max:
        cpu: '1'
        memory: 1Gi
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: preview
  namespace: pv-example
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: kube-system }
          podSelector:
            matchLabels: { app.kubernetes.io/name: traefik }
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 4143
  egress:
    - to:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: kube-system }
          podSelector:
            matchLabels: { k8s-app: kube-dns }
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    - to:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: dev }
          podSelector:
            matchLabels: { app.kubernetes.io/instance: keycloak-app }
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 4143
    - to:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: dev }
          podSelector:
            matchLabels: { cnpg.io/cluster: postgres-cluster }
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 4143
    - to:
        - namespaceSelector:
            matchLabels: { kubernetes.io/metadata.name: dev }
          podSelector:
            matchLabels: { app.kubernetes.io/name: gitea }
      ports:
        - protocol: TCP
          port: 3000
        - protocol: TCP
          port: 4143
```

Traffic between the preview's own pods (the Portal calling its own gateway) needs one more rule of the same shape with `podSelector: {}` and no namespace selector; the recipe adds it only when the preview runs more than one service.

## 7. Isolation the tests check

The preview isolation suite T-5548 adds to the conformance repository (`tests/security`, `test_preview_isolation.py`) runs from a Job inside the preview namespace, under the preview's NetworkPolicy, and checks five properties:

1. **No network path to dev's services.** TCP from the preview to `context-gateway`, `context-broker` and `portal` in `dev`, and to any address outside the cluster, fails.
2. **No database grant.** The role `pv_{slug}` cannot connect to `portal`, the broker's database or any database but `pv_{slug}`, and reads nothing there.
3. **Preview tokens are refused by dev.** A token of `pv-{slug}-portal` from realm `preview` gets 401 at dev's gateway and Portal: its issuer is not dev's realm and its audience names no dev client.
4. **No dev secret.** No pod of the preview mounts or references a Secret, ConfigMap or projected token of the `dev` namespace (`kubectl get pod -o json`, volumes and `envFrom`).
5. **Bounded size.** The ResourceQuota refuses a 2 GiB pod, and the LimitRange gives a container that names no limit 1 GiB.

A sixth property is checked by admission, not by the suite: a preview runs only images CI built and signed from its branch (T-5547, tags `pv-{slug}-{sha12}`), or dev's pinned digests for the services the branch did not change. The image-signature policy of `components/runtime-policies` applies to `pv-*` namespaces unchanged, digests only.

## 8. What a preview never does

A branch preview never touches prod and never promotes anything. Its images carry `pv-` tags that pin-images skips (T-5547), so none of them reaches `components/*/images.yaml`, dev or `dev-green`. Its forge organization is a fixture outside every project's repository, so nothing written in a preview reaches a configuration repository either. The only path to prod stays the release gate of T-0051 (`v*` tag, render diff, approval on the `production` environment) and the [Release Runbook](16-release-runbook.md). A staging cluster stays the owner's decision (2026-09-14, 2026-10-06), and so does any node bought for previews.

## Related

- [ADR-N-062](../Decisions/adr-n-062-branch-previews-on-the-dev-node.md): the decision this page carries out, with the options weighed.
- [ADR-N-024](../Decisions/adr-n-024-workspaces-branch-and-preview.md): workspace previews of configuration branches, which stay as they are.
- [Capacity and Scaling](../Operations/02-capacity-and-scaling.md): the node's memory and the add-a-node rules this page applies.
- [Release Runbook](16-release-runbook.md): the only way a change reaches prod.
- [Security Hardening](08-security-hardening.md): the NetworkPolicy, admission and image-signature layers a preview sits inside.
- [Requirements/operations.md](../Requirements/operations.md): OPS-44; [Requirements/platform.md](../Requirements/platform.md): PF-19, PF-83.
