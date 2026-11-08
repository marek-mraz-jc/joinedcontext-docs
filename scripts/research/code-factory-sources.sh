#!/usr/bin/env bash
# Re-measures the token counts of the code-factory Argon pack plan (Research/rust/code-factory.md
# section 8). Clones the pinned upstream sources (sparse, at the release tags recorded below) into
# WORK and runs repomix over each pack group; our own repositories are measured from the sibling
# clones of this docs clone when present, the swarm scripts from /workspace/tasks.
# Usage: scripts/research/code-factory-sources.sh [WORK_DIR]   (default: ${TMPDIR:-/tmp}/code-factory-sources)
set -euo pipefail

WORK=${1:-${TMPDIR:-/tmp}/code-factory-sources}
REPOMIX=${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}
HERE=$(cd "$(dirname "$0")/../.." && pwd)
OURS=$(cd "$HERE/.." && pwd)
mkdir -p "$WORK"

# name | repo | tag | sparse paths
CLONES=(
"codex|openai/codex|rust-v0.167.0|codex-rs"
"sdk|OpenHands/software-agent-sdk|v1.60.1|openhands-sdk openhands-tools openhands-workspace openhands-agent-server"
"goose|aaif-goose/goose|v1.57.0|crates"
"acp|agentclientprotocol/agent-client-protocol|schema-v1.29.1|agent-client-protocol-schema docs"
)
for c in "${CLONES[@]}"; do
  IFS='|' read -r name repo tag paths <<<"$c"
  if [ ! -d "$WORK/$name" ]; then
    git clone -q --depth 1 --branch "$tag" --filter=blob:none --sparse "https://github.com/$repo.git" "$WORK/$name"
    # shellcheck disable=SC2086
    git -C "$WORK/$name" sparse-checkout set $paths
  fi
  echo "$name $(git -C "$WORK/$name" rev-parse HEAD) ($tag)"
done

measure() { # name dir globs [ignore]
  if [ ! -d "$2" ]; then printf '%-24s %10s\n' "$1" "missing $2"; return; fi
  local log
  log=$( (cd "$2" && "$REPOMIX" --include "$3" --ignore "${4:-**/tests/**,**/test/**,**/*_test.go,**/*_tests.rs,**/snapshots/**}" \
    --remove-comments --remove-empty-lines --no-security-check -o "$WORK/$1.xml") 2>&1 )
  printf '%-24s %10s %6s\n' "$1" "$(grep -oE 'Total Tokens: [0-9,]+' <<<"$log" | tr -dc '0-9')" \
    "$(grep -oE 'Total Files: [0-9,]+' <<<"$log" | tr -dc '0-9')"
}

C=codex-rs
O=openhands-sdk/openhands/sdk
printf '%-24s %10s %6s\n' group tokens files
measure U1-codex-agents "$WORK/codex" "$C/core/src/agent/**,$C/core/src/tools/multi_agent_tool.rs,$C/core/src/session/multi_agents.rs,$C/core/src/agent_communication.rs,$C/agent-roles/src/**,$C/agent-graph-store/src/**,$C/message-board/src/**,$C/core/src/session/token_budget.rs,$C/core/src/rollout_budget.rs,$C/protocol/src/protocol.rs,$C/protocol/src/config_types.rs"
measure U2-codex-sandbox "$WORK/codex" "$C/linux-sandbox/src/**,$C/linux-sandbox/README.md,$C/sandboxing/src/**,$C/execpolicy/src/**,$C/execpolicy/README.md,$C/core/src/exec_policy.rs,$C/core/src/tools/approvals.rs"
measure U3-openhands-sdk "$WORK/sdk" "$O/agent/agent.py,$O/agent/acp_agent.py,$O/conversation/state.py,$O/conversation/event_store.py,$O/subagent/**,$O/security/*.py,$O/llm/router/**,$O/llm/utils/metrics.py,$O/context/condenser/**,openhands-tools/openhands/tools/delegate/**,openhands-tools/openhands/tools/task/**,openhands-workspace/openhands/workspace/docker/**,openhands-workspace/openhands/workspace/remote_api/**"
measure U4-goose "$WORK/goose" "crates/goose/src/agents/state_machine/**,crates/goose/src/agents/subagent_handler.rs,crates/goose/src/agents/platform_extensions/summon.rs,crates/goose/src/recipe/**,crates/goose/src/scheduler/**,crates/goose/src/config/permission.rs,crates/goose/src/permission/**,crates/goose/src/security/**,crates/goose-agent/src/**"
measure U5-acp "$WORK/acp" "docs/protocol/v1/overview.mdx,docs/protocol/v1/initialization.mdx,docs/protocol/v1/session-setup.mdx,docs/protocol/v1/prompt-turn.mdx,docs/protocol/v1/tool-calls.mdx,docs/protocol/v1/file-system.mdx,docs/protocol/v1/terminals.mdx,docs/protocol/v1/agent-plan.mdx,docs/protocol/v1/security.mdx,docs/protocol/v1/transports.mdx,docs/protocol/v1/cancellation.mdx,docs/protocol/v1/content.mdx"
measure O1-portal-agents "$OURS/joinedcontext-portal" "src/agents/**,src/apps/build_pods.rs,src/apps/built.rs,src/apps/reconciler.rs,src/connectors.rs,src/ops/runs.rs,src/costs.rs,src/quotas.rs" "**/tests/**,src/agents/oneshot/**"
measure O2-platform "$OURS/joinedcontext-platform" "crates/wasm-host/src/**,crates/wasm-host/Cargo.toml,crates/agent-proxy/src/**"
measure O3-docs "$OURS/docs" "Architecture/16-apps-on-demand.md,Architecture/19-agent-runner.md,Architecture/20-app-sdk.md,Decisions/adr-n-044*.md,Research/rust/code-factory.md"
measure O4-swarm /workspace/tasks "README.md,next,batches,claim,push,automerge,autoreview,autocheck,train,uijudge,bounce,merge" "**/*.bak*"
