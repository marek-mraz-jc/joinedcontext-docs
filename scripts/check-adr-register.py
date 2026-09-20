#!/usr/bin/env python3
"""The ADR register and the ADR files say the same thing (T-0094, TS-18).

Every `Decisions/adr-n-*.md` must appear in the `ADR-N` table of `Decisions/00-register.md`
with the same id, title, status and date, and every row of that table must point at a file
that exists. A register that drifts from the decisions is a governance record nobody can trust.

    check-adr-register.py [docs-root]
    check-adr-register.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

H1 = re.compile(r"^#\s+(ADR-N-\d+):\s*(.+?)\s*$", re.M)
FIELD = "^{}:\\s*(.+?)\\s*$"
ROW = re.compile(
    r"^\|\s*\[(ADR-N-\d+)\]\(([^)]+)\)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
)
STATUSES = {"Accepted", "Superseded", "Proposed"}


def field(text: str, name: str) -> str | None:
    match = re.search(FIELD.format(name), text, re.M)
    return match.group(1).strip() if match else None


def read_adr(path: Path) -> tuple[str | None, dict[str, str | None]]:
    text = path.read_text(encoding="utf-8")
    heading = H1.search(text)
    return (
        heading.group(1) if heading else None,
        {
            "title": heading.group(2) if heading else None,
            "status": field(text, "Status"),
            "date": field(text, "Date"),
        },
    )


def read_register(path: Path) -> dict[str, dict[str, str]]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            rows[match.group(1)] = {
                "link": match.group(2),
                "title": match.group(3),
                "status": match.group(4).strip("* "),
                "date": match.group(5),
            }
    return rows


def check(root: Path) -> list[str]:
    decisions = root / "Decisions"
    register_path = decisions / "00-register.md"
    if not register_path.exists():
        return [f"{register_path} does not exist"]

    register = read_register(register_path)
    if not register:
        return ["00-register.md holds no ADR-N row: the register or this parser is wrong"]

    problems = []
    files = sorted(decisions.glob("adr-n-*.md"))
    if not files:
        return ["no ADR file found at all: the corpus or this parser is wrong"]

    seen = set()
    for path in files:
        identifier, adr = read_adr(path)
        if identifier is None:
            problems.append(f"{path.name}: no `# ADR-N-nnn: Title` heading")
            continue
        seen.add(identifier)
        row = register.get(identifier)
        if row is None:
            problems.append(f"{path.name}: {identifier} is in no row of 00-register.md")
            continue
        if row["link"] != path.name:
            problems.append(f"{identifier}: the register links {row['link']}, the file is {path.name}")
        for key in ("title", "status", "date"):
            if adr[key] is None:
                problems.append(f"{path.name}: no {key}")
            elif adr[key] != row[key]:
                problems.append(f"{identifier}: {key} is {adr[key]!r} in the file, {row[key]!r} in the register")
        if adr["status"] is not None and adr["status"] not in STATUSES:
            problems.append(f"{path.name}: status {adr['status']!r} is not one of {sorted(STATUSES)}")

    for identifier, row in sorted(register.items()):
        if identifier not in seen:
            problems.append(f"00-register.md: {identifier} names {row['link']}, which is not an ADR file")
    return problems


ADR = """---
title: "{id}: {title}"
---

# {id}: {title}

Date: {date}
Status: {status}

## 1. Context
"""

REGISTER = """---
title: "Architecture Decision Register"
---

# Architecture Decision Register

## 1. Target Architecture Decisions (`ADR-N` Series)

| ADR ID | Title | Status | Date | Decision Summary |
|---|---|---|---|---|
| [ADR-N-001](adr-n-001-one.md) | The First Decision | **{status}** | {date} | Summary. |
{extra}"""


def selftest() -> int:
    good = dict(id="ADR-N-001", title="The First Decision", status="Accepted", date="2026-09-05")
    cases = [
        ("a register in sync", good, {}, "", None),
        ("a diverging title", good | {"title": "A Renamed Decision"}, {}, "",
         "title is 'A Renamed Decision' in the file, 'The First Decision' in the register"),
        ("a diverging status", good | {"status": "Superseded"}, {}, "", "status is 'Superseded'"),
        ("a diverging date", good | {"date": "2026-01-01"}, {}, "", "date is '2026-01-01'"),
        ("a status outside the vocabulary", good | {"status": "Draft"}, {"status": "Draft"}, "",
         "is not one of ['Accepted', 'Proposed', 'Superseded']"),
        ("an ADR file nobody listed", good, {},
         "", "ADR-N-002 is in no row of 00-register.md"),
        ("a row whose file is gone", good, {},
         "| [ADR-N-009](adr-n-009-ghost.md) | A Ghost | **Accepted** | 2026-09-05 | Summary. |\n",
         "ADR-N-009 names adr-n-009-ghost.md, which is not an ADR file"),
    ]
    failures = []
    for name, adr, register_override, extra, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            decisions = Path(tmp) / "Decisions"
            decisions.mkdir(parents=True)
            (decisions / "adr-n-001-one.md").write_text(ADR.format(**adr), encoding="utf-8")
            if name == "an ADR file nobody listed":
                (decisions / "adr-n-002-two.md").write_text(
                    ADR.format(id="ADR-N-002", title="The Second", status="Accepted", date="2026-09-05"),
                    encoding="utf-8",
                )
            (decisions / "00-register.md").write_text(
                REGISTER.format(status=register_override.get("status", "Accepted"),
                                date="2026-09-05", extra=extra),
                encoding="utf-8",
            )
            problems = check(Path(tmp))
            if expected is None and problems:
                failures.append(f"{name}: reported {problems}")
            elif expected is not None and not any(expected in problem for problem in problems):
                failures.append(f"{name}: {expected!r} was not reported, got {problems}")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a renamed, restatused, redated, unlisted or missing ADR all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} register mismatch(es) — TS-18 requires none", file=sys.stderr)
        return 1
    print("adr register ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
