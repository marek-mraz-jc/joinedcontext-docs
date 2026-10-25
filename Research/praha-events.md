---
sidebar_position: 16
title: "Event sources: Praha"
description: Every candidate event source of Prague (city, boroughs, theatres, cinemas, museums, galleries, libraries, music venues, ticketing) probed on 2026-10-25 with its verdict; the usable ones feed the space praha-akce.
---

# Event sources: Praha

Who publishes Prague's events in a form a pipeline can read, beyond the city's open data catalogue, which
holds no events feed ([Open data sources of Praha](praha-open-data.md), row 113). Task T-5666 (owner
2026-10-25) built this page and the pipelines.

## 1. How the inventory was made

1. **Candidates.** Wikidata (every museum, gallery, theatre building, culture centre, library, cinema, music venue, arena, zoo
   and botanical garden located in Prague with an official website, P856), the boroughs Praha 1 to 22 and the named
   ones Wikidata lists, and 50 sites read by hand: the city, Prague City Tourism, the ticketing sites (GoOut,
   Ticketportal, Ticketmaster), the main theatres, concert halls, clubs and culture houses. One row per host.
2. **Probe.** `seeds/city-events/probe.py` (deployment repository) read each site once on 2026-10-25 with the
   pipelines' User-Agent, one request a second per host, a 15 s timeout and a 1 MB cap: robots.txt first (a
   disallowed home page is `skip: robots.txt`), then The Events Calendar REST (`/wp-json/tribe/events/v1/events`),
   iCalendar (`?ical=1`, a linked `.ics`) and schema.org Event JSON-LD on the home page and on up to four
   event-looking pages it links.
3. **Verdict.** `usable` needs one upcoming event (start today or later) with a name, a start and a place, read
   from a stable list URL (a page holding one event's JSON-LD is `skip: event pages only`). Every other row keeps
   one reason: `down` (no answer, with the error class), `http only`, `robots.txt`, `no machine-readable events`
   (HTML only; a site that prints its calendar for people needs its own template), `none upcoming` (the feed
   parses but lists nothing ahead), `no place`.
4. **Terms.** Only public pages, no login. No candidate states an open licence for its programme, so the
   pipelines keep the facts of an event (name, time, place, link back) and never copy descriptions or images,
   as the Slovak stores do (seeds/bbsk-events/README.md).

## 2. Result

263 candidates, 15 usable on 2026-10-25. The owner's target of 100 usable sources per city
(T-5666) is not reached: the count per reason below is the target this city's open web gives today.

| verdict | sources |
|---|---|
| skip: no machine-readable events | 173 |
| skip: down | 38 |
| skip: http only | 16 |
| usable | 15 |
| skip: robots.txt | 12 |
| skip: none upcoming | 3 |
| skip: event pages only | 3 |
| skip: no place | 3 |

Integrated: each usable row is a row of deployment `seeds/bbsk-events/sources-cz.csv`; `generate.py` writes one
DataSource, Pipeline and mapping per row into the project `praha`, space `praha-akce` (public Endpoint
`praha-akce`, also as iCal), run every 6 hours. The events tail stamps scope `/CZ/PHA/hlavni_mesto_praha` and country `CZ`, and
keeps a point only inside Czechia; an event whose venue no table places takes the city office (Mariánské
náměstí 2, OpenStreetMap node 296677370) labelled `office`.

## 3. Every candidate

Copy: `Research/data/praha-events-2026-10-25.tsv` (the probe's columns, with the URL it read).

| # | candidate | type | site | kind | upcoming | verdict | reason |
|---|---|---|---|---|---|---|---|
| 1 | Schwarzenberský palác v Praze | muzeum | `ngprague.cz` | - | - | skip | no machine-readable events |
| 2 | Musoleum | muzeum | `musoleum.cz` | - | - | skip | none upcoming |
| 3 | Dům fotografie | muzeum | `ghmp.cz` | - | - | skip | no machine-readable events |
| 4 | Galerie U Betlémské kaple | muzeum | `galerieubetlemskekaple.cz` | - | - | skip | no machine-readable events |
| 5 | Lobkowiczké sbírky | muzeum | `lobkowicz.com` | - | - | skip | down: HTTPError |
| 6 | Galerie Millennium | muzeum | `gallerymillennium.cz` | - | - | skip | no machine-readable events |
| 7 | Obrazárna Pražského hradu | muzeum | `hrad.cz` | - | - | skip | no machine-readable events |
| 8 | Museum Kampa | muzeum | `museumkampa.cz` | - | - | skip | no machine-readable events |
| 9 | Signal Space | muzeum | `signalspace.com` | - | - | skip | no machine-readable events |
| 10 | Galerie Rudolfinum | muzeum | `galerierudolfinum.cz` | - | - | skip | http only |
| 11 | Stavovské divadlo | budova divadla | `estatestheatre.cz` | - | - | skip | no machine-readable events |
| 12 | Státní opera Praha | music venue | `narodni-divadlo.cz` | - | - | skip | no machine-readable events |
| 13 | Q85727011 | knihovna | `mecd.gob.es` | - | - | skip | down: URLError |
| 14 | Centrum volného času Praha 9 | kulturní centrum | `centrumvolnehocasupraha.cz` | - | - | skip | down: URLError |
| 15 | Rodinné a pohybové centrum Pražačka | kulturní centrum | `rpcprazacka.cz` | - | - | skip | none upcoming |
| 16 | MeetFactory | kulturní centrum | `meetfactory.cz` | - | - | skip | http only |
| 17 | Cinema City Galaxie | kino | `cinemacity.cz` | - | - | skip | no machine-readable events |
| 18 | Řeporyjská stezka | galerie umění | `reporyjskastezka.webnode.cz` | - | - | skip | no machine-readable events |
| 19 | Místní veřejná knihovna Horní Počernice | veřejná knihovna | `knihovnapocernice.cz` | - | - | skip | no machine-readable events |
| 20 | Rodinné centrum Mateřídouška | kulturní centrum | `toulcuvdvur.cz` | - | - | skip | no machine-readable events |
| 21 | Roxy | music venue | `roxy.cz` | - | - | skip | no machine-readable events |
| 22 | Letnice | kulturní centrum | `klubletnice.cz` | - | - | skip | no machine-readable events |
| 23 | Baby Club Kenny | kulturní centrum | `evakiedronova.cz` | - | - | skip | down: HTTPError |
| 24 | České vysoké učení technické v Praze | univerzita | `cvut.cz` | - | - | skip | down: URLError |
| 25 | Zličínská knihovna | veřejná knihovna | `zlicinska-knihovna.cz` | - | - | skip | no machine-readable events |
| 26 | Akademie múzických umění v Praze | univerzita | `amu.cz` | - | - | skip | no machine-readable events |
| 27 | Klub Decima | kulturní centrum | `praha.ymca.cz` | - | - | skip | down: URLError |
| 28 | Reduta Jazz Club | music venue | `redutajazzclub.cz` | - | - | skip | http only |
| 29 | Klub Junior | kulturní centrum | `klubjunior.cz` | - | - | skip | http only |
| 30 | Rudolfinum | music venue | `rudolfinum.cz` | - | - | skip | no machine-readable events |
| 31 | Dům dětí a mládeže hlavního města Prahy | kulturní centrum | `ddmpraha.cz` | - | - | skip | no machine-readable events |
| 32 | Dům dětí a mládeže Praha 3 - Ulita | kulturní centrum | `ulita.cz` | - | - | skip | no machine-readable events |
| 33 | Dům dětí a mládeže Praha 6 | kulturní centrum | `ddmp6.cz` | - | - | skip | no machine-readable events |
| 34 | Dům dětí a mládeže Praha 6 - Suchdol | kulturní centrum | `ddmsuchdol.cz` | - | - | skip | no machine-readable events |
| 35 | Dům dětí a mládeže Praha 7 | kulturní centrum | `ddmpraha7.cz` | - | - | skip | no machine-readable events |
| 36 | Fortuna Arena | stadion | `slavia.cz` | - | - | skip | down: HTTPError |
| 37 | Poštovní muzeum Praha | muzeum | `postovnimuzeum.cz` | - | - | skip | no machine-readable events |
| 38 | Vltavská filharmonie | music venue | `vltavskafilharmonie.cz` | - | - | skip | no machine-readable events |
| 39 | Obecní dům | music venue | `obecnidum.cz` | - | - | skip | no machine-readable events |
| 40 | Dům dětí a mládeže Praha 2 | kulturní centrum | `ddm-ph2.cz` | - | - | skip | no machine-readable events |
| 41 | Hobby centrum 4 | kulturní centrum | `hobbycentrum4.cz` | - | - | skip | no machine-readable events |
| 42 | Dům dětí a mládeže Praha 9 | kulturní centrum | `ddmpraha9.cz` | - | - | skip | no machine-readable events |
| 43 | Dům dětí a mládeže Jižní Město | kulturní centrum | `ddmjm.cz` | - | - | skip | no machine-readable events |
| 44 | Dům dětí a mládeže Modřany | kulturní centrum | `ddmm.cz` | - | - | skip | no machine-readable events |
| 45 | Dům dětí a mládeže Praha 5 | kulturní centrum | `ddmpraha5.cz` | - | - | skip | no machine-readable events |
| 46 | Dům dětí a mládeže Praha 10 - Dům UM | kulturní centrum | `dumum.cz` | - | - | skip | no machine-readable events |
| 47 | Palác Lucerna | kulturní centrum | `lucerna.cz` | - | - | skip | no machine-readable events |
| 48 | Mucha Foundation Art Museum | muzeum umění | `mucha.eu` | - | - | skip | no machine-readable events |
| 49 | Ymkárium | kulturní centrum | `ymca.cz` | - | - | skip | down: HTTPError |
| 50 | GoJa Music Hall | music venue | `goja.cz` | - | - | skip | no machine-readable events |
| 51 | Centrum volného času Botič | kulturní centrum | `praha2.cz` | - | - | skip | down: HTTPError |
| 52 | Knihovna s infocentrem MČ Praha-Kolovraty | knihovna | `kolovraty.cz` | - | - | skip | down: HTTPError |
| 53 | Knihovna Národního muzea | knihovna | `nm.cz` | - | - | skip | down: HTTPError |
| 54 | knihovna Carlose Fuentese | knihovna | `praga.cervantes.es` | - | - | skip | robots.txt |
| 55 | Knihovna Filozofického ústavu | knihovna | `knihovna.flu.cas.cz` | - | - | skip | no machine-readable events |
| 56 | Knihovna Antonína Švehly | knihovna | `kas.uzei.cz` | - | - | skip | down: URLError |
| 57 | Místní knihovna Radotín | knihovna | `knihovna-radotin.cz` | - | - | skip | no machine-readable events |
| 58 | Národní lékařská knihovna | knihovna | `nlk.cz` | - | - | skip | no machine-readable events |
| 59 | Národní technická knihovna | knihovna | `techlib.cz` | - | - | skip | down: URLError |
| 60 | Státní knihovna ČSR | knihovna | `openlibrary.org` | - | - | skip | no machine-readable events |
| 61 | Místní veřejná knihovna Šeberov | knihovna | `seberov.cz` | - | - | skip | no machine-readable events |
| 62 | Americké centrum | knihovna | `americkecentrum.cz` | - | - | skip | no machine-readable events |
| 63 | Místní lidová knihovna Praha 11 | knihovna | `mistniknihovnachodov.cz` | - | - | skip | no machine-readable events |
| 64 | Místní knihovna Uhříněves | knihovna | `praha22.cz` | - | - | skip | no machine-readable events |
| 65 | Divadelní a filmové oddělení Městské knihovny v Praze | knihovna | `mlp.cz` | - | - | skip | down: HTTPError |
| 66 | Křesťanská knihovna Praha | knihovna | `christianlibrary.cz` | - | - | skip | http only |
| 67 | Hórnikova knihovna | knihovna | `luzice.com` | - | - | skip | no machine-readable events |
| 68 | Hórnikova knihovna | knihovna | `katalog.hornikovaknihovna.cz` | - | - | skip | robots.txt |
| 69 | Obecní knihovna Ďáblice | knihovna | `dablice.knihovna.cz` | - | - | skip | no machine-readable events |
| 70 | Knihovna Orientálního ústavu AV ČR | knihovna | `orient.cas.cz` | - | - | skip | down: HTTPError |
| 71 | Veřejná knihovna Dubeč | knihovna | `praha-dubec.cz` | - | - | skip | robots.txt |
| 72 | Knihovna Městské části Praha 18 | knihovna | `knihovna.letnany.cz` | - | - | skip | robots.txt |
| 73 | Kino Vzlet | kino | `vzlet.cz` | - | - | skip | no machine-readable events |
| 74 | Modřanský biograf | kino | `modranskybiograf.cz` | - | - | skip | down: HTTPError |
| 75 | Kino Kavalírka | kino | `kinokavalirka.cz` | - | - | skip | no machine-readable events |
| 76 | Kino Petrohradská | kino | `kinopetrohradska.cz` | - | - | skip | down: URLError |
| 77 | Kino Evald | kino | `evald.cz` | - | - | skip | down: HTTPError |
| 78 | Divadlo Perštýn | kino | `divadloperstyn.cz` | - | - | skip | down: URLError |
| 79 | Kino Pilotů | kino | `kinopilotu.cz` | - | - | skip | no machine-readable events |
| 80 | Kino Ponrepo | kino | `nfa.cz` | - | - | skip | no machine-readable events |
| 81 | Divadlo Bez zábradlí | kino | `bezzabradli.cz` | - | - | skip | down: HTTPError |
| 82 | Kino MAT | kino | `mat.cz` | - | - | skip | no machine-readable events |
| 83 | Edison Filmhub | kino | `edisonfilmhub.cz` | - | - | skip | none upcoming |
| 84 | Kino Přítomnost | kino | `kinopritomnost.cz` | jsonld | 16 | usable | 16 upcoming with name, start and place |
| 85 | Zoo Praha | zoologická zahrada | `zoopraha.cz` | - | - | skip | no machine-readable events |
| 86 | Kino Atlas | kino | `kinoatlas.cz` | - | - | skip | no machine-readable events |
| 87 | Kino Aero | kino | `kinoaero.cz` | jsonld | 27 | usable | 27 upcoming with name, start and place |
| 88 | Kino Oko | kino | `biooko.net` | jsonld | 34 | usable | 34 upcoming with name, start and place |
| 89 | Kino Světozor | kino | `kinosvetozor.cz` | jsonld | 38 | usable | 38 upcoming with name, start and place |
| 90 | Divadlo Palace | kino | `divadlopalace.cz` | - | - | skip | no machine-readable events |
| 91 | Kino Lucerna | kino | `kinolucerna.cz` | jsonld | 51 | usable | 51 upcoming with name, start and place |
| 92 | zookoutek Kamýk | zoologická zahrada | `lhmp.cz` | - | - | skip | no machine-readable events |
| 93 | Zoopark Milíčov | zoologická zahrada | `facebook.com` | - | - | skip | robots.txt |
| 94 | Muzeum českého granátu Praha | muzeum | `mcgp.cz` | - | - | skip | no machine-readable events |
| 95 | Divadlo Na zábradlí | budova divadla | `nazabradli.cz` | - | - | skip | no machine-readable events |
| 96 | Muzeum iluzivního umění Praha | muzeum | `iamprague.eu` | - | - | skip | no machine-readable events |
| 97 | Malostranská beseda | budova divadla | `malostranska-beseda.cz` | - | - | skip | no machine-readable events |
| 98 | Divadlo na Vinohradech | budova divadla | `divadlonavinohradech.com` | - | - | skip | no machine-readable events |
| 99 | Gong | budova divadla | `divadlogong.cz` | - | - | skip | down: URLError |
| 100 | Kerava Museum Services | muzeum | `kerava.fi` | - | - | skip | no machine-readable events |
| 101 | Hudební divadlo Karlín | budova divadla | `hdk.cz` | - | - | skip | no machine-readable events |
| 102 | Kulturní Centrum Zahrada | budova divadla | `kczahrada.cz` | - | - | skip | no machine-readable events |
| 103 | Divadlo Broadway | budova divadla | `divadlo-broadway.cz` | - | - | skip | no machine-readable events |
| 104 | Divadlo U Hasičů | budova divadla | `divadlouhasicu.net` | - | - | skip | no machine-readable events |
| 105 | Divadlo v Korunní | budova divadla | `divadlokorunni.cz` | - | - | skip | down: HTTPError |
| 106 | Divadlo Karla Hackera | budova divadla | `divadlokh.cz` | - | - | skip | no machine-readable events |
| 107 | Divadlo Za Plotem | budova divadla | `dzp.webnode.cz` | - | - | skip | no machine-readable events |
| 108 | Divadlo Horní Počernice | budova divadla | `divadlopocernice.cz` | - | - | skip | no machine-readable events |
| 109 | Divadlo Metro | budova divadla | `divadlometro.cz` | - | - | skip | no machine-readable events |
| 110 | Klub Mlejn | budova divadla | `mlejn.cz` | - | - | skip | http only |
| 111 | Pidivadlo | budova divadla | `pidivadlo.cz` | - | - | skip | down: HTTPError |
| 112 | Divadlo Na Rejdišti a Koncertní sál Pražské konzervatoře | budova divadla | `prgcons.cz` | tribe-rest | 50 | usable | 50 upcoming with name, start and place |
| 113 | Žižkovské divadlo Járy Cimrmana | budova divadla | `zdjc.cz` | - | - | skip | no machine-readable events |
| 114 | Divadlo U22 | budova divadla | `divadlou22.cz` | - | - | skip | http only |
| 115 | Divadlo Minor | budova divadla | `minor.cz` | - | - | skip | no machine-readable events |
| 116 | ARCHA+ | budova divadla | `divadloarcha.cz` | - | - | skip | no machine-readable events |
| 117 | Muzeum granátů Magic Garnet | muzeum | `magicgarnet.cz` | - | - | skip | no machine-readable events |
| 118 | Divadlo v Celetné | budova divadla | `divadlovceletne.cz` | - | - | skip | no machine-readable events |
| 119 | Divadlo Orfeus | budova divadla | `orfeusdivadlo.cz` | - | - | skip | no machine-readable events |
| 120 | Muzeum Lega | muzeum | `muzeumlega.cz` | - | - | skip | no machine-readable events |
| 121 | Divadlo ABC | budova divadla | `mestskadivadlaprazska.cz` | - | - | skip | no machine-readable events |
| 122 | Divadlo Kámen | budova divadla | `divadlokamen.cz` | jsonld | 2 | usable | 2 upcoming with name, start and place |
| 123 | Divadlo Ponec | budova divadla | `divadloponec.cz` | - | - | skip | no machine-readable events |
| 124 | Divadlo DISK | budova divadla | `divadlodisk.cz` | - | - | skip | no machine-readable events |
| 125 | Divadlo Ungelt | budova divadla | `divadloungelt.cz` | - | - | skip | no machine-readable events |
| 126 | Muzeum a vzdělávací centrum československých legií | muzeum | `csol.cz` | - | - | skip | no machine-readable events |
| 127 | Divadlo v Dlouhé | budova divadla | `divadlovdlouhe.cz` | - | - | skip | no machine-readable events |
| 128 | Muzeum slivovice R. Jelínek | muzeum | `slivovitzmuseum.com` | - | - | skip | no machine-readable events |
| 129 | Muzeum slivovice R. Jelínek | muzeum | `muzeumslivovice.cz` | - | - | skip | no machine-readable events |
| 130 | Divadlo v Řeznické | budova divadla | `reznicka.cz` | - | - | skip | no machine-readable events |
| 131 | Divadlo Jana Kašky | budova divadla | `divadlozbraslav.cz` | - | - | skip | http only |
| 132 | Bytové divadlo Košická | budova divadla | `oldstars.cz` | - | - | skip | no machine-readable events |
| 133 | Alfred ve dvoře | budova divadla | `alfredvedvore.cz` | - | - | skip | no machine-readable events |
| 134 | Salesiánské divadlo | budova divadla | `strediskokobylisy.cz` | - | - | skip | no machine-readable events |
| 135 | Divadlo Kampa | budova divadla | `divadlokampa.cz` | - | - | skip | no machine-readable events |
| 136 | A Studio Rubín | budova divadla | `astudiorubin.cz` | - | - | skip | no machine-readable events |
| 137 | Husův sbor v Praze-Vršovicích | budova divadla | `husuvsbor.cz` | - | - | skip | no machine-readable events |
| 138 | Muzeum Československých Legií | muzeum | `muzeumlegii.cz` | - | - | skip | no machine-readable events |
| 139 | Design Museum Prague | muzeum | `designmuseumprague.com` | - | - | skip | no machine-readable events |
| 140 | Návštěvnické centrum Staropramen | muzeum | `centrumstaropramen.cz` | - | - | skip | no machine-readable events |
| 141 | Strašnické divadlo | budova divadla | `strasnickedivadlo.eu` | - | - | skip | down: URLError |
| 142 | RockOpera Praha | budova divadla | `rockopera.cz` | - | - | skip | no machine-readable events |
| 143 | Studio DVA divadlo | budova divadla | `studiodva.cz` | jsonld | 503 | usable | 499 upcoming with name, start and place |
| 144 | Divadlo Radka Brzobohatého | budova divadla | `divadlorb.cz` | - | - | skip | no machine-readable events |
| 145 | Dům národnostních menšin | muzeum | `dnm-praha.eu` | - | - | skip | no machine-readable events |
| 146 | Muzeum smyslů | muzeum | `muzeumsmyslu.cz` | - | - | skip | no machine-readable events |
| 147 | Kabaretní divadélko Labuť | budova divadla | `cernalabut.cz` | - | - | skip | no machine-readable events |
| 148 | Divadlo D21 | budova divadla | `divadlod21.cz` | - | - | skip | no machine-readable events |
| 149 | Speculum Alchemiae | muzeum | `alchemiae.cz` | - | - | skip | http only |
| 150 | Staroměstská radnice | muzeum | `prague.eu` | - | - | skip | no machine-readable events |
| 151 | Muzeum Antonína Dvořáka | muzeum | `antonindvorak2004.cz` | - | - | skip | http only |
| 152 | KGB Museum | muzeum | `kgbmuseum.com` | - | - | skip | no machine-readable events |
| 153 | Židovské muzeum v Praze | muzeum | `jewishmuseum.cz` | - | - | skip | no machine-readable events |
| 154 | Muzeum Karla Zemana | muzeum | `muzeumkarlazemana.cz` | - | - | skip | no machine-readable events |
| 155 | Galerie Václava Špály | muzeum | `galerievaclavaspaly.cz` | - | - | skip | no machine-readable events |
| 156 | Pedagogické muzeum J. A. Komenského v Praze | muzeum | `npmk.cz` | - | - | skip | no machine-readable events |
| 157 | Techtle Mechtle | music venue | `techtle-mechtle.cz` | - | - | skip | down: URLError |
| 158 | Prašná brána | muzeum | `muzeumprahy.cz` | - | - | skip | down: HTTPError |
| 159 | Kulturní dům Kyje | kulturní centrum | `kdkyje.cz` | - | - | skip | robots.txt |
| 160 | Vagon | music venue | `vagon.cz` | - | - | skip | http only |
| 161 | Galerie Nová síň | muzeum | `novasin.org` | - | - | skip | no machine-readable events |
| 162 | Hrdličkovo muzeum člověka | muzeum | `muzeumcloveka.cz` | - | - | skip | no machine-readable events |
| 163 | Balbínova poetická hospůdka | music venue | `balbinka.cz` | - | - | skip | http only |
| 164 | Jazz Club Ungelt | music venue | `jazzungelt.cz` | - | - | skip | down: URLError |
| 165 | Museum středověkých mučicích nástrojů | muzeum | `museumtortury.cz` | - | - | skip | no machine-readable events |
| 166 | Centrum současného umění DOX | muzeum | `dox.cz` | - | - | skip | no machine-readable events |
| 167 | Radost FX | music venue | `radostfx.cz` | - | - | skip | event pages only |
| 168 | Museum of Medieval Torture Instruments | muzeum | `museumtorture.com` | - | - | skip | no machine-readable events |
| 169 | Pivovarské muzeum U Fleků | muzeum | `ufleku.cz` | - | - | skip | no machine-readable events |
| 170 | Sex Machines Museum | muzeum | `sexmachinesmuseum.com` | - | - | skip | no machine-readable events |
| 171 | Clock Gallery Praha | muzeum | `clockgallery.cz` | - | - | skip | no machine-readable events |
| 172 | AghaRTA Jazz Centrum | music venue | `agharta.cz` | - | - | skip | no machine-readable events |
| 173 | Muzeum her Cibien's Corner | muzeum | `muzeumher.cz` | - | - | skip | no machine-readable events |
| 174 | Jazz Republic | music venue | `jazzrepublic.cz` | - | - | skip | no machine-readable events |
| 175 | Muzeum PRE | muzeum | `pre.cz` | - | - | skip | no machine-readable events |
| 176 | Muzeum Policie České republiky | muzeum | `muzeumpolicie.cz` | - | - | skip | down: HTTPError |
| 177 | Knihovna Národního archivu | knihovna | `knihovna.nacr.cz` | - | - | skip | no machine-readable events |
| 178 | Muzeum Franze Kafky | muzeum | `kafkamuseum.cz` | - | - | skip | no machine-readable events |
| 179 | Muzeum komunismu | muzeum | `museumofcommunism.com` | - | - | skip | no machine-readable events |
| 180 | Síň slávy českého hokeje | muzeum | `cslh.cz` | - | - | skip | down: HTTPError |
| 181 | Galerie Cesty ke světlu | muzeum | `cestykesvetlu.cz` | - | - | skip | http only |
| 182 | Kulturní centrum Novodvorská Praha | kulturní centrum | `kcnovodvorska.cz` | - | - | skip | down: HTTPError |
| 183 | Muzeum městské hromadné dopravy v Praze | muzeum | `dpp.cz` | - | - | skip | no machine-readable events |
| 184 | Sportovní hala Fortuna | aréna | `tipsportarena-praha.cz` | - | - | skip | http only |
| 185 | O₂ universum | aréna | `o2universum.cz` | - | - | skip | event pages only |
| 186 | O₂ arena | aréna | `o2arena.cz` | - | - | skip | event pages only |
| 187 | Galerie Pictura | galerie umění | `pictura.cz` | - | - | skip | no machine-readable events |
| 188 | Galerie Fasáda | galerie umění | `galeriefasada.cz` | - | - | skip | no machine-readable events |
| 189 | KodlContemporary | galerie umění | `kodlcontemporary.com` | - | - | skip | no machine-readable events |
| 190 | Galerie ocelových figurín | galerie umění | `galerieocelovychfigurin.cz` | - | - | skip | no machine-readable events |
| 191 | Lumia Gallery | galerie umění | `lumia.gallery` | - | - | skip | no machine-readable events |
| 192 | Kunsthalle Praha | galerie umění | `kunsthallepraha.org` | - | - | skip | no machine-readable events |
| 193 | Galerie KMI | galerie umění | `galeriekmoch.cz` | - | - | skip | no machine-readable events |
| 194 | Galerie Via Art | galerie umění | `galerieviaart.cz` | - | - | skip | http only |
| 195 | Galerie Villa Pellé | galerie umění | `villapelle.cz` | - | - | skip | no machine-readable events |
| 196 | Trafo Gallery | galerie umění | `trafogallery.cz` | - | - | skip | no machine-readable events |
| 197 | Galerie Jaroslava Fragnera | galerie umění | `fragnerka.cvut.cz` | - | - | skip | down: URLError |
| 198 | Galerie La Femme | galerie umění | `glf.cz` | - | - | skip | no machine-readable events |
| 199 | Ars Diva Galerie | galerie umění | `arsdiva.cz` | - | - | skip | no machine-readable events |
| 200 | Galerie Jiří Švestka | galerie umění | `jirisvestkagallery.com` | - | - | skip | no machine-readable events |
| 201 | Hauch Gallery | galerie umění | `hauchgallery.com` | - | - | skip | down: URLError |
| 202 | 400 ASA Gallery | galerie umění | `400asa.org` | - | - | skip | no machine-readable events |
| 203 | Artinbox galerie | galerie umění | `artinbox.cz` | - | - | skip | no machine-readable events |
| 204 | Galerie Kroupa | galerie umění | `galeriekroupa.cz` | - | - | skip | no machine-readable events |
| 205 | Arcimboldo Auctions | galerie umění | `arcimboldo.cz` | - | - | skip | no machine-readable events |
| 206 | Galerie Pecka | galerie umění | `galeriepecka.cz` | - | - | skip | http only |
| 207 | Pragovka Gallery | galerie umění | `x.pragovka.com` | - | - | skip | down: URLError |
| 208 | Ruský dům v Praze | kulturní centrum | `rsvk.cz` | jsonld | 1 | usable | 1 upcoming with name, start and place |
| 209 | Kulturní centrum Klubovna | kulturní centrum | `klubovna.povalec.cz` | - | - | skip | no machine-readable events |
| 210 | Kulturní centrum Knoflík | kulturní centrum | `centrumknoflik.cz` | - | - | skip | no machine-readable events |
| 211 | Kulturní centrum Úl | kulturní centrum | `uldablice.cz` | - | - | skip | no machine-readable events |
| 212 | Kulturní centrum Velký mlýn | kulturní centrum | `velkymlyn.cz` | tribe-rest | 34 | usable | 30 upcoming with name, start and place |
| 213 | Kafkárna | kulturní centrum | `umprum.cz` | - | - | skip | no machine-readable events |
| 214 | PRAGOS centrum | kulturní centrum | `pragos.cz` | - | - | skip | no machine-readable events |
| 215 | Kulturní centrum 12 | kulturní centrum | `kc12.cz` | - | - | skip | robots.txt |
| 216 | Werichova vila | music venue | `werichovavila.cz` | - | - | skip | no machine-readable events |
| 217 | JammClub | music venue | `jammclub.cz` | jsonld | 16 | usable | 16 upcoming with name, start and place |
| 218 | Lucerna Music Bar | music venue | `musicbar.cz` | - | - | skip | no machine-readable events |
| 219 | Praha 1 | city district | `praha1.cz` | ical | 53 | usable | 1 upcoming with name, start and place |
| 220 | Praha 3 | city district | `praha3.cz` | - | - | skip | down: HTTPError |
| 221 | Praha 11 | city district | `praha11.cz` | - | - | skip | no machine-readable events |
| 222 | Praha 20 | city district | `pocernice.cz` | ical | 39 | usable | 39 upcoming with name, start and place |
| 223 | Praha 10 | city district | `praha10.cz` | - | - | skip | no machine-readable events |
| 224 | Praha 9 | city district | `praha9.cz` | - | - | skip | no machine-readable events |
| 225 | Praha-Troja | city district | `mctroja.cz` | - | - | skip | no machine-readable events |
| 226 | Praha 7 | city district | `praha7.cz` | - | - | skip | no machine-readable events |
| 227 | Praha 8 | city district | `praha8.cz` | - | - | skip | no machine-readable events |
| 228 | Praha 18 | city district | `praha18.cz` | - | - | skip | robots.txt |
| 229 | Praha 17 | city district | `repy.cz` | - | - | skip | no machine-readable events |
| 230 | Praha 16 | city district | `praha16.eu` | - | - | skip | no machine-readable events |
| 231 | Praha 19 | city district | `praha19.cz` | ical | 30 | skip | no place |
| 232 | Praha-Kunratice | city district | `praha-kunratice.cz` | - | - | skip | no machine-readable events |
| 233 | Praha 6 | city district | `praha6.cz` | - | - | skip | no machine-readable events |
| 234 | Praha-Suchdol | city district | `praha-suchdol.cz` | tribe-rest | 5 | skip | no place |
| 235 | Praha 15 | city district | `praha15.cz` | - | - | skip | robots.txt |
| 236 | Praha-Zbraslav | city district | `mc-zbraslav.cz` | - | - | skip | robots.txt |
| 237 | Praha-Slivenec | city district | `praha-slivenec.cz` | - | - | skip | robots.txt |
| 238 | Praha 4 | city district | `praha4.cz` | - | - | skip | down: HTTPError |
| 239 | Praha 12 | city district | `praha12.cz` | - | - | skip | robots.txt |
| 240 | Praha 5 | city district | `praha5.cz` | ical | 6 | skip | no place |
| 241 | Hlavní město Praha | city | `praha.eu` | - | - | skip | down: URLError |
| 242 | Praha 13 | city district | `praha13.cz` | - | - | skip | no machine-readable events |
| 243 | Praha 14 | city district | `praha14.cz` | - | - | skip | no machine-readable events |
| 244 | Praha 21 | city district | `praha21.cz` | - | - | skip | no machine-readable events |
| 245 | GoOut Praha | ticketing | `goout.net` | - | - | skip | no machine-readable events |
| 246 | Ticketportal | ticketing | `ticketportal.cz` | - | - | skip | no machine-readable events |
| 247 | Ticketmaster CZ | ticketing | `ticketmaster.cz` | - | - | skip | down: HTTPError |
| 248 | Kudy z nudy | tourism organisation | `kudyznudy.cz` | - | - | skip | no machine-readable events |
| 249 | Česká filharmonie | concert hall | `ceskafilharmonie.cz` | - | - | skip | no machine-readable events |
| 250 | DOX | gallery | `dox.org` | - | - | skip | no machine-readable events |
| 251 | Divadlo Archa | theatre | `archa-plus.cz` | - | - | skip | no machine-readable events |
| 252 | Jatka78 | theatre | `jatka78.cz` | - | - | skip | no machine-readable events |
| 253 | La Fabrika | theatre | `lafabrika.cz` | jsonld | 60 | usable | 60 upcoming with name, start and place |
| 254 | Palác Akropolis | music venue | `palacakropolis.cz` | - | - | skip | no machine-readable events |
| 255 | Forum Karlín | music venue | `forumkarlin.cz` | - | - | skip | no machine-readable events |
| 256 | Pražské jaro | festival | `festival.cz` | - | - | skip | no machine-readable events |
| 257 | Prague Pride | festival | `praguepride.cz` | tribe-rest | 44 | usable | 42 upcoming with name, start and place |
| 258 | Signal festival | festival | `signalfestival.com` | - | - | skip | no machine-readable events |
| 259 | Studio Hrdinů | theatre | `studiohrdinu.cz` | - | - | skip | no machine-readable events |
| 260 | Švandovo divadlo | theatre | `svandovodivadlo.cz` | - | - | skip | no machine-readable events |
| 261 | Divadlo Hybernia | theatre | `hybernia.eu` | - | - | skip | no machine-readable events |
| 262 | KD Ládví | culture centre | `kdladvi.cz` | - | - | skip | down: HTTPError |
| 263 | Centrum Kaštan | culture centre | `kastan.cz` | - | - | skip | no machine-readable events |

## Related

- [Open data sources of Praha](praha-open-data.md), [Open data sources of Bratislava](bratislava-open-data.md),
  [Open data sources of Helsinki (HRI)](helsinki-open-data.md)
- deployment `seeds/bbsk-events/README.md` (the generator and the events tail), `seeds/city-events/` (the probes)
- conformance `tests/mcp/events_readback.py` (the read-back through the MCP connector)
- Task T-5666
