"""Gripsou — Budget Manager entry point."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gripsou.db.database import Database
from gripsou.ui.main_window import MainWindow

DEFAULT_DB = Path(__file__).parent / "gripsou.db"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gripsou")
    app.setOrganizationName("Gripsou")

    try:
        import qdarktheme
        qdarktheme.setup_theme("light")
    except ImportError:
        pass

    db = Database(DEFAULT_DB)
    db.connect()

    window = MainWindow(db)
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
