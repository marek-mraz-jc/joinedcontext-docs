---
sidebar_position: 18
title: "Event sources: Helsinki"
description: Every publisher of Helsinki's Linked Events register and every Helsinki venue site outside it, probed on 2026-10-25 with its verdict; the register's publishers feed the space helsinki.
---

# Event sources: Helsinki

Who publishes Helsinki's events. The City of Helsinki's Linked Events register (`api.hel.fi/linkedevents`, CC BY 4.0)
carries the events of the city's own services and of the venues and partners that publish into it; the
`linked-events` pipeline reads all of it every half hour into the space `helsinki` (T-5257). Task T-5666 (owner
2026-10-25) counts each publisher as one source and probes the venues outside the register.

## 1. How the inventory was made

1. **Candidates.** every publisher of an upcoming event in Linked Events (`seeds/city-events/linkedevents.py` pages the whole
   upcoming register, 100 a page, one a second, and names each publisher from `/organization/`), and Wikidata's
   museums, galleries, theatre buildings, culture centres, libraries, cinemas, music venues, arenas, zoos and
   botanical gardens located in Helsinki with an official website (P856). A publisher is `usable` with one
   upcoming event placed inside Helsinki and its 1 km margin, the pipeline's own bound.
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

172 candidates, 57 usable on 2026-10-25. The owner's target of 100 usable sources per city
(T-5666) is not reached: the count per reason below is the target this city's open web gives today.

| verdict | sources |
|---|---|
| skip: no machine-readable events | 92 |
| usable | 57 |
| skip: down | 13 |
| skip: no place in Helsinki | 4 |
| skip: robots.txt | 4 |
| skip: no place | 1 |
| skip: http only | 1 |

Integrated: every usable publisher is already read by `linked-events`; since T-5666 each event carries its
publisher's organization id as `dataProvider`, so dev counts events per source (`q=dataProvider=="ahjo:u48040050"`).
No venue outside the register publishes a feed a template reads (one, Bar Loose, lists its own shows with no
place).

## 3. Every candidate

Copy: `Research/data/helsinki-events-2026-10-25.tsv` (the probe's columns, with the URL it read).

| # | candidate | type | site | kind | upcoming | verdict | reason |
|---|---|---|---|---|---|---|---|
| 1 | Varhaiskasvatuksen ja esiopetuksen palvelukokonaisuus | Linked Events publisher ahjo:u42030010 | `api.hel.fi` | linked-events | 2601 | usable | 2601 upcoming with name, start and place in Helsinki |
| 2 | Kirjastopalvelukokonaisuus | Linked Events publisher ahjo:u48040050 | `api.hel.fi` | linked-events | 1724 | usable | 1718 upcoming with name, start and place in Helsinki |
| 3 | Elinvoima | Linked Events publisher espoo:sito | `api.hel.fi` | linked-events | 1549 | usable | 588 upcoming with name, start and place in Helsinki |
| 4 | Sosiaali-, terveys- ja pelastustoimiala | Linked Events publisher ahjo:u321200 | `api.hel.fi` | linked-events | 1083 | usable | 1083 upcoming with name, start and place in Helsinki |
| 5 | Viestintäosasto | Linked Events publisher ahjo:u021800 | `api.hel.fi` | linked-events | 949 | usable | 949 upcoming with name, start and place in Helsinki |
| 6 | Osallisuus ja neuvonta | Linked Events publisher ahjo:u02180020 | `api.hel.fi` | linked-events | 666 | usable | 666 upcoming with name, start and place in Helsinki |
| 7 | Muu | Linked Events publisher others | `api.hel.fi` | linked-events | 611 | usable | 605 upcoming with name, start and place in Helsinki |
| 8 | Vantaan kaupunki | Linked Events publisher vantaa:kaupunki | `api.hel.fi` | linked-events | 510 | usable | 354 upcoming with name, start and place in Helsinki |
| 9 | Lippupiste Oy | Linked Events publisher ytj:1789232-4 | `api.hel.fi` | linked-events | 438 | usable | 438 upcoming with name, start and place in Helsinki |
| 10 | Kasvatuksen ja koulutuksen toimiala | Linked Events publisher ahjo:u420300 | `api.hel.fi` | linked-events | 425 | usable | 410 upcoming with name, start and place in Helsinki |
| 11 | Kulttuuripalvelukokonaisuus | Linked Events publisher ahjo:u48040010 | `api.hel.fi` | linked-events | 423 | usable | 413 upcoming with name, start and place in Helsinki |
| 12 | Kontulan seniorikeskus | Linked Events publisher ahjo:u321200303030 | `api.hel.fi` | linked-events | 415 | usable | 415 upcoming with name, start and place in Helsinki |
| 13 | Myllypuron seniorikeskus | Linked Events publisher ahjo:u321200303040 | `api.hel.fi` | linked-events | 235 | usable | 235 upcoming with name, start and place in Helsinki |
| 14 | Matkailuyksikkö | Linked Events publisher ytj:0586977-6 | `api.hel.fi` | linked-events | 218 | usable | 183 upcoming with name, start and place in Helsinki |
| 15 | Aluekirjastopalvelut | Linked Events publisher ahjo:u4804005010 | `api.hel.fi` | linked-events | 212 | usable | 212 upcoming with name, start and place in Helsinki |
| 16 | Roihuvuoren seniorikeskus | Linked Events publisher ahjo:u3212003035 | `api.hel.fi` | linked-events | 187 | usable | 187 upcoming with name, start and place in Helsinki |
| 17 | Leikkipuisto Lampi | Linked Events publisher helsinki:u42030010201024 | `api.hel.fi` | linked-events | 142 | usable | 142 upcoming with name, start and place in Helsinki |
| 18 | Kustaankartanon seniorikeskus | Linked Events publisher ahjo:u321200303050 | `api.hel.fi` | linked-events | 117 | usable | 117 upcoming with name, start and place in Helsinki |
| 19 | Kulttuurin ja vapaa-ajan toimiala | Linked Events publisher ahjo:u480400 | `api.hel.fi` | linked-events | 89 | usable | 88 upcoming with name, start and place in Helsinki |
| 20 | Kaupunginorkesteri | Linked Events publisher ahjo:u4804001030 | `api.hel.fi` | linked-events | 77 | usable | 77 upcoming with name, start and place in Helsinki |
| 21 | Vuosaaren kirjasto | Linked Events publisher ahjo:u480400501036 | `api.hel.fi` | linked-events | 72 | usable | 72 upcoming with name, start and place in Helsinki |
| 22 | Koskelan seniorikeskus | Linked Events publisher ahjo:u321200303025 | `api.hel.fi` | linked-events | 68 | usable | 68 upcoming with name, start and place in Helsinki |
| 23 | Kinaporin seniorikeskus | Linked Events publisher ahjo:u321200303010 | `api.hel.fi` | linked-events | 61 | usable | 61 upcoming with name, start and place in Helsinki |
| 24 | Riistavuoren seniorikeskus | Linked Events publisher ahjo:u321200303045 | `api.hel.fi` | linked-events | 60 | usable | 60 upcoming with name, start and place in Helsinki |
| 25 | Töölön seniorikeskus | Linked Events publisher ahjo:u321200303015 | `api.hel.fi` | linked-events | 58 | usable | 58 upcoming with name, start and place in Helsinki |
| 26 | Kauniainen | Linked Events publisher kauniainen:kaupunki | `api.hel.fi` | linked-events | 57 | skip | no place in Helsinki |
| 27 | Konsernihallinto | Linked Events publisher espoo:koha | `api.hel.fi` | linked-events | 57 | usable | 19 upcoming with name, start and place in Helsinki |
| 28 | Leikkipuisto Trumpetti | Linked Events publisher helsinki:u42030010201057 | `api.hel.fi` | linked-events | 54 | usable | 54 upcoming with name, start and place in Helsinki |
| 29 | Leikkipuisto Torpparinmäki | Linked Events publisher helsinki:u42030010201055 | `api.hel.fi` | linked-events | 45 | usable | 45 upcoming with name, start and place in Helsinki |
| 30 | Seniorikeskukset | Linked Events publisher ahjo:u3212003030 | `api.hel.fi` | linked-events | 44 | usable | 44 upcoming with name, start and place in Helsinki |
| 31 | Kasvu ja oppiminen | Linked Events publisher espoo:KOTO | `api.hel.fi` | linked-events | 41 | usable | 32 upcoming with name, start and place in Helsinki |
| 32 | Kaupunginmuseo | Linked Events publisher ahjo:u4804001020 | `api.hel.fi` | linked-events | 40 | usable | 40 upcoming with name, start and place in Helsinki |
| 33 | Leikkipuisto Sanna | Linked Events publisher helsinki:u42030010201047 | `api.hel.fi` | linked-events | 40 | usable | 40 upcoming with name, start and place in Helsinki |
| 34 | Nuorisopalvelukokonaisuus | Linked Events publisher ahjo:u48040030 | `api.hel.fi` | linked-events | 35 | usable | 35 upcoming with name, start and place in Helsinki |
| 35 | Leikkipuisto Nurkka | Linked Events publisher helsinki:u42030010201038 | `api.hel.fi` | linked-events | 30 | usable | 30 upcoming with name, start and place in Helsinki |
| 36 | Elinkeino-osasto | Linked Events publisher ahjo:u021200 | `api.hel.fi` | linked-events | 25 | usable | 25 upcoming with name, start and place in Helsinki |
| 37 | Työllisyyspalvelut | Linked Events publisher ahjo:u021200130 | `api.hel.fi` | linked-events | 23 | usable | 23 upcoming with name, start and place in Helsinki |
| 38 | Nykytaiteen museo Kiasma | Linked Events publisher fng:kiasma | `api.hel.fi` | linked-events | 15 | usable | 15 upcoming with name, start and place in Helsinki |
| 39 | Itäinen nuorisotyö | Linked Events publisher ahjo:u4804003010 | `api.hel.fi` | linked-events | 15 | usable | 15 upcoming with name, start and place in Helsinki |
| 40 | Pohjoinen nuorisotyö | Linked Events publisher ahjo:u4804003030 | `api.hel.fi` | linked-events | 14 | usable | 14 upcoming with name, start and place in Helsinki |
| 41 | Leikkipuisto Piika | Linked Events publisher helsinki:u42030010201039 | `api.hel.fi` | linked-events | 11 | usable | 11 upcoming with name, start and place in Helsinki |
| 42 | Syystien seniorikeskus | Linked Events publisher ahjo:u321200303055 | `api.hel.fi` | linked-events | 10 | usable | 10 upcoming with name, start and place in Helsinki |
| 43 | Viestintäpalvelut ja osallisuus | Linked Events publisher ahjo:u3212004080 | `api.hel.fi` | linked-events | 7 | usable | 7 upcoming with name, start and place in Helsinki |
| 44 | Kaupunkiympäristön toimiala | Linked Events publisher ahjo:u541000 | `api.hel.fi` | linked-events | 7 | usable | 5 upcoming with name, start and place in Helsinki |
| 45 | Harrastukset.hel.fi kumppanit | Linked Events publisher None: | `api.hel.fi` | linked-events | 7 | usable | 7 upcoming with name, start and place in Helsinki |
| 46 | Keskustakirjasto Oodi | Linked Events publisher ahjo:u4804005020 | `api.hel.fi` | linked-events | 5 | usable | 5 upcoming with name, start and place in Helsinki |
| 47 | HAM Helsingin taidemuseo | Linked Events publisher ytj:3272340-6 | `api.hel.fi` | linked-events | 5 | usable | 5 upcoming with name, start and place in Helsinki |
| 48 | Maunulan nuorisotyöyksikkö | Linked Events publisher ahjo:u480400303040 | `api.hel.fi` | linked-events | 5 | usable | 5 upcoming with name, start and place in Helsinki |
| 49 | Ympäristöpalvelut | Linked Events publisher ahjo:u5110530040 | `api.hel.fi` | linked-events | 4 | usable | 4 upcoming with name, start and place in Helsinki |
| 50 | Helsingin tapahtumasäätiö sr | Linked Events publisher ytj:0224232-9 | `api.hel.fi` | linked-events | 3 | usable | 3 upcoming with name, start and place in Helsinki |
| 51 | Liikuntaan aktivointi | Linked Events publisher ahjo:u4804002010 | `api.hel.fi` | linked-events | 3 | usable | 3 upcoming with name, start and place in Helsinki |
| 52 | Liikuntapalvelukokonaisuus | Linked Events publisher ahjo:u48040020 | `api.hel.fi` | linked-events | 2 | usable | 2 upcoming with name, start and place in Helsinki |
| 53 | Sairaala-, kuntoutus- ja hoivapalvelut -palvelukokonaisuus | Linked Events publisher ahjo:u32120030 | `api.hel.fi` | linked-events | 2 | usable | 2 upcoming with name, start and place in Helsinki |
| 54 | Kaupunkiympäristö | Linked Events publisher espoo:tyt | `api.hel.fi` | linked-events | 1 | skip | no place in Helsinki |
| 55 | Läntinen nuorisotyö | Linked Events publisher ahjo:u4804003020 | `api.hel.fi` | linked-events | 1 | usable | 1 upcoming with name, start and place in Helsinki |
| 56 | Munkkiniemen nuorisotyöyksikkö | Linked Events publisher ahjo:u480400302040 | `api.hel.fi` | linked-events | 1 | usable | 1 upcoming with name, start and place in Helsinki |
| 57 | Sotepe-yhteistyökumppanit | Linked Events publisher helsinki:sotepe-yht | `api.hel.fi` | linked-events | 1 | usable | 1 upcoming with name, start and place in Helsinki |
| 58 | Kaupunginkanslia | Linked Events publisher ahjo:u02100 | `api.hel.fi` | linked-events | 1 | usable | 1 upcoming with name, start and place in Helsinki |
| 59 | Rakentamispalveluliikelaitos | Linked Events publisher ahjo:u31000 | `api.hel.fi` | linked-events | 1 | usable | 1 upcoming with name, start and place in Helsinki |
| 60 | Osallisuus ja neuvonta | Linked Events publisher ahjo:u02160010 | `api.hel.fi` | linked-events | 1 | skip | no place in Helsinki |
| 61 | Maahanmuutto- ja työllisyysasiat | Linked Events publisher ahjo:u02120030 | `api.hel.fi` | linked-events | 1 | skip | no place in Helsinki |
| 62 | Kallio Library | knihovna | `helmet.fi` | - | - | skip | down: HTTPError |
| 63 | Rikhardinkatu Library | knihovna | `flickr.com` | - | - | skip | robots.txt |
| 64 | Library of Parliament | knihovna | `eduskunta.fi` | - | - | skip | down: HTTPError |
| 65 | Helsinská centrální knihovna Oodi | knihovna | `oodihelsinki.fi` | - | - | skip | no machine-readable events |
| 66 | Taideteollinen korkeakoulu | akademická instituce | `arts.aalto.fi` | - | - | skip | no machine-readable events |
| 67 | Myllypuro Library | knihovna | `helmet.finna.fi` | - | - | skip | down: HTTPError |
| 68 | Alexander Theatre | music venue | `aleksanterinteatteri.fi` | - | - | skip | no machine-readable events |
| 69 | Kiasma Teatteri | budova divadla | `kiasma.fi` | - | - | skip | robots.txt |
| 70 | Teater Viirus | budova divadla | `viirus.fi` | - | - | skip | no machine-readable events |
| 71 | Q11896699 | budova divadla | `teatteritakomo.fi` | - | - | skip | no machine-readable events |
| 72 | Savoy Theatre | budova divadla | `savoyteatteri.fi` | - | - | skip | no machine-readable events |
| 73 | Lilla Teatern | budova divadla | `hkt.fi` | - | - | skip | no machine-readable events |
| 74 | Svenska Teatern | budova divadla | `svenskateatern.fi` | - | - | skip | no machine-readable events |
| 75 | Drom | budova divadla | `drom.fi` | - | - | skip | no machine-readable events |
| 76 | Teatteri Jurkka | budova divadla | `jurkka.fi` | - | - | skip | no machine-readable events |
| 77 | Suomen Pankin rahamuseo | muzeum | `rahamuseo.fi` | - | - | skip | no machine-readable events |
| 78 | Suomenlinna Museum | muzeum | `museot.fi` | - | - | skip | no machine-readable events |
| 79 | Computer Museum of Kallio | muzeum | `kalliontietokonemuseo.fi` | - | - | skip | no machine-readable events |
| 80 | Q53016271 | muzeum | `metropolia.fi` | - | - | skip | no machine-readable events |
| 81 | Worker’s Museum | muzeum | `arbetarbostadsmuseet.fi` | - | - | skip | no machine-readable events |
| 82 | Worker’s Museum | muzeum | `muzeirabochegobyta.fi` | - | - | skip | down: URLError |
| 83 | Worker’s Museum | muzeum | `tyovaenasuntomuseo.fi` | - | - | skip | no machine-readable events |
| 84 | Worker’s Museum | muzeum | `workerhousingmuseum.fi` | - | - | skip | no machine-readable events |
| 85 | Suomenlinna Museum | muzeum | `suomenlinna.fi` | - | - | skip | down: HTTPError |
| 86 | Q53456356 | muzeum | `vapaamuurarit.fi` | - | - | skip | no machine-readable events |
| 87 | Hakasalmi Villa | muzeum | `hakasalmenhuvila.fi` | - | - | skip | no machine-readable events |
| 88 | Hakasalmi Villa | muzeum | `hakasalmivilla.fi` | - | - | skip | no machine-readable events |
| 89 | Hakasalmi Villa | muzeum | `villahagasund.fi` | - | - | skip | no machine-readable events |
| 90 | Museum of Visual Impairment | muzeum | `nkl.fi` | - | - | skip | no machine-readable events |
| 91 | Nordea Bank Museum | muzeum | `nordea.fi` | - | - | skip | no machine-readable events |
| 92 | Helsinki tram museum | muzeum | `ratikkamuseo.fi` | - | - | skip | no machine-readable events |
| 93 | Studio Aalto | muzeum | `alvaraalto.fi` | - | - | skip | no machine-readable events |
| 94 | Q115553717 | muzeum | `valokuvataiteenmuseo.fi` | - | - | skip | no machine-readable events |
| 95 | Lauri and Lasse Reitz Foundation Museum | muzeum | `reitz.fi` | - | - | skip | no machine-readable events |
| 96 | TAHTO Center for Finnish Sports Culture | muzeum | `urheilumuseo.fi` | - | - | skip | no machine-readable events |
| 97 | Museum of Architecture and Design | muzeum | `admuseo.fi` | - | - | skip | no machine-readable events |
| 98 | Hotel and Restaurant Museum | muzeum | `hotellijaravintolamuseo.fi` | - | - | skip | no machine-readable events |
| 99 | Music Museum Fame | muzeum | `musiikkimuseofame.fi` | - | - | skip | no machine-readable events |
| 100 | Museum of Civil Defence | muzeum | `hvssy.fi` | - | - | skip | no machine-readable events |
| 101 | Museum of Impossible Forms | muzeum | `museumofimpossibleforms.org` | - | - | skip | no machine-readable events |
| 102 | Museum of Technology | muzeum | `tekniikanmuseo.fi` | - | - | skip | no machine-readable events |
| 103 | Seurasaari Open-Air Museum | muzeum | `kansallismuseo.fi` | - | - | skip | no machine-readable events |
| 104 | The Salvation Army Museum | muzeum | `pelastusarmeija.fi` | - | - | skip | no machine-readable events |
| 105 | Didrichsen Art Museum | muzeum | `didrichsenmuseum.fi` | - | - | skip | no machine-readable events |
| 106 | Theatre Museum | muzeum | `teatterimuseo.fi` | - | - | skip | no machine-readable events |
| 107 | Mannerheim Museum | muzeum | `mannerheim-museo.fi` | - | - | skip | no machine-readable events |
| 108 | Villa Gyllenberg | muzeum | `villagyllenberg.fi` | - | - | skip | no machine-readable events |
| 109 | Gloria Cultural Arena | muzeum | `nk.hel.fi` | - | - | skip | down: URLError |
| 110 | Helsinki City Museum | muzeum | `helsinginkaupunginmuseo.fi` | - | - | skip | no machine-readable events |
| 111 | Kaarle XII | music venue | `kaarle.fi` | - | - | skip | no machine-readable events |
| 112 | Finská národní galerie | muzeum | `kansallisgalleria.fi` | - | - | skip | no machine-readable events |
| 113 | Hanken School of Economics | univerzita | `hanken.fi` | - | - | skip | no machine-readable events |
| 114 | University of the Arts Helsinki | univerzita | `uniarts.fi` | - | - | skip | no machine-readable events |
| 115 | Riviera | kino | `rivierakallio.fi` | - | - | skip | no machine-readable events |
| 116 | Umělecké muzeum Helsinky | muzeum | `helsingintaidemuseo.fi` | - | - | skip | down: URLError |
| 117 | Museum of Finnish Architecture | muzeum | `mfa.fi` | - | - | skip | no machine-readable events |
| 118 | Kino Engel | kino | `kinoengel.fi` | - | - | skip | no machine-readable events |
| 119 | Tropicario | zoologická zahrada | `tropicario.com` | - | - | skip | no machine-readable events |
| 120 | Kinopalatsi | kino | `finnkino.fi` | - | - | skip | down: HTTPError |
| 121 | Helsinský olympijský stadion | stadion | `stadion.fi` | - | - | skip | no machine-readable events |
| 122 | Riviera Punavuori | kino | `rivieracinemas.fi` | - | - | skip | no machine-readable events |
| 123 | Korjaamo Culture Factory | kino | `korjaamo.fi` | - | - | skip | no machine-readable events |
| 124 | Kunsthalle Helsinki | muzeum | `taidehalli.fi` | - | - | skip | no machine-readable events |
| 125 | Flying Cinema Tour of Helsinki | kino | `fi.flyingcinematour.com` | - | - | skip | no machine-readable events |
| 126 | Amos Rex | muzeum | `amosrex.fi` | - | - | skip | no machine-readable events |
| 127 | Bar Loose | music venue | `barloose.com` | tribe-rest | 22 | skip | no place |
| 128 | Espa Stage | music venue | `espanlava.fi` | - | - | skip | no machine-readable events |
| 129 | Fallkulla Domestic Animal Farm | zoologická zahrada | `fallkulla.munstadi.fi` | - | - | skip | down: URLError |
| 130 | Sinebrychoff Art Museum | muzeum | `sinebrychoffintaidemuseo.fi` | - | - | skip | robots.txt |
| 131 | Helsinki University Observatory | muzeum | `observatorio.fi` | - | - | skip | no machine-readable events |
| 132 | European Digital Mathematics Library | knihovna | `eudml.org` | - | - | skip | no machine-readable events |
| 133 | Orion | kino | `cinemaorion.fi` | - | - | skip | no machine-readable events |
| 134 | Bio Rex | kino | `gilda.fi` | - | - | skip | no machine-readable events |
| 135 | Amos Anderson Art Museum | muzeum | `amosanderson.fi` | - | - | skip | no machine-readable events |
| 136 | Celia | knihovna | `celia.fi` | - | - | skip | no machine-readable events |
| 137 | Ateneum | muzeum | `ateneum.fi` | - | - | skip | robots.txt |
| 138 | Kino | kino | `andorra.fi` | - | - | skip | down: HTTPError |
| 139 | Korkeasaari Zoo | zoologická zahrada | `korkeasaari.fi` | - | - | skip | no machine-readable events |
| 140 | Tavastia Club | music venue | `tavastiaklubi.fi` | - | - | skip | no machine-readable events |
| 141 | Muzeum designu | muzeum | `designmuseum.fi` | - | - | skip | no machine-readable events |
| 142 | Paloheinä artificial turf field | stadion | `hps.fi` | - | - | skip | down: HTTPError |
| 143 | MUU Helsinki Contemporary Art Centre | galerie umění | `muu.fi` | - | - | skip | no machine-readable events |
| 144 | Bolt Arena | stadion | `boltarena.fi` | - | - | skip | no machine-readable events |
| 145 | Kulttuuritalo | koncertní sál | `kulttuuritalo.fi` | - | - | skip | no machine-readable events |
| 146 | Helsinki Music Centre | koncertní sál | `musiikkitalo.fi` | - | - | skip | no machine-readable events |
| 147 | Urhea Hall | aréna | `urhea-halli.fi` | - | - | skip | no machine-readable events |
| 148 | Sound Art Gallery Akusmata | galerie umění | `akusmata.com` | - | - | skip | http only |
| 149 | Hartwall-areena | aréna | `veikkausarena.fi` | - | - | skip | no machine-readable events |
| 150 | Tm-gallery | galerie umění | `painters.fi` | - | - | skip | no machine-readable events |
| 151 | Finlandia-talo | koncertní sál | `finlandiatalo.fi` | - | - | skip | no machine-readable events |
| 152 | Studium Catholicum | knihovna | `studium.fi` | - | - | skip | no machine-readable events |
| 153 | Q137858859 | kulturní centrum | `n10.fi` | - | - | skip | no machine-readable events |
| 154 | Vallila Allotment Garden Museum | muzeum | `vallilanspy.fi` | - | - | skip | no machine-readable events |
| 155 | Cable Factory | kulturní centrum | `kaapelitehdas.fi` | - | - | skip | no machine-readable events |
| 156 | Museum of Finnish Romani Culture | muzeum | `romanikulttuurinmuseo.com` | - | - | skip | no machine-readable events |
| 157 | Caisa | kulturní centrum | `kulttuuri.hel.fi` | - | - | skip | no machine-readable events |
| 158 | Helsinki German Library | knihovna | `deutsche-bibliothek.org` | - | - | skip | down: URLError |
| 159 | Caisa | kulturní centrum | `caisa.fi` | - | - | skip | no machine-readable events |
| 160 | Merkki Museum | muzeum | `merkkiin.fi` | - | - | skip | no machine-readable events |
| 161 | Elisa Telephone Museum | muzeum | `elisa.com` | - | - | skip | no machine-readable events |
| 162 | Elisa Telephone Museum | muzeum | `elisa.fi` | - | - | skip | no machine-readable events |
| 163 | Library of the Labour Movement | knihovna | `tyovaenperinne.fi` | - | - | skip | no machine-readable events |
| 164 | Library of Statistics | knihovna | `stat.fi` | - | - | skip | down: HTTPError |
| 165 | Q137858859 | kulturní centrum | `nilsiankatu10.fi` | - | - | skip | no machine-readable events |
| 166 | Military Museum of Finland | muzeum | `sotamuseo.fi` | - | - | skip | no machine-readable events |
| 167 | Kanneltalo | kulturní centrum | `kanneltalo.fi` | - | - | skip | no machine-readable events |
| 168 | Suvilahti | kulturní centrum | `suvilahti.fi` | - | - | skip | no machine-readable events |
| 169 | Mad House Helsinki | kulturní centrum | `madhousehelsinki.fi` | - | - | skip | no machine-readable events |
| 170 | Cultural Centre and Conference Hotel Sofia | kulturní centrum | `sofia.fi` | - | - | skip | no machine-readable events |
| 171 | Stoa | kulturní centrum | `stoa.fi` | - | - | skip | no machine-readable events |
| 172 | Ääniwalli | music venue | `aaniwalli.fi` | - | - | skip | no machine-readable events |

## Related

- [Open data sources of Praha](praha-open-data.md), [Open data sources of Bratislava](bratislava-open-data.md),
  [Open data sources of Helsinki (HRI)](helsinki-open-data.md)
- deployment `seeds/bbsk-events/README.md` (the generator and the events tail), `seeds/city-events/` (the probes)
- conformance `tests/mcp/events_readback.py` (the read-back through the MCP connector)
- Task T-5666
