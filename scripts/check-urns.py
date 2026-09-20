#!/usr/bin/env python3
"""Every concrete entity URN in the documentation must satisfy PF-42 (ADR 001, T-0100).

`urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}` — exactly four segments, a PascalCase
type, a dotted lowercase organization domain, a slug space and an RFC 8141 local id.
Placeholders (`{Type}`, `{orgDomain}`, `…`, a trailing `"` or `+`) are skipped, so a
template such as `urn:ngsi-ld:AirQualityObserved:banskabystrica.sk:ovzdusie:` inside a
string concatenation is accepted, and so is a Bloblang `%v` in place of a segment: a
pipeline mints its ids with `"urn:ngsi-ld:%v:%v:%v:%v".format(…)` (PF-44). A random UUID
in an intermediate segment is not a placeholder: it fails the domain and space patterns
and is reported.

    check-urns.py [docs-root]
    check-urns.py --selftest
"""

from __future__ import annotations

import pathlib
import re
import sys
import tempfile

URN = re.compile(r"urn:ngsi-ld:[^\s`\"'|),]*")
TYPE = re.compile(r"^[A-Z][A-Za-z0-9]{1,63}$")
DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$")
SPACE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
LOCAL = re.compile(r"^[A-Za-z0-9._~-]{1,128}$")
# One Bloblang format verb stands for exactly one segment, so the four-segment rule still
# holds over a template that fills some of them in (PF-44).
FORMAT_VERB = "%v"


def problems_of(path: pathlib.Path, text: str) -> list[str]:
    bad: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for raw in URN.findall(line):
            if "{" in raw or "…" in raw or "..." in raw or "*" in raw:
                continue
            urn = raw.rstrip(".,;").replace("\\\\.", ".").replace("\\.", ".")
            segs = urn[len("urn:ngsi-ld:"):].split(":")
            # a bare mention of the prefix ("the urn:ngsi-ld: scheme") is prose, not an example
            if len(segs) < 2:
                continue
            # a trailing empty segment means the id is built by concatenation in an example
            trailing = len(segs) == 4 and segs[3] == ""

            def segment(index: int, pattern: re.Pattern[str]) -> bool:
                return segs[index] == FORMAT_VERB or bool(pattern.match(segs[index]))

            if len(segs) != 4 or not segment(0, TYPE) or not segment(1, DOMAIN) \
               or not segment(2, SPACE) \
               or not (trailing or segs[3] == FORMAT_VERB or LOCAL.match(segs[3])):
                bad.append(f"{path}:{lineno}: {urn}")
    return bad


def check(root: pathlib.Path) -> list[str]:
    bad: list[str] = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        bad.extend(problems_of(path, path.read_text(encoding="utf-8")))
    return bad


def selftest() -> int:
    cases: list[tuple[str, str, str | None]] = [
        ("canonical urn", "id: urn:ngsi-ld:AirQualityObserved:banskabystrica.sk:ovzdusie:senzor-01", None),
        ("template placeholder", "urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}", None),
        ("bloblang format template", 'root.id = "urn:ngsi-ld:%v:%v:%v:%v".format(x)', None),
        ("format verb for the domain only", 'let id = "urn:ngsi-ld:Vehicle:%v:transport:%v"', None),
        ("a format verb does not excuse a missing segment", 'root.id = "urn:ngsi-ld:%v:%v:%v"', "urn:ngsi-ld:%v"),
        ("a format verb does not excuse a bad segment", '"urn:ngsi-ld:vehicle:%v:%v:%v"', "vehicle"),
        ("concatenation prefix", "prefix `urn:ngsi-ld:Device:banskabystrica.sk:doprava:` plus the id", None),
        ("scheme mentioned in prose", "the urn:ngsi-ld: scheme is normative", None),
        ("escaped dot in a regex", 'idPattern: "^urn:ngsi-ld:Device:banskabystrica\\\\.sk:doprava:depot-.*$"', None),
        ("uuid in the domain segment", "urn:ngsi-ld:Device:8f14e45f-ceea-467a-9575-6f6c1f2e2b3d:doprava:d-1", "8f14e45f"),
        ("uuid in the space segment", "urn:ngsi-ld:Device:banskabystrica.sk:8F14E45F-CEEA:d-1", "8F14E45F"),
        ("three segments only", "urn:ngsi-ld:Device:banskabystrica.sk:d-1", "urn:ngsi-ld:Device"),
        ("five segments", "urn:ngsi-ld:Device:banskabystrica.sk:doprava:zona:d-1", "zona"),
        ("lowercase type", "urn:ngsi-ld:device:banskabystrica.sk:doprava:d-1", "device"),
        ("domain without a dot", "urn:ngsi-ld:Device:banskabystrica:doprava:d-1", "banskabystrica"),
        ("uppercase space", "urn:ngsi-ld:Device:banskabystrica.sk:Doprava:d-1", "Doprava"),
        ("forbidden character in the local id", "urn:ngsi-ld:Device:banskabystrica.sk:doprava:d#1", "d#1"),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name, body, expected in cases:
            page = root / "page.md"
            page.write_text(f"---\ntitle: T\n---\n\n# T\n\n{body}\n", encoding="utf-8")
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: uuid segments, wrong segment counts, a lowercase type, a dotless domain and an "
          "uppercase space all go red, templates and prose stay green")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path(".")
    bad = check(root)
    if bad:
        print("URNs violating PF-42 (urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}):")
        print("\n".join(bad))
        return 1
    print("urns ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
