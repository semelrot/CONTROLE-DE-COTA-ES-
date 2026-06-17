# AGENTS.md

## Cursor Cloud specific instructions

### What this is
Python 3.12 CLI/data-processing project (no web UI). The scripts validate a list of
company domains (DNS + HTTP probing), try to auto-correct broken ones (heuristics +
manual web-search candidates), classify steel-consumption research, and write a
consolidated, styled Excel workbook. There is no package manager manifest, lint config,
or test framework — only standalone scripts plus committed JSON data.

### Dependencies
Only three third-party packages: `requests`, `openpyxl`, `urllib3` (everything else is
stdlib). `requests`/`urllib3` ship in the base image; the update script adds `openpyxl`.
No virtualenv is used; packages install to the system `dist-packages`.

### Key gotcha: the main input workbook is NOT in the repo
`base_contatos.xlsx` (sheet `Dominios (Unificado)`) is the input for the pipeline but is
**gitignored and absent** because it holds personal data (name/email/phone). Therefore
`validar.py`, `build_queue.py`, and `escrever.py` cannot run against real data here —
they all call `openpyxl.load_workbook("base_contatos.xlsx")` and will fail with
`FileNotFoundError` until that file is supplied. To exercise these scripts, create a
small stand-in workbook with sheet `Dominios (Unificado)` (col A=Dominio, B=Qtd_Contatos,
C=Empresa; build_queue.py also reads E=Tipo, F=Subtipo, G=Consome_Aco, I=Obs).

### Running clobbers tracked JSON data
Scripts read/write committed data files in the repo root:
`validar.py` overwrites `resultados.json`; the probe/correction scripts
(`buscar_correcoes.py`, `segundo_passe.py`, `probe_lote2*.py`, `probe_lote3.py`) overwrite
`correcoes.json` / `probe_lote3.json`; `build_queue.py` overwrites `research_queue.json`.
To test without polluting git, copy the `.py` files (and any needed JSON) into a temp
dir and run there.

### Pipeline order
1. `python3 validar.py [n] [start]` — validate `n` domains starting at offset `start`
   (DNS + HTTP, threaded), writes `resultados.json`.
2. Correction probes (optional): `buscar_correcoes.py`, `segundo_passe.py`,
   `probe_lote2*.py`, `probe_lote3*.py` — read JSON, probe candidate domains, update
   `correcoes.json`.
3. `python3 build_queue.py` — joins workbook + `resultados.json` + `correcoes.json`
   into `research_queue.json`.
4. `python3 escrever.py` — merges `resultados.json` + `correcoes.json` + `pesquisa/part_*.json`
   into the `Validacao` sheet of `base_contatos_validada.xlsx`.

### Network
All scripts make real outbound DNS + HTTP requests; results depend on live connectivity.

### Lint / test / build
No configured linter or test suite. Use `python3 -m py_compile *.py` as a basic check.
