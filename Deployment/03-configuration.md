---
sidebar_position: 4
title: "Global & Component Configuration"
---

# Global & Component Configuration

Platform configuration follows a hierarchical inheritance model. Defaults defined in `defaults/environment/` are merged with component defaults and environment overrides.

## 1. Hierarchy & Evaluation Precedence

```text
defaults/environment/global.yaml (Baseline Defaults)
  └─► defaults/environment/*.yaml.gotmpl (Cross-Component Aggregations)
        └─► deployment/environments/<env>/global.yaml.gotmpl (Environment Overrides)
              └─► components/<name>/values/<part>/base-values.yaml.gotmpl
                    └─► components/<name>/values/<part>/<profile>-values.yaml.gotmpl
                          └─► $.Values.<component>.<part>.rawValues (Direct Overrides)
```

## 2. Global Configuration Reference

The root configuration file (`deployment/environments/<env>/global.yaml.gotmpl`) controls all platform components:

```yaml
global:
  # Base fully qualified domain name
  domain: example.joinedcontext.com

  # Unique identifier for this instance (matches namespace & realm)
  instanceSlug: dev

  # Namespace strategy (OPS-03):
  #   true  = every component in the instance namespace, "dev"
  #   false = one namespace per component, "dev-postgres", "dev-keycloak", ...
  singleNamespace: true

  # Deployment profile: 'development' or 'production'
  profile: production

  # Primary email of the tenant administrator
  initialUserEmail: admin@example.com

  # Kubernetes Ingress Configuration
  ingress:
    ingressClass: nginx
    clusterIssuer: letsencrypt-prod

  # Service Mesh (Linkerd) Configuration
  serviceMesh:
    enable: true
    type: linkerd
    patchNamespaces: true
    defaultInboundPolicy: cluster-authenticated
    allowUnauthenticatedIngress: false

  # Kyverno Admission and Runtime Policies
  runtimePolicies:
    enabled: true
    failureAction: Enforce

  # Storage Classes Mapping
  storage:
    storageClass:
      rwo: standard-rwo

  # Metrics and Monitoring Scrape Generation
  metrics:
    enabled: true
```

`singleNamespace` is a property of the environment, not a flag: `--set` and
`--state-values-set` reach the entrypoint and not the components that resolve namespaces, so
the value has to be written into `global.yaml.gotmpl` before the render. Both strategies are
supported for the whole platform (OPS-03) and neither is a migration of the other: switching
one renders every workload into a different namespace, which the reconciler does not move for
you. Pick one per instance and keep it. One namespace is the default and the simpler thing to
read in `kubectl get all`; a namespace per component gives each an isolation boundary a cluster
administrator can grant, quota and audit separately, which is what a shared cluster wants.

The rendered manifests are the same either way in everything but the namespace: cross-component
addresses are fully qualified, every NetworkPolicy peer names the namespace it means, and each
component keeps its own ServiceAccount, so co-locating components never merges two identities.
`tests/test_namespace_modes.py` renders both and asserts exactly that.

The `development` profile seeds two realm users for the demo walkthrough, `demo.steward`
(realm role `portal-approver`, may approve change proposals) and `demo.viewer` (no role,
read only); `production` seeds none. The realm sets `registrationEmailAsUsername`, so the
login a person types is the address, `demo.steward@{orgDomain}`, not the short handle; the
handle names the Secret. Seeding a user whose username and email differ aborts the whole
realm import, which leaves the realm without any of its clients. Their passwords are
generated per cluster into the Secrets `keycloak-user-demo-steward` and
`keycloak-user-demo-viewer` in the instance namespace and never appear in Git:

```bash
kubectl get secret -n dev keycloak-user-demo-steward -o jsonpath='{.data.password}' | base64 -d && echo
```

## 3. Component-Specific Configurations

### Context Broker (`components/context-broker`)

```yaml
context-broker:
  broker:
    engine: antares # Supported: antares, stellio, scorpio
    antares:
      logLevel: info
      temporalBackend: postgres
      maxPaginationLimit: 1000
      defaultPaginationLimit: 50
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 2000m
        memory: 4Gi
```

### Context Gateway (`components/context-gateway`)

The gateway is configured through its environment, rendered by the component from the global
values; the binary refuses to start rather than run half-configured.

| Variable | From | Meaning |
|---|---|---|
| `JC_GATEWAY_BROKER_URL` | the broker service | scheme and authority of the broker it forwards to; required |
| `JC_GATEWAY_ORG_DOMAIN` | `global.orgDomain` | the org-domain segment of every entity URN, checked on every write ([PF-42](../Requirements/platform.md)); required |
| `JC_GATEWAY_PUBLIC_URL` | `https://{global.domain}` | makes `https://{host}/api/endpoint/{slug}` an accepted token audience next to the bare slug ([PF-45](../Requirements/platform.md)) |
| `JC_OIDC_ISSUER` | `https://idm.{global.domain}/realms/{global.instanceSlug}` | the `iss` every token must carry |
| `JC_OIDC_JWKS_URL` | the in-cluster Keycloak service, plain `http://` | the realm keys, refreshed in the background; both OIDC variables or neither, and without them only endpoints with `audience: public` answer |
| `JC_GATEWAY_EGRESS_URL` | unset, and then `JC_GATEWAY_PUBLIC_URL` | the base a rewritten `notification.endpoint.uri` carries, which is the address the broker dials to deliver ([R46](../Requirements/policy-firewall.md)); pointing it at the in-cluster Service keeps a delivery inside the cluster, where the NetworkPolicy admitting only the broker applies to it |
| `JC_GATEWAY_EGRESS_CA_BUNDLE` | unset | a PEM file of extra roots the notification egress dispatcher trusts on top of the public ones, for subscribers behind the installation's own CA ([R46](../Requirements/policy-firewall.md)); unreadable or empty stops the gateway |
| `SSL_CERT_FILE` | `/etc/ssl/certs/ca-certificates.crt` | the public trust anchors the egress dispatcher reads at start-up ([R46](../Requirements/policy-firewall.md)). The image ships them; set this only when the roots live somewhere else. Unreadable or holding no certificate stops the gateway |
| `JC_GATEWAY_REPO_DIR` | a checkout of the configuration repository | the tree the endpoint table is projected from ([CC-08](../Requirements/city-as-code.md)); without it the table is empty and every slug is a 404 |

`global.orgDomain` is the organization's own DNS name (`hel.fi` on `dev`), not the
platform's `global.domain`. The development profile seeds `JC_GATEWAY_REPO_DIR` from a ConfigMap
with one context space, one public endpoint and one read-only policy, so the surface answers
from the broker before the forge checkout exists; production carries no seed.

### APISIX Standalone Gateway (`components/apisix`)

APISIX runs strictly in file-based declarative mode:

```yaml
apisix:
  apisix:
    enabled: true
    deployment:
      role: data_plane
      role_data_plane:
        config_provider: yaml
    etcd:
      enabled: false # ETCD is completely disabled
    service:
      type: ClusterIP
    admin:
      enabled: false # Zero Admin API attack surface
```

:::warning
The generated `apisix.yaml` mounted inside the container **MUST** terminate with the string `#END`. If the `#END` marker is missing from the template rendering, APISIX fails silently and discards all routing rules.
:::

### Keycloak realm (`components/keycloak`)

The realm carries one optional client scope, `mcp:portal`, whose audience mapper adds
`portal-api` to the access token ([AG-60](../Requirements/agents.md), RFC 9728). The Portal MCP
server at `/api/v1/mcp` accepts only a bearer whose `aud` names the Portal, so an MCP client
(a phone app on `mcp-mobile`, a client behind the edge login on `edge`) asks for
`scope=openid mcp:portal` and nothing else on its token changes. The scope is optional until
RFC 8707 resource indicators replace it; a client that does not ask for it keeps a token the
MCP route refuses with `401` and `WWW-Authenticate: Bearer resource_metadata=…`.

### Pipeline Runner (`components/pipeline-runner`)

```yaml
pipeline-runner:
  runner:
    engine: bento
    image:
      repository: ghcr.io/warpstreamlabs/bento
      tag: 4.24.0
    streamsMode:
      enabled: true
      configPath: "/etc/bento/streams"
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: 1000m
        memory: 1Gi
```

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
