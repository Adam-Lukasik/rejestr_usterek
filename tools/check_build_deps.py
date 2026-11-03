#!/usr/bin/env python3
# tools/check_build_deps.py — weryfikacja zależności przed kompilacją release.
#
# Sprawdza, że KAŻDA dystrybucja z requirements.txt jest zainstalowana
# w interpreterze builda (venv) i że jej moduł daje się zaimportować.
# Zabezpiecza przed „niepełnymi" paczkami: Nuitka po cichu pomija moduły,
# których nie ma w venv (import w try/except w kodzie nie wywali builda),
# a brak wychodzi dopiero u klienta (incydent: brak pypdf w paczce ≤2.2.0).
#
# Użycie: venv\Scripts\python.exe tools\check_build_deps.py
#         exit 0 = wszystko OK; exit 1 = lista braków na stdout.

import importlib.metadata as md
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQ = ROOT / "requirements.txt"

# dystrybucja -> moduł importowany (tylko gdy się różnią nazwą)
IMPORT_NAME = {
    "pillow": "PIL",
    "pywebview": "webview",
    "extract-msg": "extract_msg",
    "flask-cors": "flask_cors",
    "python-dotenv": "dotenv",
    "beautifulsoup4": "bs4",
    "pythonnet": "clr",
}


def main():
    missing, unimportable = [], []
    for raw in REQ.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        dist = re.split(r"[<>=!~;\[\s]", line)[0].strip()
        if not dist:
            continue
        try:
            md.version(dist)
        except md.PackageNotFoundError:
            missing.append(dist)
            continue
        imp = IMPORT_NAME.get(dist.lower(), dist.lower().replace("-", "_"))
        try:
            __import__(imp)
        except Exception as e:
            unimportable.append(f"{dist} (import {imp}: {e})")

    for d in missing:
        print(f"[DEPS] BRAK dystrybucji: {d}")
    for d in unimportable:
        print(f"[DEPS] NIEIMPORTOWALNE: {d}")
    if missing or unimportable:
        print("[DEPS] Uruchom: venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 1
    print("[DEPS] Wszystkie zależności z requirements.txt zainstalowane i importowalne.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
