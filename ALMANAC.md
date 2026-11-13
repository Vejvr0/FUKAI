# FUKAI – Almanac

Zdieľaná pamäť projektu pre Claude Code na všetkých strojoch (Mac aj PC). Sem patria rozhodnutia, obmedzenia a kontext, ktorý sa nedá vyčítať z kódu. Pri zmene rozhodnutia prepíš príslušnú sekciu, nepridávaj protichodné záznamy. Posledná revízia: 2026-11-11 (skrátené).

Plné znenie do 2026-11-11 – podrobnosti každého kúsku, merania, zahodené alternatívy a pasce pri prepise – je v `archiv/ALMANAC-2026-11-11.md`. Keď tu niečo chýba, hľadaj tam. Výsledky testov sú v `APPTEST.md`, história práce v `SESSIONS.md`.

## 1. Projekt

- **FUKAI** = Fakultná Univerzálna Kognitívna AI. Univerzitný projekt (Žilinská univerzita), autor Lukáš Vavro.
- Desktopová aplikácia na chat s lokálnymi LLM (štýl Ollama / LM Studio), Windows + macOS.
- Repo https://github.com/Vejvr0/FUKAI (**verejné od 2026-11-13**). **Licencia GPL-3.0-or-later** (rozhodnutie autora 2026-11-13; PyQt6 je GPL-3.0-only, takže GPL v3 je povinná), `LICENSE` = nezmenený oficiálny text z gnu.org (35 149 B, SHA-256 `3972dc97…6986` – GitHub ho rozpozná), copyright „Copyright (C) 2026 Lukáš Vavro“ a poznámka „or later“ v `THIRD_PARTY_LICENSES.md` (a v README). `THIRD_PARTY_LICENSES.md` = licencie všetkých balíkov zo zámku + Python, Qt, llama.cpp, `uv`, NVIDIA (proprietárne, FUKAI ich nešíri – inštalačka ich sťahuje z PyPI). Verzia prvého vydania **1.0**. Kód sa synchronizuje **iba cez Git**; OneDrive je na dokumenty a návrhy (šablóna UI `semestralka/UI/template/`, originály loga `semestralka/brand`).
- **Assety** (`assets/`): `logo.png` 1254 px s bielym pozadím je zdroj všetkého; `logo_transparent.png` (color to alpha); `ico/fukai.ico` – jeden súbor s 9 veľkosťami 16–256, logo na bielej zaoblenej dlaždici takmer cez celé plátno (okraj 1/32, polomer 22 %); `icns/fukai.icns` – dlaždica podľa Apple mriežky (824/1024). **Pod 128 px len symbol bez nápisu.** Ikony vyrobil skript mimo repa (numpy + PyQt6 + `iconutil`; `.ico` bez Pillow; zmenšovať `QImage.scaled(…, SmoothTransformation)`, nie `QPainter`).
- **Splash** `assets/splash_screen.png` 1624 × 1320, dole pruh `#3d87b6`. Verzia sa do obrázka nepíše, vpravo v pruhu je stav štartu kreslený v kóde.

## 2. Funkcie (rozsah)

1. Chat so streamovanou odpoveďou, tlačidlo Stop.
2. Ukladanie chatov (zoznam v sidebare, premenovanie, mazanie).
3. Prílohy: txt/md/csv/json/kód, PDF, xlsx, docx. Bez OCR.
4. Webové vyhľadávanie ako rozšírenie (prepínač v input riadku, drží sa per chat – §7.2).
5. Výber `.gguf` modelu a parametre per chat: max tokens, context length, temperature, repeat penalty, top_p/top_k, CPU vs GPU podľa detegovaného HW.

## 3. Stack (zafixované)

| Komponent | Verzia | Poznámka |
|---|---|---|
| Python | 3.12.10 | `.venv` v koreni projektu, na každom OS vlastné |
| PyQt6 | 6.11.0 | GPL v3 – pre univerzitný projekt OK |
| llama-cpp-python | **0.3.36** | rovnaká verzia na oboch OS |

- **Závislosti** (od 2026-11-12): `requirements.txt` = priame závislosti appky (bez llama-cpp-python – ten je platformovo a GPU-špecifický); `dist/requirements-nvidia.txt` = cuBLAS a CUDA runtime; **zámky `dist/locks/{mac-metal,win-cpu,win-cuda}.txt`** = presná verzia a SHA-256 každého balíka z PyPI pre backend (generuje `dist/make_locks.py`, §10); wheel llama-cpp-python podľa `dist/manifest.json`. Súbory `requirements-llama-*.txt` zrušené.
- **Vývojové prostredie = prostredie používateľa:** `uv pip install --require-hashes -r dist/locks/<backend>.txt` + `uv pip install --no-deps dist/backend_whls/llama-0.3.36-<backend>/…whl` (wheely mimo gitu – stiahnuť z repa na vydania, alebo Metal postaviť podľa §10).
- **Wheels pôvodne z oficiálnych vydaní autora** (`abetlen/llama-cpp-python`, teraz kópie v našom repe na vydania, §10). CUDA wheel je **jeden pre všetky NVIDIA karty** (bez `sm` v názve), CPU aj CUDA sú na tej istej verzii.
- **Mac:** oficiálny Metal wheel 0.3.36 je poškodený (`Bad CRC-32`, chyba v nahranom súbore) → vlastný wheel postavený zo zdrojákov (stačia Xcode CLT, cmake si pip stiahne; postup a voľby v §10). Metal na M2: `recommendedMaxWorkingSetSize` 5726 MB.
- **Overené na PC 1:** wheel beží na `sm_120` (`offloaded 35/35 layers to GPU`), **cuBLAS v ňom nie je**. Z CUDA `ggml-cuda.dll` importuje len `cublas64_13.dll` (+ `cublasLt64_13.dll`); `nvcuda.dll` a `nvcudart_hybrid64.dll` dodáva ovládač a načítajú sa až za behu (sú len reťazce, nie importy); CUDA runtime je nalinkovaný staticky. cuBLAS sa dá nainštalovať pipom bez Toolkitu (§10). Wheel obsahuje cubiny len pre `sm_75, 80, 86, 89, 90` + PTX `compute_90` → **minimálna compute capability 7.5**, ovládač **≥ 580**. CUDA backend je naozaj nainštalovaný, keď je v `llama_cpp/lib/` **`ggml-cuda.dll`** (header `ggml-cuda.h` tam je vždy).
- **Compute capability ≠ verzia CUDA.** Capability (12.0 = `sm_120`) je vlastnosť čipu, používa sa už len na diagnostiku (`vars/hw.json`). Wheels sú `py3-none` (ctypes), nezávislé od verzie Pythonu.
- **Warm-up = JIT preklad PTX ovládačom** (overené 2026-11-12): karty nad `sm_90` (RTX 50xx) nemajú vo wheeli cubin, ovládač pri prvom behu preloží PTX `compute_90` (prvé generovanie ~2–6 tok/s, ďalšie ~110) a výsledok uloží do `%APPDATA%\NVIDIA\ComputeCache` (~1,2 GB). `sm_75`–`sm_90` warm-up nemajú. Prvé generovanie nesmie vyzerať ako zamrznutie.
- **CPU aj CUDA wheel vyžadujú AVX2 + FMA + F16C** (jediná `ggml-cpu.dll`, bez variantov) → na CPU starších než Intel Haswell 2013 / AMD 2015 sa appka nespustí vôbec. Kontroluje inštalačka (§10).
- Web: `ddgs==9.16.1` + **`primp==2.0.1`** – pinovať oba (9.7.1 s primp 2.x padá na `Invalid impersonate`).

## 4. Vývojový hardvér

| Stroj | CPU | GPU / VRAM | RAM | Stav |
|---|---|---|---|---|
| MacBook | Apple M2 (4P + 4E) | integrovaná, zdieľaná | **8 GB** | Metal; veľký test 2026-11-09 (`APPTEST.md`) |
| PC 1 | Core Ultra 7 265K (8P + 12E) | RTX 5060 Ti 16 GB (sm_120) | 32 GB | CUDA Toolkit 13.0, driver 621.14; celá appka overená 2026-11-06, veľký test 2026-11-11 (`APPTEST.md` → WINDOWS) |
| PC 2 | – | RTX 4080 16 GB (sm_89) | – | neoverený |
| Notebook | i7-11850H (8C/16T) | T1200 4 GB (sm_75), Optimus | 64 GB | CPU wheel, Gemma 3 4B 13–14 tok/s; CUDA wheel neskúšaný |

- **Mac 8 GB je najslabší článok** – modely do ~3–4B Q4; pred načítaním treba odhadnúť pamäť a varovať.
- **Voľná pamäť sa meria vždy nanovo** (`hardware.free_ram_mb()`), nie z `HardwareProfile` (meraný raz pri štarte). **`psutil.available` na macOS podhodnocuje** (nezapočíta súborovú cache s váhami cez mmap) → na macOS `vm_stat`: `celková − (Anonymous − purgeable + wired + occupied by compressor)`.
- **`n_threads` = výkonné jadrá**, nie `cores_physical` (265K: 8 z 20, M2: 4 z 8). Windows: `GetLogicalProcessorInformationEx`, najvyšší `EfficiencyClass` (P a E jadrá sú v zozname premiešané); macOS: `sysctl hw.perflevel0.physicalcpu`; inak fallback.
- Offload overovať podľa logu (`offloaded N/N layers to GPU`, `CUDA0 model buffer`), nie podľa toho, že appka nespadla.

### 4.1 Testovacie modely

Mimo repa, nekopírovať do projektu. PC 1: `../llama-chatbot/models/` (Gemma 3 4B it Q4_K_M, Mistral 7B Instruct v0.2 Q4_K_M, Qwen 2.5 1.5B Instruct Q4_0 – doplnený 2026-11-11 z `Qwen/Qwen2.5-1.5B-Instruct-GGUF`). Mac: `devdata/models/` (Gemma 3 4B, Qwen 2.5 1.5B Instruct Q4_0). `mmproj-google_gemma-3-4b-it-f16.gguf` na test odmietnutia; **na PC 1 ho netreba sťahovať** – rovnakú cestu `check_usable` overí syntetická hlavička s `general.architecture = clip` (generátor v scratchpade testu, §8.3).

## 5. Prototyp `llama-chatbot` – čomu sa vyhnúť

`../llama-chatbot/` je starší prototyp; FUKAI je prepis, kód sa nekopíruje. Jeho chyby, ktoré FUKAI nesmie zopakovať: generovanie v UI vlákne; model načítaný v konštruktore pri štarte; ručne písaný počet vrstiev v JSON; `n_ctx` natvrdo bez orezávania histórie; whitelist verzií OS; inline štýly pri každom widgete; história ako placeholder; `settings.json` vedľa kódu; system prompt natvrdo v kóde. Prebraté: sidebar + `QStackedWidget`, úvodná obrazovka s logom, slider CPU/GPU.

## 6. Architektúra

Hranice: `core/`, `storage/` a `extensions/` nevedia o Qt; `ui/` služby (`*_service`, `ChatController`, `ModelLibrary`) nevedia o widgetoch; widgety nevedia o databáze – prepája ich `MainWindow`. Plochá štruktúra (nie `src/fukai/`), jednoduchšie sa balí.

```
FUKAI/
├── main.py                    # → ui.application.Application
├── core/                      # bez Qt
│   ├── constants.py           # hranice parametrov, kľúče META_*, texty do promptu, cesty k vars/
│   ├── errors.py              # FukaiError (message / hint / detail), Notice, Severity
│   ├── paths.py               # app_dir() (+ FUKAI_HOME), settings, fukai.db, models/, logy
│   ├── log.py                 # setup_logging(), enable_crash_log()
│   ├── app_settings.py        # AppSettings ↔ settings.json (atomický zápis)
│   ├── settings.py            # LoadParams / SamplingParams / ChatParams / ChatProperties, ModelMeta
│   ├── hardware.py            # detekcia CPU/RAM/GPU, kontroly pri štarte, free_ram_mb()
│   ├── monitor.py             # vzorky vyťaženia CPU/GPU/pamäte
│   ├── gguf.py                # čítač hlavičky .gguf, check_usable()
│   ├── llm_engine.py          # probe_engine(), load/unload, stream, stop, tokenize, memory_pool()
│   └── context.py             # tokeny, orezanie histórie, prílohy a web do promptu
├── storage/                   # constants.py (schéma v2), database.py (Database)
├── extensions/                # file_parser.py (prílohy), web_search.py (ddgs + trafilatura)
├── ui/
│   ├── application.py         # štart (splash), služby, excepthook, shutdown()
│   ├── main_window.py         # poskladanie widgetov a signálov, show_notice (→ log)
│   ├── chat_controller.py     # tok správy, draft vlastností, zápis ťahu, vrátenie pri Stope
│   ├── llm_service.py, workers.py   # jedno vlákno pre model (LlmWorker), ImportWorker, WebWorker
│   ├── attachments.py, web_service.py, model_library.py, settings_store.py
│   ├── sidebar.py, chat_view.py, message_list.py, markdown.py, composer.py, attachment_bar.py
│   ├── properties_view.py, settings_view.py, usage_panel.py, model_info.py, text_preview.py
│   └── toast.py, toggle_switch.py, splash.py, icons.py, style.py, formatting.py, constants.py
├── vars/hw.json               # minimá: OS (macOS 14), jadrá, RAM, compute capability CUDA (7.5)
├── dist/                      # balenie: manifest.json, locks/, make_locks.py, requirements-nvidia.txt;
│                              #   mimo gitu backend_whls/ (wheely) a tools/ (uv)
├── assets/                    # logo, ikony, splash, SVG
└── archiv/                    # plné znenie ALMANAC a SESSIONS do 2026-11-11
```

## 7. Kľúčové technické rozhodnutia

- **Dve skupiny parametrov:** *load-time* (`n_ctx`, `n_gpu_layers`, `n_threads`, `n_batch`) → zmena = reload modelu; *sampling* (`temperature`, `top_p`, `top_k`, `repeat_penalty`, `max_tokens`, `seed`) → per požiadavka.
- **CPU/GPU cez `n_gpu_layers`** (0 = CPU, −1 = všetko na GPU) – slider, maximum `n_layers + 1` (llama.cpp offloaduje aj výstupnú vrstvu: Gemma 35/35, Qwen 29/29, Mistral 33/33).
- **Detekcia HW:** NVIDIA cez `nvidia-ml-py` (import `pynvml`) a `nvidia-smi`, Apple Silicon cez `arm64`, RAM cez `psutil`/`vm_stat`.
- **Vlákna:** načítanie aj generovanie mimo UI vlákna, tokeny cez signály, Stop = príznak (`threading.Event`).
- **Chat template vždy z metadát `.gguf`** (`create_chat_completion()`), žiadne ručné skladanie promptov. Model bez chat template sa odmietne.
- **`verbose=False` neutíši všetko a naopak:** počas `Llama(...)` knižnica cez `suppress_stdout_stderr` presmeruje **fd 1 a 2 celého procesu** – mlčí aj UI vlákno. Ladiace výstupy a log preto nikdy cez `stdout`/`stderr`, len do súboru.
- **Kontext:** orezáva sa to, čo ide do promptu, nie databáza; počíta sa skutočnými tokenmi modelu. RAG mimo rozsahu.
- **Web:** `ddgs` (DuckDuckGo) + `requests` + `trafilatura`. Zapína používateľ prepínačom, model si ho nevolá sám (tool-calling malých modelov je nespoľahlivý).
- **Súbory:** `pypdf` (MIT; PyMuPDF je AGPL), `openpyxl` → markdown tabuľka, `python-docx`. OCR mimo rozsahu.
- **Render odpovedí:** Qt rich text (`QTextBrowser.setMarkdown`) + `pygments`, bez QWebEngine.
- **Distribúcia (rozhodnuté 2026-11-12):** inštalačka zostaví prostredie na cieľovom stroji cez `uv` podľa zisteného hardvéru, nie PyInstaller. Windows: vlastná inštalačka v C#, pre používateľa bez admina; macOS: `.pkg` s `postinstall` (§10).

### 7.1 Nastavenia a úložisko

- **Dve úložiská:** `settings.json` = to, čo treba vedieť pred otvorením databázy (`models_dir`, téma, `attachments_enabled`, `web_search_enabled`, `last_model_id`, `version` – len informatívna pečiatka). Všetko ostatné v `fukai.db` (SQLite): `models`, `chats`, `content`, `properties`, `attachments` (schéma v2). Appka sa spustí aj s rozbitou databázou a povie prečo.
- **Jeden adresár `app_dir()`** = `platformdirs.user_data_dir("FUKAI", appauthor=False)` – Windows `%LOCALAPPDATA%\FUKAI`, macOS `~/Library/Application Support/FUKAI`. `appauthor=False` povinné (inak `FUKAI\FUKAI`), `roaming` vypnuté (gigabajtové modely). Obsahuje `settings.json`, `fukai.db`, `models/`, `fukai.log`, `fukai-crash.log`. platformdirs adresár nevytvorí – `ensure_dir()`.
- **`FUKAI_HOME`** prepíše `app_dir()` (dev a testy; `.resolve()`; prázdna hodnota = nič). Vývoj: `devdata/` (v `.gitignore`).
- **`vars/` = pevné dáta s kódom, iba na čítanie.** `settings.json` tam nepatrí (bez admina sa tam nezapíše, na macOS by zápis rozbil podpis `.app`).
- **Import modelu = kópia do `models_dir`** (ako Ollama), `models.path` relatívna k `models_dir`. Zoznam modelov je tabuľka; **pri štarte ju sken dopĺňa** o nové `.gguf` z priečinka (riadok bez súboru zostane, menu ukáže „súbor chýba“). Metadáta sa čítajú z hlavičky pri importe/skene a cachujú v `models.meta`. Názov modelu = názov súboru bez prípony (rozlíši kvantizácie). Novo vytvorená databáza vynuluje `last_model_id` (id sa prideľujú odznova).
- **Chat vzniká až s prvou dokončenou odpoveďou** (`add_turn` – jedna transakcia). Vlastnosti nového chatu drží controller ako draft.
- **Výmena modelu v chate resetuje celé `properties.data`** na predvolené pre nový model a nuluje `content.tokens` (jedna transakcia `set_model`). Ručná `temperature` sa tým stratí – zámer, jednotné správanie.
- **JSON vs stĺpce:** do JSON to, čo sa číta a zapisuje ako celok (`properties.data`, `models.meta`, `content.data`); do stĺpcov to, podľa čoho sa radí a filtruje (`updated_at`, `last_used_at`, `role`, `tokens`).
- **Web má tri úrovne:** `web_search_enabled` (funkcia dostupná = tlačidlo viditeľné) → `properties.chat.web_search` (zapnuté v chate, sticky) → `content.data.web` (pri tejto odpovedi naozaj použité). **Globálne vypnutie nemení vlastnosti chatov** – platí `enabled AND chat`. Prílohy majú dve úrovne (`attachments_enabled` a text pri správe).
- Prílohy sa ukladajú ako **text, ktorý model dostal**, nie originál. Verzia schémy cez `PRAGMA user_version`. `foreign_keys = ON` pri každom spojení. `content.tokens` je cache závislá od modelu, `NULL` = treba pretokenizovať. `chats.model_id ON DELETE SET NULL`. Cesta k databáze nie je v v1 nastaviteľná.

### 7.2 Vlastnosti chatu

- **Do `properties.data` ide len to, čo UI vie nastaviť.** Blob `{"load": {...}, "sampling": {...}, "chat": {...}}`; `chat` = `system_prompt`, `web_search`. `model_path` sa **neukladá** (ktorý model, hovorí `chats.model_id`; cesta sa dopočíta pri načítaní) – pravidlo žije v `_NOT_STORED`.
- `grammar`, `logits_processor`, `chat_handler` sú objekty, nie dáta; `logit_bias` by JSON pokazil (kľúče ako text). Tool-calling mimo rozsahu.
- **Prázdny system prompt → system správa sa do `messages` nedáva vôbec** (model použije svoj predvolený; Qwen sa s `""` správa inak). Predvolený prompt je prázdny, presety sú tlačidlá.
- **Easy** = systémový prompt + `n_ctx` s odhadom pamäte; **expert** navyše hardvér a generovanie. Režim sa nepamätá.
- **Tlačidlo Použiť len zapisuje**, model sa načíta až pri ďalšej správe (lišta to povie). Karta je počas generovania zamknutá. Zmena `n_ctx` správy nemaže.
- „Model bol vymenený“ sa neukladá ako príznak – signál je `content.tokens = NULL`.

### 7.3 SQLite – pasce (overené, žiadna nevyhodí chybu hneď)

`INTEGER PRIMARY KEY` ≠ `INT PRIMARY KEY` (inak `id = NULL`) · `foreign_keys` sa zapína pri každom `connect()` · `DEFAULT (datetime('now'))` so zátvorkami · `datetime('now')` s úvodzovkami a je **UTC** – všetky časy píše SQLite, formát `'YYYY-MM-DD HH:MM:SS'` · `PRAGMA` neprijíma parametre · `with conn:` je transakcia, nie zatvorenie · cudzie kľúče sa neindexujú samy (`idx_content_chat`) · JSON prevádza `database.py`, nie volajúci (`str(dict)` sa uloží, ale nedá sa prečítať) · WAL `-wal`/`-shm` po korektnom zatvorení zmiznú · `(x,)` nie `(x)` · v `executemany` pri `SET a = ? WHERE id = ?` je n-tica `(a, id)` · cesty pre `json_remove` sú parametre.

### 7.4 Transakcie nad viacerými príkazmi

`Database.execute()` je jedna transakcia na volanie. Viac príkazov naraz = **`Database.transaction()`** (kontextový manažér, vydá spojenie). **Vnútri sa volá `conn.execute()`, nikdy `self.execute()`** – zámok je `threading.Lock` (nie `RLock`) zámerne: vnorené `with conn:` by ticho commitlo skôr, takto to radšej zamrzne pri vývoji.

## 8. Poradie práce a stav

| Krok | Čo | Stav |
|---|---|---|
| 0 | requirements, `.venv` na oboch OS | ✅ |
| 1 | `core/errors.py` | ✅ |
| 2 | `core/hardware.py` | ✅ |
| 3 | `core/llm_engine.py` | ✅ |
| 4 | `core/paths.py` | ✅ |
| 5 | úložisko (`storage/`) | ✅ |
| 6 | `core/settings.py` | ✅ |
| 7 | `core/app_settings.py` | ✅ |
| 8 | `core/context.py` | ✅ |
| 9 | UI (kúsky 1–10) | ✅ |
| 10 | čítač hlavičky `.gguf` (= kúsok 5b) | ✅ |
| 11 | vlastnosti chatu, výber a import modelu (= kúsky 5a–5c, 9) | ✅ |
| 12 | prílohy | ✅ |
| 13 | web rozšírenie | ✅ |
| 14 | opravy pred v1 ✅ → commit ✅ → test na PC 1 ✅ (2026-11-11, 445/445) → **balenie** (návrh 2026-11-12, §10) | 🔄 |

**Prečo jadro pred UI:** tvar UI určuje worker + signály; načítanie CUDA/Metal bolo jediné skutočné riziko; nastavenia sa nedajú navrhnúť bez bežiaceho enginu.

**1. `core/errors.py`** – chyby delené **podľa príčiny**, nie modulu. Každá nesie `message` (pre používateľa), `hint` (čo s tým, keyword-only), `detail` (do logu). `Notice` + `Severity` na nefatálne hlásenia – UI ich vykresľuje rovnako ako chyby. `StorageError` → `DatabaseCorruptError` (B2).

**2. `core/hardware.py`** – `detect(gpu_offload=…)` + kontroly `check_os`, `check_cores`, `check_ram` (WARNING, nie ERROR), `check_gpu`. **Detekcia nikdy nevyhodí výnimku** – zlyhanie sondy = `Notice`, appka beží na CPU. `HardwareProfile.backend` = na čom sa naozaj generuje (GPU, ktorú engine nevie použiť, sa ráta ako `cpu` + varovanie); `backend` je odvodená vlastnosť, nie pole. `hardware.py` llama-cpp-python neimportuje.

**3. `core/llm_engine.py`** – rozhranie: `probe_engine()`, `load(params) -> list[Notice]`, `unload()`, `is_loaded`, `stream(messages, sampling) -> Iterator[str]`, `request_stop()`, `finish_reason`, `tokenize()`, `count_tokens()`, `n_ctx`, `n_ctx_train`, `n_layers`, `n_layers_offloadable`, `memory_pool()`. Engine nevie o Qt, databáze ani orezávaní.
- **Engine je súčasť štartu:** `probe_engine()` počas splashu; bez knižnice fatálna chyba. Zlyhanie DLL knižnica hlási ako **`RuntimeError`** (nie `OSError`) → vlastná správa o CUDA/CPU verzii.
- `load()`: `clamped()` → `validate()` → import pred zámkom → pod zámkom najprv uvoľniť starý model (dva sa na 8 GB nezmestia) → `Llama(model_path=str(...))`. Model sa nikdy nenačíta pri štarte. **O reloade rozhoduje volajúci** (`needs_reload()`), engine reloaduje vždy.
- `_lock` je `threading.Lock`; metódy `_locked` predpokladajú držaný zámok. **Celé generovanie pod zámkom** – `unload()` z iného vlákna počká na koniec odpovede.
- `tokenize`: `add_bos=False` (BOS pridá template), `special=False`; bez zámku (operácie s modelom idú cez jeden worker za sebou).
- `stream()` vracia len text; **Stop = `threading.Event`** kontrolovaný medzi chunkmi (`generator.close()` z iného vlákna padá), `request_stop()` nesmie brať zámok, `clear()` na **začiatku** `stream()`. Stop nie je chyba. `FinishReason` = `DONE`/`LENGTH`/`STOPPED`. Knižnica pri `prompt + max_tokens > n_ctx` ticho skráti `max_tokens` → preto rozpočet v `context.py`.
- **Pamäť:** varovanie pred načítaním (`model × 1,2` proti voľnej pamäti meranej po uvoľnení starého); `memory_pool()`: CPU, bez GPU alebo Metal → RAM; CUDA −1 → VRAM; čiastočný offload → spolu. Výnimka knižnice o príčine nič nehovorí – **preklad podľa fázy**: `Failed to create llama_context` = nezmestil sa kontext → `InsufficientMemoryError`.
- **Gemma vyžaduje striedanie rolí** user/assistant (template inak padá) → história nikdy user, user. Neoverené: Qwen 3 `<think>`, Llama 3 `strftime_now`.
- Každá cesta ukončenia musí prejsť cez `Application.shutdown()` – proces s načítaným modelom na Metale spadne pri `exit()` (`GGML_ASSERT`).

**4. `core/paths.py`** – jediné miesto s cestami (§7.1).

**5. Úložisko** – `Database` (spojenie je stav); migrácie cez `user_version`; `transaction()` (§7.4). `add_turn(chat_id, otázka, odpoveď, …, attachments) -> (chat_id, [id príloh])` – otázka, prílohy a odpoveď (a pri novom chate chat + `properties`) v jednej transakcii, posunie `updated_at`. `get_*` nemení stav (`mark_model_used` zvlášť). `set_message_tokens(counted)` jedna transakcia, `updated_at` nemení. Premenovanie chatu `updated_at` nemení. **B2:** chyby SQLite prekladá `Database._error()` – `SQLITE_NOTADB`/`SQLITE_CORRUPT` → `DatabaseCorruptError` s celou cestou v rade, ostatné → `StorageError` (disk a práva); `connect()` spúšťa `PRAGMA quick_check` (poškodenie v strede súboru inak prejde otvorením aj bežnými dotazmi) a pri chybe spojenie zatvorí. Obnova je ručná (rozhodnutie autora).

**6. `core/settings.py`** – frozen dataclassy. **`clamped()` opraví, `validate()` odmietne.** `ChatProperties.defaults_for(model, hw)`, `to_dict`/`from_dict` (cez `fields()`, `from_dict` končí `clamped()`; `data.get("x") or {}` kvôli `null`), `needs_reload()` porovnáva orezané `load`. `ModelMeta` je dataclass (preklep kľúča = `AttributeError`, nie ticho `None`); `kv_cache_mb(n_ctx)` = `n_ctx × n_layers × n_head_kv × (head_dim_k + head_dim_v) × 2 B` (overené proti logu llama.cpp). **Dve úrovne hraníc:** tvrdá bariéra je konštanta, skutočný strop z modelu (`n_ctx_train`, `n_layers + 1`); maximum slidera = `min(konštanta, model)`.

**7. `core/app_settings.py`** – `load_settings()` nikdy nevyhodí výnimku (`ConfigError` nie je podtrieda `OSError`!), `save_settings()` áno. Atomický zápis `.tmp` + `os.replace`. Rozbitý súbor → predvolené + `Notice`. `models_dir` cez `field(default_factory=…)`; neplatný → `Notice` a predvolený, nedostupný predvolený → fatálne pri štarte.

**8. `core/context.py`** – funkcie, nie trieda (objekt by si držal `n_ctx`, ktoré mení reload). `count` je `Callable[[str], int]`. `build_prompt(history, question, *, system_prompt, n_ctx, max_tokens, count, web=(), attachments=()) -> PromptPlan(messages, counted, dropped, prompt_tokens, budget, web_used, attachments)`.
- Rozpočet `n_ctx − max_tokens − PROMPT_RESERVE (64)`, cena správy `tokens + 8` – zámerne nadsadené (overené proti `prompt eval`).
- **Otázka sa neoreže nikdy** (inak `ContextOverflowError`). **Prílohy** (`fit_attachments`, B4) dostanú celé miesto po nej; keď sa nezmestia, delia sa rovnakým dielom (`_water_fill`), orezaná dostane `ATTACHMENT_CUT_NOTE`, **žiadna sa nevynechá**. **Zdroje z webu** (`fit_web`) dostanú najmenej 60 % zvyšku a viac, keď história miesto nepotrebuje; diel pod 80 tokenov → vynechá sa posledný zdroj. História dostane zvyšok. Priorita: **otázka s prílohami > zdroje > história**.
- Prílohy aj zdroje idú do **tej istej správy** ako otázka (striedanie rolí). Poradie: zdroje → pokyn citovať → prílohy → otázka (pokyn pred zdrojmi Gemma ignorovala).
- Prvá ponechaná správa histórie musí byť `user`, posledná nie `user`. `counted` = len dopočítané tokeny (zápis cez `set_message_tokens`).

**9. UI** – kúsky 1–10 podľa šablóny `semestralka/UI/template/` (záväzná od 2026-11-02; Vlastnosti a Nastavenia podľa jej neskoršej verzie).
- **Vzhľad:** sidebar 272 px (logo, taby Chat / Vlastnosti / Nastavenia, „Fúkni nový chat“, zoznam „Posledné“ podľa `updated_at`, kopce) | zaoblený panel s `QStackedWidget`. Modrá paleta z loga; `THEMES` (tokeny) + jedna QSS šablóna (`string.Template`, chýbajúci token = `KeyError` pri štarte). **`setStyle("Fusion")`** – natívny štýl macOS mal iné rozostupy tlačidiel. Témy za behu cez `MainWindow.theme_changed` → `Application._set_theme`. Čo QSS nevie: tieň `QGraphicsDropShadowEffect`, zaoblené menu `FramelessWindowHint + WA_TranslucentBackground`, SVG ikony prefarbené nahradením `currentColor`, `:focus-within` cez event filter.
- **Kúsok 1 – štart:** `Application` vlastní služby a odovzdáva ich oknám (nie cez `QApplication.instance()`). Poradie: log → nastavenia → engine → hardvér → databáza → priečinok modelov, sken, metadáta. Splash minimálne 2 s. Notice sa ukážu až po zobrazení okna. Windows: `SetCurrentProcessExplicitAppUserModelID` pred `QApplication` (ikona na paneli úloh, overené).
- **Kúsok 2 – toasty** namiesto dialógov (`QMessageBox` len pre fatálnu chybu pri štarte a potvrdenia). Názov podľa `Severity`; INFO 3 s, WARNING 5 s, **ERROR sa sám nezavrie**; pod myšou sa čas zastaví; toast je dieťa okna; trvalý (`persistent`) a s priebehom (`progress`). Toast cez prvú kartu na stránkach Vlastnosti a Nastavenia sa nerieši (rozhodnutie autora).
- **Kúsok 4 – vlákna:** `LlmService` vlastní engine a jeden trvalý `LlmWorker` v `QThread` – všetky operácie s modelom idú za sebou. **Jedno generovanie v celej appke.** **Stop obchádza frontu** (`worker.cancel(id)` + `engine.request_stop()` priamo). Každý slot workera chytá `Exception` (inak pád procesu) – preklep sa potom tvári ako chyba modelu, pozri `detail` v logu. `unload()` je synchrónne. `shutdown()`: stop → `quit` → `wait` → `unload` → až potom databáza.
- **Kúsok 4b – `ChatController`:** model sa načíta až pri odoslaní (trvalý toast „Načítavam model…“), reload keď `LoadParams.clamped()` ≠ vlastnosti chatu. Názov chatu = 15 slov otázky (pri samotnej prílohe názov súboru). **Stop/chyba = vrátenie celého ťahu** (nič sa nezapíše, otázka a prílohy späť do composera, pri prvej správe sa chat nevytvorí). Odpoveď dobehne na pozadí do pôvodného chatu (číslo zobrazenia `_view`), návrat do chatu počas odpovede ju ukáže ďalej. `content.data` odpovede: `text`, `model_id`, `model`, `finish_reason`, `stats`, `dropped`, `web`. **`open_chat` najprv číta, až potom mení stav** (B2). Draft vlastností nového chatu sa nuluje pri výmene/zmazaní modelu a pri odchode z existujúceho chatu, nie pri „Fúkni nový chat“ v novom chate.
- **Kúsok 5 – composer a modely:** `Composer` nevie o controlleri; stavy `busy` / `generating` / `loading`. Enter odošle, Shift+Enter vloží `\n` ručne (inak `U+2028`); pole rastie do 200 px. Menu modelov = `QMenu` s `QWidgetAction` riadkami, zoznam sa číta pri každom otvorení. **Model sa dá zmeniť aj v rozpísanom chate** (reset vlastností, §7.1). `SettingsStore` = jediná živá kópia `AppSettings`. Čítač `.gguf` (5b) vlastný, polia preskakuje `seek`om, každú dĺžku overí proti veľkosti súboru; `check_usable` odmietne mmproj (`arch == "clip"`), nejazykové modely a modely bez chat template. **Import** (5c-2) vo vlastnom vlákne do `*.gguf.part` → `fsync` → `os.replace`; zrušenie `threading.Event`; duplikát podľa názvu + veľkosti; `.part` sa maže až po zatvorení súboru (Windows); počas importu sa dá chatovať; po importe sa model vyberie. **Mazanie** (5c-3): pamäť → súbor → riadok (Windows nezmaže súbor držaný cez mmap – overené na PC 1); kurzor ruky v menu cez `setOverrideCursor` (macOS popup `setCursor` neuplatní).
- **Kúsok 6 – zoznam správ:** text je `QTextBrowser` (zalomí aj slovo bez medzier), výška/šírka cez `fit()`. Stĺpec max 760 px, **vodorovná politika `Ignored`** (A2 – inak deti s pevnou šírkou držia minimum stĺpca a pri zúžení okna sa nič neprepočíta). Streamovanie vkladá na koniec dokumentu najviac raz za 30 ms, kurzor ▍. **Scroll odomknutý** – drží sa spodku, len kým je používateľ dole. **Markdown až po dobehnutí odpovede** (`MarkdownDialectGitHub | MarkdownNoHTML` – bez `NoHTML` Qt zje text za `<`); odpoveď = zoznam častí: text, `_CodeBlock` (strop 400 px, vlastné posuvníky, Kopírovať, farby z tokenov), `_TableBox`. Čipy nad otázkou (`_ChipFlow`) sa zalamujú vpravo a v histórii sú klikateľné (náhľad textu z databázy); po dobehnutí ťahu dostanú id cez `turn_finished` (B1). Správa bez textu nemá bublinu. Stav v bubline (`turn_status`): „Hľadám na webe…“, „Čítam N stránok…“, „Spracúvam zdroje/prílohy…“ od začiatku spracovania promptu po prvý token (B3).
- **Kúsok 3b – menu ⋯ pri chate:** riadok je widget v položke (vlastný `clicked`, ručný elide, hover cez QSS na `QFrame`); veľkosť chatu v tokenoch sa číta pri otvorení menu; premenovanie v riadku; mazanie bez potvrdenia, **chat s bežiacou odpoveďou sa zmazať nedá**. Akcia sa berie z návratovej hodnoty `menu.exec()` a riadok sa po návrate hľadá podľa id (pád pri mazaní počas odpovede, opravené 2026-11-09, **na PC 1 ešte neoverené**).
- **Kúsok 7 – monitor:** CPU, GPU (bez karty 0 %), tretí riadok VRAM pri CUDA, inak RAM (cez `free_ram_mb()`). Vzorka 0,25 ms v UI vlákne cez `QTimer`, beží len kým je panel viditeľný; NVML lenivý; macOS GPU % cez `ioreg` bez čakania (overené). Zapnutie sa nepamätá.
- **Kúsok 8 – Nastavenia:** téma, web, prílohy (zapisujú hneď, „✓ Uložené“; riadia viditeľnosť tlačidiel v composeri); priečinok modelov len „Otvoriť priečinok“ (cesta sa nemení); sken pri otvorení karty; vlastný `ToggleSwitch`. **Kúsok 10:** klik na model → modal s údajmi z hlavičky čítanými nanovo zo súboru.
- **Kúsok 9 – Vlastnosti:** stránka nevie o databáze (`load(props, …)`, `apply_requested`). Slidery nad mocninami dvoch, spinbox prijme aj hodnotu mimo krokov; zápis cez `editingFinished`. **Seed v `QLineEdit`** (nad rozsahom 32-bit `QSpinBox`). Hodnota nad stropom modelu sa zmenší a ukáže ako neuložená zmena. Odhad „model + kontext vs voľná pamäť“ cez `kv_cache_mb` a `memory_pool()`, meraný pri otvorení a zmene `n_gpu_layers`. Mriežky sa pri úzkom okne preskupia (`_Grid`).
- **Log a chyby (A3 + A4):** `setup_logging()` na začiatku `Application.__init__`; moduly `logging.getLogger(__name__)`; `RotatingFileHandler` 1 MB + 1 starší; cudzie knižnice len WARNING. Do logu: hlavička behu, engine, hardvér, **každý toast aj s `detail`** (`MainWindow.show_notice`), načítanie modelu, súhrn odpovede, varovania Qt (bez `qt.qpa.*`). **Texty správ a príloh nie.** `faulthandler` → `fukai-crash.log`. **`sys.excepthook` + `threading.excepthook`:** traceback do logu, appka beží ďalej s chybovým toastom (cez `QueuedConnection` do hlavného vlákna; kým je toast otvorený, ďalšie chyby len do logu). Neočakávaná chyba pri štarte = fatálny dialóg „FUKAI sa nepodarilo spustiť“. **Každý fatálny dialóg má za radou cestu k logu** (`_show_fatal` → `_with_log`, 2026-11-12; bez logu len rada). Rady pri chybe enginu sú pre používateľa („spusti inštaláciu FUKAI znova“), nie pre vývojára – presná príčina je v logu.

**12. Prílohy** – `extensions/file_parser.py` (len `AttachmentError`), `AttachmentService` vo vlastnom vlákne, `AttachmentBar` v composeri: drag & drop, náhľad textu, **`QScrollArea` so zvislým posuvníkom, najviac 2 riadky čipov** (A1; `NoFocus`, čipy vľavo vedľa seba, poradie = poradie pridania, najužší stĺpec = `max(180 px, najširší čip)`). Text prílohy zostáva súčasťou správy, pri ktorej bol pripnutý (ide do promptu aj pri ďalších otázkach). Limit je len kontext: **pri pripnutí sa neorezáva**, len upozorní podľa odhadu `dĺžka / 4`; **orezáva sa až pri zostavení promptu** skutočnými tokenmi a správa sa vždy odošle (B4); uloží sa poslaný text, toast povie, čo sa orezalo. Samotná príloha bez textu je platná správa. Text príloh sa pri otvorení chatu nenačítava (až pri kliknutí).

**13. Web** – `extensions/web_search.py` (len `WebSearchError`, aj „žiadny výsledok“): `ddgs` 5 výsledkov, región `sk-sk`, všetky stránky naraz s termínom 4 s, vyberú sa 3 (s textom v poradí vyhľadávača, inak úryvok), text pod 300 znakov nie je obsah, zdroj najviac 6000 znakov, User-Agent `FUKAI/<verzia>` **s adresou repa** (inak Wikipédia 403). `WebService` vo vlastnom vlákne, zrušenie `threading.Event`, zrušená úloha nevyšle nič. Hľadanie beží **súbežne s načítaním modelu**, generuje sa po oboch. **Dopyt = otázka tak, ako je.** Zlyhanie → toast a odpoveď bez webu. Text stránok žije len v ťahu; uloží sa dopyt a použité zdroje `{n, title, url}`. Zdroje pod odpoveďou ako odkazy (len `http(s)`, escapované – sú z cudzej stránky), „· N zdroje“ v meta riadku. Prepínač Web zapisuje hneď (sticky, v novom chate do draftu), počas ťahu je vypnutý, výmena modelu ho vypne (reset vlastností).

**14. Do prvej verzie** (rozhodnutie autora 2026-11-10): opravy z veľkého testu → commit → test na PC 1 podľa §8.3 (hotový 2026-11-11, výsledky v `APPTEST.md` → WINDOWS: 445 kontrol, žiadna chyba appky, nálezy W1–W4 sú prostredie a knižnica) → balenie (§10: prostredie pri inštalácii cez `uv`, C# inštalačka, `.pkg`, CUDA bez Toolkitu cez pip balíky NVIDIA). Opravy A1–A4 a B1–B4 sú hotové 2026-11-11 (`APPTEST.md` → „Opravy po teste“). Na balenie: assety sa hľadajú cez `Path(__file__).parent.parent` (`ui/constants.py`, `core/constants.py`) – zdrojáky sa inštalujú s rovnakou štruktúrou, takže to platí bez zmeny; na macOS vypnúť obnovu okien po páde (dialóg „obnoviť okná?“ pred splashom) a nastaviť názov appky (v menu je „Python“).

### 8.1 Ako sa na projekte pracuje

- **Po malých kusoch.** Autor chce kódu rozumieť: Claude navrhne a otestuje v scratchpade, autor prepíše do repa (alebo požiada Clauda), Claude prepis skontroluje proti scratchpadu a spustí testy nad repom.
- **Návrh pred kódom**, rozhodnutia autora pred implementáciou; pri rozhodnutí dôvod a zahodená alternatíva.
- **Nekomitovať** – commituje autor.
- Rozhodnutia do ALMANACU (prepísať sekciu), priebeh do `SESSIONS.md`, výsledky testov do `APPTEST.md`.
- Testovať cestou, ktorou ide používateľ (skutočné widgety, skutočná appka), pri oprave chyby najprv zopakovať chybu na pôvodnom kóde.
- Po úprave dokumentu skriptom porovnať počet riadkov / `git diff --stat` (raz skript odsekol polovicu ALMANACU).

### 8.2 Opakujúce sa pasce (Qt a Python)

| Pasca | Prejav |
|---|---|
| **Funkcia vs. jej volanie** – `isNull`/`isNull()`, `read`/`read()`, `trigger`/`triggered`, `emit`/`emit()`, `logs_path`/`logs_path()` | do `connect` a `singleShot` patrí funkcia bez zátvoriek; getter so zátvorkami vykoná prácu |
| **Getter vs. setter** – `toolTip(x)`/`setToolTip(x)`, `devicePixelRatio(x)`, `setCheckable`/`setChecked` | `TypeError` v slote = pád, alebo ticho nič |
| **Atribút prekryje metódu**, **druhá metóda s rovnakým menom** ticho vyhrá | `TypeError: not callable` alebo volanie inej metódy; pri novom mene `grep "def meno"` |
| **Trieda bez `()`** v atribúte | `TypeError: unbound method` až pri prvom volaní |
| **Premenovanie len v polovici súboru**, **zmiznutý susedný riadok** pri úprave bloku | `AttributeError` neskôr alebo tichá chyba; porovnávať `git diff`, nie len to, čo pribudlo |
| **Preklep v `__all__`** | prejaví sa až pri `from … import *` |
| **Písmo zo stylesheetu príde až pri polish** | rozmery a skracovanie textu prepočítať v `changeEvent` (`FontChange`, `StyleChange`) alebo pred meraním `ensurePolished()` |
| **`horizontalAdvance()` je celé číslo nadol** | `elidedText()` skráti text, ktorý sa zmestí; šírka = `ceil(QFontMetricsF(font).horizontalAdvance(…))` |
| **Deti s pevnou šírkou určujú minimum rodiča** | stĺpec sa pri zúžení okna nezmenší a neprepočíta (A2); rodičovi vodorovná politika `Ignored` |
| **`QSizePolicy.Ignored` + `addStretch`** | widget má nulovú šírku; Ignored widget dostane stretch v `addWidget` |
| **Dlhý jednoriadkový text** | drží celú stránku širšiu než panel; skracovať cez `elidedText` |
| **`removeWidget` / `takeAt` widget nezmaže** | zostane viditeľný; pred `deleteLater()` zavolať `hide()` |
| **QSS `border-radius` rodiča neoreže deti** | deti musia mať priehľadné pozadie |
| **`QScrollArea.setWidget()` zapne obsahu `autoFillBackground`**; **`QScrollArea` má `StrongFocus`** | vypnúť až po `setWidget`; pomocný kontajner dostane `NoFocus`, inak berie fokus vstupu |
| **`QColor("rgba(…)")` je neplatná farba** | kreslí sa čierna; `qcolor()` v `ui/style.py` |
| **Výnimka v slote** | bez `excepthook` pád procesu (134); `except Exception` v slote workera premení preklep na doménovú chybu |
| **`pyqtSignal(int)` a `QSpinBox` sú 32-bitové** | bajty nad 2 GiB pretečú (`"qint64"`), seed do `QSpinBox` nevojde |
| **Modálne okno priamo z `QMenu`**; **widget zachytený pred `exec()`** | spúšťať cez `QTimer.singleShot(0, …)`; po `exec()` hľadať widget znova podľa id – prestavba ho mohla zmazať |
| **Ten istý widget vzniká dvoma cestami** (`set_messages` vs `begin_turn`) | signál pripojený len v jednej ceste v druhej nefunguje (B1) |
| **`os.add_dll_directory()` pre llama-cpp-python na Windows nestačí** | knižnica volá `ctypes.CDLL(..., winmode=0)` = štandardné hľadanie DLL, ktoré adresáre z `add_dll_directory` ignoruje; závislosti (cuBLAS) musia byť v `PATH` |
| **Široký `except`** okolo kódu s preklepom | preklep sa tvári ako „normálny“ výsledok (`response.code` → každá stránka len úryvok) |
| **Predvolený argument sa viaže pri definícii** | podstrčiť funkciu v teste cez `__defaults__`, nie prepísaním atribútu modulu |
| **Offscreen má iné písmo aj štýl** | rozmery a kurzor overovať na `cocoa` / `windows`, offscreen len logiku |
| **Umelé udalosti v testoch** | `sendEvent` sa nepropaguje rodičom, `widget.event()` obchádza event filtre, `singleShot` na ne-`QObject` drží slabú referenciu, drop bez `DragEnter` sa zahodí |
| **`QTest.keyClicks` zvládne len ASCII** | na diakritike Qt spadne assertom (`qasciikey.cpp:192`) a **zhodí proces**; diakritiku vkladať cez `setPlainText` |
| **`int(QtEnum)` v PyQt6** (`QMessageBox.icon()`, `QCursor.shape()`) | `TypeError`; treba `.value` alebo `.name` |
| **`QMenu.exec()` vráti akciu len pri klávesovej voľbe** | `action.trigger()` ju nevráti, takže kód rozhodujúci podľa návratovej hodnoty (menu ⋯) nič neurobí; v teste `Key_Down` + `Key_Return` |
| **`QDesktopServices.setUrlHandler` s lambdou** | prijímateľ sa zahodí a adresa sa naozaj otvorí v prehliadači; musí to byť živý `QObject` so slotom |
| **`QDropEvent` chce `QPointF`** | `QDragEnterEvent` prijme aj `QPoint`, `QDropEvent` nie |
| **`offscreen` pokazí PDF z `QPdfWriter`** | bez natívneho font enginu sa text vysádza ako krivky, PDF nemá fonty a `pypdf` z neho nevytiahne nič |

### 8.3 Test aplikácie pred vydaním – postup pre oba OS

Prvý beh na Macu 2026-11-09, výsledky v **`APPTEST.md`** (sekcia MAC), opravy po ňom tamže. Na PC rovnaký postup, výsledky do sekcie WINDOWS. **Testovacie skripty sú len v scratchpade Macu** – na PC ich treba napísať znova podľa tejto sekcie (techniky nižšie).

**Zásady:**
- **Skutočná appka v živom okne** (`cocoa` / `windows`): štart cez `ui.application.Application`, ovládanie skutočnými widgetmi (`QTest.mouseClick`, klávesy, menu). Priame volanie controllera len tam, kde UI cestu nemá.
- **Každá fáza = nový proces.** Prázdny testovací domov (`FUKAI_HOME`), ostrý domov len P0.
- **Výsledky do súboru, nie na konzolu** (stlmenie fd pri načítaní modelu, §7). Windows: `PYTHONIOENCODING=utf-8` (cp1250 + `print("▍")` v slote = pád).
- **Test nesmie pustiť výnimku zo slotu**; kroky spúšťať až po zobrazení okna.
- Pri teste opravy najprv zopakovať chybu na pôvodnom kóde.

**Parametre (rovnaké na oboch OS):**
- Modely: Qwen 2.5 1.5B Instruct Q4_0 (rýchle ťahy), Gemma 3 4B it Q4_K_M (kvalita, web, citácie), na PC aj Mistral 7B Q4_K_M; `mmproj-…gguf` a textový `nie_model.gguf` na odmietnutie.
- Prílohy (vyrobiť skriptom): `poznamky.txt` (kódové meno ZELENÝ JAVOR), `readme.md` (heslo MODRÁ SOVA), `ceny.csv`, `config.json`, `skript.py`, `sklad.xlsx` (openpyxl), `zapisnica.docx` (python-docx, maskot BAČA S OVEČKOU), `zmluva.pdf` (2 strany, nájomné 640 eur, ~5 400 znakov), `velky.pdf` (300 strán), `obrazok.png`, `binarny.txt`, `prazdny.txt`, `dlhy.txt`. PDF cez `QPdfWriter` + `QTextDocument.print`.
- Otázky s webom: „Kto je dekanom Fakulty elektrotechniky a informačných technológií UNIZA?“ (Qwen), „Kto je rektorom Žilinskej univerzity v Žiline?“ (Gemma).
- Merania: čas do okna, načítanie modelu, prvý token, tok/s, RSS, odozva UI (50 ms `QTimer`, najdlhšia medzera), časy ukončenia.

**Fázy:**

| Fáza | Kroky | Očakávané |
|---|---|---|
| P0 | ostrý domov: štart, kroky splashu, zatvorenie | `%LOCALAPPDATA%\FUKAI` / `~/Library/Application Support/FUKAI`, kód 0, bez `-wal`; vznikne `fukai.log` s hlavičkou behu |
| P1 | prázdny domov: prvé spustenie → import Qwen → duplikát → `mmproj` a `nie_model.gguf` → import Gemmy a ✕ v toaste → Gemma do `models/` a sken pri otvorení Nastavení → info o modeli → Otvoriť priečinok → menu modelov → odpoveď s monitorom → markdown → Stop / skrátená / prepnutie chatu → menu ⋯ (premenovanie s diakritikou a emoji, **mazanie iného chatu počas odpovede**) → Vlastnosti (`n_ctx` 2048 + Použiť → reload; seed; system prompt; draft) → `n_ctx=512` a 5 ťahov (`dropped`) + príliš dlhá otázka → prílohy (8 formátov, náhľad, chybné súbory, veľké PDF, len príloha) → web (zapnúť, hľadanie, klik na [1]) → Gemma s webom → tmavá téma → zmazanie modelu → zatvorenie počas odpovede | ako MAC v `APPTEST.md` |
| P1+ | **overenie opráv 2026-11-11:** A1 9 príloh (posuvník, 2 riadky, poradie po Stope); A2 chat s kódom, tabuľkou a 8 čipmi, okno 1400 → 1000 → najmenšie a späť; B1 klik na čip práve odoslanej otázky; B3 stav „Spracúvam zdroje/prílohy…“; B4 8 príloh vrátane `zmluva.pdf` pri `n_ctx` 4096 (odíde, orezaná len zmluva) a samotné `velky.pdf`; A3 výnimka v slote hlavného vlákna, v `QThread` a v `threading.Thread` (testovacím kódom) → toast, appka beží, 20 výnimok = 1 toast; A4 obsah `fukai.log` (toasty s `detail`, súhrn odpovede, **bez textov správ**) | ako „Opravy po teste“ v `APPTEST.md` |
| P2 | reštart nad P1: integrita, zachované nastavenia a chaty, história webu a príloh, chat bez modelu; 12 ťahov (RSS, tok/s); zatvorenie počas importu | rast pamäte < 100 MB, bez `.part` |
| P3 | zatvorenie počas hľadania na webe | kód 0, do ~6 s |
| P4 + P5 | tvrdý pád počas odpovede (`SIGKILL` / `taskkill /F /PID`), potom štart | integrita OK, žiadna otázka bez odpovede, rozpísaný prvý ťah nevytvorí chat |
| P6 | poškodený `settings.json` | prepísaný predvolenými + varovanie |
| P7 | (a) `models_dir` pod súborom, (b) `fukai.db` = nezmysel, (c) `fukai.db` s prepísanými stránkami v strede | (a) predvolený priečinok + varovanie; (b)(c) fatálny dialóg „Databáza chatov je poškodená.“ s cestou, kód 1; po zatvorení sa súbor dá premenovať a ďalší štart vytvorí novú databázu |
| P8 | dve inštancie naraz, obe odošlú správu | obe zapíšu, integrita OK |
| P9 | Shift+Enter, rast poľa po 200 px, Enter, fokus, drag & drop, najmenšie okno, zúženie okna | text sa prezalomí, nič sa neoreže |

**Navyše na Windows:** ikona na paneli úloh, `backend=cuda` a VRAM v monitore (NVML), Gemma a Mistral na GPU (VRAM spolu), **zmazanie práve načítaného modelu** (mmap), **plná VRAM** (veľký `n_ctx` alebo veľký model → varovanie / `InsufficientMemoryError`, appka žije), natívny dialóg `#32770`, kurzor v menu cez `GetCursorInfo`, `fukai-crash.log` vznikne, web (ddgs/primp na Windows, Wikipédia s textom, otvorenie prehliadača).

**Techniky a pasce testovacích skriptov:**
- macOS po páde procesu pri ďalšom štarte čaká na dialóg „obnoviť okná?“ → testy s `-ApplePersistenceIgnoreState YES`.
- Zatvárač modálneho okna musí mať termín a patriť jednému kroku; naplánovať ho **pred** akciou, ktorá dialóg otvorí (`exec()` blokuje). `QMessageBox` na Macu nie je natívny (`activeModalWidget()`); natívny dialóg Windows sa zatvára z obyčajného vlákna cez Win32.
- Odkazy a „Otvoriť priečinok“ cez `QDesktopServices.setUrlHandler` – adresa sa zachytí, okno sa neotvorí.
- Malý model niekedy odmietne úlohu alebo odpovie kódom → **Stop klikať hneď po prvom tokene** (`controller._turn.parts`), nie po pevnom čase.
- Falošné hľadanie: `ui.workers.WebWorker.__init__.__defaults__ = (fake_gather,)` pred vytvorením appky.
- `findChildren` vráti aj widgety čakajúce na `deleteLater` – filtrovať `isVisible()`.
- Model do testovacieho domova stačí ako symlink v `models/` (sken ho zaregistruje); na Windows hard link alebo kópia.

### 8.4 Otvorené body

- **Windows je overený** (test 2026-11-11, `APPTEST.md` → WINDOWS, 445 kontrol bez chyby appky): mazanie chatu počas odpovede, opravy A1–A4 a B1–B4, kúsky 7–13, plná VRAM, mmap, natívne dialógy, NVML. Neoverené zostáva len to, čo automat nevie (výber súboru v natívnom dialógu, uspanie počas generovania, odpojenie siete, vizuál tmavej témy).
- **Krok 14 (§10):** prieskum na PC 1 ✅ (2026-11-12); úprava `PATH` v appke ✅; VC++ runtime pribaliť ✅ (rozhodnuté); vlastný Metal wheel ✅; manifest a zámky ✅; `hw.json` minimá (macOS 14, CUDA 7.5) ✅; vydania wheelov ✅; Mac spúšťač a `Info.plist` ✅; `provision.sh` + `backend_test.py` ✅; `build_pkg.sh` + `welcome.html` overené skutočnou inštaláciou (čaká na prepis); zostáva README s návodom (Gatekeeper, odinštalovanie), C# inštalačka a spúšťač, CUDA wheel na T1200 (sm_75).
- **Pred vydaním v1.0 (návrh 2026-11-13, rozhodne autor):** skryť know-how (`ALMANAC.md`, `SESSIONS.md`, `APPTEST.md`, `CLAUDE.md`, `archiv/`) z verejného repa. Zmazanie z `main` nestačí – sú v histórii (repo verejné od 2026-11-13). Návrh: súkromné repo (napr. `FUKAI-dev`) naklonované do priečinka v `.gitignore`, `CLAUDE.md` naň odkazuje (Mac a PC si pamäť zdieľajú ďalej cez git), verejné repo raz `git filter-repo` + `push --force` – zároveň vymeniť e-mail autora v commitoch. Pozor: tagy vydaní wheelov `llama-0.3.36-*` presunúť na nové commity, na PC nový klon; kto už klonoval, kópiu má, GitHub drží staré commity cez priame odkazy do vyčistenia podporou. Poradie: commit `.pkg` → C# inštalačka → README → skrytie know-how → release `v1.0` (Mac + Windows naraz, `releases/latest`, SHA-256 v poznámkach; inštalačky nie sú v gite, `/dist/out/`).
- **Neskôr (C1–C6 v `APPTEST.md`):** jedna inštancia appky, prázdny `.txt`, zápis opraveného `models_dir`, tabulátory z `pypdf`, nápoveda composera v úzkom okne, odporúčanie modelov.
- **Neskôr (W2–W5 z windowsového testu):** seed je reprodukovateľný až od druhej rovnakej požiadavky (vlastnosť llama-cpp-python, nie chyba); `kv_cache_mb()` nepočíta so sliding-window attention a pri Gemme 3 nadsadí odhad (17 GB proti ~1 GB skutočne); `fukai-crash.log` sa len dopĺňa a appka ho drží otvorený; self-test `core.gguf` na Windows padá na kontrole adresára (`PermissionError` namiesto `IsADirectoryError`) – v appke je tá cesta zavretá cez `is_file()`.
- **Upratanie kódu (2026-11-13, autor):** self-testy z modulov zmazané (diagnostiku nahradí `backend_test.py` v inštalačke), komentáre „čo“ odstránené, komentáre „prečo“ ponechané, hlavička `# --- ./<priečinok>/<súbor>.py ---`. AST porovnanie proti commitu: kód bez zmeny (okrem nepoužívaného importu `field` v `core/errors.py`), `main.py` má spúšťací `__main__`. `import pynvml` vo VS Code na Macu podčiarknutý – balík je len pre Windows (`sys_platform == "win32"`), na Macu sa riadok nevykoná.
- **Drobnosti:** počet tokenov systémového promptu je odhad `dĺžka / 4`; kontextové menu textu je po anglicky; výber textu myšou cez viac častí odpovede nejde; tabuľka vnorená v odrážke nedostane rám; citácie `[n]` nie sú klikateľné; zoznam chatov bez klávesovej navigácie a neroluje sa na aktívny chat; monitor sa nepamätá; generátor ikon nie je v repe; Qwen 3 `<think>` a Llama 3 `strftime_now` neoverené.

## 9. Poznámky k prostrediu

PC 1: shell **PowerShell 5.1**, Claude Code má aj Git Bash.

- PowerShell 5.1 nepozná `&&` → `a; if ($?) { b }`.
- **`set X=y` je syntax cmd.exe, v PowerShelli ticho nič nespraví** (vyrobí premennú s menom `X=y`) → `$env:X = "y"`. Takto vznikol CPU-only build llama-cpp-python bez chyby – po builde zo zdrojákov vždy skontrolovať `llama_cpp/lib/`.
- Git Bash prerába argumenty začínajúce `/` na cesty → commit správy nezačínať `/`. Viacriadkové heredoc v Git Bash sa lámu na slovenských znakoch → súbory zapisovať nástrojom, nie `cat <<EOF`.
- **`py` je launcher, nie `.venv`** – globálny Python 3.14.2. Isté je `.venv\Scripts\python.exe -m pip …`.
- **Po `git pull`, ktorý mení zámky alebo requirements, prestavať prostredie zo zámku (§3).** Venv na PC 1 zostal na `ddgs` 9.7.1 z času pred krokom 13 a web padal na `Invalid impersonate` (W1 v `APPTEST.md`) – prostredie, nie appka.
- **Na Windows ovládač (WDDM) preteká VRAM do RAM.** Priveľký model alebo kontext sa načíta a odpovie (len pomalšie), `InsufficientMemoryError` z VRAM teda na Windows nečakať; varovanie pred načítaním je jediná obrana. Na Metale to padá.
- Git identita je nastavená len lokálne v repe; na novom stroji nastaviť, inak commit zlyhá a „Everything up-to-date“ pri pushi klame. `.gitattributes` `* text=auto eol=lf`. `.DS_Store` je v `.gitignore`. ALMANAC commitovať priebežne.
- Skripty v scratchpade nepomenúvať podľa modulov stdlib (`inspect.py`) a nespúšťať z adresára s kópiou `ui/` (Python importuje najprv odtiaľ).

## 10. Distribúcia – rozhodnuté 2026-11-12

**Inštalačka zostaví prostredie na cieľovom stroji** (rozhodnutie autora 2026-11-12). Nebalí sa zmrazená appka (PyInstaller), ale zdrojáky FUKAI + nástroj **`uv`** (Astral, MIT/Apache, jeden binárny súbor). Inštalačka zistí hardvér, `uv` stiahne Python 3.12.10, vytvorí vlastné prostredie appky a nainštaluje presne pinnuté balíky – **backend podľa reálneho systému**. Dôvody: CUDA bez Toolkitu cez pip balíky NVIDIA, malá inštalačka, rovnaký mechanizmus na oboch OS, prostredie sa dá opraviť alebo zmeniť (napr. CPU → CUDA). Cena: **inštalácia potrebuje internet** (offline nie vo v1) a závisí od PyPI a indexu `abetlen`. Zamietnuté: PyInstaller `--onedir` – dve varianty na OS, cuBLAS (~500 MB) pribalený alebo sťahovaný zvlášť, ladenie hookov PyQt6 a llama_cpp. Zdrojáky sa inštalujú s rovnakou štruktúrou, takže cesty k `assets/` a `vars/` (`Path(__file__)…`) platia bez zmeny.

**Postup inštalácie** (diagram autora `mermaid-diagram.png` z 2026-11-12, upravený): detekcia CPU/GPU/RAM → NVIDIA? → ovládač a compute capability → **CUDA** (wheel `cu130` + `nvidia-cublas` + `nvidia-cuda-runtime`) alebo **CPU** (wheel `cpu`) → Python a prostredie → spoločné balíky (`requirements.txt`) → súbory appky → **test backendu** (`probe_engine()` v novom prostredí) → zástupca, dokončenie. Úpravy oproti diagramu:
- „Nekompatibilná CUDA“ sú **dva prípady**: chýbajúce runtime knižnice (cuBLAS) inštalačka doinštaluje – pri tomto spôsobe vždy, na Toolkit sa nespolieha; **starý ovládač alebo stará karta** sa opraviť nedá → upozornenie a CPU backend (prípadne rada aktualizovať ovládač).
- **Test backendu zlyhá** → nainštalovať CPU wheel, otestovať znova a povedať to používateľovi.
- **Bez internetu / zlyhané sťahovanie** → jasná chyba a možnosť zopakovať.
- RAM backend nemení, len pri malej pamäti upozorní a odporučí menšie modely.

**Windows** – vlastná inštalačka v C# (rozhodnutie autora 2026-11-09), **pre používateľa bez admina** do `%LOCALAPPDATA%\Programs\FUKAI` (rozhodnutie autora 2026-11-12; bez UAC, dáta zostávajú v `%LOCALAPPDATA%\FUKAI`). Spúšťač `FUKAI.exe` v C# (ikona, názov v Správcovi úloh) spustí `pythonw.exe main.py` z prostredia appky.
- **CUDA bez Toolkitu cez PyPI** (overené 2026-11-12, že balíky existujú pre `win_amd64` v rade 13.0, zhodnom s wheelom `cu130`): `nvidia-cublas==13.0.2.14` (383 MB, obsahuje `cublas64_13.dll` a `cublasLt64_13.dll`) a `nvidia-cuda-runtime==13.0.96` (3 MB). Balíky `*-cu13` sú len zastarané aliasy. Ich adresár s DLL dá appka do `PATH` (nižšie, prieskum).
- Pôvodné fakty: `nvcuda.dll` dodáva ovládač; CUDA build sa na stroji bez NVIDIA nemusí načítať vôbec – preto výber wheelu podľa detekcie, nie prepínač. Vlastný build viacerých architektúr (`-DCMAKE_CUDA_ARCHITECTURES=75;86;89;120`, MSVC 14.44 + nvcc 13.0 na PC 1, z „x64 Native Tools Command Prompt“) zostáva ako záloha.

**macOS** – **`.pkg`** (rozhodnutie autora 2026-11-12) s `postinstall` skriptom, ktorý robí to isté cez `uv`; `.dmg` zamietnutý (nevie spustiť skript, prostredie by vzniklo až pri prvom spustení). Appka ako `.app` bundle so spúšťačom a `Info.plist`. **Inštaluje sa do `/Applications/FUKAI.app` pre všetkých používateľov** (rozhodnutie autora 2026-11-13, heslo správcu pri inštalácii je pri `.pkg` bežné); Python, prostredie a zdrojáky sú vnútri bundlu (`Contents/Resources/{python,env,app}`), dáta zostávajú v `~/Library/Application Support/FUKAI`. **`CFBundleIdentifier` = `sk.vavro.fukai`** (rozhodnutie autora, po vydaní nemeniť).
- **Spúšťač v C** (`dist/mac_app_installer/launcher.c`, rozhodnutie autora 2026-11-13; kompiluje `clang` z Xcode CLT, celý Xcode ani projekt netreba): Python **nespúšťa ako ďalší proces, ale načíta `libpython3.12.dylib` do seba** (`PyConfig`: `program_name` = `env/bin/python3` → Python nájde `pyvenv.cfg` a `site-packages` prostredia; `run_filename` = `main.py`; `parse_argv = 0` – argumenty patria appke). Proces zostáva `Contents/MacOS/FUKAI`, preto **menu aj Dock ukazujú „FUKAI“ a ikonu** (overené autorom 2026-11-13; pri `exec python` by to bol „Python“). Cesty odvodzuje z `_NSGetExecutablePath` + `realpath`. Chýba prostredie alebo `main.py` → natívne okno `CFUserNotificationDisplayAlert` „FUKAI nie je nainštalovaný úplne. Spusti inštaláciu FUKAI znova.“ (bez Qt aj Pythonu; overené). Python z `uv` má `lib/libpython3.12.dylib` aj `include/python3.12`.
- **Pasce pri skladaní bundlu:** `uv` zapisuje **absolútne cesty** (install name `libpython3.12.dylib`, symlink `cpython-3.12-…`) → spúšťač po kompilácii `install_name_tool -change <abs> @rpath/libpython3.12.dylib -add_rpath @executable_path/../Resources/python/cpython-3.12.10-macos-aarch64-none/lib`, a Python s prostredím **vznikajú až v cieľovom `/Applications/FUKAI.app`** (`postinstall`). Po `install_name_tool` treba znova podpísať: najprv `xattr -cr` (inak `codesign` hlási „resource fork… detritus not allowed“), potom `codesign -s - -f` (ad-hoc, na Apple Silicon povinné). Bundle má ~477 MB. **Prepis autora** (`launcher.c`, `Info.plist`, 2026-11-13) mal 7 preklepov – 3 by zastavili kompiláciu, ale tiché boli: `real[PASS_MAX]` (`PASS_MAX` v macOS existuje = 128, `realpath` zapisuje až 1024 B → pretečenie) a `LSMinimuumSystemVersion` (neznámy kľúč macOS ignoruje → appka by sa spustila aj na macOS 13). Po oprave kompilácia bez varovaní, identita procesu a natívne okno overené znova. VS Code: `.vscode/c_cpp_properties.json` (len lokálne) ukazuje IntelliSense hlavičky Pythonu z python.org a frameworky z Xcode CLT – červené `#include` nie je chýbajúca knižnica.
- **`provision.sh` = `postinstall` `.pkg`** (`dist/mac_app_installer/provision.sh`, návrh schválený autorom 2026-11-13; spoločný test backendu `dist/backend_test.py`). Payload `.pkg` = bundle bez Pythonu a prostredia + `Resources/installer/{uv, manifest.json, locks/mac-metal.txt, backend_test.py}`; Installer volá skript s cieľom `$2` = `/Applications`. Postup: kontrola `hw.optional.arm64` a macOS ≥ `minimum.macos_version` → `curl` wheelu + SHA-256 z manifestu → zmazať starý `python/` a `env/` → `uv python install --no-bin` do `Resources/python` → `uv venv` → zámok `--require-hashes` → wheel `--no-deps` (oboje `--compile-bytecode`, `UV_LINK_MODE=copy`, `UV_NO_CONFIG=1`, cache v `/tmp`) → `compileall` zdrojákov (bundle patrí rootovi, appka si `.pyc` nezapíše) → `backend_test.py` musí vrátiť `backend = metal` → `chown root:wheel`, `chmod go-w` → zmazať `installer/`. Manifest číta `plutil -extract` (JSON vie, `jq` na macOS 14 nie je). Log: výstup Installera (`/var/log/install.log`) + `/Library/Logs/FUKAI-install.log`. **Pri chybe zmaže `env/`** → spúšťač ukáže „nie je nainštalovaný úplne“. Overené v scratchpade (bez roota): čistá inštalácia 82 s (bundle 510 MB: Python 49 + prostredie 453), appka z bundlu iba na čítanie beží (Metal, menu FUKAI, nezapíše do bundlu nič), zlý hash a nedostupná adresa → exit 1 so správou a bez `env/`, preinštalovanie cez chybnú aj hotovú inštaláciu 73 s (staré prostredie nahradené). Štart appky ~10 s, z toho ~6 s je preklad Metal knižníc pri `probe_engine` (`ggml_metal_library_compile_all`).
- **`build_pkg.sh`** (`dist/mac_app_installer/`, 2026-11-13) → `dist/out/FUKAI-<verzia>.pkg` (~20 MB, `dist/out/` v `.gitignore`), zostavenie ~17 s. Kontroly: `app_version` z manifestu = `APP_VERSION` v `core/constants.py` = `CFBundleShortVersionString` v `Info.plist`, `LSMinimumSystemVersion` = `minimum.macos_version` (inak sa nestavia – verzia je na troch miestach, ale nerozíde sa). `uv` sa sťahuje z manifestu a overí hashom (nie `dist/tools/uv`); spúšťač sa kompiluje proti Pythonu z `uv` (`-Werror`) a **podpisuje sa mimo bundlu** (`codesign -s - -f -i sk.vavro.fukai`) – vnútri bundlu by `codesign` vyrobil `_CodeSignature` a zapečatil aj `Resources/`, ktorý `provision.sh` mení (`codesign -v` nainštalovaného bundlu preto hlási chýbajúce resources – očakávané, jadro pri štarte kontroluje len kód). Zdrojáky = `git ls-files` (bez `__pycache__`, `devdata`); do `Resources/` aj `LICENSE` a `THIRD_PARTY_LICENSES.md`. **Pred `pkgbuild` `xattr -cr` na bundle** – súbory v repe nesú atribúty macOS (`com.apple.provenance`, `com.apple.macl`, `assets/logo.png` dokonca `com.apple.quarantine`), `pkgbuild` ich zabalí ako `._*` (61 položiek navyše) a Installer ich obnoví; kópia repa cez `rsync -a` ich stratí, preto ich test v scratchpade neodhalil. **`welcome.html` (štýl autora, rovnaký ponesie C# inštalačka) musí mať tmavý variant** – Installer pozadie stránky nekreslí, pevná tmavá farba textu je v tmavom vzhľade nečitateľná; farby ako premenné v `:root` + `@media (prefers-color-scheme: dark)` (tmavé hodnoty z tmavej témy appky: text `#E4F3FB`, akcent `#6EC6E5`, kód `#CDEFFB`). Overené vykreslením cez WKWebView v oboch vzhľadoch (`screencapture` okna Installera bez povolenia nahrávania obrazovky nejde). `pkgbuild` s komponentom **`BundleIsRelocatable = NO`** (inak Installer „aktualizuje“ iný `FUKAI.app`, ktorý LaunchServices pozná – napr. skúšobný bundle – namiesto `/Applications`), `productbuild` s `distribution.xml` (`hostArchitectures=arm64`, len systémový disk, `allowed-os-versions` min 14.0, úvodná stránka `welcome.html`: internet, ~160 MB sťahovanie – spočítané z PyPI podľa zámku, ~510 MB na disku, modely nie sú súčasťou, kde sú dáta a log). **Overené skutočnou inštaláciou 2026-11-13** (Installer, heslo správcu): čistá inštalácia 89 s, preinštalovanie cez existujúcu 3 min 19 s (rozdiel je rýchlosť PyPI), bundle 510 MB celý `root:wheel`, `pkgutil` záznam `sk.vavro.fukai`, appka beží z `/Applications` s dátami v `~/Library/Application Support/FUKAI` (autor). **Odinštalovanie:** `sudo rm -rf /Applications/FUKAI.app && sudo pkgutil --forget sk.vavro.fukai` – dáta, `~/Library/Preferences/sk.vavro.fukai.plist` (píše macOS – stav dialógu na otvorenie súboru) a `/Library/Logs/FUKAI-install.log` zostávajú zámerne. `sudo` cez `!` v Claude Code nefunguje (nemá terminál na heslo) → `osascript -e 'do shell script "…" with administrator privileges'`. Python z `uv` nemá `.pyc` pre ~1 000 modulov štandardnej knižnice a do bundlu (root) si ich nezapíše → preklad v pamäti pri každom štarte, meraných ~40 ms → nepredkompilúva sa.
- **Obnova okien po páde sa v bundli nezopakovala** (2× `kill -9` → štart prešiel splashom, `Saved Application State` pre bundle nevzniká) → oprava sa nepridáva; dialóg poznáme len pri behu cez holý `python`. **Oficiálny Metal wheel 0.3.36 je poškodený** (znova overené 2026-11-12) a používateľ nemá Xcode na build → **vlastný Metal wheel** postavený raz na M2. Len Apple Silicon, **minimálne macOS 14** (rozhodnutie autora 2026-11-12). Build v `.venv` sa nedá len zabaliť: má `minos 26.0` (štítok `macosx_26_0_arm64`) a natívne inštrukcie M2 (`MATMUL_INT8 = 1`, na M1 by spadol) → stavať s `MACOSX_DEPLOYMENT_TARGET=14.0` a `GGML_NATIVE=OFF`. **Postavený 2026-11-12** do `dist/backend_whls/` (mimo gitu): `MACOSX_DEPLOYMENT_TARGET=14.0 CMAKE_ARGS="-DGGML_METAL=on -DGGML_NATIVE=OFF" .venv/bin/python -m pip wheel llama-cpp-python==0.3.36 --no-deps --no-binary llama-cpp-python --no-cache-dir -w dist/backend_whls -v` (~2 min) → `llama_cpp_python-0.3.36-py3-none-macosx_14_0_arm64.whl`, 24,2 MB, **SHA-256 `9b80c0976fe3b54db3619c37bd6094dd3129a470100db97cfa182d193fc56509`** (oficiálny – každá stavba dá iný hash, nestavať zbytočne znova). Všetkých 21 `.dylib` `minos 14.0`, závislosti len systémové frameworky, `DOTPROD` áno, `MATMUL_INT8`/`SME` nie, licencia vo wheeli. Meranie proti natívnemu buildu (Qwen 1,5B, prompt 2 403 tok): Metal 363 vs 381 tok/s prompt, 24,5 vs 25,3 generovanie; CPU rovnako (51 / 19,0 vs 16,7) → základ M1 nič podstatné nestojí. Na skutočnom M1 a macOS 14 neoverené. **`uv` 0.13.7 pre Mac:** `uv-aarch64-apple-darwin.tar.gz`, SHA-256 `81b811b57e4624df7ed3aac148e0359100d9962f3d9dce00aec533dc2e086731`; čisté prostredie z wheelu bez kompilácie za 104 s (Python 47 MB + prostredie 423 MB), `backend=metal`; **po zmazaní cache celá appka z neho beží** (splash „Pripravené · METAL“, Qwen 30,5 tok/s proti 27,2 z `.venv` v rovnakom čase – bez regresie). Nepodpísaný `.pkg` stiahnutý z internetu macOS zablokuje (Gatekeeper); podpis a notarizácia vyžadujú platený Apple Developer účet → vo v1 návod v README. Od macOS 15 už „pravý klik → Otvoriť“ blokovanie neobchádza – treba Systémové nastavenia → Súkromie a bezpečnosť → „Aj tak otvoriť“ (overiť na stiahnutom `.pkg` pri vydaní; lokálne postavený `.pkg` nemá karanténu, Installer len zapíše „nie je podpísaný“).

**Prieskum na PC 1 (2026-11-12) – spôsob je overený**, výsledky v `semestralka/TODO-vysledky-PC.md` na OneDrive. Prostredie zostavené cez `uv` (Python 3.12.10, wheel `cu130`, `nvidia-cublas` 13.0.2.14, `nvidia-cuda-runtime` 13.0.96) beží **bez Toolkitu**: Gemma 35/35 vrstiev na GPU, 114,7 tok/s; celá appka `backend=cuda`, 95 tok/s.
- **DLL od NVIDIA sú v jednom adresári** `<env>\Lib\site-packages\nvidia\cu13\bin\x86_64\` (`cublas64_13`, `cublasLt64_13`, `cudart64_13`). **Appka ho pred importom `llama_cpp` pridá na začiatok `PATH`** – hotové 2026-11-12: `_add_nvidia_dlls()` v `core/llm_engine.py` (len Windows, cesta zo `sysconfig.get_paths()["purelib"]` + `NVIDIA_DLL_SUBDIR`, len ak priečinok existuje, bez duplicity – `_import_llama()` beží pri štarte aj pri každom načítaní, riadok do logu) – `os.add_dll_directory()` nefunguje (§8.2). Druhá overená možnosť: predtiahnuť DLL cez `ctypes.CDLL` celou cestou.
- **`uv` 0.13.7** (`uv-x86_64-pc-windows-msvc.zip`, SHA-256 `0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021`, stačí `uv.exe` 30 MB). Premenné: `UV_PYTHON_INSTALL_DIR=<inštalácia>\python`, `UV_CACHE_DIR=<inštalácia>\cache`, **`UV_PYTHON_PREFERENCE=only-managed`** (inak vezme globálny Python). `uv python install --no-bin 3.12.10` (bez `--no-bin` vyrobí shim v `%USERPROFILE%\.local\bin`), `uv pip install --link-mode copy` → **cache sa po inštalácii dá zmazať**. **Prostredie nie je presunuteľné** (`pyvenv.cfg` má absolútnu cestu k Pythonu) – stavať rovno v cieľovom priečinku.
- **Rozhodovanie inštalačky** (`nvidia-smi --query-gpu=name,driver_version,compute_cap,memory.total --format=csv,noheader`; `nvidia-smi.exe` dodáva ovládač do `System32`): `compute_cap ≥ 7.5` a ovládač `≥ 580` → CUDA; nižšia capability → CPU + „karta je staršia“; starší ovládač → CPU + „aktualizuj ovládač a zopakuj“; NVIDIA vo `Win32_VideoController`, ale `nvidia-smi` chýba → CPU + „ovládač chýba / je poškodený“ (verzia z WMI: posledných 5 číslic `32.0.16.2124` → 621.24); žiadna NVIDIA → CPU; **CPU bez AVX2 → inštalácia sa nedá, skončiť so správou** (C#: `Avx2.IsSupported`).
- **Visual C++ Redistributable** (`msvcp140`, `vcruntime140`, `vcruntime140_1`, `vcomp140`) je jediná systémová závislosť mimo ovládača. Bez admina sa nainštalovať nedá → **pribalí ich Windows inštalačka k appke** (app-local, Microsoft to povoľuje; rozhodnutie autora 2026-11-12). Zamietnuté: vyžadovať Redistributable (potrebuje admina, proti inštalácii bez admina). Cena: pri novej verzii runtime ich treba v inštalačke aktualizovať ručne. Kam presne ich dať, aby ich našiel `llama_cpp` (vedľa `pythonw.exe` / v `llama_cpp\lib` / v `PATH`), sa overí pri stavbe inštalačky.
- **Test backendu** = `backend_test.py` (návrh v súbore výsledkov): v novom prostredí nastaví `PATH`, zavolá `probe_engine()` + `detect()`, vypíše jeden riadok JSON (`ok`, `backend`, `llama_cpp`, `gpu_offload`, `gpu`, `vram_mb`, `error`), exit 0/1. Exit 1 po CUDA → doinštalovať CPU wheel a test zopakovať; `backend == "cpu"` pri NVIDIA → nechať CPU a upozorniť. Spúšťať s `PYTHONIOENCODING=utf-8` a priečinkom zdrojákov v `PYTHONPATH`.
- CUDA wheel na stroji bez použiteľnej GPU sám prejde na CPU (`CUDA_VISIBLE_DEVICES=-1`: 73 tok/s, rovnako ako CPU wheel); výber backendu podľa hardvéru má zmysel aj tak (516 MB balíkov NVIDIA by boli zbytočné).
- **Veľkosti a časy (prázdna cache, 1 Gbit):** CUDA ≈ 1 243 MB na disku (Python 58 + prostredie 1 185), stiahne ~718 MiB za 46 s; CPU ≈ 413 MB, ~130 MiB za 12 s.
- **Otvorené:** notebook s T1200 (`sm_75` má cubin, malo by ísť bez warm-upu), CUDA wheel na stroji úplne bez ovládača NVIDIA, naplnenie JIT cache už pri inštalácii (potrebuje model – zatiaľ nie).

**Zdroj wheelov llama-cpp-python** (rozhodnutie autora 2026-11-12): všetky tri si vystavujeme sami vo **vydaniach repa FUKAI, ktoré je od 2026-11-13 verejné** (súbory z vydaní súkromného repa sa bez prihlásenia nestiahnu – token v inštalačke by si vytiahol ktokoľvek; zdrojáky dostane používateľ v inštalačke aj tak). Vydania `llama-0.3.36-metal`, `-cu130`, `-cpu` sú hotové (2026-11-13, nie „latest“ – to zostáva pre vydanie appky), stiahnutie bez prihlásenia overené, hashe sedia. CPU a CUDA = oficiálne súbory bez zmeny, Metal = vlastný build. Dôvod: upstream súbor sa môže pokaziť alebo zmiznúť (Metal 0.3.36) a inštalačka by prestala fungovať bez zmeny u nás. **Samostatné vydanie na backend** (`llama-0.3.36-cpu`, `-cu130`, `-metal`) – CPU a CUDA wheel majú rovnaký názov súboru a názov wheelu sa meniť nesmie. Licencia MIT (llama-cpp-python, llama.cpp) šírenie dovoľuje, licenciu pribaliť. Inštalačka wheel **sťahuje** (nepribaľuje), overí SHA-256 z manifestu a nainštaluje; Windows vyberie CPU/CUDA, Mac vždy Metal. **Balíky NVIDIA a ostatné zostávajú z PyPI** (pinnuté verzie sa tam nemenia; NVIDIA má vlastnú licenciu na šírenie). Neskôr možné: vlastný CUDA build so `sm_120` (bez warm-upu na RTX 50xx).
- **Prečo má CUDA wheel 228 MB a CPU 7,8 MB:** `ggml-cuda.dll` (115 MB) nesie hotové kernely pre 5 architektúr + PTX a tisíce variantov (kvantizácie, flash attention), strojový kód sa zle komprimuje (102 MB v zipe) a **vo wheeli je dvakrát** (`llama_cpp/lib/` aj `bin/`, artefakt scikit-build-core; za behu sa používa len `llama_cpp/lib/`). Duplikáty `site-packages/bin` a `lib` (~150 MB na disku) by inštalačka mohla po inštalácii zmazať – wheel sa neupravuje (hash); vo v1 nie. Metal wheel je malý, lebo shadery sa prekladajú až za behu.
- **Na macOS nesťahovať cez Python `urllib`:** Python z python.org nemá bez „Install Certificates.command“ certifikáty (`CERTIFICATE_VERIFY_FAILED`). Inštalačka sťahuje systémovým `curl`.

**Manifest a zámky** (hotové 2026-11-12, `dist/`): `manifest.json` = jediné miesto s verziami pre obe inštalačky – `python` (hash nie je treba, hashe Pythonu má v sebe pinnutý `uv`), `uv` (URL + SHA-256 pre Windows aj Mac; `uv` sa do inštalačky pribaľuje, údaje použije skript, ktorý ju zostavuje), `minimum` (macOS 14 `arm64`, AVX2/FMA/F16C, compute capability 7.5, ovládač 580), `backends` (`metal`/`cuda`/`cpu`: `os`, `lock`, `wheel.release` + `file` + `sha256`; `cuda` má `"fallback": "cpu"`), `releases` = `https://github.com/Vejvr0/FUKAI/releases/download` (adresa wheelu = `releases/<wheel.release>/<wheel.file>`). Wheely lokálne v `dist/backend_whls/<release>/` (mimo gitu). **Zámky** – `requirements.txt` pinuje len priame závislosti, prechodné (numpy, lxml, babel…) by sa pri každej inštalácii vyberali nanovo → `make_locks.py` (`.venv/bin/python dist/make_locks.py`, potrebuje `dist/tools/uv`) najprv overí hash všetkých wheelov proti manifestu (pri chybe sa žiadny zámok neprepíše), potom `uv pip compile --python-platform <os> --generate-hashes --no-emit-package llama-cpp-python --no-annotate --no-header` (Windows zámky vznikajú aj na Macu). Mac 37 balíkov, Win CPU 38, Win CUDA 40. **Inštalácia:** `uv pip install --require-hashes -r <lock>` → `uv pip install --no-deps <overený wheel>` → test backendu → pri zlyhaní `fallback`. Overené na Macu: zo zámku za 23 s, `pip check` OK, appka beží (Metal, 27 tok/s); pokazený hash jedného balíka → inštalácia skončí (`Hash mismatch`) a nenainštaluje nič. Zámok vybral 4 opravné verzie novšie než `.venv` z veľkého testu (click 8.5.1, dateparser 1.5.0, pyqt6-sip 13.13.1, regex 2026.11.9) → **testuje sa odteraz prostredie zo zámku**; zámok sa mení len vedome.
- **`hw.json`** (2026-11-12): minimum macOS 14 (pred tým 12 – wheel by sa na 12/13 nenačítal), mapa `cuda_arch` (pozostatok wheelov pre každú architektúru) nahradená `minimum_cuda_compute: "7.5"`; `gpu_arch()`/`required_wheel()` zrušené. `check_gpu`: karta pod 7.5 → „je staršia, než FUKAI podporuje“; NVIDIA + engine len pre CPU (inštalačka zvolila CPU, typicky starý ovládač) → „aktualizuj ovládač a preinštaluj FUKAI“. Verzie sa porovnávajú ako n-tice čísel (`_version`), neznáma hodnota = bez upozornenia, nikdy výnimka. V prepise boli dve chyby: porovnanie textu `"sm120" < 7.5` (`TypeError` pri štarte na každej podporovanej NVIDIA karte) a preklep kľúča `minimun_…` (`get_allowed_hw()` padá → vypnuté všetky kontroly pri štarte) – opravené pred commitom.

AMD (HIP/Vulkan), Linux a Intel Mac sú mimo rozsah.
