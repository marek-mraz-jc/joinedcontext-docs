---
sidebar_position: 70
title: "ADR-N-069: Credentials and Connector as an Add-on"
---

# ADR-N-069: Credentials and Connector as an Add-on

Date: 2026-11-11  
Status: Proposed  
Decision Makers: product owner (owner 2026-11-11, supervisor session: "is there already an implementation OIDC for verifiable credentials with a data space connector? look for the workflow in the FIWARE data space connector ... I need to also implement here, as an add-on, not something mandatory"); drafted by worker-t6775 (T-6775), owner may override

This record decides how the platform gains verifiable credentials (OID4VCI, OID4VP, SD-JWT VC) and a Dataspace Protocol connector: as one optional add-on, off by default, written in Rust, compatible with the FIWARE Data Space Connector without running any of its components. It refines [ADR-N-016](adr-n-016-data-space-connector.md), which placed the connector behind the Endpoint layer and left the engine open. The research behind it, with every FIWARE flow and the slice plan, is [Research/rust/vc-dsc-fiware.md](../Research/rust/vc-dsc-fiware.md).

## 1. Context

- **Nothing exists yet.** The kaisatsu identity server names OID4VCI, OID4VP and SD-JWT VC and has no code for them (T-6633 blocked). No connector serves DSP; the `DataSpaceParticipant`, `DataOffer` and `DataAgreement` kinds and the gateway's transfer-token check do exist (platform `jc-core/src/kinds/dataspace.rs`, `context-gateway/src/auth/dataspace_token.rs`).
- **Most Organizations need neither.** A city publishing open data and running dashboards signs in with OIDC and shares through Endpoints. Credentials and contracts matter when a data space partner appears.
- **FIWARE is the counterparty we will meet first.** Its connector (release 11.41.3) combines VCVerifier, a trusted issuers list with the EBSI registry API, APISIX with OPA and odrl-pap, Keycloak as OID4VCI issuer, TMForum and fdsc-edc for DSP. Several of its defaults are weaker than our rules: a nonce-less presentation is replayable at its token endpoint, its reference credentials carry no holder binding, and trust comes from a registry answer at request time (research §5).

## 2. Decision

1. **One add-on, two switches.** Credentials (`vc`) and the connector (`dsc`, which needs `vc`) are off by default. A deployment setting turns a module on for the installation; each Organization then turns it on for itself by a Change. Off means: no route mounted (404, not 403), no key, no job, no table, no token with `amr: vp`. Sign-in, Policies and Endpoints never depend on the add-on, and the full suite passes with it off (VCR-12).
2. **Rust inside the platform, no FIWARE component.** The verifier, issuer and connector are platform modules (`jc-vc`, `dsc`); no VCVerifier, OPA, odrl-pap, TMForum or EDC process runs. The gateway's PDP stays the one decision point; the Endpoint stays the one data plane (DSC-07, DSC-09).
3. **Compatibility at the wire.** We answer a FIWARE peer the way its components do: per-Endpoint `/.well-known/openid-configuration`, the `vp_token` grant and RFC 8693 exchange with `urn:eu:oidf:vp_token`, `jwt_vc_json` and `dc+sd-jwt` credentials, the EBSI TIR read API as a source of trust proposals, odrl-pap's ODRL vocabulary as a closed import and export dialect, DSP 2025-1, and DCP for plain EDC peers (VCR-13).
4. **Our rules win where FIWARE is weaker.** A presentation answers a server nonce; only an issuer whose `TrustedIssuer` row allows it may present without one, and then the VP names this verifier as `aud` and carries a fresh `iat` and an unseen `jti` (a proposed amendment of VCR-04). A `jwt_vc_json` without holder binding is accepted only where its row allows binding by subject DID; an unbound SD-JWT VC never. Trust comes only from `TrustedIssuer` rows; a registry proposes rows, a Change adds them, and a removal the registry reports narrows at once. Raw presentations are never logged.
5. **One token issuer.** Whatever the verifier accepts becomes the platform's normal short access token. Until kaisatsu issues tokens, the verifier obtains it from Keycloak by the RFC 7523 JWT authorization grant; jc-auth gains no second trust root, and Keycloak's one new trust edge is the verifier's assertion key.
6. **Proof by an oracle.** A nightly job deploys FIWARE's connector at a pinned release in kind as our counterparty in both roles, and the OpenID conformance plans for OID4VP and OID4VCI run against our verifier and issuer.

## 3. Alternatives considered

- **Deploy the FIWARE connector beside the platform.** Fastest interop, but a second identity stack, a second policy engine (OPA), a JVM and a second database per Organization, and FIWARE's weaker defaults (research §5) inherited; rejected by DSC-07 and VCR-06.
- **Credentials always on.** Every installation would carry keys, routes and jobs nobody uses, each a surface to secure; rejected by the owner's "add-on, not mandatory".
- **Our own ODRL profile only.** Simpler, but a FIWARE provider's policies could not be read or written; rejected for a second closed dialect that refuses what it cannot map.
- **Live registry lookup like VCVerifier.** No sync job, but trust would follow a network answer; rejected.

## 4. Consequences

- A FIWARE client that sends a VP without `aud` and `iat` (FIWARE's own demo script does) is refused; fdsc-edc's nonce flow passes. The interop run records which clients send what, and the refusal names the missing claim.
- The slices S0..S14 of the research page become tasks; S0 (the switch) lands first, and the FIWARE consumer path (S1a, S1b, S2, S3a, S3b, S5, S6, S8, S9, S10) before the issuer and H2M sign-in.
- `Requirements/data-space.md` DS-04 (credentials issued by Keycloak) and DS-06 (engine selectable) change when S7 lands: the engine is ours, and the issuer is kaisatsu or, until then, Keycloak.
- The interop job costs one nightly kind run of about 16 GB on a runner while any deployment has the add-on on.

## Related

- [Research: credentials and connector, FIWARE-compatible](../Research/rust/vc-dsc-fiware.md) holds the flows, gaps, slices and oracle.
- [ADR-N-016](adr-n-016-data-space-connector.md) places the connector behind the Endpoint layer.
- [00-register](00-register.md) lists every decision and its status.
- [Requirements/data-space.md](../Requirements/data-space.md) holds DS-01..DS-20.
