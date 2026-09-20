---
sidebar_position: 99
title: Documentation Style
---

# Documentation style

Every page in this documentation set follows these rules. Bigshot passes and reviewers check against them.

## Page skeleton

1. Front matter with `sidebar_position` (integer, unique inside its folder) and `title` (short noun phrase). Optional `description` (one sentence).
2. One H1 equal to the title.
3. A one-paragraph lead: what the page covers and who reads it. No "Introduction" heading.
4. Numbered H2 sections (`## 1. …`). H3 without numbers. Never deeper than H3.
5. A closing `## Related` section with 2–6 relative links (`../Folder/file.md#anchor`), each with a half-sentence saying why to follow it.

## Folders and their voice

| Folder | Voice | Contains |
|---|---|---|
| `Architecture/` | explanatory, present tense, "the gateway does X" | how the system is built and why |
| `Requirements/` | normative, RFC 2119 keywords in capitals | one family per file, IDs never reused |
| `Decisions/` | ADR: Context, Decision, Alternatives considered, Consequences | one decision per file |
| `Deployment/`, `Operations/` | imperative, step by step, copy-pasteable blocks | how to install and run |
| `Development/`, `Testing/`, `API/` | reference, tables and examples | how to build against it |
| `User-Guide/` | second person, no internals, no IDs | how to use the Portal |
| `Research/` | report; findings, evidence, verdict | imported studies |

## Requirements format

- File lead states the family prefix, the ID range, the owning Architecture chapter and the test family.
- Every requirement is one bullet: `- **XX-nn** [tags] — statement.` Tags: `[P]` performance, `[H]` human-facing, `[A]` agent-facing, `[S]` security. Statement uses MUST / SHOULD / MAY once, names the actor, and ends with the reference in parentheses when it depends on another requirement.
- Legacy families keep their original IDs (`R1`, `GW1`, `CC-01`, `SP-01`, `I1`, `MIM0`); new families use `XX-nn` with two digits.
- One statement per requirement. If a bullet needs a second sentence, it is two requirements or a note in the Architecture chapter.
- A `## Traceability` table at the end of each family file: requirement → Architecture section → test family.

## Text

- Product name: **joinedcontext platform**, lower case. CIVITAS/CORE v2 appears only as "the legacy platform" it replaces.
- Names to use: Organization, Project, Context Space, Endpoint, Pipeline, Data Model, Mapping, App, Blueprint, ServiceAccount, `jcctl`, Context Gateway, Portal, artifact store. Never Tenant, DataPool, cityctl, City-as-Code (say Configuration as Code).
- Paths and identifiers in backticks; commands and manifests in fenced blocks with a language tag; one worked example beats three fragments.
- Say a thing once. Details live in the owning chapter; other pages link to it with one sentence of context instead of repeating it.
- No marketing adjectives, no "robust", "seamless", "leverage". No em dashes in body text (use a comma or a full stop). No LaTeX.
- Mermaid for flows and sequences; ASCII trees only for URL and directory layouts.
- Dates ISO `YYYY-MM-DD`; requirement ranges with `…` (`EP-01…EP-54`).

## Related

- [intro](intro.md) — where the set starts.
- [Requirements index](Requirements/00-index.md) — family list and ID ranges.
