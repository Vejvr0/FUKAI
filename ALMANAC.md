# FUKAI – Almanac

Zdieľaná pamäť projektu pre Claude Code na všetkých strojoch (Mac aj PC). Sem patria rozhodnutia, obmedzenia a kontext, ktorý sa nedá vyčítať z kódu. Pri zmene rozhodnutia prepíš príslušnú sekciu, nepridávaj protichodné záznamy. Posledná revízia: 2026-10-30.

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
- **Rozhodnuté 2026-10-28: samostatný „rozpočet pamäte“ v `hardware.py` sa nerobí.** Stačí `ram_available_mb` z profilu a orientačné porovnanie s veľkosťou `.gguf` priamo v `llm_engine`, s `Notice` pri nedostatku. Na Macu je `ram_available_mb` aj tak jediné správne číslo, lebo GPU berie z tej istej pamäte. **Pozor:** `ram_available_mb` (aj `gpu.vram_free_mb`) sa merajú raz pri `detect()`, takže pred načítaním modelu si `llm_engine` musí spraviť **nové** meranie – hodnota z času štartu appky je už neplatná.
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

- **Web search má dve úrovne:** globálne *je funkcia dostupná* (nastavenie aplikácie) a per-message *použiť ju teraz* (prepínač, §2). Treba to takto pomenovať, inak budú v UI dva prepínače, ktoré si odporujú.
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

0. [x] `requirements.txt`, `requirements-llama-win-cuda.txt`, `requirements-llama-mac.txt` hotové (2026-10-27). V `.venv` na PC 1 je `psutil` + `llama-cpp-python` 0.3.36 CUDA (2026-10-28). **PyQt6 ešte nie je nainštalovaný** – príde s krokom 4.
1. [x] `core/errors.py` – hierarchia chýb delená **podľa príčiny**, nie podľa modulu. Každá chyba nesie tri oddelené texty: `message` (veta pre používateľa), `hint` (čo s tým), `detail` (technický text do logu). Plus `Notice` + `Severity` na **nefatálne** oznámenia. Vďaka tomu UI vykresľuje chyby aj varovania rovnako. `hint` je keyword-only, aby sa tie tri texty nedali zameniť.
2. [x] `core/hardware.py` – detekcia a 4 kontroly (`check_os`, `check_cores`, `check_ram`, `check_gpu`). Overené na PC 1 aj MacBooku. Dáva tri veci, pre ktoré modul existuje: `n_threads` (= `cores_performance`), `n_gpu_layers` (−1/0 podľa backendu) a `backend` (`cuda`/`metal`/`cpu`). **Zásada: detekcia nikdy nevyhodí výnimku von** – zlyhanie sondy sa mení na `Notice` a appka beží na CPU. `required_wheel()` je zvlášť, mimo `check_gpu` – nie je to problém, ale fakt, a hlásiť ho treba až keď llama-cpp-python chýba. Pevné údaje (minimálne verzie OS, mapa compute capability → wheel) sú vo `vars/hw.json`, konštanty v `core/constants.py`.
3. [x] `core/settings.py` (`LoadParams` / `SamplingParams`) + `core/llm_engine.py`, otestované v konzole (2026-10-28, PC 1): load `.gguf`, streaming aj stop fungujú, GPU offload overený (§3). `python -m core.llm_engine [cesta/k/modelu.gguf]`.
   **Na MacBooku zostáva:** nainštalovať `requirements-llama-mac.txt` a spustiť ten istý konzolový test – Metal wheel ani `_performance_cores_macos()` nie sú overené na reálnom stroji.
4. [x] `core/paths.py` – jediné miesto, ktoré vie, kde má aplikácia svoje dáta (`app_dir`, `settings_path`, `db_path`, `default_models_dir`, `ensure_dir`). Podrobnosti a dôvody v §7.1.
5. [x] **Úložisko** (2026-10-28/30). `storage/constants.py` (schéma + pragmy + `SCHEMA_VERSION`) a `storage/database.py` – trieda `Database` so spojením, pragmami, migráciami cez `PRAGMA user_version` a operáciami nad `models`, `chats`, `content` aj `properties`. Overené konzolovým self-testom: `python -m storage.database` – pokrýva aj atomicitu, `ON DELETE CASCADE` a `SET NULL`.
   Kľúčový primitív je **`Database.transaction()`** – kontextový manažér, ktorý vydá spojenie a celý blok commitne alebo rollbackne. Existuje preto, že `create_chat`, `add_message` a `set_model` potrebujú viac príkazov naraz a `execute()` je jedna transakcia na volanie. **Vnútri `transaction()` sa volá `conn.execute()`, nikdy `self.execute()`** – to druhé zamrzne na `self._lock`. Overené 2026-10-29/30, pozri §7.4.
6. [ ] **`core/settings.py` – vlastnosti chatu** ← **ďalší krok** (autor píše sám od nuly, 2026-10-30). Prepojí `storage/` s `llm_engine`. Kontrakt v §7.2; `LoadParams` a `SamplingParams` už obsahujú presne schválené polia, chýba tretia skupina a obal nad nimi.
   *Poradie zmenené 2026-10-30:* pôvodne bol 6. `context.py` a 7. `app_settings.py`. Dôvod: `create_chat` aj `set_model` berú `properties: dict` zvonku a **dnes ho nemá kto zostaviť**, takže hotové úložisko sa nedá použiť. `context.py` navyše potrebuje bežiaci engine, takže ide až potom.
7. [ ] `core/app_settings.py` – `settings.json` (`models_dir`, prepínače, téma, posledný model). Malý a nezávislý; pozor, je to **iné úložisko než vlastnosti chatu** (§7.1).
8. [ ] `core/context.py` – počítanie tokenov a orezávanie histórie. Engine dáva `tokenize()`, `count_tokens()`, `n_ctx` a `n_ctx_train`, úložisko `content.tokens` per správa. Orezáva sa **to, čo ide do promptu**, nie to, čo je v databáze (§7.2). Pozor na `content_tokens()`: vracia `0` pri prázdnom chate aj pri samých `NULL` tokenoch, čo sú pre tento modul dve rôzne veci.
9. [ ] Minimálne UI: okno, vstup, streamovaná odpoveď cez worker (`ui/workers.py` obalí `LlmEngine.stream()`; `request_stop()` je volateľný z UI vlákna) + sidebar s chatmi
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
- **Nástroje na PC 1 sú k dispozícii** (overené 2026-10-28): MSVC 14.44.35207 z VS 2022 BuildTools, CMake priložený k BuildTools, nvcc 13.0.88. `cl.exe` ani `cmake` **nie sú v PATH** – build spúšťať z „x64 Native Tools Command Prompt for VS 2022“. Na macOS bude treba Xcode Command Line Tools a cmake.
- AMD cez `GGML_HIP` na Windows je problematické (ROCm má na Windows obmedzenú podporu); praktickejší by bol `GGML_VULKAN`. **Mimo rozsah projektu** – §1 fixuje NVIDIA + Apple Silicon.

### 10.2 Pozor na „CUDA build s CPU fallbackom“

CUDA zostavenie `llama.dll` je nalinkované na ovládač NVIDIA (`nvcuda.dll`). Na stroji bez NVIDIA karty sa knižnica nemusí vôbec načítať – takže nie je na čo spadnúť a `n_gpu_layers=0` to nezachráni. Pre Windows preto treba počítať s **dvoma buildmi** (CUDA + CPU), nie s jedným prepínačom.

**Varianty inštalačky – nerozhodnuté:**

1. Štyri inštalačky podľa architektúry GPU. Funguje offline, ale používateľ musí vedieť, akú má kartu.
2. Inno Setup v `[Run]` sekcii stiahne správny balík. Malá inštalačka, potrebuje internet pri inštalácii.
3. CPU základ + voliteľné dotiahnutie GPU akcelerácie pri prvom spustení. Najpríjemnejšie pre používateľa, ale blokuje to nesúlad verzií (vyššie).

**macOS je jednoduchší** – Metal build je jeden pre všetky Apple Silicon, žiadna matica architektúr ani cuBLAS.
