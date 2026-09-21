#!/usr/bin/env python3
"""The one-page map names every crate, deployment component and conformance suite, and nothing
that is not there (T-1671).

`ARCHITECTURE.md` is the page an agent reads before any task. Its source of truth is the
shared workspace file `/workspace/ARCHITECTURE.md`, which no repository holds, so this check
takes the map and the folder that holds the clones as arguments instead of reading its own
repository:

    python3 scripts/check-architecture-map.py /workspace/ARCHITECTURE.md /workspace
    python3 scripts/check-architecture-map.py --selftest

Both directions: a crate, component or suite on disk that the map never names is a gap in the
map, and a `crates/…`, `components/…` or `tests/…` the map names that is not on disk is a map
that is wrong, which is worse than none.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

# What the map has to name, per repository: (clone folder, the folder of the parts, prefix).
PARTS = (
    ("joinedcontext-platform", "crates", "crates/"),
    ("joinedcontext-deployment", "components", "components/"),
    ("joinedcontext-conformance", "tests", "tests/"),
)
NAMED = re.compile(r"`((?:crates|components|tests)/[A-Za-z0-9._-]+)`")


def on_disk(root: Path) -> set[str]:
    found = set()
    for clone, folder, prefix in PARTS:
        base = root / clone / folder
        if not base.is_dir():
            raise SystemExit(f"{base} is not a folder: pass the directory that holds the clones")
        found |= {prefix + p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")}
    return found


def problems(map_text: str, root: Path) -> list[str]:
    disk = on_disk(root)
    named = set(NAMED.findall(map_text))
    missing = sorted(disk - named)
    stale = sorted(named - disk)
    return [f"{part} exists and the map never names it" for part in missing] + [
        f"the map names {part}, which does not exist" for part in stale
    ]


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for clone, folder, _ in PARTS:
            (root / clone / folder / "one").mkdir(parents=True)
        good = "`crates/one` `components/one` `tests/one`"
        assert problems(good, root) == [], problems(good, root)
        (root / "joinedcontext-platform" / "crates" / "two").mkdir()
        found = problems(good + " `tests/gone`", root)
        assert "crates/two exists and the map never names it" in found, found
        assert "the map names tests/gone, which does not exist" in found, found
        assert len(found) == 2, found
    print("ok: the map check finds a missing part and a stale one")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:] == ["--selftest"]:
        return selftest()
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    found = problems(Path(argv[1]).read_text(encoding="utf-8"), Path(argv[2]))
    for problem in found:
        print(problem, file=sys.stderr)
    if not found:
        print("architecture map ok: every crate, component and suite is named, and nothing else")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
