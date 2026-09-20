#!/usr/bin/env python3
"""Fail on broken relative links or anchors in the docs (GitHub/Docusaurus slug rules, TS-04/TS-18).

Scans every `.md` and `.mdx` page, ignores links inside fenced code blocks, and reports each
problem as `file:line: link (why)`. A heading carries its Docusaurus id when it ends in
`{#custom-id}`, otherwise the slug of its text.

    check-links.py [docs-root]
    check-links.py --selftest
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
HEADING_ID = re.compile(r"\{#([A-Za-z0-9_-]+)\}\s*$")  # Docusaurus explicit id
LINK = re.compile(r"\]\(\s*(<[^>]+>|[^)\s]+?)(?:\s+[\"'][^\"']*[\"'])?\s*\)")
PAGES = (".md", ".mdx")


def slug(heading: str) -> str:
    heading = re.sub(r"[`*_]", "", heading).strip().lower()
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading))


def body_lines(text: str):
    """(line number, line) for every line outside a fenced code block."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        opening = FENCE.match(line)
        if opening:
            if fence is None:
                fence = opening.group(1)
            elif line.strip().startswith(fence):
                fence = None
            continue
        if fence is None:
            yield number, line


def anchors_of(text: str) -> set[str]:
    found = set()
    for _, line in body_lines(text):
        heading = HEADING.match(line)
        if not heading:
            continue
        explicit = HEADING_ID.search(heading.group(1))
        found.add(explicit.group(1) if explicit else slug(HEADING_ID.sub("", heading.group(1))))
    return found


def check(root: Path) -> list[str]:
    pages = sorted(
        path
        for path in root.rglob("*")
        if path.suffix in PAGES and "node_modules" not in path.parts
    )
    text = {path.resolve(): path.read_text(encoding="utf-8") for path in pages}
    anchors = {path: anchors_of(body) for path, body in text.items()}

    problems = []
    for path in pages:
        for number, line in body_lines(text[path.resolve()]):
            for match in LINK.finditer(line):
                target = match.group(1).strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "tel:")):
                    continue
                where = f"{os.path.relpath(path, root)}:{number}: {target}"
                relative, _, anchor = target.partition("#")
                resolved = Path(os.path.normpath(path.parent / relative)) if relative else path
                resolved = resolved.resolve()
                if not resolved.exists():
                    problems.append(f"{where} (missing file)")
                elif anchor and resolved.suffix in PAGES:
                    if resolved not in anchors:
                        anchors[resolved] = anchors_of(resolved.read_text(encoding="utf-8"))
                    if anchor not in anchors[resolved]:
                        problems.append(f"{where} (missing anchor)")
    return problems


GOOD = """---
title: One
---

# One

## A Section {#custom-id}

## Another (Section)

- [the other page](two.md#heading-of-two)
- [an explicit id](#custom-id)
- [a slugged heading](#another-section)
- [an image](picture.png)
- [a titled link](two.md "the second page")

```md
[a link nobody follows](nowhere.md#nothing)
```
"""

TWO = """---
title: Two
---

# Two

## Heading of two
"""


def selftest() -> int:
    cases = [
        ("a corpus whose links all resolve", GOOD, None),
        ("a broken anchor", GOOD + "\n[bad](two.md#no-such-heading)\n", "two.md#no-such-heading (missing anchor)"),
        ("a missing file", GOOD + "\n[bad](three.md)\n", "three.md (missing file)"),
        ("a broken anchor in the page itself", GOOD + "\n[bad](#gone)\n", "#gone (missing anchor)"),
        ("an .mdx page", GOOD + "\n[bad](four.mdx#nope)\n", "four.mdx#nope (missing anchor)"),
    ]
    failures = []
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one.md").write_text(body, encoding="utf-8")
            (root / "two.md").write_text(TWO, encoding="utf-8")
            (root / "four.mdx").write_text(TWO, encoding="utf-8")
            (root / "picture.png").write_bytes(b"")
            problems = check(root)
            if expected is None and problems:
                failures.append(f"{name}: reported {problems}")
            elif expected is not None:
                if not any(expected in problem for problem in problems):
                    failures.append(f"{name}: {expected!r} was not reported, got {problems}")
                elif not any(problem.startswith("one.md:") for problem in problems):
                    failures.append(f"{name}: no file:line prefix in {problems}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a broken anchor, a missing file and an .mdx target all go red; fenced links do not")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} broken link(s)", file=sys.stderr)
        return 1
    print("links ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
