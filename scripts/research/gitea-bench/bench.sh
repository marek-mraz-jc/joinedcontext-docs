#!/usr/bin/env bash
# Clone/push benchmark of server-side Git candidates for shako (Research/rust/gitea.md section 3.4).
# Needs git, python3, cargo, docker, k6. Ports 42210 (git http-backend) and 42211 (Gitea) on 127.0.0.1.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
export BENCH=${BENCH:-$(mktemp -d)}
IMAGE='docker.gitea.com/gitea:1.27.3-rootless@sha256:1c17ecaead42eb3b5391553d8708103a4beb0e86edf5b9ebc1eb269c318845f2'
cd "$BENCH"
# 1. A ~100 MB repository: 121 commits over 400 text files plus 49 random 1.5 MB blobs.
git init -q -b master src && git -C src config user.email bench@example.invalid && git -C src config user.name bench
python3 - <<'PY'
import os, random
random.seed(7); r = random.Random(7)
words = [f"w{i}" for i in range(3000)]
os.makedirs("src/code"); os.makedirs("src/bin")
for i in range(400):
    open(f"src/code/f{i}.go", "w").write(" ".join(r.choice(words) for _ in range(6000)))
for i in range(30):
    open(f"src/bin/b{i}.dat", "wb").write(os.urandom(1_500_000))
PY
git -C src add -A && git -C src commit -qm init
for c in $(seq 1 120); do
  python3 - "$c" <<'PY'
import os, random, sys
c = int(sys.argv[1]); r = random.Random(c)
for i in r.sample(range(400), 20):
    p = f"src/code/f{i}.go"; s = open(p).read().split()
    for _ in range(200): s[r.randrange(len(s))] = r.choice(s)
    open(p, "w").write(" ".join(s))
if c % 12 == 0: open(f"src/bin/n{c}.dat", "wb").write(os.urandom(1_500_000))
if c == 120:
    for i in range(19): open(f"src/bin/x{i}.dat", "wb").write(os.urandom(1_500_000))
PY
  git -C src add -A && git -C src commit -qm "c$c"
done
git -C src repack -adq && git -C src count-objects -vH | grep size-pack
git clone -q --bare src srv.git
# 2. The Rust candidates.
cargo build --release -q --manifest-path "$here/rsbench/Cargo.toml"
export RSBENCH=${CARGO_TARGET_DIR:-$here/rsbench/target}/release/rsbench
python3 "$here/run.py" "$here/micro.py"
# 3. End to end over HTTP: git http-backend and Gitea.
mkdir -p hb && python3 "$here/cgi.py" "$BENCH/hb" & cgi=$!
head -c 18 /dev/urandom | base64 | tr -d '/+=' > .pw && chmod 600 .pw
docker run -d --name gbench --network host -e GITEA__security__INSTALL_LOCK=true -e GITEA__database__DB_TYPE=sqlite3 \
  -e GITEA__server__HTTP_PORT=42211 -e GITEA__server__ROOT_URL=http://127.0.0.1:42211/ \
  -e GITEA__repository__ENABLE_PUSH_CREATE_USER=true -e GITEA__server__DISABLE_SSH=true -e GITEA__log__LEVEL=Warn "$IMAGE" >/dev/null
trap 'docker rm -f gbench >/dev/null; kill $cgi' EXIT
for _ in $(seq 30); do curl -sf http://127.0.0.1:42211/api/healthz >/dev/null && break; sleep 2; done
docker exec gbench gitea admin user create --username bench --password "$(cat .pw)" --email bench@example.invalid --admin --must-change-password=false >/dev/null
python3 "$here/run.py" "$here/e2e.py"
echo "Gitea cgroup memory.peak after git runs: $(docker exec gbench cat /sys/fs/cgroup/memory.peak)"
# 4. 100 req/s of the API reads the Portal makes most, 60 s.
k6 run -q -e BENCH="$BENCH" "$here/k6.js"
docker stats --no-stream gbench
echo "Gitea cgroup memory.peak after k6: $(docker exec gbench cat /sys/fs/cgroup/memory.peak)"
