#!/usr/bin/env python3
"""Converts Grafana dashboards to the controlroom format proposed in marek-mraz-jc/joinedcontext
crates/controlroom/README.md and counts what converts (Research/rust/code-factory.md, T-6641).

Usage: controlroom-grafana-convert.py OUT_DIR GRAFANA_JSON...
       controlroom-grafana-convert.py --fetch-top N OUT_DIR   (downloads grafana.com's N most
       downloaded dashboards into OUT_DIR/grafana-com/ first, then converts them)
Writes OUT_DIR/<name>.controlroom.json (full Vega-Lite per chart), OUT_DIR/<name>.preset.json
(chart presets instead of Vega-Lite) and prints one line per dashboard plus a totals line.

Outcome per panel: full (chart, query and unit carry over), partial (the chart converts and a
feature drops: transformations, field overrides, value mappings, gauge styling, a non-Prometheus
query) or none (no controlroom equivalent). A row is layout, not a panel.
"""
import json
import pathlib
import sys
import urllib.request

LINE = {"timeseries", "graph"}
BAR = {"bargauge", "barchart", "histogram"}
STAT = {"stat", "singlestat", "gauge"}
TABLE = {"table", "table-old"}
ARC = {"piechart", "grafana-piechart-panel"}
RECT = {"heatmap", "state-timeline", "status-history"}
HTML = {"text"}
LOGS = {"logs"}
QUERY_OK = {"prometheus": "promql", "loki": "logs", "ngsild-grafana-datasource": "ngsi-ld"}


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get("panels", []))


def ds_type(panel, dash_default):
    ds = panel.get("datasource")
    if isinstance(ds, dict):
        t = ds.get("type") or ""
    elif isinstance(ds, str):
        t = ds
    else:
        t = ""
    if not t or t.startswith(("$", "${")) or t in ("-- Mixed --", "default"):
        targets = panel.get("targets") or []
        for tg in targets:
            tds = tg.get("datasource")
            if isinstance(tds, dict) and tds.get("type") and not str(tds.get("type")).startswith("$"):
                return tds["type"]
        return dash_default
    return t.lower()


def vega(kind):
    enc_t = {"x": {"field": "t", "type": "temporal", "title": None},
             "y": {"field": "v", "type": "quantitative", "title": None},
             "color": {"field": "series", "type": "nominal"}}
    if kind == "line":
        return {"mark": {"type": "line", "interpolate": "monotone"}, "encoding": enc_t}
    if kind == "bar":
        return {"mark": "bar", "encoding": {"y": {"field": "series", "type": "nominal"},
                                            "x": {"field": "v", "type": "quantitative"}}}
    if kind == "arc":
        return {"mark": "arc", "encoding": {"theta": {"field": "v", "type": "quantitative"},
                                            "color": {"field": "series", "type": "nominal"}}}
    if kind == "rect":
        return {"mark": "rect", "encoding": {"x": {"field": "t", "type": "temporal"},
                                             "y": {"field": "series", "type": "nominal"},
                                             "color": {"field": "v", "type": "quantitative"}}}
    return None


def convert(dash):
    default = ""
    for v in dash.get("templating", {}).get("list", []):
        if v.get("type") == "datasource":
            default = str(v.get("query", "")).lower()
    out_panels, preset_panels, counts, unsupported = [], [], {"full": 0, "partial": 0, "none": 0}, []
    for p in walk(dash.get("panels", []) or [r for row in dash.get("rows", []) for r in row.get("panels", [])]):
        t = p.get("type")
        if t == "row":
            continue
        kind = ("line" if t in LINE else "bar" if t in BAR else "stat" if t in STAT else
                "table" if t in TABLE else "arc" if t in ARC else "rect" if t in RECT else
                "html" if t in HTML else "logs" if t in LOGS else None)
        if kind is None:
            counts["none"] += 1
            unsupported.append(t)
            continue
        dst = ds_type(p, default)
        lang = QUERY_OK.get(dst)
        partial = (bool(p.get("transformations")) or bool(p.get("fieldConfig", {}).get("overrides"))
                   or bool(p.get("fieldConfig", {}).get("defaults", {}).get("mappings"))
                   or t in ("gauge", "state-timeline", "status-history", "histogram", "barchart")
                   or (kind != "html" and lang is None))
        counts["partial" if partial else "full"] += 1
        targets = [tg for tg in (p.get("targets") or []) if not tg.get("hide")]
        queries = [{"lang": lang or dst or "unknown",
                    "expr": tg.get("expr") or tg.get("query") or tg.get("rawSql") or "",
                    **({"legend": tg["legendFormat"]} if tg.get("legendFormat") else {})}
                   for tg in targets]
        gp = p.get("gridPos", {})
        base = {"title": p.get("title", ""), "grid": [gp.get("x", 0), gp.get("y", 0), gp.get("w", 12), gp.get("h", 8)]}
        unit = p.get("fieldConfig", {}).get("defaults", {}).get("unit")
        if unit:
            base["unit"] = unit
        if kind == "html":
            base["html"] = p.get("options", {}).get("content", p.get("content", ""))
            out_panels.append(base)
            preset_panels.append(base)
            continue
        base["queries"] = queries
        spec = vega(kind)
        out_panels.append({**base, **({"chart": spec} if spec else {"view": kind})})
        preset_panels.append({**base, ("chart" if spec else "view"): kind})
    variables = [{"name": v.get("name"), "kind": v.get("type"),
                  **({"query": v["query"]} if isinstance(v.get("query"), str) and v.get("query") else {})}
                 for v in dash.get("templating", {}).get("list", []) if v.get("type") != "datasource"]
    head = {"apiVersion": "controlroom/v1", "kind": "Dashboard", "title": dash.get("title", ""),
            "variables": variables}
    return ({**head, "panels": out_panels}, {**head, "panels": preset_panels}, counts, unsupported)


def fetch_top(n, out):
    out.mkdir(parents=True, exist_ok=True)
    url = f"https://grafana.com/api/dashboards?orderBy=downloads&direction=desc&pageSize={n}"
    items = json.load(urllib.request.urlopen(url, timeout=30))["items"]
    paths = []
    for it in items:
        dl = f"https://grafana.com/api/dashboards/{it['id']}/revisions/{it['revision']}/download"
        body = urllib.request.urlopen(dl, timeout=30).read()
        path = out / f"gcom-{it['id']}-r{it['revision']}.json"
        path.write_bytes(body)
        paths.append(path)
        print(f"fetched {it['id']} r{it['revision']} {it['name']!r} downloads={it.get('downloads')}")
    return paths


def main(argv):
    if argv and argv[0] == "--fetch-top":
        n, out = int(argv[1]), pathlib.Path(argv[2])
        files = fetch_top(n, out / "grafana-com")
    else:
        out, files = pathlib.Path(argv[0]), [pathlib.Path(a) for a in argv[1:]]
    out.mkdir(parents=True, exist_ok=True)
    total = {"full": 0, "partial": 0, "none": 0}
    for f in files:
        dash = json.loads(f.read_text())
        dash = dash.get("dashboard", dash)
        full, preset, counts, unsupported = convert(dash)
        (out / f"{f.stem}.controlroom.json").write_text(json.dumps(full, indent=1))
        (out / f"{f.stem}.preset.json").write_text(json.dumps(preset, indent=1))
        (out / f"{f.stem}.grafana.json").write_text(json.dumps(dash, indent=1))
        for k in total:
            total[k] += counts[k]
        print(f"{f.stem}: full {counts['full']} partial {counts['partial']} none {counts['none']}"
              + (f" unsupported {sorted(set(unsupported))}" if unsupported else ""))
    print(f"TOTAL dashboards {len(files)} full {total['full']} partial {total['partial']} none {total['none']}")


if __name__ == "__main__":
    main(sys.argv[1:])
