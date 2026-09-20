---
sidebar_position: 10
title: "Component & Helm Packaging"
---

# Component & Helm Packaging

Platform deployments are modularized into independent component packages under `components/<name>/`.

## 1. Component Directory Structure

```text
components/<component-name>/
├── civitas-component.yaml           # High-level component metadata and parts list
├── charts.yaml                      # Chart source repository and pinned version
├── default-environment.yaml.gotmpl  # Default environment value exports
├── helmfile.yaml.gotmpl             # Component-level rendering template
├── images.yaml                      # Pinned container image repository and tags
├── keycloak-clients.yaml            # Optional: OIDC client registration definitions
├── networkpolicies.yaml             # Ingress/egress network isolation rules
└── values/                          # Helm values split by part and profile
    └── <part-name>/
        ├── base-values.yaml.gotmpl
        ├── development-values.yaml.gotmpl
        └── production-values.yaml.gotmpl
```

## 2. Registering an OIDC Client (`keycloak-clients.yaml`)

To automatically provision a Keycloak client for a component:

```yaml
portal:
  name: "Portal Application"
  subdomain: "portal"
  redirectPath: "/api/auth/callback/keycloak"
  publicClient: false
  roles:
    - name: admin
      description: "Platform superuser"
    - name: viewer
      description: "Read-only access"
```

## 3. Automated Component Validation

Run the validation suite before submitting component merge requests:

```bash
# Validate chart templates, images, and copier answers
just validate-components

# Verify Kyverno security policies against rendered manifests
just verify-policies <component-name>
```

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
