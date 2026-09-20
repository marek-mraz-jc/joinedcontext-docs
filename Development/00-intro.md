---
sidebar_position: 1
title: "Development Workspace & Architecture"
---

# Development Workspace & Architecture

This guide outlines the codebase structure, developer toolchains, and repository boundaries for engineers contributing to the platform.

## 1. Repository & Workspace Layout

The core codebase is organized as a Cargo workspace for backend components, paired with a modern TypeScript frontend workspace:

```text
civitas-core-platform/
├── Cargo.toml                       # Root Cargo Workspace definition
├── crates/
│   ├── portal-api/                  # Rust Axum REST API server
│   ├── context-gateway/             # Rust PEP firewall, translator, MCP façade
│   ├── jcctl/                     # Rust CLI reconciler & drift engine
│   ├── common-kinds/                # Shared serde models for platform manifests
│   └── antares-ql/                  # Canonical NGSI-LD query parser (Wasm/native)
├── apps/
│   └── portal-ui/                   # React 19 / Vite / TypeScript web application
├── schemas/
│   └── kinds/                       # JSON Schema draft-07 definitions for all kinds
└── tests/
    ├── property/                    # Proptest suites for policy algebra
    └── conformance/                 # Robot Framework ETSI conformance suites
```

## 2. Mandatory Toolchain Requirements

- **Rust**: 1.85+ (stable toolchain)
- **Node.js**: v22 LTS (pnpm 9+)
- **Docker / Podman**: Compatible with BuildKit and local rootless testcontainers
- **just**: Command runner (replaces GNU Make)
- **minijinja-cli**: Sandboxed template linter

```bash
# Verify local environment
rustc --version
cargo --version
node --version
pnpm --version
just --version
```

## Related

- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
