---
sidebar_position: 1
title: "Development Workspace & Architecture"
---

# Development Workspace & Architecture

This page is the map a new engineer needs before the first commit: which repository holds what, which toolchain builds it, and which checks have to pass before a push. The page that follows, [01-getting-started](01-getting-started.md), is how to run it.

## 1. Repositories

The platform is five repositories, not one workspace. Which one a change lands in is decided by what it touches, and a commit stays inside one of them so a revert is one thing.

| Repository | Holds | Built with |
|---|---|---|
| `joinedcontext-platform` | the Rust workspace: `crates/jc-core` (URN scheme, manifest kinds, `Policy` model, errors), `crates/context-gateway` (PEP, in-process PDP, representation translation, MCP façade), `crates/jcctl` (reconciler library and CLI), `crates/agent-proxy` (the credential proxy an agent workspace reaches the platform through), `crates/functions`, and `tools/model-tools` (a Python image for the LinkML generators) | `cargo` |
| `joinedcontext-portal` | the one management application: `src/` is the axum backend, the resource API, the in-process reconciler and the MCP surface; `ui/` is the Vite, React 19 and TypeScript front end whose `dist` the binary embeds; `sdk/` is the generated client; `migrations/` the database schema | `cargo` and `pnpm` |
| `joinedcontext-deployment` | the Helmfile deployment: APISIX standalone, Keycloak, CloudNativePG, Linkerd, Kyverno, NetworkPolicies, and the `justfile` that applies them | `helmfile`, `just` |
| `joinedcontext-conformance` | the ETSI, OGC, SensorThings, MCP, data space, schemathesis, k6 and Playwright suites | `python`, `robot`, `pnpm` |
| `joinedcontext-docs` | this documentation set, its `scripts/` checkers and the requirement families | `python` |

The Antares broker is its own upstream repository. The platform deploys it and depends on its NGSI-LD behaviour, but does not vendor it.

## 2. Toolchain

What CI installs, which is what a workstation needs:

- **Rust**: the stable toolchain, edition 2021 (`dtolnay/rust-toolchain@stable` in every `ci.yml`).
- **Node.js**: 22, with **pnpm 10.20.0** (pinned as `packageManager` in `ui/package.json`; `corepack enable` picks it up).
- **Docker or Podman**: BuildKit and rootless testcontainers.
- **just**: the command runner the deployment repository uses.
- **helmfile**, **helm**, **kubectl**: only for the deployment repository.

```bash
# What a workstation needs, in the order a build uses it
rustc --version          # stable
cargo --version
node --version           # v22.x
pnpm --version           # 10.20.0
just --version
```

## 3. What has to pass before a push

The fast lane is the merge gate, and it runs in under five minutes:

```bash
# Rust, in either workspace: the crate you touched, never the whole workspace
cargo fmt --check -p <crate>
cargo clippy -p <crate> --all-targets -- -D warnings
cargo test -p <crate>

# The Portal UI
cd ui && pnpm lint && pnpm test -- --run && pnpm build
```

`cargo test -p <crate>` rather than the one test file you wrote: a change to a route's error path moves the status other suites in the same crate assert, and the fast lane will find it if you do not.

## Related

- [01-getting-started](01-getting-started.md) — running the stack and the components against it.
- [02-backend-guidelines](02-backend-guidelines.md) — the Rust rules the reviewers apply.
- [03-frontend-guidelines](03-frontend-guidelines.md) — the same for the UI.
- [../Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) — how a change reaches the platform.
