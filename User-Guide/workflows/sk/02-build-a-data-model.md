---
sidebar_position: 2
title: Vytvorenie dátového modelu
description: Pridajte triedy, číselník a vzťah, model skontrolujte a navrhnite.
---

# Vytvorenie dátového modelu

Dátový model hovorí, aké typy vecí priestor obsahuje a čo každá z nich nesie. Na tejto stránke ho zostavíte ručne: dve triedy, číselník a vzťah jedna k mnohým. Je určená správcom údajov a modelárom.

## 1. Pridajte triedy a vzťah

Otvorte **Dátové modely** a zvoľte **Nový prázdny model**. Zadajte **Názov** a vyberte **Priestor**, do ktorého patrí. Každú triedu pridajte cez **Pridať triedu**. Číselník zadajte do poľa pre číselník, kliknite na **Pridať číselník** a pridajte jeho hodnoty. Vyberte triedu, pridajte jej atribúty cez **Pridať atribút** a každému zvoľte **Typ hodnoty**. Dve triedy prepojíte tak, že zvolíte **Jedna k mnohým**, vyberiete **Cieľová trieda** a kliknete na **Pridať vzťah**; tabuľka **Vzťahy** ukáže oba konce.

![Editor modelu s dvoma triedami, číselníkom a vzťahom jedna k mnohým](../../img/sk/model-1-classes-and-relationship.png)

## 2. Skontrolujte ho

Čo formulár nevie nastaviť, napíšete na karte **Zdroj**. Kliknite na **Skontrolovať**: Portál overí celý model a povie vám, ako ktorá verzia sa uloží.

![Skontrolovaný model s verziou, ako ktorá sa uloží](../../img/sk/model-2-checked.png)

## 3. Uložte a navrhnite

Kliknite na **Uložiť model**. Model ide do **Schvaľovania** ako navrhnutá zmena; použije sa až po schválení.

![Model navrhnutý ako zmena](../../img/sk/model-3-proposed.png)

## Related

- [Data models](../../03-data-models.md) — v angličtine: atribúty, typy hodnôt a verzie.
- [Vytvorenie pipeliny](04-build-a-pipeline.md) — naplňte model údajmi.
