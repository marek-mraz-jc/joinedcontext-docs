---
sidebar_position: 3
title: "Installation Guide"
---

# Installation Guide

Install the platform on a prepared cluster ([01-prerequisites.md](01-prerequisites.md)), and know it worked. Copying `defaults/deployment` gives three entrypoints, and an installation uses either the first or the other two:

1. **All in one pass** (`deployment/helmfile.yaml`): every component, operators included, into one namespace. This is what one cluster needs and what the reference cluster runs.
2. **Shared operators** (`deployment/helmfile-operators.yaml`): once per cluster. It renders the operator halves of `prepare`, `postgres`, `runtime-policies` and `networkpolicies` (the CloudNativePG operator and the cluster-scoped Kyverno policies) and sets them to watch every namespace, so one operator serves every instance on the cluster. The operator namespace is `global.operators.namespace`, `jc-operators` when unset.
3. **One instance** (`deployment/helmfile-instance.yaml.gotmpl`): everything except those operator halves, once per instance. Each instance lives in the namespace named by its `global.instanceSlug`.

Steps 3 and 5 below are the second path. For a single cluster, run `helmfile -f deployment/helmfile.yaml -e <env> sync` once instead and skip step 3.

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
  - pipeline-runner
```

`components` overrides the shipped list in `defaults/environment/global.yaml`, which is longer and ordered for a reason: the forge comes after Keycloak and the edge because its init registers its OIDC login against `idm.<domain>`, and the two components that read a token it mints come after it. Add to the shipped list rather than retyping it, and keep its order. There is no `jcctl` component: the reconciler is part of the Portal ([00-intro.md](00-intro.md) §1).

## 3. Step 3: Deploy Shared Operators

Install the operators once per cluster. They land in `global.operators.namespace`, which defaults to `jc-operators`:

```bash
helmfile -f deployment/helmfile-operators.yaml -e production sync
```

Verify that operator CRDs (`clusters.postgresql.cnpg.io`, `clusterpolicies.kyverno.io`) are registered:

```bash
kubectl get crd | grep -E 'cnpg|kyverno'
```

## 4. Step 4: Secrets The Platform Does Not Generate

The `secrets` component generates every password the platform itself owns, so there is nothing to pre-create for a plain installation. Two kinds of secret are yours because the platform cannot invent them:

- **Mail**: Keycloak's SMTP is off by default (`keycloak.app.smtp.enabled: false`). Turn it on and a Secret named by `keycloak.app.smtp.existingSecret`, `keycloak-smtp` by default, must exist in Keycloak's namespace with the keys `host`, `port`, `from`, `user` and `password`. It is a real mail account, so it is never generated.
- **Object storage for backups**: the credentials the CloudNativePG Barman store uses ([07-backup-restore.md](07-backup-restore.md)).

Declare both through the `secrets` component and SOPS rather than typing them into a shell, so the value is encrypted in the repository and never in a shell history or a process list. `components/secrets/README.md` has the round trip, and `SOPS_AGE_KEY_FILE` has to be in the environment of whoever runs `helmfile`:

```yaml title="deployment/environments/production/secrets.yaml.gotmpl"
managedSecrets:
  - keycloak:
      app:
        keycloak-smtp:
          password: ref+sops://environments/production/secrets.enc.yaml#/smtp/password
          componentNamespaces: [keycloak]
```

## 5. Step 5: Sync Instance Deployment

Execute the instance release pipeline:

```bash
helmfile -f deployment/helmfile-instance.yaml.gotmpl -e production sync
```

Wait for every rollout, then check the installation answers:

```bash
./scripts/wait-rollouts.sh prod
./scripts/smoke.sh "https://city.example.joinedcontext.com" "https://idm.city.example.joinedcontext.com"
```

`wait-rollouts.sh` returns when every Deployment and StatefulSet of the namespace is available; `smoke.sh` asks the edge, the Portal, the gateway and Keycloak for the responses a working installation gives. A non-zero exit names what answered wrongly, which is where [09-troubleshooting.md](09-troubleshooting.md) starts.

## 6. Step 6: First Login

The configuration repository already exists at this point: the forge's bootstrap Job creates the organization and the repository named by `global.configRepo` (`joinedcontext/configuration` unless overridden), creates every team the group map can place a person in, and mints the tokens the Portal and the gateway read. Nothing asks an operator to connect the two.

1. Read the generated credentials. Both Secrets are in the namespace of the component that owns them, which is the instance namespace under the shipped `singleNamespace: true`:

   ```bash
   kubectl get secret -n prod keycloak-admin-user -o jsonpath='{.data.password}' | base64 -d && echo
   kubectl get secret -n prod gitea-admin-credentials -o jsonpath='{.data.password}' | base64 -d && echo
   ```

2. The Keycloak administrator signs in at `https://idm.city.example.joinedcontext.com/admin/master/console`. The installation's own realm is named after `global.instanceSlug`, `prod` here, and is selected in that console.
3. Open `https://portal.city.example.joinedcontext.com` and sign in through Keycloak as `global.initialUserEmail`. Login happens at the edge, so the Portal is reached through its own host and not by port-forward ([ADR-N-019](../Decisions/adr-n-019-login-at-the-edge-apisix-openid-connect.md)).
4. Nothing needs to be reconciled by hand. The Portal's reconciler reads the configuration repository on its own tick and applies what it declares; `jcctl apply --repo-dir <path>` does the same from a checkout, for a person who wants to see a plan first (`jcctl plan --repo-dir <path>`). There is no reconciler pod to exec into.

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
                       --registry registry.internal:5000 \
                       [--charts-dir deployment/airgap-charts] [--tls-verify=false]
```

Every image is pushed to the internal registry under the same digest it was packaged with, so the digest in `images.yaml` still identifies the same bytes and signature verification still applies (OPS-20). Charts are unpacked into `--charts-dir`, `deployment/airgap-charts` by default, which helmfile reads instead of the upstream repositories.

Then point the deployment at that registry. `defaults/environment/images.yaml.gotmpl` assembles every `components/*/images.yaml` into `.Values.images`, and an environment's own `images.yaml.gotmpl` merges over it, so an air-gapped environment carries one:

```yaml title="deployment/environments/production/images.yaml.gotmpl"
images:
  portal:
    portal:
      repository: registry.internal:5000/marek-mraz-jc/joinedcontext-portal
```

One entry per `images.<component>.<release>.repository`, each keeping its digest: the registry host is the only thing that changes, which is what keeps signature verification working. `load-airgap.sh` prints `global.imageRegistry` as the knob to set, and no chart, template or values file reads that key, so overriding the repositories is what works today.

The loader talks to the internal registry and the local filesystem, and resolves no other host: no fallback to a public registry, no chart repository to add, no update check (OPS-21). Its test asserts that by recording every destination the script names.

## Related

- [01-prerequisites](01-prerequisites.md) — what the cluster must provide before step 1.
- [03-configuration](03-configuration.md) — every value the environment file in step 2 can carry.
- [09-troubleshooting](09-troubleshooting.md) — where a failed `smoke.sh` is diagnosed.
- [07-backup-restore](07-backup-restore.md) — the object-store credentials step 4 names.
- [01-runbooks](../Operations/01-runbooks.md) — the procedures for running it afterwards.
- [13-security](../Architecture/13-security.md) — the security model this installation enforces.
