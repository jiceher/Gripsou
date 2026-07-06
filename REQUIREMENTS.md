# Gripsou — Budget Manager Desktop Application

## Software Requirements Specification (SRS)

**Version:** 1.0
**Date:** 2026-07-01
**Technology:** Python (PyQt6 or PySide6)
**Storage:** SQLite (primary) + Excel/CSV export

---

## 1. Overview

Gripsou is a desktop application for personal or small-team yearly budget management. The user can enter, view, and analyse financial flows (credits and debits) laid out as a grid where **rows are budget line items (credits or debits)** and **columns are the 12 months of a selected year**. Multiple years can be managed and compared side by side.

---

## 2. Functional Requirements

### 2.1 Budget Grid (Core)

| ID   | Requirement                                                                                                                                                                                  |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C-01 | The main view SHALL display a 2D grid: rows = budget line items, columns = Jan … Dec.                                                                                                       |
| C-02 | Each row SHALL be tagged as either**Credit** (income) or **Debit** (expense) with different color highlight.                                                                     |
| C-03 | The**Credit** and **Debit** line are differentiate by a tag column.                                                                                                              |
| C-04 | The user SHALL be able to add, rename, reorder, and delete budget line items (rows).                                                                                                         |
| C-05 | Each cell SHALL accept a numeric value (≥ 0, two decimal places, currency-aware (euro)).                                                                                                    |
| C-06 | A**row total** column SHALL show the sum of all 12 months for each line item. The row total has color indicating if the sum is positive (green) or negative (red).                    |
| C-07 | A**monthly summary** row (footer) SHALL show: total credits, total debits, and net balance per month. The rows have color indicating if the sum is positive (green) or negative (red). |
| C-08 | A**yearly summary** cell SHALL show the net balance for the full selected year. The row has color indicating if the sum is positive (green) or negative (red).                       |
| C-09 | Modified cells SHALL be visually highlighted until the record is saved.                                                                                                                      |
| C-10 | The user SHALL be able to undo/redo individual cell edits (minimum 20 levels).                                                                                                               |
| C-11 | A **single click** on a month cell SHALL open it for editing. A **double-click** SHALL toggle its **validated** state: validated cells become non-editable and display a darker background (darker green for Credit, darker red for Debit); double-clicking again restores the lighter background and editability. Validation state SHALL be persisted in the database. |

### 2.2 Year Management

| ID   | Requirement                                                                          |
| ---- | ------------------------------------------------------------------------------------ |
| Y-01 | The application SHALL support an unlimited number of budget years.                   |
| Y-01 | The user SHALL be able to create a new year (blank or copied from an existing year). |
| Y-02 | The user SHALL be able to delete a year after confirmation.                          |
| Y-03 | Year selection SHALL be available via a drop-down or tab bar in the main toolbar.    |

### 2.3 Data Persistence (SQLite)

| ID   | Requirement                                                                                          |
| ---- | ---------------------------------------------------------------------------------------------------- |
| D-01 | All data SHALL be stored in a local SQLite database file (`gripsou.db`).                           |
| D-02 | The database file location SHALL be configurable (Settings dialog).                                  |
| D-03 | Changes SHALL be auto-saved, or the user SHALL be explicitly prompted to save on exit.               |
| D-04 | The database schema SHALL support: years, categories (Credit/Debit), line items, and monthly values. |

### 2.4 Import

| ID   | Requirement                                                                                                   |
| ---- | ------------------------------------------------------------------------------------------------------------- |
| I-01 | The user SHALL be able to import an Excel (`.xlsx`, `.xlsb`) or CSV file.                                 |
| I-02 | The import wizard SHALL let the user map source columns/rows to the application model (months, credit/debit). |
| I-03 | Imported data SHALL be previewed before being committed to the database.                                      |
| I-04 | A partial import failure SHALL not corrupt existing data (transactional import).                              |

### 2.5 Export

| ID   | Requirement                                                                                   |
| ---- | --------------------------------------------------------------------------------------------- |
| E-01 | The user SHALL be able to export any year to`.xlsx` (openpyxl) or `.csv`.                 |
| E-02 | The exported file SHALL mirror the grid layout: rows = line items, columns = months + totals. |
| E-03 | The export SHALL include a summary sheet/section with monthly and yearly totals.              |

### 2.6 Charts & Visualisation

| ID   | Requirement                                                                                                                                 |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| V-01 | A**Charts** panel SHALL display visualisations for the selected year.                                                                 |
| V-02 | Available chart types SHALL include: monthly bar chart (credits vs debits), cumulative balance line chart, and expense breakdown pie chart. |
| V-03 | Charts SHALL update automatically when grid data changes.                                                                                   |
| V-04 | Charts SHALL be exportable as PNG images.                                                                                                   |

### 2.7 Multi-Year Comparison

| ID   | Requirement                                                                                        |
| ---- | -------------------------------------------------------------------------------------------------- |
| M-01 | A**Compare** view SHALL allow selecting 2 or more years for side-by-side comparison.         |
| M-02 | The comparison SHALL show: yearly totals per line item, delta (absolute and %), and a trend chart. |
| M-03 | The user SHALL be able to export the comparison report to`.xlsx` or PDF.                         |

---

## 3. Non-Functional Requirements

| ID    | Requirement                                                                                                             |
| ----- | ----------------------------------------------------------------------------------------------------------------------- |
| NF-01 | The application SHALL run on Windows 10/11,  Linux and macOS.                                                          |
| NF-02 | The UI SHALL use**PyQt6** or **PySide6** with a modern flat theme (e.g. `qt-material` or `qdarktheme`). |
| NF-03 | Application startup SHALL complete within 3 seconds on standard hardware.                                               |
| NF-04 | The grid SHALL handle at least 200 line items × 12 months without perceptible lag.                                     |
| NF-05 | All user-visible text SHALL be externalisable for future localisation (i18n-ready).                                     |
| NF-06 | The SQLite database SHALL be versioned; schema migrations SHALL be handled automatically on upgrade.                    |
| NF-07 | The application SHALL not require an internet connection to operate.                                                    |

---

## 4. Suggested Data Model

```
Year
  id         INTEGER PK
  label      TEXT (e.g. "2025")

Category
  id         INTEGER PK
  name       TEXT ("Credit" | "Debit")

LineItem
  id         INTEGER PK
  year_id    FK → Year
  category_id FK → Category
  label      TEXT
  sort_order INTEGER

MonthlyValue
  id         INTEGER PK
  line_item_id FK → LineItem
  month      INTEGER (1–12)
  amount     REAL
```

---

## 5. Proposed Technology Stack

| Concern        | Choice                                       |
| -------------- | -------------------------------------------- |
| Language       | Python 3.11+                                 |
| GUI framework  | PyQt6 / PySide6                              |
| Database       | SQLite via`sqlite3` (stdlib)               |
| ORM (optional) | SQLAlchemy 2.x                               |
| Charts         | Matplotlib (embedded in Qt canvas)           |
| Excel I/O      | `openpyxl` (xlsx) + `pyxlsb` (xlsb read) |
| CSV I/O        | `csv` (stdlib)                             |
| Packaging      | PyInstaller or cx_Freeze                     |

---

## 6. Out of Scope (v1)

- Cloud sync or multi-user access
- Bank / API integrations
- Mobile or web interface
- Budgeting forecasts / AI recommendations

---

## 7. Open Questions

1. Are line items shared across years, or independent per year?
2. t packaging format — installer (`.exe`) or portable folder?

