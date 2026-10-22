---
sidebar_position: 19
title: Katalóg a verejné stránky
description: Čo návštevník bez účtu nájde v Portáli, ako vyhľadávať v katalógu a čítať jeden dataset a ako projekt zverejňuje dataset, verejný pohľad, verejný formulár a AI konektor.
routes:
  - /catalogue
  - /catalogue/$name
  - /v/$slug
  - /d/$slug
  - /f/$slug
  - /connect/$project/$name
  - /glossary
  - /accessibility
---

# Katalóg a verejné stránky

Niektoré stránky Portálu sa otvárajú bez prihlásenia: katalóg verejných datasetov, vlastná stránka datasetu, zverejnený pohľad, verejný formulár, dokumentácia API endpointu, stránka na pripojenie AI asistenta, slovník a vyhlásenie o prístupnosti. Táto stránka vysvetľuje každú z nich pre dvoch čitateľov: návštevníka, ktorý ich používa, a dátového správcu, ktorý zverejňuje to, čo zobrazujú. Anglická verzia je [The Catalogue and Public Pages](../17-catalogue-and-public-pages.md).

## 1. Vyhľadávanie v katalógu

Otvorte `/catalogue`. **Katalóg** uvádza každý verejný dataset z katalógov otvorených dát tejto inštalácie.

1. Zadajte niekoľko slov do poľa **Hľadať datasety**, napríklad `air quality`, a stlačte **Hľadať**. Vyhľadávanie číta názvy, popisy a kľúčové slová.
2. Zoznam zúžte v časti **Filtre**: **Vydavateľ**, **Téma**, **Formát**, **Licencia**, **Územie** a **Perióda**. Na telefóne sa filtre otvárajú ako panel; tlačidlo **Zavrieť filtre** vás vráti do zoznamu.
3. Výsledkami listujte pomocou **Predchádzajúca strana** a **Ďalšia strana** a otvorte dataset kliknutím na jeho názov.
4. Voľba **Zrušiť vyhľadávanie a filtre** spustí vyhľadávanie odznova.

Vyhľadávanie a filtre sa nachádzajú priamo v adresnom riadku, takže filtrovaný zoznam môžete niekomu poslať ako odkaz.

Keď je zoznam prázdny:

- **Zatiaľ žiadny verejný dataset**: žiadny projekt tejto inštalácie zatiaľ nezverejnil dataset. Dataset sa zobrazí, len čo projekt zverejní Endpoint do svojho katalógu otvorených dát (časť 3).
- **Žiadny dataset nevyhovuje**: odstráňte filter alebo zmeňte hľadaný text.
- Oznámenie s názvami katalógov, ktoré neodpovedali, znamená, že ich datasety v tomto zozname zatiaľ chýbajú. Skúste to znova o minútu.

## 2. Prečítanie jedného datasetu a použitie jeho dát

Stránka datasetu, `/catalogue/{name}`, obsahuje všetko, čo potrebujete pred použitím dát.

- Fakty v hornej časti uvádzajú, kto ho zverejňuje (**Vydavateľ**), pod akou licenciou (**Licencia**), ako často sa aktualizuje, aké územie (**Územie**) a periódu (**Perióda**) pokrýva, koho kontaktovať a kedy sa naposledy zmenil.
- Časť **Zdroje** uvádza súbory a služby datasetu, každú s možnosťou **Stiahnuť** alebo **Náhľad**.
- Časť **Vzorka** pri otvorení stránky načíta desať riadkov cez Endpoint, takže vidíte skutočné hodnoty, nie ich popis.
- Časť **Dátový model** uvádza model, ktorým sa riadky riadia, s odkazom na **Dokumentácia modelu**.
- Časť **Použiť tieto dáta** ponúka pripravené útržky kódu: **Z príkazového riadka (NGSI-LD)**, **Stiahnuť ako CSV**, **V aplikácii postavenej na tomto endpointe** a **V klientovi MCP**. Každý má tlačidlo na kopírovanie.
- Odkaz **Otvoriť v katalógu** otvorí rovnaký dataset v samotnom katalógu otvorených dát a **Všetky datasety** vás vráti do zoznamu.

Ak stránka hlási **Žiadny verejný dataset nemá tento názov**, dataset bol odstránený alebo zmenený na súkromný. Vyhľadajte ho v katalógu.

## 3. Zverejnenie datasetu v katalógu

Potrebujete projekt, v ktorom môžete navrhnúť Endpoint. Potom sa na stránke katalógu zobrazí voľba **Zverejniť dataset**.

1. Otvorte `/catalogue` a kliknite na **Zverejniť dataset**.
2. V časti **1. Endpoint** vyberte Endpoint, ktorého dáta dataset popisuje.
3. V časti **2. Popis** vyplňte **Názov datasetu**, **Popis**, **Meno kontaktu**, **Kontaktný e-mail** a **Kľúčové slová**, a časové obdobie v položkách **Obsahuje dáta od** a **Obsahuje dáta do**. Tlačidlo **Pripraviť popis** predvyplní text z modelu Endpointu; pred pokračovaním si ho prečítajte a upravte.
4. Kliknite na **Zobraziť náhľad záznamu**. V časti **3. Náhľad** uvidíte záznam presne tak, ako ho uvidia návštevníci.
5. Kliknite na **Navrhnúť zverejnenie**. Keď Endpoint ešte nie je verejný, na tlačidle je napísané **Sprístupniť verejne a navrhnúť zverejnenie** a na potvrdenie musíte prepísať názov Endpointu, pretože verejný Endpoint môže čítať ktokoľvek.

Dataset sa v katalógu objaví po tom, čo schvaľovateľ zmenu schváli. Zverejnenie na národnom portáli, ako je data.slovensko.sk, je popísané v [National Open Data Portals](../13-national-open-data-portals.md).

## 4. Zverejnenie verejného pohľadu, verejného formulára a dokumentácie API

Tieto tri verejné adresy sa vytvárajú z kontextového priestoru alebo endpointu vnútri projektu; návštevník ich otvorí bez účtu.

### Verejný pohľad, /v/{slug}

V kontextovom priestore voľba **Zverejniť tento typ ako verejný odkaz** zverejní tabuľku jedného typu určenú len na čítanie s atribútmi, ktoré necháte zaškrtnuté. Návštevník vidí tabuľku, prepína medzi typmi v časti **Typy**, ak má pohľad viacero typov, a nemôže nič zmeniť. Pohľad, ktorý bol stiahnutý, zobrazuje hlásenie **Tento pohľad nie je zverejnený alebo už nie je.**

### Verejný formulár, /f/{slug}

Voľba **Zverejniť ako verejný formulár** umožňuje komukoľvek vytvoriť jeden záznam v priestore, napríklad hlásenie o pokazenej pouličnej lampe. Vyberiete polia, na ktoré sa formulár pýta, koľko záznamov za deň (**Záznamov za deň**) prijíma, a môžete zvoliť **Vložiť na web**. Tlačidlo **Navrhnúť verejný formulár** ho odošle schvaľovateľovi; tlačidlo **Odoslať skúšku** ho vopred otestuje.

Návštevník vyplní polia a stlačí **Vytvoriť**. Pole označené ako povinné musí byť vyplnené a formulár upozorní, ktorú odpoveď treba opraviť, napríklad „Zadajte celé číslo, napríklad 12.“ Formulár informuje návštevníka, že jeho odpovede sa stávajú verejnými údajmi priestoru a nesmú obsahovať žiadne osobné údaje.

### Dokumentácia API, /d/{slug}

Verejný Endpoint má vlastnú stránku **Dokumentácia API**, vygenerovanú zo samotného Endpointu: čo odpovedá, vzorové volanie pre každé čítanie v časti **Požiadavka cez curl**, parametre každej adresy a odkaz na **Dokument OpenAPI (JSON)**. Túto adresu pošlite vývojárovi, ktorý chce čítať vaše dáta; [Endpoints, Data Sharing & Integration](05-endpoints-and-sharing.md) vysvetľuje, ako sa Endpoint publikuje.

## 5. Pripojenie AI asistenta k verejným dátam

Verejný MCP server projektu má vlastnú stránku na `/connect/{project}/{name}` s názvom **Pripojiť AI asistenta**. Nepotrebuje žiadny účet ani kľúč.

1. Skopírujte údaj **Adresa konektora** pomocou **Kopírovať adresu**.
2. V časti **Nastavte svojho klienta** postupujte podľa sekcie pre vášho klienta: Claude Code (**Kopírovať príkaz**), Claude Desktop (**Kopírovať konfiguráciu**), ChatGPT (uvedené kroky) alebo **Iní klienti MCP**.
3. Položte asistentovi otázku, ktorú stránka navrhuje, napríklad „Aké dáta toto ponúka? Ukáž mi päť záznamov s odkazom na zdroj.“

Stránka uvádza, koľko nástrojov server ponúka, že je určený len na čítanie a koľko požiadaviek za minútu môže jedna sieť odoslať. Ak sa zobrazí hlásenie o prekročení limitu požiadaviek z vašej siete, počkajte uvedený počet sekúnd. Prihlásení používatelia si vytvárajú vlastné konektory v časti **Moje MCP konektory**, čo popisuje kapitola [Working with AI Agents](08-working-with-ai-agents.md).

## 6. Slovník a vyhlásenie o prístupnosti

- **Slovník** na `/glossary` vysvetľuje každý pojem, ktorý platforma používa, jednou vetou s jedným príkladom. Nápoveda k termínu kdekoľvek v Portáli odkazuje na jeho položku.
- **Vyhlásenie o prístupnosti** na `/accessibility` je vyhlásenie, ktoré publikuje verejný orgán: právny základ, stav súladu, obsah, ktorý zatiaľ nie je prístupný, spôsob kontroly a kam napísať. Každá verejná stránka naň odkazuje v pätičke pod názvom **Prístupnosť**.

## Súvisiace

- [Endpoints, Data Sharing & Integration](05-endpoints-and-sharing.md): ako sa Endpoint za datasetom zverejňuje.
- [National Open Data Portals](../13-national-open-data-portals.md): registrácia katalógu na data.slovensko.sk a data.gov.cz.
- [Export, Import & Synchronization](09-export-import.md): zverejnenie otvorených dát do CKAN.
- [Working with AI Agents](08-working-with-ai-agents.md): osobné MCP konektory pre prihlásených ľudí.
