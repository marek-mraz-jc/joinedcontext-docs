#!/usr/bin/env python3
"""Every data.bratislava.sk hub item has a decision in Research/bratislava-open-data.md (T-5272).

    check-bratislava-open-data.py check       # CI: the matrix against the committed snapshots
    check-bratislava-open-data.py probe       # network: 10 sampled usable rows still answer (T-5664)
    check-bratislava-open-data.py --selftest

`check` needs no network. It fails when the matrix does not hold exactly one row per hub item id
of the snapshot, names an id the snapshot does not hold, numbers its rows out of order, has a
decision outside integrate/statistics/skip, a licence or record count that differs from the
snapshot, an integrate or statistics row without a batch of T-5273 or T-5274 and a model, a
statistics row whose model is not KeyPerformanceIndicator, a score outside -1..3 (a skip has
none), or a skip that section 7 does not list with its reason. When the board is mounted
(TASKS_DIR, default /workspace/tasks) every batch id must also be a task file there; CI has no
board and skips that part.

The re-score of 2026-10-25 (T-5664) adds three cells per row and section 6.5. `check` also fails
when `usable` is not `yes` or a rule word, disagrees with the 2026-10-25 snapshot (`dead`, `empty`
status; a non-commercial or no-derivatives licence is `licence`), when `dev` is not `-` exactly for
the unusable rows, when `plan` does not follow `dev` (a seeded row goes live with T-5648, a row not
seeded names a parked batch or a P batch), when a P batch holds more than 25 rows, or when a batch
line of the section 6.5 table lists other row ids than the rows that name it.
"""

from __future__ import annotations

import csv
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/bratislava-open-data.md"
SNAPSHOT = ROOT / "Research/data/bratislava-hub-snapshot-2026-10-23.tsv"
RESCORE = ROOT / "Research/data/bratislava-hub-snapshot-2026-10-25.tsv"
WORDS = {
    "dead",
    "stale",
    "pdf-only",
    "licence",
    "empty",
    "duplicate",
    "outside",
    "no-model",
    "personal",
}
PARKED = {"T-5435", "T-5444"}
PUBLISH = "T-5648"
PLAN_ROW = re.compile(r"^\| (P\d+|T-\d+) \| (\d+) \|")
CELLS = 17
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


def plan_lines(text: str) -> dict[str, str]:
    """Batch -> its row-id cell, from the table of section 6.5."""
    found, section = {}, ""
    for line in text.splitlines():
        if line.startswith("### "):
            section = line
        elif section.startswith("### 6.5") and PLAN_ROW.match(line):
            c = cells(line)
            found[c[0]] = c[-1]
    return found


def expand(cell: str) -> set[int] | None:
    """'5, 7-9' -> {5, 7, 8, 9}; None for a cell that is not a list of row ids."""
    out: set[int] = set()
    for part in cell.split(","):
        m = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", part)
        if not m:
            return None
        out.update(range(int(m.group(1)), int(m.group(2) or m.group(1)) + 1))
    return out


def rescore_problems(text: str, rows, rescore: dict[str, dict]) -> list[str]:
    found: list[str] = []
    members: dict[str, set[int]] = {}
    for num, item, r in rows:
        if len(r) != CELLS:
            continue
        usable, dev, plan = r[14], r[15], r[16]
        snap = rescore.get(item)
        if snap is None:
            found.append(f"{item}: not in the 2026-10-25 snapshot")
            continue
        if usable != "yes" and usable not in WORDS:
            found.append(f"{item}: usable {usable!r} is not yes or a rule word")
        if snap["status"] in ("dead", "empty") and usable != snap["status"]:
            found.append(
                f"{item}: the snapshot says {snap['status']}, the row says {usable!r}"
            )
        if re.search(r"-N[CD]", snap["license"]) and usable != "licence":
            found.append(
                f"{item}: licence {snap['license']} is not open, the row says {usable!r}"
            )
        if (usable == "yes") != (dev != "-"):
            found.append(f"{item}: dev {dev!r} for usable {usable!r}")
        want = {"-": {"-"}, "seeded, 404": {PUBLISH}, "live": {"-"}}.get(dev)
        if dev == "not seeded":
            ok = plan in PARKED or re.fullmatch(r"P\d+", plan)
        elif want is None:
            found.append(
                f"{item}: dev {dev!r} is not live, seeded, 404, not seeded or -"
            )
            continue
        else:
            ok = plan in want
        if not ok:
            found.append(f"{item}: plan {plan!r} does not follow dev {dev!r}")
        if plan != "-":
            members.setdefault(plan, set()).add(num)
    listed = plan_lines(text)
    for batch, nums in sorted(members.items()):
        if batch.startswith("P") and len(nums) > 25:
            found.append(f"{batch}: {len(nums)} rows, at most 25")
        if batch not in listed:
            found.append(f"{batch}: no line in the section 6.5 table")
        elif batch != PUBLISH and expand(listed[batch]) != nums:
            found.append(
                f"{batch}: the section 6.5 line lists other rows than the matrix"
            )
    for batch in sorted(set(listed) - set(members)):
        found.append(f"{batch}: a section 6.5 line no row names")
    return found


def board_ids(tasks_dir: Path) -> set[str] | None:
    if not tasks_dir.is_dir():
        return None
    files = list(tasks_dir.glob("T-*.md")) + list(tasks_dir.glob("finished/T-*.md"))
    return {"-".join(f.name.split("-")[:2]) for f in files}


def records(cell: str) -> str:
    return cell.replace(",", "") if cell != "file" else ""


def problems(
    text: str,
    snapshot: dict[str, dict],
    board: set[str] | None,
    rescore: dict[str, dict] | None = None,
) -> list[str]:
    rows, skipped = parse(text)
    found = rescore_problems(text, rows, rescore) if rescore is not None else []
    seen: set[str] = set()
    for want, (num, item, r) in enumerate(rows, 1):
        if num != want:
            found.append(f"{item}: row number {num}, {want} expected")
        if len(r) != CELLS:
            found.append(f"{item}: {len(r)} cells, {CELLS} expected")
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
    skip_rows = {item for _, item, r in rows if len(r) == CELLS and r[4] == "skip"}
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
        f"| 1 | [`{a}`](u) | A | entities | integrate | T-5273 | `TrafficFlowObserved` (Transportation) | ngsi-ld | FS | 2026-10-22 | CC-BY-4.0 | 1,200 | n | 3 | yes | not seeded | P1 |\n"
        f"| 2 | [`{b}`](u) | B | entities | skip | - | - | - | FS | 2024-07-09 | CC-BY-4.0 | 9 | survey | - | no-model | - | - |\n"
        "### 6.5 Re-score\n| P1 | 1 | tables | `KeyPerformanceIndicator` | none | 1 |\n"
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
    re_snap = {
        a: {"status": "ok", "license": "CC-BY-4.0"},
        b: {"status": "ok", "license": "CC-BY-4.0"},
    }
    assert problems(good, snap, None, re_snap) == [], problems(
        good, snap, None, re_snap
    )

    def rescored(text: str, rs: dict = re_snap) -> list[str]:
        return problems(text, snap, None, rs)

    assert any("not in the 2026-10-25" in p for p in rescored(good, {b: re_snap[b]}))
    assert any("rule word" in p for p in rescored(good.replace("no-model", "boring")))
    dead = {**re_snap, a: {"status": "dead", "license": "CC-BY-4.0"}}
    assert any("snapshot says dead" in p for p in rescored(good, dead))
    nc = {**re_snap, a: {"status": "ok", "license": "CC-BY-NC-4.0"}}
    assert any("is not open" in p for p in rescored(good, nc))
    assert any(
        "dev '-' for usable 'yes'" in p
        for p in rescored(good.replace("yes | not seeded", "yes | -"))
    )
    assert any(
        "does not follow dev" in p
        for p in rescored(good.replace("| P1 |\n", "| T-5648 |\n"))
    )
    assert any(
        "does not follow dev" in p
        for p in rescored(good.replace("| not seeded | P1 |", "| seeded, 404 | P1 |"))
    )
    assert any(
        "lists other rows" in p
        for p in rescored(good.replace("| none | 1 |", "| none | 1-2 |"))
    )
    assert any(
        "no line in the section 6.5" in p
        for p in rescored(good.replace("| P1 | 1 |", "| P2 | 1 |"))
    )
    assert any(
        "no row names" in p
        for p in rescored(
            good.replace(
                "### 6.5 Re-score\n", "### 6.5 Re-score\n| P9 | 1 | x | y | z | 1 |\n"
            )
        )
    )
    assert expand("5, 7-9") == {5, 7, 8, 9} and expand("every row") is None
    many = "".join(
        f"| {i} | [`{i:032x}`](u) | T | entities | integrate | T-5273 | `X` (Y) | o | FS | d | CC-BY-4.0 | 1 | n | 1 | yes | not seeded | P1 |\n"
        for i in range(1, 27)
    )
    assert any(
        "26 rows, at most 25" in p
        for p in rescore_problems(
            "", parse(many)[0], {f"{i:032x}": re_snap[a] for i in range(1, 27)}
        )
    )
    assert sample({f"{i:032x}": {"status": "ok"} for i in range(30)}, [], 10) == []
    print("selftest ok")


HOSTS = ("https://services8.arcgis.com/pRlN1m0su5BYaFAS/", "https://www.arcgis.com/")


def sample(rescore: dict[str, dict], rows, k: int) -> list[str]:
    """Item ids of k usable rows, drawn at random (PROBE_SEED fixes the draw)."""
    usable = sorted(
        item
        for _, item, r in rows
        if len(r) == CELLS and r[14] == "yes" and item in rescore
    )
    rng = random.Random(os.environ.get("PROBE_SEED"))
    return rng.sample(usable, min(k, len(usable)))


def answers(item: str, snap: dict) -> str | None:
    """None when the source answers, else why not. Read-only, 20 s timeout, 2 MB cap."""
    url = (
        snap["url"] + "?f=json"
        if snap["url"]
        else f"https://www.arcgis.com/sharing/rest/content/items/{item}/data"
    )
    if not url.startswith(HOSTS):
        return f"host not allowed: {url}"
    req = urllib.request.Request(
        url,
        method="GET" if snap["url"] else "HEAD",
        headers={"User-Agent": "joinedcontext-docs-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(2_000_000) if snap["url"] else b""
    except OSError as e:
        return str(e)
    if b'"error"' in body[:200]:
        return body[:200].decode("utf-8", "replace")
    return None


def probe() -> int:
    rows, _ = parse(PAGE.read_text(encoding="utf-8"))
    rescore = load_snapshot(RESCORE)
    dead = 0
    for item in sample(rescore, rows, 10):
        why = answers(item, rescore[item])
        print(f"{item}: {'answers' if why is None else 'dead: ' + why}")
        dead += why is not None
    return 1 if dead else 0


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if sys.argv[1:] == ["probe"]:
        return probe()
    if sys.argv[1:] != ["check"]:
        print(__doc__, file=sys.stderr)
        return 2
    board = board_ids(Path(os.environ.get("TASKS_DIR", "/workspace/tasks")))
    found = problems(
        PAGE.read_text(encoding="utf-8"),
        load_snapshot(SNAPSHOT),
        board,
        load_snapshot(RESCORE),
    )
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
