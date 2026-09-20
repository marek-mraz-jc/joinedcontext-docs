#!/usr/bin/env python3
"""Every requirement is traceable, in its own family file and in the global matrix (T-0093, TS-18).

STYLE.md: a family file lists its requirements as `- **XX-nn** …` bullets and ends with a
`## Traceability` table mapping ID ranges to an Architecture section and a test family.
Requirements/traceability.md then maps every family to its canonical specification, the
architectural components and the CI gates that verify it.

A requirement nobody can trace to a chapter and a test is a requirement nobody verifies, so both
gaps fail the build:

    verify-traceability.py [docs-root]
    verify-traceability.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

# - **EP-27** [P] — …   / - **GW1, DENY** … / - **MIM3-R1 Catalogues** …
# the bold span may carry a name after the id; the id is what has to be traceable
DEFINITION = re.compile(
    r"^\s*-\s+\*\*([A-Z][A-Za-z0-9]*?-?\d+(?:-[A-Za-z]+\d+)?)(?:[,;:. ][^*]*)?\*\*"
)
# a range in a traceability row: EP-27…EP-28, R1–R43, CC-01–CC-70, or a single id
ID = r"[A-Z][A-Za-z0-9]*?-?\d+"
RANGE = re.compile(rf"^\s*({ID})\s*(?:[…–—-]{{1,3}}\s*({ID}))?\s*$")
SPLIT = re.compile(r"^([A-Za-z]+)-?(\d+)$")
SKIP = {"00-index.md", "traceability.md", "compliance-matrix.md"}
# A row of the generated compliance matrix: `| **EP-27** | [P] | tested | fast ci | … |`
MATRIX_ROW = re.compile(r"^\|\s*\*\*([A-Z][A-Za-z0-9]*?-?\d+(?:-[A-Za-z]+\d+)?)\*\*\s*\|"
                        r"[^|]*\|\s*(tested|built|open)\s*\|")
STATES = ("tested", "built", "open")


def family_of(identifier: str) -> str | None:
    """MIM3-R1 belongs to family MIM3: a two-level id is traced through its family."""
    head, _, tail = identifier.rpartition("-")
    return head if head and head[-1].isdigit() and tail[:1].isalpha() else None


def split_id(identifier: str) -> tuple[str, int] | None:
    match = SPLIT.match(identifier)
    return (match.group(1), int(match.group(2))) if match else None


def expand(first: str, last: str | None) -> set[str] | None:
    """{'EP-27', 'EP-28'} for EP-27…EP-28. None when the range is not a numeric range."""
    start, end = split_id(first), split_id(last) if last else split_id(first)
    if not start or not end or start[0] != end[0] or end[1] < start[1]:
        return None
    # zero padding follows the written form: EP-01 pads to two digits, GW1 does not pad at all
    width = len(SPLIT.match(first).group(2))
    dash = "-" if "-" in first else ""
    return {f"{start[0]}{dash}{number:0{width}d}" for number in range(start[1], end[1] + 1)}


def covered_ids(table_rows: list[list[str]], problems: list[str], where: str) -> set[str]:
    """The ids a traceability table claims to cover; a row without a chapter or a test is no coverage."""
    covered: set[str] = set()
    for cells in table_rows:
        match = RANGE.match(cells[0].replace("**", ""))
        if not match:
            continue
        ids = expand(match.group(1), match.group(2))
        if ids is None:
            problems.append(f"{where}: {cells[0]!r} is not a usable requirement range")
            continue
        if len(cells) < 2 or not cells[-1].strip():
            problems.append(f"{where}: {cells[0]} names no test family")
            continue
        if not any(cell.strip() for cell in cells[1:-1]):
            problems.append(f"{where}: {cells[0]} names no architecture chapter")
            continue
        covered |= ids
    return covered


def table_after(text: str, heading: str) -> list[list[str]]:
    """The rows of the first markdown table after a heading, as lists of cells."""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip().lower() == heading.lower())
    except StopIteration:
        return []
    rows = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and not set("".join(cells)) <= set("-: "):
                rows.append(cells)
    return rows[1:] if rows else []  # drop the header row


def states_in(path: Path, problems: list[str]) -> set[str] | None:
    """Every requirement the generated compliance matrix gives a state (T-2142, TS-19).

    `None` when the page is not there at all, which is the corpus of the self-test and of a
    checkout that has never run `tasks/compliance index`; a page that is there says `tested`,
    `built` or `open` for every requirement, and a requirement it has forgotten is one a reader
    cannot tell a proof from a wish about.
    """
    if not path.exists():
        return None
    stated: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = MATRIX_ROW.match(line)
        if match:
            stated.add(match.group(1))
    if not stated:
        problems.append(
            f"{path.name} names no requirement with one of the states {', '.join(STATES)}: "
            "the page or this check is wrong"
        )
    return stated


def check(root: Path) -> list[str]:
    problems: list[str] = []
    requirements = root / "Requirements"
    if not requirements.is_dir():
        return [f"{requirements} does not exist"]

    matrix_path = requirements / "traceability.md"
    if not matrix_path.exists():
        return [f"{matrix_path} does not exist"]
    matrix_rows = table_after(matrix_path.read_text(encoding="utf-8"), "## 1. Traceability Matrix")
    if not matrix_rows:
        problems.append("traceability.md holds no matrix table")
    matrix_covered = covered_ids(matrix_rows, problems, "traceability.md")
    stated = states_in(requirements / "compliance-matrix.md", problems)

    defined_anywhere = False
    for path in sorted(requirements.glob("*.md")):
        if path.name in SKIP:
            continue
        text = path.read_text(encoding="utf-8")
        defined = {match.group(1) for line in text.splitlines() if (match := DEFINITION.match(line))}
        if not defined:
            continue
        defined_anywhere = True

        rows = table_after(text, "## Traceability")
        if not rows:
            problems.append(
                f"{path.name}: no `## Traceability` table, so none of its "
                f"{len(defined)} requirements is mapped to a chapter and a test (STYLE.md)"
            )
        else:
            local = covered_ids(rows, problems, path.name)
            for identifier in sorted(defined):
                if identifier not in local and family_of(identifier) not in local:
                    problems.append(
                        f"{path.name}: {identifier} is in no row of the file's traceability table"
                    )

        for identifier in sorted(defined):
            if identifier not in matrix_covered and family_of(identifier) not in matrix_covered:
                problems.append(f"{identifier} ({path.name}) is in no family range of traceability.md")
            if stated is not None and identifier not in stated:
                problems.append(
                    f"{identifier} ({path.name}) has no state in compliance-matrix.md: regenerate "
                    "it with `tasks/compliance index` (T-2142)"
                )

    if not defined_anywhere:
        problems.append("no requirement bullet found at all: the parser or the corpus is wrong")
    return problems


FAMILY = """---
title: Endpoints
---

# Endpoints

- **EP-01** [P] — The first requirement.
- **EP-02** — The second requirement.
{extra}

## Traceability

| Requirement Range | Architecture Section | Test Family |
|---|---|---|
| EP-01…EP-02 | [Architecture/04.md](../Architecture/04.md) | [Testing/01.md](../Testing/01.md) |
{extra_row}
"""

MATRIX = """---
title: Traceability
---

# Requirements Traceability Matrix

## 1. Traceability Matrix

| Requirement Family | Focus Area | Canonical Specification | Architectural Components | Verification / CI Gates |
|---|---|---|---|---|
| **EP-01–EP-02** | Endpoints | `endpoints.md` | Context Gateway | OGC ATS |
"""


COMPLIANCE = """---
title: Compliance
---

# Requirement Compliance Matrix

| Requirement | Tags | State | Lane | Tests |
|---|---|---|---|---|
| **EP-01** | [P] | tested | fast ci | platform `crates/x/tests/a.rs::b` |
| **EP-02** |  | built | | `crates/x/src/a.rs` |
"""


def selftest() -> int:
    cases: list[tuple[str, str, str, str | None]] = [
        ("a family in sync", "", "", None),
        ("a requirement outside every local range", "- **EP-03** — A third requirement.", "",
         "EP-03 is in no row of the file's traceability table"),
        ("a requirement outside the global matrix", "- **EP-03** — A third requirement.",
         "| EP-03 | [Architecture/04.md](../Architecture/04.md) | [Testing/01.md](../Testing/01.md) |",
         "EP-03 (endpoints.md) is in no family range"),
        ("a row without a test family", "", "| EP-04 | [Architecture/04.md](../Architecture/04.md) |  |",
         "EP-04 names no test family"),
        # T-2142: the compliance matrix above states EP-01 and EP-02 and nothing else.
        ("a requirement with no state in the compliance matrix",
         "- **EP-03** — A third requirement.",
         "| EP-03 | [Architecture/04.md](../Architecture/04.md) | [Testing/01.md](../Testing/01.md) |",
         "EP-03 (endpoints.md) has no state in compliance-matrix.md"),
    ]
    failures = []
    for name, extra, extra_row, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            requirements = Path(tmp) / "Requirements"
            requirements.mkdir(parents=True)
            (requirements / "endpoints.md").write_text(
                FAMILY.format(extra=extra, extra_row=extra_row), encoding="utf-8"
            )
            (requirements / "traceability.md").write_text(MATRIX, encoding="utf-8")
            (requirements / "compliance-matrix.md").write_text(COMPLIANCE, encoding="utf-8")
            problems = check(Path(tmp))
            if expected is None and problems:
                failures.append(f"{name}: reported {problems}")
            elif expected is not None and not any(expected in problem for problem in problems):
                failures.append(f"{name}: {expected!r} was not reported, got {problems}")

    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "Requirements"
        requirements.mkdir(parents=True)
        body = FAMILY.format(extra="", extra_row="")
        (requirements / "endpoints.md").write_text(body[: body.index("## Traceability")], encoding="utf-8")
        (requirements / "traceability.md").write_text(MATRIX, encoding="utf-8")
        (requirements / "compliance-matrix.md").write_text(COMPLIANCE, encoding="utf-8")
        if not any("no `## Traceability` table" in problem for problem in check(Path(tmp))):
            failures.append("a family file without a traceability table was accepted")

    # T-2142: a corpus with no compliance matrix at all is not a failure — the page is
    # generated in another repository — but a matrix that states nothing is.
    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "Requirements"
        requirements.mkdir(parents=True)
        (requirements / "endpoints.md").write_text(FAMILY.format(extra="", extra_row=""), encoding="utf-8")
        (requirements / "traceability.md").write_text(MATRIX, encoding="utf-8")
        if check(Path(tmp)):
            failures.append("a corpus without a compliance matrix was refused")
        (requirements / "compliance-matrix.md").write_text("# empty\n", encoding="utf-8")
        if not any("names no requirement with one of the states" in p for p in check(Path(tmp))):
            failures.append("a compliance matrix stating nothing was accepted")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print(
        "ok: an unmapped requirement, a missing table, a row without a test and a requirement "
        "with no state all go red"
    )
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} traceability gap(s) — TS-18 requires none", file=sys.stderr)
        return 1
    print("traceability ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
