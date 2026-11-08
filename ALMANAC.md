# FUKAI – Almanac

Zdieľaná pamäť projektu pre Claude Code na všetkých strojoch (Mac aj PC). Sem patria rozhodnutia, obmedzenia a kontext, ktorý sa nedá vyčítať z kódu. Pri zmene rozhodnutia prepíš príslušnú sekciu, nepridávaj protichodné záznamy. Posledná revízia: 2026-11-09.

## 1. Projekt

- **FUKAI** = Fakultná Univerzálna Kognitívna AI. Univerzitný projekt (Žilinská univerzita), autor Lukáš Vavro.
- Desktopová aplikácia na chat s lokálnymi LLM (štýl Ollama / LM Studio), crossplatform Windows + macOS.
- Repo: https://github.com/Vejvr0/FUKAI (súkromné). Kód sa synchronizuje **iba cez Git**, nie cez OneDrive (ten je len na dokumenty/návrhy).
- **Logo a ikony** sú v `assets/` (2026-11-02). Originály sú na OneDrive (`semestralka/brand`, `semestralka/UI`).
  - `logo.png` 1254 × 1254 s **bielym pozadím** – zdroj všetkého ostatného.
  - `logo_transparent.png` 1024 – biela odstránená metódou „color to alpha“ (farby zostanú, nie je to orezanie podľa prahu). Do UI, napr. sidebar na modrom pozadí. Tmavomodré ťahy loga majú na tmavej téme slabý kontrast – riešiť pri téme.
  - `ico/fukai.ico` – **jeden súbor s 9 veľkosťami** (16–256), PNG vo vnútri. Windows aj PyInstaller chcú jeden `.ico` s viacerými veľkosťami, nie samostatné súbory na veľkosť; Pôvodné samostatné `ico/logo16x16.ico` … `logo256x256.ico` boli zmazané.
    *Od 2026-11-03 je logo na **bielej zaoblenej dlaždici** ako na macOS* (rozhodnutie autora; priehľadná ikona mala tmavomodré ťahy na tmavom paneli úloh takmer neviditeľné). Na rozdiel od `.icns` dlaždica **takmer vypĺňa plátno** (okraj 1/32, polomer 22 % strany) – Windows nemá Apple mriežku s ~10 % okrajom a taká ikona by bola na paneli úloh menšia než ostatné. Obsah: logo s nápisom 76 % strany dlaždice, samotný symbol 80 %. Zdroj je `logo.png` (biele pozadie), orezaný podľa obsahu; hranica symbol / nápis = prvý prázdny riadok pod symbolom.
  - `icns/fukai.icns` (16–1024) + `icns/fukai_1024.png` – macOS: logo na **bielej dlaždici so zaoblenými rohmi** podľa Apple mriežky (dlaždica 824/1024, polomer ~185). Windows ikona dlaždicu nemá, je priehľadná.
  - **Pod 128 px je len symbol bez nápisu FUKAI** – text by bol nečitateľný.
  - Vyrobené skriptom (numpy + PyQt6 + `iconutil`), ktorý **nie je v repe**. Pri zmene loga treba ikony vyrobiť znova. `.ico` sa zapisuje bez Pillow – formát je hlavička + adresár + PNG bloky (`struct`); veľkosť 256 sa v adresári píše ako `0`. Zmenšovať cez `QImage.scaled(…, SmoothTransformation)`, nie cez `QPainter` – ten pri zmenšení 1254 → 16 len vzorkuje a ikona je zubatá.
- **Splash** `assets/splash_screen.png` 1624 × 1320, bez priehľadnosti: bača s ovečkou, nápis FUKAI, logo ŽU/FEIT, dole modrý pruh `#3d87b6` (riadky 1266–1315) s vpáleným textom „Lokálna chatbot aplikácia“ vľavo. **Verzia sa do obrázka nepíše** – vpravo v pruhu je stav štartu kreslený v kóde.

## 2. Funkcie (rozsah)

1. Chat so streamovanou odpoveďou, tlačidlo Stop.
2. Ukladanie chatov (zoznam v sidebare, premenovanie, mazanie).
3. Prílohy: txt/md/csv/json/kód, PDF, xlsx, docx. Bez OCR.
4. Webové vyhľadávanie ako rozšírenie (prepínač v input riadku, drží sa per chat – §7.2).
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

**Overené 2026-10-28 na PC 1 – oba body naraz:**

| Otázka | Odpoveď |
|---|---|
| Obsahuje wheel `sm_120`? | **Áno.** `compute capability 12.0`, `llama_supports_gpu_offload() == True`, `offloaded 35/35 layers to GPU`. |
| Nesie wheel cuBLAS? | **Nie.** `ggml-cuda.dll` (121 MB) importuje `cublas64_13.dll`, `nvcuda.dll` a `nvcudart_hybrid64.dll` → CUDA Toolkit je stále potrebný, §10 platí. |

Výkon gemma-3-4b Q4_K_M, `n_ctx=2048`, `n_gpu_layers=-1`: load 1,8 s, prompt eval ~127 t/s, generovanie ~103 t/s, `CUDA0 model buffer = 2368 MiB`.

**Jednorazový warm-up pri prvom behu po inštalácii:** prvý `prompt eval` trval 21 s (1,73 t/s), druhý a tretí beh už 0,3 s. Príčina **nie je overená** – adresár `%LOCALAPPDATA%\NVIDIA\ComputeCache` neexistuje, takže PTX JIT to nepotvrdzuje. Dôsledok pre UI: prvé načítanie modelu môže trvať desiatky sekúnd, progres sa nesmie javiť ako zamrznutie.

Ako sa prítomnosť CUDA backendu overí rýchlo: v `.venv/Lib/site-packages/llama_cpp/lib/` musí byť **`ggml-cuda.dll`**. Súbor `include/ggml-cuda.h` tam je vždy, aj v CPU builde – header nie je dôkaz.

### 3.1 CUDA wheels – ako to naozaj funguje (overené 2026-10-27)

> **Platnosť:** matica wheelov podľa GPU architektúry (`dougeeai`, do 2026-10-28) **už neplatí** – oficiálny wheel 0.3.36 je jeden pre všetky NVIDIA karty (§10.1), *overené na PC 1: wheel bez `sm` v názve rozbehal `sm_120`*. Zo sekcie zostáva to, čo platí ďalej: rozdiel medzi verziou CUDA a compute capability, a že wheels sú nezávislé od verzie Pythonu. Compute capability sa používa na **diagnostiku a hlásenia** (`core/hardware.py`, `vars/hw.json`), nie na výber balíka.

**Dve nezávislé čísla, ktoré sa ľahko zmiešajú:**

| Číslo | Čo je to | PC 1 |
|---|---|---|
| **CUDA verzia** | verzia softvéru (ovládač, toolkit) | UMD 13.4, toolkit 13.0 |
| **Compute capability** | generácia čipu, teda hardvér | 12.0 = `sm_120` = Blackwell |

Compute capability je vlastnosť kremíka a aktualizáciou ovládača sa **nikdy nezmení**. Wheel sa vyberá podľa nej, nie podľa verzie CUDA – musí byť skompilovaný pre danú `sm_`, inak sa karta nepoužije ani s najnovším toolkitom. `nvidia-smi --query-gpu=compute_cap` ju vráti priamo (`12.0`), takže sa dá použiť ako kľúč do tabuľky bez parsovania.

- Wheels sú `py3-none-win_amd64`, teda **nezávislé od verzie Pythonu** (3.10–3.13). Dôvod: llama-cpp-python volá `llama.dll` cez `ctypes`, nie je to C extension. Pri prechode na inú verziu Pythonu sa wheel meniť nemusí.

## 4. Vývojový hardvér

| Stroj | CPU | GPU / VRAM | RAM | Backend |
|---|---|---|---|---|
| MacBook | Apple M2 (4P + 4E) | integrovaná, zdieľaná pamäť | **8 GB unified** | Metal – `core/hardware.py` *overené 2026-10-28* |
| PC 1 | Intel Core Ultra 7 265K (8P + 12E, bez HT) | RTX 5060 Ti **16 GB** (Blackwell, sm_120) | 32 GB | CUDA Toolkit 13.0, driver 621.14 – *offload na GPU overený 2026-10-28, pozri §3; celá appka vrátane UI overená 2026-11-06, §8 krok 9* |
| PC 2 | – | RTX 4080 16 GB (Ada, sm_89) | – | CUDA, wheel `sm89` (pozri §3.1) |
| Notebook | Intel Core i7-11850H (8C/16T, bez E-jadier) | Intel UHD + NVIDIA T1200 Laptop **4 GB** (Turing, sm_75), Optimus | 64 GB | *2026-11-06: `detect()` našiel T1200 → `backend=cuda`; nainštalovaný **CPU wheel** 0.3.36, Gemma 3 4B 13–14 tok/s (§8 krok 9, poznatky z notebooku)*; CUDA wheel neskúšaný |

Dôsledky pre návrh:

- **Mac 8 GB je najslabší článok.** macOS si berie ~3 GB, prakticky ~4–5 GB pre model + KV cache → modely do ~3–4B (Q4), 7–8B Q4 len na hrane s malým `n_ctx`. Aplikácia musí pred načítaním odhadnúť pamäť a varovať.
- **Rozhodnuté 2026-10-28: samostatný „rozpočet pamäte“ v `hardware.py` sa nerobí.** Stačí `ram_available_mb` z profilu a orientačné porovnanie s veľkosťou `.gguf` priamo v `llm_engine`, s `Notice` pri nedostatku. Na Macu je `ram_available_mb` aj tak jediné správne číslo, lebo GPU berie z tej istej pamäte. **Pozor:** `ram_available_mb` (aj `gpu.vram_free_mb`) sa merajú raz pri `detect()`, takže pred načítaním modelu si `llm_engine` musí spraviť **nové** meranie – hodnota z času štartu appky je už neplatná. Na to je `hardware.free_ram_mb()`.
- **`psutil.available` na macOS podhodnocuje voľnú pamäť** (overené 2026-10-31 na M2). Nezapočíta súborovú cache (`File-backed pages` vo `vm_stat`), ktorú macOS vie kedykoľvek uvoľniť – a práve tam sú váhy modelu načítaného cez mmap. Namerané: psutil 2650 MB, z toho 2483 MB cache prevažne s Gemmou po predchádzajúcom načítaní → falošné varovanie pri každom načítaní. `free_ram_mb()` preto na macOS počíta z `vm_stat`: `celková − (Anonymous − purgeable + wired + occupied by compressor)`, pri zlyhaní spadne na psutil. Na Windows psutil zodpovedá (standby list sa započíta). Hodnota na Macu silno kolíše podľa ostatných aplikácií (v ten istý deň 2,7 aj 4,8 GB).
- Pri každom PC overiť, že `n_gpu_layers=-1` reálne beží na GPU (log llama.cpp / `nvidia-smi`). **PC 1 overené 2026-10-28** (§3); MacBook a PC 2 zostávajú. Overovať sa má podľa riadku `load_tensors: offloaded N/N layers to GPU` a `CUDA0 model buffer size`, nie podľa toho, že appka nespadla.
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

- Vizuálny štýl (Catppuccin paleta `#1e1e2e` / `#cdd6f4` / `#89b4fa`) – **nahradený** modrou paletou podľa loga, pozri šablónu UI v §8 krok 9 (rozhodnuté 2026-11-02; pôvodný plán „zemitá hnedo-zelená“ neplatí).
- Navigácia: sidebar + `QStackedWidget` so stránkami. *Spresnené 2026-11-02:* sidebar nie je úzky ikonový, ale 272 px so zoznamom chatov (§8 krok 9).
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
- **Chat template:** vždy `create_chat_completion()` – template sa berie z metadát `.gguf`. Žiadne ručné skladanie promptov. *Overené 2026-10-28: gemma-3-4b má `tokenizer.chat_template` v metadátach a llama-cpp-python ho zvolí samo (`chat_format == "chat_template.default"`).*
- **Počet vrstiev pre slider `n_gpu_layers`:** `llama_model_n_layer()` vráti počet **blokov** (gemma-3-4b: 34), ale llama.cpp offloaduje **35/35** – navyše je výstupná vrstva. Maximum slidera je teda `n_layer + 1`, v engine ako `n_layers_offloadable`.
- **`verbose=False` neutíši llama.cpp celkom** – časť hlásení ide na stderr aj tak (napr. `llama_kv_cache_iswa: ...`). Pri UI bude treba stderr presmerovať, nestačí prepínač. **A naopak: pri `verbose=False` knižnica na čas načítania modelu umlčí celý proces** – `suppress_stdout_stderr` presmeruje deskriptory 1 a 2 na devnull, takže v tom okne mlčí aj UI vlákno (overené na PC 1 2026-11-06, §8 krok 9).
- **Kontext:** história sa orezáva podľa reálneho počtu tokenov (`llm.tokenize`). Príloha nad limit → orezať + upozorniť. RAG až ako neskorší bonus.
- **Web:** `ddgs` (DuckDuckGo) na vyhľadávanie, `requests` + `trafilatura` na extrakciu textu. Žiadny scraping Google. Spúšťa používateľ prepínačom, model si ho nevolá sám (tool-calling malých modelov je nespoľahlivý).
- **Súbory:** `pypdf` (MIT; PyMuPDF je rýchlejší, ale AGPL), `openpyxl`/`pandas` → markdown tabuľka, `python-docx`. OCR mimo rozsahu.
- **Úložisko:** dve miesta, nie jedno – pozri §7.1.
- **Render odpovedí:** `QTextBrowser.setMarkdown()` + `pygments` na kód. Bez QWebEngine (veľký build).
- **Distribúcia:** PyInstaller, zvlášť build pre Windows a Mac. Na Windows potom Inno Setup, na Macu `.dmg`/`.pkg`. Podrobnosti a nevyriešené body v §10.

### 7.1 Nastavenia a úložisko – ROZHODNUTÉ 2026-10-28

**Dve úložiská, nie jedno.** Pôvodné „všetko do SQLite“ nevychádza: medzi nastaveniami aplikácie je *cesta k chatom*, čiže cesta k samotnej databáze. Uložiť ju do databázy, ktorú ešte nevieš nájsť, nejde.

Hranica: **do JSON-u ide to, čo treba vedieť *predtým*, než sa otvorí databáza.** Všetko ostatné do SQLite. Vedľajší efekt je dobrý – appka sa spustí aj s rozbitou databázou a vie povedať prečo.

| | kde | čo |
|---|---|---|
| Nastavenia aplikácie | `settings.json` v `app_dir()` | `models_dir`, povoliť prílohy, povoliť web search, téma, posledný model, `version` pre migrácie |
| Dáta | `fukai.db` (SQLite) v `app_dir()` | `models`, `chats`, `content` (správy), `properties` (nastavenia chatu); `attachments` pribudnú v kroku 10 |
| Pevné dáta | `vars/` v repe | `hw.json` – minimálne verzie OS, mapa compute capability |

**Jeden adresár, dve úložiská** – rozhodnuté 2026-10-28 po overení `platformdirs` 4.9.6. `app_dir()` je v `core/paths.py` a je to `platformdirs.user_data_dir("FUKAI", appauthor=False)`, na PC 1 teda `C:\Users\<user>\AppData\Local\FUKAI`. Obsahuje `settings.json`, `fukai.db` a predvolene aj `models/`.

Pôvodný návrh mal `user_config_dir()` pre JSON a `user_data_dir()` pre databázu. **Zamietnuté:** na Windows aj macOS vracajú obe funkcie to isté miesto (`platformdirs/macos.py` to má priamo v docstringu: *„config directory tied to the user, same as `user_data_dir`“*), líšia sa iba na Linuxe, ktorý je mimo rozsah (§1). Dva názvy pre jednu cestu sú len príležitosť pomýliť sa. Delenie na **dve úložiská** (JSON vs SQLite) platí ďalej – to bolo o bootstrape, nie o adresároch.

Dve pasce zistené pri tom:

- **`appauthor=False` je povinné.** Bez neho platformdirs na Windows vloží segment s menom autora a keď ho nedostane, použije názov aplikácie → `AppData\Local\FUKAI\FUKAI`.
- **`roaming` nechať vypnuté.** `roaming=True` dá `AppData\Roaming`, ktorý sa na doménových účtoch kopíruje pri každom prihlásení – pri gigabajtových modeloch v tom istom adresári katastrofa.

platformdirs cestu iba **vypočíta**, adresár nevytvorí – na to je `ensure_dir()`, inak prvé `sqlite3.connect()` spadne.

**Premenná prostredia `FUKAI_HOME` prepíše `app_dir()`** (rozhodnuté 2026-10-28). Dôvod: bez nej je dev adresár ten istý ako v nainštalovanej appke, takže vývojové chaty a ostré dáta by boli v jednej databáze a rozbitá schéma počas vývoja by rozbila aj nainštalovanú appku. Testy by navyše zapisovali priamo do `AppData`.

- Počas vývoja sa nastavuje na priečinok v projekte (v `.gitignore`), takže dáta sú vidno vedľa kódu a reset je zmazanie adresára.
- Zabalená appka premennú nastavenú nemá → použije `AppData`, takže dev a ostré dáta sa nemiešajú.
- Hodnota sa `.resolve()`-uje, aby relatívna cesta nezávisela od toho, odkiaľ sa appka spustí.
- Prázdna hodnota (`FUKAI_HOME=`) je falsy, takže sa korektne prepadne na `AppData`.
- Keďže premenná presúva **celé** dáta aplikácie, zabudnutá nastavená hodnota je potichu zavádzajúca – self-test v `core/paths.py` preto vypisuje, či je override aktívny.

**`settings.json` nepatrí do `vars/`** (zvažované 2026-10-28, zamietnuté). `vars/` je vedľa kódu, teda v zabalenej appke v inštalačnom adresári – na Windows tam používateľ bez admina nezapíše a na macOS je to vnútri `.app` bundle, kde zápis **rozbije podpis** aplikácie. Navyše by súbor skončil v Gite (`git checkout` prepíše používateľovi nastavenia) a na stroji s viacerými používateľmi by ho zdieľali všetci. Je to chyba prototypu zo §5, bod 8.

Hranica: **`vars/` = pevné dáta dodané s kódom, iba na čítanie, v Gite. `user_config_dir()` = to, čo sa mení používaním, zapisovateľné, nikdy v Gite.**

**Import modelu = kópia do úložiska FUKAI** (ako Ollama), nie odkaz na cestu (ako LM Studio). Cieľ je `models_dir`, predvolene `user_data_dir()/models`. Dôsledky:

- `models.filename` môže byť **relatívne** k `models_dir`, takže presun knižnice nerozbije databázu. To je hlavný zisk tohto rozhodnutia.
- Import trvá minúty → worker s progresom a možnosťou zrušiť, kontrola voľného miesta vopred, kopírovať do `*.gguf.part` a premenovať až po úspechu (inak prerušený import nechá v knižnici poškodený model, ktorý sa tvári ako platný).
- Duplikáty sa zisťujú podľa názvu + veľkosti. Hashovanie obsahu je pri 30 GB neúnosné.
- Zmena `models_dir` platí len pre **budúce** importy, existujúce modely sa nepresúvajú.

**Zoznam modelov je tabuľka, nie skenovanie priečinka** (*od 2026-11-05 ju sken pri štarte dopĺňa o nové súbory – §8 krok 9, kúsok 5c-1*). Popup v input riadku musí vypísať modely a panel vlastností potrebuje rozsahy slidrov (max `n_ctx` = `n_ctx_train`, max `n_gpu_layers` = vrstvy + 1) **pred** načítaním modelu. Preto sa metadáta `.gguf` čítajú **raz pri importe** a cachujú v tabuľke `models`. Z toho vyplýva nutnosť čítača hlavičky `.gguf`, ktorý nenačíta model – dnes sú tie čísla dostupné až po `load()`.

**Chat vzniká pri prvej správe,** nie pri otvorení prázdneho okna (ako Ollama aj LM Studio). Blank chat je len stav UI – výber modelu a vlastnosti žijú do prvej správy v pamäti. Inak by sa pri každom spustení nazbierali prázdne chaty.

**Pri výmene modelu sa resetuje celý `properties.data` na predvolené pre nový model** (rozhodnuté 2026-10-30). Toto **nahrádza** pôvodné rozhodnutie z 2026-10-28, podľa ktorého sa mali zachovať parametre nezávislé od modelu (`temperature`, `top_p`, `top_k`, `repeat_penalty`, `max_tokens`) a `json_remove`-ovať len štyri load-time kľúče. Dôvod zmeny: jednotné a predvídateľné správanie – po výmene modelu je chat v tom istom stave, ako keby vznikol nanovo. Cena, ktorú treba poznať: ručne nastavená `temperature` sa výmenou modelu stratí.

Hranica *závislé / nezávislé od modelu* ostáva platná ako pojem (je to tá istá hranica ako `LoadParams` vs `SamplingParams` zo §7) – len sa už nepoužíva na výber toho, čo pri výmene prežije:

- *závislé od modelu* – `n_ctx`, `n_gpu_layers`, `n_threads`, `n_threads_batch`, `n_batch`, `n_ubatch`. Iný model má iný `n_ctx_train` aj iný počet vrstiev, takže hodnota z predchádzajúceho modelu je neplatná.
- *nezávislé* – sampling parametre a `system_prompt`.

Tým **padá dôvod rozlišovať „používateľ to nastavil“ od „to je predvolená hodnota“** cez chýbajúci kľúč, aj `json_remove` v `set_model`. Ten teraz zapíše celý nový blob. Zostáva platiť, že `set_model` je **jedna transakcia** nad tromi vecami: `chats.model_id`, `properties.data` a vynulovanie `content.tokens` (§7.2).

**Prečo JSON a nie typované stĺpce** (rozhodnuté 2026-10-28): parametrov bude s každým novým sliderom v krokoch 9–11 pribúdať a JSON nevyžaduje migráciu schémy pri každom z nich. Cena je, že schéma už nehovorí, čo sa dá nastaviť – ten kontrakt žije v `core/settings.py` (`LoadParams`, `SamplingParams`).

Hranica, podľa ktorej sa to delí a platí aj pre `models.meta` a `content.data`: **do JSON-u to, čo aplikácia číta a zapisuje ako celok; do stĺpcov to, podľa čoho sa radí, filtruje alebo hľadá.** Preto sú `last_used_at`, `imported_at`, `content.role` a `content.tokens` samostatné stĺpce.

**Cesta k chatom nie je v prvej verzii nastaviteľná** – databáza je vždy v `user_data_dir()`. Prenosnosť databázy (presun existujúcej, neplatná cesta, relatívne adresovanie príloh) sa rieši až neskôr.

Ďalšie rozhodnuté drobnosti:

- **Web search má tri úrovne, prílohy dve** (spresnené 2026-11-01). Web search: `web_search_enabled` v nastaveniach aplikácie = *funkcia je dostupná*, teda či sa prepínač v input riadku vôbec zobrazí; `properties.chat.web_search` = *zapnuté v tomto chate* (sticky, §7.2); `content.data` tej-ktorej správy = *naozaj sa pri tejto odpovedi použilo*. Prílohy: `attachments_enabled` v nastaveniach aplikácie = či sa zobrazí tlačidlo na pridanie súboru, a potom už len text prílohy pri konkrétnej správe – vlastnosť chatu pre prílohy neexistuje. Mená v nastaveniach aplikácie majú preto príponu `_enabled`, inak budú v UI dva rovnako pomenované prepínače, ktoré si odporujú.
- **Globálne vypnutie prepíše chat, ale neprepíše databázu** (rozhodnuté 2026-11-01). Pri skladaní promptu (krok 9) platí `web_search_enabled AND properties.chat.web_search`; hodnota v `properties` sa pri prepnutí globálneho prepínača **nemení**, takže po opätovnom zapnutí je chat tam, kde bol. Zamietnuté: prepísať pri vypnutí všetky chaty na `false` – jedno kliknutie v nastaveniach by nenávratne zmazalo nastavenie používateľa vo všetkých chatoch a bol by to zápis do N riadkov.
- **Prílohy sa ukladajú ako extrahovaný text,** nie ako originálny súbor – do promptu ide text, originál by databázu nafúkol bez úžitku.
- **Verziovanie schémy cez `PRAGMA user_version`,** nie vlastnou tabuľkou.
- **`PRAGMA foreign_keys = ON` sa nastavuje pri každom pripojení.** Bez toho cudzie kľúče *ticho* nefungujú a `ON DELETE CASCADE` sa nikdy nevykoná.
- **`content.tokens` je cache závislá od modelu** – pri výmene modelu sa musí vynulovať, inak orezávanie histórie počíta cudzím tokenizérom. Slúži zároveň ako signál „treba pretokenizovať“ (§7.2).
- **`chats.model_id` má `ON DELETE SET NULL`** – zmazanie modelu nezmaže chaty, história je text a dá sa čítať aj bez modelu.

**Konkrétna schéma tabuliek je zatiaľ len návrh, neschválená.**

### 7.2 Vlastnosti chatu – obsah, tok a UI (rozhodnuté 2026-10-30)

**Do `properties.data` ide len to, čo UI vie nastaviť.** Zvažovalo sa uložiť do každého chatu *všetky* parametre, ktoré llama-cpp-python prijíma (~50), aj tie, ktoré sa meniť nebudú dať. **Zamietnuté** z troch dôvodov, prvé dva overené na nainštalovanej 0.3.36:

- **Tri z nich nie sú dáta, ale Python objekty** a do JSON-u sa uložiť nedajú vôbec: `grammar` je `LlamaGrammar`, `logits_processor` je `LogitsProcessorList` (zoznam volateľných), `chat_handler` je funkcia.
- **`logit_bias` sa cestou cez JSON ticho pokazí.** Je to `Dict[int, float]`, ale JSON má kľúče vždy textové: `{15043: -1.5}` sa prečíta ako `{'15043': -1.5}`. Ak sa niekedy bude ukladať, potrebuje vlastný prevod tam aj späť.
- **Nič sa tým nezíska.** JSON blob bol zvolený práve preto, že pridanie kľúča nevyžaduje migráciu (§7.1) – predvyplnenie kľúčov teda nepridáva flexibilitu, len zavádza: každý kľúč je sľub, že ho niečo číta.

Mimo rozsahu úplne: `tools`, `tool_choice`, `functions`, `function_call` – §7 tool-calling zamieta.

Overené 2026-10-30: v 0.3.36 **existujú všetky** parametre z pôvodného zoznamu, aj `tfs_z`, `typical_p`, `mirostat_*`. Domnienka, že časť bola z llama.cpp odstránená, neplatí – obmedzenie je dané rozsahom UI, nie knižnicou.

**Tri skupiny v `properties.data`**, nie dve. Okrem `LoadParams` / `SamplingParams` zo §7 je tretia skupina vlastností chatu, ktoré nie sú ani jedno:

- `web_search` – prepínač v input riadku, **drží sa per chat** (sticky), nie per správu. Globálne povolenie je nastavenie aplikácie, toto je „použiť v tomto chate“. Mení §2, kde bolo pôvodne „prepínač pri správe“.
- `system_prompt` – §5 bod 9 ho má ako chybu prototypu (zadrôtovaný v kóde), patrí sem.

**Či sa web search pri konkrétnej odpovedi naozaj použil, sa zapisuje do `content.data` tej správy.** `properties` hovoria, ako je prepínač nastavený *teraz*; prepis chatu musí povedať, ako vznikla *tamtá* odpoveď – inak sa po vypnutí prepínača nedá zistiť, ktoré staré odpovede mali zdroje.

**„Model bol vymenený“ sa neukladá ako príznak.** Zvažované, zamietnuté: príznak, ktorý musí spotrebiteľ po použití zmazať, je zdroj zaseknutého stavu (kto ho vypne, čo pri páde appky). Signál už existuje a čistí sa sám – `set_model` nuluje `content.tokens`, takže **správa bez tokenov = treba pretokenizovať aktuálnym modelom**. Preto má byť `content.tokens` `NULL`-ovateľný: nula je legitímna hodnota a splývala by s „neviem“.

**Zmena `n_ctx` správy nemaže.** Orezáva sa to, **čo ide do promptu**, nie to, čo je v databáze (§7). Po zväčšení kontextu sa staršie správy do promptu vrátia. Je to úloha `core/context.py` (krok 6), úložisko sa pri tom nemení.

**Tok v UI:**

1. Appka sa otvorí s prázdnym chatom. Používateľ **najprv vyberá model** – tlačidlo s názvom aktuálneho modelu rozbalí zoznam s možnosťou importovať nový a mazať jednotlivé.
2. Po výbere modelu beží indikátor inicializácie (§3: prvé načítanie môže trvať desiatky sekúnd).
3. Chatovať sa dá hneď s predvolenými vlastnosťami pre daný model.
4. Zmena **sampling** parametra alebo `web_search` sa zapíše a platí od nasledujúceho generovania.
5. Zmena **load-time** parametra sa zapíše, ale vyžaduje reload modelu.
6. **Karta vlastností je počas generovania uzamknutá.**

**Easy mode / expert mode.** *Určené 2026-11-08 stránkou Vlastnosti (§8 krok 9, kúsok 9) – pôvodný návrh nižšie sa posunul:* **easy** je systémový prompt (s presetmi) a `n_ctx` s ukazovateľom „model + kontext vs voľná pamäť“; **expert** pridáva `n_gpu_layers`, `n_threads`, `n_batch`, `temperature`, `max_tokens`, `top_p`, `top_k`, `repeat_penalty`, `seed`, kľúče parametrov a spinboxy na presnú hodnotu. `temperature` teda v easy režime nie je – rozdelenie sleduje šablónu, nie pôvodný odhad. Režim sa medzi spusteniami nepamätá.

Dve veci, ktoré z toho vyplývajú:

- **Aj v easy mode zostáva tlačidlo „Použiť“** (§7). Slider mení len číslo, zápis si vypýta kliknutie. *Spresnené 2026-11-08: tlačidlo iba zapisuje, model sa načíta až pri ďalšej správe (§8 krok 9, kúsok 9) – lišta to pri load-time zmene napíše.*
- **Ukazovateľ RAM musí merať nanovo.** `ram_available_mb` z `HardwareProfile` je odmeraný raz pri `detect()` (§4), na živý ukazovateľ je už neplatný.

**Nastavenia aplikácie sú pre verziu 1 len prepínače:** téma, povoliť prílohy, povoliť web search, prípadne ďalšie UI. „Povoliť“ znamená, že sa v input riadku chatu *zobrazí* tlačidlo – samotné použitie je potom vlastnosť chatu.

**Kontrakt pre `core/settings.py`** (dohodnuté 2026-10-30, implementácia je krok 6). Blob má tvar `{"load": {...}, "sampling": {...}, "chat": {...}}`. Skupiny sa volajú takto zámerne – `load-time` by v SQLite fungovalo (`$.load-time.n_ctx` sa vyhodnotí správne), ale v Pythone to nie je platný identifikátor. Čo modul musí vedieť:

- **`defaults_for(model, hardware)`** – zostaviť blob pre nový model. Toto je presne to, čo `Database.create_chat()` a `set_model()` berú ako `properties` a dnes im to nemá kto dať.
- **`from_dict` / `to_dict`** – prevod na a z `properties.data`.
- **`needs_reload(other)`** – porovnanie podstromu `load`. Toto je ten konkrétny zisk, kvôli ktorému sú skupiny vnorené a nie ploché: UI po uložení potrebuje vedieť, či stačí ďalšie generovanie, alebo nabehne reinicializácia modelu.

**`model_path` sa do `properties.load` neukladá.** `LoadParams.to_dict()` ho dnes vracia, lebo vzniklo na prípravu argumentov pre `Llama(...)`. Do úložiska ísť nesmie: §7.1 drží `models.filename` relatívne k `models_dir` práve preto, aby presun knižnice modelov nerozbil databázu, a absolútna cesta zapísaná do vlastností každého chatu by to zrušila. Ktorý model chat používa, hovorí `chats.model_id`; cesta sa dopočíta až pri načítaní. **Dôsledok: „slovník pre úložisko“ a „slovník pre konštruktor `Llama`“ nie sú to isté volanie** a treba ich rozlíšiť.

### 7.3 SQLite – pasce overené 2026-10-28/29

Všetky nižšie sú overené spustením, nie prečítané v dokumentácii. Spoločná vlastnosť: **ani jedna nevyhodí chybu v momente, keď ju spravíš.**

- **`INTEGER PRIMARY KEY` ≠ `INT PRIMARY KEY`.** Len presný zápis `INTEGER PRIMARY KEY` robí zo stĺpca alias na `rowid` a čísluje sa sám. Pri `INT PRIMARY KEY` dostanú **všetky riadky `id = NULL`** a SQLite proti duplicitným NULL-om v primárnom kľúči neprotestuje. Mimo primárneho kľúča je `INT` v poriadku.
- **`PRAGMA foreign_keys` je po každom `connect()` vypnutý.** Bez neho sa `ON DELETE CASCADE` nikdy nevykoná a v databáze zostanú siroty – ticho. Preto je v `PRAGMAS` a nastavuje sa pri každom spojení, nie raz pri vytvorení súboru.
- **`DEFAULT '2000-01-01 00:00:00'` je konštanta, nie „teraz“.** Výraz musí byť v zátvorkách: `DEFAULT (datetime('now'))`. Bez nich dostane každý riadok doslova ten dátum zo schémy.
- **`datetime(now)` bez úvodzoviek** berie SQLite ako názov stĺpca → `no such column: now`. Správne je `datetime('now')`.
- **`datetime('now')` je UTC, `datetime.now()` v Pythone je lokálny čas.** Rozdiel bol na PC 1 hodina. **Rozhodnuté: všetky časy píše SQLite**, Python do časových stĺpcov nesiaha; na lokálny čas sa prevádza až pri zobrazení.
- **Formát času je `'YYYY-MM-DD HH:MM:SS'`**, teda s medzerou, nie `T` z `isoformat()`. Je to presne to, čo `datetime('now')` vracia, triedi sa správne ako obyčajný text a vie využiť index. Miešanie oboch tvarov v jednom stĺpci by triedenie rozbilo, lebo `T` je v ASCII vyššie než medzera.
- **`PRAGMA` neprijíma parametre** – `PRAGMA user_version = ?` je syntaktická chyba, musí ísť cez f-string.
- **`with conn:` nie je zatvorenie spojenia**, ale transakcia: na konci commit, pri výnimke rollback. Spojenie zostáva otvorené.
- **Cudzie kľúče sa neindexujú samy.** SQLite indexuje automaticky len `PRIMARY KEY` a `UNIQUE`, preto `CREATE INDEX idx_content_chat ON content(chat_id)` – načítanie chatu je `WHERE chat_id = ?` a je to najčastejší dotaz aplikácie.
- **`str(dict)` sa do JSON stĺpca uložiť *dá*** – SQLite od 3.42 vie JSON5, takže `json_extract` zvládne aj jednoduché úvodzovky. Ale `json.loads()` v Pythone ich neprijme, takže by si to zapísal a už neprečítal. Prevod `dict` ↔ JSON robí `storage/database.py`, nie volajúci.
- **WAL súbory `-wal` a `-shm`** vzniknú počas behu a pri korektnom zatvorení sa zlúčia a zmažú. Keď tam zostanú, appka buď beží, alebo predtým spadla. Pri zálohovaní patria k databáze.
- **`(x)` nie je n-tica, `(x,)` áno.** `conn.execute(sql, (chat_id))` pošle `int` namiesto sekvencie → `ProgrammingError: parameters are of unsupported type`. Pri jednom parametri je chýbajúca čiarka najčastejšia chyba v celom module.
- **`json_remove` a spol. berú cesty ako parametre** – `json_remove(data, ?, ?)` s `'$.n_ctx'` funguje, f-string na hodnoty netreba (na rozdiel od `PRAGMA`, ktorá parametre neprijíma). Odstránenie neexistujúceho kľúča je neškodné.
- **Spojovník v JSON ceste SQLite nevadí** – `$.load-time.n_ctx` sa vyhodnotí správne. Prekáža až v Pythone, kde `load-time` nie je platný identifikátor; preto sa skupiny v `properties.data` volajú `load`, `sampling`, `chat` (§7.2).

### 7.4 Transakcie nad viacerými príkazmi – overené 2026-10-29/30

`create_chat`, `add_message` a `set_model` potrebujú viac príkazov naraz, ale `Database.execute()` je **jedna transakcia na volanie**. Dva `execute()` za sebou teda nie sú atomické – overené: po zlyhaní druhého INSERT-u zostal v databáze chat bez riadku v `properties`.

**Zamietnuté: `execute_many(statements)`** so zoznamom `(sql, params)`. Nestačí – `create_chat` potrebuje `lastrowid` prvého INSERT-u ako *parameter* druhého, čo plochý zoznam nevie vyjadriť. Nie je to zoznam príkazov, ale blok kódu.

**Riešenie: `Database.transaction()`**, kontextový manažér, ktorý vydá spojenie. `execute()` je cezeň prepísaný, takže zámok aj preklad chýb na `StorageError` žijú na jednom mieste.

Dve pasce, pre ktoré sa to nedá riešiť vnorením – obe overené spustením:

- **Vnorené `with conn:` commitne skôr.** `sqlite3` vnorené transakcie nemá; každé `with conn:` je commit na výstupe. Pri pokuse A → (B) → C s výnimkou na konci zostali v tabuľke `['A', 'B']` namiesto `[]`. Vnútorné `with` commitlo aj vonkajšiu prácu a rollback zrušil len `C`.
- **`threading.Lock` nie je reentrantný.** `self.execute()` vnútri bloku, ktorý už drží `self._lock`, zamrzne.

**Zámok zostáva `threading.Lock`, nie `RLock`** – zámerne. S `RLock` by vnorenie prešlo a dostal by si tichý predčasný commit z prvého bodu. Takto to zasekne hneď pri vývoji; hlučná chyba je lepšia než tichá.

Platí teda pravidlo: **vnútri `transaction()` sa volá `conn.execute()`, nikdy `self.execute()`.**

## 8. Poradie práce a stav

0. [x] `requirements.txt`, `requirements-llama-win-cuda.txt`, `requirements-llama-mac.txt` hotové (2026-10-27). V `.venv` na PC 1 je `psutil` + `llama-cpp-python` 0.3.36 CUDA (2026-10-28). **PyQt6 6.11.0** je na MacBooku (overené 2026-11-02 spustením UI) **aj na PC 1** (overené 2026-11-06 spustením appky: Python 3.12.10 v `.venv`, PyQt6 aj Qt 6.11.0).
1. [x] `core/errors.py` – hierarchia chýb delená **podľa príčiny**, nie podľa modulu. Každá chyba nesie tri oddelené texty: `message` (veta pre používateľa), `hint` (čo s tým), `detail` (technický text do logu). Plus `Notice` + `Severity` na **nefatálne** oznámenia. Vďaka tomu UI vykresľuje chyby aj varovania rovnako. `hint` je keyword-only, aby sa tie tri texty nedali zameniť.
2. [x] `core/hardware.py` – detekcia a 4 kontroly (`check_os`, `check_cores`, `check_ram`, `check_gpu`). Overené na PC 1 aj MacBooku. Dáva tri veci, pre ktoré modul existuje: `n_threads` (= `cores_performance`), `n_gpu_layers` (−1/0 podľa backendu) a `backend` (`cuda`/`metal`/`cpu`). **Zásada: detekcia nikdy nevyhodí výnimku von** – zlyhanie sondy sa mení na `Notice` a appka beží na CPU. `required_wheel()` je zvlášť, mimo `check_gpu` – nie je to problém, ale fakt, a hlásiť ho treba až keď llama-cpp-python chýba. Pevné údaje (minimálne verzie OS, mapa compute capability → wheel) sú vo `vars/hw.json`, konštanty v `core/constants.py`.
3. [x] **`core/llm_engine.py` – prepísaný od nuly, hotový 2026-10-31** (kúsky 1–5 písal autor, 6–8 Claude na jeho žiadosť). Konzolový test: `python -m core.llm_engine [model.gguf] [n_ctx]` – načítanie, údaje o modeli, streaming s t/s, Stop, `LENGTH`. Na M2 Gemma 3 4B ~12–23 t/s (kolíše s voľnou pamäťou), Qwen 2.5 1.5B ~25 t/s. **Overené aj na PC 1 (2026-11-01), Mistral 7B Q4_K_M, `n_ctx=2048`:** load 2,3 s, `offloaded 33/33 layers to GPU` (32 blokov + výstupná → `n_layers + 1` platí aj tu), generovanie 66,9 t/s, Stop aj `LENGTH` v poriadku. Buffery na CUDA0: model 4095 MiB + KV 256 MiB + compute 168 MiB; VRAM 15296 → 10647 MB voľných, teda −4649 MB. Všetky tri vetvy `_memory_pool` dávajú zmysluplné čísla (`-1` → VRAM 15296, `0` → RAM 18240, `16` → 33538 spolu). Žiadny warm-up ako 2026-10-28 (§3) sa nezopakoval. Pôvodná verzia z 2026-10-28: `git show fd59ca9:core/llm_engine.py`.
   **Rozhranie** (na to sa spoliehajú ostatné moduly): `load(params)`, `unload()`, `is_loaded`, `stream(messages, sampling) -> Iterator[str]`, `request_stop()`, `tokenize()`, `count_tokens()`, `n_ctx`, `n_ctx_train`, `n_layers`. Engine nevie nič o Qt, databáze ani orezávaní histórie.
   **Poradie kúskov:** 1. kostra ✅ · 2. `load()`/`unload()` ✅ · 3. údaje o modeli ✅ · 4. `tokenize`/`count_tokens` ✅ · 5. `stream()` ✅ · 6. `request_stop()` + `finish_reason` ✅ · 7. varovania o pamäti + preklad chýb llama.cpp (`InsufficientMemoryError`) + návratová hodnota `list[Notice]` ✅ · 8. `__main__` test.
   **Overené na MacBooku M2 (2026-10-30):** llama-cpp-python 0.3.36 Metal zo zdrojákov (§10.1b), `hardware.detect()` → `backend=metal`, `n_threads=4` (M2 = 4P + 4E, `_performance_cores_macos()` funguje), Gemma 3 4B Q4_K_M sa načíta s `n_gpu_layers=-1`, `n_ctx=2048` a uvoľní (celý test ~6 s).
   **Rozhodnutia v kostre a `load()`:**
   - `_import_llama()` je lenivý import vo funkcii – appka sa musí spustiť aj bez wheelu. Chytá `ImportError` **aj `OSError`** (chýbajúca DLL na Windows) → `BackendUnavailableError`.
   - `_lock` je `threading.Lock` (nie `RLock`), `_stop` je `threading.Event`. Konvencia ako v `database.py`: metóda s príponou `_locked` predpokladá, že zámok už drží volajúci. `load()` volá `_unload_locked()`, nikdy `unload()` – to druhé by zamrzlo.
   - `load()`: `clamped()` → `validate()` → `_import_llama()` **pred** zámkom (pri chybe zostane starý model načítaný) → pod zámkom najprv `_unload_locked()` (dva modely naraz sa na 8 GB Macu nezmestia) → `Llama(...)` do lokálnej premennej → až potom `self._llm` / `self._params`. Výnimky z `Llama(...)` → `ModelLoadError`.
   - `_require_loaded()` vracia `_llm`; volajúci pracuje s lokálnou premennou, nie so `self._llm`.
   **Rozhodnutia v kúsku 3 – údaje o modeli** (`n_ctx`, `n_ctx_train`, `n_layers`, `n_layers_offloadable`):
   - **Zdroj sú metadáta `llm.metadata`, nie C API.** `metadata` je verejný atribút `Llama`; `llama_model_n_layer(llm._model.model)` by siahalo do súkromných vnútorností knižnice. Kľúče sú `{general.architecture}.block_count` a `{arch}.context_length` – **tie isté bude čítať čítač hlavičky v kroku 10**. Hodnoty sú vždy `str` → `int()`. Overené na Gemme 3 4B: `gemma3`, `block_count=34`, `context_length=131072`, zhodné s C API.
   - `n_ctx` je výnimka – verejná metóda `llm.n_ctx()` (skutočný kontext, nemusí sa rovnať zadanému).
   - **Bez modelu vracajú `None`, nie výnimku.** Otázka „aký je kontext?“ má platnú odpoveď „neviem“ (UI ukáže pomlčku); akcia bez modelu je chyba (`_require_loaded()`).
   - **Čítajú sa bez zámku, cez lokálnu premennú `llm = self._llm`.** UI ich číta často a nesmie čakať na worker; lokálna premenná chráni pred `unload()` z iného vlákna medzi kontrolou a použitím.
   - `n_layers_offloadable = n_layers + 1` (bloky + výstupná vrstva; llama.cpp hlási pri Gemme „offloaded 35/35“) – horná hranica slidera `n_gpu_layers`.
   - Spoločná pomocná `_meta_int(key)`: chýbajúci kľúč alebo nečíselná hodnota → `None` (`TypeError` / `ValueError`).
   - *Opravené 2026-10-31:* `n_ctx_train` volal `_meta_int("context-length")` so **spojovníkom** (správne `context_length`) a vracal `None`. Ponaučenie: bezpečné `None` pri chýbajúcom kľúči **ticho zakryje preklep v názve kľúča** – zvážiť názvy kľúčov ako konštanty v `core/constants.py`, ktoré použije aj krok 10.
   **Rozhodnutia v kúsku 4 – `tokenize(text) -> list[int]`, `count_tokens(text) -> int`** (2026-10-31, overené na Gemme 3 4B):
   - Prijíma `str`, na `bytes` prevádza engine (`.encode("utf-8")`) – `Llama.tokenize` chce `bytes`.
   - **`add_bos=False`** – `context.py` počíta správy jednotlivo, BOS pridá chat template raz za celý prompt. S `True` má každá správa +1 token (Gemma: `"Ahoj svet"` → `[2, 236776, …]` vs `[236776, …]`).
   - **`special=False`** – text `<end_of_turn>` od používateľa je obyčajný text (7 tokenov), nie riadiaci token (`[106]`).
   - Bez modelu výnimka cez `_require_loaded()`, nie `None` – je to akcia, nie otázka. Pasca: vzor `llm = self._llm` z vlastností tu skončí na `AttributeError: 'NoneType'` namiesto `ModelLoadError`.
   - **Bez zámku**, vedome: tokenizácia len číta slovník a `stream()` bude zámok držať celú odpoveď. Riziko – `unload()` z iného vlákna počas tokenizácie uvoľní C pamäť pod rukami – rieši architektúra: všetky operácie s modelom idú cez jeden worker (krok 9), teda sekvenčne.
   - Prázdny reťazec → `[]`, nespadne.
   **Rozhodnutia v kúsku 5 – `stream(messages, sampling) -> Iterator[str]`** (2026-10-31, overené na Gemme 3 4B / M2: 19 kúskov, prvý po 0,21 s):
   - Generátor (`yield`) vracajúci **len text**, nie chunky knižnice. Text je v `chunk["choices"][0]["delta"].get("content")` – prvý chunk má len `role`, posledný prázdny `delta` s `finish_reason`, preto `.get()` a `if piece`.
   - `sampling` je **povinný** (starý engine mal `sampling or SamplingParams()` = ticho predvolené hodnoty namiesto nastavení chatu). Na začiatku `clamped()`. `stop=list(...)`, `seed` sa posiela priamo – `None` = náhodný (`llama.py:1387`).
   - **Celé generovanie pod `_lock`, `_require_loaded()` vnútri zámku.** `unload()` z iného vlákna počká na koniec odpovede (overené testom), inak by `close()` uvoľnil C pamäť počas generovania → pád procesu. Pasce: zámok sa drží aj počas `yield`, takže worker musí generátor dočítať alebo `.close()`-núť; `unload()` vnútri vlastného `for … in stream()` zamrzne (Lock nie je reentrantný).
   - Kód generátora beží až pri prvom `next()` – aj chyby (`ModelLoadError`, overflow) vyskočia až v cykle, nie pri volaní `stream()`.
   - Preklad chýb: `ValueError` „exceed context window“ (knižnica, `llama.py:1344`) → `ContextOverflowError`, ostatné → `GenerationError`. Rozlišovanie podľa textu je krehké, horší prípad je všeobecná `GenerationError`. `finally: chunks.close()` uvoľní sampler aj pri chybe/stope; `except Exception` nechytí `GeneratorExit`.
   - Knižnica pri `prompt + max_tokens > n_ctx` **ticho skráti `max_tokens`** (`llama.py:1353`) a odpoveď skončí s `finish_reason="length"` – preto kúsok 6 dôvod konca vystavuje.
   **Rozhodnutia v kúsku 6 – `request_stop()` a `finish_reason`** (2026-10-31, overené na Gemme: stop po 0,5 s z iného vlákna → koniec po 0,61 s):
   - **Stop = príznak `threading.Event`, generátor sa nezatvára zvonka.** `generator.close()` z UI vlákna zlyhá: `ValueError: generator already executing` (overené). `stream()` kontroluje `_stop.is_set()` pred každým chunkom → `break` → `finally` zavrie `chunks` → zámok sa uvoľní.
   - **`request_stop()` nesmie brať `_lock`** – ten drží `stream()` celú odpoveď, Stop by čakal na koniec toho, čo má zastaviť. `Event` je bezpečný medzi vláknami sám.
   - **`_stop.clear()` na začiatku `stream()`, nie na konci.** Clear na konci by nechal nastavený Stop kliknutý tesne po prirodzenom konci a zabil by ďalšiu odpoveď po prvom tokene. Daň: Stop pred začatím generovania sa stratí (overené – ďalšia odpoveď dobehne normálne).
   - **Stop nie je chyba** – generátor skončí normálne, nevyhadzuje výnimku. `GenerationStopped` bola z `errors.py` preto zmazaná (2026-10-31).
   - Obmedzenie: stop sa kontroluje medzi tokenmi, spracovanie dlhého promptu pred prvým tokenom prerušiť nejde.
   - **Dôvod konca je `FinishReason(Enum)`**: `DONE="stop"`, `LENGTH="length"` (hodnoty = reťazce knižnice, takže prevod je `FinishReason(choice["finish_reason"])`), `STOPPED="user"` (naše). Enum namiesto reťazcov kvôli preklepom – poučenie z `context-length`.
   - Odovzdáva sa ako **vlastnosť `finish_reason`** (privátne `_finish_reason`), čítaná po skončení cyklu. Zamietnuté: `yield` slovníkov (rozbije `Iterator[str]`), `return` z generátora (`for` ho zahodí), výnimka pri stope (bežná akcia, nie chyba). Kolízia nehrozí – zámok pustí len jedno generovanie. Pred prvým generovaním a **pri chybe je `None`**.
   - **Stop = vrátenie celého ťahu** (rozhodnuté 2026-10-31, realizácia v kroku 9). Čiastočná odpoveď sa **zahodí** a s ňou aj otázka používateľa – z databázy zmizne, text otázky sa vráti do vstupného poľa na úpravu a opätovné odoslanie. Chat je tak presne v stave pred odoslaním. Dôvod: zahodiť len odpoveď by v histórii nechalo user, user a Gemma na tom padá (`Conversation roles must alternate`, viď nižšie). Zamietnuté: ponechať otázku a v `context.py` zlučovať susedné správy používateľa (opustená otázka by sa ticho prilepila k ďalšej); uložiť čiastočnú odpoveď s príznakom (štýl ChatGPT).
     Dôsledok pre krok 9: správa používateľa sa do databázy zapíše až **spolu s dokončenou odpoveďou** (jedna transakcia, `Database.transaction()`), alebo sa pri Stope zmaže – rozhodnúť pri workeri. Prvá možnosť je čistejšia: pri Stope ani chybe sa nič nezapisuje. Pozor na §7.1 – **chat vzniká pri prvej správe**, takže Stop pri prvej správe nového chatu nesmie nechať prázdny chat.
     `finish_reason` sa teda do `content.data` ukladá len pri `DONE` / `LENGTH`; `LENGTH` je dôležitý, UI pri ňom ukáže „odpoveď bola skrátená“.
   **Overenie na druhom modeli – Qwen 2.5 1.5B Instruct Q4_0** (2026-10-31, M2 Metal, porovnané s Gemmou 3 4B). Engine funguje bez zmeny:

   | | Gemma 3 4B | Qwen 2.5 1.5B |
   |---|---|---|
   | `general.architecture` | `gemma3` | `qwen2` – `_meta_int` skladá kľúč správne |
   | `n_ctx_train` / `n_layers` / `+1` | 131072 / 34 / 35 | 32768 / 28 / 29 |
   | llama.cpp offload | 35/35 | **29/29** – `n_layers + 1` platí aj tu |
   | `add_bos_token` / BOS | `true` / `<bos>` | `false` (BOS id existuje, ale nepridáva sa) |
   | EOS | `<end_of_turn>` | `<\|im_end\|>` – rozpoznaný, `finish_reason="stop"` |
   | system rola v template | prilepí ju k 1. správe používateľa | vlastný ťah `<\|im_start\|>system` |

   - **Dvojitý BOS nehrozí.** Gemma má `{{ bos_token }}` priamo v template a zároveň `add_bos=true`, ale llama-cpp-python pri Jinja template nastaví `added_special=True` a prompt tokenizuje s `add_bos=False` (`llama_chat_format.py:660`).
   - **Gemma vyžaduje striedanie rolí** user/assistant – template volá `raise_exception("Conversation roles must alternate…")`. Dve správy používateľa za sebou → `GenerationError`. Qwen to zvládne. **Dôsledok pre `context.py` / krok 9:** história poslaná do `stream()` musí striedať role. Riziko je konkrétne: zastavená alebo spadnutá odpoveď, ktorá sa neuloží → ďalšia správa používateľa = user, user.
   - **Prázdny system prompt ≠ žiadny system prompt.** Qwen bez system správy doplní vlastný („You are Qwen, created by Alibaba Cloud…“), s prázdnou `""` ho nemá a správa sa inak. Pravidlo: **pri prázdnom `system_prompt` system správu do `messages` vôbec nedávať** – nech model dostane svoj predvolený.
   - Kvalita, nie engine: oba malé modely na slovenskú otázku odpovedajú často **po česky** a Qwen 1.5B ignoroval system prompt „odpovedaj po anglicky“. Template ho do promptu vložil správne.
   - **Neoverené:** Llama 3 (`strftime_now` v template) a **Qwen 3 – `<think>…</think>`** by `stream()` poslal do UI ako bežný text. Otvorená otázka návrhu, overiť pri prvom takom modeli.
   - Riadok `llama_kv_cache_iswa: using full-size SWA cache ...` sa vypíše aj pri `verbose=False` – llama.cpp ho píše priamo na stderr mimo prepínača. Neškodné.
   - **Backend sa nevypína, model áno.** `llama_backend_init()` sa volá raz pri prvom `Llama(...)` (`llama.py:206`), `llama_backend_free()` knižnica nevolá a netreba – pamäť pri skončení procesu uvoľní OS. RAM/VRAM drží model, uvoľní ho `Llama.close()`. Pri zatváraní okna je dôležité **poradie** (krok 9, `closeEvent`): `request_stop()` → počkať na worker → `unload()`, inak hrozí pád pri ukončení (`QThread: Destroyed while thread is still running`).
   **Rozhodnutia v kúsku 7 – pamäť** (2026-10-31, overené na M2):
   - **`load()` vracia `list[Notice]`** – nefatálne varovania; chyby ďalej vyhadzuje.
   - **Text výnimky z llama-cpp-python o príčine nič nehovorí.** Vyprovokovaný nedostatok pamäte na Metale (Qwen, `n_ctx=1 000 000`): log llama.cpp píše `failed to allocate Metal buffer … (out of memory)`, ale výnimka je len `ValueError: Failed to create llama_context` (`_internals.py:266`). Pri modeli `Failed to load model from file` (`_internals.py:62`). Starý engine hľadal v texte slová „out of memory“/„alloc“ → **`InsufficientMemoryError` nikdy nevyhodil, bol to mŕtvy kód.**
   - **Preklad chýb podľa fázy, nie podľa slov:** `Failed to create llama_context` = váhy sa načítali, nezmestil sa kontext (KV cache + výpočtové buffre) → `InsufficientMemoryError` s radou znížiť `n_ctx`. Iné zlyhanie + odhad pred načítaním hlásil nedostatok → `InsufficientMemoryError` s číslami. Inak `ModelLoadError` (`validate()` už vylúčil chýbajúci súbor a zlú hlavičku).
   - **Varovanie pred načítaním:** `model_size_mb × MEMORY_MARGIN (1.2)` proti voľnej pamäti meranej **po** `_unload_locked()` (inak by starý model zabral miesto sám sebe). Kde sa meria – `_memory_pool()`:
     - CPU (`n_gpu_layers=0`), bez GPU, **alebo Metal** → RAM. Na Metale je to vždy RAM, GPU berie z tých istých 8 GB – tým je vyriešený pôvodný problém, že `on_gpu` vypínal varovanie aj na Macu.
     - CUDA, `n_gpu_layers=-1` → voľná VRAM (čerstvé meranie cez `detect_gpu()`).
     - CUDA, čiastočný offload → VRAM + RAM spolu (rozdelenie podľa vrstiev pred načítaním nevieme – krok 10).
   - **Overcommit:** Metal „pridelil“ 27 GB KV cache na 8 GB Macu bez chyby, zlyhal až výpočtový buffer. Na zlyhanie alokácie sa spoliehať nedá – preto varovanie vopred.
   - **Neúplné:** odhad nezahŕňa KV cache závislú od `n_ctx`. *Odmerané 2026-11-01 na Mistrale 7B: pri `n_ctx=2048` je KV cache 256 MiB, teda 0,125 MiB/token → pri 32768 by to bolo 4 GB.* Pri malom kontexte sa to ešte zmestí do rezervy `MEMORY_MARGIN` (odhad 4999 MB vs reálnych 4649 MB), pri veľkom je odhad o gigabajty mimo. Na výpočet treba metadáta (`block_count`, `head_count_kv`, `key_length`) pred načítaním → doplniť s čítačom hlavičky v kroku 10. Strop `recommendedMaxWorkingSetSize` (M2: 5726 MB) sa z Pythonu bez pyobjc nezistí, nepoužíva sa.
   - Po načítaní varovanie, keď `n_ctx > n_ctx_train` (Qwen 2.5: 65536 > 32768). UI to má obmedziť sliderom, toto je poistka.
4. [x] `core/paths.py` – jediné miesto, ktoré vie, kde má aplikácia svoje dáta (`app_dir`, `settings_path`, `db_path`, `default_models_dir`, `ensure_dir`). Podrobnosti a dôvody v §7.1.
5. [x] **Úložisko** (2026-10-28/30). `storage/constants.py` (schéma + pragmy + `SCHEMA_VERSION`) a `storage/database.py` – trieda `Database` so spojením, pragmami, migráciami cez `PRAGMA user_version` a operáciami nad `models`, `chats`, `content` aj `properties`. Overené konzolovým self-testom: `python -m storage.database` – pokrýva aj atomicitu, `ON DELETE CASCADE` a `SET NULL`. *Doplnené 2026-11-02:* `set_message_tokens(counted)` na zápis `PromptPlan.counted` z kroku 8 (podrobnosti tam) a self-test beží v `devdata/selftest-storage/`, nie v temp adresári – súbor po behu zostane na pozretie a na začiatku sa adresár maže, inak by sa modely a chaty nabalili.
   Kľúčový primitív je **`Database.transaction()`** – kontextový manažér, ktorý vydá spojenie a celý blok commitne alebo rollbackne. Existuje preto, že `create_chat`, `add_message` a `set_model` potrebujú viac príkazov naraz a `execute()` je jedna transakcia na volanie. **Vnútri `transaction()` sa volá `conn.execute()`, nikdy `self.execute()`** – to druhé zamrzne na `self._lock`. Overené 2026-10-29/30, pozri §7.4.
6. [x] **`core/settings.py` – vlastnosti chatu, hotové 2026-11-01** (autor písal sám, Claude navrhoval a kontroloval; `__main__` self-test napísal Claude). Prepojí `storage/` s `llm_engine`. Kontrakt v §7.2. Self-test: `python -m core.settings` – predvolené hodnoty, blob, round-trip cez JSON, blob z inej verzie appky, `needs_reload`, `validate()`, `ModelMeta`.
   *Poradie zmenené 2026-10-30:* pôvodne bol 6. `context.py` a 7. `app_settings.py`. Dôvod: `create_chat` aj `set_model` berú `properties: dict` zvonku a **dnes ho nemá kto zostaviť**, takže hotové úložisko sa nedá použiť. `context.py` navyše potrebuje bežiaci engine, takže ide až potom.

   **Hotové (2026-10-30) – časť pre engine:** hranice a predvolené hodnoty v `core/constants.py` (`*_MIN` / `*_MAX` / `*_DEFAULT`, `GGUF_SUFFIX`). V `core/settings.py`:
   - `LoadParams`: `__post_init__` (prevod `model_path` na `Path`), `for_hardware(model_path, hw, *, n_ctx=...)`, `clamped()`, `validate()` (existencia súboru → `ModelNotFoundError`, prípona + hlavička `b"GGUF"` → `ModelFormatError`), `model_size_mb`, `on_gpu`.
   - `SamplingParams`: `clamped()` (`seed=None` zostáva `None`, `stop` → `tuple`). `validate()` nemá – nič sa na ňom nedá pokaziť neopraviteľne.
   - `ChatParams`: len polia (`system_prompt`, `web_search`).
   **Hotové (2026-11-01) – časť pre úložisko:** `ChatProperties` (obal nad tromi skupinami) s `defaults_for()`, `to_dict()`, `from_dict()`, `needs_reload()`; `to_dict`/`from_dict` na všetkých štyroch dataclassoch; nová `ModelMeta` ako dohodnutý tvar `models.meta`. Rozhodnutia:
   - **`ModelMeta` je dataclass, nie dict** (`arch`, `n_ctx_train`, `n_layers`, všetky `| None`). Dôvod: preklep v názve kľúča je potom `AttributeError`, nie ticho `None` – to isté ponaučenie ako `context_length`. Krok 10 ju bude vracať a do databázy pôjde `meta.to_dict()`; krok 11 ju z `models.meta` prečíta a dá `defaults_for()`. Žije v `core/settings.py`; ak jej krok 10 pridá polia (veľkosť, kvantizácia, `mmproj` príznak), presunie sa k čítaču hlavičky.
   - **`_NOT_STORED = frozenset({"model_path"})` je jediné miesto, kde žije pravidlo „cesta do blobu nikdy“** (§7.2). Riadi oba smery: `_as_dict(obj)` ju vynechá pri zápise, `_known(cls, data)` pri čítaní. To druhé nie je kozmetika – `model_path` zabudnutý v blobe by inak spôsobil `TypeError: got multiple values for keyword argument 'model_path'`.
   - **`_as_dict` / `_known` idú cez `fields()`, nie cez vymenované kľúče.** Nový slider v krokoch 9–11 sa tak ukladá sám; vymenovaný zoznam by sa ticho neaktualizoval. `_as_dict` berie inštanciu, `_known` triedu – `fields()` zvládne oboje.
   - **`from_dict` končí na `.clamped()`** (okrem `ChatParams` a `ModelMeta`, ktoré `clamped()` nemajú a netreba). Rieši tým dve veci naraz: rozsahy z blobu staršej verzie a prevod `stop` z JSON `list` späť na `tuple`. Dôsledok: `from_dict` **nie je presná inverzia** `to_dict` pre hodnotu mimo rozsahu – to je zámer.
   - **`data.get("load") or {}`, nie `data.get("load", {})`.** Pri `"load": null` v blobe vráti `get` hodnotu `None` a `**None` padne.
   - **`defaults_for` testuje `meta`, nie `n_ctx`:** `if meta is not None and meta.n_ctx_train`. Obe polovice treba – `meta` je predvolene `None` (kým nie je krok 10) a `n_ctx_train` v nej môže byť `None`, pričom `min(4096, None)` padne. *Pri písaní tu bola podmienka `if n_ctx is None`, ktorá nikdy nenabehla a predvolený kontext sa teda nikdy neorezal na možnosti modelu – tichá chyba, prejavila by sa až ako slider nad `n_ctx_train` v kroku 11.*
   - **O reloade modelu rozhoduje volajúci, nie engine** (rozhodnuté 2026-11-01). UI sa po uložení spýta `needs_reload()` a `load()` zavolá len vtedy, keď treba; engine reloaduje vždy, keď dostane `load()`. Dôvod: engine zostane hlúpy a predvídateľný, čo sedí s tlačidlom „Použiť a reloadnúť“ (§7.2) – tichá optimalizácia vnútri enginu by sa ladila horšie. **Tým padá pôvodná veta nižšie o porovnaní `params == self._params`** – engine také porovnanie nemá a mať nebude.
   - `needs_reload` porovnáva **orezané** podstromy `load` oboch strán, takže `n_ctx=99` a `256` nevyjdú ako rozdiel. Porovnanie zahŕňa aj `model_path`, teda iný model = reload (správne, aj keď výmenu modelu rieši `set_model()` resetom celého blobu, §7.1).
   **Rozhodnutia:**
   - **`clamped()` opraví, `validate()` odmietne.** `clamped()` ticho oreže čísla do rozsahu (hodnoty zo slidera, z JSON staršej verzie); `validate()` kontroluje len to, čo sa opraviť nedá, a vyhadzuje. `clamped()` sa volá pred každým porovnaním parametrov – v `needs_reload()` na oboch stranách – takže `n_ctx=100` a `256` sa po orezaní rovnajú a UI nespustí zbytočný reload. *Opravené 2026-11-01: pôvodne tu stálo, že to porovnanie robí engine; engine ho nemá, rozhoduje volajúci (krok 6).*
   - **`for_hardware()` nevolá `detect()`.** `HardwareProfile` sa zistí raz pri štarte a odovzdáva; `settings.py` na hardvér nesiaha. Predvolené hodnoty polí sú neutrálne (`n_gpu_layers=0`, `n_threads=None`).
   - **`model_size_mb` nikdy nevyhadzuje** (pri `OSError` vráti `0` = „neviem“). Engine ho volá aj vnútri `except` – výnimka by tam prekryla pôvodnú chybu.
   - `on_gpu` = `n_gpu_layers != 0`. Obmedzenie pri Metale je v kroku 3, nie tu.

   **Dve úrovne hraníc, ktoré netreba zamieňať** (2026-10-30): *tvrdá bariéra* je konštanta v `core/constants.py` (napr. `N_CTX_MAX`), *skutočný strop* je z metadát modelu (`n_ctx_train`, `n_layers + 1`). Maximum slidera v UI je `min(konštanta, model)`. Preto `n_gpu_layers` **nemá** `*_MAX` konštantu – horná hranica je per model. Má len `N_GPU_LAYERS_MIN = -1`, kde `-1` je príznak „všetko na GPU“, nie číselné minimum.

   **Pasce overené 2026-10-30:**
   - **`@dataclass` bez anotácie typu nevyrobí pole.** `n_ctx = 4096` je premenná triedy, `n_ctx: int = 4096` je pole. Bez dvojbodky má trieda `fields() == []`, konštruktor neprijíma argumenty a `replace()` nemá čo meniť – ale `LoadParams()` aj `p.n_ctx` fungujú (čítajú atribút triedy), takže to vyzerá v poriadku. Pole bez predvolenej hodnoty (`model_path: Path`) musí byť **prvé**, inak `TypeError: non-default argument follows default argument`.
   - **`STOP_DEFAULT` musí byť `()`, nie `None`.** Engine robí `list(sampling.stop)` → `TypeError: 'NoneType' object is not iterable`. Pri `frozen=True` je prázdna n-tica bezpečná predvolená hodnota, `field(default_factory=...)` netreba.
   - **`tuple(str, ...)` ≠ `tuple[str, ...]`.** Hranaté zátvorky = typ do anotácie, okrúhle = volanie → `TypeError: tuple expected at most 1 argument`. Hodnota je `()`, anotácia `tuple[str, ...]`.
   - **Volanie v predvolenej hodnote poľa sa vyhodnotí raz, pri importe.** `n_threads: int = HardwareProfile.n_threads()` by spúšťalo detekciu pri každom `import core.settings` – a navyše `n_threads` je `@property` na inštancii, na triede je to objekt `property` → `TypeError: 'property' object is not callable`.
   - **`frozen=True` + úprava v `__post_init__`:** `self.x = ...` vyhodí `FrozenInstanceError`, správne je `object.__setattr__(self, "x", ...)` – a **len** v `__post_init__`. Ten sa volá pri každom vzniku inštancie (priamo, cez `classmethod`, cez `replace()`).
   - **`replace()` potrebuje objekt ako prvý argument** – `replace(self, ...)`, nie `replace(...)`.
   - **`_clamp(None, ...)` padá** (`min(hi, None)`). Polia, kde `None` znamená „nech rozhodne llama.cpp / náhodný“ (`n_threads`, `seed`), potrebujú `None if x is None else ...`.
   - **`LoadParams()` v kóde enginu = nová prázdna inštancia**, nie parametre od volajúceho. Parametre prichádzajú ako argument `load(self, params)`.
   - **`Llama(model_path=...)` musí dostať `str`, nie `Path`** – `_internals.py:58` robí `path_model.encode("utf-8")`.
   - **Čiarka na konci priradenia vyrobí n-ticu:** `self.verbose = verbose,` → `(False,)`, čo je pravdivé → llama.cpp vypisuje plný log. Bez chyby, ticho.
   - `SEED_MAX` opravený na `uint32` (4294967295).
   - `mmproj-*.gguf` **nie je model**, ale vizuálny projektor (obrázky) – text negeneruje. Aplikácia ho pri importe bude musieť rozpoznať (krok 10).
7. [x] **`core/app_settings.py` – `settings.json`, hotové 2026-11-01** (`models_dir`, `theme`, `attachments_enabled`, `web_search_enabled`, `last_model_id`, `version`). Iné úložisko než vlastnosti chatu (§7.1). Self-test: `python -m core.app_settings` – beží v temp adresári cez `FUKAI_HOME`, takže sa `AppData` nedotkne.
   **Rozhodnutia:**
   - **`frozen` dataclass + modulové `load_settings()` / `save_settings()`**, nie trieda s metódami `load`/`save`. Hranica: metódy pracujú s hodnotami (`__post_init__`, `to_dict`, `from_dict`), funkcie so súborom. `load_settings()` inštanciu **vyrába**, takže metódou byť nemôže; `save_settings()` by metódou byť mohlo, ale potom by dataclass vedel o `os.replace` aj `ConfigError`.
   - **`load_settings()` nikdy nevyhodí výnimku, `save_settings()` áno** (`ConfigError`). Tá istá hranica ako `hardware.detect()` vs akcie v enginu: appka sa musí spustiť vždy, problémy ide hlásiť ako `Notice`. Dôsledok: `load_settings()` volá `save_settings()` v `try` a chybu mení cez `exc.as_notice()`. **Pozor: `ConfigError` nie je podtrieda `OSError`** – `except OSError` okolo toho zápisu prepustí chybu von a zabije štart (bolo tak napísané a opravené).
   - **Atomický zápis:** do `settings.json.tmp`, potom `os.replace()`. Bez toho pád v polovici zápisu nechá odseknutý JSON a appka sa neotvorí – tá istá pasca ako `*.gguf.part` pri importe modelu (§7.1). `os.replace` aj preto, že `Path.rename` na Windows padne, keď cieľ existuje, a ten existuje vždy okrem prvého spustenia. Pri `OSError` sa `.tmp` maže (`missing_ok=True`), inak po zlyhaní zostane mŕtvy súbor. Názov cez `with_name(path.name + ".tmp")` – `with_suffix(".tmp")` príponu **nahradí** a vyrobí `settings.tmp`.
   - **`version` je informatívna** (rozhodnuté 2026-11-01). Zapisuje sa ako pečiatka „kto to naposledy uložil“ (stampuje `save_settings`, nie volajúci), ale **nič sa na nej nevetví** – žiadne migrácie, export chatov sa nerieši. Kompatibilitu so starším súborom rieši čítanie po kľúčoch: chýbajúci kľúč → predvolená hodnota, kľúč navyše → zahodený. Netreba zamieňať s `SCHEMA_VERSION` v `storage/constants.py`, ktorá migruje (§7.3).
   - **Rozbitý `settings.json` sa prepíše predvolenými** + `Notice` (rozhodnuté 2026-11-01). Zamietnuté: premenovať na `.bad` (nestojí za kód, obsahom sú 4 prepínače) a nechať súbor tak (varovalo by pri každom štarte a prvý zápis ho aj tak prepíše). Pokrýva to `except (OSError, ValueError)` – `json.JSONDecodeError` aj `UnicodeDecodeError` sú podtriedy `ValueError`, takže rozbitý JSON, zle zakódovaný súbor aj „JSON je platný, ale nie je to objekt“ (`[1,2,3]`) padnú do tej istej vetvy.
   - **`AppSettings` nemá `clamped()`** – na rozdiel od `settings.py`. Nie je čo orezávať: `bool` sa pokaziť nedá, `models_dir` normalizuje `__post_init__`, `version` je pečiatka. Jediná opraviteľná hodnota je `theme`, a tá prichádza len zo súboru, nie zo slidera – overuje sa preto v `from_dict` proti `THEMES`, kde vstupuje nedôveryhodný JSON.
   - **`models_dir: Path = field(default_factory=default_models_dir)`**, nie `= default_models_dir()`. Volanie v predvolenej hodnote poľa sa vyhodnotí raz pri **importe** (§8 krok 6), takže by ignorovalo `FUKAI_HOME` nastavenú neskôr – čo robí práve self-test. `__post_init__` potom cestu prevedie na `Path`, `expanduser()` (ručne napísané `~/models`) a `.resolve()` (relatívna cesta v súbore inak znamená „relatívne k tomu, odkiaľ sa appka spustila“).
   - **`data.get("models_dir") or default_models_dir()`**, nie `.get(kľúč, default)`. Pri `"models_dir": null` kľúč existuje, takže `get` vráti `None` a `Path(None)` padne – tá istá pasca ako `data.get("load") or {}` (§8 krok 6).
   - **Neexistujúci `models_dir` nie je chyba:** skúsi sa `ensure_dir()`, pri `OSError` (odpojený disk, cesta pod súborom) `Notice` + návrat na `default_models_dir()`. Overené: `ensure_dir` na mieste, kde je súbor, hodí `FileExistsError`.
   - **Typy z JSON sa nekontrolujú** okrem `theme` a `models_dir` – `"last_model_id": "5"` sa uloží ako `str`. Vedomé: hodnotu zapisuje UI a jediný spotrebiteľ je dotaz do databázy. Keď sa to ukáže ako problém, patrí to do `from_dict`.
   - Dev vs ostré dáta: `/devdata/` je v `.gitignore` a `FUKAI_HOME` sa pri vývoji nastavuje naň (`$env:FUKAI_HOME = ".\devdata"`, nie `set` – §9). Krok 7 je prvý, ktorý reálne vyrobí súbor, dovtedy to nebolo treba.
8. [x] **`core/context.py` – hotové 2026-11-02** (autor písal, Claude navrhoval; self-test písal Claude). Počítanie tokenov a orezávanie histórie. Orezáva sa **to, čo ide do promptu**, nie to, čo je v databáze (§7.2). Self-test: `python -m core.context [model.gguf]` – bez argumentu beží s falošným počítadlom (1 slovo = 1 token), s cestou k modelu overí aj reálny template.
   **Rozhranie:** `fill_tokens(history, count) -> (history, counted)` a `build_prompt(history, question, *, system_prompt, n_ctx, max_tokens, count) -> PromptPlan`. Dátové typy `HistoryItem(id, role, text, tokens | None)` a `PromptPlan(messages, counted, dropped, prompt_tokens, budget)`.
   **Rozhodnutia:**
   - **Modul je funkcie, nie trieda.** Zvažovaný `Tokenizer` / `ContextBuilder` zamietnutý z dvoch dôvodov: tokenizácia už je v `llm_engine` (druhý obal nad tým istým slovníkom nič nevlastní) a objekt by si držal `n_ctx`, ktoré sa mení **reloadom modelu** – oschnutá hodnota, ktorá vyzerá platne. Tá istá pasca ako `ram_available_mb` z `detect()` (§4) a `content.tokens` po výmene modelu (§7.2). Funkcia s argumentmi oschnúť nemôže.
   - **`count` je `Callable[[str], int]`, nie engine ani databáza.** Rovnaká hranica ako `llm_engine` (nevie o Qt a databáze) a `settings.py` (nevolá `detect()`). Zisk je konkrétny: self-test overí orezávanie s `len(text.split())`, teda bez načítaného modelu.
   - **Tokenizuje `context.py`, zapisuje volajúci.** `PromptPlan.counted` je slovník „id → tokeny, **ktoré sa dopočítali**“, teda signál na zápis do `content.tokens`, nie súčet všetkých. Keby obsahoval aj tie, čo už v databáze sú, krok 9 by pri každej odpovedi prepisoval N riadkov hodnotami, ktoré tam sú.
   - **`PromptPlan.messages` je hotový vstup pre `stream()`**, nie zoznam id na vynechanie – volajúci nemá čo skladať druhýkrát. `dropped` existuje preto, že UI musí vedieť povedať „staršie správy sa do kontextu nezmestili“, inak to vyzerá, že model bez dôvodu zabudol.
   - **Rozpočet je `n_ctx − max_tokens − PROMPT_RESERVE`**, nie `n_ctx`. Knižnica pri `prompt + max_tokens > n_ctx` ticho skráti `max_tokens` a odpoveď skončí na `LENGTH` (§8 krok 5) – orezávanie teda musí nechať miesto na odpoveď.
   - **Cena správy je `tokens + TOKENS_PER_MESSAGE`** (8), navrch `PROMPT_RESERVE` (64) na BOS a preambulu template-u. `count()` má `special=False`, takže značky template-u (`[INST]`, `<start_of_turn>`) v čísle nie sú. Sú to **zámerne nadsadené odhady**; presné číslo by znamenalo renderovať template pri každom orezaní. *Overené 2026-11-02 proti `prompt eval` z llama.cpp: Mistral 7B odhad 256 vs reálnych 211 tokenov, Gemma 3 4B 230 vs 206 – odhad je v oboch prípadoch nad skutočnosťou, čo je požadovaný smer.*
   - **Prvá ponechaná správa musí byť `user`, posledná v histórii nesmie byť `user`.** Prvé preto, že po systéme by inak nasledoval `assistant` a Gemma template vyhodí `Conversation roles must alternate` (§8 krok 3); druhé preto, že otázka sa pripája ako `user`. Rez sa teda nerobí po pároch, ale „posuň hranicu, kým prvá ponechaná nie je `user`“ – to zvládne aj históriu, ktorá páry nedrží. Visiaca otázka na konci v teórii nemôže existovať (§8 krok 3 ju ukladá až s hotovou odpoveďou), ale pád počas generovania ju tam nechá a stojí to jeden `if`.
   - **Posledná otázka sa neoreže nikdy** – keď sa sama so system promptom nezmestí, je to `ContextOverflowError`. Orezanie prílohy je krok 12.
   - **Prázdny `system_prompt` → system správa sa do `messages` nedáva vôbec** (§8 krok 3, overené na Qwene).
   - **`Database.content_tokens()` sa tu nepoužíva** – vracia `0` pri prázdnom chate aj pri samých `NULL`, čo sú pre tento modul dve rôzne veci. Je to číslo pre UI.
   - **Uvoľnené tokeny po zahodení vedúceho `assistant` sa nevracajú do rozpočtu.** Nedajú sa využiť: na ich miesto by sa dala pridať len ešte starší `assistant`, čo hranicu posunie späť. Kód, ktorý by `remaining` zväčšoval, by preto len klamal.
   - **Zápis cache je `Database.set_message_tokens(counted)`** (doplnené 2026-11-02). Berie **celý slovník** `plan.counted`, nie jednu správu: `execute()` je jedna transakcia na volanie (§7.4), takže cyklus by znamenal N transakcií a N zápisov do WAL. Prázdny slovník je bežný stav (všetko už tokenizované) → `return` pred otvorením transakcie. `chats.updated_at` sa pri tom **nemení** – dopočítanie tokenov nie je zmena obsahu a `updated_at` radí chaty v sidebare, takže by sa poradie preskupilo len otvorením starého chatu po výmene modelu. `UPDATE` na neexistujúce `id` je neškodný no-op (správa mohla byť medzitým zmazaná, je to cache).
   - **Pasca v `executemany`: poradie parametrov je obrátené voči slovníku.** V SQL je `SET tokens = ?` prvé a `WHERE id = ?` druhé, takže n-tica musí byť `(tokens, message_id)`. Pri zámene SQLite **neprotestuje** – spraví `tokens = <id>` tam, kde `id = <počet tokenov>`, čo väčšinou neaktualizuje nič. Self-test to odhalí len vtedy, keď sú hodnoty rôzne a nie sú to id (`{id1: 11, id2: 22}`).
   - **Pasca na krok 11:** `max_tokens` môže byť podľa `MAX_TOKENS_MAX` 32768, zatiaľ čo `n_ctx` 4096 – `clamped()` tieto dve hodnoty navzájom nekontroluje, takže rozpočet vyjde negatívny a `build_prompt` skončí `ContextOverflowError` ešte pred prvým tokenom. Slider `max_tokens` treba v UI obmedziť podľa `n_ctx`; chyba je poistka, nie náhrada.
9. [x] **UI – hotové 2026-11-08.** Okno, sidebar s chatmi, chat so streamovanou odpoveďou cez worker, stránky Vlastnosti a Nastavenia. Postavené po kúskoch; podrobnosti každého sú nižšie v tomto kroku.

   | Kúsok | Čo | Stav |
   |---|---|---|
   | 1 | štart aplikácie, splash, služby v `Application` | ✅ |
   | 2 | toasty namiesto dialógov | ✅ `54e7150` |
   | 3 | kostra okna, sidebar, témy | ✅ |
   | 3b | menu ⋯ pri chate (premenovať, vymazať, veľkosť) | ✅ `cbfa5c5` |
   | 4a | `LlmWorker` + `LlmService` (jedno vlákno pre model) | ✅ |
   | 4b | tok správy, `ChatController`, zápis ťahu | ✅ |
   | 5a | composer a výber modelu | ✅ `5353816` |
   | 5b | čítač hlavičky `.gguf` (= pôvodný krok 10) | ✅ `44fc7e6` |
   | 5c | sken priečinka, import, mazanie modelu | ✅ |
   | 6a | zoznam správ, streamovanie obyčajného textu | ✅ |
   | 6b | markdown, bloky kódu, tabuľky | ✅ `00a7409` |
   | 7 | monitor vyťaženia CPU/GPU/pamäte | ✅ `05e727f` |
   | 8 | stránka Nastavenia aplikácie | ✅ `a77b3d5` |
   | 9 | stránka Vlastnosti chatu (= pôvodný krok 11) | ✅ `79fc572` |
   | 10 | modal s informáciami o modeli v Nastaveniach | ✅ necommitnuté |

   **Šablóna UI – záväzná od 2026-11-02:** `semestralka/UI/template/` na OneDrive (`index.html`, `style.css`, `app.js`, `assets/`). Navrhnutá rovno pre Qt: atribúty `data-qt` hovoria, ktorý widget čo je, a hlavička `style.css` opisuje prevod CSS → QSS. Pokrýva **len stránku Chat** (prázdny chat aj konverzáciu, svetlú aj tmavú tému). Stránky Vlastnosti a Nastavenia v nej nie sú – pre ich obsah platí `dizajn.png` a §7.2, vzhľad sa prevezme zo šablóny. Nahrádza skorší `dizajn.png` tam, kde si odporujú.
   - **Rozloženie:** `QMainWindow` → `QHBoxLayout`: sidebar `QFrame#sidebar` s pevnou šírkou 272 px | zaoblený panel `QFrame#chatPanel` (okraj 12 px, polomer 22 px). Sidebar zhora: logo (svetlá/tmavá verzia, mení sa s témou) → **3 taby** `Chat` / `Vlastnosti` / `Nastavenia` (`QButtonGroup`, exkluzívne, checkable `QPushButton`) → tlačidlo **„Fúkni nový chat“** → zoznam chatov (stretch 1) → kopce dole. Taby prepínajú **pravý panel** (`QStackedWidget`), sidebar so zoznamom chatov zostáva viditeľný vždy; klik na chat prepne na tab Chat.
   - **Zoznam chatov** má jednu skupinu **„Posledné“**, nie „Tento týždeň / Staršie“ ako v šablóne (rozhodnutie autora). Radí sa podľa `chats.updated_at`. Položka: názov skrátený `QFontMetrics.elidedText()`, tlačidlo ⋯ len pod myšou → `QMenu` Premenovať (inline `QLineEdit`) / Vymazať.
   - **Stránka Chat:** hlavička s názvom chatu a čipom hardvéru (z `HardwareProfile`) → správy (`QScrollArea`, šírka obsahu max 760 px, centrované) → composer. **Prázdny chat** = uvítanie s logom a composer uprostred, **konverzácia** = composer dole + riadok „FUKAI môže robiť chyby“. Správa používateľa je bublina vpravo (čipy príloh a „Web“ nad ňou), odpoveď vľavo s avatarom a riadkom meta: model · tok/s · čas · zdroje z webu.
   - **Composer:** viacriadkový vstup (rastie do 200 px), Enter odošle, Shift+Enter nový riadok; tlačidlá príloha (+), web (checkable), **výber modelu** (`QToolButton` + `QMenu`: názov, kvantizácia, veľkosť, „Pridať .gguf model…“), odoslať/Stop v jednom tlačidle.
   - **Model sa dá zmeniť aj v rozpísanom chate** (rozhodnutie autora) – zámok zo šablóny (`.modelPill.locked`, ikona `i-lock`) sa **nerobí**. Je to presne prípad, na ktorý sú pripravené `set_model()` a pretokenizovanie (§7.1, §7.2). Dôsledky: (1) zmena modelu resetuje vlastnosti chatu na predvolené pre nový model (§7.1), (2) počas generovania je tlačidlo modelu zablokované spolu s kartou vlastností (§7.2 bod 6), (3) meta riadok odpovede musí brať názov modelu z `content.data` **tej správy**, nie z `chats.model_id` – po výmene by inak staré odpovede ukazovali nový model. Menu má nadpis „Model“, nie „Model pre nový chat“.
   - **Farby:** modrá paleta z loga (`#0D1E48`, `#2A368B`, `#3D87B6`, `#6EC6E5`) – dve sady tokenov v `style.css` (`main.light`, `main.dark`). V Qt to bude slovník `THEMES["light" | "dark"]` dosadený do jednej QSS šablóny. Toasty z kúsku 2 sa na tokeny prevedú tiež.
   - **Prevod do Qt – čo QSS nevie a ako sa to rieši:** `box-shadow` (composer, menu, logo) → `QGraphicsDropShadowEffect`; `border-radius` nadradeného `QFrame` **neoreže deti** (CSS `overflow: hidden` nemá obdobu) → deti panelu musia mať priehľadné pozadie, inak prekryjú zaoblené rohy; zaoblené `QMenu` potrebuje `FramelessWindowHint` + `WA_TranslucentBackground`, inak má v rohoch čierne/sivé trojuholníky; `:focus-within` composera → `eventFilter` na `FocusIn/Out` + dynamická vlastnosť; SVG ikony so `stroke="currentColor"` farbu z QSS nepreberú → pri zmene témy prefarbiť (nahradiť `currentColor` v texte SVG a vykresliť cez `QSvgRenderer`); hover ⋯ → `enterEvent`/`leaveEvent`.
   - **Obsah odpovede** (markdown, kód s `pygments`) ide cez Qt rich text (`QTextDocument`), ktorý vie len podmnožinu CSS: **bez `border-radius` a bez `padding` na `div`**. Bloky kódu budú hranaté (tabuľka s `bgcolor` a `cellpadding`) – zaoblené rohy zo šablóny sa v texte odpovede nedajú. „Kopírovať“ = odkaz `copy:N` + `anchorClicked`.
   - `assets/hills.svg` autor dodal (2026-11-02), `strip.svg` sa nepoužíva.
   - Vyriešené nezhody zo skoršieho `dizajn.png`: farby sú modré (§5 opravený), zoznam chatov je trvalo v sidebare, „Cesta ku konverzáciam“ do stránky Nastavenia **nepatrí** (§7.1 – v 1. verzii nenastaviteľná).
   **Kúsok 1 – štart aplikácie ✅** (hotové 2026-11-02 na M2; Claude navrhol, autor písal): `FUKAI_HOME=./devdata python main.py` → splash so stavom v pruhu → detekcia → prázdne okno s riadkom o hardvéri → `shutdown()` zavrie databázu. Súbory: `main.py` → `ui/application.py` → `ui/splash.py` → `ui/main_window.py` (zatiaľ prázdne), konštanty UI v `ui/constants.py`, `APP_VERSION` v `core/constants.py`. Rozhodnutia:
   - **`Application(QApplication)` vlastní služby** (`settings`, `hardware`, `db`, neskôr engine a worker) a **odovzdáva ich oknám v konštruktore**. Widgety si ich nemajú brať cez `QApplication.instance()` – to je globálna premenná v prestrojení. Patrí sem aj `shutdown()` na `aboutToQuit`, lebo poradie ukončenia (stop → worker → `unload()` → `db.close()`) presahuje okno.
   - **Štart beží v UI vlákne**: `load_settings()` → `detect()` + 4 kontroly → `Database.connect()`, medzi krokmi `showMessage()` + `processEvents()`. Worker netreba – na M2 to trvá **0,04 s**. Model sa pri štarte nenačítava (§5 bod 2).
   - **Splash je zobrazený minimálne 2 s** (`SPLASH_MIN_MS`), čas sa meria až od zobrazenia. Prvé `show()` na macOS samo trvá ~1 s, takže od spustenia po hlavné okno je to ~3 s.
   - **Notice sa zbierajú a hlásia až po zobrazení hlavného okna** – všetky do logu (`log_line()`), `ERROR` aj do dialógu. Je to dočasné, neskôr ich nahradí pás v okne. **`StorageError` pri štarte** = kritický dialóg a koniec (`return 1`).
   - **`detail` sa do `QMessageBox` nedáva** (`setDetailedText`) – na macOS to Qt hlási ako `qt.qpa.dialogs: Message box contains detailed text` a podľa `errors.py` je to text do logu.
   - **Splash pixmap sa škáluje na `SPLASH_WIDTH × devicePixelRatio`** a dostane `setDevicePixelRatio`, inak je na Retine/150 % rozmazaný. Pozícia textu je v pomeroch obrázka, nie v pixeloch. `mousePressEvent` je prázdny – predvolene klik splash skryje.
   - **Windows: `SetCurrentProcessExplicitAppUserModelID` pred `QApplication`**, inak je na paneli úloh ikona `python.exe`. *Neoverené na PC.* Na macOS sa pri spustení cez `python` v menu zobrazí „Python“ – vyrieši až `.app` bundle (krok 14).
   - **Pasce pri písaní** (všetky overené, štyri z nich ticho – appka by bežala, len inak):
     - `SplashScreen` / `Database` bez `()` = trieda namiesto inštancie → `TypeError: first argument of unbound method` až pri prvom volaní metódy.
     - `source.isNull` bez `()` – metóda je vždy pravdivá, takže splash by bol **vždy** náhradný modrý obdĺžnik. Ticho.
     - `def drawContent` namiesto `drawContents` – Qt prepísanú metódu nájde len pod presným menom; inak kreslí predvolene (čierny text vľavo dole). Ticho, pri prepisovaní virtuálnych metód Qt kontrolovať meno.
     - `pixmap.devicePixelRatio(dpr)` – getter, správne `setDevicePixelRatio`.
     - `QRect` s `float` → `TypeError`; pri výpočtoch z pomerov `QRectF`.
     - `self.notices: list[Notice]` **bez `= []` atribút nevytvorí** – anotácia bez priradenia sa zahodí → `AttributeError`. Opak pasce z kroku 6: v `@dataclass` robí pole dvojbodka, v `__init__` robí atribút len `=`.
     - `_set_windows_app_id()` definovaná, ale nezavolaná – na Macu sa to neprejaví nikdy, na Windows len ikonou na paneli úloh. Ticho.
   - **Zistené pri teste:** `check_ram` na 8 GB Macu hlásil `ERROR` takmer vždy (voľných 1,6 GB pri minime 4 GB) → modálny dialóg pri každom štarte. Vyriešené v kúsku 2.
   **Kúsok 2 – toast hlásenia ✅** (hotové a commitnuté 2026-11-02, `54e7150`): `Notice` sa v GUI neukazujú dialógom, ale **toastom** – názov, správa, hint, tlačidlo ✕ a časová os do automatického zatvorenia. `QMessageBox` zostáva **len pre fatálnu chybu pri štarte**, keď ešte nie je okno, kam toast dať. Súbory: `ui/toast.py` (`Toast`, `ToastHost`), `ui/style.py` (začiatok globálneho stylesheetu, §5 bod 6), `MainWindow.show_notice()`. Rozhodnutia:
   - **`check_ram` je `WARNING`, nie `ERROR`** (rozhodnutie autora): „Voľná pamäť RAM nemusí na model stačiť“ s číslami v hinte. Nedostatok voľnej RAM appku neblokuje – model sa ešte nenačítava a pamäť sa uvoľní zatvorením iných aplikácií. Hlási sa pri každom štarte, keď platí.
   - **Názov toastu sa odvodzuje zo `Severity`** (Informácia / Varovanie / Chyba), `Notice` pole `title` nemá. Zmena `errors.py` a všetkých miest, kde `Notice` vzniká, by nepriniesla nič, čo by severity nepovedala. Ak bude treba konkrétnejší názov, pribudne voliteľné pole.
   - **Trvanie podľa závažnosti:** INFO 3 s, WARNING 5 s (voľba autora pri prepise), **ERROR sa sám nezavrie** (bez časovej osi, len ✕) – chyba sa nemá stratiť, kým ju používateľ nevidel. Pod myšou sa čas **pozastaví** (`enterEvent` / `leaveEvent`).
   - **Časová os je `QTimeLine` → `QProgressBar`**, nie `QTimer` + ručný výpočet. Pozor: predvolená krivka `QTimeLine` je `InOutSine`, odpočet by sa na začiatku a konci spomaľoval → `Linear`.
   - **Toast je dieťa okna (overlay), nie samostatné okno.** Bezrámové top-level okno sa na macOS nehýbe s hlavným oknom, kradne fokus a zostáva nad inými aplikáciami. Cena: polohu treba prepočítať pri zmene veľkosti okna – `ToastHost` je `eventFilter` na `Resize` a vracia `False`, aby udalosť išla ďalej.
   - **Pravý horný roh panelu, pod jeho hlavičkou** (od kúsku 3: `TOAST_TOP`, `TOAST_RIGHT`), toasty pod sebou v poradí príchodu. Nad hlavičkou by zakryli čip hardvéru, dole bude vstupné pole chatu.
   - **`detail` do toastu nejde** – len do logu, tak ako pri dialógu (kúsok 1).
   - **`dismiss()` je chránený príznakom `_closing`** – klik na ✕ v tej istej chvíli, ako dobehne čas, by inak vyradil toast zo zoznamu dvakrát (`ValueError` v `list.remove`).
   - **Výška cez `setFixedHeight(heightForWidth(TOAST_WIDTH))`, nie `adjustSize()`.** `adjustSize()` odhadne výšku zalomeného textu skôr, než pozná šírku, a prebytok rozdelí medzi riadky – toast mal medzi názvom, správou a hintom veľké medzery (overené screenshotom).
   - Farby idú od kúsku 3 z tokenov tém (`$menu`, `$text`, `$accent`, `$warning`, `$danger`). Od kúsku 3 je toast aj menší: šírka 320, okraje 12/8/8/8, písmo 13/12 px. Štýl podľa závažnosti cez dynamickú vlastnosť: `setProperty("severity", ...)` + `QFrame#toast[severity="warning"]`.
   - **Pasce pri písaní** (2026-11-02, overené):
     - `event.Type()` namiesto `event.type()` – `QEvent.Type` je trieda enumu, jej volanie bez hodnoty → `TypeError: EnumType.__call__() missing … 'value'`. Padá hneď pri prvom `Resize` okna, ešte pred zobrazením toastu, a výnimka v `eventFilter` zhodí celý proces (`zsh: abort`).
     - Chýbajúce `super().__init__(parent)` v podtriede widgetu → `RuntimeError: super-class __init__() … was never called` pri prvom `self.set…()`.
     - `QVBoxLayout()` bez `self` – layout nie je nastavený na toast, ten je prázdny a jeho deti sa nezobrazia. Ticho.
     - `self.close.emit(...)` namiesto `self.closed.emit(...)` – `close` je metóda `QWidget`, nie signál → `AttributeError` pri každom zatvorení. Pozor na mená signálov, ktoré sa líšia od zdedených metód jedným písmenom.
     - Zabudnuté `setObjectName("toastClose")`, `setTextVisible(False)` a `setFixedHeight(heightForWidth(...))` – nič nespadne, len sa neuplatní štýl, vedľa pruhu sa ukáže „100 %“ a výška nesedí. Ticho.
   **Kúsok 3 – kostra okna a témy ✅** (hotové 2026-11-03 na M2: autor prepísal, Claude skontroloval a opravil 6 chýb, overené spustením v oboch témach): sidebar (logo, 3 taby, „Fúkni nový chat“, zoznam „Posledné“ z databázy, kopce) | zaoblený panel s `QStackedWidget` (Chat s hlavičkou a čipom hardvéru, Vlastnosti a Nastavenia zatiaľ prázdne). Súbory: `ui/style.py` (prepísaný: `THEMES` + QSS šablóna), `ui/icons.py`, `ui/sidebar.py`, `ui/chat_view.py`, `ui/main_window.py`; assety `assets/icons/*.svg` (15 ikon zo šablóny, bez zámku), `assets/logo_sidebar_light.png` / `_dark.png`, `assets/hills.svg` (bez `class`/`id` atribútov z Tailwindu). `strip.svg` sa nepoužíva (rozhodnutie autora). Rozhodnutia:
   - **Témy = slovník tokenov + jedna QSS šablóna** (`string.Template`, `$token`). `THEMES` sú 1:1 tokeny zo `style.css` šablóny (pomlčky → podčiarkovníky) a tri navyše: `ok`, `warning`, `danger`. `Template.substitute()` pri chýbajúcom tokene vyhodí `KeyError` – preklep sa prejaví pri štarte, nie ako chýbajúca farba. `str.format()` zamietnuté: zložené zátvorky QSS by sa museli zdvojovať.
   - **Stylesheet nastavuje `Application` až po `load_settings()`** – téma je v `settings.json`. To, čo QSS nevie (logo, farba SVG ikon), prekresľuje `MainWindow.apply_theme()` → `Sidebar.set_theme()`. Prepnutie témy za behu (stránka Nastavenia) = zavolať oboje znova.
   - **`rgba(r, g, b, 0.25)` QSS prijíma** (overené), tokeny sa preto nemusia prepočítavať. Do **SVG ikon** ale ide len `#hex` (`side_text`, `text`).
   - **Ikony:** SVG so `stroke="currentColor"`; `icon(name, color)` nahradí `currentColor` v texte a vykreslí cez `QSvgRenderer` do pixmapy × `devicePixelRatio`.
   - **Sidebar nevie o databáze.** `MainWindow` načíta `list_chats()` a podá ho `Sidebar.set_chats()`; sidebar vysiela `page_changed`, `new_chat_request`, `chat_selected(id)`. Klik na chat prepne na tab Chat (`show_page()` – `setChecked()` signál `idClicked` nevyšle, takže `MainWindow` prepína aj `QStackedWidget`). Nadpis „Posledné“ sa pri prázdnom zozname skryje.
   - **`itemClicked`, nie `currentItemChanged`** – klik na už vybraný chat (napr. z tabu Vlastnosti) musí tiež prepnúť na Chat.
   - **Medzera ikona–text v tlačidlách = dve medzery v texte** (`ICON_GAP`). QSS `gap` nemá a `QPushButton` medzeru nastaviť nevie.
   - **Kopce** sú `QSvgWidget` s `KeepAspectRatio` a výškou dopočítanou z `viewBox` (272 × 600/1600 = 102 px), nie konštantou.
   - Pozadie detí panelu musí zostať priehľadné (QSS `border-radius` neoreže deti, §8 krok 9 – šablóna). Overené: rohy panelu sú čisté v oboch témach.
   - Menu ⋯ (premenovať / vymazať) pri chate je **ďalší kúsok**, nie tento.
   - **Pasca overená pri návrhu:** `QPushButton(text)` bez rodiča pridaný len do `QButtonGroup` Python zruší, len čo premennú v cykle prepíše ďalšie tlačidlo – `QButtonGroup` tlačidlo nevlastní. Prejaví sa až ako `button(0)` → `None`. Riešenie: `QPushButton(text, self)`.
   - **Pasce pri prepise** (2026-11-03, zoznam v SESSIONS): dva pády na preklepe v názve metódy, štyri tiché – `setCheckable` namiesto `setChecked` (po štarte nebol zapnutý žiadny tab), `addSpacing(0)` namiesto `setSpacing(0)`, preklep v okrajoch a v `__all__`.
   **Rozostupy tlačidiel na macOS ≠ Windows** (zistené autorom 2026-11-03, príčina overená meraním): `setSpacing(8)` medzi tabmi dal na Windows 8 px, na Macu sa tlačidlá prekrývali.
   - **Príčina nie je OS, ale natívny štýl `macos`.** Ten pre `QPushButton` hlási layoutu *layout item rect* menší než widget (rezerva na natívny tieň tlačidla, ~6 px hore aj dole) a layout ukladá tlačidlá podľa neho. Náš QSS tlačidlo vykreslí cez celý widget, takže sa prekryje so susedom. Namerané na M2: `setSpacing(8)` → medzera **−4 px**; autorovo `16` → **4 px** (nie 8 ako na Windows). Týka sa každého `QPushButton` v layoute – aj „Fúkni nový chat“ a budúcich tlačidiel composera.
   - **Riešenie: `self.setStyle("Fusion")` v `Application.__init__`** (rozhodnuté a urobené 2026-11-03, autor schválil). Fusion je rovnaký na oboch OS a takú rezervu nemá – overené na `cocoa` cez skutočnú `Application`: medzery tabov 8 / 8 px, pred „Fúkni nový chat“ 16 px (8 + `addSpacing(8)`). Rozostup tabov je späť na `top.setSpacing(8)` pre oba OS. Keďže celý vzhľad je z QSS, natívny štýl nám nič nedáva, len rozdiely. Natívne zostanú systémové dialógy (`QFileDialog`). Lokálna alternatíva: `setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)` na každom tlačidle – presné, ale treba na to pamätať pri každom novom.
   - **Zamietnuté: rozostup podľa OS** (`8` vs `16`). Na Macu nedá rovnaký výsledok, treba ho opakovať pri každom tlačidle a `Sidebar` kvôli tomu závisel od `HardwareProfile`.
   - **Pasca pri testovaní:** `QT_QPA_PLATFORM=offscreen` natívny štýl macOS nepoužíva, takže screenshoty z kúsku 3 chybu neukázali. Rozdiely štýlu sa overujú na platforme `cocoa` – widget sa dá zmerať (`layout().activate()`, `geometry()`) aj vykresliť (`grab()`) bez `show()`, teda bez okna na obrazovke.
   **Kúsok 4a – worker a `LlmService`** (navrhnuté 2026-11-03, autor prepísal 2026-11-04, Claude opravil 3 chyby, test prešiel nad repom; `Application.llm` zapojené v kúsku 4b; poradie zmenené – worker pred composerom, lebo určuje tvar UI). Súbory: `ui/workers.py` (`GenerateRequest`, `GenerationResult`, `LlmWorker`), `ui/llm_service.py` (`LlmService`), `Application` ju vlastní ako `self.llm`. Konzolový test bez okien: `test_worker.py <model.gguf>` (v scratchpade). Rozhodnutia:
   - **Jeden trvalý worker v jednom `QThread`** (`moveToThread`), od štartu po koniec appky. Všetky operácie s modelom – `load`, `build_prompt` (tokenizácia), `stream`, `unload` – idú cez neho, teda za sebou; na tom stojí tokenizácia bez zámku (krok 3). Zamietnuté: podtrieda `QThread` s `run()` (vlákno na odpoveď), `QThreadPool` (súbežnosť).
   - **UI hovorí len so službou, nie s workerom ani engine** (rozhodnutie autora). `LlmService(QObject)` v UI vlákne vlastní engine, vlákno aj workera; metódy `load`, `generate → request_id`, `stop`, `unload`, `shutdown`; signály `loaded`, `load_failed`, `token(id, text)`, `finished(id, GenerationResult)`, `failed(id, FukaiError)`, `busy_changed`. `engine` je vystavený len na čítanie údajov o modeli.
   - **Jedno generovanie v celej appke** (rozhodnutie autora). Pri prepnutí chatu alebo tabu odpoveď dobehne na pozadí do pôvodného chatu (`request_id`), ale novú správu – v žiadnom chate – nejde odoslať, kým nedobehne. Drží to `LlmService.busy`; `generate()`/`load()` počas `busy` vyhodí `RuntimeError` – chyba programu, UI má mať tlačidlá vypnuté podľa `busy_changed`.
   - **Stop obchádza frontu.** Signál do workera by prišiel až po konci odpovede (overené: slot zavolaný po 1,01 s namiesto 0,2 s). `stop()` volá priamo `worker.cancel(id)` a `engine.request_stop()`. `cancel` pokrýva Stop pred `stream()`, ktorý si príznak enginu na začiatku nuluje (krok 3, kúsok 6): worker ho kontroluje po `build_prompt` a znova v cykle – tam už `clear()` prebehol, takže `request_stop()` zaberie. Príznak je **id požiadavky**, nie bool, takže ho netreba nulovať a nemôže zabiť ďalšiu odpoveď.
   - **Každý slot workera chytá aj `Exception`** a mení ju na `failed` / `load_failed` (`GenerationError`, `ModelLoadError`). Neodchytená výnimka v slote zhodí celý proces (overené: abort, `exit 134`).
   - **`n_ctx` nie je v `GenerateRequest`** – worker berie skutočný `engine.n_ctx`; hodnota z UI by po reloade mohla byť oschnutá.
   - **Do databázy worker nesiaha.** `GenerationResult` nesie `counted`, `dropped`, `prompt_tokens` (odhad) a štatistiky (`first_token_s`, `total_s`, `completion_tokens` cez `count_tokens` hotového textu, `tokens_per_s` bez času promptu); zapisuje UI vlákno (4b).
   - **`shutdown()`: stop → `quit()` → `wait()` → `unload()`**, volá ho `Application.shutdown()` **pred** `db.close()`. `unload()` beží až po skončení vlákna. Načítanie modelu sa prerušiť nedá – zatvorenie počas neho počká.
   - **Overené na M2, Gemma 3 4B** (2026-11-03): odpoveď 22,9 tok/s, prvý token 0,22 s, UI vlákno tikalo celý čas (28× za 1,4 s pri 50 ms časovači); Stop po 1 s → `STOPPED`; Stop pred `stream()` → `STOPPED` s prázdnym textom; ďalšia odpoveď po Stope normálne `DONE`; `max_tokens > n_ctx` → `failed` s `ContextOverflowError`, appka žije; `shutdown()` počas generovania 0,19 s, model uvoľnený, bez `QThread: Destroyed while thread is still running`.
   - **Pasce pri prepise** (2026-11-04, zoznam v SESSIONS): `load_failed` v úspešnej vetve a dva preklepy (`tokens` vs `token`, `monotronic`), ktoré **záchytná `except Exception` v slote premenila na `GenerationError`** – pri `failed` preto vždy pozrieť `detail` v logu.
   - **Proces, ktorý skončí s načítaným modelom, na Metale spadne pri ukončení:** `GGML_ASSERT([rsets->data count] == 0) failed` v `ggml_metal_device_free` počas `exit()` (overené – test skončil výnimkou bez `shutdown()`). Dôvod, prečo `unload()` v `shutdown()` nie je kozmetika; každá cesta ukončenia appky musí prejsť cez `Application.shutdown()`.
   **Kúsok 4b – tok správy ✅** (navrhnuté 2026-11-04; autor prepísal `chat_controller.py` a `database.py`, Claude opravil 8 chýb a dorobil `toast.py`, `main_window.py`, `application.py`, `tools/dev_add_model.py`; `test_controller.py` 8/8 aj UI test offscreen prešli nad repom; 2026-11-04 autor appku spustil na M2 a zaregistroval Gemmu do `devdata` cez `tools/dev_add_model` – štart OK, chatovať sa ešte nedá, chýba composer (4c)). Konštanty `TITLE_WORDS`, `NEW_CHAT_TITLE`, `ICON_GAP` sú v `ui/constants.py` (presunul autor). Súbory: nový `ui/chat_controller.py` (`ChatController`), `Database.add_turn()` + `get_chat()`, `Toast` / `ToastHost.show_notice(..., persistent=True) -> Toast`, `MainWindow` dostane controller, `Application` vlastní `self.llm` a `self.chat`, vývojový skript `tools/dev_add_model.py`. Konzolový test `test_controller.py` (scratchpad) – 8 scenárov nad Gemmou, všetky prešli. Rozhodnutia:
   - **`ChatController(QObject)` v samostatnom súbore** (rozhodnutie autora) – spája `Database` a `LlmService`, widgety nepozná. Metódy `new_chat()`, `open_chat(id)`, `select_model(id)`, `send(text)`, `stop()`; signály `busy_changed`, `chat_opened(id|None, názov, správy)`, `chats_changed(vybraný)`, `loading_started(model)`, `loading_finished`, `turn_started(otázka)`, `token`, `turn_finished(data odpovede)`, `turn_rolled_back(otázka)`, `notice`. `MainWindow` je len poskladanie widgetov a prepája signály.
   - **Model sa načíta až pri odoslaní** (rozhodnutie autora) – v novom chate aj v starom chate s uloženým modelom; otvorenie chatu nič nenačítava. Reload sa robí, keď `LoadParams.clamped()` v engine ≠ vlastnosti chatu (iný model aj iné `n_ctx` / vrstvy). Počas načítania je zobrazený **trvalý info toast** „Načítavam model…“ (rozhodnutie autora), zavrie ho `loading_finished`.
   - **Trvalý toast:** `show_notice(notice, persistent=True)` vráti `Toast`, ktorý nemá časovú os a zavrie ho volajúci cez `dismiss()`. Opakovaný `dismiss()` – aj po zavretí cez ✕ – je neškodný vďaka `_closing` (Python atribút prežije aj `deleteLater()` C++ objektu). Overené offscreen: bežné info po 3,6 s preč, trvalé viditeľné.
   - **`busy` controllera ≠ `busy` služby.** Služba je medzi načítaním a generovaním na okamih voľná; controller je zaneprázdnený od `send()` po zápis / vrátenie, takže tlačidlo Odoslať v UI neblikne. UI počúva `ChatController.busy_changed`, nie službu.
   - **Názov nového chatu = prvých 15 slov otázky** (rozhodnutie autora), `TITLE_WORDS = 15`, bez „…“.
   - **Zápis = `Database.add_turn(chat_id, otázka, odpoveď, answer_tokens, new_chat)`** – otázka + odpoveď (+ pri `chat_id=None` aj chat a `properties`) v **jednej transakcii**. Chat teda vzniká až s prvou dokončenou odpoveďou; Stop / chyba pri prvej správe nenechajú prázdny chat (overené). Tokeny otázky sa ukladajú `NULL` – dopočíta ich `counted` pri ďalšej správe (overené), tokeny odpovede = `completion_tokens`.
   - **`content.data` odpovede:** `text`, `model_id`, `model` (názov – meta riadok berie model z tejto správy), `finish_reason`, `stats` (`prompt_tokens`, `completion_tokens`, `first_token_s`, `total_s`, `tokens_per_s`), `dropped`. Otázka: `{"text": ...}`.
   - **Stop / chyba = vrátenie ťahu:** nič sa nezapíše okrem `counted` (to je cache, platí aj pri Stope), `turn_rolled_back(otázka)` → UI vráti text do poľa. UI vyprázdni pole pri `turn_started`; keď ťah ani nezačal (chýba model), text v poli zostal a nič sa nevracia.
   - **Odpoveď na pozadí:** každé `new_chat()` / `open_chat()` zvýši číslo zobrazenia; `token` / `turn_*` idú do UI len pre zobrazený ťah. Po odchode odpoveď dobehne a zapíše sa do svojho chatu, `chats_changed` obnoví sidebar. Návrat do chatu počas generovania vyšle `turn_started` + doterajší text naraz. Keď odpoveď v novom chate dobehne a používateľ je stále tam, controller prejde do vzniknutého chatu – ďalšia správa už nevytvorí druhý chat.
   - **`select_model()` v existujúcom chate** volá `set_model()` s predvolenými vlastnosťami nového modelu (§7.1); v prázdnom chate si model len zapamätá. Predvolený model prázdneho chatu = `settings.last_model_id`. Ukladanie `last_model_id` pri výbere modelu je kúsok 4c.
   - **Dočasný `tools/dev_add_model.py`** – zaregistruje `.gguf` do `models` (cesta relatívna k `models_dir`, ako pri importe) a nastaví `last_model_id`. Model sa nekopíruje: symlink, na Windows bez práv admina hard link (len na tom istom disku). Zmizne s importom v kroku 10–11.
   - **Pasce pri prepise** (2026-11-04, zoznam v SESSIONS): celé telo `add_turn` pod `if chat_id is None:` (druhá správa v chate by ticho zmizla), premenovaný atribút len v polovici súboru, `emit()` bez argumentu a preklep v `__all__`. Pri premenovaní atribútu hľadať všetky výskyty (`grep`), nie len tie na očiach.
   **Kúsok 5a – composer a výber modelu** (navrhnuté 2026-11-04, Claude napísal a otestoval v scratchpade; autor prepísal composer, controller, store, knižnicu, ikony a konštanty, Claude opravil 7 chýb, doplnil QSS a `qcolor()` v `style.py` a zapojenie v `chat_view` / `main_window` / `application`; všetky tri testy prešli nad repom; commit `5353816`). Poradie zmenené na želanie autora: composer + modely pred zoznamom správ. Súbory: nový `ui/composer.py` (`Composer`, `model_subtitle`), `ui/settings_store.py` (`SettingsStore`), `ui/model_library.py` (`ModelLibrary`); zmeny v `chat_controller.py` (`model_changed`, `select_model` ukladá `last_model_id`), `chat_view.py` (stĺpec s composerom), `main_window.py` (prepojenie), `application.py` (`SettingsStore`, `ModelLibrary`), `icons.py` (vypnutý stav ikon), `style.py` (`qcolor()`, QSS composera a menu), `constants.py`. Testy (scratchpad): UI offscreen 14/14, výber modelu 7/7, regresia `test_controller.py` 8/8. Rozhodnutia:
   - **`Composer` nevie o controlleri ani databáze** – vysiela `send_requested`, `stop_requested`, `model_selected`, `add_model_requested`; stav dostáva cez `set_busy` / `set_loading` / `begin_turn` / `end_turn` / `roll_back` / `set_model`. Prepája `MainWindow`, rovnako ako `Sidebar`.
   - **Tri stavy, nie jeden:** `busy` (ťah beží v hociktorom chate → Odoslať a výber modelu vypnuté), `generating` (ťah beží v *zobrazenom* chate → tlačidlo je Stop), `loading` (načítava sa model → Stop vypnutý, `load()` sa prerušiť nedá).
   - **Pole sa vyprázdni v `begin_turn`, nie pri odoslaní**, a len keď v ňom je práve odoslaná otázka. Controller pri návrate do chatu s bežiacou odpoveďou vyšle `turn_started` znova – rozpísaný nový text sa vtedy zmazať nesmie. Bez modelu `turn_started` nepríde, text zostane.
   - **`roll_back`** vráti otázku do poľa len vtedy, keď je pole prázdne (inak by prepísal nový rozpísaný text).
   - **Enter odošle, Shift+Enter vloží `\n` ručne** – predvolené správanie `QPlainTextEdit` pri Shift+Enter vkladá `U+2028` (oddeľovač riadkov), nie `\n`.
   - **Auto-výška:** `QPlainTextEdit` meria dokument v **riadkoch** (aj zalomených), nie v pixeloch → výška = riadky × `lineSpacing` + okraje, strop 200 px, potom posuvník. Prepočet aj v `resizeEvent` (iná šírka = iné zalomenie).
   - **`:focus-within` → `eventFilter` na `FocusIn/Out`** + vlastnosť `focused` + `unpolish/polish`. Placeholder farbu QSS nevie → `QPalette.PlaceholderText`.
   - **`qcolor(token)` v `style.py`** – `QColor("rgba(13, 30, 72, 0.58)")` je neplatná farba (overené: `isValid() == False`, kreslí sa čierna). Treba pre tieň a placeholder; do SVG ikon ďalej len `#hex`.
   - **Vypnuté ikony:** `icon(..., disabled_color=)` pridá `QIcon.Mode.Disabled` – tá istá ikona s nepriehľadnosťou 0,45, voliteľne inou farbou (biela šípka Odoslať by na vypnutom svetlom pozadí zmizla).
   - **Tlačidlo modelu = `QToolButton` s vlastným layoutom** (text + šípka vpravo; vstavaná ikona je vždy vľavo). Pasca: `QToolButton.sizeHint()` o layoute nevie → tlačidlo bolo široké len na kúsok šípky a text chýbal (overené snímkou) → vlastný `sizeHint()` z `layout().sizeHint()` + `updateGeometry()` pri zmene textu. Dlhý názov sa skracuje `elidedText` na 200 px, celý je v tooltipe.
   - **Menu modelov = `QMenu` s `QWidgetAction` riadkami** (názov, podnadpis, ✓). Klik na widget v `QWidgetAction` akciu nespustí → riadok má vlastný signál `clicked`. Zaoblené rohy: `FramelessWindowHint | NoDropShadowWindowHint` + `WA_TranslucentBackground`. Otvára sa nad tlačidlom, zarovnané vpravo.
   - **Zoznam modelov sa číta pri každom otvorení menu** (`set_model_source(library.models)`), žiadny signál `models_changed` – zoznam je vždy čerstvý (veľkosť, poradie podľa posledného použitia, chýbajúci súbor) a netreba nič synchronizovať. `ModelLibrary.models()` pridá `size_mb` zo `stat()` (`None` = súbor chýba → podnadpis „súbor chýba“).
   - **`SettingsStore` – jediná živá kópia `AppSettings`** (číta sa `current`, mení `update(**zmeny)`, ktoré aj uloží). Dôvod: `AppSettings` je frozen; keby si controller a stránka Nastavenia držali každý svoju kópiu, druhý zápis by prepísal zmenu prvého (téma so starým `last_model_id`). `ChatController`, `ModelLibrary` a `MainWindow` dostávajú store, nie `AppSettings`.
   - **`select_model` toho istého modelu nerobí nič** – `set_model()` by zbytočne resetoval vlastnosti chatu (§7.1). Inak: v existujúcom chate `set_model()` s predvolenými vlastnosťami, potom `last_model_id` (predvolený model ďalšieho nového chatu), potom `model_changed`. Chyba úložiska → toast.
   - **`model_changed(model | None)`** ide pri `new_chat`, `open_chat` aj `select_model`. `None` = chat bez modelu (zmazaný → `model_id` NULL) alebo neplatné `last_model_id` → tlačidlo „Vyber model“. `MainWindow` na konci konštruktora volá `controller.new_chat()`, takže tlačidlo má model hneď po štarte.
   - **Prílohy (+) a Web sú zobrazené, ale vypnuté** s tooltipom „pripravuje sa“ (rozhodnutie autora 2026-11-04). Neskôr ich viditeľnosť riadi `attachments_enabled` / `web_search_enabled` (§7.2).
   - **Tieň composera sa oreže na hranice rodiča** – stĺpec rovnako široký ako composer mal pod ním svetlý obdĺžnik s ostrými hranami (overené snímkou). Stĺpec má preto bočný okraj `COMPOSER_SHADOW_ROOM` (20 px).
   - **Centrovanie stĺpca s max. šírkou:** `addStretch(1)` + `addWidget(stĺpec, 100)` + `addStretch(1)`. `setAlignment(widget, AlignHCenter)` nefunguje – layout dá zarovnanému widgetu len jeho `sizeHint` (composer bol úzky).
   - **Pasce pri prepise** (2026-11-04, zoznam v SESSIONS): päť pádov pri štarte okna (trieda bez `()`, preklepy v názvoch metód, `setGraphicsEffect` na efekte samom) a dve tiché – `setEnabled` bez volania nechalo tlačidlo modelu počas generovania zapnuté.
   **Kúsok 5b – čítač hlavičky `.gguf`** (= pôvodný krok 10; navrhnuté 2026-11-05, Claude napísal a otestoval v scratchpade, autor prepísal, Claude opravil 5 chýb, všetky testy prešli nad repom; commit `44fc7e6`). Súbory: nový `core/gguf.py` (`read_header`, `read_meta`, self-test `python -m core.gguf [model.gguf …]`), `core/constants.py` (kľúče `META_*`), `core/settings.py` (`ModelMeta` – nové polia), `storage/database.py` (`set_model_meta`), `ui/model_library.py` (`refresh_meta`), `ui/application.py` (krok štartu „Kontrolujem modely…“). Testy: self-test gguf 23/23 (syntetické aj poškodené súbory), doplnenie metadát 7/7, regresia UI 14/14, výber modelu 7/7, `test_controller.py` 8/8. Rozhodnutia:
   - **Vlastný čítač, bez knižnice `gguf`** (tá ťahá numpy a číta aj tenzory). Hlavička: `GGUF`, verzia u32, počet tenzorov u64, počet kľúčov u64, potom páry kľúč–typ–hodnota. Prijíma verzie **2 a 3** (v1 mala dĺžky u32). **Polia sa preskakujú cez `seek`**, nečítajú sa – slovník tokenov Gemmy je 262 144 reťazcov (6,5 MB); čítanie trvá 58 ms (Gemma), 70 ms (Qwen).
   - **Hlavička je nedôveryhodný vstup.** Každá dĺžka (u64) sa pred použitím porovná so zvyškom súboru – inak `f.read(10**18)` = `MemoryError` a počet kľúčov 2^63 = nekonečný cyklus. `seek` za koniec súboru nezlyhá, preto sa po preskočení poľa overuje pozícia. Pole polí a neznámy typ = `ModelFormatError` (llama.cpp ich tiež neprijme). Overené na 11 poškodených vstupoch, každý zlyhá do 0,1 ms.
   - Chyby: `ModelNotFoundError` (súbor/adresár), `ModelFormatError` (nie GGUF, odseknutý, poškodený), `ModelError` (iný `OSError`, napr. práva). Chýbajúci kľúč nie je chyba → `None`.
   - **`ModelMeta` zostáva v `core/settings.py`** (rozhodnutie autora), `core/gguf.py` ju importuje. Nové polia: `name` (`general.name`), `quant` (z `general.file_type` cez tabuľku `llama_ftype` – natvrdo v `gguf.py`, lebo `llama_cpp` sa importuje lenivo), `size_label`, `has_chat_template`, `n_head_kv`, `head_dim_k`, `head_dim_v`. Kľúče sú konštanty `META_*` v `core/constants.py` (poučenie z `context-length`, krok 3).
   - **Predvolené hodnoty ako llama.cpp:** bez `key_length` je rozmer hlavy `embedding_length / head_count` (Qwen 2.5 ho nemá: 1536 / 12 = 128), bez `head_count_kv` je kv hláv toľko ako hláv. `head_count_kv` ako pole (niektoré architektúry) sa preskočí → `head_count`.
   - **KV polia sa zatiaľ len ukladajú** (rozhodnutie autora), odhad príde so stránkou Vlastnosti. *Vzorec overený 2026-11-05 na M2 proti logu llama.cpp, `n_ctx=2048`:* `n_ctx × n_layers × n_head_kv × (head_dim_k + head_dim_v) × 2 B` (f16) → Qwen 56 MiB = 56 MiB, Gemma 272 MiB = 40 + 232 MiB (non-SWA + SWA; pri „full-size SWA cache“ sa SWA vrstvy počítajú plnou dĺžkou, takže vzorec platí).
   - **`mmproj` = `arch == "clip"`** – overené na `mmproj-google_gemma-3-4b-it-f16.gguf`: bez `n_ctx_train`, vrstiev aj chat template. Odmietnutie je v 5c.
   - **Doplnenie starých riadkov pri štarte** (rozhodnutie autora; krok počas splashu, nie pri otvorení menu – controller potrebuje `n_ctx_train` pri prvej správe, aj keď menu nikto neotvoril). **Bez čísla verzie:** číta sa znova, keď v `models.meta` chýba niektoré pole `ModelMeta` – nové pole = jedno prečítanie navyše, nič sa nemusí zvyšovať. Model bez súboru sa preskočí (menu: „súbor chýba“), nečitateľný = varovanie (toast) pri každom štarte, appka beží ďalej.
   - **Pasce pri prepise** (2026-11-05, zoznam v SESSIONS): **druhá metóda s rovnakým menom** (`Database.set_model`) – Python ticho nechá tú neskoršiu, takže pri novej metóde treba `grep "def meno"`; `read()` namiesto `read` v slučke načítalo celý 2,3 GB súbor; dva tiché preklepy v kľúčoch a poliach.
   **Kúsok 5c – modely v knižnici: sken, import, mazanie** (rozhodnutia autora 2026-11-04/05). Rozdelené na tri kúsky:
   **5c-1 – sken priečinka modelov pri štarte** (navrhnuté 2026-11-05 po autorovom teste: zmazaná `fukai.db` → nová prázdna databáza, modely v `models/` sa neobjavili; Claude napísal a otestoval v scratchpade, autor prepísal bez chýb, testy prešli nad repom). Súbory: `core/gguf.py` (`check_usable`), `core/constants.py` (`ARCH_PROJECTOR`), `storage/database.py` (`Database.created`), `ui/model_library.py` (`scan_folder`), `ui/application.py`. Testy: sken 11/11 (nová databáza, druhý štart, ručne pridaný a zmazaný súbor), regresia 5a/5b celá. Rozhodnutia:
   - **Sken pri každom štarte** (rozhodnutie autora – priečinok môže niekto upravovať ručne). Poradie štartu: databáza (vytvorí sa, keď chýba) → sken → doplnenie metadát (`refresh_meta`). **Mení §7.1:** tabuľka zostáva jediný zdroj pre menu, sken ju len dopĺňa o `.gguf`, ktoré v nej nie sú. Opačný smer sa nerobí – riadok, ktorého súbor zmizol, zostane a menu ukáže „súbor chýba“ (mazanie je 5c-3).
   - Známe súbory sa porovnajú len podľa názvu (`models.path` je relatívny), hlavička sa číta len novým – bežný štart stojí `iterdir()`. Prípona sa porovnáva bez ohľadu na veľkosť písmen (`glob("*.gguf")` by na POSIX vynechal `MODEL.GGUF`); `*.gguf.part` z nedokončeného importu má príponu `.part`, takže sa preskočí sám.
   - **`check_usable(meta)`** – spoločná kontrola pre sken aj import: `arch == "clip"` (mmproj), chýba architektúra alebo `block_count` (nie je to jazykový model), chýba chat template (§7 – bez neho by llama-cpp-python potichu použil náhradný formát). Vyhadzuje `ModelFormatError` s vlastnou správou a radou.
   - **Nevhodné súbory sa pri skene preskočia len do logu** (rozhodnutie autora) – mmproj tam môže byť oprávnene. Daň: čítajú sa pri každom štarte znova (pri mmproj ~1 ms, pri veľkom modeli bez template ~60 ms).
   - **Názov modelu = názov súboru bez prípony** (rozhodnutie autora; platí aj pre import) – rozlíši dve kvantizácie toho istého modelu, `general.name` nie.
   - Pribudnuté modely → jeden info toast so zoznamom názvov.
   - **Nová databáza vynuluje `last_model_id`.** Id sa v nej prideľujú odznova, takže staré číslo zo `settings.json` by mohlo ukazovať na **iný** model. `Database.created` = `connect()` práve vytvoril schému (`user_version` bol 0 – pokryje aj prázdny súbor, nielen chýbajúci).
   - `tools/dev_add_model.py` je so skenom zbytočný (stačí model skopírovať alebo nalinkovať do `models/`) – autor ho zmazal.
   **5c-2 – import** (navrhnuté 2026-11-05, Claude napísal a otestoval v scratchpade; autor prepísal všetko okrem `main_window.py`, Claude opravil 3 chyby a dokončil `main_window.py`; všetky testy prešli nad repom). Súbory: `ui/workers.py` (`ImportRequest`, `ImportWorker`), `ui/model_library.py` (`start_import`, `cancel_import`, `find_duplicate`, `shutdown`, signály `import_*`), `ui/toast.py` (režim priebehu), `ui/main_window.py` (dialóg, toast, výber), nový `ui/formatting.py` (`size_text` presunutý z composera – používa ho aj knižnica a toast), `ui/composer.py`, `ui/style.py`, `ui/application.py` (`library.shutdown()`), `core/errors.py` (`ModelImportError`), `core/constants.py` (`IMPORT_CHUNK_BYTES`, `IMPORT_FREE_MARGIN_MB`). Testy nad repom: `import_flow.py` 22/22 (9 scenárov), akcia v menu → dialóg → import 3/3 (`add_action.py`), sken 11/11, okno 14/14, výber modelu 7/7, controller, metadáta, self-test gguf. Rozhodnutia:
   - **Tok:** `QFileDialog` → v UI vlákne duplikát (názov súboru + veľkosť; riadok bez súboru duplikát nie je) a voľné miesto (model + 1 GB rezerva, `shutil.disk_usage`) – chyba sa ukáže hneď, bez toastu priebehu → **vo vlastnom vlákne** hlavička + `check_usable` → kópia po 8 MB do `*.gguf.part` → `fsync` → `os.replace` → v UI vlákne zápis do databázy. Databáza sa zo súbežného vlákna nevolá.
   - **Vlastné vlákno, nie vlákno modelu** – import nečaká na odpoveď a odpoveď na import; počas importu sa dá chatovať. Vlákno vznikne pri prvom importe. Naraz beží len jeden import – „Pridať…“ počas behu ukáže info toast.
   - **Zrušenie = `threading.Event` nový pre každý import**, nastavuje sa priamo z UI vlákna (signál by worker dostal až po konci kópie – tá istá pasca ako Stop, kúsok 4a). Kontroluje sa medzi kúskami a ešte raz pred premenovaním (✕ tesne po poslednom kúsku).
   - **`.part` sa maže až po zatvorení súboru** – Windows otvorený súbor zmazať nedovolí. Pri zrušení aj chybe kópie sa `.part` zmaže; pri páde appky zostane, ale má príponu `.part`, takže ho sken ignoruje (prepíše ho ďalší import toho istého súboru).
   - **Cieľové meno vyberá UI vlákno:** obsadené iným súborom → `-2`, `-3`…; riadok, ktorého súbor chýba, meno neblokuje – **import ho opraví** (ten istý riadok, id aj chaty zostanú, len `set_model_meta`).
   - Chyba zápisu do databázy po kópii → toast; súbor v knižnici zostane a sken ho pri ďalšom štarte zaregistruje.
   - **Toast priebehu:** `show_notice(..., progress=True)` – trvalý toast s pruhom (`toastProgress`, 4 px) a `set_progress(podiel, text)`; text nahradí hint („208 MB z 1017 MB“). **✕ = zrušiť import** (`closed` → `cancel_import()`, po dokončení neškodné). Koniec → info toast „Model je pridaný do knižnice“ / „Import modelu bol zrušený“ / chyba.
   - **Po importe sa model vyberie** (rozhodnutie autora), okrem chvíle, keď beží odpoveď – vtedy je len v menu. Duplikát → info toast a výber existujúceho.
   - **Akcia v menu spúšťa dialóg cez `QTimer.singleShot(0, …)`** – modálny dialóg otvorený priamo v `triggered` by bežal vo vnorenej slučke `menu.exec()`, ktoré sa práve zatvára.
   - **Zatvorenie appky počas importu:** `Application.shutdown()` → `library.shutdown()` (zruší, počká na vlákno – worker zmaže `.part`) **pred** `database.close()`. Namerané 6 ms.
   - **Overené autorom v živom okne na M2 (2026-11-05):** import cez natívny dialóg aj zrušenie krížikom počas kópie – v priečinku nezostal žiadny `.part`. Neoverené: zatvorenie appky počas importu v živom okne (len offscreen test, 8 ms) a Windows.
   - **Pasce pri prepise** (2026-11-05, zoznam v SESSIONS): `trigger` namiesto `triggered` a `emit()` so zátvorkami v odloženom volaní – **appka padala pri každom otvorení menu modelov**; chýbajúce `library.shutdown()` a QSS pruhu priebehu boli tiché.
   **5c-3 – mazanie** (rozhodnutia autora 2026-11-04; navrhnuté 2026-11-06, Claude napísal a otestoval v scratchpade; autor prepísal bez chýb a overil v živom okne na M2; Claude opravil kurzor nad riadkom menu; všetky testy prešli nad repom). Súbory: `ui/composer.py` (kôš v `_ModelRow`, signál `delete_model_requested`), `ui/main_window.py` (potvrdenie, poradie krokov), `ui/chat_controller.py` (`release_model`, `model_deleted`), `ui/model_library.py` (`model_path`, `delete_model`), `ui/llm_service.py` (`unload()` synchrónne), `ui/workers.py` (slot `unload` odstránený), `ui/style.py`. Test `delete_flow.py` 23/23 (8 scenárov), `row_cursor.py` 4/4, regresia celá (import 22/22, akcia v menu 3/3, okno 14/14, sken 11/11, výber modelu, controller). Rozhodnutia:
   - **Kôš v riadku menu len pod myšou** (`enterEvent` / `leaveEvent`), červená ikona `trash`.
   - **Kurzor ruky v menu cez `QApplication.setOverrideCursor`, nie `setCursor`** (zistené autorom 2026-11-06: nad košom zostala šípka). Príčina overená na M2 meraním `[NSCursor currentCursor]` cez Objective-C runtime (`ctypes`): `setCursor` v kľúčovom okne → ruka, **v `QMenu` → nie ruka**, override v `QMenu` → ruka. Menu je na macOS popup, ktorý nikdy nie je kľúčové okno, a cocoa plugin v ňom zmenu kurzora pri pohybe myši neuplatní (aktualizáciu kurzora si vynúti len pre kľúčové okno). Týka sa **celého riadku**, nielen koša – ruka nad riadkom predtým fungovala nanajvýš náhodou, keď myš vošla do menu priamo nad riadkom. `_ModelRow._set_hand()` nastaví override pri `enterEvent` a vráti ho pri `leaveEvent` **aj `hideEvent`** (menu zavreté klikom pod myšou leave nepošle); override je zásobník, preto príznak `_hand` – každé nastavenie sa vráti práve raz. Overené na cocoa aj offscreen (`row_cursor.py` 4/4). Platí pre každý budúci widget s vlastným kurzorom vnútri menu alebo iného popupu. Skrytý kôš si drží miesto (`setRetainSizeWhenHidden`), inak by text pri prechode myšou poskakoval. Klik na kôš model nevyberie – `QToolButton` udalosť spotrebuje, riadok `clicked` nedostane.
   - **Potvrdenie `QMessageBox` až po zatvorení menu** (`QTimer.singleShot(0, …)`, rovnako ako „Pridať“). Text podľa súboru: bežný („… a jeho súbor (1017 MB) sa zmaže z disku“), symlink („zmaže sa len odkaz, pôvodný súbor zostane“), chýbajúci („súbor už na disku nie je“). Predvolené tlačidlo je **Zrušiť**. `_confirm_delete()` je samostatná metóda, aby ju test vedel nahradiť.
   - **Poradie: pamäť → súbor → riadok.** Windows nezmaže súbor, ktorý llama.cpp drží cez mmap; keď zlyhá súbor, riadok zostane (inak by ho sken vrátil); keď zlyhá riadok, menu ukáže „súbor chýba“ a dá sa zmazať znova (`unlink(missing_ok=True)`). Orchestruje `MainWindow` – controller vie o pamäti a výbere, knižnica o súbore a riadku.
   - **`LlmService.unload()` je synchrónne** (dovtedy nepoužívané, išlo signálom do workera bez správy o dokončení). Mazanie potrebuje vedieť, že model je preč, **skôr** než siahne na súbor. Volanie engine z UI vlákna je bezpečné, lebo nečinná služba = worker nič nerobí a engine má aj vlastný zámok. Slot `LlmWorker.unload` sa tým stal mŕtvym kódom a je zmazaný.
   - **Uvoľňuje sa len mazaný model** – `release_model` porovná `LoadParams.model_path` s cestou modelu. Zmazanie iného modelu nechá načítaný model v pamäti (inak by ďalšia správa zbytočne čakala na reload).
   - **Po zmazaní:** `last_model_id` = mazaný → `None`; model zobrazeného chatu = mazaný → „Vyber model“. Chaty zostanú so správami, `model_id` je `NULL` (`ON DELETE SET NULL`), odoslanie v nich → „Najprv vyber model.“ Info toast „Model je zmazaný.“
   - **Počas odpovede sa mazať nedá** – tlačidlo modelu je vypnuté, takže sa menu ani neotvorí; `MainWindow` to po potvrdení kontroluje znova (odpoveď sa mohla rozbehnúť počas dialógu) a `release_model` pri `busy` vyhodí `RuntimeError`.
   - **Zlyhanie zmazania súboru** (overené na priečinku bez práva zápisu): toast „Súbor modelu sa nepodarilo zmazať.“ s cestou v hinte, riadok aj súbor zostanú, výber sa nemení. Model je vtedy už uvoľnený z pamäte – ďalšia správa ho načíta znova.
   - Overené autorom v živom okne na M2 (2026-11-06), vrátane potvrdzovacieho dialógu. Neoverené: Windows (mmap – na macOS sa dá zmazať aj namapovaný súbor, takže test poradie len kontroluje, nedokazuje).
   **Kúsok 6 – zoznam správ.** Rozdelený na **6a – obyčajný text** a **6b – markdown + `pygments`** (bloky kódu, „Kopírovať“). Rozhodnutia autora (2026-11-06): scroll počas generovania je **odomknutý**; uvítanie v prázdnom chate = logo + **jedna veta**, bez návrhov otázok.
   **6a – obyčajný text** (navrhnuté 2026-11-06, Claude napísal a otestoval v scratchpade; autor prepísal, Claude opravil 8 chýb, testy prešli nad repom). Súbory: nový `ui/message_list.py` (`MessageList`, `_TextView`, `_UserMessage`, `_AnswerMessage`), `ui/chat_view.py` (uvítanie, prepínanie prázdny chat / konverzácia, metódy pre správy), `ui/main_window.py` (signály controllera → `ChatView`), `ui/formatting.py` (`answer_meta`), `ui/constants.py`, `ui/style.py`. Testy: `stream_flow.py` 20/20 so skutočným Qwenom (streamovanie, scroll, Stop, návrat do bežiaceho chatu, koliesko), snímky offscreen aj cocoa v oboch témach, regresia celá. Rozhodnutia:
   - **Text správy je `QTextBrowser`, nie `QLabel`.** `QLabel` nevie zalomiť dlhé slovo bez medzier (URL, cesta) – bublina by pretiekla; v 6b navyše príde markdown a odkazy. Bez vlastného posúvania: výšku (bublina aj šírku) nastavuje `fit()` podľa dokumentu, posúva sa celý zoznam. Zalamovanie `WrapAtWordBoundaryOrAnywhere`.
   - **Bublina je široká len na text** (`idealWidth`), najviac 78 % stĺpca; odpoveď má celú šírku stĺpca mínus avatar. Stĺpec max 760 px, centrovaný rovnako ako composer.
   - **Streamovanie vkladá kúsok na koniec dokumentu** (`QTextCursor.insertText`), nie `setPlainText` celého textu – inak by sa pri každom tokene prerábal celý dokument. Tokeny sa zbierajú a vkladajú **najviac raz za 30 ms** (`STREAM_FLUSH_MS`) – každý vklad prepočíta výšku a posunie zoznam. Kurzor `▍` (farba `accent_strong`) je posledný znak, text sa vkladá pred neho s prázdnym formátom (inak by zdedil jeho farbu). Ukazuje sa hneď po odoslaní, teda aj počas načítania modelu.
   - **Po dobehnutí `show_answer()` nastaví celý text znova** z uloženej odpovede (zhoda s databázou, v 6b tu bude markdown) a pridá meta riadok.
   - **Meta riadok** (`answer_meta`): `model · 23 tok/s · 6,4 s`, pri `finish_reason == "length"` navyše „skrátená – dosiahnutý limit tokenov“. Model z `content.data` tej správy (§8 krok 9 – šablóna). Chýbajúce údaje sa vynechajú.
   - **Odomknutý scroll:** `_stick` = „som dole“ (do 24 px od spodku), prepočíta sa pri každej zmene hodnoty posuvníka; pri raste obsahu (`rangeChanged`) sa posunie dole len pri `_stick`. Vlastná otázka a otvorenie chatu prilepia vždy.
   - **Prázdny chat = jeden composer, iné medzery.** Uvítanie (logo z `.ico` – biela zaoblená dlaždica, 120 px, tieň) a zoznam sa prepínajú `setVisible`, dve `QSpacerItem` menia `changeSize` (Expanding / Fixed). Spodná má navyše 72 px, takže obsah je 36 px nad stredom ako v šablóne. Composer sa nepresúva medzi layoutmi, rozpísaný text prežije. Riadok „FUKAI môže robiť chyby“ je v prázdnom chate skrytý, ale **drží miesto** (`setRetainSizeWhenHidden`) – inak by bol zrezaný tieň composera.
   - **Návrat do chatu s bežiacou odpoveďou** funguje bez ďalšej logiky: controller pošle `chat_opened` (zoznam sa prekreslí), `turn_started` a doterajší text ako jeden `token`. `begin_turn` pri už rozbehnutom ťahu nerobí nič.
   - **Stop / chyba = zmiznú obe správy ťahu**; pri prvej správe nového chatu sa vráti uvítanie.
   - **Pasce zistené pri návrhu** (všetky overené snímkou alebo testom):
     - **`QScrollArea.setWidget()` zapne obsahu `autoFillBackground`** – vypnúť až **po** `setWidget`, inak má zoznam sivé pozadie namiesto prechodu panelu.
     - **`layout.takeAt()` / `removeWidget()` widget len vyberie z layoutu** – kým ho `deleteLater()` naozaj nezmaže, zostane viditeľný na starom mieste. Pri prepnutí chatu boli správy na snímke dvakrát. Pred `deleteLater()` → `hide()`.
     - **Písmo zo stylesheetu príde až pri polish** (zobrazenie, zmena témy). Rozmer bubliny spočítaný predtým bol pre menšie písmo – „Ok“ ukazovalo len „O“. `_TextView` si pamätá posledné `fit()` a zopakuje ho pri `FontChange` / `StyleChange`.
     - **Riadkovanie `ProportionalHeight` dáva Qt celé pod riadok** (CSS polovicu nad, polovicu pod). Namerané na M2: 14 px písmo, riadok 17 → 25,5 px, 8,5 px pod textom. Bublina s jedným riadkom mala dole o 8 px viac. Widget je preto o túto medzeru nižší a `setViewportMargins(0, 0, 0, -medzera)` nechá viewport plnej výšky – inak by sa text dal o 8 px posúvať.
     - **Umelá udalosť kolieska (`sendEvent`) sa rodičom neposiela** – Qt propaguje len spontánne udalosti od systému. Test preto overuje zvlášť, že text udalosť odmietne a že zoznam sa ňou posunie. `_TextView.wheelEvent` volá `ignore()`, aby koliesko nad textom posúvalo zoznam.
     - **Snímka okna v teste musí počkať, kým je okno zobrazené** (`QTimer` 4,5 s namiesto 2,6 s – splash trvá 2 s + štart). `grab()` skrytého okna vykreslí zastaraný layout.
   - **Pasce pri prepise** (2026-11-06, zoznam v SESSIONS): pri úprave bloku signálov **zmizol susedný `connect`** (composer by nevyprázdnil pole ani neukázal Stop) – porovnávať `git diff`, nie len to, čo pribudlo; k tomu tri pády na preklepoch a atribút vs metóda líšiace sa podčiarkovníkom.
   - **Odozva UI počas generovania:** 50 ms časovač tikal s najdlhšou medzerou 50–60 ms počas tokenov. **Pred prvým tokenom** (worker skladá prompt, 16 správ histórie) boli medzery do ~150 ms, raz 300 ms. Zoznam správ vtedy nič nerobí – príčina je pravdepodobne GIL držaný Pythonom v llama-cpp-python (šablóna, tokenizácia), **neoverené**. Ak bude na PC alebo pri dlhej histórii vidno zasekávanie, začať tu.
   - Neoverené: kontextové menu textu (Kopírovať / Označiť všetko) je po anglicky – Qt bez prekladov; vyriešiť spolu s 6b alebo neskôr. Windows.
   **Poznatky z testu na notebooku** (2026-11-06, Windows, i7-11850H + T1200 4 GB, §4) – *všetky spracované, zostáva posledný bod:*
   - **Opravené (`f2a1772`):** priebeh importu ukazoval pri modeli nad 2 GiB záporné čísla – `pyqtSignal(int, int)` prenáša 32-bitový C++ `int`, takže bajty nad 2^31 pretečú. Oprava je `pyqtSignal("qint64", "qint64")` na oboch miestach (§8.2). `import_flow.py` to neodhalil, lebo kopíruje malé súbory.
   - **Overené bez llama-cpp-python** (appka vtedy ešte nabehla a hlásila toast; od kúska „Engine pri štarte“ je to fatálna chyba) **a s CPU wheelom 0.3.36** bez CUDA Toolkitu: import, odpoveď, Gemma 3 4B Q4_K_M **13–14 tok/s**, CPU v špičke 60–75 %. Falošné varovanie o VRAM pri CPU builde na stroji s NVIDIA kartou vyriešil `llama_supports_gpu_offload()` pri štarte.
   - **Otvorené: CUDA wheel na T1200 (sm_75) neskúšaný** – ovládač 595.95 podporuje CUDA 13.2, Toolkit nie je nainštalovaný. Požiadavka autora: **používateľ nesmie musieť inštalovať CUDA Toolkit zvlášť** – vyriešiť počas vývoja, nie až pri balení (§10: priložiť `cublas64_13.dll` + `cublasLt64_13.dll`, ~507 MB, alebo iná cesta).
   **Engine pri štarte + 64-bit priebeh importu** (navrhnuté 2026-11-06 po teste na notebooku; Claude napísal a otestoval v scratchpade `run12`; autor prepísal bez chýb, test aj regresia prešli nad repom). Súbory: `core/llm_engine.py` (`EngineInfo`, `probe_engine()`, `_import_llama`, `_memory_pool`), `core/hardware.py` (`HardwareProfile.gpu_offload`, `backend`, `n_gpu_layers`, `detect(gpu_offload=)`, `check_gpu`), `core/errors.py` (rada `BackendUnavailableError`), `ui/application.py` (krok štartu „Spúšťam engine…“), `ui/chat_view.py` (čip), `ui/workers.py` + `ui/model_library.py` (`"qint64"`). Test `t14/engine_probe.py` v 4 scenároch (Metal, CPU-only build na stroji s GPU, chýbajúca knižnica, nenačítateľná DLL) – všetko OK; regresia: `stream_flow` s Qwenom, mazanie, import 22/22, akcia v menu 3/3, sken 12/12. Rozhodnutia:
   - **Engine je súčasť štartu, bez neho appka nebeží** (rozhodnutie autora). `probe_engine()` naimportuje `llama_cpp` počas splashu (na M2 0,35 s – presúva sa sem z prvej správy) a vráti `EngineInfo(version, gpu_offload)`. `BackendUnavailableError` je `FukaiError`, takže ju zachytí existujúca vetva v `Application.run()` → fatálny dialóg, kód 1, okno nevznikne. Dovtedy appka bez knižnice nabehla a chyba prišla až toastom pri odoslaní.
   - **Dve rôzne správy:** knižnica chýba (`ImportError`) → „Engine pre spúšťanie modelov nie je dostupný.“ + rada nainštalovať podľa requirements; knižnica je, ale jej DLL sa nenačíta → „Engine pre spúšťanie modelov sa nepodarilo spustiť.“ + rada o CUDA Toolkite / CPU verzii. **Pasca overená v zdrojákoch 0.3.36 (`_ctypes_extensions.py`):** zlyhanie `ctypes.CDLL` knižnica prebalí na **`RuntimeError`** („Failed to load shared library …“), nie `OSError` – pôvodné `except (ImportError, OSError)` ho nezachytilo a CUDA wheel bez Toolkitu by skončil ako všeobecná chyba načítania modelu.
   - **`HardwareProfile.backend` = na čom sa naozaj generuje**, nie len čo je v stroji. Nové pole `gpu_offload` (predvolene `True`, aby `python -m core.hardware` fungoval bez enginu); grafika, ktorú engine nevie použiť, sa ráta ako `cpu` → `n_gpu_layers = 0`, čip „CPU · 64 GB RAM“ (v tooltipe, že GPU sa nepoužíva), splash „Pripravené · CPU“. `gpu` zostáva vyplnené – na diagnostiku a varovanie. **`hardware.py` llama-cpp-python neimportuje** (detekcia nikdy nevyhodí výnimku, krok 2); príznak dostane ako argument `detect(gpu_offload=…)`, preto je poradie štartu nastavenia → engine → hardvér.
   - **`check_gpu`: GPU je, engine ju nevie použiť → varovanie** „Grafická karta … sa nepoužije, model pobeží na CPU.“ s radou podľa typu (CUDA verzia + Toolkit / build s Metal). Nie fatálne – na CPU sa chatovať dá.
   - **`_memory_pool` dostáva `gpu_offload` od enginu** (`llama_supports_gpu_offload()` v `load()`), nie z profilu. Chaty vytvorené predtým majú v `properties` uložené `n_gpu_layers=-1`; CPU build ho ignoruje, ale varovanie by počítalo s VRAM. Pri CPU builde sa `detect_gpu()` ani nevolá.
   - **`"qint64"` v signáloch s bajtmi** – pozri chybu vyššie.
   **Test celej appky na PC 1 (Windows 11, RTX 5060 Ti 16 GB, CUDA Toolkit 13.0, driver 621.14) – 2026-11-06.**
   Stav repa `41b9375`, `FUKAI_HOME=devdata`, Python 3.12.10 + PyQt6 6.11.0 + llama-cpp-python 0.3.36 CUDA.
   Testovalo sa **v živom okne na platforme `windows`** (nie offscreen – inak sa neoverí Fusion, priehľadné menu ani natívny dialóg); appku riadili skripty v scratchpade cez skutočné signály UI, nie obídením vrstiev. **Prešlo všetko, v kóde sa nenašla ani jedna chyba.**

   **Prešlo všetko, v kóde sa nenašla ani jedna chyba** – 20 overených oblastí (štart a detekcia CUDA, ikona na paneli úloh, rozostupy Fusion, sken a import vrátane 4,1 GB a zrušenia, zaoblené menu s kurzorom ruky, natívny dialóg, chat a streamovanie, scroll a koliesko, zalomenie dlhého slova, Stop, prepnutie chatu počas odpovede, skrátená odpoveď, mazanie modelu s mmap, obe cesty ukončenia). **Úplná matica výsledkov je v `SESSIONS.md`**, tu zostávajú čísla a zistenia, ktoré platia ďalej.

   **Výkon na GPU** (`n_ctx=4096`, `n_gpu_layers=-1`; VRAM je celé GPU, z toho ~1,3 GB držia iné aplikácie):

   | Model | Načítanie | Prvý token | Rýchlosť | VRAM spolu |
   |---|---|---|---|---|
   | Gemma 3 4B Q4_K_M | 1,8 s | 0,44–0,51 s | **107 tok/s** | 4 692 MiB |
   | Mistral 7B Q4_K_M | 2,2 s | 0,50 s | **77 tok/s** | 6 211 MiB |

   Mistral je rýchlejší než 66,9 tok/s nameraných konzolovo 2026-11-01 (odvtedy novší ovládač). Dlhá odpoveď na 1 023 tokenov (`length`) bežala 94 tok/s.

   **Odozva UI je na PC 1 lepšia než na Macu.** 50 ms časovač: počas generovania medzery 50–63 ms, okolo načítania modelu jednorazovo 156–234 ms. **V dlhom chate (16 správ, prompt 1 803 tokenov) bola najdlhšia medzera pred prvým tokenom 63 ms** a prvý token prišiel po 0,33 s – podozrenie na GIL z kúsku 6a sa tu neprejavilo. Buď je to vlastnosť Macu, alebo to rýchlejší stroj prekryje.

   **Zistenie: počas načítania modelu je celá appka nemá.** `llama-cpp-python` obalí `Llama(...)` pri `verbose=False` manažérom `suppress_stdout_stderr` (`llama_cpp/_utils.py`), ktorý cez `os.dup2` presmeruje **deskriptory 1 a 2 celého procesu** na devnull a vymení aj `sys.stdout` / `sys.stderr`. Načítanie beží vo workeri, takže v tom okne mlčí **aj UI vlákno**: `print`, `Notice.log_line()` aj traceback neodchytenej výnimky sa stratia. Overené meraním – sloty naplánované na čas načítania **naozaj bežali** (zapísali sa do zoznamu), nebolo vidieť len ich výpis; práve toto zdržalo test, lebo to vyzeralo ako nefunkčné časovače. Dôsledky: (1) čokoľvek, čo sa ladí počas načítania, treba písať do súboru, nie na konzolu; (2) logovanie do súboru v kroku 14 nesmie ísť cez `sys.stdout` / `sys.stderr`, inak v ňom budú chýbať práve riadky z načítavania.

   **Warm-up po štarte systému sa zopakoval, príčina stále neoverená.** Úplne prvé načítanie modelu po zapnutí PC generovalo **6,3 tok/s** (56 tokenov za 8,8 s), každý ďalší beh 107 tok/s; samotné načítanie bolo normálne (1,8–2,1 s). Oproti §3 (2026-10-28) to tentoraz nebol pomalý `prompt eval`, ale pomalé generovanie. `%LOCALAPPDATA%\NVIDIA\ComputeCache` **naďalej neexistuje**, takže PTX JIT sa ani teraz nepotvrdil. Pre UI platí to isté: prvé načítanie po štarte systému môže byť citeľne pomalšie.

   **Pasca pri písaní testov (nie v appke):** `QTimer.singleShot(ms, obj.metóda)` drží na `obj` **slabú referenciu**, keď `obj` nie je `QObject` – len čo testovací objekt stratí inú referenciu, časovač ticho nič nezavolá. Testovací objekt treba držať v globále.

   **Kúsok 6b – markdown (2026-11-06, hotové).** Rozhodnutia autora: markdown sa renderuje **až po dobehnutí odpovede** (počas streamovania zostáva obyčajný text), kód ide do **samostatného okna so stropom 400 px** a vlastným zvislým posuvníkom, **široká tabuľka dostane tiež vodorovne posúvateľné okno** a farby kódu sú **vlastná paleta z tokenov FUKAI**, nie hotová téma pygments. Rozsah: bloky kódu, tabuľky, tučné, kurzíva, UL, OL.

   **Odpoveď prestala byť jeden dokument.** `_AnswerMessage` je zvislý zoznam častí: text → `_TextView` so `setMarkdown`, blok kódu → `_CodeBlock`, tabuľka → `_TableBox`. Dôvod je tvrdý: Qt rich text **nevie vodorovný posuvník vnútri dokumentu ani vložené tlačidlo**, takže „okno s kódom, scroll doboku a Kopírovať v hlavičke“ sa do `QTextBrowser`-u nedá vložiť. Tým **padá pôvodný plán zo šablóny** („bloky kódu ako tabuľka s `bgcolor` a `cellpadding`, Kopírovať ako odkaz `copy:N` + `anchorClicked“`).

   Hranica modulov: nový **`ui/markdown.py`** nevie o widgetoch – `Part(kind, content, language)`, `split_markdown(text) -> list[Part]`, `code_html(code, language, theme)`, `style_tables(doc, theme)`. Widgety (`_Body`, `_CodeBlock`, `_TableBox`) sú v `ui/message_list.py`, `CODE_MAX_HEIGHT = 400` v `ui/constants.py`. Poradie kúskov: **6b-1** `split_markdown` + testy (fence, neuzavretý fence, tabuľka), **6b-2** paleta a `code_html`, **6b-3** `_CodeBlock`, **6b-4** `_TableBox` + `style_tables`, **6b-5** zapojenie do `_AnswerMessage.show_answer()` a `set_theme`.

   **Overené prototypom na PC 1** (`p2_blocks.py` v scratchpade, obe témy): `setMarkdown` s `MarkdownDialectGitHub` dá tučné, kurzívu, inline kód, UL aj vnorené, OL aj tabuľku vrátane zarovnania stĺpca cez `---:`; tabuľka sa dá doštylovať `QTextTableFormat` (border 1, `cellPadding 6`, `cellSpacing 0`, `headerRowCount 1`, hlavička `chip`); riadok kódu 776 px v okne 700 px vyrobí vodorovný posuvník (12 px), 40 riadkov kódu narazí na strop (400 + 30 px hlavička) a dostane zvislý posuvník; široká tabuľka `idealWidth` 896 px → vodorovný posuvník; Kopírovať vloží do schránky presne surový kód a tlačidlo sa prepne na „Skopírované“.

   **Pasce, všetky namerané pri prototype:**

   - **Bez `MarkdownNoHTML` Qt interpretuje surové HTML a ticho zje zvyšok odseku.** Vstup `Text <b>html</b> a <img src="…"> koniec.` sa vykreslí ako `Text html a ` – zvyšok vety zmizne. Stačí jedno `<` v odpovedi (porovnanie `a < b`, C++ šablóny, ukážka HTML mimo bloku kódu). Riešenie: `MarkdownDialectGitHub | MarkdownNoHTML`; tabuľky a zvyšok fungujú ďalej. Pozor, GitHub dialekt `NoHTML` **neobsahuje** (0x104f0c & 0x60 == 0).
   - **Nefarebné tokeny z pygments dedia farbu textu widgetu.** `HtmlFormatter` obalí `<span style="color:…">` len tie tokeny, ktoré téma farbí – ostatné zdedia farbu widgetu a pri nesprávnej farbe je polovica kódu neviditeľná (overené). Kódové okno musí mať `color` nastavenú explicitne v HTML aj v QSS.
   - **`QColor("rgba(13, 30, 72, 0.07)")` je neplatná farba** → pozadie hlavičky tabuľky vyšlo čierne. Na tokeny s `rgba()` treba `qcolor()` zo `style.py` – tá istá pasca ako pri tieni a placeholderi v kúsku 5a.
   - **Po `setMarkdown` zostane široký dokument odrolovaný takmer na koniec** (namerané `h = 192/196`), takže z tabuľky vidno posledné stĺpce. Po renderi nastaviť oba posuvníky na 0.
   - **Rozmery sa musia počítať až po polish** – písmo zo stylesheetu príde neskôr a prvá časť bola inak orezaná. Platí pre každú časť, nielen pre `_TextView` (pasca z 6a).
   - **Koliesko nad kódom so stropom** musí posúvať kód, kým je kam, a potom udalosť `ignore()`-núť, aby posúvala zoznam správ. Inak sa buď nedá prejsť kódom, alebo sa nedá prejsť chatom.
   - **QLabel v hlavičke kódu potrebuje priehľadné pozadie** – v prototype s blanket pravidlom `QWidget { background }` prekryl hlavičku farbou stránky. V QSS appky to rieši globálne `QLabel { background: transparent; }`.

   **Čo sa tým stráca:** výber textu myšou cez viac častí (každá časť je vlastný `QTextBrowser`) a zmena témy musí kód prerenderovať, lebo farby sú zapečené v HTML.


   **Hotové 2026-11-06 (kúsky 6b-1 až 6b-5).** `ui/markdown.py` navrhol a napísal Claude do scratchpadu, autor ho prepísal a konštanty presunul do `ui/constants.py` (`PLAIN`, `CODE_FONT`, `CODE_FONT_SIZE`, `TABLE_PADDING`, `TABLE_BORDER`); Claude opravil tri chyby prepisu a dorobil widgety, QSS a zapojenie. Súbory: nový **`ui/markdown.py`**; **`ui/message_list.py`** (`_Body`, `_CodeBlock`, `_TableBox`, `_TextView.set_markdown`, prestavaný `_AnswerMessage`); **`ui/constants.py`** (`CODE_MAX_HEIGHT = 400`, `CODE_HEAD_HEIGHT = 30`, `BOX_MARGIN`, `CODE_NO_LANGUAGE`, `COPY_LABEL`, `COPY_DONE_LABEL`, `COPY_RESET_MS`); **`ui/style.py`** (token `code_scroll`, pravidlá vodorovného posuvníka, QSS blokov).

   Rozhodnutia, ktoré pribudli až pri písaní:

   - **`_AnswerMessage.text` žije len počas streamovania, potom je `None`.** Po dobehnutí ho nahradia časti, takže čokoľvek, čo po skončení odpovede siahne na `.text`, dostane `None` (zakoplo o to aj `t3b`). Streamovací `_TextView` sa preto vyrába až v `start()` – načítanie starého chatu ho vôbec nepotrebuje.
   - **Pozadie kódového okna kreslí rámec `#codeBlock`, telo je priehľadné.** `border-radius` nadradeného widgetu neoreže deti (§8 krok 9 – šablóna), takže keby pozadie kreslilo telo, zaoblené rohy by boli dole hranaté. K tomu patrí `viewport().setAutoFillBackground(False)` – tá istá pasca ako pri `MessageList` v 6a.
   - **`_Body.reset_view()` po každom `setHtml` / `setMarkdown`.** Kurzor zostane na konci dokumentu a pohľad za ním odskočí – pri širokej tabuľke potom vidno posledné stĺpce. `setValue(0)` to nespraví, lebo v tej chvíli ešte neexistuje rozsah posuvníka; treba presunúť kurzor na začiatok.
   - **Koliesko nad kódom** posúva kód, kým je kam, inak udalosť `ignore()`-ne a posúva sa zoznam správ.
   - **Tabuľka má strop výšky ako kód** (`CODE_MAX_HEIGHT`), aby dlhá tabuľka nevytlačila zvyšok odpovede.

   **Chyba, ktorú odhalila až regresia: po dobehnutí odpovede zoznam odskočil dole, aj keď používateľ čítal vyššie.** Prestavba na časti obsah nakrátko zmenší (staré widgety preč, nové ešte nie), rozsah posuvníka spadne na nulu, `_on_value_changed` to vyhodnotí ako „som dole“ a `_on_range_changed` potom pri náraste skočí na koniec. Prejavovalo sa to **občas** – podľa toho, či sa odpoveď dokončila, kým bol zoznam odrolovaný. Opravené dvojako: `_on_value_changed` sa pri `maximum <= 0` neprepisuje (vtedy niet čo posúvať, takže „som dole“ nemá novú informáciu) a `finish_turn` si pred prestavbou zapamätá pozíciu a po nej ju vráti, keď sa zoznam nedrží spodku. Overené deterministicky mimo modelu (`t11_finish_scroll.py`) aj dvoma behmi `t3c`.

   **Pasce v prepise `markdown.py`** (2026-11-06, našiel self-test): `def _close(...)` pri volaní `_closes(...)` → `NameError` pri každom bloku kódu; `table.setFormat(table)` namiesto `frame.setFormat(table)` – formát sa nastavuje tabuľke v dokumente, nie formátu samému sebe, a chýbala k tomu farba rámu (`setBorderBrush`) a `setBorderCollapse`; kozmeticky `rows. append` a `formartter`.

   **Testy** (všetky nad repom na PC 1): `python -m ui.markdown` 24 kontrol; `t8_markdown_ui.py` 20 kontrol nad skutočnými widgetmi (poradie častí, posuvníky, strop, kopírovanie, prepnutie témy, streamovanie → dokončenie, Stop); `t11_finish_scroll.py` (pozícia po dokončení); regresia `t3c` 9/9 dvakrát, `t3b` 19/19, `t9_live_markdown.py` so skutočnou odpoveďou Gemmy – odpoveď sa rozdelila na `_TextView, _CodeBlock, _TextView, _TableBox`, meta `81 tok/s · 3,7 s`.

   **Čo zostáva otvorené:** výber textu myšou cez viac častí nejde (každá časť je vlastný `QTextBrowser`); tabuľka vnorená v odrážke zostane v textovej časti a nedostane rám (`style_tables` sa volá len nad `_TableBox`); podfarbenie hlavičky tabuľky je `chip`, teda jemné – ak bude treba výraznejšie, patrí to do `THEMES`.

   **Kúsok 3b – menu ⋯ pri chate ✅** (navrhnuté a napísané 2026-11-07, Claude; testy prešli nad repom na PC 1; commit `cbfa5c5`). Tlačidlo ⋯ pod myšou → `QMenu` s veľkosťou chatu v tokenoch, Premenovať (pero) a Vymazať (kôš); premenovanie je vstup priamo v riadku a ⋯ sa v ňom zmení na ✓. Súbory: `ui/sidebar.py` (`_ChatRow`, menu, edit režim), `ui/main_window.py` (sloty rename/delete), `ui/chat_controller.py` (`turn_chat_id`), `ui/formatting.py` (`tokens_text`), `ui/style.py` (`#chatRow`, `#chatEdit`, `#chatMore`, `#chatMenu`), `ui/constants.py` (`CHAT_ITEM_SPACING`, `CHAT_ROW_BUTTON`, `CHAT_MENU_WIDTH`). Rozhodnutia:
   - **Riadok prestal byť kreslený text a stal sa widgetom v položke** (`setItemWidget`) – do kresleného itemu sa tlačidlo ani vstup dať nedá. Tri dôsledky, všetky overené: `itemClicked` sa už nevyšle (widget udalosť spotrebuje – tá istá pasca ako `QWidgetAction` v menu modelov, 5a), takže `_ChatRow` má vlastný `clicked`; **`::item:hover` a `::item:selected` prestali platiť** (hover state ide na widget, nie na index) → `SelectionMode.NoSelection`, pozadie kreslí `QFrame#chatRow:hover` a `[active="true"]`, ktorú prepína `select_chat()`; **elide treba ručne** (`QFontMetrics.elidedText` v `resizeEvent` **a `changeEvent`** – písmo zo stylesheetu príde až pri polish, pasca z 6a). Elide počíta so šírkou skrytého ⋯ (`setRetainSizeWhenHidden`), inak by text pri prechode myšou poskakoval.
   - **Veľkosť chatu sa číta pri otvorení menu, nie pri `set_chats`** – `Sidebar.set_token_source(database.content_tokens)`, vzor `Composer.set_model_source` z 5a. Číslo je tak vždy čerstvé, sidebar ďalej nevie o databáze a nerobí sa N dotazov pri každom reloade zoznamu.
   - **Label je `~1 234 tokenov`** (rozhodnutie autora). Vlnka preto, že je to spodná hranica: tokeny otázok sú do dopočítania `NULL` (§7.2) a `content_tokens()` ich nezapočíta. Nula je legitímna – po výmene modelu sa `content.tokens` nuluje – preto pri nule text „tokeny sa dopočítajú“, nie „~0 tokenov“. Skloňovanie 1 / 2–4 / 5+ je v `tokens_text`.
   - **✓ má `FocusPolicy.NoFocus`** – inak by si klik naň vzal fokus vstupu, `focusOut` by premenovanie zrušil a tlačidlo by nikdy nepotvrdilo. Escape a strata fokusu rušia, Enter a ✓ potvrdzujú; prázdny alebo nezmenený názov sa nezapíše.
   - **Signály z riadku idú odložene cez `QTimer.singleShot(0, …)`** – premenovanie aj mazanie prestavia zoznam, teda zmažú widget, ktorého signál práve beží. Tá istá príčina ako pri dialógoch spúšťaných z `QMenu` v 5c-2.
   - **⋯ sa neskryje, kým je otvorené menu** (`set_menu_open`) – myš odíde z riadku do menu, príde `leaveEvent` a tlačidlo by zmizlo pod otvoreným menu.
   - **Premenovanie nemení `updated_at`** (overené) – nie je to zmena obsahu, takže sa poradie v sidebare nepreskupí; rovnaká úvaha ako pri `set_message_tokens` (krok 8). Poradie sa pri zhodnom `updated_at` riadi `title ASC`, takže v teste s chatmi z tej istej sekundy premenovanie poradím pohne – v reálnych dátach nie.
   - **Mazanie je bez potvrdenia** (rozhodnutie autora) a **chat, do ktorého beží odpoveď, sa zmazať nedá** (rozhodnutie autora) – toast „Počas odpovede sa chat zmazať nedá.“ Tým padá alternatíva zahodiť ťah; kontroluje sa per chat (`ChatController.turn_chat_id`, nie `busy` + `chat_id` – odpoveď môže dobiehať do iného chatu, než je zobrazený), takže mazanie ostatných chatov počas generovania ide. Zmazanie otvoreného chatu prepne na nový chat.
   - Zápis robí `MainWindow` (`rename_chat` / `delete_chat` v `try/except FukaiError`), sidebar len vysiela `chat_rename_requested` / `chat_delete_requested` – rovnaká hranica ako pri mazaní modelu v 5c-3.
   - **Pasca v testoch (nie v appke): `widget.event(...)` obchádza event filtre.** Escape aj `FocusOut` edit režimu idú cez `eventFilter`, takže umelá udalosť poslaná priamo cez `event()` sa k nim nedostane a test hlási, že edit režim neskončil. Posielať cez `QApplication.sendEvent`. Doplnok k pasci z 6a (umelá udalosť kolieska sa naopak rodičom nepropaguje).
   - **Testy** (scratchpad, PC 1): `t1_chat_menu.py` 47 kontrol offscreen (hover, menu, meta label, premenovanie Enterom / ✓ / Escape / focusOut / prázdny názov, klik v edit režime, mazanie iného aj otvoreného chatu, mazanie počas odpovede, prázdny zoznam, prepnutie témy); `t2_live.py` 18 kontrol na platforme `windows` so snímkami menu a edit režimu v oboch témach (kurzory, geometria, pozícia menu); regresia – skutočná appka nad `devdata` (23 chatov, scrollbar, hover).
   - **Zostáva otvorené:** klávesová navigácia zoznamu (šípky) zanikla spolu so `SelectionMode` – nebola zapojená ani predtým; zoznam sa neroluje na aktívny chat po `select_chat` (pri 23 chatoch v `devdata` zatiaľ netreba).

   **Kúsok 7 – monitor vyťaženia ✅** (návrh `semestralka/UI/power_monitoring.png` na OneDrive; napísané 2026-11-07, Claude; testy prešli nad repom na PC 1; commit `05e727f`). Klik na čip hardvéru v hlavičke zobrazí a skryje panel s tromi riadkami vľavo od čipu. Súbory: nový **`core/monitor.py`** (`Usage`, `UsageMonitor`, self-test `python -m core.monitor [počet vzoriek]`), nový **`ui/usage_panel.py`** (`UsagePanel`), `ui/chat_view.py` (`_HwChip` so signálom `clicked`), `ui/main_window.py` + `ui/application.py` (služba a jej `close()`), `ui/style.py`, `ui/constants.py` (`USAGE_INTERVAL_MS = 1000`, `USAGE_WIDEST`).
   - **Obsah riadkov je rozhodnutie autora:** CPU vždy; GPU vždy, ale bez detegovanej karty ukáže `0 %`, nie pomlčku; tretí riadok je **VRAM len pri backende s vlastnou pamäťou** (`backend == "cuda"` a známa `vram_total_mb`), inak **RAM**. Na Apple Silicon je teda tretí riadok RAM – GPU tam berie z tej istej pamäte (§4). Na stroji s NVIDIA kartou a CPU wheelom je to tiež RAM, lebo model vtedy beží v RAM.
   - **Namerané na PC 1:** `nvmlInit()` 17 ms jednorazovo, vzorka (utilization + memory + CPU) **0,25 ms**, takže vzorkovanie beží v UI vlákne cez `QTimer`, bez workera. `psutil.cpu_percent(interval=None)` je priemer od posledného volania, teda nečaká; prvé volanie vracia 0 %, preto je „priming“ v konštruktore.
   - **NVML je lenivý a po prvom zlyhaní sa už neskúša** (`_nvml_dead`) – inak by sa pri každom tiku chytala tá istá výnimka. `hardware.py` ďalej používa `nvidia-smi`; na sekundové vzorkovanie sa subprocess nehodí, na jednorazovú detekciu pri štarte áno, takže obe cesty zostávajú.
   - **macOS GPU % je jediná neistá časť.** Metal nemá verejné API na vyťaženie a `powermetrics` chce root; zostáva `ioreg -r -d 1 -c IOAccelerator` a kľúč `"Device Utilization %"` (fallback `"GPU Activity(%)"`). Je to subprocess za desiatky ms, takže sa naň **nečaká**: `sample()` výsledok predchádzajúceho behu vyzdvihne a hneď spustí ďalší. Číslo je o jeden tik staršie (pri sekundovom monitore nevadí) a UI nezamrzne ani raz – bez vlákna a bez Qt v `core/`. **Neoverené na Macu**, autor doladí na M2; keď kľúč nesedí, GPU riadok ukáže pomlčku.
   - **RAM % cez `hardware.free_ram_mb()`, nie `psutil.virtual_memory().percent`** – appka na tom istom čísle stavia varovania pred načítaním modelu a na macOS je psutil mimo (§4). Monitor tak nemôže ukazovať niečo iné než to, čím sa appka riadi.
   - **Zásada `core/hardware.py` platí aj tu: sonda nikdy nevyhodí výnimku von.** Nezistená hodnota je `None` a UI ukáže pomlčku.
   - **Časovač beží len kým je panel viditeľný** – vypnutý monitor nestojí nič a `nvmlInit` sa odloží až na prvé zapnutie. `setVisible` je prepísané, takže sa to nedá obísť ani priamym volaním.
   - **Panel má pevnú šírku** spočítanú z `fontMetrics` najdlhšieho možného textu (`VRAM: 100 %`), prepočítanú pri `FontChange`/`StyleChange` – inak by pri každom tiku menil šírku a ťahal za sebou celú hlavičku. (Písmo zo stylesheetu príde až pri polish, pasca z 6a.)
   - **`UsageMonitor` je služba `Application`** a `shutdown()` ju zatvára (`nvmlShutdown`, prípadne zabitie bežiaceho `ioreg`) – rovnaká hranica ako `LlmService` a `ModelLibrary`. `close()` je idempotentné.
   - **Overené pri skutočnom generovaní** (Gemma 3 4B, 107 tok/s): GPU vyskočilo na **87–89 %**, VRAM z 9 % na **31 %** (načítanie modelu), CPU 9–10 %. Kontrolný 50 ms časovač mal počas odpovede najdlhšiu medzeru **78 ms** (bez monitora 50–63 ms, §8 krok 9 – test na PC 1), takže vzorkovanie odozvu UI nezhoršuje.
   - **Pasca:** `HardwareProfile.backend` je **odvodená vlastnosť, nie pole** – `dataclasses.replace(hw, backend="cpu")` je `TypeError`; stroj bez GPU sa v teste vyrobí ako `replace(hw, gpu=None)`.
   - **Testy:** `python -m core.monitor`; `t4_usage.py` 21 kontrol (toggle, časovač, tri riadky, stabilná šírka, pomlčky, vzorka pod 5 ms, stroj bez GPU, dvojité `close()`), aj naživo na platforme `windows` so snímkou; `t5_under_load.py` so skutočnou odpoveďou.
   - **Nerozhodnuté:** zapnutý monitor sa **nepamätá medzi spusteniami** (po štarte je vypnutý). Keby sa mal pamätať, je to jeden kľúč v `settings.json` (§7.1 – chýbajúci kľúč = predvolená hodnota, žiadna migrácia).

   **Kúsok 8 – stránka Nastavenia aplikácie ✅** (2026-11-07; Claude dával podklady súbor po súbore, autor prepisoval, Claude po ňom opravoval; testy prešli nad repom na PC 1; commit `a77b3d5`). Podľa aktualizovanej šablóny `semestralka/UI/template/` na OneDrive, ktorá už stránku Nastavenia obsahuje. Tri karty: Vzhľad (tmavý vzhľad), Funkcie chatu (web, prílohy), Modely (cesta + zoznam nájdených). Súbory: nový **`ui/toggle_switch.py`**, nový **`ui/settings_view.py`**, `ui/style.py` (QSS stránky), `ui/constants.py`, `ui/composer.py` (`set_features`, `set_web`, signály `attach_requested` / `web_toggled`), `ui/main_window.py` (stránka, zápis, téma), `ui/application.py` (`_ensure_models_dir`, `_set_theme`), `ui/formatting.py` (presun `model_subtitle`), 4 nové ikony v `assets/icons/` (`moon`, `clip`, `folder`, `cube`).
   - **„Otvoriť priečinok“, nie „Vybrať priečinok“** (rozhodnutie autora, jediný odklon od šablóny). Cestu si aplikácia určuje sama (§7.1), používateľ ju nemení – tlačidlo len otvorí Prieskumníka/Finder cez `QDesktopServices.openUrl(QUrl.fromLocalFile(...))`, čo je jedna cesta pre oba OS. Pred otvorením `ensure_dir()`, lebo priečinok mohol zmiznúť.
   - **Nedostupný `models_dir` je pri štarte fatálny** (rozhodnutie autora) – `Application._ensure_models_dir()` v kroku „Kontrolujem modely…“, `ConfigError` → existujúca fatálna vetva v `run()`. **Mení §8 krok 7**, kde `OSError` znamenal len `Notice` a návrat na predvolený priečinok: ten fallback v `load_settings()` zostáva (a je to zámerne tá istá funkcia, ktorá nikdy nevyhadzuje), toto je posledná kontrola po ňom. Overené na ceste pod existujúcim súborom → `FileExistsError` → fatálny dialóg.
   - **Prepínače zapisujú hneď pri prepnutí** cez `SettingsStore.update(...)` (rozhodnutie autora) a v hlavičke blikne „✓ Uložené“ na 1,5 s. Zápis ide cez jedinú živú kópiu `AppSettings` (5a), takže zmena témy neprepíše `last_model_id` – overené. Pri zlyhaní zápisu sa prepínače vrátia na uložený stav a composer sa nemení.
   - **Prepínače riadia viditeľnosť tlačidiel v composeri** (§7.2: `*_enabled` = dostupnosť funkcie). `Composer.set_features()` ich skrýva a ukazuje; tlačidlá už nie sú natrvalo vypnuté. Keďže web ani prílohy ešte nefungujú (kroky 12–13), klik zatiaľ ukáže info toast „Pripravuje sa“ a web sa vráti do vypnutého stavu – `_on_attach_preview` / `_on_web_preview` v `MainWindow` sú **dočasné** a zmiznú s tými krokmi.
   - **Téma za behu ide cez signál `MainWindow.theme_changed` do `Application._set_theme()`**, nie priamo z okna. Stylesheet je vlastnosť `QApplication` a widgety si ju podľa zásady z kúska 1 nemajú brať cez `QApplication.instance()`; vedľajší zisk je, že štart aj prepnutie nastavujú štýl na jednom mieste. Prekreslenie prejde celou appkou (`apply_theme` → sidebar, chat, nastavenia; `MessageList.set_theme` prerenderuje kód a tabuľky, 6b).
   - **`scan_folder()` pri otvorení karty** (rozhodnutie autora) – sken inak beží len pri štarte (5c-1), takže súbor pridaný do priečinka za behu by sa objavil až po reštarte. Zoznam nájdených sa obnovuje pri otvorení karty, po importe a po zmazaní; číta `ModelLibrary.models()`, teda vždy čerstvo (vzor `set_model_source` z 5a).
   - **`ToggleSwitch` je vlastný widget** – QSS nevie `.switch::after`, teda pseudoelement s animovaným `left`. `paintEvent` kreslí dráhu aj gulôčku, posun animuje `QPropertyAnimation` nad `pyqtProperty(float)`. Dôsledok: prepínač sa musí prefarbiť v `set_theme()`, QSS ho nenájde.
   - **`set_on()` vedľa `setChecked()`** – naplnenie karty z `AppSettings` blokuje signály a nastaví offset priamo. Bez toho by zobrazenie karty hneď zapísalo nastavenia späť na disk a prepínače by pri štarte „preleteli“.
   - **`model_subtitle` sa presunula z `ui/composer.py` do `ui/formatting.py`** – ten istý podnadpis modelu používa menu modelov aj zoznam na karte, a karta nemá dôvod importovať z widgetu composera.
   - **Čo sa z CSS nedalo preniesť:** `text-transform` (rieši `text.upper()`), `letter-spacing` (Qt ho nemá vôbec – nadpisy skupín sú hustejšie než v HTML), `line-height` na popise, `text-overflow: ellipsis` v `QLineEdit` (preto `setCursorPosition(0)` a celá cesta v tooltipe) a desatinné `font-size` (12.5 → 12, Qt ho inak ignoruje). Padding kariet robia layout margins, nie QSS – inak sa sčíta s marginmi a nedá sa dopátrať, odkiaľ je medzera.
   - **Dlhý názov v zozname skracuje `_FoundRow` ručne** (`QSizePolicy.Ignored` + `elidedText` v `resizeEvent`), inak by `QLabel` roztiahol kartu a stránka nemá vodorovný posuvník.
   - **Pasca v testoch:** `isVisible()` je `False` pre **všetky** widgety skrytej stránky `QStackedWidget`, takže kontrola „tlačidlo composera sa skrylo“ z karty nastavení vždy prejde aj keď nemá. Testovať cez `isHidden()`.
   - **Chyby nájdené pri kontrole prepisu** (všetky opravené): `@pyqtProperty` bez typu a so zlúčeným getterom a setterom (`TypeError` pri importe); `event.type() is (A, B)` namiesto `in` (ticho – elide sa pri zmene písma neprepočítal); `set_model` vs `set_models`; `connect(self._open_folder_requested)` s podčiarkovníkom; `set_models(models_dir)` namiesto `set_models_dir`; `_save_settings` bez `return` (ticho – nastavenie sa uložilo, ale composer sa neprispôsobil); `QVBoxLayout` v hlavičke a `savedNote` nepridaný do layoutu (ticho – štítok neexistoval na obrazovke); `__al__`, `savedNone`, `self._icons.append(box, name)`.
   - **Testy:** `t6_settings.py` 28 kontrol offscreen aj naživo na platforme `windows` (naplnenie zo `settings.json`, sken a zoznam, zápis prepínačov, téma, otvorenie priečinka vrátane obnovy zmazaného, dočasné toasty, zlyhanie zápisu); `t7_app_theme.py` – skutočná appka nad `devdata`, prepnutie témy za behu a späť; regresia `t1_chat_menu` 47/47 a `t4_usage` 21/21.
   - **Otvorené:** toast sa na karte nastavení prekrýva s prvými prepínačmi (`TOAST_TOP` je počítaný pre hlavičku chatu); stránka Vlastnosti je stále placeholder (krok 11).

   **Kúsok 9 - stránka Vlastnosti chatu ✅** (2026-11-08; autor rozbehal hlavičku a pätu, zvyšok navrhol a napísal Claude; testy prešli nad repom na PC 1; commity `79fc572` + `cdfe7cd` (autorova úprava: čip rozsahu má strop výšky 28 px, panel monitora menší polomer a okraje)). Podľa aktualizovanej šablóny `semestralka/UI/template/` na OneDrive (pribudla do nej strana `propsPage`). Súbory: nový **`ui/properties_view.py`** (1165 riadkov: `PropertiesView`, `_Grid`, `_Ticks`, `_Elided`, `_Param`, `PARAMS`, `_ParamRow`, `_SeedRow`), `ui/chat_controller.py` (`properties()`, `apply_properties()`, draft), `ui/main_window.py` (zapojenie), `core/settings.py` (`ModelMeta.kv_cache_mb`), `core/llm_engine.py` (`_memory_pool` → verejná `memory_pool`), `ui/formatting.py` (`int_text`, `short_tokens`, `pages_text`), `ui/style.py` (tokeny `warn_bg`/`warn_text`, QSS stránky, slidera, spinboxov), `ui/constants.py`; `SETTINGS_MAX_WIDTH` premenovaná na `PAGE_MAX_WIDTH` (tú istú šírku 720 má aj stránka Nastavenia).
   Rozdelené na štyri kúsky: **9a** kostra + systémový prompt + lišta Použiť, **9b** karta kontextu s odhadom pamäte, **9c** expertné parametre, **9d** zapojenie a živý test.
   - **Tlačidlo Použiť len zapisuje, model sa načíta až pri ďalšej správe** (rozhodnutie autora). Šablóna sľubuje okamžitý reload („Použiť a načítať model“), ale `send()` už reload rieši sám (porovná `LoadParams.clamped()` s načítanými), takže reload z vlastností by znamenal druhú cestu k `load()` a `_on_loaded`, ktorý dnes predpokladá bežiaci ťah. Namiesto toho to hovorí stav v lište: „Neuložené zmeny (2) · model sa načíta pri ďalšej správe“.
   - **Predvolený systémový prompt zostáva prázdny** (rozhodnutie autora) - §8 krok 3: pri prázdnom prompte sa system správa do `messages` vôbec nedáva a model použije svoj vlastný. Šablóna má v `DEFAULTS` preset „Všeobecný asistent“; štyri presety zo šablóny sú v `PROMPT_PRESETS` ako tlačidlá, „Predvolené“ vráti prázdny prompt. Hint nad poľom to hovorí: „prázdny · model použije svoj predvolený“.
   - **Expertný režim sa medzi spusteniami nepamätá** (rozhodnutie autora) - je to stav UI, nie nastavenie. Easy = systémový prompt + kontext, expert = easy + hardvér (`n_gpu_layers`, `n_threads`, `n_batch`) a generovanie (`temperature`, `max_tokens`, `top_p`, `top_k`, `repeat_penalty`, `seed`). Tým je určený obsah oboch režimov, ktorý §7.2 nechával otvorený. V easy režime sa navyše skrývajú kľúčové chipy (`system_prompt`, `n_ctx`), spinbox kontextu a odznaky skupín; `use_mmap` a `stop` v UI nie sú vôbec.
   - **Stránka nevie o databáze ani controlleri.** Dostane `load(props, chat_title=, model=)` a vysiela `apply_requested(ChatProperties)` + `opened`; zápis robí `MainWindow`, po úspechu zavolá `confirm_applied()`, po chybe stránku načíta znova (rovnaká hranica ako pri `SettingsView` a mazaní modelu). Pôvodných 12 signálov „po parametri“ z rozpracovanej verzie padlo - pri jednom tlačidle Použiť nemá kto počúvať jednotlivé zmeny.
   - **Vlastnosti chatu, ktorý ešte nevznikol, drží controller v pamäti** (`_draft`) - §7.1 hovorí, že chat vzniká až s prvou dokončenou odpoveďou, takže do databázy niet čo zapísať. `send()` draft použije a `add_turn` ho uloží ako `properties` nového chatu. Draft sa nuluje v `select_model()` (§7.1 - výmena modelu resetuje vlastnosti), v `model_deleted()` a v `new_chat()` **len pri odchode z existujúceho chatu** (`chat_id is not None`).
   - **„Fúkni nový chat“ v novom chate draft nezahodí** (rozhodnutie autora 2026-11-08, po skúške appky). Pôvodne `new_chat()` draft nuloval vždy, takže keď si používateľ v prázdnom chate nastavil vlastnosti, dal Použiť a potom namiesto tabu Chat trafil „Fúkni nový chat“, nastavenia ticho zmizli. Pravidlo je teda: **jeden draft, s ktorým sa pracuje, kým si v novom chate; nový draft vzniká až pri návrate z existujúceho chatu.** Zamietnuté: tlačidlo v prázdnom chate nerobí nič (klik by neodpovedal ničím, aj keď používateľ stojí na stránke Vlastnosti) a draft, ktorý prežije aj vznik chatu (to už by boli „predvolené pre nové chaty“, teda nová vlastnosť a nie oprava).
   - **Dve úrovne hraníc (§8 krok 6) sa prvýkrát reálne používajú:** maximum slidera je `min(konštanta, model/hardvér)`. `n_ctx` ≤ `n_ctx_train`, `n_gpu_layers` ≤ `n_layers + 1`, `n_threads` ≤ logické jadrá, `max_tokens` ≤ `n_ctx`. Tým **padá pasca z kroku 8** („slider `max_tokens` treba obmedziť podľa `n_ctx`“) - strop sa prepočíta pri každej zmene kontextu.
   - **Uložená hodnota nad stropom sa zmenší a ukáže ako neuložená zmena**, nie ticho. Inak by stránka zobrazovala iné číslo, než je v databáze. Týka sa `n_ctx` (iný model s menším `n_ctx_train`) aj `max_tokens` (zmenšený kontext); pri `n_ctx` to vysvetľuje varovanie v karte.
   - **Odhad pamäte je v karte kontextu** (§7.2 to žiadal pre easy režim): „Model 2,3 GB + kontext 544 MB = 2,9 GB · voľných 14,2 GB pamäte grafickej karty“. KV cache počíta nová **`ModelMeta.kv_cache_mb(n_ctx)`** vzorcom overeným v kúsku 5b; voľnú pamäť a jej názov dáva **`memory_pool()`**, ktorá sa kvôli tomu z `_memory_pool` stala verejnou - dve miesta s vlastným výpočtom voľnej pamäte by si odporovali. Engine ju ďalej volá tiež, len **bez KV cache** (nemá metadáta, §8 krok 3 kúsok 7 platí).
   - **Voľná pamäť sa meria raz pri otvorení stránky a znova pri zmene `n_gpu_layers`**, nie pri každom posune slidera: `detect_gpu()` je `nvidia-smi`, teda desiatky ms. `ram_available_mb` z profilu sa nepoužíva, je odmerané pri štarte (§4).
   - **Mriežky sa pri úzkom okne preskupia** (`_Grid`): počet stĺpcov je `width // min_width`, prepočítaný v `resizeEvent`. Parametre 2 → 1 stĺpec, presety promptu 4 → 2 → 1. Pasca: bez `QSizePolicy.Ignored` je minimálna šírka mriežky súčet všetkých stĺpcov, takže sa nikdy nezúži a preskupenie nenabehne; k tomu `minimumSizeHint()` vracia `min_width`, nie šírku layoutu.
   - **Popisky pod sliderom kontextu (`_Ticks`) sa umiestňujú ručne na stredy pozícií jazdca**, nie do rovnako širokých buniek layoutu - bunky majú stredy v `(i+0,5)/n`, jazdec v `i/(n-1)`, a pri 10 krokoch sa to rozíde až o pol bunky. Krajné popisky sa zarovnávajú dovnútra, inak „128K“ prečnieva. Aktívny popisok je tučný, teda širší - po `set_current` treba `adjustSize()` a nové umiestnenie.
   - **Seed má `QLineEdit`, nie `QSpinBox`:** `SEED_MAX` je 4 294 967 295, teda nad rozsahom 32-bitového `int`, ktorý Qt v `QSpinBox` používa. Rovnaká rodina pasce ako `pyqtSignal(int)` pri bajtoch importu (`f2a1772`). Prepínač „Náhodný“ = `seed=None`; vypnutie dá 42 ako šablóna.
   - **Nelineárne slidery sú nad zoznamom mocnín dvoch** (`power_steps`), spinbox pritom prijme aj hodnotu mimo krokov (napr. `n_ctx=5000`) a jazdec sa postaví na najbližší krok - porovnáva sa v `log2`, nie lineárne. Desatinné parametre majú slider v krokoch `step` (teplota 0,05 → 40 polôh) a `QDoubleSpinBox`.
   - **Hodnoty sa zapisujú cez `editingFinished`, nie `valueChanged`** - pri písaní „8“ do poľa s minimom 256 by `valueChanged` okamžite opravil na 256 a prepísal rozpísané číslo.
   - **Názov chatu do čipu ide z databázy, nie zo zásobníka pre sidebar.** `MainWindow._chats` sa obnovuje až signálom `chats_changed`, ktorý príde po `turn_finished`, takže práve vzniknutý chat by sa v ten moment javil ako „Predvolené pre nový chat“ (odhalil živý test).
   - **Riadok modelu musí prísť z `ModelLibrary.models()`, nie z `Database.get_model()`** - `size_mb` dopĺňa knižnica zo `stat()`, bez neho sa odhad pamäte nezobrazí vôbec (odhalila snímka zo živého testu, nie test).
   - **Pasce, ktoré sa prejavili pri písaní:**
     - `self._expert` je prepínač v hlavičke a zároveň som pomenoval metódu `_expert(widget)` - atribút z `__init__` metódu prekryl a stavba okna skončila na `TypeError: 'ToggleSwitch' object is not callable`. Metódy sa volajú `_only_expert` / `_only_easy`.
     - **`QSizePolicy.Ignored` + `addStretch` = widget so šírkou nula.** Titulok a čip v hlavičke zmizli úplne (vidno len na snímke, nič nespadne). Ignored widget musí dostať stretch faktor v `addWidget`, nie stretch vedľa seba - vzor z `chat_view`.
     - **Dlhý jednoriadkový text drží celú stránku širšiu než panel.** Hint „prázdny · model použije svoj predvolený“ a názov parametra nafúkli minimálnu šírku tak, že sa mriežka nemala ako preskupiť. Riešenie: `Ignored` na tom, čo sa smie skrátiť (`pLabel`), a `_Elided` (skracovanie cez `QFontMetrics` v `resizeEvent` + `changeEvent`) na čip s názvom chatu.
     - **Offscreen platforma má výrazne väčšie predvolené písmo než Windows** - minimálna šírka stránky vyšla offscreen 692 px, na skutočných fontoch 366 px. Testy rozmerov preto patria na platformu `windows`; offscreen sa dá overiť len mechanizmus (tu: `_Grid` bez rodiča v kontajneri).
     - `QPlainTextEdit` má `sizeHint` väčší než `minimumHeight`, takže pole promptu narástlo na ~180 px; je preto `setFixedHeight(104)` ako štyri riadky v šablóne.
   - **Testy** (scratchpad, PC 1): `t1_props.py` 46 kontrol (načítanie, draft vs databáza, prežitie draftu cez „Fúkni nový chat“, lišta Použiť, Predvolené, zámok počas generovania, chat bez modelu), `t4_ctx.py` 40 (kroky, KV cache proti číslam z llama.cpp, spinbox, varovania, strop modelu, pozície popiskov), `t5_params.py` 55 (rozsahy z modelu a hardvéru, oba typy slidera, seed vrátane `SEED_MAX`, väzba `max_tokens` na `n_ctx`, easy/expert, preskupenie mriežky), `t7_live.py` 17 v **skutočnej appke na platforme `windows`** so snímkami oboch tém: nastavené `n_ctx=512` a `max_tokens=16` sa prejavili až v engine (`engine.n_ctx == 512`, odpoveď skončila na `length` po 16 tokenoch) - teda celá cesta stránka → properties → `send()` → reload modelu. Regresia: self-testy `core.settings`, `core.gguf`, `core.context`, `ui.markdown`.
   - **Zostáva otvorené:** toast sa na stránke prekrýva s prvou kartou (`TOAST_TOP` je počítaný pre hlavičku chatu, rovnako ako na stránke Nastavenia); počet tokenov systémového promptu je odhad `dĺžka / 4`, nie `llm.tokenize()` (presné číslo vie len načítaný model); pri zmene modelu v rozpísanom chate stránka ukáže nové predvolené hodnoty až po jej otvorení (`showEvent`), čo stačí, lebo model sa mení v composeri na stránke Chat.

   **Kúsok 10 - modal s informáciami o modeli ✅** (2026-11-08; rozhodnutie a event filter autor, modal navrhol a otestoval Claude v scratchpade, autor prepísal bez chýb). Klik na názov modelu v zozname nájdených na stránke Nastavenia otvorí malý modal s údajmi z hlavičky `.gguf`. Súbory: nový **`ui/model_info.py`** (`ModelInfoDialog`, `info_rows`), `ui/settings_view.py` (`_FoundRow.clicked`, `SettingsView.model_info_requested`), `ui/main_window.py` (`_on_model_info`), `ui/style.py`, `ui/constants.py` (`DASH`, `KV_SAMPLE`, `MODEL_INFO_*`).
   - **Hlavička sa číta nanovo zo súboru** (`read_meta`), nie z `models.meta` – modal má ukázať, čo je naozaj v súbore, nie čo si appka zapamätala pri importe. Stojí to ~60 ms (kúsok 5b), takže to beží v UI vlákne. Chýbajúci alebo poškodený súbor je `FukaiError` → namiesto dialógu príde toast.
   - **Modal nevie o knižnici ani o disku** – dostane hotový `model`, `ModelMeta` a tému, číta ich `MainWindow` (rovnaká hranica ako pri mazaní a importe). Vďaka tomu je `info_rows(model, meta)` obyčajná funkcia a dá sa overiť bez okna.
   - **Chýbajúci údaj je pomlčka, nie prázdny riadok** (`DASH`) – „neviem“ a „nula“ sú dve rôzne veci, tá istá úvaha ako pri `content.tokens` (§7.2). Pri modeli bez metadát vyjde 8 pomlčiek, `Chat template: nie` a názov súboru.
   - **Obsah (10 riadkov):** názov z metadát, architektúra, parametre, kvantizácia, `n_ctx_train`, vrstvy, KV cache na 1 024 tokenov (`ModelMeta.kv_cache_mb`), chat template áno/nie, veľkosť súboru, názov súboru. Cesta je relatívna k priečinku modelov – ten je na tej istej stránke o kúsok vyššie.
   - **Zaoblené rohy ako pri `QMenu`:** `FramelessWindowHint` + `WA_TranslucentBackground` + vnútorný `QFrame#infoCard`; bez rámu teda nie je ani systémové ✕, preto vlastné (Esc zatvára `QDialog` sám). Tieň potrebuje okraj v layoute, inak sa oreže o hranu okna. Dialóg sa v `showEvent` postaví na stred rodiča – automatické centrovanie sa pri frameless okne nedá spoliehať.
   - **Klikateľný je názov modelu, nie celý riadok** (rozhodnutie autora) – `installEventFilter` na `QLabel` s kurzorom ruky. Celý riadok by znamenal `mouseReleaseEvent` na `_FoundRow`.
   - **Testy:** `t9_info_repo.py` 12 kontrol nad repom (riadky z hlavičky Gemmy, prázdne metadáta, klik v živej appke → modal s 10 dvojicami → zatvorenie), snímky v oboch témach. Regresia: `t1_props` 46/46, `t4_ctx` 40/40, `t5_params` 55/55, `t7_live` 17/17.
   - **Pasca v teste (nie v appke):** klik treba poslať cez `QApplication.sendEvent`, inak sa event filter neuplatní; a `exec()` modalu blokuje, takže zatvorenie si treba naplánovať časovačom **pred** kliknutím.

   **Čo v kroku 9 zostáva otvorené** (hotové kúsky sú v tabuľke na začiatku kroku):
   - 🔴 **PRIORITA – appka spadne, keď sa počas generovania zmaže chat zo zoznamu** (hlásil autor 2026-11-08 na PC 1, pád celého procesu, nie `FukaiError`). Zapísané ako prvé na ďalšiu session.
     **Čo je známe:** `MainWindow._on_delete_chat` odmietne zmazať chat, **do ktorého práve beží ťah** (`ChatController.turn_chat_id`), ale táto poistka nepokrýva dva prípady: (1) odpoveď beží v chate, ktorý ešte nevznikol (`turn_chat_id` je vtedy `None`, §7.1), (2) zmaže sa **iný** chat než ten s odpoveďou, pričom ide o práve zobrazený chat.
     **Prvá hypotéza (neoverená):** pri zmazaní zobrazeného chatu sa volá `reload_chats()` + `controller.new_chat()`, čo prekreslí `MessageList` - a tokeny, ktoré medzitým prichádzajú, dorazia do `_AnswerMessage`, ktorého C++ objekt je už zmazaný. „Wrapped C/C++ object has been deleted“ je výnimka v slote, a tá zhodí celý proces (§8.2). Sedí to aj s tým, že nebolo vidieť žiadne hlásenie.
     **Kde začať:** `MainWindow._on_delete_chat`, `ChatController._visible()` a číslovanie zobrazení (`_view`), `ChatView.begin_turn` / `append_token`. Overiť v živom okne: dlhá odpoveď → zmazať zobrazený chat; a to isté v chate, ktorý ešte nevznikol.
     **Smery riešenia (rozhodnúť zajtra):** zakázať mazanie ktoréhokoľvek chatu počas generovania (najjednoduchšie, ale obmedzujúce); alebo pri zmazaní chatu s bežiacim ťahom ťah vrátiť (`_roll_back`) a až potom mazať; alebo spraviť streamovacie sloty odolné (kontrola, že cieľová správa ešte existuje).
   - **Toast sa prekrýva s prvou kartou** na stránkach Vlastnosti aj Nastavenia – `TOAST_TOP` je počítaný pre hlavičku chatu.
   - **Neoverené na Windows:** chat dlhý natoľko, že sa začne orezávať história (`dropped`), a správanie pri plnej VRAM. Na macOS: GPU % v monitore (`ioreg`) a všetko z kúskov 7–9, ktoré vznikli na PC.
   - **Drobnosti:** počet tokenov systémového promptu je odhad `dĺžka / 4`, nie `llm.tokenize()`; kontextové menu textu je po anglicky (Qt bez prekladov); výber textu myšou cez viac častí odpovede nejde (každá časť je vlastný `QTextBrowser`).
   - **Ponúknuté, nerozhodnuté:** `sys.excepthook` → fatálny dialóg pri neodchytenej výnimke; generátor ikon do repa (`tools/`).
10. [x] **Čítač hlavičky `.gguf`, ktorý nenačíta model** – *robený v kroku 9 ako kúsok 5b (vyššie), hotový a commitnutý 2026-11-05 (`44fc7e6`).* Prerekvizita importu modelu. *Overené 2026-10-30:* `n_layers` aj `n_ctx_train` v `llm_engine.py` idú cez `self._llm._model.model`, teda sú dostupné **až po `load()`**. Popup so zoznamom modelov a rozsahy slidrov ich ale potrebujú **pred** načítaním, preto sa čítajú raz pri importe a cachujú v `models.meta` (§7.1). Pri vytváraní chatu to nevadí – model vtedy už beží.
11. [x] Panel nastavení per chat + výber a import modelu – *výber a import modelu sú v kroku 9 (kúsky 5a–5c), panel vlastností je kúsok 9 (2026-11-08).*
12. [x] **Prílohy – hotové 2026-11-09** (drag & drop, extrakcia, kontrola tokenov). Hotové kúsky:

    | Kúsok | Čo | Stav |
    |---|---|---|
    | 12a | migrácia schémy na v2, tabuľka `attachments`, `add_turn`/`get_attachments` | ✅ |
    | 12b | `extensions/file_parser.py` – txt/md/csv/json/kód, PDF, xlsx, docx | ✅ |
    | 12c | `AttachmentService` vo vlastnom vlákne, čipy v composeri, drag & drop, náhľad textu | ✅ |
    | 12d | príloha do promptu, do databázy a späť do histórie, orezanie na kontext | ✅ |
    | 12e | čipy príloh pri správach, správa bez textu | ✅ |

    Rozhodnutia (autor, 2026-11-08): **text prílohy zostáva súčasťou tej správy, pri ktorej bol pripnutý** – do promptu teda ide aj pri ďalších otázkach; **extrakcia beží vo vlastnom vlákne** (veľké PDF trvá sekundy); **limit je len kontext**, nie počet súborov – každá príloha sa pri pripnutí odpočíta z voľného rozpočtu a ďalšia dostane zvyšok; **čo sa nezmestí, sa oreže** a čip to povie (`orezané`); **samotná príloha bez textu je platná správa** a názov chatu potom vznikne z názvu súboru.
    Hranice: `extensions/file_parser.py` nevie o Qt a vracia iba `AttachmentError`; `AttachmentService` nevie o widgetoch; `AttachmentBar` nevie o službe ani o vlastnostiach chatu – rozpočet počíta `MainWindow`. Text prílohy sa do promptu vkladá **do tej istej správy ako otázka** (`core/context.with_attachments`), lebo samostatná správa by rozbila striedanie rolí, na ktorom trvá Gemma (§8 krok 3).
    Pasce, ktoré to stálo: chýbajúci `setObjectName("chip")` (QSS sa nechytilo, čip bol bez pozadia aj zaoblenia); `icon("×")` namiesto `icon("x")` → `FileNotFoundError` pri každom čipe; `chip._reflow()` namiesto `self._reflow()` → výnimka v slote zhodila proces; `self._chips.get()` namiesto `.pop()` nechal zmazaný widget v slovníku; `_reflow(force=True)` v `resizeEvent` sa v composeri zacyklil; **SVG ✕ pri 10 px je kocka** (ťah 0,8 px, guľaté konce zmiznú) – krížik je preto text, ako v dialógoch.
    **Kúsok 12e (2026-11-09):** čipy príloh sú nad bublinou otázky - v rozpísanom ťahu bez možnosti kliknúť, v histórii klikateľné (náhľad textu). **Správa bez textu bublinu nedostane vôbec**, zostanú len čipy; prázdna bublina vyzerala ako chyba. Text príloh sa pri otvorení chatu stále nenačítava (§12a), náhľad si ho dotiahne až pri kliknutí cez `Database.get_attachment(id)`. `ChipName` (skracovanie názvu v strede) je spoločná pre composer aj históriu - preto sa z `_Name` stala verejná trieda v `ui/attachment_bar.py`. `turn_started` nesie okrem otázky aj zoznam názvov príloh, takže čipy vidno hneď pri odoslaní; `Composer.begin_turn` má stále jeden parameter, lebo Qt slotu s menej parametrami nadbytočné zahodí.
    Neoverené: správanie na macOS, veľmi veľké PDF (stovky strán) a súbeh importu modelu s extrakciou prílohy.
13. [ ] Web rozšírenie
14. [ ] Doladenie: témy, markdown, ikony, PyInstaller

### Prečo sa začína jadrom, a nie UI ani nastaveniami

Rozhodnuté 2026-10-27, platí ako odpoveď na otázku „UI / core / nastavenia a história?“:

- **Tvar UI určuje worker + signál architektúra** (§7). UI postavené pred jadrom by sa prepisovalo druhýkrát – presne to sa stalo prototypu (§5, bod 1).
- **Načítanie CUDA/Metal wheelu je jediné skutočné riziko projektu.** Kým nie je overené, že `n_gpu_layers=-1` reálne offloaduje na GPU, všetko ostatné stojí na neoverenom predpoklade.
- **Nastavenia a história sa nedajú navrhnúť naslepo.** Schéma `chat_settings` je priamo zoznam parametrov, ktoré engine naozaj prijíma – kým engine nebeží, je to hádanie. Prototyp si takto do nastavení zadrôtoval ručný počet vrstiev (§5, bod 3).

Jadro sa dá otestovať čistým konzolovým skriptom, takže je hotové a overené skôr, než vznikne prvý widget.

### 8.1 Ako sa na projekte pracuje

Rozhodnuté 2026-10-28, platí pre každú session:

- **Po malých kusoch, nie celé moduly naraz.** Autor chce kódu rozumieť a kontrolovať ho, prípadne písať sám – nie dostať hotový súbor na schválenie. Hotový modul, ktorý nikto neprečítal, je horší než polovica, ktorej autor rozumie.
- **Návrh pred kódom.** Schéma, názvy a hranice modulov sa dohodnú skôr, než sa píše implementácia. Dôvod je ten istý ako pri „jadro pred UI“ vyššie: čo sa napíše pred dohodou, píše sa druhýkrát.
- **Vysvetliť *prečo*, nie len *čo*.** Pri rozhodnutí sa uvádza dôvod a zahodená alternatíva – preto má tento súbor aj `SESSIONS.md` takú podobu.
- **Nekomitovať bez vyžiadania.** Zmeny zostávajú v pracovnom strome, kým autor nepovie.

### 8.2 Opakujúce sa pasce (Qt a Python)

Pasce, ktoré sa pri stavbe UI zopakovali vo viacerých kúskoch. Zoznam je tu preto, aby sa
nemuseli hľadať v jednotlivých kúskoch kroku 9; konkrétne výskyty sú tam a v `SESSIONS.md`.

| Pasca | Prejav |
|---|---|
| **Funkcia vs. jej volanie** – `isNull` / `isNull()`, `read` / `read()`, `trigger` / `triggered`, `emit` / `emit()` | do `connect` a `QTimer.singleShot` patrí funkcia **bez** zátvoriek; getter so zátvorkami naopak vykoná prácu (raz načítal 2,3 GB súbor do pamäte) |
| **Atribút prekryje metódu** (`self._expert`), **druhá metóda s rovnakým menom** ticho vyhrá (`Database.set_model`) | `TypeError: object is not callable`, prípadne volanie úplne inej metódy; pri novom mene `grep "def meno"` |
| **Trieda bez `()`** v atribúte (`self._text = QLabel`) | `TypeError: unbound method` až pri prvom volaní, nie pri priradení |
| **Písmo zo stylesheetu príde až pri polish** | rozmery a skracovanie textu treba prepočítať v `changeEvent` (`FontChange`, `StyleChange`), inak sedia pre menšie písmo |
| **`QSizePolicy.Ignored` + `addStretch`** | widget dostane nulovú šírku a zmizne; Ignored widget musí dostať stretch faktor priamo v `addWidget` |
| **Dlhý jednoriadkový text** v karte alebo hlavičke | drží celú stránku širšiu než panel; skracovať cez `QFontMetrics.elidedText`, nie nechať orezať |
| **`removeWidget` / `takeAt` widget nezmaže** | zostane viditeľný na starom mieste; pred `deleteLater()` zavolať `hide()` |
| **QSS `border-radius` rodiča neoreže deti** | deti panelu musia mať priehľadné pozadie, inak prekryjú zaoblené rohy |
| **`QColor("rgba(…)")` je neplatná farba** | kreslí sa čierna; na tokeny s `rgba()` je `qcolor()` v `ui/style.py` |
| **Výnimka v slote zhodí celý proces** | a naopak: `except Exception` v slote workera premení preklep na doménovú chybu – pri `failed` pozrieť `detail` |
| **`pyqtSignal(int)` je 32-bitový**, `QSpinBox` tiež | bajty nad 2 GiB pretečú (`"qint64"`), `SEED_MAX` sa do `QSpinBox` nezmestí (`QLineEdit`) |
| **Preklep v `__all__`** | prejaví sa len pri `from … import *`, bežný import ho neodhalí |
| **Modálne okno otvorené priamo z `QMenu`** | beží vo vnorenej slučke zatváraného menu; spúšťať cez `QTimer.singleShot(0, …)` |
| **Offscreen platforma má iné písmo aj štýl** | rozmery, rozostupy a kurzor overovať na `windows` / `cocoa`; offscreen stačí na logiku |
| **Umelé udalosti v testoch** | `sendEvent` sa nepropaguje rodičom, `widget.event()` obchádza event filtre, `singleShot` na ne-`QObject` drží slabú referenciu |

## 9. Poznámky k prostrediu

Na PC 1 je shell **PowerShell 5.1**, Claude Code má aj Git Bash. Každé z nich má inú pascu:

- **PowerShell 5.1 nepozná `&&`.** `git add . && git commit -m "x"` skončí na `ParserError`. Správne: `git add .; if ($?) { git commit -m "x" }`, alebo len `a; b`.
- **Git Bash prerába argumenty začínajúce lomkou na windowsové cesty.** Z `git commit -m "/core - ..."` sa stane predmet `C:/Users/.../hermes/git/core - ...`. Commit správy nikdy nezačínať `/` – písať `core: ...`.
- **Viacriadkové `heredoc` v Git Bash** sa na slovenských úvodzovkách a apostrofoch rozbíja – dlhé súbory zapisovať priamo, nie cez `cat > file <<EOF`.
- **`py` je launcher, nie `.venv`.** Na PC 1 je globálny Python **3.14.2** (`%LOCALAPPDATA%\Python\pythoncore-3.14-64`), zafixovaná verzia projektu je 3.12.10 (§3). `py -m pip install ...` ide do `.venv` **iba keď je venv aktivovaný** (vtedy launcher ctí `VIRTUAL_ENV`); bez aktivácie to ticho nainštaluje do 3.14. Isté je `.venv\Scripts\python.exe -m pip ...`. Kam to naozaj šlo, povie `python -c "import sys; print(sys.prefix)"`.
- **`set NIECO=hodnota` je syntax cmd.exe, v PowerShelli to ticho nič nespraví.** `set` je v PowerShelli alias pre `Set-Variable`, takže `set CMAKE_ARGS=-DGGML_CUDA=on` vyrobí PowerShell premennú s názvom `CMAKE_ARGS=-DGGML_CUDA=on` a hodnotou `$null` – **bez chybového hlásenia**. Environment premenná sa nenastaví a podproces (tu cmake) o ničom nevie. Správne je `$env:CMAKE_ARGS = "-DGGML_CUDA=on"`.
  *Stalo sa 2026-10-28:* takto postavený `llama-cpp-python` sa skompiloval úspešne, ale **ako CPU-only build** – v `llama_cpp/lib/` chýbala `ggml-cuda.dll`. Build neprotestoval, lebo CUDA jednoducho nebola vyžiadaná. Poučenie: po každom builde zo zdrojákov skontrolovať obsah `llama_cpp/lib/`, nie len to, že `pip install` prešiel.

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
| oficiálny CUDA wheel 0.3.36 | 218 MB (z toho `ggml-cuda.dll` 121 MB) |

CUDA wheel **nemá cuBLAS v sebe** – *potvrdené 2026-10-28* zoznamom importov `ggml-cuda.dll`: `cublas64_13.dll`, `nvcuda.dll`, `nvcudart_hybrid64.dll`. Z toho `nvcuda.dll` dodáva ovládač (je na každom stroji s NVIDIA kartou), ale cuBLAS je z Toolkitu. Koncový používateľ Toolkit mať nebude, takže ~507 MB CUDA knižníc treba priložiť k appke. NVIDIA redistribúciu týchto DLL povoľuje (CUDA EULA), ale overiť podmienky pred vydaním.

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
   **Neplatí pre 0.3.36 (overené 2026-10-30):** oficiálny Metal wheel 0.3.36 je na GitHube poškodený – `BadZipFile: Bad CRC-32 for file 'lib/cmake/ggml/ggml-config.cmake'`. SHA-256 stiahnutého súboru sa zhoduje s digestom, ktorý publikuje GitHub, takže chyba je v nahranom súbore, nie v sťahovaní ani v cache pipu. Wheel 0.3.35-metal je v poriadku, ale **verzia musí byť na Macu aj PC rovnaká**, preto sa na Macu 0.3.36 zostavuje zo zdrojákov (§10.1b). Keď autor wheel opraví, dá sa vrátiť k nemu.

**Overené inštaláciou 2026-10-28:** wheel `sm_120` podporuje, cuBLAS v sebe nemá. Body 3 (nie je per-architektúra) aj 5 sa potvrdili. Detaily a čísla výkonu sú v §3.

**Rozhodnuté:** pin v §3 posunutý z `0.3.20` na `0.3.36`, `requirements-llama-*.txt` prepísané na oficiálne URL. Zdroj `dougeeai` sa už nepoužíva.

### 10.1b Build zo zdrojákov – čo to je a čo nie je

`CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python==0.3.36` **nie je inštalácia, ale kompilácia**.

> **Stav 2026-10-28:** pre vývoj build zo zdrojákov **netreba** – oficiálny wheel na PC 1 funguje aj na `sm_120` (§3). Build zostáva relevantný iba pre problém B nižšie, teda na výrobu vlastnej distribučnej binárky. Pokus o build na PC 1 zlyhal tichým spôsobom (CPU-only), príčina je v §9.

Treba rozlišovať dva nezávislé problémy, ktoré sa pri tom často mieša:

| | problém | čo ho rieši |
|---|---|---|
| A | rozbehať to na PC 1, PC 2, Macu | predkompilovaný wheel **alebo** build zo zdrojákov |
| B | doručiť appku používateľovi | **len** hotové binárky, nikdy build na stroji používateľa |

- Každý `CMAKE_ARGS` variant (`GGML_CUDA`, `GGML_METAL`, `GGML_HIP`, `GGML_VULKAN`) je **samostatný build a samostatný wheel**. CUDA a HIP sa v jednom builde vylučujú – „podpora pre všetky GPU“ znamená „vyber si jeden“, nie „jeden pokryje všetko“.
- **Viac NVIDIA architektúr v jednom builde sa ale dá:** `-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=75;86;89;120` dá **jeden wheel pre RTX 20xx až 50xx**. Výstupom buildu je `.whl`, teda priamo tá binárka, ktorú priložíš k inštalačke – build zo zdrojákov je teda spôsob, ako si distribučnú binárku vyrobiť, a zároveň odstráni závislosť na cudzom repe.
- **V PowerShelli nefunguje bashová syntax** `CMAKE_ARGS="..." pip install ...`. Musí byť `$env:CMAKE_ARGS = "-DGGML_CUDA=on"` na samostatnom riadku (pozri §9).
- **Nástroje na PC 1 sú k dispozícii** (overené 2026-10-28): MSVC 14.44.35207 z VS 2022 BuildTools, CMake priložený k BuildTools, nvcc 13.0.88. `cl.exe` ani `cmake` **nie sú v PATH** – build spúšťať z „x64 Native Tools Command Prompt for VS 2022“. Na macOS stačia Xcode Command Line Tools – `cmake` si pip pri builde stiahne sám ako build závislosť. **Mac M2 (2026-10-30):** `CMAKE_ARGS="-DGGML_METAL=on" python -m pip install --no-cache-dir --no-binary llama-cpp-python llama-cpp-python==0.3.36` prešiel, `llama_supports_gpu_offload()` = `True`, Metal hlási `recommendedMaxWorkingSetSize = 5726.63 MB` – to je reálny strop pre model + KV cache na GPU pri 8 GB.
- AMD cez `GGML_HIP` na Windows je problematické (ROCm má na Windows obmedzenú podporu); praktickejší by bol `GGML_VULKAN`. **Mimo rozsah projektu** – §1 fixuje NVIDIA + Apple Silicon.

### 10.2 Pozor na „CUDA build s CPU fallbackom“

CUDA zostavenie `llama.dll` je nalinkované na ovládač NVIDIA (`nvcuda.dll`). Na stroji bez NVIDIA karty sa knižnica nemusí vôbec načítať – takže nie je na čo spadnúť a `n_gpu_layers=0` to nezachráni. Pre Windows preto treba počítať s **dvoma buildmi** (CUDA + CPU), nie s jedným prepínačom.

**Varianty inštalačky – nerozhodnuté:**

1. Štyri inštalačky podľa architektúry GPU. Funguje offline, ale používateľ musí vedieť, akú má kartu.
2. Inno Setup v `[Run]` sekcii stiahne správny balík. Malá inštalačka, potrebuje internet pri inštalácii.
3. CPU základ + voliteľné dotiahnutie GPU akcelerácie pri prvom spustení. Najpríjemnejšie pre používateľa, ale blokuje to nesúlad verzií (vyššie).

**macOS je jednoduchší** – Metal build je jeden pre všetky Apple Silicon, žiadna matica architektúr ani cuBLAS.
