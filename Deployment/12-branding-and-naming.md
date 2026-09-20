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
```

Every value is a string or a list of strings. Colours are hex triplets or sextets and are validated as such before anything renders them, because a colour token reaches a browser as a CSS custom property and a value that is not a colour is a way into the page (OPS-46). The logo and the favicon are file names, never URLs: they sit beside the branding file in the same ConfigMap and the Portal serves them from its own origin at `/api/v1/branding/logo` and `/api/v1/branding/favicon`.

## 2. Who reads what

| Consumer | Reads | Effect |
|---|---|---|
| Portal API | the whole block, from `JC_BRANDING_FILE` | answers `GET /api/v1/branding` (public, cached) |
| Portal UI | that endpoint at runtime | page title, sidebar and login logo, colour tokens (`--portal-color-primary`, `--portal-color-secondary`, `--portal-color-accent`, `--portal-color-surface`, `--portal-color-surface-fg`), font stacks (`--portal-font-heading`, `--portal-font-sans`), language switcher, footer organisation and contact |
| CKAN | `instanceName`, `organisation`, `logo`, `favicon`, `colours`, `languages` | site title, site logo, theme tokens, `locale_default` and `locales_offered`, and the organization the publisher creates for a project |
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

The catalogue is the public face of the instance, so its pages are laid out around what a visitor is looking for rather than around CKAN's defaults.

- **Front page.** A hero carrying the instance name, the one-line organisation, and how many datasets the catalogue holds. Below it, one group per context space (transport, air quality, and so on), so the first choice a visitor makes is a subject and not a search box.
- **Dataset page.** The representation resources come first, in the order the publisher writes them: NGSI-LD, then GeoJSON, then the tabular and API surfaces the Endpoint offers. The model artifacts that describe those representations, the JSON Schema and the JSON-LD context, sit apart in a **Model** section at the end. A visitor who wants the data never scrolls past a schema; a developer who wants the schema knows where it always is.
- **Everything else** is stock CKAN. The theme overrides the header, the footer and one stylesheet of custom properties, and holds no copy of a CKAN page it does not need to change.

Of that layout, the header, the footer, the colours and the resource order arrive with the branding block and the publisher: `jcctl` writes the representation resources first and the schema resource last, so a stock dataset page already reads in the order above. The hero's dataset count and the separate **Model** heading are template overrides the theme does not carry yet; they are the next change to it, and they are worth writing against a running catalogue rather than blind.

The colour tokens the theme sets are `--jc-primary`, `--jc-primary-fg`, `--jc-secondary`, `--jc-accent`, `--jc-background`, `--jc-text`, `--jc-font-heading` and `--jc-font-body`, all filled from the block in section 1. `ckan.site_title`, `ckan.site_logo`, `ckan.locale_default` and `ckan.locales_offered` are set from the same block when CKAN starts, so the catalogue's own configuration never carries a literal either. A language the running CKAN does not ship is dropped from the offered list rather than taken as an instruction, because an unknown locale stops CKAN at start-up.

## Related

- [00-intro](00-intro.md) — the deployment invariants this block sits under.
- [Architecture/09-portal](../Architecture/09-portal.md#5-branding-at-runtime) — how the Portal serves and applies it.
- [Architecture/04 §7](../Architecture/04-context-spaces-and-endpoints.md#7-publication-to-an-open-data-portal) — the CKAN publication that uses the organisation and licence defaults.
- [Requirements/operations](../Requirements/operations.md) — OPS-46 and OPS-47.
