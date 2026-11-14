# FUKAI

**Fakultná Univerzálna Kognitívna AI** – desktopová aplikácia na chat s jazykovými modelmi, ktoré bežia priamo na tvojom počítači. Pomôže s každodennými otázkami, prácou so súbormi aj domácimi úlohami. Rozhovory, prílohy ani modely neodchádzajú na žiadny server.

Windows a macOS · Python, PyQt6 a [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) · licencia GPL-3.0-or-later

## Čo vie

- **Chat so streamovanou odpoveďou**, tlačidlo Stop, odpovede v markdowne (kód, tabuľky).
- **Uložené chaty** – zoznam v bočnom paneli, premenovanie, mazanie.
- **Prílohy** – text a kód (`.txt`, `.md`, `.csv`, `.json`, `.py`, …), PDF, Excel (`.xlsx`), Word (`.docx`). Bez OCR.
- **Vyhľadávanie na webe** – voliteľne, prepínačom pri písaní správy (DuckDuckGo); odpoveď uvedie zdroje.
- **Vlastné modely** vo formáte `.gguf` a nastavenia pre každý chat: systémový prompt, dĺžka kontextu, teplota, top-p/top-k, CPU vs. GPU.
- **Grafická karta** – NVIDIA (CUDA) na Windows, Metal na Macu; bez vhodnej karty beží na procesore.

## Požiadavky

| | macOS | Windows |
|---|---|---|
| Systém | macOS 14 Sonoma alebo novší | Windows 10 verzia 2004 (build 19041) alebo novší, 64-bit |
| Procesor | Apple Silicon (M1 alebo novší) | s inštrukciami AVX2 (Intel od roku 2013, AMD od roku 2015) |
| Grafická karta | integrovaná (Metal) | voliteľne NVIDIA GTX 16xx, RTX 20xx a novšia s ovládačom 580 alebo novším; inak beží na procesore |
| Pamäť | 8 GB a viac | 8 GB a viac |
| Disk | ~510 MB + modely | ~530 MB (procesor), ~1,3 GB (NVIDIA) + modely |
| Internet | pri inštalácii | pri inštalácii |

Inštalačka si sama zistí hardvér a pripraví verziu pre tvoj počítač. Ak karta NVIDIA nespĺňa požiadavky (napríklad staršia GeForce MX), FUKAI ťa upozorní a nainštaluje verziu pre procesor.

Väčšie modely potrebujú viac pamäte. Pri 8 GB odporúčame modely do 3–4 miliárd parametrov v kvantizácii Q4, napríklad Qwen 2.5 1.5B / 3B Instruct alebo Gemma 3 4B it.

## Inštalácia

Stiahni inštalačku zo stránky **[Releases](https://github.com/Vejvr0/FUKAI/releases/latest)**:

- macOS: `FUKAI-<verzia>.pkg`
- Windows: `FUKAI-Setup-<verzia>.exe`

Inštalačky nie sú podpísané platenými certifikátmi Apple a Microsoft, preto ich systém pri prvom otvorení zastaví. Postup nižšie to obíde – urob to len so súborom stiahnutým z tejto stránky.

### macOS

1. Otvor `FUKAI-<verzia>.pkg`. macOS ukáže, že balík nemôže overiť – klikni **Hotovo**.
2. Otvor **Systémové nastavenia → Súkromie a bezpečnosť**, nalistuj časť **Bezpečnosť** a pri hlásení o `FUKAI-<verzia>.pkg` klikni **Aj tak otvoriť**.
3. Prejdi inštalátor. Pýta si heslo správcu, lebo FUKAI sa inštaluje do priečinka Aplikácie pre všetkých používateľov.
4. Krok **„Spúšťajú sa skripty balíka“** trvá niekoľko minút – stiahne Python a knižnice (~160 MB). Inštalátor vtedy nezatváraj.

Na macOS 14 stačí namiesto krokov 1–2 kliknúť na balík pravým tlačidlom a zvoliť **Otvoriť**.

### Windows

1. Spusti `FUKAI-Setup-<verzia>.exe`. Ak sa objaví **„Windows chránil váš počítač“**, klikni **Ďalšie informácie → Spustiť aj tak**.
2. Inštalácia nepotrebuje práva správcu – FUKAI sa nainštaluje len pre teba.
3. Inštalačka stiahne Python a knižnice (~130 MB, s kartou NVIDIA ~720 MB) a overí, že engine beží. Na konci vytvorí zástupcu v ponuke Štart (a voliteľne na ploche).

## Prvé spustenie

1. FUKAI neobsahuje žiadny model. Stiahni si model vo formáte `.gguf`, napríklad z [Hugging Face](https://huggingface.co/models?library=gguf) (súbor s `Q4_K_M` alebo `Q4_0` v názve je dobrý kompromis medzi kvalitou a veľkosťou).
2. V aplikácii klikni na výber modelu pri poli na písanie správy → **Pridať .gguf model…**. FUKAI si model skopíruje do svojho priečinka.
3. Napíš správu. Model sa načíta pri prvej otázke.

Rýchlosť a nastavenia modelu (dĺžka kontextu, CPU vs. GPU, systémový prompt) zmeníš na karte **Vlastnosti**, tému, web a prílohy na karte **Nastavenia**.

## Kde sú dáta a logy

| | macOS | Windows |
|---|---|---|
| Aplikácia | `/Applications/FUKAI.app` | `%LOCALAPPDATA%\Programs\FUKAI` |
| Chaty, nastavenia, modely | `~/Library/Application Support/FUKAI` | `%LOCALAPPDATA%\FUKAI` |
| Log aplikácie | `fukai.log` v priečinku s dátami | `fukai.log` v priečinku s dátami |
| Log inštalácie | `/Library/Logs/FUKAI-install.log` | `install.log` v priečinku aplikácie |

Log neobsahuje texty správ ani príloh – len priebeh (načítanie modelu, rýchlosť, chyby). Ak niečo nefunguje, pripoj ho k hláseniu chyby.

## Odinštalovanie

**macOS** – v Termináli:

```
sudo rm -rf /Applications/FUKAI.app
sudo pkgutil --forget sk.vavro.fukai
```

Dáta zostanú. Ak ich nechceš, zmaž aj `~/Library/Application Support/FUKAI`.

**Windows** – **Nastavenia → Aplikácie → FUKAI → Odinštalovať**. Odinštalátor sa opýta, či zmazať aj chaty, nastavenia a modely.

## Súkromie

Modely bežia lokálne, chaty a prílohy zostávajú na disku. FUKAI sa pripája na internet len pri inštalácii (Python a knižnice z PyPI a z vydaní tohto repozitára) a pri vyhľadávaní na webe, ak ho zapneš – vtedy odíde text otázky do DuckDuckGo a FUKAI stiahne nájdené stránky.

## Pre vývojárov

Zdrojáky sú v Pythone 3.12.10. Vývojové prostredie sa zostavuje rovnako ako u používateľa – nástrojom [uv](https://github.com/astral-sh/uv) zo zámkov s presnými verziami a hashmi:

```
uv venv --python 3.12.10 .venv
uv pip install --python .venv/bin/python --require-hashes -r dist/locks/mac-metal.txt
uv pip install --python .venv/bin/python --no-deps <wheel llama-cpp-python>
.venv/bin/python main.py
```

Na Windows zámok `win-cpu.txt` alebo `win-cuda.txt` a `.venv\Scripts\python.exe`. Wheel llama-cpp-python pre daný backend je vo vydaniach `llama-0.3.36-metal`, `-cpu` a `-cu130` ([Releases](https://github.com/Vejvr0/FUKAI/releases)); presný súbor a SHA-256 sú v `dist/manifest.json`. Premenná `FUKAI_HOME` presmeruje dáta do iného priečinka (vývoj, testy).

| Priečinok | Obsah |
|---|---|
| `core/` | engine, hardvér, nastavenia, kontext – bez Qt |
| `storage/` | SQLite databáza chatov |
| `extensions/` | prílohy a vyhľadávanie na webe |
| `ui/` | rozhranie v PyQt6 |
| `dist/` | manifest, zámky, inštalačky (`mac_app_installer/build_pkg.sh`, `windows_app_installer/build_setup.ps1`) |

## Licencia

FUKAI – Copyright (C) 2026 Lukáš Vavro

Tento program je slobodný softvér: môžeš ho šíriť a upravovať za podmienok licencie GNU General Public License vo verzii 3 alebo (podľa tvojej voľby) v ktorejkoľvek neskoršej verzii, ako ju vydala Free Software Foundation. Program sa šíri bez akejkoľvek záruky. Plné znenie je v súbore [LICENSE](LICENSE), licencie použitých knižníc v [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

### Releases

<b>v1.0 -</b> <i>14.11. 2026</i>

## Autor

Lukáš Vavro – semestrálny projekt, Žilinská univerzita v Žiline.
