---
sidebar_position: 3
title: Organizácie, projekty a kontextové priestory
description: Správa hraníc organizačných domén, spoločných projektov, kontextových priestorov, kvót a pracovných kópií.
routes:
  - /projects/$project/spaces
  - /projects/$project/spaces/complete
  - /projects/$project/workspaces
  - /projects/$project/workspaces/new
  - /projects/$project/workspaces/$name/compare
  - /projects/$project/workspaces/$name/try-it
  - /projects/$project/workspaces/$name/bring-back
  - /projects/$project/federation
---

# Organizácie, projekty a kontextové priestory

Platforma joinedcontext organizuje všetky mestské operácie do štruktúrovaných hraníc domén. Táto príručka vysvetľuje, ako spravovať projekty, vytvárať a skúmať izolované kontextové priestory, sledovať kvóty zdrojov a bezpečne pracovať na kópiách projektov bez zmeny živých dát. Je napísaná pre správcov projektov (stewardov), dátových architektov a správcov mesta. Anglická verzia je [Organizations, Projects & Context Spaces](../02-organizations-projects-spaces.md).

Každá zmena projektu sa v Portáli riadi rovnakým pravidlom: vyplníte formulár, platforma vykoná overovaciu kontrolu, kliknete na tlačidlo, ktoré navrhne zmenu, a schvaľovateľ posúdi a zlúči návrh v časti **Schvaľovania** skôr, než akákoľvek zmena nadobudne účinnosť.

## 1. Hranice domén

Platforma organizuje mestské dáta do troch štrukturálnych úrovní:

1. **Organizácia:** Reprezentuje celú mestskú správu alebo regionálny úrad (ako napríklad `hel.fi`). Spravuje riadenie na najvyššej úrovni, zdieľané definície rolí a predvolené kvóty.
2. **Projekt:** Reprezentuje spoločný pracovný priestor oddelenia (ako napríklad `helsinki`). Definuje prístupové práva, kvóty zdrojov a vlastní pipeliny, dashboardy a priestory.
3. **Kontextový priestor:** Reprezentuje izolovaný dátový oddiel. Každá entita patrí presne do jedného kontextového priestoru a je neprístupná pre externých volajúcich, pokiaľ nie je explicitne sprístupnená endpointom.

## 2. Správa projektov a kvót

### Otvoriť projekt

#### Ručne

1. Otvorte prepínač projektov v navigačnej hlavičke a vyberte **Nový projekt**.
2. V dialógu zadajte identifikátor projektu do poľa **Názov** pomocou malých písmen, číslic a spojovníkov (ako napríklad `helsinki-mobility`).
3. Zadajte názov do poľa **Zobrazovaný názov** (ako napríklad `Helsinki Mobility`) a zhrnutie do poľa **Popis**.
4. Kliknite na **Otvoriť projekt**.
5. Mali by ste vidieť pruh s návrhom odkazujúci na **Schvaľovania**. Administrátor návrh posúdi skôr, ako sa projekt inicializuje.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Open a new project called helsinki-mobility for urban transport`

Asistent overí vaše oprávnenia, pripraví návrh manifestu a otvorí formulár na vytvorenie. Vy kliknete na **Otvoriť projekt** a administrátor návrh schváli.

### Sledovanie kvót

#### Ručne

1. Prejdite na **Kontextové priestory** na `/projects/helsinki/spaces`.
2. Posuňte sa na časť **Kvóta** pod tabuľkou priestorov.
3. Mali by ste vidieť ukazovatele využitia kvóty pre **Kontextové priestory**, **Trvalé linky**, **Verejné endpointy** a **Aplikácie**.
4. Po dosiahnutí limitu je vytvorenie ďalšieho zdroja zablokované, kým administrátor nezvýši limit alebo sa neodstráni nepoužívaný zdroj.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`What are the remaining quotas for the helsinki project?`

Asistent sa opýta na využitie projektu a oznámi aktívne počty a limity pre každú dimenziu.

## 3. Vytváranie a prehliadanie kontextových priestorov

### Vytvoriť kontextový priestor

#### Ručne

1. Prejdite na **Kontextové priestory** na `/projects/helsinki/spaces`.
2. Kliknite na **Nový kontextový priestor**.
3. V dialógu zadajte `air-quality` do poľa **Názov**.
4. Do poľa **Popis** zadajte `Air Quality & Weather`.
5. Do poľa **Dátový model** zadajte odkaz na model `helsinki`.
6. Kliknite na **Skontrolovať**. Mali by ste vidieť odznak výsledku návrhu so stavom `Checked`.
7. Kliknite na **Navrhnúť zmenu**.
8. Prejdite na `/projects/helsinki/approvals`, kde schvaľovateľ vyberie návrh a klikne na **Schváliť**.
9. Stav priestoru prejde do **Aktívne**.

Živá cesta `verdict-gate.spec.ts` zopakuje tieto kroky.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Create a context space called air-quality in the helsinki project`

Asistent prejde na `/projects/helsinki/spaces` a otvorí dialóg s vyplneným poľom **Názov**. Vy kliknete na **Skontrolovať**, overíte zelený odznak a kliknete na **Navrhnúť zmenu**. Schvaľovateľ zlúči návrh v časti **Schvaľovania**.

Živá cesta `assistant-creates.spec.ts` zopakuje tieto kroky.

### Preskúmať obsah priestoru

#### Ručne

1. Prejdite na `/projects/helsinki/spaces`.
2. Nájdite riadok pre `helsinki` a kliknite na **Pozrieť obsah**.
3. Dostanete sa na `/projects/helsinki/spaces/helsinki`.
4. V časti **Typy entít** by ste mali vidieť definované typy (`BikeHireDockingStation`, `Vehicle`, `Event`), počet živých entít a ukážkové záznamy.
5. V časti **Dáta** vyberte typ entity z poľa **Typ entity**, aby ste si prezreli záznamy v tabuľke dát.
6. V častiach **Endpointy** a **Politiky** skontrolujte verejné a organizačné pohľady nakonfigurované nad týmto priestorom.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`What entity types and how many entities are inside the helsinki space?`

Asistent preskúma povrch priestoru a odpovie s aktívnymi typmi a živými počtami záznamov.

## 4. Doplnenie priestoru zo vzorky

### Doplniť priestor z kanála

#### Ručne

1. Na `/projects/helsinki/spaces` kliknite na **Doplniť tento priestor**, čím otvoríte `/projects/helsinki/spaces/complete`.
2. Do poľa **Názov priestoru** zadajte `city-bikes`.
3. Do poľa **URL endpointu** zadajte `https://gbfs.theta.fifteen.eu/gbfs/2.2/helsinki/en/station_information.json` alebo pripojte súbor CSV pomocou **Súbory**.
4. Kliknite na **Doplniť**.
5. Mali by ste vidieť pripravené karty zdrojov pre DataModel, ContextSpace, DataSource a Pipeline, každú označenú odznakom stavu kontroly.
6. Kliknite na **Navrhnúť všetko**. Schvaľovateľ skontroluje a schváli balík v časti **Schvaľovania**.

Živá cesta `space_complete.spec.ts` zopakuje tieto kroky.

#### Opýtaním sa asistenta

Presuňte súbor so vzorkou do panela asistenta a napíšte:
`Complete a space called city-bikes from this sample.`

Asistent analyzuje vzorku, navrhne schémy a pipeliny a prejde na `/projects/helsinki/spaces/complete` s návrhmi pripravenými na vašu kontrolu a navrhnutie.

## 5. Práca na kópiách projektov

Kópia predstavuje projekt bokom: zmeňte niekoľko zdrojov, vyskúšajte ich a prineste ich späť ako jednu zmenu, ktorú človek schváli. Stránka **Kópie** uvádza vaše kópie v časti **Moje kópie** a kópie všetkých ostatných, len na čítanie, v časti **Kópie iných ľudí**. Stránka **Vyskúšať** (`/projects/{project}/workspaces/{copy}/try-it`) spustí náhľad kópie pod jej vlastnými adresami; iba osoba, ktorá kópiu spustila, ju spúšťa a zastavuje a tlačidlo **Skopírovať dáta** ju naplní skutočnými entitami prečítanými s vašimi vlastnými právami. Kópia sa vymaže po uplynutí času v časti **Ponechať**; projektu sa to nikdy nedotkne.

### Vykonávanie zmien v kópii

#### Ručne

1. Prejdite na **Kópie** na `/projects/helsinki/workspaces`.
2. Kliknite na **Pracovať na kópii**.
3. Do poľa **Názov** zadajte `emp-test`. Vyberte `The whole project` pod **Pokrýva** a kliknite na **Začať kópiu**.
4. Mali by ste vidieť pruh kópie navrchu, ktorý uvádza, že pracujete na kópii a nič nie je živé.
5. Prejdite na `/projects/helsinki/pipelines?workspace=emp-test` a kliknite na **Pozastaviť** pri `hel-news`. Vo vnútri kópie sa úprava uchováva v kópii a neotvára žiadny samostatný návrh.
6. Otvorte `/projects/helsinki/workspaces/emp-test/compare`, aby ste preskúmali, čo kópia mení.
7. Otvorte `/projects/helsinki/workspaces/emp-test/bring-back` a kliknite na **Navrhnúť ako jednu zmenu**.
8. V časti `/projects/helsinki/approvals` schvaľovateľ skontroluje rozdiel (diff) a schváli zmenu.

Živá cesta `copy-employee.spec.ts` zopakuje tieto kroky.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Work on a copy of the helsinki project called agent-test, and in that copy pause the hel-news pipeline.`

Asistent spustí kópiu, vytvorí skontrolovaný návrh vo vnútri kópie a zastaví sa pred dverami. Navrhnutie kópie späť do projektu alebo jej zahodenie musíte vykonať vy.

Živá cesta `copy-agent.spec.ts` zopakuje tieto kroky.

Starý odkaz na `/projects/{project}/federation` otvorí **Kontextové priestory**: priestor, ktorý odpovedá dátami iného zdroja, sa nastavuje pod **Kontextové zdroje** ([Endpointy, zdieľanie údajov a integrácia](05-endpoints-and-sharing.md)).

## Súvisiace

- [Začíname](01-getting-started.md): prvé kroky v Portáli.
- [Dátové modely](03-data-models.md): vizuálne modelovanie v LinkML a verziovanie schém.
- [Endpointy a zdieľanie](05-endpoints-and-sharing.md): sprístupnenie dát priestoru pre spotrebiteľov a nástroje.
- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): priraďovanie rolí, servisné účty a posudzovanie zmien.
- [Uchovávanie a expirácia](../14-retention-and-expiry.md): ako dlho priestor uchováva aktuálne hodnoty a históriu.
