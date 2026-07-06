"""Import wizard — 4-step QWizard."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from gripsou.io.importer import parse_import, read_file


class FilePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 1 — Select file")
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Path to xlsx, xlsb or csv file…")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self._path_edit)
        row.addWidget(browse)
        layout.addLayout(row)
        self.registerField("file_path*", self._path_edit)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "",
            "Spreadsheets (*.xlsx *.xlsb *.csv);;All files (*)"
        )
        if path:
            self._path_edit.setText(path)


class MappingPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Step 2 — Map columns")
        self._raw: list[list[str]] = []
        form = QFormLayout(self)

        self._header_spin = QSpinBox()
        self._header_spin.setRange(0, 100)
        self._header_spin.setValue(0)
        form.addRow("Header row (0-indexed):", self._header_spin)

        self._label_spin = QSpinBox()
        self._label_spin.setRange(0, 200)
        form.addRow("Label column (0-indexed):", self._label_spin)

        self._tag_check = QCheckBox("File contains Credit/Debit tag column")
        form.addRow(self._tag_check)

        self._tag_spin = QSpinBox()
        self._tag_spin.setRange(0, 200)
        self._tag_spin.setEnabled(False)
        self._tag_check.toggled.connect(self._tag_spin.setEnabled)
        form.addRow("Tag column (0-indexed):", self._tag_spin)

        self._default_cat = QComboBox()
        self._default_cat.addItems(["Credit", "Debit"])
        self._default_cat.setCurrentText("Debit")
        form.addRow("Default category (if no tag column):", self._default_cat)

        self._month_edit = QLineEdit("2,3,4,5,6,7,8,9,10,11,12,13")
        self._month_edit.setToolTip("Comma-separated 0-indexed column numbers for Jan…Dec")
        form.addRow("Month columns (Jan→Dec, 0-indexed):", self._month_edit)

        self.registerField("header_row", self._header_spin, "value")
        self.registerField("label_col", self._label_spin, "value")
        self.registerField("month_cols", self._month_edit)
        self.registerField("default_cat", self._default_cat, "currentText")

    def initializePage(self):
        path = self.field("file_path")
        try:
            self._raw = read_file(path)
        except Exception as e:
            self._raw = []

    def get_params(self):
        header_row = self._header_spin.value()
        label_col = self._label_spin.value()
        tag_col = self._tag_spin.value() if self._tag_check.isChecked() else None
        try:
            month_cols = [int(x.strip()) for x in self._month_edit.text().split(",") if x.strip()]
        except ValueError:
            month_cols = list(range(2, 14))
        default_cat = self._default_cat.currentText()
        return header_row, label_col, tag_col, month_cols, default_cat

    def raw(self):
        return self._raw


class PreviewPage(QWizardPage):
    def __init__(self, mapping_page: MappingPage):
        super().__init__()
        self.setTitle("Step 3 — Preview")
        self._mapping = mapping_page
        self._parsed: list[dict] = []
        layout = QVBoxLayout(self)
        self._table = QTableWidget()
        layout.addWidget(self._table)

    def initializePage(self):
        raw = self._mapping.raw()
        header_row, label_col, tag_col, month_cols, default_cat = self._mapping.get_params()
        self._parsed = parse_import(raw, header_row, label_col, tag_col, month_cols, default_cat)
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self._table.clear()
        self._table.setColumnCount(2 + 12)
        self._table.setHorizontalHeaderLabels(["Label", "Category"] + months)
        self._table.setRowCount(len(self._parsed))
        for r, item in enumerate(self._parsed):
            self._table.setItem(r, 0, QTableWidgetItem(item["label"]))
            self._table.setItem(r, 1, QTableWidgetItem(item["category"]))
            for m in range(1, 13):
                val = item["monthly_values"].get(m, 0.0)
                ti = QTableWidgetItem(f"{val:.2f}")
                ti.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._table.setItem(r, 1 + m, ti)

    def parsed_data(self):
        return self._parsed


class ImportWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Budget Data")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self._file_page = FilePage()
        self._mapping_page = MappingPage()
        self._preview_page = PreviewPage(self._mapping_page)

        self.addPage(self._file_page)
        self.addPage(self._mapping_page)
        self.addPage(self._preview_page)

    def parsed_data(self) -> list[dict]:
        return self._preview_page.parsed_data()
