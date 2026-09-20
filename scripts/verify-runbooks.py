#!/usr/bin/env python3
"""No runbook hands an operator a destructive command without a warning (T-0105, OPS).

`Operations/01-runbooks.md` is read during an incident and its blocks are pasted under pressure.
Diagnosis must be read-only; a destructive remediation must carry a visible warning next to it,
and every runbook must end with a way to tell whether it worked. The command patterns live in one
module-level table so the list stays auditable at a glance.

    verify-runbooks.py [docs-root]
    verify-runbooks.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

DESTRUCTIVE: dict[str, str] = {
    r"\brm\s+-[a-zA-Z]*[rf]": "recursive or forced delete",
    r"\brm\s+/": "delete of an absolute path",
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b": "schema drop",
    r"\bTRUNCATE\b": "table truncation",
    r"\bDELETE\s+FROM\s+(?!.*\bWHERE\b)": "unfiltered DELETE",
    r"\bkubectl\s+delete\b": "kubernetes object delete",
    r"\bcurl\b[^\n]*-X\s*DELETE": "HTTP DELETE",
    r"--force\b": "forced operation",
    r"--purge\b": "purge",
    r"\bhelm\s+uninstall\b": "release removal",
    r"\bhelmfile\s+destroy\b": "deployment destroy",
    r"\bterraform\s+destroy\b": "infrastructure destroy",
    r"\bdd\s+if=": "raw disk write",
    r"\bmkfs\b": "filesystem creation",
    r">\s*/dev/sd": "raw device write",
    r"\bgit\s+push\b[^\n]*--force": "force push",
    r"\bemergency-revoke\b|\brevoke\b": "credential or policy revocation",
    r"--revert\b": "overwrite of live state from Git",
    r"--overwrite\b": "overwrite",
    r"\bflushall\b": "cache flush",
}
COMPILED = {re.compile(pattern, re.I): reason for pattern, reason in DESTRUCTIVE.items()}
READ_ONLY_SECTIONS = ("symptoms", "diagnosis", "detection", "triage")
WARNING = re.compile(r"^\s*(:::(warning|danger|caution)|\*\*(warning|danger|caution|irreversible))", re.I)
RUNBOOK_HEADING = re.compile(r"^##\s+\d+\.\s+.*runbook", re.I)
WARNING_WINDOW = 12


def _blocks(text: str) -> list[tuple[int, str, str, str]]:
    """(line number, runbook heading, subsection heading, block body) for every fenced block."""
    out: list[tuple[int, str, str, str]] = []
    runbook = subsection = ""
    fence: list[str] | None = None
    fence_line = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if fence is None:
                fence, fence_line = [], lineno
            else:
                out.append((fence_line, runbook, subsection, "\n".join(fence)))
                fence = None
            continue
        if fence is not None:
            fence.append(line)
            continue
        if line.startswith("## "):
            runbook, subsection = line[3:].strip(), ""
        elif line.startswith("### "):
            subsection = line[4:].strip()
    if fence is not None:
        out.append((fence_line, runbook, subsection, "\n".join(fence)))
    return out


def _findings(body: str) -> list[str]:
    reasons: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for pattern, reason in COMPILED.items():
            if pattern.search(line) and reason not in reasons:
                reasons.append(reason)
    return reasons


def _warned(lines: list[str], fence_line: int) -> bool:
    start = max(0, fence_line - 1 - WARNING_WINDOW)
    window = lines[start : fence_line - 1]
    for line in window:
        if line.startswith("### ") or line.startswith("## "):
            continue
        if WARNING.match(line):
            return True
    return False


def check(root: Path) -> list[str]:
    problems: list[str] = []
    pages = [p for p in sorted(root.rglob("*.md")) if "Operations" in p.parts or p.parent == root]
    runbook_pages = 0
    for path in pages:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        sections = [line for line in lines if RUNBOOK_HEADING.match(line)]
        if not sections:
            continue
        runbook_pages += 1
        rel = path.relative_to(root).as_posix()
        blocks = _blocks(text)
        if not blocks:
            problems.append(f"{rel}: holds runbooks but no command block, so nothing was audited")

        for fence_line, runbook, subsection, body in blocks:
            reasons = _findings(body)
            if not reasons:
                continue
            where = subsection.lower()
            if any(k in where for k in READ_ONLY_SECTIONS):
                problems.append(
                    f"{rel}:{fence_line}: {', '.join(reasons)} under '{subsection}' of '{runbook}': "
                    "diagnosis must be read-only"
                )
            elif not _warned(lines, fence_line):
                problems.append(
                    f"{rel}:{fence_line}: {', '.join(reasons)} under '{subsection}' of '{runbook}' "
                    "carries no warning callout within the preceding "
                    f"{WARNING_WINDOW} lines"
                )

        # every runbook has to say how the operator knows it worked
        current, verified = "", set()
        for line in lines:
            if RUNBOOK_HEADING.match(line):
                current = line[3:].strip()
            elif line.startswith("## "):
                current = ""
            elif current and line.startswith("### ") and "verification" in line.lower():
                verified.add(current)
        for section in sections:
            name = section[3:].strip()
            if name not in verified:
                problems.append(f"{rel}: runbook '{name}' has no '### Verification' subsection")

    if runbook_pages == 0:
        problems.append("no runbook was found, so this run proves nothing")
    return problems


def selftest() -> int:
    clean = """---
title: Runbooks
---

# Runbooks

## 1. Runbook 1: Drift

### Diagnosis

```bash
jcctl plan --repo-dir ./repo
```

### Remediation

:::danger
Overwrites live state.
:::

```bash
jcctl apply --revert --repo-dir ./repo
```

### Verification

```bash
jcctl plan --assert-empty
```
"""
    cases: list[tuple[str, str, str | None]] = [
        ("clean runbook", clean, None),
        ("delete under diagnosis", clean.replace("jcctl plan --repo-dir ./repo", "kubectl delete pod broker-0"),
         "diagnosis must be read-only"),
        ("unwarned remediation", clean.replace(":::danger\nOverwrites live state.\n:::\n\n", ""),
         "carries no warning callout"),
        ("bold callout instead of an admonition",
         clean.replace(":::danger\nOverwrites live state.\n:::", "**Warning:** overwrites live state."), None),
        ("rm -rf with a warning", clean.replace("jcctl apply --revert --repo-dir ./repo", "rm -rf /var/lib/data"), None),
        ("rm -rf without a warning",
         clean.replace(":::danger\nOverwrites live state.\n:::\n\n", "").replace(
             "jcctl apply --revert --repo-dir ./repo", "rm -rf /var/lib/data"), "recursive or forced delete"),
        ("unfiltered delete", clean.replace("jcctl plan --repo-dir ./repo", "psql -c \"DELETE FROM entities;\""),
         "unfiltered DELETE"),
        ("filtered delete", clean.replace("jcctl plan --repo-dir ./repo",
                                          "psql -c \"DELETE FROM entities WHERE id = '1';\""), None),
        ("no verification section", clean.replace("### Verification\n\n```bash\njcctl plan --assert-empty\n```\n", ""),
         "no '### Verification' subsection"),
        ("no runbook at all", "---\ntitle: X\n---\n\n# X\n\nProse only.\n", "no runbook was found"),
        ("runbook without a command block",
         "---\ntitle: R\n---\n\n# R\n\n## 1. Runbook 1: Drift\n\n### Verification\n\nRead the console.\n",
         "no command block"),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Operations").mkdir()
        for name, body, expected in cases:
            (root / "Operations" / "01-runbooks.md").write_text(body, encoding="utf-8")
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a delete in a diagnosis block, an unwarned destructive remediation, an unfiltered "
          "DELETE, a runbook without verification and a corpus without runbooks all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} runbook safety problem(s)", file=sys.stderr)
        return 1
    print("runbooks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
