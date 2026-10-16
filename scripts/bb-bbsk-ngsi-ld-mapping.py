#!/usr/bin/env python3
"""Every Banská Bystrica and BBSK dataset on data.dev, mapped to NGSI-LD or refused (T-4254).

The mapping file `Research/bb-bbsk-ngsi-ld-mapping.yaml` is what the seed generator (T-4255)
reads. It is built from two committed snapshots, never by hand: the CKAN `package_search`
answer of the two organizations and one probe of each resource. The type of each dataset comes
from TYPES below, the only judgement in this script; everything else is read.

    bb-bbsk-ngsi-ld-mapping.py snapshot   # CKAN package_search -> Research/data/bb-bbsk-ckan.json
    bb-bbsk-ngsi-ld-mapping.py probe      # one request per resource -> Research/data/bb-bbsk-probe.json
    bb-bbsk-ngsi-ld-mapping.py draft      # both snapshots -> Research/bb-bbsk-ngsi-ld-mapping.yaml
    bb-bbsk-ngsi-ld-mapping.py check      # CI: every dataset mapped or refused, page totals equal
    bb-bbsk-ngsi-ld-mapping.py --selftest

`check` needs no network: it reads the committed snapshot and fails when the mapping misses a
dataset id, names one the snapshot does not hold, refuses one without a reason, or when the
totals table of `Research/bb-bbsk-ngsi-ld-mapping.md` differs from what it counts.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CKAN = "https://data.dev.joinedcontext.com"
ORGS = ("banskabystrica", "bbsk")
SNAPSHOT = ROOT / "Research/data/bb-bbsk-ckan.json"
PROBE = ROOT / "Research/data/bb-bbsk-probe.json"
MAPPING = ROOT / "Research/bb-bbsk-ngsi-ld-mapping.yaml"
PAGE = ROOT / "Research/bb-bbsk-ngsi-ld-mapping.md"
# The public space of each project that holds what this mapping loads, beside the curated spaces:
# its generated classes cannot collide with a curated class of the same name (DM-61).
SPACE = {"banskabystrica": "banskabystrica-otvorene-data", "bbsk": "bbsk-otvorene-data"}
UA = {"User-Agent": "joinedcontext-docs T-4254 inventory (hello@joinedcontext.com)"}
EXTRAS = ("publisher_name", "license_url", "generated_by", "harvest_source", "source_id", "source_url", "source_uri", "modified",
          "frequency", "issued")
# Esri bookkeeping fields: never a property of the entity.
ESRI_SKIP = re.compile(r"^(OBJECTID|FID|GlobalID|Shape__\w+|Shape_\w+|SHAPE_\w+|ObjectId\d*)$", re.I)

# The type of each dataset: (name pattern, NGSI-LD type, Smart Data Model or None, note).
# First match wins. A Smart Data Model only where its attributes fit the columns; the rest
# are project types named after what one row is.
TYPES: list[tuple[str, str, str | None, str]] = [
    (r"nabijacky", "EVChargingStation", "dataModel.Transportation/EVChargingStation", ""),
    (r"nehodovost", "RoadAccident", "dataModel.Transportation/RoadAccident", ""),
    (r"cykloscitace", "TrafficFlowObservedSite", None, "the counting sites; no counts in the layer"),
    (r"mosty", "Bridge", None, "the name of the bbsk-registre class"),
    (r"podjazdy|priepusty|dilatacne-celky|zeleznicne-priecestia", "RoadStructure", None, ""),
    (r"cykloturisticke-trasy-linie", "CycleRoute", None, ""),
    (r"cykloturisticke-trasy-nosic", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "signposts, boards and rest stops"),
    (r"lekarni|zdravotnickych", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "category from the facility kind"),
    (r"skoly|skolske", "School", None, "the name of the bbsk-registre class"),
    (r"kulturne-institucie|kontaktne-miesta", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", ""),
    (r"organizacie|prispevkove", "PublicOrganization", None, "the name of the bbsk-registre class"),
    (r"poskytovatelov-socialnych", "SocialService", None, "the name of the bbsk-registre class"),
    (r"kraj-bbk-hranica|okresy-bbk-hranice|obce-bbk-hranice|obce-bbk-centroidy", "AdministrativeArea", None, "the name of the bbsk-registre class"),
    (r"povodia", "RiverBasin", None, ""),
    (r"vodnych-utvarov", "WaterBodyStatus", None, "one row per water body and assessment"),
    (r"vyvoj-emisii|vyvoj-imisii", "StatisticalObservation", None, "one row per station or source and year"),
    (r"obyvatel|vekov|ohrozenie-samosprav|ppa-platby-po-okresoch", "StatisticalObservation", None, "one row per area (and year)"),
    (r"register-investicii|projekty-banskobystrickeho", "PublicInvestment", None, ""),
    (r"faktury", "Invoice", None, ""),
    (r"objednavky", "PurchaseOrder", None, ""),
    (r"zmluvy", "Contract", None, ""),
    (r"dotacie|ppa-platby", "Grant", None, ""),
    (r"dodavatelia", "Supplier", None, ""),
    (r"verejneho-obstaravania|verejne-obstaravania", "PublicProcurement", None, ""),
    (r"clenovia|komisie", "CouncilMember", None, "public office holders, published under Act 211/2000"),
    (r"hlasovania", "CouncilVote", None, "public office holders' votes"),
    (r"zasadnutia", "CouncilMeeting", None, ""),
    (r"peticie", "Petition", None, "the petition, not its signatories"),
    (r"vzn|nariadeni", "Regulation", None, ""),
    (r"organizacna-struktura|uradne-hodiny|kontakty-na-miestne", "OrganizationUnit", None, ""),
    (r"bb-adresy", "Address", None, "the city's address list, without coordinates"),
    (r"bb-aktuality", "Article", None, "the city's news (WordPress)"),
    (r"bb-podujatia", "Event", None, "the name of the banskabystrica-verejne class"),
    (r"pocet-obcanov|prirastky", "StatisticalObservation", None, ""),
]


def get(url: str, *, method: str = "GET", headers: dict | None = None, limit: int = 1 << 20):
    """(status, headers, at most `limit` bytes). TLS is verified; a failure is a status, not a raise.
    A network error, a 429/5xx or an Esri error body is tried once more: ArcGIS Online answers an
    occasional count query with an error and the same query a second later with the number."""
    first = _get(url, method, headers, limit)
    if first[0] in (0, 429) or first[0] >= 500 or first[2].startswith(b'{"error"'):
        return _get(url, method, headers, limit)
    return first


def _get(url: str, method: str, headers: dict | None, limit: int):
    req = urllib.request.Request(url, method=method, headers={**UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict(r.headers), r.read(limit) if method != "HEAD" else b""
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), b""
    except Exception as e:  # DNS, TLS, timeout: recorded, never hidden
        return 0, {"error": f"{type(e).__name__}: {e}"[:200]}, b""


def snapshot() -> None:
    out = {"fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "source": CKAN, "datasets": []}
    for org in ORGS:
        q = urllib.parse.urlencode({"fq": f"organization:{org}", "rows": 1000, "sort": "name asc"})
        status, _, body = get(f"{CKAN}/api/3/action/package_search?{q}", limit=1 << 26)
        result = json.loads(body)["result"]
        if status != 200 or result["count"] != len(result["results"]):
            sys.exit(f"{org}: package_search answered {status} with {len(result['results'])} of {result['count']}")
        for p in result["results"]:
            ex = {e["key"]: e["value"] for e in p.get("extras", [])}
            out["datasets"].append({
                "id": p["id"], "name": p["name"], "org": org, "title": p["title"],
                "license": p.get("license_id"), "modified": p.get("metadata_modified"),
                "extras": {k: ex[k] for k in EXTRAS if k in ex},
                "resources": [{"id": r["id"], "name": r.get("name"), "format": r.get("format") or "",
                               "url": r["url"], "datastore": bool(r.get("datastore_active"))}
                              for r in p["resources"]],
            })
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out['datasets'])} datasets -> {SNAPSHOT.relative_to(ROOT)}")


def zip_members(url: str) -> dict:
    """The size and member names of a remote ZIP, from its central directory (one ranged GET)."""
    status, h, _ = get(url, method="HEAD")
    size = int(h.get("Content-Length") or 0)
    info = {"status": status, "size": size, "type": h.get("Content-Type")}
    if status != 200 or not size:
        return info
    tail = min(size, 1 << 20)
    st, _, buf = get(url, headers={"Range": f"bytes={size - tail}-"}, limit=tail)
    at = buf.rfind(b"PK\x05\x06")
    if st not in (200, 206) or at < 0:
        return info
    count, cd_size, cd_off = struct.unpack("<HII", buf[at + 10:at + 20])
    cd = buf[cd_off - (size - tail):] if cd_off >= size - tail else b""
    names, i = [], 0
    while len(names) < count and cd[i:i + 4] == b"PK\x01\x02":
        n, e, c = struct.unpack("<HHH", cd[i + 28:i + 34])
        names.append(cd[i + 46:i + 46 + n].decode("utf-8", "replace"))
        i += 46 + n + e + c
    exts: dict[str, int] = {}
    for n in names:
        if "." in n and not n.endswith("/"):
            x = n.rsplit(".", 1)[1].lower()
            exts[x] = exts.get(x, 0) + 1
    return {**info, "members": len(names), "extensions": exts}


def zip_geojson(url: str) -> dict:
    """Features, property names and CRS of the one GeoJSON inside a small ZIP."""
    import io
    import zipfile
    status, _, body = get(url, limit=ZIP_LIMIT + 1)
    if status != 200 or len(body) > ZIP_LIMIT:
        return {}
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        member = next(n for n in z.namelist() if n.lower().endswith(".geojson"))
        raw = z.read(member)
    try:  # the archives set no UTF-8 flag, so zipfile read the name as cp437
        name = member.encode("cp437").decode("utf-8")
    except UnicodeError:
        name = member
    doc = json.loads(raw.decode("utf-8-sig"))
    feats = doc.get("features", [])
    keys: list[str] = []
    for f in feats[:200]:
        keys += [k for k in (f.get("properties") or {}) if k not in keys]
    distinct = {"+".join(c): len({tuple((f.get("properties") or {}).get(k) for k in c) for f in feats})
                for c in key_candidates(keys)}
    return {"file": name, "features": len(feats), "fields": [{"name": k} for k in keys], "distinct": distinct,
            "geometry": sorted({(f.get("geometry") or {}).get("type") for f in feats} - {None}),
            "crs": ((doc.get("crs") or {}).get("properties") or {}).get("name", "EPSG:4326 (no crs member)")}


def key_candidates(fields: list[str]) -> list[list[str]]:
    """Columns that may identify a row: an id-like column alone, then with a year column."""
    singles = [f for f in fields if KEY_HINT.match(attr(f))]
    years = [f for f in fields if re.search(r"^(rok|year)(_|$)|_rok$|obdobie", f, re.I) and f not in singles]
    return [[k] for k in singles] + [[k, y] for k in singles for y in years]


def esri_layer(fs: str, layer: int) -> dict:
    status, _, body = get(f"{fs}/{layer}?f=json")
    if status != 200:
        return {"status": status}
    meta = json.loads(body)
    if "error" in meta:
        return {"status": meta["error"].get("code", 0)}
    _, _, cnt = get(f"{fs}/{layer}/query?where=1%3D1&returnCountOnly=true&f=json")
    fields = [{"name": f["name"], "type": f["type"].removeprefix("esriFieldType"), "alias": f.get("alias")}
              for f in meta.get("fields", []) if not ESRI_SKIP.match(f["name"])]
    # ArcGIS Online answers returnDistinctValues with returnCountOnly by the plain row count, which
    # took Číslo+Rok of the BBSK grants for a key while 4775 rows held 3905 values (T-4255), so the
    # distinct values are paged and counted here.
    distinct = {}
    for cols in key_candidates([f["name"] for f in fields]):
        seen, offset = set(), 0
        while True:
            q = urllib.parse.urlencode({"where": "1=1", "outFields": ",".join(cols), "returnDistinctValues": "true",
                                        "returnGeometry": "false", "resultOffset": offset,
                                        "resultRecordCount": 2000, "f": "json"})
            _, _, body = get(f"{fs}/{layer}/query?{q}", limit=1 << 24)
            page = json.loads(body or b"{}")
            seen |= {tuple(f["attributes"].get(c) for c in cols) for f in page.get("features", [])}
            if not page.get("exceededTransferLimit"):
                break
            offset += 2000
        distinct["+".join(cols)] = len(seen)
    return {"status": 200, "layer": layer, "name": meta.get("name"), "geometry": meta.get("geometryType"),
            "count": json.loads(cnt or b"{}").get("count"), "fields": fields, "distinct": distinct}


def datastore(resource_id: str) -> dict:
    q = urllib.parse.urlencode({"resource_id": resource_id, "limit": 0})
    status, _, body = get(f"{CKAN}/api/3/action/datastore_search?{q}")
    if status != 200:
        return {"status": status}
    r = json.loads(body)["result"]
    fields = [{"name": f["id"], "type": f["type"]} for f in r["fields"] if f["id"] != "_id"]
    distinct = {}
    for cols in key_candidates([f["name"] for f in fields]):
        q = urllib.parse.urlencode({"resource_id": resource_id, "limit": 0, "distinct": "true", "fields": ",".join(cols)})
        _, _, n = get(f"{CKAN}/api/3/action/datastore_search?{q}")
        distinct["+".join(cols)] = json.loads(n or b"{}").get("result", {}).get("total")
    return {"status": 200, "count": r.get("total"), "fields": fields, "distinct": distinct}


def json_feed(url: str) -> dict:
    status, h, body = get(url, limit=1 << 22)
    info = {"status": status, "type": h.get("Content-Type", "").split(";")[0]}
    if status != 200:
        return info
    try:
        doc = json.loads(body)
    except ValueError:
        enc = "utf-8" if body[:3] == b"\xef\xbb\xbf" else None
        return {**info, "json": False, "head": body[:80].decode(enc or "utf-8", "replace")}
    rows = doc if isinstance(doc, list) else next((v for v in doc.values() if isinstance(v, list)), []) if isinstance(doc, dict) else []
    keys = sorted(rows[0]) if rows and isinstance(rows[0], dict) else []
    return {**info, "json": True, "rows_in_first_page": len(rows), "keys": keys,
            "total": next((v for k, v in h.items() if k.lower() == "x-wp-total"), None)}


def probe() -> None:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    out = {"fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "resources": {}}
    for d in snap["datasets"]:
        if d["extras"].get("generated_by"):
            continue  # published by the platform from its own NGSI-LD Endpoint
        layer = next((int(m.group(1)) for r in d["resources"]
                      if (m := re.search(r"[?&]layers=(\d+)", r["url"]))), 0)
        for r in d["resources"]:
            fmt = r["format"].upper()
            if fmt == "ESRI REST":
                res = esri_layer(r["url"].rstrip("/"), layer)
            elif r["datastore"]:
                res = datastore(r["id"])
            elif fmt == "ZIP":
                res = zip_members(r["url"])
                if "geojson" in res.get("extensions", {}) and res["size"] <= ZIP_LIMIT:
                    res |= zip_geojson(r["url"])
            elif fmt == "JSON":
                res = json_feed(r["url"])
            else:
                # The Hub's CSV and GeoJSON exports of the layer the Esri REST probe reads.
                res = {"status": None, "note": "export of the Esri layer, not fetched"}
            out["resources"][r["id"]] = res
            print(d["name"][:50].ljust(50), fmt.ljust(9), res.get("status"), res.get("count", res.get("size", "")), flush=True)
    PROBE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def attr(field: str) -> str:
    """An NGSI-LD attribute name from a column: ASCII lowerCamelCase."""
    plain = unicodedata.normalize("NFKD", field).encode("ascii", "ignore").decode()
    words = [w for w in re.split(r"[^A-Za-z0-9]+", plain) if w]
    if not words:
        return "value"
    out = words[0][0].lower() + words[0][1:] + "".join(w[:1].upper() + w[1:] for w in words[1:])
    return out if out[0].isalpha() else "n" + out


def refresh(modified: str | None, fetched: str, typ: str = "") -> str:
    """No harvested dataset carries a frequency, so the interval follows its last change: one that
    changed in the last 31 days is read daily, a yearly statistic monthly (Open data integration
    rules §3), anything else weekly."""
    if modified and (date.fromisoformat(fetched[:10]) - date.fromisoformat(modified[:10])).days <= 31:
        return "P1D"
    return "P1M" if typ == "StatisticalObservation" else "P1W"


# NGSI-LD core members: a column with one of these names keeps its value under `source<Name>`.
RESERVED = {"id", "type", "scope", "location", "observationSpace", "operationSpace", "createdAt",
            "modifiedAt", "deletedAt", "observedAt", "datasetId", "instanceId", "unitCode", "value", "object"}
# What a WordPress post is to a reader; the rest of the REST answer is theme and editor state.
WP_FIELDS = {"title": "string", "link": "uri", "date_gmt": "datetime", "modified_gmt": "datetime", "content": "string"}
# The value type of a column, from the source's own field type: what the generator converts to and
# what the generated model declares.
RANGES = {
    "SmallInteger": "integer", "Integer": "integer", "BigInteger": "integer", "OID": "integer",
    "Double": "float", "Single": "float", "Date": "datetime", "DateOnly": "date", "TimestampOffset": "datetime",
    "int2": "integer", "int4": "integer", "int8": "integer", "numeric": "float", "float8": "float",
    "timestamp": "datetime", "date": "date",
}


def prop(field: str) -> str:
    a = attr(field)
    return "source" + a[0].upper() + a[1:] if a in RESERVED else a


def properties(fields: list[str], ranges: dict[str, str]) -> dict[str, dict]:
    """Attribute name -> column and range. Two columns that fold to one name (case, diacritics)
    take a number after the second, in column order."""
    out: dict[str, dict] = {}
    for f in fields:
        name, n = prop(f), 2
        while name in out:
            name, n = f"{prop(f)}{n}", n + 1
        out[name] = {"column": f, "range": ranges[f]}
    return out


def type_of(name: str):
    for pattern, typ, sdm, note in TYPES:
        if re.search(pattern, name):
            return typ, sdm, note
    return None


# Columns that name or reach a person, dropped before a row becomes an entity (Security of T-4254;
# Open data integration rules §1). Office holders keep name and function; their phones and e-mails
# and every employee's or appointee's name and contact stay out.
DROP: list[tuple[str, list[str], str]] = [
    (r"organizacna-struktura", ["Priezvisko", "Meno", "Titul_pred_menom", "Titul_za_menom", "Telefon", "Mobil", "Email"],
     "employees' names and contacts; the units and functions stay"),
    (r"clenovia-samospravy", ["Telefonický_kontakt", "Emailový_kontakt"], "office holders' own phones and e-mails"),
    (r"komisie", ["Meno"], "committees seat citizens who hold no office; the seats stay, the names do not"),
    (r"kontakty-na-miestne", ["Starosta", "Telefónne_číslo___starosta", "E_mail___starosta", "Zástupca_primátora",
                               "E_mail___zástupca_primátora"], "mayors' own contacts; the offices' general ones stay"),
    (r"zdravotnickych", ["Odborný_zástupca"], "the named physician of each facility"),
]
# Rows that can name a natural person, kept out by a filter on a column (§8 of the sources page).
# The city's three finance tables were filtered by the harvest itself (T-4151). An IČO column also
# holds surnames padded to eight characters (`0000BIBA`, 1903 of the BBSK orders, T-4255), which no
# Esri SQL can tell from a number, so those rows are kept only when the column matches IČO.
ICO = r"^[0-9]{6,8}( ?[0-9]{4})?$"
ICO_WHY = "a row without an IČO, or with a name where the IČO belongs, can name a natural person"
# The city's contracts name each party, a social-service client by name too ("úhrada za SS"); a
# contract stays only when every party line carries an IČO (T-4255).
PARTIES = r"^IČO:[^\r]*(\rIČO:[^\r]*)*$"
ROWS: list[tuple[str, str, str | None, str | None, str]] = [
    (r"bb-zmluvy-bb", "Zmluvné_strany_s_údajom_IČO", None, PARTIES,
     "a party without an IČO is a natural person, a social-service client among them"),
    (r"bbsk-(faktury|objednavky|dotacie)", "IČO", "IČO IS NOT NULL AND IČO <> ''", ICO, ICO_WHY),
    (r"bbsk-dodavatelia", "ICO", "ICO IS NOT NULL AND ICO <> ''", ICO, ICO_WHY),
    (r"bbsk-zmluvy", "IČO_dodávateľa", "IČO_dodávateľa IS NOT NULL AND IČO_dodávateľa <> ''", ICO,
     "a contract whose supplier has no IČO, or a name where the IČO belongs, can name a natural person"),
    (r"poskytovatelov-socialnych", "Typ_poskytovateľa", "Typ_poskytovateľa <> 'neverejný poskytovateľ'", None,
     "a private provider can be a natural person; bbsk-datasource-socialne-sluzby applies the same filter"),
]
# Seed DataSources that already read the same source (joinedcontext-deployment
# components/context-gateway/seed/); the generator extends or leaves them, never duplicates.
EXISTING: list[tuple[str, str, str]] = [
    (r"bb-podujatia", "banskabystrica/datasource-podujatia.yaml", "whole"),
    (r"mosty-v-banskobystrickom", "bbsk/bbsk-datasource-mosty.yaml", "whole"),
    (r"organizacie-v-zriadovatelskej", "bbsk/bbsk-datasource-organizacie.yaml", "whole"),
    (r"okresy-bbk-hranice", "bbsk/bbsk-datasource-okresy.yaml", "whole"),
    (r"obce-bbk-hranice", "bbsk/bbsk-datasource-obce.yaml", "whole"),
    (r"zdravotnickych", "bbsk/bbsk-datasource-nemocnice.yaml", "hospitals only"),
    (r"poskytovatelov-socialnych", "bbsk/bbsk-datasource-socialne-sluzby.yaml", "whole"),
]
# observedAt is a time of measurement: only rows that are observations carry one.
OBSERVED = {"StatisticalObservation", "RoadAccident", "WaterBodyStatus", "CouncilVote", "CouncilMeeting"}
# A ZIP whose GeoJSON is larger than this is not loaded in this round (16 GB node, one broker).
ZIP_LIMIT = 10 << 20
# A source with more rows than this waits for a later round: 240 636 survey points would double
# the broker's entities for the least-asked question.
ROW_LIMIT = 100_000

KEY_HINT = re.compile(r"^(id\w*|\w*_id|kod\w*|\w*_kod|ico|idn\d|lau\d?_code|\w*cislo\w*|nuts\w*|identifik\w*)$", re.I)


def plan(d: dict, probe_: dict, fetched: str) -> dict:
    """One mapping entry: mapped (with its source resource), already NGSI-LD, or not ingestible."""
    entry = {"id": d["id"], "name": d["name"], "org": d["org"], "title": d["title"]}
    if d["extras"].get("generated_by"):
        return {**entry, "status": "already-ngsi-ld",
                "reason": "published by the platform from its own public Endpoint (jcctl ckan-publisher)"}
    by_fmt = {r["format"].upper(): (r, probe_.get(r["id"], {})) for r in d["resources"]}
    if "ESRI REST" in by_fmt:
        r, p = by_fmt["ESRI REST"]
        if p.get("status") != 200:
            return {**entry, "status": "not-ingestible", "reason": f"Esri layer answered {p.get('status')}"}
        fields = [f["name"] for f in p["fields"]]
        ranges = {f["name"]: RANGES.get(f["type"], "string") for f in p["fields"]}
        source = {"kind": "esri-featureserver", "url": f"{r['url'].rstrip('/')}/{p['layer']}",
                  "geometry": p["geometry"], "rows": p["count"]}
    elif "CSV" in by_fmt and by_fmt["CSV"][1].get("status") == 200:
        r, p = by_fmt["CSV"]
        fields = [f["name"] for f in p["fields"]]
        ranges = {f["name"]: RANGES.get(f["type"], "string") for f in p["fields"]}
        source = {"kind": "ckan-datastore", "url": r["url"], "resource": r["id"], "rows": p["count"]}
    elif "ZIP" in by_fmt and by_fmt["ZIP"][1].get("features") and "5514" in by_fmt["ZIP"][1].get("crs", ""):
        r, p = by_fmt["ZIP"]
        return {**entry, "status": "not-ingestible",
                "reason": f"{p['features']} {', '.join(p['geometry'])} features in S-JTSK (EPSG:5514): NGSI-LD "
                          "locations are WGS 84 and no pipeline step reprojects; without the geometry the rows "
                          "carry little (the city's address list without points is bb-adresy)"}
    elif "ZIP" in by_fmt:
        r, p = by_fmt["ZIP"]
        exts = p.get("extensions", {})
        shp = "shp" in exts
        why = (f"a ZIP of {', '.join(f'{n} .{x}' for x, n in sorted(exts.items()))} ({p.get('size', 0) // 1024} KiB)"
               if exts else f"a ZIP that answered {p.get('status')}")
        if "geojson" in exts:
            why += f": larger than the {ZIP_LIMIT >> 20} MiB this round loads into the one broker"
        elif shp:
            why += ": Esri shapefiles; no ingestion path reads a shapefile today"
        elif set(exts) == {"pdf"}:
            why += ": a PDF map sheet, no data"
        else:
            why += ": no table or feature file inside"
        return {**entry, "status": "not-ingestible", "reason": why}
    elif "JSON" in by_fmt:
        r, p = by_fmt["JSON"]
        if p.get("status") == 200 and p.get("json"):
            if "wp-json" not in r["url"]:
                return {**entry, "status": "not-ingestible", "reason": "a JSON feed other than WordPress: no mapping reads it yet"}
            fields = ["id", *(k for k in WP_FIELDS if k in p.get("keys", []))]
            ranges = {"id": "integer", **WP_FIELDS}
            source = {"kind": "json-feed", "url": r["url"], "rows": int(p["total"]) if p.get("total") else p.get("rows_in_first_page")}
        else:
            return {**entry, "status": "not-ingestible",
                    "reason": f"the JSON link answered {p.get('status')} with {p.get('type') or 'no body'}, not JSON"}
    else:
        return {**entry, "status": "not-ingestible", "reason": "no machine-readable resource"}
    if (source.get("rows") or 0) > ROW_LIMIT:
        return {**entry, "status": "not-ingestible",
                "reason": f"{source['rows']} rows, more than the {ROW_LIMIT} this round loads into the one broker"}
    if not source.get("rows"):
        return {**entry, "status": "not-ingestible", "reason": f"the source holds no rows ({source['url']})"}
    typed = type_of(d["name"])
    if not typed:
        return {**entry, "status": "not-ingestible", "reason": "no type decided (TYPES has no rule)"}
    typ, sdm, note = typed
    rows = source["rows"]
    # A key is a column (or column and year) the probe counted as many distinct values as rows;
    # a WordPress post id is unique by definition. Anything else is a row hash.
    unique = [k.split("+") for k, n in (p.get("distinct") or {}).items() if n == rows and all(c in fields for c in k.split("+"))]
    if source["kind"] == "json-feed" and "id" in fields:
        unique = [["id"]]
    observed = next((f for f in fields if re.search(r"d[aá]tum|date|rok$|^rok|year|obdobie", f, re.I)), None) if typ in OBSERVED else None
    dropped = next(((cols, why) for pat, cols, why in DROP if re.search(pat, d["name"])), ([], ""))
    absent = [c for c in dropped[0] if c not in fields]
    if absent:
        sys.exit(f"{d['name']}: DROP names {absent}, which the source does not have")
    fields = [f for f in fields if f not in dropped[0]]
    out = {**entry, "status": "mapped", "type": typ, "smartDataModel": sdm, "source": source,
           "entityId": {"keys": unique[0]} if unique else {"rowHash": True},
           "observedAt": observed, "space": SPACE[d["org"]],
           "refresh": "P1D" if source["kind"] == "json-feed" else refresh(d["extras"].get("modified"), fetched, typ),
           "dataProvider": d["extras"].get("publisher_name"), "license": d["license"],
           "dataset": f"{CKAN}/dataset/{d['name']}",
           "properties": properties(fields, ranges)}
    if dropped[0]:
        out["dropped"] = {"columns": dropped[0], "why": dropped[1]}
    for pat, column, where, keep, why in ROWS:
        if re.search(pat, d["name"]):
            if column not in fields:
                sys.exit(f"{d['name']}: ROWS filters on {column}, which the source does not have")
            out["rowFilter"] = {**({"where": where} if where else {}),
                                **({"keep": {"column": column, "pattern": keep}} if keep else {}), "why": why}
    for pat, seed, part in EXISTING:
        if re.search(pat, d["name"]):
            out["existing"] = {"seed": seed, "covers": part}
    if note:
        out["note"] = note
    return out


def draft() -> None:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    probe_ = json.loads(PROBE.read_text(encoding="utf-8"))["resources"]
    entries = [plan(d, probe_, snap["fetched"]) for d in snap["datasets"]]
    import yaml  # draft only: the CI check reads the file with the same library
    head = (f"# Generated by scripts/bb-bbsk-ngsi-ld-mapping.py draft from Research/data/ (CKAN snapshot "
            f"{snap['fetched']}). T-4255's seed generator reads this file. Do not edit by hand:\n"
            f"# change TYPES in the script and run `draft` again.\n")
    body = yaml.safe_dump({"fetched": snap["fetched"], "datasets": entries}, allow_unicode=True,
                          sort_keys=False, width=110)
    MAPPING.write_text(head + body, encoding="utf-8")
    if PAGE.exists():
        PAGE.write_text(fill(PAGE.read_text(encoding="utf-8"), sections(snap, entries)), encoding="utf-8")
    print(totals_table(totals(snap, entries)))


def totals(snap: dict, entries: list[dict]) -> dict[str, dict[str, int]]:
    t: dict[str, dict[str, int]] = {}
    for e in entries:
        for org in (e["org"], "all"):
            row = t.setdefault(org, {"datasets": 0, "mapped": 0, "already-ngsi-ld": 0, "not-ingestible": 0, "rows": 0})
            row["datasets"] += 1
            row[e["status"]] += 1
            row["rows"] += (e.get("source") or {}).get("rows") or 0
    return {k: t[k] for k in [*ORGS, "all"] if k in t}


def totals_table(t: dict) -> str:
    lines = ["| organization | datasets | mapped | already NGSI-LD | not ingestible | source rows of the mapped |",
             "|---|---:|---:|---:|---:|---:|"]
    for org, r in t.items():
        lines.append(f"| {org} | {r['datasets']} | {r['mapped']} | {r['already-ngsi-ld']} | {r['not-ingestible']} | {r['rows']} |")
    return "\n".join(lines)


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def sections(snap: dict, entries: list[dict]) -> dict[str, str]:
    """Every table of the page, built from the mapping: the page holds no number of its own."""
    mapped = [e for e in entries if e["status"] == "mapped"]
    by_type: dict[str, list[dict]] = {}
    for e in mapped:
        by_type.setdefault(e["type"], []).append(e)
    types = ["| NGSI-LD type | Smart Data Model | datasets | source rows |", "|---|---|---:|---:|"]
    for t, es in sorted(by_type.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        types.append(f"| `{t}` | {'`' + es[0]['smartDataModel'] + '`' if es[0].get('smartDataModel') else 'project type'} "
                     f"| {len(es)} | {sum(e['source']['rows'] for e in es)} |")
    refused = ["| dataset | organization | status | reason |", "|---|---|---|---|"]
    for e in entries:
        if e["status"] != "mapped":
            refused.append(f"| {cell(e['title'])} (`{e['name']}`) | {e['org']} | {e['status']} | {cell(e['reason'])} |")
    personal = ["| dataset | kept out | why |", "|---|---|---|"]
    for e in mapped:
        if e.get("dropped"):
            personal.append(f"| `{e['name']}` | columns {', '.join(f'`{c}`' for c in e['dropped']['columns'])} | {cell(e['dropped']['why'])} |")
        if e.get("rowFilter"):
            f = e["rowFilter"]
            parts = ([f"rows outside `{cell(f['where'])}`"] if f.get("where") else []) + (
                [f"rows whose `{f['keep']['column']}` does not match `{cell(f['keep']['pattern'])}`"] if f.get("keep") else [])
            personal.append(f"| `{e['name']}` | {', or '.join(parts)} | {cell(f['why'])} |")
    existing = ["| dataset | seed that already reads it | covers |", "|---|---|---|"]
    existing += [f"| `{e['name']}` | `{e['existing']['seed']}` | {e['existing']['covers']} |" for e in mapped if e.get("existing")]
    keys = {"a key column": 0, "a key column and its year": 0, "a row hash": 0}
    for e in mapped:
        k = e["entityId"].get("keys") or []
        keys["a row hash" if not k else "a key column" if len(k) == 1 else "a key column and its year"] += 1
    ids = ["| entity id from | datasets |", "|---|---:|"] + [f"| {k} | {n} |" for k, n in keys.items()]
    return {"totals": totals_table(totals(snap, entries)), "types": "\n".join(types), "refused": "\n".join(refused),
            "personal": "\n".join(personal), "existing": "\n".join(existing), "ids": "\n".join(ids)}


def fill(page: str, tables: dict[str, str]) -> str:
    for name, table in tables.items():
        page = re.sub(rf"(<!-- {name} -->\n)(?:.*?\n)?(<!-- /{name} -->)", lambda m: m.group(1) + table + "\n" + m.group(2),
                      page, flags=re.S)
    return page


def check(snap: dict, mapping: dict, page: str) -> list[str]:
    errors = []
    ids = {d["id"]: d for d in snap["datasets"]}
    seen: dict[str, int] = {}
    for e in mapping.get("datasets", []):
        seen[e.get("id")] = seen.get(e.get("id"), 0) + 1
        if e.get("id") not in ids:
            errors.append(f"{e.get('name')}: id {e.get('id')} is not in the CKAN snapshot")
        st = e.get("status")
        if st not in ("mapped", "already-ngsi-ld", "not-ingestible"):
            errors.append(f"{e.get('name')}: status {st!r}")
        elif st != "mapped" and not e.get("reason"):
            errors.append(f"{e.get('name')}: {st} without a reason")
        elif st == "mapped":
            missing = [k for k in ("type", "source", "entityId", "space", "refresh", "properties") if not e.get(k)]
            if missing:
                errors.append(f"{e.get('name')}: mapped without {', '.join(missing)}")
    for i, d in ids.items():
        if i not in seen:
            errors.append(f"{d['name']} ({i}) is in CKAN and missing from the mapping")
    errors += [f"{i} is in the mapping {n} times" for i, n in seen.items() if n > 1]
    for name, want in sections(snap, mapping.get("datasets", [])).items():
        m = re.search(rf"<!-- {name} -->\n(.*?)\n<!-- /{name} -->", page, re.S)
        if not m:
            errors.append(f"the page has no <!-- {name} --> table")
        elif m.group(1).strip() != want:
            errors.append(f"the page's {name} table differs from the mapping (run `draft`); it is:\n{want}")
    return errors


def selftest() -> None:
    snap = {"datasets": [{"id": "a", "name": "x"}, {"id": "b", "name": "y"}]}
    ok = {"datasets": [{"id": "a", "name": "x", "title": "X", "org": "bbsk", "status": "not-ingestible", "reason": "pdf"},
                       {"id": "b", "name": "y", "title": "Y", "org": "bbsk", "status": "mapped", "type": "T", "space": "s", "smartDataModel": None,
                        "source": {"rows": 3}, "entityId": {"rowHash": True}, "refresh": "P1D", "properties": {"a": "A"}}]}
    page = fill("x\n" + "".join(f"<!-- {n} -->\n<!-- /{n} -->\n" for n in sections(snap, [])), sections(snap, ok["datasets"]))
    assert fill(page, sections(snap, ok["datasets"])) == page
    assert check(snap, ok, page) == [], check(snap, ok, page)
    short = {"datasets": ok["datasets"][1:]}
    assert any("missing from the mapping" in e for e in check(snap, short, page))
    no_reason = {"datasets": [{**ok["datasets"][0], "reason": ""}, ok["datasets"][1]]}
    assert any("without a reason" in e for e in check(snap, no_reason, page))
    assert any("totals table differs" in e for e in check(snap, ok, page.replace("| 3 |", "| 4 |")))
    assert any("no <!-- types -->" in e for e in check(snap, ok, page.replace("<!-- types -->", "")))
    assert any("not in the CKAN snapshot" in e for e in check(snap, {"datasets": ok["datasets"] + [{**ok["datasets"][0], "id": "z"}]}, page))
    assert attr("Dĺžka_premostenia___m") == "dlzkaPremosteniaM" and attr("IČO") == "iCO" and attr("2021") == "n2021"
    assert list(properties(["Rok", "rok", "Rók"], {"Rok": "integer", "rok": "string", "Rók": "string"})) == ["rok", "rok2", "rok3"]
    assert prop("id") == "sourceId" and prop("Typ") == "typ" and prop("type") == "sourceType"
    assert refresh("2026-10-15T09:00Z", "2026-10-16T04:00Z") == "P1D" and refresh("2024-01-01", "2026-10-16") == "P1W"
    assert refresh(None, "2026-10-16", "StatisticalObservation") == "P1M"
    print("selftest ok")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "--selftest":
        return selftest()
    if cmd in ("snapshot", "probe", "draft"):
        return {"snapshot": snapshot, "probe": probe, "draft": draft}[cmd]()
    import yaml
    errors = check(json.loads(SNAPSHOT.read_text(encoding="utf-8")),
                   yaml.safe_load(MAPPING.read_text(encoding="utf-8")), PAGE.read_text(encoding="utf-8"))
    for e in errors:
        print(f"bb-bbsk-ngsi-ld-mapping: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
