#!/bin/sh
# Re-measure the token counts of the ekiben Argon pack slices (Research/rust/bento.md section 8).
# Usage: scripts/research/bento-sources.sh [bento-dir] [ekiben-dir] [portal-dir] [platform-dir]
# Without bento-dir it clones Bento v1.22.0 into a temporary directory. Prints "slice<TAB>files<TAB>tokens".
set -eu
TAG=v1.22.0
SHA=2fbbce3076619cd18c28f2dc23fd413a49744250
REPOMIX=${REPOMIX:-/workspace/.cache/npm/_npx/cad0f0e99bf115c9/node_modules/.bin/repomix}
WORK=$(mktemp -d)
trap 'rm -rf "${WORK:?}"' EXIT
BENTO=${1:-}
if [ -z "$BENTO" ]; then
  BENTO=$WORK/bento
  git clone -q --depth 1 --branch "$TAG" https://github.com/warpstreamlabs/bento.git "$BENTO" 2>/dev/null
fi
[ "$(git -C "$BENTO" rev-parse HEAD)" = "$SHA" ] || { echo "bento is not $TAG ($SHA)" >&2; exit 1; }
EKIBEN=${2:-/workspace/ekiben}
PORTAL=${3:-/workspace/joinedcontext-portal}
PLATFORM=${4:-/workspace/joinedcontext-platform}

measure() { # name dir include [ignore]
  out=$("$REPOMIX" "$2" --include "$3" --ignore "${4:-.git/**}" --no-git-sort-by-changes -o "$WORK/p.xml" 2>&1) || { echo "$1 repomix failed" >&2; return 1; }
  files=$(printf '%s\n' "$out" | sed -n 's/.*Total Files: *\([0-9,]*\).*/\1/p' | tr -d ,)
  tokens=$(printf '%s\n' "$out" | sed -n 's/.*Total Tokens: *\([0-9,]*\).*/\1/p' | tr -d ,)
  printf '%s\t%s\t%s\n' "$1" "$files" "$tokens"
}
GOSRC='**/*_test.go,**/testdata/**'
printf 'slice\tfiles\ttokens\n'
# Upstream Bento slices
measure up-runtime "$BENTO" 'internal/stream/**/*.go,internal/pipeline/**/*.go,internal/manager/**/*.go,internal/transaction/**/*.go,internal/batch/**/*.go,internal/message/**/*.go,internal/component/**/*.go,internal/bundle/**/*.go,internal/api/**/*.go,internal/autoretry/**/*.go,internal/retries/**/*.go,internal/errorhandling/**/*.go,internal/value/**/*.go,internal/metadata/**/*.go' "$GOSRC"
measure up-plugin-api "$BENTO" 'public/service/**/*.go,public/bloblang/**/*.go,public/wasm/**/*.go,internal/impl/wasm/**/*.go,internal/template/**/*.go' "$GOSRC"
measure up-config-docs-cli "$BENTO" 'internal/config/**/*.go,internal/docs/**/*.go,internal/cli/**/*.go,internal/httpserver/**/*.go,internal/log/**/*.go,internal/tracing/**/*.go' "$GOSRC"
measure up-bloblang "$BENTO" 'internal/bloblang/**/*.go,internal/impl/pure/bloblang_*.go,internal/impl/crypto/bloblang*.go,internal/impl/lang/**/*.go' "$GOSRC"
measure up-bloblang-tests "$BENTO" 'internal/bloblang/**/*_test.go,internal/impl/pure/bloblang_*_test.go'
measure up-pure "$BENTO" 'internal/impl/pure/**/*.go' "$GOSRC"
measure up-io-platform "$BENTO" 'internal/impl/io/**/*.go,internal/impl/nats/**/*.go,internal/impl/sql/**/*.go,internal/impl/parquet/**/*.go,internal/impl/protobuf/**/*.go,internal/impl/msgpack/**/*.go,internal/impl/xml/**/*.go,internal/impl/jsonpath/**/*.go,internal/impl/prometheus/**/*.go,internal/impl/otlp/**/*.go,internal/impl/mqtt/**/*.go,internal/impl/crypto/**/*.go,internal/httpclient/**/*.go,internal/codec/**/*.go,internal/tls/**/*.go' "$GOSRC"
measure up-impl-all "$BENTO" 'internal/impl/**/*.go' "$GOSRC"
measure up-go-all "$BENTO" '**/*.go' "$GOSRC"
measure up-missing-needed "$BENTO" 'internal/impl/mqtt/**/*.go,internal/impl/io/*websocket*.go,internal/impl/nats/**/*.go,internal/impl/sql/**/*.go,internal/impl/pure/bloblang_cache.go,internal/impl/pure/*buffer*.go,internal/impl/pure/*scanner*.go,internal/codec/**/*.go' "$GOSRC"
measure up-wasm "$BENTO" 'internal/impl/wasm/**/*.go,public/wasm/**' "$GOSRC"
measure up-docs-components "$BENTO" 'website/docs/components/**/*.md'
measure up-docs-guides "$BENTO" 'website/docs/guides/**/*.md,website/docs/configuration/**/*.md'
# Our side
DOCS=$(cd "$(dirname "$0")/../.." && pwd)
measure this-doc "$DOCS" 'Research/rust/bento.md'
if [ -d "$EKIBEN/crates" ]; then
  measure ek-src "$EKIBEN" 'crates/ekiben-*/src/**/*.rs,crates/ekiben-*/Cargo.toml,Cargo.toml,REPOSITORY.md'
  measure ek-core "$EKIBEN" 'crates/ekiben-core/src/**/*.rs'
  measure ek-server "$EKIBEN" 'crates/ekiben-server/src/**/*.rs'
  measure ek-io "$EKIBEN" 'crates/ekiben-io-*/src/**/*.rs'
  measure ek-bloblang "$EKIBEN" 'crates/ekiben-bloblang/src/**/*.rs'
  measure ek-tests "$EKIBEN" 'crates/ekiben-*/tests/**,tests/**,scripts/**'
fi
if [ -d "$PORTAL/src" ]; then
  measure portal-streams "$PORTAL" 'src/reconciler/streams.rs,src/reconciler/streams/**/*.rs,src/reconciler/run_queue.rs'
  measure portal-pipeline-api "$PORTAL" 'src/api/pipeline*.rs'
fi
if [ -d "$PLATFORM/crates/jc-core" ]; then
  measure platform-kinds "$PLATFORM" 'crates/jc-core/src/kinds/data_source.rs,crates/jc-core/src/kinds/pipeline*.rs,crates/jc-core/src/kinds/bento_*.rs,crates/jc-core/src/kinds/mapping.rs,crates/jc-core/src/outbound.rs,crates/jc-core/src/secret.rs,crates/jc-core/src/cron.rs'
  measure platform-wasm-host "$PLATFORM" 'crates/wasm-host/src/**/*.rs,crates/wasm-host/Cargo.toml'
  measure platform-manifest-bento "$PLATFORM" 'crates/jc-manifest/src/bento.rs'
fi
