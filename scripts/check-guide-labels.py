#!/usr/bin/env python3
"""Every **bolded label** in the User Guide must be a label the Portal really shows.

The guide quotes buttons, tabs, fields and messages. A quoted label that is not in the Portal's
English locale bundle is a label nobody will find on the screen, which is how the guide went
stale the last time (T-1635…T-1644: nineteen invented buttons in nine pages).

Run it with the bundle's path, from a checkout of the Portal beside this one:

    python3 scripts/check-guide-labels.py ../joinedcontext-portal/ui/src/locales/en.json

It prints what it cannot match and exits 0: names of things and plain emphasis are bolded too, so
the list is read by a person rather than gating a lane. It is not in `ci.yml`, because the locale
bundle lives in another repository; wire it in the same way the manifest checkers fetch the
published schemas if that changes.
"""
import json, re, sys, pathlib

UI = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1 else "../joinedcontext-portal/ui/src/locales/en.json"
)
GUIDE = pathlib.Path(__file__).resolve().parent.parent / "User-Guide"

if not UI.is_file():
    print(f"no locale bundle at {UI}; pass the path to the Portal's en.json", file=sys.stderr)
    sys.exit(0)

flat = {}
def walk(o, p=""):
    for k, v in o.items():
        if isinstance(v, dict): walk(v, p + k + ".")
        elif isinstance(v, str): flat[p + k] = v
walk(json.loads(UI.read_text()))
values = {v.strip().lower() for v in flat.values()}
# A label with an interpolation is compared on its literal head, e.g. "Version {version}".
heads = {re.split(r"\{", v.strip().lower())[0].strip() for v in flat.values() if "{" in v}

NOUNS = {w.lower() for w in [
 "Organization","Organizations","Project","Projects","Context Space","Context Spaces","Endpoint",
 "Endpoints","Pipeline","Pipelines","Data Model","Data Models","Mapping","Mappings","App","Apps",
 "Application","Applications","Blueprint","Blueprints","ServiceAccount","ServiceAccounts",
 "Portal","Context Gateway","Change","Changes","Approver","Steward","Analyst","Developer",
 "Administrator","Copy","Copies","Flow","Flows","Data source","Data sources","Dashboard",
 "Dashboards","Space","Spaces","Role","Roles","Group","Groups","Assistant","Import","Export",
 "by hand","by asking the assistant","you","note","warning","tip",
]}

missing = {}
for page in sorted(GUIDE.glob("*.md")):
    for label in re.findall(r"\*\*([^*\n]{2,60})\*\*", page.read_text()):
        clean = label.strip().rstrip(":").strip()
        low = clean.lower()
        if low in values or low in NOUNS or low in heads: continue
        if any(low.startswith(h) for h in heads if h): continue
        missing.setdefault(page.name, []).append(clean)

for name, labels in missing.items():
    for label in dict.fromkeys(labels):
        print(f"{name}: **{label}** is not a label in en.json")
print(f"\n{sum(len(set(v)) for v in missing.values())} unmatched bold strings in {len(missing)} pages")
sys.exit(0)
