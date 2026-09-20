#!/usr/bin/env python3
"""Every Mermaid diagram must parse structurally against the platform subset (STYLE.md, TS-18).

This is a structural parser for the Mermaid subset used in this documentation set:
it proves that a block declares a supported diagram type, that its statements parse
and its brackets, quotes, subgraph/end pairs and participants are consistent — not that
Mermaid would render it pixel-perfect.

    lint-mermaid.py [docs-root]
    lint-mermaid.py --selftest
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

PAGES = (".md", ".mdx")

DIAGRAM_TYPES = {
    "flowchart",
    "graph",
    "sequenceDiagram",
    "stateDiagram-v2",
    "stateDiagram",
    "erDiagram",
    "classDiagram",
    "gantt",
    "journey",
    "timeline",
    "mindmap",
    "C4Context",
}

DIRECTIONS = {"TD", "TB", "LR", "RL", "BT"}

OPEN_MERMAID = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})mermaid\s*$")
OPEN_ANY_FENCE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})")

BRACKET_OPEN = {"[": "]", "(": ")", "{": "}"}
BRACKET_CLOSE = {"]": "[", ")": "(", "}": "{"}

FLOWCHART_EDGE_RE = re.compile(
    # `A -- "label" --> B` keeps its two dashes after the quoted label is blanked out, so the
    # labelled form has to accept an empty middle; forbidding `-` inside it stops the pattern
    # from swallowing the next arrow on the same line
    r"(?:--\s[^->\n]*-->|--\s[^->\n]*---|--x|--o|o--o|<--o|x--x|<-->|-->|---|-.->|-.-|==>|===)"
)
NODE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")

SEQ_ARROW_RE = re.compile(r"(-->>|->>|-->|->|--x|-x|--\)|-\))[+-]?")


def strip_quotes_and_comments(line: str) -> tuple[str, bool]:
    in_quote = False
    chars = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and in_quote and i + 1 < len(line) and line[i + 1] == '"':
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote:
            if ch == "%" and i + 1 < len(line) and line[i + 1] == "%":
                break
            chars.append(ch)
        i += 1
    return "".join(chars), not in_quote


def strip_node_labels_and_pipes(text: str) -> str:
    res = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == "\\" and i + 1 < len(text):
                    i += 2
                else:
                    i += 1
            if i < len(text):
                i += 1
            continue
        if ch == "|":
            i += 1
            while i < len(text) and text[i] != "|":
                i += 1
            if i < len(text):
                i += 1
            res.append(" ")
            continue
        if ch in BRACKET_OPEN:
            stack = [ch]
            i += 1
            while i < len(text) and stack:
                curr = text[i]
                if curr == '"':
                    i += 1
                    while i < len(text) and text[i] != '"':
                        if text[i] == "\\" and i + 1 < len(text):
                            i += 2
                        else:
                            i += 1
                    if i < len(text):
                        i += 1
                    continue
                if curr in BRACKET_OPEN:
                    stack.append(curr)
                elif curr in BRACKET_CLOSE and BRACKET_OPEN.get(stack[-1]) == curr:
                    stack.pop()
                i += 1
            res.append(" ")
            continue
        res.append(ch)
        i += 1
    return "".join(res)


def lint_flowchart_line(
    rel: str, line_no: int, raw_line: str, problems: list[str]
) -> None:
    outside, _ = strip_quotes_and_comments(raw_line)
    stripped_outside = outside.strip()
    if not stripped_outside:
        return
    if (
        re.match(
            r"^(?:subgraph|end|classDef|class|style|click|linkStyle|direction)\b",
            stripped_outside,
        )
        or stripped_outside.startswith("%%")
    ):
        return

    statements = [stmt.strip() for stmt in outside.split(";") if stmt.strip()]
    for stmt in statements:
        stripped = strip_node_labels_and_pipes(stmt)
        if re.search(r"(?<![-.])->(?!>)", stripped):
            problems.append(
                f"{rel}:{line_no}: malformed arrow '->' in flowchart, use '-->' or '-.->'"
            )
            continue
        if re.search(r"(?<!=)=>(?!>)", stripped):
            problems.append(
                f"{rel}:{line_no}: malformed arrow '=>' in flowchart, use '==>'"
            )
            continue

        edges = FLOWCHART_EDGE_RE.findall(stripped)
        nodes = FLOWCHART_EDGE_RE.split(stripped)
        if edges:
            if not nodes[0].strip():
                problems.append(f"{rel}:{line_no}: arrow with no source node")
            if not nodes[-1].strip():
                problems.append(f"{rel}:{line_no}: trailing arrow with no target node")
            for middle in nodes[1:-1]:
                if not middle.strip():
                    problems.append(f"{rel}:{line_no}: arrow with no node between operators")

        for part in nodes:
            trimmed = part.strip()
            if not trimmed:
                continue
            for node_expr in trimmed.split("&"):
                node_id = node_expr.strip()
                if node_id and not NODE_ID_RE.match(node_id):
                    problems.append(f"{rel}:{line_no}: invalid node id '{node_id}'")


def lint_block(
    rel: str,
    block_start: int,
    lines: list[tuple[int, str]],
    problems: list[str],
) -> None:
    for line_no, text in lines:
        if "\t" in text:
            problems.append(
                f"{rel}:{line_no}: tab character found, Mermaid indentation must use spaces"
            )

    non_empty: list[tuple[int, str]] = []
    for line_no, text in lines:
        outside, _ = strip_quotes_and_comments(text)
        if outside.strip():
            non_empty.append((line_no, text))

    if not non_empty:
        problems.append(f"{rel}:{block_start}: empty mermaid diagram")
        return

    first_line_no, first_raw = non_empty[0]
    decl_outside, _ = strip_quotes_and_comments(first_raw)
    decl_tokens = decl_outside.strip().split()
    diagram_type = decl_tokens[0] if decl_tokens else ""

    if diagram_type not in DIAGRAM_TYPES:
        problems.append(
            f"{rel}:{first_line_no}: unknown or missing Mermaid diagram type '{diagram_type}'"
        )
        return

    if diagram_type in ("flowchart", "graph"):
        if len(decl_tokens) < 2:
            problems.append(
                f"{rel}:{first_line_no}: missing direction for {diagram_type}, expected TD, TB, LR, RL, or BT"
            )
        else:
            direction = decl_tokens[1].rstrip(";")
            if direction not in DIRECTIONS:
                problems.append(
                    f"{rel}:{first_line_no}: invalid {diagram_type} direction '{direction}', expected TD, TB, LR, RL, or BT"
                )

    if len(non_empty) < 2:
        problems.append(f"{rel}:{first_line_no}: empty mermaid diagram, no statements")
        return

    bracket_stack: list[tuple[str, int]] = []
    subgraph_stack: list[int] = []

    for line_no, raw in lines:
        outside, quotes_ok = strip_quotes_and_comments(raw)
        if not quotes_ok:
            problems.append(f"{rel}:{line_no}: unbalanced double quotes")
        for ch in outside:
            if ch in BRACKET_OPEN:
                bracket_stack.append((ch, line_no))
            elif ch in BRACKET_CLOSE:
                if not bracket_stack:
                    problems.append(f"{rel}:{line_no}: unmatched closing '{ch}'")
                else:
                    top_ch, top_line = bracket_stack[-1]
                    if BRACKET_OPEN[top_ch] != ch:
                        problems.append(
                            f"{rel}:{line_no}: mismatched bracket '{ch}', expected closing for '{top_ch}' from line {top_line}"
                        )
                    else:
                        bracket_stack.pop()

        if diagram_type in ("flowchart", "graph"):
            trimmed = outside.strip()
            if re.match(r"^subgraph\b", trimmed):
                subgraph_stack.append(line_no)
            elif re.match(r"^end\b", trimmed):
                if not subgraph_stack:
                    problems.append(f"{rel}:{line_no}: 'end' without matching 'subgraph'")
                else:
                    subgraph_stack.pop()

    if bracket_stack:
        top_ch, top_line = bracket_stack[-1]
        problems.append(f"{rel}:{top_line}: unclosed '{top_ch}' bracket")

    if subgraph_stack:
        open_line = subgraph_stack[-1]
        problems.append(f"{rel}:{open_line}: missing 'end' for 'subgraph'")

    if diagram_type in ("flowchart", "graph"):
        for line_no, raw in non_empty[1:]:
            lint_flowchart_line(rel, line_no, raw, problems)
    elif diagram_type == "sequenceDiagram":
        lint_sequence_diagram(rel, non_empty[1:], problems)


def lint_sequence_diagram(
    rel: str, statements: list[tuple[int, str]], problems: list[str]
) -> None:
    declared: set[str] = set()
    for _, raw in statements:
        outside, _ = strip_quotes_and_comments(raw)
        match = re.match(r"^\s*(?:participant|actor)\s+(.+)$", outside)
        if match:
            spec = match.group(1).strip()
            if " as " in spec:
                parts = re.split(r"\s+as\s+", spec, maxsplit=1)
                for part in parts:
                    name = part.strip().strip('"')
                    if name:
                        declared.add(name)
            else:
                name = spec.strip().strip('"')
                if name:
                    declared.add(name)

    block_stack: list[tuple[str, int]] = []
    act_stack: list[tuple[str, int]] = []

    for line_no, raw in statements:
        outside, _ = strip_quotes_and_comments(raw)
        trimmed = outside.strip()
        if not trimmed or trimmed.startswith("%%"):
            continue
        if trimmed == "autonumber" or re.match(r"^(?:participant|actor)\b", trimmed):
            continue
        if re.match(r"^Note\b", trimmed, re.I):
            continue

        act_match = re.match(r"^activate\s+(\S+)$", trimmed)
        if act_match:
            act_stack.append((act_match.group(1), line_no))
            continue
        deact_match = re.match(r"^deactivate\s+(\S+)$", trimmed)
        if deact_match:
            deact_name = deact_match.group(1)
            found = False
            for i in range(len(act_stack) - 1, -1, -1):
                if act_stack[i][0] == deact_name:
                    act_stack.pop(i)
                    found = True
                    break
            if not found:
                problems.append(
                    f"{rel}:{line_no}: 'deactivate {deact_name}' without matching 'activate'"
                )
            continue

        if re.match(r"^(?:alt|opt|loop|par|critical|break|rect)\b", trimmed):
            block_kw = trimmed.split()[0]
            block_stack.append((block_kw, line_no))
            continue
        if re.match(r"^(?:else|and)\b", trimmed):
            if not block_stack:
                problems.append(
                    f"{rel}:{line_no}: '{trimmed.split()[0]}' outside conditional block"
                )
            continue
        if trimmed == "end" or re.match(r"^end\b", trimmed):
            if not block_stack:
                problems.append(f"{rel}:{line_no}: 'end' without matching block")
            else:
                block_stack.pop()
            continue

        arrow_match = SEQ_ARROW_RE.search(trimmed)
        if arrow_match:
            sender = trimmed[: arrow_match.start()].strip()
            rest = trimmed[arrow_match.end() :].strip()
            receiver = rest.split(":", 1)[0].strip() if ":" in rest else rest
            if declared:
                if sender and sender not in declared:
                    problems.append(
                        f"{rel}:{line_no}: participant '{sender}' was not declared with participant/actor"
                    )
                if receiver and receiver not in declared:
                    problems.append(
                        f"{rel}:{line_no}: participant '{receiver}' was not declared with participant/actor"
                    )
        elif ":" in trimmed and not re.match(
            r"^(?:title|link|links|box)\b", trimmed, re.I
        ):
            problems.append(
                f"{rel}:{line_no}: invalid sequence diagram arrow, must be one of ->>, -->>, ->, -->, -x, --x, -), --)"
            )

    if block_stack:
        open_kw, open_line = block_stack[-1]
        problems.append(f"{rel}:{open_line}: unclosed '{open_kw}' block, missing 'end'")
    if act_stack:
        open_name, open_line = act_stack[-1]
        problems.append(
            f"{rel}:{open_line}: unclosed 'activate {open_name}', missing 'deactivate'"
        )


def check_file(path: Path, root: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    rel = os.path.relpath(path, root)
    lines = path.read_text(encoding="utf-8").splitlines()

    in_mermaid = False
    in_other = False
    active_fence = ""
    block_start = 0
    block_lines: list[tuple[int, str]] = []
    blocks_count = 0

    for line_no, line in enumerate(lines, 1):
        if not in_mermaid and not in_other:
            m_match = OPEN_MERMAID.match(line)
            if m_match:
                in_mermaid = True
                active_fence = m_match.group("fence")
                block_start = line_no
                block_lines = []
                blocks_count += 1
                continue
            other_match = OPEN_ANY_FENCE.match(line)
            if other_match:
                in_other = True
                active_fence = other_match.group("fence")
                continue
        elif in_other:
            if re.match(r"^\s*" + re.escape(active_fence) + r"\s*$", line):
                in_other = False
            continue
        elif in_mermaid:
            if re.match(r"^\s*" + re.escape(active_fence) + r"\s*$", line):
                lint_block(rel, block_start, block_lines, problems)
                in_mermaid = False
                block_lines = []
            else:
                block_lines.append((line_no, line))

    if in_mermaid:
        problems.append(f"{rel}:{block_start}: unterminated ```mermaid fence")

    return problems, blocks_count


def check(root: Path) -> list[str]:
    if root.is_file() and root.suffix in PAGES:
        pages = [root]
    else:
        pages = sorted(
            path
            for path in root.rglob("*")
            if path.suffix in PAGES
            and "node_modules" not in path.parts
            and not path.name.startswith("_")
        )
    if not pages:
        return [f"no page found under {root}"]

    problems: list[str] = []
    total_blocks = 0
    for page in pages:
        page_problems, count = check_file(page, root)
        problems.extend(page_problems)
        total_blocks += count

    if total_blocks == 0 and not problems:
        return [f"no mermaid diagrams found under {root}"]

    return problems


def selftest() -> int:
    cases = [
        (
            "a valid flowchart and a valid sequence diagram pass",
            (
                "---\ntitle: One\n---\n\n# One\n\n```mermaid\nflowchart TD\n"
                "    A[Start] --> B{Choice}\n    B -->|Yes| C[OK]\n"
                "    B -->|No| D[Done]\n```\n\n```mermaid\nsequenceDiagram\n"
                "    actor Alice\n    participant Bob\n"
                "    Alice->>Bob: Hello\n    Bob-->>Alice: Hi\n```\n"
            ),
            None,
        ),
        (
            "a block with no diagram type is flagged",
            "---\ntitle: Two\n---\n\n# Two\n\n```mermaid\nA --> B\n```\n",
            "diagram type",
        ),
        (
            "flowchart XZ is flagged for the direction",
            "---\ntitle: Three\n---\n\n# Three\n\n```mermaid\nflowchart XZ\n    A --> B\n```\n",
            "direction",
        ),
        (
            "an unclosed [ is flagged",
            "---\ntitle: Four\n---\n\n# Four\n\n```mermaid\nflowchart TD\n    A[Start --> B\n```\n",
            "unclosed '['",
        ),
        (
            "a missing end for a subgraph is flagged",
            (
                "---\ntitle: Five\n---\n\n# Five\n\n```mermaid\nflowchart TD\n"
                "    subgraph Cluster\n        A --> B\n```\n"
            ),
            "missing 'end' for 'subgraph'",
        ),
        (
            "A -> B inside a flowchart is flagged",
            "---\ntitle: Six\n---\n\n# Six\n\n```mermaid\nflowchart TD\n    A -> B\n```\n",
            "malformed arrow '->'",
        ),
        (
            "a sequence message to a participant never declared is flagged",
            (
                "---\ntitle: Seven\n---\n\n# Seven\n\n```mermaid\nsequenceDiagram\n"
                "    participant Alice\n    Alice->>Bob: Hello\n```\n"
            ),
            "not declared",
        ),
        (
            "an unterminated ```mermaid fence is flagged",
            "---\ntitle: Eight\n---\n\n# Eight\n\n```mermaid\nflowchart TD\n    A --> B\n",
            "unterminated",
        ),
        (
            'a label containing "a[0]" passes',
            '---\ntitle: Nine\n---\n\n# Nine\n\n```mermaid\nflowchart TD\n    A["a[0]"] --> B\n```\n',
            None,
        ),
        (
            "an empty mermaid block is flagged",
            "---\ntitle: Ten\n---\n\n# Ten\n\n```mermaid\n```\n",
            "empty",
        ),
    ]

    failures = []
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "page.md").write_text(body, encoding="utf-8")
            problems = check(root)
            if expected is None and problems:
                failures.append(f"{name}: reported {problems}")
            elif expected is not None:
                if not any(expected in problem for problem in problems):
                    failures.append(
                        f"{name}: {expected!r} was not reported, got {problems}"
                    )
                elif not any(problem.startswith("page.md:") for problem in problems):
                    failures.append(f"{name}: no file:line prefix in {problems}")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1

    print(
        "ok: diagram type, direction, unclosed brackets, subgraph ends, malformed arrows, participants and unterminated fences all go red"
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
        print(f"\n{len(problems)} diagram problem(s)", file=sys.stderr)
        return 1
    print("mermaid diagrams ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
