#!/usr/bin/env python3
"""The documentation holds no secret, no live host and no real person (T-2146, OPS-27).

These pages are written to be published. Everything in them that looks like a place or a
person therefore has to be one that cannot be reached: a documentation domain, a
documentation address range, and the demo accounts the deployment itself creates. A page
that names the running cluster is a page that tells a stranger where to knock; one that
names an address at a real organisation is one that can reach somebody who never agreed to
be an example.

What fails:

* a routable IPv4 literal — anything outside the documentation ranges of RFC 5737, the
  private ranges of RFC 1918, loopback, link-local, the unspecified and broadcast
  addresses, and the shared range of RFC 6598;
* `sslip.io` and the other wildcard-DNS hosts, which resolve to whatever address is spelled
  in front of them and are how a dev node gets into a page by accident;
* a complete JSON Web Token — three base64url parts, none of them elided;
* a credential that names its own kind: a GitHub token, an OpenAI key, a Slack token, an
  AWS access key id, a PEM private key block;
* an e-mail address whose domain is not a documentation domain and is not one of the demo
  accounts below.

`ALLOWED` is the list of the exceptions, each with the reason it is one. It is a constant
in this file rather than a configuration page, so adding to it is a change somebody reviews.

    check-examples-are-safe.py [docs-root]
    check-examples-are-safe.py --selftest
"""

from __future__ import annotations

import ipaddress
import pathlib
import re
import sys
import tempfile

# The domains an example may name. `.example` and the RFC 2606 names are reserved for
# documentation; `.invalid` and `.test` can never be registered; `.local` is mDNS and
# `service.joinedcontext.local` is what a service principal of ours is named after.
DOC_DOMAIN_SUFFIXES = (
    ".example.com",
    ".example.net",
    ".example.org",
    ".example",
    ".invalid",
    ".test",
    ".local",
    ".localhost",
)
DOC_DOMAINS = {"example.com", "example.net", "example.org"}

# The two accounts `DEMO.md` creates in the `dev` realm. They are named in the runbooks
# because an operator has to type them; the password never appears in a docs page and the
# secret-shape rules below are what keeps it out.
DEMO_ACCOUNTS = {"demo.steward@hel.fi", "demo.viewer@hel.fi"}

# Exceptions, each with the reason. A value here is exempt only on the page that is named.
ALLOWED: dict[tuple[str, str], str] = {
    (
        "Deployment/08-security-hardening.md",
        "1.1.1.1",
    ): "the egress probe has to dial a host that is actually reachable: a documentation "
    "address times out whether or not egress is blocked, which would report 'enforced' "
    "for a cluster that enforces nothing",
}

IPV4 = re.compile(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3})(?![\w.])")
# `CIM 009 clause 4.3.6.5` is four dotted numbers and is not an address. The specifications
# this platform implements are cited by clause on nearly every page, so the reference words
# in front of one are what tells the two apart.
CITATION = re.compile(r"\b(?:clauses?|sections?|chapter|annex|rev|version|RFC|CIM\s*009)\b|§", re.I)
WILDCARD_DNS = re.compile(r"\b(?:sslip\.io|nip\.io|xip\.io|traefik\.me|localtest\.me)\b")
# Three base64url parts. An elided example writes `…` or `...` inside or after a part, and
# is a template rather than a token.
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
CREDENTIALS = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}"
    r"|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9]{20,}"
    r"|xox[abposr]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_-]{30,})\b"
)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# The domain is matched case-sensitively in lower case, so a JSON member such as
# `Locations@iot.navigationLink` (SensorThings) is not read as an address.
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}\b")


def documentation_address(raw: str) -> bool:
    """Whether an IPv4 literal is one that can never reach anybody."""
    try:
        address = ipaddress.IPv4Address(raw)
    except ipaddress.AddressValueError:
        # Not an address at all — a version number, a clause reference such as `4.3.6.5`.
        return True
    return (
        address.is_private  # RFC 1918, loopback, link-local, the unspecified address
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or address in ipaddress.IPv4Network("192.0.2.0/24")  # RFC 5737 TEST-NET-1
        or address in ipaddress.IPv4Network("198.51.100.0/24")  # TEST-NET-2
        or address in ipaddress.IPv4Network("203.0.113.0/24")  # TEST-NET-3
        or address in ipaddress.IPv4Network("100.64.0.0/10")  # RFC 6598
        or address == ipaddress.IPv4Address("255.255.255.255")
    )


def documentation_domain(domain: str) -> bool:
    domain = domain.lower().rstrip(".")
    return domain in DOC_DOMAINS or domain.endswith(DOC_DOMAIN_SUFFIXES)


def problems_of(relative: str, text: str) -> list[str]:
    bad: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):

        def report(value: str, why: str) -> None:
            if ALLOWED.get((relative, value)) is None:
                bad.append(f"{relative}:{lineno}: {why}: {value}")

        for match in IPV4.finditer(line):
            # A specification clause is four dotted numbers too. The citation in front of it
            # is what tells the two apart, and it is looked for only before the match, so a
            # page that cites a clause and then names an address is still reported.
            if CITATION.search(line[: match.start()]):
                continue
            if not documentation_address(match.group(1)):
                report(match.group(1), "a routable address; use 192.0.2.0/24 (RFC 5737)")

        for host in WILDCARD_DNS.findall(line):
            report(host, "a wildcard-DNS host names a live node; use example.org")

        for token in JWT.findall(line):
            report(token[:16] + "…", "a complete JSON Web Token; elide it with `…`")

        for credential in CREDENTIALS.findall(line):
            report(credential[:8] + "…", "a credential; use a secretRef name")

        if PRIVATE_KEY.search(line):
            report("PEM", "a private key block")

        for address in EMAIL.findall(line):
            _, _, domain = address.rpartition("@")
            if documentation_domain(domain) or address.lower() in DEMO_ACCOUNTS:
                continue
            report(address, "an address at a real organisation; use example.org")
    return bad


def check(root: pathlib.Path) -> list[str]:
    bad: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if any(part in {"node_modules", ".git"} for part in path.parts):
            continue
        bad.extend(problems_of(str(path.relative_to(root)), path.read_text(encoding="utf-8")))
    return bad


SAFE_CORPUS = """---
title: A safe page
---

# A safe page

The gateway answers at `https://portal.example.org/api/v1/projects/helsinki/endpoints`.
An operator signs in as `demo.steward@hel.fi` and a colleague at `aino.virtanen@example.org`.
The node sits behind `192.0.2.10`, the pod network is `10.42.2.18`, and the health probe
dials `127.0.0.1:8080`. CIM 009 clause 4.3.6.5 names the tenant member.

```bash
curl -H 'Authorization: Bearer eyJhbGciOi…' https://portal.example.org/api/v1/health
```

The signing key is named by `secretRef: { name: gateway-signing, key: private }`.
"""

UNSAFE_CORPUS = """---
title: An unsafe page
---

# An unsafe page

The cluster answers at `https://2.28.67.127.sslip.io/api/v1/health` from `2.28.67.127`.
Write to `jana.kovacova@banskabystrica.sk` when the probe fails.

```bash
curl -H 'Authorization: Bearer eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJqYW5hIn0.c2lnbmF0dXJlLWhlcmU' \\
  -H 'X-Forge-Token: ghp_0123456789abcdefghijklmnopqrstuvwxyz' https://203.0.113.9/api
```

```text
-----BEGIN RSA PRIVATE KEY-----
```
"""


def selftest() -> int:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        (root / "safe.md").write_text(SAFE_CORPUS, encoding="utf-8")
        clean = check(root)
        if clean:
            print("the safe corpus was rejected:", *clean, sep="\n  ", file=sys.stderr)
            return 1

        (root / "safe.md").unlink()
        (root / "unsafe.md").write_text(UNSAFE_CORPUS, encoding="utf-8")
        found = check(root)
        wanted = [
            "a wildcard-DNS host",
            "a routable address",
            "an address at a real organisation",
            "a complete JSON Web Token",
            "a credential",
            "a private key block",
        ]
        missing = [want for want in wanted if not any(want in problem for problem in found)]
        if missing:
            print(
                "the unsafe corpus got past the checker:",
                *missing,
                "what was found:",
                *found,
                sep="\n  ",
                file=sys.stderr,
            )
            return 1

        # `203.0.113.9` is TEST-NET-3 and must not be among the findings: a checker that
        # rejects the addresses the pages are told to use is a checker nobody can satisfy.
        if any("203.0.113.9" in problem for problem in found):
            print("a documentation address was reported", file=sys.stderr)
            return 1

    print("check-examples-are-safe selftest: ok")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    root = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
    bad = check(root)
    if bad:
        print(
            f"{len(bad)} example(s) name something real:",
            *bad,
            sep="\n  ",
            file=sys.stderr,
        )
        return 1
    print(f"examples are safe in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
