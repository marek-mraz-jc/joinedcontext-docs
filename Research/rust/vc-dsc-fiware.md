---
sidebar_position: 11
title: "Verifiable Credentials and the Data Space Connector, FIWARE-Compatible"
description: Research input for the credentials and connector add-on (VCR-01..VCR-13, DSC-01..DSC-12); the FIWARE Data Space Connector 11.41.3 flows message by message, what the platform answers at each step and the gap, the add-on switch, the slice plan and the interop oracle, every FIWARE claim with its file and line at the pinned release (T-6775).
---

# Verifiable Credentials and the Data Space Connector, FIWARE-Compatible

This page is the research input for the credentials and data space connector add-on: OpenID for Verifiable Credential Issuance (OID4VCI), OpenID for Verifiable Presentations (OID4VP), SD-JWT VC and a Dataspace Protocol (DSP) connector, built in Rust, off by default, and able to talk to a FIWARE Data Space Connector in either role. It walks the FIWARE flows with their exact messages, says per step what the platform answers today and what is missing, defines what "off" means, cuts the work into task-sized slices and names the interop oracle that proves compatibility. Readers: the worker who takes a slice, the reviewer of that slice, the owner deciding section 9. The decision itself is [ADR-N-069](../../Decisions/adr-n-069-credentials-and-connector-as-an-add-on.md); the target requirements are VCR-01..VCR-13 and DSC-01..DSC-12 in `ARCHITECTURE-TARGET.md` §12 and §25.

## 1. Sources and pins

| Short | What | Pin |
|---|---|---|
| `DSC` | github.com/FIWARE/data-space-connector | tag `11.41.3`, commit `b8e73970e82aa416f4ed9ed436a348c391b22543` (2026-11-11), umbrella chart `data-space-connector` 10.15.12 (`DSC charts/data-space-connector/Chart.yaml:5`) |
| `DIAM` | github.com/FIWARE/decentralized-iam | tag `decentralized-iam-2.1.28`, commit `057e7597b3ac521a9a4b253bf2103910c8348403`, the version `DSC charts/data-space-connector/Chart.yaml:7-10` pins; sub-charts `vc-authentication` 1.5.2 and `odrl-authorization` 2.4.3 |
| `VCV` | github.com/FIWARE/VCVerifier | tag `6.27.0`, commit `1e0aaca6d3571b77ffdf55fc583397fe8d9dfa6c`: the appVersion of chart `vcverifier` 4.17.0 inside `vc-authentication` 1.5.2. [keycloak.md](keycloak.md) read 6.31.0; the DSC release ships 6.27.0, so this page cites 6.27.0 |
| `TIL` | github.com/FIWARE/trusted-issuers-list | tag `0.10.0`, commit `46141d42295fb4e27805ce82e5202fa742bbd0e4` (appVersion of chart `trusted-issuers-list` 0.19.1) |
| `PAP` | github.com/SEAMWARE/odrl-pap | tag `1.7.1`, commit `877b56ef78bd06d8ff2aef1937b9d640e8586b85` (appVersion of chart `odrl-pap` 2.10.20) |
| other images | APISIX `3.17.0-ubuntu`, OPA `openpolicyagent/opa:1.11.0` (`odrl-authorization` 2.4.3 `values.yaml:66`), credentials-config-service 3.4.3, Keycloak 26.7.0 (`DSC README.md:247`), fdsc-edc chart 0.7.9 (`DSC charts/data-space-connector/Chart.yaml:44-46`) | as `DSC` |
| `PLT` | joinedcontext-platform | `b1defe6c` (2026-11-11) |
| `JC` | joinedcontext monorepo, branch `jc-portal-1` | `05911dba` (2026-11-11) |

`helm pull --repo https://fiware.github.io/vc-authentication/ vc-authentication --version 1.5.2` and the same for `odrl-authorization` 2.4.3 reproduce the image versions above. The interop oracle (section 8) deploys exactly these pins.

## 2. What the platform has today

| Piece | Where | State |
|---|---|---|
| OID4VCI issuer, OID4VP verifier, SD-JWT VC | `JC crates/kaisatsu/README.md:3` names them | no code: `git grep -i 'vp_token\|credential_offer\|dcql'` in `crates/kaisatsu` finds nothing; T-6633 (kaisatsu) is blocked, T-6637 research done ([keycloak.md §2.4](keycloak.md#24-verifiable-credentials-and-federation)) |
| Policy assignee `did` | `PLT crates/jc-core/src/kinds/policy.rs:512`, `:527` | exists; a grant can name a DID |
| Data space kinds `DataSpaceParticipant`, `DataOffer`, `DataAgreement` | `PLT crates/jc-core/src/kinds/dataspace.rs:153`, `:219`, `:468` (601 lines, T-0120) | manifests and validation exist; nothing serves DSP |
| ODRL import and export of a Policy | `PLT crates/jc-core/src/kinds/policy_odrl.rs:74` (`render`), `:253` (`import`) | an ODRL `Set` in the closed `ngsi-ld:` profile; refuses `Offer` and `Agreement` and every member it cannot map (`:1-10`) |
| Transfer token check | `PLT crates/context-gateway/src/auth/dataspace_token.rs:1-15`; [Architecture/18 §4](../../Architecture/18-data-space-connector.md#4-trust-and-limits) | runs today: a realm token with `agreementId` and `participant`, 15 minutes at most, against a finalized `DataAgreement` |
| Connector process | none | `tasks/later/T-0037` waits for a partner; [ADR-N-016](../../Decisions/adr-n-016-data-space-connector.md) places it behind the Endpoint layer |
| Issuer address | [API/15 §6](../../API/15-addresses-v1.md) | frozen: issuer `https://{canonical-host}/{org}/id`, OID4VCI metadata at `/.well-known/openid-credential-issuer/{org}/id`, connector at `/{org}/dsc/` |

## 3. The FIWARE flows, step by step

### 3.1 Issuance: Keycloak OID4VCI, pre-authorized code

The consumer's Keycloak issues the participant and employee credentials. Keycloak 26.7.0 follows OID4VCI Draft 15 (`DSC README.md:247-252`); roles go into `credentialSubject.roles[*]` through `oid4vc-target-role-mapper`. The local deployment fetches a credential with `DSC doc/scripts/get_credential.sh`:

1. `POST {kc}/realms/test-realm/protocol/openid-connect/token` with `grant_type=password`, `client_id=account-console`: a user token.
2. `GET {kc}/realms/test-realm/protocol/oid4vc/create-credential-offer?credential_configuration_id={id}&pre_authorized=true` with that bearer: answers `{issuer, nonce}`; the script builds the offer URI `{issuer}/{nonce}`.
3. `GET {offer_uri}`: the credential offer; the script reads `grants."urn:ietf:params:oauth:grant-type:pre-authorized_code"."pre-authorized_code"`.
4. `POST .../openid-connect/token` with `grant_type=urn:ietf:params:oauth:grant-type:pre-authorized_code&pre-authorized_code=...`: answers `access_token` and `authorization_details[].credential_identifiers`.
5. `POST .../protocol/oid4vc/credential` with `{"credential_identifier": ...}` (or `credential_configuration_id`): answers `credentials[0].credential`.

The request in step 5 carries no `proof`. The reference configurations set `binding_required: "false"` on every credential (`DSC k3s/consumer.yaml:168`, `k3s/provider.yaml:1182`, `k3s/consumer-eidas.yaml:289`), formats `dc+sd-jwt` and `jwt_vc_json` (`DSC k3s/consumer.yaml:156`, `:216`). A FIWARE credential is therefore usually not key-bound: whoever holds the string can present it, unless the verifier checks that the presentation's signer is `credentialSubject.id`.

### 3.2 Human sign-in by OID4VP (H2M, cross-device)

`DSC README.md:277-307` lists 19 steps; the messages are:

1. The relying party's backend redirects the browser to the verifier start page with `client_id`, `state`, `nonce`, `scope`, `response_type` (step 2).
2. The verifier page shows a QR code holding `client_id` and `request_uri` and polls a status endpoint (steps 3-4); routes `/api/v2/loginQR`, `/api/v1/request/:id`, `/ws` (`VCV openapi/routers.go:135`, `:114`, `:148`).
3. The wallet fetches the request object at `request_uri`. The verifier reads the credentials config for `client_id` and `scope` (step 7) and signs a request object with `response_type=vp_token`, `response_mode=direct_post`, `client_id`, `response_uri`, `state`, `nonce` and `dcql_query` (step 8; `VCV verifier/verifier.go:1858-1883`).
4. The wallet posts `vp_token` (and a SIOPv2 `id_token` where asked) to `response_uri` by `direct_post` (step 10; `VCV openapi/routers.go:86`, handler `openapi/api_api.go:558`).
5. The verifier checks signature, holder binding, validity, revocation, the requested claims and both trust lists (step 11), then mints its own JWT and an authorization code (step 12).
6. The page redirects to the relying party's callback with `code` and `state`; the backend calls `POST /token` with `grant_type=authorization_code` (steps 13-15; `VCV openapi/api_api.go:112-139`). The JWT carries the presented credential under `verifiableCredential` (one) or `verifiablePresentation` (several) (`VCV verifier/verifier.go:1800-1818`).

### 3.3 Machine to machine: `vp_token` grant and token exchange

`DSC doc/flows/service-interaction-m2m/README.md:13-127` (client) and `:128-197` (server):

1. `GET https://{service-host}/.well-known/openid-configuration` answers at least `{"grant_types_supported": ["vp_token"], "token_endpoint": ...}` (`:24-38`). VCVerifier serves it per service at `/services/{service_id}/.well-known/openid-configuration` (`VCV api/api.yaml:217`); its metadata lists `authorization_code`, `vp_token` and token exchange (`VCV verifier/verifier.go:1141`).
2. The client signs a VP JWT: header `{"typ":"JWT","alg":"ES256","kid":"{holder did}#{key}"}`, payload `iss` = `sub` = holder DID, `vp.verifiableCredential` = [credential] (`:44-84`).
3. `POST {token_endpoint}` form `grant_type=vp_token&vp_token={jwt}&presentation_submission=&scope={scope}` (`:88-96`). Answer `{"access_token", "token_type": "Bearer", "expires_in", "scope", "id_token"}` (`:104-112`).
4. VCVerifier also takes RFC 8693: `grant_type=urn:ietf:params:oauth:grant-type:token-exchange`, `subject_token_type=urn:eu:oidf:vp_token`, `subject_token={vp}`, optional `requested_token_type=urn:ietf:params:oauth:token-type:access_token`, `audience`, `scope`; on `/token` it also needs `resource` (`VCV openapi/api_api.go:128-133`, `:281-309`; `common/metadata.go:5-6`; `api/api.yaml:662-704`).
5. Server checks, in order (`:174-190`): credential types match the scope, signature by DID method, issuer is a trusted participant (EBSI TIR `GET /v4/issuers/{did}` at the data space's registry), issuer is trusted for that credential type in the provider's local list, then the access token.

The local deployment's own client, `DSC doc/scripts/get_access_token_oid4vp.sh:2-50`, signs a VP JWT with only `iss`, `sub` and `vp`: no `aud`, no `nonce`, no `iat`, no `exp`.

Connector to connector, the DSP control plane uses the OID4VP form with a server nonce: `GET /.well-known/openid-configuration`, then the authorization endpoint, which answers a request with a DCQL query, then the signed `vp_token` to the token endpoint (`DSC doc/DSP_INTEGRATION.md:23-40`; `VCV openapi/routers.go:72`, handler `openapi/api_api.go:141`).

### 3.4 Authorization at the provider: APISIX, OPA, odrl-pap

`DSC README.md:330-369`: APISIX verifies the JWT and calls OPA (sidecar, `opa:1.11.0`) with the token, method, path and body; OPA evaluates ODRL policies that odrl-pap compiled to Rego. A policy is an `odrl:Policy` posted to `POST {pap}/policy` (`DSC doc/scripts/prepare-dsp-policies.sh:4-6`). Example `DSC it/src/test/resources/policies/uptimeReport.json`: permission with `odrl:assigner`, `odrl:target` an `odrl:AssetCollection` refined by `ngsi-ld:entityType eq UptimeReport`, `odrl:assignee` `vc:any`, `odrl:action` `odrl:read`.

The vocabulary odrl-pap 1.7.1 accepts is its `PAP src/main/resources/mapping.json`:

| Member | Accepted terms |
|---|---|
| action (`:2`) | `odrl:` read, use, modify, delete; `dspace:` read, use; `ngsild:` create; `tmf:` create; `dome-op:` read, create, modify, write; `json:` read, use, create, write, delete |
| leftOperand (`:217`) | `http:` path, bodyValue; `vc:` role, type, currentParty; `ngsi-ld:` entityType, entityTypeGroup; `odrl:` dateTime, dayOfWeek, hourOfDay; `dspace:` membershipType, participant, scope; `tmf:` lifecycleStatus, resource; `dome-op:` 7 terms; `json:` payloadType, payloadValue, subjectValue |
| operator (`:101`) | `odrl:` eq, neq, lt, lteq, gt, gteq, isAnyOf, isAllOf, isNoneOf, isPartOf, hasPart, anyOf, regex; `http:isInPath` |
| assignee (`:367`) | `odrl:assignee`, `vc:any`, `json:any`, `json:assignee` |
| target (`:395`) | `odrl:target`, `odrl:uid`, `json:` target, uid, payloadTarget |
| constraint (`:426`) | `ovc:constraint`, `ovc:credentialSubjectType` |

### 3.5 Onboarding into the trusted issuers list

Two lists, two roles (`DSC doc/deployment-integration/roles/operator/README.md:1-40`):

- The **trust anchor** (data space operator) runs the Trusted Issuers Registry: read `GET /v4/issuers` and `GET /v4/issuers/{did}` (`TIL api/trusted-issuers-registry.yaml:11`, `:33`), public; write `POST /issuer` (`TIL api/trusted-issuers-list.yaml:10-60`), which "must be strictly restricted" (`operator/README.md:306-307`). Onboarding: the operator checks the organization out of band, registers its DID, names the credential types it may issue, hands over the TIR address (`:13-20`). Local example: `POST {til}/issuer` with `{"did": "did:key:myKey", "credentials": []}` against the anchor's local host (`DSC doc/deployment-integration/local-deployment/LOCAL.MD:82-87`).
- Each **provider** runs a local trusted issuers list of the same API that says which issuer may issue which credential type with which claim values: `TrustedIssuer {did, credentials[]}`, `Credentials {validFor, credentialsType, claims[]}`, `Claim {name, path, allowedValues}` (`TIL api/trusted-issuers-list.yaml:283-323`). Both VCVerifier and the EDC control plane read it (`DSC doc/DSP_INTEGRATION.md:313-319`). `contract-management` adds the buyer's DID there when a TMForum ProductOrder completes, tagged with a `scope` so the grant can be revoked alone (`DSC README.md:392-402`; `TIL api/trusted-issuers-list.yaml:206-228`).

VCVerifier reads both through one client: `IsTrustedParticipant` for the registry, `GetTrustedIssuer` for the list, v4 and v5 paths (`VCV tir/tirClient.go:19`, `:163`, `:171`, `:350`). It asks at request time; the answer the network gives is the trust decision.

### 3.6 Offer, negotiation, agreement, transfer

The DSP control plane is fdsc-edc, Dataspace Protocol `2025-1` (`dataspace-protocol-http:2025-1`), with TMForum as its store (`DSC README.md:405-498`, `doc/DSP_INTEGRATION.md:5-21`):

1. **Catalogue.** `dcat:Catalog` maps to a TMForum Catalog, `dcat:Dataset` to a ProductSpecification, the ODRL `Offer` to a ProductOffering (`DSC README.md:439-453`).
2. **Negotiation.** The consumer sends a Contract Request Message with the dataset and an ODRL `Offer`; the provider ACKs, may counter-offer, sends a Contract Agreement Message; the consumer verifies; the provider finalizes (`DSC README.md:455-477`). States map to a TMForum Quote and, at VERIFIED, a ProductOrder (`DSC doc/CONTRACT_NEGOTIATION.md:9-35`). The offer in the example constrains `odrl:dayOfWeek lt 6` and `dspace:membershipType eq FullMember` (`DSC doc/DSP_INTEGRATION.md:996-1028`).
3. **Transfer.** Transfer Request Message with `contractAgreementId`, ACK, Transfer Start with the data address, completion or termination (`DSC README.md:479-498`). FIWARE has no separate data plane: on start it creates APISIX routes per transfer. With OID4VP: access policies into the PAP, a credentials config, a route `{transferProcessId}/.well-known/openid-configuration` and a route `{transferProcessId}/` to the data service, and returns that address. With DCP: the route plus a JWT with the transfer id as scope, signed by the control plane key (`DSC doc/DSP_INTEGRATION.md:60-81`).
4. **DCP authentication** (when the counterparty is plain EDC): self-issued ID token plus access token from the consumer's identity hub, provider resolves the DID document, fetches a presentation from the consumer's credential service with that token, checks issuers on the local list (`DSC README.md:422-437`, `doc/DSP_INTEGRATION.md:45-58`).

The data service in the demo is NGSI-LD: Scorpio at `/ngsi-ld/v1/entities` (`DSC doc/DSP_INTEGRATION.md:321-341`).

## 4. Per step: what the platform answers, and the gap

| FIWARE step | Platform answer | Gap today |
|---|---|---|
| 3.1 OID4VCI pre-authorized code issuance | kaisatsu issuer per Organization at `/{org}/id` (VCR-01..VCR-03); claims from records it holds, never the request body | no issuer; Keycloak 26.8.1 has the preview `OID4VC_VCI` ([keycloak.md §2.4](keycloak.md#24-verifiable-credentials-and-federation)), not enabled |
| 3.1 credential without holder binding | our issuer always binds (`cnf`, proof required); our verifier accepts an unbound `jwt_vc_json` only where its `TrustedIssuer` row says `holderBinding: subjectDid` and the VP JWT's signer DID equals `credentialSubject.id`; an SD-JWT VC without `cnf` and a KB-JWT is refused, since nothing ties it to a presenter | the `TrustedIssuer` kind does not exist |
| 3.2 H2M OID4VP with DCQL, `direct_post`, code to token | kaisatsu verifier at `/{org}/id/vp/`, request object signed, nonce single-use (VCR-04, VCR-09); the result is the normal 5-minute access token with `amr: vp` (VCR-06) | no verifier; no token issuer besides Keycloak |
| 3.3 `.well-known/openid-configuration` per service | `{endpoint base}/.well-known/openid-configuration` naming the verifier's token endpoint for that Endpoint | Endpoints publish RFC 9728 metadata only ([API/15](../../API/15-addresses-v1.md)) |
| 3.3 `grant_type=vp_token` and RFC 8693 `urn:eu:oidf:vp_token` | both grants, same checks; a VP without a server nonce must carry `aud` = this verifier, `iat` within 60 s and a `jti`, and the `jti` is accepted once: seen ids live in Postgres, shared by every replica, for the window plus 30 s of skew (section 5, F1; section 9, D2) | none of it exists |
| 3.3 trusted participant + trusted issuer | one check: the issuer DID has a `TrustedIssuer` row in this Organization for that credential type, with the claim constraints (VCR-05) | no rows, no kind |
| 3.4 APISIX + OPA + odrl-pap | the gateway's PDP and Antares views decide (ADR-N-050, ADR-N-057); no OPA. An ODRL policy from or for a FIWARE peer goes through a second, closed ODRL dialect (`fiware-pap`) next to `ngsi-ld:` | `policy_odrl.rs` speaks only our profile and refuses `Offer`/`Agreement` |
| 3.5 TIR read and TIL write | a TIR read client that proposes `TrustedIssuer` changes from a configured registry; additions go through a Change, removals apply as narrowing (section 9, D3). Our own Organization appears in the peer's TIR by the operator's onboarding, out of band | no client; no published DID document for `/{org}/dsc/` |
| 3.6 DSP catalogue | `/{org}/dsc/` serves `dcat:Catalog` of `DataOffer`s, each an Endpoint plus ODRL (DSC-01, DSC-03, DS-08) | kinds exist, no server |
| 3.6 negotiation | state machine persisted per Organization, idempotent per message id (DSC-05); green lane when the request equals the offer (DS-09) | none |
| 3.6 agreement | compiles to a Policy with assignee `agreement` (DSC-04), bound to the consumer's DID (DS-10), inside the Endpoint's ceiling (DS-03) | the mapper from ODRL `Agreement` is missing; `import` refuses it |
| 3.6 transfer with OID4VP route | the Endpoint is the data plane (DSC-09): Transfer Start returns the Endpoint address and its `/.well-known/openid-configuration`; the FIWARE consumer then runs 3.3 against our verifier with `scope` = the agreement id | the gateway checks a realm token with `agreementId` (section 2); a token minted by our verifier must carry the same two claims |
| 3.6 transfer with DCP JWT | transfer token signed by the platform issuer, audience the Endpoint, `agreementId` and `participant` (DS-11); the gateway check runs unchanged | the issuing side is missing |
| 3.6 DCP | the connector presents our Organization's credentials from kaisatsu and verifies the peer's through the same verifier (VCR-10, DSC-08) | none |
| NGSI-LD data service | Endpoint NGSI-LD surface, which a FIWARE consumer reads as it reads Scorpio | exists |

## 5. FIWARE behaviour the design does not copy

| # | Finding at the pin | Impact | Our rule |
|---|---|---|---|
| F1 | On `grant_type=vp_token` and token exchange there is no server nonce; VCVerifier binds and ages only JSON-LD VPs (`VCV verifier/verifier.go:879-894`). A grep of `verifier/`, `common/` and `openapi/` finds no `aud` or `iat` check on a JWT VP, and FIWARE's own client sends neither (`DSC doc/scripts/get_access_token_oid4vp.sh:17`) | a captured VP JWT is replayable at the token endpoint until its credential expires | a VP without `aud` = this verifier, without `iat` inside 60 s, or with a `jti` already seen is refused (VCR-04). FIWARE's script fails against us by design; fdsc-edc's authorization-endpoint path (nonce from the server) passes. The interop run records which FIWARE clients send `aud`/`iat` |
| F2 | Reference credentials are issued with `binding_required: "false"` (section 3.1) | a bearer credential: theft equals impersonation | bound by default; unbound only per `TrustedIssuer` row with `holderBinding: subjectDid`, never for a human sign-in step-up |
| F3 | `verifiyVPToken` receives the form's `audience` and passes `clientId` to `GenerateToken` anyway (`VCV openapi/api_api.go:295-299`, `:340`) | the token's audience is the service, whatever the caller asked | the token's audience is the Endpoint the request names (RFC 8707); an unknown `resource` or `audience` is `invalid_target` |
| F4 | Trust comes from a live TIR/TIL answer at request time (`VCV tir/tirClient.go:163-201`) | a registry outage or a spoofed answer decides trust; answers are cached (`tirCache`, `VCV tir/tirClient.go:171-193`), so a removal also lags | trust comes only from `TrustedIssuer` rows; a registry only proposes rows (VCR-05, the task's security line) |
| F6 | The `vp_token` grant logs the whole presentation at warn level (`VCV openapi/api_api.go:320`, `Warnf("Got token %s", vpToken)`); token exchange logs it at debug (`:306`), and both token handlers log the whole request at debug (`:114`, `:259`) | every M2M presentation, personal data included, lands in the default logs | no log line at any level carries a VP, a credential or a token; S3a tests at debug level |
| F5 | The TIL write API `POST /issuer` has no authentication in its OpenAPI (`TIL api/trusted-issuers-list.yaml:10-60`); the operator guide asks to restrict it at the network (`operator/README.md:307`) | an exposed TIL lets anyone become a trusted issuer | we never run a TIL; our list changes only through a Change with its approval lane |

## 6. The add-on switch (VCR-12)

Two levels, both off by default:

- **Deployment setting.** Helm values `addons.credentials.enabled` and `addons.dataspace.enabled` (the latter requires the former), read once at start into the binary's config. Off: the module's routes are not mounted, its jobs are not scheduled, its migrations are not applied, it creates no key.
- **Per Organization.** `OrganizationSettings.addons.credentials` and `.dataspace` (booleans, default false), changed only by a Change with steward approval. An Organization that has not turned it on answers as if the module were off, even when the deployment has it on.

| Area | Off means |
|---|---|
| Routes | `/{org}/id/vp/*`, `/{org}/id/credential*`, `/.well-known/openid-credential-issuer/{org}/id`, `/{org}/dsc/*`, `{endpoint}/.well-known/openid-configuration` answer 404 from the router (not mounted, RTE-16), never 403; the 404 body is the platform's plain not-found, so a scan cannot tell "off" from "never existed". `/.well-known/dspace-version` is not mounted when the deployment is off and lists only Organizations that turned the connector on |
| Keys | no issuer key, no connector signing key, no DID document. Turning an Organization on generates its keys in that Change's apply; turning it off deletes them in the same apply, so every credential and token they signed stops verifying at once, and no status list stays served |
| Jobs | no TIR sync, no status-list publisher, no negotiation retry worker |
| Migrations | the `vc` and `dsc` tables live in their own migration sets, applied when the deployment setting first turns on; a fresh install with the add-on off has none of them and starts |
| Tokens | without the add-on no token carries `amr: vp`; jc-auth refuses `amr: vp` from an Organization whose setting is off (a token minted before switching off dies within 5 minutes) |
| Policies | a Policy may name `did` assignees with the add-on off (they exist today); nothing matches them until a verifier or transfer token asserts a DID |
| UI and MCP | Portal pages and MCP tools of the add-on are not listed; a deep link shows the not-found page |
| Tests | the whole suite runs with the add-on off (the default) and stays green; an `addon_off` test per module asserts 404 on every route above, no key row, no job and no table; the add-on suite runs with it on in its own CI job |

## 7. Slices

Each row is one task. "First for FIWARE" marks the path a FIWARE connector needs: FIWARE as consumer reading our Endpoint needs S0, S1a, S1b, S2, S3a, S3b, S5, S6, S8, S9, S10; FIWARE as provider also needs S4, S11 and S7.

| # | Slice | Depends on | Done when | Tests | First for FIWARE |
|---|---|---|---|---|---|
| S0 | Add-on switch: deployment values, `OrganizationSettings.addons`, router gate, migration sets | none | both levels exist; off is the default; section 6 holds | `addon_off` per route, key, job, table; a Change toggling one Organization leaves another unchanged; `dspace-version` lists only Organizations that are on | yes |
| S1a | `jc-vc` formats: SD-JWT VC (with KB-JWT) and `jwt_vc_json` verification, ES256 and EdDSA only | S0 | a pure library verifies FIWARE's two formats | vectors from the specs plus one credential of each format issued by FIWARE's Keycloak 26.7.0 (captured by the oracle); `alg: none`, HS256, expired, wrong `vct`, SD-JWT without `cnf` refused | yes |
| S1b | `jc-vc` DID resolution: `did:web` (allow-listed fetch, timeout, size cap), `did:key`, `did:jwk` | S1a | holder and issuer keys resolve | redirect off-host, oversized document, unknown method refused | yes |
| S1c | `jc-vc` Token Status List (read and publish) | S1a | a revoked credential is refused within the list lifetime (VCR-07) | revoked, suspended, list unreachable (refuse), list signed by another key | no |
| S2 | `TrustedIssuer` kind and trust check | S1a | kind with issuer DID, credential types, claim constraints (`path`, `allowedValues`, as `TIL Claim`), `holderBinding`, `acceptNoncelessVp`, expiry; lands by Change | issuer without a row refused; Organization A's row does not trust for B (VCR-11); claim value outside `allowedValues` refused | yes |
| S3a | Verifier: `vp_token` grant and RFC 8693 `urn:eu:oidf:vp_token`, claim mapping, store mapped claims, issuer and credential hash (VCR-08) | S1b, S2 | a verified VP yields a subject with mapped claims and `participant` = holder DID | missing `jti`, replayed `jti` across two replicas, missing `aud`, stale `iat`, unbound credential without the row flag, unknown `resource`; no VP in logs at debug level | yes |
| S3b | Token for a verified subject (D1) and per-Endpoint `/.well-known/openid-configuration` | S3a | a FIWARE client gets a 5-minute token with `amr: vp` that the gateway accepts | an unknown DID cannot create a persistent Keycloak user; the token carries `agreementId` only when the scope names a finalized agreement | yes |
| S4 | EBSI TIR read client: v4 and v5 `GET /issuers/{did}` and attributes | S2 | a configured registry (allow-listed host, timeout, size cap) yields proposed `TrustedIssuer` Changes; a removal needs an explicit answer (404 for that DID after a 200 list), never an outage | recorded TIR answers from the oracle's anchor; outage keeps rows; malformed base64, oversized page, off-host redirect refused | yes (provider) |
| S5 | ODRL dialect `fiware-pap`: import and export of the `PAP mapping.json` subset that maps exactly onto a Policy | none | `odrl:Policy` with `ngsi-ld:entityType` refinement, `vc:role`, `vc:type`, `dspace:participant`, `odrl:dateTime` maps both ways; every other term refused naming the member | round trip of each `DSC it/src/test/resources/policies/*.json` that maps; `http:path`, `tmf:*`, `dome-op:*`, `json:*`, `ovc:*` refused | yes |
| S6 | DSP catalogue at `/{org}/dsc/`, `/.well-known/dspace-version`, the DID document `did:web:{host}:{org}:dsc` and per-Organization participant keys (DSC-01, DSC-02, DSC-11) | S0, S5 | `CatalogRequestMessage` answers a `dcat:Catalog` of the Organization's `DataOffer`s that the caller may see | DSP TCK catalogue cases; non-member sees public offers only; another Organization's offers and keys never served | yes |
| S7 | DSP consumer client with OID4VP to the peer; the agreement becomes a `Registration` by Change (DSC-10) | S3a, S11 | our connector negotiates with FIWARE as provider and stores a `DataAgreement` with `role: consumer` | oracle scenario "FIWARE provider" | yes (provider) |
| S8 | Negotiation state machine (provider) | S3b, S6 | Contract Request, Offer, Agreement, Verification, Finalized, Terminated persisted per Organization, idempotent per message id, resumable | DSP TCK negotiation cases; duplicate message id; callback to a host outside the peer's DID document refused | yes |
| S9 | Agreement to Policy (ODRL `Agreement` import) | S5, S8 | a finalized agreement becomes a Policy with assignee `agreement` bound to the consumer DID, inside the Endpoint's ceiling (DS-03, DSC-04) | agreement wider than the offer refused before finalization; end of agreement revokes the Policy (DS-12) | yes |
| S10 | Transfer: Transfer Start with the Endpoint address and its OID4VP metadata, or a DCP transfer token | S3b, S9 | the FIWARE consumer reads NGSI-LD through the Endpoint under the agreement | oracle scenario "FIWARE consumer"; a token for agreement A refused on agreement B's Endpoint | yes |
| S11 | OID4VCI issuer (authorization code; pre-authorized code with transaction code), membership and employee credentials | kaisatsu T-6633, S1a | a FIWARE VCVerifier accepts our credential | OpenID conformance OID4VCI issuer plan; oracle provider scenario | yes (provider) |
| S12 | H2M OID4VP sign-in (same-device and cross-device, DCQL) | S3b | a person signs in with a wallet; the consent page names the Organization, verifier and claims (VCR-09) | OpenID conformance OID4VP verifier plan; two independent wallets (VCR-11); cross-device never satisfies step-up | no |
| S13 | DCP (identity hub role and DCP verification) | S1a, S11 | a plain EDC peer negotiates with us | oracle DCP scenario | no |
| S14 | Agreement obligations the Policy cannot express: recorded, shown, acknowledged before finalization (DSC-12) | S8 | a duty such as "delete after a date" is listed on the agreement and needs a person's acknowledgement | finalization without acknowledgement refused; refusal of onward sharing enforced | no |

## 8. The interop oracle

**FIWARE as counterparty.** A job (`interop-fiware.yml` in joinedcontext-conformance; `workflow_dispatch` while that private repository's Actions minutes are metered, nightly once they are restored, and on a runner with at least 16 GB, a self-hosted one if the hosted private runner is smaller) creates a kind cluster on the runner and deploys, from the pins in section 1, a trust anchor and one FIWARE participant, rendered with `helm template` and applied with `kubectl`, the path FIWARE's own CI also runs (`DSC doc/adr/0007-test-both-deployment-paths.md`), including its post-render step (`DSC k3s/ci-post-render.sh`). FIWARE's local deployment needs Maven and a JDK 17 to drive k3s (`DSC doc/deployment-integration/local-deployment/LOCAL.MD:13-17`, `README.md:566-579`); the oracle replaces that driver with kind and the rendered manifests. FIWARE suggests 16 GB, better more than 24 GB, for two participants plus the anchor (`LOCAL.MD:11`); the oracle runs one participant, and its first run measures the real peak. Our side is the jc image of the commit under test with the add-on on, in the same cluster.

| Scenario | FIWARE role | Steps | Proves |
|---|---|---|---|
| consumer M2M | consumer | FIWARE Keycloak issues a `jwt_vc_json` and a `dc+sd-jwt` credential (3.1); its client runs 3.3 against an Endpoint of ours; reads entities | S1, S2, S3; F1 recorded per client |
| consumer DSP | consumer (fdsc-edc OID4VC flavour) | catalogue, negotiation, agreement, transfer against `/{org}/dsc/`; reads through the Endpoint | S5, S6, S8, S9, S10 |
| provider DSP | provider | our S7 client negotiates for `ASSET-1` (`DSC doc/DSP_INTEGRATION.md:996-1028`), presents our credential to VCVerifier, reads Scorpio | S7, S11 |
| trust anchor | operator | registry lists our DID after `POST /issuer` on the anchor's TIL; S4 imports the FIWARE participant | S4 |
| refusal | either | credential from an issuer with no `TrustedIssuer` row; replayed VP; agreement for another Endpoint | the security line of T-6775 |

The job runs while any deployment has the add-on on (VCR-13), and the platform's ci dispatches it for a branch that touches `jc-vc` or `dsc`; it captures the FIWARE-issued credentials as test vectors for S1.

**OpenID conformance suite.** The OpenID Foundation's conformance suite, its container image pinned by digest, runs the OID4VP verifier test plan (`oid4vp-1final-verifier-test-plan`, the plan Keycloak's own tests use, [keycloak.md §2.4](keycloak.md#24-verifiable-credentials-and-federation)) against S12 and the OID4VCI 1.0 issuer test plan against S11, both nightly (VCR-11). Two independent wallets (the Lissi and EUDI reference wallets FIWARE tested, `DSC README.md:254-275`) run the S12 sign-in by hand once per release until a scripted wallet exists.

**DSP TCK.** The Eclipse Dataspace TCK runs against S6 and S8 (DSC-06).

## 9. Decisions and open questions

- **D1** Decided (worker-t6775, owner may override): until kaisatsu (T-6633) issues tokens, the verifier hands a verified subject to Keycloak by the RFC 7523 JWT authorization grant (`JWT_AUTHORIZATION_GRANT`, default in Keycloak 26.8.1, [keycloak.md §2.1](keycloak.md#21-protocols-and-grants)), so jc-auth keeps one trust root. The one new trust edge is Keycloak's identity provider entry holding the verifier's assertion key; users it creates for a holder DID are transient (no stored account), and S3b tests that an unknown DID leaves no persistent user. Options: the verifier signs its own tokens (a second trust root in jc-auth, rejected), or S3 waits for T-6633 (the FIWARE path waits with it). S3's first test proves the grant on Keycloak 26.8.1 for a holder DID with no pre-created user; if it cannot, S3 is `merge-after` T-6633.
- **D2** Decided: the server-nonce flow is the default; a nonce-less VP (F1) is accepted only for an issuer whose `TrustedIssuer` row sets `acceptNoncelessVp`, and then only with `aud`, `iat` within 60 s and an unseen `jti`. This deviates from VCR-04 ("single-use nonce"); the owner amends VCR-04 or drops the row flag, and the FIWARE M2M path then needs the authorization-endpoint flow. Options: options: accept FIWARE's bare VP for compatibility (replayable, rejected), require the authorization-endpoint nonce flow only (breaks the documented M2M flow even for well-formed clients).
- **D3** Decided: a registry (TIR) proposes; additions to `TrustedIssuer` need the Change's approval, a removal the registry reports explicitly (never an outage) applies at once as narrowing; options: live lookup like FIWARE (F4, rejected), manual only (a revoked issuer stays trusted until someone notices).
- **D4** Decided: FIWARE's ODRL vocabulary is a second closed dialect beside `ngsi-ld:` (S5), not a widening of our profile; a member that does not map is refused, as `policy_odrl.rs` does today.
- **D5** Decided: no OPA, no APISIX OPA plugin, no TMForum: the gateway's PDP stays the one decision point ([ADR-N-016](../../Decisions/adr-n-016-data-space-connector.md) already left TMForum out).
- **Requirement changes this page proposes** (contract first, before S2 and S3a land): VCR-04 gains the nonce-less exception of D2, VCR-05 gains `holderBinding` and `acceptNoncelessVp`. Section 3.6 names the DSP messages; their fields (`consumerPid`, `providerPid`, `callbackAddress`, `agreementId`, `dataAddress`) are those of DSP 2025-1, which S6 and S8 pin with the TCK.
- **Open for the owner:** whether a data space trust anchor of our own (an Organization acting as operator, serving the TIR read API) is wanted. Nothing in S0..S14 needs it; it is one more slice when a data space asks.

## Related

- [ADR-N-069](../../Decisions/adr-n-069-credentials-and-connector-as-an-add-on.md) records the add-on decision this page feeds.
- [Keycloak and VCVerifier for kaisatsu](keycloak.md) covers the issuer and token side that S3, S11 and S12 build on.
- [Architecture/18](../../Architecture/18-data-space-connector.md) describes where the connector sits and the transfer-token check that runs today.
- [Requirements/data-space.md](../../Requirements/data-space.md) holds DS-01..DS-20, the accepted connector requirements.
- [API/15 Addresses v1](../../API/15-addresses-v1.md) fixes the `/{org}/id` and `/{org}/dsc/` addresses the slices serve.
