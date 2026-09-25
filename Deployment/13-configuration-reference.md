---
sidebar_position: 13
title: "Configuration Reference"
description: Every environment variable the platform's services read, with its default and whether it holds a secret, generated from the code that reads it.
---

# Configuration Reference

Every environment variable the platform's services read, generated from the code that
reads it by `scripts/generate-config-reference.py` (OPS-27). Do not edit this page by
hand: a change belongs in the rustdoc of the field that reads the variable, and CI
fails when a variable is read and not here, or here and read by nothing.

A variable with no default is one the service cannot invent. Where the service can run
without it, the sentence says what it does instead — usually refusing the routes that
need it, never falling back to something weaker. A variable marked as a secret is
resolved from a `secretRef` by the deployment and is never written into a manifest, an
image, a log or a task; one marked *a path to one* names a file the value is mounted
into, which is how a credential reaches a pod without passing through its environment.

## 1. Context Gateway

The enforcement point in front of every broker surface (`context-gateway`).

| Variable | Default | Secret | What it is |
|---|---|---|---|
| `JC_ENVIRONMENT` | — | no | The overlay `JC_ENVIRONMENT` names, as `validate` and `plan` read it (CC-73). |
| `JC_GATEWAY_ASSEMBLY_DIR` | `/tmp/jc-assembly` | no | Where a layout 2 organization is assembled (`JC_GATEWAY_ASSEMBLY_DIR`, default `/tmp/jc-assembly`), a scratch directory the pod owns. |
| `JC_GATEWAY_BIND` | `0.0.0.0:8080` | no | The address to listen on (`JC_GATEWAY_BIND`, default `0.0.0.0:8080`). |
| `JC_GATEWAY_BROKER_URL` | — | no | The broker to forward to, scheme and authority only (`JC_GATEWAY_BROKER_URL`). |
| `JC_GATEWAY_DELIVERY_KEY` | — | yes | The key a subscription's subscriber is sealed with (`JC_GATEWAY_DELIVERY_KEY`, a secret of at least 32 bytes), so each delivery is decided again against the policies in force (GW27, T-2383); unset refuses every subscription that routes a delivery with `501`. |
| `JC_GATEWAY_DOMAIN_VERIFICATION` | `report` | no | `report` or `enforce` (`JC_GATEWAY_DOMAIN_VERIFICATION`, default `report`): whether a write waits for the Organization's verified domain (PF-41, Architecture/03 §3). |
| `JC_GATEWAY_DOMAIN_VERIFICATIONS_URL` | — | no | The Portal's list of domain states (`JC_GATEWAY_DOMAIN_VERIFICATIONS_URL`, its internal listener's `/internal/domain-verifications`); required under `enforce`. |
| `JC_GATEWAY_EGRESS_CA_BUNDLE` | — | no | A PEM file of extra trust anchors the notification egress trusts on top of the public roots (`JC_GATEWAY_EGRESS_CA_BUNDLE`), for subscribers behind the installation's own CA (R46). |
| `JC_GATEWAY_EGRESS_PRIVATE_HOSTS` | — | no | Hosts inside the platform's own networks a notification may still be delivered to (`JC_GATEWAY_EGRESS_PRIVATE_HOSTS`, comma-separated); empty refuses them all (T-1302). |
| `JC_GATEWAY_EGRESS_URL` | — | no | The base a rewritten `notification.endpoint.uri` carries (`JC_GATEWAY_EGRESS_URL`), which is the address the broker dials to deliver; the public URL when the deployment names none. |
| `JC_GATEWAY_ORG_DOMAIN` | — | no | The organization's verified domain, the middle segment of every entity URN (`JC_GATEWAY_ORG_DOMAIN`). |
| `JC_GATEWAY_PREVIEWS_DIR` | `/tmp/jc-previews` | no | Where the previews are written (`JC_GATEWAY_PREVIEWS_DIR`, default `/tmp/jc-previews`), a scratch directory the pod owns. |
| `JC_GATEWAY_PREVIEWS_URL` | — | no | The Portal's list of running workspace previews (`JC_GATEWAY_PREVIEWS_URL`, its internal listener's `/internal/previews`); absent serves `main` alone (CC-78). |
| `JC_GATEWAY_PROJECTS_DIR` | — | no | The project checkouts of a layout 2 organization, one directory per registry slug at its pinned ref (`JC_GATEWAY_PROJECTS_DIR`); a layout 1 repository needs none (CC-86). |
| `JC_GATEWAY_PUBLIC_URL` | — | no | The gateway's own public base URL (`JC_GATEWAY_PUBLIC_URL`), which makes the full RFC 8707 resource URI an acceptable token audience alongside the endpoint slug. |
| `JC_GATEWAY_REPO_DIR` | — | no | The manifest repository the endpoint table is built from (`JC_GATEWAY_REPO_DIR`); absent means an empty table until one is loaded. |
| `JC_OIDC_CLIENT_ID` | — | no | The gateway's own Keycloak client and its secret (`JC_OIDC_CLIENT_ID`, `JC_OIDC_CLIENT_SECRET`): the identity it presents when it calls the Portal's internal listener (PF-46, AG-52). |
| `JC_OIDC_CLIENT_SECRET` | — | yes | The gateway's own Keycloak client and its secret (`JC_OIDC_CLIENT_ID`, `JC_OIDC_CLIENT_SECRET`): the identity it presents when it calls the Portal's internal listener (PF-46, AG-52). |
| `JC_OIDC_ISSUER` | — | no | The realm every token must be issued by (`JC_OIDC_ISSUER`); absent means the gateway serves public endpoints only and refuses every presented token. |
| `JC_OIDC_JWKS_URL` | — | no | The realm's JWKS, fetched in the background (`JC_OIDC_JWKS_URL`). |
| `JC_OIDC_TOKEN_URL` | — | no | Where the gateway asks for its own token (`JC_OIDC_TOKEN_URL`), for the same reason `JC_OIDC_JWKS_URL` exists: the issuer is the address a *browser* uses, and a pod that dials its own cluster's public hostname leaves through the ingress or not at all. |

## 2. Portal

The management application: the API, the embedded UI and the in-process reconciler.

| Variable | Default | Secret | What it is |
|---|---|---|---|
| `JC_AGENTS_NAMESPACE` | — | no | `JC_AGENTS_NAMESPACE` and `JC_AGENT_PROXY_BASE` are set together or not at all; `JC_PORTAL_NAMESPACE` (default: the workspaces' own namespace), `JC_INTERNAL_BIND` (default `0.0.0.0:9090`), `JC_AGENT_RUN_TTL` (whole seconds, default `1200`) and `JC_AGENT_APPROVAL_TTL` (whole seconds a run waits for its change's approval, default `604800`) tune the rest. |
| `JC_AGENT_APPROVAL_TTL` | — | no | How long a run that built an application waits for its change's approval, in seconds (`JC_AGENT_APPROVAL_TTL`, T-2772): the run's own wall clock stops when it proposes, and an approver has days, not what was left of the build's twenty minutes. |
| `JC_AGENT_PROXY_BASE` | — | no | `JC_AGENTS_NAMESPACE` and `JC_AGENT_PROXY_BASE` are set together or not at all; `JC_PORTAL_NAMESPACE` (default: the workspaces' own namespace), `JC_INTERNAL_BIND` (default `0.0.0.0:9090`), `JC_AGENT_RUN_TTL` (whole seconds, default `1200`) and `JC_AGENT_APPROVAL_TTL` (whole seconds a run waits for its change's approval, default `604800`) tune the rest. |
| `JC_AGENT_RUN_TTL` | `1200` | no | `JC_AGENTS_NAMESPACE` and `JC_AGENT_PROXY_BASE` are set together or not at all; `JC_PORTAL_NAMESPACE` (default: the workspaces' own namespace), `JC_INTERNAL_BIND` (default `0.0.0.0:9090`), `JC_AGENT_RUN_TTL` (whole seconds, default `1200`) and `JC_AGENT_APPROVAL_TTL` (whole seconds a run waits for its change's approval, default `604800`) tune the rest. |
| `JC_APP_MIRROR_GITHUB_API` | — | no | `JC_APP_MIRROR_GITHUB_API` and `JC_APP_MIRROR_GITHUB_URL` name a GitHub Enterprise server; github.com when unset. |
| `JC_APP_MIRROR_GITHUB_OWNER` | — | no | `JC_APP_MIRROR_GITHUB_OWNER` (the organization or user the copies are created under) and `JC_APP_MIRROR_GITHUB_TOKEN` (a secret: creates the repositories and is the push mirror's credential) are set together or not at all. |
| `JC_APP_MIRROR_GITHUB_TOKEN` | — | yes | `JC_APP_MIRROR_GITHUB_OWNER` (the organization or user the copies are created under) and `JC_APP_MIRROR_GITHUB_TOKEN` (a secret: creates the repositories and is the push mirror's credential) are set together or not at all. |
| `JC_APP_MIRROR_GITHUB_URL` | — | no | `JC_APP_MIRROR_GITHUB_API` and `JC_APP_MIRROR_GITHUB_URL` name a GitHub Enterprise server; github.com when unset. |
| `JC_BASEMAP_ATTRIBUTION` | — | no | `JC_BASEMAP_URL` (an `https` template holding `{z}`, `{x}` and `{y}`) turns the proxy on and `JC_BASEMAP_ATTRIBUTION` is then required, because a tile source that is served without its attribution is served against its licence. |
| `JC_BASEMAP_CACHE_DIR` | `/tmp/basemap-cache` | no | `JC_BASEMAP_MAX_ZOOM` (default `19`), `JC_BASEMAP_CACHE_DIR` (default `/tmp/basemap-cache`), `JC_BASEMAP_CACHE_MAX_BYTES` (default `268435456`) and `JC_BASEMAP_CACHE_TTL_SECS` (default `604800`) tune the cache. |
| `JC_BASEMAP_CACHE_MAX_BYTES` | `268435456` | no | `JC_BASEMAP_MAX_ZOOM` (default `19`), `JC_BASEMAP_CACHE_DIR` (default `/tmp/basemap-cache`), `JC_BASEMAP_CACHE_MAX_BYTES` (default `268435456`) and `JC_BASEMAP_CACHE_TTL_SECS` (default `604800`) tune the cache. |
| `JC_BASEMAP_CACHE_TTL_SECS` | `604800` | no | `JC_BASEMAP_MAX_ZOOM` (default `19`), `JC_BASEMAP_CACHE_DIR` (default `/tmp/basemap-cache`), `JC_BASEMAP_CACHE_MAX_BYTES` (default `268435456`) and `JC_BASEMAP_CACHE_TTL_SECS` (default `604800`) tune the cache. |
| `JC_BASEMAP_KEY_FILE` | — | a path to one | `JC_BASEMAP_KEY_FILE` names a file holding the tile provider's key — a path to a secret, and the reason the browser fetches tiles from the Portal rather than from the provider. |
| `JC_BASEMAP_MAX_ZOOM` | `19` | no | `JC_BASEMAP_MAX_ZOOM` (default `19`), `JC_BASEMAP_CACHE_DIR` (default `/tmp/basemap-cache`), `JC_BASEMAP_CACHE_MAX_BYTES` (default `268435456`) and `JC_BASEMAP_CACHE_TTL_SECS` (default `604800`) tune the cache. |
| `JC_BASEMAP_URL` | — | no | `JC_BASEMAP_URL` (an `https` template holding `{z}`, `{x}` and `{y}`) turns the proxy on and `JC_BASEMAP_ATTRIBUTION` is then required, because a tile source that is served without its attribution is served against its licence. |
| `JC_BRANDING_FILE` | — | no | The file the deployment renders `global.branding` into (`JC_BRANDING_FILE`; UI-30, OPS-46). |
| `JC_ENVIRONMENT` | — | no | `JC_ENVIRONMENT` names the overlay the branch is rendered with, the same one the reconciler applies for this installation (CC-73); unset renders the manifests as they are written. |
| `JC_FUNCTIONS_URL` | — | no | Base URL of the `jc-functions` runtime (`JC_FUNCTIONS_URL`), e.g. `http://jc-functions.jc-system.svc.cluster.local:8080`. |
| `JC_GITEA_OWNER` | — | no | `JC_GITEA_URL` (the API base the Portal dials), `JC_GITEA_OWNER`, `JC_GITEA_REPO` and `JC_GITEA_TOKEN` (a secret: the token every push and merge request is written with). |
| `JC_GITEA_PUBLIC_URL` | — | no | `JC_GITEA_PUBLIC_URL`; the API base when unset. |
| `JC_GITEA_REPO` | — | no | `JC_GITEA_URL` (the API base the Portal dials), `JC_GITEA_OWNER`, `JC_GITEA_REPO` and `JC_GITEA_TOKEN` (a secret: the token every push and merge request is written with). |
| `JC_GITEA_TOKEN` | — | yes | `JC_GITEA_URL` (the API base the Portal dials), `JC_GITEA_OWNER`, `JC_GITEA_REPO` and `JC_GITEA_TOKEN` (a secret: the token every push and merge request is written with). |
| `JC_GITEA_URL` | — | no | `JC_GITEA_URL` (the API base the Portal dials), `JC_GITEA_OWNER`, `JC_GITEA_REPO` and `JC_GITEA_TOKEN` (a secret: the token every push and merge request is written with). |
| `JC_GITEA_WEBHOOK_SECRET` | — | yes | The secret the forge signs its webhook calls with (`JC_GITEA_WEBHOOK_SECRET`). |
| `JC_GITEA_WEBHOOK_SECRET_PREVIOUS` | — | yes | The secret this Portal accepted before the current one, during a rotation (`JC_GITEA_WEBHOOK_SECRET_PREVIOUS`). |
| `JC_INTERNAL_BIND` | `0.0.0.0:9090` | no | `JC_AGENTS_NAMESPACE` and `JC_AGENT_PROXY_BASE` are set together or not at all; `JC_PORTAL_NAMESPACE` (default: the workspaces' own namespace), `JC_INTERNAL_BIND` (default `0.0.0.0:9090`), `JC_AGENT_RUN_TTL` (whole seconds, default `1200`) and `JC_AGENT_APPROVAL_TTL` (whole seconds a run waits for its change's approval, default `604800`) tune the rest. |
| `JC_OIDC_CA_FILE` | — | no | The realm humans sign in against: `JC_OIDC_ISSUER`, `JC_OIDC_CLIENT_ID` and `JC_OIDC_CLIENT_SECRET` (a secret), all three together or none, plus the optional `JC_OIDC_CA_FILE` for a realm behind a private CA. |
| `JC_OIDC_CLIENT_ID` | — | no | The realm humans sign in against: `JC_OIDC_ISSUER`, `JC_OIDC_CLIENT_ID` and `JC_OIDC_CLIENT_SECRET` (a secret), all three together or none, plus the optional `JC_OIDC_CA_FILE` for a realm behind a private CA. |
| `JC_OIDC_CLIENT_SECRET` | — | yes | The realm humans sign in against: `JC_OIDC_ISSUER`, `JC_OIDC_CLIENT_ID` and `JC_OIDC_CLIENT_SECRET` (a secret), all three together or none, plus the optional `JC_OIDC_CA_FILE` for a realm behind a private CA. |
| `JC_OIDC_ISSUER` | — | no | The realm humans sign in against: `JC_OIDC_ISSUER`, `JC_OIDC_CLIENT_ID` and `JC_OIDC_CLIENT_SECRET` (a secret), all three together or none, plus the optional `JC_OIDC_CA_FILE` for a realm behind a private CA. |
| `JC_PORTAL_AGENT_PROXY_CLIENT_ID` | — | no | The Keycloak client `jc-agent-proxy` holds (`JC_PORTAL_AGENT_PROXY_CLIENT_ID`), which is the only caller the run callbacks on the internal listener answer (AG-52, T-2271). |
| `JC_PORTAL_APISIX_NAMESPACE` | `apisix` | no | `JC_PORTAL_APISIX_NAMESPACE` — the namespace the installation runs APISIX in, the only one whose pods reach an app pod; default `apisix`. |
| `JC_PORTAL_APPS_CACHE_DIR` | — | no | Where this replica keeps the builds it fetched from the package registry, one `{name}/{hex}` directory per build (`JC_PORTAL_APPS_CACHE_DIR`, AP-102); it must be writable, and `{apps_dir}` need not be. |
| `JC_PORTAL_APPS_DIR` | — | no | Root of the built app bundles, one directory per app (`JC_PORTAL_APPS_DIR`). |
| `JC_PORTAL_APPS_NAMESPACE` | — | no | Where an App's four Kubernetes objects are applied (`JC_PORTAL_APPS_NAMESPACE` with `JC_PORTAL_ORG_DOMAIN`; AP-13, AP-18, T-0411). |
| `JC_PORTAL_APPS_PULL_SECRET_NAME` | — | no | `JC_PORTAL_APPS_PULL_SECRET_NAME` — the name of the `dockerconfigjson` Secret in the apps namespace a node pulls app images with (a forge token that reads packages only). |
| `JC_PORTAL_APPS_REGISTRY` | — | no | `JC_PORTAL_APPS_REGISTRY` — the host, and port if any, of the forge's container registry; an App's image is composed as `{registry}/{forge organization}/app-{name}@{digest}`. |
| `JC_PORTAL_APPS_URL` | — | no | `JC_PORTAL_APPS_URL`: an absolute `http(s)` origin with nothing after it. |
| `JC_PORTAL_APP_TESTS_IMAGE` | — | no | The run's test sandbox (SDK-38): `JC_PORTAL_APP_TESTS_NAMESPACE`, a Kubernetes name, and `JC_PORTAL_APP_TESTS_IMAGE`, an image reference pinned by `@sha256:` digest, both or neither. |
| `JC_PORTAL_APP_TESTS_NAMESPACE` | — | no | The run's test sandbox (SDK-38): `JC_PORTAL_APP_TESTS_NAMESPACE`, a Kubernetes name, and `JC_PORTAL_APP_TESTS_IMAGE`, an image reference pinned by `@sha256:` digest, both or neither. |
| `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` | — | yes | `JC_PORTAL_ARTIFACT_STORE_ENDPOINT`, `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` and `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` (the last two secrets) name the store and the root credential; `JC_PORTAL_ARTIFACT_STORE_BUCKET` (default `jc-artifacts`) and `JC_PORTAL_ARTIFACT_STORE_REGION` (default `us-east-1`) are the same in every installation this platform deploys, so they have defaults. |
| `JC_PORTAL_ARTIFACT_STORE_BUCKET` | `jc-artifacts` | no | `JC_PORTAL_ARTIFACT_STORE_ENDPOINT`, `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` and `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` (the last two secrets) name the store and the root credential; `JC_PORTAL_ARTIFACT_STORE_BUCKET` (default `jc-artifacts`) and `JC_PORTAL_ARTIFACT_STORE_REGION` (default `us-east-1`) are the same in every installation this platform deploys, so they have defaults. |
| `JC_PORTAL_ARTIFACT_STORE_ENDPOINT` | — | no | `JC_PORTAL_ARTIFACT_STORE_ENDPOINT`, `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` and `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` (the last two secrets) name the store and the root credential; `JC_PORTAL_ARTIFACT_STORE_BUCKET` (default `jc-artifacts`) and `JC_PORTAL_ARTIFACT_STORE_REGION` (default `us-east-1`) are the same in every installation this platform deploys, so they have defaults. |
| `JC_PORTAL_ARTIFACT_STORE_REGION` | `us-east-1` | no | `JC_PORTAL_ARTIFACT_STORE_ENDPOINT`, `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` and `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` (the last two secrets) name the store and the root credential; `JC_PORTAL_ARTIFACT_STORE_BUCKET` (default `jc-artifacts`) and `JC_PORTAL_ARTIFACT_STORE_REGION` (default `us-east-1`) are the same in every installation this platform deploys, so they have defaults. |
| `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` | — | yes | `JC_PORTAL_ARTIFACT_STORE_ENDPOINT`, `JC_PORTAL_ARTIFACT_STORE_ACCESS_KEY` and `JC_PORTAL_ARTIFACT_STORE_SECRET_KEY` (the last two secrets) name the store and the root credential; `JC_PORTAL_ARTIFACT_STORE_BUCKET` (default `jc-artifacts`) and `JC_PORTAL_ARTIFACT_STORE_REGION` (default `us-east-1`) are the same in every installation this platform deploys, so they have defaults. |
| `JC_PORTAL_BIND` | `0.0.0.0:8080` | no | The address to listen on (`JC_PORTAL_BIND`, default `0.0.0.0:8080`). |
| `JC_PORTAL_BOOTSTRAP_ADMINS` | `portal-approver` | no | The group (or realm role) whose members may do everything everywhere, so the first `RoleBinding` can be written into an empty repository (`JC_PORTAL_BOOTSTRAP_ADMINS`, default `portal-approver`; T-0526, PF-50). |
| `JC_PORTAL_BROKER_URL` | — | no | It is also the address the registration tells the broker to read a member at, because a hub reads a member's tenant on the same broker (PF-48; `JC_PORTAL_BROKER_URL`). |
| `JC_PORTAL_BUILD_CACHE_SIZE` | `1Gi` | no | Where an App's build pods run and on which runner images (`JC_PORTAL_BUILD_NAMESPACE` with `JC_PORTAL_BUILD_IMAGE_NODE`, `JC_PORTAL_BUILD_IMAGE_RUST` and the forge's API base; `JC_PORTAL_BUILD_CACHE_SIZE`, default `1Gi`; AP-130, AP-131). |
| `JC_PORTAL_BUILD_IMAGE_NODE` | — | no | Where an App's build pods run and on which runner images (`JC_PORTAL_BUILD_NAMESPACE` with `JC_PORTAL_BUILD_IMAGE_NODE`, `JC_PORTAL_BUILD_IMAGE_RUST` and the forge's API base; `JC_PORTAL_BUILD_CACHE_SIZE`, default `1Gi`; AP-130, AP-131). |
| `JC_PORTAL_BUILD_IMAGE_RUST` | — | no | Where an App's build pods run and on which runner images (`JC_PORTAL_BUILD_NAMESPACE` with `JC_PORTAL_BUILD_IMAGE_NODE`, `JC_PORTAL_BUILD_IMAGE_RUST` and the forge's API base; `JC_PORTAL_BUILD_CACHE_SIZE`, default `1Gi`; AP-130, AP-131). |
| `JC_PORTAL_BUILD_NAMESPACE` | — | no | Where build pods run (AP-130): nothing when `JC_PORTAL_BUILD_NAMESPACE` is unset, and every other part required once it is, because a namespace with no image would start pods that never run. |
| `JC_PORTAL_COOKIE_KEY` | — | yes | The key every session cookie is sealed with (`JC_PORTAL_COOKIE_KEY`, at least 64 bytes). |
| `JC_PORTAL_COOKIE_KEY_PREVIOUS` | — | yes | Keys a session cookie may still be sealed with, during a rotation (`JC_PORTAL_COOKIE_KEY_PREVIOUS`, comma-separated, each held to the same length as the active one; T-0973). |
| `JC_PORTAL_DATABASE_URL` | — | yes | PostgreSQL connection string of the preferences tier (`JC_PORTAL_DATABASE_URL`, UI-09). |
| `JC_PORTAL_GATEWAY_CLIENT_ID` | — | no | The Keycloak client the Context Gateway holds (`JC_PORTAL_GATEWAY_CLIENT_ID`), which is the only caller `GET /internal/previews` answers (PF-46, AG-52). |
| `JC_PORTAL_GATEWAY_URL` | — | no | The platform host the context spaces are served on, which is where a declared `Subscription` is written (`JC_PORTAL_GATEWAY_URL`, `/cs/{space}/ngsi-ld/v1/subscriptions`, T-0931). |
| `JC_PORTAL_JOURNEY_USERS` | — | no | The usernames the Portal's own live journeys sign in as, the only people whose runs may carry `X-JC-Run-Origin: journey` (`JC_PORTAL_JOURNEY_USERS`, comma-separated; default none, so no one can mark a run; AG-93, T-2816). |
| `JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_ID` | — | no | The client the reconciler manages the realm's groups with: a `ServiceAccount` client holding `manage-users` and `query-groups` of `realm-management` and nothing else (`JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_ID` and `JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_SECRET`, a secret, both together or neither; PF-63). |
| `JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_SECRET` | — | yes | The client the reconciler manages the realm's groups with: a `ServiceAccount` client holding `manage-users` and `query-groups` of `realm-management` and nothing else (`JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_ID` and `JC_PORTAL_KEYCLOAK_ADMIN_CLIENT_SECRET`, a secret, both together or neither; PF-63). |
| `JC_PORTAL_MODEL_TOOLS_URL` | — | no | Base URL of the stateless Model Tools service (`JC_PORTAL_MODEL_TOOLS_URL`), e.g. `http://model-tools.tools.svc.cluster.local:8080`. |
| `JC_PORTAL_NAMESPACE` | — | no | `JC_AGENTS_NAMESPACE` and `JC_AGENT_PROXY_BASE` are set together or not at all; `JC_PORTAL_NAMESPACE` (default: the workspaces' own namespace), `JC_INTERNAL_BIND` (default `0.0.0.0:9090`), `JC_AGENT_RUN_TTL` (whole seconds, default `1200`) and `JC_AGENT_APPROVAL_TTL` (whole seconds a run waits for its change's approval, default `604800`) tune the rest. |
| `JC_PORTAL_OPENBAO_ADDR` | — | no | `JC_PORTAL_SOPS_AGE_KEY_FILE` names the age key file and chooses SOPS; otherwise `JC_PORTAL_OPENBAO_ADDR` and `JC_PORTAL_OPENBAO_ROLE` choose OpenBao, with `JC_PORTAL_OPENBAO_JWT_PATH` (default `/var/run/secrets/kubernetes.io/serviceaccount/token`) for the ServiceAccount token it logs in with. |
| `JC_PORTAL_OPENBAO_JWT_PATH` | `/var/run/secrets/kubernetes.io/serviceaccount/token` | no | `JC_PORTAL_SOPS_AGE_KEY_FILE` names the age key file and chooses SOPS; otherwise `JC_PORTAL_OPENBAO_ADDR` and `JC_PORTAL_OPENBAO_ROLE` choose OpenBao, with `JC_PORTAL_OPENBAO_JWT_PATH` (default `/var/run/secrets/kubernetes.io/serviceaccount/token`) for the ServiceAccount token it logs in with. |
| `JC_PORTAL_OPENBAO_ROLE` | — | no | `JC_PORTAL_SOPS_AGE_KEY_FILE` names the age key file and chooses SOPS; otherwise `JC_PORTAL_OPENBAO_ADDR` and `JC_PORTAL_OPENBAO_ROLE` choose OpenBao, with `JC_PORTAL_OPENBAO_JWT_PATH` (default `/var/run/secrets/kubernetes.io/serviceaccount/token`) for the ServiceAccount token it logs in with. |
| `JC_PORTAL_ORG_DOMAIN` | — | no | The organization's domain, the third segment of every URN this instance writes (`JC_PORTAL_ORG_DOMAIN`; `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`). |
| `JC_PORTAL_PIPELINE_RUNNER_CLIENT_ID` | — | no | The Keycloak client the project's pipeline runner holds (`JC_PORTAL_PIPELINE_RUNNER_CLIENT_ID`), which is the only caller `POST /internal/pipeline-tests/{id}` answers (AG-52, T-2271). |
| `JC_PORTAL_PIPELINE_RUNNER_URL` | — | no | Base URL of a project's Bento pipeline runner with `{project}` still in it, e.g. `http://pipeline-runner.{project}-pipeline-runner.svc.cluster.local:4195` (`JC_PORTAL_PIPELINE_RUNNER_URL`). |
| `JC_PORTAL_PIPELINE_TEST_CAPTURE_URL` | — | no | Where a pipeline test's harness posts what it produced (PL-43): the Portal's internal listener as the project's runner reaches it, e.g. `http://portal-internal:9090` (`JC_PORTAL_PIPELINE_TEST_CAPTURE_URL`). |
| `JC_PORTAL_PUBLIC_URL` | `http://localhost:8080` | no | The address a browser reaches this Portal at (`JC_PORTAL_PUBLIC_URL`, default `http://localhost:8080`). |
| `JC_PORTAL_RELEASE` | — | no | `JC_PORTAL_RELEASE` — the installation's release name; a project's pod-backed Apps run in `{release}-{project}-apps`, bound to the ClusterRole `{release}-portal-apps` (AP-116). |
| `JC_PORTAL_SERVICE_ACCOUNT` | — | no | `JC_PORTAL_SERVICE_ACCOUNT` — the Portal's ServiceAccount in `JC_PORTAL_APPS_NAMESPACE`, the subject of the RoleBinding in each project's apps namespace (AP-116). |
| `JC_PORTAL_SOPS_AGE_KEY_FILE` | — | a path to one | `JC_PORTAL_SOPS_AGE_KEY_FILE` names the age key file and chooses SOPS; otherwise `JC_PORTAL_OPENBAO_ADDR` and `JC_PORTAL_OPENBAO_ROLE` choose OpenBao, with `JC_PORTAL_OPENBAO_JWT_PATH` (default `/var/run/secrets/kubernetes.io/serviceaccount/token`) for the ServiceAccount token it logs in with. |
| `JC_PORTAL_SYNC_INTERVAL` | `60` | no | How often the reconciler re-reads the configuration repository (`JC_PORTAL_SYNC_INTERVAL`, whole seconds, default `60`). |
| `JC_SETUP_BACKUPS` | — | no | The databases are backed up to an object store (`JC_SETUP_BACKUPS`, the literal `true`). |
| `JC_SETUP_LOGIN_THEME` | — | no | The realm's login theme (`JC_SETUP_LOGIN_THEME`); unset or blank says nothing about it. |
| `JC_SETUP_SMTP` | — | no | The realm sends mail (`JC_SETUP_SMTP`, the literal `true`). |
| `JC_TRUST_EDGE_TOKEN` | `false` | no | The deployment sets it behind the edge, which strips the header from every client request first; a Portal without an edge in front leaves it off and the header is ignored (`JC_TRUST_EDGE_TOKEN`, the literal string `true` to turn it on; default `false`). |

## 3. Agent proxy

The credential holder of a builder run (`jc-agent-proxy`): a workspace reaches the model, the forge and the context through it and holds none of their credentials.

| Variable | Default | Secret | What it is |
|---|---|---|---|
| `JC_FORGE_BASE` | `http://gitea-http:3000` | no | The forge as the proxy reaches it inside the cluster (`JC_FORGE_BASE`, default `http://gitea-http:3000`), where a run's branch and its merge request are written. |
| `JC_FORGE_REPO` | `joinedcontext/configuration` | no | The configuration repository a run proposes its change to (`JC_FORGE_REPO`, default `joinedcontext/configuration`), as `owner/name`. |
| `JC_FORGE_TOKEN` | — | yes | The forge token the proxy writes a run's branch with, read from the file named by `JC_FORGE_TOKEN_FILE` or from `JC_FORGE_TOKEN`. |
| `JC_FORGE_TOKEN_FILE` | — | a path to one | The forge token the proxy writes a run's branch with, read from the file named by `JC_FORGE_TOKEN_FILE` or from `JC_FORGE_TOKEN`. |
| `JC_GATEWAY_BASE` | `http://context-gateway:8080` | no | The Context Gateway as the proxy reaches it inside the cluster (`JC_GATEWAY_BASE`, default `http://context-gateway:8080`), the only address a run's context call is forwarded to. |
| `JC_MODEL_BASE` | `https://api.anthropic.com` | no | The model API the proxy forwards a run's completions to (`JC_MODEL_BASE`, default `https://api.anthropic.com`). |
| `JC_MODEL_KEY` | — | yes | The key for that API, read from the file named by `JC_MODEL_KEY_FILE` or from `JC_MODEL_KEY`. |
| `JC_MODEL_KEY_FILE` | — | a path to one | The key for that API, read from the file named by `JC_MODEL_KEY_FILE` or from `JC_MODEL_KEY`. |
| `JC_MODEL_PROVIDER` | `anthropic` | no | Which provider's protocol `model_base` speaks (`JC_MODEL_PROVIDER`, default `anthropic`). |
| `JC_OIDC_CLIENT_ID` | `agent-proxy` | no | The proxy's own Keycloak client (`JC_OIDC_CLIENT_ID`, default `agent-proxy`), whose token the Portal's internal listener accepts (AG-52). |
| `JC_OIDC_CLIENT_SECRET` | — | yes | That client's secret, read from the file named by `JC_OIDC_CLIENT_SECRET_FILE` or, when no file is named, from `JC_OIDC_CLIENT_SECRET` itself. |
| `JC_OIDC_CLIENT_SECRET_FILE` | — | a path to one | That client's secret, read from the file named by `JC_OIDC_CLIENT_SECRET_FILE` or, when no file is named, from `JC_OIDC_CLIENT_SECRET` itself. |
| `JC_OIDC_ISSUER` | `http://keycloak:8080/realms/joinedcontext` | no | The realm every token the proxy mints and verifies is issued by (`JC_OIDC_ISSUER`, default `http://keycloak:8080/realms/joinedcontext`). |
| `JC_OIDC_TOKEN_URL` | — | no | Where the realm's token endpoint is, for the same reason the gateway needs one (`JC_OIDC_TOKEN_URL`, T-2272): the issuer is the address a browser uses, and a pod cannot dial its own cluster's ingress hostname. |
| `JC_PORTAL_BASE` | `http://portal:8080` | no | The Portal as the proxy reaches it inside the cluster (`JC_PORTAL_BASE`, default `http://portal:8080`), where it reads a run's plan and posts its callbacks. |
| `JC_PROXY_BIND` | `0.0.0.0:8080` | no | The address to listen on (`JC_PROXY_BIND`, default `0.0.0.0:8080`). |
| `JC_REQUIRE_MESH_IDENTITY` | — | no | Whether a caller must arrive through the mesh with a Linkerd identity (`JC_REQUIRE_MESH_IDENTITY`, the string `true` to require it; default off). |

## 4. Functions runtime

The QuickJS runtime a generated application's functions run in (`jc-functions`).

| Variable | Default | Secret | What it is |
|---|---|---|---|
| `JC_FUNCTIONS_AUDIENCE` | `jc-functions` | no | `JC_FUNCTIONS_AUDIENCE` — the audience that token must carry, default `jc-functions`. |
| `JC_FUNCTIONS_BIND` | `0.0.0.0:8080` | no | `JC_FUNCTIONS_BIND` — the address to listen on, default `0.0.0.0:8080`. |
| `JC_FUNCTIONS_CALLER` | — | no | `JC_FUNCTIONS_CALLER` — the one client whose token may invoke a function, which is the Portal (SDK-23). Required. |
| `JC_GATEWAY_URL` | — | no | `JC_GATEWAY_URL` — the Context Gateway a function's context call is forwarded to, scheme and authority only; a path or a query is refused at startup, because the endpoint the permission is checked against and the URL that is fetched would then differ. Required. |
| `JC_OIDC_ISSUER` | — | no | `JC_OIDC_ISSUER` — the realm every presented token must be issued by. Required. |
| `JC_OIDC_JWKS_URL` | — | no | `JC_OIDC_JWKS_URL` — that realm's signing keys, fetched now and kept current in the background. It is named separately because the issuer is the address a browser uses and a pod cannot dial its own cluster's ingress hostname. Required. |

## 5. jcctl

The reconciler, as a CLI for an operator and as the library the Portal embeds.

| Variable | Default | Secret | What it is |
|---|---|---|---|
| `JC_ENVIRONMENT` | — | no | The overlay `JC_ENVIRONMENT` names, as `validate` and `plan` read it (CC-73). |
| `JC_GATEWAY_URL` | — | no | `JC_GATEWAY_URL` is the Context Gateway this run writes through, and `JC_TOKEN_FILE` the file holding the reconciler's ServiceAccount token — a path to a secret, projected by the deployment and never a value in the environment. |
| `JC_IDM` | — | no | `JC_IDM` is the identity provider's issuer when `--idm` is not given, e.g. `https://idm.<domain>/realms/<realm>`. |
| `JC_MODEL_TOOLS_URL` | — | no | Where Model Tools is, when `--url` names no address: `JC_MODEL_TOOLS_URL`. |
| `JC_SERVER` | — | no | The Portal the client verbs talk to: `--server` or `JC_SERVER`, with the token from `--token-file` or `JC_TOKEN_FILE` (API/03 §2a). |
| `JC_TOKEN_FILE` | — | a path to one | The Portal the client verbs talk to: `--server` or `JC_SERVER`, with the token from `--token-file` or `JC_TOKEN_FILE` (API/03 §2a). |

## 6. Injected into a workload

These the platform sets rather than reads: the environment a pipeline's runner and a
generated application are started with. They are a contract with whoever writes a
mapping or an application, not something an operator configures, and none of them ever
carries a credential — a run's ticket is minted per run and is not a stored secret.

| Variable | What it is |
|---|---|
| `JC_ANONYMOUS` | `JC_ANONYMOUS` — set to `true` for a public app, so its backend treats an absent `X-Access-Token` as normal rather than as a bug. |
| `JC_APP_CLASS` | `JC_APP_NAME`, `JC_APP_CLASS` — the application being built and what kind it is. |
| `JC_APP_CONFIG` | `JC_APP_CONFIG` — the `#jc-config` object the static host writes for a `ui` App, without `user`: the backend writes it into its page with `user` from `JC_ME_URL`, so the App SDK in `ui/` reads its endpoints as it does on the static host (AP-95, AP-126). |
| `JC_APP_NAME` | `JC_APP_NAME`, `JC_APP_CLASS` — the application being built and what kind it is. |
| `JC_BASE_PATH` | `JC_BASE_PATH` — the path it is served under, so every link it writes resolves. |
| `JC_BIND_ADDRESS` | `JC_BIND_ADDRESS` — where it listens, which is the port the Service routes to. |
| `JC_BRANCH` | `JC_BRANCH` — the branch the run proposes its change on. |
| `JC_ENDPOINT_URL` | `JC_ENDPOINT_URL` — the one Endpoint it may read, as a caller reaches it. |
| `JC_ME_URL` | `JC_ME_URL` — the Portal route that answers the caller's roles in this App, called with the edge's `X-Access-Token` as the bearer (AP-109). |
| `JC_ORG_DOMAIN` | `JC_ORG_DOMAIN` — the organisation's domain, a variable of the runner's process. |
| `JC_PATH_PREFIX` | `JC_PATH_PREFIX` — where the built application will be served, so the code it writes uses the right base path. |
| `JC_PROXY_BASE` | `JC_PROXY_BASE` — the credential proxy, the one address a run may call out to. |
| `JC_RUN_ID` | `JC_RUN_ID` — the run this workspace is, as the Portal records it. |
| `JC_RUN_TICKET` | `JC_RUN_TICKET` — the bearer that proves it to the proxy: minted for this run, spent with it, and worth nothing anywhere else. |
| `JC_SOURCE_SPACE` | `JC_SOURCE_SPACE` — the space an indicator pipeline records its provenance from. |
| `JC_SPACE` | `JC_SPACE`, `JC_SPACE_2`, … — the space segment of each output, which the renderer writes into the stream before it reaches the runner. |
| `JC_TEST_TIMEOUT_MS` | `JC_TEST_TIMEOUT_MS` — how many milliseconds the lane's `test-project` gives the whole test run before it reports the tests as not finished. |

## Related

- [Global & Component Configuration](03-configuration.md) — the Helm values that set
  these variables on each component.
- [Security Hardening](08-security-hardening.md) — where the secrets come from, and
  what a `secretRef` resolves to.
- [Installation](02-installation.md) — the step that sets them for the first time.
