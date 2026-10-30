---
sidebar_position: 4
title: Dátové modelovanie a editor LinkML
description: Tvorba, import, prispôsobovanie a verziovanie dátových modelov pomocou LinkML, projekcií modelov a mapovaní.
routes:
  - /projects/$project/models
  - /projects/$project/models/$name
  - /projects/$project/datamodels
  - /projects/$project/projections
  - /projects/$project/mappings
---

# Dátové modelovanie a editor LinkML

V platforme joinedcontext sú všetky zmluvy o štruktúre dát modelované pomocou LinkML (Linked Open Data Modeling Language). Táto príručka vysvetľuje, ako importovať štandardné modely Smart Data Models, vytvárať vlastné triedy a sloty, konfigurovať projekcie endpointov, vytvárať mapovania a spravovať verzie schém. Je napísaná pre dátových architektov, správcov (stewardov) a integračných inžinierov. Anglická verzia je [Data Modeling & The LinkML Editor](../03-data-models.md).

Každá zmena dátového modelu sa riadi štandardným tokom zmien: upravíte model, kliknete na **Skontrolovať**, kliknete na uložiť model a schvaľovateľ posúdi a zlúči návrh v časti **Schvaľovania** skôr, ako sa schémy skompilujú.

## 1. Modely LinkML a vývoj schém

LinkML poskytuje jediný zdroj pravdy pre definície entít. Z jednej definície modelu platforma odvodzuje:

- Striktné schémy JSON Schema draft-07 na overovanie obsahu API.
- Štandardné súbory JSON-LD `@context` pre sémantickú interoperabilitu.
- Tvary SHACL, vykreslenia OWL a RDF, stránky dokumentácie a jednu overenú ukážkovú entitu, poskytovanú vedľa schémy na každom endpointe, ktorý model publikuje.

Zmeny schémy sa klasifikujú podľa ich vplyvu:

- **Doplnková zmena:** Pridanie voliteľných slotov alebo tried smeruje cez žltú úroveň.
- **Prelamujúca zmena:** Premenovanie slotov, zmena typov alebo odstránenie atribútov zvyšuje hlavnú verziu, vyžaduje explicitné potvrdenie a smeruje cez červenú úroveň.

## 2. Import dátového modelu

### Importovať model Smart Data Models

#### Ručne

1. Prejdite na **Dátové modely** na `/projects/helsinki/models`.
2. Vyberte kartu **Import**.
3. V časti **Katalóg Smart Data Models** napíšte `WeatherObserved` do poľa **Hľadať modely a atribúty**.
4. Vyberte `WeatherObserved` zo zoznamu.
5. Na paneli náhľadu skontrolujte atribúty. Kliknite na **Len povinné**, aby ste zachovali povinné sloty, alebo vyberte konkrétne atribúty. Nezaškrtnuté nadradené sloty sa označia ako zastarané (deprecated), aby sa obsahy partnerov overili.
6. V poli **Priestor pre tento model** vyberte `helsinki`.
7. Kliknite na importovať WeatherObserved. Zdroj sa načíta priamo do editora.
8. Na karte **Editor** kliknite na **Skontrolovať**. Mali by ste vidieť odznak závažnosti potvrdzujúci aktualizáciu.
9. Kliknite na uložiť model. Schvaľovateľ posúdi a zlúči návrh v časti **Schvaľovania**.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Import the WeatherObserved model from Smart Data Models into the helsinki project`

Asistent stiahne model, nakonfiguruje návrh a otvorí `/projects/helsinki/models` s naplneným editorom. Vy kliknete na **Skontrolovať**, kliknete na uložiť model a schvaľovateľ zmenu schváli.

### Odvodiť model zo súboru

#### Ručne

1. Na `/projects/helsinki/models` otvorte kartu **Import**.
2. V časti **Model zo súboru** presuňte vzorkový súbor CSV alebo JSON do zóny nahrávania.
3. Mali by ste vidieť dialóg náhľadu zobrazujúci odvodené triedy, stĺpce, zistené dátové typy a zhody v katalógu.
4. Kliknite na **Naplniť editor**.
5. Na karte **Editor** zadajte do poľa **Názov** hodnotu `city-weather` a ako priestor vyberte `helsinki`.
6. Kliknite na **Skontrolovať** a potom na uložiť model. Schvaľovateľ zlúči zmenu v časti **Schvaľovania**.

#### Opýtaním sa asistenta

Priložte súbor CSV alebo JSON v paneli asistenta a napíšte:
`Draft a data model from this sample file.`

Asistent analyzuje štruktúru vzorky, naplní editor LinkML a predloží návrh na `/projects/helsinki/models`.

## 3. Úprava tried a slotov

### Vytváranie atribútov vo vizuálnom editore

#### Ručne

1. Na `/projects/helsinki/models` vyberte kartu **Editor** a prepnite sa na zobrazenie **Štruktúra**.
2. V časti tried vyberte `WeatherObserved` alebo zadajte názov do poľa **Nová trieda** a kliknite na **Pridať**.
3. V časti slotov kliknite na slot, ktorý chcete upraviť, alebo zadajte názov do nového slotu a kliknite na **Pridať**.
4. Na paneli s podrobnosťami slotu nakonfigurujte:
   - Rozsah: Vyberte `float`, `string`, `integer` alebo enum.
   - Druh NGSI-LD: Vyberte `Property`, `Relationship` alebo `GeoProperty`.
   - Jednotka: Vyberte kód jednotky UN/CEFACT (ako napríklad `CEL` pre Celzius alebo `MTS` pre metre za sekundu).
   - Povinné: Zaškrtnite, ak užitočné zaťaženia musia tento atribút obsahovať.
5. Prepnite sa na zobrazenie zdroja, aby ste si prečítali a upravili vlastný YAML modelu, pričom jeho problémy sa označujú počas písania.
6. Prepnite sa na zobrazenie **Náhľad** a vyberte karty na kontrolu vygenerovanej schémy JSON Schema, `@context`, dokumentácie a vzorových normalizovaných entít.
7. Kliknite na **Skontrolovať** a potom na uložiť model. Schvaľovateľ zmenu zlúči.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Add an optional float slot called airQualityIndex to the WeatherObserved class`

Asistent aplikuje operáciu na návrh modelu a obnoví zobrazenie editora. Vy kliknete na **Skontrolovať** a uložiť model, aby ste navrhli zmenu.

## 4. Konfigurácia projekcií modelu pre endpointy

### Sprístupniť podmnožinu modelu na endpointe

#### Ručne

1. Prejdite na `/projects/helsinki/endpoints` a kliknite na **Nový endpoint** (alebo otvorte existujúci endpoint).
2. V časti **Projekcia modelu** vyberte **Navrhnúť novú** alebo vyberte existujúcu projekciu.
3. Pod triedami zaškrtnite typ entity, ktorý chcete sprístupniť (ako napríklad `BikeHireDockingStation`).
4. Zaškrtnite jednotlivé sloty, ktoré chcete sprístupniť (ako napríklad `availableBikeNumber`). Identifikačné sloty `id` a `type` zostávajú uzamknuté.
5. Ak endpoint prijíma zápisy dát, zaškrtnite **Zapisovateľné** a zadajte obmedzenia dopytov.
6. Kliknite na **Skontrolovať** a potom na **Navrhnúť zmenu**.
7. V `/projects/helsinki/approvals` schvaľovateľ návrh schváli.

#### Opýtaním sa asistenta

Napíšte do poľa pre asistenta:
`Create a projection for endpoint helsinki-bikes exposing only id, type, and availableBikeNumber`

Asistent vyberie požadované triedy a sloty, vygeneruje manifest projekcie a vyplní formulár pripravený na vašu kontrolu a navrhnutie.

## 5. Mapovania medzi modelmi

### Vytvoriť mapovanie transformácie schémy

#### Ručne

1. V `/projects/helsinki/models` vyberte kartu **Mapovania**.
2. V časti **Modely** vyberte zdrojový model v poli **Zdrojový model** a cieľový v poli **Cieľový model**.
3. Skontrolujte tabuľku zarovnania slotov. Pre nemapované sloty vyberte atribút z poľa **Zdrojový slot** alebo nakonfigurujte prevod jednotky v poli **Prevod jednotky**.
4. V časti **Zlatý test** vložte ukážkový objekt JSON do poľa **Vstupný príklad (JSON)**.
5. Mali by ste vidieť, ako **Transformovaný výstup** vykreslí výslednú transformovanú entitu podľa vašich pravidiel.
6. Kliknite na navrhnúť mapovanie.
7. V `/projects/helsinki/approvals` schvaľovateľ skontroluje rozdiel a súbory zlatých testov a potom zmenu schváli.

#### Opýtaním sa asistenta

Asistent nemôže automaticky overiť a navrhnúť mapovania schém bez posúdenia operátorom. Mapovacie transformácie konfigurujte a overujte ručne na karte **Mapovania**.

### Úprava mapovania pomocou formulára

Pravidlá slot po slote zostávajú na karte **Mapovania**. Formulár obsahuje všetko okolo nich: ktoré modely mapovanie spája, jeho zlaté testy a akýkoľvek kód, ktorý napíšete ručne. Každé pole má vedľa seba vo vašom jazyku uvedené, na čo slúži.

#### Ručne

1. Otvorte `/projects/banskabystrica/mappings`, otvorte ponuku riadka mapovania, napríklad `ovzdusie-to-airqualityobserved`, a kliknite na **Upraviť**.
2. V časti medzi ktorými modelmi sú **Názov** a **Kontextový priestor** pevne dané: iný názov by predstavoval nové mapovanie. V častiach **Zdrojový model** a **Cieľový model** nastavte **Dátový model** na publikovaný názov, ako napríklad `ovzdusie-senzory` a `airqualityobserved`, a **Hlavná verzia** na celé číslo, ako napríklad `1`. Cieľ nemôže byť zdrojom na rovnakej verzii.
3. V časti **Zlaté testy** každý riadok spája **Vstupný príklad** s **Očakávaný výstup**, ktorý musí vytvoriť, ako cesty vedľa mapovania, napríklad `./tests/ovzdusie-to-airqualityobserved.input.json`. Kontrola porovnáva každý pár, takže zmena pravidla, ktorá by niektorý porušila, sa ukáže skôr, ako ju niekto schváli.
4. V časti **Natívne bloky** pridajte kód iba vtedy, keď pravidlo nedokáže vyjadriť to, čo potrebujete. Vyberte **Cieľový slot**, ktorý napĺňa, napríklad `pm10`, **Jazyk** a napíšte **Kód**, napríklad `root = this.pm10_raw.number() / 10`. Ručne písaný kód ide vždy na prísnejšie posúdenie, pretože žiadna kontrola ho nedokáže prečítať.
5. Ponechajte **Skompilované artefakty** tak, ako sú: kompilátor tieto súbory zapíše za vás.
6. Kliknite na **Navrhnúť zmenu**. Mali by ste vidieť oznámenie s odkazom na návrh; schvaľovateľ o ňom rozhodne v `/projects/banskabystrica/approvals`.

## 6. Rozhodovanie o životnom cykle verzie modelu

Triedy a atribúty modelu pochádzajú z editora LinkML. Dve veci o verzii pochádzajú od vás: kde sa nachádza vo svojom živote a či jej entity môžu niesť atribúty, ktoré model nedeklaruje.

### Zmena životného cyklu verzie pomocou formulára

#### Ručne

1. Otvorte `/projects/banskabystrica/datamodels`, otvorte ponuku riadka modelu, napríklad `ovzdusie-senzory`, a kliknite na **Upraviť**.
2. V časti o verzii modelu si prečítajte **Názov**, **Kontextový priestor**, **Verzia** (ako napríklad `1.2.0`) a zdroj LinkML (napríklad `ovzdusie-senzory.linkml.yaml`). Tieto hodnoty meníte v editore LinkML na stránke **Modely**, nie tu.
3. V časti vašich rozhodnutí vyberte **Životný cyklus**. Návrh sa stále môže meniť. Publikovaná verzia je nemenná, takže jej čitatelia sa na ňu môžu spoľahnúť. Zastaraná verzia stále odpovedá, ale varuje každého čitateľa, a vyradená neodpovedá nikomu.
4. Prepnite **Prijímať nedeklarované atribúty** na zapnuté iba vtedy, keď priestor musí prijímať atribúty, ktoré model zatiaľ neuvádza. Pri vypnutom stave sa entita nesúca takýto atribút odmietne.
5. Kliknite na **Navrhnúť zmenu**. Schvaľovateľ vidí v návrhu presne tieto dve rozhodnutia.

## Súvisiace

- [Organizácie, projekty a kontextové priestory](02-organizations-projects-spaces.md): správa dátových oddielov.
- [Pipeliny a príjem dát](04-pipelines.md): použitie mapovaní v dátových transformačných prúdoch.
- [Endpointy a zdieľanie](05-endpoints-and-sharing.md): publikovanie schém projekcií modelov.
- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): posudzovanie návrhov zmien modelov.
- [Uchovávanie a expirácia](../14-retention-and-expiry.md): ako dlho sa uchovávajú typy modelu a osobné atribúty.
