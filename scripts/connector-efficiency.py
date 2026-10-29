#!/usr/bin/env python3
"""Connector efficiency report (T-6030): tables from saved model-lane transcripts.

Two steps, so the docs never hold a transcript:

  extract  reads the transcript directories the Portal model lane wrote
           (tests/connector_scenarios/model.rs, JC_MODEL_EVAL_TRANSCRIPTS), the grader's table
           of each run (JC_MODEL_EVAL_OUT or a JC_MODEL_EVAL_FROM regrade), the per-scenario tool
           definitions (the lane's the_tool_definitions_a_model_reads_are_measured,
           JC_MODEL_EVAL_TOOLS) and a public-door probe (initialize + tools/list answers), and
           writes counts only: tool names, byte sizes, token counts, verdicts and a refusal class
           per call. No answer text, argument, token or person leaves the transcripts.
  render   turns that metrics file into the Markdown tables of docs Testing/09 and writes them
           between the page's markers (--write) or fails when the page differs (--check).

  python3 scripts/connector-efficiency.py extract --out scripts/connector-efficiency.json \\
      --tools tools.json --public-init init.json --public-tools tools-list.json \\
      --run "T-6037 run 2|envelope|20000|8|<dir>|<table.md>" ...
  python3 scripts/connector-efficiency.py render --check Testing/09-connector-efficiency.md
  python3 scripts/connector-efficiency.py selftest
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

BEGIN = "<!-- connector-efficiency:begin (scripts/connector-efficiency.py render --write) -->"
END = "<!-- connector-efficiency:end -->"

# Refusal classes, first match wins; read off the refusal texts of the saved runs.
REFUSALS = [
    ("argument refused", re.compile(r"^(unprocessable|invalid input|bad request)|-32602|invalid params", re.I)),
    ("outside the grant", re.compile(r"^forbidden|connector's segments|not allowed|401|403", re.I)),
    ("unknown kind", re.compile(r"kind '[^']+' not found", re.I)),
    ("not served in the harness", re.compile(r"gateway does not serve Endpoint", re.I)),
    ("unknown name", re.compile(r"not found|no such", re.I)),
    ("state conflict", re.compile(r"^conflict", re.I)),
]

TIMESTAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z")


def compact(value) -> int:
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False))


def refusal_class(text: str) -> str:
    for name, pattern in REFUSALS:
        if pattern.search(text):
            return name
    return "other"


def answer_parts(raw: str):
    """(text bytes, structuredContent bytes, _meta bytes, refusal text) of one stored answer,
    or None when the stored answer was cut and no longer parses."""
    try:
        answer = json.loads(raw)
    except ValueError:
        # Cut on store: the keys are sorted, so a whole `content` array still reads before the
        # cut `structuredContent`.
        at = raw.find('"content":')
        try:
            content = json.JSONDecoder().raw_decode(raw, at + len('"content":'))[0] if at >= 0 else None
        except ValueError:
            content = None
        if not isinstance(content, list):
            return None
        answer = {"result": {"content": content}}
    result = answer.get("result") or {}
    text = "\n".join(p.get("text", "") for p in result.get("content", []) if isinstance(p, dict))
    structured = compact(result["structuredContent"]) if "structuredContent" in result else 0
    meta = compact(result["_meta"]) if "_meta" in result else 0
    said = text or json.dumps(answer.get("error") or "")
    return len(text), structured, meta, said


def read_table(path: str) -> dict:
    """{(model, scenario): (segment, verdict, why)} from the grader's Markdown table."""
    rows, model = {}, None
    for line in open(path, encoding="utf-8"):
        if line.startswith("### "):
            model = line[4:].strip()
        elif line.startswith("| S-") and model:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[(model, cells[0])] = (cells[1], cells[3], cells[8])
    return rows


def classify(scenario: dict, listed: set) -> str:
    """Why a graded scenario failed, read from the grader's line and the transcript."""
    why = scenario["why"]
    if why.startswith("the model API refused"):
        return "model API error"
    if why.lower().startswith("deny"):
        return "leak (deny step)"
    wanted = re.search(r"no unrefused (\S+) in", why)
    tool = wanted.group(1) if wanted else None
    calls = [c for c in scenario["calls"] if c["tool"] == tool]
    if tool and not calls and listed and tool not in listed:
        return "missing tool"
    if calls and all(c["refused"] for c in calls):
        return {"argument refused": "argument refused", "outside the grant": "auth"}.get(
            calls[-1]["refusal"], "unclear error")
    if calls:
        return "description misread"
    if any(c["cut"] for c in scenario["calls"]):
        return "answer too large"
    if not scenario["final_text"]:
        return "ran out of turns"
    return "wrong tool chosen" if scenario["calls"] else "stopped before a call"


def extract(args) -> dict:
    tools = {row["scenario"]: row for row in json.load(open(args.tools))} if args.tools else {}
    runs = []
    for spec in args.run:
        label, view, cap, turn_cap, folder, table = spec.split("|")
        graded = read_table(table)
        scenarios = []
        for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
            t = json.load(open(path))
            segment, verdict, why = graded.get((t["model"], t["scenario"]), ("?", "?", ""))
            seen, calls = set(), []
            for c in t["calls"]:
                parts = answer_parts(c["answer"])
                text, structured, meta, said = parts or (0, 0, 0, "")
                wire = len(c["answer"])
                stored_cut = wire >= int(cap) and (parts is None or not structured)
                # What the model read: the envelope (cut at the run's cap) before T-6042, the
                # text content after it.
                if view == "envelope":
                    model_bytes, cut = min(wire, int(cap)), wire >= int(cap)
                else:
                    model_bytes, cut = (text, False) if parts else (int(cap), True)
                key = (c["tool"], TIMESTAMP.sub("", c["answer"]))
                calls.append({
                    "tool": c["tool"], "refused": c["refused"], "wire": wire, "text": text,
                    "structured": structured, "meta": meta, "model": model_bytes, "cut": cut, "stored_cut": stored_cut,
                    "repeat": key in seen,
                    "refusal": refusal_class(said) if c["refused"] else "",
                })
                seen.add(key)
            row = {
                "scenario": t["scenario"], "model": t["model"], "door": t["door"],
                "segment": segment, "verdict": verdict, "why": why[:120],
                "tokens": t["tokens"], "usd": round(t["cost_usd"], 6), "seconds": round(t["seconds"], 1),
                "final_text": bool(t["text"].strip()), "error": bool(t.get("error")),
                "definitions": tools.get(t["scenario"], {}).get("bytes", 0),
                "turns": t.get("turns", []), "calls": calls,
            }
            listed = set(tools.get(t["scenario"], {}).get("tools", {}))
            row["failure"] = classify(row, listed) if verdict == "FAIL" else ""
            scenarios.append(row)
        runs.append({"label": label, "view": view, "cap": int(cap), "turn_cap": int(turn_cap),
                     "scenarios": scenarios})
    public = {}
    if args.public_tools:
        listed = json.load(open(args.public_tools))["result"]["tools"]
        public["tools"] = sorted(
            ({"name": t["name"], "bytes": compact(t), "description": len(t.get("description", "")),
              "schema": compact(t.get("inputSchema", {}))} for t in listed),
            key=lambda t: (-t["bytes"], t["name"]))
    if args.public_init:
        public["instructions"] = len(json.load(open(args.public_init))["result"].get("instructions", ""))
    for spec in args.public_answer or []:
        name, path = spec.split("|")
        text, structured, meta, _ = answer_parts(open(path).read())
        public.setdefault("answers", []).append(
            {"tool": name, "wire": os.path.getsize(path), "text": text, "structured": structured})
    return {"tools": list(tools.values()), "runs": runs, "public": public}


def md(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def n(value) -> str:
    return f"{value:,}"


def per_model(data):
    for run in data["runs"]:
        by = defaultdict(list)
        for s in run["scenarios"]:
            by[s["model"]].append(s)
        for model, rows in sorted(by.items()):
            yield run, model.split("/")[-1], rows


def render(data) -> str:
    parts = []
    # 1. Runs.
    rows = []
    for run, model, ss in per_model(data):
        graded = [s for s in ss if s["verdict"] in ("pass", "FAIL")]
        calls = sum(len(s["calls"]) for s in ss)
        tokens = sum(s["tokens"] for s in ss)
        rows.append([run["label"], model, len(ss), len(graded),
                     sum(s["verdict"] == "pass" for s in ss), n(calls), n(tokens),
                     n(tokens // max(len(ss), 1)), f"{sum(s['usd'] for s in ss):.2f}",
                     f"{sum(s['seconds'] for s in ss):.0f}"])
    parts.append("### Runs\n\n" + md(["run", "model", "scenarios", "graded", "passed", "calls",
                                      "tokens", "tokens per scenario", "USD", "seconds"], rows))
    # 2. Tool definitions sent with every turn.
    seg = defaultdict(list)
    for t in data["tools"]:
        seg[(t["segment"], t["door"])].append(t)
    rows = []
    for (segment, door), ts in sorted(seg.items()):
        biggest = max(ts, key=lambda t: t["bytes"])
        top = sorted(biggest["tools"].items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        rows.append([segment, door, len(ts), f"{min(len(t['tools']) for t in ts)}-{max(len(t['tools']) for t in ts)}",
                     n(min(t["bytes"] for t in ts)), n(max(t["bytes"] for t in ts)),
                     ", ".join(f"`{k}` {n(v)}" for k, v in top)])
    parts.append("### Tool definitions per turn, Portal doors\n\n" + md(
        ["segment", "door", "scenarios", "tools", "bytes min", "bytes max", "largest three"], rows))
    pub = data.get("public", {})
    if pub.get("tools"):
        total = sum(t["bytes"] for t in pub["tools"])
        schema = sum(t["schema"] for t in pub["tools"])
        rows = [[f"`{t['name']}`", n(t["bytes"]), n(t["description"]), n(t["schema"])] for t in pub["tools"][:6]]
        rows.append([f"all {len(pub['tools'])} tools", n(total), n(sum(t['description'] for t in pub['tools'])), n(schema)])
        if "instructions" in pub:
            rows.append(["server `instructions` (initialize)", n(pub["instructions"]), "", ""])
        parts.append("### Public door (`/api/mcp`): what a client loads before the first question\n\n" + md(
            ["tool", "bytes", "description", "input schema"], rows))
    if pub.get("answers"):
        rows = [[f"`{a['tool']}`", n(a["wire"]), n(a["text"]), n(a["structured"])] for a in pub["answers"]]
        parts.append("### Public door answers\n\n" + md(["tool", "bytes on the wire", "content text", "structuredContent"], rows))
    # 3. Token split. A turn re-sends the definitions; a transcript with turns[] counts them.
    rows = []
    for run, model, ss in per_model(data):
        zero = [s for s in ss if not s["calls"] and s["definitions"] > 2 and not s["error"]]
        if not zero:
            continue
        per_byte = sum(s["tokens"] for s in zero) / sum(s["definitions"] for s in zero)
        defs = answers = total = 0
        for s in ss:
            turns = len(s["turns"]) or min(run["turn_cap"], len(s["calls"]) + 1)
            d = turns * s["definitions"] * per_byte
            # An answer is read again in every later turn, one call per turn (no turns[] recorded).
            a = sum(c["model"] * max(turns - i - 1, 0) for i, c in enumerate(s["calls"])) * per_byte
            total += s["tokens"]
            defs += min(d, s["tokens"])
            answers += min(a, max(s["tokens"] - d, 0))
        rows.append([run["label"], model, len(zero), f"{1 / per_byte:.2f}", n(total),
                     f"{100 * defs / total:.0f} %", f"{100 * answers / total:.0f} %",
                     f"{100 * (total - defs - answers) / total:.0f} %"])
    parts.append("### Where the tokens go\n\n" + md(
        ["run", "model", "zero-call runs", "bytes per token", "tokens", "tool definitions",
         "answers", "model text and prompt"], rows))
    # 4. Largest answers and duplicated payload.
    calls = [(run["label"], model, s["scenario"], c) for run, model, ss in per_model(data) for s in ss for c in s["calls"]]
    by_tool = defaultdict(list)
    for _, _, _, c in calls:
        by_tool[c["tool"]].append(c)
    rows = []
    for tool, cs in sorted(by_tool.items(), key=lambda kv: -max(c["wire"] for c in kv[1]))[:10]:
        parsed = [c for c in cs if not c["stored_cut"]]
        rows.append([f"`{tool}`", len(cs), n(max(c["wire"] for c in cs)),
                     n(sum(c["wire"] for c in cs) // len(cs)), sum(c["cut"] for c in cs),
                     n(sum(c["text"] for c in parsed)), n(sum(c["structured"] for c in parsed)),
                     n(sum(c["meta"] for c in parsed))])
    parts.append("### Largest answers by tool (all runs)\n\n" + md(
        ["tool", "calls", "largest bytes", "mean bytes", "cut", "content text", "structuredContent",
         "_meta"], rows))
    rows = []
    for run, model, ss in per_model(data):
        read = Counter()
        for s in ss:
            for c in s["calls"]:
                read[c["tool"]] += c["model"]
        total = sum(read.values())
        top = read.most_common(3)
        rows.append([run["label"], model, n(total)] + [
            f"`{t}` {n(b)} ({100 * b / max(total, 1):.0f} %)" for t, b in top])
    parts.append("### Answer bytes the model read, by tool\n\n" + md(
        ["run", "model", "answer bytes", "first", "second", "third"], rows))
    # 5. Turns lost.
    rows = []
    for run, model, ss in per_model(data):
        cs = [c for s in ss for c in s["calls"]]
        refused = Counter(c["refusal"] for c in cs if c["refused"])
        rows.append([run["label"], model, n(len(cs)), sum(c["repeat"] for c in cs),
                     sum(c["refused"] for c in cs)] + [refused.get(k, 0) for k, _ in REFUSALS])
    parts.append("### Calls lost to repeats and refusals\n\n" + md(
        ["run", "model", "calls", "same answer again", "refused"] + [k for k, _ in REFUSALS], rows))
    # 6. Failure classes.
    classes = sorted({s["failure"] for _, _, ss in per_model(data) for s in ss if s["failure"]})
    rows = []
    for run, model, ss in per_model(data):
        c = Counter(s["failure"] for s in ss if s["failure"])
        rows.append([run["label"], model, sum(c.values())] + [c.get(k, 0) for k in classes])
    parts.append("### Failure classes of graded fails\n\n" + md(["run", "model", "fails"] + classes, rows))
    rows = []
    for run, model, ss in per_model(data):
        for s in ss:
            if s["failure"]:
                rows.append([run["label"], model, s["scenario"], s["segment"], len(s["calls"]),
                             n(s["tokens"]), s["failure"]])
    parts.append("### Every graded fail\n\n" + md(["run", "model", "scenario", "segment", "calls", "tokens", "class"], rows))
    return "\n\n".join(parts) + "\n"


def splice(page: str, tables: str) -> str:
    head, rest = page.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{BEGIN}\n\n{tables}\n{END}{tail}"


def selftest():
    assert refusal_class("unprocessable: 1 of the plan's changes fail") == "argument refused"
    assert refusal_class("not found: kind 'Role' not found in project 'org'") == "unknown kind"
    assert refusal_class("this connector's segments (data-read) read only Endpoint") == "outside the grant"
    assert refusal_class("conflict: change is not merged") == "state conflict"
    call = {"tool": "jc_change_plan", "refused": True, "refusal": "argument refused", "cut": False}
    row = {"why": "expect: no unrefused jc_change_plan in t-scn-1 whose answer holds", "calls": [call], "final_text": True}
    assert classify(row, {"jc_change_plan"}) == "argument refused"
    row["calls"] = []
    assert classify(row, {"jc_resource_list"}) == "missing tool"
    row["final_text"] = False
    assert classify(row, {"jc_change_plan"}) == "ran out of turns"
    assert answer_parts('{"result":{"content":[{"type":"text","text":"ab"}],"structuredContent":{"a":1}}}')[:2] == (2, 7)
    assert answer_parts('{"result":') is None
    page = f"x\n{BEGIN}\nold\n{END}\ny"
    assert splice(page, "new\n") == f"x\n{BEGIN}\n\nnew\n\n{END}\ny"
    print("selftest ok")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--out", required=True)
    e.add_argument("--tools")
    e.add_argument("--public-init")
    e.add_argument("--public-tools")
    e.add_argument("--public-answer", action="append", help="tool|answer.json")
    e.add_argument("--run", action="append", required=True,
                   help="label|envelope or text|answer cap|turn cap|transcript dir|grader table")
    r = sub.add_parser("render")
    r.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "connector-efficiency.json"))
    g = r.add_mutually_exclusive_group()
    g.add_argument("--write")
    g.add_argument("--check")
    sub.add_parser("selftest")
    args = p.parse_args()
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "extract":
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(extract(args), f, separators=(",", ":"), sort_keys=True)
            f.write("\n")
        return None
    tables = render(json.load(open(args.data)))
    target = args.write or args.check
    if not target:
        sys.stdout.write(tables)
        return None
    page = open(target, encoding="utf-8").read()
    wanted = splice(page, tables)
    if args.write:
        open(target, "w", encoding="utf-8").write(wanted)
    elif wanted != page:
        sys.exit(f"{target}: tables differ from {args.data}; run render --write {target}")
    return None


if __name__ == "__main__":
    main()
