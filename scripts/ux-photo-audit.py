#!/usr/bin/env python3
"""T-4164: write the counted parts of Research/ux-photo-audit-2026-10.md from the audit folders.

Each folder is /workspace/evidence/<agent>/<task id>/ of one UX photo audit (T-4157..T-4163): its
PNGs and its findings.json. scripts/ux-photo-audit-triage.json names the audit's area per task and
puts each finding in a shared pattern (matched on the task and the start of its description).
Everything between the page's `<!-- generated -->` markers is rewritten: screenshot counts, findings
by area and severity, the patterns, the top 20. Nothing in it is typed.

  python3 scripts/ux-photo-audit.py /workspace/evidence/*/T-41[56]?/   # rewrite the page
  python3 scripts/ux-photo-audit.py --selftest
"""

import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/ux-photo-audit-2026-10.md"
TRIAGE = ROOT / "scripts/ux-photo-audit-triage.json"
START, END = "<!-- generated: scripts/ux-photo-audit.py -->", "<!-- end generated -->"
SEVERITIES = ("blocker", "major", "minor")
# A white page saved as PNG is under this size; the audits count only what is over it (T-4157..T-4163).
NON_BLANK = 25 * 1024
TOP = 20


# A URL an auditor quotes in a finding; bare in a table it breaks markdownlint MD034 (T-4262).
BARE_URL = re.compile(r"(?<![<(`])\bhttps?://[^\s|'\"<>)`]+")


def cell(text: str) -> str:
    text = " ".join(str(text).split()).replace("|", "\\|")
    return BARE_URL.sub(lambda m: f"<{m.group(0).rstrip('.,;')}>{m.group(0)[len(m.group(0).rstrip('.,;')):]}", text)


def load(folders: list[Path], triage: dict) -> tuple[list[dict], list[dict], list[str]]:
    """The audits (task, area, counts) and their findings, each with its pattern; and the unmatched."""
    audits, findings, unmatched = [], [], []
    for folder in folders:
        task = folder.name
        if task not in triage["areas"]:
            raise SystemExit(f"{folder}: no area for {task} in {TRIAGE.name}")
        pngs = list(folder.glob("*.png"))
        found = json.loads((folder / "findings.json").read_text()) if (folder / "findings.json").exists() else []
        audits.append({
            "task": task,
            "area": triage["areas"][task],
            "folder": str(folder),
            "pngs": len(pngs),
            "shots": sum(p.stat().st_size > NON_BLANK for p in pngs),
            "findings": len(found),
        })
        for finding in found:
            if finding.get("severity") not in SEVERITIES:
                raise SystemExit(f"{folder}/findings.json: severity {finding.get('severity')!r} of {finding.get('file')}")
            pattern = next(
                (p["id"] for p in triage["patterns"] for key in p["findings"]
                 if key.split(":", 1)[0] == task and finding["description"].startswith(key.split(":", 1)[1])),
                None,
            )
            if pattern is None:
                unmatched.append(f"{task}:{finding['description'][:60]}")
            findings.append({**finding, "task": task, "area": triage["areas"][task], "pattern": pattern,
                             "path": f"{folder}/{finding['file']}"})
    return audits, findings, unmatched


def render(audits: list[dict], findings: list[dict], triage: dict) -> str:
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    size = Counter(f["pattern"] for f in findings if f["pattern"])
    out = [START, "", "### Screenshots and findings per audit", "",
           "| Audit | Area | PNGs | Non-blank (> 25 KB) | Findings |", "|---|---|---:|---:|---:|"]
    for a in sorted(audits, key=lambda a: a["task"]):
        out.append(f"| {a['task']} | {a['area']} | {a['pngs']} | {a['shots']} | {a['findings']} |")
    out.append(f"| **total** | | **{sum(a['pngs'] for a in audits)}** | **{sum(a['shots'] for a in audits)}** "
               f"| **{len(findings)}** |")

    out += ["", "### Findings by area and severity", "", "| Area | " + " | ".join(SEVERITIES) + " |",
            "|---|" + "---:|" * len(SEVERITIES)]
    for area in dict.fromkeys(a["area"] for a in sorted(audits, key=lambda a: a["task"])):
        count = Counter(f["severity"] for f in findings if f["area"] == area)
        out.append(f"| {area} | " + " | ".join(str(count[s]) for s in SEVERITIES) + " |")
    total = Counter(f["severity"] for f in findings)
    out.append("| **total** | " + " | ".join(f"**{total[s]}**" for s in SEVERITIES) + " |")

    out += ["", "### Patterns", "", "| Pattern | Shared fix | Findings | Worst | Areas |", "|---|---|---:|---|---|"]
    for p in sorted(triage["patterns"], key=lambda p: -size[p["id"]]):
        mine = [f for f in findings if f["pattern"] == p["id"]]
        if not mine:
            continue
        worst = min((f["severity"] for f in mine), key=rank.__getitem__)
        areas = ", ".join(dict.fromkeys(f["area"] for f in mine))
        out.append(f"| {cell(p['title'])} | {cell(p['fix'])} | {len(mine)} | {worst} | {areas} |")
    alone = sum(f["pattern"] is None for f in findings)
    out.append(f"| (page only) | one fix per page | {alone} | | |")

    ranked = sorted(findings, key=lambda f: (rank[f["severity"]], -size.get(f["pattern"], 0), f["task"]))
    out += ["", f"### Top {TOP}", "", "| # | Severity | Area | Route | Finding | Screenshot |", "|---:|---|---|---|---|---|"]
    for n, f in enumerate(ranked[:TOP], 1):
        out.append(f"| {n} | {f['severity']} | {f['area']} | `{cell(f['route'])}` | {cell(f['description'])} "
                   f"| `{cell(f['path'])}` |")
    out += ["", END]
    return "\n".join(out)


def write(page: Path, block: str) -> None:
    text = page.read_text()
    if START not in text or END not in text:
        raise SystemExit(f"{page}: the markers {START} … {END} are missing")
    head, rest = text.split(START, 1)
    page.write_text(head + block + rest.split(END, 1)[1])


def selftest() -> None:
    triage = {"areas": {"T-1": "shell", "T-2": "public"},
              "patterns": [{"id": "lang", "title": "Slovak ignored", "fix": "locale from the URL", "findings": ["T-1:Slovak", "T-2:Slovak"]}]}
    with tempfile.TemporaryDirectory() as tmp:
        folders = []
        for task, found in (("T-1", [("major", "Slovak page in English"), ("minor", "A | cut button"),
                                     ("minor", "Area shows 'http://data.europa.eu/nuts/code/CZ010'.")]),
                            ("T-2", [("blocker", "Slovak gone, white page")])):
            folder = Path(tmp) / task
            folder.mkdir()
            (folder / "a.png").write_bytes(b"x" * (NON_BLANK + 1))
            (folder / "blank.png").write_bytes(b"x" * 100)
            (folder / "findings.json").write_text(json.dumps(
                [{"file": "a.png", "route": "/r", "width": 375, "lang": "sk", "who": "anonymous", "rule": "1",
                  "severity": s, "description": d, "fix": "f"} for s, d in found]))
            folders.append(folder)
        audits, findings, unmatched = load(folders, triage)
        assert [a["shots"] for a in audits] == [1, 1] and [a["pngs"] for a in audits] == [2, 2]
        assert unmatched == ["T-1:A | cut button", "T-1:Area shows 'http://data.europa.eu/nuts/code/CZ010'."], unmatched
        block = render(audits, findings, triage)
        assert "| **total** | | **4** | **2** | **4** |" in block, block
        # T-4262: a quoted URL is an autolink, never bare (MD034).
        assert "'<http://data.europa.eu/nuts/code/CZ010>'." in block and not BARE_URL.search(block), block
        assert "| shell | 0 | 1 | 2 |" in block and "| **total** | **1** | **1** | **2** |" in block, block
        assert "| Slovak ignored | locale from the URL | 2 | blocker | shell, public |" in block, block
        top = [line for line in block.splitlines() if re.match(r"\| \d+ \|", line)]
        assert top[0].startswith("| 1 | blocker | public") and "A \\| cut button" in top[2], top
        page = Path(tmp) / "page.md"
        page.write_text(f"# x\n\n{START}\nold\n{END}\n\n## Related\n")
        write(page, block)
        assert "old" not in page.read_text() and page.read_text().endswith(f"{END}\n\n## Related\n")
        bad = Path(tmp) / "T-3"
        bad.mkdir()
        (bad / "findings.json").write_text(json.dumps([{"severity": "bad", "file": "x"}]))
        try:
            load([bad], {**triage, "areas": {"T-3": "x"}})
            raise AssertionError("an unknown severity passed")
        except SystemExit:
            pass
    print("ux-photo-audit: selftest passed")


def main(args: list[str]) -> None:
    if args == ["--selftest"]:
        return selftest()
    if not args:
        raise SystemExit(__doc__)
    triage = json.loads(TRIAGE.read_text())
    folders = sorted({Path(a).resolve() for a in args}, key=lambda p: p.name)
    audits, findings, unmatched = load(folders, triage)
    write(PAGE, render(audits, findings, triage))
    for key in unmatched:
        print(f"page only (no pattern): {key}", file=sys.stderr)
    print(f"{PAGE.relative_to(ROOT)}: {len(audits)} audits, {sum(a['shots'] for a in audits)} non-blank shots, "
          f"{len(findings)} findings, {len(unmatched)} page only")


if __name__ == "__main__":
    main(sys.argv[1:])
