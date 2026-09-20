---
sidebar_position: 2
title: "Local Development Setup"
---

# Local Development Setup

Set up a complete local development stack in minutes using lightweight in-cluster components.

## 1. Quickstart with k3d

The fastest path to a full local environment is the automated `dev-up` recipe using `k3d`:

```bash
# Clone the platform repository
git clone https://gitlab.com/civitas-connect/civitas-core/civitas-core-v2/civitas-core-platform.git
cd civitas-core-platform

# Spin up local k3d cluster with Antares, Keycloak, PostgreSQL, and Gitea
just dev-up
```

The recipe executes:

1. Creates a local `k3d` cluster named `joinedcontext-dev` mapping ports 80/443 to localhost.
2. Deploys PostgreSQL via lightweight local containers.
3. Bootstraps Keycloak with pre-configured developer realms (`dev`).
4. Starts the local Gitea instance and seeds the `city-config-dev` repository.

## 2. Local Configuration Seeding

Seed a developer context space and sample smart city data:

```bash
# Seed LinkML data models, policies, and sample parking entities
just seed-demo

# Verify jcctl can plan against local broker
cargo run -p jcctl -- plan --repo-dir ./tests/fixtures/demo-city-config
```

## 3. Running Components Standalone

You can run individual Rust crates outside Kubernetes against the local infrastructure:

```bash
# Run Context Gateway locally on :8080
export BROKER_URL="http://localhost:8081"
export KEYCLOAK_URL="http://localhost:8082"
cargo run -p context-gateway

# Run Portal API locally on :3000
export DATABASE_URL="postgres://postgres:postgres@localhost:5432/portal_dev"
cargo run -p portal-api

# Run Portal UI locally on :5173
cd apps/portal-ui
pnpm install
pnpm dev
```

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
