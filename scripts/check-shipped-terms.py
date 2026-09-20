#!/usr/bin/env python3
"""No page may call a kind the platform ships legacy, deprecated or an early draft (T-0552).

The kinds are the ones `schema/kinds/` ships and the Portal has a section for. A CIVITAS/CORE
mapping row that names the old system's term is not a label on ours: lines naming CIVITAS pass.
"""
import pathlib
import re
import sys

TERMS = "Flow|Blueprint|Pipeline|Endpoint|DataSource|Data Source"
LABEL = r"legacy|deprecated|early draft"
PATTERNS = [
    re.compile(rf"\*\*(?:{TERMS})(?: \((?:{LABEL})\))?\*\*\s*[—-]+\s*(?:{LABEL})", re.I),
    re.compile(rf"\b(?:{LABEL})\s+`?(?:{TERMS})`?\b"),
]
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    problems = []
    for page in sorted(ROOT.rglob("*.md")):
        if "node_modules" in page.parts:
            continue
        for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if "CIVITAS" in line:
                continue
            if any(p.search(line) for p in PATTERNS):
                problems.append(f"{page.relative_to(ROOT)}:{number}: a shipped kind is labelled legacy or deprecated")
    for problem in problems:
        print(problem)
    print(f"check-shipped-terms: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
