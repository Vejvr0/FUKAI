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
