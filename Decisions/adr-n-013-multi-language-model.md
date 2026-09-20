---
sidebar_position: 14
title: "ADR-N-013: Multilingual Architecture with ICU MessageFormat"
---

# ADR-N-013: Multilingual Architecture with ICU MessageFormat

Date: 2026-09-05  
Status: Accepted  
Decision Makers: Architecture Board

## 1. Context

CIVITAS/CORE v2 originated in Germany with documentation and user interfaces primarily authored in German, later retrofitted with partial English translations. Cross-border federated digital twins across Central and Eastern Europe require first-class support for multiple languages across UI text, error envelopes, and data model metadata.

Ad-hoc string concatenation and simple key-value dictionaries fail when handling complex pluralization, gender, and grammatical cases common in Slavic languages (Slovak, Czech). Furthermore, data catalog metadata must allow multilingual descriptions for cross-border discoverability.

## 2. Checked Architecture Principles

| Principle | Rating | Analysis |
|---|---|---|
| Model-driven data flow | **Full** | LinkML models and manifests define multi-language maps natively. |
| Distributed architecture with unified UX | **Full** | Consistent multilingual presentation across all user interface routes. |
| Modular design | **Full** | Translation bundles are versioned declarative manifests in Git. |
| Integrability via defined interfaces | **Full** | Conforms to Unicode ICU MessageFormat standard. |
| Open source as default | **Full** | Uses standard `react-i18next` and ICU open-source libraries. |
| Cloud-native architecture | **Full** | Zero runtime server translation lookups; compiled into client bundles. |
| Standard solutions before custom code | **Full** | Standardizes on Unicode CLDR and ICU syntax. |
| Self-contained deployment | **Full** | Shipped bundles include all core languages. |
| Technological consistency | **Full** | Unified locale handling across API error envelopes and UI. |
| Multi-tenancy | **Full** | Organizations customize translation bundles in their own repository. |
| Security by design | **Full** | Parameterized translation prevents format-string injection attacks. |

## 3. Decision

1. **Four Core Supported Locales**:
   - The platform core officially supports and ships complete translations for:
     - **English (`en`)**
     - **Slovak (`sk`)**
     - **German (`de`)**
     - **Czech (`cs`)**
   - English is listed first because it is the fallback locale of the platform's own
     documentation and examples, the one entry every human-facing field here carries. An
     Organization designates its own fallback for its own manifests (PF-25), and a Finnish
     instance designates Finnish; the order here binds the platform's material, not an
     installation's data.
   - A manifest's language map is instance data, not a shipped bundle, so its keys are the
     whole of ISO 639-1 and not this list. Shipping four bundles is a statement about the
     Portal's own strings.
2. **ICU MessageFormat Bundles**:
   - All user interface strings, system alerts, and validation messages MUST be authored using **ICU MessageFormat** syntax to handle complex grammatical plurals and gender.
   - Translation bundles are managed as declarative JSON files under `portal/locales/{locale}.json` in the organization repository, allowing tenant-specific overrides.
3. **Manifest Multi-Language Maps**:
   - All human-facing metadata in manifests (`title`, `description`) MUST be structured as language maps (`{"sk": "...", "en": "..."}`) per PF-24.
   - Organizations define an ordered locale preference list with an explicit fallback locale.
4. **Data Model Translations**:
   - LinkML models declare slot and class titles using `title` and `description` with `in_language` annotations, compiling into localized data dictionaries.

## 4. Consequences

### Positive

- **Natural Slavic Language Support**: Proper dual/plural handling in Slovak and Czech without awkward UI syntax hacks.
- **Declarative Customization**: Organisationalities can tailor UI terminology (e.g., German organisational terms vs. Slovak public sector terms) directly in their Git repository without recompiling code.

### Negative / Trade-offs

- Adding new UI features requires authoring or validating translation keys across four language files; missing translations are flagged as CI errors (TS-14).

## 5. See Also

- Requirements: [PF-24…PF-28 (Metadata Locales)](../Requirements/platform.md), [UI-11…UI-14 (UI i18n)](../Requirements/portal-and-ui.md), [TS-14 (i18n Gate)](../Requirements/testing.md).

## Related

- [PF-24…PF-28 (Metadata Locales)](../Requirements/platform.md) — referenced above.
- [UI-11…UI-14 (UI i18n)](../Requirements/portal-and-ui.md) — referenced above.
- [TS-14 (i18n Gate)](../Requirements/testing.md) — referenced above.
- [00-register](00-register.md) — all decisions and their status.
- [01-overview](../Architecture/01-overview.md) — the architecture these decisions shape.
