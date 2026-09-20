#!/usr/bin/env python3
"""Every manifest printed in the documentation is a manifest that would apply (T-0101, CC-12).

Each fenced block carrying `apiVersion: joinedcontext.com/v1alpha1` is extracted and checked:
the YAML parses, the apiVersion is exact, the kind is one the kind table in
`Development/04-manifest-kinds.md` declares, and `metadata.name` is present and a slug. With
`JC_SCHEMAS_DIR` pointing at the draft-07 schemas the platform publishes
(`<dir>/<Kind>.json`), each manifest is also validated against its schema; without it that leg
says which variable would enable it instead of pretending it ran.

A page that prints one section of a manifest rather than the whole of it marks the fence
`excerpt` (```yaml excerpt, or a title that contains the word). Such a block is still held to
every structural check above; only the schema, which cannot tell an abbreviation from a
mistake, is skipped. The kinds the platform does not publish a schema for at all are listed
under "Schema not published yet" on the kind page, and a kind listed there whose schema HAS
since appeared is itself reported: the list cannot go stale quietly.

    validate-doc-manifests.py [docs-root]
    validate-doc-manifests.py --selftest
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

KINDS_PAGE = "Development/04-manifest-kinds.md"
API_VERSION = "joinedcontext.com/v1alpha1"
# response envelopes carry the payload, not a stored object, so they have no metadata.name
ENVELOPES = {"List", "Bundle", "Change", "ChangeList"}
NAME = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
KIND_CELL = re.compile(r"`([A-Za-z]+)`")
# The fence info string of a block that prints part of a manifest on purpose.
EXCERPT = re.compile(r"\bexcerpts?\b", re.I)
PENDING_HEADING = "Schema not published yet"


def declared_kinds(root: Path) -> tuple[set[str], list[str]]:
    path = root / KINDS_PAGE
    if not path.is_file():
        return set(), [f"{KINDS_PAGE}: the kind table lives here and the file is missing"]
    kinds: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        kinds.update(KIND_CELL.findall(cells[0]))
    if len(kinds) < 5:
        return kinds, [f"{KINDS_PAGE}: the kind table declares {len(kinds)} kinds, expected at least 5"]
    return kinds, []


def pending_kinds(root: Path) -> set[str]:
    """Kinds the kind page lists under "Schema not published yet".

    They are documented and printed, and the platform publishes no schema for them, so the
    schema leg has nothing to check. The list is on the page rather than in this script
    because the page is where a reader asks the question.
    """
    path = root / KINDS_PAGE
    if not path.is_file():
        return set()
    kinds: set[str] = set()
    under = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            under = PENDING_HEADING.lower() in line.lower()
            continue
        if under and line.lstrip().startswith(("-", "*")):
            kinds.update(KIND_CELL.findall(line))
    return kinds


def manifests(text: str) -> list[tuple[int, str, str]]:
    """(line number of the block body, fence info string, body) for every manifest block."""
    out: list[tuple[int, str, str]] = []
    body: list[str] | None = None
    start = 0
    info = ""
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if body is None:
                body, start = [], lineno + 1
                info = stripped[3:].strip()
            else:
                block = "\n".join(body)
                if API_VERSION in block:
                    out.append((start, info, block))
                body, info = None, ""
            continue
        if body is not None:
            body.append(line)
    return out


def _documents(block: str) -> list[str]:
    """A block may hold several manifests separated by `---`, and prose between them."""
    return [d for d in re.split(r"^---\s*$", block, flags=re.M) if API_VERSION in d]


def check(root: Path) -> list[str]:
    kinds, problems = declared_kinds(root)
    if problems:
        return problems

    schemas_dir = os.getenv("JC_SCHEMAS_DIR")
    validator = None
    if schemas_dir:
        try:
            import jsonschema
        except ImportError:
            problems.append("JC_SCHEMAS_DIR is set but jsonschema is not installed")
        else:
            validator = jsonschema.Draft7Validator

    pending = pending_kinds(root)
    if validator:
        # A kind stays on that list only until the platform publishes its schema. Reporting the
        # ones that have arrived is what stops the list from quietly outliving its reason.
        for kind in sorted(pending):
            if (Path(schemas_dir) / f"{kind}.json").is_file():
                problems.append(
                    f"{KINDS_PAGE}: '{kind}' is listed under \"{PENDING_HEADING}\" and "
                    f"{schemas_dir}/{kind}.json now exists — take it off that list"
                )

    found = 0
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        for lineno, info, block in manifests(path.read_text(encoding="utf-8")):
            for document in _documents(block):
                found += 1
                try:
                    data = yaml.safe_load(document)
                except yaml.YAMLError as err:
                    problems.append(f"{rel}:{lineno}: manifest does not parse as YAML ({err.__class__.__name__})")
                    continue
                if not isinstance(data, dict):
                    problems.append(f"{rel}:{lineno}: manifest is not a mapping")
                    continue

                # A blueprint's `spec.templates[].template` holds a manifest as a string, so the
                # block carries the api version while its own document is a fragment of one.
                # A document declaring neither field is that fragment; one that declares either
                # is an example manifest and is still held to both (T-0374).
                if "apiVersion" not in data and "kind" not in data:
                    found -= 1
                    continue

                if data.get("apiVersion") != API_VERSION:
                    problems.append(f"{rel}:{lineno}: apiVersion is {data.get('apiVersion')!r}, expected {API_VERSION!r}")
                kind = data.get("kind")
                if not kind:
                    problems.append(f"{rel}:{lineno}: manifest declares no kind")
                    continue
                if kind not in kinds:
                    problems.append(
                        f"{rel}:{lineno}: kind '{kind}' is not declared in {KINDS_PAGE} "
                        f"(declared: {', '.join(sorted(kinds))})"
                    )
                metadata = data.get("metadata")
                if kind in ENVELOPES:
                    continue
                if not isinstance(metadata, dict) or not metadata.get("name"):
                    problems.append(f"{rel}:{lineno}: {kind} has no metadata.name")
                elif "{{" in str(metadata["name"]):
                    pass  # a Blueprint prints the template, and the reconciler renders the name
                elif not NAME.match(str(metadata["name"])):
                    problems.append(
                        f"{rel}:{lineno}: {kind} name '{metadata['name']}' is not a slug "
                        "(lower case, digits and dashes, PF-06)"
                    )

                # An excerpt prints one section of a manifest, which a schema reads as a
                # manifest missing everything else. Every check above still applies to it.
                if validator and kind in kinds and kind not in pending and not EXCERPT.search(info):
                    schema_path = Path(schemas_dir) / f"{kind}.json"
                    if not schema_path.is_file():
                        problems.append(f"{rel}:{lineno}: no schema {schema_path} for kind '{kind}'")
                        continue
                    import json
                    schema = json.loads(schema_path.read_text(encoding="utf-8"))
                    for error in sorted(validator(schema).iter_errors(data), key=str):
                        where = "/".join(str(p) for p in error.absolute_path) or "(root)"
                        problems.append(f"{rel}:{lineno}: {kind} fails its schema at {where}: {error.message}")

    if found == 0:
        problems.append("no manifest block was found in the corpus, so this run proves nothing")
    return problems


def selftest() -> int:
    """The self-test builds its own corpus and its own schemas.

    An inherited `JC_SCHEMAS_DIR` — which CI now sets for the real run in the same job — would
    check that corpus against the platform's schemas and fail cases that are about something
    else entirely.
    """
    inherited = os.environ.pop("JC_SCHEMAS_DIR", None)
    try:
        return _selftest()
    finally:
        if inherited is not None:
            os.environ["JC_SCHEMAS_DIR"] = inherited


def _selftest() -> int:
    kinds_page = """---
title: Kinds
---

# Kinds

| Kind | Target Directory | Engine Consumer | Description |
|---|---|---|---|
| `Organization` | root | Portal | root |
| `Project` | projects | Portal | project |
| `ContextSpace` | spaces | Broker | space |
| `Endpoint` | endpoints | Gateway | endpoint |
| `Policy` | policies | Gateway | policy |
"""
    good = """---
title: Page
---

# Page

```yaml
apiVersion: joinedcontext.com/v1alpha1
kind: ContextSpace
metadata:
  name: ovzdusie
spec:
  retention: 90d
```
"""
    cases: list[tuple[str, str, str | None, str | None]] = [
        ("valid manifest", good, None, None),
        ("undeclared kind", good.replace("kind: ContextSpace", "kind: Wormhole"), "kind 'Wormhole' is not declared", None),
        ("wrong apiVersion", good.replace(API_VERSION, "joinedcontext.com/v1"), "no manifest block was found", None),
        ("missing metadata.name", good.replace("metadata:\n  name: ovzdusie", "metadata: {}"), "has no metadata.name", None),
        ("name that is not a slug", good.replace("name: ovzdusie", "name: Ovzdusie_1"), "is not a slug", None),
        ("broken yaml", good.replace("spec:\n  retention: 90d", "spec:\n retention: 90d\n  bad: ["), "does not parse as YAML", None),
        ("two manifests in one block", good.replace("  retention: 90d",
            "  retention: 90d\n---\napiVersion: joinedcontext.com/v1alpha1\nkind: Endpoint\nmetadata:\n  name: verejny\n"), None, None),
        ("second manifest is broken", good.replace("  retention: 90d",
            "  retention: 90d\n---\napiVersion: joinedcontext.com/v1alpha1\nkind: Wormhole\nmetadata:\n  name: verejny\n"),
         "kind 'Wormhole' is not declared", None),
        ("no manifest at all", "---\ntitle: P\n---\n\n# P\n\nProse.\n", "no manifest block was found", None),
        ("a template string is not the document", """---
title: P
---

# P

```yaml
spec:
  templates:
    - name: subscription
      template: |
        apiVersion: joinedcontext.com/v1alpha1
        kind: Subscription
```
""", "no manifest block was found", None),
        ("a fragment beside a manifest leaves the manifest checked", good.replace("  retention: 90d",
            "  retention: 90d\n---\nspec:\n  templates:\n    - template: |\n"
            "        apiVersion: joinedcontext.com/v1alpha1\n        kind: Wormhole\n"), None, None),
        ("kind table missing", good, "the kind table lives here", ""),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Development").mkdir()
        for name, body, expected, kinds_override in cases:
            page = root / KINDS_PAGE
            if kinds_override == "":
                page.unlink(missing_ok=True)
            else:
                page.write_text(kinds_override or kinds_page, encoding="utf-8")
            (root / "page.md").write_text(body, encoding="utf-8")
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")

        # the schema leg: a schema that forbids the spec the documentation prints must go red
        try:
            import json
            import jsonschema  # noqa: F401
        except ImportError:
            print("note: jsonschema is not installed, the schema leg of the self-test was skipped",
                  file=sys.stderr)
        else:
            schemas = root / "schemas"
            schemas.mkdir()
            (root / KINDS_PAGE).write_text(kinds_page, encoding="utf-8")
            (root / "page.md").write_text(good, encoding="utf-8")
            (schemas / "ContextSpace.json").write_text(json.dumps({
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["apiVersion", "kind", "metadata", "spec"],
                "properties": {"spec": {"type": "object", "required": ["retentionDays"],
                                        "additionalProperties": False,
                                        "properties": {"retentionDays": {"type": "integer"}}}},
            }), encoding="utf-8")
            os.environ["JC_SCHEMAS_DIR"] = str(schemas)
            found = check(root)
            if not any("fails its schema" in problem for problem in found):
                failures.append(f"schema leg: a manifest violating its schema was not reported, got {found}")
            else:
                print("schema leg ok: a manifest violating the published schema goes red")

            # An excerpt is exempt from the schema and from nothing else.
            excerpt = good.replace("```yaml", "```yaml excerpt")
            (root / "page.md").write_text(excerpt, encoding="utf-8")
            found = check(root)
            if found:
                failures.append(f"excerpt: an abbreviated manifest was still held to its schema, got {found}")
            (root / "page.md").write_text(
                excerpt.replace("kind: ContextSpace", "kind: Wormhole"), encoding="utf-8")
            if not any("is not declared" in problem for problem in check(root)):
                failures.append("excerpt: an excerpt with an undeclared kind was not reported")
            (root / "page.md").write_text(
                excerpt.replace("metadata:\n  name: ovzdusie", "metadata: {}"), encoding="utf-8")
            if not any("has no metadata.name" in problem for problem in check(root)):
                failures.append("excerpt: an excerpt with no metadata.name was not reported")

            # A kind on the pending list is exempt while it is genuinely unpublished, and the
            # entry itself is reported once the schema arrives.
            (root / "page.md").write_text(good, encoding="utf-8")
            pending_page = kinds_page + (
                f"\n### {PENDING_HEADING}\n\n- `Dashboard` — served by the Portal only.\n")
            (root / KINDS_PAGE).write_text(pending_page, encoding="utf-8")
            if any("fails its schema" not in p_ and "Dashboard" in p_ for p_ in check(root)):
                failures.append("pending list: a kind with no schema at all was still reported")
            (root / KINDS_PAGE).write_text(
                pending_page.replace("`Dashboard`", "`ContextSpace`"), encoding="utf-8")
            if not any(PENDING_HEADING in p_ for p_ in check(root)):
                failures.append("pending list: a kind whose schema has since appeared was not reported")
            else:
                print("pending list ok: an entry the platform has caught up with goes red")
            (root / KINDS_PAGE).write_text(kinds_page, encoding="utf-8")
            os.environ.pop("JC_SCHEMAS_DIR")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: an undeclared kind, a missing or non-slug name, unparsable YAML, a second manifest "
          "in the same block, a missing kind table, an empty corpus, an excerpt that is wrong "
          "about something a schema does not judge, and a stale pending-schema entry all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    if not os.getenv("JC_SCHEMAS_DIR"):
        print("note: JC_SCHEMAS_DIR is not set, so manifests are checked structurally and not "
              "against the published draft-07 schemas", file=sys.stderr)
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} manifest problem(s)", file=sys.stderr)
        return 1
    print("documented manifests ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
