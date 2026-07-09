"""Gripsou — Budget Manager entry point."""

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from gripsou.db.database import Database
from gripsou.ui.main_window import MainWindow


def _default_db_path() -> Path:
    if os.environ.get("GRIPSOU_DB"):
        return Path(os.environ["GRIPSOU_DB"])
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle
        exe_dir = Path(sys.executable).parent.resolve()
        if sys.platform == "darwin":
            # Store user data outside the .app bundle so it survives updates/moves
            support_dir = Path.home() / "Library" / "Application Support" / "Gripsou"
            support_dir.mkdir(parents=True, exist_ok=True)
            return support_dir / "gripsou.db"
        return exe_dir / "gripsou.db"
    return Path(__file__).parent / "gripsou.db"


DEFAULT_DB = _default_db_path()


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
