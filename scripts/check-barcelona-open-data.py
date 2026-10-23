#!/usr/bin/env python3
"""Every Open Data BCN dataset has a decision in Research/barcelona-open-data.md (T-5261).

    check-barcelona-open-data.py check       # CI: the matrix against the committed snapshot
    check-barcelona-open-data.py --selftest

The rules are those of check-helsinki-open-data.py (one row per snapshot dataset, a decision of
integrate/statistics/skip, a batch and a model for each integrate or statistics row, a score of
-1..3, every skip listed with its reason in section 7), with the Barcelona batches T-5262..T-5266.
When the board is mounted (TASKS_DIR, default /workspace/tasks) every batch id must also be a
task file there; CI has no board and skips that part.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/barcelona-open-data.md"
SNAPSHOT = ROOT / "Research/data/barcelona-opendata-snapshot-2026-10-22.tsv"
BATCHES = {f"T-{n}" for n in range(5262, 5267)}
SOURCE = "Open Data BCN"

_spec = importlib.util.spec_from_file_location(
    "matrix", Path(__file__).with_name("check-helsinki-open-data.py")
)
matrix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(matrix)


def problems(text: str, snapshot: set[str], board: set[str] | None) -> list[str]:
    return matrix.problems(text, snapshot, board, BATCHES, SOURCE)


def selftest() -> None:
    good = (
        "## 6. The matrix\n"
        "| 1 | [`a`](u) | A | entities | integrate | T-5262 | `TrafficFlowObserved` (Transportation) | ngsi-ld | CSV | 5 min | CC-BY-4.0 | 200 | n | 3 |\n"
        "| 2 | [`b`](u) | B | statistics | statistics | T-5266 | `KeyPerformanceIndicator` (KeyPerformanceIndicator) | ngsi-ld | CSV | yearly | CC-BY-4.0 | 200 | n | 2 |\n"
        "| 3 | [`c`](u) | C | documents | skip | - | - | - | XML | monthly | CC-BY-4.0 | 200 | index | - |\n"
        "## 7. Nothing left\n- `c`: document index.\n## 8. Provenance\n"
    )
    names = {"a", "b", "c"}
    assert problems(good, names, {"T-5262", "T-5266"}) == [], problems(
        good, names, {"T-5262", "T-5266"}
    )
    assert any("Open Data BCN snapshot" in p for p in problems(good, {"b", "c"}, None))
    assert any("has no row" in p for p in problems(good, names | {"d"}, None))
    assert any(
        "is not one of T-5262, T-5263, T-5264, T-5265, T-5266" in p
        for p in problems(good.replace("T-5262 |", "T-5253 |"), names, None)
    )
    assert any(
        "not a task on the board" in p for p in problems(good, names, {"T-5262"})
    )
    assert any(
        "section 7" in p
        for p in problems(good.replace("- `c`: document index.\n", ""), names, None)
    )
    print("selftest ok")


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    text = PAGE.read_text(encoding="utf-8")
    board = matrix.board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    found = problems(text, matrix.snapshot_names(SNAPSHOT), board)
    for p in found:
        print(f"{PAGE.relative_to(ROOT)}: {p}", file=sys.stderr)
    if found:
        return 1
    rows, _ = matrix.parse(text)
    print(
        f"barcelona open data: {len(rows)} rows, one per snapshot dataset"
        + ("" if board is None else ", every batch on the board")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
