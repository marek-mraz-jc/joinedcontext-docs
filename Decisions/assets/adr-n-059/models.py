#!/usr/bin/env python3
"""Render one reference municipality under five tenancy models and count what each costs (ADR-N-059).

The municipality: 100 people in 8 departments, 12 Context Spaces, 40 Endpoints, 3 datasets one
department reads from another, 2 public datasets. Each model is written as a configuration
repository (jc-core PATH_TEMPLATEs) that `jcctl validate --repo-dir` checks, and counted:
manifests per kind, the Keycloak groups and clients, forge repositories and teams, app namespaces
and quotas they imply, and the Changes three everyday requests take.

    python3 models.py --table            # the ADR's comparison table
    python3 models.py --out DIR          # every model's repository under DIR/<model>/

Manifests are written as JSON, which is YAML; nothing here needs a package outside the stdlib.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

API = "joinedcontext.com/v1alpha1"
DOMAIN = "mesto.sk"
ORG = "mesto"
ONE_PROJECT = "mesto"

# (department, people, spaces, Endpoints per space): 100 people, 12 spaces, 40 Endpoints.
DEPARTMENTS = [
    ("doprava", 20, ["doprava-cesty", "doprava-parkovanie"], [4, 3]),
    ("zivotne-prostredie", 15, ["zp-ovzdusie", "zp-odpady"], [4, 3]),
    ("skolstvo", 15, ["skolstvo-skoly", "skolstvo-skolky"], [4, 3]),
    ("socialne", 12, ["socialne-sluzby", "socialne-davky"], [3, 3]),
    ("financie", 12, ["financie-rozpocet"], [4]),
    ("majetok", 10, ["majetok-budovy"], [3]),
    ("uzemne-planovanie", 8, ["up-plany"], [3]),
    ("primator", 8, ["primator-ukazovatele"], [3]),
]
PUBLIC = {"doprava-cesty-e1", "zp-ovzdusie-e1"}
# (owner's Endpoint, the department that reads it)
CROSS = [
    ("doprava-cesty-e2", "skolstvo"),
    ("skolstvo-skoly-e1", "socialne"),
    ("majetok-budovy-e1", "financie"),
]
LEADS = 2  # the first two people of a department edit its spaces

READ = [
    "retrieveOps",
    "createSubscription",
    "retrieveSubscription",
    "updateSubscription",
    "deleteSubscription",
]
WRITE = ["upsertBatch", "createBatch"]
VIEWER_KINDS = [
    "Organization",
    "Project",
    "ContextSpace",
    "Policy",
    "Endpoint",
    "SharedSpaceReference",
    "ServiceAccount",
    "Entity",
]
EDITOR_KINDS = [
    "ContextSpace",
    "DataModel",
    "Mapping",
    "Policy",
    "Endpoint",
    "Pipeline",
    "DataSource",
]

MODELS = {
    "A": "Project per department",
    "B": "Departments as Groups in one project",
    "C": "Spaces as the unit, shared Policies",
    "D": "Organization per department",
    "E": "Department attribute from Keycloak",
}


@dataclass(frozen=True)
class Town:
    """The municipality as data: who is in which department, and what is shared."""

    departments: list = field(default_factory=lambda: [list(d) for d in DEPARTMENTS])
    extra_people: tuple = ()  # (department, user) added by a scenario
    cross: tuple = tuple(CROSS)
    merged: tuple = ()  # (absorbed, into)

    def people(self) -> dict[str, list[str]]:
        out, n = {}, 0
        for dept, count, _spaces, _eps in self.departments:
            out[dept] = [f"u{n + i + 1:03d}@{{orgDomain}}" for i in range(count)]
            n += count
        for dept, user in self.extra_people:
            out[dept].append(user)
        for absorbed, into in self.merged:
            out[into] += out.pop(absorbed)
        return out

    def leads(self) -> dict[str, list[str]]:
        base = Town(departments=self.departments)
        out = {d: users[:LEADS] for d, users in base.people().items()}
        for absorbed, into in self.merged:
            out[into] += out.pop(absorbed)
        return out

    def owner(self, dept: str) -> str:
        return dict(self.merged).get(dept, dept)

    def spaces(self) -> list[tuple[str, str, list[str]]]:
        """(owning department, space, its Endpoint names)."""
        return [
            (self.owner(dept), space, [f"{space}-e{i + 1}" for i in range(eps)])
            for dept, _n, spaces, counts in self.departments
            for space, eps in zip(spaces, counts)
        ]


def slug(name: str) -> str:
    """A stable 32-character base32 slug, so every run renders the same repository."""
    return (
        base64.b32encode(hashlib.sha256(name.encode()).digest()).decode().lower()[:32]
    )


def entity_type(endpoint: str) -> str:
    return "Record" + "".join(part.capitalize() for part in endpoint.split("-"))


def doc(
    kind: str, name: str, namespace: str, spec: dict, title: str | None = None
) -> dict:
    meta = {"name": name, "namespace": namespace, "title": {"sk": title or name}}
    return {"apiVersion": API, "kind": kind, "metadata": meta, "spec": spec}


def policy_urn(space: str, name: str) -> str:
    return f"urn:ngsi-ld:Policy:{{orgDomain}}:{space}:{name}"


def rule(kind: str, who: str, operations: list[str], types: list[str]) -> dict:
    return {
        "assignee": {"kind": kind, "id": who},
        "operations": operations,
        "information": [{"entities": [{"type": t} for t in types]}],
    }


def group_subject(dept: str, model: str) -> dict:
    subject = {"group": f"dept-{dept}"}
    if model == "E":
        subject["source"] = "provider"
    return subject


def render(model: str, town: Town) -> dict[str, dict]:
    """Every manifest of the model, by repository path."""
    files: dict[str, dict] = {}
    per_dept = model in ("A", "D")
    space_scoped = model in ("C", "E")
    spaces = town.spaces()
    depts = sorted({d for d, _s, _e in spaces})
    project_of = {d: (d if per_dept else ONE_PROJECT) for d in depts}

    files[f"organizations/{ORG}.yaml"] = doc(
        "Organization",
        ORG,
        "org",
        {
            "domain": DOMAIN,
            "locales": ["sk"],
            "defaultLocale": "sk",
            "installation": True,
        },
        "Mesto",
    )
    # The two roles every model binds, as the development seed defines them (helsinki-role-*.yaml).
    files["users/roles/viewer.yaml"] = doc(
        "Role", "viewer", "org", {"rules": [{"kinds": VIEWER_KINDS, "verbs": ["read"]}]}
    )
    files["users/roles/editor.yaml"] = doc(
        "Role",
        "editor",
        "org",
        {
            "rules": [
                {"kinds": EDITOR_KINDS, "verbs": ["propose", "approve"]},
                {"kinds": ["RoleBinding"], "verbs": ["propose"]},
            ]
        },
    )
    if model == "D":
        for d in depts:
            files[f"organizations/{d}.yaml"] = doc(
                "Organization",
                d,
                "org",
                {"domain": f"{d}.{DOMAIN}", "locales": ["sk"], "defaultLocale": "sk"},
            )

    for project in sorted(set(project_of.values())):
        org = project if model == "D" else ORG
        files[f"projects/{project}/project.yaml"] = doc(
            "Project", project, "org", {"organizationRef": org}
        )
        own = [s for d, s, _e in spaces if project_of[d] == project]
        files[f"projects/{project}/access/serviceaccounts/pipelines.yaml"] = doc(
            "ServiceAccount",
            "pipelines",
            project,
            {
                "owner": {
                    "user": town.leads()[
                        next(d for d in depts if project_of[d] == project)
                    ][0]
                },
                "purpose": "The ingestion pipelines write the project's spaces",
                "roles": [
                    {"role": "space-writer", "scope": {"contextSpace": s}} for s in own
                ],
                "credentials": [{"kind": "oauth-client", "name": "main"}],
            },
        )

    readers_of = {ep: [] for _d, _s, eps in spaces for ep in eps}
    for ep, dept in town.cross:
        readers_of[ep].append(town.owner(dept))

    for dept, space, eps in spaces:
        project = project_of[dept]
        base = f"projects/{project}/spaces/{space}"
        files[f"{base}/space.yaml"] = doc(
            "ContextSpace", space, project, {"urnSegment": space, "isSandbox": False}
        )
        types = [entity_type(ep) for ep in eps]
        if space_scoped:
            files[f"{base}/policies/{space}-access.yaml"] = doc(
                "Policy",
                f"{space}-access",
                project,
                {
                    "contextSpaceRef": {"kind": "ContextSpace", "name": space},
                    "assigner": "did:web:{orgDomain}",
                    "rules": [
                        rule("group", f"dept-{dept}", READ, types),
                        rule("serviceAccount", "pipelines", WRITE, types),
                    ],
                },
            )
        for ep in eps:
            t = [entity_type(ep)]
            refs, extra = [], []
            if ep in PUBLIC:
                extra.append(("public", rule("role", "public", READ, t)))
            for reader in readers_of[ep]:
                extra.append((f"to-{reader}", rule("group", f"dept-{reader}", READ, t)))
            if space_scoped:
                refs.append(policy_urn(space, f"{space}-access"))
                for suffix, r in extra:
                    name = f"{ep}-{suffix}"
                    files[f"{base}/policies/{name}.yaml"] = doc(
                        "Policy",
                        name,
                        project,
                        {
                            "contextSpaceRef": {"kind": "ContextSpace", "name": space},
                            "assigner": "did:web:{orgDomain}",
                        }
                        | {"rules": [r]},
                    )
                    refs.append(policy_urn(space, name))
            else:
                rules = [
                    rule("group", f"dept-{dept}", READ, t),
                    rule("serviceAccount", "pipelines", WRITE, t),
                ]
                rules += [r for _s, r in extra]
                files[f"{base}/policies/{ep}-access.yaml"] = doc(
                    "Policy",
                    f"{ep}-access",
                    project,
                    {
                        "contextSpaceRef": {"kind": "ContextSpace", "name": space},
                        "assigner": "did:web:{orgDomain}",
                    }
                    | {"rules": rules},
                )
                refs.append(policy_urn(space, f"{ep}-access"))
            spec = {
                "contextSpaceRef": {"kind": "ContextSpace", "name": space},
                "slug": slug(ep),
            }
            if ep in PUBLIC:
                spec["audience"] = "public"
            else:
                allowed = {project} | {project_of[r] for r in readers_of[ep]}
                spec |= {"audience": "project-list", "allowedProjects": sorted(allowed)}
            spec["policyRefs"] = refs
            files[f"{base}/endpoints/{ep}.yaml"] = doc("Endpoint", ep, project, spec)
            for reader in readers_of[ep]:
                if project_of[reader] != project:
                    files[f"projects/{project_of[reader]}/shared/{ep}.yaml"] = doc(
                        "SharedSpaceReference",
                        ep,
                        project_of[reader],
                        {"endpointRef": {"project": project, "name": ep}, "alias": ep},
                    )

    people, leads = town.people(), town.leads()
    for d in depts:
        if model != "E":
            files[f"users/groups/dept-{d}.yaml"] = doc(
                "Group",
                f"dept-{d}",
                "org",
                {"members": [{"user": u} for u in people[d]]},
            )
        own = [s for o, s, _e in spaces if o == d]
        scopes = (
            [{"contextSpace": s} for s in own]
            if space_scoped
            else [{"project": project_of[d]}]
        )
        for scope in scopes:
            key = scope.get("contextSpace") or d
            files[f"users/assignments/{key}-viewers.yaml"] = doc(
                "RoleBinding",
                f"{key}-viewers",
                "org",
                {
                    "subjects": [group_subject(d, model)],
                    "role": "viewer",
                    "scope": scope,
                },
            )
            files[f"users/assignments/{key}-editors.yaml"] = doc(
                "RoleBinding",
                f"{key}-editors",
                "org",
                {
                    "subjects": [{"user": u} for u in leads[d]],
                    "role": "editor",
                    "scope": scope,
                },
            )
    return files


def repository(path: str) -> str:
    """ADR-N-029: a project's files live in its own repository, the rest in the organization's."""
    parts = path.split("/")
    return f"project:{parts[1]}" if parts[0] == "projects" else "organization"


def count(model: str, town: Town | None = None) -> dict[str, int]:
    town = town or Town()
    files = render(model, town)
    kinds: dict[str, int] = {}
    for d in files.values():
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    projects = kinds.get("Project", 0)
    rules = sum(
        len(d["spec"]["rules"]) for d in files.values() if d["kind"] == "Policy"
    )
    dept_rules = sum(
        1
        for d in files.values()
        if d["kind"] == "Policy"
        for r in d["spec"]["rules"]
        if r["assignee"]["kind"] == "group"
    )
    groups_in_git = kinds.get("Group", 0)
    provider_groups = len({d for d, _s, _e in town.spaces()}) if model == "E" else 0
    return {
        "Manifests": len(files),
        "Organization": kinds.get("Organization", 0),
        "Project": projects,
        "ContextSpace": kinds.get("ContextSpace", 0),
        "Endpoint": kinds.get("Endpoint", 0),
        "Policy": kinds.get("Policy", 0),
        "Policy rules": rules,
        "Rules naming a department": dept_rules,
        "Group manifests": groups_in_git,
        "RoleBinding": kinds.get("RoleBinding", 0),
        "SharedSpaceReference": kinds.get("SharedSpaceReference", 0),
        "ServiceAccount": kinds.get("ServiceAccount", 0),
        # Group manifests, the two derived groups per project (PF-87), one subtree per
        # Organization (ADR-N-058 2.5), and the department groups Keycloak owns in model E.
        "Keycloak groups": groups_in_git
        + 2 * projects
        + kinds["Organization"]
        + provider_groups,
        # One `{project}-pipelines` client per project that ingests (pipeline-runner keycloak-clients.yaml).
        "Keycloak clients": projects,
        "Forge repositories": 1 + projects,
        "Forge teams": 2 * projects,
        "App namespaces": projects,
        "Quota blocks": projects,
        "CKAN organisations": kinds["Organization"],
    }


SCENARIOS = {
    "a": (
        "Add a person to a department",
        lambda t: replace(t, extra_people=(("skolstvo", "u101@{orgDomain}"),)),
    ),
    "b": (
        "Give one department read on another's dataset",
        lambda t: replace(t, cross=t.cross + (("financie-rozpocet-e1", "primator"),)),
    ),
    "c": (
        "Merge two departments into one",
        lambda t: replace(t, merged=(("uzemne-planovanie", "majetok"),)),
    ),
}


def changes(model: str, scenario: str) -> tuple[int, int, int]:
    """(Changes, files, Keycloak edits outside Git): one Change per repository a request touches."""
    before = render(model, Town())
    town = SCENARIOS[scenario][1](Town())
    after = render(model, town)
    touched = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    outside = 0
    if model == "E":
        # Membership is a Keycloak attribute: each person whose department is new or changed.
        old, new = Town().people(), town.people()
        where = lambda people: {u: d for d, us in people.items() for u in us}
        o, n = where(old), where(new)
        outside = sum(1 for u in n if o.get(u) != n[u])
    return len({repository(p) for p in touched}), len(touched), outside


def table() -> str:
    cols = list(MODELS)
    rows = [count(m) for m in cols]
    lines = ["| Measure | " + " | ".join(f"{m}: {MODELS[m]}" for m in cols) + " |"]
    lines.append("|---|" + "---:|" * len(cols))
    for key in rows[0]:
        lines.append(f"| {key} | " + " | ".join(str(r[key]) for r in rows) + " |")
    for s, (label, _f) in SCENARIOS.items():
        cells = []
        for m in cols:
            ch, files, outside = changes(m, s)
            cell = f"{ch} Change{'s' if ch != 1 else ''}, {files} file{'s' if files != 1 else ''}"
            if outside:
                cell += f", {outside} Keycloak edit{'s' if outside != 1 else ''}"
            cells.append(cell)
        lines.append(f"| ({s}) {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write(out: Path, model: str, town: Town | None = None) -> Path:
    root = out / model
    for path, d in render(model, town or Town()).items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return root


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--table", action="store_true", help="print the ADR's comparison table"
    )
    parser.add_argument(
        "--out", type=Path, help="write each model's repository under this directory"
    )
    args = parser.parse_args(argv)
    if args.out:
        for m in MODELS:
            print(write(args.out, m))
    if args.table or not args.out:
        print(table())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
