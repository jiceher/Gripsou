"""Database connection, schema creation and migrations."""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 2

_CREATE_YEARS = """
CREATE TABLE IF NOT EXISTS years (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE
);
"""

_CREATE_LINE_ITEMS = """
CREATE TABLE IF NOT EXISTS line_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    year_id    INTEGER NOT NULL REFERENCES years(id) ON DELETE CASCADE,
    category   TEXT NOT NULL CHECK(category IN ('Credit','Debit')),
    label      TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_MONTHLY_VALUES = """
CREATE TABLE IF NOT EXISTS monthly_values (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    line_item_id INTEGER NOT NULL REFERENCES line_items(id) ON DELETE CASCADE,
    month        INTEGER NOT NULL CHECK(month BETWEEN 1 AND 12),
    amount       REAL    NOT NULL DEFAULT 0.0,
    validated    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(line_item_id, month)
);
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self):
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    # ------------------------------------------------------------------
    # Schema init / migrations
    # ------------------------------------------------------------------

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            _CREATE_META
            + _CREATE_YEARS
            + _CREATE_LINE_ITEMS
            + _CREATE_MONTHLY_VALUES
        )
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='schema_version'")
        row = cur.fetchone()
        current = int(row["value"]) if row else 0
        if current < 2:
            try:
                cur.execute(
                    "ALTER TABLE monthly_values ADD COLUMN validated INTEGER NOT NULL DEFAULT 0"
                )
            except Exception:
                pass  # column already exists
        if current < SCHEMA_VERSION:
            cur.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)",
                (str(SCHEMA_VERSION),),
            )
            self.conn.commit()

    # ------------------------------------------------------------------
    # Year CRUD
    # ------------------------------------------------------------------

    def get_years(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, label FROM years ORDER BY label DESC"
        ).fetchall()

    def add_year(self, label: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO years(label) VALUES(?)", (label,)
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_year(self, year_id: int):
        self.conn.execute("DELETE FROM years WHERE id=?", (year_id,))
        self.conn.commit()

    def copy_year(self, src_year_id: int, new_label: str) -> int:
        new_id = self.add_year(new_label)
        items = self.get_line_items(src_year_id)
        for item in items:
            new_item_id = self.add_line_item(
                new_id, item["category"], item["label"], item["sort_order"]
            )
            src_vals = {v["month"]: v["amount"] for v in self.get_monthly_values(item["id"])}
            for m in range(1, 13):
                self.conn.execute(
                    "INSERT INTO monthly_values(line_item_id, month, amount, validated) "
                    "VALUES(?, ?, ?, 0)",
                    (new_item_id, m, src_vals.get(m, 0.0)),
                )
        self.conn.commit()
        return new_id

    # ------------------------------------------------------------------
    # LineItem CRUD
    # ------------------------------------------------------------------

    def get_line_items(self, year_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, year_id, category, label, sort_order "
            "FROM line_items WHERE year_id=? ORDER BY sort_order, id",
            (year_id,),
        ).fetchall()

    def add_line_item(
        self, year_id: int, category: str, label: str, sort_order: int = 0
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO line_items(year_id,category,label,sort_order) VALUES(?,?,?,?)",
            (year_id, category, label, sort_order),
        )
        self.conn.commit()
        return cur.lastrowid

    def rename_line_item(self, item_id: int, label: str):
        self.conn.execute(
            "UPDATE line_items SET label=? WHERE id=?", (label, item_id)
        )
        self.conn.commit()

    def delete_line_item(self, item_id: int):
        self.conn.execute("DELETE FROM line_items WHERE id=?", (item_id,))
        self.conn.commit()

    def reorder_line_items(self, ordered_ids: list[int]):
        for pos, item_id in enumerate(ordered_ids):
            self.conn.execute(
                "UPDATE line_items SET sort_order=? WHERE id=?", (pos, item_id)
            )
        self.conn.commit()

    # ------------------------------------------------------------------
    # MonthlyValue CRUD
    # ------------------------------------------------------------------

    def get_monthly_values(self, line_item_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT month, amount FROM monthly_values WHERE line_item_id=? ORDER BY month",
            (line_item_id,),
        ).fetchall()

    def get_all_monthly_values(self, year_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT mv.line_item_id, mv.month, mv.amount "
            "FROM monthly_values mv "
            "JOIN line_items li ON li.id=mv.line_item_id "
            "WHERE li.year_id=?",
            (year_id,),
        ).fetchall()

    def set_monthly_value(self, line_item_id: int, month: int, amount: float):
        self.conn.execute(
            "INSERT INTO monthly_values(line_item_id,month,amount) VALUES(?,?,?) "
            "ON CONFLICT(line_item_id,month) DO UPDATE SET amount=excluded.amount",
            (line_item_id, month, amount),
        )
        self.conn.commit()

    def set_validated(self, line_item_id: int, month: int, validated: bool):
        self.conn.execute(
            "INSERT INTO monthly_values(line_item_id,month,amount,validated) VALUES(?,?,0,?) "
            "ON CONFLICT(line_item_id,month) DO UPDATE SET validated=excluded.validated",
            (line_item_id, month, 1 if validated else 0),
        )
        self.conn.commit()

    def get_validated_cells(self, year_id: int) -> set[tuple[int, int]]:
        """Return set of (line_item_id, month) that are validated."""
        rows = self.conn.execute(
            "SELECT mv.line_item_id, mv.month "
            "FROM monthly_values mv "
            "JOIN line_items li ON li.id=mv.line_item_id "
            "WHERE li.year_id=? AND mv.validated=1",
            (year_id,),
        ).fetchall()
        return {(r["line_item_id"], r["month"]) for r in rows}

    def get_year_summary(self, year_id: int) -> dict:
        """Return {item_id: {month: amount}} for a full year."""
        rows = self.get_all_monthly_values(year_id)
        summary: dict[int, dict[int, float]] = {}
        for r in rows:
            summary.setdefault(r["line_item_id"], {})[r["month"]] = r["amount"]
        return summary
