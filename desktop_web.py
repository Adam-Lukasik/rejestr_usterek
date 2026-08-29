# desktop_web.py — Nowoczesny launcher okna WebView2 dla aplikacji Rejestr Usterek
# Uruchamia natywne, płynne okno z silnikiem Edge WebView2 (bez pasków przeglądarki)

import os
import sys
import json
import time
import socket
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CFG_FILE = BASE_DIR / "config.json"
DESKTOP_CFG = BASE_DIR / "desktop_config.json"

APP_TITLE = "Rejestr Usterek"

def _is_port_open(host: str, port: int) -> bool:
    """Sprawdza czy port jest otwarty i nasłuchuje."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def _start_backend():
    """Uruchamia lokalny serwer Flask w osobnym wątku."""
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    from app import app as flask_app, init_db, CFG
    
    init_db()
    port = CFG.get("PORT", 5000)
    
    def _run_server():
        try:
            # Użyj waitress jeśli dostępne (bardziej stabilne dla wątków), fallback do Flask
            try:
                from waitress import serve
                serve(flask_app, host="127.0.0.1", port=port, threads=8, _quiet=True)
            except ImportError:
                flask_app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"[BACKEND ERROR] {e}")

    t = threading.Thread(target=_run_server, daemon=True, name="FlaskWebviewBackend")
    t.start()

    # Poczekaj na start serwera (max 4 sekundy)
    for _ in range(40):
        if _is_port_open("127.0.0.1", port):
            break
        time.sleep(0.1)

    return port

def _load_desktop_config():
    if DESKTOP_CFG.exists():
        try:
            return json.loads(DESKTOP_CFG.read_text("utf-8"))
        except Exception:
            pass
    return {}

def _save_desktop_config(cfg):
    try:
        DESKTOP_CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass

def main():
    is_local_forced = "--local" in sys.argv
    server_url = ""

    if not is_local_forced:
        for idx, arg in enumerate(sys.argv[1:]):
            if arg.startswith("--server="):
                server_url = arg.split("=", 1)[1]
            elif arg == "--server" and idx + 2 <= len(sys.argv):
                server_url = sys.argv[idx + 2]
            elif arg.startswith("http://") or arg.startswith("https://"):
                server_url = arg

    cfg = _load_desktop_config()
    if not server_url and not is_local_forced:
        server_url = cfg.get("server_url", "").strip().rstrip("/")

    if is_local_forced or not server_url:
        port = _start_backend()
        target_url = f"http://127.0.0.1:{port}"
    else:
        target_url = server_url

    try:
        import webview
    except ImportError:
        print("Brak biblioteki pywebview. Zainstaluj ja poleceniem: pip install pywebview")
        # Fallback: otwarcie w przeglądarce
        import webbrowser
        webbrowser.open(target_url)
        print("Aplikacja zostala otwarta w przegladarce internetowej.")
        input("Nacisnij ENTER, aby zakonczyc...")
        return

    # Ustawienia okna
    window_w = 1440
    window_h = 900
    if "window_size" in cfg and isinstance(cfg["window_size"], list) and len(cfg["window_size"]) == 2:
        try:
            window_w = max(1024, int(cfg["window_size"][0]))
            window_h = max(640, int(cfg["window_size"][1]))
        except Exception:
            pass

    # Tworzenie nowoczesnego okna WebView2
    window = webview.create_window(
        title=APP_TITLE,
        url=target_url,
        width=window_w,
        height=window_h,
        min_size=(1024, 640),
        background_color="#0F172A",
        easy_drag=False,
        text_select=True,
        zoomable=True
    )

    def on_resized(width, height):
        cfg["window_size"] = [width, height]
        _save_desktop_config(cfg)

    window.events.resized += on_resized

    # Start pętli okna WebView2 (Edge Chromium na Windows)
    webview.start(debug=("--debug" in sys.argv), gui="edgechromium")

if __name__ == "__main__":
    main()
