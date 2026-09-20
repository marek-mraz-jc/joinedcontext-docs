---
sidebar_position: 3
title: "Backend Development Guidelines (Rust)"
---

# Backend Development Guidelines (Rust)

Backend services (**Context Gateway**, **Portal API**, **`jcctl`**, **`antares-ql`**) are implemented in idiomatic Rust. Code must be safe, performant, clean, and strictly avoid unhandled errors.

## 1. Core Rules

1. **Zero Panics in Request Paths**: Never use `.unwrap()` or `.expect()` in request handlers or parsing code. Use `?` operator bubbling up to standard error enums.
2. **Explicit Error Boundaries**:
   - Internal module errors: Handled using `thiserror`.
   - API boundaries: Convert internal errors into RFC 7807 `ProblemDetails` responses.
3. **Strict Linting**: Every commit must pass `cargo clippy --all-targets -- -D warnings`.
4. **Supply Chain Audit**: Dependencies must pass `cargo deny check` (licenses, bans, security advisories).

## 2. API Design & OpenAPI Generation

The Portal API uses **`axum`** with **`utoipa`** for code-first OpenAPI documentation:

```rust
use axum::{extract::{State, Path}, Json};
use utoipa::ToSchema;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, ToSchema)]
pub struct ContextSpaceDto {
    pub id: String,
    pub name: String,
    pub project_id: String,
}

#[utoipa::path(
    get,
    path = "/api/v1/spaces/{id}",
    responses(
        (status = 200, description = "Space retrieved successfully", body = ContextSpaceDto),
        (status = 404, description = "Space not found", body = ProblemDetails)
    )
)]
pub async fn get_space(
    State(pool): State<sqlx::PgPool>,
    Path(id): Path<String>,
) -> Result<Json<ContextSpaceDto>, AppError> {
    let space = sqlx::query_as!(
        ContextSpaceRecord,
        "SELECT id, name, project_id FROM context_spaces WHERE id = $1",
        id
    )
    .fetch_optional(&pool)
    .await?
    .ok_or(AppError::NotFound("Space not found".into()))?;

    Ok(Json(space.into()))
}
```

## 3. Database Migrations (sqlx)

Database queries must be checked at compile time using `sqlx`. Migrations live in `crates/portal-api/migrations/` as standard SQL files:

```bash
# Create a new migration
sqlx migrate add create_context_spaces

# Run migrations against local database
sqlx migrate run
```

## Related

- [00-intro](00-intro.md) — development overview.
- [06-configuration-as-code](../Architecture/06-configuration-as-code.md) — how changes reach the platform.
