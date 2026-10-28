# FUKAI – Almanac

Zdieľaná pamäť projektu pre Claude Code na všetkých strojoch (Mac aj PC). Sem patria rozhodnutia, obmedzenia a kontext, ktorý sa nedá vyčítať z kódu. Pri zmene rozhodnutia prepíš príslušnú sekciu, nepridávaj protichodné záznamy. Posledná revízia: 2026-10-28.

## 1. Projekt

- **FUKAI** = Fakultná Univerzálna Kognitívna AI. Univerzitný projekt (Žilinská univerzita), autor Lukáš Vavro.
- Desktopová aplikácia na chat s lokálnymi LLM (štýl Ollama / LM Studio), crossplatform Windows + macOS.
- Repo: https://github.com/Vejvr0/FUKAI (súkromné). Kód sa synchronizuje **iba cez Git**, nie cez OneDrive (ten je len na dokumenty/návrhy).
- Logo: štvorcové 1:1, profesionálne logo v .png formáte. Zatiaľ nie je v repe → patrí do `assets/` (+ `.ico` pre Windows, `.icns` pre Mac).
- SpashScreen: ilustrácia baču s ovečkou, kde je nápis FUKAI s popisom chat ktorý to fúka. áno prechádzame na Zatiaľ nie je v repe → patrí do `assets/` 

## 2. Funkcie (rozsah)

1. Chat so streamovanou odpoveďou, tlačidlo Stop.
2. Ukladanie chatov (zoznam v sidebare, premenovanie, mazanie).
3. Prílohy: txt/md/csv/json/kód, PDF, xlsx, docx. Bez OCR.
4. Webové vyhľadávanie ako rozšírenie (prepínač pri správe).
5. Výber `.gguf` modelu a parametre per chat: max tokens, context length, temperature, repeat penalty, top_p/top_k, CPU vs GPU podľa detegovaného HW.

## 3. Stack (zafixované)

| Komponent | Verzia | Poznámka |
|---|---|---|
| Python | 3.12.10 | `.venv` v koreni projektu, v `.gitignore`, na každom OS vlastné |
| PyQt6 | 6.11.0 | licencia GPL v3 – pre univerzitný projekt OK |
| llama-cpp-python | **0.3.36** | rovnaká verzia na oboch OS. Zmenené 2026-10-28 z 0.3.20 – dôvody v §10.1 |

Závislosti sú pinované v **troch** súboroch – `llama-cpp-python` je zámerne mimo hlavného, lebo jediný je platformovo aj GPU-architektúrne špecifický:

- `requirements.txt` – spoločné pre oba OS (PyQt6, psutil, platformdirs, nvidia-ml-py, Pygments + závislosti pre prílohy a web, ktoré prídu v krokoch 5–6).
- `requirements-llama-win-cuda.txt` – Windows CUDA wheel, **jeden pre všetky NVIDIA karty**.
- `requirements-llama-mac.txt` – macOS Apple Silicon, Metal wheel.

**Od 2026-10-28 berieme wheels z oficiálnych indexov autora knižnice (`abetlen`), nie od tretej strany.** PyPI samo CUDA ani Metal build nemá, ale autor ich hostuje zvlášť:

| Varianta | Index | Wheel |
|---|---|---|
| Windows CUDA 13.0 | `.../whl/cu130` | `v0.3.36-cu130/...win_amd64.whl` (218 MB) |
| Windows CPU | `.../whl/cpu` | `v0.3.36/...win_amd64.whl` |
| macOS Metal (arm64) | `.../whl/metal` | `v0.3.36-metal/...macosx_11_0_arm64.whl` |

Základ URL: `https://abetlen.github.io/llama-cpp-python/whl/<varianta>`.

Dôsledky oproti pôvodnému stavu:

- **Padá matica 4 architektúr** zo §3.1 – oficiálny CUDA wheel nemá `sm` v názve a je jeden pre RTX 20xx–50xx. Tabuľka compute capability v §3.1 a vo `vars/hw.json` zostáva užitočná na diagnostiku a hlásenia, ale wheel sa už podľa nej nevyberá.
- **Na macOS netreba build zo zdrojákov** – teda ani Xcode Command Line Tools, ani cmake.
- **CPU a CUDA sú na tej istej verzii** (0.3.36), čo pôvodný pin 0.3.20 neumožňoval.
- Pri prechode treba **preinštalovať aj MacBook** na 0.3.36, aby vetvy nebežali na rôznych llama.cpp.

**Neoverené:** či CUDA wheel obsahuje `sm_120` (Blackwell, PC 1) a či stále vyžaduje nainštalovaný CUDA Toolkit (`cublas64_13.dll`), alebo nesie cuBLAS v sebe. Zistí sa pri prvej inštalácii.

### 3.1 CUDA wheels – ako to naozaj funguje (overené 2026-10-27)

> **Platnosť:** táto sekcia opisuje wheels od `dougeeai`, ktoré sme používali do 2026-10-28. Od prechodu na oficiálne wheels 0.3.36 (§10.1) sa **wheel podľa architektúry nevyberá** – oficiálny je jeden pre všetky NVIDIA karty. Tabuľka compute capability nižšie zostáva užitočná na **diagnostiku a hlásenia** používateľovi (`core/hardware.py`, `vars/hw.json`), nie na výber balíka.

Pôvodná otvorená otázka bola o „spätnej kompatibilite CUDA 13.0 → 12.8“. Tá sa **vôbec nerieši** – wheels od tretej strany boli vydávané **zvlášť pre každú GPU architektúru**. Pre `0.3.20 + CUDA 13.0 + win_amd64` existovali:

| Wheel | Architektúra | Karty |
|---|---|---|
| `...cuda13.0.sm100.sm120.blackwell...` | sm_100 + sm_120 | RTX 50XX |
| `...cuda13.0.sm89.ada...` | sm_89 | RTX 40XX |
| `...cuda13.0.sm86.ampere...` | sm_86 | RTX 30XX |
| `...cuda13.0.sm75.turing...` | sm_75 | RTX 20XX, GTX 16XX |

**Pozor na dve nezávislé čísla, ktoré sa ľahko zmiešajú:**

| Číslo | Čo je to | PC 1 |
|---|---|---|
| **CUDA verzia** | verzia softvéru (ovládač, toolkit) | UMD 13.4, toolkit 13.0 |
| **Compute capability** | generácia čipu, teda hardvér | 12.0 = `sm_120` = Blackwell |

Compute capability je vlastnosť kremíka a aktualizáciou ovládača sa **nikdy nezmení**. Wheel sa vyberá podľa nej, nie podľa verzie CUDA – musí byť skompilovaný pre danú `sm_`, inak sa karta nepoužije ani s najnovším toolkitom. `nvidia-smi --query-gpu=compute_cap` ju vráti priamo (`12.0`), takže sa dá použiť ako kľúč do tabuľky bez parsovania.

- Všetky sú `py3-none-win_amd64`, teda **nezávislé od verzie Pythonu** (3.10–3.13). Dôvod: llama-cpp-python volá `llama.dll` cez `ctypes`, nie je to C extension. Pri prechode na inú verziu Pythonu sa wheel meniť nemusí.
- Dôsledok pre PC 2 (RTX 4080): netreba nič testovať, stačí odkomentovať `sm89` riadok.
- Wheel má cca 300 MB.
- Pre staršiu vetvu 0.3.16 existujú aj CUDA 12.1 a 11.8 wheels – relevantné, ak by niekto nemal Toolkit 13.0.

## 4. Vývojový hardvér

| Stroj | CPU | GPU / VRAM | RAM | Backend |
|---|---|---|---|---|
| MacBook | Apple M2 (4P + 4E) | integrovaná, zdieľaná pamäť | **8 GB unified** | Metal – `core/hardware.py` *overené 2026-10-28* |
| PC 1 | Intel Core Ultra 7 265K (8P + 12E, bez HT) | RTX 5060 Ti **16 GB** (Blackwell, sm_120) | 32 GB | CUDA Toolkit 13.0, driver 617.42 – *overené 2026-10-27* |
| PC 2 | – | RTX 4080 16 GB (Ada, sm_89) | – | CUDA, wheel `sm89` (pozri §3.1) |

Dôsledky pre návrh:

- **Mac 8 GB je najslabší článok.** macOS si berie ~3 GB, prakticky ~4–5 GB pre model + KV cache → modely do ~3–4B (Q4), 7–8B Q4 len na hrane s malým `n_ctx`. Aplikácia musí pred načítaním odhadnúť pamäť a varovať.
- **Rozhodnuté 2026-10-28: samostatný „rozpočet pamäte“ v `hardware.py` sa nerobí.** Stačí `ram_available_mb` z profilu a orientačné porovnanie s veľkosťou `.gguf` priamo v `llm_engine`, s `Notice` pri nedostatku. Na Macu je `ram_available_mb` aj tak jediné správne číslo, lebo GPU berie z tej istej pamäte. **Pozor:** `ram_available_mb` (aj `gpu.vram_free_mb`) sa merajú raz pri `detect()`, takže pred načítaním modelu si `llm_engine` musí spraviť **nové** meranie – hodnota z času štartu appky je už neplatná.
- Pri každom PC overiť, že `n_gpu_layers=-1` reálne beží na GPU (log llama.cpp / `nvidia-smi`).
- **Oba stroje majú P- a E-jadrá, takže `cores_physical` je na `n_threads` zlá hodnota na oboch.** 265K: `psutil` vráti 20, správne je 8. M2: vráti 8, správne sú 4. `psutil` P a E nerozlíši (na 265K nie je ani HyperThreading, takže fyzické = logické = 20).
  Vyriešené v `core/hardware.py` ako `_performance_cores()`, hodnota je v profile ako `cores_performance` a vystupuje ako `n_threads`:
  - **Windows** – `GetLogicalProcessorInformationEx` cez `ctypes`, počítajú sa jadrá s najvyšším `EfficiencyClass`. *Overené na PC 1 (2026-10-28): `{trieda 1: 8 jadier, trieda 0: 12}` → 8 P-jadier.* Pozor: P a E jadrá sú v zozname **premiešané** (jadro 0,1 = P, jadro 2 = E), takže „vezmi prvých N“ nefunguje. Záznamy majú premenlivú dĺžku, treba ju čítať z každého záznamu zvlášť.
  - **macOS** – `sysctl -n hw.perflevel0.physicalcpu`. *Zatiaľ neoverené na reálnom Macu.*
  - **Inde / pri zlyhaní sondy** – fallback na `cores_physical`, appka beží ďalej s menej optimálnou hodnotou.
  - Hodnota musí zostať v UI nastaviteľná.

### 4.1 Testovacie modely

Na PC 1 sú lokálne dostupné (mimo repa, **nekopírovať** do projektu):

- `../llama-chatbot/models/gemma-3-4b-it-Q4_K_M.gguf` – malý, na rýchle testy, zmestí sa aj na Mac.
- `../llama-chatbot/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` – väčší, na test GPU offloadu.
- `../llama/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` – duplikát toho istého.

## 5. Predchádzajúci projekt `llama-chatbot` – čo prebrať a čomu sa vyhnúť

V `../llama-chatbot/` je starší prototyp toho istého nápadu (PyQt6 + llama-cpp-python, ~590 riadkov, naposledy upravený 2026-10-19). FUKAI je jeho **prepis, nie pokračovanie** – kód sa nekopíruje, ale vizuál a navigácia sa použiť dajú.

**Prebrať:**

- Vizuálny štýl (Catppuccin paleta `#1e1e2e` / `#cdd6f4` / `#89b4fa`) – funguje, len sa prefarbí do zemitej hnedo-zelenej podľa loga (§1).
- Navigácia: úzky ikonový sidebar (70 px) + `QStackedWidget` so stránkami.
- Úvodná „init“ obrazovka s logom, z ktorej sa vstupuje do chatu.
- Slider na rozdelenie CPU/GPU – v §7 už zafixované ako `n_gpu_layers`.

**Čomu sa vyhnúť – konkrétne chyby prototypu:**

1. **Generovanie bežalo v UI vlákne.** `pages/chat_page.py` volal `llm.response()` priamo v `send_message()` → appka zamrzla na celú odpoveď, bez streamovania a bez Stop. Toto je hlavný dôvod, prečo FUKAI začína jadrom + workerom, nie UI.
2. **Model sa načítal v konštruktore pri štarte appky** (`core/lm.py`) → zlá cesta = nefunkčná appka a zmena nastavení sa prejavila až po reštarte. FUKAI načítava model lazy a vie ho reloadnúť.
3. **Počet vrstiev modelu bol ručne písaný v `models/models_list.json`** (`"layers": "32"`) → pridanie modelu znamenalo ručnú editáciu JSON-u. FUKAI číta počet vrstiev z metadát `.gguf`.
4. **`n_ctx=2048` natvrdo, žiadne orezávanie histórie** → dlhý chat ticho prestal fungovať.
5. **Whitelist OS vo `supported_OS.json`** s vymenovanými verziami jadra (`"26.4.1"`, `"5.15.0-generic"`) → appka sa odmietla spustiť na akejkoľvek neznámej verzii. FUKAI OS whitelistom neoveruje.
6. **Štýly duplikované inline** pri každom widgete (ten istý blok QSS aj 5×) → jeden globálny stylesheet.
7. **História bola len placeholder** (`QListWidgetItem(f"Konverzácia {i}")`), nikdy nenapojená na úložisko.
8. **Nastavenia sa ukladali do `settings.json` vedľa kódu**, nie do používateľského adresára → v zabalenej appke by to padlo na právach. FUKAI používa `platformdirs`.
9. **System prompt bol natvrdo v kóde** (`"Si pomocný asistent, komunikuj v slovenčine"`) → v FUKAI patrí medzi nastavenia per chat.

## 6. Architektúra

```
FUKAI/
├── main.py                 # vstupný bod
├── core/
│   ├── llm_engine.py       # načítanie modelu, streaming, stop
│   ├── hardware.py         # detekcia CPU/RAM/GPU, odporúčané parametre
│   ├── context.py          # počítanie tokenov, orezávanie histórie
│   └── settings.py         # LoadParams / SamplingParams (dataclasses)
├── storage/
│   └── database.py         # SQLite
├── extensions/
│   ├── file_parser.py      # pdf, xlsx, docx, txt…
│   └── web_search.py       # ddgs + trafilatura
├── ui/
│   ├── main_window.py
│   ├── chat_view.py
│   ├── sidebar.py
│   ├── settings_panel.py
│   └── workers.py          # QThread workery
├── assets/                 # logo, ikony
├── requirements.txt
├── requirements-llama-win-cuda.txt
└── requirements-llama-mac.txt
```

Plochá štruktúra (nie `src/fukai/`) – je to aplikácia, nie knižnica, a jednoduchšie sa balí cez PyInstaller.

## 7. Kľúčové technické rozhodnutia

- **Dve skupiny parametrov.** *Load-time* (`model_path`, `n_ctx`, `n_gpu_layers`, `n_threads`) → zmena = reload modelu, v UI tlačidlo „Použiť a reloadnúť“. *Sampling* (`temperature`, `top_p`, `top_k`, `repeat_penalty`, `max_tokens`) → per request.
- **CPU/GPU** sa ovláda cez `n_gpu_layers` (0 = CPU, -1 = všetko na GPU, medzi tým čiastočný offload) → v UI slider, nie prepínač.
- **Detekcia HW:** NVIDIA cez `nvidia-ml-py` (importuje sa ako `pynvml`) / `nvidia-smi` (meno, VRAM), Apple Silicon cez `platform.machine() == "arm64"` (Metal), RAM cez `psutil`. Pozn.: balík `pynvml` na PyPI je zastaraný alias, inštaluje sa `nvidia-ml-py`.
- **Vlákna:** načítanie aj generovanie mimo UI vlákna (QThread worker), tokeny do UI cez signály. Stop = prerušenie generátora.
- **Chat template:** vždy `create_chat_completion()` – template sa berie z metadát `.gguf`. Žiadne ručné skladanie promptov.
- **Kontext:** história sa orezáva podľa reálneho počtu tokenov (`llm.tokenize`). Príloha nad limit → orezať + upozorniť. RAG až ako neskorší bonus.
- **Web:** `ddgs` (DuckDuckGo) na vyhľadávanie, `requests` + `trafilatura` na extrakciu textu. Žiadny scraping Google. Spúšťa používateľ prepínačom, model si ho nevolá sám (tool-calling malých modelov je nespoľahlivý).
- **Súbory:** `pypdf` (MIT; PyMuPDF je rýchlejší, ale AGPL), `openpyxl`/`pandas` → markdown tabuľka, `python-docx`. OCR mimo rozsahu.
- **Úložisko:** SQLite cez `platformdirs` – tabuľky `chats`, `messages`, `chat_settings`, `attachments`.
- **Render odpovedí:** `QTextBrowser.setMarkdown()` + `pygments` na kód. Bez QWebEngine (veľký build).
- **Distribúcia:** PyInstaller, zvlášť build pre Windows a Mac. Na Windows potom Inno Setup, na Macu `.dmg`/`.pkg`. Podrobnosti a nevyriešené body v §10.

## 8. Poradie práce a stav

0. [x] `requirements.txt`, `requirements-llama-win-cuda.txt`, `requirements-llama-mac.txt` hotové (2026-10-27). V `.venv` je zatiaľ **iba `psutil`** – PyQt6 ani llama-cpp-python sa ešte neinštalovali.
1. [x] `core/errors.py` – hierarchia chýb delená **podľa príčiny**, nie podľa modulu. Každá chyba nesie tri oddelené texty: `message` (veta pre používateľa), `hint` (čo s tým), `detail` (technický text do logu). Plus `Notice` + `Severity` na **nefatálne** oznámenia. Vďaka tomu UI vykresľuje chyby aj varovania rovnako. `hint` je keyword-only, aby sa tie tri texty nedali zameniť.
2. [x] `core/hardware.py` – detekcia a 4 kontroly (`check_os`, `check_cores`, `check_ram`, `check_gpu`). Overené na PC 1 aj MacBooku. Dáva tri veci, pre ktoré modul existuje: `n_threads` (= `cores_performance`), `n_gpu_layers` (−1/0 podľa backendu) a `backend` (`cuda`/`metal`/`cpu`). **Zásada: detekcia nikdy nevyhodí výnimku von** – zlyhanie sondy sa mení na `Notice` a appka beží na CPU. `required_wheel()` je zvlášť, mimo `check_gpu` – nie je to problém, ale fakt, a hlásiť ho treba až keď llama-cpp-python chýba. Pevné údaje (minimálne verzie OS, mapa compute capability → wheel) sú vo `vars/hw.json`, konštanty v `core/constants.py`.
3. [ ] `core/settings.py` (LoadParams / SamplingParams) → `core/llm_engine.py`, otestované v konzole (load `.gguf`, streaming, stop) ← **ďalší krok**.
   Pred tým: nainštalovať llama-cpp-python 0.3.36 (`pip install -r requirements-llama-win-cuda.txt`, 218 MB) a na MacBooku `requirements-llama-mac.txt`.
   Prvý test má odpovedať na dve neoverené veci: či CUDA wheel podporuje `sm_120` (Blackwell) a či potrebuje CUDA Toolkit. Postup: načítať `gemma-3-4b-it-Q4_K_M.gguf` s `n_gpu_layers=-1` a v `nvidia-smi` overiť, že model naozaj sedí vo VRAM, nie v RAM.
2. [ ] Minimálne UI: okno, vstup, streamovaná odpoveď cez worker
3. [ ] SQLite + sidebar s chatmi
4. [ ] Panel nastavení per chat + výber modelu
5. [ ] Prílohy (drag & drop, extrakcia, kontrola tokenov)
6. [ ] Web rozšírenie
7. [ ] Doladenie: témy, markdown, ikony, PyInstaller

### Prečo sa začína jadrom, a nie UI ani nastaveniami

Rozhodnuté 2026-10-27, platí ako odpoveď na otázku „UI / core / nastavenia a história?“:

- **Tvar UI určuje worker + signál architektúra** (§7). UI postavené pred jadrom by sa prepisovalo druhýkrát – presne to sa stalo prototypu (§5, bod 1).
- **Načítanie CUDA/Metal wheelu je jediné skutočné riziko projektu.** Kým nie je overené, že `n_gpu_layers=-1` reálne offloaduje na GPU, všetko ostatné stojí na neoverenom predpoklade.
- **Nastavenia a história sa nedajú navrhnúť naslepo.** Schéma `chat_settings` je priamo zoznam parametrov, ktoré engine naozaj prijíma – kým engine nebeží, je to hádanie. Prototyp si takto do nastavení zadrôtoval ručný počet vrstiev (§5, bod 3).

Jadro sa dá otestovať čistým konzolovým skriptom, takže je hotové a overené skôr, než vznikne prvý widget.

## 9. Poznámky k prostrediu

Na PC 1 je shell **PowerShell 5.1**, Claude Code má aj Git Bash. Každé z nich má inú pascu:

- **PowerShell 5.1 nepozná `&&`.** `git add . && git commit -m "x"` skončí na `ParserError`. Správne: `git add .; if ($?) { git commit -m "x" }`, alebo len `a; b`.
- **Git Bash prerába argumenty začínajúce lomkou na windowsové cesty.** Z `git commit -m "/core - ..."` sa stane predmet `C:/Users/.../hermes/git/core - ...`. Commit správy nikdy nezačínať `/` – písať `core: ...`.
- **Viacriadkové `heredoc` v Git Bash** sa na slovenských úvodzovkách a apostrofoch rozbíja – dlhé súbory zapisovať priamo, nie cez `cat > file <<EOF`.

Git:

- **Identita je nastavená iba lokálne v tomto repe** (`Lukáš Vavro <vavrolukas1911@gmail.com>`), nie globálne. Na MacBooku a PC 2 treba nastaviť vlastnú, inak `git commit` zlyhá na „Author identity unknown“. Globálne: `git config --global user.email "..."`.
- Pozor na klamlivé **„Everything up-to-date“** pri `git push`: znamená len, že nie je žiadny nový *commit*. Keď commit zlyhá (napr. na chýbajúcej identite), súbory zostanú iba *staged* a push nemá čo poslať. Overovať cez `git log --oneline`, nie podľa výstupu pushu.
- `.gitattributes` s `* text=auto eol=lf` drží jednotné konce riadkov. Bez neho Git na Windows hlási `LF will be replaced by CRLF` a súbory sa javia zmenené aj keď v nich nič nie je.
- `.DS_Store` z macOS bol omylom v repe (commit `510c7a1`), od commitu `9ca7529` je odstránený zo sledovania a v `.gitignore`.
- Commit `510c7a1` obsahoval `ALMANAC.md` ako **prázdny** súbor – obsah bol len v pracovnom strome. Od `9ca7529` je ALMANAC v Gite s obsahom. Poučenie: ALMANAC commitovať priebežne, inak ho `git checkout -- ALMANAC.md` vymaže.

## 10. Distribúcia – zistené fakty a otvorené body

Rieši sa až v kroku 7, ale nasledujúce čísla sú overené (2026-10-28) a ovplyvňujú rozhodnutia, ktoré sa robia skôr.

**Windows:** PyInstaller `--onedir` (nie `--onefile` – ten pri každom spustení rozbaľuje obsah do temp, čo je pri ~300 MB DLL neúnosné), potom Inno Setup zabalí ten adresár do `setup.exe`.

**Do zabalenej PyInstaller appky sa nedá doinštalovať wheel pipom.** Nie je tam pip ani `site-packages`. „Dynamická inštalácia správneho wheelu“ sa teda musí riešiť stiahnutím samotných DLL, nie pipom. Funkcia `required_wheel()` v `core/hardware.py` na to už existuje – vracia napr. `sm120`.

**Veľkosť je hlavný problém, a nie je to Python kód:**

| Súbor | Veľkosť |
|---|---|
| `cublas64_13.dll` | 49 MB |
| `cublasLt64_13.dll` | **458 MB** |
| CUDA wheel llama-cpp-python | ~300 MB |

CUDA wheel **nemá cuBLAS v sebe** – vyžaduje nainštalovaný CUDA Toolkit (§3). Koncový používateľ ho mať nebude, takže ~507 MB CUDA knižníc treba priložiť k appke. NVIDIA redistribúciu týchto DLL povoľuje (CUDA EULA), ale overiť podmienky pred vydaním.

**Verzie CPU a CUDA wheelov sa neprekrývajú:**

| Zdroj | Rozsah |
|---|---|
| CUDA wheels, `dougeeai` | po **0.3.20** |
| CPU wheels, oficiálny index `abetlen.github.io/llama-cpp-python/whl/cpu` | od **0.3.21** |

Pôvodný pin `0.3.20` **nemal oficiálny CPU wheel pre Windows**, takže variant „appka beží na CPU a GPU podporu si dotiahne“ by vyžadoval dve rôzne verzie llama.cpp. **Vyriešené prechodom na 0.3.36** (§10.1) – tam sú CPU aj CUDA v tej istej verzii.

### 10.1 Oficiálne wheels – ROZHODNUTÉ 2026-10-28, prechod na 0.3.36

Autor knižnice (`abetlen`) hostuje vlastné indexy, nie len PyPI. Overené HTTP dotazom:

| Index | URL | Verzie `win_amd64` |
|---|---|---|
| CPU | `https://abetlen.github.io/llama-cpp-python/whl/cpu` | 0.3.21 – 0.3.36 |
| CUDA 13.0 | `https://abetlen.github.io/llama-cpp-python/whl/cu130` | 0.3.27 – 0.3.36 |
| CUDA 12.1–12.5 | `.../whl/cu121` … `cu125` | staršie |
| Metal (macOS arm64) | `https://abetlen.github.io/llama-cpp-python/whl/metal` | 0.3.31 – 0.3.36 |

Existujú `cu121`–`cu125` a `cu130`; `cu126`, `cu128`, `cu129` neexistujú.

**Prečo je to lepšie než `dougeeai`:**

1. Oficiálny zdroj namiesto tretej strany.
2. **CPU a CUDA sa prekrývajú na 0.3.27 – 0.3.36**, takže obe vetvy môžu bežať na tej istej verzii llama.cpp.
3. Názov súboru je `llama_cpp_python-0.3.36-py3-none-win_amd64.whl` – **bez `sm` prípony**, čiže to zrejme nie je per-architektúra a padá celá matica 4 wheelov zo §3.1.
4. Menší: 218 MB oproti ~300 MB.
5. **Existuje aj Metal index**, takže na macOS padá build zo zdrojákov – netreba Xcode Command Line Tools ani cmake.

**Neoverené, zistí sa pri inštalácii:** či wheel obsahuje `sm_120` (Blackwell, PC 1) a či má v sebe cuBLAS, alebo stále vyžaduje CUDA Toolkit. Podpísané GitHub odkazy nepustia HTTP Range, takže zoznam súborov vo wheeli sa bez stiahnutia celých 218 MB zistiť nedá.

**Rozhodnuté:** pin v §3 posunutý z `0.3.20` na `0.3.36`, `requirements-llama-*.txt` prepísané na oficiálne URL. Zdroj `dougeeai` sa už nepoužíva.

### 10.1b Build zo zdrojákov – čo to je a čo nie je

`CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python==0.3.36` **nie je inštalácia, ale kompilácia**. Treba rozlišovať dva nezávislé problémy, ktoré sa pri tom často mieša:

| | problém | čo ho rieši |
|---|---|---|
| A | rozbehať to na PC 1, PC 2, Macu | predkompilovaný wheel **alebo** build zo zdrojákov |
| B | doručiť appku používateľovi | **len** hotové binárky, nikdy build na stroji používateľa |

- Každý `CMAKE_ARGS` variant (`GGML_CUDA`, `GGML_METAL`, `GGML_HIP`, `GGML_VULKAN`) je **samostatný build a samostatný wheel**. CUDA a HIP sa v jednom builde vylučujú – „podpora pre všetky GPU“ znamená „vyber si jeden“, nie „jeden pokryje všetko“.
- **Viac NVIDIA architektúr v jednom builde sa ale dá:** `-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=75;86;89;120` dá **jeden wheel pre RTX 20xx až 50xx**. Výstupom buildu je `.whl`, teda priamo tá binárka, ktorú priložíš k inštalačke – build zo zdrojákov je teda spôsob, ako si distribučnú binárku vyrobiť, a zároveň odstráni závislosť na cudzom repe.
- **V PowerShelli nefunguje bashová syntax** `CMAKE_ARGS="..." pip install ...`. Musí byť `$env:CMAKE_ARGS = "-DGGML_CUDA=on"` na samostatnom riadku (pozri §9).
- **Nástroje na PC 1 sú k dispozícii** (overené 2026-10-28): MSVC 14.44.35207 z VS 2022 BuildTools, CMake priložený k BuildTools, nvcc 13.0.88. `cl.exe` ani `cmake` **nie sú v PATH** – build spúšťať z „x64 Native Tools Command Prompt for VS 2022“. Na macOS bude treba Xcode Command Line Tools a cmake.
- AMD cez `GGML_HIP` na Windows je problematické (ROCm má na Windows obmedzenú podporu); praktickejší by bol `GGML_VULKAN`. **Mimo rozsah projektu** – §1 fixuje NVIDIA + Apple Silicon.

### 10.2 Pozor na „CUDA build s CPU fallbackom“

CUDA zostavenie `llama.dll` je nalinkované na ovládač NVIDIA (`nvcuda.dll`). Na stroji bez NVIDIA karty sa knižnica nemusí vôbec načítať – takže nie je na čo spadnúť a `n_gpu_layers=0` to nezachráni. Pre Windows preto treba počítať s **dvoma buildmi** (CUDA + CPU), nie s jedným prepínačom.

**Varianty inštalačky – nerozhodnuté:**

1. Štyri inštalačky podľa architektúry GPU. Funguje offline, ale používateľ musí vedieť, akú má kartu.
2. Inno Setup v `[Run]` sekcii stiahne správny balík. Malá inštalačka, potrebuje internet pri inštalácii.
3. CPU základ + voliteľné dotiahnutie GPU akcelerácie pri prvom spustení. Najpríjemnejšie pre používateľa, ale blokuje to nesúlad verzií (vyššie).

**macOS je jednoduchší** – Metal build je jeden pre všetky Apple Silicon, žiadna matica architektúr ani cuBLAS.
