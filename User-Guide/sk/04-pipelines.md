---
sidebar_position: 5
title: Pipeliny a príjem údajov
description: Nasadzovanie, monitorovanie a testovanie pipelín na príjem údajov, pripájanie zdrojov údajov a vytváranie inštancií šablón.
routes:
  - /projects/$project/pipelines
  - /projects/$project/datasources
  - /projects/$project/flows
  - /projects/$project/blueprints
  - /projects/$project/mqttbrokers
---

# Pipeliny a príjem údajov

Pipeline číta zdroj údajov a zapisuje entity do kontextového priestoru. Tento návod vysvetľuje, ako deklarovať zdroj údajov, zostaviť pipeline, ktorá ho číta, otestovať mapovanie na vzorke pred navrhnutím zmien, nastaviť celý kanál z galérie tokov a skontrolovať, či pipeline beží. Je určený pre dátových stewardov, integračných inžinierov a operátorov pipelín. Anglická verzia je [Pipelines & Ingestion](../04-pipelines.md).

Každá zmena pipeliny prebieha cez proces schvaľovania zmien: nakonfigurujete zdroj alebo pipeline, otestujete mapovanie alebo otestujete kanál sondou, kliknete na **Navrhnúť zmenu** a schvaľovateľ posúdi a zlúči návrh v Schvaľovaniach pred spustením vykonávania.

## 1. Triedy vykonávania a tok zmien

Pipeline beží jedným z dvoch spôsobov a o tom, ktorým, rozhoduje **Beh**:

- `resident` beží nepretržite: kanál, ktorý dáta tlačí (MQTT broker, WebSocket), alebo **Perióda** kratšia ako 30 sekúnd.
- `scheduled` sa spustí a dokončí: **Perióda** 30 sekúnd alebo viac, alebo **Rozvrh** zapísaný ako päť polí cron, napríklad `10 0 * * *`. Medzi behmi nič nestojí.
- `auto` je tretia a najjednoduchšia voľba: platforma prečíta periódu a zvolí `resident` pri menej ako 30 sekundách a `scheduled` pri 30 sekundách a viac.

## 2. Pripojenie externého zdroja údajov

### Pridanie pripojenia zdroja údajov

#### Ručne

1. Prejdite na **Zdroje údajov** na `/projects/helsinki/datasources`.
2. V **Typ** vyberte typ pripojenia (napríklad `HTTP endpoint` alebo `MQTT broker`).
3. Kliknite na **Nový zdroj údajov**.
4. Do **Názov** zadajte `hsl-citybikes-free`.
5. Do **URL** zadajte `https://gbfs.theta.fifteen.eu/gbfs/2.2/helsinki/en/free_bike_status.json`.
6. Nastavte **Časový limit** na `15s`. Ak sa vyžaduje autentifikácia, vyberte odkazy na prihlasovacie údaje v **Prihlasovacie údaje** (odkazy na tajomstvá preberajú názov tajomstva a kľúč; surové hodnoty sa nikdy neukladajú).
7. Kliknite na **Skontrolovať**. Uvidíte **Plánovaná zmena** a výsledky sondy zobrazujúce stiahnuté záznamy a počty bajtov.
8. Kliknite na **Navrhnúť zmenu**.
9. V `/projects/helsinki/approvals` schvaľovateľ klikne na **Schváliť**.

Tieto kroky prehráva živá cesta `load.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Add an HTTP data source called hsl-citybikes-free that reads https://gbfs.theta.fifteen.eu/gbfs/2.2/helsinki/en/free_bike_status.json`

Asistent otvorí dialóg vytvorenia na `/projects/helsinki/datasources` s predvyplnenou URL. Kliknete na **Skontrolovať**, overíte správu sondy a kliknete na **Navrhnúť zmenu**. Schvaľovateľ návrh zlúči.

Tieto kroky prehráva živá cesta `assistant-creates.spec.ts`.

## 3. Zostavenie a testovanie pipelín v štúdiu

### Zostavenie a testovanie pipeliny na príjem údajov

#### Ručne

1. Prejdite na **Pipeliny** na `/projects/helsinki/pipelines`.
2. Kliknite na **Nová pipelina**.
3. V časti **1. Zdroj** vyberte **Čítať z** ako `A data source of this project (external feed)` a zvoľte `hsl-citybikes-free`.
4. V **Pipeline** zadajte `citybikes-free` a nastavte **Perióda** na `60s`.
5. Nastavte **Cieľový endpoint** na `helsinki-all`.
6. V **Výpočet** vyberte **Druh** ako `Bloblang mapping`.
7. Zadajte výraz Bloblang mapovania, ktorý mapuje vstupné záznamy na entity NGSI-LD, alebo presuňte vzorový súbor na automatickú prípravu mapovania.
8. V **Výstup** zadajte **Typ entity** ako `Vehicle` a nastavte **Režim zápisu** na `upsert`.
9. V časti **Vyskúšať na vzorke** kliknite na **Otestovať na URL zdroja** a kliknite na **Otestovať mapovanie**.
10. Uvidíte, že všetky správy sa mapujú na entity, a tlačidlo **Navrhnúť zmenu** sa sprístupní.
11. Kliknite na **Navrhnúť zmenu**.
12. V `/projects/helsinki/approvals` schvaľovateľ návrh zlúči.

Tieto kroky prehráva živá cesta `load.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Create a pipeline called citybikes-free that reads the hsl-citybikes-free data source every 60s and writes into the helsinki space through the helsinki-all endpoint`

Asistent otvorí dialóg štúdia na `/projects/helsinki/pipelines` s nakonfigurovanými parametrami. Overíte test mapovania a kliknete na **Navrhnúť zmenu**.

Tieto kroky prehráva živá cesta `assistant-creates.spec.ts`.

## 4. Výpočet KPI pomocou predvolieb pipeliny

### Konfigurácia indikačnej pipeliny

#### Ručne

1. V `/projects/helsinki/pipelines` kliknite na **Nová pipelina**.
2. V **Predvoľba** vyberte `Analyse (KPI)`.
3. V **Zdrojový endpoint** vyberte `helsinki-all`.
4. Nastavte **Názov ukazovateľa** na `bikes-available-avg`.
5. Nastavte **Typ entity** na `BikeHireDockingStation` a **Atribút** na `availableBikeNumber`.
6. V **Agregácia** vyberte `Average`.
7. Do **Perióda** zadajte `15m`.
8. Kliknite na **Otestovať na stránke endpointu**. Uvidíte, ako **Vypočítaná hodnota** vypočíta a zobrazí číselný výsledok.
9. Kliknite na **Navrhnúť zmenu**.
10. V `/projects/helsinki/approvals` schvaľovateľ posúdi a zlúči návrh.

Tieto kroky prehráva živá cesta `analyse.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Create a KPI pipeline called bikes-available-avg calculating average availableBikeNumber every 15m from endpoint helsinki-all`

Asistent vyplní predvoľbu KPI v štúdiu, zostaví vzorec ukazovateľa a vypočíta hodnotu náhľadu. Kliknete na **Navrhnúť zmenu** a schvaľovateľ zmenu zlúči.

## 5. Nasadzovanie tokov zo šablón

### Vytvorenie inštancie zo šablóny

#### Ručne

1. Prejdite na **Zdroje údajov** na `/projects/helsinki/datasources`.
2. V časti **Pripravené nastavenia** si prečítajte karty: kanál GBFS mestských bicyklov, kanál JSON načítavaný do kontextového priestoru, kanál MQTT. Každá karta ukazuje cestu posúdenia (**Schvaľuje sa automaticky**, **Jeden schvaľovateľ** alebo **Úplné schválenie**). Časť ukazuje iba nastavenia, ktoré vaša rola smie spustiť; ak žiadne nie sú, chýba.
3. Kliknite na **Nastaviť** na karte.
4. Vyplňte parametre vygenerované zo schémy šablóny (ako je adresa kanála, interval načítania a Endpoint, cez ktorý tok zapisuje).
5. Kliknite na **Navrhnúť zmenu**. **Späť na zdroje údajov** odíde bez zápisu.
6. Platforma rozbalí šablónu do manifestov a otvorí návrh zmeny.
7. V `/projects/helsinki/approvals` schvaľovateľ návrh schváli.

Aplikácia zo zadania sa začína v **Aplikácie** tlačidlom **Nová aplikácia**. Stará adresa `/projects/helsinki/flows` otvorí domovskú stránku projektu.

#### Požiadaním asistenta

Asistent vám môže odporučiť šablóny zodpovedajúce vášmu zdroju údajov a spustiť ich nástrojom `jc_flow_start`, ale formuláre parametrov musíte odoslať a skontrolovať vy.

## 6. Pozastavenie, spustenie a stav prúdu

### Správa bežiacich pipelín

#### Ručne

1. Na `/projects/helsinki/pipelines` skontrolujte živé prevádzkové hodnoty v tabuľke: priepustnosť správ (msg/s), prijaté správy, počty chýb a latenciu p99.
2. V ponuke akcií riadku kliknite na **Pozastaviť** pri bežiacej pipeline.
3. Tým sa vytvorí návrh nastavujúci `spec.enabled: false`.
4. V `/projects/helsinki/approvals` schvaľovateľ klikne na **Schváliť**. Prúd sa čisto zastaví.
5. Ak chcete prúd znova spustiť, kliknite na **Spustiť** na pozastavenom riadku a schváľte výsledný návrh.

Tieto kroky prehráva živá cesta `change.spec.ts`.

#### Požiadaním asistenta

Napíšte do poľa pre asistenta:
`Pause the hel-news pipeline`

Asistent otvorí `/projects/helsinki/pipelines?edit=hel-news` s formulárom prepnutým na pozastavenie pipeliny. Kliknete na **Navrhnúť zmenu** a schvaľovateľ ju potvrdí v Schvaľovaniach.

Tieto kroky prehráva živá cesta `change.spec.ts`.

## 7. Odstraňovanie entít, ktoré zdroj prestal posielať

Pipeline zapisuje to, čo jej zdroj posiela, a nikdy nemaže. Keď kanál prestane uvádzať vozidlo, vozidlo v priestore zostane so svojou poslednou polohou. Ak zdroj posiela pri každom behu celý stav, môžete pipeline povedať, že absencia znamená odstránenie.

Použite to pre zdroje s úplným stavom: zoznam vozidiel, register staníc, export katalógu. Položka, ktorá v stave chýba, je preč.

Nechajte to vypnuté pri prírastkových kanáloch a kanáloch udalostí: merania senzorov, prúdy zmien, kanál, ktorý posiela len to, čo sa zmenilo. Tichá entita tam nemá čo nové povedať a expirácia by ju vymazala. Preto je expirácia vypnutá, kým ju nezapnete.

Keď zdroj dáva každej položke koncový čas, dajte pipeline radšej **Životnosť** (časť 8); spôsoby odstraňovania údajov porovnáva [Retention & Expiry](../14-retention-and-expiry.md#3-which-one-do-i-pick). Pipeline nemôže niesť pre rovnaký typ expiráciu aj životnosť celej entity.

### Zapnutie expirácie

#### Ručne

1. Na `/projects/helsinki/pipelines` otvorte pipeline a zapnite **Odstraňovať entity, ktoré zdroj už neposiela**.
2. Zadajte časové okno (napríklad `14d`) a typy entít, ktoré táto pipeline zapisuje.
3. Kliknite na **Navrhnúť zmenu**. Portál návrh odmietne, kým do rovnakého priestoru zapisuje iná pipeline a kým žiadna Politika neudeľuje účtu pipeliny operáciu `deleteBatch` na tieto typy; správa pomenúva Politiku, ktorú treba rozšíriť.
4. Schvaľovateľ ju potvrdí v Schvaľovaniach. Na stránke pipeliny a v zozname sa potom zobrazuje „Entity neaktualizované 14 dní sa odstraňujú“ a vymazania sa zobrazia v zázname aktivity pod účtom pipeliny.

## 8. Ukončenie entít a polí so životnosťou

Životnosť dáva tomu, čo pipeline zapisuje, koncový čas a broker to po uplynutí tohto času odstráni. Na rozdiel od expirácie nepotrebuje oprávnenie na mazanie ani druhý prechod: koncový čas cestuje s každým zápisom.

### Nastavenie životnosti

#### Ručne

1. Na `/projects/helsinki/pipelines` otvorte pipeline a kliknite na **Úprava pipeliny**.
2. Otvorte krok **Životnosť**. Vyberte jednu zo štyroch možností:
   - **Celá entita vyprší**, **Od poľa**: vyberte **Pole**, ktoré obsahuje čas, pre autobus `observedAt`, a rezervu v **Pridať**, pre autobus `5` `minutes`. Pre upozornenie vyberte `validTo` a nastavte **Najviac po zápise** na `30 days`, aby ho chybný rok neuchovával desaťročia.
   - **Celá entita vyprší**, **Po každom zápise**: entita sa odstráni daný čas po tom, čo ju pipeline naposledy zapísala.
   - **Celá entita vyprší**, **K pevnému dátumu**: každá entita pipeliny skončí k jednému dátumu a času, pre udalosť, ktorá sa končí v známy deň.
   - **Vypršia len niektoré polia**: vyberte polia, pre autobus `location`, a ako dlho každé zostane, napríklad `5` `minutes` **Po každom zápise**. Entita zostane; odstránia sa len tieto polia.
3. Kliknite na **Skontrolovať**. Každý vzorový záznam sa skontroluje voči dátovému modelu priestoru, tomu, čo cieľový endpoint dovoľuje pipeline zapísať, a životnosti, ktorú dostane; prípadný problém pomenúva záznam, pole a pravidlo.
4. Keď je kontrola zelená, kliknite na **Navrhnúť zmenu**. Portál odmietne návrh, ktorého kontrola chýba alebo je staršia ako koncept, pevný dátum, ktorý už uplynul, a mapovanie, ktoré nastavuje `expiresAt` pre rovnakú entitu alebo pole.
5. Schvaľovateľ návrh zlúči v Schvaľovaniach. Editor načíta životnosť späť z manifestu, aj keď mapovanie upravíte ručne.

Štyri voľby a kedy sa ktorá hodí, sú v [Retention & Expiry](../14-retention-and-expiry.md#4-the-lifetime-step-of-the-pipeline-editor).

## 9. Prevádzka MQTT brokera pre vaše zariadenia

Keď zariadenia posielajú svoje merania cez MQTT, projekt môže prevádzkovať vlastný broker. Stránka **MQTT brokery** na `/projects/{project}/mqttbrokers` ich uvádza v zozname; pipeline potom číta témy brokera ako akýkoľvek iný zdroj.

1. Kliknite na **Nový MQTT broker** a zadajte **Názov**.
2. V časti **Role** pridajte jednu rolu pre každú skupinu zariadení: jej **Servisné účty (zariadenia)**, témy, do ktorých **Smie publikovať do**, napríklad `sensors/+/air`, a témy, ktoré **Smie odoberať**.
3. Vyberte **Čo broker robí**: **Príjem** (pipeline číta každú správu), **Príjem a uchovanie** (broker uchováva aj posledné správy v **Uchované správy**) alebo **Obojsmerný** (zariadenia správy aj prijímajú).
4. Nastavte **Limity**: **Najväčšia správa (bajty)**, **Správ za sekundu na zariadenie** a **Najviac spojení**. Ak majú zariadenia prichádzať len z vašich sietí, zapíšte ich do **Povolené zdrojové siete**, jeden rozsah CIDR na riadok (ďalší pridá **Pridať**), napríklad `203.0.113.0/24`; prázdne pole pripustí akúkoľvek adresu s platným tokenom.
5. Kliknite na **Navrhnúť zmenu**.

Po schválení broker otvorte. Prístup k témam ukazuje, ktorá rola smie kde publikovať a odoberať; panel pripojenia poskytuje **Adresa**, **ID klienta a používateľské meno**, postup na získanie **Heslo** a **Certifikát** a príkaz **Vyskúšať** na odoslanie testovacej správy; časť **Namerané** ukazuje, koľko zariadení je **Práve pripojené**; časť **Spojenia** kreslí, kto s kým komunikuje, a označuje krok, ktorý vyžaduje **Opraviť**.

Keď stránka uvádza **MQTT je pre tento projekt vypnuté**, administrátor organizácie ho zapne v časti **Administrácia**, v nastaveniach MQTT daného projektu. Ten istý administrátor môže zvýšiť počet brokerov, ktoré projekt smie mať.

### Pridelenie roly brokera zariadeniam

Broker určuje, čo smie každá rola; servisný účet zariadenia určuje, že zariadenie rolu má. Ak chcete pustiť skupinu senzorov ovzdušia k role `air-sensor` brokera `air`, pridajte servisnému účtu skupiny jedno priradenie a navrhnite zmenu:

```yaml
# spec.roles servisného účtu air-fleet-north (výňatok)
- role: mqtt/air/air-sensor     # mqtt/*/air-sensor: každý broker projektu s touto rolou
  scope:
    project: bratislava         # vždy vlastný projekt účtu
  validity:
    notAfter: "2027-03-31T23:59:59Z"
```

Od schválenia smie každé zariadenie účtu `air-fleet-north` publikovať tam, kam rola `air-sensor` dovoľuje, do konca marca 2027. Keď priradenie odstránite alebo uplynie `notAfter`, zariadenie skončí pri ďalšej publikácii; manifest brokera sa nemení. Broker, ktorý pri role ešte uvádza `serviceAccounts`, zatiaľ funguje ďalej a `jcctl migrate` presunie tieto mená do priradení ako vyššie.

## Súvisiace

- [Organizácie, projekty a kontextové priestory](02-organizations-projects-spaces.md): správa cieľových priestorov.
- [Dátové modely](03-data-models.md): tvorba schém na validáciu v pipeline.
- [Endpointy a zdieľanie](05-endpoints-and-sharing.md): zverejnenie prijatých kontextových údajov.
- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): posudzovanie návrhov zmien pipelín.
- [Uchovávanie a expirácia](../14-retention-and-expiry.md): recepty životnosti pre autobusy, upozornenia, udalosti a jednotlivé polia a kedy zvoliť radšej expiráciu.
