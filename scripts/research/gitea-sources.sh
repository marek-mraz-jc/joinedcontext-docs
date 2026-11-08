#!/usr/bin/env bash
# Re-measure the token counts of the Argon pack plan in Research/rust/gitea.md (section 9).
# Usage: scripts/research/gitea-sources.sh [workdir]
#   GITEA_SRC  an existing checkout of go-gitea/gitea at v1.27.3 (else cloned into workdir)
#   PORTAL, DEPLOYMENT, PLATFORM  our clones (default: siblings of this docs clone)
#   REPOMIX    repomix binary (default: the shared npx cache copy, 1.18.1)
set -euo pipefail
TAG=v1.27.3
COMMIT=146cc3eec57174711eac0e0a0c7b38670c6e3922
here=$(cd "$(dirname "$0")/../.." && pwd)
work=${1:-$(mktemp -d)}
REPOMIX=${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}
PORTAL=${PORTAL:-$here/../joinedcontext-portal}
DEPLOYMENT=${DEPLOYMENT:-$here/../joinedcontext-deployment}
PLATFORM=${PLATFORM:-$here/../joinedcontext-platform}
src=${GITEA_SRC:-$work/gitea}
if [ ! -d "$src/.git" ]; then
  git clone -q --depth 1 --branch "$TAG" https://github.com/go-gitea/gitea.git "$src"
fi
got=$(git -C "$src" rev-parse HEAD)
[ "$got" = "$COMMIT" ] || { echo "gitea checkout is $got, want $COMMIT ($TAG)" >&2; exit 1; }

NOTEST='**/*_test.go,**/testdata/**,**/*.test.ts'
count() { # name dir include
  local out="$work/$1.xml" log
  log=$(cd "$2" && "$REPOMIX" --no-git-sort-by-changes --style xml \
     --include "$3" --ignore "$NOTEST" -o "$out" . 2>&1)
  local files tokens
  files=$(grep -c '<file path=' "$out")
  tokens=$(printf '%s\n' "$log" | sed -n 's/.*Total Tokens: \([0-9,]*\).*/\1/p' | tr -d ,)
  echo "| $1 | $files | $(wc -c < "$out") | $tokens |"
}
echo "| Part | Files | Bytes | Tokens (repomix o200k) |"
echo "|---|---|---|---|"
count R1-git-core "$src" 'routers/web/githttp.go,routers/web/repo/githttp.go,routers/private/**,cmd/hook.go,cmd/serv.go,modules/git/**,modules/gitrepo/**,services/lfs/**,modules/lfs/**,models/perm/**,models/organization/**,models/repo/collaboration.go,models/repo/repo.go,models/git/protected_branch*.go,models/git/protected_tag.go,models/unit/**'
count R2-api-pulls "$src" 'routers/api/v1/repo/file.go,routers/api/v1/repo/pull.go,routers/api/v1/repo/pull_review.go,routers/api/v1/repo/branch.go,routers/api/v1/repo/tree.go,routers/api/v1/repo/commits.go,routers/api/v1/repo/repo.go,routers/api/v1/repo/collaborators.go,routers/api/v1/repo/hook.go,routers/api/v1/repo/mirror.go,routers/api/v1/repo/migrate.go,routers/api/v1/org/team.go,routers/api/v1/org/org.go,services/repository/files/**,services/pull/**,services/webhook/deliver.go,services/webhook/webhook.go,services/webhook/gitea.go,modules/structs/repo*.go,modules/structs/pull*.go,modules/structs/org*.go,modules/structs/hook*.go'
count R3-packages-actions "$src" 'routers/api/packages/api.go,routers/api/packages/container/**,routers/api/packages/generic/**,services/packages/auth.go,services/packages/packages.go,services/packages/container/**,models/packages/package.go,models/packages/package_version.go,models/packages/package_file.go,models/packages/package_blob.go,routers/api/actions/**,models/actions/**,services/actions/**'
count R4-ui-auth "$src" 'templates/repo/home.tmpl,templates/repo/view*.tmpl,templates/repo/blame.tmpl,templates/repo/commits*.tmpl,templates/repo/diff/**,templates/repo/pulls/**,templates/repo/issue/view_content/pull_merge_box.tmpl,routers/web/repo/view*.go,routers/web/repo/blame.go,routers/web/repo/commit.go,routers/web/repo/compare.go,routers/web/repo/pull.go,routers/web/repo/download.go,routers/web/repo/repo.go,services/auth/source/oauth2/**,routers/web/auth/oauth.go,routers/web/auth/linkaccount.go'
count ours-portal "$PORTAL" 'src/git/gitea.rs,src/api/webhook.rs,src/apps/build_pods.rs,src/reconciler/project_teams.rs'
count ours-deployment "$DEPLOYMENT" 'components/gitea/values/**,components/gitea/charts/bootstrap/templates/job.yaml,components/gitea/networkpolicies.yaml,components/gitea-runner/values/**'
count ours-platform "$PLATFORM" 'crates/agent-proxy/src/routes/forge.rs,crates/jcctl/src/commands/checkouts.rs,crates/jc-core/src/kinds/organization.rs,crates/jc-core/src/kinds/project.rs'
