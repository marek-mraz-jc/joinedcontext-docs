---
sidebar_position: 21
title: Dátové priestory, rozsahy a prostredia
description: Vstup do dátového priestoru a ponuka údajov jeho účastníkom na základe dohody, pomenovanie rozsahov, pod ktorými sú vaše dáta zaradené, a popis inštalácií, do ktorých sa zmeny projektu povyšujú.
routes:
  - /projects/$project/dataspaceparticipants
  - /projects/$project/dataoffers
  - /projects/$project/dataagreements
  - /projects/$project/scopedefinitions
  - /projects/$project/environments
---

# Dátové priestory, rozsahy a prostredia

Táto stránka pokrýva päť druhov zdrojov, ktoré väčšina projektov nikdy nepotrebuje a niekoľko ich potrebuje nevyhnutne: členstvo organizácie v dátovom priestore, dáta, ktoré v ňom ponúka, dohody, ktoré podpisuje, rozsahy, pod ktorými dáta eviduje, a inštalácie, do ktorých sa zmeny povyšujú. Každý z nich je zoznam s formulárom na pridanie; každé uloženie navrhuje zmenu, ktorú schvaľuje schvaľovateľ. Je napísaná pre dátových stewardov a správcov platformy. Anglická verzia je [Data Spaces, Scopes and Environments](../19-data-spaces-scopes-environments.md).

## 1. Vstúpte do dátového priestoru

Dátový priestor je skupina organizácií, ktoré si vymieňajú dáta na základe podpísaných dohôd, každá cez vlastný konektor. **Dátový priestor**, na `/projects/{project}/dataspaceparticipants`, drží jedno členstvo vašej organizácie; tlačidlo **Nové členstvo v dátovom priestore** sa zobrazuje len vtedy, keď žiadne neexistuje.

1. Kliknite na **Nové členstvo v dátovom priestore**.
2. Vyplňte **Identifikátor účastníka (did:web)**, napríklad `did:web:data.example.sk`, pole **Vydavateľ poverení**, ktorý sa za vás zaručuje, **Adresa konektora** a **Motor konektora**.
3. V časti **Dôveryhodní vydavatelia** pridajte vydavateľov, ktorých poverenia prijímate od ostatných.
4. Kliknite na **Navrhnúť zmenu**.

## 2. Ponúknite dáta a podpíšte dohodu

**Dátové ponuky** hovoria, čo do dátového priestoru ponúkate a za akých podmienok.

1. Kliknite na **Nová dátová ponuka**. Vyberte **Kontextový priestor** a **Ponúkané endpointy**.
2. Napíšte podmienky v časti **Ponuka (ODRL, JSON)**, zaškrtnite **Obsahuje osobné údaje**, ak ich obsahuje, a uveďte **Účel (DPV)**.
3. Kliknite na **Navrhnúť zmenu**.

**Dátové dohody** zaznamenávajú, čo smie iný účastník čítať v rámci jednej ponuky. Kliknite na **Nová dátová dohoda**, zvoľte svoju položku **Rola**, **Dátová ponuka** a **Druhý účastník**, nastavte platnosť v poliach **Platí od** a **Platí do** a zúžte, čo dohoda číta, pod **Obmedzenia dopytov**: **Filter dopytu**, **Filter rozsahu**, **Filter oblasti** alebo **Časový filter**. Pole **Prenosový token** pomenúva tajomstvo, ktoré token drží; samotný token nikdy nepíšete.

## 3. Pomenujte rozsahy, pod ktorými sú dáta evidované

Rozsah zatrieďuje entity pod cestu, napríklad `/bratislava/ruzinov`, takže čitateľ môže požiadať len o jednu mestskú časť. **Definície rozsahov** uvádzajú cesty, ktoré váš projekt používa. Kliknite na **Nová definícia rozsahu**, zadajte **Názov** a hodnotu **Cesta rozsahu** a navrhnite to. Úroveň rozsahu obsahuje písmená, číslice a podčiarkovníky; spojovník sa odmietne.

## 4. Popíšte, kam sa zmeny povyšujú

Prostredie je iná inštalácia platformy, do ktorej sa zmeny tohto projektu povyšujú, napríklad testovacia inštalácia pred produkciou. **Prostredia** ich uvádzajú. Kliknite na **Nové prostredie** a vyplňte polia **Doména organizácie v tomto prostredí**, **Servery** každého komponentu, **Odtlačky obrazov**, ktoré prevádzkuje, **Úložisko tajomstiev** a jeho pripojenie a **Prepínače funkcií**, ktoré sú v ňom zapnuté. Potom to navrhnite.

## Súvisiace

- [Endpoints, zdieľanie údajov a integrácia](05-endpoints-and-sharing.md): endpointy, ktoré dátová ponuka menuje.
- [Správa vašej organizácie a projektov](12-managing-organization-and-projects.md): rovnaké druhy pre celú organizáciu v časti Administrácia.
- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): kto schvaľuje zmeny, ktoré tieto formuláre navrhujú.
