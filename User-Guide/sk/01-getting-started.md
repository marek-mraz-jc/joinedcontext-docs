---
sidebar_position: 2
title: "Začíname"
description: Vaša prvá hodina v Portáli, úloha po úlohe, každá urobená ručne a vyžiadaná od asistenta jednou vetou.
routes:
  - /login
  - /
  - /projects/$project
  - /projects/$project/home
  - /playground
---

# Začíname

Táto stránka je prehliadkou vašej prvej hodiny v Portáli v poradí, v akom prvá hodina zvyčajne prebieha: pozrite sa, čo projekt už obsahuje, prečítajte jeho dáta, priveďte nový kanál, zverejnite ho a dovoľte inému projektu ho čítať. Každý krok pomenúva stránku, tlačidlo a čo máte zadať, presne slovami, ktoré obrazovka používa. Každá úloha je ukázaná dvakrát, pretože Portál ponúka oboje: ručne vyplnením formulára a požiadaním asistenta jednou vetou, ktorý vyplní rovnaký formulár a nechá vám ho na kontrolu. Anglická verzia je [Getting Started](../01-getting-started.md).

Nič v tejto príručke sa nestane aktívnym, keď stlačíte Uložiť. Každý zápis sa navrhuje ako zmena, ktorú niekto schváli, a preto posledné tlačidlo každého formulára hovorí **Navrhnúť zmenu**, a nie „Vytvoriť“. Časť 6 je miesto, kde sa zmena stane skutočnou.

## 1. Prihláste sa a zorientujte sa

1. Otvorte Portál. Prihlasovacia stránka patrí vašej organizácii; zadajte používateľské meno a heslo, ktoré ste dostali. Keď sa prihlásite, Portál sa otvorí v projekte.
2. Lišta navrchu uvádza názov projektu, na ktorý sa pozeráte. Ak patríte do viacerých projektov, použite ju na prepnutie: všetko pod ňou, každá stránka a každý zoznam, patrí projektu, ktorý je tam uvedený.
3. Ľavá navigácia predstavuje celý Portál: **Kontextové priestory**, **Endpointy**, **Zdroje údajov**, **Pipeliny**, **Dashboardy**, **Aplikácie**, **Schvaľovania**, **Prístup**, **Prehliadať dáta**, **Dátové modely**, **Kópie**, **Otvorené dáta** a **Aktivita**.
4. Asistent sedí v rohu za tlačidlom **Otvoriť asistenta**. Dokáže čítať stránky, ktoré môžete čítať vy, a vypĺňať formuláre, ktoré môžete vypĺňať vy, a môže navrhnúť zmenu rovnako ako vy; nemôže ju však schváliť.

Ak stránka hovorí, že niečo nesmiete vidieť, hovorí to vaša rola, nie je to chyba. Stránka **Prístup** ukazuje, čo vám vaše roly dovoľujú robiť.

Prihlásenie sa začína tlačidlom **Prihlásiť sa**: pošle vás na prihlásenie vašej organizácie a späť na stránku, ktorú ste žiadali. Stránka **Domov** vás privíta tým, čo je dôležité pre vašu rolu: kontrolným zoznamom **Začíname** v novom projekte a v časti **Ďalej pre vás** zmenami, ktoré čakajú na vaše schválenie, zlyhávajúcimi pipelinami, návrhmi, ktoré ste zanechali, a dashboardmi, ktoré môžete čítať. Starý odkaz na `/playground` otvorí vašu domovskú stránku.

## 2. Pozrite sa, čo projekt už obsahuje

Začnite s tým, čo tam už je. Nič v tejto časti nič nemení.

1. Otvorte **Kontextové priestory**. Kontextový priestor je pomenovaná zbierka kontextových dát; každá entita žije presne v jednom. Demonštračný projekt `helsinki` má jeden, tiež nazvaný `helsinki`.
2. V jeho riadku zvoľte **Pozrieť obsah**. Stránka uvádza typy entít, ktoré dátový model priestoru definuje, spolu s **Entity**, počtom každej z nich a ich vzorkou. Pod tým riadok o zobrazení priestoru cez jeho endpointy uvádza vstupy doň a **Politiky** uvádzajú, čo jednotlivé vstupy prepúšťajú.
3. Ak počet hovorí *nie je možné čítať anonymne*, priestor nemá verejný vstup. To je normálne a nie je to chyba; ďalšia časť ho namiesto toho prečíta s vašou vlastnou reláciou.

**Opýtaním sa asistenta:** otvorte asistenta a napíšte *čo obsahuje tento projekt?* Otvorí rovnaké stránky a odpovie z nich.

## 3. Prečítajte dáta s vlastnou reláciou

1. Otvorte **Prehliadať dáta**. Vyberte **Kontextový priestor**, potom **Čítať cez endpoint** a následne typ entity.
2. Tabuľka zobrazuje entity tak, ako ich tento endpoint poskytuje. Politika endpointu rozhoduje o tom, čo vidíte, takže dvaja ľudia môžu otvoriť rovnakú stránku a vidieť rôzne stĺpce. To je zámer, nie chyba.
3. Zvoľte riadok na otvorenie jednej entity a exportovať túto stránku, čím si stránku stiahnete ako súbor.

**Opýtaním sa asistenta:** *ukáž mi stanice bicyklov, ktoré práve nemajú žiadne bicykle*. Asistent číta cez endpoint, ktorý môžete čítať vy, a ukáže vám riadky.

## 4. Priveďte nový kanál

Dve časti v tomto poradí: zdroj údajov hovorí, odkiaľ sa má čítať, a pipeline hovorí, čo sa má urobiť s tým, čo príde. Sú oddelené, pretože jeden zdroj bežne číta viacero pipelín.

### Zdroj údajov

1. Otvorte **Zdroje údajov** a zvoľte **Nový zdroj údajov**.
2. Vyberte **Typ**: *HTTP endpoint*, *MQTT broker*, *WebSocket stream* alebo *GTFS-realtime feed*. Zvyšok formulára sa prispôsobí typu, ktorý ste vybrali.
3. Vyplňte **Názov** (malé písmená, číslice a spojovníky: toto je názov, ktorý budú pipeliny používať), **Popis** vlastnými slovami a pripojenie: pre HTTP endpoint je to **URL**, **Metóda** a **Časový limit**.
4. Ak kanál vyžaduje prihlasovací údaj, formulár žiada **Názov tajomstva** a **Kľúč v tajomstve**, nikdy nie samotný prihlasovací údaj. Prihlasovacie údaje zostávajú v úložisku tajomstiev; formulár prijíma iba odkaz naň. Ak názov, ktorý potrebujete, ešte neexistuje, požiadajte oň svojho administrátora skôr, ako budete pokračovať.
5. Zvoľte **Skontrolovať**, aby platforma vyskúšala pripojenie, a potom **Navrhnúť zmenu**.

### Pipeline

1. Otvorte **Pipeliny** a začnite novú. Pipeline číta jeden zdroj, transformuje to, čo príde, a zapisuje cez endpoint.
2. **Zdroj** predstavuje jeden vstup a iba jeden: **Zdroj údajov** tohto projektu alebo **Zdrojový endpoint** čítaný dopytom. Nie oboje.
3. **Beh** je *auto*, *resident* alebo *scheduled*. *Resident* beží nepretržite v spúšťači projektu; *scheduled* beží ako naplánovaná úloha a medzi behmi stojí, pričom vtedy sa vyžaduje **Rozvrh**, päť polí cronu ako napríklad `10 0 * * *`; *auto* umožní platforme vybrať podľa hodnoty **Perióda**, ktorú zadáte, čo je trvanie ako `15s` alebo `1h`.
4. Štúdio vykreslí pipeline ako pás krokov a umožní vám upravovať každý krok. Využite jeho testovací beh: ukáže vám, čím sa jedna správa stane, a zvýrazní krok, ktorý zlyhal.
5. **Navrhnúť zmenu**.

**Opýtaním sa asistenta:** *načítaj kanál kvality ovzdušia mesta z tejto URL do nového priestoru každých pätnásť minút*. Asistent pripraví návrh zdroja údajov, pipeliny aj priestoru spoločne a nechá ich vyplnené, aby ste si ich prečítali. Oznámenie nad formulárom uvádza, že ho vyplnil asistent; pred navrhnutím ho skontrolujte, pretože zmena odchádza pod vaším menom.

Alebo začnite z pripraveného nastavenia: **Zdroje údajov** ich ukazujú v časti **Pripravené nastavenia**. Tlačidlo **Nastaviť** sa opýta iba na to, čo daný kanál potrebuje, a zapíše zdroj, jeho pipeline aj plán spoločne.

## 5. Zverejnite ho

Endpoint je miesto, kde je priestor publikovaný: kto ho smie volať, v akých reprezentáciách a pod akou adresou.

1. Otvorte **Endpointy** a zvoľte **Nový endpoint**.
2. Vyplňte **Názov** a **Popis** a vyberte **Kontextový priestor**, ktorý publikuje.
3. **Slug** je adresa a **Vygenerovať slug** ho vytvorí za vás. Nikdy sa nemení, ani keď sa endpoint premenuje, takže odkaz, ktorý rozdáte, funguje ďalej.
4. **Publikum** je jedno z troch: *Vybrané projekty: len projekty, ktoré zaškrtnete*, *Organizácia: každý projekt organizácie* alebo *Verejné: ktokoľvek s adresou*. Výber *Vybrané projekty* pridá **Povolené projekty**, kde ich zaškrtnete.
5. **Reprezentácie** určujú, ako sa tie isté dáta poskytujú: *NGSI-LD API*, *CSV*, *OGC API Features*, *SensorThings API*, *OData* a *MCP pre AI asistentov*. CSV je jediný súbor, ktorý endpoint ponúka; mapy a programy čítajú API. Zaškrtnite tie, ktoré chcete; každé zaškrtnutie sa stane odkazom v riadku endpointu.
6. V časti **Ktoré triedy a atribúty zobrazuje** zaškrtnite triedy a atribúty, ktoré tento endpoint sprístupňuje. Čo nezaškrtnete, to sa neposkytuje. **Skryť atribúty** odoberie jednotlivé atribúty z toho, čo by sa inak zobrazovalo.
7. **Zobraziť manifesty, ktoré to navrhuje** sa oplatí raz otvoriť: je to presne to, čo sa zapíše, skôr než to zapíšete.
8. **Navrhnúť zmenu**.

Zverejnenie endpointu pre verejnosť je väčší krok ako ostatné a schválenie v nasledujúcej časti bude vyžadovať viac.

## 6. Získajte schválenie zmeny a sledujte, ako sa prejaví

1. Otvorte **Schvaľovania**. Každá zmena projektu tu čaká, kým ju schvaľovateľ zlúči. Každá ukazuje svojho **Autor**, svoju **Úroveň rizika** a pole po poli, čo by zmenila.
2. Schvaľovateľ ju otvorí a zvolí **Schváliť** alebo **Zamietnuť**. Nemôžete schváliť svoj vlastný návrh a sprístupnenie endpointu alebo aplikácie verejnosti vyžaduje rolu vydavateľa; samotný správca (steward) to urobiť nemôže. Zmena v červenej úrovni rizika žiada opätovné prepísanie názvu prostriedku, kým sa vykoná.
3. Po schválení stránka oznámi, že sa zmena nasadzuje, a potom, že je uplatnená. Otvorte riadok endpointu a jeho odkazy odpovedajú.
4. **Aktivita** je následne históriou tohto všetkého: čo sa zmenilo, kto to navrhol a kto to schválil.

## 7. Dovoľte inému projektu dáta čítať

Dva projekty nikdy nezapisujú jeden do druhého. To, čo prechádza medzi nimi, je publikovaný endpoint.

1. Ako projekt, ktorý vlastní dáta, otvorte endpoint a nastavte jeho **Publikum** na *Vybrané projekty*, potom zaškrtnite projekt, s ktorým zdieľate. Navrhnite zmenu a nechajte ju schváliť.
2. Ako projekt, s ktorým sa zdieľa, otvorte **Endpointy** a nájdite časť **Zdieľané s týmto projektom**: endpointy, ktoré iné projekty organizácie otvorili tomuto projektu. Zvoľte **Použiť v tomto projekte** a priestor sa tu odkáže pod aliasom.
3. Tento odkaz sa navrhne ako zmena ako každý iný zápis. Po jeho schválení môže tento projekt čítať dáta druhého projektu, stále cez vlastný endpoint druhého projektu a stále podľa politiky druhého projektu. Vlastník ho zruší zmenou publika späť a nič z vášho projektu netreba prerábať.

**Opýtaním sa asistenta:** *zdieľaj stanice bicyklov s projektom mobility*. Asistent pripraví návrh publikácie a povie vám, čo a komu by otvoril.

## 8. Skôr než zmeníte čokoľvek skutočné

Tri návyky, ktoré ušetria celé popoludnie.

- **Pracovať na kópii**. Stránka **Kópie** predstavuje projekt bokom: zmeňte niekoľko zdrojov spoločne, vyskúšajte ich a prineste ich všetky späť ako jednu zmenu. Nič v kópii nie je živé, kým to neurobíte.
- Prečítajte si návrh, nie formulár. Každý dialóg vám môže ukázať manifesty, ktoré sa chystá zapísať. Zmena, ktorú ste si prečítali, je zmena, ktorú viete vysvetliť človeku, ktorý ju schvaľuje.
- Nechajte asistenta pripraviť návrh a sami ho skontrolujte. Vypĺňa rovnaké formuláre podľa rovnakých pravidiel a nemôže schvaľovať. To, čo navrhne, odchádza pod vaším menom.

## Súvisiace

- [02-organizations-projects-spaces](02-organizations-projects-spaces.md): čo je projekt a kontextový priestor predtým, ako ho vytvoríte.
- [04-pipelines](04-pipelines.md): štúdio pipelín v plnom rozsahu vrátane testovacieho behu.
- [05-endpoints-and-sharing](05-endpoints-and-sharing.md): publiká, reprezentácie a zdieľanie podrobne.
- [15-build-your-data](15-build-your-data.md): jeden kanál postavený druh po druhu na dev s predvolenými hodnotami, ktoré každý krok dopĺňa.
- [07-users-roles-approvals](07-users-roles-approvals.md): kto môže navrhovať, kto môže schvaľovať a prečo to nikdy nie je tá istá osoba.
- [08-working-with-ai-agents](08-working-with-ai-agents.md): čo môže asistent robiť vo vašom mene.
