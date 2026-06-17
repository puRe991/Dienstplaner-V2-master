"""Build a Windows executable with PyInstaller.

Run on Windows from the repository root:
    py -3 -m pip install pyinstaller
    py -3 scripts/build_windows_pyinstaller.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "Dienstplaner"
REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = REPO_ROOT / "start_python_dienstplaner.py"
ICON_PATH = REPO_ROOT / "assets" / "dienstplaner.ico"
LICENSE_PATH = REPO_ROOT / "LICENSE"
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build" / "pyinstaller"


def _require_file(path: Path, description: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{description} nicht gefunden: {path}")


def main() -> int:
    _require_file(ENTRYPOINT, "Startskript")
    if not LICENSE_PATH.exists():
        print(
            f"WARNUNG: Keine LICENSE-Datei gefunden ({LICENSE_PATH}). "
            "Der Build wird ohne Lizenzdatei erstellt.",
            file=sys.stderr,
        )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
    ]
    if ICON_PATH.exists():
        command.extend(["--icon", str(ICON_PATH)])
    else:
        print(
            f"WARNUNG: Kein Icon gefunden ({ICON_PATH}). Lege dort eine .ico-Datei ab, "
            "um ein Windows-App-Icon einzubinden.",
            file=sys.stderr,
        )
    if LICENSE_PATH.exists():
        command.extend(["--add-data", f"{LICENSE_PATH}{os.pathsep}."])
    command.append(str(ENTRYPOINT))

    subprocess.run(command, cwd=REPO_ROOT, check=True)
    print(f"Build erstellt: {DIST_DIR / APP_NAME}")
    print("Datenbank/Backups liegen weiterhin außerhalb des Programmordners im konfigurierten Datenverzeichnis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
