---
sidebar_position: 3
title: Conformance & Standards Verification
description: The standards suites, what each one claims, which surfaces they run against, and how to run one.
---

# Conformance & Standards Verification

This page is for whoever has to prove that a surface still speaks its standard: which suite covers it, what the platform claims, and what a run needs. Every suite lives in `joinedcontext-conformance`, one folder per standard, each with a `run.sh` and a README. The claims below were read off the code on 2026-09-20; where a suite asserts more than the code implements, this page says so.

Run one suite through the runner's entrypoint, which takes suite folder names and writes its reports under `JC_REPORTS_DIR`:

```bash
NGSILD_URL=https://{host}/cs/{space}/ngsi-ld/v1 jc-conformance etsi
```

The suites with a runner today are `etsi`, `etsi-ttf`, `ogc`, `sta`, `mcp`, `dsp`, `schemathesis`, `security`, `models`, `ckan`, `chaos`, `pipelines`, `e2e`, `playwright` and `k6`. Each has a `workflow_dispatch` lane of its own in the conformance repository, with the target URL as an input; the fast lane there proves the runners rather than the platform.

---

## 1. ETSI GS CIM 009 NGSI-LD Conformance

The broker and the gateway in front of it are held to the official ETSI NGSI-LD Testing Task Force Robot Framework suite.

### System under test matrices

Three matrices can be run today:

1. **The vanilla broker.** The NGSI-LD API root of the broker itself. This is baseline engine compliance, and it is also what proves the suite: two cases used to demand `200` where clause 5.7.2.4 mandates `BadRequestData`.
2. **A context space through the gateway**, `/cs/{space}/ngsi-ld/v1`. The same data with the enforcement point in front of it ([SP-03](../Requirements/space-surface.md#1-url-scheme)).
3. **An endpoint slug**, `/api/endpoint/{endpointSlug}/ngsi-ld/v1`. A standard NGSI-LD client against one endpoint's own root.

[Architecture/05](../Architecture/05-context-gateway.md#4-deployment-modes-embedded-vs-standalone) also describes an embedded mode, the enforcement point compiled into the broker. No code implements it: the broker does not depend on the gateway crate, so there is no fourth matrix to run, and the suite README's fourth entry is a plan rather than a lane.

Matrices 2 and 3 differ from matrix 1 in more than latency. A broker accepts any syntactically valid URN; the gateway refuses an identifier whose organization and context space are not the endpoint's ([SP-02](../Requirements/space-surface.md#1-url-scheme), GW20), so a suite that mints its own identifiers has to be given the deployment's `NGSILD_ORG_DOMAIN` and `NGSILD_SPACE` or every case fails on its fixtures instead of on the clause under test.

### Execution in CI

Both ETSI lanes run from the conformance runner image
(`ghcr.io/marek-mraz-jc/joinedcontext-conformance`), which carries Robot Framework and the suite
libraries. `NGSILD_URL` selects the matrix, `NGSILD_TENANT` and `NGSILD_TOKEN` carry the tenant
header and the bearer token, and `NGSILD_ORG_DOMAIN` and `NGSILD_SPACE` are the org-domain and
space segments of the entity identifiers the suite mints.

On `dev` the suite runs as the service account `conformance` of project `helsinki`: a
confidential Keycloak client `helsinki-air-quality-conformance` whose `client_credentials` token carries
the seeded endpoint's slug as its audience, and a policy that binds the write operations to that
account and to nobody else; the anonymous caller keeps `retrieveOps` only
([PF-45](../Requirements/platform.md), GW22). `NGSILD_TOKEN` carries that token; the client secret
lives in the cluster and never in a workflow file.

Measured on `dev` through the seeded endpoint with that token: 31 cases, 28 pass and the three
gateway defects quarantined by task id, the same result as the gateway lab in CI. Before the first
write the space answers every read with `404 NonexistentTenant`: the broker creates a tenant on
the first create operation (CIM 009 clause 5.5.10), so the run needs no tenant provisioning and an
empty space reads as absent, not as empty. The `etsi-smoke` workflow dispatch of the conformance
repository repeats the run with the repository secret `NGSILD_CLIENT_SECRET`.

The last two are what makes matrices 3 and 4 different from matrices 1 and 2 rather than merely
slower. A broker accepts any syntactically valid URN; a Context Gateway refuses an identifier
whose organization and context space are not the endpoint's
([SP-02](../Requirements/space-surface.md#1-url-scheme), GW20), so a suite that mints its own
identifiers has to be told the deployment's values or it fails on its fixtures rather than on the
clause under test, in every case at once.

The merge-request gate is the smoke suite in `tests/etsi/`: 31 cases named after the CIM 009
clause each one verifies, budgeted at 60 seconds. It is green against the default broker
(`ghcr.io/marek-mraz/antares-broker`, in-memory store), which is the run that proves the suite
itself: two cases used to demand `200` for an `id`-only and an `idPattern`-only query, where
clause 5.7.2.4 mandates `BadRequestData` for a query with no type selector, attribute list, query,
geoquery or local scope. A suite nothing executes can disagree with the specification it cites and
still look healthy.

Beside it in `tests/etsi/` are three temporal suites, run when their URL is given: `temporal.robot`
(CIM 009 clauses 6.18 to 6.20), `temporal_projected.robot` through a ModelProjection, and
`temporal_federated.robot` over Context Source registrations. `NGSILD_PROJECTED_URL` and
`NGSILD_FEDERATED_URL` select them; empty skips them instead of failing.

Matrix 3 is 28 of those 31 today, measured against the published gateway image in front of the
same broker, with the endpoint table loaded from a three-manifest repository (a context space, a
public endpoint, and a policy granting the role `public` the operations the suite performs). The
three that fail are the gateway's answers, not the suite's assertions, and each was reproduced
against the broker for contrast before it was filed: a `georel=near;maxDistance==N` geoquery is
refused because the gateway forwards `maxDistance` as a query parameter of its own; NGSI-LD errors
are rendered `application/problem+json` with platform error types, where clause 5.5.3 requires
`application/json` and a clause 5.5.2 type; and an unsupported request `Content-Type` answers
`400` where clause 6.3.2 requires `415`. Matrices 1 and 2 report none of them.

```bash
docker run --rm -e NGSILD_URL=https://{host}/cs/{space}/ngsi-ld/v1 \
  -v "$PWD/reports:/reports" ghcr.io/marek-mraz-jc/joinedcontext-conformance:main etsi
```

The full Testing Task Force suite is `tests/etsi-ttf/`. It fetches the official suite at a pinned
commit rather than vendoring it, and `run.sh` runs all five legs by default: `CommonBehaviours`,
`ContextInformation`, `ContextSource`, `DistributedOperations` and `jsonldContext`. `TTF_LEGS`
narrows the run, and the `etsi-ttf` workflow's own default input leaves `DistributedOperations`
out, so a dispatch with the defaults runs four of the five:

```bash
docker run --rm -e NGSILD_URL=https://{host}/cs/{space}/ngsi-ld/v1 \
  -e TTF_LEGS="CommonBehaviours ContextInformation" \
  -v "$PWD/reports:/reports" ghcr.io/marek-mraz-jc/joinedcontext-conformance:main etsi-ttf
```

Reports (`output.xml`, `log.html`, `report.html`) land in `reports/etsi-ttf/`.

Two properties of the system under test decide whether a failure in this suite means anything.

The suite runs three mock servers of its own, a notification receiver, a Context Source and an
`@context` server, and binds each on `TTF_CALLBACK_HOST` while telling the system under test to
call back on that same address, so it has to be an address of the runner that the system under
test can reach (`127.0.0.1` when both share a network namespace, the runner's routable address on
a cluster). `run.sh` refuses a value it cannot bind rather than letting Robot stall on it.

Temporal test purposes only mean something against a system that persists temporal
representations. A broker on an in-memory store answers `GET /temporal/entities/{id}` with the
entity and no attribute instances, and every temporal purpose then fails for that one reason. The
same holds for an ordered query while any Context Source Registration matching the queried type is
present: clause 5.7.2.4 makes `orderBy` outside local scope a `400`, so a leg that orders needs a
broker whose registrations were cleaned up first.

### Expected Failure Quarantine

Deviations or unimplemented optional features are tracked explicitly in
`tests/etsi-ttf/expected_failures.json`, a JSON array whose `suite` and `test_case` are the names
Robot prints (the file `5510_01.robot` is the suite `5510 01`):

```json
{
  "suite": "009_BatchOperations",
  "test_case": "Batch_Create_Entities_Invalid_Payload",
  "reason": "Tracking upstream issue #142: Returns 400 instead of 207 ProblemDetails",
  "expiration": "2026-12-31"
}
```

`tests/etsi-ttf/check_expected_failures.py` enforces the list on every run: an unexpected
failure, a quarantined test that now passes, an entry whose test no longer runs, an entry past its
`expiration`, and an entry with an empty `reason` each fail the build. The quarantine list
therefore cannot rot, and a deviation cannot be parked indefinitely.

---

## 2. OGC API - Features Part 1

Endpoints that carry a geospatial representation serve OGC API - Features ([SP-04](../Requirements/space-surface.md#1-url-scheme)).

### Conformance classes claimed

The landing page advertises exactly the five classes in `crates/context-gateway/src/translators/ogc.rs`:

- `http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core`
- `http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30`
- `http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson`
- `http://www.opengis.net/spec/ogcapi-features-2/1.0/conf/crs`
- `http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/basic-cql2`

Not claimed and not advertised: HTML output, Part 4 (create, replace, update, delete), the CQL2 text and JSON conformance classes of their own, and anything in CQL2 beyond the subset [EP-35](../Requirements/endpoints.md) lists. The compiler refuses an unsupported construct by name rather than ignoring it, which is why a filter the endpoint cannot honour is a `400` and never a silently wider answer.

### The two runs

`tests/ogc/` runs the query contract the platform owns (`test_cql2_filtering.py`: the advertised class list, `bbox`, `datetime`, CQL2 comparison and its refusals, pagination, `404` on an unknown feature, `405` on every write) and then the official `ets-ogcapi-features10` Abstract Test Suite through TEAM Engine, whose image is pinned by digest in `run.sh`. `tests/ogc/check_ogc_results.py` turns the TestNG document into the verdict, because the runtime exits `0` even when cases failed.

```bash
OGC_LANDING_URL=https://{host}/api/endpoint/{slug}/ogc/features jc-conformance ogc
```

`OGC_COLLECTIONS` bounds how many collections the Abstract Test Suite walks (three by default, `-1` for all), and `TE_BASE_URL` points the run at a TEAM Engine that is already up instead of starting one.

---

## 3. OGC SensorThings API v1.1

An endpoint with the SensorThings representation projects entities into the Sensing profile read path. OGC publishes no CITE suite for v1.1, so `tests/sta/` asserts the profile against the response bodies.

`sta/v1.1/` advertises three requirement classes, from `crates/context-gateway/src/translators/sta.rs`: `http://www.opengis.net/spec/iot_sensing/1.1/req/datamodel`, `.../req/resource-path` and `.../req/request-data`.

| Query option | State | How it is served |
|---|---|---|
| `$filter` | implemented | compiled into the NGSI-LD `q` and a temporal window; a predicate it cannot compile is a `400` |
| `$expand` | implemented | parent to child relations, `Datastream/Observations` |
| `$top`, `$skip` | implemented | one page per broker request, `$skip` becomes `lastN`, bounded by the gateway's own maximum |
| `$count` | implemented | `@iot.count` on the collection |
| `$orderby` | partly | newest first is honoured on the page; any other ordering is not |
| `$select` | **not implemented** | the gateway reads no `$select`; it is neither transpiled to `attrs` nor refused |

The last row is a claim this documentation set and `tests/sta/README.md` both made and the code does not keep. Until the gateway either serves `$select` or refuses it, `tests/sta/test_sta_sensing.py::test_ts08_select_returns_only_the_requested_fields` is a red case waiting for a dispatch, not a proven class.

Not claimed: the DataArray extension, MultiDatastream, and Tasking or Actuation. Bulk reads leave through the file representations (`file.csv`, `file.xlsx`, `file.zip`, `file.geojson`), not through an STA array, and every write to `sta/v1.1/` is a `405`.

---

## 4. Model Context Protocol

The gateway serves an MCP Streamable HTTP surface per space and per endpoint, and the Portal serves one for the configuration plane ([SP-14](../Requirements/space-surface.md#4-per-space-mcp-instances)).

`tests/mcp/` is a pytest suite of the platform's own, not the TypeScript inspector. It asserts:

1. **The handshake.** `initialize` negotiates the protocol version the gateway implements, `2025-06-18`, and the capabilities it announces.
2. **JSON-RPC 2.0 framing.** Responses, errors and notifications carry the shapes the specification requires.
3. **RFC 9728 binding.** An anonymous call is a `401` whose `WWW-Authenticate` names `resource_metadata`, and that metadata document answers `200` without a login redirect.
4. **Tool annotations.** A query tool declares `annotations.readOnlyHint: true`; a mutating tool declares `destructiveHint`.
5. **Isolation.** A token for one space reaches no other space's tools, resources or prompts, and a private space's surface says no more than an unknown one.
6. **Read parity.** `test_mcp_read_parity.py` asks the same question over MCP and over the REST surface and fails when the two answers differ, so a tool cannot become a second, wider read path.

`tests/mcp/selftest.py` runs those assertions against `stub_mcp_server.py` in a broken configuration in the fast lane, so a check that can no longer fail is caught on the commit that breaks it.

---

## 5. Data model artifacts and JSON-LD

The data modelling path turns LinkML sources into the artifacts an endpoint publishes ([CC-12](../Requirements/city-as-code.md#2-repository-and-manifest-model)). `tests/models/` holds it to them, against a projects tree given by `PROJECTS_DIR`:

- The generated artifacts are committed beside their source: `json-schema/{name}.v{major}.json`, `context/{name}.v{major}.jsonld`, `docs/{name}.md`, `examples/{name}.example.jsonld`.
- The committed JSON Schema is draft-07, with none of the 2019-09 or 2020-12 keywords.
- The semantic version major matches the `v{major}` segment of the artifact paths, and the lifecycle is one of `draft`, `published`, `deprecated`, `retired`.
- The served SHACL shapes accept the committed example entity expanded with the served `@context`, and reject an entity that violates the model. pySHACL does the validation; `selftest_endpoint.py` proves toothless shapes go red.
- `test_mapping_parity.py` runs the same mapping through both engines and fails when they disagree.

There is no run of the W3C JSON-LD 1.1 test suite here. The `@context` documents are checked by expanding the committed examples through them, which is the property the platform depends on; the algorithms themselves are the JSON-LD library's.

---

## 6. Dataspace Protocol

`tests/dsp/` runs the Eclipse Dataspace Protocol test kit, pinned by digest, against the connector addon as the system under test ([DS-05](../Requirements/data-space.md)). `check_dsp_results.py` decides the verdict, because the runtime exits `0` even when every case failed. The lane is `workflow_dispatch` with the connector's DSP URL, its base URL and its `did:web` participant id as inputs.

The platform half of the protocol is covered in the gateway crate rather than here: `crates/context-gateway/tests/odrl_compiler_tests.rs` asserts that an accepted agreement yields exactly the grants the ODRL mapper predicts and that an agreement cannot exceed the endpoint's ceiling, and the dataspace token files assert what a foreign token may reach.

## Related

- [00-strategy.md](00-strategy.md) — the lanes, and which of these suites the hourly batch runs.
- [01-backend-tests.md](01-backend-tests.md) — the in-crate tests behind these surfaces.
- [05-deployment-and-performance-tests.md](05-deployment-and-performance-tests.md) — the k6 budgets and the chaos drills.
- [SP-03](../Requirements/space-surface.md) — the URL scheme the matrices walk.
- [testing](../Requirements/testing.md) — the TS family this page is verified against.
