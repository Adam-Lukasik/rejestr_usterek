"""Headless entrypoint serwera Rejestru Usterek (Docker / QNAP Container Station).

Uruchamia Flask/Waitress bez okna WebView — do użycia na serwerze centralnym.
Klienci łączą się przeglądarką lub skompilowanym exe z --server=URL
(albo "server_url" w desktop_config.json).

Zmienne środowiskowe:
    RU_DATA_DIR  - katalog danych (db, Baza wiedzy, config)  [domyślnie ./data]
    RU_HOST      - adres bind [domyślnie z config.json, tam 0.0.0.0]
    RU_PORT      - port [domyślnie z config.json]
"""
import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("RU_DATA_DIR") or APP_DIR / "data").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Gdy brak data/config.json — kopiuj szablon serwerowy (HOST=0.0.0.0, PORT=5050).
# Bez tego app.py wziąłby domyślne 127.0.0.1:5000 i serwer byłby niedostępny z LAN.
_cfg = DATA_DIR / "config.json"
_tpl = APP_DIR / "config.docker.json"
if not _cfg.exists() and _tpl.exists():
    import shutil as _shutil
    _shutil.copy2(_tpl, _cfg)

os.environ["RU_SERVER"] = "1"
os.environ["RU_STATIC_DIR"] = str(APP_DIR)
os.environ["RU_DATA_DIR"] = str(DATA_DIR)
os.chdir(DATA_DIR)
sys.path.insert(0, str(APP_DIR))

from app import app as flask_app, init_db, CFG

init_db()
host = os.environ.get("RU_HOST") or CFG.get("HOST", "0.0.0.0")
port = int(os.environ.get("RU_PORT") or CFG.get("PORT", 5050))

from waitress import serve

print(f"[server] Rejestr Usterek nasluchuje na http://{host}:{port} (data={DATA_DIR})", flush=True)
serve(flask_app, host=host, port=port, threads=16, _quiet=True)
