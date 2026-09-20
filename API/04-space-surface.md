---
sidebar_position: 5
title: "Canonical Space Surface"
description: Wire-level specification of /cs, the DCAT-AP space record and the NGSI-LD tree under a context space.
---

# Canonical Space Surface

`https://{host}/cs/{space}/` is the direct surface of one context space, for the project that owns it and for the pipelines that write into it. Where an Endpoint is an opaque slug shared with the outside world, a space is named after the evidencia code in the entity URN, and the caller has to hold a grant on it. This page specifies what the surface answers; the requirements are [SP-01…SP-13](../Requirements/space-surface.md) and the design is [Architecture/04](../Architecture/04-context-spaces-and-endpoints.md#1-context-space-canonical-surface-sp-01sp-04).

## 1. Resource tree

```text
/cs                                     catalog of the spaces the caller may discover (SP-11)
/cs/{space}                             DCAT-AP dataset record of one space (SP-10)
/cs/{space}/ngsi-ld/v1/…                the CIM 009 resource tree, byte for byte (SP-03)
/cs/{space}/mcp                         MCP Streamable HTTP instance of the space (SP-14)
/cs/{space}/schema/…                    the space's model artifacts (SP-04)
/cs/{space}/dump/…                      dated immutable snapshots (SP-04)
/cs/{space}/access                      the caller's effective grant document (EP-55)
```

No other child exists. Anything else under `/cs/{space}/` answers `404`, the same answer a space the caller may not discover gives, so a probe learns nothing either way (SP-06, R20).

## 2. Discovery: `GET /cs`

Returns a DCAT-AP catalog, narrowed to the caller through the same policy layer that enforces requests: a space appears only when the caller holds a grant that reads something in it. An anonymous caller is the synthetic `public` role, so the anonymous catalog is exactly the publicly readable spaces (SP-11, GW22).

```http
GET /cs
Accept: application/ld+json
```

```json
{
  "@context": "https://www.w3.org/ns/dcat.jsonld",
  "@type": "dcat:Catalog",
  "dct:title": "joinedcontext context spaces",
  "dcat:dataset": [
    { "@id": "https://hel.example.fi/cs/air-quality", "@type": "dcat:Dataset", "dct:title": "Ilmanlaatu" }
  ]
}
```

## 3. The space record: `GET /cs/{space}`

Returns the DCAT-AP dataset record of one space, whose distributions are exactly the children of §1: the NGSI-LD tree and the MCP instance as `dcat:DataService`, each dump as a `dcat:Distribution`, and the MQTT topic namespace as an access service (SP-10, ADR 011). One URL hands a human, a program and an agent the same entry point.

Content negotiation on `Accept`, with `application/ld+json` as the default:

| `Accept` | Answer |
|---|---|
| `application/ld+json`, `application/json` | DCAT-AP as JSON-LD |
| `text/turtle` | the same graph as Turtle |
| `text/html` | a minimal page listing the title, the description and the children as links |

```http
GET /cs/air-quality
Accept: text/turtle
```

```turtle
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<https://hel.example.fi/cs/air-quality> a dcat:Dataset ;
    dct:identifier "air-quality" ;
    dct:title "Ilmanlaatu" ;
    dcat:distribution <https://hel.example.fi/cs/air-quality/dump/latest.nq.gz> .

<https://hel.example.fi/cs/air-quality/ngsi-ld/v1/> a dcat:DataService ;
    dct:title "NGSI-LD API" ;
    dcat:endpointURL <https://hel.example.fi/cs/air-quality/ngsi-ld/v1/> ;
    dcat:servesDataset <https://hel.example.fi/cs/air-quality> .
```

A caller with no grant on the space gets `404`, never `403`: a refusal that distinguishes the two would confirm the space exists (SP-06, R20).

## 4. The NGSI-LD tree: `/cs/{space}/ngsi-ld/v1/`

Byte for byte the CIM 009 resource tree, so a stock NGSI-LD client pointed at the space base works unmodified (SP-03, R15). The request passes exactly the steps an Endpoint request passes, in the same code: the client's tenancy and identity claims are stripped, the space is resolved, the operation is named, the PDP decides, a read is narrowed to the grant and a write is checked whole, and only then is `NGSILD-Tenant: {space}` injected on the internal hop (SP-07, GW20, GW25).

The difference from `/api/endpoint/{slug}/ngsi-ld/v1/` is the name in the path and the audience the token has to carry, nothing else. `aud` names the space (`air-quality`) or the full resource URI (`https://{host}/cs/air-quality`); a token minted for an Endpoint does not open a space.

```http
GET /cs/air-quality/ngsi-ld/v1/entities?type=AirQualityObserved&limit=10
Authorization: Bearer eyJhbGciOi…
```

Clients never send `NGSILD-Tenant`; one that does has it removed before anything reads it, and no
answer of this surface carries it back either — the space name is pinned for the internal hop to
the broker and stripped from the response (SP-05).

`NGSILD-Results-Restricted` is opt-in: a caller who sends `NGSILD-Results-Restricted: true` is
told when the answer was narrowed, and a caller who does not ask is answered as if the result were
simply what it is (R22).

## Related

- [Requirements/space-surface](../Requirements/space-surface.md) — SP-01…SP-21, the normative statements this page implements.
- [Architecture/04](../Architecture/04-context-spaces-and-endpoints.md#1-context-space-canonical-surface-sp-01sp-04) — why the surface has this shape and how tenancy is derived.
- [API/02](02-endpoint-representations.md) — the endpoint surface, which serves the same data under an opaque slug.
- [Architecture/12](../Architecture/12-identity-and-access.md) — how a token is bound to the resource it names.
