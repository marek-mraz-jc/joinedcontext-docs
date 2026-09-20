#!/usr/bin/env python3
"""Architecture and Deployment describe the same components (T-0104, TS-18).

`Deployment/04-components-and-addons.md` §1 is the authoritative matrix: slug, class, language,
responsibility. `Architecture/14-components.md` describes what each of those does and how it
fails. The two chapters name components differently on purpose (slugs against display names), so
each architecture entry carries its slug in a backtick span — `### Context Gateway (\`context-gateway\`)`
and `- **Apache Superset** (\`superset\`):`. An entry without a slug is reported rather than guessed
at: a fuzzy match is exactly how the two chapters drift apart without anyone noticing.

    audit-component-matrix.py [docs-root]
    audit-component-matrix.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

ARCH = "Architecture/14-components.md"
DEPLOY = "Deployment/04-components-and-addons.md"
LANGUAGES = ("Rust", "Go", "Java", "Python", "Lua", "JavaScript", "TypeScript", "React", "Node")
LABELS = ("**Primary Role:**", "**Interfaces:**", "**State & Failure Behavior:**")
SLUG = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
CORE_HEADING = re.compile(r"^###\s+(.*)$")
ADDON_BULLET = re.compile(r"^-\s+\*\*([^*]+)\*\*\s*(.*)$")
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+)(#[^)]*)?\)")


def _matrix(text: str) -> tuple[dict[str, tuple[str, str, str]], list[str]]:
    """slug -> (class, language, responsibility) from the first table of the deployment chapter."""
    rows: dict[str, tuple[str, str, str]] = {}
    problems: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or all(set(c) <= {"-", ":"} and c for c in cells):
            continue
        slug = re.sub(r"[*`]", "", cells[0]).strip()
        if slug.lower() in ("component", ""):
            continue
        if not cells[1] or not cells[2]:
            problems.append(f"{DEPLOY}: component '{slug}' has an empty class or language cell")
            continue
        rows[slug] = (cells[1], cells[2], cells[3] if len(cells) > 3 else "")
    return rows, problems


def _architecture(text: str) -> tuple[dict[str, tuple[str, str, str]], list[str]]:
    """slug -> (display name, class, body) from the core section and the addon section."""
    entries: dict[str, tuple[str, str, str]] = {}
    problems: list[str] = []
    section = ""
    current: tuple[str, str] | None = None
    body: list[str] = []

    def close() -> None:
        if current:
            entries[current[1]] = (current[0], "Core", "\n".join(body))

    for line in text.splitlines():
        if line.startswith("## "):
            close()
            current, body = None, []
            low = line.lower()
            section = "core" if "core platform component" in low else "addon" if "addon" in low else ""
            continue
        if section == "core":
            m = CORE_HEADING.match(line)
            if m:
                close()
                body = []
                name = m.group(1).strip()
                slug = SLUG.findall(name)
                if not slug:
                    problems.append(f"{ARCH}: core component '{name}' declares no `slug`")
                    current = None
                    continue
                current = (name, slug[-1])
                continue
            if current:
                body.append(line)
        elif section == "addon":
            m = ADDON_BULLET.match(line)
            if m:
                name, rest = m.group(1).strip(), m.group(2)
                slug = SLUG.findall(rest.split(":")[0])
                if not slug:
                    problems.append(f"{ARCH}: addon '{name}' declares no `slug`")
                    continue
                entries[slug[0]] = (name, "Add-on", rest)
    close()
    return entries, problems


def check(root: Path) -> list[str]:
    arch_path, deploy_path = root / ARCH, root / DEPLOY
    for path, rel in ((arch_path, ARCH), (deploy_path, DEPLOY)):
        if not path.is_file():
            return [f"{rel}: the chapter this audit compares is missing"]

    deploy_text = deploy_path.read_text(encoding="utf-8")
    arch_text = arch_path.read_text(encoding="utf-8")
    matrix, problems = _matrix(deploy_text)
    entries, arch_problems = _architecture(arch_text)
    problems += arch_problems

    if len(matrix) < 10:
        problems.append(f"{DEPLOY}: the component matrix holds {len(matrix)} rows, expected at least 10")
        return problems
    if not entries:
        problems.append(f"{ARCH}: neither the core nor the addon section named a component")
        return problems

    for slug in sorted(set(matrix) - set(entries)):
        problems.append(f"{ARCH}: '{slug}' is in the deployment matrix ({matrix[slug][0]}) and is described nowhere here")
    for slug in sorted(set(entries) - set(matrix)):
        problems.append(f"{DEPLOY}: '{slug}' is described in the architecture chapter as "
                        f"'{entries[slug][0]}' and is missing from the matrix")

    for slug in sorted(set(matrix) & set(entries)):
        name, arch_class, body = entries[slug]
        dep_class, dep_language, _ = matrix[slug]
        if arch_class.lower().replace("-", "") != dep_class.lower().replace("-", ""):
            problems.append(f"{DEPLOY}: '{slug}' is {dep_class} in the matrix and {arch_class} in the architecture chapter")
        claimed = [lang for lang in LANGUAGES if re.search(rf"\b{lang}\b", body)]
        if claimed and not any(lang in dep_language for lang in claimed):
            problems.append(
                f"{DEPLOY}: '{slug}' is {dep_language} in the matrix and "
                f"{'/'.join(claimed)} in the architecture chapter"
            )
        if arch_class == "Core":
            for label in LABELS:
                if label not in body:
                    problems.append(f"{ARCH}: core component '{name}' has no {label} line")

    for lineno, line in enumerate(arch_text.splitlines(), 1):
        for target, _anchor in LINK.findall(line):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (arch_path.parent / target).resolve().is_file():
                problems.append(f"{ARCH}:{lineno}: link target '{target}' does not exist")
    return problems


def _corpus(root: Path, arch: str, deploy: str) -> None:
    (root / "Architecture").mkdir(exist_ok=True)
    (root / "Deployment").mkdir(exist_ok=True)
    (root / ARCH).write_text(arch, encoding="utf-8")
    (root / DEPLOY).write_text(deploy, encoding="utf-8")


def selftest() -> int:
    core_names = ["context-gateway", "context-broker", "portal", "jcctl", "gitea", "apisix",
                  "keycloak", "postgres", "artifact-store", "pipeline-runner"]
    arch_core = "".join(
        f"### Component {slug} (`{slug}`)\n\n"
        f"- **Primary Role:** does {slug} things in Rust.\n"
        f"- **Interfaces:** HTTPS.\n"
        f"- **State & Failure Behavior:** stateless.\n\n"
        for slug in core_names
    )
    arch = ("---\ntitle: Components\n---\n\n# Components\n\n"
            "## 2. Core Platform Components\n\n" + arch_core +
            "## 3. Pluggable Addon Ecosystem\n\n- **Grafana** (`grafana`): dashboards.\n")
    rows = "".join(f"| **{slug}** | Core | Rust | does {slug} things |\n" for slug in core_names)
    deploy = ("---\ntitle: Matrix\n---\n\n# Matrix\n\n## 1. Core Components vs. Add-ons Matrix\n\n"
              "| Component | Class | Language / Engine | Responsibility |\n|---|---|---|---|\n"
              + rows + "| **grafana** | Add-on | Go | dashboards |\n")

    cases: list[tuple[str, str, str, str | None]] = [
        ("matching chapters", arch, deploy, None),
        ("slug only in the matrix", arch, deploy + "| **frost** | Add-on | Java | sta |\n",
         "'frost' is in the deployment matrix"),
        ("slug only in the architecture chapter",
         arch + "\n- **FROST** (`frost`): sta.\n", deploy, "'frost' is described in the architecture chapter"),
        ("class disagreement", arch, deploy.replace("| **grafana** | Add-on |", "| **grafana** | Core |"),
         "'grafana' is Core in the matrix and Add-on"),
        ("language disagreement", arch, deploy.replace("| **portal** | Core | Rust |", "| **portal** | Core | Go |"),
         "'portal' is Go in the matrix and Rust"),
        ("core entry without an Interfaces line", arch.replace("- **Interfaces:** HTTPS.\n", "", 1), deploy,
         "has no **Interfaces:** line"),
        ("architecture entry without a slug",
         arch.replace("### Component portal (`portal`)", "### Component portal"), deploy,
         "declares no `slug`"),
        ("no matrix table at all", arch,
         "---\ntitle: Matrix\n---\n\n# Matrix\n\nProse only.\n", "expected at least 10"),
        ("dead link in the architecture chapter",
         arch + "\nSee [sizing](../Deployment/99-missing.md).\n", deploy, "link target"),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, a, d, expected in cases:
            _corpus(root, a, d)
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a component in one chapter only, a class or language disagreement, a missing "
          "interface line, a slugless entry, a missing matrix and a dead link all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} component matrix problem(s)", file=sys.stderr)
        return 1
    print("component matrix ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
