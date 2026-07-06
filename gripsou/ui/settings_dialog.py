"""Settings dialog — configure database file path."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, current_db_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._db_path = current_db_path
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit(self._db_path)
        self._path_edit.setMinimumWidth(350)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._path_edit)
        path_row.addWidget(browse_btn)

        form.addRow("Database file:", path_row)
        layout.addLayout(form)

        layout.addWidget(
            QLabel("Note: changing the database path requires a restart.")
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select database file",
            self._path_edit.text(),
            "SQLite databases (*.db);;All files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def selected_path(self) -> str:
        return self._path_edit.text().strip()
