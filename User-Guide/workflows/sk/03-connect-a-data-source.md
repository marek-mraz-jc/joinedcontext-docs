---
sidebar_position: 3
title: Pripojenie zdroja údajov
description: Začnite zo šablóny, zadajte adresu zdroja a pozrite si jeho prvé záznamy ešte pred uložením.
---

# Pripojenie zdroja údajov

Zdroj údajov je miesto, odkiaľ pipelina číta: súbor CSV na adrese, REST API, dataset z CKAN, vrstva WFS alebo zdroj GTFS Realtime. Na tejto stránke jeden pripojíte a overíte, že odpovedá. Je určená správcom údajov a integrátorom.

## 1. Vyberte šablónu

Otvorte **Zdroje údajov** a kliknite na **Nový zdroj údajov**. V časti **Začať zo šablóny** vyberte druh zdroja, ktorý máte.

![Šablóny zdrojov údajov: súbor CSV, REST API, dataset z CKAN, vrstva WFS a GTFS Realtime](../../img/sk/datasource-1-templates.png)

## 2. Zadajte adresu

Vložte adresu zdroja a zadajte zdroju **Názov**. Zdroj WFS si pýta aj **Názov vrstvy**.

![Šablóna vyplnená adresou súboru CSV a názvom](../../img/sk/datasource-2-address.png)

## 3. Prečítajte prvé záznamy

Kliknite na **Vyplniť formulár a overiť**. Portál vyplní formulár zo šablóny a raz prečíta zdroj, takže ešte pred návrhom vidíte, koľko záznamov vrátil a ako vyzerajú.

![Prvé záznamy, ktoré zdroj vrátil](../../img/sk/datasource-3-first-records.png)

## Related

- [Pipelines and ingestion](../../04-pipelines.md#2-connecting-an-external-data-source) — v angličtine: všetky druhy zdrojov a ich voľby.
- [Vytvorenie pipeliny](04-build-a-pipeline.md) — načítajte zdroj do priestoru.
