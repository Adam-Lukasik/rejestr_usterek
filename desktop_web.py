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
    from ctypes import wintypes
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

# ── Zapobieganie wielokrotnemu uruchomieniu (Single Instance Mutex) ──
_MUTEX_HANDLE = None
try:
    ERROR_ALREADY_EXISTS = 183
    _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(None, wintypes.BOOL(True), "Local\\RejestrUsterek_App_Mutex")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # Program jest już uruchomiony - zakończ zdublowany proces
        sys.exit(0)
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

class SplashScreen:
    """Eleganckie okno ładowania (Splash Screen) wyświetlane natychmiast po uruchomieniu."""
    def __init__(self):
        self.root = None
        self.lbl_status = None
        try:
            import tkinter as tk
            from tkinter import ttk
            
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes('-topmost', True)
            root.configure(bg="#0F172A", cursor="watch")
            
            w, h = 420, 200
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            root.geometry(f"{w}x{h}+{x}+{y}")
            
            frame = tk.Frame(root, bg="#0F172A", highlightbackground="#3B82F6", highlightthickness=1, cursor="watch")
            frame.pack(fill="both", expand=True)
            
            lbl_title = tk.Label(frame, text="⚡ Rejestr Usterek", font=("Segoe UI", 16, "bold"), fg="#F8FAFC", bg="#0F172A")
            lbl_title.pack(pady=(26, 4))
            
            lbl_sub = tk.Label(frame, text="Panel Diagnostyki & Serwisu", font=("Segoe UI", 10), fg="#94A3B8", bg="#0F172A")
            lbl_sub.pack(pady=(0, 18))
            
            style = ttk.Style()
            style.theme_use('clam')
            style.configure("Custom.Horizontal.TProgressbar", foreground='#3B82F6', background='#3B82F6', troughcolor='#1E293B', bordercolor='#0F172A')
            
            progress = ttk.Progressbar(frame, style="Custom.Horizontal.TProgressbar", mode="indeterminate", length=320)
            progress.pack(pady=(0, 10))
            progress.start(15)
            
            self.lbl_status = tk.Label(frame, text="Trwa uruchamianie aplikacji...", font=("Segoe UI", 10), fg="#60A5FA", bg="#0F172A")
            self.lbl_status.pack()
            
            root.update()
            self.root = root
        except Exception as e:
            logging.warning(f"Nie udało się otworzyć SplashScreen: {e}")
            self.root = None

    def set_status(self, text):
        if self.root and self.lbl_status:
            try:
                self.lbl_status.config(text=text)
                self.root.update()
            except Exception:
                pass

    def update(self):
        if self.root:
            try:
                self.root.update()
            except Exception:
                pass

    def close(self):
        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

def _is_port_open(host: str, port: int) -> bool:
    """Sprawdza czy port jest otwarty i serwer nasłuchuje."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def _start_backend(splash=None):
    """Uruchamia serwer Flask/Waitress w osobnym wątku."""
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    from app import app as flask_app, init_db, CFG
    
    if splash:
        splash.set_status("Inicjalizacja serwera i bazy danych...")
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
        if splash:
            splash.update()
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

def _force_activate_app():
    """Wymusza pełny focus systemu Windows na oknie aplikacji."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        current_pid = kernel32.GetCurrentProcessId()
        found_hwnds = []
        
        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == current_pid:
                    found_hwnds.append(hwnd)
            return True
            
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(EnumWindowsProc(enum_cb), 0)
        
        for hwnd in found_hwnds:
            user32.AllowSetForegroundWindow(-1)
            cur_thread = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
            
            if fg_thread and cur_thread != fg_thread:
                user32.AttachThreadInput(cur_thread, fg_thread, True)
                user32.ShowWindow(hwnd, 5)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetActiveWindow(hwnd)
                user32.SetFocus(hwnd)
                user32.AttachThreadInput(cur_thread, fg_thread, False)
            else:
                user32.ShowWindow(hwnd, 5)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetActiveWindow(hwnd)
                user32.SetFocus(hwnd)
                
            user32.PostMessageW(hwnd, 0x0006, 1, 0)
            user32.PostMessageW(hwnd, 0x0007, 0, 0)
    except Exception as e:
        logging.warning(f"Błąd _force_activate_app: {e}")

def main():
    splash = SplashScreen()
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
            splash.set_status("Inicjalizacja serwera i bazy danych...")
            port = _start_backend(splash)
            target_url = f"http://127.0.0.1:{port}"
        else:
            target_url = server_url

        logging.info(f"Target URL: {target_url}")
        splash.set_status("Ładowanie silnika WebView2...")

        try:
            import webview
        except ImportError as e:
            logging.error(f"Brak biblioteki pywebview: {e}")
            splash.close()
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

        # Zamknij splash screen tuż przed uruchomieniem okna webview
        splash.close()

        # Ukryj ewentualne okno konsoli terminala
        try:
            hwnd_console = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd_console:
                ctypes.windll.user32.ShowWindow(hwnd_console, 0)
        except Exception:
            pass

        def on_started():
            def _delayed_focus_loop():
                for delay in (0.15, 0.4, 0.8, 1.5):
                    time.sleep(delay)
                    try:
                        window.focus()
                    except Exception:
                        pass
                    _force_activate_app()
            
            t = threading.Thread(target=_delayed_focus_loop, daemon=True, name="FocusActivator")
            t.start()

        logging.info("Start webview.start()")
        # EdgeChromium jako domyślny silnik WebView2 na Windows
        webview.start(on_started, debug=("--debug" in sys.argv), gui="edgechromium")
        logging.info("Zamknięto okno webview")

    except Exception as ex:
        logging.error(f"Krytyczny błąd w main(): {ex}", exc_info=True)
        if splash:
            splash.close()

if __name__ == "__main__":
    main()
