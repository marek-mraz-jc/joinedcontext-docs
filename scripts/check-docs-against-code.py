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
  registry and the metrics beside it (ADR-N-021);
* **a problem type** — a printed `https://joinedcontext.com/errors/{slug}` must have its slug
  as a string in the tree, and a `…/problems/{slug}` must be there whole. A client branches on
  `type`, so a slug nothing produces sends it down a branch that never runs; this is how
  `https://joinedcontext.com/problems/forbidden` stood on an API page while every refusal of
  that kind says `…/errors/forbidden` (TS-19, T-2148).

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
# Which repositories a *bare* path — one with no repository name in front of it — can live in.
# A claim is judged only when every repository that could hold it is checked out: `ci.yml`
# fetches the two public ones, so `tests/etsi-ttf/expected_failures.json` (conformance) would
# otherwise be reported as missing when it exists and simply was not fetched (T-2141).
BARE_PREFIX_OWNERS = {
    "crates/": ("joinedcontext-platform",),
    "ui/src/": ("joinedcontext-portal",),
    "ui/tests/": ("joinedcontext-portal",),
    "charts/": ("joinedcontext-deployment",),
    "schemas/": ("joinedcontext-platform",),
    "tests/": (
        "joinedcontext-conformance",
        "joinedcontext-deployment",
        "joinedcontext-platform",
        "joinedcontext-portal",
    ),
    "scripts/": (
        "joinedcontext-conformance",
        "joinedcontext-deployment",
        "joinedcontext-platform",
    ),
}

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
    "JC_ME_URL": "handed to a fullstack application's backend by the reconciler beside "
    "JC_ENDPOINT_URL (Architecture/16 §13, AP-109); the application reads it, not a service of ours",
    "JC_PARAM_": "the prefix of a project parameter a mapping reads as env(\"JC_PARAM_<NAME>\") "
    "(CC-88); the project's own Bloblang reads it, not a service of ours",
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
# The `type` of a problem document. `{slug}` itself is a page explaining the form, not a claim
# about one refusal, and the pattern does not match it.
PROBLEM_TYPE = re.compile(r"https://joinedcontext\.com/(errors|problems)/([a-z0-9][a-z0-9-]*)")


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


# Which repository a page describes, for the variable leg. A variable is read wherever it is
# read, and the checker cannot tell "nothing reads this" from "the tree that reads it was not
# fetched": `ci.yml` fetches the platform and the Portal, so `JC_NETPOL_SETTLE`
# (`joinedcontext-deployment/scripts/smoke.sh`) and every variable of the conformance suites
# read as unread claims, nineteen of them at once. The path leg already answers this with
# `BARE_PREFIX_OWNERS`; the same rule, keyed by the page, because a page about the conformance
# suites names the conformance suites' variables (T-2141, T-2366).
PAGE_OWNERS: dict[str, tuple[str, ...]] = {
    "Testing/02-conformance-tests.md": ("joinedcontext-conformance",),
    "Testing/03-frontend-and-e2e-tests.md": ("joinedcontext-conformance", "joinedcontext-portal"),
    "Testing/05-deployment-and-performance-tests.md": (
        "joinedcontext-conformance",
        "joinedcontext-deployment",
    ),
    "Testing/06-security-tests.md": ("joinedcontext-conformance", "joinedcontext-platform"),
    "Deployment/04-components-and-addons.md": ("joinedcontext-deployment",),
    "Deployment/08-security-hardening.md": ("joinedcontext-deployment",),
}


def variables_judgeable(relative: pathlib.PurePath, checkouts: frozenset[str]) -> bool:
    """Whether this page's variables can be judged at all from the trees that were fetched."""
    owners = PAGE_OWNERS.get(str(relative))
    return owners is None or all(owner in checkouts for owner in owners)


def judgeable(claimed: str, checkouts: frozenset[str]) -> bool:
    """Whether a missing path is a finding or simply a repository nobody fetched.

    A path that names its own repository (`joinedcontext-conformance/tests/…`) is judged when
    that repository is there. A bare one is judged only when every repository that could hold
    it is there; otherwise the checker has not read the tree that would prove it (T-2141).
    """
    for name in REPOSITORIES:
        if claimed.startswith(f"{name}/"):
            return name in checkouts
    for prefix, owners in BARE_PREFIX_OWNERS.items():
        if claimed.startswith(prefix):
            return all(owner in checkouts for owner in owners)
    return True


def problems_of(
    relative: pathlib.PurePath,
    text: str,
    paths: set[str],
    code_text: str,
    checkouts: frozenset[str] = frozenset(REPOSITORIES),
) -> list[str]:
    bad: list[str] = []
    history = is_history(relative)
    for lineno, line in enumerate(text.splitlines(), 1):
        for claimed in BACKTICKED_PATH.findall(line):
            if not claimed.startswith(OUR_PREFIXES):
                continue
            if claimed in paths:
                continue
            if not judgeable(claimed, checkouts):
                continue
            bad.append(f"{relative}:{lineno}: no such file in any repository: {claimed}")

        if history:
            continue

        for name in ENVIRONMENT.findall(line):
            if name in USER_SIDE or name in code_text:
                continue
            if not variables_judgeable(relative, checkouts):
                continue
            bad.append(f"{relative}:{lineno}: nothing reads this variable: {name}")

        for name in OPERATION.findall(line):
            if name in code_text:
                continue
            bad.append(f"{relative}:{lineno}: no such operation or metric: {name}")

        for family, slug in PROBLEM_TYPE.findall(line):
            # The `errors` family is built as `format!(".../errors/{slug}")`, so the slug is
            # what a tree can be searched for; the `problems` family is written whole where it
            # is produced, and is looked up whole.
            found = (
                f"https://joinedcontext.com/{family}/{slug}" in code_text
                if family == "problems"
                else f'"{slug}"' in code_text
            )
            if not found:
                bad.append(
                    f"{relative}:{lineno}: nothing answers this problem type: "
                    f"https://joinedcontext.com/{family}/{slug}"
                )
    return bad


def check(docs: pathlib.Path, code: pathlib.Path) -> list[str]:
    paths, code_text = inventory(code, docs)
    checkouts = frozenset(present(code))
    bad: list[str] = []
    for path in sorted(docs.rglob("*.md")):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        relative = path.relative_to(docs)
        bad.extend(
            problems_of(
                relative,
                path.read_text(encoding="utf-8"),
                paths,
                code_text,
                checkouts,
            )
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
A refusal is `https://joinedcontext.com/errors/forbidden`, and a draft that moved under the
request is `https://joinedcontext.com/problems/draft-conflict`.
"""

STALE_PAGE = """---
title: A page that has gone stale
---

# A page that has gone stale

The command is `crates/jcctl/src/mcp.rs` and it reads `JC_MCP_SOCKET`.
Ask the assistant for `jc_model_validate`.
A refusal is `https://joinedcontext.com/problems/forbidden`.
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
            'let url = std::env::var("JC_BROKER_URL")?;\nconst TOOL: &str = "jc_catalog_search";\n'
            'let slug = "forbidden";\n'
            'let conflict = "https://joinedcontext.com/problems/draft-conflict";\n',
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
        wanted = [
            "no such file",
            "nothing reads this variable",
            "no such operation",
            "nothing answers this problem type",
        ]
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

        # A path that lives in a repository nobody fetched is unchecked, not missing: CI
        # fetches platform and portal only, and `tests/etsi-ttf/…` is the conformance
        # repository's (T-2141). With every owner present the same claim is a finding again.
        (docs / "Decisions" / "adr-n-021.md").unlink()
        (docs / "Architecture" / "elsewhere.md").write_text(
            "---\ntitle: A page about another repository\n---\n\n"
            "# A page about another repository\n\n"
            "The expected failures live in `tests/etsi-ttf/expected_failures.json`.\n",
            encoding="utf-8",
        )
        if any("no such file" in problem for problem in check(docs, code)):
            print(
                "a path in a repository that was never fetched was called missing",
                file=sys.stderr,
            )
            return 1
        for name in REPOSITORIES:
            (code / name).mkdir(parents=True, exist_ok=True)
        if not any("no such file" in problem for problem in check(docs, code)):
            print(
                "with every repository present a missing path stopped being a finding",
                file=sys.stderr,
            )
            return 1
        (docs / "Architecture" / "elsewhere.md").unlink()

        # The same rule for a variable, keyed by the page: `Deployment/08` describes the
        # deployment repository, so `JC_NETPOL_SETTLE` is unchecked while that tree is absent
        # and a finding once it is there (T-2141, T-2366).
        page = docs / "Deployment" / "08-security-hardening.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            "---\ntitle: Security hardening\n---\n\n# Security hardening\n\n"
            "The settle window is `JC_NETPOL_SETTLE` seconds.\n",
            encoding="utf-8",
        )
        deployment = code / "joinedcontext-deployment"
        present_before = deployment.is_dir()
        if present_before:
            deployment.rename(code / "put-aside")
        if any("JC_NETPOL_SETTLE" in problem for problem in check(docs, code)):
            print("a variable of a repository nobody fetched was called unread", file=sys.stderr)
            return 1
        if present_before:
            (code / "put-aside").rename(deployment)
        else:
            deployment.mkdir()
        if not any("JC_NETPOL_SETTLE" in problem for problem in check(docs, code)):
            print(
                "with its repository present an unread variable stopped being a finding",
                file=sys.stderr,
            )
            return 1
        page.unlink()

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
