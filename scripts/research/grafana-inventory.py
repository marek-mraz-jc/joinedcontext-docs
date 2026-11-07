#!/usr/bin/env python3
"""List every panel type, datasource, query language and transformation in our Grafana dashboards.

Research input for controlroom (T-6649, Research/rust/grafana.md section 1). Reads every JSON file
under <deployment>/components that carries a `panels` list, so a dashboard added anywhere in the
deployment repo shows up without editing this script.

Usage: python3 scripts/research/grafana-inventory.py [path to joinedcontext-deployment]
Prints Markdown tables; exit 1 when no dashboard is found (a wrong path must not look like "none").
"""

import collections
import json
import pathlib
import sys


def panels(items):
    """Every panel, rows' nested panels included (a collapsed row keeps its children inside)."""
    for p in items or []:
        yield p
        yield from panels(p.get("panels"))


def ds_type(ds):
    if isinstance(ds, dict):
        return ds.get("type") or ds.get("uid") or "?"
    return ds or "(default)"


def language(ds, target):
    """The query language a target speaks, named from the fields Grafana stores for it."""
    kind = ds_type(target.get("datasource") or ds)
    if "expr" in target:
        return "LogQL" if kind == "loki" else "PromQL"
    if "rawSql" in target:
        return "SQL"
    if kind.startswith("ngsild"):
        return "NGSI-LD " + str(target.get("queryType") or target.get("type") or "query")
    return kind


def fieldconfig_features(p):
    d = (p.get("fieldConfig") or {}).get("defaults") or {}
    out = []
    if d.get("unit"):
        out.append("unit:" + d["unit"])
    if d.get("thresholds"):
        out.append("thresholds:" + d["thresholds"].get("mode", "?"))
    if d.get("mappings"):
        out.append("mappings:" + ",".join(sorted({m.get("type", "?") for m in d["mappings"]})))
    if d.get("custom"):
        out.append("custom:" + ",".join(sorted(d["custom"])))
    for key in ("min", "max", "decimals", "color", "displayName", "noValue", "links"):
        if key in d:
            out.append(key)
    for o in (p.get("fieldConfig") or {}).get("overrides") or []:
        out.append("override:" + o.get("matcher", {}).get("id", "?"))
    return out


def main(argv):
    root = pathlib.Path(argv[1] if len(argv) > 1 else "../joinedcontext-deployment")
    files = []
    for f in sorted(root.glob("components/**/*.json")):
        try:
            doc = json.loads(f.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get("panels"), list):
            files.append((f.relative_to(root), doc))
    if not files:
        print(f"no dashboard JSON under {root}/components", file=sys.stderr)
        return 1

    types, sources, langs, transforms, features, opts = (collections.Counter() for _ in range(6))
    print("| File | uid | schemaVersion | Panels | Panel types | Variables | Transformations |")
    print("|---|---|---|---|---|---|---|")
    for path, doc in files:
        ps = list(panels(doc["panels"]))
        kinds = collections.Counter(p.get("type", "?") for p in ps)
        tr = collections.Counter(t.get("id", "?") for p in ps for t in p.get("transformations") or [])
        variables = [f"{v.get('name')}({v.get('type')})" for v in (doc.get("templating") or {}).get("list", [])]
        for p in ps:
            types[p.get("type", "?")] += 1
            for t in p.get("targets") or []:
                sources[ds_type(t.get("datasource") or p.get("datasource"))] += 1
                langs[language(p.get("datasource"), t)] += 1
            features.update(fieldconfig_features(p))
            opts.update(f"{p.get('type')}.{k}" for k in (p.get("options") or {}))
        transforms.update(tr)
        print(
            f"| `{path}` | `{doc.get('uid')}` | {doc.get('schemaVersion')} | {len(ps)} | "
            f"{', '.join(f'{k} {n}' for k, n in sorted(kinds.items()))} | "
            f"{', '.join(variables) or '-'} | {', '.join(f'{k} {n}' for k, n in sorted(tr.items())) or '-'} |"
        )
    for title, counter in (
        ("Panel type", types),
        ("Datasource (per target)", sources),
        ("Query language (per target)", langs),
        ("Transformation", transforms),
        ("fieldConfig feature", features),
        ("Panel option", opts),
    ):
        print(f"\n| {title} | Count |\n|---|---|")
        for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"| `{k}` | {n} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
