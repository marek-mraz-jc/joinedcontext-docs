---
sidebar_position: 13
title: Správa vašej organizácie a projektov
description: Kde sa nachádzajú nastavenia, členovia, role a projekty organizácie a kde sídlia nastavenia jedného projektu.
routes:
  - /organization
  - /organization/$tab
  - /organization/$tab/$
  - /projects/$project/settings
  - /projects/$project/settings/$tab
  - /projects/$project/settings/$tab/$
  - /endpoints
  - /projects/$project/access
---

# Správa vašej organizácie a projektov

Prístup spravujete na dvoch miestach. **Administrácia** na `/organization` obsahuje to, čo je rovnaké v každom projekte. **Nastavenia projektu** obsahujú to, čo patrí jednému projektu. Každá zmena, ktorú vykonáte na ktorejkoľvek z týchto stránok, je navrhovanou zmenou, ktorú schvaľovateľ zlúči, rovnako ako všade inde v Portáli ([07](07-users-roles-approvals.md)). Anglická verzia je [Managing Your Organization and Projects](../12-managing-organization-and-projects.md).

## 1. Administrácia

Administrácia je určená správcom organizácie; ktokoľvek iný uvidí hlásenie „Táto stránka je pre správcov organizácie“ a musí požiadať jedného z nich. Jej bočná navigácia má štyri skupiny:

| Skupina | Časti | Čo sa tam robí |
|---|---|---|
| **Ľudia a prístup** | **Ľudia**, **Členovia**, **Role**, **Skupiny**, **Servisné účty**, **Agenti** | Pozrite sa, kto patrí do organizácie a s akou rolou; pridajte osobu alebo skupinu, prípadne ich odstráňte; prečítajte si role slovom a navrhnite novú; spravujte skupiny, ktoré priraďujete naraz; servisné účty organizácie a ich kľúče; agentov konajúcich za ľudí. |
| **Projekty a aplikácie** | **Projekty**, **Všetky aplikácie**, **Všetky endpointy**, **MCP servery organizácie**, **Modely organizácie**, **Šablóny**, **Profily agentov** | Otvorte, importujte, exportujte alebo zmažte projekt a zapnite preň MQTT; pozrite si každú aplikáciu a Endpoint organizácie v jednom zozname; spravujte MCP servery, modely, šablóny a profily agentov, ktoré zdieľa každý projekt. |
| **Platforma** | **Brokery**, **Prostredia**, **Dátový priestor**, **Zdravie** | Brokery, do ktorých projekty zapisujú, inštalácie, do ktorých tento projekt povyšuje zmeny, členstvo organizácie v dátovom priestore ([Dátové priestory, rozsahy a prostredia](19-data-spaces-scopes-environments.md)), a kontroly zdravia všetkých projektov naraz. |
| **Nastavenia** | **Nastavenia**, **Nastavenie** | Doména organizácie, jazyky a kontakty, kto smie otvoriť projekt, kvóta projektov; prvé nastavenie po inštalácii. |

Starý odkaz na `/endpoints` otvorí **Všetky endpointy**. Pri mazaní projektu musíte napísať jeho názov a dialóg vypíše všetko, čo zmazanie odstráni.

## 2. Nastavenia projektu

Otvorte projekt a vyberte **Nastavenia**, poslednú položku v jeho ponuke. Pole **Nájsť nastavenie** vyhľadáva vo všetkých záložkách, napríklad výraz `quota` alebo `delete`.

| Záložka | Čo sa tam robí |
|---|---|
| **Všeobecné** | Názov projektu, popis, kto projekty číta a vydavateľ v katalógu. |
| **Členovia** | Kto je priradený v tomto projekte alebo v jednom z jeho priestorov. Pridelenie organizačnej roly alebo niektorej z rolí tohto projektu osobe či skupine. |
| **Role** | Vlastné role tohto projektu, napríklad taká, ktorá navrhuje pipeliny, ale nie endpointy. Môžete zapísať len takú rolu, ktorej práva sami vlastníte. |
| **Servisné účty** | Servisné účty a kľúče projektu. |
| **Váš prístup** | Čo môžete v tomto projekte čítať, navrhovať, schvaľovať a mazať a ktoré priradenie vám to umožňuje. |
| **Prehľad prístupu** | Pre správcov organizácie: kto smie čo v tomto projekte robiť. |
| **Odstrániť alebo odovzdať** | Možnosť **Odovzdať projekt** inému správcovi, alebo **Zmazať projekt**: zmena v červenej úrovni rizika, ktorú schvaľuje správca, so zoznamom všetkého, čo sa s ním odstráni. |

Starý odkaz na `/projects/{project}/access` otvorí **Nastavenia → Členovia**.

## 3. Ktorá rola je ktorá

| Chcete, aby niekto… | Použite | Kde |
|---|---|---|
| mal rovnaké práva v každom projekte | organizačnú rolu naviazanú na úrovni organizácie | Administrácia → Členovia |
| mal organizačnú rolu len v jednom projekte | organizačnú rolu naviazanú na úrovni projektu | Nastavenia projektu → Členovia |
| mal práva, ktoré definuje váš projekt | projektovú rolu | Nastavenia projektu → Role, potom Členovia |
| používal jednu aplikáciu určitým spôsobom | aplikačnú rolu | na vlastnej stránke aplikácie |

Keycloak vie len to, kto daná osoba je a ako sa prihlasuje. Rolu ani členstvo tam nikdy neupravujete.

## Súvisiace

- [07-users-roles-approvals.md](07-users-roles-approvals.md): pridelenie roly, schvaľovania a drift, krok za krokom.
- [Architecture/09 §14](../../Architecture/09-portal.md#14-organization-and-project-management): špecifikácia oboch stránok.
- [Architecture/12 §2a](../../Architecture/12-identity-and-access.md#2a-roles-as-code): role, väzby a skupiny ako manifesty.
