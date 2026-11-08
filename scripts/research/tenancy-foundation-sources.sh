#!/usr/bin/env bash
# Re-measures the token counts of the Argon pack plan in Research/rust/tenancy-foundation.md §8.
# Usage: tenancy-foundation-sources.sh [CODE_DIR] [EKIBEN_DIR]
#   CODE_DIR holds checkouts named joinedcontext-platform, joinedcontext-portal and
#   Antares-NGSI-LD-Context-Broker (default /workspace/.cache/cg-main).
#   EKIBEN_DIR is an ekiben checkout (default: ../ekiben beside this docs checkout).
# Needs repomix 1.18 (REPOMIX, default the shared npx cache copy). Prints one line per part,
# a total per run and the sha of every tree read.
set -euo pipefail
DOCS="$(cd "$(dirname "$0")/../.." && pwd)"
CODE="${1:-/workspace/.cache/cg-main}"
EKIBEN="${2:-$DOCS/../ekiben}"
REPOMIX="${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}"
OUT="$(mktemp -d)"
trap 'rm -rf "${OUT:?}"' EXIT
PLATFORM="$CODE/joinedcontext-platform"
PORTAL="$CODE/joinedcontext-portal"
ANTARES="$CODE/Antares-NGSI-LD-Context-Broker"
ASKAMA="${ASKAMA:-$HOME/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f}"

for tree in "$DOCS" "$PLATFORM" "$PORTAL" "$ANTARES" "$EKIBEN"; do
  printf 'tree %s %s\n' "$(basename "$tree")" "$(git -C "$tree" rev-parse --short HEAD)"
done

total=0
measure() { # run part root include-globs
  local run="$1" part="$2" root="$3" include="$4" tokens
  tokens=$(cd "$root" && "$REPOMIX" --include "$include" -o "$OUT/$run-$part.xml" --no-security-check 2>&1 |
    sed -n 's/.*Total Tokens: \([0-9,]*\).*/\1/p' | tr -d ,)
  printf '%-2s %-22s %8s\n' "$run" "$part" "${tokens:-0}"
  total=$((total + ${tokens:-0}))
}
end_run() { printf '%-2s %-22s %8s\n\n' "$1" "TOTAL" "$total"; total=0; }

# Run A: jc-auth, tenancy types, RLS store layer, isolation tests.
measure A docs "$DOCS" "Research/rust/tenancy-foundation.md,Research/next-platform/02-architecture.md,Research/next-platform/03-identity-and-authz.md,Research/next-platform/04-isolation-threat-model.md,Architecture/12-identity-and-access.md,Architecture/13-security.md,Decisions/adr-n-035-*.md,Decisions/adr-n-041-*.md,Decisions/adr-n-050-*.md,Decisions/adr-n-058-*.md,Decisions/adr-n-061-*.md,Decisions/adr-n-064-*.md,Decisions/adr-n-066-*.md,Decisions/adr-n-067-*.md"
measure A jc-core-kinds "$PLATFORM" "crates/jc-core/src/kinds/organization.rs,crates/jc-core/src/kinds/org_settings.rs,crates/jc-core/src/kinds/space.rs,crates/jc-core/src/kinds/role.rs,crates/jc-core/src/kinds/service_account.rs,crates/jc-core/src/kinds/group.rs,crates/jc-core/src/kinds/policy.rs,crates/jc-core/src/kinds/delegation_policy.rs,crates/jc-core/src/kinds/endpoint.rs,crates/jc-core/src/auth/**"
measure A gateway-auth "$PLATFORM" "crates/context-gateway/src/auth/subject.rs,crates/context-gateway/src/middleware/tenancy.rs,crates/context-gateway/src/pdp/mod.rs,crates/context-gateway/src/pdp/evaluator.rs,crates/context-gateway/src/pdp/write_guard.rs"
measure A assistant-rls "$PLATFORM" "crates/assistant/migrations/**,crates/assistant/src/lib.rs,crates/wasm-host/src/limits.rs"
measure A portal-authz "$PORTAL" "src/permissions.rs,src/connectors.rs,src/personal_data.rs,src/quotas.rs,src/activity.rs,migrations/0012_activity.sql,migrations/0051_connectors.sql"
measure A antares-policy "$ANTARES" "addons/joinedcontext-policy/src/**,crates/antares-api/src/admin_auth.rs,crates/antares-api/src/provenance.rs"
measure A antares-rls "$ANTARES" "crates/antares-sql/migrations/0001_init.sql,crates/antares-sql/migrations/0005_*.sql,crates/antares-sql/migrations/0015_*.sql,crates/antares-sql/migrations/0024_*.sql,crates/antares-sql/migrations/0027_*.sql,crates/antares-sql/src/lib.rs,crates/antares-sql/tests/pg_rls_pentest.rs,crates/antares-sql/tests/rls_covers_every_table.rs"
measure A ekiben-org "$EKIBEN" "REPOSITORY.md,crates/ekiben-core/src/org.rs,crates/ekiben-server/src/api.rs,crates/jc-auth/README.md,crates/jc-core/README.md,crates/identity/README.md"
end_run A

# Run B: jc-ops registry, jc-odata over module tables, CLI, MCP situation tools.
measure B docs "$DOCS" "Research/rust/tenancy-foundation.md,Decisions/adr-n-063-*.md,Decisions/adr-n-064-*.md,Research/next-platform/08-management-api-and-testing.md"
measure B portal-ops "$PORTAL" "src/ops/mod.rs,src/ops/views.rs,src/ops/pipeline_runs.rs,src/mcp/connector.rs,src/api/connectors.rs,src/personal_data.rs"
measure B antares-odata "$ANTARES" "crates/odata-url/src/**,crates/odata-csdl/src/**,crates/odata-axum/src/**"
measure B antares-mcp "$ANTARES" "crates/antares-mcp/src/tools.rs,crates/antares-mcp/src/server.rs,crates/antares-mcp/src/summary.rs,crates/antares-mcp/src/area.rs,crates/antares-mcp/src/budget.rs"
measure B jcctl "$PLATFORM" "crates/jcctl/src/main.rs"
end_run B

# Run C: jc-web, the server-rendered HTML shell every module adds pages to.
measure C docs "$DOCS" "Research/rust/tenancy-foundation.md,scripts/research/tenancy-foundation-templating/**"
measure C portal-csp "$PORTAL" "src/csp.rs,ui/src/cspNonce.ts,ui/src/index.css"
if [ -d "$ASKAMA/askama-0.16.1" ]; then
  measure C askama-0.16.1 "$ASKAMA/askama-0.16.1" "src/**,README.md"
fi
end_run C
