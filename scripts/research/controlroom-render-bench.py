#!/usr/bin/env python3
"""Render time of a 12-panel controlroom dashboard: server HTML (grid, 2 stat panels, 1 table)
plus 9 Vega-Lite charts embedded by vega-embed, in headless Chromium at 1440 and 400 px
(Research/rust/code-factory.md, T-6641).

Usage: python3 -I controlroom-render-bench.py VEGA_DIR [RUNS]
VEGA_DIR holds vega.min.js 5.30.0, vega-lite.min.js 5.21.0, vega-embed.min.js 6.26.0 (jsDelivr).
Each chart: 5 series x 288 points (24 h at 5 min). Prints p50 and max of: HTML parse to
DOMContentLoaded, and navigation start to the last chart's SVG drawn, per width.
"""
import json
import math
import pathlib
import statistics
import sys

from playwright.sync_api import sync_playwright


def page(vega_dir: pathlib.Path) -> str:
    t0 = 1_762_000_000_000
    charts = []
    for c in range(9):
        values = [{"t": t0 + i * 300_000, "series": f"s{s}", "v": round(50 + 30 * math.sin(i / 20 + s + c), 2)}
                  for s in range(5) for i in range(288)]
        mark = "bar" if c == 8 else "line"
        enc = ({"x": {"field": "t", "type": "temporal", "title": None},
                "y": {"field": "v", "type": "quantitative", "title": None},
                "color": {"field": "series", "type": "nominal"}} if mark == "line" else
               {"y": {"field": "series", "type": "nominal"}, "x": {"aggregate": "mean", "field": "v"}})
        charts.append({"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "width": "container",
                       "height": 180, "data": {"values": values}, "mark": mark, "encoding": enc})
    cells = "".join(f'<section class="p"><h2>Chart {i + 1}</h2><div class="c" id="c{i}"></div></section>' for i in range(9))
    rows = "".join(f"<tr><td>route {i}</td><td>{i * 7} req/s</td><td>{i}.2 ms</td></tr>" for i in range(20))
    js = "".join((vega_dir / f).read_text() for f in ("vega.min.js", "vega-lite.min.js", "vega-embed.min.js"))
    return f"""<!doctype html><meta charset=utf-8><title>bench</title>
<style>body{{font:14px system-ui;margin:0;padding:16px}}main{{display:grid;gap:12px;
grid-template-columns:repeat(auto-fill,minmax(min(100%,420px),1fr))}}.p{{border:1px solid #ccc;padding:8px}}
.c{{width:100%}}.s{{font-size:32px}}table{{width:100%}}</style>
<main><section class="p"><h2>Up</h2><div class="s">99.98 %</div></section>
<section class="p"><h2>Errors</h2><div class="s">0.4 /s</div></section>{cells}
<section class="p"><h2>Routes</h2><table>{rows}</table></section></main>
<script>{js}</script>
<script>const specs={json.dumps(charts)};
Promise.all(specs.map((s,i)=>vegaEmbed('#c'+i,s,{{renderer:'svg',actions:false}})))
.then(()=>{{window.__done=performance.now()}});</script>"""


def main(argv):
    vega_dir = pathlib.Path(argv[0]).resolve()
    runs = int(argv[1]) if len(argv) > 1 else 7
    html = page(vega_dir)
    out = vega_dir / "bench.html"
    out.write_text(html)
    print(f"page {len(html.encode())} bytes")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, height in ((1440, 900), (400, 800)):
            dcl, done = [], []
            for _ in range(runs):
                ctx = browser.new_context(viewport={"width": width, "height": height})
                pg = ctx.new_page()
                pg.goto(out.as_uri())
                pg.wait_for_function("window.__done !== undefined", timeout=30_000)
                dcl.append(pg.evaluate("performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd"))
                done.append(pg.evaluate("window.__done"))
                ctx.close()
            print(f"{width}px DOMContentLoaded p50 {statistics.median(dcl):.0f} ms max {max(dcl):.0f}; "
                  f"all 9 charts drawn p50 {statistics.median(done):.0f} ms max {max(done):.0f} (runs {runs})")
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
