---
sidebar_position: 2
title: "Keycloak and VCVerifier for kaisatsu"
description: Research input for kaisatsu, the Rust identity server that replaces Keycloak 26.8.1 and FIWARE VCVerifier 6.31.0; capability inventory, internals, extension model, security, tenancy, operations, test oracles, Argon pack plan and the MCP mapping, every claim with its source (T-6637).
---

# Keycloak and VCVerifier for kaisatsu

This page is the research input for kaisatsu (T-6633): one Rust identity server for every organization of an installation, replacing Keycloak and FIWARE VCVerifier. It lists what upstream does, what the platform uses today with file:line, how upstream works inside, what the Rust design keeps, changes or drops, and which upstream files feed the Argon generation. Readers: the worker who builds the kaisatsu pack, the reviewer of the generated code, the owner deciding the open questions in section 10.

## 1. Sources and pins

| Short | What | Pin |
|---|---|---|
| `KC` | github.com/keycloak/keycloak | tag `26.8.1`, commit `24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b`; deployed image `quay.io/keycloak/keycloak:26.8.1@sha256:a78d6b79…dd6b` (`DEP components/keycloak/images.yaml:12-16`) |
| `S` | `KC services/src/main/java/org/keycloak` | as `KC` |
| `VCV` | github.com/FIWARE/VCVerifier | tag `6.31.0`, commit `485226ba4364c6c658bd0fb41c4c19e6a83a7f54` (2026-10-28); no environment deploys it (`docs Architecture/12-identity-and-access.md:29`) |
| `DEP` | joinedcontext-deployment | `cee6ebcb9` (2026-11-07) |
| `POR` | joinedcontext-portal | `d7f91eb28` (2026-11-05) |
| `PLT` | joinedcontext-platform | `e59ceb9f` (2026-11-05) |
| `RI` | the realm import, `DEP components/keycloak/values/config/base-values.yaml.gotmpl` (1317 lines) | as `DEP` |
| `GHSA` | `gh api repos/keycloak/keycloak/security-advisories?per_page=100`, run 2026-11-07: 83 advisories, 2021-12 to 2026-09 | |

Every row below cites one of these. `scripts/research/keycloak-sources.sh` clones `KC` and `VCV` at the pins and re-measures section 9.

## 2. Capability inventory

Upstream's own feature list is the enum `Profile.Feature` (`KC common/src/main/java/org/keycloak/common/Profile.java:60-211`, 75 features with type DEFAULT, PREVIEW, EXPERIMENTAL, DEPRECATED or DISABLED_BY_DEFAULT). The build enables two non-default ones and disables one: `kc.sh build ... --features=cimd,parameterized-scopes --features-disabled=scripts` (`DEP components/keycloak/values/app/base-values.yaml.gotmpl:199`). Verdict column: **used** (file:line of our use), **needed** (the platform specifies it, nothing uses it yet), **drop** (with the reason).

### 2.1 Protocols and grants

| Capability | Upstream source | Verdict |
|---|---|---|
| OIDC authorization code + PKCE | `S/protocol/oidc/endpoints/AuthorizationEndpoint.java`, `S/protocol/oidc/utils/PkceUtils.java` | used: Portal login `POR src/auth/oidc.rs`, every browser client (`RI:702-876`); kaisatsu: S256 only |
| Refresh tokens, offline tokens | `S/protocol/oidc/TokenManager.java`, `S/protocol/oidc/grants/RefreshTokenGrantType.java` | used: offline sessions 30 d idle, 60 d max (`RI:133-135`), claude.ai asks `offline_access` (`RI:435-437`) |
| client_credentials | `S/protocol/oidc/grants/ClientCredentialsGrantType.java` | used: every workload client, `DEP components/*/keycloak-clients.yaml` (13 files) |
| Resource owner password grant | `S/protocol/oidc/grants/ResourceOwnerPasswordCredentialsGrantType.java` | used only by journeys and `scripts/keycloak-login-journey.py` (`DEP components/keycloak/README.md` "Password grant"); drop in kaisatsu: OAuth 2.1 removes it; journeys move to a browser or a test-only signed assertion |
| Implicit flow | `S/protocol/oidc/endpoints/AuthorizationEndpoint.java` | drop: off on every client (`RI:760` `implicitFlowEnabled false`) |
| Standard token exchange V2 (RFC 8693) | `S/protocol/oidc/tokenexchange/StandardTokenExchangeProvider.java` (390 lines); feature `TOKEN_EXCHANGE_STANDARD_V2` default (`Profile.java:93`) | used: Portal person to Endpoint (`POR src/auth/oidc.rs:372`, `DEP components/portal/keycloak-clients.yaml:59-64`), agent proxy (`DEP components/agent-runner/keycloak-clients.yaml:33-34`), gateway to brokers (`RI:857-862`) |
| Token exchange V1 (legacy, impersonation, IdP tokens) | `S/protocol/oidc/tokenexchange/` V1 providers; feature `TOKEN_EXCHANGE` preview, deprecated | drop: never enabled; CVE class GHSA-75p6-52g3-rqc8 |
| Token exchange delegation (`act` claim) | feature `TOKEN_EXCHANGE_DELEGATION` preview (`Profile.java:94`) | needed: an agent acting for a person (`docs Architecture/07-agents-and-mcp.md`); kaisatsu emits `act` from day one |
| JWT authorization grant (RFC 7523 assertion) | `JWT_AUTHORIZATION_GRANT` default (`Profile.java:96`) | needed: device by own key pair (`docs Architecture/12-identity-and-access.md` §3 "A device by its own key pair") |
| Identity Assertion JWT (ID-JAG, cross-domain chaining) | `IDENTITY_ASSERTION_JWT` experimental (`Profile.java:192`), `KC docs/guides/securing-apps/identity-assertion-jwt-authorization-grant.adoc` | needed later: one organization's agent reaching another installation; not in the first run |
| Device authorization grant | `S/protocol/oidc/grants/device/`, `DEVICE_FLOW` default | drop for now: no TV-style client; GHSA-f5h4-wmp5-xhg6 shows the risk |
| CIBA | `CIBA` default | drop: no backchannel-auth client |
| PAR (RFC 9126) | `S/protocol/oidc/par/`, `PAR` default | needed: required by FAPI 2 and HAIP, cheap |
| DPoP (RFC 9449) | `DPOP` default, `KC docs/guides/securing-apps/dpop.adoc` | needed: binds connector refresh tokens to the client key |
| Resource indicators (RFC 8707) | `S/protocol/oidc/resourceindicators/`, `RESOURCE_INDICATORS` experimental | needed and kept off today: 26.8 matches `resource` against a static list only (`DEP components/keycloak/values/app/base-values.yaml.gotmpl:195-198`); kaisatsu resolves `resource` to an Endpoint or connector at request time |
| Parameterized scopes | `PARAMETERIZED_SCOPES` preview (`Profile.java:90`), SPI `ParameterizedScopeType` | used: `connector:{id}` with regexp `[a-z2-7]{26}` (`RI:473-480`) |
| CIMD (Client ID Metadata Document) | `S/protocol/oauth2/cimd/clientpolicy/executor/ClientIdMetadataDocumentExecutor.java`, `CIMD` experimental (`Profile.java:190`) | used: claude.ai and VS Code clients (`RI:443-465`) |
| Dynamic client registration (RFC 7591) | `S/services/clientregistration/` | drop as open registration: CVE class GHSA-95cx-vmr5-3cmr, GHSA-95rm-h7g9-rhcf, GHSA-r7rc-c989-86g6; kaisatsu registers clients only from manifests and CIMD |
| Token introspection (RFC 7662) | `S/protocol/oidc/AccessTokenIntrospectionProvider.java` | needed: APISIX edge and Gitea read opaque state today by JWKS; introspection serves revoked-token checks |
| Revocation (RFC 7009) | `S/protocol/oidc/endpoints/TokenRevocationEndpoint.java` | used: refresh-token revocation ends sibling grants (KNOWLEDGE T-6483) |
| RP-initiated and back-channel logout | `S/protocol/oidc/endpoints/LogoutEndpoint.java`, `BackchannelLogoutResponse.java` | used: `POST /api/v1/auth/backchannel-logout` (`POR src/auth/oidc.rs:1004-1029`) |
| Front-channel logout | `S/protocol/oidc/FrontChannelLogoutHandler.java` | drop: no iframe client |
| Discovery, JWKS, key rotation | `S/protocol/oidc/OIDCWellKnownProvider.java`, `S/keys/` | used: `PLT crates/jc-core/src/auth/jwks.rs:38-96` polls JWKS |
| ES256 default, RS256 per client, HS512 off | `S/keys/` providers `ecdsa-generated`, `rsa-generated`, `hmac-generated` | used: `RI:119`, `RI:354-433`; RS256 only for APISIX `edge` (lua-resty-openidc) |
| SAML 2.0 IdP (Keycloak as SAML server) | `KC saml-core`, `S/protocol/saml/` | drop: no SAML service provider; 9 of 83 GHSA are SAML parsing or signature classes |
| SAML 2.0 broker (upstream SAML IdP) | `S/broker/saml/` | needed: ADFS and Entra ID by SAML (PF-127, T-6633 scope); kaisatsu takes SAML through a separate adapter process (section 5.4) |
| OIDC broker (upstream OIDC IdP) | `S/broker/oidc/` | needed: an organization's own Entra ID or Google Workspace |
| Social brokers (Google, GitHub, Twitter, Instagram, ...) | `S/social/` | drop as named providers: a generic OIDC broker covers the useful ones |
| Kerberos / SPNEGO | `KERBEROS` default (`Profile.java:119`) | drop: no Windows domain login requirement |
| Docker registry auth | `DOCKER` disabled | drop |
| SSF transmitter (Shared Signals) | `KC ssf/`, `SSF` experimental | needed later: push session revocation to the gateway instead of polling (`PLT crates/jc-core/src/auth/token.rs:279` `replace_revocations`) |
| AuthZEN PDP | `KC authzen/`, `AUTHZEN` experimental | drop in kaisatsu: the platform's AuthZEN endpoints are the gateway's (`docs Architecture/12-identity-and-access.md:401-436`); jc-auth decides |
| UMA / Authorization Services | `KC authz/`, `AUTHORIZATION` default | drop: forbidden by I1 (`docs Architecture/12-identity-and-access.md:28`); GHSA-w3p3-7cjg-vgfw, GHSA-2888-g6qc-w4mj, GHSA-f5p5-6xmx-p252 are all in this module |
| SCIM 2.0 server | `KC scim/`, `SCIM_API` default | needed: an organization's HR system provisions people (PF-127 `source: provider`) |
| Client policies and profiles | `S/services/clientpolicy/`, `CLIENT_POLICIES` | used for CIMD only (`RI:443-465`); kaisatsu replaces the engine by fixed per-client-kind rules |
| Client secret rotation | `CLIENT_SECRET_ROTATION` | drop: no client secret exists for workloads (PF-47); remaining secrets rotate by the reconciler |
| Federated client auth (Kubernetes SA tokens) | `S/authentication/authenticators/client/FederatedJWTClientAuthenticator.java`, `S/broker/kubernetes/KubernetesIdentityProvider.java`, `KUBERNETES_SERVICE_ACCOUNTS` default | used: `RI:783-795` `clientAuthenticatorType federated-jwt`, `jwt.credential.issuer kubernetes`; IdP `RI:929-934`; Portal writes them `POR src/reconciler/workload_clients.rs:4-7` |
| SPIFFE trust | `SPIFFE` preview | drop now: Linkerd identities are not SPIFFE SVIDs at the edge; revisit with a mesh change |
| Attestation-based client auth | `CLIENT_AUTH_ABCA` experimental | needed for HAIP wallets only (section 2.4) |

### 2.2 Login, credentials, sessions

| Capability | Upstream source | Verdict |
|---|---|---|
| Authentication flows and executions | `S/authentication/`, tables `AUTHENTICATION_FLOW`, `AUTHENTICATION_EXECUTION` | used: browser step-up, direct grant, master browser (`RI:1022-1250`, `RI:1281-`); kaisatsu replaces configurable flows with one fixed state machine per login kind (section 3.3) |
| Level of assurance (`acr`), step-up | `STEP_UP_AUTHENTICATION`, `acr.loa.map` | used: `{"pwd":1,"mfa":2}` (`RI:348`); Portal refuses decisions without `amr otp` or `acr mfa` (`POR src/auth/session.rs:108-109`) |
| `amr` claim | `oidc-amr-mapper` | used: every platform client (`RI:530`, `RI:825`) |
| Password with policy | `KC server-spi-private/src/main/java/org/keycloak/policy/` | used: `length(12) and upperCase(1) and lowerCase(1) and digits(1) and notUsername and notEmail and passwordHistory(5)` (`RI:178`); master `length(20)...` (`RI:1267`) |
| Password hashing | `KC crypto/default/.../Argon2PasswordHashProviderFactory.java` (id `argon2`, order 300, default when not FIPS, `:151-158`), `Argon2Parameters.java` (argon2id v1.3, 7168 KiB, 5 iterations, parallelism 1, 32 B); `pbkdf2-sha512` 210 000, `pbkdf2-sha256`, `pbkdf2` (SHA-1) 1 300 000 (`KC server-spi-private/.../credential/hash/`) | used by every realm user; migration in section 5.5 |
| TOTP | `S/authentication/authenticators/browser/OTPFormAuthenticator.java`, `OTPCredentialModel` | used: HmacSHA256, 6 digits, 30 s, look-ahead 1 (`RI:181-187`); required for realm role `mfa-required` |
| HOTP | `otpPolicyType hotp` | drop |
| WebAuthn second factor | `S/authentication/authenticators/browser/WebAuthnAuthenticator.java`, `WEB_AUTHN` | configured, not enforced (`RI:191-212`, empty `webAuthnPolicyRpId` means the host, `S/authentication/requiredactions/WebAuthnRegister.java:174-175`) |
| Passkeys (passwordless, conditional UI) | `PASSKEYS` default (`Profile.java:162`) | needed: PF-128, T-6633 scope; first-class in kaisatsu |
| Recovery codes | `RECOVERY_CODES` default | needed: replaces the break-glass kcadm credential delete (`DEP components/keycloak/README.md` "Break-glass") for ordinary people |
| Brute-force protection | `S/services/managers/DefaultBruteForceProtector.java`, `LOGIN_FAILURES_V2` persistent | used: 10 failures in 12 h, 60 s step to 15 min, never permanent (`RI:165-177`, README table) |
| Required actions (verify e-mail, update password, configure TOTP, terms) | `S/authentication/requiredactions/` | used: CONFIGURE_TOTP (`RI:977-1021`), Portal `send_actions` (`POR src/people.rs:373`) |
| Reset credentials by e-mail | `resetCredentialsFlow` (`RI:342`) | used |
| User profile (declarative attributes) | `S/userprofile/` | used implicitly; kaisatsu: typed person record, attributes per organization schema |
| Sessions: SSO, client, offline | `S/services/managers/UserSessionManager.java`, tables `OFFLINE_USER_SESSION`, `OFFLINE_CLIENT_SESSION`; `PERSISTENT_USER_SESSIONS` default | used: SSO 60 min idle, 10 h max, no remember-me (`RI:126-129`) |
| Impersonation | `IMPERSONATION` default | drop for people: GHSA-7fpj-9hr8-28vh, GHSA-w354-2f3c-qvg9; support reads through jc-auth instead |
| Consents | tables `USER_CONSENT*` | used: Portal lists and revokes (`POR src/people.rs:451-458`); `mcp-*` clients consent on (`POR src/reconciler/mcp_clients.rs:4-5`) |
| Account console | `ACCOUNT_V3` | drop: the Portal owns the person's own page; kaisatsu serves only login, enrolment and recovery pages |
| Themes (FreeMarker login, account) | `KC themes/`, `S/theme/` | used: `DEP components/keycloak/charts/theme/files/` (login.ftl 62, template.ftl 277, field.ftl 166 lines, 4 locales) |
| Organizations (identity-first, domains, invitations) | `S/organization/` (23 files, 50 270 tokens), `ORGANIZATION` default (`Profile.java:160`) | not used: one realm, one group subtree per Organization (`docs Decisions/adr-n-058-several-organizations-per-installation.md:48-50`); section 6 |
| Workflows | `WORKFLOWS` default, table `WORKFLOW_STATE` | drop: joiner/leaver automation belongs to the Portal's change lanes |
| Transient users | `TRANSIENT_USERS` experimental | needed for data space participants who must never get a local account (I3, `docs Architecture/12-identity-and-access.md:30`) |

### 2.3 Directory, administration, audit

| Capability | Upstream source | Verdict |
|---|---|---|
| Users, groups, realm and client roles, composites | `S/services/resources/admin/` | used: `POR src/people.rs:284-519` (users, credentials, sessions, consents, groups, role mappings), `POR src/reconciler/groups.rs` (groups, members) |
| Clients, client scopes, protocol mappers | admin `ClientsResource`, `ClientScopesResource` | used: `POR src/reconciler/workload_clients.rs`, `app_clients.rs`, `mcp_clients.rs`, `hub_scopes.rs`, `mqtt_brokers.rs` |
| Group-membership mapper with full path | `oidc-group-membership-mapper` | used: `full.path true` (`RI:505-509`, `RI:810-814`); readers trim one leading `/` (KNOWLEDGE T-6408) |
| User/group attribute mapper (`jc_org`, `jc_groups`) | `oidc-usermodel-attribute-mapper`, aggregate attrs | used: `RI:516`, `RI:843` |
| Audience mapper | `oidc-audience-mapper` | used: 5 scopes (`RI:575-600`, broker audiences per `contextBrokers`) |
| Partial import | `S/partialimport/` | used: `DEP components/keycloak/charts/people/files/ensure-user-ids.sh` (fixed ids, PF-126) and presenter credential copy (`DEP components/keycloak/README.md` "The presenter") |
| Realm import by keycloak-config-cli | external tool, `DEP components/keycloak/images.yaml:17-22` | used for the whole realm; kaisatsu reads the same declarations as manifests (section 7.1) |
| Fine-grained admin permissions V2 | `ADMIN_FINE_GRAINED_AUTHZ_V2` default | used by `DEP components/keycloak/charts/admin-permissions/files/sync-admin-permissions.sh` (201 lines); kaisatsu: jc-auth decides admin calls; GHSA-2qxf-v3g6-73v9, GHSA-27gp-8389-hm4w are this class |
| Admin REST API v2 (clients) | `KC rest/admin-v2`, `CLIENT_ADMIN_API_V2` preview | drop: kaisatsu's admin API is the Portal ops registry (section 11) |
| Events (user, admin) | `S/events/`, tables `EVENT_ENTITY`, `ADMIN_EVENT_ENTITY` | used: 16 enabled types, 30 d expiry, `jboss-logging` listener (`RI:240-260`), admin events with details (`RI:324-325`) |
| Metrics, OpenTelemetry | `USER_EVENT_METRICS`, `OPENTELEMETRY` default | used: metrics on (`DEP .../app/base-values.yaml.gotmpl:199`); GHSA-3692-rrj9-24qw (label cardinality) |
| LDAP user federation | `KC federation/ldap` (105 files) | needed: PF-127 Active Directory, OpenLDAP; none configured (`grep -ril ldap DEP components/keycloak` empty) |
| Vault (secrets SPI) | `S/vault/` | drop: secrets come from the secrets mount by `secretRef` |
| E-mail sender | `S/email/` | used: SMTP from Secret `keycloak-smtp` (`RI:62`) |
| Localization | `REALM_LOCALIZATIONS` | used: en, sk, cs, de theme messages |

### 2.4 Verifiable credentials and federation

| Capability | Upstream source | Verdict |
|---|---|---|
| OID4VCI issuer | `S/protocol/oid4vc/issuance/OID4VCIssuerEndpoint.java`, `OID4VC_VCI` preview, `OID4VC_VCI_PREAUTH_CODE` experimental | needed: I1 (`docs Architecture/12-identity-and-access.md:28`) |
| SD-JWT VC, JWT VC, LDP VC formats | `S/protocol/oid4vc/issuance/signing/` | needed: SD-JWT VC first (EUDI ARF) |
| mso_mdoc | `OID4VC_MDOC` experimental | drop now: no mdoc relying party in the platform |
| OID4VP verifier as identity broker | `S/broker/oid4vp/` (SD-JWT user attribute mapper, request objects, `direct_post.jwt`), `OID4VC_VP` experimental (`Profile.java:152`) | needed: replaces VCVerifier in I2; conformance-tested upstream (`KC tests/conformance/README.md`, suite `oid4vp-1final-verifier-test-plan`) |
| VCVerifier: OID4VP / SIOPv2 relying party | `VCV verifier/verifier.go` (2887 lines), routes `VCV openapi/routers.go`: `/api/v1/authorization`, `/api/v1/samedevice`, `/api/v1/authentication_response`, `/api/v1/loginQR`, `/api/v2/loginQR`, `/api/v1/startsiop`, `/services/:service_id/token`, `/services/:service_id/.well-known/openid-configuration`, `/.well-known/jwks`, `/ws` | needed as behaviour, dropped as a process (I2) |
| DID resolution: did:web, did:key, did:jwk, did:elsi | `VCV did/did_web.go`, `did_key.go`, `did_jwk.go`, `eidas/` | needed: did:web for peers (I3); did:key and did:jwk for wallet holder keys |
| EBSI Trusted Issuers Registry and trusted participants | `VCV tir/tirClient.go`, `tir/did_registry_client.gen.go` | needed: I3 |
| eIDAS trust lists (LOTL) | `VCV eidas/trustlist.go` (828 lines), `eidas/fetcher.go` | needed later: qualified issuers; behind a feature |
| Gaia-X registry | `VCV gaiax/` | drop: no Gaia-X compliance chain is specified |
| Credential status (status lists) | `VCV verifier/credential_status_client.go` (1121 lines), `common/credential_status.go` | needed: revocation of issued and presented credentials |
| JSON-LD proofs | `VCV common/ldproof.go` (1357 lines) | drop in run 1: SD-JWT and JOSE first; LDP behind a feature if a partner needs it |
| Decentralized Claims Protocol (data space) | not in `KC` or `VCV`; `docs Architecture/18-data-space-connector.md:72-107` | needed: kaisatsu issues the participant's credentials, the connector presents them; agreement tokens today are realm tokens with `agreementId` (`PLT crates/context-gateway/src/auth/dataspace_token.rs:1-15`) |

## 3. Internals

### 3.1 Architecture

| Layer | Keycloak 26.8.1 | Source |
|---|---|---|
| Runtime | Quarkus (Vert.x HTTP, RESTEasy Reactive), JVM | `KC quarkus/runtime` |
| Provider model | `KeycloakSession` per request, `ProviderFactory` per SPI, 134 SPIs | `KC server-spi*/src/main/resources/META-INF/services/org.keycloak.provider.Spi` |
| Persistence | JPA (Hibernate) over Postgres, Liquibase migrations (79 changelog files) | `KC model/jpa/src/main/resources/META-INF/jpa-changelog-*.xml` |
| Caches | embedded Infinispan: `realms`, `users`, `authorization`, `keys` (local, invalidated by cluster events), `sessions`, `authenticationSessions`, `loginFailures`, `work` (distributed) | `KC model/infinispan`, `KC docs/guides/server/caching.adoc` |
| Clustering | JGroups; dev uses `KUBE_PING` env but the chart sets `jdbc-ping` | `DEP .../app/base-values.yaml.gotmpl:64-67`, `:80-85` |
| Hostname | one frontend URL per server (`KC_HOSTNAME`), optional per-realm `frontendUrl` attribute | `S/url/HostnameV2Provider.java:130`; ours `https://idm.{domain}` (`DEP .../app/base-values.yaml.gotmpl:71-72`, `DEP components/keycloak/apisix-routes.yaml:6`) |
| Admin UI, account UI | React apps in `KC js/apps` | not deployed to people: console route off (`DEP .../app/base-values.yaml.gotmpl` `ingress.console.enabled false`) |

### 3.2 Data model

Tables from `@Table` annotations in `KC model/jpa/src/main/java` (80 tables). Grouped by what kaisatsu keeps:

| Group | Upstream tables | kaisatsu table (every row carries `installation_id`, `org_id` where it is tenant data) |
|---|---|---|
| Realm config | `REALM`, `REALM_ATTRIBUTE`, `REALM_REQUIRED_CREDENTIAL`, `REALM_LOCALIZATIONS`, `COMPONENT`, `COMPONENT_CONFIG`, `REQUIRED_ACTION_PROVIDER`, `AUTHENTICATION_FLOW`, `AUTHENTICATION_EXECUTION`, `AUTHENTICATOR_CONFIG` | `installation`, `organization` (policy columns: password rules, MFA requirement, session lengths), `signing_key`; no flow tables (fixed state machine) |
| People | `USER_ENTITY`, `USER_ATTRIBUTE`, `USER_REQUIRED_ACTION`, `CREDENTIAL`, `FEDERATED_IDENTITY`, `BROKER_LINK`, `FED_*` (9 tables for federated storage) | `person`, `person_attribute`, `credential` (typed: password, totp, webauthn, recovery), `upstream_link`, `pending_action` |
| Directory | `KEYCLOAK_GROUP`, `GROUP_ATTRIBUTE`, `USER_GROUP_MEMBERSHIP`, `KEYCLOAK_ROLE`, `COMPOSITE_ROLE`, `ROLE_ATTRIBUTE`, `USER_ROLE_MAPPING`, `GROUP_ROLE_MAPPING` | `group`, `membership`; roles stay jc-core `Role`/`RoleBinding` manifests decided by jc-auth, no role tables |
| Organizations | `ORG`, `ORG_DOMAIN`, `ORG_IDENTITY_PROVIDER`, `ORG_INVITATION` | `organization`, `org_domain`, `org_upstream_idp`, `invitation` |
| Clients | `CLIENT`, `CLIENT_ATTRIBUTES`, `CLIENT_INITIAL_ACCESS`, `CLIENT_SCOPE`, `CLIENT_SCOPE_ATTRIBUTES`, `CLIENT_SCOPE_CLIENT`, `CLIENT_SCOPE_ROLE_MAPPING`, `DEFAULT_CLIENT_SCOPE`, `PROTOCOL_MAPPER` | `client` (kind: browser, workload, connector, cimd, device), `client_redirect`, `scope`; mappers become typed claim rules per client kind |
| Upstream IdPs | `IDENTITY_PROVIDER`, `IDENTITY_PROVIDER_MAPPER`, `USER_FEDERATION_PROVIDER`, `USER_FEDERATION_MAPPER` | `upstream_idp` (oidc, saml-adapter, ldap-adapter, kubernetes, did) |
| Sessions | `OFFLINE_USER_SESSION`, `OFFLINE_CLIENT_SESSION`, `AUTH_SESSION`, `ROOT_AUTH_SESSION`, `LOGIN_FAILURE`, `SINGLE_USE_OBJECT`, `REVOKED_TOKEN` | `session`, `client_session`, `login_attempt`, `single_use` (codes, nonces, DPoP jti), `revocation` |
| Consent | `USER_CONSENT`, `USER_CONSENT_CLIENT_SCOPE` | `consent` |
| Credentials issued/held | `ISSUED_VER_CREDENTIAL`, `USER_VER_CREDENTIAL`, `FED_ISSUED_VER_CREDENTIAL`, `FED_USER_VER_CREDENTIAL` | `issued_credential`, `status_list` |
| Audit | `EVENT_ENTITY`, `ADMIN_EVENT_ENTITY`, `OUTBOX_ENTRY` | `audit_event` (one table, append-only, partitioned by month), outbox for SSF |
| Dropped | `RESOURCE_SERVER*` (5), `RESOURCE_ATTRIBUTE`, `WORKFLOW_STATE`, `CLUSTER_EVENT`, `MIGRATION_MODEL`, `SERVER_CONFIG` | UMA, workflows and Infinispan bookkeeping have no kaisatsu counterpart |

Credential payloads (the migration contract, section 5.5): `CREDENTIAL.SECRET_DATA` holds JSON `{value, salt, additionalParameters}` (`KC server-spi/.../credential/dto/PasswordSecretData.java:18-31`), `CREDENTIAL_DATA` holds `{hashIterations, algorithm, additionalParameters}` (`PasswordCredentialData.java:12-33`); argon2 puts `type`, `version`, `hashLength`, `memory`, `parallelism` in `additionalParameters` (`Argon2PasswordHashProviderFactory.java:22-27`). OTP: secret value plus `{subType, digits, counter, period, algorithm, secretEncoding}` (`OTPCredentialData.java:7-16`, encoding UTF8 or BASE32 `OTPCredentialModel.java:25`). WebAuthn: `{aaguid, credentialId, counter, attestationStatement, credentialPublicKey, attestationStatementFormat, transports}` (`WebAuthnCredentialData.java:33-42`).

### 3.3 Request flows

Browser login today (`RI:1022-1250` flows, `S/authentication/AuthenticationProcessor.java`):

1. Client redirects to `/realms/{r}/protocol/openid-connect/auth` with PKCE; `AuthorizationEndpoint` creates a root and a tab authentication session (Infinispan `authenticationSessions`, cookie `AUTH_SESSION_ID`).
2. `AuthenticationProcessor` walks the browser flow: cookie (existing SSO) or username/password form, then the conditional subflow: holder of `mfa-required` must pass OTP; anyone with a configured OTP or WebAuthn passes it; `acr_values=mfa` runs the step-up subflow (`DEP components/keycloak/README.md` login table).
3. Required actions run (CONFIGURE_TOTP for an unenrolled `mfa-required` holder).
4. `AuthenticationManager` creates the user session (`KEYCLOAK_IDENTITY` cookie, persisted since `PERSISTENT_USER_SESSIONS`), issues a code bound to the client session.
5. Token endpoint: code + verifier, client auth, `TokenManager` builds access/ID/refresh tokens by applying the client's default scopes and their mappers; signs ES256 (RS256 for `edge`).

Workload token today: the pod's projected ServiceAccount token goes as `client_assertion` with `client_assertion_type jwt-bearer`; `FederatedJWTClientAuthenticator` finds client `{project}-{name}`, sees `jwt.credential.issuer kubernetes`, and `KubernetesIdentityProvider` verifies the assertion against `https://kubernetes.default.svc.cluster.local` keys read with Keycloak's own projected token (`DEP .../app/base-values.yaml.gotmpl:224-249`); the subject must equal `system:serviceaccount:{ns}:{sa}` (`POR src/reconciler/workload_clients.rs:4-7`).

Token exchange today: the Portal holds the person's token, posts `grant_type urn:ietf:params:oauth:grant-type:token-exchange` with `audience {endpoint slug}` (`POR src/auth/oidc.rs:372`); Keycloak checks `standard.token.exchange.enabled` on the requester, the subject token's `aud` contains the requester, the requested scope is optional on the requester and an audience mapper exists (KNOWLEDGE T-6063).

kaisatsu keeps the wire for every one of these and drops the configurable flow graph: four fixed state machines (browser person, upstream broker, workload assertion, wallet presentation), each a Rust enum whose transitions are unit-tested, with per-organization policy columns choosing which steps are mandatory. Reason: second-factor, step-up and flow bypasses recur in the advisories (GHSA-5jfq-x6xp-7rw2, GHSA-4f53-xh3v-g8x4, GHSA-4pc7-vqv5-5r3v, GHSA-c9h6-v78w-52wj, section 5.3), and a flow graph an administrator can rewire is a test matrix nobody covers.

### 3.4 Background work, caching, scaling

| Concern | Keycloak | kaisatsu |
|---|---|---|
| Expired sessions, events, single-use | Quarkus timers (`S/timer/`), event expiry 30 d (`RI:241`) | one tokio task per table: partition drop for `audit_event`, `DELETE ... WHERE expires_at < now()` in batches of 1000 for sessions and single-use |
| Key rotation | manual or by provider priority | scheduled: new ES256 key published in JWKS 24 h before it signs, old key kept 2x max token life |
| Cache invalidation | Infinispan cluster events | none needed at one replica; at N replicas Postgres `LISTEN/NOTIFY` on `config_version` plus a 5 s TTL on per-organization config |
| Revocation fan-out | gateway polls marks (`PLT crates/jc-core/src/auth/token.rs:279`) | SSF push (outbox) plus the existing poll as fallback |
| Scale model | stateless pods plus distributed caches; dev runs 1 replica, DB pool 4 (`DEP .../app/base-values.yaml.gotmpl:55-56`) | stateless pods, all state in Postgres; login CPU bounded by an argon2 semaphore (section 7.3) |

## 4. Extension model

### 4.1 Keycloak SPIs

134 SPIs are registered (`KC server-spi/src/main/resources/META-INF/services/org.keycloak.provider.Spi`, `KC server-spi-private/...`). The ones a deployment writes plugins for:

| SPI | Hook | What it may touch | Isolation upstream |
|---|---|---|---|
| `Authenticator`, `FormAuthenticator`, `RequiredAction` | a step in a flow | the whole `KeycloakSession`: every realm, user, credential | none: same JVM, same classloader rules, full DB access |
| `ProtocolMapper` | token and userinfo building | user, session, client models | none; script mappers turned off (`--features-disabled=scripts`, `DEP .../app/base-values.yaml.gotmpl:188-199`, T-2857) |
| `EventListener` | every user and admin event | event payload, session | none |
| `UserStorageProvider` (LDAP, custom DB) | user lookup, credential validation | user federation tables | none |
| `IdentityProvider`, `IdentityProviderMapper` | brokering | user creation, linking | none |
| `PasswordHashProvider`, `PasswordPolicy` | credential storage | credential rows | none |
| `ClientPolicyExecutor`, `ClientPolicyCondition` | client registration and requests | client model | none |
| `Theme`, `ThemeResource` | FreeMarker templates, messages | template model of the page | template engine only |
| `RealmResourceProvider` | arbitrary REST endpoints under `/realms/{r}/` | everything | none |

A provider is a JAR in `/opt/keycloak/providers`, picked up at `kc.sh build`; it runs with the server's privileges. Our deployment ships none: only a theme (`DEP components/keycloak/charts/theme`).

### 4.2 Rust equivalent

| Keycloak SPI | kaisatsu | Mechanism |
|---|---|---|
| Authenticator, RequiredAction | fixed steps: password, totp, webauthn, recovery code, upstream OIDC, upstream SAML (adapter), LDAP bind (adapter), wallet presentation, terms acceptance | built-in modules behind Cargo features `saml`, `ldap`, `oid4vp`, `oid4vci`, `scim`; no runtime-loaded authenticators |
| ProtocolMapper | claim rules per client kind: `groups` (full path), `jc_org`, `jc_groups`, `amr`, `acr`, `aud` from scopes, `act` | data, not code: a manifest field per client kind; an organization may add attribute claims from its own person schema |
| EventListener | audit stream: Postgres table plus OTLP log export plus SSF outbox | sinks configured per installation; a custom sink is a WASM component (below) |
| UserStorageProvider | LDAP and SCIM adapters writing `person` rows (import mode), never live federation on every login | adapter crate per protocol |
| Theme | per-organization branding: logo, colours, texts per locale, from the Organization manifest; templates compiled in (askama), no template upload | data only; CSP nonce per page |
| Custom endpoint, custom claim logic | WASM component on the platform wasm-host | WIT interface `jc:identity/claims@0.1` (input: person attributes the organization exposes, client id; output: extra claims of a declared schema); fuel 10 M per call, 16 MiB memory, no network, no clock beyond the request time, deadline 50 ms; a component failing or timing out yields no extra claims and an audit row |

Decided (worker-t6637, owner may override): kaisatsu has no in-process plugin that can read credentials or sessions; the only code extension is the claims component above, because every upstream SPI runs with full database access and the CVE history (section 5.3) shows mapper and policy plugins as a privilege-escalation path. Options: (a) WASM claims hook only (chosen), (b) WASM authenticator steps with a capability API, (c) no extension at all.

## 5. Security

### 5.1 Flows in kaisatsu (sequence per flow)

Browser person (`org` chosen first, identity-first):

1. `GET /authorize` (PKCE S256 required, PAR optional, `client_id` known or CIMD-fetched): kaisatsu resolves the installation by host and the organization by host (custom domain), by `org` hint, or by the e-mail domain the person types (`org_domain`, exact beats wildcard as upstream, `KC docs/documentation/server_admin/topics/organizations/managing-domains.adoc`).
2. Organization policy picks the first factor: passkey (conditional UI), upstream IdP (domain routing, auto-redirect only when the person has no local first factor, same rule as upstream), or password.
3. Second factor when the organization, the client, `acr_values=mfa` or a role marked MFA-required demands it: passkey (counts as both), TOTP, recovery code.
4. Pending actions (enrol TOTP or passkey, accept terms, change temporary password).
5. Session row (`session_id`, `org_id`, `person_id`, `acr`, `amr`, `auth_time`), cookie `__Host-wk` (Secure, HttpOnly, SameSite=Lax, 32 random bytes, stored hashed).
6. Code (single-use row, 60 s), token endpoint, tokens with `iss` (one issuer per installation), `org`, `sub`, `azp`, `aud`, `acr`, `amr`, `sid`, `groups` (full paths inside `org`), `scope`.

Workload: `client_credentials` with `client_assertion` = projected Kubernetes token (kept wire-compatible with `federated-jwt`), or RFC 7523 private-key JWT for devices; the Kubernetes issuer keys are fetched with kaisatsu's own projected token as today.

Connector (AI client): code + PKCE from a CIMD client (document fetched from an allow-listed host, exact redirect URIs, `RI:443-465`); scope `connector:{id}` resolved against the Portal connector at request time, so `aud` names the connector door (closes the 26.8 gap noted at `RI:466-472`); DPoP-bound refresh token; revocation by connector id.

Wallet: OID4VP request (signed request object, `direct_post.jwt`), presentation verified (SD-JWT VC signature, key binding JWT `aud` and nonce, status list, issuer in TIR or the organization's trust list), mapped to a transient subject, short internal JWT (5 min) for the gateway, no local person row unless the organization links one.

Token exchange: requester client must be allowed to exchange for that audience by its client kind and manifest; subject token must name the requester in `aud`; result carries `act` when an agent acts for a person.

### 5.2 Authorization, secrets, crypto, limits

| Topic | Keycloak today | kaisatsu |
|---|---|---|
| Admin authorization | realm-management client roles + FGAP v2 (`DEP components/keycloak/charts/admin-permissions`) | every admin call is a Portal op checked by jc-auth (`Effective` today, `POR src/permissions.rs`); kaisatsu's admin API accepts only the Portal's workload identity and the person's token, and re-checks the organization of every target row |
| Data authorization | none (I1) | none: jc-auth and Antares views decide data (ADR-N-050) |
| Secrets at rest | client secrets in `CLIENT.SECRET` (plain), TOTP secrets plain in `CREDENTIAL.SECRET_DATA`, signing keys in `COMPONENT_CONFIG` | TOTP secrets and signing keys encrypted with an installation key from the secrets mount (AES-256-GCM, key id per row); client secrets stored as argon2id hashes; no secret in logs |
| Token signing | ES256 default, RS256 for `edge` (`RI:354-433`) | ES256 default, EdDSA optional, RS256 per client kind `edge` until APISIX moves; algorithm taken from the key, never from the header (as `PLT crates/jc-core/src/auth/token.rs:9-10`) |
| Password hashing | argon2id 7 MiB, t=5 (`Argon2Parameters.java`) | argon2id m=19 MiB, t=2, p=1 (OWASP 2024 minimum), legacy formats verified and rehashed (5.5) |
| Input limits | per endpoint, form sizes in Quarkus | request body 64 KiB on login and token endpoints, 1 MiB on admin import, redirect URI exact match only, `state` and `nonce` 512 B, CIMD document 5 KiB and 3 s fetch timeout from allow-listed hosts |
| Rate limits | brute force per user (`RI:165-177`) | per person (same lockout rule), per source address, per client on the token endpoint; per organization quota on logins and token mints |

### 5.3 CVE history by class (GHSA, 83 advisories) and the design answer

Classification by worker-t6637 from the 83 advisory summaries (`GHSA` command in section 1, output kept in the task evidence `evidence/T-6637/ghsa.tsv`); a class count is the number of summaries that name it, rounded into the closest class.

| Class | Count | Examples | kaisatsu answer |
|---|---|---|---|
| Redirect URI validation (open redirect, path traversal, wildcard, case) | 9 | GHSA-mpwq-j3xf-7m5w, GHSA-72vp-xfrc-42xm, GHSA-mrv8-pqfj-7gp5, GHSA-g8q8-fggx-9r3q, GHSA-w8gr-xwp4-r9f7, GHSA-cvg2-7c3j-g36j, GHSA-v3f7-2p4r-mwfw | exact string match only, no wildcard, no normalisation; parsed with `url` crate then compared byte-for-byte; test corpus of the upstream bypass shapes |
| XSS and HTML injection in pages | 9 | GHSA-9hhc-pj4w-w5rv, GHSA-8rmm-gm28-pj8q, GHSA-27gc-wj6x-9w55, GHSA-755v-r4x4-qf7m, GHSA-w9mf-83w3-fv49 | askama auto-escaping, no user-supplied template, `error_description` never rendered (fixed message per error code), CSP with nonce, no inline handlers |
| SAML signature and assertion handling | 7 | GHSA-xgfv-xpx8-qhcr, GHSA-794g-x443-36f7, GHSA-f8m4-v488-rmrm, GHSA-fgq2-hxm5-8xg2, GHSA-4pc7-vqv5-5r3v | no SAML parser in the identity process: a separate adapter speaks SAML and hands a signed internal assertion (5.4) |
| Dynamic registration and client takeover | 4 | GHSA-95cx-vmr5-3cmr, GHSA-95rm-h7g9-rhcf, GHSA-r7rc-c989-86g6, GHSA-v436-q368-hvgg | no open registration; clients from manifests and CIMD only; CIMD clients are public, code flow only, no mappers |
| Admin privilege escalation | 6 | GHSA-2qxf-v3g6-73v9, GHSA-27gp-8389-hm4w, GHSA-2cww-fgmg-4jqc, GHSA-83x4-9cwr-5487, GHSA-32h4-44jj-c5vx | one decision path (jc-auth), deny by default, per-row organization check, a test per admin route for every role |
| Authorization Services (UMA, path matcher) | 4 | GHSA-2888-g6qc-w4mj, GHSA-f5p5-6xmx-p252, GHSA-w3p3-7cjg-vgfw, GHSA-46c8-635v-68r2 | module not built (I1) |
| Second factor and step-up bypass | 4 | GHSA-5jfq-x6xp-7rw2, GHSA-4f53-xh3v-g8x4, GHSA-xmmm-jw76-q7vg, GHSA-c9h6-v78w-52wj | fixed state machine, `acr` computed from the factors actually passed in this session, OTP code single-use per period (stored in `single_use`), re-authentication creates a new session id |
| Token and signature verification | 3 | GHSA-j97h-3f8r-mrjr (algorithm confusion), GHSA-xpwp-2pcm-8xq3 (replay), GHSA-9g98-5mj6-f9mv | algorithm pinned by key, `jti` replay table with a unique constraint, codes bound to client and PKCE |
| mTLS and proxy trust | 3 | GHSA-93ww-43rr-79v3, GHSA-jgwc-jh89-rpgq, GHSA-hw58-3793-42gg | forwarded headers trusted only from the mesh peer identity; outbound TLS verifies hostnames (rustls) |
| Brute force and lockout | 3 | GHSA-gc7q-jgjv-vjr2, GHSA-cq42-vhv7-xr7p | attempt counter in one `UPDATE ... RETURNING` (no race), lockout time-limited, per-address limiter separate from per-person |
| LDAP (injection, deserialization, bind, DN boundary) | 5 | GHSA-8hc5-rmgf-qx6p, GHSA-4hx9-48xh-5mxr, GHSA-2p82-5wwr-43cw, GHSA-hmr6-pxx9-552p, GHSA-c25h-c27q-5qpv | adapter with escaped filters (RFC 4515), no Java object attributes, bind result checked, search base enforced, bind secret by `secretRef` and never echoed |
| Config and environment exposure | 4 | GHSA-8hxp-qmph-w5gq, GHSA-f4v7-3mww-9gc2, GHSA-v7gv-xpgf-6395, GHSA-g6qq-c9f9-2772 | no variable substitution in imported data; configuration is typed manifests |
| DoS (TLS renegotiation, headers, regex, metrics cardinality) | 5 | GHSA-q8hq-4h99-fj7x, GHSA-w3g8-r9gw-qrh8, GHSA-wq8x-cg39-8mrr, GHSA-3692-rrj9-24qw, GHSA-m6q9-p373-g5q8 | rustls (no renegotiation), `regex` crate (linear time), metric labels from fixed enums only, body and header limits |
| Session fixation, logout, impersonation | 4 | GHSA-5rxp-2rhr-qwqv, GHSA-97g8-xfvw-q4hg, GHSA-7fpj-9hr8-28vh, GHSA-rvjg-gxwx-j5gf | session id rotated at every authentication step, logout requires `id_token_hint` or a session cookie, no impersonation |
| E-mail trust and phishing | 3 | GHSA-c7xw-p58w-h6fj, GHSA-xhpr-465j-7p9q, GHSA-m4j5-5x4r-2xp9 | an upstream e-mail is trusted only when the organization marks the IdP as e-mail-verifying and the domain belongs to that organization; SMTP headers built by `lettre` |
| Organization claim | 1 | GHSA-gvgg-2r3r-53x7 | `org` claim from the session's organization only, never from a requested scope alone |
| Other (PAR leak, plaintext password storage, cert validation, IDN, debug bind) | 9 | GHSA-69fp-7c8p-crjr, GHSA-5q66-v53q-pm35, GHSA-3qh5-qqj2-c78f, GHSA-mwm4-5qwr-g9pf, GHSA-j4vq-q93m-4683 | PAR request objects expire in 60 s and are single-use; passwords never logged (typed `Secret<String>` with redacting Debug); IDN domains normalised to punycode before domain matching |

### 5.4 Federation adapters

SAML and LDAP stay out of the token-signing process. `kaisatsu-saml` and `kaisatsu-ldap` run as separate workloads with their own ServiceAccount, speak the legacy protocol, and post a signed internal assertion (ES256, 60 s, audience `kaisatsu`) to kaisatsu's broker endpoint. A parser bug there yields at most a forged login for that organization's upstream, never key material or another organization's people. Decided (worker-t6637, owner may override): separate adapter processes, because 12 of 83 GHSA sit in SAML and LDAP code. Options: in-process behind features, separate adapters (chosen), drop SAML and LDAP.

### 5.5 Credential migration from Keycloak without resets

| Credential | Keycloak storage | Migration |
|---|---|---|
| Password | argon2id (default since the FIPS-off order 300 factory) or pbkdf2-sha512/-sha256/-sha1 rows (3.2) | copy `SECRET_DATA` and `CREDENTIAL_DATA` into `credential.legacy`; verify with the stored algorithm and parameters (`argon2` crate, `pbkdf2` crate); on the first successful login rehash with kaisatsu's parameters and clear `legacy`. The deployment already copies hashed credentials between realms (`DEP components/keycloak/README.md` "The presenter", `scripts/presenter-secret.sh`), which proves the export path |
| TOTP | secret value and parameters in `CREDENTIAL` | copy secret (encrypt at rest), algorithm HmacSHA256, digits, period, encoding; codes keep working with no re-enrolment |
| WebAuthn and passkeys | public key, credential id, counter, AAGUID; RP ID = Keycloak host when `webAuthnPolicyRpId` is empty (`WebAuthnRegister.java:174-175`), so `idm.{domain}` today (`DEP components/keycloak/apisix-routes.yaml:6`) | copy rows; a credential answers only to the RP ID it was made for, so kaisatsu keeps RP ID `idm.{domain}` and serves logins of migrated passkeys on that host |
| Recovery codes | hashed codes | copy hashes |
| Sessions, offline tokens | `OFFLINE_*` tables | not migrated: people sign in once after cut-over; connectors re-consent (offline tokens are bound to Keycloak's key and session ids) |
| Upstream links | `FEDERATED_IDENTITY` | copy (`upstream_idp`, `subject`) |
| User ids | Keycloak UUIDs, fixed for demo people (`DEP components/keycloak/demo-users.yaml`) | kept as `person_id`: manifests name people by id (ADR-N-061, PF-126) |

Export: a one-shot `kaisatsu import --from-keycloak <postgres url>` reads the Keycloak database read-only (no admin API, which does not return hashes), maps the group subtree `/{organization}/...` to `org_id` + group path, and writes a dry-run report first.

## 6. Tenancy

### 6.1 Upstream model and limits

| Question | Keycloak 26.8.1 | Source |
|---|---|---|
| Unit of isolation | realm: own users, clients, keys, flows, themes, sessions | `REALM` table, every entity has `REALM_ID` |
| Organizations inside a realm | `ORG` rows with domains, linked IdPs, groups, invitations, members; identity-first login picks the organization by e-mail domain | `S/organization/authentication/authenticators/browser/OrganizationAuthenticator.java`, `KC docs/.../organizations/managing-domains.adoc` |
| Organization in tokens | scope `organization`, `organization:{alias}`, `organization:*`; membership mapper | `S/organization/protocol/mappers/oidc/OrganizationScope.java:54-190`, `OrganizationMembershipMapper.java` |
| Custom domain per organization | no: a server has one hostname; a realm may set `frontendUrl` | `S/url/HostnameV2Provider.java:130` |
| Keys, password policy, MFA rules, session lengths per organization | no: realm-wide | `REALM` columns |
| Admin per organization | FGAP v2 can scope admins to members of an organization; GHSA-27gp-8389-hm4w shows the class | `KC docs/.../admin-console-permissions/` |
| Many realms | realm-per-tenant works to some hundreds of realms; every realm loads into the `realms` cache and the admin console | `KC docs/guides/server/caching.adoc` |
| Several instances of one product per organization | not modelled | |

### 6.2 Platform today

One realm per installation (PF-01). Each Organization owns a group subtree `/{organization}` (`docs Decisions/adr-n-058-several-organizations-per-installation.md:48-50`); jc-core `Organization`, `Project`, `ContextSpace`, `Role`, `RoleBinding`, `Group`, `Policy`, `DelegationPolicy`, `ServiceAccount` are manifests in the forge, the Portal reconciler writes Keycloak groups (`POR src/reconciler/groups.rs:1-6`, attribute `managed-by: joinedcontext`) and clients (`workload_clients.rs`, `app_clients.rs`, `mcp_clients.rs`). Tokens carry `groups` with full paths and `jc_org` (`RI:505-516`); `PLT crates/jc-core/src/auth/token.rs:141-148` `member_of`, `groups_in`. Known traps: bare group names matched across organizations until full paths (KNOWLEDGE T-6408), seed Organization `hel` owning subtree `/helsinki` (KNOWLEDGE T-6461), demo people with no `jc_org` (KNOWLEDGE T-6464). Members join an organization's `members` group (`POR src/people.rs:503`).

### 6.3 kaisatsu design

| Requirement | Design |
|---|---|
| Ids in every table | `installation_id` and `org_id` (UUIDv7) on every tenant row; `instance_id` where a product runs several identity domains for one organization (an organization may run two login domains, e.g. staff and citizens: `identity_domain` row with its own host, upstream IdPs, branding, password and MFA policy) |
| Forced RLS | `ALTER TABLE ... FORCE ROW LEVEL SECURITY`; policy `org_id = current_setting('wk.org')::uuid`; the app role is not BYPASSRLS; cross-organization reads (login before the organization is known, token endpoint) go through `SECURITY DEFINER` functions that return one row by unique key (host, client id, code hash) and nothing else. Predicates use btree keys (leakproof operators only, KNOWLEDGE T-4852) |
| Custom domain and TLS | `org_domain` (login host) per organization or identity domain; certificates by cert-manager HTTP-01 per host (no wildcard, per CLAUDE.md cluster rule); issuer stays one per installation, `org` is a claim (`Research/next-platform/03-identity-and-authz.md` §2) |
| Organization choice | by host first, then `org` hint from the client, then e-mail domain; a person in two organizations has two `person` rows linked by a verified e-mail, never one row with two orgs (avoids cross-org inference through one account) |
| One identity, one policy engine | kaisatsu issues tokens, jc-auth decides; both share the `jc-auth` crate types (`OrgId`, `Subject`, `Decision`) |
| Quotas | per organization and per identity domain: people count, clients, logins per minute, token mints per minute, audit retention days; enforced in the same transaction as the write (`SELECT ... FOR UPDATE` on the quota row) |
| Keys | one signing key set per installation (gateway and Antares trust one JWKS); per-organization keys only if the owner asks (section 10) |

Isolation tests (each a Rust integration test over Postgres with forced RLS, two organizations `a`, `b` with the same group names, client slugs and person e-mail local parts):

1. A person of `a` signs in on `b`'s host: refused with the same page as an unknown user.
2. Admin token of `a` lists people, groups, clients, sessions, audit: zero rows of `b`; `total` counts only `a`.
3. Admin of `a` gets a `b` person by id: 404 identical in body and timing class to an unknown id.
4. Token of `a` exchanged for an audience in `b`: refused.
5. CIMD client first seen on `a` reaches `b`: separate client row, separate consent.
6. Upstream IdP shared by `a` and `b`: a `b` domain e-mail never joins `a` (upstream rule, `managing-domains.adoc` "domain gate").
7. `groups` claim of an `a` token never holds a `b` path, even with the same leaf names.
8. Audit read tool of `a` (section 11) sees no `b` event, including failed logins with `b` usernames typed on `a`'s host.

## 7. Operations

### 7.1 Config as code

Today: realm from `RI` by keycloak-config-cli, people by partial import (`DEP components/keycloak/charts/people`), admin permissions by a script Job, clients written by the Portal reconciler at runtime. kaisatsu reads the Organization, Group, ServiceAccount and client-kind manifests the reconciler already stages, plus an `IdentityConfig` per organization (policy columns, branding, domains, upstream IdPs with `secretRef`). No admin UI writes configuration outside a manifest except people, sessions and credentials (personal data stays out of git, ADR-N-061).

### 7.2 Migrations, backups, upgrades

| Topic | Keycloak | kaisatsu |
|---|---|---|
| Schema migration | Liquibase at boot, 79 changelogs; a major upgrade wants a dump first (`DEP components/keycloak/images.yaml:13-14`, T-4124) | sqlx migrations, forward-only, `migrations.rollback.toml` as Antares does; boot under an advisory lock |
| Backup | the shared CNPG cluster dump (nightly on prod) | same database cluster, own schema; `pg_dump --schema=kaisatsu` drill per release |
| Upgrade | rolling for patch releases (`ROLLING_UPDATES_V2`) | rolling: two consecutive versions read the same schema |

### 7.3 Observability and budget

Keycloak on dev: heap capped at 25 % of a 2048 Mi limit with 146 MB live (`DEP .../app/base-values.yaml.gotmpl:57-64`, T-5282), sat at 1021 Mi before the cap (T-5892); the build init container alone asks 256 Mi to 1 Gi (`:200-206`); keycloak-config-cli 512 Mi to 1 Gi per apply (`RI:19-24`).

kaisatsu budget at 100 req/s (mix: 80 % JWKS, discovery, introspection and token refresh; 15 % token exchange and client_credentials; 5 % browser logins = 5 password checks/s):

| Resource | Budget | Basis |
|---|---|---|
| RSS steady | 64 MiB | axum + sqlx pool of 4 + config cache for 100 organizations |
| RSS peak | 160 MiB | argon2id semaphore of 4 concurrent hashes x 19 MiB = 76 MiB above steady |
| CPU | 0.3 core | ES256 sign about 50 µs per token; argon2id t=2 m=19 MiB about 30-50 ms per check: 5/s = 0.25 core |
| Postgres connections | 4 | the 55-connection budget of dev (`DEP tests/test_postgres_connection_budget.py`, KNOWLEDGE T-4933) |
| Platform share | 160 MiB of the 2 GB whole-platform target | replaces Keycloak (up to 2 Gi limit) and keycloak-config-cli Jobs |

Signals: Prometheus metrics with fixed label sets (`outcome`, `flow`, `org` as an id from the config table, never request text), OTLP traces, audit events carrying `org_id`, `identity_domain_id`, `client_id`, `person_id`, `session_id` at write time (T-6640 rule).

## 8. Test oracles

| Oracle | What it proves | How |
|---|---|---|
| OpenID Foundation conformance suite | OIDC basic, config, PKCE, FAPI 2 security profile, OID4VCI issuer (HAIP and non-HAIP), OID4VP verifier | containers `mongodb`, `conformance`, `nginx` as upstream runs them (`KC tests/conformance/README.md`, suite `release-v5.2.2`); one plan per profile, 100 % of modules passing or a written waiver per module |
| Differential run against Keycloak 26.8.1 | the Portal's admin calls and every token our services read | same manifests applied to Keycloak (pinned image) and kaisatsu; a recorder replays the calls of `POR src/people.rs`, `src/reconciler/{groups,workload_clients,app_clients,mcp_clients,hub_scopes}.rs` and compares status and normalised bodies; tokens compared claim by claim (`iss`, `aud`, `groups`, `jc_org`, `amr`, `acr`, `scope`, `azp`) |
| Our consumers' tests | the platform still verifies kaisatsu tokens | `PLT crates/jc-core` auth tests (`--features auth`), `context-gateway` `tests/` (subject, accounts), Portal `tests/` that sign in (wiremock realm helpers `auth::oidc::tests`) |
| Deployment journeys | browser flows end to end | `DEP scripts/keycloak-login-journey.py` modes steward, enrol, lockout, stepup, grant; `tests/test_keycloak_login_hardening.py` rule checks rewritten against kaisatsu config |
| Upstream unit and integration tests as specification | edge cases per protocol | `KC testsuite/integration-arquillian` (1454 files) and `KC tests/base` (799 files): mined for cases (redirect validation, token exchange, PKCE, brute force), rewritten as Rust tests; never executed against kaisatsu |
| EUDI reference wallet | real wallet interop for OID4VCI and OID4VP | issuance and presentation of an SD-JWT VC end to end |
| Credential migration | no reset needed | import a dump of a Keycloak realm with argon2, pbkdf2-sha256 and TOTP and WebAuthn users; scripted logins succeed; rows rehashed after first login |
| Isolation tests | section 6.3 list | required green before merge |

A worker proves 100 % by the conformance plan reports (JSON exported per plan, all modules PASSED or REVIEW with a note), the differential report (0 unexplained differences), and the isolation suite.

## 9. Argon pack plan

Token counts measured 2026-11-07 by `scripts/research/keycloak-sources.sh` (repomix 1.18.1, `--remove-comments --remove-empty-lines`, tests excluded). Globs are in the script; `S` and docs prefixes as in section 1.

| Group | Contents | Tokens | Files |
|---|---|---|---|
| A1-protocol | `S/protocol/oidc/**`, `S/protocol/oauth2/**` (CIMD), login protocol base, `AuthenticationManager`, `AuthenticationSessionManager`, `UserSessionManager`, `DefaultBruteForceProtector`, `S/broker/kubernetes/**`, `S/keys/**`, `S/jose/**` | 306 136 | 284 |
| A2-login-orgs | `S/authentication/**`, `S/organization/**`, `S/credential/**`, login FreeMarker model, `Profile.java`, password hash providers (argon2, pbkdf2) | 266 594 | 251 |
| A3-model-docs | `server-spi` models and credential DTOs, JPA entities, organization JPA, server_admin topics organizations, authentication, sessions, threat, clients; guides token-exchange, mcp-authz-server, dpop, hostname, caching, db | 245 749 | 232 |
| B1-admin-federation | admin REST resources, events, partial import, export/import, LDAP federation, docs admin permissions, user federation, identity broker, events, users, roles and groups | 346 347 | 261 |
| C1-vc | `S/protocol/oid4vc/**`, `S/broker/oid4vp/**`, `S/broker/trust/**`, docs oid4vci | 174 610 | 198 |
| C2-vcverifier | VCVerifier Go sources without tests, `api/*.yaml`, `docs/*.md`, README, `server.yaml` | 236 533 | 101 |
| O1-deployment | `DEP components/keycloak/**`, `components/*/keycloak-clients.yaml` | 79 935 | 74 |
| O2-portal | `POR src/people.rs`, `src/auth/**`, reconciler groups, workload, app, mcp clients, hub scopes, `src/connectors.rs` | 134 634 | 15 |
| O3-platform | `PLT crates/jc-core/src/auth/**`, `crates/context-gateway/src/auth/**` | 23 885 | 7 |
| O4-docs | Architecture/12, Architecture/18, ADR-N-058, -061, -064, -067, this page (about 26k of the measured 29 284 is without this page; with it about 55k) | 55 000 | 7 |

Contract file (shared by every run, written before run 1, about 15k tokens): crate layout, the `jc-auth` types, table DDL of section 3.2, the state machine enums of 3.3, the WIT of 4.2, error codes, the admin op names of section 11.

| Run | Packs | Tokens | Output |
|---|---|---|---|
| 1 core protocol | contract + A1 + O3 + O4 | about 400k | `kaisatsu-oidc` (authorize, token, exchange, revocation, introspection, discovery, keys, CIMD, DPoP, PAR), `kaisatsu-store` sessions part; about 12k lines |
| 2 login and organizations | contract + A2 + O1 + O4 | about 417k | `kaisatsu-login` state machines, password/TOTP/passkey/recovery, organizations, domains, branding pages; about 10k lines |
| 3 data model and Portal contract | contract + A3 + O2 + O4 | about 451k | `kaisatsu-store` (sqlx migrations, RLS policies), Keycloak importer, admin API matching the Portal's calls; about 9k lines |
| 4 admin, events, federation adapters | contract + B1 + O4 + `POR src/people.rs` | about 425k | admin ops, audit, SCIM server, `kaisatsu-ldap` adapter, OIDC broker, `kaisatsu-saml` adapter skeleton; about 10k lines |
| 5 credential issuance | contract + C1 + O3 + O4 | about 270k | `kaisatsu-vci` (OID4VCI, SD-JWT VC, status lists), OID4VP broker; about 6k lines |
| 6 verifier and trust | contract + C2 + O4 | about 306k | `kaisatsu-vp` (did:web, did:key, did:jwk, TIR client, eIDAS behind a feature, internal JWT); about 6k lines |

Every run stays under 500k tokens. Expected total output about 53k lines of Rust plus tests, matching the 45-60k estimate in T-6633.

## 10. Decisions and owner questions

- Decided (worker-t6637, owner may override): one issuer per installation, organization as the `org` claim and as rows, no realm per organization, because the gateway, Antares and the Portal trust one JWKS today and ADR-N-058 already chose one realm with organization subtrees. Options: realm per organization (Keycloak style), one issuer per organization.
- Decided (worker-t6637, owner may override): fixed login state machines with per-organization policy columns instead of configurable flows, because second-factor and flow bypasses recur in the upstream advisories (section 5.3) and a fixed machine is fully testable.
- Decided (worker-t6637, owner may override): SAML and LDAP in separate adapter workloads (section 5.4).
- Decided (worker-t6637, owner may override): Keycloak's built-in OID4VP broker (`S/broker/oid4vp`) and VCVerifier are both reference behaviour; kaisatsu follows the OpenID conformance verifier plan, so I2's "short internal JWT" is kaisatsu's own token, not a second issuer.
- Decided (worker-t6637, owner may override): password grant, implicit flow, impersonation, UMA, open dynamic registration, account console, front-channel logout, device flow and CIBA are not built.
- Decided (worker-t6637, owner may override): migrated passkeys keep the login host `idm.{domain}`; an organization's custom login domain serves its own new passkeys and offers the platform host for passkeys made before.
- Owner question: per-organization signing keys (each organization its own JWKS) or one installation key set? One key set is assumed.
- Owner question: may an organization's administrator see the audit of failed logins that typed one of its members' e-mails on another organization's host? Assumed no.
- Owner question: keep the password grant for scripted journeys (test-only client) or move every journey to a browser? Assumed browser only.

## 11. MCP mapping

Rule (T-6640 "The whole platform through MCP, strictly separated"): every operation a person can do in the UI is one tool in the Portal ops registry (`POR src/ops`), checked by jc-auth, in a connector segment (`POR src/connectors.rs:50` `SEGMENTS`). Today's identity tools: `jc_person_list`, `jc_person_get`, `jc_person_create`, `jc_person_edit`, `jc_person_disable`, `jc_person_enable`, `jc_person_sign_out` (`POR src/ops/people.rs:369-522`), `jc_member_list`, `jc_access_simulate`, `jc_access_explore` (segment `access`, `POR src/connectors.rs:118-130`), `jc_activity_list`.

| Tool | Input | Output | Permission (jc-auth) | Segment |
|---|---|---|---|---|
| `jc_person_list` (exists) | `org`, `query`, `group`, `cursor` | people (id, display name, enabled, factors present, last seen) | `Person` read in `org` | admin |
| `jc_person_get` (exists) | `id` | person, groups, factors, sessions count | `Person` read | admin |
| `jc_person_create` (exists) | `org`, `email`, `name`, `groups` | id, invitation sent | `Person` create | admin |
| `jc_person_edit`, `jc_person_disable`, `jc_person_enable`, `jc_person_sign_out` (exist) | `id`, fields | status | `Person` update / disable | admin |
| `jc_person_factor_reset` (new; today `remove_second_factor`, `POR src/people.rs:424`) | `id`, `factor` (totp, passkey, all) | removed count | `Person` disable, red lane approval | admin |
| `jc_session_list` (new) | `person` or `client`, `cursor` | sessions (id, client, started, last used, acr) | `Person` read | admin |
| `jc_session_revoke` (new) | `session` | revoked | `Person` disable | admin |
| `jc_consent_list`, `jc_consent_revoke` (new; `POR src/people.rs:451-458`) | `person`, `client` | consents | `Person` read / disable | admin |
| `jc_identity_config_get`, `jc_identity_config_plan` (new) | `org`, `identityDomain`, desired `IdentityConfig` | config, change plan | `IdentityConfig` read / propose (red lane) | access |
| `jc_identity_domain_list` (new) | `org` | login hosts, certificate state | `IdentityConfig` read | access |
| `jc_upstream_idp_plan` (new) | `org`, IdP manifest (`secretRef` only) | change plan | propose, red lane | access |
| `jc_upstream_idp_test` (new) | `org`, `idp` | discovery and metadata check result, no login | `IdentityConfig` read | access |
| `jc_client_list`, `jc_client_get` (new) | `org`, `project` | clients by kind, redirect URIs, scopes | `ServiceAccount` / `App` read | access |
| `jc_credential_offer_create` (new) | `org`, `credentialType`, `subject` | offer URI | `CredentialIssuer` propose | access |
| `jc_trust_list_get` (new) | `org` | trusted issuers, TIR entries | read | access |
| `jc_identity_audit_list` (new, read tool for logs) | `org`, `identityDomain`, `kind` (login, admin, token, credential), `since`, `cursor` | audit rows with ids, outcome, client, no secrets, e-mail shown only for members of `org` | `Person` read in `org` | operate |
| `jc_identity_metrics` (new) | `org`, `window` | logins, failures, lockouts, token mints, quota use | read in `org` | operate |

Read tools filter by the caller's jc-auth decision before paging and counting: `total`, an empty page, "not found" and "forbidden" look the same for another organization's rows. Audit rows carry `org_id` and `identity_domain_id` from write time; a failed login typed on `a`'s host with a `b` member's e-mail is recorded under `a` with the e-mail hashed, never shown to `b`. Every call is audited with the connector id. Isolation tests: the eight of section 6.3 run again through `/c/{id}` with an `a` connector, plus: `jc_identity_audit_list` of `a` never returns a row written by `b`'s login traffic; `jc_person_get` with a `b` id answers like an unknown id; a connector narrowed to segment `access` gets no `admin` tool.

## Related

- [Identity and access](../../Architecture/12-identity-and-access.md): I1-I3 and the organization, group and role model this design keeps.
- [Data space connector](../../Architecture/18-data-space-connector.md): the Decentralized Claims Protocol side kaisatsu issues credentials for.
- [Next platform identity and authorization](../next-platform/03-identity-and-authz.md): the provider scope and the one-issuer decision this page details.
- [ADR-N-058](../../Decisions/adr-n-058-several-organizations-per-installation.md): several organizations in one realm, the starting point for section 6.
- [ADR-N-064](../../Decisions/adr-n-064-scoped-connectors.md): `connector:{id}` scopes and CIMD clients, kept wire-compatible in section 5.1.
