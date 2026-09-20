#!/usr/bin/env python3
"""The HTTP examples in the documentation are requests that would work (T-0103, MIM0-R7).

Every ```http and ```bash block under `API/`, `User-Guide/` and `Architecture/` is parsed: a
request line and its headers must be well formed, a documented response must carry a real status
line, no example may print a whole bearer token, and no `curl` may reach for `--insecure` or plain
http. With `JC_BASE_URL` set, the safe requests are executed against that deployment and their
status compared with the documented response. Only GET, HEAD and OPTIONS ever run: a documented
write is reported as not executed, because a documentation test must not create entities on a
shared cluster.

    JC_BASE_URL=https://host [JC_TOKEN=…] [JC_VAR_project=bb] test-curl-snippets.py [docs-root]
    test-curl-snippets.py --selftest
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FOLDERS = ("API", "User-Guide", "Architecture")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
SAFE = ("GET", "HEAD", "OPTIONS")
REQUEST = re.compile(rf"^({'|'.join(METHODS)})\s+(\S+)(\s+HTTP/[\d.]+)?\s*$")
STATUS = re.compile(r"^HTTP/[\d.]+\s+(\d{3})\b")
HEADER = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$")
# three dot-separated base64 segments is a whole JWT; an example must elide it
WHOLE_JWT = re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b")
PLACEHOLDER = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")


def blocks(text: str) -> list[tuple[int, str, list[str]]]:
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


def _lint_request(where: str, lines: list[str]) -> tuple[list[str], dict[str, str]]:
    problems: list[str] = []
    headers: dict[str, str] = {}
    for offset, line in enumerate(lines[1:], 1):
        if not line.strip():
            break
        header = HEADER.match(line.strip())
        if not header:
            problems.append(f"{where}: line {offset + 1} of the request is neither a header nor blank: {line.strip()!r}")
            continue
        name, value = header.group(1), header.group(2)
        if name.lower() in headers:
            problems.append(f"{where}: header '{name}' appears twice")
        headers[name.lower()] = value
        if name.lower() == "authorization" and WHOLE_JWT.search(value):
            problems.append(f"{where}: the Authorization example prints a whole token; elide it with '…'")
    return problems, headers


def check(root: Path) -> list[str]:
    problems: list[str] = []
    requests: list[tuple[str, str, str, dict[str, str], int | None]] = []

    for folder in FOLDERS:
        directory = root / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            found = blocks(path.read_text(encoding="utf-8"))
            for index, (start, info, lines) in enumerate(found):
                where = f"{rel}:{start}"
                body = [line for line in lines if line.strip()]
                if not body:
                    continue
                if info.startswith("http"):
                    if STATUS.match(body[0]):
                        continue
                    request = REQUEST.match(body[0].strip())
                    if not request:
                        # a block may quote headers alone: the page is showing what a response or a
                        # forwarded request carries, not a whole call
                        fragment, _ = _lint_request(where, ["", *body])
                        if all(HEADER.match(line.strip()) for line in body):
                            problems += fragment
                        else:
                            problems.append(
                                f"{where}: the block is tagged http but starts with {body[0].strip()!r}"
                            )
                        continue
                    # the blank line ends the headers and starts the body, so the raw lines are
                    # what the header walk needs
                    header_problems, headers = _lint_request(where, [line for line in lines])
                    problems += header_problems
                    expected: int | None = None
                    if index + 1 < len(found):
                        next_body = [line for line in found[index + 1][2] if line.strip()]
                        if next_body and STATUS.match(next_body[0]):
                            expected = int(STATUS.match(next_body[0]).group(1))
                    requests.append((where, request.group(1), request.group(2), headers, expected))
                elif info.startswith(("bash", "sh", "shell", "console")):
                    for offset, line in enumerate(lines):
                        if "curl" not in line:
                            continue
                        if re.search(r"(^|\s)(-k|--insecure)(\s|$)", line):
                            problems.append(f"{rel}:{start + offset}: the curl example disables certificate "
                                            "verification; a reader will copy that into production")
                        if re.search(r"curl[^\n|]*\bhttp://(?!localhost|127\.0\.0\.1)", line):
                            problems.append(f"{rel}:{start + offset}: the curl example uses plain http")
                        if WHOLE_JWT.search(line):
                            problems.append(f"{rel}:{start + offset}: the curl example prints a whole token")

    if not requests:
        problems.append("no HTTP request example was found, so this run proves nothing")
        return problems

    base = os.getenv("JC_BASE_URL")
    if not base:
        return problems

    token = os.getenv("JC_TOKEN")
    for where, method, target, headers, expected in requests:
        if method not in SAFE:
            print(f"{where}: {method} is a write, not executed", file=sys.stderr)
            continue
        missing = [name for name in PLACEHOLDER.findall(target) if not os.getenv(f"JC_VAR_{name}")]
        if missing:
            print(f"{where}: not executed, set {', '.join('JC_VAR_' + m for m in missing)}", file=sys.stderr)
            continue
        url = base.rstrip("/") + PLACEHOLDER.sub(lambda m: os.environ[f"JC_VAR_{m.group(1)}"], target)
        request = urllib.request.Request(url, method=method)
        for name, value in headers.items():
            if name in ("host", "authorization", "content-length"):
                continue
            request.add_header(name, value)
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
        except urllib.error.HTTPError as err:
            status = err.code
        except Exception as err:  # a connection failure is a finding, not a crash
            problems.append(f"{where}: {method} {url} could not be reached ({err.__class__.__name__})")
            continue
        if expected is not None and status != expected:
            problems.append(f"{where}: {method} {url} answered {status}, the page documents {expected}")
        elif expected is None and status >= 500:
            problems.append(f"{where}: {method} {url} answered {status}")
    return problems


def selftest() -> int:
    page = """---
title: API
---

# API

## 1. Examples

```http
GET /api/v1/projects/{project}/spaces?limit=20 HTTP/1.1
Host: portal.example.com
Authorization: Bearer eyJhbGciOiJSUzI1Ni...
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```bash
curl -s https://portal.example.com/api/v1/auth/me
```
"""
    cases: list[tuple[str, str, str | None]] = [
        ("clean examples", page, None),
        ("whole token in the example", page.replace(
            "eyJhbGciOiJSUzI1Ni...",
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkphbmEifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"),
         "prints a whole token"),
        ("duplicate header", page.replace("Host: portal.example.com", "Host: a.example.com\nHost: b.example.com"),
         "appears twice"),
        ("http block that is neither request nor response",
         page.replace("GET /api/v1/projects/{project}/spaces?limit=20 HTTP/1.1", "just some prose"),
         "starts with"),
        ("curl with --insecure", page.replace("curl -s https://", "curl -s --insecure https://"),
         "disables certificate verification"),
        ("curl over plain http", page.replace("curl -s https://", "curl -s http://"), "uses plain http"),
        ("garbled header line", page.replace("Host: portal.example.com", "Host portal.example.com"),
         "neither a header nor blank"),
        ("no example at all", "---\ntitle: API\n---\n\n# API\n\nProse.\n", "no HTTP request example was found"),
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "API").mkdir()
        for name, body, expected in cases:
            (root / "API" / "01-portal-api.md").write_text(body, encoding="utf-8")
            found = check(root)
            if expected is None and found:
                failures.append(f"{name}: reported {found}")
            elif expected is not None and not any(expected in problem for problem in found):
                failures.append(f"{name}: {expected!r} was not reported, got {found}")

        # the execution leg: an unreachable base url is a finding, and a write is never executed
        (root / "API" / "01-portal-api.md").write_text(
            page.replace("GET /api/v1/projects/{project}/spaces?limit=20 HTTP/1.1",
                         "POST /api/v1/projects/bb/spaces HTTP/1.1"), encoding="utf-8")
        os.environ["JC_BASE_URL"] = "http://127.0.0.1:9"
        found = check(root)
        if any("could not be reached" in problem for problem in found):
            failures.append(f"a documented write was executed against the base url: {found}")
        (root / "API" / "01-portal-api.md").write_text(page.replace("{project}", "bb"), encoding="utf-8")
        found = check(root)
        if not any("could not be reached" in problem for problem in found):
            failures.append(f"an unreachable deployment was not reported: {found}")
        os.environ.pop("JC_BASE_URL")

    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    if failures:
        return 1
    print("ok: a printed token, a duplicate or garbled header, a block that is neither request nor "
          "response, an insecure or plain-http curl, an empty chapter and an unreachable deployment "
          "all go red, and a documented write is never executed")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:2] == ["--selftest"]:
        return selftest()
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    if not os.getenv("JC_BASE_URL"):
        print("note: JC_BASE_URL is not set, so the examples are checked but not executed",
              file=sys.stderr)
    problems = check(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} HTTP example problem(s)", file=sys.stderr)
        return 1
    print("http examples ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
