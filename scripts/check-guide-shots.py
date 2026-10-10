#!/usr/bin/env python3
"""The User Guide's screenshots are the ones the live journeys take, and only those (T-3270).

The Portal's journeys shoot each guide step with `guideShot(page, name)` at 1280 px in English and
Slovak, and `scripts/publish-guide-shots.sh` in the Portal repository commits them, quantized, to
`User-Guide/img/{en,sk}/{name}.png`. This check holds the guides to that:

- an image a guide page shows lives under `User-Guide/img/en/` or `User-Guide/img/sk/`, so no
  screenshot is made by hand and goes stale unseen;
- it exists, so a guide never names a shot no journey produced;
- it is a PNG 1280 px wide and at most 300 KB, the shape the publisher writes;
- it has alt text, which says the step to a reader who cannot see it;
- its twin in the other language exists, because every shot is taken in both;
- and every shot under `img/` is shown by some page, so a step the guides dropped leaves no file.

    check-guide-shots.py [docs-root]
    check-guide-shots.py --selftest
"""

from __future__ import annotations

import re
import struct
import sys
import tempfile
from pathlib import Path

GUIDE = "User-Guide"
LANGS = ("en", "sk")
WIDTH = 1280
MAX_BYTES = 300 * 1024
IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*(```|~~~)")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_width(path: Path) -> int | None:
    """The width an IHDR chunk declares, or None when the file is not a PNG."""
    head = path.read_bytes()[:24]
    if len(head) < 24 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">I", head[16:20])[0]


def images(page: Path):
    """Every `![alt](target)` of a page outside code fences, with its line number."""
    fenced = False
    for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            for match in IMAGE.finditer(line):
                yield number, match.group(1).strip(), match.group(2)


def problems(root: Path) -> list[str]:
    guide = root / GUIDE
    img = guide / "img"
    found: list[str] = []
    shown: set[Path] = set()
    for page in sorted(guide.rglob("*.md")):
        where = page.relative_to(root)
        for number, alt, target in images(page):
            if re.match(r"^[a-z]+:", target):
                found.append(f"{where}:{number}: {target} is not a journey's shot; the guides show only User-Guide/img/{{en,sk}}/")
                continue
            path = (page.parent / target).resolve()
            try:
                lang, name = path.relative_to(img.resolve()).parts
            except ValueError:
                found.append(f"{where}:{number}: {target} is outside User-Guide/img/{{en,sk}}/, so no journey takes it")
                continue
            if lang not in LANGS or not name.endswith(".png"):
                found.append(f"{where}:{number}: {target} is not User-Guide/img/{{en,sk}}/<name>.png")
                continue
            shown.add(path)
            if not alt:
                found.append(f"{where}:{number}: {target} has no alt text; say the step it shows")
            if not path.is_file():
                found.append(f"{where}:{number}: {target} does not exist; no journey produced that shot")
                continue
            twin = img / LANGS[1 - LANGS.index(lang)] / name
            if not twin.is_file():
                found.append(f"{where}:{number}: {target} has no twin {twin.relative_to(root)}; every shot is taken in en and sk")
    for shot in sorted(img.rglob("*")) if img.is_dir() else []:
        if not shot.is_file():
            continue
        where = shot.relative_to(root)
        width = png_width(shot)
        if width is None:
            found.append(f"{where}: not a PNG")
            continue
        if width != WIDTH:
            found.append(f"{where}: {width} px wide; the journeys shoot at {WIDTH}")
        if shot.stat().st_size > MAX_BYTES:
            found.append(f"{where}: {shot.stat().st_size} bytes, over {MAX_BYTES}")
        if shot.resolve() not in shown:
            found.append(f"{where}: no guide page shows it; drop it or show it")
    return found


def png(width: int) -> bytes:
    """The smallest file png_width reads: signature and an IHDR header."""
    return PNG_SIGNATURE + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, 800) + bytes(5)


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for lang in LANGS:
            (root / GUIDE / "img" / lang).mkdir(parents=True)
            (root / GUIDE / "img" / lang / "space-1.png").write_bytes(png(WIDTH))
        page = root / GUIDE / "04-pipelines.md"
        page.write_text("# P\n\n![Open the space](img/en/space-1.png)\n\n```md\n![x](nowhere.png)\n```\n")
        sk = root / GUIDE / "sk" / "04-pipelines.md"
        sk.parent.mkdir()
        sk.write_text("# P\n\n![Otvorte priestor](../img/sk/space-1.png)\n")
        assert problems(root) == [], problems(root)

        page.write_text(
            "![](img/en/space-1.png)\n![a](img/en/space-2.png)\n![a](shots/x.png)\n"
            "![a](https://example.org/x.png)\n![a](img/de/space-1.png)\n"
        )
        (root / GUIDE / "img" / "en" / "space-3.png").write_bytes(png(1600))
        (root / GUIDE / "img" / "en" / "notes.txt").write_text("x")
        said = "\n".join(problems(root))
        for expected in (
            "has no alt text",
            "space-2.png does not exist",
            "shots/x.png is outside",
            "https://example.org/x.png is not a journey's shot",
            "img/de/space-1.png is not User-Guide/img",
            "space-3.png: 1600 px wide",
            "notes.txt: not a PNG",
            "space-3.png: no guide page shows it",
        ):
            assert expected in said, f"{expected!r} not in:\n{said}"

        (root / GUIDE / "img" / "en" / "space-3.png").unlink()
        (root / GUIDE / "img" / "en" / "notes.txt").unlink()
        (root / GUIDE / "img" / "sk" / "space-1.png").unlink()
        sk.write_text("# P\n")
        page.write_text("![a](img/en/space-1.png)\n")
        assert any("has no twin" in p for p in problems(root)), problems(root)
    print("check-guide-shots selftest: ok")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    found = problems(root)
    for problem in found:
        print(problem)
    shots = len(list((root / GUIDE / "img").rglob("*.png"))) if (root / GUIDE / "img").is_dir() else 0
    print(f"check-guide-shots: {shots} shots, {len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
