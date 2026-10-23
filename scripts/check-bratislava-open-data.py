#!/usr/bin/env python3
"""Every data.bratislava.sk hub item has a decision in Research/bratislava-open-data.md (T-5272).

    check-bratislava-open-data.py check       # CI: the matrix against the committed snapshot
    check-bratislava-open-data.py --selftest

`check` needs no network. It fails when the matrix does not hold exactly one row per hub item id
of the snapshot, names an id the snapshot does not hold, numbers its rows out of order, has a
decision outside integrate/statistics/skip, a licence or record count that differs from the
snapshot, an integrate or statistics row without a batch of T-5273 or T-5274 and a model, a
statistics row whose model is not KeyPerformanceIndicator, a score outside -1..3 (a skip has
none), or a skip that section 7 does not list with its reason. When the board is mounted
(TASKS_DIR, default /workspace/tasks) every batch id must also be a task file there; CI has no
board and skips that part.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/bratislava-open-data.md"
SNAPSHOT = ROOT / "Research/data/bratislava-hub-snapshot-2026-10-23.tsv"
DECISIONS = {"integrate", "statistics", "skip"}
BATCHES = {"T-5273", "T-5274"}
ROW = re.compile(r"^\| (\d+) \| \[`([0-9a-f]{32})`\]")
SKIP_ITEM = re.compile(r"^- `([0-9a-f]{32})`: (.+)$")


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.split("|")[1:-1]]


def parse(text: str) -> tuple[list[tuple[int, str, list[str]]], dict[str, str]]:
    rows, skipped, section = [], {}, ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line
        elif m := ROW.match(line):
            rows.append((int(m.group(1)), m.group(2), cells(line)))
        elif section.startswith("## 7.") and (m := SKIP_ITEM.match(line)):
            skipped[m.group(1)] = m.group(2)
    return rows, skipped


def board_ids(tasks_dir: Path) -> set[str] | None:
    if not tasks_dir.is_dir():
        return None
    files = list(tasks_dir.glob("T-*.md")) + list(tasks_dir.glob("finished/T-*.md"))
    return {"-".join(f.name.split("-")[:2]) for f in files}


def records(cell: str) -> str:
    return cell.replace(",", "") if cell != "file" else ""


def problems(text: str, snapshot: dict[str, dict], board: set[str] | None) -> list[str]:
    rows, skipped = parse(text)
    found, seen = [], set()
    for want, (num, item, r) in enumerate(rows, 1):
        if num != want:
            found.append(f"{item}: row number {num}, {want} expected")
        if len(r) != 14:
            found.append(f"{item}: {len(r)} cells, 14 expected")
            continue
        decision, batch, model, licence, count, score = (
            r[4],
            r[5],
            r[6],
            r[10],
            r[11],
            r[13],
        )
        if item in seen:
            found.append(f"{item}: listed twice")
        seen.add(item)
        snap = snapshot.get(item)
        if snap is None:
            found.append(f"{item}: not in the hub snapshot")
        else:
            if licence != snap["license"]:
                found.append(
                    f"{item}: licence {licence!r}, snapshot says {snap['license']!r}"
                )
            if records(count) != snap["records"]:
                found.append(
                    f"{item}: records {count!r}, snapshot says {snap['records']!r}"
                )
        if decision not in DECISIONS:
            found.append(
                f"{item}: decision {decision!r} is not integrate, statistics or skip"
            )
        elif decision == "skip":
            if score != "-":
                found.append(f"{item}: a skip has no score, found {score!r}")
            if not skipped.get(item):
                found.append(
                    f"{item}: skipped but not listed with a reason in section 7"
                )
        else:
            if batch not in BATCHES:
                found.append(f"{item}: batch {batch!r} is not T-5273 or T-5274")
            elif board is not None and batch not in board:
                found.append(f"{item}: batch {batch} is not a task on the board")
            if not re.fullmatch(r"-?[0-3]", score):
                found.append(f"{item}: score {score!r} is not -1..3")
            if "`" not in model:
                found.append(f"{item}: {decision} without a model")
            if decision == "statistics" and "`KeyPerformanceIndicator`" not in model:
                found.append(
                    f"{item}: statistics row not modelled as KeyPerformanceIndicator"
                )
    for item in sorted(set(snapshot) - seen):
        found.append(f"{item}: in the snapshot but has no row")
    skip_rows = {item for _, item, r in rows if len(r) == 14 and r[4] == "skip"}
    for item in sorted(set(skipped) - skip_rows):
        found.append(f"{item}: in section 7 but its row is not a skip")
    return found


def load_snapshot(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f, delimiter="\t")}


def selftest() -> None:
    a, b = "a" * 32, "b" * 32
    snap = {
        a: {"license": "CC-BY-4.0", "records": "1200"},
        b: {"license": "CC-BY-4.0", "records": "9"},
    }
    good = (
        "## 6. The matrix\n"
        f"| 1 | [`{a}`](u) | A | entities | integrate | T-5273 | `TrafficFlowObserved` (Transportation) | ngsi-ld | FS | 2026-10-22 | CC-BY-4.0 | 1,200 | n | 3 |\n"
        f"| 2 | [`{b}`](u) | B | entities | skip | - | - | - | FS | 2024-07-09 | CC-BY-4.0 | 9 | survey | - |\n"
        f"## 7. Nothing left\n- `{b}`: B: survey.\n## 8. Provenance\n"
    )
    assert problems(good, snap, {"T-5273"}) == [], problems(good, snap, {"T-5273"})
    assert problems(good, snap, None) == []
    assert any(
        "not in the hub snapshot" in p for p in problems(good, {b: snap[b]}, None)
    )
    assert any(
        "has no row" in p for p in problems(good, {**snap, "c" * 32: snap[b]}, None)
    )
    assert any("not a task on the board" in p for p in problems(good, snap, {"T-5274"}))
    assert any(
        "row number" in p
        for p in problems(good.replace("| 2 |", "| 3 |", 1), snap, None)
    )
    assert any(
        "licence" in p
        for p in problems(good.replace("CC-BY-4.0 | 9", "CC-BY-NC-4.0 | 9"), snap, None)
    )
    assert any(
        "records" in p for p in problems(good.replace("1,200", "1,201"), snap, None)
    )
    assert any(
        "not T-5273 or T-5274" in p
        for p in problems(good.replace("T-5273", "T-5258"), snap, None)
    )
    assert any(
        "no score" in p
        for p in problems(good.replace("survey | -", "survey | 1"), snap, None)
    )
    assert any(
        "section 7" in p
        for p in problems(good.replace(f"- `{b}`: B: survey.\n", ""), snap, None)
    )
    assert any(
        "listed twice" in p
        for p in problems(good.replace(f"[`{b}`]", f"[`{a}`]"), snap, None)
    )
    stat = good.replace("| entities | integrate |", "| statistics | statistics |", 1)
    assert any("KeyPerformanceIndicator" in p for p in problems(stat, snap, None))
    assert any(
        "score" in p
        for p in problems(good.replace("| n | 3 |", "| n | 4 |"), snap, None)
    )
    print("selftest ok")


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if sys.argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    board = board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    found = problems(PAGE.read_text(encoding="utf-8"), load_snapshot(SNAPSHOT), board)
    for p in found:
        print(p, file=sys.stderr)
    if found:
        return 1
    print(
        f"{PAGE.relative_to(ROOT)}: every hub item of the snapshot has one row and a decision"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
