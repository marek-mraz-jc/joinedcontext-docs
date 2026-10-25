#!/usr/bin/env python3
"""Every Praha open dataset has a decision in Research/praha-open-data.md (T-5267).

    check-praha-open-data.py check       # CI: the matrix against the committed snapshots
    check-praha-open-data.py --selftest

`check` needs no network. It fails when the matrix does not hold exactly one row per entry of the
four snapshots (city catalogue, IPR geoportal, Golemio OpenAPI paths, other sources), names an id
its source snapshot does not hold, has a decision outside live/integrate/blocked/skip/part, a live
or integrate row without a batch of T-5268, T-5269, T-5270, T-5276, T-5423 or T-5428 and a model, an integrate row
scoring under 1, a blocked or skip row without a reason, a score outside -1..3, or a part row that
does not name the row it belongs to. When the board is mounted (TASKS_DIR, default /workspace/tasks)
every batch id must also be a task file there; CI has no board and skips that part.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/praha-open-data.md"
SNAPSHOTS = {
    "city": ROOT / "Research/data/praha-city-catalogue-snapshot-2026-10-22.tsv",
    "ipr": ROOT / "Research/data/praha-ipr-geoportal-snapshot-2026-10-23.tsv",
    "golemio": ROOT / "Research/data/praha-golemio-endpoints-2026-10-22.tsv",
    "other": ROOT / "Research/data/praha-other-sources-2026-10-23.tsv",
}
DECISIONS = {"live", "integrate", "blocked", "skip", "part"}
BATCHES = {"T-5268", "T-5269", "T-5270", "T-5276", "T-5423", "T-5428"}
ROW = re.compile(r"^\| \d+ \| \[`([^`]+)`\]")
PART = re.compile(r"^(?:history|detail) of `([^`]+)`")


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]


def rows_of(text: str) -> list[tuple[str, list[str]]]:
    return [
        (m.group(1), cells(line))
        for line in text.splitlines()
        if (m := ROW.match(line))
    ]


def board_ids(tasks_dir: Path) -> set[str] | None:
    if not tasks_dir.is_dir():
        return None
    files = list(tasks_dir.glob("T-*.md")) + list(tasks_dir.glob("finished/T-*.md"))
    return {"-".join(f.name.split("-")[:2]) for f in files}


def problems(
    text: str, snapshots: dict[str, set[str]], board: set[str] | None
) -> list[str]:
    found: list[str] = []
    rows = rows_of(text)
    decision_of = {name: r[4] for name, r in rows if len(r) == 11}
    seen: set[tuple[str, str]] = set()
    for name, r in rows:
        if len(r) != 11:
            found.append(f"{name}: {len(r)} cells, 11 expected")
            continue
        source, decision, batch, model, note, score = (
            r[3],
            r[4],
            r[5],
            r[6],
            r[9],
            r[10],
        )
        if (source, name) in seen:
            found.append(f"{name}: listed twice")
        seen.add((source, name))
        if source not in snapshots:
            found.append(
                f"{name}: source {source!r} is not city, ipr, golemio or other"
            )
        elif name not in snapshots[source]:
            found.append(f"{name}: not in the {source} snapshot")
        if decision not in DECISIONS:
            found.append(
                f"{name}: decision {decision!r} is not live, integrate, blocked, skip or part"
            )
            continue
        if decision == "part":
            m = PART.match(note)
            if score != "-":
                found.append(f"{name}: a part row has no score, found {score!r}")
            if not m:
                found.append(
                    f"{name}: a part row names its row as 'history of `x`' or 'detail of `x`'"
                )
            elif decision_of.get(m.group(1)) in (None, "part"):
                found.append(
                    f"{name}: belongs to {m.group(1)}, which is not a row of its own"
                )
            continue
        if not re.fullmatch(r"-?[0-3]", score):
            found.append(f"{name}: score {score!r} is not -1..3")
        elif decision == "integrate" and int(score) < 1:
            found.append(
                f"{name}: integrate with score {score}, a batch builds only rows scoring 1 or more"
            )
        if decision in ("live", "integrate"):
            if batch not in BATCHES:
                found.append(
                    f"{name}: batch {batch!r} is not one of {', '.join(sorted(BATCHES))}"
                )
            elif board is not None and batch not in board:
                found.append(f"{name}: batch {batch} is not a task on the board")
            if "`" not in model:
                found.append(f"{name}: {decision} without a model")
        elif batch != "-":
            found.append(f"{name}: a {decision} row has no batch, found {batch!r}")
        if decision in ("blocked", "skip") and len(note) < 10:
            found.append(f"{name}: {decision} without a reason in the note")
    for source, names in snapshots.items():
        for name in sorted(names - {n for s, n in seen if s == source}):
            found.append(f"{name}: in the {source} snapshot but has no row")
    return found


def snapshot_ids(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f, delimiter="\t")}


def selftest() -> None:
    good = (
        "| 1 | [`a`](u) | A | city | live | T-5270 | `Road` (Transportation) | ngsi-ld | monthly | runs | 2 |\n"
        "| 2 | [`b`](u) | B | city | part | - | - | - | - | history of `a` (2020) | - |\n"
        "| 3 | [`/v2/x`](u) | X | golemio | integrate | T-5269 | `Vehicle` (Transportation) | ngsi-ld | - | live | 1 |\n"
        "| 4 | [`/v2/y`](u) | Y | golemio | skip | - | - | - | - | internal route of the spec | 0 |\n"
        "| 5 | [`/v2/z`](u) | Z | golemio | blocked | - | `Alert` (Alert) | ngsi-ld | - | 403 for the project key | 3 |\n"
    )
    snaps = {"city": {"a", "b"}, "golemio": {"/v2/x", "/v2/y", "/v2/z"}}
    assert problems(good, snaps, {"T-5269", "T-5270"}) == [], problems(
        good, snaps, {"T-5269", "T-5270"}
    )
    assert problems(good, snaps, None) == []

    def bad(text: str, needle: str, board: set[str] | None = None) -> None:
        got = problems(text, snaps, board)
        assert any(needle in p for p in got), (needle, got)

    assert any(
        "has no row" in p
        for p in problems(good, {**snaps, "city": {"a", "b", "c"}}, None)
    )
    bad(good.replace("| A | city |", "| A | ipr |"), "source")
    bad(good.replace("[`a`]", "[`q`]"), "not in the city snapshot")
    bad(good, "not a task on the board", {"T-5269"})
    bad(good.replace("T-5270", "T-9999"), "batch 'T-9999'")
    bad(
        good.replace(
            "| live | T-5270 | `Road` (Transportation)", "| live | T-5270 | -"
        ),
        "without a model",
    )
    bad(good.replace("| live |", "| maybe |"), "decision")
    bad(good + good.splitlines()[0] + "\n", "twice")
    bad(good.replace("| runs | 2 |", "| runs | x |"), "score 'x'")
    bad(good.replace("| live | 1 |", "| live | 0 |"), "integrate with score 0")
    bad(good.replace("internal route of the spec", "-"), "without a reason")
    bad(good.replace("| skip | - |", "| skip | T-5269 |"), "has no batch")
    bad(good.replace("history of `a`", "history of `zz`"), "not a row of its own")
    bad(
        good.replace("history of `a` (2020) | - |", "an old year | - |"),
        "names its row",
    )
    bad(good.replace("(2020) | - |", "(2020) | 1 |"), "part row has no score")
    print("selftest ok")


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    snapshots = {source: snapshot_ids(path) for source, path in SNAPSHOTS.items()}
    board = board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    text = PAGE.read_text(encoding="utf-8")
    found = problems(text, snapshots, board)
    for p in found:
        print(f"{PAGE.relative_to(ROOT)}: {p}", file=sys.stderr)
    if found:
        return 1
    print(
        f"praha open data: {len(rows_of(text))} rows, one per snapshot entry"
        + ("" if board is None else ", every batch on the board")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
