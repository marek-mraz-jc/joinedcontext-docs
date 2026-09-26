---
sidebar_position: 12
title: "Branding and Naming"
description: One block of values that names an installation, themes the Portal and CKAN, and fills the DCAT-AP publisher fields.
---

# Branding and Naming

Nothing about a deployment is hard-coded to a city. One block in the environment's values, `global.branding`, says what the installation is called, who publishes its data, what it looks like and which languages it speaks; every component that shows a name, a colour or a logo reads it from there. Operators change a name and apply; nobody rebuilds an image. This page is for whoever installs or rebrands an instance.

## 1. The block

```yaml
global:
  branding:
    instanceName: "Banská Bystrica Context"      # full name, page titles, login page
    shortName: "BB Context"                       # sidebars, tabs, e-mail subjects
    city: "Banská Bystrica"
    organisation: "Mesto Banská Bystrica"         # legal publisher, DCAT-AP dcterms:publisher
    orgDomain: "banskabystrica.sk"                # URN segment, Keycloak realm display, did:web
    domain: "bb.example.com"                      # the platform host
    contactEmail: "opendata@example.org"    # DCAT-AP contact point, e-mail templates
    licenseDefault: "CC-BY-4.0"                   # default dataset licence
    logo: "logo.svg"                              # served from the platform origin
    favicon: "favicon.svg"
    colours:
      primary: "#0000bf"
      secondary: "#0072c6"
      accent: "#ffe977"
      background: "#ffffff"
      text: "#1a1a1a"
    fonts:
      heading: "HelsinkiGrotesk, system-ui, sans-serif"
      body: "system-ui, sans-serif"
    languages:
      default: "sk"
      offered: ["sk", "en"]
    documentationBaseUrl: "https://docs.bb.example.com"   # where this installation serves the
                                                          # User Guide; omit it and no form links
    tagline: "Otvorené dáta mesta, naživo"        # the catalogue's home page, under the name
    footerLines:                                  # the catalogue's footer, one paragraph each
      - "Demo instance, not affiliated with the city."
```

Every value is a string or a list of strings. Colours are hex triplets or sextets and are validated as such before anything renders them, because a colour token reaches a browser as a CSS custom property and a value that is not a colour is a way into the page (OPS-46). The logo and the favicon are file names, never URLs: they sit beside the branding file in the same ConfigMap and the Portal serves them from its own origin at `/api/v1/branding/logo` and `/api/v1/branding/favicon`. Those two names are the whole of the route: `GET /api/v1/branding/{asset}` accepts `logo` and `favicon` and answers `404` to anything else, so the path can reach no file the ConfigMap does not carry. The content type comes from the file's own extension (`.svg`, `.png`, `.jpg`, `.webp`, `.ico`).

`tagline` and `footerLines` are the catalogue's own words: the line under the name on its home page (empty means the theme's default, in the page's language) and the lines of its footer, such as a demo disclaimer or an imprint. A value that is not a string, or a list entry that is empty, is dropped rather than rendered.

A colour the Portal UI cannot read is named in the browser console and skipped; the token keeps the default it already had rather than taking a value that is not a colour.

`documentationBaseUrl` is optional and empty by default. It is the root of the installation's copy of this documentation, and a create form joins it with the page its kind's arrangement names (`guide:`, [Architecture/09](../Architecture/09-portal.md) section 2) to offer one link beside the form's `about`. An installation that serves no guide leaves it out and no form shows a link, because a dead link is worse than none. It is validated as an absolute `http` or `https` URL before it is served, for the reason the colours are validated: it reaches the page as an attribute a browser acts on, and a value carrying another scheme is dropped and logged. Nothing follows it — the Portal never makes a request to it.

## 2. Who reads what

| Consumer | Reads | Effect |
|---|---|---|
| Portal API | the whole block, from `JC_BRANDING_FILE` | answers `GET /api/v1/branding` with `Cache-Control: public, max-age=300` |
| Portal UI | that endpoint at runtime | page title, sidebar and login logo, colour tokens (`--portal-color-primary`, `--portal-color-primary-fg`, `--portal-color-primary-dark`, `--portal-color-primary-fg-dark`, `--portal-color-secondary`, `--portal-color-accent`, `--portal-color-surface`, `--portal-color-surface-fg`), font stacks (`--portal-font-heading`, `--portal-font-sans`), language switcher, footer organisation and contact |
| CKAN | `instanceName`, `organisation`, `contactEmail`, `logo`, `favicon`, `colours`, `fonts`, `languages`, `tagline`, `footerLines`, `domain` | site title, site logo and favicon, the whole stylesheet (every colour mixed from the five brand colours), `locale_default` and `locales_offered`, the home page's tagline, the footer, and the organization the publisher creates for a project |
| DCAT-AP records | `organisation`, `contactEmail`, `licenseDefault`, `domain` | `dcterms:publisher`, `dcat:contactPoint`, the default `dcterms:license` of a distribution |
| Keycloak | `instanceName`, `orgDomain`, `colours`, `logo` | realm display name and login theme |
| E-mail templates | `shortName`, `organisation`, `contactEmail`, `domain` | subject prefix, signature, links |
| Demo and seed data | `orgDomain`, `city`, `languages` | entity URNs, space names and the language of seeded titles, never a literal |

## 3. Rules

- No component, chart, image or UI string carries a city-specific literal. A grep for one city's name across the repositories returns hits only inside an environment's own values file and inside example fixtures (OPS-46).
- The Portal applies branding at runtime, so one image serves every installation and a rebrand is a values change plus an apply, never a rebuild (UI-30).
- The CKAN theme renders any branding block; it holds templates and one stylesheet of custom properties, and no value of its own (OPS-47).
- A missing or unreadable branding file is not an error. The Portal falls back to neutral joinedcontext defaults and keeps serving; an installation without branding looks plain, it does not break.
- Fonts are self-hosted or system fallbacks. Nothing on a page fetches from a third-party origin at runtime.
- A link the Portal offers to a place outside itself is built from configuration and a path the platform ships, never from a field somebody writes into a manifest (`documentationBaseUrl` plus a `UiSchema`'s `guide`).

## 4. Changing the branding of a running instance

1. Edit `global.branding` in the environment's values file and commit it.
2. Apply the environment. The `portal` component re-renders the branding ConfigMap and the CKAN component re-renders its theme values.
3. The Portal picks the new file up on its next read; a browser sees the new name and colours on reload. CKAN restarts its web pods and shows the new title and theme.

No image is rebuilt in any of those steps, and no manifest under `projects/` changes: branding names the installation, not the data in it.

## 5. Example: the dev instance

The development cluster runs as **Helsinki Region Context**, a demo instance for the Helsinki region. It is the worked example of everything above: the block below is the only difference between it and any other installation of the same images.

```yaml
global:
  branding:
    instanceName: "Helsinki Region Context"
    shortName: "HKI Context"
    city: "Helsinki"
    organisation: "City of Helsinki (demo instance, not affiliated)"
    orgDomain: "hel.fi"
    contactEmail: "opendata@example.invalid"
    licenseDefault: "CC-BY-4.0"
    logo: "logo.svg"
    colours:
      primary: "#0000bf"        # Helsinki Design System brand blue
      secondary: "#0072c6"      # bus blue
      accent: "#ffe977"         # engel
      background: "#ffffff"
      text: "#1a1a1a"           # black-90
    fonts:
      heading: "HelsinkiGrotesk, system-ui, sans-serif"
      body: "system-ui, sans-serif"
    languages:
      default: "fi"
      offered: ["fi", "sv", "en"]
```

Two constraints shape it. The organisation line says *demo instance, not affiliated*, and the logo is a plain geometric mark in the brand colours, because the city's coat of arms is a trademark and this installation does not belong to the city. `HelsinkiGrotesk` is named first and never fetched: the Portal serves its own typeface, Inter (SIL OFL 1.1), from its origin and puts it before the system families of every branding stack, and the apps it builds carry the same face inside their preview document, so a brand font the browser does not have falls back to the same letters on every machine and no page reaches a third-party origin for a typeface (UI-30, T-0756).

`orgDomain` here is the branding identity. It is not the same value as `global.orgDomain`, which is the URN segment the gateway checks on every write: renaming that renames every entity already stored, so the two move separately.

## 6. Catalogue page layout

The catalogue is the public face of the instance, so its pages are laid out around what a visitor is looking for rather than around CKAN's defaults, and they look like the Portal's family: a light header with a hairline under it, surfaces on a tinted page, one type scale, the brand colour for actions and the current place (T-3009).

- **Home page.** A hero in the brand colour carrying the instance name, the `tagline`, one search field and how many datasets and publishers the catalogue holds. Below it, the datasets changed last as cards (publisher, title, description, the formats a reader gets, the last update), and beside them the ways in by publisher and by keyword. CKAN's sample page ("Welcome to CKAN" and its placeholder image) is gone.
- **Dataset page.** The description, then **the data itself**: every DataStore table of the dataset (one per entity type), each framed on the page with its row count, searchable and sortable, with a link to the table's own page and a CSV download. The first table is open; the others open on a click and load nothing until then. Then the About list, the live API box and the downloads in three sections: the data as files (the DataStore tables first), the APIs (NGSI-LD, MCP), and the **data model** (the artifacts under the Endpoint's `/schema/` path), folded, because its formats are for validators and developers. Each resource is one row with its format, one line saying what it is for, and its one action (Download, or Open for an API) in place of CKAN's "Explore" menu. The sidebar keeps the publisher; the follower count, the share buttons and a second licence box are gone.
- **Search results.** One row per dataset with the data and API formats as plain chips, never the model's seven artifacts, and the publisher and last update beside them.
- **About, publishers and topics.** The About page says whose catalogue this is (`instanceName`, `organisation`), how to get at the data, the catalogue API and, when DCAT-AP is on, the harvest address, and whom to write to (`contactEmail`); a sysadmin's own `ckan.site_about` still replaces it. The header and the pages name CKAN's organizations and groups as publishers and topics, the words the search filters use, and the cards sit in a grid that wraps names at word boundaries (T-3028).
- **Everything else** is stock CKAN, restyled by the same stylesheet.

The theme is templates, `jc-theme.css` and `plugin.py`, and nothing else. The stylesheet carries no colour of its own: `base.html` writes the brand values as `--jc-primary`, `--jc-primary-fg`, `--jc-primary-rgb`, `--jc-secondary`, `--jc-accent`, `--jc-background`, `--jc-text`, `--jc-font-heading` and `--jc-font-body`, and every other colour (the neutral scale, the soft tints, the focus ring, the dark footer) is mixed from them with `color-mix()`, the way the Portal's `tokens.css` derives its scales. A second installation restyles the whole catalogue by its branding block alone. `ckan.site_title`, `ckan.site_logo`, `ckan.favicon`, `ckan.locale_default` and `ckan.locales_offered` are set from the same block when CKAN starts, so the catalogue's own configuration never carries a literal either. A language the running CKAN does not ship is dropped from the offered list rather than taken as an instruction, because an unknown locale stops CKAN at start-up.

The theme (package `ckanext_jc_theme`) is the first plugin in `ckan.plugins`: CKAN gives the templates of the first plugin precedence, and the theme overrides the table view's own page so that the grid framed on a dataset page wears the same look.

## Related

- [00-intro](00-intro.md) — the deployment invariants this block sits under.
- [Architecture/09-portal](../Architecture/09-portal.md#5-branding-at-runtime) — how the Portal serves and applies it.
- [Architecture/04 §7](../Architecture/04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) — the CKAN publication that uses the organisation and licence defaults.
- [Requirements/operations](../Requirements/operations.md) — OPS-46 and OPS-47.
