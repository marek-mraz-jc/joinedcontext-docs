#!/usr/bin/env python3
"""Every Helsinki HRI dataset has a decision in Research/helsinki-open-data.md (T-5252).

    check-helsinki-open-data.py check       # CI: the matrix against the committed snapshot
    check-helsinki-open-data.py --selftest

`check` needs no network. It fails when the matrix table does not hold exactly one row per
snapshot dataset, names a dataset the snapshot does not hold, has a decision outside
integrate/statistics/skip, an integrate or statistics row without a batch task and a model, a
batch outside T-5253..T-5259 and their splits T-5278, T-5378, a score outside -1..3 (a skip has none), or a skip that section 7 does not list with its reason. When the
board is mounted (TASKS_DIR, default /workspace/tasks) every batch id must also be a task file
there; CI has no board and skips that part.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/helsinki-open-data.md"
SNAPSHOT = ROOT / "Research/data/helsinki-hri-snapshot-2026-10-22.tsv"
DECISIONS = {"integrate", "statistics", "skip"}
BATCHES = {f"T-{n}" for n in range(5253, 5260)} | {"T-5278", "T-5378"}
ROW = re.compile(r"^\| \d+ \| \[`([^`]+)`\]")
SKIP_ITEM = re.compile(r"^- `([^`]+)`: (.+)$")


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
        "T-5259, T-5278, T-5378" in p
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
    print("selftest ok")


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    snapshot = snapshot_names(SNAPSHOT)
    board = board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    found = problems(PAGE.read_text(encoding="utf-8"), snapshot, board)
    for p in found:
        print(f"{PAGE.relative_to(ROOT)}: {p}", file=sys.stderr)
    if found:
        return 1
    rows, _ = parse(PAGE.read_text(encoding="utf-8"))
    print(
        f"helsinki open data: {len(rows)} rows, one per snapshot dataset"
        + ("" if board is None else ", every batch on the board")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
