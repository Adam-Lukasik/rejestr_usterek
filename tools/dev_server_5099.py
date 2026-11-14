"""Serwer testowy asystenta na porcie 5099 (osobno od działającej aplikacji
na 5050) — pod tools/cdp_ui_check.js. Baza: RU_DATA_DIR albo domyślna.
Uruchamiać interpreterem z python-embed (ma Flaska)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import app as A  # noqa: E402

A.app.run(host='127.0.0.1', port=5099, debug=False, use_reloader=False, threaded=True)
