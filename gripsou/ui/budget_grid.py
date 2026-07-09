"""Budget grid widget — editable QTableWidget with color coding, totals, undo/redo."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from gripsou.db.database import Database
from gripsou.db.models import LineItem

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Column indices
COL_LABEL = 0
COL_TAG = 1
COL_JAN = 2           # months: COL_JAN + (month-1)
COL_TOTAL = 14        # after 12 months

FIXED_COLS = 15       # label + tag + 12 months + total

# Colours
COLOR_CREDIT_BG = QColor("#e8f5e9")          # light green
COLOR_CREDIT_VALIDATED = QColor("#81c784")   # darker green
COLOR_DEBIT_BG = QColor("#ffebee")           # light red
COLOR_DEBIT_VALIDATED = QColor("#e57373")    # darker red
COLOR_DIRTY = QColor("#fff9c4")              # yellow
COLOR_POSITIVE = QColor("#1b5e20")           # dark green text
COLOR_NEGATIVE = QColor("#b71c1c")           # dark red text
COLOR_SUMMARY_BG = QColor("#e3f2fd")         # light blue footer
COLOR_HEADER_BG = QColor("#1565c0")
COLOR_HEADER_FG = QColor("#ffffff")


def _amount_item(value: float, editable: bool = True, dirty: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(f"{value:,.2f}")
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if dirty:
        item.setBackground(QBrush(COLOR_DIRTY))
    return item


def _color_by_sign(value: float) -> QColor:
    return COLOR_POSITIVE if value >= 0 else COLOR_NEGATIVE


class CellEditCommand(QUndoCommand):
    def __init__(self, grid: "BudgetGrid", row: int, col: int,
                 old_val: float, new_val: float, item_id: int, month: int):
        super().__init__(f"Edit [{row},{col}]")
        self._grid = grid
        self._row = row
        self._col = col
        self._old = old_val
        self._new = new_val
        self._item_id = item_id
        self._month = month

    def redo(self):
        self._apply(self._new)

    def undo(self):
        self._apply(self._old)

    def _apply(self, value: float):
        self._grid.db.set_monthly_value(self._item_id, self._month, value)
        self._grid._line_items[self._row].monthly_values[self._month] = value
        self._grid._refresh_row(self._row)
        self._grid._refresh_summary_rows()
        self._grid.data_changed.emit()


class BudgetGrid(QTableWidget):
    data_changed = pyqtSignal()   # emitted after any value commit

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._year_id: int | None = None
        self._line_items: list[LineItem] = []
        self._dirty_cells: set[tuple[int, int]] = set()
        # key: (line_item_id, month), value: True = validated
        self._validated: set[tuple[int, int]] = set()
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(20)
        self._programmatic = False   # guard against recursive itemChanged

        self._setup_table()
        self.itemChanged.connect(self._on_item_changed)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    def load_year(self, year_id: int):
        self._year_id = year_id
        self._load_data()

    def reload(self):
        if self._year_id is not None:
            self._load_data()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_table(self):
        self.setColumnCount(FIXED_COLS)
        headers = ["Line item", "Type"] + MONTHS + ["Total"]
        self.setHorizontalHeaderLabels(headers)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setMinimumSectionSize(50)
        self.setColumnWidth(COL_LABEL, 220)
        self.setColumnWidth(COL_TAG, 70)
        for c in range(COL_JAN, COL_TOTAL + 1):
            self.setColumnWidth(c, 85)
        hh.setStretchLastSection(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.SelectedClicked |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.setAlternatingRowColors(False)
        vh = self.verticalHeader()
        vh.setVisible(True)
        vh.setDefaultSectionSize(26)
        vh.setMinimumSectionSize(18)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self):
        self._programmatic = True
        self.clearContents()
        self._dirty_cells.clear()

        raw_items = self.db.get_line_items(self._year_id)
        summary = self.db.get_year_summary(self._year_id)
        self._validated = self.db.get_validated_cells(self._year_id)

        self._line_items = []
        for r in raw_items:
            li = LineItem(
                id=r["id"],
                year_id=r["year_id"],
                category=r["category"],
                label=r["label"],
                sort_order=r["sort_order"],
                monthly_values={m: summary.get(r["id"], {}).get(m, 0.0) for m in range(1, 13)},
            )
            self._line_items.append(li)

        n_data = len(self._line_items)
        self.setRowCount(n_data + 4)  # data rows + sep + credits total + debits total + net
        self._apply_row_resize_mode()

        for row, li in enumerate(self._line_items):
            self._populate_row(row, li)

        self._refresh_summary_rows()
        self._programmatic = False

    def _populate_row(self, row: int, li: LineItem):
        bg = COLOR_CREDIT_BG if li.category == "Credit" else COLOR_DEBIT_BG

        label_item = QTableWidgetItem(li.label)
        label_item.setBackground(QBrush(bg))
        self.setItem(row, COL_LABEL, label_item)

        tag_item = QTableWidgetItem(li.category)
        tag_item.setFlags(tag_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        tag_item.setBackground(QBrush(bg))
        tag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, COL_TAG, tag_item)

        for m in range(1, 13):
            col = COL_JAN + m - 1
            dirty = (row, col) in self._dirty_cells
            validated = (li.id, m) in self._validated
            item = _amount_item(li.monthly_values.get(m, 0.0),
                                editable=not validated, dirty=dirty)
            item.setBackground(QBrush(self._cell_bg(li.category, dirty, validated)))
            item.setData(Qt.ItemDataRole.UserRole, (li.id, m))
            self.setItem(row, col, item)

        self._refresh_row_total(row, li)

    def _cell_bg(self, category: str, dirty: bool, validated: bool) -> QColor:
        if validated:
            return COLOR_CREDIT_VALIDATED if category == "Credit" else COLOR_DEBIT_VALIDATED
        if dirty:
            return COLOR_DIRTY
        return COLOR_CREDIT_BG if category == "Credit" else COLOR_DEBIT_BG

    def _apply_cell_state(self, item, category: str, dirty: bool, validated: bool):
        item.setBackground(QBrush(self._cell_bg(category, dirty, validated)))
        if validated:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    def _refresh_row(self, row: int):
        if row >= len(self._line_items):
            return
        li = self._line_items[row]
        self._programmatic = True
        for m in range(1, 13):
            col = COL_JAN + m - 1
            item = self.item(row, col)
            if item:
                dirty = (row, col) in self._dirty_cells
                validated = (li.id, m) in self._validated
                item.setText(f"{li.monthly_values.get(m, 0.0):,.2f}")
                self._apply_cell_state(item, li.category, dirty, validated)
        self._refresh_row_total(row, li)
        self._programmatic = False

    def _refresh_row_total(self, row: int, li: LineItem):
        total = li.total()
        t_item = _amount_item(total, editable=False)
        t_item.setForeground(QBrush(_color_by_sign(total)))
        bold = QFont()
        bold.setBold(True)
        t_item.setFont(bold)
        bg = COLOR_CREDIT_BG if li.category == "Credit" else COLOR_DEBIT_BG
        t_item.setBackground(QBrush(bg))
        self.setItem(row, COL_TOTAL, t_item)

    def _refresh_summary_rows(self):
        n = len(self._line_items)
        sep_row = n
        credits_row = n + 1
        debits_row = n + 2
        net_row = n + 3

        if self.rowCount() < n + 4:
            self.setRowCount(n + 4)
            self._apply_row_resize_mode()

        bold = QFont()
        bold.setBold(True)

        def _summary_label(row: int, text: str):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setFont(bold)
            item.setBackground(QBrush(COLOR_SUMMARY_BG))
            self.setItem(row, COL_LABEL, item)
            tag = QTableWidgetItem("")
            tag.setFlags(tag.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tag.setBackground(QBrush(COLOR_SUMMARY_BG))
            self.setItem(row, COL_TAG, tag)

        credits = [li for li in self._line_items if li.category == "Credit"]
        debits = [li for li in self._line_items if li.category == "Debit"]

        # separator row
        for c in range(FIXED_COLS):
            sep = QTableWidgetItem("")
            sep.setFlags(sep.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(sep_row, c, sep)

        _summary_label(credits_row, "Total Credits")
        _summary_label(debits_row, "Total Debits")
        _summary_label(net_row, "Net Balance")

        total_credits_year = 0.0
        total_debits_year = 0.0

        for m in range(1, 13):
            col = COL_JAN + m - 1
            tc = sum(li.amount(m) for li in credits)
            td = sum(li.amount(m) for li in debits)
            net = tc - td
            total_credits_year += tc
            total_debits_year += td

            for row, value in [(credits_row, tc), (debits_row, td), (net_row, net)]:
                item = _amount_item(value, editable=False)
                item.setFont(bold)
                item.setForeground(QBrush(_color_by_sign(value)))
                item.setBackground(QBrush(COLOR_SUMMARY_BG))
                self.setItem(row, col, item)

        net_year = total_credits_year - total_debits_year

        for row, value in [
            (credits_row, total_credits_year),
            (debits_row, total_debits_year),
            (net_row, net_year),
        ]:
            item = _amount_item(value, editable=False)
            item.setFont(bold)
            item.setForeground(QBrush(_color_by_sign(value if row != debits_row else -value)))
            item.setBackground(QBrush(COLOR_SUMMARY_BG))
            self.setItem(row, COL_TOTAL, item)

    def _apply_row_resize_mode(self):
        vh = self.verticalHeader()
        vh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for r in range(self.rowCount()):
            vh.resizeSection(r, vh.defaultSectionSize())

    # ------------------------------------------------------------------
    # Validation toggle
    # ------------------------------------------------------------------

    def _on_cell_double_clicked(self, row: int, col: int):
        if row >= len(self._line_items):
            return
        if col < COL_JAN or col > COL_TOTAL - 1:
            return
        li = self._line_items[row]
        month = col - COL_JAN + 1
        key = (li.id, month)
        validated = key in self._validated
        # toggle
        validated = not validated
        if validated:
            self._validated.add(key)
        else:
            self._validated.discard(key)
        self.db.set_validated(li.id, month, validated)
        item = self.item(row, col)
        if item:
            dirty = (row, col) in self._dirty_cells
            self._programmatic = True
            self._apply_cell_state(item, li.category, dirty, validated)
            self._programmatic = False
        self.data_changed.emit()

    # ------------------------------------------------------------------
    # Edit handling
    # ------------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._programmatic:
            return
        col = item.column()
        row = item.row()
        if row >= len(self._line_items):
            return
        if col == COL_LABEL:
            self._handle_label_change(row, item.text())
            return
        if col < COL_JAN or col > COL_TOTAL - 1:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        item_id, month = data

        try:
            new_val = float(item.text().replace(",", "").replace(" ", ""))
        except ValueError:
            self._programmatic = True
            old = self._line_items[row].monthly_values.get(month, 0.0)
            item.setText(f"{old:,.2f}")
            self._programmatic = False
            return

        old_val = self._line_items[row].monthly_values.get(month, 0.0)
        if abs(new_val - old_val) < 1e-9:
            return

        cmd = CellEditCommand(self, row, col, old_val, new_val, item_id, month)
        self._undo_stack.push(cmd)
        self._dirty_cells.add((row, col))
        self._programmatic = True
        item.setBackground(QBrush(COLOR_DIRTY))
        self._programmatic = False

    def _handle_label_change(self, row: int, new_label: str):
        li = self._line_items[row]
        if new_label == li.label:
            return
        li.label = new_label
        self.db.rename_line_item(li.id, new_label)
        self.data_changed.emit()

    # ------------------------------------------------------------------
    # Row operations (called from MainWindow menus)
    # ------------------------------------------------------------------

    def add_row(self, category: str, label: str):
        if self._year_id is None:
            return
        sort_order = len(self._line_items)
        item_id = self.db.add_line_item(self._year_id, category, label, sort_order)
        for m in range(1, 13):
            self.db.set_monthly_value(item_id, m, 0.0)
        self._load_data()
        self.data_changed.emit()

    def delete_selected_row(self):
        rows = sorted({idx.row() for idx in self.selectedIndexes()})
        data_rows = [r for r in rows if r < len(self._line_items)]
        if not data_rows:
            return
        for r in reversed(data_rows):
            self.db.delete_line_item(self._line_items[r].id)
        self._load_data()
        self.data_changed.emit()

    def get_line_items(self) -> list[LineItem]:
        return list(self._line_items)
