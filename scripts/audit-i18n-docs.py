#!/usr/bin/env python3
"""Every localized example in the documentation obeys the locale policy (T-0106, PF-24…PF-28).

ADR-N-013 §3 fixes the core locales and their order, so this checker reads the set out of the ADR
instead of hard-coding it: a later decision that adds a locale changes the check with it. The
four-locale set is normative in the ADR, not in `Requirements/platform.md` §7, which only demands
ISO 639-1 keys and one declared fallback. There is no PyYAML in this CI lane, so a language map is
recognised line by line: two or more `xx: value` lines at one indentation inside a fenced block, or
a JSON object whose keys are all two-letter codes. A run has to contain at least one real ISO 639-1
code to be a language map at all, otherwise two ordinary sibling keys that happen to look like a
locale (`use_jwks:` and `use_pkce:` in an APISIX plugin block) would be read as a map of two
invented languages.

    audit-i18n-docs.py [docs-root]
    audit-i18n-docs.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

ADR = "Decisions/adr-n-013-multi-language-model.md"
# ISO 639-1 codes a language map may use. This is the standard's own two-letter set, not a
# shortlist of one city's neighbours: a map in a manifest is instance data, and an installation
# writes the languages it serves (ADR-N-013 §3). Anything outside ISO 639-1, a regional tag
# (`sk-SK`) or a three-letter code is a typo or an invented code.
ISO_639_1 = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy
da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu
hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb
lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om
or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw
ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu
""".split())
BUNDLE = re.compile(r"portal/locales/\{locale\}\.json|locales/\*\.json|locales/\{locale\}\.json")
YAML_ENTRY = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")
JSON_ENTRY = re.compile(r'^\s*"([A-Za-z][A-Za-z0-9_-]*)"\s*:')
LOCALE_LIKE = re.compile(r"^[A-Za-z]{2,3}([-_][A-Za-z]{2,4})?$")


def _fenced(text: str) -> list[tuple[int, str, list[str]]]:
    """(first body line number, info string, body lines) for every fenced block."""
    out: list[tuple[int, str, list[str]]] = []
    body: list[str] | None = None
    info, start = "", 0
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if body is None:
                body, info, start = [], stripped.lstrip("`~").strip(), lineno + 1
            else:
                out.append((start, info, body))
                body = None
            continue
        if body is not None:
            body.append(line)
    if body is not None:
        out.append((start, info, body))
    return out


def _policy(root: Path) -> tuple[list[str], list[str]]:
    """(ordered core locales, problems) read from ADR-N-013 §3."""
    path = root / ADR
    if not path.is_file():
        return [], [f"{ADR}: the locale policy lives here and the file is missing"]
    text = path.read_text(encoding="utf-8")
    section: list[str] = []
    collecting = False
    for line in text.splitlines():
        if line.startswith(("## ", "1. ", "2. ", "3. ")) and "locale" in line.lower():
            collecting = "locale" in line.lower()
            continue
        if collecting:
            if line.startswith("## ") or re.match(r"^\d+\.\s+\*\*", line):
                collecting = False
                continue
            section.append(line)
    codes = [c for c in re.findall(r"`([a-z]{2})`", "\n".join(section))]
    ordered: list[str] = []
    for code in codes:
        if code not in ordered:
            ordered.append(code)
    if len(ordered) < 2:
        return [], [f"{ADR}: could not read the core locale set, so nothing can be checked against it"]
    return ordered, []


def _is_language_map(keys: list[str]) -> bool:
    """Sibling keys are a language map when there are at least two and one names a real language.

    `LOCALE_LIKE` alone is too wide: it also matches `use_jwks` and `use_pkce`, two ordinary keys
    of an APISIX `openid-connect` block. Requiring one recognised code keeps every typo the check
    exists for (`fi-FI`, `fin` beside `en`) and drops the runs that are not maps.
    """
    return len(keys) >= 2 and any(key in ISO_639_1 for key in keys)


def _language_maps(lines: list[str], info: str) -> list[tuple[int, list[str]]]:
    """(offset of the first key, locale-like keys) for each run of sibling entries."""
    maps: list[tuple[int, list[str]]] = []
    # a JSON object written on one line is still a map: {"sk": "…", "en": "…"}
    for offset, line in enumerate(lines):
        inline = re.findall(r'"([A-Za-z][A-Za-z0-9_-]*)"\s*:', line)
        if all(LOCALE_LIKE.match(k) for k in inline) and _is_language_map(inline):
            maps.append((offset, inline))
    run: list[str] = []
    run_indent, run_start = None, 0
    for offset, line in enumerate(lines):
        key, indent = None, None
        if info.startswith("json"):
            m = JSON_ENTRY.match(line)
            if m:
                key, indent = m.group(1), len(line) - len(line.lstrip())
        else:
            m = YAML_ENTRY.match(line)
            if m:
                key, indent = m.group(2), len(m.group(1))
        if key is not None and LOCALE_LIKE.match(key) and (run_indent is None or indent == run_indent):
            if not run:
                run_start = offset
            run_indent = indent
            run.append(key)
            continue
        if _is_language_map(run):
            maps.append((run_start, run))
        run, run_indent = [], None
    if _is_language_map(run):
        maps.append((run_start, run))
    return maps


# A language map is written in YAML or JSON. In Turtle and its relatives a prefixed
# predicate (`dct:title "Ovzdušie"`) is indistinguishable from a YAML entry whose key
# looks like a locale, so those blocks are not language-map material at all (T-0371).
NOT_LANGUAGE_MAPS = {"turtle", "ttl", "n3", "nquads", "nq", "trig", "sparql", "rq"}


def check(root: Path) -> list[str]:
    ordered, problems = _policy(root)
    if problems:
        return problems
    fallback = ordered[0]

    found_maps = 0
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for start, info, lines in _fenced(text):
            language = info.split()[0].lower() if info.split() else ""
            if language in NOT_LANGUAGE_MAPS:
                continue
            body = "\n".join(lines)
            for offset, keys in _language_maps(lines, info):
                found_maps += 1
                lineno = start + offset
                for key in keys:
                    if key not in ISO_639_1:
                        problems.append(
                            f"{rel}:{lineno}: '{key}' is not an ISO 639-1 code this documentation uses "
                            f"(PF-24; allowed: {', '.join(sorted(ISO_639_1))})"
                        )
                if fallback not in keys:
                    problems.append(
                        f"{rel}:{lineno}: language map {keys} has no '{fallback}' entry, the fallback "
                        "locale every human-facing field must carry (PF-26)"
                    )
            if "machineTranslated" in body and not _language_maps(lines, info):
                problems.append(
                    f"{rel}:{start}: 'machineTranslated' annotates no language map in this block (PF-27)"
                )
        if BUNDLE.search(text):
            missing = [code for code in ordered if not re.search(rf"[`'\"/]{code}[`'\".,)/]|\b{code}\b", text)]
            if missing:
                problems.append(
                    f"{rel}: names the locale bundle path but never mentions {', '.join(missing)} "
                    f"of the core locales {', '.join(ordered)} (ADR-N-013)"
                )
    if found_maps == 0:
        problems.append("no language map was found in the corpus, so this run proves nothing")
    return problems


def selftest() -> int:
    adr = """---
title: ADR
---

# ADR-N-013

## 3. Decision

1. **Four Core Supported Locales**:
   - The platform core ships translations for:
     - **English (`en`)**
     - **Slovak (`sk`)**
     - **German (`de`)**
     - **Czech (`cs`)**
"""
    clean = """---
title: Page
---

# Page

```yaml
title:
  en: "Space"
  fi: "Tila"
```
"""
    cases: list[tuple[str, str, str | None, str | None]] = [
        ("clean language map", clean, None, None),
        ("map without the fallback", clean.replace('en: "Space"', 'de: "Raum"'), "has no 'en' entry", None),
        ("regional locale as a key", clean.replace("  fi:", "  fi-FI:"), "'fi-FI' is not an ISO 639-1 code", None),
        ("three-letter code", clean.replace("  fi:", "  fin:"), "'fin' is not an ISO 639-1 code", None),
        ("json language map", """---
title: Page
---

# Page

```json
{"fi": "Tila", "en": "Space"}
```
""", None, None),
        ("turtle predicates are not a language map", """---
title: Page
---

# Page

```turtle
@prefix dct: <http://purl.org/dc/terms/> .

<https://example.sk/cs/ovzdusie> a dcat:Dataset ;
    dct:identifier "ovzdusie" ;
    dct:title "Ovzdušie" .
```
""" + clean, None, None),
        ("machineTranslated without a map", """---
title: Page
---

# Page

```yaml
machineTranslated: true
```
""", "annotates no language map", None),
        ("bundle page naming three locales", clean + """
Bundles live in `portal/locales/{locale}.json` for sk, en and de.
""", "never mentions cs", None),
        ("bundle page naming all four", clean + """
Bundles live in `portal/locales/{locale}.json` for sk, en, de and cs.
""", None, None),
        ("no ADR", clean, "the locale policy lives here", ""),
        ("no language map at all", "---\ntitle: P\n---\n\n# P\n\nProse.\n", "no language map was found", None),
        ("locale-shaped plugin keys are not a map", clean + """
```yaml
openid-connect:
  use_jwks: false
  use_pkce: true
```
""", None, None),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Decisions").mkdir()
        for name, body, expected, adr_override in cases:
            adr_path = root / ADR
            if adr_override == "":
                adr_path.unlink(missing_ok=True)
            else:
                adr_path.write_text(adr_override or adr, encoding="utf-8")
            (root / "page.md").write_text(body, encoding="utf-8")
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a map without the fallback locale, an invented code, a free-floating "
          "machineTranslated, a bundle page missing a core locale, a missing ADR and a corpus "
          "with no language map at all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} localization problem(s)", file=sys.stderr)
        return 1
    print("localization examples ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
