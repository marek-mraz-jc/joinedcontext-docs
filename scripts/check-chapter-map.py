#!/usr/bin/env python3
"""The Architecture Chapter Map in Architecture/01-overview.md must match files and navigation metadata (T-0097).

The Architecture Chapter Map table in Architecture/01-overview.md §4 acts as the canonical
index for the architecture specification. Every linked chapter must exist with matching numeric
prefixes, front-matter titles, and sidebar positions, and every chapter on disk must be mapped.
Loosely compared title terms ensure chapters cannot be silently renamed without updating the map.

    check-chapter-map.py [docs-root]
    check-chapter-map.py --selftest
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"^\s*(```|~~~)")
LINK = re.compile(r"\]\(\s*(<[^>]+>|[^)\s]+?)(?:\s+[\"'][^\"']*[\"'])?\s*\)")
IGNORE_WORDS = {"&", "and", "the", "of", "from"}


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


def front_matter_of(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end < 0:
        return None
    return text[4:end]


def h1_of(text: str) -> str | None:
    for _, line in body_lines(text):
        if line.startswith("# "):
            return line[2:].strip()
    return None


def significant_words(label: str) -> list[str]:
    clean = re.sub(r"[`*_\"']", "", label)
    words = []
    for token in re.findall(r"[A-Za-z0-9&]+", clean):
        token_lower = token.lower()
        if token_lower in IGNORE_WORDS or token_lower.isdigit() or len(token_lower) < 4:
            continue
        words.append(token_lower)
    return words


def word_in_target(word: str, target: str) -> bool:
    if word in target:
        return True
    base = word.rstrip("s")
    if len(base) >= 3 and base in target:
        return True
    return False


def check(root: Path) -> list[str]:
    # every path compared below is resolved, so a relative root and an absolute link target
    # still line up when a problem is reported
    root = root.resolve()
    arch_dir = root / "Architecture"
    if not arch_dir.is_dir():
        return [f"{root}: missing Architecture directory"]

    overview_file = arch_dir / "01-overview.md"
    if not overview_file.is_file():
        return [f"{overview_file.relative_to(root)}: missing file"]

    problems: list[str] = []
    rel_overview = overview_file.relative_to(root)
    overview_text = overview_file.read_text(encoding="utf-8")

    # 5. Architecture/_category_.json and global uniqueness across the repository
    arch_cat = arch_dir / "_category_.json"
    if not arch_cat.is_file():
        problems.append(f"{arch_cat.relative_to(root)}: missing _category_.json")

    category_positions: dict[int, list[Path]] = {}
    for cat_path in sorted(root.rglob("_category_.json")):
        if "node_modules" in cat_path.parts or ".git" in cat_path.parts:
            continue
        rel_cat = cat_path.relative_to(root)
        try:
            data = json.loads(cat_path.read_text(encoding="utf-8"))
        except Exception as err:
            problems.append(f"{rel_cat}: invalid JSON ({err})")
            continue
        if not isinstance(data, dict):
            problems.append(f"{rel_cat}: JSON root must be an object")
            continue

        if cat_path == arch_cat:
            label = data.get("label")
            if not isinstance(label, str) or not label.strip():
                problems.append(f"{rel_cat}: missing or empty 'label'")
            pos = data.get("position")
            if not isinstance(pos, int) or isinstance(pos, bool):
                problems.append(f"{rel_cat}: 'position' must be an integer, got {pos!r}")

        pos = data.get("position")
        if isinstance(pos, int) and not isinstance(pos, bool):
            category_positions.setdefault(pos, []).append(rel_cat)

    # a top-level page and a folder share one ordering space in the sidebar, so they collide too
    for page in sorted(root.glob("*.md")):
        fm = front_matter_of(page.read_text(encoding="utf-8"))
        m_pos = re.search(r"^sidebar_position:\s*(\d+)", fm, re.M) if fm else None
        if m_pos:
            category_positions.setdefault(int(m_pos.group(1)), []).append(page.relative_to(root))

    for pos, paths in sorted(category_positions.items()):
        if len(paths) > 1:
            paths_str = ", ".join(str(p) for p in paths)
            problems.append(f"{paths[0]}: duplicate sidebar position {pos} shared with {paths_str}")

    # 4. sidebar_position values inside Architecture/ must be unique
    arch_positions: dict[int, list[Path]] = {}
    for page in sorted(arch_dir.iterdir()):
        if page.suffix not in (".md", ".mdx") or not page.is_file():
            continue
        fm = front_matter_of(page.read_text(encoding="utf-8"))
        if not fm:
            continue
        m_pos = re.search(r"^sidebar_position:\s*(\d+)", fm, re.M)
        if m_pos:
            arch_positions.setdefault(int(m_pos.group(1)), []).append(page.relative_to(root))

    for pos, paths in sorted(arch_positions.items()):
        if len(paths) > 1:
            paths_str = ", ".join(str(p) for p in paths)
            problems.append(f"Architecture: duplicate sidebar_position {pos} in {paths_str}")

    # 1. Parse §4 Architecture Chapter Map table
    lines = overview_text.splitlines()
    in_s4 = False
    s4_lineno = None
    table_rows: list[tuple[int, list[str]]] = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r"^##\s+4\.?\s+.*Chapter Map", stripped, re.I):
            in_s4 = True
            s4_lineno = lineno
            continue
        if in_s4 and stripped.startswith("## "):
            break
        if in_s4 and stripped.startswith("|"):
            if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if any(c.lower() in ("chapter", "specification") for c in cells):
                continue
            table_rows.append((lineno, cells))

    disk_chapters = [
        p for p in sorted(arch_dir.glob("[0-9][0-9]-*.md"))
        if p.resolve() != overview_file.resolve()
    ]

    if not in_s4:
        problems.append(f"{rel_overview}: missing §4 Architecture Chapter Map heading")
        return problems

    if not table_rows:
        problems.append(f"{rel_overview}:{s4_lineno}: §4 Architecture Chapter Map table is absent")
        return problems

    min_expected = min(5, len(disk_chapters)) if disk_chapters else 5
    if len(table_rows) < min_expected or (len(disk_chapters) >= 5 and len(table_rows) < 5):
        problems.append(
            f"{rel_overview}:{table_rows[0][0]}: chapter map holds {len(table_rows)} row(s), expected at least {min_expected}"
        )

    mapped_files: set[Path] = set()
    table_file_targets: set[str] = set()

    # 2. Check each chapter entry
    for lineno, cells in table_rows:
        cell_label = cells[0] if cells else ""
        cell_link = cells[1] if len(cells) > 1 else ""

        m_label = re.match(r"^\*{0,2}(\d{2})\.?\s*(.+?)\*{0,2}$", cell_label)
        if not m_label:
            problems.append(f"{rel_overview}:{lineno}: malformed chapter label {cell_label!r} (expected '**NN Name**')")
            continue

        num_str = m_label.group(1)
        name_str = m_label.group(2).strip()

        m_link = re.search(r"\]\(\s*(<[^>]+>|[^)\s]+?)(?:\s+[\"'][^\"']*[\"'])?\s*\)", cell_link)
        target = m_link.group(1).strip("<>") if m_link else cell_link.strip().strip("<>")
        file_part, _, _ = target.partition("#")
        if not file_part:
            problems.append(f"{rel_overview}:{lineno}: chapter {num_str} row has empty link target")
            continue

        table_file_targets.add(file_part)
        target_path = (overview_file.parent / file_part).resolve()

        if not target_path.is_file():
            problems.append(f"{rel_overview}:{lineno}: map row points to missing file '{file_part}'")
            continue

        try:
            target_path.relative_to(arch_dir.resolve())
        except ValueError:
            problems.append(f"{rel_overview}:{lineno}: linked file '{file_part}' is not under Architecture/")
            continue

        mapped_files.add(target_path)
        rel_target = target_path.relative_to(root)

        m_prefix = re.match(r"^(\d+)", target_path.name)
        if not m_prefix or m_prefix.group(1) != num_str:
            problems.append(
                f"{rel_overview}:{lineno}: chapter {num_str} file name '{target_path.name}' prefix does not match chapter number"
            )

        target_text = target_path.read_text(encoding="utf-8")
        fm = front_matter_of(target_text)
        if not fm:
            problems.append(f"{rel_target}: missing front matter")
            continue

        m_pos = re.search(r"^sidebar_position:\s*(\d+)", fm, re.M)
        if not m_pos:
            problems.append(f"{rel_target}: missing front-matter sidebar_position")
        else:
            pos_val = int(m_pos.group(1))
            if pos_val != int(num_str):
                problems.append(
                    f"{rel_target}: front-matter sidebar_position ({pos_val}) does not match chapter number ({int(num_str)})"
                )

        m_title = re.search(r"^title:\s*(.+)$", fm, re.M)
        fm_title = m_title.group(1).strip().strip("\"'") if m_title else ""
        if not fm_title:
            problems.append(f"{rel_target}: front matter declares no title")

        h1_title = h1_of(target_text)
        if not h1_title:
            problems.append(f"{rel_target}: missing H1 heading")
        elif fm_title and fm_title != h1_title:
            problems.append(f"{rel_target}: front-matter title {fm_title!r} does not match H1 {h1_title!r}")

        sig_words = significant_words(name_str)
        target_combined = f"{fm_title} {h1_title or ''}".lower()
        for w in sig_words:
            if not word_in_target(w, target_combined):
                problems.append(
                    f"{rel_overview}:{lineno}: map label '{name_str}' word '{w}' does not appear in title '{fm_title}' or H1 of {rel_target}"
                )

    # 3. Every Architecture/NN-*.md on disk must be in the map
    for path in disk_chapters:
        if path.resolve() not in mapped_files:
            problems.append(f"{path.relative_to(root)}: chapter file on disk is not listed in chapter map")

    # 6. Every relative link in Architecture/01-overview.md resolves to an existing file
    for lineno, line in body_lines(overview_text):
        for match in LINK.finditer(line):
            target = match.group(1).strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            file_part, _, _ = target.partition("#")
            if not file_part:
                continue
            resolved = (overview_file.parent / file_part).resolve()
            if not resolved.exists():
                problems.append(f"{rel_overview}:{lineno}: link '{target}' points to missing file '{file_part}'")

    return problems


def _build_corpus(
    root: Path,
    *,
    overview_body: str | None = None,
    p2_title: str = "Principles",
    p2_h1: str = "Principles",
    p2_pos: int = 2,
    p3_pos: int = 3,
    include_p3: bool = True,
    include_p3_in_map: bool = True,
    p2_link: str = "02-principles.md",
    extra_category: bool = False,
) -> None:
    arch = root / "Architecture"
    arch.mkdir(parents=True, exist_ok=True)
    (arch / "_category_.json").write_text('{"label": "Architecture", "position": 1}\n', encoding="utf-8")

    if extra_category:
        dep = root / "Deployment"
        dep.mkdir(parents=True, exist_ok=True)
        (dep / "_category_.json").write_text('{"label": "Deployment", "position": 1}\n', encoding="utf-8")

    if include_p3:
        (arch / "03-domain-model.md").write_text(
            f"---\nsidebar_position: {p3_pos}\ntitle: Domain Model\n---\n\n# Domain Model\n\nDomain model.\n",
            encoding="utf-8",
        )

    (arch / "02-principles.md").write_text(
        f"---\nsidebar_position: {p2_pos}\ntitle: {p2_title}\n---\n\n# {p2_h1}\n\nPrinciples.\n",
        encoding="utf-8",
    )

    overview_file = arch / "01-overview.md"
    if overview_body is not None:
        overview_file.write_text(overview_body, encoding="utf-8")
    else:
        map_p3 = "| **03 Domain Model** | [03-domain-model.md](03-domain-model.md) | Domain structure |\n" if include_p3_in_map else ""
        rel_p3 = "- [03-domain-model.md](03-domain-model.md) — domain model.\n" if include_p3_in_map else ""
        body = (
            "---\n"
            "sidebar_position: 1\n"
            "title: Architecture Overview\n"
            "---\n\n"
            "# Architecture Overview\n\n"
            "Overview lead.\n\n"
            "## 4. Architecture Chapter Map\n\n"
            "| Chapter | Specification | Core Question Answered |\n"
            "|---|---|---|\n"
            f"| **02 Principles** | [{p2_link}]({p2_link}) | Core rules |\n"
            f"{map_p3}\n"
            "## Related\n\n"
            f"- [{p2_link}]({p2_link}) — principles.\n"
            f"{rel_p3}"
        )
        overview_file.write_text(body, encoding="utf-8")


def selftest() -> int:
    cases = [
        ("a clean two-chapter corpus", {}, None),
        ("a map row pointing at a missing file", {"p2_link": "02-missing.md"}, "missing file"),
        (
            "a renamed title that no longer shares a word with the map label",
            {"p2_title": "Unrelated Foundations", "p2_h1": "Unrelated Foundations"},
            "does not appear in title",
        ),
        ("a chapter on disk missing from the map", {"include_p3_in_map": False}, "not listed in chapter map"),
        ("a duplicate sidebar_position", {"p3_pos": 2}, "duplicate sidebar_position"),
        ("two folders sharing a _category_.json position", {"extra_category": True}, "duplicate sidebar position"),
        (
            "a corpus with no §4 table",
            {"overview_body": "---\nsidebar_position: 1\ntitle: Architecture Overview\n---\n\n# Architecture Overview\n\nNo map.\n"},
            "missing §4",
        ),
    ]

    failures = []
    for name, kwargs, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            _build_corpus(Path(tmp), **kwargs)
            found = check(Path(tmp))
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in p for p in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: missing file, renamed title, unlisted chapter, duplicate position and missing table all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} chapter-map problem(s)", file=sys.stderr)
        return 1
    print("chapter map ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
