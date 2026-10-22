---
sidebar_position: 6
title: Endpointy, zdieľanie údajov a integrácia
description: Zverejňovanie endpointov s viacerými reprezentáciami, konfigurácia publika, projekcií, filtrov a zdieľania medzi projektmi.
routes:
  - /projects/$project/endpoints
  - /projects/$project/policies
  - /projects/$project/subscriptions
  - /projects/$project/csrs
  - /projects/$project/shared
---

# Endpointy, zdieľanie údajov a integrácia

V platforme joinedcontext sú kontextové priestory predvolene súkromné. Jediným mechanizmom, ako môžu externé systémy, partnerské projekty, verejné portály alebo AI agenti pristupovať ku kontextovým údajom, je Endpoint. Tento návod vysvetľuje, ako zverejňovať endpointy, konfigurovať publikum a reprezentácie, aplikovať projekcie atribútov a filtre oblastí, pripájať nástroje tretích strán a odkazovať na zdieľané endpointy medzi projektmi. Je určený pre dátových stewardov, GIS analytikov a integračných inžinierov. Anglická verzia je [Endpoints, Data Sharing & Integration](../05-endpoints-and-sharing.md).

Každá zmena endpointu prebieha cez proces schvaľovania zmien: nakonfigurujete formulár endpointu, spustíte **Skontrolovať**, kliknete na **Navrhnúť zmenu** a schvaľovateľ návrh posúdi a zlúči v Schvaľovaniach. Verejné endpointy prechádzajú červenou úrovňou rizika a na potvrdenie vyžadujú zadanie názvu prostriedku.

## 1. Hranice endpointu a publikum

Endpoint poskytuje pohľad chránený politikami nad jedným kontextovým priestorom. Prístup je riadený publikom endpointu:

- **Vybrané projekty (`project-list`):** Dopytovať sa alebo odkazovať na tento endpoint môžu len určené spolupracujúce projekty v rámci organizácie.
- **Organizácia (`organization`):** K tomuto endpointu má prístup ktorýkoľvek prihlásený používateľ alebo servisný účet v správe mesta.
- **Verejné (`public`):** Otvorené pre anonymných volajúcich na celom svete na čítanie. Anonymní volajúci nemôžu zapisovať údaje ani registrovať odbery.

Každý endpoint má svoju vlastnú adresu: 26-znakový náhodný slug, ktorý nikto neuhádne.
`https://api.{domain}/api/endpoint/{slug}/`

## 2. Zverejnenie endpointu

### Vytvorenie nového endpointu

#### Ručne

1. Prejdite na **Endpointy** na `/projects/helsinki/endpoints`.
2. Kliknite na **Nový endpoint**.
3. Do **Názov** zadajte `helsinki-bikes`. Do **Popis** zadajte `City bikes live feed`.
4. V **Kontextový priestor** vyberte `helsinki`.
5. Kliknite na **Vygenerovať slug** na vytvorenie náhodnej adresy.
6. V časti **Publikum** vyberte `Public: anyone with the address` (alebo `Organization`).
7. V časti **Reprezentácie** zaškrtnite potrebné formáty: `NGSI-LD API`, `CSV`, `OGC API Features` a `MCP for AI assistants`.
8. Pole **Prevádzka a limity** nechajte prázdne pre endpoint bez obmedzenia rýchlosti, čo je predvolené nastavenie. **Požiadavky za minútu** nastavte len vtedy, ak chcete ochrániť verejný endpoint pred jedným preťažujúcim volajúcim.
9. V časti **Projekcia modelu** zaškrtnite triedy (napr. `BikeHireDockingStation`) a sloty, ktoré chcete zverejniť. Identifikačné sloty `id` a `type` zostávajú uzamknuté.
10. Kliknite na **Skontrolovať**. Mali by ste vidieť stavový štítok `Checked`.
11. Kliknite na **Navrhnúť zmenu**.
12. V `/projects/helsinki/approvals` schvaľovateľ zadá `helsinki-bikes` do **Názov prostriedku pre potvrdenie** a klikne na **Schváliť**.

Tieto kroky prehráva živá cesta `share.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Set the helsinki-bikes endpoint's rate limit to 300 requests per minute`

Asistent otvorí `/projects/helsinki/endpoints` s otvoreným formulárom a aktualizovaným limitom požiadaviek. Spustíte **Skontrolovať** a kliknete na **Navrhnúť zmenu**. Schvaľovateľ ju potvrdí v Schvaľovaniach.

Tieto kroky prehráva živá cesta `change.spec.ts`.

## 3. Filtrovanie atribútov a geografických oblastí

### Správa filtrov na stránke endpointu

#### Ručne

1. Na `/projects/helsinki/endpoints` kliknite na názov endpointu, čím otvoríte jeho stránku s podrobnosťami na `/projects/helsinki/endpoints/helsinki-bikes`.
2. Skontrolujte živú URL, publikum a povolené reprezentácie.
3. V časti **Filtrovanie** si pozrite aktívne dopyty.
4. Ak chcete pridať podmienku atribútu, prejdite na **Pridať podmienku**: vyberte **Atribút** (`availableBikeNumber`), **Podmienka** (`is greater than`), zadajte hodnotu `0` a kliknite na **Pridať do dotazu**.
5. Na geografické obmedzenie prejdite na **Nastaviť územie podľa obdľžnika**: zadajte súradnice do polí **Západ**, **Juh**, **Východ** a **Sever**, potom kliknite na **Použiť toto územie**.
6. Mali by ste vidieť aktualizovaný počet entít, ktorý ukazuje, koľko záznamov vyhovuje filtru.
7. Kliknite na **Navrhnúť tento filter**.
8. V `/projects/helsinki/approvals` schvaľovateľ posúdi a zlúči zmenu filtra.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Propose a filter for endpoint helsinki-bikes with query availableBikeNumber>0`

Asistent aktualizuje filter projekcie a otvorí `/projects/helsinki/endpoints/helsinki-bikes`. Skontrolujete zodpovedajúci počet a kliknete na **Navrhnúť tento filter**.

## 4. Pripojenie externých nástrojov

### Pripojenie GIS, analytických nástrojov a klientov agentov

Skopírujte adresy endpointu pomocou tlačidla **Kopírovať URL** vedľa ľubovoľného slugu:

- **QGIS a desktopový GIS:** Pridajte pripojenie OGC API Features smerujúce na `https://api.{domain}/api/endpoint/{slug}/ogc/features`.
- **Microsoft Excel a Power BI:** Zvoľte **Data > From Web** a zadajte URL pre export do CSV `https://api.{domain}/api/endpoint/{slug}/file.csv`.
- **Grafana:** V plugine zdroja údajov Infinity sa dopytujte na `/ngsi-ld/v1/entities?type=…` s hlavičkou `Accept: application/geo+json` na vykreslenie živých polôh na paneli Geomap.
- **AI agenti (MCP):** Pripojte externé prostredia agentov (napríklad Claude Code) na `https://api.{domain}/api/endpoint/{slug}/mcp`. Agent automaticky objaví dopytovacie nástroje podľa politiky endpointu.
- Schéma a čo môžete robiť: `https://api.{domain}/api/endpoint/{slug}/schema/v1/AirQualityObserved.json` je zverejnená schéma jedného typu a `https://api.{domain}/api/endpoint/{slug}/access` odpovedá, čo volajúci v danom momente smie čítať a zapisovať.

## 5. Zdieľanie údajov medzi projektmi

### Odkazovanie na zdieľaný endpoint

#### Ručne

1. Prejdite na `/projects/helsinki/endpoints`.
2. Prejdite do časti **Zdieľané s týmto projektom**.
3. Pozrite si endpointy, ktoré iné projekty v organizácii zdieľali s projektom `helsinki`.
4. Na vybranom riadku kliknite na **Použiť v tomto projekte**.
5. Odošle sa návrh zmeny na deklarovanie `SharedSpaceReference`.
6. V `/projects/helsinki/approvals` schvaľovateľ odkaz schváli. Po zlúčení stavový štítok ukazuje **Odkazované**.
7. Administrátor organizácie nájde každý endpoint každého projektu na stránke **Organizácia**, záložka **Endpointy** (`/organization/endpoints`). Nikomu inému sa táto tabuľka neponúka: vlastné endpointy projektu zostávajú v jeho časti **Endpointy**.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`What endpoints are shared with project helsinki?`

Asistent skontroluje medziprojektový adresár a vypíše prístupné endpointy, ich zdrojové projekty a ich zverejnené typy entít.

## 6. Rozhodovanie o tom, kto smie čítať a zapisovať: Politiky

Endpoint určuje, kde sa údaje poskytujú; Politika určuje, kto s nimi smie čo robiť. Každá politika pokrýva jeden Kontextový priestor a udeľuje (alebo zamieta) množinu operácií jednému príjemcovi. Ako každá iná zmena, aj nová politika nadobudne účinnosť až po schválení jej návrhu.

### Zápis politiky pomocou formulára

Nižšie uvedený príklad je politika, ktorá umožňuje komukoľvek čítať merania kvality ovzdušia v Banskej Bystrici, `public-read` v projekte `banskabystrica`.

1. V bočnom paneli otvorte **Politiky** na `/projects/banskabystrica/policies`. Každý riadok uvádza, čo politika povoľuje, komu, na ktorom priestore a koľko operácií to pokrýva. Zákaz nesie červený odznak **Zákaz**.
2. Kliknite na **Nová politika**. Formulár sa otvorí v troch skupinách; prvá je otvorená.
3. Kto a čo:
   - **Názov**: krátky názov, pod ktorým je politika evidovaná, napríklad `public-read`. Dve politiky jedného projektu nemôžu mať rovnaký názov.
   - **Kontextový priestor**: priestor, o ktorého údajoch politika rozhoduje, tu `ovzdusie`. Politika pokrýva presne jeden priestor.
   - **Účinok**: **Povolenie** udeľuje to, čo politika uvádza. **Zákaz** to odoberá a platforma vyhodnocuje každý zákaz pred akýmkoľvek povolením, preto ho zvoľte len na uzavretie niečoho, čo iná politika otvára.
   - **Druh príjemcu**: rola, skupina, jedna osoba, servisný účet alebo DID. Pre anonymných volajúcich zvoľte `role`.
   - **Príjemca**: názov tejto roly, skupiny, osoby alebo účtu, ako ho uvádza poskytovateľ identity, tu `public`.
   - **Operácie**: zaškrtnite jednu z piatich pomenovaných skupín. Vedľa každej skupiny formulár uvádza operácie, ktoré pokrýva, a dve skupiny, ktoré menia údaje, nesú označenie **mení údaje**. Pre prístup na čítanie zaškrtnite `retrieveOps`. Jednotlivé operácie sa nachádzajú pod **Jednotlivé operácie**; povolenie zvyčajne namiesto toho uvádza skupinu. Nič nie je udelené, kým nie je zaškrtnuté aspoň jedno políčko.
4. **Entity a atribúty** (otvorte skupinu):
   - V časti **Výbery entít** pridajte jeden a zadajte **Typ entity** `AirQualityObserved`. Selektor bez typu nepokrýva nič a formulár ho pri danom poli odmietne.
   - **Vzor identifikátora** je nepovinný a zužuje povolenie na identifikátory, ktoré mu zodpovedajú, napríklad `^urn:ngsi-ld:AirQualityObserved:banskabystrica\.sk:ovzdusie:.*$`.
   - **Vlastnosti**: uveďte vlastnosti, ktoré príjemca smie dosiahnuť, tu `dateObserved`, `location`, `observedAt`, `pm10`, `pm25`. Atribút, ktorý vynecháte, sa neposkytuje, takže `reliability` a `refDevice` stanice zostanú súkromné. Prázdny zoznam dosiahne každú vlastnosť.
   - **Vzťahy**: to isté platí pre vzťahy, napríklad `refDistrict`. Prázdny zoznam dosiahne všetky.
5. Zvyškové filtre a platnosť (nepovinné, otvorte skupinu):
   - `q`: podmienka na atribúty, napríklad `pm10>=0`. Entita, ktorá jej nevyhovie, je mimo povolenia.
   - `scopeQ`: vetva stromu rozsahu, ktorú povolenie pokrýva, napríklad `/geo/SK/BB`, a všetko pod ňou.
   - `geoQ`: oblasť, ktorú povolenie pokrýva; entita mimo nej sa nečíta ani nezapisuje.
   - `temporalQ`: časové okno histórie, ktoré povolenie pokrýva, napríklad `timerel=after&timeAt=2026-01-01T00:00:00Z`.
   - **Platí od** a **Platí do**: okamihy, kedy povolenie začína a prestáva platiť. Obe nechajte prázdne pre povolenie bez časového obmedzenia.
6. Kliknite na **Skontrolovať**. Stavový štítok zobrazí `Checked`, keď je politika úplná.
7. Kliknite na **Navrhnúť zmenu**. Formulár nenavrhne širšie povolenie, než aké môžete navrhnúť sami; ak je odmietnuté, dôvod sa zobrazí vedľa tlačidla.
8. V `/projects/banskabystrica/approvals` schvaľovateľ povolenie posúdi a schváli ho. Odvtedy endpointy na priestore `ovzdusie` odpovedajú anonymným čitateľom s piatimi uvedenými vlastnosťami.

Ak chcete zmeniť existujúcu politiku, otvorte ponuku jej riadku a zvoľte **Upraviť**. Otvorí sa rovnaký formulár s uloženými hodnotami. Zobrazenie **YAML** ukazuje rovnaký manifest a zmena v ktoromkoľvek zobrazení sa prejaví aj v druhom.

## 7. Upozornenie na zmenu údajov: Odbery

Odber žiada brokera jedného priestoru, aby poslal notifikáciu vášmu prijímaču vždy, keď sa sledované entity zmenia: napríklad dispečing, ktorý chce vedieť o každom meraní PM10 nad limitom.

### Vytvorenie odberu pomocou formulára

#### Ručne

1. Otvorte `/projects/banskabystrica/subscriptions` a kliknite na **Nový odber**.
2. V časti Priestor a príjemca zadajte **Názov**, napríklad `ovzdusie-prekrocenia`, a vyberte **Kontextový priestor**, ktorého údaje sleduje, napríklad `ovzdusie`. **Zobrazovaný názov** je to, čo ľudia vidia v Portáli, napríklad *Prekročenia PM10 v Banskej Bystrici*.
3. V časti **Príjemca** zadajte **Adresa**, na ktorú broker odosiela požiadavky, napríklad `https://dispecing.example.org/hooks/ovzdusie`. Mimo klastra to musí byť `https` a nikdy nenesie heslo ani token. Ak príjemca overuje prihlasovacie údaje, uveďte **Názov tajomstva** a **Kľúč v tajomstve**, ktoré ich uchovávajú, napríklad `dispecing-hook` a `token`. Formulár ukladá len tento odkaz, nikdy nie hodnotu. **Hlavičky** slúžia na bežné hodnoty, ktoré príjemca potrebuje, napríklad `X-Dispecing-Zdroj: jc-ovzdusie`; hlavička `Authorization` alebo `Cookie` patrí radšej do prihlasovacieho údaja.
4. V časti Čo sa sleduje pridajte riadky do **Sledované entity**: **Typ entity** ako `AirQualityObserved` sleduje každú entitu tohto typu, **Identifikátor entity** sleduje jednu a **Vzor identifikátora** sleduje každú entitu, ktorej identifikátor mu zodpovedá. V **Sledované atribúty** uveďte atribúty, ktorých zmena má odber spustiť, napríklad `pm10` a `pm25`; ak zostane prázdne, spustí ho akákoľvek zmena. Napíšte **Popis**, prečo odber existuje.
5. V časti Filtre, tempo a životnosť zúžte podmienky spustenia pomocou `q`, napríklad `pm10>50`, alebo oblasť pomocou `geoQ`. **Najkratší interval (sekundy)**, napríklad `60`, bráni vyťaženej stanici zaplaviť príjemcu. **Platí do** ukončí odber k dátumu; ak zostane prázdne, beží, kým ho neodstránite. Vypnutie **Posielať notifikácie** odber pozastaví bez jeho vymazania.
6. Kliknite na **Skontrolovať**, potom na **Navrhnúť zmenu**. Odber sa spustí po tom, čo schvaľovateľ návrh prijme, a jeho riadok zobrazuje **Pozastavené**, kým sú notifikácie vypnuté.

## 8. Odpovedanie z iného zdroja: Registrácie kontextových zdrojov

Registrácia oznámi brokerovi priestoru, že časť jeho údajov má iný zdroj, takže na dopyt na váš priestor sa odpovedá z oboch. Týmto iným zdrojom môže byť endpoint tejto platformy alebo broker NGSI-LD inde. O tom, čo vráti, naďalej rozhodujú jeho vlastné politiky.

### Registrácia zdroja pomocou formulára

#### Ručne

1. Otvorte `/projects/banskabystrica/csrs` a kliknite na **Nová registrácia**.
2. V časti **Kde sú údaje** vyberte **Endpoint tejto platformy** alebo **NGSI-LD API inde**. Zadajte registrácii **Názov**, napríklad `zvolen-ovzdusie`, a vyberte **Kontextový priestor**, ktorého broker má odpovedať s údajmi tohto zdroja, napríklad `ovzdusie`.
3. Pri endpointe tejto platformy vyberte **Endpoint**; údaje sa čítajú cez neho a jeho politiky. Pri brokeri inde zadajte jeho **Základná URL NGSI-LD** bez `/ngsi-ld/v1`, napríklad `https://ngsi.example.org`, a v časti **Identita pri preposielaní** vyberte, či sa platforma pýta ako jeden z jej **Servisné účty**, napríklad `ovzdusie-hub`, alebo posiela ďalej prihlásenie samotného volajúceho.
4. V časti **Čo zdroj drží** pridajte riadok pre každé tvrdenie: **Typ entity** ako `AirQualityObserved`, alebo jeden **Identifikátor entity**, alebo **Vzor identifikátora**, ktorý typ zužuje. Uveďte **Vlastnosti** a **Vzťahy**, ktoré zdroj drží, napríklad `pm10`, `pm25` a `location`; ak zostanú prázdne, tvrdenie pokrýva všetky.
5. Vyberte, ktoré **Operácie** smerujú na zdroj, a **Režim**. Inkluzívny režim zlúči odpoveď zdroja s vlastnými údajmi priestoru; exkluzívny režim urobí zo zdroja jedinú odpoveď pre to, čo registrácia pokrýva.
6. V časti Schéma zrkadlenia a expirácia **Interval zrkadlenia schém** určuje, ako často sa schémy zdroja kopírujú sem, napríklad `24h`; ak zostane prázdne, raz denne. **Platí do** zabezpečí, že broker sa k danému dátumu prestane zdroja pýtať.
7. Kliknite na **Skontrolovať**, potom na **Navrhnúť zmenu**. Po tom, čo ju schvaľovateľ prijme, sa na dopyty na priestor odpovedá aj zo zdroja.

## Súvisiace

- [Začíname](01-getting-started.md): prvé kroky v Portáli.
- [Pipeliny a príjem údajov](04-pipelines.md): príjem údajov cez cieľové endpointy.
- [Dashboardy a vizualizácia](06-dashboards.md): vykreslenie entít endpointu na mape.
- [Spolupráca s autonómnymi AI agentmi](08-working-with-ai-agents.md): pripojenie autonómnych agentov k endpointom cez MCP.
