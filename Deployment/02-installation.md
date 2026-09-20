---
sidebar_position: 3
title: "Installation Guide"
---

# Installation Guide

The platform uses a two-tier Helmfile execution architecture:

1. **Shared Operators Layer** (`deployment/helmfile-operators.yaml`): Deployed once per cluster. Installs CloudNativePG operator, Strimzi (if messaging addons are used), and cluster-scoped Kyverno policies.
2. **Instance Layer** (`deployment/helmfile-instance.yaml.gotmpl`): Deployed per instance or city tenant namespace.

## 1. Step 1: Clone Deployment Repository

```bash
git clone https://github.com/<org>/joinedcontext-deployment.git
cd joinedcontext-deployment
cp -r defaults/deployment deployment
```

## 2. Step 2: Configure Environment

Create or edit your target environment file under `deployment/environments/<env>/global.yaml.gotmpl`:

```yaml title="deployment/environments/production/global.yaml.gotmpl"
global:
  domain: city.example.joinedcontext.com
  instanceSlug: prod
  profile: production
  initialUserEmail: admin@city.example.com

  ingress:
    clusterIssuer: letsencrypt-prod
    ingressClass: nginx

  serviceMesh:
    enable: true
    type: linkerd
    patchNamespaces: true
    defaultInboundPolicy: cluster-authenticated
    allowUnauthenticatedIngress: false

  runtimePolicies:
    enabled: true
    failureAction: Enforce

  storage:
    storageClass:
      rwo: local-nvme

components:
  - prepare
  - secrets
  - networkpolicies
  - runtime-policies
  - postgres
  - keycloak
  - gitea
  - apisix
  - context-broker
  - context-gateway
  - portal
  - jcctl
  - pipeline-runner
```

## 3. Step 3: Deploy Shared Operators

Ensure operators are installed in the `joinedcontext-operators` namespace:

```bash
helmfile -f deployment/helmfile-operators.yaml -e production sync
```

Verify that operator CRDs (`clusters.postgresql.cnpg.io`, `clusterpolicies.kyverno.io`) are registered:

```bash
kubectl get crd | grep -E 'cnpg|kyverno'
```

## 4. Step 4: Pre-generate Required Secrets

Generate the mandatory initial secrets before triggering the instance deployment:

```bash
INSTANCE_SLUG="prod"
kubectl create namespace "${INSTANCE_SLUG}" || true

# Keycloak SMTP configuration for invitations and verification
kubectl create -n "${INSTANCE_SLUG}" secret generic keycloak-smtp \
  --from-literal=host='smtp.city.example.com' \
  --from-literal=port='587' \
  --from-literal=from='noreply@city.example.com' \
  --from-literal=user='smtp-user' \
  --from-literal=password='super-secret-smtp-password'
```

## 5. Step 5: Sync Instance Deployment

Execute the instance release pipeline:

```bash
helmfile -f deployment/helmfile-instance.yaml.gotmpl -e production sync
```

Monitor pod readiness in the namespace:

```bash
kubectl get pods -n prod -w
```

## 6. Step 6: Initial Login & Configuration-as-Code Bootstrap

1. Retrieve initial generated credentials:

   ```bash
   # Keycloak Master Admin Password
   kubectl get secret -n prod keycloak-admin-user -o jsonpath='{.data.password}' | base64 -d && echo
   
   # Gitea Administrator Credentials
   kubectl get secret -n prod gitea-admin-credentials -o jsonpath='{.data.password}' | base64 -d && echo
   ```

2. Log in to `https://idm.city.example.joinedcontext.com/admin/prod/console`.
3. Log in to `https://portal.city.example.joinedcontext.com` using `admin@city.example.com`.
4. The Portal will prompt to initialize the primary **Organization** and connect to the in-cluster Gitea instance (`https://city.example.joinedcontext.com/git/city-org/city-config`).
5. Run the initial reconciliation via CLI or trigger via the Portal UI:

   ```bash
   kubectl exec -n prod deploy/jcctl -- jcctl apply --repo-dir /var/git/city-config
   ```

## 7. Air-Gapped Installation (OPS-19…OPS-21)

An air-gapped installation runs the six steps above unchanged. Only the source of the images and charts differs: they arrive on the media you carried in, from a registry inside the zone, and nothing during install or run reaches the Internet (OPS-19, OPS-21).

### On a connected machine

```bash
scripts/package-airgap.sh --out /media/transfer
```

The script reads every `components/*/images.yaml` and `components/*/charts.yaml` in this repository, which is where each image digest and each upstream chart version is already pinned. It pulls each image by digest and each chart by version, then writes one archive:

```text
joinedcontext-airgap-<date>.tar.gz
├── manifest.yaml        # every image and chart in the archive, with the digest each was pulled at
├── images/              # one OCI layout per image, named by its digest
└── charts/              # one .tgz per upstream chart, at its pinned version
```

The archive is complete by construction: an image or chart the deployment can ask for is one this repository pins, and a pin the script cannot resolve fails the run rather than producing a short archive.

### Inside the zone

```bash
scripts/load-airgap.sh --archive joinedcontext-airgap-<date>.tar.gz \
                       --registry registry.internal:5000
```

Every image is pushed to the internal registry under the same digest it was packaged with, so the digest in `images.yaml` still identifies the same bytes and signature verification still applies (OPS-20). Charts are unpacked to a local directory that helmfile reads instead of the upstream repositories.

The loader also writes `airgap-images.yaml.gotmpl` beside the charts, an ordinary values file that repoints every `images.<component>.<part>.repository` at the internal registry and keeps each digest. Copy it into `deployment/environments/<env>/` and the six installation steps proceed as written.

The loader talks to the internal registry and the local filesystem, and resolves no other host: no fallback to a public registry, no chart repository to add, no update check (OPS-21).

## Related

- [00-intro](00-intro.md) — deployment chapter order.
- [01-runbooks](../Operations/01-runbooks.md) — what to do when it breaks.
- [13-security](../Architecture/13-security.md) — the security model being deployed.
