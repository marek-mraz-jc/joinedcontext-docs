#!/usr/bin/env python3
"""Every manifest the documentation prints is run through the real `jcctl validate` (T-2143).

`validate-doc-manifests.py` checks each block against the published JSON Schema. That is the
weaker half of the truth: the schema cannot refuse an unknown field beside a `secretRef`, it
does not know that `metadata.namespace` is required of every kind (MF-02) or that an
organization-scoped kind must carry `org`, and it knows nothing about where a manifest belongs
in the repository (MF-06). `jcctl validate` knows all of it, because it is the same code the
reconciler runs — so the examples are run rather than trusted.

One temporary organization repository per page, because a page's examples belong together: an
`Endpoint` and the `DataSource` it reads are printed a few lines apart and reference each
other. The repository is scaffolded with the `Organization` and the `Project` manifests the
examples never print (nobody repeats `org.yaml` on every page), each manifest is placed where
its kind says it belongs, and `jcctl validate` is run over the whole tree.

A finding that says a manifest is wrong fails this check. A finding that says a manifest points
at something *this page* does not print — a DataModel introduced in another chapter, an
Endpoint of the neighbouring instance — is listed as a note instead: a page is not required to
reprint the rest of the repository. The message shapes are listed in `CROSS_REFERENCE`, so a
new kind of finding fails rather than being quietly forgiven.

    JC_JCCTL=/path/to/jcctl validate-doc-manifests-with-jcctl.py [docs-root]
    validate-doc-manifests-with-jcctl.py --selftest

Without `JC_JCCTL` it prints what would enable it and passes, the same way the other checkers
that need the code do.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

API_VERSION_PREFIX = "joinedcontext.com"
FENCE = re.compile(r"^```(.*)$")
EXCERPT = re.compile(r"\bexcerpts?\b", re.I)
BELONGS = re.compile(r"belongs at `([^`]+)` \(MF-06\)")
# A finding about what a page does not reprint, rather than about the manifest it prints.
CROSS_REFERENCE = (
    "which no manifest of this project declares",
    "which the repository does not",
    "which the repository holds no",
    "declares no Project",
)
ORG_NAMESPACE = "org"
# The scaffolding a page never prints: one organization and one project per namespace used.
ORGANIZATION = {
    "apiVersion": "joinedcontext.com/v1alpha1",
    "kind": "Organization",
    "metadata": {"name": "example", "namespace": ORG_NAMESPACE},
    "spec": {"domain": "example.org", "locales": ["en"], "defaultLocale": "en"},
}


def manifests_of(text: str) -> list[tuple[int, dict]]:
    """Every whole manifest printed on one page, with the line its block opens on.

    An `excerpt` block prints one section of a manifest on purpose (the convention
    `validate-doc-manifests.py` defines), so it is not a manifest anybody could apply.
    """
    found: list[tuple[int, dict]] = []
    info: str | None = None
    block: list[str] = []
    start = 0
    for number, line in enumerate(text.splitlines(), start=1):
        fence = FENCE.match(line)
        if fence is not None:
            if info is None:
                info, block, start = fence.group(1), [], number
                continue
            body = "\n".join(block)
            if (
                info.split(" ")[0] in {"yaml", "yml"}
                and not EXCERPT.search(info)
                and f"apiVersion: {API_VERSION_PREFIX}" in body
            ):
                try:
                    documents = list(yaml.safe_load_all(body))
                except yaml.YAMLError:
                    documents = []
                for document in documents:
                    if isinstance(document, dict) and str(
                        document.get("apiVersion", "")
                    ).startswith(API_VERSION_PREFIX):
                        found.append((start, document))
            info = None
            continue
        if info is not None:
            block.append(line)
    return found


def identity(manifest: dict) -> tuple[str, str, str]:
    metadata = manifest.get("metadata") or {}
    return (
        str(manifest.get("kind", "")),
        str(metadata.get("namespace", "")),
        str(metadata.get("name", "")),
    )


def project(namespace: str) -> dict:
    return {
        "apiVersion": "joinedcontext.com/v1alpha1",
        "kind": "Project",
        "metadata": {"name": namespace, "namespace": ORG_NAMESPACE},
        "spec": {"organizationRef": ORGANIZATION["metadata"]["name"]},
    }


def build_tree(root: pathlib.Path, manifests: list[tuple[int, dict]]) -> dict[str, int]:
    """Writes one page's manifests into a repository, and says which line each file came from."""
    (root / "org.yaml").write_text(yaml.safe_dump(ORGANIZATION, sort_keys=False), encoding="utf-8")
    staging = root / "staging"
    staging.mkdir()
    lines: dict[str, int] = {}
    namespaces: set[str] = set()
    seen: set[tuple[str, str, str]] = set()
    for line, manifest in manifests:
        key = identity(manifest)
        # A page may print the same object twice, shorter and then in full; the repository
        # refuses a duplicate identity, and the second printing is the same object either way.
        if key in seen:
            continue
        seen.add(key)
        kind, namespace, name = key
        if namespace and namespace != ORG_NAMESPACE:
            namespaces.add(namespace)
        path = staging / f"{line}-{kind}-{name or 'unnamed'}.yaml"
        path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        lines[path.relative_to(root).as_posix()] = line
    for namespace in sorted(namespaces):
        path = root / "projects" / namespace / "project.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(project(namespace), sort_keys=False), encoding="utf-8")
    return lines


def run_jcctl(jcctl: str, root: pathlib.Path) -> list[str]:
    result = subprocess.run(
        [jcctl, "validate", "--repo-dir", str(root)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return [
        line
        for line in result.stderr.splitlines()
        if line and not line.startswith("warning:") and "manifests valid" not in line
    ]


def place_and_validate(jcctl: str, root: pathlib.Path, lines: dict[str, int]) -> list[str]:
    """Moves each manifest where its kind says it belongs, then validates the repository.

    The paths come from `jcctl` itself rather than from a copy of the rules here: the first run
    reports where every staged file belongs (MF-06), the files are moved there, and the second
    run is the verdict. A rule that changes in the platform changes this check with it.
    """
    findings = run_jcctl(jcctl, root)
    moves: dict[str, str] = {}
    for finding in findings:
        where = BELONGS.search(finding)
        relative = finding.split(":", 1)[0]
        if where and relative in lines:
            moves[relative] = where.group(1)
    for relative, destination in moves.items():
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        (root / relative).rename(target)
        lines[destination] = lines.pop(relative)
    return run_jcctl(jcctl, root)


def locate(finding: str, page: str, lines: dict[str, int]) -> str:
    """A finding as a person can act on it: the page and the block, not the temporary tree."""
    relative = finding.split(":", 1)[0]
    rest = finding.split("): ", 1)[-1]
    line = lines.get(relative)
    return f"{page}:{line}: {rest}" if line else f"{page}: {rest}"


def check(root: pathlib.Path, jcctl: str) -> tuple[list[str], list[str], int]:
    """Every page's examples, validated. Returns (failures, notes, manifests checked)."""
    failures: list[str] = []
    notes: list[str] = []
    checked = 0
    for page in sorted(root.rglob("*.md")):
        if any(part in {"node_modules", ".git"} for part in page.parts):
            continue
        manifests = manifests_of(page.read_text(encoding="utf-8"))
        if not manifests:
            continue
        name = page.relative_to(root).as_posix()
        with tempfile.TemporaryDirectory() as temporary:
            tree = pathlib.Path(temporary)
            lines = build_tree(tree, manifests)
            checked += len(lines)
            for finding in place_and_validate(jcctl, tree, lines):
                where = locate(finding, name, lines)
                if any(shape in finding for shape in CROSS_REFERENCE):
                    notes.append(where)
                else:
                    failures.append(where)
    return failures, notes, checked


GOOD = """# A page

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: air-quality
  namespace: helsinki
spec:
  urnSegment: airquality
```
"""
# The schema accepts it (`namespace` is not in its required list); `jcctl` does not (MF-02).
NO_NAMESPACE = GOOD.replace("  namespace: helsinki\n", "")
# An excerpt is not a manifest anybody applies, so it is not run.
EXCERPT_PAGE = GOOD.replace("```yaml", "```yaml excerpt")


def selftest(jcctl: str | None) -> int:
    failures: list[str] = []

    # The reader, which needs no platform at all.
    if len(manifests_of(GOOD)) != 1:
        failures.append("a whole manifest was not read out of its page")
    if manifests_of(EXCERPT_PAGE):
        failures.append("an excerpt was read as a manifest anybody could apply")
    if manifests_of("```yaml\nnot: a manifest\n```\n"):
        failures.append("a yaml block that is not a manifest was read as one")

    if not jcctl:
        print(
            "JC_JCCTL is not set, so the self-test checked the reader alone. Point it at a "
            "`jcctl` binary to check the verdicts too.",
            file=sys.stderr,
        )
    else:
        for name, page, expected in [
            ("a valid manifest", GOOD, False),
            ("a manifest with no namespace", NO_NAMESPACE, True),
        ]:
            with tempfile.TemporaryDirectory() as temporary:
                docs = pathlib.Path(temporary)
                (docs / "page.md").write_text(page, encoding="utf-8")
                found, _, checked = check(docs, jcctl)
                if expected and not found:
                    failures.append(f"{name}: jcctl refused nothing")
                if not expected and found:
                    failures.append(f"{name}: reported {found}")
                if not expected and checked != 1:
                    failures.append(f"{name}: {checked} manifest(s) checked, expected 1")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: an excerpt is skipped, and a manifest the schema accepts can still be refused")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_root", nargs="?", default=".")
    parser.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args(argv[1:])

    jcctl = os.environ.get("JC_JCCTL") or shutil.which("jcctl")
    if arguments.selftest:
        return selftest(jcctl)

    if not jcctl:
        print(
            "JC_JCCTL is not set and no `jcctl` is on PATH, so the documented manifests were "
            "not run through it. Build it with `cargo build -p jcctl` and point JC_JCCTL at the "
            "binary."
        )
        return 0

    root = pathlib.Path(arguments.docs_root)
    failures, notes, checked = check(root, jcctl)
    for note in notes:
        print(f"note: {note}")
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        print(
            f"\n{len(failures)} documented manifest(s) `jcctl validate` refuses, of {checked} "
            "checked",
            file=sys.stderr,
        )
        return 1
    print(f"{checked} documented manifests validate, {len(notes)} cross-page reference(s) noted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
