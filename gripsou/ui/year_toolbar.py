"""Year selector toolbar widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gripsou.db.database import Database


class NewYearDialog(QDialog):
    def __init__(self, existing_years: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Budget Year")
        self._existing = existing_years
        self._result_label: str = ""
        self._result_copy_id: int | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._year_edit = QComboBox()
        import datetime
        current_year = datetime.date.today().year
        for y in range(current_year - 5, current_year + 6):
            self._year_edit.addItem(str(y))
        self._year_edit.setCurrentText(str(current_year))
        self._year_edit.setEditable(True)
        form.addRow("Year label:", self._year_edit)
        layout.addLayout(form)

        self._radio_blank = QRadioButton("Blank year")
        self._radio_copy = QRadioButton("Copy line items from:")
        self._radio_blank.setChecked(True)
        self._copy_combo = QComboBox()
        self._copy_combo.setEnabled(False)
        for y in self._existing:
            self._copy_combo.addItem(y["label"], y["id"])
        self._radio_copy.toggled.connect(self._copy_combo.setEnabled)

        layout.addWidget(self._radio_blank)
        layout.addWidget(self._radio_copy)
        layout.addWidget(self._copy_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        self._result_label = self._year_edit.currentText().strip()
        if not self._result_label:
            QMessageBox.warning(self, "Error", "Year label cannot be empty.")
            return
        if self._radio_copy.isChecked() and self._copy_combo.count() > 0:
            self._result_copy_id = self._copy_combo.currentData()
        else:
            self._result_copy_id = None
        self.accept()

    def result_data(self) -> tuple[str, int | None]:
        return self._result_label, self._result_copy_id


class YearToolbar(QWidget):
    year_changed = pyqtSignal(int)   # year_id

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Year:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(120)
        self._combo.currentIndexChanged.connect(self._on_year_changed)
        layout.addWidget(self._combo)

        self._btn_new = QPushButton("+ New year")
        self._btn_new.clicked.connect(self._on_new_year)
        layout.addWidget(self._btn_new)

        self._btn_del = QPushButton("Delete year")
        self._btn_del.clicked.connect(self._on_delete_year)
        layout.addWidget(self._btn_del)

        layout.addStretch()

    def refresh(self):
        self._combo.blockSignals(True)
        current_id = self.current_year_id()
        self._combo.clear()
        for y in self.db.get_years():
            self._combo.addItem(y["label"], y["id"])
        if current_id is not None:
            idx = self._combo.findData(current_id)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)
        self._combo.blockSignals(False)
        self._emit_current()

    def current_year_id(self) -> int | None:
        if self._combo.count() == 0:
            return None
        return self._combo.currentData()

    def _emit_current(self):
        yid = self.current_year_id()
        if yid is not None:
            self.year_changed.emit(yid)

    def _on_year_changed(self, _index: int):
        self._emit_current()

    def _on_new_year(self):
        years = [{"id": self._combo.itemData(i), "label": self._combo.itemText(i)}
                 for i in range(self._combo.count())]
        dlg = NewYearDialog(years, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        label, copy_id = dlg.result_data()
        existing = [y["label"] for y in self.db.get_years()]
        if label in existing:
            QMessageBox.warning(self, "Duplicate", f"Year '{label}' already exists.")
            return
        if copy_id is not None:
            new_id = self.db.copy_year(copy_id, label)
        else:
            new_id = self.db.add_year(label)
        self.refresh()
        idx = self._combo.findData(new_id)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)

    def _on_delete_year(self):
        yid = self.current_year_id()
        if yid is None:
            return
        label = self._combo.currentText()
        reply = QMessageBox.question(
            self,
            "Delete year",
            f"Delete year '{label}' and all its data? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_year(yid)
        self.refresh()
