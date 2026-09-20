---
sidebar_position: 2
title: Backend & Crate Testing
description: Where the Rust tests live, the harness each crate gives you, and how to run one file.
---

# Backend & Crate Testing

This page is for whoever is about to change Rust code: which crate owns the behaviour, which harness is already there, what one test file looks like, and the one command that runs it. Read [00-strategy.md](00-strategy.md) first for the lanes. Everything named here was read off the trees on 2026-09-20.

The backend is two repositories:

- `joinedcontext-platform`, a workspace of five crates: `jc-core` (the manifest kinds, the registry, the URN and i18n rules), `context-gateway` (the enforcement point, the representation translators and the MCP server), `jcctl` (the loader, the reconciler and the publishers), `agent-proxy` and `functions`. A Python tool, `tools/model-tools`, renders the data model artifacts.
- `joinedcontext-portal`, one crate plus `apps/*`: the axum API, the in-process reconciler and the embedded UI.

---

## 1. Where the tests are, and how to run one

| Crate | Unit tests | Test files | Run one file |
|---|---|---|---|
| `crates/jc-core` | beside the code | 38 | `cargo test -p jc-core --test kind_documentation_tests` |
| `crates/context-gateway` | beside the code | about 130 | `cargo test -p context-gateway --test edge_app_space_record_tests` |
| `crates/jcctl` | beside the code | 42 | `cargo test -p jcctl --test apply_tests` |
| `crates/agent-proxy` | beside the code | 11 | `cargo test -p agent-proxy --test <file>` |
| `crates/functions` | beside the code | 1 | `cargo test -p functions` |
| `joinedcontext-portal` | beside the code | over 120 | `cargo test --test openapi_tests` |

One file per behaviour, named after the behaviour it proves, with the requirement ids in the module doc comment. A module inside a crate runs with `cargo test -p <crate> --lib <module>::`.

The fast lane runs `cargo test --workspace --lib --bins`, which does not build the files in `tests/`. A change that moves a shape has to be run with the whole crate, `cargo test -p <crate>`, before it is pushed; otherwise the fast lane passes a break and the hourly `ci-full` finds it an hour later.

---

## 2. The Context Gateway harness

`crates/context-gateway/tests/common/mod.rs` builds the gateway the way it is deployed, not a stand-in for it:

- **A throwaway realm.** One P-256 key per test run, published as a JWKS exactly as Keycloak publishes one, so the token verifier is exercised through its production path. No signing key is committed. `Realm::mint`, `Realm::mint_with_kid` and `Realm::workload_token` issue the person and workload tokens; `ISSUER` is the realm the gateway is configured with.
- **A broker stub.** `BrokerStub::start(pages)` answers NGSI-LD reads from fixed pages and records every hop, so a test asserts what the gateway forwarded as well as what it answered. A test that expects no broker call asserts an empty hop list.
- **The real router.** `router(Arc::new(Gateway::new(Broker::new(url), Box::new(PolicyPdp), "banskabystrica.sk").serve([endpoint]).serve_spaces([space]).authenticate(...)))`, driven with `tower::ServiceExt::oneshot`. Policies are parsed from YAML in the test, the same `PolicySpec` the reconciler loads.

The files are grouped by the surface they cover: `edge_pdp_*` (about 20 files) for the policy decision point and its geo grants, `edge_app_*` (16) for the routes, `edge_gateway_*` (13) for the proxy and middleware, `edge_auth_*` (11) for tokens, keys and accounts, and `edge_translators_*` (6) for the representations.

### What the gateway files prove

- An entity, space or endpoint the caller may not see answers the same `404` as one that does not exist, so a name cannot be probed ([R20](../Requirements/access-control.md#5-requesting-extra-data)).
- A filter naming a hidden attribute empties the answer instead of confirming that the attribute is there.
- A grant narrows and never widens: the entities a caller can end up seeing are inside every grant area.
- A header a client supplies, `NGSILD-Tenant` included, never reaches the broker unless the claims put it there ([GW20](../Requirements/gateway-firewall.md#5-tenants-pinning-and-chaining)).
- Every representation of one endpoint shows the same data as every other one.

One case, from `crates/context-gateway/tests/edge_app_space_record_tests.rs`:

```rust
/// The first case: no other spelling of a space name is that name. The names are guessable words,
/// so every near miss has to answer what a name nobody created answers (SP-06, R20).
#[tokio::test]
async fn no_other_spelling_of_a_space_name_is_that_space() {
    let (expected_status, expected_media, expected_body) =
        call(gateway(two_spaces()), get("/cs/nothing-here")).await;
    assert_eq!(expected_status, StatusCode::NOT_FOUND);

    for path in ["/cs/OVZDUSIE", "/cs/ovzdusie.", "/cs/ovzdusie%20", "/cs/ovzdusi", "/cs/ovzdusie/"] {
        let (status, media, body) = call(gateway(two_spaces()), get(path)).await;
        assert_eq!(status, expected_status, "{path}: {body}");
        assert_eq!(media, expected_media, "{path}");
        assert_eq!(body, expected_body, "{path}: one answer for all of them");
    }

    // A percent-encoded unreserved character is the same character (RFC 3986 2.3), so `%6F` is an
    // `o` and names the same space. That is equivalence, not a second name.
    let (status, _, _) = call(gateway(two_spaces()), get("/cs/%6Fvzdusie")).await;
    assert_eq!(status, StatusCode::OK, "%6F is an `o`");
}
```

The shape is worth copying: one answer is taken as the baseline and every other input is asserted equal to it, body included. A test that only compares status codes passes while the body says which name exists.

---

## 3. `jcctl`

`jcctl` reads a repository and converges the platform to it. Its surface is a fixed argument list rather than a parser, printed by the binary itself:

```bash
jcctl validate --repo-dir <path>
jcctl plan --repo-dir <path> [--gateway-url <url>] [--token-file <path>] [--json]
jcctl apply --repo-dir <path> [--gateway-url <url>] [--token-file <path>] [--prune] [--confirm-deletions]
jcctl drift --repo-dir <path> [--gateway-url <url>] [--json] [--adopt-dir <path>]
jcctl model generate|diff|validate --repo-dir <path> [--url <url>]
jcctl pipeline test --pipeline <manifest.yaml> --sample <file> [--format csv|json|text]
jcctl schema export [--out <dir>]
```

- **Idempotency.** `crates/jcctl/tests/apply_tests.rs` applies a repository, then plans again and asserts the second plan is empty ([CC-18](../Requirements/city-as-code.md#3-reconciler-jcctl)).
- **Determinism.** `crates/jcctl/tests/blueprint_tests.rs` re-renders a committed blueprint instance and asserts byte-identical output; maps are ordered before rendering, so two runs and two machines agree.
- **Artifacts.** `crates/jcctl/tests/rebuild_tests.rs` rebuilds the artifacts of a space at a revision and compares them with the committed ones. The same comparison runs in the platform's fast lane as `jcctl model diff --repo-dir examples/datamodels` against a live generator.
- **Pipelines.** `crates/jcctl/tests/bento_datasource_render_tests.rs` and its neighbours render a pipeline manifest into a Bento configuration; `bento lint` and `bento test` then run over `examples/ingestion/` in CI.

---

## 4. The Portal

The Portal crate holds the API, the reconciler and the embedded UI, in over 120 test files.

- **Routes.** One file per route family, driven through the axum router with a stubbed dependency, the same shape as the gateway's files.
- **The reconciler.** The stream, app and agent deployers are tested against `wiremock` servers standing in for the runner and for Kubernetes, so a converge, an apply, a retire and a failed retry are asserted on the requests that were sent.
- **PostgreSQL.** The Portal keeps preferences, hashed key rows and agent runs in its own database (`src/db.rs`); the migrations are embedded and run on connect. The database test files take a URL from `JC_PORTAL_TEST_DATABASE_URL` and print `skipped:` when it is unset, so a developer without Postgres still gets a green run and the database cases still exist for whoever has one.
- **The OpenAPI document.** `cargo test --test openapi_tests` asserts that what `utoipa` publishes matches the routes the router serves. It runs in the fast lane, because the UI's generated client is built from that document.

---

## 5. The tests that hold the docs to the code

Two files in `jc-core` are why a manifest printed in this documentation set can be trusted:

- `crates/jc-core/tests/docs_golden_tests.rs` reads every file in `crates/jc-core/tests/golden/`, 24 manifests lifted from the pages that print them, and asserts each one parses, validates and round-trips. The file names carry the page they came from, so a broken example names its own page.
- `crates/jc-core/tests/kind_documentation_tests.rs` asserts that every field of every kind carries a doc comment and that none of them carries a credential-shaped value. That comment becomes the JSON Schema `description` the Portal ships, the API publishes and the MCP tool list hands a model, so a missing one is a field unexplained in four places.

---

## 6. What the requirements ask for and is not built yet

- **TS-01** asks for coverage verified in CI. No coverage tool is configured; the lanes assert the tests pass.
- **TS-02**, **TS-03** ask for `proptest` over query rewriting and the representation translators. `proptest` is in no manifest. The invariants those requirements name are covered by the hand written files above and by the representation parity suite in the conformance repository, one asserted case at a time rather than a generated space.
- There is no `criterion` benchmark and no `benches/` directory in either repository. The latency budget is measured against a running deployment by the k6 suite and gated by `scripts/compare-latency.py`; see [05-deployment-and-performance-tests.md](05-deployment-and-performance-tests.md).

## Related

- [00-strategy.md](00-strategy.md) — the lanes and what has to be green before a push.
- [02-conformance-tests.md](02-conformance-tests.md) — the suites that need a running system.
- [06-security-tests.md](06-security-tests.md) — the access control and injection suites.
- [R20](../Requirements/access-control.md) — the masking rule the gateway files assert.
- [testing](../Requirements/testing.md) — the TS family this page is verified against.
