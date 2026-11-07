#!/usr/bin/env bash
# Clones Grafana at the tag the deployment pins (sparse, no history) and measures the Argon pack
# groups of Research/rust/grafana.md section 10 (T-6649).
#
# Usage: scripts/research/grafana-sources.sh <work dir>
# Tokens are estimated as non-blank bytes / 4 (comments kept, tests and snapshots dropped); the
# pack builder's own count is authoritative, this one sizes the runs.
set -euo pipefail

work=${1:?usage: grafana-sources.sh <work dir>}
tag=v12.4.14
mkdir -p "$work"
if [ ! -d "$work/gf/.git" ]; then
  git clone -q --filter=blob:none --sparse --depth 1 --branch "$tag" https://github.com/grafana/grafana.git "$work/gf"
fi
cd "$work/gf"

declare -A groups=(
  [G1-dashboard-model]="kinds apps/dashboard/kinds apps/dashboard/pkg/migration/schemaversion apps/dashboard/pkg/migration/conversion pkg/services/provisioning/dashboards pkg/services/provisioning/datasources pkg/api/dashboard.go pkg/api/folder.go pkg/api/datasources.go pkg/api/dtos"
  [G2-query-expr]="pkg/expr pkg/services/query pkg/api/pluginproxy pkg/plugins/backendplugin pkg/tsdb/grafanads"
  [G3-datasources]="pkg/promlib pkg/tsdb/loki pkg/tsdb/grafana-postgresql-datasource"
  [G4-transform-frames]="packages/grafana-data/src/transformations packages/grafana-data/src/dataframe packages/grafana-data/src/field packages/grafana-data/src/valueFormats"
  [G5-alerting]="pkg/services/ngalert/api/tooling/definitions pkg/services/ngalert/models pkg/services/ngalert/eval pkg/services/ngalert/schedule pkg/services/ngalert/state pkg/services/ngalert/notifier pkg/services/provisioning/alerting"
  [G6-tenancy-authz]="pkg/services/org pkg/services/team pkg/services/folder pkg/services/accesscontrol pkg/services/dashboards/dashboardaccess pkg/services/datasources"
  [G7-panels]="public/app/plugins/panel/timeseries public/app/plugins/panel/table public/app/plugins/panel/stat public/app/plugins/panel/bargauge public/app/plugins/panel/geomap"
)

paths=()
for g in "${!groups[@]}"; do
  read -ra dirs <<<"${groups[$g]}"
  for p in "${dirs[@]}"; do paths+=("/$p"); done
done
git sparse-checkout set --no-cone "${paths[@]}" /go.mod /conf/defaults.ini

echo "Grafana $tag at $(git rev-parse HEAD)"
printf '| Group | Paths | Files | Tokens |\n|---|---|---|---|\n'
for g in $(printf '%s\n' "${!groups[@]}" | sort); do
  files=0 bytes=0
  read -ra dirs <<<"${groups[$g]}"
  while IFS= read -r -d '' f; do
    files=$((files + 1))
    bytes=$((bytes + $(grep -v '^[[:space:]]*$' "$f" | wc -c)))
  done < <(find "${dirs[@]}" -type f \( -name '*.go' -o -name '*.ts' -o -name '*.tsx' -o -name '*.cue' -o -name '*.json' \) \
    ! -name '*_test.go' ! -name '*.test.ts' ! -name '*.test.tsx' ! -path '*/testdata/*' ! -path '*/__snapshots__/*' \
    ! -path '*/mocks/*' ! -name '*_mock.go' ! -name '*.pb.go' -print0 2>/dev/null)
  printf "| %s | \`%s\` | %d | %d |\n" "$g" "${groups[$g]}" "$files" $((bytes / 4))
done
