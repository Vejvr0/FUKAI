# FUKAI – Almanac

Zdieľaná pamäť projektu pre Claude Code na všetkých strojoch (Mac aj PC). Sem patria rozhodnutia, obmedzenia a kontext, ktorý sa nedá vyčítať z kódu. Pri zmene rozhodnutia prepíš príslušnú sekciu, nepridávaj protichodné záznamy. Posledná revízia: 2026-11-03.

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

> **Platnosť:** táto sekcia opisuje wheels od `dougeeai`, ktoré sme používali do 2026-10-28. Od prechodu na oficiálne wheels 0.3.36 (§10.1) sa **wheel podľa architektúry nevyberá** – oficiálny je jeden pre všetky NVIDIA karty, *overené inštaláciou na PC 1 (2026-10-28): jeden wheel bez `sm` v názve rozbehal `sm_120`*. Tabuľka compute capability nižšie zostáva užitočná na **diagnostiku a hlásenia** používateľovi (`core/hardware.py`, `vars/hw.json`), nie na výber balíka.

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
| PC 1 | Intel Core Ultra 7 265K (8P + 12E, bez HT) | RTX 5060 Ti **16 GB** (Blackwell, sm_120) | 32 GB | CUDA Toolkit 13.0, driver 617.42 – *offload na GPU overený 2026-10-28, pozri §3* |
| PC 2 | – | RTX 4080 16 GB (Ada, sm_89) | – | CUDA, wheel `sm89` (pozri §3.1) |

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
- **`verbose=False` neutíši llama.cpp celkom** – časť hlásení ide na stderr aj tak (napr. `llama_kv_cache_iswa: ...`). Pri UI bude treba stderr presmerovať, nestačí prepínač.
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

**Zoznam modelov je tabuľka, nie skenovanie priečinka.** Popup v input riadku musí vypísať modely a panel vlastností potrebuje rozsahy slidrov (max `n_ctx` = `n_ctx_train`, max `n_gpu_layers` = vrstvy + 1) **pred** načítaním modelu. Preto sa metadáta `.gguf` čítajú **raz pri importe** a cachujú v tabuľke `models`. Z toho vyplýva nutnosť čítača hlavičky `.gguf`, ktorý nenačíta model – dnes sú tie čísla dostupné až po `load()`.

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

**Easy mode / expert mode.** Easy mode: názov modelu, slider `n_ctx`, slider `n_gpu_layers` (rozdelenie vrstiev CPU/GPU), `temperature`, plus ukazovateľ „potrebná RAM vs dostupná“. Expert mode = easy + ďalšie parametre, konkrétny výber zatiaľ **neurčený**.

Dve veci, ktoré z toho vyplývajú:

- **Aj v easy mode zostáva tlačidlo „Použiť a reloadnúť“** (§7). Dva z troch slidrov easy mode sú load-time, takže bez neho by začiatočník posunutím slidera spustil desiatky sekúnd dlhý reload. Slider mení len číslo, reload si vypýta kliknutie. `temperature` sa aplikuje hneď.
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

0. [x] `requirements.txt`, `requirements-llama-win-cuda.txt`, `requirements-llama-mac.txt` hotové (2026-10-27). V `.venv` na PC 1 je `psutil` + `llama-cpp-python` 0.3.36 CUDA (2026-10-28). **PyQt6 6.11.0** je na MacBooku (overené 2026-11-02 spustením UI); na PC 1 overiť pred prvým spustením `main.py`.
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
9. [ ] Minimálne UI: okno, vstup, streamovaná odpoveď cez worker (`ui/workers.py` obalí `LlmEngine.stream()`; `request_stop()` je volateľný z UI vlákna) + sidebar s chatmi
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
   **Kúsok 3 – kostra okna a témy ✅** (hotové 2026-11-03 na M2: autor prepísal, Claude skontroloval a opravil 6 chýb, overené spustením v oboch témach; **necommitnuté** spolu s novou `fukai.ico`): sidebar (logo, 3 taby, „Fúkni nový chat“, zoznam „Posledné“ z databázy, kopce) | zaoblený panel s `QStackedWidget` (Chat s hlavičkou a čipom hardvéru, Vlastnosti a Nastavenia zatiaľ prázdne). Súbory: `ui/style.py` (prepísaný: `THEMES` + QSS šablóna), `ui/icons.py`, `ui/sidebar.py`, `ui/chat_view.py`, `ui/main_window.py`; assety `assets/icons/*.svg` (15 ikon zo šablóny, bez zámku), `assets/logo_sidebar_light.png` / `_dark.png`, `assets/hills.svg` (bez `class`/`id` atribútov z Tailwindu). `strip.svg` sa nepoužíva (rozhodnutie autora). Rozhodnutia:
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
   - **Pasce pri prepise** (2026-11-03, opravené pri kontrole; štyri ticho, dve pádom):
     - `self._reload_chats()` volané, ale metóda sa volá `reload_chats` → `AttributeError` hneď v konštruktore okna.
     - `hills.renderer().staticMetaObject(KeepAspectRatio)` namiesto `setAspectRatioMode(...)` → `TypeError`, `staticMetaObject` je atribút každej Qt triedy, nie metóda. Doplňovanie v editore ho ponúkne medzi prvými.
     - `button(PAGE_CHAT).setCheckable(True)` namiesto `setChecked(True)` – tlačidlo už checkable je, takže po štarte **nebol zapnutý žiadny tab**. Ticho. Tá istá dvojica mien ako `isNull` / `isNull()` z kúsku 1: líšia sa pár písmenami a obe sú platné.
     - `layout.addSpacing(0)` namiesto `setSpacing(0)` – pridá prázdnu medzeru nulovej veľkosti, predvolený rozostup layoutu zostane a medzi sidebarom a panelom je pás pozadia okna. Ticho.
     - `top.setContentsMargins(16, 20, 26, 0)` – preklep, taby a tlačidlo boli užšie sprava. Ticho.
     - `__all__` s `"PASE_SETTINGS"` – `from ui.sidebar import *` padne na `AttributeError`; bežný `from ui.sidebar import Sidebar` to neodhalí. Ticho, kým to niekto neskúsi.
   **Rozostupy tlačidiel na macOS ≠ Windows** (zistené autorom 2026-11-03, príčina overená meraním): `setSpacing(8)` medzi tabmi dal na Windows 8 px, na Macu sa tlačidlá prekrývali.
   - **Príčina nie je OS, ale natívny štýl `macos`.** Ten pre `QPushButton` hlási layoutu *layout item rect* menší než widget (rezerva na natívny tieň tlačidla, ~6 px hore aj dole) a layout ukladá tlačidlá podľa neho. Náš QSS tlačidlo vykreslí cez celý widget, takže sa prekryje so susedom. Namerané na M2: `setSpacing(8)` → medzera **−4 px**; autorovo `16` → **4 px** (nie 8 ako na Windows). Týka sa každého `QPushButton` v layoute – aj „Fúkni nový chat“ a budúcich tlačidiel composera.
   - **Riešenie: `self.setStyle("Fusion")` v `Application.__init__`** (rozhodnuté a urobené 2026-11-03, autor schválil). Fusion je rovnaký na oboch OS a takú rezervu nemá – overené na `cocoa` cez skutočnú `Application`: medzery tabov 8 / 8 px, pred „Fúkni nový chat“ 16 px (8 + `addSpacing(8)`). Rozostup tabov je späť na `top.setSpacing(8)` pre oba OS. Keďže celý vzhľad je z QSS, natívny štýl nám nič nedáva, len rozdiely. Natívne zostanú systémové dialógy (`QFileDialog`). Lokálna alternatíva: `setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)` na každom tlačidle – presné, ale treba na to pamätať pri každom novom.
   - **Zamietnuté: rozostup podľa OS** (`8` vs `16`). Na Macu nedá rovnaký výsledok, treba ho opakovať pri každom tlačidle a `Sidebar` kvôli tomu závisel od `HardwareProfile`.
   - **Pasca pri testovaní:** `QT_QPA_PLATFORM=offscreen` natívny štýl macOS nepoužíva, takže screenshoty z kúsku 3 chybu neukázali. Rozdiely štýlu sa overujú na platforme `cocoa` – widget sa dá zmerať (`layout().activate()`, `geometry()`) aj vykresliť (`grab()`) bez `show()`, teda bez okna na obrazovke.
   **Kúsok 4a – worker a `LlmService`** (navrhnuté 2026-11-03, autor prepísal 2026-11-04, Claude opravil 3 chyby, test prešiel nad repom; **`Application` ešte nemá `self.llm`** – zapojenie čaká; poradie zmenené – worker pred composerom, lebo určuje tvar UI). Súbory: `ui/workers.py` (`GenerateRequest`, `GenerationResult`, `LlmWorker`), `ui/llm_service.py` (`LlmService`), `Application` ju vlastní ako `self.llm`. Konzolový test bez okien: `test_worker.py <model.gguf>` (v scratchpade). Rozhodnutia:
   - **Jeden trvalý worker v jednom `QThread`** (`moveToThread`), od štartu po koniec appky. Všetky operácie s modelom – `load`, `build_prompt` (tokenizácia), `stream`, `unload` – idú cez neho, teda za sebou; na tom stojí tokenizácia bez zámku (krok 3). Zamietnuté: podtrieda `QThread` s `run()` (vlákno na odpoveď), `QThreadPool` (súbežnosť).
   - **UI hovorí len so službou, nie s workerom ani engine** (rozhodnutie autora). `LlmService(QObject)` v UI vlákne vlastní engine, vlákno aj workera; metódy `load`, `generate → request_id`, `stop`, `unload`, `shutdown`; signály `loaded`, `load_failed`, `token(id, text)`, `finished(id, GenerationResult)`, `failed(id, FukaiError)`, `busy_changed`. `engine` je vystavený len na čítanie údajov o modeli.
   - **Jedno generovanie v celej appke** (rozhodnutie autora). Pri prepnutí chatu alebo tabu odpoveď dobehne na pozadí do pôvodného chatu (`request_id`), ale novú správu – v žiadnom chate – nejde odoslať, kým nedobehne. Drží to `LlmService.busy`; `generate()`/`load()` počas `busy` vyhodí `RuntimeError` – chyba programu, UI má mať tlačidlá vypnuté podľa `busy_changed`.
   - **Stop obchádza frontu.** Signál do workera by prišiel až po konci odpovede (overené: slot zavolaný po 1,01 s namiesto 0,2 s). `stop()` volá priamo `worker.cancel(id)` a `engine.request_stop()`. `cancel` pokrýva Stop pred `stream()`, ktorý si príznak enginu na začiatku nuluje (krok 3, kúsok 6): worker ho kontroluje po `build_prompt` a znova v cykle – tam už `clear()` prebehol, takže `request_stop()` zaberie. Príznak je **id požiadavky**, nie bool, takže ho netreba nulovať a nemôže zabiť ďalšiu odpoveď.
   - **Každý slot workera chytá aj `Exception`** a mení ju na `failed` / `load_failed` (`GenerationError`, `ModelLoadError`). Neodchytená výnimka v slote zhodí celý proces (overené: abort, `exit 134`).
   - **`n_ctx` nie je v `GenerateRequest`** – worker berie skutočný `engine.n_ctx`; hodnota z UI by po reloade mohla byť oschnutá.
   - **Do databázy worker nesiaha.** `GenerationResult` nesie `counted`, `dropped`, `prompt_tokens` (odhad) a štatistiky (`first_token_s`, `total_s`, `completion_tokens` cez `count_tokens` hotového textu, `tokens_per_s` bez času promptu); zapisuje UI vlákno (4b).
   - **`shutdown()`: stop → `quit()` → `wait()` → `unload()`**, volá ho `Application.shutdown()` **pred** `db.close()`. `unload()` beží až po skončení vlákna. Načítanie modelu sa prerušiť nedá – zatvorenie počas neho počká.
   - **Overené na M2, Gemma 3 4B** (2026-11-03): odpoveď 22,9 tok/s, prvý token 0,22 s, UI vlákno tikalo celý čas (28× za 1,4 s pri 50 ms časovači); Stop po 1 s → `STOPPED`; Stop pred `stream()` → `STOPPED` s prázdnym textom; ďalšia odpoveď po Stope normálne `DONE`; `max_tokens > n_ctx` → `failed` s `ContextOverflowError`, appka žije; `shutdown()` počas generovania 0,19 s, model uvoľnený, bez `QThread: Destroyed while thread is still running`.
   - **Pasce pri prepise** (2026-11-04, overené testom nad repom):
     - `self.load_failed.emit(notices)` v úspešnej vetve `load` – UI by úspešné načítanie bralo ako chybu a `loaded` nepríde nikdy. Test skončil na `TimeoutError: loaded`.
     - `self.tokens.emit(...)` (signál je `token`) a `time.monotronic()` – oba sú `AttributeError`, ale **záchytná `except Exception` v slote ich premení na `GenerationError`**: appka nespadne, len každá odpoveď skončí toastom „Odpoveď sa nepodarilo vygenerovať“. Cena za to, že výnimka nesmie zhodiť proces – preklep v kóde vyzerá ako chyba modelu. Pravidlo: pri `failed` vždy pozrieť `detail` v logu (je tam `AttributeError: …`).
     - `def busy(self) -> None` pri `@property`, ktorá vracia `bool` – len anotácia, beží to, ale klame.
   - **Proces, ktorý skončí s načítaným modelom, na Metale spadne pri ukončení:** `GGML_ASSERT([rsets->data count] == 0) failed` v `ggml_metal_device_free` počas `exit()` (overené – test skončil výnimkou bez `shutdown()`). Dôvod, prečo `unload()` v `shutdown()` nie je kozmetika; každá cesta ukončenia appky musí prejsť cez `Application.shutdown()`.
   **Ďalej v kroku 9** (stav 2026-11-03):
   - **Kúsok 4b – tok správy:** odoslanie → `LlmService.generate()` → po `finished` otázka aj odpoveď v **jednej transakcii** (nová `Database.add_turn(...)`, dnes je `add_message` transakcia na správu), nový chat vznikne až tu (§7.1); `set_message_tokens(result.counted)`; pri `STOPPED` / `failed` sa nezapíše nič a otázka sa vráti do poľa; do `content.data` odpovede model, `finish_reason` a štatistiky (meta riadok). Dočasne pre vývoj: model zapísaný do tabuľky `models` skriptom (symlink v `devdata/models/`), kým nie je import (krok 10–11).
   - **Kúsok 4c – UI:** composer (auto-výška do 200 px, Enter / Shift+Enter, Send/Stop podľa `busy_changed`) a zoznam správ (`QScrollArea`, max 760 px), najprv obyčajný text, potom markdown + `pygments`; výber modelu **bez zámku**, počas `busy` vypnutý.
   - **Kúsok 3b – menu ⋯ pri chate:** tlačidlo ⋯ len pod myšou, `QMenu` Premenovať (inline `QLineEdit`) / Vymazať, zaoblené menu cez `FramelessWindowHint` + `WA_TranslucentBackground`. Sidebar dostane signály, nie `Database`. Vymazať chat, do ktorého práve beží odpoveď, treba ošetriť.
   - Prepínanie témy za behu príde so stránkou Nastavenia (`setStyleSheet` + `apply_theme()`).
   - Ponúknuté, nerozhodnuté: `sys.excepthook` → fatálny dialóg pri neodchytenej výnimke; generátor ikon do repa (`tools/`).
   - **Overiť na PC 1:** PyQt6 v `.venv`, ikona na paneli úloh (AppUserModelID + nová `fukai.ico` s bielou dlaždicou; pri starej ikone reštartovať Prieskumníka – cache ikon), sidebar s Fusion, worker s CUDA.
10. [ ] **Čítač hlavičky `.gguf`, ktorý nenačíta model** – prerekvizita importu modelu. *Overené 2026-10-30:* `n_layers` aj `n_ctx_train` v `llm_engine.py` idú cez `self._llm._model.model`, teda sú dostupné **až po `load()`**. Popup so zoznamom modelov a rozsahy slidrov ich ale potrebujú **pred** načítaním, preto sa čítajú raz pri importe a cachujú v `models.meta` (§7.1). Pri vytváraní chatu to nevadí – model vtedy už beží.
11. [ ] Panel nastavení per chat + výber a import modelu
12. [ ] Prílohy (drag & drop, extrakcia, kontrola tokenov) – prvá migrácia schémy, `SCHEMA_VERSION` na 2
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
