# desktop_web.py — Launcher okna WebView2 dla aplikacji Rejestr Usterek
import os
import sys
import io
import json
import time
import socket
import logging
import threading
from pathlib import Path

# ── High DPI awareness dla Windows (4K / 2K / FHD) ──
try:
    import ctypes
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Zabezpieczenie przed brakiem strumieni w pythonw.exe na Windows
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()


BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "desktop_web.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

CFG_FILE = BASE_DIR / "config.json"
DESKTOP_CFG = BASE_DIR / "desktop_config.json"
APP_TITLE = "Rejestr Usterek"

def _is_port_open(host: str, port: int) -> bool:
    """Sprawdza czy port jest otwarty i serwer nasłuchuje."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def _start_backend():
    """Uruchamia serwer Flask/Waitress w osobnym wątku."""
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    from app import app as flask_app, init_db, CFG
    
    init_db()
    port = CFG.get("PORT", 5000)
    
    def _run_server():
        try:
            try:
                from waitress import serve
                logging.info(f"Start serwera waitress na porcie {port}")
                serve(flask_app, host="127.0.0.1", port=port, threads=8, _quiet=True)
            except ImportError:
                logging.info(f"Start serwera flask na porcie {port}")
                flask_app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            logging.error(f"Błąd serwera backendu: {e}", exc_info=True)

    t = threading.Thread(target=_run_server, daemon=True, name="FlaskWebviewBackend")
    t.start()

    # Czekaj na start serwera (max 5 sekund)
    for _ in range(50):
        if _is_port_open("127.0.0.1", port):
            logging.info(f"Serwer gotowy na porcie {port}")
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
    try:
        logging.info("Start aplikacji desktop_web.py")
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

        logging.info(f"Target URL: {target_url}")

        try:
            import webview
        except ImportError as e:
            logging.error(f"Brak biblioteki pywebview: {e}")
            import webbrowser
            webbrowser.open(target_url)
            return

        window_w = 1440
        window_h = 900
        if "window_size" in cfg and isinstance(cfg["window_size"], list) and len(cfg["window_size"]) == 2:
            try:
                window_w = max(1024, int(cfg["window_size"][0]))
                window_h = max(640, int(cfg["window_size"][1]))
            except Exception:
                pass

        logging.info(f"Tworzenie okna webview: {window_w}x{window_h}")
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

        logging.info("Start webview.start()")
        # EdgeChromium jako domyślny silnik WebView2 na Windows
        webview.start(debug=("--debug" in sys.argv), gui="edgechromium")
        logging.info("Zamknięto okno webview")

    except Exception as ex:
        logging.error(f"Krytyczny błąd w main(): {ex}", exc_info=True)

if __name__ == "__main__":
    main()
