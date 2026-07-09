# Gripsou — Budget Manager

A desktop budget management application written in Python / PyQt6.

## Features

- Yearly budget grid (rows = credit/debit line items, columns = Jan–Dec)
- Color-coded credits (green) and debits (red) with sign-aware totals
- Undo/redo (20 levels)
- Multi-year management — create blank or copy-from-existing years
- Import from Excel (`.xlsx`, `.xlsb`) and CSV
- Export to Excel (`.xlsx`) and CSV
- Embedded charts: bar, cumulative balance line, expense pie
- Multi-year comparison with trend chart and Excel/PDF export
- SQLite persistence with automatic schema migration

## Requirements

- Python 3.11+
- See `requirements.txt`

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Portable packaging

A PyInstaller-based build script is provided. It produces a portable folder on Windows
and a `.app` bundle on macOS.

### Windows 11

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt
python build.py
```

The portable folder will be in `dist\Gripsou\`. Run `dist\Gripsou\Gripsou.exe`.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-build.txt
python build.py
```

The app bundle will be in `dist/Gripsou.app`.

### Automated builds

A GitHub Actions workflow in `.github/workflows/build.yml` builds and zips both the
Windows portable folder and the macOS `.app` bundle on every push to `main`.

## Project structure

```
gripsou/
  db/
    database.py     # SQLite layer, CRUD
    models.py       # dataclasses
  ui/
    main_window.py  # QMainWindow
    budget_grid.py  # editable QTableWidget grid
    year_toolbar.py # year selector widget
    charts_panel.py # Matplotlib charts
    compare_dialog.py # multi-year comparison
    import_wizard.py  # 3-step import wizard
    settings_dialog.py
  io/
    exporter.py     # xlsx / csv export
    importer.py     # xlsx / xlsb / csv read + parse
main.py             # entry point
requirements.txt
```
