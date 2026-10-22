#!/usr/bin/env python3
"""Every page of the Portal has a User Guide page in English and Slovak (T-5110, UI-02).

A guide page names the Portal addresses it explains in its front matter, as the router writes them:

    routes:
      - /projects/$project/spaces
      - /projects/$project/spaces/upload

This check reads the Portal's router (`ui/src/router.tsx`) and the project sections its section
page serves (the kinds of `ui/src/routes/ResourceListPage.tsx`) and fails when

- an address of the router is named by no guide page, so a new page arrived without its guide;
- a guide page names an address the router no longer has, so the guide describes a page that went;
- a guide page that names addresses has no Slovak twin `User-Guide/sk/<same file>`, or the twin
  names other addresses than the English page;
- the Portal's in-page help (`ui/src/pageHelp.ts`) links a guide page that does not exist.

    check-guide-routes.py <portal-ui-dir> [docs-root]
    check-guide-routes.py --selftest
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import yaml

GUIDE = "User-Guide"
SK = "sk"
# The section page: one route whose `$plural` is each kind ResourceListPage serves.
SECTION = "/projects/$project/$plural"
SECTION_KINDS = ("VIEWS", "EDIT_FORMS", "CREATE_KINDS")
# Built only into a development bundle (`import.meta.env.DEV`); no person of an installation sees it.
DEVELOPMENT_ONLY = {"/__gallery"}
ROUTE = re.compile(r'^\s*path:\s*"(/[^"]*)"', re.M)
GUIDE_LINK = re.compile(r'guide:\s*"User-Guide/([^"#]+)"')


def kinds(source: str) -> set[str]:
    """The keys of the section page's kind tables, each `const NAME... = {` up to its closing `};`."""
    found: set[str] = set()
    for table in SECTION_KINDS:
        body = re.search(rf"^const {table}\b[^\n]*=\s*\{{\n(.*?)^\}};", source, re.M | re.S)
        if body is None:
            raise SystemExit(f"check-guide-routes: ResourceListPage.tsx has no table {table}; update SECTION_KINDS")
        found.update(re.findall(r"^  (\w+):", body.group(1), re.M))
    return found


def portal_routes(ui: Path) -> set[str]:
    routes = set(ROUTE.findall((ui / "src" / "router.tsx").read_text(encoding="utf-8")))
    if SECTION not in routes:
        raise SystemExit(f"check-guide-routes: router.tsx has no {SECTION}; update SECTION")
    routes -= DEVELOPMENT_ONLY | {SECTION}
    plurals = kinds((ui / "src" / "routes" / "ResourceListPage.tsx").read_text(encoding="utf-8"))
    return routes | {f"/projects/$project/{plural}" for plural in plurals}


def front_matter(page: Path) -> dict:
    text = page.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    return (yaml.safe_load(text[4:end]) or {}) if end > 0 else {}


def page_routes(page: Path) -> list[str]:
    routes = front_matter(page).get("routes") or []
    return [str(route) for route in routes] if isinstance(routes, list) else [f"<not a list: {routes!r}>"]


def problems(ui: Path, root: Path) -> list[str]:
    guide = root / GUIDE
    known = portal_routes(ui)
    named: dict[str, list[str]] = {}
    found: list[str] = []
    for page in sorted(guide.glob("*.md")):
        where = page.relative_to(root)
        routes = page_routes(page)
        for route in routes:
            named.setdefault(route, []).append(page.name)
            if route not in known:
                found.append(f"{where}: names {route}, which the Portal's router does not have")
        if not routes:
            continue
        twin = guide / SK / page.name
        if not twin.is_file():
            found.append(f"{where}: no Slovak twin {twin.relative_to(root)}; every guide page is written in en and sk")
        elif sorted(page_routes(twin)) != sorted(routes):
            found.append(f"{twin.relative_to(root)}: routes differ from {where}; the twin explains the same pages")
    for route in sorted(known - named.keys()):
        found.append(f"{route}: no User Guide page names it under routes:; write its guide page in en and sk")
    help_file = ui / "src" / "pageHelp.ts"
    if help_file.is_file():
        for target in sorted(set(GUIDE_LINK.findall(help_file.read_text(encoding="utf-8")))):
            if not (guide / f"{target}.md").is_file():
                found.append(f"pageHelp.ts: links User-Guide/{target}, which does not exist")
    return found


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ui, root = Path(tmp) / "ui", Path(tmp) / "docs"
        (ui / "src" / "routes").mkdir(parents=True)
        (ui / "src" / "router.tsx").write_text(
            'const a = createRoute({\n  path: "/catalogue",\n});\n'
            'const b = createRoute({\n  path: "/projects/$project/$plural",\n});\n'
            'const c = createRoute({\n  path: "new",\n});\n'
            '        path: "/__gallery",\n'
        )
        (ui / "src" / "routes" / "ResourceListPage.tsx").write_text(
            "const VIEWS: Record<string, X> = {\n  spaces: SpacesPage,\n  // a comment\n};\n"
            "const EDIT_FORMS: Record<string, (t: T) => Y> = {\n  mappings: (t) => ({\n    plural: 1,\n  }),\n};\n"
            "const CREATE_KINDS: Record<string, string> = {\n};\n"
        )
        (ui / "src" / "pageHelp.ts").write_text('  spaces: { key: "spaces", guide: "User-Guide/02-spaces" },\n')
        (root / GUIDE / SK).mkdir(parents=True)
        en = "---\ntitle: S\nroutes:\n  - /catalogue\n  - /projects/$project/spaces\n  - /projects/$project/mappings\n---\n# S\n"
        (root / GUIDE / "02-spaces.md").write_text(en)
        (root / GUIDE / SK / "02-spaces.md").write_text(en)
        (root / GUIDE / "ui-writing.md").write_text("---\ntitle: W\n---\n# W\n")
        assert problems(ui, root) == [], problems(ui, root)

        (root / GUIDE / "02-spaces.md").write_text(en.replace("  - /catalogue\n", "  - /gone\n"))
        (root / GUIDE / "03-more.md").write_text("---\nroutes:\n  - /catalogue\n---\n")
        (ui / "src" / "pageHelp.ts").write_text('  x: { guide: "User-Guide/09-missing" },\n')
        said = "\n".join(problems(ui, root))
        for expected in (
            "02-spaces.md: names /gone, which the Portal's router does not have",
            "sk/02-spaces.md: routes differ",
            "03-more.md: no Slovak twin",
            "links User-Guide/09-missing, which does not exist",
        ):
            assert expected in said, f"{expected!r} not in:\n{said}"

        (root / GUIDE / "03-more.md").unlink()
        said = "\n".join(problems(ui, root))
        assert "/catalogue: no User Guide page names it" in said, said
        assert "__gallery" not in said and "new" not in said.split(), said
    print("check-guide-routes selftest: ok")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--selftest"]:
        return selftest()
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    ui = Path(sys.argv[1])
    root = Path(sys.argv[2]) if len(sys.argv) == 3 else Path(__file__).resolve().parent.parent
    found = problems(ui, root)
    for problem in found:
        print(problem)
    print(f"check-guide-routes: {len(portal_routes(ui))} Portal addresses, {len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
