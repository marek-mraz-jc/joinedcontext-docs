---
sidebar_position: 3
title: "Backend Development Guidelines (Rust)"
---

# Backend Development Guidelines (Rust)

The backend is Rust everywhere: the **Context Gateway**, the **Portal**, **`jcctl`** and the **credential proxy**. (`antares-ql` belongs to the Antares broker upstream, not to this platform.) Code must be safe, clean, and must never leave an error unhandled on a request path.

## 1. Core Rules

1. **Zero Panics in Request Paths**: Never use `.unwrap()` or `.expect()` in request handlers or parsing code. Use `?` operator bubbling up to standard error enums.
2. **Explicit Error Boundaries**:
   - Internal module errors: Handled using `thiserror`.
   - API boundaries: Convert internal errors into RFC 7807 `ProblemDetails` responses.
3. **Strict Linting**: Every commit must pass `cargo clippy --all-targets -- -D warnings`.
4. **Supply Chain Audit**: Dependencies must pass `cargo deny check` (licenses, bans, security advisories).
5. **Refuse What You Did Not Declare**: every type deserialized from a manifest, a request body or a configuration file carries `#[serde(deny_unknown_fields)]`. A field the platform does not know is a typo the caller wants to hear about, or a field the caller believes is being honoured; silently dropping it is both.
6. **A Credential Is Never Printable**: a secret is held in a `jc_core::Secret`, whose `Debug` writes `<redacted>` and which has no `Display` and no `Serialize`. A derived `Debug` over a configuration struct is how a client secret reaches the cluster's log.

## 2. API Design & OpenAPI Generation

The Portal uses **`axum`** with **`utoipa`** for code-first OpenAPI documentation. Two rules bind every route:

- The URL scheme is `/api/v1/projects/{project}/{plural}` and `/api/v1/projects/{project}/{plural}/{name}`. Never `/api/v1/spaces/{id}`, and never `/apis/joinedcontext.com/...`: a resource is reached inside the project that holds it, by the plural of its kind. `apiVersion` and `kind` live inside the manifest, not in the path.
- A route without a `#[utoipa::path]` and without an entry in the ApiDoc's `paths(...)` is a route the generated client cannot call, and the API documentation will describe a platform that is not the one running.

```rust
use axum::extract::{Path, State};
use axum::Json;

#[utoipa::path(
    get,
    path = "/api/v1/projects/{project}/{plural}/{name}",
    tag = "resources",
    params(
        ("project" = String, Path, description = "Project name"),
        ("plural" = String, Path, description = "Resource kind plural"),
        ("name" = String, Path, description = "Resource name"),
    ),
    responses(
        (status = 200, description = "Resource envelope", body = ResourceEnvelope),
        (status = 401, description = "Unauthorized", body = ProblemDetails),
        (status = 404, description = "Resource not found", body = ProblemDetails)
    )
)]
pub async fn get_resource(
    State(state): State<AppState>,
    Path((project, plural, name)): Path<(String, String, String)>,
) -> Result<Json<ResourceEnvelope>, ApiError> {
    // Configuration kinds are read from the reconciler's mirror of the Git repository, never
    // with SQL: Git is the source of truth and the database holds preferences and state.
    state
        .resources()
        .get(&project, &plural, &name)
        .ok_or_else(|| ApiError::NotFound(format!("{plural}/{name} is not in project {project}")))
        .map(Json)
}
```

The shape above is the real one; `src/api/resources.rs` is the handler it is taken from.

## 3. Database Migrations (sqlx)

Database queries are checked at compile time with `sqlx`. Migrations are numbered SQL files in `joinedcontext-portal/migrations/` (`0001_user_preferences.sql`, `0002_service_account_keys.sql`, …).

What belongs in the database is the short list: user preferences, ServiceAccount key records, sync-source state. Everything declarative, a Context Space, an Endpoint, a Policy, a Pipeline, is a manifest in Git that the reconciler mirrors, so a handler that reaches for SQL to answer a question about configuration is answering from the wrong place.

```bash
# Create a new migration
sqlx migrate add create_context_spaces

# Run migrations against local database
sqlx migrate run
```

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
