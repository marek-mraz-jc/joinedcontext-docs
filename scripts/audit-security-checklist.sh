#!/usr/bin/env bash
# The phase-1 security acceptance checklist, executed (T-0102, BSI TR-03187).
#
# Deployment/08-security-hardening.md §5 is the source of truth: this script reads the CHK table
# out of that page and runs the command in each row, so a command edited in the documentation is
# the command that runs here. The expected result of each row is asserted by a case below; a CHK
# id in the table with no case is reported rather than skipped, so the checklist cannot grow a
# row that nothing verifies.
#
#   JC_NS=dev JC_API_HOST=api.example.com scripts/audit-security-checklist.sh
#   scripts/audit-security-checklist.sh --selftest      # stubbed binaries, no cluster
#
# Every command is read-only. Nothing here creates, patches or deletes a cluster object.
set -uo pipefail

PAGE=${JC_SECURITY_PAGE:-Deployment/08-security-hardening.md}
NS=${JC_NS:-prod}
API_HOST=${JC_API_HOST:-api.city.example.com}
pass=0; fail=0; skipped=0

note() { printf '%-8s %-8s %s\n' "$1" "$2" "$3"; }

# the command cell of one CHK row, with the namespace and host of this environment substituted
command_of() {
  # a cell may contain an escaped pipe (`\|`), which is not a column separator: hide it before
  # splitting the row and put it back afterwards, or the command is cut in half
  awk -v id="$1" '
    $0 ~ ("\\*\\*" id "\\*\\*") {
      line = $0
      gsub(/\\\|/, "\001", line)
      n = split(line, cell, "|")
      cmd = cell[4]
      gsub(/^ *`|` *$/, "", cmd)
      gsub(/\001/, "|", cmd)
      print cmd
      exit
    }' "$PAGE" | sed "s/-n prod/-n $NS/g; s/get ns prod/get ns $NS/g; s/api\.city\.example\.com/$API_HOST/g"
}

ids_in_page() {
  grep -oE '\*\*CHK-[0-9]+\*\*' "$PAGE" | tr -d '*' | sort -u
}

run() {  # run <command>; its stdout and stderr, whatever it exits with
  eval "$1" 2>&1
}

assert() {  # assert <id> <output>
  local id=$1 out=$2
  case "$id" in
    # jsonpath prints one value per container, on one line or on many depending on the shell
    # quoting the table happens to use, so these three are asserted token by token
    CHK-01) [ -n "$out" ] && ! printf '%s' "$out" | tr -s ' \n' '\n' | grep -qv '^true$'  ;;
    CHK-02) [ -n "$out" ] && ! printf '%s' "$out" | tr -s ' \n' '\n' | grep -qv '^\["ALL"\]$'  ;;
    CHK-03) [ -n "$out" ] && ! printf '%s' "$out" | tr -s ' \n' '\n' | grep -qv '^false$'  ;;
    CHK-04) [ -n "$out" ] && ! printf '%s' "$out" | grep -v '^$' | grep -qv 'Ingress.*Egress' ;;
    CHK-05) [ -n "$out" ] && ! printf '%s' "$out" | grep -v '^$' | grep -qv 'linkerd-proxy' ;;
    CHK-06) printf '%s' "$out" | grep -qE '^enabled +(cluster|all)-authenticated' ;;
    CHK-07) [ -n "$out" ] && ! printf '%s' "$out" | tr -s ' \n' '\n' | grep -qv '^0$'  ;;
    CHK-08) [ -n "$out" ] && ! printf '%s' "$out" | tr -s ' \n' '\n' | grep -q '^9180$' ;;
    CHK-09) [ "$(printf '%s' "$out" | tail -n1 | tr -d ' \r')" = "#END" ] ;;
    CHK-10) printf '%s' "$out" | grep -qi 'x-request-id' && ! printf '%s' "$out" | grep -qi '^ngsild-tenant:' ;;
    CHK-11) printf '%s' "$out" | grep -qi 'strict-transport-security' \
              && printf '%s' "$out" | grep -qi 'x-content-type-options: *nosniff' ;;
    CHK-12) printf '%s' "$out" | grep -qE '^\s*on\s*$' ;;
    CHK-13) local len; len=$(printf '%s' "$out" | tr -dc '0-9'); [ "${len:-0}" -ge 32 ] ;;
    CHK-14) [ -z "$(printf '%s' "$out" | tr -d ' \n')" ] ;;
    # a render check, not a cluster probe: pytest's summary, with no failure, error or empty run
    CHK-15) printf '%s' "$out" | grep -qE '[0-9]+ passed' \
              && ! printf '%s' "$out" | grep -qE '[0-9]+ (failed|errors?)|no tests ran' ;;
    *) return 2 ;;
  esac
}

main() {
  [ -f "$PAGE" ] || { echo "the checklist page $PAGE is missing" >&2; exit 1; }
  local ids; ids=$(ids_in_page)
  [ -n "$ids" ] || { echo "$PAGE holds no CHK row, so this run proves nothing" >&2; exit 1; }

  for id in $ids; do
    local cmd out
    cmd=$(command_of "$id")
    if [ -z "$cmd" ]; then
      note "$id" "SKIP" "no verification command in the table"; skipped=$((skipped + 1)); continue
    fi
    out=$(run "$cmd")
    if printf '%s' "$out" | grep -qE 'command not found|Internal error occurred|Error from server \(NotFound\): (pods|secrets) '; then
      note "$id" "ERROR" "the probe itself did not run: $cmd"
      printf '         output: %s\n' "$(printf '%s' "$out" | head -c 300 | tr '\n' ' ')"
      fail=$((fail + 1)); continue
    fi
    if assert "$id" "$out"; then
      note "$id" "pass" "$cmd"; pass=$((pass + 1))
    elif [ $? -eq 2 ]; then
      note "$id" "NOCASE" "the table declares $id and this script asserts nothing for it"
      fail=$((fail + 1))
    else
      note "$id" "FAIL" "$cmd"
      printf '         output: %s\n' "$(printf '%s' "$out" | head -c 400 | tr '\n' ' ')"
      fail=$((fail + 1))
    fi
  done

  printf '\n%d passed, %d failed, %d skipped against namespace %s\n' "$pass" "$fail" "$skipped" "$NS"
  [ "$fail" -eq 0 ]
}

selftest() {
  local tmp; tmp=$(mktemp -d)
  local bin="$tmp/bin"; mkdir -p "$bin"

  make_stubs() {  # make_stubs <conforming|violating>
    local mode=$1
    cat > "$bin/kubectl" <<STUB
#!/usr/bin/env bash
all="\$*"
case "\$all" in
  *runAsNonRoot*)  [ "$mode" = conforming ] && echo "true true" || printf 'true true\ntrue false\n' ;;
  *readOnlyRootFilesystem*) [ "$mode" = conforming ] && echo "true true" || printf 'true false\n' ;;
  *capabilities*)  [ "$mode" = conforming ] && echo '["ALL"]' || printf '["ALL"]\n["NET_ADMIN"]\n' ;;
  *automountServiceAccountToken*) [ "$mode" = conforming ] \
    && printf 'false <none>\n<none> CloudNativePG operator: reconciles Cluster resources\n' \
    || printf 'false <none>\n<none> <none>\n' ;;
  *netpol*)        [ "$mode" = conforming ] && echo 'default-deny-portal ["Ingress","Egress"]' || echo 'default-deny-portal ["Ingress"]' ;;
  *initContainers*) [ "$mode" = conforming ] \
    && printf 'portal linkerd-proxy portal\napisix linkerd-proxy apisix\n' \
    || printf 'portal linkerd-proxy portal\nlegacy-importer legacy-importer\n' ;;
  *default-inbound-policy*) [ "$mode" = conforming ] && echo "enabled cluster-authenticated" || echo "enabled all-unauthenticated" ;;
  *clusterpolicyreport*) [ "$mode" = conforming ] && echo 0 || echo 3 ;;
  *ports*)         [ "$mode" = conforming ] && printf '9080\n9443\n' || printf '9080\n9180\n' ;;
  *apisix.yaml*)   [ "$mode" = conforming ] && echo "#END" || echo "routes:" ;;
  *SHOW\ ssl*)     [ "$mode" = conforming ] && echo " on" || echo " off" ;;
  *secret*)        [ "$mode" = conforming ] && echo "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE=" || echo "c2hvcnQ=" ;;
  *.image*)        [ "$mode" = conforming ] && true || echo "ghcr.io/x/y:latest" ;;
  *) true ;;
esac
STUB
    cat > "$bin/curl" <<STUB
#!/usr/bin/env bash
if [ "$mode" = conforming ]; then
  printf 'HTTP/2 200\nx-request-id: abc\nstrict-transport-security: max-age=63072000\nx-content-type-options: nosniff\n'
else
  printf 'HTTP/2 200\nNGSILD-Tenant: malicious\n'
fi
STUB
    cat > "$bin/base64" <<'STUB'
#!/usr/bin/env bash
/usr/bin/base64 "$@"
STUB
    cat > "$bin/python3" <<STUB
#!/usr/bin/env bash
[ "$mode" = conforming ] && echo "9 passed in 1.20s" || echo "1 failed, 8 passed in 1.20s"
STUB
    chmod +x "$bin"/*
  }

  local failures=0
  make_stubs conforming
  if PATH="$bin:$PATH" JC_NS=stub JC_DEPLOYMENT_DIR="$tmp" "$0" > "$tmp/out.txt" 2>&1; then
    echo "case 1 ok: a conforming cluster passes all fifteen checks"
  else
    echo "FAIL case 1: a conforming cluster did not pass:" >&2; cat "$tmp/out.txt" >&2; failures=1
  fi

  make_stubs violating
  if PATH="$bin:$PATH" JC_NS=stub JC_DEPLOYMENT_DIR="$tmp" "$0" > "$tmp/bad.txt" 2>&1; then
    echo "FAIL case 2: a violating cluster passed" >&2; cat "$tmp/bad.txt" >&2; failures=1
  else
    local red; red=$(grep -c 'FAIL' "$tmp/bad.txt")
    if [ "$red" -ge 12 ]; then
      echo "case 2 ok: a violating cluster fails $red of the checks"
    else
      echo "FAIL case 2: only $red checks went red:" >&2; cat "$tmp/bad.txt" >&2; failures=1
    fi
  fi

  # a row the script asserts nothing for is reported, never silently passed
  local page="$tmp/page.md"
  { grep -v 'CHK-14' "$PAGE" || true; } > "$page"
  # shellcheck disable=SC2016  # the backticks are markdown, not a substitution
  echo '| **CHK-99** | Invented | `true` | nothing | none |' >> "$page"
  make_stubs conforming
  PATH="$bin:$PATH" JC_NS=stub JC_DEPLOYMENT_DIR="$tmp" JC_SECURITY_PAGE="$page" "$0" > "$tmp/nocase.txt" 2>&1
  if grep -q 'NOCASE' "$tmp/nocase.txt"; then
    echo "case 3 ok: a checklist row with no assertion is reported"
  else
    echo "FAIL case 3: an unasserted row passed silently" >&2; failures=1
  fi

  rm -rf "$tmp"
  [ "$failures" -eq 0 ] || return 1
  echo "ok: the checklist passes on a conforming cluster, fails on a violating one and reports a row nothing asserts"
}

case "${1:-}" in
  --selftest) selftest ;;
  "") main ;;
  *) echo "usage: $0 [--selftest]" >&2; exit 2 ;;
esac
