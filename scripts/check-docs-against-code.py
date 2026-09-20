#!/usr/bin/env python3
"""What the docs assert about the code is checked against the code (T-2139, TS-19).

The seventeen checkers beside this one hold the documentation to itself: links resolve,
front matter is present, a requirement is traceable, a manifest validates. None of them
knows whether the thing a page names still exists. That is how `jcctl serve --mcp` stayed on
four pages after the command was never built, and how a page came to describe a security gap
as bounded by an environment variable nothing reads.

This checker takes a tree of the platform's own repositories and holds three kinds of claim
to it:

* **a repository path** — a backticked path that begins with one of our own top-level
  directories (`crates/`, `ui/src/`, `charts/`, …) or with a repository name must exist. A
  path inside somebody else's tree — a user's configuration repository, a container image,
  the legacy system — is not a claim about our code and is not checked;
* **an environment variable** — a `JC_*` or `PORTAL_*` name must be read somewhere in the
  tree. `USER_SIDE` lists the ones a user's own workload receives instead, each with the
  reason;
* **an operation name** — a `jc_*` name must exist in the tree. This is the operation
  registry and the metrics beside it (ADR-N-021).

`Decisions/` and `Research/` are read differently: a decision records what was decided and a
research page records what was looked at, both at a moment that has passed. Neither is a
description of the platform today, so the name legs skip them — that is what keeps an ADR
honest instead of rewritten. Their links and paths are still checked, because a path that
never existed was wrong when it was written too.

Point it at a directory holding checkouts named after the repositories:

    check-docs-against-code.py --code ../ [docs-root]
    JC_CODE_DIR=/tmp/code check-docs-against-code.py
    check-docs-against-code.py --selftest

Without a code tree it prints what would enable it and exits 0, the same way the OpenAPI leg
of `verify-openapi-snippets.py` does: a checker that cannot see the code must say so rather
than pass quietly.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import tempfile

REPOSITORIES = (
    "joinedcontext-platform",
    "joinedcontext-portal",
    "joinedcontext-deployment",
    "joinedcontext-conformance",
)

# A backticked path beginning with one of these is a claim about our own code. Everything
# else — `compute/src/lib.rs` in a user's pipeline repository, `conf/apisix.yaml` inside a
# container, `components/authz/...` in the legacy deployment — is not.
OUR_PREFIXES = (
    "crates/",
    "ui/src/",
    "ui/tests/",
    "charts/",
    "schemas/",
    "tests/",
    "scripts/",
) + tuple(f"{name}/" for name in REPOSITORIES)
# `deployment/…` is left out on purpose: `just dev-apply` assembles that directory from the
# component templates, so a page naming a file in it is describing a generated tree rather
# than a committed one, and this gate checks what is committed.

# The pages that describe a moment rather than the platform today.
HISTORY = ("Decisions", "Research")

# `JC_*` names a user's own workload receives, which our services never read.
USER_SIDE: dict[str, str] = {
    "JC_SOURCE_URL": "handed to a pipeline's compute container by its manifest "
    "(Architecture/08 §the compute step), never read by a service of ours",
    "JC_TARGET_URL": "the same, for where the compute step writes back",
}

SOURCE_SUFFIXES = (
    ".rs",
    ".ts",
    ".tsx",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".justfile",
    ".robot",
    ".rego",
)
SKIP_DIRECTORIES = {".git", "node_modules", "target", "dist", ".venv", "__pycache__"}

BACKTICKED_PATH = re.compile(
    r"`([A-Za-z0-9_.\-/]+\.(?:rs|ts|tsx|py|toml|yaml|yml|json|md|sh|robot|sql|rego|js))`"
)
ENVIRONMENT = re.compile(r"\b((?:JC|PORTAL)_[A-Z0-9_]{2,})\b")
# The trailing guard keeps a hyphenated name out: `jc_edge_app_air-quality-today` is a cookie
# name, and its head is not an operation that has to exist.
OPERATION = re.compile(r"\b(jc_[a-z][a-z0-9_]{2,})(?![-\w])")


def walk(root: pathlib.Path):
    """Every file under `root` that is not build output or somebody's cache."""
    for path in root.rglob("*"):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_file():
            yield path


def inventory(code: pathlib.Path, docs: pathlib.Path) -> tuple[set[str], str]:
    """Every path the code tree holds, and the text of every source file in it."""
    paths: set[str] = set()
    sources: list[str] = []
    roots = [(name, code / name) for name in REPOSITORIES if (code / name).is_dir()]
    roots.append(("docs", docs))
    for name, root in roots:
        for path in walk(root):
            relative = path.relative_to(root).as_posix()
            paths.add(relative)
            paths.add(f"{name}/{relative}")
            if path.suffix in SOURCE_SUFFIXES or path.name == "justfile":
                try:
                    sources.append(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue
    return paths, "\n".join(sources)


def is_history(relative: pathlib.PurePath) -> bool:
    return bool(relative.parts) and relative.parts[0] in HISTORY


def problems_of(
    relative: pathlib.PurePath, text: str, paths: set[str], code_text: str
) -> list[str]:
    bad: list[str] = []
    history = is_history(relative)
    for lineno, line in enumerate(text.splitlines(), 1):
        for claimed in BACKTICKED_PATH.findall(line):
            if not claimed.startswith(OUR_PREFIXES):
                continue
            if claimed in paths:
                continue
            bad.append(f"{relative}:{lineno}: no such file in any repository: {claimed}")

        if history:
            continue

        for name in ENVIRONMENT.findall(line):
            if name in USER_SIDE or name in code_text:
                continue
            bad.append(f"{relative}:{lineno}: nothing reads this variable: {name}")

        for name in OPERATION.findall(line):
            if name in code_text:
                continue
            bad.append(f"{relative}:{lineno}: no such operation or metric: {name}")
    return bad


def check(docs: pathlib.Path, code: pathlib.Path) -> list[str]:
    paths, code_text = inventory(code, docs)
    bad: list[str] = []
    for path in sorted(docs.rglob("*.md")):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        relative = path.relative_to(docs)
        bad.extend(
            problems_of(relative, path.read_text(encoding="utf-8"), paths, code_text)
        )
    return bad


def present(code: pathlib.Path) -> list[str]:
    return [name for name in REPOSITORIES if (code / name).is_dir()]


SAFE_PAGE = """---
title: A page that is true
---

# A page that is true

The router lives in `crates/context-gateway/src/app.rs` and the Portal form in
`ui/src/pages/endpoints/Form.tsx`. The gateway reads `JC_BROKER_URL` at start-up.
The assistant calls `jc_catalog_search`; a user's compute container receives `JC_SOURCE_URL`.
A pipeline of somebody else's lives in `compute/src/lib.rs`, which is their repository.
"""

STALE_PAGE = """---
title: A page that has gone stale
---

# A page that has gone stale

The command is `crates/jcctl/src/mcp.rs` and it reads `JC_MCP_SOCKET`.
Ask the assistant for `jc_model_validate`.
"""

HISTORY_PAGE = """---
title: A decision
---

# A decision

The configuration MCP was to be `jcctl serve --mcp` reading `JC_MCP_SOCKET`, exposing
`jc_model_validate`. It was never built; the Portal serves the configuration API instead.
"""


def selftest() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        docs = root / "docs"
        (docs / "Architecture").mkdir(parents=True)
        (docs / "Decisions").mkdir(parents=True)

        code = root / "code"
        gateway = code / "joinedcontext-platform" / "crates" / "context-gateway" / "src"
        gateway.mkdir(parents=True)
        (gateway / "app.rs").write_text(
            'let url = std::env::var("JC_BROKER_URL")?;\nconst TOOL: &str = "jc_catalog_search";\n',
            encoding="utf-8",
        )
        form = code / "joinedcontext-portal" / "ui" / "src" / "pages" / "endpoints"
        form.mkdir(parents=True)
        (form / "Form.tsx").write_text("export function Form() { return null; }\n", encoding="utf-8")

        (docs / "Architecture" / "true.md").write_text(SAFE_PAGE, encoding="utf-8")
        clean = check(docs, code)
        if clean:
            print("a true page was rejected:", *clean, sep="\n  ", file=sys.stderr)
            return 1

        (docs / "Architecture" / "true.md").unlink()
        (docs / "Architecture" / "stale.md").write_text(STALE_PAGE, encoding="utf-8")
        found = check(docs, code)
        wanted = ["no such file", "nothing reads this variable", "no such operation"]
        missing = [want for want in wanted if not any(want in problem for problem in found)]
        if missing:
            print(
                "a stale page got past the checker:",
                *missing,
                "what was found:",
                *found,
                sep="\n  ",
                file=sys.stderr,
            )
            return 1

        # The same sentences inside a decision: the names are history and only the path is
        # still a claim, because a path that never existed was wrong when it was written.
        (docs / "Architecture" / "stale.md").unlink()
        (docs / "Decisions" / "adr-n-021.md").write_text(HISTORY_PAGE, encoding="utf-8")
        history = check(docs, code)
        if any("nothing reads" in problem or "no such operation" in problem for problem in history):
            print("a decision was held to today's code:", *history, sep="\n  ", file=sys.stderr)
            return 1

        # And with no code tree at all the checker reports nothing rather than everything.
        if check(docs, root / "nowhere"):
            print("a missing code tree produced findings", file=sys.stderr)
            return 1

    print("check-docs-against-code selftest: ok")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_root", nargs="?", default=None)
    parser.add_argument("--code", default=os.environ.get("JC_CODE_DIR"))
    parser.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args(argv[1:])

    if arguments.selftest:
        return selftest()

    docs = (
        pathlib.Path(arguments.docs_root)
        if arguments.docs_root
        else pathlib.Path(__file__).resolve().parent.parent
    )
    if not arguments.code:
        print(
            "no code tree: set JC_CODE_DIR or pass --code with a directory holding "
            f"checkouts named {', '.join(REPOSITORIES)}; nothing was checked",
            file=sys.stderr,
        )
        return 0
    code = pathlib.Path(arguments.code)
    checkouts = present(code)
    if not checkouts:
        print(f"no repository checkout under {code}; nothing was checked", file=sys.stderr)
        return 0

    bad = check(docs, code)
    if bad:
        print(
            f"{len(bad)} claim(s) the code does not support:",
            *bad,
            sep="\n  ",
            file=sys.stderr,
        )
        return 1
    print(f"the docs agree with {', '.join(checkouts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
