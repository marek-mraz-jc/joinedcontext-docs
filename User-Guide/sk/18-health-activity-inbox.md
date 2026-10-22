---
sidebar_position: 20
title: Zdravie, aktivita a doručené
description: Kde uvidíte, či projekt funguje, čo sa v ňom stalo a čo čaká na vaše rozhodnutie.
routes:
  - /projects/$project/health
  - /projects/$project/activity
  - /projects/$project/inbox
---

# Zdravie, aktivita a doručené

Tri stránky odpovedajú na otázky, ktoré si kladiete každé ráno: či projekt funguje (**Zdravie**), čo sa v ňom stalo (**Aktivita**) a čo čaká na vás (**Doručené**). Sú napísané pre dátových stewardov a schvaľovateľov; prvé dve môže otvoriť každý, kto smie projekt čítať. Anglická verzia je [Health, Activity and Your Inbox](../18-health-activity-inbox.md).

## 1. Funguje všetko: Zdravie

Otvorte projekt a zvoľte **Zdravie**. Stránka uvádza každú kontrolu pipelín projektu, kontextových priestorov, endpointov, modelov a zdrojov údajov, chyby sú na prvom mieste. Portál spúšťa kontroly sám každých niekoľko minút.

1. Zúžte zoznam pomocou **Zobraziť**, napríklad na **Pipeline**, alebo ponechajte **Všetky druhy**.
2. Prečítajte si každý riadok: **Stav**, **Zdroj**, ktorý kontrolovala, a **Čo našla**, napríklad „ešte neuplatnené“ alebo „čaká na schválenie“.
3. Postupujte podľa odporúčania za „Oprava:“. Pomenúva krok, ktorý treba urobiť, napríklad skontrolovať adresu zdroja údajov, keď zdroj neodpovedal.
4. **Posledných 7 dní** ukazuje, či je problém nový alebo sa stále vracia; **Naposledy v poriadku** hovorí, kedy kontrola naposledy prešla, alebo že neprešla nikdy.

Kontrola pokrýva jednu vec: či je prostriedok uplatnený, či jeho behy úspešne prebiehajú, či sú jeho dáta čerstvé, či entity prichádzajú, koľko úložiska využíva, či dáta dodržiavajú pravidlá modelu a či je zdroj dostupný.

Keď stránka hovorí **Zatiaľ nič neskontrolované**, Portál ešte nespustil svoje prvé kontroly: pridajte pipeline, kontextový priestor alebo endpoint, alebo sa vráťte o niekoľko minút. Keď sú všetky kontroly v poriadku, netreba nič opravovať.

## 2. Čo sa stalo: Aktivita

**Aktivita** ukazuje, čo sa v projekte deje, od najnovšieho: uplatnené zmeny, behy pipelín, obslúžené a odmietnuté požiadavky a publikovanie v katalógu.

1. Prečítajte si súhrn v hornej časti, **Čo sa stalo za poslednú hodinu**: **Prijaté správy**, **Uplatnené zmeny**, **Obslúžené požiadavky**, **Preposlania** a **Odmietnutia**.
2. Zúžte prehľad pomocou **Druh**, **Zdroj**, **Závažnosť** a **Kontextový priestor**. Hodnota **Akékoľvek** filter zruší.
3. **Priebežný záznam** priebežne pridáva nové udalosti, ako nastávajú; kým beží, zobrazuje **Sleduje sa**, a keď ho zastavíte, ukazuje **Pozastavené**, takže riadok, ktorý práve čítate, sa neposunie.
4. **Zobraziť staršie** listuje späť v čase. **Technické podrobnosti** na riadku zobrazia celú udalosť, čo pomôže pri nahlasovaní problému.

Udalosť, ktorá sa opakuje, sa zobrazí raz s informáciou, koľkokrát a odkedy nastala. Odmietnutá požiadavka, napríklad **Prístup odmietnutý**, vám povie, ktorého čitateľa vaše politiky nepustili; [Endpoints, zdieľanie údajov a integrácia](05-endpoints-and-sharing.md) vysvetľuje, ako zmeniť, kto smie čítať.

## 3. Čo čaká na vás: Doručené

**Doručené** zhromažďuje cez všetky projekty, ktoré smiete čítať, zmeny, o ktorých môžete rozhodnúť, a komentáre, ktoré vás spomínajú.

1. V časti **Čaká na vaše rozhodnutie** otvorte **Ukázať, čo mení**, aby ste si zmenu prečítali bez opustenia stránky, alebo **Otvoriť zmenu** pre jej celú stránku.
2. Kliknite na **Schváliť**. Zmena v červenej úrovni rizika vás najprv požiada o napísanie názvu prostriedku, pretože niečo sprístupňuje verejnosti alebo odstraňuje.
3. Alebo kliknite na **Zamietnuť**, do **Prečo to zamietate?** napíšte, čo musí autor opraviť, a kliknite na **Zamietnuť zmenu**. Autor si váš dôvod prečíta pri zmene.
4. V časti **Zmienky o vás** otvorte komentár, ktorý o vás niekto napísal v priestore.

Tlačidlá **Schváliť** a **Zamietnuť** fungujú len tam, kde vám vaša rola dovoľuje o zmenách rozhodovať; inde si zmenu môžete prečítať a rozhodnutie prenechať schvaľovateľovi. Keď stránka hlási, že zmeny projektu sa nenačítali, pokúsi sa o to sama znova o 30 sekúnd.

## Súvisiace

- [Používatelia, roly a schvaľovania](07-users-roles-approvals.md): ako sa zmena posudzuje a kto o nej smie rozhodovať.
- [Pipeliny](04-pipelines.md): pozastavenie pipeliny a sledovanie zdravia dátového toku.
- [Retention & Expiry](../14-retention-and-expiry.md): kedy varovanie o úložisku znamená, že staré dáta by mali odísť.
