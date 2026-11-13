# Licencie tretích strán

FUKAI – Copyright (C) 2026 Lukáš Vavro. Program je slobodný softvér: môžeš ho šíriť a upravovať podľa
GNU General Public License verzie 3 alebo (podľa tvojho výberu) ktorejkoľvek neskoršej verzie (GPL-3.0-or-later),
ktorú vydala Free Software Foundation. Program je šírený BEZ AKEJKOĽVEK ZÁRUKY. Plné znenie je v súbore `LICENSE`.

FUKAI používa nasledujúce knižnice. Všetky sú s GPL v3 kompatibilné. Inštalačka ich sťahuje z PyPI
(okrem llama-cpp-python, ktorý je vo vydaniach tohto repa) – presné verzie sú v `dist/locks/`.

## Python balíky

| Balík | Verzia | Licencia | Projekt |
|---|---|---|---|
| babel | 2.18.0 | BSD-3-Clause | https://github.com/python-babel/babel |
| certifi | 2026.10.23 | MPL-2.0 | https://github.com/certifi/python-certifi |
| charset-normalizer | 3.5.2 | MIT | https://github.com/jawah/charset_normalizer |
| click | 8.5.1 | BSD-3-Clause | https://github.com/pallets/click/ |
| courlan | 1.4.0 | Apache-2.0 | https://github.com/adbar/courlan |
| dateparser | 1.5.0 | BSD-3-Clause | https://github.com/scrapinghub/dateparser |
| ddgs | 9.16.1 | MIT | https://github.com/deedy5/ddgs |
| diskcache | 5.6.3 | Apache-2.0 | https://github.com/grantjenks/python-diskcache |
| et-xmlfile | 2.0.0 | MIT | https://foss.heptapod.net/openpyxl/et_xmlfile |
| htmldate | 1.11.0 | Apache-2.0 | https://htmldate.readthedocs.io |
| idna | 3.20 | BSD-3-Clause | https://github.com/kjd/idna |
| jinja2 | 3.1.6 | BSD-3-Clause | https://github.com/pallets/jinja/ |
| justext | 3.0.2 | BSD-2-Clause | https://github.com/miso-belica/jusText |
| llama-cpp-python | 0.3.36 | MIT | https://github.com/abetlen/llama-cpp-python |
| lxml | 6.1.3 | BSD-3-Clause | https://github.com/lxml/lxml |
| lxml-html-clean | 0.4.6 | BSD-3-Clause | https://lxml-html-clean.readthedocs.io/ |
| markupsafe | 3.0.4 | BSD-3-Clause | https://github.com/pallets/markupsafe/ |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | https://numpy.org |
| nvidia-ml-py | 13.580.82 | BSD-3-Clause | https://pypi.org/project/nvidia-ml-py/ – len Windows |
| openpyxl | 3.1.5 | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| platformdirs | 4.9.6 | MIT | https://github.com/tox-dev/platformdirs |
| primp | 2.0.1 | MIT | https://github.com/deedy5/primp |
| psutil | 7.2.2 | BSD-3-Clause | https://github.com/giampaolo/psutil |
| pygments | 2.20.0 | BSD-2-Clause | https://pygments.org |
| pypdf | 6.1.3 | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| pyqt6 | 6.11.0 | GPL-3.0-only | https://www.riverbankcomputing.com/software/pyqt/ |
| pyqt6-qt6 | 6.11.2 | LGPL-3.0-only | https://www.riverbankcomputing.com/software/pyqt/ |
| pyqt6-sip | 13.13.1 | BSD-2-Clause | https://github.com/Python-SIP/sip |
| python-dateutil | 4.0.0 | BSD-3-Clause | https://github.com/dateutil/dateutil |
| python-docx | 1.2.0 | MIT | https://github.com/python-openxml/python-docx |
| pytz | 2026.6 | MIT | https://github.com/stub42/pytz.git |
| regex | 2026.11.9 | Apache-2.0 AND CNRI-Python | https://github.com/mrabarnett/mrab-regex |
| requests | 2.32.5 | Apache-2.0 | https://github.com/psf/requests |
| tld | 0.13.2 | LGPL-2.1-or-later (výber z MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later) | https://github.com/barseghyanartur/tld/ |
| trafilatura | 2.0.0 | Apache-2.0 | https://trafilatura.readthedocs.io |
| typing-extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| tzdata | 2026.6 | Apache-2.0 | https://github.com/python/tzdata |
| tzlocal | 5.4.5 | MIT | https://github.com/regebro/tzlocal |
| urllib3 | 2.8.0 | MIT | https://github.com/urllib3/urllib3 |

## Ostatné súčasti

| Súčasť | Licencia | Poznámka |
|---|---|---|
| Python 3.12.10 (python-build-standalone) | PSF-2.0 | inštalačka ho stiahne cez `uv` |
| Qt 6 | LGPL-3.0-only | súčasť `pyqt6-qt6` |
| llama.cpp / ggml | MIT | súčasť `llama-cpp-python`; Metal wheel postavený zo zdrojákov 0.3.36 |
| uv 0.13.7 (Astral) | MIT OR Apache-2.0 | pribalený v inštalačke, zostavuje prostredie |
| NVIDIA cuBLAS a CUDA runtime (`nvidia-cublas`, `nvidia-cuda-runtime`) | NVIDIA Software License (proprietárna) | **len Windows s kartou NVIDIA**; FUKAI ich nešíri – inštalačka ich stiahne z PyPI priamo do počítača používateľa |
