#!/usr/bin/env python3
"""Every Helsinki HRI dataset has a decision in Research/helsinki-open-data.md (T-5252).

    check-helsinki-open-data.py check       # CI: the matrix against the committed snapshot
    check-helsinki-open-data.py probe       # network: re-read 10 sampled usable rows (T-5663)
    check-helsinki-open-data.py --selftest

`check` needs no network. It fails when the matrix table does not hold exactly one row per
snapshot dataset, names a dataset the snapshot does not hold, has a decision outside
integrate/statistics/skip, an integrate or statistics row without a batch task and a model, a
batch outside T-5253..T-5259 and their splits T-5278, T-5286, T-5378, a score outside -1..3 (a skip has none), or a skip that section 7 does not list with its reason. When the
board is mounted (TASKS_DIR, default /workspace/tasks) every batch id must also be a task file
there; CI has no board and skips that part.

`check` also reads the re-score of section 9 (T-5663): one row per matrix row with the same number
and name, a usable word of USABLE, a plan of PLANS that fits it (a usable row has a plan, any other
row none, `live` only beside a `live:` dev cell), and the counts of the tables in sections 9.3 and
10 equal to the rows. `probe` takes 10 usable rows at random whose resources are not only on
kartta.hel.fi (the sandbox reaches no kartta host), reads each package from the HRI API and GETs its
first resource (15 s timeout, 64 KiB read, no credentials); a 4xx, 5xx or no answer fails it.
"""

from __future__ import annotations

import csv
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/helsinki-open-data.md"
SNAPSHOT = ROOT / "Research/data/helsinki-hri-snapshot-2026-10-22.tsv"
DECISIONS = {"integrate", "statistics", "skip"}
BATCHES = {f"T-{n}" for n in range(5253, 5260)} | {"T-5278", "T-5286", "T-5378"}
ROW = re.compile(r"^\| \d+ \| \[`([^`]+)`\]")
SKIP_ITEM = re.compile(r"^- `([^`]+)`: (.+)$")
USABLE = {
    "yes",
    "dead",
    "stale",
    "licence",
    "duplicate",
    "format",
    "not-data",
    "outside",
}
PLANS = {"live", "F1", "B1", "B2", "B3", "T-5256", "T-5286", "T-5378"}
RESCORE = re.compile(r"^\| (\d+) \| `([^`]+)` \| ")
COUNT = re.compile(r"^\| (\S+) \| (\d+) \|")
HRI_API = "https://hri.fi/data/api/3/action/package_show?id="


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def parse(text: str) -> tuple[list[list[str]], dict[str, str]]:
    rows, skipped, section = [], {}, ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line
        elif ROW.match(line):
            rows.append(cells(line))
        elif section.startswith("## 7.") and (m := SKIP_ITEM.match(line)):
            skipped[m.group(1)] = m.group(2)
    return rows, skipped


def board_ids(tasks_dir: Path) -> set[str] | None:
    if not tasks_dir.is_dir():
        return None
    files = list(tasks_dir.glob("T-*.md")) + list(tasks_dir.glob("finished/T-*.md"))
    return {"-".join(f.name.split("-")[:2]) for f in files}


def problems(
    text: str,
    snapshot: set[str],
    board: set[str] | None,
    batches: set[str] = BATCHES,
    source: str = "HRI",
) -> list[str]:
    rows, skipped = parse(text)
    found, seen = [], set()
    for r in rows:
        if len(r) != 14:
            found.append(f"row {r[:2]}: {len(r)} cells, 14 expected")
            continue
        name = ROW.match(f"| {r[0]} | {r[1]}").group(1)
        decision, batch, model, score = r[4], r[5], r[6], r[13]
        if name in seen:
            found.append(f"{name}: listed twice")
        seen.add(name)
        if name not in snapshot:
            found.append(f"{name}: not in the {source} snapshot")
        if decision not in DECISIONS:
            found.append(
                f"{name}: decision {decision!r} is not integrate, statistics or skip"
            )
        elif decision == "skip":
            if score != "-":
                found.append(f"{name}: a skip has no score, found {score!r}")
            if not skipped.get(name):
                found.append(
                    f"{name}: skipped but not listed with a reason in section 7"
                )
        else:
            if batch not in batches:
                found.append(
                    f"{name}: batch {batch!r} is not one of {', '.join(sorted(batches))}"
                )
            elif board is not None and batch not in board:
                found.append(f"{name}: batch {batch} is not a task on the board")
            if not re.fullmatch(r"-?[0-3]", score):
                found.append(f"{name}: score {score!r} is not -1..3")
            if "`" not in model:
                found.append(f"{name}: {decision} without a model")
    for name in sorted(snapshot - seen):
        found.append(f"{name}: in the snapshot but has no row")
    for name in sorted(
        set(skipped)
        - {
            ROW.match(f"| {r[0]} | {r[1]}").group(1)
            for r in rows
            if len(r) == 14 and r[4] == "skip"
        }
    ):
        found.append(f"{name}: in section 7 but its row is not a skip")
    return found


def section(text: str, head: str) -> list[str]:
    level, lines, inside = len(head) - len(head.lstrip("#")), [], False
    for line in text.splitlines():
        hashes = len(line) - len(line.lstrip("#"))
        if (
            hashes
            and line[hashes : hashes + 1] == " "
            and (line.startswith(head) or hashes <= level)
        ):
            inside = line.startswith(head)
        elif inside:
            lines.append(line)
    return lines


def rescore(text: str) -> list[list[str]]:
    return [cells(l) for l in section(text, "## 9.") if RESCORE.match(l)]


def rescore_problems(text: str) -> list[str]:
    matrix = [
        (r[0], ROW.match(f"| {r[0]} | {r[1]}").group(1))
        for r in parse(text)[0]
        if len(r) == 14
    ]
    rows, found = rescore(text), []
    if [(r[0], r[1].strip("`")) for r in rows] != matrix:
        found.append(
            "section 9.5 does not hold one row per matrix row, in matrix order"
        )
    for r in rows:
        if len(r) != 5:
            found.append(f"re-score row {r[:2]}: {len(r)} cells, 5 expected")
            continue
        n, usable, dev, plan = r[0], r[2], r[3], r[4]
        if usable not in USABLE:
            found.append(
                f"re-score row {n}: usable {usable!r} is not one of {sorted(USABLE)}"
            )
        elif usable == "yes" and plan not in PLANS:
            found.append(
                f"re-score row {n}: a usable row needs a plan of {sorted(PLANS)}"
            )
        elif usable != "yes" and plan != "-":
            found.append(f"re-score row {n}: {usable} row with plan {plan!r}")
        if plan == "live" and not dev.startswith("live:"):
            found.append(f"re-score row {n}: plan live but dev {dev[:30]!r}")
    usable = Counter(r[2] for r in rows if len(r) == 5)
    plans = Counter(r[4] for r in rows if len(r) == 5)
    stated = {
        m.group(1): int(m.group(2))
        for l in section(text, "### 9.3")
        if (m := COUNT.match(l))
    }
    want = dict(usable, total=len(rows))
    if stated != want:
        found.append(f"section 9.3 counts {stated} differ from the rows {want}")
    batches = {
        m.group(1): int(m.group(2))
        for l in section(text, "## 10.")
        if (m := COUNT.match(l))
    }
    if batches != {p: c for p, c in plans.items() if p not in ("live", "-")}:
        found.append(f"section 10 rows {batches} differ from the plans {dict(plans)}")
    return found


def get(url: str, cap: int) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "jc-open-data-probe/1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read(cap)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except (OSError, ValueError):
        return 0, b""


def probe(text: str, n: int = 10) -> list[str]:
    names = [r[1].strip("`") for r in rescore(text) if r[2] == "yes"]
    random.shuffle(names)
    found, done = [], 0
    for name in names:
        status, body = get(HRI_API + name, 4 << 20)
        if status != 200:
            found.append(f"{name}: package_show answered {status or 'nothing'}")
            done += 1
        else:
            urls = [
                r.get("url", "")
                for r in json.loads(body).get("result", {}).get("resources", [])
                if r.get("url", "").startswith("https://")
            ]
            urls = [u for u in urls if "kartta.hel.fi" not in u]
            if not urls:
                continue
            status, _ = get(urls[0], 64 << 10)
            print(f"{status or 'no answer'} {name} {urls[0]}")
            if not 200 <= status < 400:
                found.append(f"{name}: {urls[0]} answered {status or 'nothing'}")
            done += 1
        if done == n:
            break
    return found


def snapshot_names(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as f:
        return {r["name"] for r in csv.DictReader(f, delimiter="\t")}


def selftest() -> None:
    head = "| # | dataset |\n"
    good = (
        "## 6. The matrix\n"
        "| 1 | [`a`](u) | A | entities | integrate | T-5253 | `Road` (Transportation) | ngsi-ld | WFS | yearly | CC-BY-4.0 | 200 | n | 2 |\n"
        "| 2 | [`b`](u) | B | statistics | skip | - | - | - | XLSX | ended | CC-BY-4.0 | 200 | survey | - |\n"
        "## 7. Nothing left\n- `b`: survey.\n## 8. Provenance\n"
    )
    assert problems(head + good, {"a", "b"}, {"T-5253"}) == [], problems(
        head + good, {"a", "b"}, {"T-5253"}
    )
    assert problems(good, {"a", "b"}, None) == []
    assert any("not in the HRI snapshot" in p for p in problems(good, {"b"}, None))
    assert any("has no row" in p for p in problems(good, {"a", "b", "c"}, None))
    assert any(
        "not a task on the board" in p for p in problems(good, {"a", "b"}, {"T-5254"})
    )
    assert any(
        "section 7" in p
        for p in problems(good.replace("- `b`: survey.\n", ""), {"a", "b"}, None)
    )
    assert any(
        "without a model" in p
        for p in problems(
            good.replace("`Road` (Transportation)", "-"), {"a", "b"}, None
        )
    )
    assert any(
        "T-5259, T-5278, T-5286, T-5378" in p
        for p in problems(good.replace("T-5253", "T-9999"), {"a", "b"}, None)
    )
    assert problems(good.replace("T-5253", "T-5378"), {"a", "b"}, None) == []
    assert any(
        "decision" in p
        for p in problems(good.replace("| integrate |", "| maybe |"), {"a", "b"}, None)
    )
    assert any(
        "twice" in p
        for p in problems(good + good.splitlines()[1] + "\n", {"a", "b"}, None)
    )
    assert any(
        "score" in p
        for p in problems(good.replace("| n | 2 |", "| n | x |"), {"a", "b"}, None)
    )
    assert any(
        "no score" in p
        for p in problems(
            good.replace("| survey | - |", "| survey | 1 |"), {"a", "b"}, None
        )
    )
    resc = good.replace(
        "## 7. Nothing left",
        "## 9. Re-score\n### 9.3 Counts\n"
        "| usable | rows |\n|---|---|\n| yes | 1 |\n| not-data | 1 |\n| total | 2 |\n"
        "### 9.5 All rows\n| 1 | `a` | yes | live: `e` 3 | live |\n"
        "| 2 | `b` | not-data | - | - |\n## 10. Plan\n## 7. Nothing left",
    )
    assert rescore_problems(resc) == [], rescore_problems(resc)
    assert any(
        "section 10" in p for p in rescore_problems(resc.replace("| live |", "| F1 |"))
    )
    assert any(
        "plan live" in p for p in rescore_problems(resc.replace("live: `e` 3", "empty"))
    )
    assert any(
        "matrix row" in p
        for p in rescore_problems(resc.replace("| 2 | `b` | not", "| 3 | `b` | not"))
    )
    assert any(
        "usable" in p
        for p in rescore_problems(resc.replace("| not-data | - |", "| maybe | - |"))
    )
    assert any(
        "with plan" in p
        for p in rescore_problems(
            resc.replace("| not-data | - | - |", "| not-data | - | B1 |")
        )
    )
    assert any(
        "9.3" in p for p in rescore_problems(resc.replace("| yes | 1 |", "| yes | 2 |"))
    )
    print("selftest ok")


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if argv[1:] == ["probe"]:
        found = probe(PAGE.read_text(encoding="utf-8"))
        for p in found:
            print(f"dead: {p}", file=sys.stderr)
        return 1 if found else 0
    if argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    snapshot = snapshot_names(SNAPSHOT)
    board = board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    text = PAGE.read_text(encoding="utf-8")
    found = problems(text, snapshot, board) + rescore_problems(text)
    for p in found:
        print(f"{PAGE.relative_to(ROOT)}: {p}", file=sys.stderr)
    if found:
        return 1
    rows, _ = parse(PAGE.read_text(encoding="utf-8"))
    print(
        f"helsinki open data: {len(rows)} rows, one per snapshot dataset, re-scored"
        + ("" if board is None else ", every batch on the board")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
