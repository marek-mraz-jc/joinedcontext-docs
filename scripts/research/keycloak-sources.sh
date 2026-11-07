#!/usr/bin/env bash
# Re-measures the token counts of the wardkeep Argon pack plan (Research/rust/keycloak.md section 9).
# Clones the pinned upstream sources (Keycloak 26.8.1, FIWARE VCVerifier 6.31.0) into WORK and runs
# repomix over each pack group. Our own repositories are measured from sibling clones when present.
# Usage: scripts/research/keycloak-sources.sh [WORK_DIR]   (default: ${TMPDIR:-/tmp}/wardkeep-sources)
set -euo pipefail

WORK=${1:-${TMPDIR:-/tmp}/wardkeep-sources}
REPOMIX=${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}
KC_TAG=26.8.1          # quay.io/keycloak/keycloak:26.8.1, deployment components/keycloak/images.yaml
VCV_TAG=6.31.0         # FIWARE/VCVerifier, newest release tag on 2026-11-07
HERE=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$WORK"

if [ ! -d "$WORK/kc" ]; then
  git clone -q --depth 1 --branch "$KC_TAG" --filter=blob:none --sparse \
    https://github.com/keycloak/keycloak.git "$WORK/kc"
  git -C "$WORK/kc" sparse-checkout set services server-spi server-spi-private model/jpa docs \
    federation crypto/default common tests/conformance
fi
if [ ! -d "$WORK/vcv" ]; then
  git clone -q --depth 1 --branch "$VCV_TAG" https://github.com/FIWARE/VCVerifier.git "$WORK/vcv"
fi
echo "keycloak $(git -C "$WORK/kc" rev-parse HEAD) ($KC_TAG)"
echo "vcverifier $(git -C "$WORK/vcv" rev-parse HEAD) ($VCV_TAG)"

S=services/src/main/java/org/keycloak
D=docs/documentation/server_admin/topics
G=docs/guides

# group name | repo dir | comma-separated include globs
PACKS=(
"A1-protocol|kc|$S/protocol/oidc/**,$S/protocol/oauth2/**,$S/protocol/AuthorizationEndpointBase.java,$S/protocol/LoginProtocol*.java,$S/services/managers/AuthenticationManager.java,$S/services/managers/AuthenticationSessionManager.java,$S/services/managers/UserSessionManager.java,$S/services/managers/DefaultBruteForceProtector.java,$S/broker/kubernetes/**,$S/keys/**,$S/jose/**"
"A2-login-orgs|kc|$S/authentication/**,$S/organization/**,$S/credential/**,$S/forms/login/freemarker/model/**,common/src/main/java/org/keycloak/common/Profile.java,crypto/default/src/main/java/org/keycloak/crypto/hash/**,server-spi-private/src/main/java/org/keycloak/credential/hash/**"
"A3-model-docs|kc|server-spi/src/main/java/org/keycloak/models/*.java,server-spi/src/main/java/org/keycloak/models/credential/**,model/jpa/src/main/java/org/keycloak/models/jpa/entities/**,model/jpa/src/main/java/org/keycloak/organization/jpa/**,$D/organizations/**,$D/authentication/**,$D/sessions/**,$D/threat/**,$D/clients/**,$G/securing-apps/token-exchange.adoc,$G/securing-apps/mcp-authz-server.adoc,$G/securing-apps/dpop.adoc,$G/server/hostname.adoc,$G/server/caching.adoc,$G/server/db.adoc"
"B1-admin-federation|kc|$S/services/resources/admin/**,$S/events/**,$S/partialimport/**,$S/exportimport/**,federation/ldap/src/main/java/**,$D/admin-console-permissions/**,$D/user-federation/**,$D/identity-broker/**,$D/events/**,$D/users/**,$D/roles-groups/**"
"C1-vc|kc|$S/protocol/oid4vc/**,$S/broker/oid4vp/**,$S/broker/trust/**,$D/oid4vci/**"
"C2-vcverifier|vcv|**/*.go,api/*.yaml,docs/*.md,README.md,server.yaml"
)

total=0
printf '%-22s %10s %6s\n' group tokens files
for g in "${PACKS[@]}"; do
  IFS='|' read -r name dir globs <<<"$g"
  out="$WORK/$name.xml"
  log=$( (cd "$WORK/$dir" && "$REPOMIX" --include "$globs" --ignore '**/*_test.go,**/test/**,**/integration_test/**' \
    --remove-comments --remove-empty-lines --no-security-check -o "$out") 2>&1 )
  tok=$(grep -oE 'Total Tokens: [0-9,]+' <<<"$log" | tr -dc '0-9')
  files=$(grep -oE 'Total Files: [0-9,]+' <<<"$log" | tr -dc '0-9')
  printf '%-22s %10s %6s\n' "$name" "${tok:-?}" "${files:-?}"
  total=$((total + ${tok:-0}))
done

# Our side: the files a wardkeep generation must read (paths relative to /workspace/agents/<you>).
OURS=$(cd "$HERE/.." && pwd)
measure_ours() { # name dir globs
  if [ -d "$OURS/$2" ]; then
    log=$( (cd "$OURS/$2" && "$REPOMIX" --include "$3" --remove-empty-lines --no-security-check -o "$WORK/$1.xml") 2>&1 )
    printf '%-22s %10s %6s\n' "$1" "$(grep -oE 'Total Tokens: [0-9,]+' <<<"$log" | tr -dc '0-9')" \
      "$(grep -oE 'Total Files: [0-9,]+' <<<"$log" | tr -dc '0-9')"
  else
    printf '%-22s %10s\n' "$1" "missing $2"
  fi
}
measure_ours O1-deployment joinedcontext-deployment 'components/keycloak/**,components/*/keycloak-clients.yaml'
measure_ours O2-portal joinedcontext-portal 'src/people.rs,src/auth/**,src/reconciler/groups.rs,src/reconciler/workload_clients.rs,src/reconciler/app_clients.rs,src/reconciler/mcp_clients.rs,src/reconciler/hub_scopes.rs,src/connectors.rs'
measure_ours O3-platform joinedcontext-platform 'crates/jc-core/src/auth/**,crates/context-gateway/src/auth/**'
measure_ours O4-docs docs 'Architecture/12-identity-and-access.md,Architecture/18-data-space-connector.md,Decisions/adr-n-058*.md,Decisions/adr-n-061*.md,Decisions/adr-n-064*.md,Decisions/adr-n-067*.md,Research/rust/keycloak.md'
echo "upstream total: $total"
