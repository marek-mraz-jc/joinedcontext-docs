---
sidebar_position: 17
title: "Event sources: Bratislava"
description: Every candidate event source of Bratislava (city, boroughs, theatres, museums, galleries, libraries, culture centres, clubs, ticketing) probed on 2026-10-25 with its verdict; the usable ones feed the national store, read through the Endpoint Events in Bratislava.
---

# Event sources: Bratislava

Who publishes Bratislava's events in a form a pipeline can read. Bratislava's events live once, in the national
store `slovensko-podujatia`; the city reads them through its own Endpoint, as the Banská Bystrica Region reads its
slice. Task T-5666 (owner 2026-10-25) built this page.

## 1. How the inventory was made

1. **Candidates.** Wikidata (every item located in Bratislava with an official website whose class is a museum, theatre,
   gallery, library, cinema, faculty, university, castle, zoo, festival, concert or music venue, club, culture
   centre, church or association), the 17 boroughs, 50 sites read by hand (the city, Visit Bratislava, BKIS, the
   boroughs' culture centres, theatres, cinemas, clubs, ticketing) and the Bratislava rows of the national
   inventory `seeds/bbsk-events/sources-sk.csv`, whose decision stands where a row exists (HTML card templates the
   probe does not try). One row per host.
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

162 candidates, 9 usable on 2026-10-25. The owner's target of 100 usable sources per city
(T-5666) is not reached: the count per reason below is the target this city's open web gives today.

| verdict | sources |
|---|---|
| skip: no machine-readable events | 97 |
| skip: down | 36 |
| skip: http only | 10 |
| usable | 9 |
| skip: national inventory later | 3 |
| skip: none upcoming | 2 |
| skip: national inventory skip | 2 |
| skip: no place | 1 |
| skip: no template for wp-rss | 1 |
| skip: no template for wp-rest | 1 |

Integrated: a usable row is a `pipeline` row of `seeds/bbsk-events/sources-sk.csv` (town Bratislava, region BA), so
its events carry scope `/SK/BA/bratislava` in `slovensko-podujatia`. The Policy `podujatia-bratislava-read` narrows
the public Endpoint `slovensko-podujatia-bratislava` (Events in Bratislava, also as iCal) to that scope. One new
source joined on 2026-10-25: F. A. Hayek Foundation (insap.sk, The Events Calendar).

## 3. Every candidate

Copy: `Research/data/bratislava-events-2026-10-25.tsv` (the probe's columns, with the URL it read).

| # | candidate | type | site | kind | upcoming | verdict | reason |
|---|---|---|---|---|---|---|---|
| 1 | Slovenská zdravotnícka univerzita v Bratislave | university | `szu.sk` | - | - | skip | no machine-readable events |
| 2 | Katedrála svätého Martina | cathedral | `dom.fara.sk` | - | - | skip | no machine-readable events |
| 3 | Kostol Zvestovania Pána | church building | `frantiskani.sk` | - | - | skip | no machine-readable events |
| 4 | Bratislavský hrad | castle | `bratislava-hrad.sk` | - | - | skip | down: URLError |
| 5 | Devín | castle | `muzeumbratislava.sk` | - | - | skip | no machine-readable events |
| 6 | Chrám Povýšenia vznešeného a životodarného kríža | cathedral | `grkat.net` | - | - | skip | no machine-readable events |
| 7 | Divadlo Aréna | theatre building | `divarena.sk` | - | - | skip | down: HTTPError |
| 8 | Zoologická záhrada Bratislava | zoo | `zoobratislava.sk` | - | - | skip | no machine-readable events |
| 9 | Galéria mesta Bratislavy | art museum | `gmb.sk` | - | - | skip | no machine-readable events |
| 10 | Aupark | shopping center | `aupark-bratislava.sk` | - | - | skip | down: HTTPError |
| 11 | Nová scéna | theatre building | `nova-scena.sk` | - | - | skip | no machine-readable events |
| 12 | Chrám svätého Mikuláša | church building | `pravoslavni.sk` | - | - | skip | no machine-readable events |
| 13 | Paneurópska vysoká škola | private university | `paneurouni.com` | wp-rest | 47 listed | skip | national inventory later: WP REST list + detail HTML: no event start date found in the feed or in 3 sampled event pages; read by hand before a pip |
| 14 | Múzeum mesta Bratislavy | city museum | `muzeum.bratislava.sk` | - | - | skip | down: URLError |
| 15 | Múzeum dopravy v Bratislave | museum | `muzeumdopravy.com` | - | - | skip | http only |
| 16 | Ústredná knižnica Slovenskej akadémie vied | library | `uk.sav.sk` | - | - | skip | no machine-readable events |
| 17 | Centrum vedecko-technických informácií Slovenskej republiky | library | `cvtisr.sk` | - | - | skip | down: ConnectionResetError |
| 18 | Kostol Najsvätejšej Trojice (Podhradie) | church building | `podhradie.fara.sk` | - | - | skip | no machine-readable events |
| 19 | Slovenský Zväz Rádioamatérov | nonprofit organization | `szr.sk` | - | - | skip | http only |
| 20 | Slovenské národné múzeum | national museum | `snm.sk` | - | - | skip | no machine-readable events |
| 21 | Slovenská národná galéria | national gallery | `sng.sk` | - | - | skip | no machine-readable events |
| 22 | Štúdio L+S | theatre building | `studios.sk` | - | - | skip | no machine-readable events |
| 23 | Národný futbalový štadión | sports venue | `narodnyfutbalovystadion.sk` | - | - | skip | no machine-readable events |
| 24 | Slovenská technická univerzita v Bratislave | public university | `stuba.sk` | - | - | skip | no machine-readable events |
| 25 | Divadlo Astorka Korzo ’90 | theatre company | `astorka.sk` | - | - | skip | down: HTTPError |
| 26 | Fakulta matematiky, fyziky a informatiky Univerzity Komenského v Bratislave | faculty | `fmph.uniba.sk` | - | - | skip | no machine-readable events |
| 27 | Židovské komunitné múzeum | museum | `synagogue.sk` | - | - | skip | no machine-readable events |
| 28 | Slovenské múzeum dizajnu | museum | `scd.sk` | wp-rss | 10 listed | skip | national inventory later: RSS/Atom: no event start date found in the feed or in 3 sampled event pages; read by hand before a pipeline |
| 29 | Cinema City AuPark | movie theater | `cinema-city.co.il` | - | - | skip | no machine-readable events |
| 30 | Kino Lumiere | movie theater | `aic.sk` | - | - | skip | http only |
| 31 | Slovenské plynárenské múzeum | museum | `spp.sk` | - | - | skip | no machine-readable events |
| 32 | Múzeum školstva a pedagogiky | museum | `msap.sk` | - | - | skip | no machine-readable events |
| 33 | B-S 4 „Lány“ | museum | `mpo.sk` | - | - | skip | no machine-readable events |
| 34 | Vodárenské múzeum BVS, a. s. | museum | `vodarenskemuzeum.sk` | - | - | skip | no machine-readable events |
| 35 | Múzeum obchodu | museum | `muzeumobchodu.sk` | - | - | skip | no machine-readable events |
| 36 | Slovenský olympijský a športový výbor – Slovenské olympijské a športové múzeum | museum | `olympic.sk` | - | - | skip | no machine-readable events |
| 37 | Železničné múzeum Slovenskej republiky | museum | `zeleznicnemuzeum.sk` | - | - | skip | no machine-readable events |
| 38 | Múzeum Jána Cikkera | museum | `jan-cikker.org` | tribe-rest | 1 listed | usable | pipeline in slovensko-podujatia (tribe-rest) |
| 39 | Múzeum divadelného ústavu | museum | `theatre.sk` | - | - | skip | no machine-readable events |
| 40 | Centrum excelentnosti Therapolis | voluntary association | `therapolis.sk` | - | - | skip | no machine-readable events |
| 41 | Q85682434 | special library | `mecd.gob.es` | - | - | skip | down: URLError |
| 42 | Energy Centre Bratislava | nonprofit organization | `ecb2.sk` | - | - | skip | down: URLError |
| 43 | Slovenská Spoločnosť pre Kvalitu | nonprofit organization | `ssk.sk` | - | - | skip | no machine-readable events |
| 44 | Slovak Organization for Research and Development Activities | nonprofit organization | `sovva.sk` | - | - | skip | no machine-readable events |
| 45 | Drama Queer | theatre festival | `duhovyrok.sk` | - | - | skip | none upcoming |
| 46 | BROZ - ochranárske združenie | voluntary association | `broz.sk` | - | - | skip | no machine-readable events |
| 47 | Q136513218 | sports club | `tsunamiflorbal.sk` | - | - | skip | no machine-readable events |
| 48 | Ústavu zoológie SAV | publishing house | `zoo.sav.sk` | - | - | skip | no machine-readable events |
| 49 | Bienále animácie Bratislava | festival | `bibiana.sk` | - | - | skip | down: HTTPError |
| 50 | Refinery Gallery | convention center | `refinerygallery.sk` | - | - | skip | no machine-readable events |
| 51 | Právnická fakulta Univerzity Komenského v Bratislave | faculty | `flaw.uniba.sk` | - | - | skip | no machine-readable events |
| 52 | Fakulta chemickej a potravinárskej technológie Slovenskej technickej univerzity | faculty | `fchpt.stuba.sk` | - | - | skip | no machine-readable events |
| 53 | Filozofická fakulta Univerzity Komenského v Bratislave | faculty | `fphil.uniba.sk` | - | - | skip | no machine-readable events |
| 54 | Strojnícka fakulta Slovenskej technickej univerzity | faculty | `sjf.stuba.sk` | - | - | skip | no machine-readable events |
| 55 | Lekárska fakulta Univerzity Komenského v Bratislave | faculty | `fmed.uniba.sk` | - | - | skip | no machine-readable events |
| 56 | Slovak Business Agency | nonprofit organization | `sbagency.sk` | - | - | skip | no machine-readable events |
| 57 | Slovak Academic Information Agency | nonprofit organization | `saia.sk` | - | - | skip | down: HTTPError |
| 58 | EsFem | nonprofit organization | `esfem.sk` | - | - | skip | http only |
| 59 | Eurea | nonprofit organization | `eurea.sk` | - | - | skip | http only |
| 60 | Cord Blood Center | nonprofit organization | `cordbloodcenter.sk` | - | - | skip | no machine-readable events |
| 61 | Association for Youth, Science and Technology | nonprofit organization | `amavet.sk` | - | - | skip | no machine-readable events |
| 62 | P-MAT | nonprofit organization | `p-mat.sk` | - | - | skip | no machine-readable events |
| 63 | Raptor Protection of Slovakia | nonprofit organization | `dravce.sk` | - | - | skip | no machine-readable events |
| 64 | F. A. Hayek Foundation | nonprofit organization | `hayek.sk` | tribe-rest | 4 | usable | pipeline in slovensko-podujatia (tribe-rest) |
| 65 | International Centre for Applied Research and Sustainable Technology | nonprofit organization | `icarst.org` | - | - | skip | no machine-readable events |
| 66 | Múzeum polície Slovenskej Republiky | police museum | `minv.sk` | - | - | skip | no machine-readable events |
| 67 | Institute of Construction and Architecture | facility | `ustarch.sav.sk` | - | - | skip | no machine-readable events |
| 68 | Elektrotechnický ústav Slovenskej akadémie vied | facility | `elu.sav.sk` | - | - | skip | down: HTTPError |
| 69 | Institute of Experimental Endocrinology | facility | `endo.sav.sk` | - | - | skip | no machine-readable events |
| 70 | Institute of Landscape Ecology | facility | `uke.sav.sk` | - | - | skip | no machine-readable events |
| 71 | Institute of Economic Research | facility | `ekonom.sav.sk` | - | - | skip | no machine-readable events |
| 72 | Geophysical Institute | facility | `gpi.savba.sk` | - | - | skip | http only |
| 73 | Institute for Forecasting | facility | `prog.sav.sk` | - | - | skip | no machine-readable events |
| 74 | Ústav experimentálnej farmakológie a toxikológie | facility | `uef.sav.sk` | - | - | skip | no machine-readable events |
| 75 | Ústav normálnej a patologickej fyziológie | facility | `unpf.sav.sk` | - | - | skip | no machine-readable events |
| 76 | Národný Onkologický Ustav | facility | `nou.sk` | - | - | skip | down: HTTPError |
| 77 | International Laser Center | facility | `ilc.sk` | - | - | skip | down: ConnectionResetError |
| 78 | Ústav experimentálnej onkológie Slovenskej akadémie vied | facility | `exon.sav.sk` | - | - | skip | down: HTTPError |
| 79 | Výskumný ústav pôdoznalectva a ochrany pôdy | facility | `vupop.sk` | - | - | skip | no machine-readable events |
| 80 | Institute of Virology | facility | `virology.sav.sk` | - | - | skip | no machine-readable events |
| 81 | Institute of Informatics | facility | `ui.sav.sk` | - | - | skip | down: HTTPError |
| 82 | Centrum Vied o Umení SAV | facility | `cvu.sav.sk` | - | - | skip | http only |
| 83 | GUnaGU | theatre company | `gunagu.sk` | tribe-rest | 30 | usable | pipeline in slovensko-podujatia (tribe-rest) |
| 84 | Opera Slovenského národného divadla | theatre company | `snd.sk` | - | - | skip | no machine-readable events |
| 85 | Bratislava Monarchs | sports club | `monarchs.sk` | - | - | skip | no machine-readable events |
| 86 | Goetheho inštitút v Bratislave | cultural institution | `goethe.de` | - | - | skip | no machine-readable events |
| 87 | Univerzitná knižnica v Bratislave | scientific library | `ulib.sk` | - | - | skip | no machine-readable events |
| 88 | Bratislavské bábkové divadlo | theatre company | `babkovedivadlo.sk` | - | - | skip | no machine-readable events |
| 89 | Divadlo Ludus | theatre company | `ludusdivadlo.sk` | - | - | skip | no machine-readable events |
| 90 | Institute of Molecular Biology | facility | `imb.savba.sk` | - | - | skip | http only |
| 91 | Národné poľnohospodárske a potravinárske centrum | facility | `nppc.sk` | - | - | skip | no machine-readable events |
| 92 | Centres of Excellence | facility | `sav.sk` | - | - | skip | no machine-readable events |
| 93 | Building Testing and Research Institute | facility | `tsus.sk` | - | - | skip | no machine-readable events |
| 94 | Jednota slovenských matematikov a fyzikov | facility | `jsmf.eu.sk` | - | - | skip | down: URLError |
| 95 | Výskumný ústav ekonomiky poľnohospodárstva a potravinárstva | facility | `vuepp.sk` | - | - | skip | down: URLError |
| 96 | Biomedicínske centrum | facility | `bmc.sav.sk` | - | - | skip | no machine-readable events |
| 97 | Vyskumny Ustav Detskej Psychologie a Patopsychologie | facility | `vudpap.sk` | jsonld | 4 | skip | no place |
| 98 | Centrum Excelentnosti pre Aplikácie s Pokročilými Materiálmi | facility | `cemea.sav.sk` | - | - | skip | no machine-readable events |
| 99 | Interklinik Bratislava | medical facility | `interklinik.sk` | - | - | skip | no machine-readable events |
| 100 | Záhorská Bystrica | city district | `zahorskabystrica.sk` | tribe-rest | 0 | skip | national inventory later: tribe-rest parses but lists 0 upcoming events on the read date; keep, re-check before T-4896 |
| 101 | Čunovo | city district | `cunovo.eu` | - | - | skip | no machine-readable events |
| 102 | Devín | city district | `devin.sk` | - | - | skip | no machine-readable events |
| 103 | Podunajské Biskupice | city district | `biskupice.sk` | - | - | skip | no machine-readable events |
| 104 | Nové Mesto | city district | `banm.sk` | - | - | skip | no machine-readable events |
| 105 | Lamač | city district | `lamac.sk` | - | - | skip | no machine-readable events |
| 106 | Ružinov | city district | `ruzinov.sk` | - | - | skip | no machine-readable events |
| 107 | Devínska Nová Ves | city district | `devinskanovaves.sk` | - | - | skip | no machine-readable events |
| 108 | Karlova Ves | city district | `karlovaves.sk` | - | - | skip | down: URLError |
| 109 | Petržalka | city district | `petrzalka.sk` | - | - | skip | no machine-readable events |
| 110 | Vrakuňa | city district | `vrakuna.sk` | - | - | skip | no machine-readable events |
| 111 | Rača | city district | `raca.sk` | - | - | skip | no machine-readable events |
| 112 | Jarovce | city district | `jarovce.sk` | - | - | skip | http only |
| 113 | Vajnory | city district | `vajnory.sk` | - | - | skip | no machine-readable events |
| 114 | Rusovce | city district | `bratislava-rusovce.sk` | - | - | skip | no machine-readable events |
| 115 | Staré Mesto | city district | `staremesto.sk` | - | - | skip | no machine-readable events |
| 116 | Visit Bratislava | tourism organisation | `visitbratislava.com` | wp-rest-jsonld | 100 listed | usable | pipeline in slovensko-podujatia (wp-rest-jsonld) |
| 117 | Hlavné mesto SR Bratislava | city | `bratislava.sk` | - | - | skip | no machine-readable events |
| 118 | Bratislavské kultúrne a informačné stredisko | culture centre | `bkis.sk` | html-cards | 7 listed | usable | pipeline in slovensko-podujatia (html-cards) |
| 119 | Staromestské centrum kultúry a komunity | culture centre | `sckk.sk` | - | - | skip | down: URLError |
| 120 | Dom kultúry Dúbravka | culture centre | `dkdubravka.sk` | - | - | skip | no machine-readable events |
| 121 | Kultúrne zariadenia Petržalky | culture centre | `kzp.sk` | - | - | skip | no machine-readable events |
| 122 | Kultúrne zariadenia Ružinova | culture centre | `kzr.sk` | - | - | skip | down: URLError |
| 123 | Kultúrne centrum Nové Mesto | culture centre | `kcnm.sk` | - | - | skip | down: URLError |
| 124 | Kultúrne centrum Karlova Ves | culture centre | `kckv.sk` | - | - | skip | down: URLError |
| 125 | Miestne kultúrne stredisko Rača | culture centre | `mksraca.sk` | - | - | skip | down: URLError |
| 126 | Mestská knižnica v Bratislave | library | `mestskakniznica.sk` | - | - | skip | no machine-readable events |
| 127 | Nová scéna | theatre | `novascena.sk` | - | - | skip | no machine-readable events |
| 128 | Divadlo Aréna | theatre | `divadloarena.sk` | - | - | skip | no machine-readable events |
| 129 | Štúdio L+S | theatre | `studiols.sk` | - | - | skip | down: URLError |
| 130 | Radošinské naivné divadlo | theatre | `rnd.sk` | - | - | skip | http only |
| 131 | Divadlo Ludus | theatre | `divadloludus.sk` | - | - | skip | no machine-readable events |
| 132 | Divadlo West | theatre | `divadlowest.sk` | - | - | skip | down: URLError |
| 133 | Kino Lumière | cinema | `kinolumiere.sk` | - | - | skip | down: URLError |
| 134 | Kino Film Europe | cinema | `filmeurope.sk` | - | - | skip | no machine-readable events |
| 135 | Kino Mladosť | cinema | `kinomladost.sk` | - | - | skip | no machine-readable events |
| 136 | Slovenská filharmónia | concert hall | `filharmonia.sk` | - | - | skip | no machine-readable events |
| 137 | A4 – priestor súčasnej kultúry | culture centre | `a4.sk` | - | - | skip | no machine-readable events |
| 138 | Nová Cvernovka | culture centre | `novacvernovka.eu` | html-cards | 21 listed | usable | pipeline in slovensko-podujatia (html-cards) |
| 139 | KC Dunaj | music venue | `kcdunaj.sk` | - | - | skip | no machine-readable events |
| 140 | Fuga | music venue | `fuga.sk` | - | - | skip | down: HTTPError |
| 141 | Ateliér Babylon | music venue | `atelierbabylon.sk` | - | - | skip | down: URLError |
| 142 | Majestic Music Club | music venue | `majesticmusicclub.sk` | - | - | skip | down: URLError |
| 143 | Kunsthalle Bratislava | gallery | `kunsthallebratislava.sk` | - | - | skip | no machine-readable events |
| 144 | Danubiana | gallery | `danubiana.sk` | - | - | skip | no machine-readable events |
| 145 | Ticketportal | ticketing | `ticketportal.sk` | - | - | skip | no machine-readable events |
| 146 | GoOut Bratislava | ticketing | `goout.net` | - | - | skip | no machine-readable events |
| 147 | Kupvstupenku | ticketing | `kupvstupenku.sk` | - | - | skip | down: URLError |
| 148 | Predpredaj | ticketing | `predpredaj.sk` | - | - | skip | none upcoming |
| 149 | Bratislavský samosprávny kraj | region | `bratislavskykraj.sk` | - | - | skip | down: HTTPError |
| 150 | Bratislava Region Tourism | tourism organisation | `regionbratislava.sk` | - | - | skip | down: URLError |
| 151 | Malý Berlín | culture centre | `malyberlin.sk` | - | - | skip | no machine-readable events |
| 152 | Zichyho palác | culture centre | `zichyhopalac.sk` | - | - | skip | down: URLError |
| 153 | Pistori palác | culture centre | `pistoripalace.sk` | - | - | skip | down: URLError |
| 154 | Klub Lab | music venue | `klublab.sk` | - | - | skip | down: URLError |
| 155 | Divadlo Nová Scéna detské | theatre | `divadlo.sk` | - | - | skip | down: URLError |
| 156 | Knižnica Petržalka | library | `kniznicapetrzalka.sk` | wp-rss | 10 listed | skip | no template for wp-rss |
| 157 | Múzeum obetí komunizmu | museum | `mok.sk` | wp-rest | 33 listed | skip | no template for wp-rest |
| 158 | ÚĽUV, Múzeum ľudovej umeleckej výroby | museum | `uluv.sk` | html-cards | 100 listed | usable | pipeline in slovensko-podujatia (html-cards) |
| 159 | Aurelium | science centre | `aurelium.sk` | tribe-rest | 0 | skip | national inventory skip: feed answers 404: JSONDecodeError: Expecting value: line 1 column 1 (char 0) |
| 160 | Lúčnica | folk ensemble | `lucnica.sk` | jsonld | 4 | usable | pipeline in slovensko-podujatia (jsonld) |
| 161 | Univerzita Komenského | university | `uniba.sk` | wp-rss | 10 listed | skip | national inventory skip: RSS is the university news portal (articles after the fact), not an events feed |
| 162 | Vysoká škola múzických umení | university | `vsmu.sk` | html-cards | 40 listed | usable | pipeline in slovensko-podujatia (html-cards) |

## Related

- [Open data sources of Praha](praha-open-data.md), [Open data sources of Bratislava](bratislava-open-data.md),
  [Open data sources of Helsinki (HRI)](helsinki-open-data.md)
- deployment `seeds/bbsk-events/README.md` (the generator and the events tail), `seeds/city-events/` (the probes)
- conformance `tests/mcp/events_readback.py` (the read-back through the MCP connector)
- Task T-5666
