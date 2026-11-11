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

**Ďalej:** commit (autor) → test na PC 1 podľa ALMANAC §8.3 → krok 14 (balenie).
