---
sidebar_position: 7
title: Dashboardy a geopriestorová vizualizácia
description: Vytváranie mapových dashboardov a vrstiev nad endpointmi projektu a skúmanie entít za nimi.
routes:
  - /projects/$project/dashboards
  - /projects/$project/explore
---

# Dashboardy a geopriestorová vizualizácia

Dashboard je stránka máp a čísel vytvorená z endpointov vášho projektu. Tento návod vysvetľuje, ako ho vytvoriť, ako nastylovať jeho vrstvy, čo smie verejný dashboard čítať, ako pridať graf alebo tabuľku vedľa mapy a ako sa pozrieť na entity za bodom. Je určený pre analytikov, autorov dashboardov a dátových stewardov. Anglická verzia je [Dashboards & Geospatial Visualization](../06-dashboards.md).

Každá zmena dashboardu prechádza procesom schvaľovania zmien: vytvoríte alebo upravíte dashboard alebo vrstvu, kliknete na **Navrhnúť zmenu** a schvaľovateľ posúdi a zlúči návrh v Schvaľovaniach pred tým, ako sa akákoľvek vizualizácia zverejní.

## 1. Čo je dashboard a čo smie verejný dashboard čítať

Dashboard obsahuje stránky; stránka obsahuje vrstvy na mape a widgety vedľa nej. Vrstva predstavuje entity jedného typu z jedného endpointu so štýlom, kódovaním a filtrom, takže dashboard číta len to, čo endpoint už zverejňuje a čo jeho politika už povoľuje.

O tom, čo môžete umiestniť na dashboard, rozhoduje jedno pravidlo: dashboard, ktorého **Viditeľnosť** je `public`, smie čítať len verejné endpointy. Ak vrstva verejného dashboardu ukazuje na endpoint zverejnený pre organizáciu alebo vybrané projekty, táto vrstva sa nevykreslí a dashboard uvedie, ktorú vynechal.

Mapa vyžaduje WebGL. V prehliadači bez jeho podpory to dashboard oznámi namiesto toho, aby vykreslil prázdny rámec.

## 2. Vytvorenie mapového dashboardu

### Vytvorenie dashboardu a stylovaných vrstiev

#### Ručne

1. Prejdite na **Dashboardy** na `/projects/helsinki/dashboards`.
2. Kliknite na **Nový dashboard**.
3. Do **Názov** zadajte `city-bikes-overview`. Do **Popis** zadajte `City Bikes Overview`. Nastavte **Viditeľnosť** na `project` (alebo `public`). Kliknite na **Navrhnúť zmenu**.
4. Kliknite na **Nová vrstva**.
5. Do **Názov** zadajte `bike-stations-layer`.
6. Vyberte **Endpoint** `helsinki-bikes` a **Typ entity** `BikeHireDockingStation`.
7. Vyberte **Štýl**: `circle`, `line`, `fill`, `heatmap`, `hexagon` alebo `icon`.
8. V časti **Farba podľa** vyberte číselnú vlastnosť `availableBikeNumber`, **Paleta** a **Rozsah hodnôt [min, max]**, medzi ktorými sa farby pohybujú (napríklad 0 a 30).
9. V časti **Atribúty v bubline** vyberte atribúty, ktoré sa majú zobraziť po výbere bodu na mape.
10. Kliknite na **Navrhnúť zmenu**.
11. V `/projects/helsinki/approvals` schvaľovateľ schváli návrhy dashboardu a vrstvy.
12. Mali by ste vidieť interaktívnu mapu vykresľujúcu vektorové body so živým škálovaním farieb a legenda **Vrstvy** umožňuje prepínať viditeľnosť vrstiev.

Tieto kroky prehráva živá cesta `assistant-creates.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Make a dashboard called city-bikes-overview showing the bikes of the helsinki space`

Asistent otvorí `/projects/helsinki/dashboards` s pripraveným návrhom dashboardu a vrstiev. Skontrolujete plánované zmeny a kliknete na **Navrhnúť zmenu**. Schvaľovateľ návrh zlúči.

Tieto kroky prehráva živá cesta `assistant-creates.spec.ts`.

## 3. Pridávanie widgetov: Grafy a tabuľky

### Pridanie časových grafov a dátových tabuliek

#### Ručne

1. Na `/projects/helsinki/dashboards` vyberte svoj dashboard a kliknite na **Upraviť**.
2. V časti **Stránky** pridajte alebo spravujte stránky. Keď dashboard obsahuje viacero stránok, nad plátnom sa zobrazia navigačné záložky.
3. V časti **Widgety** pridajte analytický widget:
   - Graf jednej vlastnosti v čase: nastavte **Typ widgetu** na `temporal-chart`, vyberte **Endpoint** `helsinki-bikes`, zadajte **Id entity** (napríklad `urn:ngsi-ld:BikeHireDockingStation:hel.fi:helsinki:station-1`) a **Atribút**, ktorý sa má vykresliť (`availableBikeNumber`).
   - Tabuľka entít: nastavte **Typ widgetu** na `grid`, vyberte **Endpoint** a **Typ entity** a vyplňte **Nastavenie tabuľky**.
4. Kliknite na **Navrhnúť zmenu**.
5. V `/projects/helsinki/approvals` schvaľovateľ návrh zlúči.
6. Mali by ste vidieť časový graf vykresľujúci trendy hodnôt v čase a dátovú tabuľku uvádzajúcu záznamy pod plátnom mapy.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Add a temporal chart widget for availableBikeNumber on station-1 to the city-bikes-overview dashboard`

Asistent nakonfiguruje parametre widgetu a otvorí editor dashboardu. Skontrolujete nastavenia a kliknete na **Navrhnúť zmenu**.

## 4. Prehliadanie údajov v prieskumníku entít

### Vyhľadávanie, kontrola a export entít

#### Ručne

1. Prejdite na **Prehliadať dáta** na `/projects/helsinki/explore`.
2. V **Kontextový priestor** vyberte `helsinki`.
3. V **Čítať cez endpoint** vyberte `helsinki-all` (alebo ľubovoľný endpoint zverejňujúci priestor).
4. V **Typ entity** vyberte `BikeHireDockingStation`.
5. Mali by ste vidieť tabuľku entít naplnenú živými záznamami, ovládacími prvkami stránkovania a hodnotami atribútov.
6. Použite vstupy stĺpcových filtrov na zúženie záznamov podľa atribútu alebo kliknite na **Nakresliť oblasť** na paneli mapy na nakreslenie ohraničujúcej oblasti a geografické filtrovanie.
7. Kliknutím na ľubovoľné ID riadku entity otvoríte úplný dokument entity JSON-LD v paneli podrobností.
8. Kliknite na export tejto stránky a stiahnite aktívnu stránku záznamov ako súbor JSON.

Tieto kroky prehráva živá cesta `load.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Show me bike stations with available bikes in the helsinki space`

Asistent vykoná dopyt a prejde na `/projects/helsinki/explore?space=helsinki&endpoint=helsinki-bikes&type=BikeHireDockingStation&q=availableBikeNumber>0` s tabuľkou filtrovanou na zodpovedajúce záznamy.

## Súvisiace

- [Začíname](01-getting-started.md): prvé kroky v Portáli.
- [Endpointy a zdieľanie](05-endpoints-and-sharing.md): konfigurácia zdrojov endpointov pre dashboardy.
- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): posudzovanie návrhov zmien dashboardov a vrstiev.
- [Aplikácie na požiadanie](11-apps.md): rozhodovanie medzi interaktívnymi dashboardmi a účelovými aplikáciami.
