#!/usr/bin/env python3
"""Legacy vocabulary never appears unqualified in a normative chapter (T-0095, STYLE.md §Text).

The Terminology Delta table in `Requirements/00-index.md` §4 is the authoritative legacy → target
map, and STYLE.md names the terms that must never be used at all. This checker reads the table,
asserts the glossary defines both sides of every row, and then scans the normative chapters for a
legacy term used as if it were current. A hit is forgiven only when the line says it is history
(`legacy`, `deprecated`, `superseded`, `CIVITAS`, `v2`, `migration`) or when the term is part of a
path, a link target, a code span or a fenced block, where it names a file rather than a concept.

    check-glossary.py [docs-root]
    check-glossary.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

INDEX = "Requirements/00-index.md"
GLOSSARY = "Glossary.md"
NORMATIVE = ("Requirements", "Architecture", "Deployment", "Operations", "Development", "Testing", "API", "User-Guide")
# the chapters whose subject is the mapping itself, plus imported studies and dated decisions
EXEMPT = {INDEX, GLOSSARY, "Architecture/15-migration-from-v2.md", "STYLE.md"}
EXEMPT_DIRS = ("Research", "Decisions")
QUALIFIERS = ("legacy", "deprecated", "superseded", "civitas", " v2", "v2 ", "migration", "renamed", "no longer")
# STYLE.md §Text: never write these, whatever the terminology table says
FORBIDDEN = {"cityctl": "jcctl", "City-as-Code": "Configuration as Code", "Mandant": "Organization"}
# `Tenant` is also the live word for the broker tenant a Context Space maps onto (the second
# terminology row says so), so a hit next to one of these words is correct usage, not drift
LIVE_CONTEXT = {
    "Tenant": ("broker", "ngsi-ld", "ngsild", "header", "pinning", "masking", "derivation",
               "provision", "context space", "multi-tenant", "tenant id"),
}
TERM_LINE = re.compile(r"^\s*-\s+\*\*([^*]+)\*\*")
CODE_SPAN = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")


def _table_rows(text: str, heading_prefix: str) -> list[list[str]]:
    """The rows of the first markdown table under the heading starting with `heading_prefix`."""
    rows: list[list[str]] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.startswith(heading_prefix)
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def _aliases(cell: str) -> list[str]:
    """`Tenant (Mandant)` and `(Platform-level) Tenant ID` both name two searchable terms."""
    plain = re.sub(r"[*`]", "", cell).strip()
    # the cell without its parentheses, plus every single-word alias inside them
    parts = [re.sub(r"\([^)]*\)", " ", plain)]
    parts += [g for g in re.findall(r"\(([^)]+)\)", plain) if re.fullmatch(r"[A-Za-z]+", g.strip())]
    out: list[str] = []
    for part in parts:
        for piece in part.split("/"):
            piece = " ".join(piece.split())
            if piece and piece not in out:
                out.append(piece)
    return out


def _normal(term: str) -> set[str]:
    """`Org Repository (`org-repo`)`, `Data Model` and `DataModel` are the same term."""
    plain = " ".join(re.sub(r"\([^)]*\)", " ", re.sub(r"[`*]", "", term)).lower().split())
    # one glossary entry may cover two spellings: `DataSource / Connector (legacy)`
    out = {plain, plain.replace(" ", "")}
    for part in plain.split("/"):
        part = part.strip()
        if part:
            out |= {part, part.replace(" ", "")}
    return out


def _defined_terms(glossary: str) -> tuple[set[str], set[str]]:
    """Every glossary term, and the subset marked `(legacy)`."""
    all_terms: set[str] = set()
    legacy: set[str] = set()
    for line in glossary.splitlines():
        m = TERM_LINE.match(line)
        if not m:
            continue
        raw = m.group(1)
        all_terms |= _normal(raw)
        if "(legacy)" in raw.lower():
            legacy |= _normal(raw)
    return all_terms, legacy


def _qualified(line: str) -> bool:
    low = line.lower()
    return any(q in low for q in QUALIFIERS)


def _distinctive(term: str) -> bool:
    """A legacy term worth searching for is one an English sentence cannot use innocently.

    `Connector`, `Flow`, `Application` and `Distribution` are ordinary words and a DCAT term; a
    checker that flags them cries wolf until someone deletes it. What stays is the CamelCase and
    hyphenated names, the multi-word phrases, and the two words this platform renamed outright.
    """
    return bool(re.search(r"[a-z][A-Z]", term)) or "-" in term or " " in term or term in {"Mandant", "Tenant"}


def _prose_of(line: str) -> str:
    """The part of a line that is prose: code spans and link targets name files, not concepts."""
    return LINK_TARGET.sub(" ", CODE_SPAN.sub(" ", line))


def check(root: Path) -> list[str]:
    problems: list[str] = []
    index_path, glossary_path = root / INDEX, root / GLOSSARY
    if not index_path.is_file():
        return [f"{INDEX}: the terminology table lives here and the file is missing"]
    rows = _table_rows(index_path.read_text(encoding="utf-8"), "## 4")
    if len(rows) < 8:
        return [f"{INDEX}: the §4 Terminology Delta table has {len(rows)} rows, expected at least 8"]

    mapping: dict[str, str] = {}
    for row in rows:
        if len(row) < 2 or not row[0].strip() or not row[1].strip():
            problems.append(f"{INDEX}: terminology row {row!r} has an empty legacy or target cell")
            continue
        # a row marked (Kept) renames nothing: the term survives into this specification
        if "kept" in row[1].lower():
            continue
        target = re.sub(r"[*`]", "", row[1]).split("(")[0].strip()
        for alias in _aliases(row[0]):
            if alias.lower() not in {"kept"} and not alias.lower().startswith(target.lower()):
                mapping[alias] = target

    if not glossary_path.is_file():
        problems.append(f"{GLOSSARY}: the canonical glossary is missing")
    else:
        defined, defined_legacy = _defined_terms(glossary_path.read_text(encoding="utf-8"))
        for legacy, target in sorted(mapping.items()):
            # a decomposed target ("Context Space + DataModel + Endpoint") is defined part by part
            for part in target.split("+"):
                part = part.strip()
                if part and not _normal(part) & defined:
                    problems.append(f"{GLOSSARY}: target term '{part}' is not defined")
            if not _normal(legacy) & defined_legacy:
                problems.append(f"{GLOSSARY}: legacy term '{legacy}' is not defined and marked (legacy)")

    searchable = {t: v for t, v in mapping.items() if _distinctive(t)}
    searchable.update(FORBIDDEN)
    patterns = {
        term: re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])", 0 if term[0].isupper() else re.I)
        for term in searchable
    }

    scanned = 0
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if rel in EXEMPT or rel.split("/")[0] in EXEMPT_DIRS:
            continue
        if "/" in rel and rel.split("/")[0] not in NORMATIVE:
            continue
        scanned += 1
        fence = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith(("```", "~~~")):
                fence = not fence
                continue
            if fence or _qualified(line):
                continue
            prose = _prose_of(line)
            low_line = line.lower()
            for term, pattern in patterns.items():
                if pattern.search(prose) and not any(w in low_line for w in LIVE_CONTEXT.get(term, ())):
                    problems.append(
                        f"{rel}:{lineno}: legacy term '{term}' used without a legacy qualifier "
                        f"(target: {searchable[term]})"
                    )
    if scanned == 0:
        problems.append("no normative chapter was scanned, so this run proves nothing")
    return problems


def selftest() -> int:
    index = """---
title: Index
---

# Index

## 4. Terminology Delta

| Legacy Term | Target Term | Delta |
|---|---|---|
| Tenant (Mandant) | **Organization** | boundary |
| DataPool / DataSpace | **Project** | domain |
| DataSet | **Context Space** | decomposed |
| DataStructure | **DataModel** | schema |
| DataSource / Connector | **Pipeline** | ingest |
| Distribution | **Endpoint Representation** | view |
| City Repository | **Org Repository** | git |
| Flow | **Blueprint Instance** | instance |
| Application | **Addon** | workload |
"""
    glossary_terms = [
        "Organization", "Project", "Context Space", "DataModel", "Pipeline", "Endpoint Representation",
        "Org Repository", "Blueprint Instance", "Addon",
        "Tenant (legacy)", "Mandant (legacy)", "DataPool (legacy)", "DataSpace (legacy)", "DataSet (legacy)",
        "DataStructure (legacy)", "DataSource (legacy)", "Connector (legacy)", "Distribution (legacy)",
        "City Repository (legacy)", "Flow (legacy)", "Application (legacy)",
    ]
    glossary = "---\ntitle: Glossary\n---\n\n# Glossary\n\n" + "".join(
        f"- **{t}** — a term.\n" for t in glossary_terms
    )

    cases: list[tuple[str, str, str | None, str | None]] = [
        ("clean chapter", "The Organization owns the Project.", None, None),
        ("bare legacy term", "The Tenant owns the project.", "legacy term 'Tenant'", None),
        ("qualified by the word legacy", "The legacy Tenant became an Organization.", None, None),
        ("qualified by CIVITAS", "CIVITAS/CORE v2 called this a DataPool.", None, None),
        ("inside a fenced block", "```yaml\nkind: DataPool\n```", None, None),
        ("inside a code span", "The file `city-as-code.md` holds it.", None, None),
        ("inside a link target", "See [configuration](../Requirements/city-as-code.md).", None, None),
        ("forbidden binary name", "Run cityctl apply to converge.", "'cityctl'", None),
        ("forbidden draft term", "The City-as-Code plane converges state.", "'City-as-Code'", None),
        ("glossary missing a target", "The Organization owns the Project.", "target term 'Addon' is not defined",
         "\n".join(l for l in glossary.splitlines() if "Addon" not in l) + "\n"),
        ("terminology table with an empty cell", "clean", "empty legacy or target cell", None),
        ("no terminology table at all", "clean", "expected at least 8", None),
    ]

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Requirements").mkdir()
        (root / "Architecture").mkdir()
        for name, body, expected, glossary_override in cases:
            idx = index
            if name == "terminology table with an empty cell":
                idx = index.replace("| Flow | **Blueprint Instance** | instance |", "| Flow |  | instance |")
            if name == "no terminology table at all":
                idx = "---\ntitle: Index\n---\n\n# Index\n\n## 4. Terminology Delta\n\nNo table yet.\n"
            (root / INDEX).write_text(idx, encoding="utf-8")
            (root / GLOSSARY).write_text(glossary_override or glossary, encoding="utf-8")
            (root / "Architecture" / "01-overview.md").write_text(
                f"---\ntitle: O\n---\n\n# O\n\n{body}\n", encoding="utf-8"
            )
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: an unqualified legacy term, a forbidden name, a missing glossary entry, an empty "
          "terminology cell and a missing table all go red; fences, code spans and link targets stay green")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} terminology problem(s)", file=sys.stderr)
        return 1
    print("glossary and terminology ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
