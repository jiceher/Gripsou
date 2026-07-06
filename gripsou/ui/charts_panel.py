"""Embedded Matplotlib charts panel."""

from __future__ import annotations

import itertools

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gripsou.db.models import LineItem

MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CHART_TYPES = [
    "Monthly bar (Credits vs Debits)",
    "Cumulative net balance",
    "Expense breakdown (pie)",
]


class ChartsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_items: list[LineItem] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Chart:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(CHART_TYPES)
        self._type_combo.currentIndexChanged.connect(self._refresh)
        top.addWidget(self._type_combo)

        save_btn = QPushButton("Save as PNG…")
        save_btn.clicked.connect(self._save_png)
        top.addWidget(save_btn)
        top.addStretch()
        layout.addLayout(top)

        self._figure = Figure(figsize=(8, 4), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._canvas)

    def update_data(self, line_items: list[LineItem]):
        self._line_items = line_items
        self._refresh()

    def _refresh(self):
        self._figure.clear()
        idx = self._type_combo.currentIndex()
        if idx == 0:
            self._draw_bar()
        elif idx == 1:
            self._draw_cumulative()
        else:
            self._draw_pie()
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Chart drawers
    # ------------------------------------------------------------------

    def _monthly_totals(self):
        credits = [0.0] * 12
        debits = [0.0] * 12
        for li in self._line_items:
            for m in range(1, 13):
                val = li.amount(m)
                if li.category == "Credit":
                    credits[m - 1] += val
                else:
                    debits[m - 1] += val
        return credits, debits

    def _draw_bar(self):
        ax = self._figure.add_subplot(111)
        credits, debits = self._monthly_totals()
        x = range(12)
        width = 0.35
        ax.bar([i - width / 2 for i in x], credits, width, label="Credits",
               color="#4caf50", alpha=0.85)
        ax.bar([i + width / 2 for i in x], debits, width, label="Debits",
               color="#f44336", alpha=0.85)
        ax.set_xticks(list(x))
        ax.set_xticklabels(MONTHS_SHORT)
        ax.set_ylabel("Amount (€)")
        ax.set_title("Monthly Credits vs Debits")
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.5)

    def _draw_cumulative(self):
        ax = self._figure.add_subplot(111)
        credits, debits = self._monthly_totals()
        net = [c - d for c, d in zip(credits, debits)]
        cumulative = list(itertools.accumulate(net))
        colors = ["#4caf50" if v >= 0 else "#f44336" for v in cumulative]
        ax.plot(MONTHS_SHORT, cumulative, marker="o", color="#1565c0", linewidth=2)
        for i, (x, y) in enumerate(zip(MONTHS_SHORT, cumulative)):
            ax.fill_between([i], [0], [y], alpha=0.15, color=colors[i])
        ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_ylabel("Cumulative net (€)")
        ax.set_title("Cumulative Net Balance")
        ax.grid(linestyle="--", alpha=0.4)

    def _draw_pie(self):
        ax = self._figure.add_subplot(111)
        debit_items = [(li.label, li.total()) for li in self._line_items
                       if li.category == "Debit" and li.total() > 0]
        if not debit_items:
            ax.text(0.5, 0.5, "No debit data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=14)
            return
        labels, values = zip(*debit_items)
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%", startangle=90,
            pctdistance=0.8,
        )
        ax.set_title("Expense Breakdown")

    # ------------------------------------------------------------------

    def _save_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save chart as PNG", "", "PNG images (*.png)"
        )
        if path:
            self._figure.savefig(path, dpi=150, bbox_inches="tight")
