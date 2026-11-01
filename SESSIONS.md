# FUKAI – denník sessions

Chronologický záznam práce. **Rozhodnutia a stav projektu patria do `ALMANAC.md`**, nie sem – tento súbor je len história „čo sa kedy robilo a prečo“, aby sa dalo dohľadať, odkiaľ niečo prišlo. ALMANAC sa načítava do kontextu pri každom spustení, tento súbor nie.

---

## 2026-10-27 / 28 – errors, hardware, výber wheelu

**Stav na začiatku:** prázdny projekt (`main.py` s jedným `print`), `.venv` len s pipom, ALMANAC s plánom.

### Hotové

**`requirements.txt` + `requirements-llama-win-cuda.txt` + `requirements-llama-mac.txt`**
`llama-cpp-python` je zámerne mimo hlavného súboru – je jediná závislosť, ktorá je platformovo špecifická.

**`core/errors.py`** – hierarchia chýb, 21 tried.
Zvolené delenie **podľa príčiny**, nie podľa modulu. Dôvod: `except` sa v praxi píše okolo toho, *čo* sa pokazilo, nie *odkiaľ* to prišlo – a pri delení podľa modulov by UI nerozlíšilo „nepodporovaný typ súboru“ od „vyhľadávač nedostupný“.
Každá chyba nesie tri oddelené texty: `message` (pre používateľa), `hint` (čo s tým), `detail` (do logu). `hint` je keyword-only, aby sa nedali zameniť.
`Notice` + `Severity` pre nefatálne oznámenia – vďaka tomu UI vykresľuje chyby aj varovania rovnako.
Web vyhľadávanie má na žiadosť používateľa len jednu všeobecnú chybu na úrovni INFO.

**`core/hardware.py`** – 383 riadkov, detekcia + 4 kontroly. Overené na PC 1 aj MacBooku.
Postupnosť krokov: slovník → dataclass → kontroly OS → GPU → P/E jadrá.
Zásada: **detekcia nikdy nevyhodí výnimku von.** Zlyhanie sondy sa mení na `Notice` a appka beží na CPU. Prototyp v takom prípade zobrazil dialóg a zavolal `sys.exit(0)`.
Výsledky na PC 1: `n_threads=8` (z 20 jadier), `n_gpu_layers=-1`, `backend=cuda`, RTX 5060 Ti rozpoznaná ako Blackwell `sm_120`.

**`vars/hw.json` + `core/constants.py`** – pevné dáta a konštanty.
Hranica: do JSON tabuľky a zoznamy, ktoré sa môžu rozrastať; do Pythonu čísla, s ktorými sa počíta.

### Opravené chyby (a prečo stáli za zmienku)

| Chyba | Prečo bola zradná |
|---|---|
| `return ConfigError` namiesto `raise` | vráti triedu, tá je vždy truthy → chyba sa nikdy neukáže, spadne niečo iné o 20 riadkov nižšie |
| `release[0:1]` | z `"11"` urobí `"1"` |
| `data["cores"].get(...)` | `.get()` má slovník, nie číslo (vzor skopírovaný z `check_os`, kde to slovník bol) |
| `Notice.error(msg, hint)` | `hint` je keyword-only |
| `"./vars/hw.json"` | závisí od toho, odkiaľ sa appka spustí; nahradené cestou od `__file__` |
| `minimum_ram: 4` | porovnávalo sa s MB, teda 4 MB; prejmenované na `minimum_ram_gb` |
| `from errors import` | pri `python -m core.hardware` sa hľadá od korena projektu → `core.errors` |
| chýbajúci `@lru_cache` | tri checky parsovali ten istý JSON trikrát |

### Zahodené / neurobené

- **Samostatný „rozpočet pamäte“ v `hardware.py`** – zbytočný, `ram_available_mb` stačí (ALMANAC §4).
- **INFO notice „potrebuješ wheel sm120“ v `check_gpu`** – hlásila sa pri každom štarte, aj keď bolo všetko v poriadku. `check_gpu` má hlásiť problémy, nie fakty. Presunuté do samostatnej `required_wheel()`.
- **Návrh ChatGPT na vrstvy `ChatManager`/`ModelManager`/`ConversationManager`/`InferenceEngine`** – štyri triedy tam, kde treba jednu. Plochá štruktúra zo §6 zostáva.
- **Návrh ChatGPT na `backends/windows_cuda/` v repe** – stovky MB binárok v Gite.
- **Návrh ChatGPT na `_detect_backend()` podľa názvu OS** – slabšie než hotová detekcia v `hardware.py`.
- **AMD / Linux** – mimo rozsah (§1).

### Zmena závislostí

Pin `llama-cpp-python` posunutý **0.3.20 → 0.3.36** a prechod od wheelov tretej strany (`dougeeai`) na oficiálne indexy autora knižnice. Padá tým matica 4 wheelov podľa GPU architektúry aj build zo zdrojákov na macOS. Podrobne v ALMANAC §10.1.

### Problémy prostredia, ktoré zdržali

PowerShell 5.1 nepozná `&&`; Git Bash prerába argumenty začínajúce `/` na cesty (pokazilo commit správu `/core - ...`); `py` spúšťa globálny Python 3.14, nie `.venv`; heredoc v Git Bash sa láme na slovenskej diakritike. Všetko zapísané v ALMANAC §9.
Pri tom zhavarovala jedna vec: `git checkout -- ALMANAC.md` ALMANAC **vymazal**, lebo v commite `510c7a1` bol uložený ako prázdny súbor a obsah existoval len v pracovnom strome. Obnovené z kontextu, nič sa nestratilo.

### Nedoriešené do ďalšej session

1. **Nainštalovať `llama-cpp-python` 0.3.36** – na PC 1 aj na MacBooku. Zatiaľ nie je nikde.
2. **Overiť dve neznáme** o CUDA wheeli: či podporuje `sm_120` a či potrebuje CUDA Toolkit (`cublas64_13.dll`, 49 MB + `cublasLt64_13.dll`, 458 MB). Test: `gemma-3-4b-it-Q4_K_M.gguf` s `n_gpu_layers=-1`, kontrola vo `nvidia-smi`.
3. **`core/settings.py`** – `LoadParams` vs `SamplingParams`. Rozdelenie podľa toho, či zmena vyžaduje reload modelu.
4. **`core/llm_engine.py`** – trieda (má stav: načítaný model), streaming ako generátor, Stop ako `threading.Event`. **Bez importu PyQt6** – QThread príde až v `ui/workers.py`, aby sa engine dal testovať konzolou bez `QApplication`.
5. **Variant inštalačky** – nerozhodnuté, tri možnosti v ALMANAC §10.
6. Drobnosť: konštanty `_RELATION_PROCESSOR_CORE` a `_ERROR_INSUFFICIENT_BUFFER` majú podtržník, ale importujú sa medzi modulmi – podtržník znamená „privátne“, takže klame.

---

## 2026-10-28 – CUDA wheel rozbehaný, settings + llm_engine

**Stav na začiatku:** `llama-cpp-python` 0.3.36 nainštalovaný buildom zo zdrojákov, ale **model bežal na CPU**. V `core/` bol rozbehaný `llama_engine.py` – jednorazový skript bez triedy.

### Prečo GPU nefungovala

Build bol spustený takto:

```
set CMAKE_ARGS=-DGGML_CUDA=on
set FORCE_CMAKE=1
py -m pip install llama-cpp-python==0.3.36 --upgrade --force-reinstall --no-cache-dir
```

`set` je syntax cmd.exe. V PowerShelli je to alias pre `Set-Variable`, takže to vyrobilo PowerShell premennú s názvom `CMAKE_ARGS=-DGGML_CUDA=on` a hodnotou `$null`. **Bez jediného chybového hlásenia.** cmake o CUDA nedozvedel a postavil CPU variantu – `pip install` prešiel, appka fungovala, len bez GPU.

Diagnostika, ktorá to ukázala za 10 sekúnd: v `.venv/Lib/site-packages/llama_cpp/lib/` bola len `ggml-cpu.dll`, `ggml-cuda.dll` chýbala. Pozor na falošnú stopu – `include/ggml-cuda.h` tam bol, ale header sa pribalí vždy, aj v CPU builde.

Zapísané do ALMANAC §9 spolu s druhou pascou, ktorá tam tiež je: `py` bez aktivovaného venv inštaluje do globálneho Pythonu 3.14.

### Riešenie: oficiálny predkompilovaný wheel

Build sa neopravoval. Namiesto toho `pip install -r requirements-llama-win-cuda.txt`, teda presne to, čo ALMANAC §8 krok 3 predpisoval – 218 MB, bez kompilácie. Tým sa naraz zodpovedali **obe neoverené otázky** zo §10.1:

- **`sm_120` áno** – `compute capability 12.0`, `offloaded 35/35 layers to GPU`, `CUDA0 model buffer = 2368 MiB`.
- **cuBLAS vo wheeli nie** – `ggml-cuda.dll` importuje `cublas64_13.dll`, `nvcuda.dll`, `nvcudart_hybrid64.dll`. CUDA Toolkit je stále potrebný, takže distribučný problém zo §10 (~507 MB DLL) platí.

Vedľajšie zistenie: **prvý beh po inštalácii mal `prompt eval` 21 s (1,73 t/s), druhý 0,3 s (127 t/s).** Vyzeralo to na PTX JIT, ale `%LOCALAPPDATA%\NVIDIA\ComputeCache` neexistuje, takže to nie je potvrdené – zapísané ako jednorazový warm-up neznámej príčiny. Pre UI to znamená, že prvé načítanie modelu nesmie vyzerať ako zamrznutie.

Pri tom padol aj pôvodný dojem zo „zlého výkonu“: ustálene je to ~103 t/s generovanie na gemma-3-4b Q4_K_M.

### Hotové

**`core/settings.py`** – `LoadParams` a `SamplingParams`, oba `frozen` dataclass.
Delenie presne podľa §7: load-time parametre idú do konštruktora `Llama(...)` a ich zmena znamená reload, sampling parametre idú do `create_chat_completion()` pri každej požiadavke.
`clamped()` je **zámerne samostatná metóda, nie `__post_init__`** – oprava hodnôt z databázy má byť viditeľný krok, nie tichá zmena v konštruktore. `validate()` rieši cestu k modelu a vyhadzuje `ModelFormatError` / `ModelNotFoundError`.
`to_dict()` / `from_dict()` sú priamo schéma tabuľky `chat_settings` pre krok 6.
`LoadParams.for_hardware()` berie `n_threads` a `n_gpu_layers` z `HardwareProfile`, nie z `psutil` priamo – profil už rieši P/E jadrá a chýbajúcu GPU.

**`core/llm_engine.py`** – trieda `LlmEngine`, bez importu PyQt6.
Model sa načítava v `load()`, nie v konštruktore (§5, bod 2), a `load()` sa chová ako no-op, keď sú parametre rovnaké – reload si vyžiada `force=True`.
`import llama_cpp` je **vnútri funkcie**, nie na úrovni modulu: import trvá dlho, inicializuje GPU a na zlom wheeli zlyhá. Appka sa musí dať spustiť aj bez enginu a chybu ukázať v UI ako `BackendUnavailableError`.
Stop je `threading.Event`, takže `request_stop()` sa smie volať z UI vlákna. Pri zastavení **generátor skončí normálne** a `stopped` je `True` – doteraz vygenerovaný text je platný výstup, nie chyba.
Pamäť sa meria **nanovo** pri `load()`, nie z `HardwareProfile` (§4) – hodnota z času štartu appky je už neplatná. Výsledkom je `Notice`, nie výnimka; keď sa model naozaj nenačíta, chybu nahlási llama.cpp a `load()` ju podľa textu preloží na `InsufficientMemoryError` alebo `ModelLoadError`.
Počet vrstiev sa číta z metadát (§5, bod 3): `n_layers` = 34 blokov, ale `n_layers_offloadable` = **35**, lebo llama.cpp offloaduje aj výstupnú vrstvu. Toto druhé číslo je maximum slidera CPU/GPU.

Konzolový test je v `__main__`: `python -m core.llm_engine [cesta.gguf]` – vypíše backend a parametre, načíta model, odstreamuje odpoveď a potom úmyselne zastaví generovanie po 10 častiach.

### Opravené / zahodené

- `core/llama_engine.py` (skript) **zmazaný** – nahradený `core/llm_engine.py`, čo je aj názov zo architektúry v §6. Dva takmer rovnaké názvy vedľa seba by boli pasca.
- V `settings.py` zostal po prvom zápise mŕtvy riadok (`known = {... if False}` + `del known`) – odstránený.
- Číslovanie krokov v ALMANAC §8 bolo pokazené (po `3.` nasledovalo znova `2.`) – prečíslované na 0–10 a pridaný krok `core/context.py`.

### Nedoriešené do ďalšej session

1. **MacBook** – nainštalovať `requirements-llama-mac.txt` (0.3.36 Metal) a spustiť `python -m core.llm_engine`. Neoverené zostáva Metal wheel aj `_performance_cores_macos()`.
2. **`core/context.py`** – počítanie tokenov a orezávanie histórie. Engine už dáva `tokenize()`, `count_tokens()`, `n_ctx`, `n_ctx_train`.
3. **Čítanie metadát `.gguf` bez načítania modelu** – na panel nastavení (krok 7) treba počet vrstiev a `n_ctx_train` **pred** loadom, aby sa dal nastaviť rozsah slidera. Teraz sú dostupné až po `load()`.
4. **stderr z llama.cpp** – `verbose=False` neutíši všetko (napr. `llama_kv_cache_iswa: ...`). Pri UI bude treba presmerovať stderr.
5. **Príčina 21 s warm-upu** pri prvom behu – nezistená, len zaznamenaná.
6. Model `gemma-3-4b-it-Q4_K_M.gguf` (2,4 GB) je skopírovaný v `models/`. Gitu neprekáža (`/models/` aj `*.gguf` sú v `.gitignore`), ale ALMANAC §4.1 hovorí modely do projektu nekopírovať – rozhodnúť, či to tak zostane.
7. **Variant inštalačky** – stále nerozhodnuté, tri možnosti v ALMANAC §10.

---

## 2026-10-28 / 29 – nastavenia, cesty, úložisko

**Stav na začiatku:** jadro hotové (`errors`, `hardware`, `settings`, `llm_engine`), úložisko nulové. Otázka „kde sa budú ukladať nastavenia“ otvorená.

### Zmena spôsobu práce

Od tejto session sa pracuje **po malých kusoch** – autor chce kódu rozumieť a písať ho sám, nie dostávať hotové moduly na schválenie. Zapísané do ALMANAC §8.1, platí aj pre ďalšie sessiony. Prakticky to znamená: návrh → jeden blok → prejdenie → ďalší blok.

### Návrh nastavení a úložiska

Pôvodný nápad „všetko do SQLite“ padol na jednej položke zo zoznamu nastavení: **cesta k chatom**. Uložiť cestu k databáze do databázy, ktorú ešte nevieš nájsť, nejde. Z toho vzniklo pravidlo v §7.1: *do JSON-u to, čo treba vedieť predtým, než sa otvorí databáza*.

Rozhodnuté (podrobne v ALMANAC §7.1): import modelu je **kópia** do `models_dir`, chat vzniká **pri prvej správe**, pri výmene modelu sa resetujú **len parametre závislé od modelu**, cesta k chatom **nie je** vo v1 nastaviteľná.

`settings.json` do `vars/` **nejde** – `vars/` je vedľa kódu, teda v zabalenej appke v inštalačnom adresári, kde používateľ bez admina nezapíše a na macOS by zápis rozbil podpis `.app`. Navyše by sa commitoval do Gitu. Hranica: `vars/` = pevné dáta dodané s kódom, `app_dir()` = to, čo sa mení používaním.

### Hotové

**`core/paths.py`** – jediné miesto, ktoré vie, kde má appka dáta.
Pri písaní sa overením `platformdirs` 4.9.6 zrušil pôvodný návrh dvoch adresárov: `user_config_dir()` a `user_data_dir()` vracajú na Windows aj macOS **to isté miesto** (overené aj v zdrojáku `platformdirs/macos.py`), líšia sa len na Linuxe, ktorý je mimo rozsah. Dva názvy pre jednu cestu = príležitosť pomýliť sa, takže jeden adresár.
Zistené pasce: `appauthor=False` je povinné (inak `AppData\Local\FUKAI\FUKAI`), `roaming` nechať vypnuté (doménové účty kopírujú `Roaming` pri každom prihlásení, a modely majú gigabajty).
Pridaná premenná **`FUKAI_HOME`**, ktorá `app_dir()` prepíše – bez nej by dev a ostré dáta boli v jednej databáze a testy by zapisovali do `AppData`.

**`storage/constants.py` + `storage/database.py`** – spojenie, pragmy, schéma, migrácie, operácie nad `models`.
Trieda `Database`, nie sada funkcií ako v `hardware.py`: **spojenie je stav a musí ho niekto držať**. Kostra vyšla skoro riadok po riadku rovnaká ako `LlmEngine` – `connect`/`close`/`_require_conn` namiesto `load`/`unload`/`_require_loaded`, lebo oba moduly riešia to isté: zdroj, ktorý sa otvorí, chvíľu žije a zavrie sa.
Migrácie cez `PRAGMA user_version` hneď od začiatku, nie až keď budú treba – prvá príde s prílohami (krok 10) a vtedy už v databáze budú dáta.

**Hranica, ktorá sa drží:** `database.py` vie SQL, nevie pravidlá. „Chat vzniká pri prvej správe“ ani „model sa počíta za použitý pri výbere“ tam nepatria – rozhoduje o tom vrstva nad ním. Preto `get_model()` nezapisuje `last_used_at` a `mark_model_used()` je zvlášť; všeobecne: **čo sa volá `get_*`, nemá meniť stav.**

### Schéma

Prešla tromi verziami. Prvý návrh mal celú konverzáciu ako `chats.content TEXT`, druhý ju presunul do tabuľky `content` 1:1 – čo ten istý problém len presťahovalo. Rozhodujúca zmena bola **`chats 1:N content`**, teda jeden riadok = jedna správa. Bez toho sa nedá streamovať bez prepisovania celého blobu, orezávať kontext podľa tokenov per správa, označiť prerušenú odpoveď ani navesiť prílohu.

Výsledok: `models`, `chats`, `content`, `properties`. Parametre a metadáta sú JSON (`data`, `meta`), ale to, podľa čoho sa radí a filtruje, sú stĺpce (`last_used_at`, `imported_at`, `role`, `tokens`). Dôvod pre JSON: parametrov bude s každým novým sliderom pribúdať a nechceme migráciu pri každom.

### Opravené chyby (a prečo stáli za zmienku)

| Chyba | Prečo bola zradná |
|---|---|
| `INT PRIMARY KEY` namiesto `INTEGER PRIMARY KEY` | všetky riadky dostanú `id = NULL`, bez protestu; cudzie kľúče by ukazovali na nič |
| chýbajúce `ON DELETE CASCADE` | so zapnutým `foreign_keys` zmazanie chatu **zlyhá**, s vypnutým nechá siroty – obe ticho |
| `chats.title ... UNIQUE` | druhý chat menom „Nový chat“ neprejde, a appka ich tak pomenúva |
| `DEFAULT '2000-01-01 00:00:00'` | konštanta, nie „teraz“ – chýbali zátvorky okolo `datetime('now')` |
| `datetime(now)` | bez úvodzoviek je `now` názov stĺpca → `no such column: now` |
| `ensure_dir(app_dir)` bez zátvoriek | odovzdá funkciu; `TypeError` navyše neprejde cez `except (OSError, sqlite3.Error)` |
| `hint=f"{exc}"` | technický text do poľa, kde má byť rada pre používateľa (`errors.py` to delí na `message`/`hint`/`detail`) |
| `c.commit()` | `commit()` je na spojení, nie na kurzore |
| `_with_meta` odsadený do triedy | stane sa atribútom triedy, ale volá sa holým menom → `NameError` |
| `json.loads(x or {})` | záloha je slovník, nie reťazec → `TypeError` |
| `from __future__` na druhom riadku | musí byť prvý *príkaz* v súbore, pred ním len docstring a komentáre |

### Poučenie, ktoré stojí za tých jedenásť riadkov vyššie

Tri z piatich metód nad `models` padli pri prvom zavolaní, hoci „to prešlo“. Dôvod: `__main__` self-test overoval len to, že sa otvorí spojenie – žiadnu z tých metód nezavolal. **Pokiaľ self-test nevolá to, čo píšeš, chybu nájdeš až v UI, kde sa hľadá oveľa horšie.** Self-test teraz prechádza celý cyklus nad temp databázou: pridaj model → vypíš → načítaj → označ použitý → over poradie → vytvor chat so správami → zmaž model → zmaž chat a over, že `CASCADE` aj `SET NULL` zabrali.

### Nedoriešené do ďalšej session

1. **Operácie nad `chats`, `content` a `properties`** – `create_chat`, `list_chats`, `rename_chat`, `delete_chat`, `set_model`, `add_message`, `get_messages`, `get_properties`, `set_properties`, reset parametrov cez `json_remove`.
2. **`core/app_settings.py`** – `settings.json`, zatiaľ neexistuje.
3. **`chats.date` sa volá `date`, ale bude sa aktualizovať** pri každej novej správe (sidebar radí podľa poslednej aktivity). `updated_at` by čitateľa neklamalo.
4. **`SELECT *` v `list_models` a `get_model`** – pri zmene schémy sa ticho zmenia kľúče v `dict`-och, ktoré očakáva UI. Vypísať stĺpce namenovito.
5. **Čítanie metadát `.gguf` bez načítania modelu** – teraz už nutnosť, nie bonus: import ich musí zapísať do `models.meta` a popup aj panel vlastností ich potrebujú pred `load()`.
6. Body 3–7 z predchádzajúcej session stále platia.

---

## 2026-10-30 – MacBook: settings pre engine, Metal build, engine od nuly

**Stav na začiatku:** prvá session na MacBooku po práci na PC 1. Repo aktuálne s `origin/main` (`fd59ca9`), `core/settings.py` len kostry dataclass, na Macu chýbal llama-cpp-python aj model.

### Hotové

**`core/settings.py` – časť pre engine.** Autor písal sám po kúskoch, Claude kontroloval a vysvetľoval. Poradie: oprava kostry → `for_hardware()` → `_clamp` + `clamped()` (obe triedy) → `validate()` → `model_size_mb` + `on_gpu` → `__post_init__`. Každý kúsok overený jednoriadkovým `python -c` testom pred ďalším.

**llama-cpp-python 0.3.36 Metal na M2 – build zo zdrojákov.** Oficiálny Metal wheel 0.3.36 je na GitHube poškodený (`Bad CRC-32` v `lib/cmake/ggml/ggml-config.cmake`). Postup diagnostiky: `--no-cache-dir` nepomohol → samostatné stiahnutie, SHA-256 sa zhoduje s digestom z GitHub API → `python -m zipfile -t` potvrdil poškodený súbor priamo vo wheeli → 0.3.35-metal je v poriadku. Zvolený build 0.3.36 zo zdrojákov namiesto 0.3.35, lebo **verzia musí byť na Macu aj PC rovnaká**. `requirements-llama-mac.txt` prepísaný na build.

**`core/llm_engine.py` od nuly – kúsky 1 až 3** (kostra, `load()` / `unload()`, údaje o modeli). Návrh rozhrania a poradie 8 kúskov dohodnuté pred kódom (ALMANAC §8 krok 3). Overené na M2: Gemma 3 4B cez Metal, `n_gpu_layers=-1`, `n_threads=4`.

### Opravené chyby (a prečo stáli za zmienku)

| Chyba | Prečo bola zradná |
|---|---|
| `STOP_DEFAULT = tuple(str, ...)` | typ vs. hodnota; padá už pri importe `constants.py` |
| `HardwareProfile.n_gpu_layers()` v predvolenej hodnote poľa | property volaná na triede; a aj keby fungovala, detekcia HW pri každom importe |
| `stop: tuple[str, ...]` bez `= STOP_DEFAULT` | pole bez predvolenej hodnoty za poľami s ňou → `non-default argument follows default argument` |
| `replace(` bez `self` | `missing 1 required positional argument: 'obj'` |
| `_clamp(self.seed, ...)` pri `seed=None` | padlo by pri **každej** správe, `None` je predvolený seed |
| `LoadParams("x.gguf")` → `model_path` ostal `str` | prevod bol len v `for_hardware`/`clamped`; vyriešené `__post_init__` |
| `import_llama` bez podčiarkovníka | test hľadal `_import_llama`; interné funkcie majú `_` |
| `self.verbose = verbose,` | n-tica `(False,)` je pravdivá → plný log llama.cpp, bez chyby |
| `LoadParams().model_path` v `load()` | šesť nových prázdnych inštancií namiesto parametrov od volajúceho |
| `for_hardware(cls, hw)` bez `model_path` a `n_ctx` | `model_path` je povinné pole – `LoadParams` bez modelu nedáva zmysel |
| `_meta_int("context-length")` – **neopravené** | spojovník namiesto `_`; bezpečné `None` pri chýbajúcom kľúči preklep ticho zakrylo – test dal `n_ctx_train=None` |

### Otázka, ktorá stojí za zápis

„Netreba pri vypnutí appky vypnúť backend, aby sa uvoľnila RAM?“ – Nie. Backend sa inicializuje raz pri prvom `Llama(...)` a knižnica ho neuvoľňuje; pamäť po procese uvoľní OS. Pamäť drží **model** a ten sa uvoľňuje pri výmene modelu (inak dva naraz) a pri zatvorení okna – tam ide o **poradie** (stop → počkať na worker → unload), nie o RAM. Podrobne v ALMANAC §8 krok 3.

### Nedoriešené do ďalšej session

1. **Opraviť `context-length` → `context_length`** v `n_ctx_train` a znova spustiť test kúsku 3 (má dať `2048 131072 34 35`).
2. **Engine kúsky 4–8:** `tokenize`/`count_tokens`, `stream()`, `request_stop()`, varovania o pamäti + preklad chýb, `__main__` test.
3. **Varovanie o pamäti na Metale** – `on_gpu` ho nesmie vypnúť pri zdieľanej pamäti ani čiastočnom offloade (ALMANAC §8 krok 3, „Otvorené“).
4. **`settings.py` – časť pre úložisko:** `to_dict`/`from_dict`, obal s `defaults_for()` a `needs_reload()`.
5. Všetko z tejto session je **necommitnuté**.

## 2026-10-31 – MacBook: llm_engine.py dokončený (kúsky 3–8)

**Stav na začiatku:** kúsky 1–3 enginu hotové, v `n_ctx_train` preklep `context-length`. Všetko z 2026-10-30 necommitnuté.

### Hotové

**`core/llm_engine.py` – kúsky 4 až 8, engine je kompletný.** Kúsky 4–5 písal autor (Claude navrhol a opravil), kúsky 6–8 napísal Claude na žiadosť autora. Každý overený na Gemme 3 4B cez Metal; rozhodnutia a zahodené alternatívy sú v ALMANAC §8 krok 3.

- **4 `tokenize`/`count_tokens`** – `add_bos=False`, `special=False`, bez zámku.
- **5 `stream()`** – generátor `Iterator[str]`, celé generovanie pod `_lock`, `ValueError` „exceed context window“ → `ContextOverflowError`.
- **6 `request_stop()` + `finish_reason`** – `threading.Event`, `FinishReason(Enum)` `DONE`/`LENGTH`/`STOPPED`. Stop z iného vlákna zaberie do ~0,1 s.
- **7 pamäť** – `load()` vracia `list[Notice]`, preklad chýb podľa fázy načítania, nové `hardware.free_ram_mb()`.
- **8 `__main__`** – `python -m core.llm_engine [model.gguf] [n_ctx]`.

**Overenie na druhom modeli** – Qwen 2.5 1.5B Q4_0: engine bez zmeny funguje (iná architektúra, bez BOS, iný EOS, `n_layers + 1` platí). Porovnávací skript ostal mimo repa.

**Rozhodnutie o Stope:** vráti sa celý ťah – zahodí sa čiastočná odpoveď aj otázka, text otázky sa vráti do vstupu (ALMANAC §8 krok 3, realizácia v kroku 9). `GenerationStopped` z `errors.py` zmazaná.

### Zistenia, ktoré stoja za zápis

| Zistenie | Prečo bolo zradné |
|---|---|
| `add_bos=True` v `tokenize` | nič nespadne, len každá správa +1 token – chyba rastie s dĺžkou chatu |
| `llm = self._llm` v akcii namiesto `_require_loaded()` | vzor z vlastností; bez modelu `AttributeError: 'NoneType'` namiesto `ModelLoadError` |
| `message=` namiesto `messages=` pri volaní knižnice | ľavá strana `názov=hodnota` patrí knižnici, nie nám |
| knižnica ticho skráti `max_tokens`, keď `prompt + max_tokens > n_ctx` | odpoveď sa utne bez hlásenia → preto `FinishReason.LENGTH` |
| `generator.close()` z iného vlákna | `ValueError: generator already executing` → stop musí byť príznak |
| Gemma template padá pri user, user | Qwen nie – na jednom modeli by sa to neukázalo; viedlo k rozhodnutiu o Stope |
| prázdny system prompt ≠ žiadny (Qwen) | bez system správy si Qwen doplní vlastnú |
| výnimka knižnice pri OOM je len `Failed to create llama_context` | starý engine hľadal „out of memory“ v texte → `InsufficientMemoryError` bol mŕtvy kód |
| `psutil.available` na macOS | nezapočíta súborovú cache (váhy cez mmap) → falošné varovanie pri každom načítaní |

### Nedoriešené do ďalšej session

1. **Na PC 1 spustiť `python -m core.llm_engine`** – overiť CUDA vetvu `_memory_pool` (VRAM), offload a rýchlosť; ideálne aj s Mistral 7B.
2. **`settings.py` – časť pre úložisko:** `to_dict`/`from_dict`, obal s `defaults_for()` a `needs_reload()` (krok 6).
3. Odhad pamäte bez KV cache – doplniť s čítačom hlavičky `.gguf` (krok 10).
4. Neoverené modely: Llama 3 (`strftime_now`), Qwen 3 (`<think>`).

## 2026-11-01 – PC 1: engine overený na Mistrale, `settings.py` dokončený (krok 6)

**Stav na začiatku:** všetko z Macu commitnuté (`f825724`), engine na PC 1 ešte nespustený, `settings.py` mal hotovú len časť pre engine.

### Hotové

**Engine overený na PC 1 na Mistrale 7B Q4_K_M** (`n_ctx=2048`), teda nedoriešený bod 1 z 2026-10-31. Čísla a všetky tri vetvy `_memory_pool` sú v ALMANAC §8 krok 3. Podstatné: `offloaded 33/33 layers to GPU` (32 blokov + výstupná, takže `n_layers + 1` platí aj na `llama` architektúre), 66,9 t/s, load 2,3 s bez warm-upu.

**`core/settings.py` dokončený – krok 6 je `[x]`.** Autor písal sám, Claude navrhoval a kontroloval, `__main__` self-test písal Claude. Pribudlo: `ChatProperties` (obal s `defaults_for`, `to_dict`, `from_dict`, `needs_reload`), `to_dict`/`from_dict` na štyroch dataclassoch, nová `ModelMeta` ako dohodnutý tvar `models.meta`, pomocné `_as_dict` / `_known` / `_NOT_STORED` a konštanty kľúčov metadát (`META_ARCH`, `META_CONTEXT_LENGTH`, `META_BLOCK_COUNT`), ktoré používa aj `llm_engine._meta_int()`. Rozhodnutia a dôvody v ALMANAC §8 krok 6.

**Rozhodnuté: o reloade modelu rozhoduje volajúci (UI), nie engine.** Engine reloaduje vždy, keď dostane `load()`; UI sa pred tým spýta `needs_reload()`. Tým sa opravila veta v ALMANAC §8 krok 6, ktorá tvrdila, že engine porovnáva `params == self._params` – engine také porovnanie nemá.

### Zistenia, ktoré stoja za zápis

| Zistenie | Prečo bolo zradné |
|---|---|
| `if n_ctx is None and meta.n_ctx_train` v `defaults_for` | `n_ctx` je o riadok vyššie nastavené na `N_CTX_DEFAULT`, takže vetva nikdy nenabehne a kontext sa neoreže na možnosti modelu – nič nespadne |
| `model_path` zabudnutý v blobe | `cls(model_path=path, **data)` → `TypeError: got multiple values for keyword argument`; preto `_known()` filtruje aj výstupný smer |
| `data.get("load", {})` pri `"load": null` | `get` vráti `None` (kľúč existuje), `**None` padne – musí byť `or {}` |
| `stop` cez JSON | z `tuple` sa stane `list`; vracia to `.clamped()` na konci `from_dict` |
| vymenované kľúče v `to_dict` namiesto `fields()` | nový slider v krokoch 9–11 by sa ticho neukladal |
| KV cache pri odhade pamäte | odmerané: Mistral 7B má pri `n_ctx=2048` KV 256 MiB, pri 32768 by to boli 4 GB – `MEMORY_MARGIN` to pokryje len pri malom kontexte |

**`core/app_settings.py` dokončený – krok 7 je `[x]`.** `AppSettings` (frozen dataclass) + modulové `load_settings()` / `save_settings()`, atomický zápis cez `.tmp` + `os.replace()`, rozbitý súbor → predvolené + `Notice`, `models_dir` pod neexistujúcou cestou → fallback. `version` je informatívna pečiatka, nič sa na nej nevetví. Self-test písal Claude, beží v temp adresári cez `FUKAI_HOME`. Rozhodnutia v ALMANAC §8 krok 7.

**Spresnené v §7.1:** web search má **tri** úrovne (aplikácia / chat / správa), prílohy dve. Globálne vypnutie prepíše chat pri skladaní promptu (`web_search_enabled AND properties.chat.web_search`), ale hodnotu v `properties` nemení.

### Zistenia z kroku 7

| Zistenie | Prečo bolo zradné |
|---|---|
| `except OSError` okolo `save_settings()` v `load_settings()` | `ConfigError` nie je podtrieda `OSError` → chyba preletí von a zabije štart funkcie, ktorá nikdy nemá vyhodiť výnimku |
| `with_suffix(".tmp")` | príponu **nahradí**, nie pridá – zo `settings.json` je `settings.tmp`; správne je `with_name(path.name + ".tmp")` |
| `Path.rename` na Windows | padne, keď cieľ existuje – a ten existuje vždy okrem prvého spustenia; `os.replace` prepíše |
| `clamped()` na `AppSettings` | navrhnutý zo zvyku zo `settings.py`, ale nie je čo orezávať – jediná opraviteľná hodnota (`theme`) prichádza len zo súboru, takže patrí do `from_dict` |
| `= default_models_dir()` ako predvolená hodnota poľa | vyhodnotí sa pri importe → ignorovalo by `FUKAI_HOME` nastavenú neskôr; preto `field(default_factory=...)` |
| `data.get("models_dir", default)` pri `"models_dir": null` | kľúč existuje, `get` vráti `None` a `Path(None)` padne – treba `or` |

### Nedoriešené do ďalšej session

1. **Krok 8 – `core/context.py`** (počítanie tokenov, orezávanie histórie). Engine dáva `tokenize()`, `count_tokens()`, `n_ctx`; úložisko `content.tokens`. Orezáva sa to, čo ide do promptu, nie databáza (§7.2). Pozor na striedanie rolí user/assistant (Gemma template padne na user, user) a na `content_tokens()`, ktoré vracia `0` aj pri samých `NULL`.
2. Odhad pamäte bez KV cache – doplniť s čítačom hlavičky `.gguf` (krok 10), teraz už je známa aj veľkosť na token.
3. Neoverené modely: Llama 3 (`strftime_now`), Qwen 3 (`<think>`).
