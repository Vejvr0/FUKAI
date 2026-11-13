# FUKAI – denník sessions

Chronologický záznam práce, skrátený 2026-11-11. **Rozhodnutia a stav projektu patria do `ALMANAC.md`**, výsledky testov do `APPTEST.md`. Plné znenie denníka do 2026-11-11 (tabuľky chýb, matica testu na PC 1, zoznamy preklepov z prepisov) je v `archiv/SESSIONS-2026-11-11.md`.

---

**2026-10-27/28 – errors, hardware, wheels.** Requirements v troch súboroch, `core/errors.py` (chyby podľa príčiny, `message`/`hint`/`detail`, `Notice`), `core/hardware.py` (detekcia nikdy nevyhodí výnimku, P-jadrá). Prechod z wheelov `dougeeai` 0.3.20 na oficiálne indexy 0.3.36. Prostredie PC 1: PowerShell `&&`, `set` vs `$env:`, `py` vs `.venv`, Git Bash a lomka.

**2026-10-28 – CUDA rozbehaná.** Build zo zdrojákov bol ticho CPU-only (`set CMAKE_ARGS` v PowerShelli) → oficiálny CUDA wheel: `sm_120` áno, cuBLAS nie (Toolkit potrebný). Prvá verzia `settings.py` a `llm_engine.py`, jednorazový warm-up 21 s.

**2026-10-28/29 – úložisko.** Dve úložiská (JSON pred databázou, inak SQLite), jeden `app_dir()` cez platformdirs, `FUKAI_HOME`, schéma `chats 1:N content`, `Database` s migráciami. Spôsob práce po malých kusoch (autor píše, Claude navrhuje a kontroluje).

**2026-10-30 – MacBook.** Metal wheel 0.3.36 poškodený → build zo zdrojákov. `settings.py` pre engine, `llm_engine.py` od nuly (kúsky 1–3).

**2026-10-31 – engine hotový.** Kúsky 4–8: tokenizácia, `stream()`, Stop cez `Event`, `FinishReason`, pamäť a preklad chýb podľa fázy, `free_ram_mb()` cez `vm_stat`. Overené aj na Qwene. Rozhodnutie: Stop vráti celý ťah.

**2026-11-01 – PC 1.** Engine na Mistrale 7B (33/33 vrstiev, 67 tok/s). `settings.py` dokončený (`ChatProperties`, `ModelMeta`), `app_settings.py` (atomický zápis). O reloade rozhoduje volajúci.

**2026-11-02 – `context.py` (PC 1) a štart appky (Mac).** Orezávanie histórie, odhady overené proti `prompt eval`. Logo, ikony, splash, `Application`, `check_ram` ako varovanie.

**2026-11-02/03 – toasty, šablóna UI, kostra okna a témy.** Šablóna z OneDrive záväzná, `THEMES` + QSS šablóna, Windows ikona na dlaždici.

**2026-11-03/04 – Fusion, worker, tok správy.** `setStyle("Fusion")` namiesto rozostupov podľa OS, `LlmService` + `LlmWorker`, `ChatController` (lazy načítanie, zápis ťahu jednou transakciou).

**2026-11-04 – composer a výber modelu (5a).** `Composer`, `SettingsStore`, `ModelLibrary`, menu modelov s `QWidgetAction`.

**2026-11-05 – `.gguf`, sken, import (5b, 5c-1, 5c-2).** Vlastný čítač hlavičky, sken priečinka pri štarte (podnet: zmazaná databáza), import cez `.part` vo vlastnom vlákne s priebehom a zrušením.

**2026-11-06 – mazanie modelu, zoznam správ, notebook, PC 1.** Mazanie (pamäť → súbor → riadok), kurzor v `QMenu` cez override. Kúsok 6a (bubliny, streamovanie, scroll). Notebook: `pyqtSignal(int)` pretiekol pri 2 GiB → `qint64`; engine sa zisťuje pri štarte (`probe_engine`). **PC 1 – kompletný test appky v živom okne: bez chyby v kóde** (Gemma 107, Mistral 77 tok/s), zistené stlmenie fd pri načítaní modelu. Kúsok 6b – markdown po častiach.

**2026-11-07 – PC 1: menu ⋯ (3b), monitor (7), Nastavenia (8).**

**2026-11-08 – PC 1: Vlastnosti (9), info o modeli (10), prílohy (krok 12).** Draft vlastností prežije „Fúkni nový chat“. Prílohy: schéma v2, extrakcia vo vlákne, čipy, orezanie na kontext. Autor hlásil pád pri mazaní chatu počas odpovede.

**2026-11-09 – Mac.** Pád v menu ⋯ nájdený (widget zachytený pred `menu.exec()` zmazaný prestavbou) a opravený. Krok 12e (čipy pri správach). **Krok 13 – web** (13a–13e): `ddgs` + `trafilatura`, hľadanie súbežne s načítaním modelu, zdroje do promptu (varianta A), čip, stav, zdroje pod odpoveďou, sticky prepínač. **Veľký test celej appky na Macu** (`APPTEST.md`): 97/109, appka ani raz nespadla, nálezy A1–A4, B1–B3, C1–C6.

**2026-11-10 – plán do v1** (rozhodnutie autora): opravy A a B → commit → test na PC 1 → balenie.

**2026-11-11 – Mac: opravy z veľkého testu.** Všetko podľa postupu „Claude navrhne a otestuje v scratchpade (`a1`, `b1`, `b2`, `b3`, `a34`, `b4`, `a2`), autor prepíše, Claude skontroluje a spustí testy nad repom“; B3, A3/A4 a A2 prepísal do repa Claude na žiadosť autora.
- **A1** bar príloh ako `QScrollArea` s 2 riadkami (+ poradie po Stope, pretečenie čipu, zaokrúhlenie `horizontalAdvance`, fokus).
- **B1** id príloh z `add_turn` k čipom; druhá príčina nepripojený `preview_requested` v `begin_turn`. Prepis: 3 chyby (`toolTip`, `json.dumbs`, zmiznutý `UPDATE updated_at`).
- **B2** `DatabaseCorruptError` + `quick_check` (autor: len pravdivá správa); popri tom pád pri kliknutí na nečitateľný chat a `open_chat` meniaci stav pred čítaním.
- **B3** stav „Spracúvam zdroje/prílohy…“ (bez neho 12–33 s prázdna bublina), `web_progress` → `turn_status`.
- **A3 + A4** log (`core/log.py` napísal autor po kontrole prvej verzie) a `excepthook` s toastom (autor: appka beží ďalej).
- **B4** (nový nález pri overení A1: odhad tokenov príloh 2× nízky) – orezanie príloh pri zostavení promptu, správa odíde vždy (autor).
- **A2** stĺpec správ `Ignored` + zalamovanie čipov v histórii.
- Regresia celého dňa nad repom prechádza. ALMANAC a SESSIONS skrátené, plné znenie v `archiv/`. WINDOWS sekcia `APPTEST.md` a §8.3 doplnené o overenie opráv.

**2026-11-11 – PC 1: veľký test Windows verzie.** Kód bez zmeny (commit `46963e7`), testovalo sa, nie prepisovalo. Najprv prostredie: self-testy jadra prechádzajú, `probe_engine` 0.3.36 s CUDA, detekcia `backend=cuda` a 8 P-jadier – ale **venv zostal na `ddgs` 9.7.1** a web padal na `Invalid impersonate` (W1, opravené `pip install -r requirements.txt`). Doplnené chýbajúce testovacie dáta: stiahnutý Qwen 2.5 1.5B Q4_0, syntetické neplatné modely (`clip`, textový `.gguf`, bez chat template) a 14 príloh vrátane `zmluva.pdf` (2 strany, 5 571 znakov) a `velky.pdf` (300 strán, 773 784 znakov).
- **17 fáz, 445 kontrol, všetky OK, žiadna chyba appky** (`APPTEST.md` → WINDOWS). Testy spúšťajú skutočné `Application.run()` a kroky vkladajú do jeho smyčky, telo `run()` sa nekopíruje.
- Overené opravy A1–A4 a B1–B4; na PC prvýkrát aj mazanie chatu počas odpovede, plná VRAM, mazanie načítaného modelu pod `mmap`, natívne dialógy `#32770`, kurzor v menu, NVML, ikona na paneli úloh, priebeh importu nad 2 GiB.
- Nálezy mimo appky: **W2** seed je reprodukovateľný až od druhej rovnakej požiadavky (overené izolovane proti llama-cpp-python), **W3** `kv_cache_mb()` nepočíta so sliding-window attention (Gemma 3: odhad 17 GB proti ~1 GB skutočne) a na Windows ovládač preteká VRAM do RAM, takže `InsufficientMemoryError` z VRAM nenastane, **W4** `fukai-crash.log` sa drží otvorený a len dopĺňa.
- Pasce testov na Windows do §8.2: `QTest.keyClicks` zvládne len ASCII (na diakritike Qt assert zhodí proces), `int(QtEnum)` padá, `QMenu.exec()` vráti akciu len pri klávesovej voľbe, `setUrlHandler` s lambdou nefunguje, `offscreen` pokazí PDF z `QPdfWriter`.
- Výkon proti Macu: Qwen 222 tok/s (Mac 74), Gemma 96 (24), Mistral 75,6 (nezmestí sa), Gemma s webom prvý token 3,1 s (11,5 s), 12 ťahov RSS +31 MB.
- Testovacie skripty (kostra `harness.py` + 17 fáz + generátor dát) zostali v scratchpade session, ako na Macu – v repe nie sú. Pri ďalšom teste sa píšu znova podľa §8.3; pasce, ktoré to stálo, sú už v §8.2.
- Nezmeraný zostal čistý RAM profil: cudzí proces `javaw` držal 13,5 GB a systém bol na 94,5 %.

**2026-11-12 – Mac: výsledok testu na PC a návrh balenia.** Test Windows prešiel 445/445 bez chyby appky (nálezy W1–W5 mimo appky). Rozhodnutia autora ku kroku 14: **inštalačka zostaví prostredie pri inštalácii cez `uv`** (nie PyInstaller), Windows C# inštalačka pre používateľa bez admina, macOS `.pkg`. Overené na PyPI: `nvidia-cublas` 13.0.2.14 a `nvidia-cuda-runtime` 13.0.96 pre `win_amd64` existujú → CUDA bez Toolkitu cez pip. Pripomienky k diagramu autora (dva druhy nekompatibility CUDA, zlyhanie testu backendu, bez internetu) v ALMANAC §10.

Zadanie prieskumu pre PC poslané cez OneDrive (`semestralka/TODO.md`), bez commitu.

**2026-11-12 – PC 1: prieskum ku kroku 14** (výsledky `semestralka/TODO-vysledky-PC.md`, repo bez zmeny). CUDA bez Toolkitu cez `uv` + pip balíky NVIDIA funguje (Gemma 114,7 tok/s, appka 95 tok/s). Zistené: cuBLAS musí byť v `PATH` (nie `add_dll_directory`), wheel vyžaduje AVX2, CUDA od compute capability 7.5 a ovládača 580, warm-up je JIT z PTX (`ComputeCache` existuje), `nvcudart_hybrid64.dll` je z ovládača, VC++ runtime je jediná systémová závislosť, prostredie nie je presunuteľné. Na Macu prenesené do ALMANAC §3, §8.2, §10.

**2026-11-12 – Mac: cuBLAS z prostredia appky.** `_add_nvidia_dlls()` pred importom `llama_cpp` (návrh a test `scratchpad/path`, prepis autor). V prepise `sysconfig.get_path()` namiesto `get_paths()` – na Macu neviditeľné, na každom Windows by appka nenaštartovala (`TypeError` mimo zachytávaných výnimiek); opravené, test nad repom 12/12 (podvrhnutý `win32`, skutočný `probe_engine` na Macu). Skutočná CUDA bez Toolkitu sa overí pri teste inštalačky na PC.

Rozhodnutie autora: VC++ runtime pribalí Windows inštalačka (app-local).

Rady pri chybe enginu prepísal autor pre používateľa (preinštalovať FUKAI, nie Toolkit / requirements). Každý fatálny dialóg pri štarte má za radou cestu k logu (overené naživo: poškodená databáza, neočakávaná chyba, chyba DLL enginu, bez logu).

**2026-11-12 – Mac: príprava balíkov pre inštalačky** (autor po krokoch s návodom, Claude skúšal najprv v scratchpade a kontroloval).
- Rozhodnutia autora: všetky tri wheely llama-cpp-python vo vlastnom verejnom repe na vydania (CPU a CUDA oficiálne bez zmeny, Metal vlastný), inštalačky ich sťahujú; minimum macOS 14; všetko na balenie v `dist/`.
- **Metal wheel** postavený s `MACOSX_DEPLOYMENT_TARGET=14.0` a `GGML_NATIVE=OFF` (build v `.venv` mal `minos 26.0` a inštrukcie M2 – na M1 by spadol). Rozdiel proti natívnemu buildu do 5 %. Prostredie cez `uv` 0.13.7 z wheelu bez kompilácie, appka z neho beží na Metale aj po zmazaní cache.
- **`dist/manifest.json`, `dist/make_locks.py`, zámky pre tri backendy** (verzie a hashe všetkých balíkov z PyPI), `requirements-llama-*.txt` zrušené. Inštalácia zo zámku s `--require-hashes` overená, aj odmietnutie pokazeného hashu.
- **`hw.json` a `check_gpu`:** minimum macOS 14, compute capability 7.5 namiesto mapy architektúr, rady pre používateľa. V prepise dve chyby, ktoré by sa na Macu neukázali (`TypeError` pri každej NVIDIA karte, preklep kľúča vypínajúci všetky kontroly) – opravené.

**2026-11-13 – vydania wheelov.** Repo FUKAI zverejnené (autor) namiesto samostatného repa na vydania; kontrola histórie: bez tajomstiev, veľkých súborov a lokálnych ciest, viditeľný je len e-mail autora (commity, `archiv/ALMANAC-2026-11-11.md`). Tri vydania wheelov hotové, stiahnutie bez prihlásenia overené, `releases` v manifeste doplnené.

**2026-11-13 – Mac: spúšťač, upratanie, licencia.** Rozhodnutia autora: inštalácia do `/Applications` (A), spúšťač v C, `sk.vavro.fukai`, GPL-3.0-or-later, verzia 1.0. Skúšobný `FUKAI.app` v scratchpade: spúšťač načíta `libpython` do vlastného procesu → menu a Dock „FUKAI“ (overené autorom), prostredie a Metal z bundlu, natívne okno pri chýbajúcom prostredí (overené autorom), obnova okien po páde sa nezopakovala. Autor upratal komentáre a zmazal self-testy vo všetkých moduloch; AST porovnanie: kód bez zmeny, regresia (appka so správou, `PATH`, fatálne dialógy) prechádza. `LICENSE` (oficiálny text GPL v3) a `THIRD_PARTY_LICENSES.md` (vygenerované zo zámku).

**Ďalej:** commit (upratanie + licencia) → prepis `launcher.c` a `Info.plist` do `dist/mac_app_installer/` → `provision.sh` → `build_pkg.sh` → test `.pkg`; potom C# inštalačka.
