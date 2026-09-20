#!/usr/bin/env python3
"""Every page carries closed front matter with a title and exactly one H1 (STYLE.md, TS-18).

A site build rejects a page whose front matter is unterminated or whose title is missing, and
STYLE.md allows exactly one H1 per page. Fences are skipped, so a `# comment` inside a code
block is not counted as a heading.

    check-front-matter.py [docs-root]
    check-front-matter.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

TITLE = re.compile(r"^title:\s*(\S.*)$", re.M)
SKIP = {"STYLE.md", "README.md"}
PAGES = (".md", ".mdx")


def problems_of(path: Path, text: str) -> list[str]:
    if not text.startswith("---\n"):
        return [f"{path}: no front matter"]
    end = text.find("\n---\n", 3)
    if end < 0:
        return [f"{path}: front matter is not closed"]
    found = []
    front = text[4:end]
    title = TITLE.search(front)
    if not title:
        found.append(f"{path}: front matter declares no title")
    elif title.group(1).strip() in {'""', "''"}:
        found.append(f"{path}: front matter title is empty")
    for line in front.splitlines():
        if line.strip() and not line.startswith((" ", "-")) and ":" not in line:
            found.append(f"{path}: front matter line {line.strip()!r} is not a `key: value` pair")

    headings, fence = 0, False
    for line in text[end + 5 :].splitlines():
        if line.startswith(("```", "~~~")):
            fence = not fence
        elif not fence and line.startswith("# "):
            headings += 1
    if headings != 1:
        found.append(f"{path}: {headings} H1 headings, exactly one is required (STYLE.md)")
    return found


def check(root: Path) -> list[str]:
    pages = sorted(
        path
        for path in root.rglob("*")
        if path.suffix in PAGES
        and "node_modules" not in path.parts
        and path.name not in SKIP
        and not path.name.startswith("_")
    )
    if not pages:
        return [f"no page found under {root}"]
    found = []
    for path in pages:
        found += problems_of(path.relative_to(root), path.read_text(encoding="utf-8"))
    return found


GOOD = '---\nsidebar_position: 1\ntitle: "A Page"\n---\n\n# A Page\n\n```md\n# not a heading\n```\n'


def selftest() -> int:
    cases = [
        ("a conforming page", GOOD, None),
        ("no front matter", "# A Page\n", "no front matter"),
        ("unterminated front matter", "---\ntitle: A Page\n\n# A Page\n", "front matter is not closed"),
        ("no title", "---\nsidebar_position: 1\n---\n\n# A Page\n", "declares no title"),
        ("an empty title", '---\ntitle: ""\n---\n\n# A Page\n', "title is empty"),
        ("a broken front-matter line", "---\ntitle: A Page\nbroken\n---\n\n# A Page\n", "is not a `key: value` pair"),
        ("two H1 headings", GOOD + "\n# A Second H1\n", "2 H1 headings"),
        ("no H1 at all", '---\ntitle: "A Page"\n---\n\n## Only an H2\n', "0 H1 headings"),
    ]
    failures = []
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "page.mdx").write_text(body, encoding="utf-8")
            found = check(Path(tmp))
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: missing, unterminated, titleless and malformed front matter and a stray H1 all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    found = check(root)
    for problem in found:
        print(problem)
    if found:
        print(f"\n{len(found)} front-matter problem(s)", file=sys.stderr)
        return 1
    print("front matter ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
