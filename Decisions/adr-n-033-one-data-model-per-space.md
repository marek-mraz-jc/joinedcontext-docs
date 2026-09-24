---
sidebar_position: 34
title: "ADR-N-033: A Context Space Has One LinkML Data Model, and Every Reference Is a Picker"
---

# ADR-N-033: A Context Space Has One LinkML Data Model, and Every Reference Is a Picker

Date: 2026-09-24  
Status: Accepted  
Decision Makers: product owner (decisions of 2026-09-24)

## 1. Context

The owner's direction of 2026-09-24: "one context space should have one data model, with LinkML, and make everywhere options to pick from all data models … so everywhere is the options to make that pickable". Today a space holds any number of `DataModel` files (`spaces/{s}/datamodels/{name}.linkml.yaml`, DM-01), and many forms take a model, a type, a space or an Endpoint as free text.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Standard solutions before custom code | **Full** | Built on what exists: the assistant's `navigate` event and prefill, LinkML `imports`, the shared pickers. |
| Technological consistency | **Full** | One propose function, one model format, one picker per kind. |
| Security by design | **Full** | Nothing widens a role; every write stays a Change the person sends; pickers list only what the caller may read. |
| Modular design | **Full** | Paths, steps and pickers are separate, testable parts. |
| Multi-tenancy | **Full** | Every list is filtered by the caller's read permission. |

## 3. Decision

1. **One model per space.** A Context Space has exactly one `DataModel`, `spaces/{s}/datamodel.linkml.yaml`, which the space manifest names in `spec.dataModel`. Its classes are the space's entity types, and the gateway refuses a write of a type the model does not declare. The model may `import` published models (Smart Data Models, or another space's model at a pinned version), which is how a space reuses a type without a second model.
2. **A new space comes with its model.** Creating a space creates its model in the same Change, either empty or importing picked models.
3. **Migration.** `jcctl model merge` turns several models of one space into one, keeping class names and IRIs, and refuses a clash naming both classes. Validation refuses a second model file in a space.
4. **Pickers everywhere.** Every form field that names an existing resource is a picker over what exists and the caller may read. The kinds are data model, type, space, Endpoint, pipeline, group, person, role and project. A picker searches, shows the owner and the version, and offers "create new" where the kind allows it.
5. **One list for the pickers.** `GET /api/v1/organization/datamodels?search=` returns every published model the caller may read (name, project, space, version, classes), with the Smart Data Models catalog entries.

## 4. Alternatives Considered

- **Keep several models per space and add a picker only.** The owner asked for one model per space. It also makes "which schema validates this write" a single answer.
- **One model per project.** That is too coarse: two spaces of one project hold different things.

## 5. Consequences

- DM-01, DM-56 and DM-57 change. DM-61…DM-63 and UI-84…UI-85 are new.
- Every seed space is migrated with no entity id change.
- Work: T-2699…T-2702.

## Related

- [Requirements/data-models](../Requirements/data-models.md) — DM-01, DM-61…DM-63.
- [ADR-N-032](adr-n-032-assistant-paths.md) — the assistant steps that use the pickers.
