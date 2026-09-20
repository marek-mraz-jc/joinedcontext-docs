#!/usr/bin/env python3
"""The API pages describe routes the platform actually serves (T-0096, MF-11…MF-15, EP-01).

Every route printed under `API/` is parsed out of its fenced block and held to the URL scheme the
platform committed to: `/api/v1/projects/{project}/{plural}`, never a Kubernetes-style group path,
with path parameters spelled the same way on every page. Every JSON example must parse, and an
error example must carry the RFC 7807 members. With `OPENAPI_JSON` pointing at the specification
the Portal generates, each documented route is also looked up in it; without the variable that leg
names what would enable it rather than passing quietly.

    verify-openapi-snippets.py [docs-root]
    verify-openapi-snippets.py --selftest
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

API_DIR = "API"
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
ROUTE = re.compile(rf"^\s*({'|'.join(METHODS)})\s+(/\S*)")
PARAM = re.compile(r"\{([^}/]+)\}")
# `/ngsi-ld/v1` is the broker's own surface: the endpoint chapter prints the upstream request the
# gateway makes after rewriting, and that is a documented route too
# `/apps` is the static apps host: the Portal serves a published app under the platform host
# without a hostname of its own (AP-12, AP-14, Architecture/16 §5)
ALLOWED_PREFIXES = ("/api/v1", "/api/endpoint", "/apps", "/cs", "/ngsi-ld/v1",
                    "/healthz", "/livez", "/readyz", "/.well-known")
# The published specification is the Portal's own (utoipa over its axum router), so only the
# Portal's surface is looked up in it. `/api/endpoint`, `/cs`, `/ngsi-ld/v1` and `/apps` are
# the gateway's and the apps host's, documented here and served elsewhere; holding them to a
# document that cannot contain them would report a gap that is not one.
SPEC_SCOPE = ("/api/v1",)
FORBIDDEN = re.compile(r"^/apis/")
PROBLEM_MEMBERS = ("type", "title", "status")


def _blocks(text: str) -> list[tuple[int, str, list[str]]]:
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
    return out


def routes(root: Path) -> tuple[dict[tuple[str, str], str], list[str]]:
    """{(method, path): 'file:line'} for every documented route under API/."""
    found: dict[tuple[str, str], str] = {}
    problems: list[str] = []
    api_dir = root / API_DIR
    if not api_dir.is_dir():
        return found, [f"{API_DIR}/: the API chapter is missing"]
    for path in sorted(api_dir.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for start, info, lines in _blocks(text):
            if info.startswith("json"):
                body = "\n".join(lines).strip()
                if body.startswith(("{", "[")):
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError as err:
                        problems.append(f"{rel}:{start}: json example does not parse ({err.msg} at line {err.lineno})")
                        continue
                    # a problem document is recognised by its own shape, not by a nearby word:
                    # an identity or a manifest example must not be held to RFC 7807
                    looks_like_problem = isinstance(payload, dict) and (
                        isinstance(payload.get("status"), int)
                        or str(payload.get("type", "")).startswith("http") and "title" in payload
                    )
                    if looks_like_problem:
                        missing = [m for m in PROBLEM_MEMBERS if m not in payload]
                        if missing:
                            problems.append(
                                f"{rel}:{start}: problem+json example omits {', '.join(missing)} (RFC 7807)"
                            )
                continue
            for offset, line in enumerate(lines):
                match = ROUTE.match(line)
                if match:
                    found[(match.group(1), match.group(2).rstrip(","))] = f"{rel}:{start + offset}"
    return found, problems


def check(root: Path) -> list[str]:
    found, problems = routes(root)
    if not found:
        problems.append(f"{API_DIR}/: no documented route was found, so this run proves nothing")
        return problems

    spellings: dict[str, set[str]] = {}
    for (method, path), where in sorted(found.items(), key=lambda item: item[1]):
        if FORBIDDEN.match(path):
            problems.append(f"{where}: {method} {path} uses a group path; the scheme is /api/v1/projects/{{project}}/{{plural}}")
        elif not path.startswith(ALLOWED_PREFIXES):
            problems.append(f"{where}: {method} {path} is outside the documented URL scheme {ALLOWED_PREFIXES}")
        for name in PARAM.findall(path):
            if not re.fullmatch(r"[a-z][A-Za-z0-9]*", name):
                problems.append(f"{where}: path parameter '{{{name}}}' is not lowerCamelCase")
            key = re.sub(r"(_?id|Id|_?name|Name)$", "", name).lower() or name.lower()
            spellings.setdefault(key, set()).add(name)

    for key, names in sorted(spellings.items()):
        if len(names) > 1:
            problems.append(
                f"{API_DIR}/: the same path parameter is spelled {', '.join(sorted(names))}; "
                "pick one spelling"
            )

    spec_path = os.getenv("OPENAPI_JSON")
    if spec_path:
        try:
            spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        except Exception as err:
            return problems + [f"OPENAPI_JSON={spec_path} could not be read: {err}"]
        paths = spec.get("paths")
        if not isinstance(paths, dict) or not paths:
            return problems + [f"OPENAPI_JSON={spec_path} declares no paths"]
        # A documented route is served by a specification path when the two have the same
        # number of segments and every segment either matches or is a parameter on the
        # specification's side. The direction matters: `/branding/logo` is served by
        # `/branding/{asset}` and `/projects/{p}/csrs` by `/projects/{project}/{plural}`,
        # because a page is free to show the value a parameter takes. The reverse is not
        # true — a page that writes `{plural}` where the specification has a fixed segment
        # is describing a surface wider than the one that exists.
        spec_segments = {route: route.strip("/").split("/") for route in paths}

        def serves(spec_route: str, documented_segments: list[str]) -> bool:
            published = spec_segments[spec_route]
            if len(published) != len(documented_segments):
                return False
            return all(
                PARAM.fullmatch(part) is not None or part == mine
                for part, mine in zip(published, documented_segments)
            )

        for (method, path), where in sorted(found.items(), key=lambda item: item[1]):
            # A documented route often shows the query it takes (`?limit=20`,
            # `?format=yaml|json|zip`). A specification path never carries one, so the
            # comparison is on the path alone: the query is documented per parameter.
            bare = path.split("?", 1)[0]
            if not bare.startswith(SPEC_SCOPE):
                continue
            documented_segments = bare.strip("/").split("/")
            # The most specific match first, so `/branding/{asset}` is preferred over a
            # wildcard that would also accept it and the parameter names are compared
            # against the path a client would really call.
            candidates = sorted(
                (route for route in paths if serves(route, documented_segments)),
                key=lambda route: len(PARAM.findall(route)),
            )
            if not candidates:
                problems.append(f"{where}: {method} {path} is in no path of the published specification")
                continue
            spec_route = candidates[0]
            if method.lower() not in {k.lower() for k in paths[spec_route]}:
                problems.append(f"{where}: the specification serves {spec_route} without {method}")
            # Only the positions where both sides wrote a parameter are compared: a page
            # showing a value is not a rename, and a rename is still caught.
            published = spec_segments[spec_route]
            renamed = [
                (mine, theirs)
                for theirs, mine in zip(published, documented_segments)
                if PARAM.fullmatch(theirs) and PARAM.fullmatch(mine) and theirs != mine
            ]
            if renamed:
                problems.append(
                    f"{where}: {path} names its parameters "
                    f"{[mine.strip('{}') for mine, _ in renamed]} and the specification "
                    f"names them {[theirs.strip('{}') for _, theirs in renamed]}"
                )
    return problems


def selftest() -> int:
    page = """---
title: API
---

# API

## 2. Error Response Format (RFC 7807)

All errors return `application/problem+json`:

```json
{"type": "https://joinedcontext.com/errors/not-found", "title": "Not Found", "status": 404}
```

## 3. Routes

```text
GET    /api/v1/projects/{project}/{plural}            list
POST   /api/v1/projects/{project}/{plural}            create
GET    /api/endpoint/{endpointSlug}/ngsi-ld/v1/entities   entities
```
"""
    cases: list[tuple[str, str, str | None, dict | None]] = [
        ("documented routes", page, None, None),
        ("group path", page.replace("/api/v1/projects/{project}/{plural}            list",
                                    "/apis/joinedcontext.com/v1alpha1/spaces   list"), "uses a group path", None),
        ("route outside the scheme", page.replace("GET    /api/v1/projects", "GET    /internal/projects"),
         "outside the documented URL scheme", None),
        ("parameter spelled two ways", page.replace("{endpointSlug}", "{projectId}"),
         "spelled project, projectId", None),
        ("parameter not lowerCamelCase", page.replace("{plural}", "{Plural}"), "is not lowerCamelCase", None),
        ("broken json example", page.replace('"status": 404}', '"status": 404'), "does not parse", None),
        ("problem+json without status", page.replace(', "status": 404', ""), "omits status", None),
        ("no route at all", "---\ntitle: API\n---\n\n# API\n\nProse.\n", "no documented route was found", None),
        ("route missing from the specification", page, "is in no path of the published specification",
         {"paths": {"/api/v1/projects/{project}/changes": {"get": {}, "post": {}}}}),
        ("method missing from the specification", page, "without POST",
         {"paths": {"/api/v1/projects/{project}/{plural}": {"get": {}},
                    "/api/endpoint/{endpointSlug}/ngsi-ld/v1/entities": {"get": {}}}}),
        ("parameter renamed in the specification", page, "names them ['kind']",
         {"paths": {"/api/v1/projects/{project}/{kind}": {"get": {}, "post": {}},
                    "/api/endpoint/{endpointSlug}/ngsi-ld/v1/entities": {"get": {}}}}),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / API_DIR).mkdir()
        for name, body, expected, spec in cases:
            (root / API_DIR / "01-portal-api.md").write_text(body, encoding="utf-8")
            if spec is None:
                os.environ.pop("OPENAPI_JSON", None)
            else:
                spec_file = root / "openapi.json"
                spec_file.write_text(json.dumps(spec), encoding="utf-8")
                os.environ["OPENAPI_JSON"] = str(spec_file)
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")
        os.environ.pop("OPENAPI_JSON", None)
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a group path, a route outside the scheme, two spellings of one parameter, broken "
          "json, an incomplete problem+json, an empty chapter and three kinds of drift from a "
          "published specification all go red")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    if not os.getenv("OPENAPI_JSON"):
        print("note: OPENAPI_JSON is not set, so routes are checked against the URL scheme and "
              "not against the specification the Portal publishes", file=sys.stderr)
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} API documentation problem(s)", file=sys.stderr)
        return 1
    print("api snippets ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
