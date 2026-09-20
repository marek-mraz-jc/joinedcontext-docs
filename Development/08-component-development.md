---
sidebar_position: 10
title: "Component & Helm Packaging"
---

# Component & Helm Packaging

Platform deployments are modularized into independent component packages under `components/<name>/`.

## 1. Component Directory Structure

```text
components/<component-name>/
├── component.yaml                   # the component and its parts
├── charts.yaml                      # chart source repository and pinned version
├── default-environment.yaml.gotmpl  # default environment value exports
├── helmfile.yaml.gotmpl             # component-level rendering template
├── images.yaml                      # container images, pinned by digest
├── apisix-routes.yaml               # optional: the routes APISIX standalone serves
├── apisix-plugins.yaml              # optional: the plugin chain of those routes
├── keycloak-clients.yaml            # optional: the OIDC clients the realm template builds
├── databases.yaml                   # optional: the CloudNativePG databases the part needs
├── secrets.yaml                     # optional: secretRef names, never a secret value
├── networkpolicies.yaml             # ingress and egress isolation
├── networkpolicies-linkerd.yaml     # the same for the meshed path
└── values/                          # Helm values per part and profile
    └── <part-name>/
        ├── base-values.yaml.gotmpl
        ├── development-values.yaml.gotmpl
        └── production-values.yaml.gotmpl
```

`components/portal/` is the fullest example of all of these. `just new-component` scaffolds a new one from `template-component/`.

## 2. Registering an OIDC Client (`keycloak-clients.yaml`)

A component declares the clients it needs, and the realm template builds `rootUrl`, `redirectUris` and `webOrigins` from `subdomain`. A browser client is public with PKCE and no secret; a backend client is confidential and may carry a service account.

```yaml
portal-ui:
  name: Portal UI
  description: Browser client of the portal single-page UI; public, PKCE only, no secret
  subdomain: portal
  redirectPath: /*
  rawValues:
    publicClient: true
    standardFlowEnabled: true
    directAccessGrantsEnabled: false
    serviceAccountsEnabled: false

portal-api:
  name: Portal API
  description: Confidential client of the portal backend for the OIDC code flow and its service account
  subdomain: portal
  redirectPath: /api/v1/auth/callback
  componentNamespaces:
    - portal
```

No client secret is written here. The realm mints it and the deployment resolves it by `secretRef`; a secret in this file would be a secret in Git.

## 3. Automated Component Validation

Run the validation suite before submitting component merge requests:

```bash
just validate            # every pre-commit hook over the whole repository
just verify-policies     # the Kyverno policies against the rendered manifests
just test-policies       # the policy regression fixtures, good and bad
```

`just --list` prints the rest, grouped. These take no component argument: they run over everything the repository renders, which is the point, because a component that renders on its own can still break the chain it sits in.

## Related

- [00-intro](00-intro.md) — the repositories and the toolchain.
- [../Deployment/04-components-and-addons.md](../Deployment/04-components-and-addons.md) — what each component is and how it is sized.
- [../Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) — how a change reaches the platform.
