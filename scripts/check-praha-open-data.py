#!/usr/bin/env python3
"""Every Praha open dataset has a decision in Research/praha-open-data.md (T-5267, T-5665).

    check-praha-open-data.py check       # CI: the matrix against the committed snapshots
    check-praha-open-data.py probe       # network: 10 sampled usable rows still answer
    check-praha-open-data.py --selftest

`check` needs no network. It fails when the matrix does not hold exactly one row per entry of the
four snapshots (city catalogue, IPR geoportal, Golemio OpenAPI paths, other sources), names an id
its source snapshot does not hold, has a decision outside live/seeded/integrate/skip/part, a usable
verdict outside yes/part/stale/duplicate/login/format/licence/personal or one that disagrees with the
decision (skip exactly when not usable, part with part), a live row without a `live` dev cell, a
seeded row without a `seeded` dev cell, a live or seeded row without a build task, an integrate row
without a parked task or a planned batch (F-n, P-nn), a planned batch over 25 rows, a live, seeded
or integrate row without a model, a skip row without a reason, a score outside -1..3, or a part row
that does not name the row it belongs to. When the board is mounted (TASKS_DIR, default
/workspace/tasks) every task id must also be a task file there; CI has no board and skips that part.

`probe` reads the source of each row in SAMPLE (timeout 30 s, at most 64 KiB) and fails when one
does not answer with data or the page no longer calls the row usable.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "Research/praha-open-data.md"
SNAPSHOTS = {
    "city": ROOT / "Research/data/praha-city-catalogue-snapshot-2026-10-22.tsv",
    "ipr": ROOT / "Research/data/praha-ipr-geoportal-snapshot-2026-10-23.tsv",
    "golemio": ROOT / "Research/data/praha-golemio-endpoints-2026-10-22.tsv",
    "other": ROOT / "Research/data/praha-other-sources-2026-10-23.tsv",
}
DECISIONS = {"live", "seeded", "integrate", "skip", "part"}
UNUSABLE = {"stale", "duplicate", "login", "format", "licence", "personal"}
BUILT = {"T-5268", "T-5269", "T-5270", "T-5276", "T-5423", "T-5424", "T-5425", "T-5428", "T-5429"}
PARKED = {"T-5426", "T-5427", "T-5428", "T-5684"}
PLANNED = re.compile(r"^(?:F-\d|P-\d\d)$")
CELLS = 13
IPR = "https://mp.iprpraha.cz/arcgis/rest/services/Hosted/"
COUNT = "/FeatureServer/0/query?where=1%3D1&returnCountOnly=true&f=json"
CITY = "https://opendata-storage.praha.eu/"
# Row number, source of the data. Keyless sources only: Golemio needs the project key.
SAMPLE = [
    (9, IPR + "FSV_CUR_OV_KULTZAR_B" + COUNT),
    (10, IPR + "MAP_CUR_MAP_MESTSKECASTI_P" + COUNT),
    (14, IPR + "FSV_CUR_OV_SKOLSTVI_B" + COUNT),
    (32, IPR + "OPK_CUR_OPK_SMZ_VP_B" + COUNT),
    (57, IPR + "URK_CUR_URK_BUC_P" + COUNT),
    (235, IPR + "MPP_CUR_MPP_700_TI_KORIDORY_P" + COUNT),
    (
        22,
        CITY
        + "ROZ_rozpocet_finance/financni_vztahy/Zdroje/2026/Financni_vztahy_mezi_HMP_a_MC_HMP_2026.json",
    ),
    (133, CITY + "HOM_obsazene_nebytove_prostory/Obsazene_nebytove_prostory_MHMP.csv"),
    (5, "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_tg/gbfs.json"),
    (15, "https://data.pid.cz/pointsOfSale/json/pointsOfSale.json"),
]
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
    files = list(tasks_dir.glob("T-*.md")) + list(tasks_dir.glob("finished/T-*.md")) + list(tasks_dir.glob("later/T-*.md"))
    return {"-".join(f.name.split("-")[:2]) for f in files}


def problems(
    text: str, snapshots: dict[str, set[str]], board: set[str] | None
) -> list[str]:
    found: list[str] = []
    rows = rows_of(text)
    decision_of = {name: r[4] for name, r in rows if len(r) == CELLS}
    seen: set[tuple[str, str]] = set()
    planned: dict[str, int] = {}
    for name, r in rows:
        if len(r) != CELLS:
            found.append(f"{name}: {len(r)} cells, {CELLS} expected")
            continue
        source, decision, batch, model, note, score, usable, dev = (
            r[3],
            r[4],
            r[5],
            r[6],
            r[9],
            r[10],
            r[11],
            r[12],
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
                f"{name}: decision {decision!r} is not live, seeded, integrate, skip or part"
            )
            continue
        if usable not in UNUSABLE | {"yes", "part"}:
            found.append(f"{name}: usable {usable!r} is not yes, part or a reason")
        elif (decision == "part") != (usable == "part") or (decision == "skip") != (
            usable in UNUSABLE
        ):
            found.append(f"{name}: usable {usable!r} does not fit decision {decision}")
        if decision == "live" and not dev.startswith("live, "):
            found.append(f"{name}: live without a live dev count")
        if decision == "seeded" and not dev.startswith("seeded, "):
            found.append(f"{name}: seeded without what its Endpoint answers")
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
        if decision in ("live", "seeded", "integrate"):
            allowed = BUILT if decision != "integrate" else PARKED
            if decision == "integrate" and PLANNED.match(batch):
                planned[batch] = planned.get(batch, 0) + 1
            elif batch not in allowed:
                found.append(
                    f"{name}: batch {batch!r} is not one of {', '.join(sorted(allowed))}"
                    + (" or a planned batch" if decision == "integrate" else "")
                )
            elif board is not None and batch not in board:
                found.append(f"{name}: batch {batch} is not a task on the board")
            if "`" not in model:
                found.append(f"{name}: {decision} without a model")
        elif batch != "-":
            found.append(f"{name}: a {decision} row has no batch, found {batch!r}")
        if decision == "skip" and len(note) < 10:
            found.append(f"{name}: {decision} without a reason in the note")
    for batch, n in sorted(planned.items()):
        if n > 25:
            found.append(f"{batch}: {n} rows, a batch holds at most 25")
    for source, names in snapshots.items():
        for name in sorted(names - {n for s, n in seen if s == source}):
            found.append(f"{name}: in the {source} snapshot but has no row")
    return found


def snapshot_ids(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f, delimiter="\t")}


def selftest() -> None:
    good = (
        "| 1 | [`a`](u) | A | city | live | T-5270 | `Road` (Transportation) | ngsi-ld | monthly | runs | 2 | yes | live, 12 |\n"
        "| 2 | [`b`](u) | B | city | part | - | - | - | - | history of `a` (2020) | - | part | - |\n"
        "| 3 | [`/v2/x`](u) | X | golemio | integrate | P-01 | `Vehicle` (Transportation) | ngsi-ld | - | feed | 1 | yes | - |\n"
        "| 4 | [`/v2/y`](u) | Y | golemio | skip | - | - | - | - | internal route of the spec | 0 | login | - |\n"
        "| 5 | [`/v2/z`](u) | Z | golemio | seeded | T-5269 | `Alert` (Alert) | ngsi-ld | - | reads the alerts | 3 | yes | seeded, `e` answers 404 |\n"
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
    bad(good.replace("| P-01 |", "| T-5269 |"), "batch 'T-5269'")
    bad(good.replace("| P-01 |", "| T-5426 |"), "not a task on the board", {"T-5269"})
    bad(good.replace("| 1 | yes | - |", "| 1 | stale | - |"), "does not fit")
    bad(good.replace("| 0 | login |", "| 0 | yes |"), "does not fit")
    bad(good.replace("| 0 | login |", "| 0 | gone |"), "usable 'gone'")
    bad(good.replace("| live, 12 |", "| - |"), "live without")
    bad(good.replace("| seeded, `e` answers 404 |", "| - |"), "seeded without")
    many = "".join(
        f"| {9 + i} | [`c{i}`](u) | C | city | integrate | P-02 | `Road` (Transportation) | ngsi-ld | - | x | 0 | yes | - |\n"
        for i in range(26)
    )
    bad(good + many, "26 rows")
    assert len(probe("")) == len(SAMPLE)
    assert all("sampled but" in p for p in probe(""))
    bad(
        good.replace(
            "| live | T-5270 | `Road` (Transportation)", "| live | T-5270 | -"
        ),
        "without a model",
    )
    bad(good.replace("| live |", "| maybe |"), "decision")
    bad(good + good.splitlines()[0] + "\n", "twice")
    bad(good.replace("| runs | 2 |", "| runs | x |"), "score 'x'")
    bad(good.replace("internal route of the spec", "-"), "without a reason")
    bad(good.replace("| skip | - |", "| skip | T-5269 |"), "has no batch")
    bad(good.replace("history of `a`", "history of `zz`"), "not a row of its own")
    bad(
        good.replace("history of `a` (2020) | - |", "an old year | - |"),
        "names its row",
    )
    bad(good.replace("(2020) | - |", "(2020) | 1 |"), "part row has no score")
    print("selftest ok")


def answers(url: str) -> str | None:
    """None when the source answers with data, else why not."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "jc-check-praha-open-data"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read(65536)
    except (OSError, ValueError) as e:  # URLError, HTTPError and timeouts are OSError
        return f"{type(e).__name__}: {e}"
    if not body.strip():
        return "empty answer"
    if url.endswith("f=json"):
        try:
            count = json.loads(body).get("count")
        except ValueError:
            return "not JSON"
        if not count:
            return f"count {count!r}"
    return None


def probe(text: str) -> list[str]:
    usable = {int(r[0]): r[11] for _, r in rows_of(text) if len(r) == CELLS}
    found = []
    for row, url in SAMPLE:
        if usable.get(row) != "yes":
            found.append(f"row {row}: sampled but the page says {usable.get(row)!r}")
        elif (why := answers(url)) is not None:
            found.append(f"row {row}: {url} is dead: {why}")
    return found


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        selftest()
        return 0
    if argv[1:] == ["probe"]:
        found = probe(PAGE.read_text(encoding="utf-8"))
        for p in found:
            print(p, file=sys.stderr)
        if not found:
            print(f"praha open data: {len(SAMPLE)} sampled usable rows answer")
        return 1 if found else 0
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
