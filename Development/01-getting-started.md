---
sidebar_position: 2
title: "Local Development Setup"
---

# Local Development Setup

How to get the platform running in front of you, from the least you need to the whole stack. Read [00-intro](00-intro.md) first for which repository holds what.

## 1. The three ways to run it

There is no one-command local platform, and pretending otherwise costs an afternoon. Pick by what you are changing:

| You are changing | Run |
|---|---|
| one crate's logic | its tests: `cargo test -p <crate>`. Most of the platform's behaviour is pinned by tests that need no cluster, no broker and no realm. |
| the Portal UI | `cd ui && pnpm dev` against a running Portal, or against the UI's own fixtures. |
| how components fit together, or anything in the deployment | the `dev` cluster, through `joinedcontext-deployment` (§3). |

## 2. Running a component standalone

Each component reads its whole configuration from the environment, so it runs outside Kubernetes as long as the environment names an upstream it can reach. The variable names are the component's own; there are no bare `BROKER_URL` or `DATABASE_URL` names.

```bash
# Context Gateway. The broker URL is scheme and authority only, and an issuer without a JWKS
# URL is refused at startup: it would verify nothing.
export JC_GATEWAY_BIND=127.0.0.1:8080
export JC_GATEWAY_BROKER_URL=http://localhost:1026
export JC_GATEWAY_ORG_DOMAIN=hel.fi
export JC_GATEWAY_REPO_DIR=/path/to/a/configuration/checkout
cargo run -p context-gateway
```

```bash
# Portal. Without JC_PORTAL_DATABASE_URL it runs without the preferences tier rather than
# refusing to start; JC_PORTAL_BIND defaults to 0.0.0.0:8080.
export JC_PORTAL_BIND=127.0.0.1:8081
export JC_PORTAL_DATABASE_URL=postgres://postgres:postgres@localhost:5432/portal_dev
cargo run --bin joinedcontext-portal
```

```bash
# Portal UI, against whatever Portal the proxy in vite.config.ts points at.
cd ui
pnpm install --frozen-lockfile
pnpm dev
```

The Portal binary serves the built UI from `ui/dist` at `/`, so a release build is `pnpm build` in `ui/` first and `cargo build --release` second. For day-to-day UI work `pnpm dev` is the faster loop.

## 3. The `dev` cluster

The deployment repository drives one cluster, and the same three recipes apply and check it:

```bash
cd joinedcontext-deployment
export JUST_NO_DOTENV=true            # the justfile loads a dotenv that must not win here
export KUBECONFIG=...                 # the cluster's kubeconfig, never committed

just dev-apply                        # helmfile sync of everything the repository declares
just dev-smoke                        # the smoke suite against what is now running
just dev-destroy                      # only when a fix cycle is tangled, and announce it first
```

`just --list` prints the rest. `just deploy-k3d` exists for a throwaway local cluster and calls `dev-deployment/startup.sh -k`, which needs `k3d`, `helm`, `docker` and `kubectl` on the PATH; it is the legacy path and is not what CI or the demo uses.

## 4. Seeding configuration

Configuration is manifests in a Git repository, so seeding is a checkout and a plan rather than a command that invents data:

```bash
# What the reconciler would do, against a repository checkout, without writing anything
cargo run -p jcctl -- validate --repo-dir <checkout>
cargo run -p jcctl -- plan --repo-dir <checkout>
```

`jcctl` with no arguments prints every subcommand it has. `plan` is non-mutating; `apply` writes, and wants a gateway URL and a token.

## Related

- [00-intro](00-intro.md) — the repositories and the toolchain.
- [09-development-process](09-development-process.md) — what has to be true before a push.
- [../Architecture/06-configuration-as-code.md](../Architecture/06-configuration-as-code.md) — how a change reaches the platform.
- [../Deployment/02-installation.md](../Deployment/02-installation.md) — installing the platform properly, rather than for development.
