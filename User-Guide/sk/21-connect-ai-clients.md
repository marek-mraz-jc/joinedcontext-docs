---
sidebar_position: 23
title: Pripojenie Claude Code, claude.ai, ChatGPT a VS Code
description: Vytvorenie AI konektora na stránke Moje AI konektory, jeho pridanie do Claude Code, claude.ai, ChatGPT alebo VS Code, čo dovoľuje každá predvoľba, ako zmena čaká na schválenie, čo odchádza k dodávateľovi AI a čo znamená každé odmietnutie.
routes:
  - /ai-connectors
---

# Pripojenie Claude Code, claude.ai, ChatGPT a VS Code

AI konektor je vaša vlastná adresa, `https://portal.{domain}/c/{id}`, ktorú AI klient volá, aby pracoval v platforme vlastnými nástrojmi Portálu: vypisoval a čítal objekty, dopytoval údaje, pripravoval zmeny a spúšťal pipeliny. Vytvoríte ho na stránke **Moje AI konektory** na `/ai-connectors` vo vašom vlastnom menu a vyberiete, na čo siaha. Nikdy nesiaha na viac, než smiete vy sami: Portál pri každom volaní znova číta vaše práva. Každý klient vás prihlási cez prihlasovaciu stránku platformy; stránka neukazuje žiadny token a nikto klientovi nedáva heslo. Anglická verzia je [Connect Claude Code, claude.ai, ChatGPT and VS Code](../21-connect-ai-clients.md).

## 1. Vytvorenie konektora

1. Otvorte **Moje AI konektory** a kliknite na **Nový AI konektor**. Zadajte **Názov**, napríklad `doprava-in-claude`: malé písmená, číslice a pomlčky. Pod týmto názvom konektor uvádza váš AI klient.
2. Vyberte jednu alebo viac **Predvoľby** (časť 2). Sivá predvoľba vyžaduje schválenie vašou organizáciou.
3. V časti **Na čo siaha** zaškrtnite celý projekt alebo jednotlivé priestory, Endpointy či pipeliny, každý na čítanie alebo zápis. Zoznam obsahuje len to, čo smiete čítať. Zápis, ktorý vaša organizácia zatiaľ nedovoľuje, sa ukazuje ako „zápis (vyžaduje schválenie)“.
4. Vyberte, dokedy **Platí do**, najviac 30 dní odo dneška, ak vaša organizácia nenastavila iný limit.
5. Voliteľne zaškrtnite **Povolení klienti**. Ak ostanú prázdni, môže ho použiť ktorýkoľvek AI klient, s ktorým sa prihlásite.
6. Kliknite na **Vytvoriť**. Portál znova skontroluje každú zaškrtnutú položku; položku, ktorú nesmiete čítať, odmietne pri poli.

Karta konektora uvádza jeho stav, na čo siaha, predvoľby, klientov, posledné volanie a platnosť. **Nastaviť** ukáže adresu a čo vložiť do každého klienta. Žiadosť nad rámec toho, čo vaša organizácia dovoľuje, môže čakať ako `pending`, kým ju schváli správca; funguje až potom.

Adresa sama osebe nenesie žiadne právo. Volanie cez ňu potrebuje token vydaný vám pre tento jeden konektor, takže uniknutá adresa odpovie inej osobe, akoby neexistovala. Napriek tomu ju nevkladajte do četov ani snímok obrazovky.

## 2. Čo dovoľuje každá predvoľba

| Predvoľba | Čo smie AI klient robiť so zaškrtnutými položkami |
|---|---|
| **Čítanie údajov** | Čítať Endpointy, priestory a modely a dopytovať údaje Endpointov, napríklad na odpovede na otázky o údajoch. |
| **Kontext (modely, priestory, Endpointy)** | Ako Čítanie údajov a navyše pripravovať zmeny dátových modelov, kontextových priestorov, Endpointov a projekcií. |
| **Pipeliny** | Ako Kontext pre pipeliny a zdroje údajov a navyše vzorkovať zdroj, skúšať mapovanie, spustiť pipelinu a čítať jej záznamy. |
| **Prístupy** | Čítať roly, väzby, skupiny a servisné účty a pripravovať ich zmeny. |
| **Publikovanie** | Čítať katalóg a stav CKAN a pripravovať zmeny toho, čo Endpoint publikuje. |
| **Aplikácie** | Čítať aplikácie, dashboardy a vrstvy a ich behy a pripravovať ich zmeny. |
| **Prevádzka** | Čítať aktivitu, zmeny, behy, zdravie a stav synchronizácie a spustiť pipelinu. |
| **Všetko (správca)** | Všetky predvoľby vyššie, v rámci toho, čo dovoľuje vaša organizácia. |

Predvoľba nikdy nepridá právo, ktoré nemáte. Konektor s predvoľbou **Pipeliny** a jednou zaškrtnutou pipelinou siaha len na túto pipelinu, a len tak ďaleko, ako siaha vaša vlastná rola v jej projekte.

## 3. Pridanie do AI klienta

Otvorte **Nastaviť** na karte konektora a kopírujte odtiaľ; adresa nižšie zastupuje tú vašu. Prvé volanie otvorí v prehliadači prihlasovaciu stránku platformy. Prihláste sa svojím účtom Portálu; klient si prihlásenie ponechá len pre tento konektor.

### 3.1 Claude Code

Skopírujte riadok pod **Claude Code** a spustite ho v termináli:

```bash
claude mcp add --transport http doprava-in-claude https://portal.example.org/c/{id}
```

Potom v Claude Code spustite `/mcp`, vyberte `doprava-in-claude` a zvoľte overenie. Prehliadač otvorí prihlasovaciu stránku a vráti sa do Claude Code na port vášho počítača.

### 3.2 claude.ai a Claude Desktop

Claude Desktop používa konektory vášho účtu claude.ai, takže jedno nastavenie slúži obom.

1. Na claude.ai otvorte Settings, potom Connectors, a zvoľte Add custom connector.
2. Vložte adresu, zvoľte Add a potom Connect.
3. Prihláste sa na prihlasovacej stránke platformy; prehliadač sa vráti na claude.ai.

Polia OAuth Client ID a Client Secret nechajte prázdne: platforma pozná claude.ai podľa jeho zverejneného identifikátora klienta.

### 3.3 ChatGPT

1. V ChatGPT otvorte Settings, potom Apps & Connectors, potom Advanced settings, a zapnite Developer mode (musí ho ponúkať váš plán).
2. Zvoľte Create, vložte adresu a ako overenie vyberte OAuth.
3. Ak ChatGPT žiada OAuth Client ID, zadajte `mcp-mobile` a tajomstvo nechajte prázdne.
4. Keď sa otvorí prihlasovacia stránka platformy, prihláste sa.

### 3.4 VS Code

Skopírujte záznam pod **VS Code (.vscode/mcp.json)** do súboru `.vscode/mcp.json` vo vašom pracovnom priestore:

```json
{
  "servers": {
    "doprava-in-claude": {
      "type": "http",
      "url": "https://portal.example.org/c/{id}"
    }
  }
}
```

Spustite server zo súboru alebo z pohľadu MCP; VS Code otvorí prihlasovaciu stránku a prihlásenie si ponechá.

### 3.5 Viazanie konektora na jedného klienta

**Povolení klienti** menuje klientov, ktorí smú konektor použiť. Pre claude.ai a ChatGPT to Portál vie vynútiť: ich prihlásenie nemôže prijať žiadny program na vašom počítači. Pre Claude Code a VS Code to hovorí, pre koho je konektor určený, a iný program na vašom počítači by mohol uviesť toho istého klienta; formulár takú voľbu označuje „hovorí, pre koho je“.

## 4. Zmeny čakajú na schválenie človekom

AI klient nikdy nemení platformu sám. Zmena ide v dvoch krokoch:

1. Plán: klient pošle zmenu ako plán. Portál spustí každú kontrolu, ktorú by spustila zmena v Portáli, a nič neuloží. Odpoveďou je rozdiel a každé zistenie, napríklad pole, ktoré dátový model odmieta, aby ho klient mohol opraviť. claude.ai, ChatGPT a VS Code ukážu plán ako pohľad s odkazom na **Schvaľovania** projektu.
2. Použitie: keď je zaškrtnutá položka nastavená na zápis, klient smie do 30 minút použiť svoj nezmenený plán. Tým otvorí žiadosť o zmenu; nezlúči ju. Plán, ktorého základ sa medzitým posunul, je odmietnutý a klient plánuje znova.

Žiadosť o zmenu schváli alebo zamietne človek na stránke **Schvaľovania** v Portáli, ako každý iný návrh. Žiadny konektor nemôže schváliť, zrušiť ani rozšíriť konektor. Keď je zápis vypnutý, klient stále môže plánovať a plán použijete v Portáli vy sami.

AI klient nikdy nevidí heslo ani API kľúč. Volanie nástroja s hodnotou, ktorá vyzerá ako heslo alebo kľúč, je odmietnuté s `secret-in-argument`. Keď plán potrebuje prihlasovací údaj, uvedie formulár tajomstva v Portáli, kde hodnotu zadáte sami (pozri [Zadanie tajomstva, ktoré plán potrebuje](08-working-with-ai-agents.md#8-zadanie-tajomstva-ktoré-plán-potrebuje)).

## 5. Čo odchádza k dodávateľovi AI

Každá odpoveď, ktorú platforma dá klientovi, ide k dodávateľovi tohto klienta: k Anthropic pre Claude Code, claude.ai a Claude Desktop, k OpenAI pre ChatGPT a k poskytovateľovi modelu, ktorého ste vybrali vo VS Code. Jeho model číta odpoveď popri vašej výzve a dodávateľ ju uchováva podľa nastavení vášho plánu.

Konektor vynechá každý atribút, ktorý dátový model označuje ako osobný, napríklad e-mail alebo telefónne číslo občana, a uvedie, čo vynechal, bez hodnôt. Také atribúty sa ku klientovi dostanú len tam, kde to vaša organizácia dovoľuje a rozsah konektora ich menuje. Text načítaný z údajov je označený ako nedôveryhodný, aby klient nenasledoval pokyny v ňom ukryté. Posúdenie vašej zodpovednej osoby je [Data Protection Impact Assessment for AI Connectors](../../Operations/04-ai-connectors-dpia.md).

## 6. Sledovanie, zmena a zrušenie

- **Aktivita** uvádza každé volanie cez konektor za posledných 30 dní: kedy, nástroj, jeho cieľ, klienta a verdikt. Nikdy neukazuje token ani hodnoty, ktoré nástroj dostal.
- **Upraviť** mení predvoľby, na čo siaha, platnosť alebo povolených klientov; názov ostáva. Portál výsledok skontroluje tak, ako kontroluje nový konektor.
- **Zrušiť** a potom **Zrušiť teraz** odmietne ďalšie volanie cez konektor. Zrušený konektor sa nedá znova zapnúť; vytvorte nový.

Správca vidí konektory každej osoby v prehľade organizácie a môže ktorýkoľvek zrušiť.

## 7. Keď je volanie odmietnuté

| Čo hlási klient | Prečo | Čo robiť |
|---|---|---|
| `401` s `WWW-Authenticate: Bearer resource_metadata=…` | Klient nemá prihlásenie pre tento konektor, prihlásenie vypršalo alebo bol token vydaný pre iný konektor. | Overte sa znova: `/mcp` v Claude Code, Connect v claude.ai, alebo konektor v ChatGPT odstráňte a pridajte znova. |
| `404`, konektor neexistuje | Adresa je preklepnutá alebo ste sa prihlásili ako iná osoba než vlastník konektora. | Skopírujte adresu znova z **Nastaviť** a prihláste sa vlastným účtom. |
| `403` „this connector is revoked“ alebo „expired“ | Konektor bol zrušený alebo jeho platnosť uplynula. | Pri vypršanom zvoľte **Upraviť** a v **Platí do** vyberte neskorší deň. Zrušený ostane vypnutý: vytvorte nový. |
| `403` „this connector answers only …; the token was obtained by …“ | **Povolení klienti** konektora neobsahujú klienta, ktorého ste použili. | Použite uvedeného klienta alebo **Upraviť** **Povolení klienti** konektora. |
| `403` s nástrojom, druhom alebo cieľom mimo rozsahu | Volanie siaha na nástroj alebo položku, ktorú predvoľby a zaškrtnutia konektora nepokrývajú, alebo to nedovoľuje vaša vlastná rola. | **Upraviť** **Predvoľby** alebo **Na čo siaha** konektora. Ak vašej role chýba právo, požiadajte správcu projektu; pozri [Používatelia, roly, schvaľovania a správa driftu](07-users-roles-approvals.md). |
| `422` `secret-in-argument` | Argument nástroja obsahuje hodnotu, ktorá vyzerá ako heslo alebo kľúč. | Prihlasovací údaj zadajte vo formulári tajomstva v Portáli; nikdy ho nepíšte do četu. |
| `429` s `Retry-After` | Konektor urobil viac než 60 volaní za minútu (120 spolu za všetky vaše konektory) alebo viac než 4 naraz. | Počkajte toľko sekúnd, koľko uvádza `Retry-After`; požiadajte klienta o menej a väčších čítaní. |
| Odpoveď nástroja je príliš veľká (`413`) | Jedna odpoveď by prekročila 1 MiB. | Zúžte čítanie pomocou `limit`, `attrs` alebo jedného názvu. |

## 8. Spoločná MCP adresa Portálu

Okrem vašich vlastných konektorov má Portál jednu MCP adresu pre celú sadu nástrojov, `https://portal.{domain}/api/v1/mcp`, ktorá koná so všetkými vašimi právami. Klient ju pridá s OAuth Client ID `mcp-mobile` (claude.ai, Claude Desktop, ChatGPT) alebo `mcp-local` (Claude Code a iní klienti na vašom počítači, so spätnou adresou `http://localhost:{port}/callback`), bez tajomstva a so scope `openid mcp:portal`, ak ho klient žiada. Konektor je lepšia voľba: siaha len na to, čo zaškrtnete, a môžete ho zrušiť samostatne.

## Súvisiace

- [Spolupráca s autonómnymi AI agentmi](08-working-with-ai-agents.md): asistent, behy agentov a MCP adresy Endpointov
- [Používatelia, roly, schvaľovania a správa driftu](07-users-roles-approvals.md)
- [Data Protection Impact Assessment for AI Connectors](../../Operations/04-ai-connectors-dpia.md)
- [Connectors API](../../API/14-connectors.md)
- [Agents and MCP](../../Architecture/07-agents-and-mcp.md)
