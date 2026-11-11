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

## WINDOWS – PC 1 (čaká na test)

Postup, parametre a techniky sú v ALMANAC §8.3, rovnaké ako na Macu; testovacie skripty z Macu na PC nie sú, treba ich napísať podľa §8.3. Prostredie podľa ALMANAC §4: Core Ultra 7 265K, RTX 5060 Ti 16 GB, 32 GB RAM, CUDA Toolkit 13.0. Modely: Qwen 2.5 1.5B Q4_0, Gemma 3 4B Q4_K_M a pre GPU aj Mistral 7B Q4_K_M. Kód: commit s opravami z 2026-11-11.

Po teste sem zapíš rovnaké tabuľky ako v sekcii MAC (prostredie, výsledky podľa oblastí, merania, nálezy). Opravy A1–A4 a B1–B4 sú hotové – na PC ich treba **overiť** (riadky „Overenie opráv“), nie hľadať znova.

| Oblasť | Výsledok |
|---|---|
| **Fázy ako na Macu** | |
| P0 – ostrý `%LOCALAPPDATA%\FUKAI`: štart, zatvorenie, vznikne `fukai.log` s hlavičkou | |
| Štart, detekcia (`backend=cuda`, 8 P-jadier), čip, ikona na paneli úloh | |
| Prvé spustenie na prázdnom domove | |
| Import (Gemma 2,3 GB, priebeh nad 2 GiB s Mistralom), duplikát, `mmproj`, falošný `.gguf`, zrušenie, natívny dialóg `#32770` | |
| Sken priečinka, Nastavenia, info o modeli, Otvoriť priečinok | |
| Menu modelov (rohy, kurzor `GetCursorInfo`) | |
| Chat: Qwen, Gemma a Mistral na GPU (načítanie, prvý token, tok/s, VRAM spolu) | |
| Markdown (kód, tabuľka), Kopírovať | |
| Stop, skrátená odpoveď, prepnutie chatu počas odpovede | |
| Menu ⋯: premenovanie, mazanie, **mazanie iného chatu počas odpovede** (oprava z 2026-11-09, na PC prvýkrát) | |
| Vlastnosti: `n_ctx` cez UI → reload, seed, draft | |
| Kontext: `dropped`, príliš dlhá otázka | |
| Prílohy: 8 formátov, chyby, veľké PDF, len príloha, drag & drop | |
| Web: prepínač, hľadanie (ddgs/primp na Windows, Wikipédia s textom), zdroje, klik na zdroj, Gemma cituje | |
| Monitor: GPU % a VRAM (NVML) počas odpovede | |
| Mazanie **načítaného** modelu (mmap) | |
| Plná VRAM: veľký `n_ctx` / veľký model → varovanie alebo `InsufficientMemoryError`, appka žije | |
| Reštart: zachované nastavenia a dáta, 12 ťahov a pamäť | |
| Ukončenie počas odpovede, importu a hľadania | |
| Tvrdý pád (`taskkill /F /PID`) a štart po ňom | |
| Poškodené nastavenia, neplatný priečinok modelov | |
| Dve inštancie naraz | |
| Klávesnica, pole, drag & drop | |
| **Overenie opráv z 2026-11-11** | |
| A1 – 9 príloh: posuvník, najviac 2 riadky, všetky čipy dosiahnuteľné, poradie po Stope | |
| A2 – chat s kódom, tabuľkou a 8 čipmi: okno 1400 → 1000 → najmenšie a späť, nič nepretečie; chat otvorený až v úzkom okne | |
| A3 – výnimka v slote hlavného vlákna, v `QThread` a v `threading.Thread` → chybový toast s cestou k logu, appka beží, 20 výnimok = 1 toast; neočakávaná chyba pri štarte → fatálny dialóg, kód 1 | |
| A4 – `fukai.log` (hlavička, toasty s `detail`, načítanie modelu, súhrn odpovede, **bez textov správ**), rotácia, `fukai-crash.log` vznikne | |
| B1 – klik na čip práve odoslanej otázky otvorí náhľad | |
| B2 – `fukai.db` = nezmysel a s prepísanými stránkami → „Databáza chatov je poškodená.“ s cestou, kód 1; po zatvorení sa súbor dá premenovať; priečinok bez práv → pôvodná rada; klik na nečitateľný chat → toast, správa ide do zobrazeného chatu | |
| B3 – stav „Spracúvam zdroje…“ / „Spracúvam prílohy…“ do prvého tokenu (na CUDA krátko) | |
| B4 – 8 príloh vrátane `zmluva.pdf` pri `n_ctx` 4096: odíde, orezaná len zmluva, toast; samotné `velky.pdf`; Stop vráti celú prílohu | |
