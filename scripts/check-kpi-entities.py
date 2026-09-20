#!/usr/bin/env python3
"""Every KPI entity printed in the documentation is one the platform would store (T-2310, PF-54).

A fenced block marked ```json ngsi-ld-kpi is an NGSI-LD `KeyPerformanceIndicator` entity, not a
manifest, so `validate-doc-manifests.py` never sees it. Each one is parsed, held to the shape
PF-54 fixes, and, with `JC_SCHEMAS_DIR` pointing at the draft-07 schemas the platform publishes
(`<dir>/KeyPerformanceIndicator.json`), validated against that schema. The schema closes the
object, so an attribute the contract invented is reported here rather than at the first write.

The corpus must contain at least one such block: the Banská Bystrica contract
(`Development/10-banska-bystrica-contract.md`) is what ingestion, computation and the application
are built against, and a contract whose examples quietly disappeared is worse than none.

    check-kpi-entities.py [docs-root]
    check-kpi-entities.py --selftest
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

MARKER = "ngsi-ld-kpi"
SCHEMA_FILE = "KeyPerformanceIndicator.json"
# `urn:ngsi-ld:{Type}:{orgDomain}:{space}:{localId}`, the four segments of PF-42. The general
# grammar is check-urns.py's; here only the type matters, because the space is the indicator's.
KPI_URN = re.compile(
    r"^urn:ngsi-ld:KeyPerformanceIndicator:"
    r"[a-z0-9][a-z0-9.-]*\.[a-z]{2,}:"
    r"[a-z0-9][a-z0-9-]{0,62}:"
    r"([A-Za-z0-9._~-]{1,128})$"
)
PAGES = (".md", ".mdx")


def blocks(text: str):
    """(line number of the block body, body) for every ```json ngsi-ld-kpi block."""
    out: list[tuple[int, str]] = []
    body: list[str] | None = None
    start = 0
    wanted = False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if body is None:
                info = stripped[3:].strip().split()
                wanted = MARKER in info
                body, start = [], lineno + 1
            else:
                if wanted:
                    out.append((start, "\n".join(body)))
                body, wanted = None, False
            continue
        if body is not None:
            body.append(line)
    return out


def problems_of(path: Path, text: str, validator) -> list[str]:
    found: list[str] = []
    for lineno, body in blocks(text):
        where = f"{path}:{lineno}"
        try:
            entity = json.loads(body)
        except json.JSONDecodeError as error:
            found.append(f"{where}: the KPI entity does not parse: {error}")
            continue
        if not isinstance(entity, dict):
            found.append(f"{where}: a KPI entity is a JSON object, got {type(entity).__name__}")
            continue
        if entity.get("type") != "KeyPerformanceIndicator":
            found.append(f"{where}: type is {entity.get('type')!r}, expected 'KeyPerformanceIndicator'")
        match = KPI_URN.match(str(entity.get("id", "")))
        if not match:
            found.append(f"{where}: id {entity.get('id')!r} is not a four-segment KPI URN (PF-42, PF-54)")
        else:
            # PF-54: `name` is the `{localId}` of the id, so a renamed indicator cannot keep an
            # id that says otherwise.
            name = entity.get("name")
            value = name.get("value") if isinstance(name, dict) else None
            if value != match.group(1):
                found.append(
                    f"{where}: name.value {value!r} is not the id's localId {match.group(1)!r} (PF-54)")
        value = entity.get("currentValue")
        if isinstance(value, dict) and isinstance(value.get("value"), str) and "unitCode" in value:
            found.append(
                f"{where}: currentValue is a state, not a quantity, so it carries no unitCode")
        if validator is not None:
            for error in sorted(validator.iter_errors(entity), key=str):
                place = "/".join(str(part) for part in error.absolute_path) or "(root)"
                found.append(f"{where}: {place}: {error.message}")
    return found


def check(root: Path) -> list[str]:
    schema_dir = os.getenv("JC_SCHEMAS_DIR")
    validator = None
    if schema_dir:
        path = Path(schema_dir) / SCHEMA_FILE
        if not path.is_file():
            return [f"JC_SCHEMAS_DIR is set but {path} is missing: the platform publishes this schema"]
        import jsonschema

        schema = json.loads(path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)

    found: list[str] = []
    seen = 0
    for page in sorted(root.rglob("*")):
        if page.suffix not in PAGES or "node_modules" in page.parts:
            continue
        text = page.read_text(encoding="utf-8")
        seen += len(blocks(text))
        found += problems_of(page.relative_to(root), text, validator)
    if seen == 0:
        found.append(
            "no ```json ngsi-ld-kpi block in the corpus: the Banská Bystrica contract's examples "
            "are what T-2305…T-2309 build against and they cannot vanish silently")
    return found


GOOD = """---
title: "A contract"
---

# A contract

```json ngsi-ld-kpi
{
  "id": "urn:ngsi-ld:KeyPerformanceIndicator:bbsk.sk:bbsk-kpi:emisie-tuhe-kraj",
  "type": "KeyPerformanceIndicator",
  "name": { "type": "Property", "value": "emisie-tuhe-kraj" },
  "currentValue": { "type": "Property", "value": 5354.3, "unitCode": "TNE" },
  "calculationPeriod": {
    "type": "Property",
    "value": { "start": "2023-01-01T00:00:00Z", "end": "2023-12-31T23:59:59Z" }
  },
  "calculationFormula": { "type": "Property", "value": "sum(value)" },
  "derivedFrom": { "type": "Relationship", "object": "urn:ngsi-ld:Endpoint:bbsk.sk:bbsk-kraj:kraj-read" },
  "computedBy": { "type": "Relationship", "object": "urn:ngsi-ld:Pipeline:bbsk.sk:bbsk-kpi:emisie-tuhe" },
  "updatedAt": { "type": "Property", "value": { "@type": "DateTime", "@value": "2026-09-20T06:00:00Z" } }
}
```
"""


def selftest() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        page = root / "page.md"

        page.write_text(GOOD, encoding="utf-8")
        found = check(root)
        if found:
            failures.append(f"a correct KPI entity was reported: {found}")

        page.write_text("---\ntitle: t\n---\n\n# t\n\nNo entity here.\n", encoding="utf-8")
        if not any("no ```json ngsi-ld-kpi block" in problem for problem in check(root)):
            failures.append("a corpus with no KPI example was not reported")

        page.write_text(GOOD.replace('"emisie-tuhe-kraj" }', '"emisie-tuhe-okres-brezno" }'), encoding="utf-8")
        if not any("is not the id's localId" in problem for problem in check(root)):
            failures.append("a name that disagrees with the id was not reported")

        page.write_text(GOOD.replace('"KeyPerformanceIndicator",', '"Indicator",'), encoding="utf-8")
        if not any("expected 'KeyPerformanceIndicator'" in problem for problem in check(root)):
            failures.append("a wrong entity type was not reported")

        page.write_text(GOOD.replace(":bbsk-kpi:emisie-tuhe-kraj", ":bbsk:kpi:emisie-tuhe-kraj"), encoding="utf-8")
        if not any("four-segment KPI URN" in problem for problem in check(root)):
            failures.append("a five-segment id was not reported")

        page.write_text(GOOD.replace('"value": 5354.3, "unitCode"', '"value": "not measured", "unitCode"'),
                        encoding="utf-8")
        if not any("carries no unitCode" in problem for problem in check(root)):
            failures.append("a state carrying a unit was not reported")

        page.write_text(GOOD.replace('"calculationFormula": { "type": "Property", "value": "sum(value)" },', ""),
                        encoding="utf-8")
        structural = check(root)

        page.write_text(GOOD.replace('"currentValue"', '"territory": "kraj",\n  "currentValue"'),
                        encoding="utf-8")
        invented = check(root)

        page.write_text(GOOD + "\n```json ngsi-ld-kpi\n{ not json }\n```\n", encoding="utf-8")
        if not any("does not parse" in problem for problem in check(root)):
            failures.append("an unparsable KPI block was not reported")

        # The schema leg only runs where the platform's schemas are on disk. Both cases above
        # are ones only the schema can judge, so they are asserted here and skipped otherwise.
        schema_dir = os.getenv("JC_SCHEMAS_DIR")
        if schema_dir and (Path(schema_dir) / SCHEMA_FILE).is_file():
            if not any("calculationFormula" in problem for problem in structural):
                failures.append("a KPI entity missing a required attribute was not reported")
            if not any("territory" in problem for problem in invented):
                failures.append("a KPI entity carrying an invented attribute was not reported")
        else:
            print("note: JC_SCHEMAS_DIR is not set, so the two schema-only cases were not asserted",
                  file=sys.stderr)

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a wrong type, a five-segment id, a name that disagrees with it, a state with a "
          "unit, unparsable JSON and an empty corpus all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    if not os.getenv("JC_SCHEMAS_DIR"):
        print("note: JC_SCHEMAS_DIR is not set, so KPI entities are checked structurally and not "
              "against the published draft-07 schema", file=sys.stderr)
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} KPI entity problem(s)", file=sys.stderr)
        return 1
    print("documented KPI entities ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
