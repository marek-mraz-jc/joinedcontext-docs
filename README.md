# joinedcontext-docs

The specification of the **joinedcontext platform**: the requirements the code is held to, the
architecture it follows, the decisions behind it and the guides for running and using it. A
contract change lands here first, in its own commit, and the code follows the pushed page.

## 1. What is in it

| Folder | What |
|---|---|
| `Requirements/` | the normative requirements, one page per family, each bullet an id the code and the tests cite |
| `Architecture/` | how the platform is built, chapter by chapter; the map every other page links into |
| `Decisions/` | the ADRs and the register that indexes them |
| `API/` | the surfaces a caller sees: the Portal API, the gateway representations, the error shapes |
| `Development/` | what somebody building on the platform needs: manifest kinds, the SDK, MCP, the agents |
| `Deployment/`, `Operations/` | installing it, hardening it, running it, and the runbooks |
| `Testing/` | which layer answers which question, and which suite proves each requirement |
| `User-Guide/` | the Portal as a person uses it, in the words the UI shows |
| `Research/` | the notes behind a decision, kept for the reasoning, not as current truth |
| `scripts/` | the checkers below: each takes `--selftest` and each is a CI gate |

`STYLE.md` governs the shape of a page (front matter, a single H1, numbered H2s, `## Related`,
requirement bullets `- **XX-nn** [tags] — …`), `Glossary.md` the vocabulary, and
`OPEN-QUESTIONS.md` what is still undecided.

## 2. How it fits

These pages are the source, not a rendering of one: there is no site in this repository, and
the published documentation is assembled from this corpus elsewhere. Start at `intro.md`, then
`Architecture/00-index.md`. A requirement id is the thread through everything — a page states
it, `Testing/` names the suite that proves it, and a commit in a code repository cites it.

## 3. Build

There is nothing to build: the pages are the source, and the checkers below need Python 3.12
and nothing installed. The markdown lint comes from `npx`, pinned to the version CI uses, so
the repository needs no `node_modules` either — `npm install` works for an editor integration,
but nothing here depends on it.

## 4. Test

The checkers are the gate, and each is written to fail the corpus it is meant to reject —
`--selftest` proves that it still can, which is what keeps a checker from passing by doing
nothing:

```bash
npx --yes markdownlint-cli@0.45.0 '**/*.md'
python3 scripts/check-links.py
python3 scripts/check-front-matter.py
python3 scripts/verify-traceability.py
python3 scripts/check-glossary.py
python3 scripts/check-links.py --selftest
python3 scripts/verify-traceability.py --selftest
```

`ci.yml` runs every checker in `scripts/` on every push, and `--selftest` on each of them: the
URNs, the chapter map, the Mermaid diagrams, the component matrix, the runbooks, the curl
snippets, the manifests in the examples, the i18n audit, the ADR register, and — since T-2139
— what these pages claim about the code, against the code.

## 5. Read it locally

A page is markdown and opens in any editor. To read the corpus the way a reader will, point a
markdown viewer at the folder; the relative links between pages resolve as they are written.

## 6. Security

Report a vulnerability in the platform privately through the security advisories of the
repository it lives in ([platform](https://github.com/marek-mraz-jc/joinedcontext-platform/security/advisories/new)
for the gateway, the reconciler and the manifest model,
[portal](https://github.com/marek-mraz-jc/joinedcontext-portal/security/advisories/new) for the
management application). Please do not open a public issue for one.

A documentation page is published, so an example in it is published too.
`scripts/check-examples-are-safe.py` refuses a routable address, a real host, a complete token,
a private key or a person's e-mail anywhere in the corpus — an example uses a documentation
domain and a placeholder, and a page that needs a real value names where it is read from
instead of printing it.

## 7. Working here

Read `STYLE.md` before writing a page, and run the checkers before pushing: they are cheap and
they are the merge gate. A new requirement needs an id, a chapter that states it and a test
that proves it, or `verify-traceability.py` refuses it. A claim about the code is checked
against the code, so write what is true today and name the task for what is not yet built.
