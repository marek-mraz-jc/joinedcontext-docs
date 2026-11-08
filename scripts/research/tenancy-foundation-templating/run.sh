#!/bin/bash
cd "$(dirname "$0")"
unset RUSTC_WRAPPER
for e in ${ENGINES:-askama maud minijinja}; do
  ( cd t-$e
    s=$(date +%s.%N); CARGO_TARGET_DIR=$PWD/target cargo build -q --release 2>&1 | tail -5; f=$(date +%s.%N)
    echo "$e cold_release_build_s=$(echo "$f-$s"|bc)"
    touch src/main.rs; s=$(date +%s.%N); CARGO_TARGET_DIR=$PWD/target cargo build -q --release; f=$(date +%s.%N)
    echo "$e incremental_release_build_s=$(echo "$f-$s"|bc) bin_bytes=$(stat -c %s target/release/t-$e)"
    ./target/release/t-$e; ./target/release/t-$e )
done
echo "deps:"; for e in askama maud minijinja; do (cd t-$e; echo "$e $(cargo tree -e normal --prefix none 2>/dev/null | sort -u | wc -l) crates"); done
uptime
