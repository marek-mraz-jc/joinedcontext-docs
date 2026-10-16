#!/usr/bin/env python3
"""Every Banská Bystrica and BBSK dataset on data.dev, mapped to NGSI-LD or refused (T-4254).

The mapping file `Research/bb-bbsk-ngsi-ld-mapping.yaml` is what the seed generator (T-4255)
reads. It is built from two committed snapshots, never by hand: the CKAN `package_search`
answer of the two organizations and one probe of each resource. The type of each dataset comes
from TYPES below, the only judgement in this script; everything else is read.

    bb-bbsk-ngsi-ld-mapping.py snapshot   # CKAN package_search -> Research/data/bb-bbsk-ckan.json
    bb-bbsk-ngsi-ld-mapping.py probe      # one request per resource -> Research/data/bb-bbsk-probe.json
    bb-bbsk-ngsi-ld-mapping.py layers     # the city GIS layers LAYERS names -> Research/data/bb-dtm-layers.json
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
GIS_PROBE = ROOT / "Research/data/bb-dtm-layers.json"
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
    # The city's DTM (T-4317): a model where one fits (T-4319), else a type NO_MODEL removes.
    (r"dtm-bb-register-adries", "Address", "dataModel.CPSV-AP/Address", "the city's address points (DTM_BB), reprojected from S-JTSK"),
    (r"dtm-bb-register-stavby", "Building", None, "the city's building footprints (DTM_BB)"),
    (r"dtm-bb-register-ulic", "RoadSegment", None, "the city's street segments (DTM_BB)"),
    (r"dtm-bb-polohopis", "SurveyPoint", None, "the city's survey points (DTM_BB)"),
    (r"dtm-bb-vyskopis-teran", "TerrainFeature", None, "contour lines, their height labels and terrain edges (DTM_BB)"),
    (r"dtm-bb-register-chodnikov", "Footway", None, "the definition point of each footway and cycle path (DTM_BB)"),
    (r"dtm-bb-register-miestnych-komunikacii", "Road", None, "the definition point of each road (DTM_BB)"),
    (r"dtm-bb-register-statickej-dopravy", "OffStreetParking", "dataModel.Parking/OffStreetParking",
     "the definition point of each car park off the street (DTM_BB)"),
    (r"dtm-bb-register-stlpov-vo", "Streetlight", None, "the supports the DTM codes as street-light poles (DTM_BB)"),
    (r"dtm-bb-register-verejnej-zelene-1", "Garden", "dataModel.ParksAndGardens/Garden",
     "the definition point of each kept green area (DTM_BB)"),
    (r"dtm-bb-register-verejnej-zelene-2", "Tree", None, "single trees (DTM_BB)"),
    (r"dtm-bb-register-verejnej-zelene-3", "GreenAreaBoundary", None, "the edges of the kept green areas (DTM_BB)"),
    (r"dtm-bb-register-zvisleho-dopravneho", "TrafficSign", None, "traffic signs (DTM_BB)"),
    (r"dtm-bb-vodne-toky", "WaterBody", None, "the definition point of each stream, reservoir and channel (DTM_BB)"),
    (r"dtm-bb-(funkcne-vyuzitie|verejne-dopravne|tvorba-krajiny|regulativy|vyuzitie-pody|verejnoprospesne|zaujmove-uzemie)",
     "LandUsePlanFeature", None, "the land-use plan's drawing, one entity per feature of its layers (ÚPN)"),
    (r"nabijacky", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest",
     "a tourism-portal layer of places; no socket, capacity or vehicle column for EVChargingStation"),
    (r"nehodovost", "RoadAccident", "dataModel.Transportation/RoadAccident", ""),
    (r"cykloscitace", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "the counting sites; no counts in the layer"),
    (r"mosty", "Bridge", None, "the name of the bbsk-registre class"),
    (r"podjazdy|priepusty|dilatacne-celky|zeleznicne-priecestia", "RoadStructure", None, ""),
    (r"cykloturisticke-trasy-linie", "CycleRoute", None, ""),
    (r"cykloturisticke-trasy-nosic", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "signposts, boards and rest stops"),
    (r"lekarni|zdravotnickych", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "category from the facility kind"),
    (r"skoly|skolske", "Organization", "dataModel.Organization/Organization", "schools as schema.org organizations"),
    (r"kulturne-institucie|kontaktne-miesta", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", ""),
    (r"organizacie|prispevkove", "PublicOrganization", "dataModel.CPSV-AP/PublicOrganization", ""),
    (r"poskytovatelov-socialnych", "PointOfInterest", "dataModel.PointOfInterest/PointOfInterest", "a provider's place of service"),
    (r"kraj-bbk-hranica|okresy-bbk-hranice|obce-bbk-hranice|obce-bbk-centroidy", "AdministrativeArea", None, "the name of the bbsk-registre class"),
    (r"povodia", "RiverBasin", None, ""),
    (r"vodnych-utvarov", "WaterBodyStatus", None, "one row per water body and assessment"),
    (r"vyvoj-emisii|vyvoj-imisii", "KeyPerformanceIndicator", "dataModel.KeyPerformanceIndicator/KeyPerformanceIndicator", "one row per station or source and year"),
    (r"obyvatel|vekov|ohrozenie-samosprav|ppa-platby-po-okresoch", "KeyPerformanceIndicator", "dataModel.KeyPerformanceIndicator/KeyPerformanceIndicator", "one row per area (and year)"),
    (r"register-investicii|projekty-banskobystrickeho", "PublicInvestment", None, ""),
    (r"faktury", "Invoice", None, ""),
    (r"objednavky", "PurchaseOrder", None, ""),
    (r"zmluvy", "Contract", None, ""),
    (r"dotacie|ppa-platby", "Grant", None, ""),
    (r"dodavatelia", "Organization", "dataModel.Organization/Organization", "suppliers with an IČO"),
    (r"verejneho-obstaravania|verejne-obstaravania", "PublicProcurement", None, ""),
    (r"komisie", "CommitteeSeat", None, "committee seats; the citizens' names are kept out"),
    (r"clenovia", "Person", "dataModel.Organization/Person", "public office holders, published under Act 211/2000"),
    (r"hlasovania", "CouncilVote", None, "public office holders' votes"),
    (r"zasadnutia", "CouncilMeeting", None, ""),
    (r"peticie", "Petition", None, "the petition, not its signatories"),
    (r"vzn|nariadeni", "Regulation", None, ""),
    (r"uradne-hodiny", "OfficeHours", None, "one row per office and weekday"),
    (r"organizacna-struktura|kontakty-na-miestne", "Organization", "dataModel.Organization/Organization", ""),
    (r"bb-adresy", "Address", "dataModel.CPSV-AP/Address", "the city's address list, without coordinates"),
    (r"bb-aktuality", "Article", None, "the city's news (WordPress)"),
    (r"bb-podujatia", "Event", "dataModel.TourismDestinations/Event", "the name of the banskabystrica-verejne class"),
    (r"pocet-obcanov|prirastky", "KeyPerformanceIndicator", "dataModel.KeyPerformanceIndicator/KeyPerformanceIndicator", ""),
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
    names, encrypted, i = [], 0, 0
    while len(names) < count and cd[i:i + 4] == b"PK\x01\x02":
        flags, = struct.unpack("<H", cd[i + 8:i + 10])
        n, e, c = struct.unpack("<HHH", cd[i + 28:i + 34])
        names.append(cd[i + 46:i + 46 + n].decode("utf-8", "replace"))
        encrypted += bool(flags & 1) and not names[-1].endswith("/")
        i += 46 + n + e + c
    exts: dict[str, int] = {}
    for n in names:
        if "." in n and not n.endswith("/"):
            x = n.rsplit(".", 1)[1].lower()
            exts[x] = exts.get(x, 0) + 1
    return {**info, "members": len(names), "extensions": exts, "encrypted": encrypted}


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

    def range_of(k: str) -> str:
        seen = {type(v) for f in feats[:2000] if (v := (f.get("properties") or {}).get(k)) is not None}
        return "integer" if seen == {int} else "float" if seen and seen <= {int, float} else "string"
    return {"file": name, "features": len(feats), "fields": [{"name": k, "range": range_of(k)} for k in keys],
            "distinct": distinct,
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
            features = page.get("features", [])
            seen |= {tuple(f["attributes"].get(c) for c in cols) for f in features}
            if not page.get("exceededTransferLimit") or not features:
                break
            # A layer serves at most its maxRecordCount (1000 on the BBSK Hub), not the 2000 asked:
            # stepping by 2000 skipped every other page and took Číslo_nehody's 3046 values for 2000.
            offset += len(features)
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
    return "P1M" if typ == "KeyPerformanceIndicator" else "P1W"


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


# Each model's schema.json was read at this commit of its subject repository (T-4319): a model is
# named only after its schema was opened, and the seed validates against these same files.
SDM_SHA = {
    "dataModel.CPSV-AP": "a05d1663475fc0f79361bc9bc2550c3f24df1ba0",
    "dataModel.KeyPerformanceIndicator": "ec7f3b642faf3f807d3c8549ccc9e0b743e05f26",
    "dataModel.Organization": "77a4911e7cbc72bf87bf202ade282c1bc41a36a4",
    "dataModel.Parking": "24342efb3425c0059c7a4b82d6d201847418b29c",
    "dataModel.ParksAndGardens": "4563de6c0ab462ab7db73bfc4ca90dbacfa0421d",
    "dataModel.PointOfInterest": "7e5e24963a142b9bf6fd15b144a0e24588217608",
    "dataModel.TourismDestinations": "6d78cb4ff0c1a7d16dc0c1bab7266e40d4b3a00c",
    "dataModel.Transportation": "b83ede9d3db29be1365cc272eb535f46af83bed2",
}
# A type no published Smart Data Model holds: its datasets leave data.dev (owner, 2026-10-16,
# T-4319). Each names the models opened and why none fits, so it can come back when one does.
FINANCE = "no subject of the official list (2026-07-19) holds orders, invoices, contracts or procurement"
COUNCIL = ("no subject holds council meetings, votes, petitions or regulations; "
           "CPSV-AP has PublicService, BusinessEvent and LifeEvent")
NO_MODEL: dict[str, str] = {
    "Bridge": ("Transportation/Road and RoadSegment describe roads; RoadSegment requires refRoad, startPoint and "
               "endPoint, which a bridge register has not"),
    "RoadStructure": ("Transportation/Road and RoadSegment describe roads, not underpasses, culverts, expansion "
                      "joints or level crossings"),
    "AdministrativeArea": ("OpenStreetMap/OSMBoundary requires osmId and osmType; these boundaries come from the "
                           "region's register, not OpenStreetMap"),
    "RiverBasin": "OpenStreetMap/OSMWater requires osmId and osmType; the basins come from the region's register",
    "WaterBodyStatus": ("WaterQuality/WaterQualityObserved and Environment/WaterObserved require dateObserved and "
                        "location and hold measured parameters; these rows are ecological status classes"),
    "CycleRoute": ("OpenStreetMap/OSMCycleRoute requires osmId and osmType; Transportation/BikeLane is a lane, "
                   "not a touring route"),
    "Grant": "no subject of the official list (2026-07-19) holds grants or subsidies",
    "PublicInvestment": "no subject of the official list (2026-07-19) holds public investment projects",
    "PurchaseOrder": FINANCE,
    "Invoice": FINANCE,
    "Contract": FINANCE,
    "PublicProcurement": FINANCE,
    "CouncilMeeting": COUNCIL,
    "CouncilVote": COUNCIL,
    "Petition": COUNCIL,
    "Regulation": COUNCIL,
    "CommitteeSeat": "Organization/Person is a person; a seat whose holder's name is kept out is none",
    "OfficeHours": "a row is one office's hours on one weekday; no model holds an opening slot as an entity",
    "Article": "no subject of the official list (2026-07-19) holds news articles",
    # The city's DTM (T-4317, models read 2026-10-16). An OpenStreetMap model (OSMBuilding,
    # OSMHighway, OSMTrafficSign, OSMLanduse, OSMWater, OSMNatural) requires osmId and osmType, and
    # none of these features comes from OpenStreetMap.
    "Building": "Building/Building requires address and category; the register has neither (municipality and district only)",
    "RoadSegment": ("Transportation/RoadSegment requires refRoad, startPoint, endPoint and allowedVehicleType, "
                    "which a street register has not"),
    "Road": "Transportation/Road requires name and roadClass; a DTM road point has neither, only a surface code",
    "Streetlight": ("Streetlighting/Streetlight requires status (ok, defectiveLamp, columnIssue, brokenLantern); "
                    "the DTM records whether a pole is operated, not the state of its lamp"),
    "SurveyPoint": "no subject of the official list (2026-07-19) holds geodetic survey points",
    "TerrainFeature": "no subject of the official list (2026-07-19) holds contour lines or terrain edges",
    "Footway": "Transportation/BikeLane is a lane on a road; no model holds a footway or a pavement",
    "Tree": "ParksAndGardens has Garden, FlowerBed and GreenspaceRecord (a measurement); no model holds a single tree",
    "GreenAreaBoundary": "ParksAndGardens/Garden is the area; no model holds the line around it",
    "TrafficSign": "no subject of the official list (2026-07-19) holds a traffic sign but OpenStreetMap's",
    "WaterBody": ("OpenChannelManagement/OpenChannel is a hydraulic model of a channel (cross sections, "
                  "flow); Environment/WaterObserved is a measurement; no model holds a stream or a reservoir"),
    "LandUsePlanFeature": ("dataModel.UrbanPlanning holds no model yet; no other subject holds a land-use plan's "
                           "zones, limits or planned works"),
}
# A column that is a model attribute takes the model's name (dataset pattern -> attribute -> model
# attribute); the first matching pattern applies. `name` is the GSMA common name every model has.
RENAME: list[tuple[str, dict[str, str]]] = [
    (r"skoly-a-skolske-zariadenia", {"nazovZauzivany": "name", "nazovOficialny": "legalName"}),
    (r"materske-skoly|stredne-skoly|zakladne-skoly", {"nazov": "name"}),
    (r"vysoke-skoly", {"fakulta": "name"}),
    (r"kontakty-na-miestne", {"obecDlhyNazov": "name"}),
    (r"organizacna-struktura", {"utvarNazov": "name"}),
    (r"dodavatelia", {"nazov": "legalName"}),
    (r"organizacie-v-zriadovatelskej", {"oficialnyNazov": "preferredLabel", "obecNazov": "spatial"}),
    (r"prispevkove", {"nazovOrganizacie": "preferredLabel", "obec": "spatial"}),
    (r"bb-adresy", {"ulica": "thoroughfare", "castObce": "addressArea", "obec": "postName"}),
    (r"dtm-bb-register-adries", {"uLICA": "thoroughfare", "cASTOBCE": "addressArea", "oBEC": "postName", "pSC": "postCode"}),
    (r"bb-podujatia", {"link": "url", "content": "description"}),
    (r"cykloscitace", {"miesto": "name"}),
    (r"nabijacky", {"pRIMNAME": "name", "name": "sourceName"}),
    (r"poskytovatelov-socialnych", {"obchodneMeno": "name"}),
    (r"kontaktne-miesta", {"nazovOrganizacie": "name"}),
    (r"kulturne-institucie-bbsk-a-ich", {"institucia1": "name"}),
    (r"kulturne-institucie-bbsk-[0-9a-f]{6}$", {"institucia": "name"}),
    (r"zoznam-lekarni", {"nazov": "name"}),
    (r"zdravotnickych", {"vlastnyNazovZariadenia": "name"}),
]
# Model attributes whose value is a list of text (CPSV-AP, PointOfInterest category): one column becomes a one-item list.
# A model attribute whose column is empty in some rows reads these columns next, in order: a
# PointOfInterest needs a name, and 2288 health facilities have no name of their own, 174 places
# of the tourism portal no PRIM_NAME (T-4319).
OTHERWISE: list[tuple[str, dict[str, list[str]]]] = [
    (r"nabijacky", {"name": ["Categ"]}),
    (r"zdravotnickych", {"name": ["Názov_poskytovateľa"]}),
]
LISTS = {"thoroughfare", "addressArea", "postName", "postCode", "spatial", "category"}
# Attributes a model requires that no column holds: the same value on every entity of the type.
# A RoadAccident row is an accident the police closed and published, so `archived`.
CONSTANTS: dict[str, dict[str, str]] = {"RoadAccident": {"status": "archived"}}


def sdm_schema(sdm: str) -> str:
    """The schema.json of a model at the commit it was read at."""
    subject, model = sdm.split("/")
    return f"https://raw.githubusercontent.com/smart-data-models/{subject}/{SDM_SHA[subject]}/{model}/schema.json"


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


def modelled(name: str, props: dict[str, dict]) -> dict[str, dict]:
    """The columns a model names take its attribute names; a list attribute reads one column."""
    renames = next((r for pat, r in RENAME if re.search(pat, name)), {})
    absent = [a for a in renames if a not in props]
    if absent:
        sys.exit(f"{name}: RENAME names {absent}, which the mapping does not have")
    clash = [m for m in renames.values() if m in props and m not in renames]
    if clash:
        sys.exit(f"{name}: RENAME to {clash}, which another column already is")
    out = {renames.get(a, a): p for a, p in props.items()}
    for a, cols in next((o for pat, o in OTHERWISE if re.search(pat, name)), {}).items():
        known = {p["column"] for p in out.values()}
        if a not in out or not set(cols) <= known:
            sys.exit(f"{name}: OTHERWISE names {a} or {cols}, which the mapping does not read")
        out[a] = {**out[a], "otherwise": cols}
    return {a: {**p, "range": "string-list"} if a in LISTS else p for a, p in out.items()}


def type_of(name: str):
    for pattern, typ, sdm, note in TYPES:
        if re.search(pattern, name):
            return typ, sdm, note
    return None


# Keys the probe does not find: a column without an id-like name, or one it counted before the
# paging fix above. Each checked unique and never empty over the whole source on 2026-10-16
# (T-4332). A key keeps one entity per row when a value changes; a row hash makes a second one.
KEYS: dict[str, list[str]] = {
    "bb-pocet-obcanov-podla-dna-narodenia": ["Deň", "Pohlavie"],  # 732 rows, 732 pairs
    "bb-pocet-obcanov-podla-veku": ["Vek"],  # 105 rows
    "bb-prirastky-a-ubytky-obcanov-za-jednotlive-roky": ["Rok"],  # 27 rows
    "bbsk-cyklisti-nehodovost-addf0f": ["Rok", "obdobie", "parameter", "Územie"],  # 81 rows
    "bbsk-nabijacky-a-zastavky-937210": ["CMS_ID"],  # 606 rows
    "bbsk-nehodovost-v-bbk-0ea72d": ["Číslo_nehody"],  # 3046 rows
    "bbsk-prispevkove-rozpoctove-a-ine-organizacie-samospravy-cec768": ["IČO_organizácie"],  # 126 rows
}


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
    (r"dtm-bb-register-adries", ["POINT_X", "POINT_Y"], "the point in S-JTSK; the location carries it in WGS 84"),
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
    (r"nabijacky", "Categ", "Categ IS NOT NULL AND Categ <> ''", None,
     "three rows of the layer hold nothing but a point, no name and no category"),
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
OBSERVED = {"KeyPerformanceIndicator", "RoadAccident"}
# A ZIP whose GeoJSON is larger than this is not loaded in this round (16 GB node, one broker).
ZIP_LIMIT = 10 << 20
# A source with more rows than this waits for a later round: 240 636 survey points would double
# the broker's entities for the least-asked question.
ROW_LIMIT = 100_000

# The city's public ArcGIS Server 11.1 (found 2026-10-16, T-4317): its DTM and its land-use plan
# (ÚPN) as query layers that answer GeoJSON in WGS 84 themselves (outSR=4326), so no step reprojects.
# A DTM_BB dataset whose ZIP holds a map sheet, a locked shapefile or a file too big to load reads
# the layers its sheet draws: (name pattern, [(service or service prefix, layer or None for every
# thematic layer of it, where)]). Decided (worker-2, owner may override): the three archives with
# their own GeoJSON (addresses, streets, buildings) stay on the archive, whose register columns
# the layers lack; the three greenery sheets are the green areas (OE_19), the trees (the locked
# shapefile's point layer) and the edges of the green areas.
GIS = "https://dtm-banskabystrica.tmapserver.sk/arcgis/rest/services"
DTM = "dtm/DTM_v_1_4_2_3_verejny"
LAYERS: list[tuple[str, list[tuple[str, int | None, str | None]]]] = [
    (r"dtm-bb-polohopis", [(DTM, 1, None)]),
    (r"dtm-bb-vyskopis-teran", [(DTM, 136, None), (DTM, 135, None), (DTM, 79, None)]),
    (r"dtm-bb-register-chodnikov", [(DTM, 4, None), (DTM, 5, None)]),
    (r"dtm-bb-register-miestnych-komunikacii", [(DTM, 3, None)]),
    (r"dtm-bb-register-statickej-dopravy", [(DTM, 6, None)]),
    (r"dtm-bb-register-stlpov-vo", [(DTM, 226, "typpodpernehozarizeni=3")]),
    (r"dtm-bb-register-verejnej-zelene-1", [(DTM, 57, None)]),
    (r"dtm-bb-register-verejnej-zelene-2", [(DTM, 128, None)]),
    (r"dtm-bb-register-verejnej-zelene-3", [(DTM, 88, None)]),
    (r"dtm-bb-register-zvisleho-dopravneho", [(DTM, 175, None)]),
    (r"dtm-bb-vodne-toky", [(DTM, 51, None), (DTM, 23, None), (DTM, 26, None)]),
    (r"dtm-bb-zaujmove-uzemie", [("up/02___", None, None)]),
    (r"dtm-bb-funkcne-vyuzitie", [("up/3a___", None, None)]),
    (r"dtm-bb-verejne-dopravne", [("up/04___", None, None), ("up/5a_", None, None), ("up/5b___", None, None), ("up/5c___", None, None)]),
    (r"dtm-bb-tvorba-krajiny", [("up/06___", None, None)]),
    (r"dtm-bb-regulativy", [("up/7a___", None, None), ("up/7b___", None, None), ("up/7c___", None, None)]),
    (r"dtm-bb-vyuzitie-pody", [("up/8___", None, None)]),
    (r"dtm-bb-verejnoprospesne", [("up/10___", None, None)]),
]
# What a land-use plan service draws under its own layers: the cadastral map (the ÚGKK's, not the
# city's, 295 000 lines in every service) and the masks; never an entity.
GIS_BASEMAP = re.compile(r"^(vnutorn[aá] kresba|hranice parcel|maska( zu)?)$", re.I)
# Geodatabase bookkeeping, and who entered or edited a feature (an editor's name or account). The
# DTM's own `id` is empty on all but 3 of the 25 000 features counted (layers 4, 57, 128, 136, 175,
# 226; 2026-10-16), and as text it would turn every model's `sourceId` from a number into a string.
GIS_SKIP = re.compile(r"^(id|objectid|globalid|fid|shape|shape_length|shape_area|shape_leng|st_length\(shape\)|"
                      r"created_date|last_edited_date)$", re.I)
GIS_PERSON = re.compile(r"^(vkladosoba|zmenaosoba|ideditora|created_user|last_edited_user)$", re.I)


def gis_layers() -> None:
    """Name, geometry, row count and fields of every layer LAYERS names, one service at a time."""
    status, _, body = get(f"{GIS}/up?f=json")
    services = [s["name"] for s in json.loads(body)["services"]] if status == 200 else []
    out = {"fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "source": GIS, "layers": {}}
    for _, parts in LAYERS:
        for svc, layer, where in parts:
            name = svc if layer is not None else next(s for s in services if s.startswith(svc))
            base = f"{GIS}/{urllib.parse.quote(name)}/MapServer"
            _, _, body = get(f"{base}/layers?f=json", limit=1 << 24)
            for m in json.loads(body)["layers"]:
                if (layer is not None and m["id"] != layer) or m["type"] != "Feature Layer" or GIS_BASEMAP.match(m["name"].strip()):
                    continue
                q = urllib.parse.urlencode({"where": where or "1=1", "returnCountOnly": "true", "f": "json"})
                _, _, cnt = get(f"{base}/{m['id']}/query?{q}")
                out["layers"][f"{name}/{m['id']}"] = {
                    "url": f"{base}/{m['id']}", "name": m["name"].strip(), "geometry": m.get("geometryType"),
                    "count": json.loads(cnt or b"{}").get("count"), **({"where": where} if where else {}),
                    "fields": [{"name": f["name"], "type": f["type"].removeprefix("esriFieldType")} for f in m.get("fields") or []]}
                print(name[:40].ljust(40), m["id"], out["layers"][f"{name}/{m['id']}"]["count"], m["name"].strip(), flush=True)
    GIS_PROBE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def gis_source(d: dict, gis: dict) -> tuple[dict, list[str], dict[str, str], list[str]] | None:
    """The `esri-layers` source of a dataset LAYERS names: its layers that hold rows, the union of
    their columns with the range each takes, and the person columns kept out. None: no rule."""
    parts = next((p for pat, p in LAYERS if re.search(pat, d["name"])), None)
    if parts is None:
        return None
    layers, fields, ranges, dropped = [], [], {}, []
    for svc, layer, _ in parts:
        for key, m in gis.items():
            name, lid = key.rsplit("/", 1)
            if not name.startswith(svc) or (layer is not None and int(lid) != layer) or not m["count"] or not m["geometry"]:
                continue
            if any((x["name"], x["rows"]) == (m["name"], m["count"]) for x in layers):
                continue  # one layer the plan draws in two sheets (Telekomunikačné vedenie in 5b and 5c)
            kept = [f for f in m["fields"] if not GIS_SKIP.match(f["name"]) and not GIS_PERSON.match(f["name"])]
            dropped += [f["name"] for f in m["fields"] if GIS_PERSON.match(f["name"]) and f["name"] not in dropped]
            for f in kept:
                r = RANGES.get(f["type"], "string")
                seen = ranges.setdefault(f["name"], r)
                ranges[f["name"]] = r if seen == r else "float" if {seen, r} <= {"integer", "float"} else "string"
                if f["name"] not in fields:
                    fields.append(f["name"])
            short = "dtm" if name == DTM else name.removeprefix("up/").split("_")[0]
            layers.append({"url": m["url"], "key": f"{short}-{lid}", "name": m["name"], "rows": m["count"],
                           **({"where": m["where"]} if m.get("where") else {}), "fields": [f["name"] for f in kept]})
    source = {"kind": "esri-layers", "geometry": True, "rows": sum(x["rows"] for x in layers), "layers": layers}
    return source, fields, ranges, dropped


KEY_HINT = re.compile(r"^(id\w*|\w*_id|kod\w*|\w*_kod|ico|idn\d|lau\d?_code|\w*cislo\w*|nuts\w*|identifik\w*)$", re.I)


def plan(d: dict, probe_: dict, fetched: str, gis: dict | None = None) -> dict:
    """One mapping entry: mapped (with its source resource), already NGSI-LD, or not ingestible."""
    entry = {"id": d["id"], "name": d["name"], "org": d["org"], "title": d["title"]}
    if d["extras"].get("generated_by"):
        return {**entry, "status": "already-ngsi-ld",
                "reason": "published by the platform from its own public Endpoint (jcctl ckan-publisher)"}
    by_fmt = {r["format"].upper(): (r, probe_.get(r["id"], {})) for r in d["resources"]}
    layered = gis_source(d, gis or {})
    if layered:
        source, fields, ranges, gis_dropped = layered
        p = {}
        if not source["layers"]:
            return {**entry, "status": "no-data-source", "reason": "no layer LAYERS names holds a feature",
                    "tried": [f"{GIS}/{svc}" for svc, _, _ in next(p for pat, p in LAYERS if re.search(pat, d["name"]))]}
        # The layer and the feature's own id, which the pipeline writes into each row (T-4317).
        fields, ranges = [*fields, "vrstva"], {**ranges, "vrstva": "string"}
    elif "ESRI REST" in by_fmt:
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
        # The pipeline unpacks the ZIP and reprojects S-JTSK to WGS 84 itself (T-4317).
        r, p = by_fmt["ZIP"]
        fields = [f["name"] for f in p["fields"]]
        ranges = {f["name"]: f.get("range", "string") for f in p["fields"]}
        source = {"kind": "zip-geojson", "url": r["url"], "member": p["file"], "crs": "EPSG:5514",
                  "geometry": True, "rows": p["features"]}
    elif "ZIP" in by_fmt:
        r, p = by_fmt["ZIP"]
        exts = p.get("extensions", {})
        shp = "shp" in exts
        why = (f"a ZIP of {', '.join(f'{n} .{x}' for x, n in sorted(exts.items()))} ({p.get('size', 0) // 1024} KiB)"
               if exts else f"a ZIP that answered {p.get('status')}")
        if exts and p.get("encrypted") == sum(exts.values()):
            # Found on 2026-10-16 (T-4317): every member needs a password, so the archive is no
            # open data at all, whatever format sits inside.
            return {**entry, "status": "no-data-source", "reason": why + ": every member is encrypted (a password is required)",
                    "tried": [r["url"]]}
        if "geojson" in exts:
            why += f": larger than the {ZIP_LIMIT >> 20} MiB this round loads into the one broker"
        elif shp:
            why += ": Esri shapefiles; no ingestion path reads a shapefile today"
        elif set(exts) == {"pdf"}:
            # Looked for as data on 2026-10-16 (T-4317): the T-MAPY host serves no OGC service
            # (/-/wfs/ and /-/wms/ answer its map application, whose GraphQL sits behind its own
            # sign-in), and the national catalogue lists this ZIP as the only distribution. With
            # no data found, data.dev hides the dataset (owner 2026-10-16: no ZIP-only dataset).
            # The city's ArcGIS services came after (LAYERS): a sheet still here has no layer there.
            host = urllib.parse.urlsplit(r["url"])
            return {**entry, "status": "no-data-source",
                    "reason": why + ": a PDF map sheet, and no layer of the city's ArcGIS services holds its data",
                    "tried": [r["url"], f"{host.scheme}://{host.netloc}/-/wfs/?service=WFS&request=GetCapabilities",
                              f"{host.scheme}://{host.netloc}/-/wms/?service=WMS&request=GetCapabilities",
                              "https://data.slovensko.sk/api/sparql (dcat:distribution of "
                              f"{d['extras'].get('source_uri') or d['name']})",
                              f"{GIS}/{DTM}/MapServer/layers?f=json (247 layers)", f"{GIS}/up?f=json (14 land-use plan services)"]}
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
    if typ in NO_MODEL:
        # The layers a DTM sheet would read stay named, so it comes back when a model does (T-4317).
        return {**entry, "status": "removed", "type": typ, "reason": f"no smart data model: {NO_MODEL[typ]}",
                **({"layers": [x["url"] for x in source["layers"]]} if layered else {})}
    rows = source["rows"]
    # A key is a column (or column and year) the probe counted as many distinct values as rows;
    # a WordPress post id is unique by definition. Anything else is a row hash.
    unique = [k.split("+") for k, n in (p.get("distinct") or {}).items() if n == rows and all(c in fields for c in k.split("+"))]
    if source["kind"] == "json-feed" and "id" in fields:
        unique = [["id"]]
    if source["kind"] == "esri-layers":
        unique = [["vrstva_id"]]
    if d["name"] in KEYS:
        missing = [c for c in KEYS[d["name"]] if c not in fields]
        if missing:
            sys.exit(f"{d['name']}: KEYS names {missing}, which the source does not have")
        unique = [KEYS[d["name"]]]
    observed = next((f for f in fields if re.search(r"d[aá]tum|date|rok$|^rok|year|obdobie", f, re.I)), None) if typ in OBSERVED else None
    dropped = next(((cols, why) for pat, cols, why in DROP if re.search(pat, d["name"])), ([], ""))
    if layered and gis_dropped:
        dropped = (gis_dropped, "who entered or edited a feature: an editor's name or account")
    absent = [] if layered else [c for c in dropped[0] if c not in fields]  # a layer leaves them out itself
    if absent:
        sys.exit(f"{d['name']}: DROP names {absent}, which the source does not have")
    fields = [f for f in fields if f not in dropped[0]]
    out = {**entry, "status": "mapped", "type": typ, "smartDataModel": sdm, "source": source,
           "entityId": {"keys": unique[0]} if unique else {"rowHash": True},
           "observedAt": observed, "space": SPACE[d["org"]],
           "refresh": "P1D" if source["kind"] == "json-feed" else "P1W" if layered else refresh(d["extras"].get("modified"), fetched, typ),
           "dataProvider": d["extras"].get("publisher_name"), "license": d["license"],
           "dataset": f"{CKAN}/dataset/{d['name']}",
           "properties": modelled(d["name"], properties(fields, ranges))}
    if typ in CONSTANTS:
        out["constants"] = dict(CONSTANTS[typ])
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
    gis = json.loads(GIS_PROBE.read_text(encoding="utf-8"))["layers"] if GIS_PROBE.exists() else {}
    entries = [plan(d, probe_, snap["fetched"], gis) for d in snap["datasets"]]
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
            row = t.setdefault(org, {"datasets": 0, "mapped": 0, "already-ngsi-ld": 0, "not-ingestible": 0, "removed": 0,
                                     "no-data-source": 0, "rows": 0})
            row["datasets"] += 1
            row[e["status"]] += 1
            row["rows"] += ((e.get("source") or {}).get("rows") or 0) if e["status"] == "mapped" else 0
    return {k: t[k] for k in [*ORGS, "all"] if k in t}


def totals_table(t: dict) -> str:
    lines = ["| organization | datasets | mapped | already NGSI-LD | not ingestible | removed (no model) | no data source "
             "| source rows of the mapped |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for org, r in t.items():
        lines.append(f"| {org} | {r['datasets']} | {r['mapped']} | {r['already-ngsi-ld']} | {r['not-ingestible']} "
                     f"| {r['removed']} | {r['no-data-source']} | {r['rows']} |")
    return "\n".join(lines)


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def sections(snap: dict, entries: list[dict]) -> dict[str, str]:
    """Every table of the page, built from the mapping: the page holds no number of its own."""
    mapped = [e for e in entries if e["status"] == "mapped"]
    by_type: dict[str, list[dict]] = {}
    for e in mapped:
        by_type.setdefault(e["type"], []).append(e)
    types = ["| NGSI-LD type | Smart Data Model (the schema read) | datasets | source rows |", "|---|---|---:|---:|"]
    for t, es in sorted(by_type.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        sdm = es[0]["smartDataModel"]
        model = f"[`{sdm}`]({sdm_schema(sdm)})" if sdm else "none"
        types.append(f"| `{t}` | {model} | {len(es)} | {sum(e['source']['rows'] for e in es)} |")
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
        if st not in ("mapped", "already-ngsi-ld", "not-ingestible", "removed", "no-data-source"):
            errors.append(f"{e.get('name')}: status {st!r}")
        elif st != "mapped" and not e.get("reason"):
            errors.append(f"{e.get('name')}: {st} without a reason")
        elif st == "no-data-source" and not e.get("tried"):
            errors.append(f"{e.get('name')}: no-data-source without the URLs tried")
        elif st == "mapped":
            missing = [k for k in ("type", "smartDataModel", "source", "entityId", "space", "refresh", "properties")
                       if not e.get(k)]
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
                       {"id": "b", "name": "y", "title": "Y", "org": "bbsk", "status": "mapped", "type": "T", "space": "s", "smartDataModel": "dataModel.Organization/Organization",
                        "source": {"rows": 3}, "entityId": {"rowHash": True}, "refresh": "P1D", "properties": {"a": "A"}}]}
    page = fill("x\n" + "".join(f"<!-- {n} -->\n<!-- /{n} -->\n" for n in sections(snap, [])), sections(snap, ok["datasets"]))
    assert fill(page, sections(snap, ok["datasets"])) == page
    assert check(snap, ok, page) == [], check(snap, ok, page)
    short = {"datasets": ok["datasets"][1:]}
    assert any("missing from the mapping" in e for e in check(snap, short, page))
    no_reason = {"datasets": [{**ok["datasets"][0], "reason": ""}, ok["datasets"][1]]}
    assert any("without a reason" in e for e in check(snap, no_reason, page))
    untried = {"datasets": [{**ok["datasets"][0], "status": "no-data-source"}, ok["datasets"][1]]}
    assert any("without the URLs tried" in e for e in check(snap, untried, page))
    assert any("totals table differs" in e for e in check(snap, ok, page.replace("| 3 |", "| 4 |")))
    assert any("no <!-- types -->" in e for e in check(snap, ok, page.replace("<!-- types -->", "")))
    assert any("not in the CKAN snapshot" in e for e in check(snap, {"datasets": ok["datasets"] + [{**ok["datasets"][0], "id": "z"}]}, page))
    assert attr("Dĺžka_premostenia___m") == "dlzkaPremosteniaM" and attr("IČO") == "iCO" and attr("2021") == "n2021"
    assert list(properties(["Rok", "rok", "Rók"], {"Rok": "integer", "rok": "string", "Rók": "string"})) == ["rok", "rok2", "rok3"]
    assert prop("id") == "sourceId" and prop("Typ") == "typ" and prop("type") == "sourceType"
    assert refresh("2026-10-15T09:00Z", "2026-10-16T04:00Z") == "P1D" and refresh("2024-01-01", "2026-10-16") == "P1W"
    assert refresh(None, "2026-10-16", "KeyPerformanceIndicator") == "P1M"
    no_model = {"datasets": [ok["datasets"][0], {**ok["datasets"][1], "smartDataModel": None}]}
    assert any("mapped without smartDataModel" in e for e in check(snap, no_model, page))
    removed = {"datasets": [ok["datasets"][0], {**ok["datasets"][1], "status": "removed", "reason": "no smart data model: x"}]}
    assert not any(e.startswith("y: status") or "without a reason" in e for e in check(snap, removed, page))
    adr = {"ulica": {"column": "Ulica", "range": "string"}, "obec": {"column": "Obec", "range": "string"},
           "castObce": {"column": "C", "range": "string"}}
    assert modelled("bb-adresy", adr) == {"thoroughfare": {"column": "Ulica", "range": "string-list"},
                                          "postName": {"column": "Obec", "range": "string-list"},
                                          "addressArea": {"column": "C", "range": "string-list"}}
    assert modelled("bb-other", adr) == adr
    assert sdm_schema("dataModel.Organization/Person").endswith("/77a4911e7cbc72bf87bf202ade282c1bc41a36a4/Person/schema.json")
    up = f"{GIS}/up/5b___x/MapServer"
    layer = lambda n, c, f: {"url": f"{up}/{n}", "name": "Telekomunikačné vedenie", "geometry": "esriGeometryPolyline",  # noqa: E731
                             "count": c, "fields": [{"name": x, "type": t} for x, t in f]}
    gis = {"up/5b___x/11": layer(11, 3, [("OBJECTID", "OID"), ("Typ", "String"), ("vkladosoba", "String")]),
           "up/5c___y/12": layer(12, 3, [("OBJECTID", "OID"), ("Typ", "String")]),
           "up/5c___y/13": {**layer(13, 0, []), "name": "Empty"}}
    src, fields, ranges, dropped = gis_source({"name": "bb-dtm-bb-verejne-dopravne-a"}, gis)
    assert [x["key"] for x in src["layers"]] == ["5b-11"] and src["rows"] == 3, src  # read once, the empty one skipped
    assert fields == ["Typ"] and ranges == {"Typ": "string"} and dropped == ["vkladosoba"]
    assert gis_source({"name": "bb-adresy"}, gis) is None
    assert GIS_BASEMAP.match("vnutorná kresba") and GIS_BASEMAP.match("Hranice parcel") and not GIS_BASEMAP.match("Funkčné plochy")
    print("selftest ok")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "--selftest":
        return selftest()
    if cmd in ("snapshot", "probe", "layers", "draft"):
        return {"snapshot": snapshot, "probe": probe, "layers": gis_layers, "draft": draft}[cmd]()
    import yaml
    errors = check(json.loads(SNAPSHOT.read_text(encoding="utf-8")),
                   yaml.safe_load(MAPPING.read_text(encoding="utf-8")), PAGE.read_text(encoding="utf-8"))
    for e in errors:
        print(f"bb-bbsk-ngsi-ld-mapping: {e}", file=sys.stderr)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
