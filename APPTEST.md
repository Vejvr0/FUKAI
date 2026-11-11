# FUKAI – test aplikácie

Veľký test celej aplikácie pred vydaním prvej verzie. Testuje sa **skutočná appka v živom okne**: štart cez `ui.application.Application`, ovládanie cez skutočné widgety (kliky `QTest`, klávesy, menu, dialógy), skutočné modely a skutočný internet. Postup a parametre, ktoré musia byť na oboch OS rovnaké, sú v ALMANAC §8.3. Sem patria výsledky.

Závažnosť nálezov: **A** – opraviť pred vydaním v1 · **B** – opraviť pred v1, ak je čas, inak prvá oprava po vydaní · **C** – neskoršia verzia alebo kozmetika.

---

## MAC – 2026-11-09

### Prostredie

| | |
|---|---|
| Stroj | MacBook, Apple M2 (4P + 4E), 8 GB unified, macOS 26.6.2 |
| Voľná pamäť pri teste | 2,3–4,1 GB (väčšina aplikácií zatvorená) |
| Softvér | Python 3.12.10, PyQt6 / Qt 6.11.0, llama-cpp-python 0.3.36 Metal |
| Kód | commit `2455bc8` (web rozšírenie hotové), bez úprav počas testu |
| Modely | Qwen 2.5 1.5B Instruct Q4_0 (1,0 GB), Gemma 3 4B it Q4_K_M (2,3 GB) |
| Platforma Qt | `cocoa` (živé okno, nie offscreen) |
| Dáta | fáza P0 na ostrom `~/Library/Application Support/FUKAI`, ostatné v testovacom priečinku, ktorý začína prázdny ako ostrý |

**Ostrý FUKAI_HOME** je `~/Library/Application Support/FUKAI` (vznikol 2026-11-06 pri prvom ostrom spustení). Obsahuje `settings.json`, `fukai.db` (schéma v2, 0 modelov, 0 chatov) a prázdny `models/`. Fáza P0 ho len spustila a zatvorila.

### Ako sa testovalo

Desať fáz, každá je samostatný proces appky. Skripty sú v scratchpade session (nie v repe). Výsledky sa zapisujú do súboru, nie na konzolu: počas načítania modelu llama-cpp-python umlčí stdout aj stderr celého procesu (§7).

| Fáza | Obsah |
|---|---|
| P0 | ostrý FUKAI_HOME: štart a zatvorenie |
| P1 | prvé spustenie na prázdnom domove a všetky funkcie (podrobne nižšie) |
| P1b | doplnky: Stop, skrátená odpoveď, prepnutie chatu, čipy príloh, mazanie modelu |
| P2 | reštart nad dátami z P1: čo sa zachovalo, integrita, 12 ťahov a pamäť, zatvorenie počas importu |
| P3 | zatvorenie počas hľadania na webe |
| P4 + P5 | `SIGKILL` počas odpovede, potom štart a kontrola databázy |
| P6 | poškodený `settings.json` |
| P7 | neplatný priečinok modelov (a), poškodená databáza (b) |
| P8 | dve inštancie naraz nad tým istým domovom |
| P9 | klávesnica, výška poľa, drag & drop, najmenšie okno, zúženie okna |

### Výsledok v skratke

**109 kontrol, z toho 97 OK.** Zo zvyšných 12 je **6 skutočných chýb appky** (3 nálezy, A1, A2, B1) a 6 sú chyby testovacieho skriptu. Tie som preveril zvlášť a správanie appky je v poriadku (pozri „Chyby testu“). K tomu 1 sekcia spadla na výnimke testu (Stop), P1b ju zopakoval a prešla.

Nepadla ani raz **appka**. Pád procesu (kód 134) nastal len raz, keď výnimku vyhodil môj testovací kód v slote. Zatvorenie počas odpovede, importu aj hľadania prebehlo bez `GGML_ASSERT` (Metal) a bez `QThread: Destroyed`. Po zatvorení nezostali `-wal` / `-shm` a databáza prešla `integrity_check` aj po `SIGKILL`.

### Výsledky podľa oblastí

| Oblasť | Čo sa overilo | Výsledok |
|---|---|---|
| Štart | kroky splashu, `Pripravené · METAL`, detekcia (Metal, 4 P-jadrá), varovanie o RAM pri < 4 GB voľnej | ✅ |
| Prvé spustenie | `settings.json` s predvolenými hodnotami, `fukai.db` v2, `models/`, uvítanie, „Vyber model“, Odoslať vypnuté, bez modelu toast „Najprv vyber model.“ a text zostane v poli | ✅ |
| Vzhľad | rozostup tabov 8 / 8 px (Fusion), čip „GPU · Apple Metal · 8 GB RAM“, obe témy, 23 snímok | ✅ |
| Import | Qwen 1 GB, priebeh kladný a rastúci, model sa po importe vyberie; duplikát → info a výber existujúceho; `mmproj` aj falošný `.gguf` odmietnuté s vlastnou správou; zrušenie ✕ v toaste → bez `.part`, nič sa nezaregistrovalo | ✅ |
| Sken priečinka | Gemma (odkaz) sa objavila pri otvorení Nastavení, toast „pribudli: 1“ | ✅ |
| Nastavenia | modal s informáciami o modeli (10 riadkov z hlavičky), „Otvoriť priečinok“, prepínače web / téma sa uložia do `settings.json` | ✅ |
| Menu modelov | otvorí sa, 2 riadky, zaoblené, zatvorí sa | ✅ |
| Chat | načítanie, streamovanie, meta riadok, chat vznikne až s odpoveďou, sidebar radí podľa poslednej zmeny | ✅ |
| Markdown | odpoveď rozdelená na text + blok kódu, Kopírovať vloží kód do schránky; tabuľku Qwen nevyrobil (model, nie appka) | ✅ |
| Stop | ťah vrátený, otázka späť v poli; pri prvej správe chat nevznikne a vráti sa uvítanie; Stop počas načítania vypnutý | ✅ |
| Skrátená odpoveď | `max_tokens=24` → `length`, meta „skrátená - dosiahnutý limit tokenov“ | ✅ |
| Prepnutie chatu počas odpovede | v inom chate nie je Stop a Odoslať je nedostupné; návrat → rozpísaná odpoveď pokračuje a dobehne do pôvodného chatu | ✅ |
| Menu ⋯ (oprava z rána, živé cocoa) | premenovanie s diakritikou a emoji, mazanie iného chatu počas odpovede **bez pádu**, vlastný chat počas odpovede odmietnutý toastom | ✅ |
| Vlastnosti | stránka easy / expert, `n_ctx` a `max_tokens` cez UI → lišta „Neuložené zmeny (2)“ → Použiť → ďalšia správa načíta model s `n_ctx=2048`; rovnaký seed → rovnaká odpoveď; draft prežije „Fúkni nový chat“ | ✅ |
| Kontext | pri `n_ctx=512` sa staršie správy vynechajú (`dropped` + toast); príliš dlhá otázka → chyba, ťah vrátený | ✅ (doteraz neoverené) |
| Prílohy | txt, md, csv, json, py, xlsx, docx, pdf naraz za 0,24 s; náhľad; model z nich odpovedal (všetky 4 tajné údaje); png, binárny a prázdny súbor odmietnuté; PDF so 300 stranami za 9,4 s, UI plynulé, orezané na kontext s varovaním; správa len s prílohou → názov chatu z názvu súboru; drag & drop | ⚠️ A1, B1 |
| Web | prepínač v Nastaveniach a v composeri, skutočné hľadanie (3 zdroje vrátane Wikipédie), stav v bubline, zdroje pod odpoveďou, **klik na [1] otvorí adresu** (cez `QDesktopServices`), Gemma cituje `[3]`, výmena modelu prepínač vypne | ✅ |
| Monitor | CPU / GPU / RAM počas odpovede; **GPU % na Macu cez `ioreg` funguje** (13–15 % pri Qwene) | ✅ (doteraz neoverené) |
| Mazanie modelu | dialóg „zmaže sa len odkaz“, odkaz preč, pôvodný súbor zostal, chat bez modelu → „Vyber model“ a „Najprv vyber model.“ | ✅ |
| Reštart | téma, web, posledný model, chaty, zdroje aj čipy v histórii sa zachovali | ✅ |
| Dlhšie používanie | 12 ťahov: pamäť +8 MB, rýchlosť 70–78 tok/s | ✅ |
| Ukončenie | počas odpovede 0,06 s, počas importu 0,2 s (bez `.part`), počas hľadania 1,3 s; kód 0 | ✅ |
| Pád (`SIGKILL`) | `-wal` zostal, pri štarte sa zlúčil; integrita OK, žiadna otázka bez odpovede, rozpísaný prvý ťah nevytvoril chat | ✅ |
| Poškodené nastavenia | prepísané predvolenými, varovanie | ✅ |
| Neplatný priečinok modelov | nie je fatálny: použije sa predvolený s varovaním (§8 krok 7) | ✅ / C3 |
| Poškodená databáza | fatálny dialóg, kód 1, okno nevznikne | ⚠️ B2 |
| Dve inštancie | obe odpovedali a zapísali, databáza v poriadku | ✅ / C1 |
| Klávesnica a pole | Enter odošle, Shift+Enter nový riadok, pole rastie po 200 px, fokus po odpovedi v poli | ✅ |
| Okno | najmenšia veľkosť 800 × 560 | ⚠️ A2 |

### Namerané hodnoty

| Meranie | Hodnota |
|---|---|
| Štart do zobrazenia okna | 3,5 s (z toho ~1,35 s import Pythonu, Qt a splash; minimálny čas splashu 2 s) |
| Kroky štartu | nastavenia 0,06 s · engine 0,2 s · hardvér < 0,01 s · databáza a modely < 0,01 s |
| Pamäť appky bez modelu | 250–340 MB |
| Import 1 GB | 0,9 s (SSD, ~1,1 GB/s) |
| Qwen 1.5B: načítanie / prvý token / rýchlosť | 0,8 s / 0,10 s / 74 tok/s |
| Qwen 1.5B: pamäť procesu s modelom | 1,4 GB |
| Gemma 4B: načítanie / rýchlosť | 2,8 s / 24 tok/s |
| Gemma 4B s webom: prvý token | 11,5 s (spracovanie ~2 900 tokenov zdrojov pri 2–3 GB voľnej RAM) |
| Odozva UI (50 ms časovač, najdlhšia medzera) | 63 ms pri načítaní aj generovaní, 69 ms pri extrakcii 300-stranového PDF |
| Otázka s webom (Qwen) | 7,2 s celkom vrátane hľadania |
| 12 ťahov za sebou | RSS 1545 → 1553 MB, 78 → 70 tok/s |
| Ukončenie | odpoveď 0,06 s · import 0,2 s · hľadanie 1,3 s |

### Nálezy

| ID | Nález | Dopad | Návrh | Kedy |
|---|---|---|---|---|
| **A1** | **Pri 5 a viac prílohách sú viditeľné len prvé 4 čipy.** `AttachmentBar._reflow()` (`ui/attachment_bar.py:197`) skončí, keď sa počet stĺpcov nezmenil, takže 5. až 8. čip sa do mriežky vôbec nevloží. Nepomôže ani zmena šírky okna. | Čipy sú neviditeľné a nedajú sa odobrať, no ich text sa **odošle modelu**. Používateľ nevie, čo posiela. | Prestavať mriežku vždy, keď sa zmení zoznam čipov. Kontrolu „rovnaký počet stĺpcov“ nechať len pre `resizeEvent` (tam chráni pred zacyklením, krok 12). | pred v1 · **✅ opravené 2026-11-11** |
| **A2** | **Po zúžení okna sa stĺpec správ nezmenší.** Zostane 760 px, kým viewport má 494 px, a text odpovede aj meta riadok sú orezané vpravo. Platí to aj pre chat otvorený až v zúženom okne. | Rozdelenie obrazovky alebo menší notebook = nečitateľné odpovede. | Príčina: `_TextView.fit()` a časti odpovede majú `setFixedSize` / `setFixedWidth` podľa poslednej šírky stĺpca, takže minimum stĺpca je 760 a `Resize` nepríde. Šírka detí nesmie určovať minimum stĺpca (vodorovná politika `Ignored` alebo `setMinimumWidth(0)` na stĺpci); `fit()` stačí volať s novou šírkou viewportu. | pred v1 · **✅ opravené 2026-11-11** |
| **A3** | **Neodchytená výnimka v slote zhodí proces bez hlásenia** (PyQt6 → abort, kód 134). Na Macu sa potom pri ďalšom štarte **ešte pred splashom** objaví systémový dialóg „aplikácia sa neočakávane ukončila pri obnove okien“ a appka čaká, kým ho používateľ zavrie. Overené: môj testovací skript vyhodil výnimku a ďalší štart visel na tomto dialógu. | Akákoľvek prehliadnutá chyba = zmiznuté okno bez stopy. Po balení nebude ani konzola. | `sys.excepthook` v `main.py`: zápis do logu + dialóg (ponúknuté už v kroku 9). Pri balení `.app` vypnúť obnovu okien (napr. `NSQuitAlwaysKeepsWindows = NO`) a overiť v kroku 14. | pred v1 (excepthook) · **✅ opravené 2026-11-11**; krok 14 (bundle – obnova okien) |
| **A4** | **Log do súboru neexistuje.** Hlásenia idú na `stderr` (`Application._report_notices`, `[SKEN]`), v zabalenej appke s `--windowed` sa stratia; počas načítania modelu sa strácajú aj teraz (§7). | Chyby u používateľa sa nedajú diagnostikovať. | Malý logger do `app_dir()/fukai.log` (rotovaný), nie cez `sys.stderr`. Spolu s A3. | pred v1 · **✅ opravené 2026-11-11** |
| **B1** | **Čip prílohy pri práve odoslanej správe nie je klikateľný**, kým sa chat znova neotvorí (nemá ešte `id` z databázy). | Drobná nekonzistencia: rovnaký čip raz ide otvoriť, raz nie. | Po `turn_finished` doplniť id príloh do posledného `_UserMessage` (`add_turn` ich vie vrátiť) alebo správu prestavať z databázy. | pred v1 · **✅ opravené 2026-11-11** |
| **B2** | **Poškodená databáza → appka sa nespustí a dialóg radí „skontroluj priestor na disku a práva“.** Príčina je však poškodený súbor, nie disk. | Používateľ nemá ako pokračovať, kým súbor ručne nezmaže. | Rozlíšiť `sqlite3.DatabaseError` („file is not a database“) od chýb disku. Správa „Databáza chatov je poškodená“ s cestou; voliteľne presunúť súbor na `fukai.db.bad` a začať s prázdnou. | pred v1, ak je čas · **✅ opravené 2026-11-11** |
| **B3** | **Gemma s webom: prvý token po 11,5 s, bublina je dovtedy prázdna.** Stav „Čítam 3 stránky…“ sa po hľadaní zmaže a spracovanie ~2 900 tokenov zdrojov už nič neukazuje. | Pôsobí to ako zamrznutie (na PC s CUDA bude čas zlomkom). | Po hľadaní ukázať stav „Spracúvam zdroje…“, ktorý zmizne pri prvom tokene. | pred v1, ak je čas · **✅ opravené 2026-11-11** |
| **B4** | **Odhad tokenov príloh (`dĺžka / 4`) je pri Qwene asi 2× nízky** (zistené 2026-11-11 pri overení A1). 8 testovacích príloh: odhad 1 595, skutočne 3 046 tokenov pri rozpočte promptu 3 008 (`n_ctx` 4096). Najväčší rozdiel má CSV (70 → 212) a PDF s tabulátormi (1 350 → 2 492, pozri C4). | Čipy ukazujú, že sa prílohy zmestia, ale odoslanie skončí „Správa je príliš dlhá…“ a ťah sa vráti – bez rady, ktorú prílohu odobrať. | Opatrnejší odhad (slovenčina pri Qwene ~2 znaky na token), presný počet tokenizérom modelu, alebo orezať prílohy až v `build_prompt` podľa skutočného počtu (ako zdroje z webu, 13c). | pred v1 (rozhodnutie autora: orezať pri zostavení promptu) · **✅ opravené 2026-11-11** |
| **C1** | Dve inštancie naraz fungujú, ale každá načíta vlastný model (2× pamäť) a nevidia navzájom nové chaty. | Na 8 GB Macu dvojité načítanie = swap. | Jedna inštancia (`QLockFile` v `app_dir()`); druhé spustenie len prenesie okno do popredia. | neskôr |
| **C2** | Prázdny `.txt` → hlásenie „súbor môže byť poškodený, zašifrovaný… OCR nie je podporované“. | Zavádzajúca rada. | Vlastná správa „Súbor je prázdny.“ | neskôr |
| **C3** | Neplatný `models_dir` v `settings.json`: appka použije predvolený priečinok s varovaním, ale súbor sa neopraví, takže varovanie príde pri každom štarte. | Kozmetika. | Po návrate na predvolený priečinok ho zapísať. | neskôr |
| **C4** | PDF z niektorých generátorov (overené na PDF z Qt) vracia `pypdf` so slovami oddelenými tabulátormi. | Modelu to nevadí, náhľad vyzerá zvláštne. | Normalizovať medzery v riadku pri extrakcii PDF. | neskôr |
| **C5** | Pri najmenšej šírke je nápoveda composera odrezaná v strede slova („Shift+Ente“) a názvy príloh sú skrátené na „poz…txt“, aj keď je miesto. | Kozmetika. | Nápovedu pri úzkom composeri skryť. Skracovanie názvov príloh bola chyba zaokrúhlenia v `ChipName.sizeHint`. | neskôr · názvy príloh **✅ 2026-11-11** (s A1) |
| **C6** | Malé modely odpovedajú slabo: Qwen 1.5B odpovedal „¡Hola! Kto si?“, ignoroval systémový prompt „po anglicky“, odmietol napísať príbeh („Sorry, but I can't assist…“) a miestami odpovedá po česky. | Nie je to chyba appky, ale dojem používateľa. | Do dokumentácie alebo uvítania odporučiť Gemmu 4B a väčšie modely; Qwen 1.5B len na rýchle testy. | dokumentácia |

Známe a nerozhodnuté body, ktoré test len potvrdil (bez nového ID): toast prekrýva prvú kartu na stránkach Nastavenia a Vlastnosti (rozhodnutie autora: nerieši sa), kontextové menu textu je po anglicky, citácie `[n]` v texte nie sú klikateľné, v menu macOS je názov „Python“ (vyrieši `.app`, krok 14).

### Opravy po teste

Overené na Macu; na PC sa overia v teste WINDOWS.

| ID | Dátum | Čo sa zmenilo | Overenie |
|---|---|---|---|
| A1 | 2026-11-11 | Bar príloh je rámček so zvislým posuvníkom, viditeľné najviac 2 riadky čipov. Mriežka sa prestaví pri každej zmene zoznamu. Popri tom opravené: obrátené poradie príloh po Stope, pretečenie čipu „· orezané“ v úzkom okne, skracovanie názvov, ktoré sa zmestia (časť C5), a klik do baru, ktorý bral fokus vstupu. | `test_bar.py` 35/35 (`offscreen` aj `cocoa`); skutočná appka s Qwenom 8/8 – 7 reálnych príloh, posuvník pri 3 riadkoch, poradie po Stope, odpoveď z príloh |
| B1 | 2026-11-11 | `add_turn` vracia aj id príloh a `turn_finished` ich donesie k poslednej otázke, čipy dostanú id cez `set_id`. Druhá príčina: `MessageList.begin_turn` nepripájal `preview_requested` (robil to iba `set_messages` pri otvorení chatu), takže klik by aj s id nikam neviedol. | `live_b1.py` 11/11 v skutočnej appke s Qwenom – nový aj existujúci chat, klik → náhľad s textom z databázy, otázka bez príloh, Stop, odchod z chatu a návrat počas odpovede, znovuotvorenie; `add_turn` 4/4 vrátane posunu `updated_at`; regresia A1 |
| B2 | 2026-11-11 | Poškodenie (`SQLITE_NOTADB`, `SQLITE_CORRUPT`) má vlastnú chybu `DatabaseCorruptError` – „Databáza chatov je poškodená.“ s celou cestou k súboru v rade; chyby disku a práv majú pôvodnú radu. `PRAGMA quick_check` pri otvorení nájde aj poškodenie v strede súboru. Popri tom opravený pád: klik v sidebare na chat, ktorého správy sa nedajú prečítať, zhodil appku (134) a `open_chat` predtým prepol `_chat_id` – teraz toast a zobrazený chat zostáva. Obnova je ručná (rozhodnutie autora). | `test_b2.py` 22/22 (4 druhy poškodenia, 2 chyby práv, zdravá/nová/prázdna databáza); skutočná appka: nezmysel aj prepísané stránky → fatálny dialóg s cestou, kód 1, bez práv → pôvodná rada; `live_open.py` 5/5 (klik na nečitateľný chat: toast, správa ide do zobrazeného chatu) |
| B3 | 2026-11-11 | Keď model začne spracúvať prompt, bublina ukáže „Spracúvam zdroje…“ (web) alebo „Spracúvam prílohy…“; zmizne prvým tokenom, pri návrate do chatu sa ukáže znova. Signál `web_progress` premenovaný na `turn_status`. | `live_b3.py` 9/9 (falošné hľadanie, 3 dlhé zdroje): stav po načítaní modelu a pred prvým tokenom, viditeľný celý čas (vzorky po 100 ms), prílohy, obyčajná otázka bez stavu, návrat do chatu. Bez stavu bola bublina prázdna 12 s (Qwen) a 33 s (Gemma, ~2 GB voľnej RAM) |
| A3 + A4 | 2026-11-11 | `fukai.log` v dátovom priečinku (rotácia 1 MB + 1 starší, `core/log.py` napísal autor): hlavička behu, všetky toasty aj s `detail`, načítanie modelu, súhrn odpovede bez textov, varovania Qt; tvrdé pády cez `faulthandler` do `fukai-crash.log`. `sys.excepthook` + `threading.excepthook`: traceback do logu, appka beží ďalej s chybovým toastom (rozhodnutie autora), pri záplave jeden toast; neočakávaná chyba pri štarte = fatálny dialóg s cestou k logu. | `live_a34.py` 18/18 (výnimka v slote, v `QThread`, v `threading.Thread`, 20 naraz = 1 toast, appka ďalej odpovedá, text otázky nie je v logu) + 3/3 chyba pri štarte; `test_rotate.py` 3/3; regresia A1, B1, B2, B3 nad repom |
| B4 | 2026-11-11 | Prílohy sa orežú až pri zostavení promptu skutočnými tokenmi modelu (`fit_attachments`, delenie ako pri webe), správa odíde vždy; žiadna príloha sa nevynechá, ukladá sa poslaný text, toast povie, ktoré sa orezali. Pri pripnutí len upozornenie podľa odhadu. | `live_b4.py` 9/9 (pôvodný kód 0/5): 8 príloh z P1 – orezaná len `zmluva.pdf`, odpoveď „ZELENÝ JAVOR“; ďalšia otázka v chate; 300-stranové PDF (uložených 5 459 z 810 082 znakov, tokenizácia ~0,4 s); Stop vráti celú prílohu. 8 kontrol `core.context`; regresia celého dňa nad repom |
| A2 | 2026-11-11 | Stĺpec správ má vodorovnú politiku `Ignored` – šírku určuje okno, nie deti s pevnou šírkou z `fit()`; čipy nad otázkou v histórii sa zalamujú do riadkov vpravo (`_ChipFlow`). | `live_a2.py` 6/6 (pôvodný kód 3/6): okno 1400/1000/800 → stĺpec 760/642/438, 0 pretečených widgetov, aj pri chate otvorenom až v úzkom okne; po rozšírení znova 760; 8 čipov viditeľných. Regresia celého dňa nad repom |

### Overené na Macu prvýkrát

Tieto body boli v ALMANACu vedené ako neoverené a test ich uzavrel:
- **GPU % v monitore cez `ioreg`** (§8 krok 9, kúsok 7) – funguje, kľúč `Device Utilization %` sedí.
- **Kúsky 7–12 na macOS:** monitor, Nastavenia, Vlastnosti, info o modeli, menu ⋯, prílohy.
- **Veľké PDF** (krok 12): 300 strán za 9,4 s vo vlastnom vlákne, UI plynulé.
- **Orezávanie histórie (`dropped`)**, doteraz neoverené ani na Windows – funguje.
- **Web v živom okne `cocoa`** vrátane kliku na zdroj.
- **Oprava pádu v menu ⋯** (ráno 2026-11-09) – mazanie chatu počas odpovede v živom okne bez pádu.

### Čo test neoveril (treba ručne)

- **Natívne dialógy** (`QFileDialog` pri „Pridať model“ a prílohách) – automat ich neovládne. Cesta za dialógom (`import_model`, `add_attachments`) je overená.
- **Skutočné otvorenie prehliadača a Findera** – test zachytil adresu cez `QDesktopServices.setUrlHandler`, okná sa neotvárali.
- **Kurzor ruky v menu modelov** (overený 2026-11-06 na M2, odvtedy bez zmeny).
- **Uspanie a prebudenie počas generovania, odpojenie siete počas hľadania.**
- **Odrolovanie počas streamovania** – v P9 sa odpoveď zmestila do okna (overené na PC 1 2026-11-06).

### Chyby testu (nie appky)

Pre úplnosť, aby sa ZLE v surových výsledkoch nečítali ako chyby appky:
- **Stop (P1):** Qwen odmietol napísať príbeh, takže 15 tokenov nikdy neprišlo. Opakované v P1b s iným promptom – prešlo.
- **Mazanie modelu (P1, P1b, 6 ZLE):** dialóg zachytil a zrušil zatvárač modálnych okien z predchádzajúcej sekcie, ktorý ešte čakal. Overené zvlášť (dialóg aj zmazanie fungujú) a znova v P2.
- **Čip v histórii po opätovnom otvorení (P1b):** test klikol na starý widget, ktorý ešte čakal na `deleteLater`. V P2 so správnym výberom OK.
- **P7a:** test čakal fatálny dialóg, ale neplatný `models_dir` fatálny nie je (správne podľa §8 krok 7).

---

## WINDOWS – PC 1, 2026-11-11

### Prostredie

| | |
|---|---|
| Stroj | PC 1, Core Ultra 7 265K (8P + 12E), RTX 5060 Ti 16 GB (sm_120), 32 GB RAM, Windows 11 Pro 26300 |
| Softvér | Python 3.12.10, PyQt6 / Qt 6.11.0, llama-cpp-python 0.3.36 CUDA, CUDA Toolkit 13.0 |
| Kód | commit `46963e7` (opravy A1–A4, B1–B4), bez úprav počas testu |
| Modely | Qwen 2.5 1.5B Instruct Q4_0 (1,0 GB), Gemma 3 4B it Q4_K_M (2,3 GB), Mistral 7B Instruct v0.2 Q4_K_M (4,1 GB) |
| Platforma Qt | `windows` (živé okno, nie offscreen) |
| Voľná RAM pri teste | 1,6–2,5 GB (cudzí proces `javaw` držal 13,5 GB) – RAM merania sú tým skreslené, GPU nie |
| Dáta | P0 na ostrom `%LOCALAPPDATA%\FUKAI`, ostatné fázy v testovacom domove, ktorý začína prázdny |

Ostrý domov nebol pred testom čistý ako na Macu – obsahoval 2 modely, 5 chatov a 32 správ z vývoja. Fáza P0 ho len spustila a zatvorila, nič v ňom nemenila.

### Ako sa testovalo

Sedemnásť fáz, každá samostatný proces appky, skripty v scratchpade session (nie v repe). Testy spúšťajú **skutočné `Application.run()`** a kroky vkladajú do jeho vlastnej smyčky cez `QTimer` – telo `run()` sa nekopíruje, takže sa testuje tá istá cesta, ktorou ide používateľ. Výsledky idú do súboru, `PYTHONIOENCODING=utf-8`.

| Fáza | Obsah |
|---|---|
| P0 | ostrý `%LOCALAPPDATA%\FUKAI`: štart, kroky splashu, zatvorenie |
| P1a | prvé spustenie na prázdnom domove, import, duplikát, odmietnutie `mmproj` / falošného a beztemplejtového `.gguf`, zrušenie importu, sken, info o modeli, Otvoriť priečinok, menu modelov |
| P1b | chat s Qwenom na CUDA, monitor, markdown + Kopírovať, Stop, skrátená odpoveď, prepnutie chatu počas odpovede a návrat |
| P1c | menu ⋯ (tokeny, premenovanie s diakritikou a emoji, **mazanie iného chatu počas odpovede**), Vlastnosti (`n_ctx` cez UI → Použiť → reload, seed, system prompt, draft), kontext (`dropped`, príliš dlhá otázka) |
| P1d | prílohy: 8 formátov, 9 čipov, chybné súbory, 300-stranové PDF, len príloha, drag & drop + **overenie A1, B1, B3, B4** |
| P1e | web: tri úrovne prepínača, skutočné hľadanie, zdroje, klik na zdroj, Gemma cituje, globálne vypnutie |
| P1f | import 4,1 GB, Gemma a Mistral na GPU s VRAM, **zmazanie načítaného modelu (mmap)**, tmavá téma |
| P1g | veľký `n_ctx` (Gemma 131072), čiastočný offload, CPU režim |
| P1h | **plná VRAM** – tri cudzie procesy držia grafickú pamäť, zostáva 0,3 GB |
| P1i | **overenie A2, A3, A4**: šírky okna 1400/1000/800, výnimky v troch druhoch vlákien, obsah logu |
| P2 | reštart nad dátami z P1, integrita, 12 ťahov a pamäť, zatvorenie počas importu |
| P3 | zatvorenie počas hľadania na webe |
| P4 + P5 | `taskkill /F` počas odpovede, potom štart |
| P6 + P7 | poškodený `settings.json`, `models_dir` pod súborom, `fukai.db` ako nezmysel aj s prepísanými stránkami |
| P8 | dve inštancie naraz nad tým istým domovom |
| P9 | klávesnica, rast poľa, fokus, najmenšie okno, zúženie |
| P10 | natívne dialógy `#32770`, kurzor ruky v menu (`GetCursorInfo`), `fukai-crash.log` pri tvrdom páde |

### Výsledok v skratke

**445 kontrol, všetky OK. Ani jedna chyba appky.** Appka nespadla ani raz; jediné pády procesu spôsobil môj testovací kód (a z nich dva potvrdili, že A3 funguje – výnimka v slote skončila toastom a záznamom v logu, nie abortom).

Zo 17 fáz žiadna nenašla chybu v kóde FUKAI. Nájdené boli tri veci mimo appky (jedna v prostredí, dve v knižnici / odhade) – nižšie ako W1–W4. Opravy A1–A4 a B1–B4 sú na Windows overené, rovnako ako body, ktoré sa na Macu overiť nedali (VRAM, mmap, natívne dialógy, NVML, ikona na paneli úloh).

### Výsledky podľa oblastí

| Oblasť | Čo sa overilo | Výsledok |
|---|---|---|
| Štart | 6 krokov splashu, `Pripravené · CUDA`, `backend=cuda`, 8 P-jadier z 20, sm_120, VRAM 16 311 MB, model sa pri štarte nenačíta | ✅ |
| Ikona na paneli úloh | `SetCurrentProcessExplicitAppUserModelID` = `FEIT.FUKAI` (čitateľné cez `GetCurrentProcessExplicitAppUserModelID`), ikona má 9 veľkostí 16–256 | ✅ |
| Prvé spustenie | `settings.json` s predvolenými hodnotami, `fukai.db` v2, `models/`, `fukai.log`, „Vyber model“, Odoslať vypnuté, bez modelu toast a text zostane v poli | ✅ |
| Import | Qwen 1,0 GB za 1 s (128 hlásení priebehu), Mistral 4,1 GB za 2,7 s **bez pretečenia nad 2 GiB**, model sa po importe vyberie, duplikát → info, zrušenie ✕ bez `.part` | ✅ |
| Odmietnutie modelov | `mmproj` (arch `clip`), textový `.gguf`, model bez chat template – každý s vlastnou správou, nič sa nezaregistruje ani neskopíruje | ✅ |
| Sken a Nastavenia | Gemma pribudla pri otvorení Nastavení („pribudli: 1“), modal s 21 riadkami z hlavičky, Otvoriť priečinok mieri na `models/` | ✅ |
| Menu modelov | 2 riadky, frameless + priehľadné (zaoblené rohy), **kurzor ruky `PointingHandCursor` cez `setOverrideCursor`**, po odchode sa override vráti | ✅ |
| Chat na GPU | Qwen 29/29 vrstiev, Gemma 35/35, Mistral 33/33; odpoveď, meta riadok, chat vzniká až s odpoveďou, sidebar radí podľa poslednej zmeny | ✅ |
| Monitor | CPU, GPU % a **tretí riadok VRAM cez NVML** (26 % s Qwenom, 36 % s Gemmou) | ✅ |
| Markdown | blok kódu, tabuľka, Kopírovať vloží kód do schránky | ✅ |
| Stop | ťah vrátený celý, nič v databáze, otázka aj prílohy späť v poli (poradie zachované) | ✅ |
| Skrátená odpoveď | `max_tokens=24` → `finish_reason=length`, 23 tokenov | ✅ |
| Prepnutie chatu | v inom chate Odoslať nedostupné, odpoveď beží ďalej a dobehne; **návrat počas odpovede ju ukáže ďalej** | ✅ |
| Menu ⋯ | počet tokenov, Premenovať + Vymazať, premenovanie „Žltý kôň ťahá voz 🐴 ďžď“, **mazanie iného chatu počas odpovede bez pádu** (oprava 2026-11-09, na PC prvýkrát), vlastný chat počas odpovede odmietnutý | ✅ |
| Vlastnosti | odhad „model + kontext vs voľná VRAM“, easy/expert (spinbox `n_ctx` len v expert), `n_ctx` 2048 → „Neuložené zmeny (1)“ → Použiť → reload pri ďalšej správe, správy sa nezmazali, draft prežije „Fúkni nový chat“ a zahodí sa pri odchode z chatu | ✅ |
| System prompt | prompt naozaj ide do `messages` ako `role: system`; **prázdny prompt system správu neposiela vôbec** | ✅ |
| Seed | ten istý seed dá rovnakú odpoveď od druhej rovnakej požiadavky, iný seed iný text | ✅ / W2 |
| Kontext | pri `n_ctx=512` sa staršie správy vynechávajú (`dropped`), databáza sa nemaže; príliš dlhá otázka → chyba a vrátený ťah | ✅ |
| Prílohy | 8 formátov za 0,47 s, 9 čipov v mriežke s posuvníkom, náhľad, png/binárny/prázdny/skenované PDF odmietnuté, 300-stranové PDF (774 382 znakov) za 10,9 s, samotná príloha ako správa, drag & drop, vypnutie v Nastaveniach skryje tlačidlo | ✅ |
| Web | prepínač v troch úrovniach, skutočné hľadanie (`ddgs` + `primp` na Windows funguje), 3 zdroje vrátane Wikipédie s textom, stavy v bubline, zdroje ako odkazy, klik otvorí adresu, **Gemma cituje `[3]` správne**, globálne vypnutie nemení vlastnosti chatu | ✅ |
| Čiastočný offload a CPU | Gemma 10/35 vrstiev 35,5 tok/s, čisté CPU (8 vlákien) 28,4 tok/s | ✅ |
| Plná VRAM | pri 0,3 GB voľnej VRAM appka varuje („potrebuje 4,9 GB, voľných 0,3 GB“), **model sa aj tak načíta a odpovie** – ovládač Windows preteká VRAM do RAM; po uvoľnení ide Mistral znova na GPU | ✅ / W3 |
| Mazanie modelu | dialóg s textom o zmazaní z disku, **súbor sa zmazal aj keď bol model načítaný cez mmap**, riadok zmizol, engine model nedrží, chat zostal bez modelu | ✅ |
| Natívne dialógy | `QFileDialog` pri prílohe aj pri „Pridať .gguf model…“ – trieda `#32770`, po zrušení sa nič nepripne ani neimportuje | ✅ |
| Témy | dark aj light, zápis do `settings.json`, QSS sa prekreslí | ✅ |
| Reštart | téma, web, posledný model, chaty, správy, prílohy aj ich čipy s id sa zachovali | ✅ |
| Dlhšie používanie | 12 ťahov Gemmy: RSS +31 MB, 81 → 109 tok/s | ✅ |
| Ukončenie | počas odpovede, počas importu (bez `.part`) aj počas hľadania (2,6 s) – kód 0, bez `-wal`/`-shm` | ✅ |
| Tvrdý pád | `taskkill /F` počas odpovede: `-wal` a `-shm` zostali a pri štarte sa zlúčili, `integrity_check` ok, žiadna otázka bez odpovede, rozpísaný ťah chat nevytvoril, appka ďalej normálne odpovedá | ✅ |
| Poškodené nastavenia | prepísané predvolenými s varovaním, chaty zostali | ✅ |
| Neplatný `models_dir` | súbor namiesto priečinka → predvolený priečinok s varovaním, nie fatálne | ✅ / C3 |
| Poškodená databáza | nezmysel aj prepísané stránky v strede (`quick_check`) → „Databáza chatov je poškodená.“ s celou cestou, kód 1, okno nevznikne; súbor sa potom dá premenovať a ďalší štart vyrobí novú prázdnu databázu s vynulovaným `last_model_id` | ✅ |
| Dve inštancie | obe odpovedali, obe zapísali, integrita ok | ✅ / C1 |
| Klávesnica a pole | Shift+Enter vloží `\n` (nie U+2028), pole rastie 24 → 200 px a potom má posuvník, Enter odošle a vyprázdni, po odpovedi je fokus v poli | ✅ |
| Okno | `resize(1,1)` skončí na minime 800 × 560, composer, pole, Odoslať aj pilulka zostávajú viditeľné; dlhé slovo bez medzier okno nerozšíri | ✅ |
| Log a crash log | `fukai.log` s hlavičkou, engine, hardvérom, toastmi s detailom, načítaním modelu a súhrnom odpovede – **bez textov správ a príloh**; `fukai-crash.log` pri `SIGSEGV` zapíše traceback všetkých vlákien aj zoznam rozšírení | ✅ / W4 |

### Namerané hodnoty (PC 1, CUDA)

| Meranie | Windows | Mac (pre porovnanie) |
|---|---|---|
| Štart do zobrazenia okna | 3,27 s | 3,5 s |
| Kroky štartu | nastavenia 1,16 s · engine 0,01 s · hardvér 0,58 s · databáza a modely < 0,01 s (minimálny čas splashu 2 s) | nastavenia 0,06 s · engine 0,2 s |
| Import 1,0 GB / 4,1 GB | 1,0 s / 2,7 s | 0,9 s (1 GB) |
| Qwen 1.5B: načítanie + prvá odpoveď | 1,38 s | 0,8 s načítanie |
| Qwen 1.5B: prvý token v teplom chate / rýchlosť | 0,02 s / 222 tok/s | 0,10 s / 74 tok/s |
| Gemma 4B: prvý token / rýchlosť | 2,22 s / 96,0 tok/s | 2,8 s načítanie / 24 tok/s |
| Mistral 7B: prvý token / rýchlosť | 2,31 s / 75,6 tok/s | – (nezmestí sa) |
| Gemma 10/35 vrstiev na GPU | 35,5 tok/s | – |
| Gemma na CPU (8 P-jadier) | 28,4 tok/s | – |
| VRAM: Gemma model + kontext | 3 609 MB (zo 16 311) | – |
| VRAM: Mistral model + kontext | 5 094 MB | – |
| Otázka s webom (Qwen) | 5,4 s celkom, prvý token 3,9 s | 7,2 s |
| Gemma s webom | 3,6 s celkom, **prvý token 3,1 s** | prvý token 11,5 s |
| Extrakcia 8 príloh | 0,47 s | 0,24 s |
| Extrakcia 300-stranového PDF | 10,9 s (774 382 znakov) | 9,4 s (810 082 znakov) |
| Odozva UI (50 ms časovač, najdlhšia medzera) | 63 ms pri generovaní, 93 ms pri veľkom PDF | 63 ms / 69 ms |
| 12 ťahov za sebou | RSS 3 147 → 3 178 MB (+31 MB), 81 → 109 tok/s | +8 MB, 78 → 70 tok/s |
| Ukončenie | odpoveď < 0,1 s · import < 0,1 s · hľadanie 2,64 s | 0,06 / 0,2 / 1,3 s |
| Dve inštancie (štart + odpoveď) | 5,0 s | – |

### Nálezy

| ID | Nález | Dopad | Návrh | Kedy |
|---|---|---|---|---|
| **W1** | **`.venv` na PC nebol zosúladený s `requirements.txt`: `ddgs` 9.7.1 namiesto 9.16.1.** Skutočné hľadanie padalo na `BuilderError: Invalid impersonate: "safari_16.5"` – presne na pasci z ALMANAC §3. | Celá fáza „web“ by vyzerala ako chyba appky. | Opravené 2026-11-11 (`pip install -r requirements.txt`). Po každom `git pull`, ktorý mení requirements, spustiť inštaláciu na oboch strojoch. | ✅ hotové |
| **W2** | **Seed je reprodukovateľný až od druhej rovnakej požiadavky.** Overené izolovane proti knižnici: ten istý seed trikrát za sebou dá 1 ≠ 2, 2 = 3; striedavé seedy 777/999/777 sú reprodukovateľné; `set_seed()` pred požiadavkou nič nezmení; cudzia požiadavka medzi tým reprodukovateľnosť zruší. Ide o stav KV cache v llama-cpp-python 0.3.36, nie o chybu FUKAI. | Karta Vlastnosti seed nabízí, používateľ môže očakávať, že *prvá* odpoveď s daným seedom bude vždy rovnaká. | Buď nič (vlastnosť knižnice), alebo pri seede dopísať do popisu, že platí pre opakovanú tú istú otázku. | neskôr / dokumentácia |
| **W3** | **`kv_cache_mb()` nepočíta so sliding-window attention.** Pre Gemmu 3 pri `n_ctx` 131072 odhadne 17,0 GB a karta varuje, že sa to nezmestí – llama.cpp však kontext vytvoril a model odpovedal, reálne zabral ~1 GB nad model. Na Windows navyše ovládač (WDDM) preteká VRAM do RAM, takže `InsufficientMemoryError` sa pri priveľkom modeli nevyvolá vôbec (pri 0,3 GB voľnej VRAM sa Mistral načítal a odpovedal). | Odhad odstraší od kontextu, ktorý by fungoval. Varovanie je pravdivé len pre modely bez SWA. | Pri modeloch so SWA (Gemma 3) počítať KV cache len pre globálne vrstvy, alebo odhad označiť ako horný strop. | neskôr |
| **W4** | **`fukai-crash.log` drží appka otvorený celý beh**, takže sa na Windows nedá zmazať ani premenovať, kým FUKAI beží (`WinError 32`). Súbor sa len dopĺňa (append), nerotuje. | Kozmetika; pri dlhom používaní môže rásť. | Nechať tak, alebo pri štarte súbor skrátiť, keď presiahne napríklad 1 MB. | neskôr |
| **W5** | **Self-test `core.gguf` na Windows padá na poslednej kontrole.** `read_header()` nad adresárom tam vyhodí `PermissionError` (nie `IsADirectoryError` ako na macOS), takže z neho vyjde `ModelError` a test čaká `ModelNotFoundError` → `python -m core.gguf` končí kódom 1 s tracebackom. V appke je tá cesta zavretá: `ModelLibrary.scan_folder()` filtruje `path.is_file()`, takže priečinok s menom `*.gguf` sa ignoruje. | Chyba je v self-teste modulu, nie v appke; na Macu self-test prejde, na Windows nie. | V `read_header()` chytiť aj `PermissionError` nad adresárom, alebo kontrolu v self-teste podmieniť platformou. | neskôr |

Nálezy A1–A4 a B1–B4 sú na Windows **overené** (nižšie), C1–C6 z macovského testu platia aj tu a nepribudol k nim nový dopad.

### Overenie opráv z 2026-11-11 na Windows

| ID | Ako sa overila | Výsledok |
|---|---|---|
| A1 | 9 príloh v bare: všetkých 9 čipov je v mriežke (3 riadky), bar vysoký 58 px proti obsahu 90 px (teda posuvník, najviac 2 riadky), `focusPolicy = NoFocus`, poradie 5 príloh po Stope zachované | ✅ |
| A2 | chat s blokom kódu, tabuľkou a 8 čipmi pri šírkach okna 1400 → 1000 → 800 → 1400: stĺpec 760 → 634 → 438 → 760 px, **0 pretečených widgetov** v každej šírke, aj keď sa chat otvorí až v úzkom okne | ✅ |
| A3 | výnimka v slote hlavného vlákna, v `QThread` a v `threading.Thread` → chybový toast s cestou k logu, traceback v logu, appka beží a ďalej odpovedá; 20 výnimiek naraz = 1 toast a 60 záznamov v logu | ✅ |
| A4 | `fukai.log` (59 832 znakov): hlavička behu s verziami, engine, hardvér, toasty s `detail`, načítanie modelu, súhrn odpovede s tok/s – **text otázky ani prílohy v ňom nie sú**; `fukai-crash.log` pri `SIGSEGV` zapísal traceback aj zoznam rozšírení | ✅ |
| B1 | čipy práve odoslanej otázky dostali id z databázy (`[2…9]`) a klik na prvý otvoril náhľad s textom prílohy („Text prílohy · poznamky.txt · 177 znakov · ~44 tokenov“) | ✅ |
| B2 | `fukai.db` ako nezmysel aj s prepísanými stránkami v strede → „Databáza chatov je poškodená.“ s celou cestou, `run()` vráti 1, okno nevznikne; súbor sa potom dá premenovať a ďalší štart vyrobí novú databázu | ✅ |
| B3 | stavy v bubline pri webe: „Hľadám na webe…“ (0,02 s) → „Čítam 3 stránky…“ (1,7 s) → „Spracúvam zdroje…“ (3,17 s) → zmizne prvým tokenom; pri prílohách „Spracúvam prílohy…“ a po dobehnutí odpovede je stav skrytý | ✅ |
| B4 | samotné `velky.pdf` (774 382 znakov) sa odoslalo, uložilo sa 7 189 znakov poslaného textu a toast povedal, že sa orezalo; 8 príloh pri `n_ctx` 4096 odišlo celých (na CUDA sa zmestili všetky), žiadna sa nevynechala, model z nich odpovedal „ZELENÝ JAVOR“; Stop vrátil všetky prílohy v pôvodnom poradí | ✅ |

### Overené na Windows prvýkrát

Body, ktoré ALMANAC §8.4 vedie ako neoverené, test uzavrel:

- **Oprava pádu pri mazaní chatu počas odpovede** (menu ⋯) – appka nespadla, chat sa zmazal, odpoveď v druhom chate dobehla.
- **Kúsky 7–13 na Windows** – monitor s NVML, Nastavenia, Vlastnosti, info o modeli, menu ⋯, prílohy aj web.
- **Plná VRAM** – appka varuje a žije; na Windows sa `InsufficientMemoryError` nevyvolá, lebo ovládač preteká do RAM (W3).
- **Zmazanie práve načítaného modelu** – `mmap` zmazaniu súboru nebráni, poradie pamäť → súbor → riadok funguje.
- **Priebeh importu nad 2 GiB** – Mistral 4,1 GB, `qint64` nepretieklo.
- **Natívne dialógy `#32770`** a **kurzor ruky v menu modelov** (`GetCursorInfo` + `overrideCursor`).
- **Ikona na paneli úloh** a `AppUserModelID`.

### Čo test neoveril (treba ručne)

- **Výber súboru v natívnom dialógu** – test dialóg otvorí a zruší, ale súbor v ňom nevyberie (cesta za dialógom je overená volaním `import_model` / `add_attachments`).
- **Skutočné otvorenie prehliadača a Priečinka** – adresa sa zachytáva cez `QDesktopServices.setUrlHandler`, okná sa neotvárali.
- **Uspanie a prebudenie počas generovania, odpojenie siete počas hľadania.**
- **Vizuálna kontrola tmavej témy a rozostupov** – overené len programovo (téma sa prepne a zapíše, QSS sa prekreslí).
- **Qwen 3 `<think>` a Llama 3 `strftime_now`** – modely neboli k dispozícii.

### Pasce testovacích skriptov na Windows

Zistené pri písaní tohto testu; na Macu sa neprejavili:

- **`QTest.keyClicks` zvládne len ASCII.** Na diakritike Qt spadne assertom (`qasciikey.cpp:192`) a **zhodí celý proces**. Diakritiku vkladať cez `setPlainText`.
- **`QT_QPA_PLATFORM=offscreen` pokazí PDF z Qt.** `QPdfWriter` bez natívneho font enginu vysádza text ako krivky, PDF nemá fonty a `pypdf` z neho nevytiahne nič. Testovacie PDF generovať na platforme `windows`.
- **`int(QtEnum)` v PyQt6 padá na `TypeError`** (`QMessageBox.icon()`, `QCursor.shape()`) – treba `.value` alebo `.name`.
- **`QMenu.exec()` vráti akciu len pri klávesovej voľbe.** `action.trigger()` ju nevráti, takže sidebar (ktorý sa rozhoduje podľa návratovej hodnoty) nič neurobí. V teste: `Key_Down` kým `activeAction()` nie je tá správna, potom `Key_Return`.
- **`QDesktopServices.setUrlHandler` s lambdou nefunguje** – prijímateľ musí byť živý `QObject` so slotom, inak sa zahodí a adresa skutočne otvorí prehliadač.
- **`QDropEvent` chce `QPointF`**, `QDragEnterEvent` prijme aj `QPoint`.
- **Testovací domov v `%TEMP%` má krátku cestu (`LUKASV~1`)**, ale `app_dir()` robí `.resolve()` – cesty porovnávať až po `resolve()`.
- **Výnimka v testovacom slote sa stratí v appke.** Vďaka A3 ju appka premení na toast a záznam v logu, takže test „len nefunguje“ – pri nejasnom zlyhaní čítať `fukai.log`.
- **Vlastný `fukai-crash.log` sa nedá zmazať, kým appka beží** (W4) – merať prírastok veľkosti.
