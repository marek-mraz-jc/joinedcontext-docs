---
sidebar_position: 18
title: Data Space Connector
description: Normative requirements for negotiated data sharing with other participants through a data space connector behind the Endpoint layer.
---

# Data Space Connector

Family **DS** (DS-01…DS-20). Owning chapter: [Architecture/18-data-space-connector.md](../Architecture/18-data-space-connector.md). Verified by: [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) (DSP/DCP conformance) and [Testing/06-security-tests.md](../Testing/06-security-tests.md).

:::info Post-MVP
The connector addon is **not part of the MVP**: no engine is chosen, no chart ships and no
component is deployed. This family stays the accepted design ([ADR-N-016](../Decisions/adr-n-016-data-space-connector.md))
for the release that adds it. An engine is picked when a data-space partner appears, against the
placement and trust rules below; nothing in the platform depends on one today.
:::

## 1. Placement and trust

- **DS-01** [S] — The data space connector MUST run as an addon behind the Endpoint layer; it MUST NOT hold broker, database or space credentials and MUST reach context data only through Endpoints like any other consumer.
- **DS-02** [S] — The only effects a connector MAY produce inside the platform are (a) a change proposing `Policy` entities compiled from an agreement and (b) transfer tokens whose audience is one Endpoint (RFC 8707); both MUST pass the same lanes and PDP as human-made grants (CC-6x, EP-06).
- **DS-03** [S] — An agreement MUST NOT grant more than the offered Endpoint's own Policy set allows; the ODRL mapper MUST reject such agreements before negotiation completes (MIM3-R10).

## 2. Identity and protocol

- **DS-04** — Participant identity MUST be `did:web:{orgDomain}` of the verified Organization domain (PF-41); credentials MUST be Verifiable Credentials issued by the instance's Keycloak (I1) and presented through the Decentralized Claims Protocol.
- **DS-05** [P] — The connector MUST implement the IDSA/Eclipse Dataspace Protocol (catalog, contract negotiation, transfer process) in its current published version and MUST pass the protocol's conformance test kit in CI for both roles.
- **DS-06** — No engine is named as the default. The engine MUST be selectable through the `DataSpaceParticipant` manifest without changes to offers, agreements or Endpoints, and a candidate MUST publish a signed image under a vendor or organisation namespace before it is deployed (DEP-08); the choice is made when a data-space partner appears.

## 3. Provider role

- **DS-07** — `kind: DataSpaceParticipant` MUST be declared once per Organization with DID, credential issuer, trust anchors and connector URL; `kind: DataOffer` MUST reference one or more Endpoints and an ODRL 2.2 offer in the `ngsi-ld:` profile (R52).
- **DS-08** [A] — The DSP catalog MUST publish each offered Endpoint as a Dataset whose DCAT-AP record is the Endpoint's own (EP-27) and whose `odrl:hasPolicy` is the offer derived from the Endpoint's access surface (EP-57).
- **DS-09** [H][A] — Negotiation outcomes MUST be recorded as `kind: DataAgreement` status; requests equal to the offer MAY be accepted automatically (green lane), counter-offers MUST be accepted by an authorised person in the Portal or by an agent through elicitation (red lane).
- **DS-10** [S] — The ODRL mapper MUST compile an accepted agreement into `Policy` entities with the consumer DID as `assignee`, validity equal to the agreement period, and constraints mapped losslessly to `q`, `scopeQ`, `geoQ`, `temporalQ` (R26); the compiled change MUST be authored by the connector's ServiceAccount and reviewed by the space's lane rules.
- **DS-11** [P] — Transfers MUST use `HttpData-PULL` by default, returning the Endpoint URL and a token bound to the agreement (`agreementId`, participant, audience) with a lifetime ≤ 15 min and refresh through the connector; push transfers MUST be modelled as Pipelines.
- **DS-12** [S] — Termination or expiry of an agreement MUST invalidate its `Policy` entities in one reconcile and the PDP cache within 5 s (OPS-45), and MUST revoke outstanding transfer tokens.
- **DS-13** — Every gateway audit record produced under an agreement MUST carry `agreementId`; usage counters per agreement MUST be available in the Portal and as DSP transfer status.
- **DS-14** [S] — Offers over spaces flagged as containing personal data MUST carry a purpose constraint expressed with the DPV vocabulary (MIM4) and MUST NOT be publishable with a `public` audience.

## 4. Consumer role

- **DS-15** — Consuming another participant's data MUST start from a `kind: DataAgreement` whose transfer token is stored in OpenBao and referenced by `secretRef`; tokens MUST NOT appear in Git or manifests.
- **DS-16** — `kind: ContextSourceRegistration` MAY carry `spec.dataSpace.agreementRef`; the Context Gateway MUST then attach the transfer token to forwarded requests and apply the inbound Mapping (DM-51); the peer's schema MUST be mirrored as a foreign DataModel (DM-48).
- **DS-17** — `kind: SharedSpaceReference` MAY carry `spec.remote.agreementRef` to mount the peer Endpoint for dashboards, Apps and agents; the gateway MUST proxy with the token and MUST expose the peer's `schema/` and `access` surfaces unchanged.
- **DS-18** — Pipelines MAY declare input `dataspace: { agreementRef }`; the reconciler MUST render the Bento input with the token from OpenBao and MUST mint local URNs for replicated entities from the injected `JC_ORG_DOMAIN` (PF-44).
- **DS-19** — When an agreement ends, the reconciler MUST set dependent registrations, references and pipelines to `Suspended` with the reason, never delete them.
- **DS-20** [A] — The configuration MCP MUST expose `list_data_offers`, `list_agreements` and `negotiate_agreement` (elicitation required); the data MCP of a mounted peer Endpoint MUST be the peer's own MCP reached through the gateway proxy.

## Traceability

| Requirements | Section | Architecture | Tests |
|---|---|---|---|
| DS-01…DS-03 | Placement and trust | [Architecture/18-data-space-connector.md#1-where-the-connector-sits](../Architecture/18-data-space-connector.md#1-where-the-connector-sits) | [Testing/06-security-tests.md](../Testing/06-security-tests.md) |
| DS-04…DS-06 | Identity and protocol | [Architecture/18-data-space-connector.md#1-where-the-connector-sits](../Architecture/18-data-space-connector.md#1-where-the-connector-sits) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| DS-07…DS-14 | Provider role | [Architecture/18-data-space-connector.md#2-provider-role-publishing-an-endpoint-into-a-data-space](../Architecture/18-data-space-connector.md#2-provider-role-publishing-an-endpoint-into-a-data-space) | [Testing/02-conformance-tests.md](../Testing/02-conformance-tests.md) |
| DS-15…DS-20 | Consumer role | [Architecture/18-data-space-connector.md#3-consumer-role-reading-another-participants-data](../Architecture/18-data-space-connector.md#3-consumer-role-reading-another-participants-data) | [Testing/04-configuration-and-pipeline-tests.md](../Testing/04-configuration-and-pipeline-tests.md) |

## Related

- [00-index](00-index.md) — all requirement families.
- [access-control](access-control.md) — MIM3 marketplace and ODRL requirements this family builds on.
- [endpoints](endpoints.md) — the Endpoint surface that serves agreed data.
