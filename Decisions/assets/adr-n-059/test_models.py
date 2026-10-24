#!/usr/bin/env python3
"""ADR-N-059's numbers are the generator's, and every model it renders is a valid repository.

    JC_JCCTL=/path/to/jcctl pytest Decisions/assets/adr-n-059/test_models.py
    JC_JCCTL=/path/to/jcctl python3 Decisions/assets/adr-n-059/test_models.py   # without pytest

`jcctl validate` is the reconciler's own verdict, so the jcctl case fails when JC_JCCTL names no
binary rather than passing unchecked. Build it with `cargo build -p jcctl` in the platform.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import models

ADR = HERE.parent.parent / "adr-n-059-departments-and-the-unit-of-tenancy.md"
BEGIN = "<!-- begin table: python3 Decisions/assets/adr-n-059/models.py --table -->"
END = "<!-- end table -->"


def adr_table() -> str:
    text = ADR.read_text(encoding="utf-8")
    start, end = text.index(BEGIN) + len(BEGIN), text.index(END)
    return text[start:end].strip()


def test_the_adr_table_is_what_the_generator_counts():
    assert adr_table() == models.table(), (
        "rerun `models.py --table` and paste it between the markers"
    )


def test_the_reference_municipality_has_the_shape_the_adr_names():
    town = models.Town()
    people = town.people()
    assert len(people) == 8 and sum(map(len, people.values())) == 100
    spaces = town.spaces()
    assert len(spaces) == 12 and sum(len(eps) for _d, _s, eps in spaces) == 40
    assert len(models.PUBLIC) == 2 and len(town.cross) == 3
    for m in models.MODELS:
        c = models.count(m)
        assert (c["ContextSpace"], c["Endpoint"]) == (12, 40), m


def test_no_department_reads_another_without_a_policy_naming_it():
    """The security property every model keeps: a department group appears only in its own
    spaces' Policies, or in a rule written for one shared dataset."""
    for m in models.MODELS:
        town = models.Town()
        owner = {s: d for d, s, _e in town.spaces()}
        shared = {(ep, d) for ep, d in town.cross}
        for path, doc in models.render(m, town).items():
            if doc["kind"] != "Policy":
                continue
            space = doc["spec"]["contextSpaceRef"]["name"]
            for rule in doc["spec"]["rules"]:
                who = rule["assignee"]
                if who["kind"] != "group":
                    continue
                dept = who["id"].removeprefix("dept-")
                if dept == owner[space]:
                    continue
                types = {e["type"] for i in rule["information"] for e in i["entities"]}
                assert any(
                    models.entity_type(ep) in types and d == dept for ep, d in shared
                ), f"{m}: {path} lets {dept} read {space} without a shared dataset"


def test_urn_segments_stay_the_same_in_every_model():
    """The migration renames no space: each space pins the same segment wherever it lives."""
    seen = {}
    for m in models.MODELS:
        segs = {
            d["metadata"]["name"]: d["spec"]["urnSegment"]
            for d in models.render(m, models.Town()).values()
            if d["kind"] == "ContextSpace"
        }
        seen[m] = segs
    assert all(s == seen["A"] for s in seen.values())


def jcctl() -> str:
    found = os.environ.get("JC_JCCTL") or shutil.which("jcctl")
    assert found and Path(found).is_file(), (
        "set JC_JCCTL to a jcctl binary (cargo build -p jcctl)"
    )
    return found


def test_every_model_and_scenario_passes_jcctl_validate():
    binary = jcctl()
    with tempfile.TemporaryDirectory() as tmp:
        for m in models.MODELS:
            towns = [("base", models.Town())] + [
                (s, f(models.Town())) for s, (_l, f) in models.SCENARIOS.items()
            ]
            for label, town in towns:
                root = models.write(Path(tmp) / label, m, town)
                run = subprocess.run(
                    [binary, "validate", "--repo-dir", str(root)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                errors = [
                    line
                    for line in run.stderr.splitlines() + run.stdout.splitlines()
                    if line and not line.startswith("warning:")
                ]
                assert run.returncode == 0, f"model {m} ({label}): {errors}"


if __name__ == "__main__":
    failed = 0
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            try:
                test()
                print(f"ok   {name}")
            except AssertionError as err:
                failed += 1
                print(f"FAIL {name}: {err}")
    sys.exit(1 if failed else 0)
