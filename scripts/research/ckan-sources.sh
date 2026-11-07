#!/usr/bin/env bash
# Re-measures the token counts of the CKAN -> dataroom Argon pack (Research/rust/ckan.md section 10).
# Clones the pinned upstream sources into $WORK (default: a temp dir), runs repomix over each pack slice
# and prints one "slice<TAB>files<TAB>tokens" line per slice plus the run totals.
# Usage: scripts/research/ckan-sources.sh [--work DIR] [--ours DIR]
#   --ours DIR  a directory holding joinedcontext-deployment, joinedcontext-platform and joinedcontext-portal clones
#               (default: the parent of this docs clone); our slices are skipped when a clone is missing.
set -euo pipefail

WORK=""
OURS="$(cd "$(dirname "$0")/../../.." && pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --work) WORK="$2"; shift 2 ;;
    --ours) OURS="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [ -z "$WORK" ]; then WORK="$(mktemp -d)"; fi
REPOMIX="${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}"
command -v "$REPOMIX" >/dev/null || REPOMIX="npx --yes repomix@1.18.1"

# repo, ref (tag or commit): the pins the document cites.
PINS="
ckan/ckan ckan-2.11.6
ckan/ckanext-dcat v2.4.4
ckan/ckanext-harvest 37baba6
ckan/ckanext-scheming de22cc4
ckan/ckanext-fluent eb5581a
ckan/ckanext-spatial 119376f
ckan/ckanext-pages 28eba99
ckan/ckanext-showcase acc2665
ckan/ckanext-validation df68598
DataShades/ckanext-oidc-pkce v0.4.1
"

clone() {
  local repo="$1" ref="$2" dir
  dir="$WORK/$(basename "$1")"
  [ -d "$dir/.git" ] && return 0
  if ! git clone -q --depth 1 --branch "$ref" "https://github.com/$repo.git" "$dir" 2>/dev/null; then
    git clone -q "https://github.com/$repo.git" "$dir"
    git -C "$dir" checkout -q "$ref"
  fi
}
echo "$PINS" | while read -r repo ref; do if [ -n "$repo" ]; then clone "$repo" "$ref"; fi; done

# slice name, root directory, comma-separated include globs, comma-separated ignore globs
measure() {
  local name="$1" root="$2" include="$3" ignore="${4:-}"
  if [ ! -d "$root" ]; then printf '%s\tmissing\t0\n' "$name"; return; fi
  local out
  # shellcheck disable=SC2086 # REPOMIX may be "npx --yes repomix@x"
  out="$(cd "$root" || exit 0; $REPOMIX --no-gitignore --include "$include" ${ignore:+--ignore "$ignore"} \
        --style plain --output /dev/null --no-file-summary --no-security-check 2>/dev/null || true)"
  local files tokens
  files="$(printf '%s\n' "$out" | sed -n 's/.*Total Files: *\([0-9,]*\).*/\1/p' | tr -d ,)"
  tokens="$(printf '%s\n' "$out" | sed -n 's/.*Total Tokens: *\([0-9,]*\).*/\1/p' | tr -d ,)"
  printf '%s\t%s\t%s\n' "$name" "${files:-0}" "${tokens:-0}"
}

U="$WORK"
T="**/tests/**,**/test_*.py,**/*.min.js,**/i18n/**,**/public/**,**/assets/**,**/migration/**"
{
  echo "# run 1: core, API, search, auth"
  measure core-logic        "$U/ckan" "ckan/logic/**/*.py,ckan/authz.py,ckan/lib/api_token.py" "$T"
  measure core-model        "$U/ckan" "ckan/model/**/*.py,ckan/lib/dictization/**/*.py" "$T"
  measure core-search       "$U/ckan" "ckan/lib/search/**/*.py,ckan/config/solr/schema.xml" "$T"
  measure core-plugins      "$U/ckan" "ckan/plugins/**/*.py,ckan/lib/plugins.py" "$T"
  measure core-views-api    "$U/ckan" "ckan/views/api.py,ckan/views/__init__.py,ckan/views/dataset.py,ckan/views/resource.py,ckan/views/group.py,ckan/views/user.py,ckan/views/feed.py,ckan/config/middleware/flask_app.py" "$T"
  measure core-config       "$U/ckan" "ckan/config/config_declaration.yaml" ""
  measure ext-activity      "$U/ckan" "ckanext/activity/**/*.py" "$T"
  measure ext-datastore     "$U/ckan" "ckanext/datastore/**/*.py,ckanext/datastore/config_declaration.yaml" "$T"
  measure doc-api           "$U/ckan" "doc/api/**/*.rst,doc/maintaining/authorization.rst,doc/maintaining/configuration.rst" ""
  echo "# run 2: plugins, DCAT, harvest"
  measure doc-extensions    "$U/ckan" "doc/extensions/**/*.rst" ""
  measure ext-views         "$U/ckan" "ckanext/datatablesview/**/*.py,ckanext/textview/**/*.py,ckanext/imageview/**/*.py,ckanext/multilingual/**/*.py" "$T"
  measure dcat              "$U/ckanext-dcat" "ckanext/dcat/**/*.py,docs/**/*.md,ckanext/dcat/schemas/*.yaml" "$T"
  measure harvest           "$U/ckanext-harvest" "ckanext/harvest/**/*.py,README.rst" "$T"
  measure scheming          "$U/ckanext-scheming" "ckanext/scheming/**/*.py,ckanext/scheming/**/*.yaml,ckanext/scheming/**/*.json,README.md" "$T"
  measure fluent            "$U/ckanext-fluent" "ckanext/fluent/**/*.py,README.md" "$T"
  measure pages-showcase    "$U" "ckanext-pages/ckanext/pages/**/*.py,ckanext-showcase/ckanext/showcase/**/*.py" "$T"
  measure validation        "$U/ckanext-validation" "ckanext/validation/**/*.py,README.md" "$T"
  measure oidc-pkce         "$U/ckanext-oidc-pkce" "ckanext/oidc_pkce/**/*.py,README.md" "$T"
  echo "# run 3: UI and theme"
  measure spatial           "$U/ckanext-spatial" "ckanext/spatial/**/*.py,doc/**/*.rst" "$T"
  measure doc-theming       "$U/ckan" "doc/theming/**/*.rst" ""
  measure core-templates    "$U/ckan" "ckan/templates/package/**,ckan/templates/organization/**,ckan/templates/home/**,ckan/templates/snippets/**,ckan/templates/page.html,ckan/templates/base.html" ""
  echo "# ours (named per run in the document)"
  measure ours-deployment   "$OURS/joinedcontext-deployment" "components/ckan/README.md,components/ckan/apisix-routes.yaml,charts/ckan/values.yaml,charts/ckan/templates/ckan.yaml,charts/ckan/templates/harvest.yaml,charts/ckan/files/*.py,charts/ckan/files/startup/*,charts/ckan/files/jc_theme/*.py,images/ckan/Dockerfile" ""
  measure ours-theme-ui     "$OURS/joinedcontext-deployment" "charts/ckan/files/jc_theme/templates__*.html,charts/ckan/files/jc_theme/public__jc-*.js,charts/ckan/files/jc_theme/public__jc-theme.css" ""
  measure ours-jcctl        "$OURS/joinedcontext-platform" "crates/jcctl/src/publish/**,crates/jc-core/src/kinds/ckan.rs,crates/jc-core/src/kinds/catalog.rs" ""
  measure ours-portal       "$OURS/joinedcontext-portal" "src/reconciler/ckan.rs,src/reconciler/catalog.rs,src/api/catalogue.rs" ""
} | tee "$WORK/ckan-sources.tsv"
echo "# work dir: $WORK"
