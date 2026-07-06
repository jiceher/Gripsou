"""Multi-year comparison dialog."""

from __future__ import annotations

import itertools

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gripsou.db.database import Database
from gripsou.db.models import LineItem


class CompareDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Multi-Year Comparison")
        self.resize(1000, 650)
        self._year_checks: dict[int, QCheckBox] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Year selection
        sel_layout = QHBoxLayout()
        sel_layout.addWidget(QLabel("Select years to compare:"))
        for y in self.db.get_years():
            cb = QCheckBox(y["label"])
            cb.setChecked(True)
            self._year_checks[y["id"]] = cb
            sel_layout.addWidget(cb)
        compare_btn = QPushButton("Compare")
        compare_btn.clicked.connect(self._run_comparison)
        sel_layout.addWidget(compare_btn)
        sel_layout.addStretch()
        layout.addLayout(sel_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Table
        self._table = QTableWidget()
        splitter.addWidget(self._table)

        # Chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        self._figure = Figure(figsize=(8, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        chart_layout.addWidget(self._canvas)
        splitter.addWidget(chart_widget)

        layout.addWidget(splitter)

        # Buttons
        btn_row = QHBoxLayout()
        export_xlsx_btn = QPushButton("Export to Excel…")
        export_xlsx_btn.clicked.connect(self._export_xlsx)
        export_pdf_btn = QPushButton("Export to PDF…")
        export_pdf_btn.clicked.connect(self._export_pdf)
        btn_row.addWidget(export_xlsx_btn)
        btn_row.addWidget(export_pdf_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._run_comparison()

    def _selected_years(self) -> list[tuple[int, str]]:
        return [
            (yid, cb.text())
            for yid, cb in self._year_checks.items()
            if cb.isChecked()
        ]

    def _load_year_totals(self, year_id: int) -> dict[str, float]:
        """Return {line_item_label: yearly_total}."""
        items = self.db.get_line_items(year_id)
        summary = self.db.get_year_summary(year_id)
        result = {}
        for r in items:
            monthly = summary.get(r["id"], {})
            total = sum(monthly.values())
            result[r["label"]] = total
        return result

    def _run_comparison(self):
        years = self._selected_years()
        if len(years) < 2:
            return

        all_labels: list[str] = []
        year_data: dict[int, dict[str, float]] = {}
        for yid, _ in years:
            totals = self._load_year_totals(yid)
            year_data[yid] = totals
            for lbl in totals:
                if lbl not in all_labels:
                    all_labels.append(lbl)

        # Build table: col per year + delta columns
        base_id, base_label = years[0]
        compare_years = years[1:]

        cols = ["Line item", base_label]
        for yid, ylabel in compare_years:
            cols += [ylabel, f"Δ vs {base_label}", f"Δ% vs {base_label}"]

        self._table.clear()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setRowCount(len(all_labels))

        for row, label in enumerate(all_labels):
            self._table.setItem(row, 0, QTableWidgetItem(label))
            base_val = year_data[base_id].get(label, 0.0)
            self._table.setItem(row, 1, QTableWidgetItem(f"{base_val:,.2f}"))
            col = 2
            for yid, _ in compare_years:
                val = year_data[yid].get(label, 0.0)
                delta = val - base_val
                pct = (delta / base_val * 100) if base_val != 0 else 0.0
                self._table.setItem(row, col, QTableWidgetItem(f"{val:,.2f}"))
                d_item = QTableWidgetItem(f"{delta:+,.2f}")
                d_item.setForeground(
                    Qt.GlobalColor.darkGreen if delta >= 0 else Qt.GlobalColor.red
                )
                self._table.setItem(row, col + 1, d_item)
                p_item = QTableWidgetItem(f"{pct:+.1f}%")
                p_item.setForeground(
                    Qt.GlobalColor.darkGreen if pct >= 0 else Qt.GlobalColor.red
                )
                self._table.setItem(row, col + 2, p_item)
                col += 3

        self._table.resizeColumnsToContents()

        # Trend chart
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        year_labels = [yl for _, yl in years]
        for label in all_labels[:10]:  # limit to first 10 for readability
            values = [year_data[yid].get(label, 0.0) for yid, _ in years]
            ax.plot(year_labels, values, marker="o", label=label)
        ax.set_title("Year-over-year trend (top line items)")
        ax.set_ylabel("Amount (€)")
        ax.legend(fontsize=7, loc="best")
        ax.grid(linestyle="--", alpha=0.4)
        self._canvas.draw()

        self._last_years = years
        self._last_all_labels = all_labels
        self._last_year_data = year_data

    def _export_xlsx(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export comparison", "", "Excel (*.xlsx)"
        )
        if not path:
            return
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Comparison"
        years = self._last_years
        base_id, base_label = years[0]
        headers = ["Line item", base_label]
        for yid, ylabel in years[1:]:
            headers += [ylabel, f"Δ vs {base_label}", f"Δ% vs {base_label}"]
        ws.append(headers)
        for label in self._last_all_labels:
            base_val = self._last_year_data[base_id].get(label, 0.0)
            row = [label, base_val]
            for yid, _ in years[1:]:
                val = self._last_year_data[yid].get(label, 0.0)
                delta = val - base_val
                pct = (delta / base_val * 100) if base_val != 0 else 0.0
                row += [val, delta, f"{pct:+.1f}%"]
            ws.append(row)
        wb.save(path)

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export comparison PDF", "", "PDF (*.pdf)"
        )
        if not path:
            return
        self._figure.savefig(path, format="pdf", bbox_inches="tight")
