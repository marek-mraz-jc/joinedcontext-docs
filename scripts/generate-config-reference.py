#!/usr/bin/env python3
"""The configuration reference is generated from the code that reads it (T-2140, OPS-27).

Every `JC_*` and `PORTAL_*` variable a service reads is found in that service's sources, and
its description is the rustdoc that names it — so the page cannot say something the code does
not, and a variable added without a word of explanation fails a lane instead of reaching an
operator as a name with no meaning.

    generate-config-reference.py [--write] [--selftest] [docs-root]

Without `--write` it checks: every variable the code reads is on the page, and every variable
the page names is read by the code. It is a coverage check rather than a byte comparison,
because CI reads the platform at a pinned tag: a page regenerated from `main` would otherwise
turn the lane red at whatever hour an unrelated push moved a sentence.

The code tree comes from `JC_CODE_DIR` (a directory holding `joinedcontext-platform` and
`joinedcontext-portal`, as `ci.yml` checks them out). Without it the check prints what would
enable it and passes, the same way `check-docs-against-code.py` does.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

PAGE = "Deployment/13-configuration-reference.md"

# One entry per service that reads its configuration from the environment: the section title,
# the repository and the source root its variables are read in, and the sentence that says
# what the service is.
# What the reconciler injects into a project's pipeline runner: read by a mapping, never by a
# service, and named here because jcctl validates them and would otherwise appear to read them.
INJECTED_INTO_A_RUN = ("JC_ORG_DOMAIN", "JC_SOURCE_SPACE", "JC_SPACE")

# Read for documentation alone: the manifest model reads no variable, and it is where the
# pipeline runner's injected environment is described.
DOC_ONLY = (("joinedcontext-platform", "crates/jc-core/src"),)

SERVICES = [
    (
        "Context Gateway",
        "joinedcontext-platform",
        "crates/context-gateway/src",
        "The enforcement point in front of every broker surface (`context-gateway`).",
    ),
    (
        "Portal",
        "joinedcontext-portal",
        "src",
        "The management application: the API, the embedded UI and the in-process reconciler.",
    ),
    (
        "Agent proxy",
        "joinedcontext-platform",
        "crates/agent-proxy/src",
        "The credential holder of a builder run (`jc-agent-proxy`): a workspace reaches the "
        "model, the forge and the context through it and holds none of their credentials.",
    ),
    (
        "Functions runtime",
        "joinedcontext-platform",
        "crates/functions/src",
        "The QuickJS runtime a generated application's functions run in (`jc-functions`).",
    ),
    (
        "jcctl",
        "joinedcontext-platform",
        "crates/jcctl/src",
        "The reconciler, as a CLI for an operator and as the library the Portal embeds.",
    ),
]

# A variable is read where its name is a string literal in the sources; it is *set* where the
# platform writes it into a workload it starts, which is a different contract (the pipeline
# runner's and a generated application's environment, documented with those).
LITERAL = re.compile(r'"((?:JC|PORTAL)_[A-Z0-9_]+)"')
INJECTED = re.compile(r'"name"\s*:\s*"((?:JC|PORTAL)_[A-Z0-9_]+)"')
MENTION = re.compile(r"(?:JC|PORTAL)_[A-Z0-9_]+")
DEFAULT = re.compile(r"default `([^`]+)`")
# The shapes of a name that holds, or points at, a credential.
SECRET = re.compile(r"(SECRET|TOKEN|_KEY$|_KEY_|PASSWORD|DATABASE_URL)")
# `JC_OIDC_TOKEN_URL` holds the address a token is asked for, not a token. An address is
# never the secret, whatever word its name contains — `JC_PORTAL_DATABASE_URL` excepted,
# because that one carries the password inside it.
ADDRESS = re.compile(r"_URL$")
# `JC_PORTAL_APPS_PULL_SECRET_NAME` names a Kubernetes Secret; the name is not the credential.
NAME_OF = re.compile(r"_NAME$")
# A line that logs, and a read of a variable on that same line. A secret is named in a log
# ("JC_PORTAL_COOKIE_KEY is unset") often and rightly; what must never happen is its value
# being read into one.
LOGS = re.compile(r"\b(tracing::(trace|debug|info|warn|error)!|println!|eprintln!|dbg!)")
READS = re.compile(r"(?:env::var|env::var_os|lookup|var|var_os)\s*\(\s*\"((?:JC|PORTAL)_[A-Z0-9_]+)\"")
PATH_TO_SECRET = re.compile(r"(_FILE|_PATH)$")
# Sentence end, with the abbreviations a rustdoc sentence really contains left alone.
SENTENCE = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<!\bcf)\.(?:\s|$)")


class Variable:
    """One environment variable, as the code shows it.

    The same name can mean two things in two services — `JC_OIDC_CLIENT_ID` is the gateway's
    client in one and the proxy's in another, with a different default — so the description is
    held per service, and a service that documents a variable nowhere borrows another's.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.services: set[str] = set()
        self.docs: dict[str, str] = {}
        self.doc = ""

    def about(self, service: str) -> "Variable":
        """This variable as one service documents it."""
        seen = Variable(self.name)
        seen.services = {service}
        seen.doc = self.docs.get(service, self.doc)
        return seen

    @property
    def secret(self) -> str:
        # A secret never has a default: nobody ships a credential in a chart. A name that
        # holds `TOKEN` and a default is a flag about a token (`JC_TRUST_EDGE_TOKEN`), not one.
        if self.default != "—":
            return "no"
        if ADDRESS.search(self.name) and self.name != "JC_PORTAL_DATABASE_URL":
            return "no"
        if NAME_OF.search(self.name):
            return "no"
        if PATH_TO_SECRET.search(self.name) and SECRET.search(self.name):
            return "a path to one"
        return "yes" if SECRET.search(self.name) else "no"

    @property
    def default(self) -> str:
        """The default this variable's own clause names, never a neighbour's.

        One doc block can introduce a whole group — the basemap block names four defaults —
        so the search starts at this variable's name and stops at the next variable's.
        """
        text = " ".join(self.doc.split())
        at = text.find(self.name)
        if at == -1:
            return "—"
        rest = text[at + len(self.name) :]
        following = MENTION.search(rest)
        if following:
            rest = rest[: following.start()]
        found = DEFAULT.search(rest)
        return f"`{found.group(1)}`" if found else "—"

    @property
    def sentence(self) -> str:
        """What the rustdoc says about this variable.

        The opening sentence when it names the variable, because that is the sentence written
        about it; otherwise the sentence that does name it, which is how a block introducing a
        group of variables explains each of them.
        """
        for bullet in bullets(self.doc):
            if self.name in bullet:
                return bullet
        text = " ".join(self.doc.split())
        if not text:
            return ""
        parts = [part.strip() for part in SENTENCE.split(text) if part.strip()]
        if not parts:
            return ""
        if self.name in parts[0]:
            return parts[0] + "."
        for part in parts:
            if self.name in part:
                return part + "."
        return parts[0] + "."


def bullets(doc: str) -> list[str]:
    """The bullets of a doc block, one line each.

    A module comment that lists its variables writes one bullet per variable, and gluing them
    into sentences would hand every one of them the same paragraph.
    """
    found: list[str] = []
    current = ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            if current:
                found.append(current)
            current = stripped[2:].strip()
        elif current and stripped:
            current += " " + stripped
        elif current:
            found.append(current)
            current = ""
    if current:
        found.append(current)
    return found


def sources(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Rust file of a service, tests excluded."""
    return [
        path
        for path in sorted(root.rglob("*.rs"))
        if "/tests/" not in str(path) and not path.name.startswith("test")
    ]


def without_tests(text: str) -> str:
    """The source up to its test module, which configures variables rather than reading them."""
    cut = text.find("#[cfg(test)]")
    return text if cut == -1 else text[:cut]


def doc_blocks(text: str) -> list[str]:
    """Every rustdoc block of a file that documents a thing, not an error.

    The doc of an error variant names the variable too — "`JC_ENVIRONMENT` names an overlay
    the repository does not hold" — but it describes what goes wrong, not what the variable is
    for, so a block whose item is an `#[error…]` attribute is left out.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("///") or stripped.startswith("//!"):
            current.append(stripped[3:].strip())
            continue
        if current and stripped and not stripped.startswith("#[error"):
            blocks.append("\n".join(current))
        if stripped:
            current = []
    if current:
        blocks.append("\n".join(current))
    return blocks


def better(block: str, against: tuple[str, bool] | None, name: str, configuration: bool) -> bool:
    """Whether `block` explains `name` better than the block already found.

    A field's own doc comment opens with the variable and is short; a function's doc mentions
    it somewhere in the middle of a paragraph about something else. Preferring the first over
    the second is what keeps `JC_ENVIRONMENT` from being described as "loads and indexes an
    organization repository".
    """
    if against is None:
        return True
    return rank(block, name, configuration) < rank(against[0], name, against[1])


def opens_with(text: str, name: str) -> bool:
    """Whether this text is about the variable rather than mentioning it in passing.

    `\`JC_SPACE\`, \`JC_SPACE_2\`, … are the space segment of each output` is written about
    the variable; `\`env("JC_SPACE")\` yields the name` is written about a parser that happens
    to use it as an example.
    """
    return text.lstrip("`").startswith(name)


def rank(block: str, name: str, configuration: bool) -> tuple[int, int, int]:
    """How well a doc block explains a variable.

    A configuration module first — that is the file whose job is to say what a variable does,
    and every other mention is a use of the value. Then a block written about this variable:
    one that opens with it, or that gives it a bullet of its own. Then the shortest, which is
    a field's own comment rather than a function's.
    """
    text = " ".join(block.split())
    first = SENTENCE.split(text)[0] if text else ""
    about = opens_with(first, name) or any(opens_with(b, name) for b in bullets(block))
    return (0 if configuration else 1, 0 if about else 1, len(text))


def scan(code_dir: pathlib.Path) -> tuple[dict[str, Variable], dict[str, Variable], list[str]]:
    """Every variable the services read and every one they inject, each with its rustdoc."""
    variables: dict[str, Variable] = {}
    written: dict[str, Variable] = {}
    documentation: dict[str, tuple[str, bool]] = {}
    per_service: dict[tuple[str, str], tuple[str, bool]] = {}
    missing: list[str] = []

    for repo, relative in DOC_ONLY:
        root = code_dir / repo / relative
        if not root.is_dir():
            continue
        for path in sources(root):
            text = without_tests(path.read_text(encoding="utf-8"))
            for block in doc_blocks(text):
                for name in set(MENTION.findall(block)):
                    # The runner's injected names are described here on purpose: every other
                    # mention of them is a validation refusing a mapping that misuses one.
                    if name in INJECTED_INTO_A_RUN:
                        if better(block, documentation.get(name), name, True):
                            documentation[name] = (block, True)
                    elif better(block, documentation.get(name), name, False):
                        documentation[name] = (block, False)

    for service, repo, relative, _ in SERVICES:
        root = code_dir / repo / relative
        if not root.is_dir():
            missing.append(f"{repo}/{relative}")
            continue
        for path in sources(root):
            text = without_tests(path.read_text(encoding="utf-8"))
            injected = set(INJECTED.findall(text))
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("//"):
                    continue
                for name in LITERAL.findall(line):
                    # A prefix (`JC_SPACE_`) is a family of names, not a variable.
                    if name.endswith("_"):
                        continue
                    if name in injected and '"name"' in line:
                        written.setdefault(name, Variable(name)).services.add(service)
                        continue
                    if name in INJECTED_INTO_A_RUN:
                        written.setdefault(name, Variable(name)).services.add(service)
                        continue
                    variables.setdefault(name, Variable(name)).services.add(service)
            configuration = path.name == "config.rs"
            for block in doc_blocks(text):
                for name in set(MENTION.findall(block)):
                    if better(block, documentation.get(name), name, configuration):
                        documentation[name] = (block, configuration)
                    if better(block, per_service.get((service, name)), name, configuration):
                        per_service[(service, name)] = (block, configuration)

    # The runner's three are injected whether or not a service happens to name one: they are
    # the mapping author's contract, and the renderer writes them into every pipeline.
    for name in INJECTED_INTO_A_RUN:
        written.setdefault(name, Variable(name)).services.add("pipeline runner")

    for name, variable in list(variables.items()) + list(written.items()):
        found = documentation.get(name)
        variable.doc = found[0] if found else ""
        variable.docs = {
            service: block
            for (service, held), (block, _) in per_service.items()
            if held == name and service in variable.services
        }
    return variables, written, missing


def logged_secrets(code_dir: pathlib.Path, variables: dict[str, Variable]) -> list[str]:
    """Every place a secret's value is read straight into a log line (OPS-27, SEC).

    The read and the log have to be on one line for this to see it, so it is a tripwire on the
    obvious mistake rather than a taint analysis; a value that travels through a variable is
    covered by the `Debug` redaction each service tests for itself.
    """
    found = []
    secrets = {name for name, variable in variables.items() if variable.secret == "yes"}
    for _, repo, relative, _ in SERVICES:
        root = code_dir / repo / relative
        if not root.is_dir():
            continue
        for path in sources(root):
            text = without_tests(path.read_text(encoding="utf-8"))
            for number, line in enumerate(text.splitlines(), start=1):
                if not LOGS.search(line):
                    continue
                for name in READS.findall(line):
                    if name in secrets:
                        found.append(f"{repo}/{path.relative_to(root.parent)}:{number}: {name}")
    return sorted(found)


def page_variables(text: str) -> set[str]:
    """Every variable the page documents: the first cell of a row of one of its tables."""
    found = set()
    for line in text.splitlines():
        if line.startswith("| `"):
            cell = line.split("|")[1].strip().strip("`")
            if MENTION.fullmatch(cell):
                found.add(cell)
    return found


def render(variables: dict[str, Variable], written: dict[str, Variable]) -> str:
    """The page, generated."""
    lines = [
        "---",
        "sidebar_position: 13",
        'title: "Configuration Reference"',
        "description: Every environment variable the platform's services read, with its "
        "default and whether it holds a secret, generated from the code that reads it.",
        "---",
        "",
        "# Configuration Reference",
        "",
        "Every environment variable the platform's services read, generated from the code that",
        "reads it by `scripts/generate-config-reference.py` (OPS-27). Do not edit this page by",
        "hand: a change belongs in the rustdoc of the field that reads the variable, and CI",
        "fails when a variable is read and not here, or here and read by nothing.",
        "",
        "A variable with no default is one the service cannot invent. Where the service can run",
        "without it, the sentence says what it does instead — usually refusing the routes that",
        "need it, never falling back to something weaker. A variable marked as a secret is",
        "resolved from a `secretRef` by the deployment and is never written into a manifest, an",
        "image, a log or a task; one marked *a path to one* names a file the value is mounted",
        "into, which is how a credential reaches a pod without passing through its environment.",
        "",
    ]
    for index, (service, _, _, about) in enumerate(SERVICES, start=1):
        owned = sorted(
            variable for variable in variables.values() if service in variable.services
        )
        lines += [f"## {index}. {service}", "", about, ""]
        if not owned:
            lines += ["This service reads no environment variable.", ""]
            continue
        lines += ["| Variable | Default | Secret | What it is |", "|---|---|---|---|"]
        for variable in owned:
            here = variable.about(service)
            sentence = here.sentence.replace("|", "\\|") or "—"
            lines.append(f"| `{here.name}` | {here.default} | {here.secret} | {sentence} |")
        lines.append("")
    index = len(SERVICES) + 1
    lines += [
        f"## {index}. Injected into a workload",
        "",
        "These the platform sets rather than reads: the environment a pipeline's runner and a",
        "generated application are started with. They are a contract with whoever writes a",
        "mapping or an application, not something an operator configures, and none of them ever",
        "carries a credential — a run's ticket is minted per run and is not a stored secret.",
        "",
        "| Variable | What it is |",
        "|---|---|",
    ]
    for variable in sorted(written.values()):
        sentence = variable.sentence.replace("|", "\\|") or "—"
        lines.append(f"| `{variable.name}` | {sentence} |")
    lines += [
        "",
        "## Related",
        "",
        "- [Global & Component Configuration](03-configuration.md) — the Helm values that set",
        "  these variables on each component.",
        "- [Security Hardening](08-security-hardening.md) — where the secrets come from, and",
        "  what a `secretRef` resolves to.",
        "- [Installation](02-installation.md) — the step that sets them for the first time.",
        "",
    ]
    return "\n".join(lines)


def sort_key(variable: Variable) -> str:
    return variable.name


Variable.__lt__ = lambda self, other: self.name < other.name  # noqa: E731


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_root", nargs="?", default=".")
    parser.add_argument("--write", action="store_true", help="regenerate the page")
    parser.add_argument("--selftest", action="store_true")
    arguments = parser.parse_args(argv[1:])

    if arguments.selftest:
        return selftest()

    docs = pathlib.Path(arguments.docs_root)
    code = os.environ.get("JC_CODE_DIR", "")
    if not code or not pathlib.Path(code).is_dir():
        print(
            "JC_CODE_DIR is not set, so the configuration reference is not checked against the "
            "code. Set it to a directory holding joinedcontext-platform and joinedcontext-portal.",
        )
        return 0

    variables, written, missing = scan(pathlib.Path(code))
    if missing:
        print(
            "these source trees are not in JC_CODE_DIR, so the reference cannot be checked:",
            *missing,
            sep="\n  ",
            file=sys.stderr,
        )
        return 1

    page = docs / PAGE
    if arguments.write:
        page.write_text(render(variables, written), encoding="utf-8")
        print(f"{PAGE}: {len(variables)} read, {len(written)} injected")
        return 0

    if not page.is_file():
        print(f"{PAGE} does not exist; run with --write", file=sys.stderr)
        return 1

    logged = logged_secrets(pathlib.Path(code), variables)
    for place in logged:
        print(f"{place} reads a secret straight into a log line", file=sys.stderr)

    documented = page_variables(page.read_text(encoding="utf-8"))
    known = set(variables) | set(written)
    undocumented = sorted(known - documented)
    invented = sorted(documented - known)
    for name in undocumented:
        where = ", ".join(sorted((variables.get(name) or written[name]).services))
        print(f"{name} is read by {where} and is not in {PAGE}", file=sys.stderr)
    for name in invented:
        print(f"{name} is in {PAGE} and no service reads it", file=sys.stderr)
    if undocumented or invented or logged:
        print(
            f"\n{len(undocumented) + len(invented) + len(logged)} configuration reference "
            "problem(s); regenerate with --write",
            file=sys.stderr,
        )
        return 1
    print(
        f"configuration reference ok: {len(variables)} variable(s) read, {len(written)} injected"
    )
    return 0


SELFTEST_SOURCE = '''
/// The address to listen on (`JC_DEMO_BIND`, default `0.0.0.0:8080`).
pub bind: SocketAddr,
/// The token it writes with (`JC_DEMO_TOKEN`), read from `JC_DEMO_TOKEN_FILE`.
pub token: String,

fn from_env(lookup: impl Fn(&str) -> Option<String>) {
    let bind = lookup("JC_DEMO_BIND");
    let token = lookup("JC_DEMO_TOKEN");
    let file = lookup("JC_DEMO_TOKEN_FILE");
    let injected = json!({ "name": "JC_DEMO_INJECTED", "value": "x" });
    tracing::warn!("JC_DEMO_TOKEN is unset, carrying on");
}

#[cfg(test)]
mod tests {
    fn only_a_test() { lookup("JC_DEMO_ONLY_IN_A_TEST"); }
}
'''


def selftest() -> int:
    """The scanner reads a source the way the checker needs, and the checker goes red."""
    import tempfile

    with tempfile.TemporaryDirectory() as temporary:
        root = pathlib.Path(temporary) / "joinedcontext-platform" / "crates/context-gateway/src"
        root.mkdir(parents=True)
        (root / "config.rs").write_text(SELFTEST_SOURCE, encoding="utf-8")
        for _, repo, relative, _ in SERVICES:
            (pathlib.Path(temporary) / repo / relative).mkdir(parents=True, exist_ok=True)
        variables, written, missing = scan(pathlib.Path(temporary))

        problems = []
        if missing:
            problems.append(f"the empty trees were reported missing: {missing}")
        names = set(variables)
        if names != {"JC_DEMO_BIND", "JC_DEMO_TOKEN", "JC_DEMO_TOKEN_FILE"}:
            problems.append(f"the scanner read {sorted(names)}")
        if "JC_DEMO_BIND" in names and variables["JC_DEMO_BIND"].default != "`0.0.0.0:8080`":
            problems.append("the default was not read out of the rustdoc")
        if "JC_DEMO_TOKEN" in names and variables["JC_DEMO_TOKEN"].secret != "yes":
            problems.append("a token was not called a secret")
        if Variable("JC_DEMO_PULL_SECRET_NAME").secret != "no":
            problems.append("the name of a Secret was called a secret")
        if (
            "JC_DEMO_TOKEN_FILE" in names
            and variables["JC_DEMO_TOKEN_FILE"].secret != "a path to one"
        ):
            problems.append("a secret file was not called a path to a secret")
        if "JC_DEMO_BIND" in names and "JC_DEMO_BIND" not in variables["JC_DEMO_BIND"].sentence:
            problems.append(f"the sentence was {variables['JC_DEMO_BIND'].sentence!r}")

        if set(written) != {"JC_DEMO_INJECTED", *INJECTED_INTO_A_RUN}:
            problems.append(f"the injected set was {sorted(written)}")
        if logged_secrets(pathlib.Path(temporary), variables):
            problems.append("naming a secret in a log line was read as leaking it")
        leaky = root / "leaky.rs"
        leaky.write_text(
            'fn f() { tracing::info!("token={}", lookup("JC_DEMO_TOKEN").unwrap()); }',
            encoding="utf-8",
        )
        leaked, _, _ = scan(pathlib.Path(temporary))
        if not logged_secrets(pathlib.Path(temporary), leaked):
            problems.append("a secret read into a log line was not noticed")
        leaky.unlink()

        rendered = render(variables, written)
        if page_variables(rendered) != names | set(written):
            problems.append("a page generated here does not pass its own check")
        if page_variables(rendered.replace("| `JC_DEMO_BIND` |", "| `JC_GONE` |")) == names:
            problems.append("a page naming a variable nothing reads was not noticed")

    if problems:
        print("generate-config-reference selftest failed:", *problems, sep="\n  ", file=sys.stderr)
        return 1
    print("generate-config-reference: selftest passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
