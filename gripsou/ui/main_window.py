"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gripsou.db.database import Database
from gripsou.ui.budget_grid import BudgetGrid
from gripsou.ui.charts_panel import ChartsPanel
from gripsou.ui.year_toolbar import YearToolbar


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setWindowTitle("Gripsou — Budget Manager")
        self.resize(1200, 700)
        self._build_status_bar()
        self._build_ui()
        self._build_menu()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        self._year_toolbar = YearToolbar(self.db)
        self._year_toolbar.year_changed.connect(self._on_year_changed)
        self._year_toolbar.years_modified.connect(self._refresh_last_update_label)
        layout.addWidget(self._year_toolbar)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._grid = BudgetGrid(self.db)
        self._grid.data_changed.connect(self._on_data_changed)
        self._tabs.addTab(self._grid, "Budget Grid")

        self._charts = ChartsPanel()
        self._tabs.addTab(self._charts, "Charts")

        # Trigger initial load
        yid = self._year_toolbar.current_year_id()
        if yid is not None:
            self._grid.load_year(yid)
            self._charts.update_data(self._grid.get_line_items())

    def _build_menu(self):
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("&File")

        act_import = QAction("&Import from Excel/CSV…", self)
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        act_import.triggered.connect(self._on_import)
        file_menu.addAction(act_import)

        act_export_xlsx = QAction("Export to &Excel…", self)
        act_export_xlsx.setShortcut(QKeySequence("Ctrl+E"))
        act_export_xlsx.triggered.connect(self._on_export_xlsx)
        file_menu.addAction(act_export_xlsx)

        act_export_csv = QAction("Export to &CSV…", self)
        act_export_csv.triggered.connect(self._on_export_csv)
        file_menu.addAction(act_export_csv)

        file_menu.addSeparator()

        act_settings = QAction("&Settings…", self)
        act_settings.triggered.connect(self._on_settings)
        file_menu.addAction(act_settings)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_quit)

        # Edit menu
        edit_menu = mb.addMenu("&Edit")

        act_undo = self._grid.undo_stack().createUndoAction(self, "&Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(act_undo)

        act_redo = self._grid.undo_stack().createRedoAction(self, "&Redo")
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_add_credit = QAction("Add &Credit row…", self)
        act_add_credit.triggered.connect(lambda: self._add_row("Credit"))
        edit_menu.addAction(act_add_credit)

        act_add_debit = QAction("Add &Debit row…", self)
        act_add_debit.triggered.connect(lambda: self._add_row("Debit"))
        edit_menu.addAction(act_add_debit)

        act_del_row = QAction("&Delete selected row(s)", self)
        act_del_row.setShortcut(QKeySequence.StandardKey.Delete)
        act_del_row.triggered.connect(self._delete_row)
        edit_menu.addAction(act_del_row)

        # Analysis menu
        analysis_menu = mb.addMenu("&Analysis")
        act_compare = QAction("Multi-year &comparison…", self)
        act_compare.triggered.connect(self._on_compare)
        analysis_menu.addAction(act_compare)

    def _build_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")
        self._last_update_label = QLabel()
        self._last_update_label.setStyleSheet("color: gray; padding-right: 6px;")
        self._status.addPermanentWidget(self._last_update_label)
        self._refresh_last_update_label()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_year_changed(self, year_id: int):
        self._grid.load_year(year_id)
        self._charts.update_data(self._grid.get_line_items())
        label = self._year_toolbar._combo.currentText()
        self.setWindowTitle(f"Gripsou — {label}")
        self._status.showMessage(f"Loaded year {label}")

    def _on_data_changed(self):
        self._charts.update_data(self._grid.get_line_items())
        self._refresh_last_update_label()

    def _refresh_last_update_label(self):
        import datetime
        import os
        try:
            mtime = os.path.getmtime(self.db.path)
        except OSError:
            mtime = datetime.datetime.now().timestamp()
        ts = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d  %H:%M:%S")
        self._last_update_label.setText(f"Last update: {ts}")

    def _add_row(self, category: str):
        label, ok = QInputDialog.getText(
            self, f"Add {category} row", f"Label for new {category} line:"
        )
        if ok and label.strip():
            self._grid.add_row(category, label.strip())
            self._status.showMessage(f"Added {category}: {label.strip()}")

    def _delete_row(self):
        reply = QMessageBox.question(
            self,
            "Delete row",
            "Delete selected budget line(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._grid.delete_selected_row()

    def _on_import(self):
        from gripsou.ui.import_wizard import ImportWizard
        wizard = ImportWizard(self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        data = wizard.parsed_data()
        if not data:
            QMessageBox.information(self, "Import", "Nothing to import.")
            return
        year_id = self._year_toolbar.current_year_id()
        if year_id is None:
            QMessageBox.warning(self, "Import", "No active year. Create a year first.")
            return
        reply = QMessageBox.question(
            self, "Import",
            f"Import {len(data)} line item(s) into the current year? "
            "Existing data will NOT be overwritten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = self.db.conn
            conn.execute("BEGIN")
            sort_base = len(self.db.get_line_items(year_id))
            for i, item in enumerate(data):
                item_id = self.db.add_line_item(
                    year_id, item["category"], item["label"], sort_base + i
                )
                for m, amt in item["monthly_values"].items():
                    self.db.set_monthly_value(item_id, m, amt)
            conn.execute("COMMIT")
        except Exception as e:
            self.db.conn.execute("ROLLBACK")
            QMessageBox.critical(self, "Import failed", str(e))
            return
        self._grid.reload()
        self._on_data_changed()
        self._status.showMessage(f"Imported {len(data)} line item(s).")

    def _on_export_xlsx(self):
        year_id = self._year_toolbar.current_year_id()
        if year_id is None:
            return
        year_label = self._year_toolbar._combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to Excel",
            f"budget_{year_label}.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        from gripsou.io.exporter import export_xlsx
        export_xlsx(self._grid.get_line_items(), year_label, path)
        self._status.showMessage(f"Exported to {path}")

    def _on_export_csv(self):
        year_id = self._year_toolbar.current_year_id()
        if year_id is None:
            return
        year_label = self._year_toolbar._combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV",
            f"budget_{year_label}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        from gripsou.io.exporter import export_csv
        export_csv(self._grid.get_line_items(), path)
        self._status.showMessage(f"Exported to {path}")

    def _on_settings(self):
        from gripsou.ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(str(self.db.path), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_path = dlg.selected_path()
            if new_path != str(self.db.path):
                QMessageBox.information(
                    self,
                    "Settings saved",
                    f"Database path set to:\n{new_path}\nRestart the application to apply.",
                )

    def _on_compare(self):
        from gripsou.ui.compare_dialog import CompareDialog
        dlg = CompareDialog(self.db, self)
        dlg.exec()
