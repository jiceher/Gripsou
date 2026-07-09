"""Build a standalone Gripsou executable/bundle with PyInstaller.

Usage:
    .venv\Scripts\python build.py          # Windows -> dist\Gripsou\
    .venv/bin/python build.py               # macOS   -> dist/Gripsou.app
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def pyinstaller_args() -> list[str]:
    system = platform.system()
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        "Gripsou",
        "--paths",
        str(ROOT),
        "--hidden-import",
        "PyQt6.sip",
        "--hidden-import",
        "matplotlib.backends.backend_qtagg",
        "--hidden-import",
        "openpyxl",
        "--hidden-import",
        "pyxlsb",
        str(ROOT / "main.py"),
    ]
    if system == "Darwin":
        args += ["--osx-bundle-identifier", "com.gripsou.budgetmanager"]
    return args


def main():
    dist = ROOT / "dist"
    build = ROOT / "build"
    if dist.exists():
        shutil.rmtree(dist)
    if build.exists():
        shutil.rmtree(build)

    subprocess.run(pyinstaller_args(), check=True, cwd=ROOT)

    system = platform.system()
    if system == "Windows":
        print(f"\nBuild complete: {dist / 'Gripsou' / 'Gripsou.exe'}")
    elif system == "Darwin":
        print(f"\nBuild complete: {dist / 'Gripsou.app'}")
    else:
        print(f"\nBuild complete: {dist}")


if __name__ == "__main__":
    main()
