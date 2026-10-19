---
sidebar_position: 4
title: Vytvorenie pipeliny
description: Vyberte zdroj a cieľ, napíšte mapovanie a opravujte ho, kým nie sú platné všetky záznamy.
---

# Vytvorenie pipeliny

Pipelina číta zdroj údajov a zapisuje jeho záznamy do kontextového priestoru, overené podľa modelu priestoru. Pracovná plocha ukazuje každý krok na skutočných záznamoch, takže chybné pole uvidíte skôr, než čokoľvek spustíte. Je určená správcom údajov a integrátorom.

## 1. Vyberte zdroj

Otvorte **Pipeliny** a kliknite na **Nová pipelina**. V časti **Zdroj** vyberte zdroj údajov. **Vzorka** ukazuje záznamy tak, ako ich pipelina prečíta.

![Pracovná plocha pipeliny s vybraným zdrojom a jeho vzorkou záznamov](../../img/sk/pipeline-1-source-and-sample.png)

## 2. Vyberte cieľ

Zadajte pipeline **Názov** a vyberte **Cieľ**: priestor, do ktorého záznamy pôjdu, a model, podľa ktorého sa overia. **Mapovanie** potom ukáže, čo daný model prijíma.

![Vybraný cieľ a krok mapovania so zoznamom toho, čo model prijíma](../../img/sk/pipeline-2-target-and-mapping.png)

## 3. Prečítajte chyby pri každom zázname

Napíšte mapovanie. **Namapovaný výstup** ukazuje každý záznam tak, ako by sa zapísal, a pole, ktoré model odmietne, je označené pri danom zázname spolu s pravidlom, ktoré porušuje. **Validácia** spočíta záznamy, ktoré model porušujú, a kým nejaký taký je, tlačidlo na návrh zostáva neaktívne.

![Mapovanie s poľom nesprávneho typu, chyba pri každom zázname](../../img/sk/pipeline-3-errors-at-each-record.png)

## 4. Opravujte, kým nie sú platné všetky záznamy

Opravte mapovanie. Keď **Validácia** hlási, že všetky záznamy sú platné, navrhnite pipelinu. Spustí sa po schválení druhou osobou.

![Všetky záznamy platné podľa modelu](../../img/sk/pipeline-4-all-valid.png)

## Related

- [Pipelines and ingestion](../../04-pipelines.md) — v angličtine: plány, predvoľby a stav prúdu.
- [Pripojenie zdroja údajov](03-connect-a-data-source.md) — krok pred týmto.
- [Sprístupnenie údajov cez endpoint](05-share-through-an-endpoint.md) — nechajte ostatných čítať, čo pipelina zapísala.
