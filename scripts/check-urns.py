#!/usr/bin/env python3
"""Every concrete entity URN in the documentation must satisfy PF-43 (ADR-N-041, T-0100, T-3080).

`urn:ngsi-ld:{Type}:{nss}` — a PascalCase type and an RFC 8141 namespace-specific string of at
most 256 characters. Identity is the space and the URN, so the old four-segment shape is no longer
required; but a URN written in the platform's `prefixed` shape (its second segment a dotted
domain) must be a correct one, `{Type}:{orgDomain}:{space}:{localId}`, so a mistyped example of
the shape the platform mints still goes red. Placeholders (`{Type}`, `{orgDomain}`, `…`, a
trailing `"` or `+`) are skipped, and so is a Bloblang `%v` in place of a segment: a pipeline
mints its ids with `"urn:ngsi-ld:%v:%v:%v:%v".format(…)` (PF-44).

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
# RFC 8141: NSS = pchar *( pchar / "/" ), pchar = unreserved / pct-encoded / sub-delims / ":" / "@".
NSS = re.compile(r"^(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})(?:[A-Za-z0-9._~!$&'()*+,;=:@/-]|%[0-9A-Fa-f]{2}){0,255}$")
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

            nss = ":".join(segs[1:])
            prefixed = segs[1] == FORMAT_VERB or "." in segs[1]
            if not segment(0, TYPE):
                bad.append(f"{path}:{lineno}: {urn}")
            elif prefixed:
                if len(segs) != 4 or not segment(1, DOMAIN) or not segment(2, SPACE) \
                   or not (trailing or segs[3] == FORMAT_VERB or LOCAL.match(segs[3])):
                    bad.append(f"{path}:{lineno}: {urn}")
            elif not NSS.match(nss):
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
        ("unprefixed FIWARE id (ADR-N-041)", "urn:ngsi-ld:WeatherObserved:Helsinki-001", None),
        ("unprefixed id with colons", "urn:ngsi-ld:Device:depot:7", None),
        ("uuid as the whole id", "urn:ngsi-ld:Device:8f14e45f-ceea-467a-9575-6f6c1f2e2b3d", None),
        ("prefixed with a uuid space", "urn:ngsi-ld:Device:banskabystrica.sk:8F14E45F-CEEA:d-1", "8F14E45F"),
        ("prefixed with five segments", "urn:ngsi-ld:Device:banskabystrica.sk:doprava:zona:d-1", "zona"),
        ("prefixed with three segments", "urn:ngsi-ld:Device:banskabystrica.sk:d-1", "urn:ngsi-ld:Device"),
        ("lowercase type", "urn:ngsi-ld:device:banskabystrica.sk:doprava:d-1", "device"),
        ("one-letter type", "urn:ngsi-ld:X:abc", "urn:ngsi-ld:X"),
        ("prefixed with an uppercase space", "urn:ngsi-ld:Device:banskabystrica.sk:Doprava:d-1", "Doprava"),
        ("forbidden character in a prefixed local id", "urn:ngsi-ld:Device:banskabystrica.sk:doprava:d#1", "d#1"),
        ("forbidden character in an unprefixed id", "urn:ngsi-ld:Device:d^1", "d^1"),
        ("an id over 256 characters", "urn:ngsi-ld:Device:" + "a" * 257, "urn:ngsi-ld:Device"),
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
    print("ok: unprefixed NGSI-LD ids stay green; a bad type, a bad character, an overlong id and a "
          "malformed prefixed id go red; templates and prose stay green")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = pathlib.Path(argv[1]) if len(argv) > 1 else pathlib.Path(".")
    bad = check(root)
    if bad:
        print("URNs violating PF-43 (urn:ngsi-ld:{Type}:{nss}; a prefixed one as {Type}:{orgDomain}:{space}:{localId}):")
        print("\n".join(bad))
        return 1
    print("urns ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
