# desktop.py  —  Rejestr Usterek, natywne okno Tkinter + ttkbootstrap
# UI v4.1 — obsługa wielu techników na 1 stanowisku, szybkie przełączanie, role, zdjęcia, dokumenty

import os, sys, json, sqlite3, threading, csv, base64, io
from pathlib import Path
from datetime import datetime
import uuid

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog

# ── High DPI awareness i dynamiczne skalowanie dla Windows (4K / 2K / FHD) ──
def _get_dpi_info():
    """Zwraca (dpi, scale_factor, tk_scaling) dla Windows / High DPI."""
    dpi = 96
    try:
        from ctypes import windll
        try:
            windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI aware
        except Exception:
            try:
                windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        if hasattr(windll.user32, 'GetDpiForSystem'):
            d = windll.user32.GetDpiForSystem()
            if d > 0: dpi = d
        else:
            hdc = windll.user32.GetDC(0)
            if hdc:
                d = windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                windll.user32.ReleaseDC(0, hdc)
                if d > 0: dpi = d
    except Exception:
        pass

    scale = max(1.0, dpi / 96.0)
    tk_scaling = dpi / 72.0
    return dpi, scale, tk_scaling

DPI, SCALE, TK_SCALING = _get_dpi_info()

def px(v):
    """Przelicza piksele bazowe (dla 96 DPI) na piksele dla aktualnej skali ekranu."""
    return int(round(v * SCALE))

try:
    import ttkbootstrap as ttk
    from ttkbootstrap import Window as _TkWindow
    _BOOT = True
except ImportError:
    from tkinter import ttk
    _TkWindow = None
    _BOOT = False


try:
    from PIL import Image, ImageTk, ImageGrab
    _PIL = True
except ImportError:
    _PIL = False

try:
    import pypdfium2 as pdfium
    _PDFIUM = True
except ImportError:
    _PDFIUM = False

import requests
import tempfile

# ═══════════════════════════════════════════════════════════════════
APP_TITLE = "Rejestr Usterek"
BASE_DIR  = Path(__file__).resolve().parent
CFG_FILE  = BASE_DIR / "desktop_config.json"
DB_PATH   = BASE_DIR / "rejestr_usterek.db"

GREEN = "#2E8B57"
RED   = "#D64545"
DIM   = "#5B6572"
NAVY  = "#1B2430"
AMBER = "#D97706"

def _get_theme_palette(is_dark=False):
    """Zwraca dopasowane kolory dla trybu jasnego i ciemnego (kontrast, czytelność, tagi)."""
    if is_dark:
        return {
            "dim": "#94A3B8",        # jasny szary do etykiet opisowych w dark mode
            "navy": "#93C5FD",       # jasny błękit dla nagłówka użytkownika
            "green": "#4ADE80",      # jasna czytelna zieleń (Status: Naprawiona)
            "open": "#F87171",       # jasny koral / wyrazista czerwień (Status: Otwarta w dark mode)
            "amber": "#F87171",      # kompatybilność
            "link": "#60A5FA",       # jasny błękit do linków/plików
        }
    else:
        return {
            "dim": "#5B6572",
            "navy": "#1B2430",
            "green": "#16A34A",      # wyrazista zieleń (Status: Naprawiona)
            "open": "#B91C1C",       # ciemna, szlachetna czerwień ostrzegawcza (Status: Otwarta)
            "amber": "#B91C1C",      # kompatybilność
            "link": "#1A6EC7",
        }

def _get_link_color():
    return "#60A5FA" if UI.get("theme") == "dark" else "#1A6EC7"
THUMB_SIZE = (px(300), px(225))          # rozmiar miniaturki w formularzu
PANEL_PREVIEW_SIZE = (px(580), px(360))  # bazowy rozmiar dopasowanego zdjęcia w panelu szczegółów

STATUS_PL = {"open": "Otwarta", "fixed": "Naprawiona"}
ROLE_PL   = {"admin": "Administrator", "technik": "Technik", "podglad": "Podgląd"}
_DEFAULT_CFG = {
    "theme": "light",
    "last_klient": "",
    "last_model": "",
    "last_projekt": "",
    "auth_token": "",
    "remember_user": True,
    "last_username": ""
}

# ── Spójna typografia w całej aplikacji ──
FONT_TITLE    = ("Segoe UI", 15, "bold")
FONT_SUBTITLE = ("Segoe UI", 13, "bold")
FONT_SECTION  = ("Segoe UI", 12, "bold")
FONT_LABEL    = ("Segoe UI", 11, "bold")
FONT_REGULAR  = ("Segoe UI", 11)
FONT_MUTED    = ("Segoe UI", 10)
FONT_SMALL    = ("Segoe UI", 9)

def _load_cfg():
    if CFG_FILE.exists():
        try: return json.loads(CFG_FILE.read_text("utf-8"))
        except Exception: pass
    return dict(_DEFAULT_CFG)

def _save_cfg(c):
    try: CFG_FILE.write_text(json.dumps(c, indent=2, ensure_ascii=False), "utf-8")
    except Exception: pass

UI = _load_cfg()

CURRENT_USER = {}
AUTH_TOKEN = ""

# ═══════════════════════════════════════════════════════════════════
# BACKEND
# ═══════════════════════════════════════════════════════════════════
_LOCAL_PORT = 5000
_BACKEND_STARTED = False

def _start_backend():
    global _LOCAL_PORT, _BACKEND_STARTED
    if _BACKEND_STARTED:
        return _LOCAL_PORT
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    from app import app as _flask, init_db, CFG
    init_db()
    port = CFG.get("PORT", 5000)
    _LOCAL_PORT = port
    def _run():
        _flask.run(host="127.0.0.1", port=port,
                   debug=False, use_reloader=False, threaded=True)
    t = threading.Thread(target=_run, daemon=True, name="FlaskBackend")
    t.start()
    _BACKEND_STARTED = True
    return port


# ═══════════════════════════════════════════════════════════════════
# REST-klient z obsługą autoryzacji
# ═══════════════════════════════════════════════════════════════════
class _Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.token = ""

    def set_token(self, token):
        self.token = token or ""

    def _headers(self):
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _url(self, p): return self.base + p

    def get(self, p):
        r = requests.get(self._url(p), headers=self._headers(), timeout=7)
        r.raise_for_status()
        return r.json()

    def post(self, p, d):
        r = requests.post(self._url(p), json=d, headers=self._headers(), timeout=7)
        r.raise_for_status()
        return r.json()

    def put(self, p, d):
        r = requests.put(self._url(p), json=d, headers=self._headers(), timeout=7)
        r.raise_for_status()
        return r.json()

    def patch(self, p, d):
        r = requests.patch(self._url(p), json=d, headers=self._headers(), timeout=7)
        r.raise_for_status()
        return r.json()

    def delete(self, p):
        r = requests.delete(self._url(p), headers=self._headers(), timeout=7)
        r.raise_for_status()
        return r.json()

API = None

# ═══════════════════════════════════════════════════════════════════
# NARZĘDZIA OBRAZÓW I DOKUMENTÓW
# ═══════════════════════════════════════════════════════════════════
def _optimize_image_bytes(raw_bytes: bytes, max_dim: int = 1920, quality: int = 85) -> bytes:
    """Automatycznie kompresuje i skaluje zdjęcie do max 1920px (JPEG 85%)."""
    if not _PIL or not raw_bytes:
        return raw_bytes
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if 'A' in img.getbands() else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        res = buf.getvalue()
        if len(res) < len(raw_bytes):
            return res
        return raw_bytes
    except Exception:
        return raw_bytes

def _make_thumb(data_bytes, size=THUMB_SIZE):
    """Zwraca PhotoImage miniaturki lub None gdy PIL niedostępny."""

    if not _PIL: return None
    try:
        img = Image.open(io.BytesIO(data_bytes))
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def _make_panel_preview(data_bytes, size=None):
    """Zwraca PhotoImage dopasowane do panelu szczegółów lub None gdy PIL niedostępny."""
    if not _PIL: return None
    if size is None:
        size = (px(580), px(360))
    try:
        img = Image.open(io.BytesIO(data_bytes))
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def _make_pdf_thumb(data_bytes, size=None):
    """Zwraca PhotoImage pierwszej strony PDF lub None gdy pypdfium2 niedostępny."""
    if not _PDFIUM or not _PIL: return None
    if size is None:
        size = (px(100), px(130))
    try:
        pdf = pdfium.PdfDocument(data_bytes)
        if len(pdf) == 0: return None
        page = pdf[0]
        img = page.render(scale=1.5).to_pil()
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

_TREE_FONT = None

def _get_tree_font():
    """Zwraca obiekt Font odpowiadający czcionce tabeli dla precyzyjnych pomiarów szerokości tekstu."""
    global _TREE_FONT
    if _TREE_FONT is None:
        try:
            from tkinter import font as tkfont
            _TREE_FONT = tkfont.Font(font=FONT_REGULAR)
        except Exception:
            try:
                from tkinter import font as tkfont
                _TREE_FONT = tkfont.nametofont("TkDefaultFont")
            except Exception:
                _TREE_FONT = None
    return _TREE_FONT

def _wrap_to_pixels(text, max_px, max_lines=3, font=None):
    """Zawija tekst do podanej liczby pikseli z podziałem na słowa, zachowaniem akapitów i limitem do max_lines wierszy."""
    if not text:
        return ""
    if not font:
        font = _get_tree_font()
    
    paragraphs = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = []
    
    for raw_p in paragraphs:
        p = " ".join(raw_p.split())
        if not p:
            if raw_p == "" and len(paragraphs) > 1 and len(lines) < max_lines:
                lines.append("")
            continue

        if not font or font.measure(p) <= max_px:
            lines.append(p)
            if len(lines) >= max_lines:
                break
            continue

        words = p.split(" ")
        curr = ""
        for i, w in enumerate(words):
            cand = f"{curr} {w}".strip() if curr else w
            if font.measure(cand) <= max_px:
                curr = cand
            else:
                if curr:
                    lines.append(curr)
                    if len(lines) == max_lines - 1:
                        rest = " ".join(words[i:])
                        while rest and font.measure(rest + "…") > max_px:
                            rest = rest[:-1]
                        lines.append((rest.rstrip() + "…") if rest != " ".join(words[i:]) else rest)
                        curr = ""
                        break
                    curr = w
                else:
                    part = w
                    while part and font.measure(part) > max_px:
                        part = part[:-1]
                    lines.append(part)
                    curr = w[len(part):]
                    if len(lines) >= max_lines:
                        break
        if curr and len(lines) < max_lines:
            lines.append(curr)
            
        if len(lines) >= max_lines:
            break

    return "\n".join(lines[:max_lines])

def _open_full(parent, photos_list, start_idx):
    """Otwiera pełne zdjęcia w zmaksymalizowanym oknie z nawigacją strzałkami i panelem."""
    if not _PIL:
        messagebox.showinfo(APP_TITLE,
            "Podgląd pełnego zdjęcia wymaga biblioteki Pillow.\n"
            "Zainstaluj: pip install pillow", parent=parent)
        return

    win = tk.Toplevel(parent)
    try:
        win.state("zoomed")
    except Exception:
        win.attributes("-zoomed", True)
        
    win.title("Podgląd zdjęcia — pełny ekran")
    win.configure(bg="#111111")
    win.grab_set()

    idx = [start_idx]
    current_pi = [None]
    rendered_size = [None]

    container = tk.Frame(win, bg="#111111")
    container.pack(fill="both", expand=True)

    lbl = tk.Label(container, bg="#111111")
    lbl.pack(fill="both", expand=True)

    def _show_current():
        p = photos_list[idx[0]]
        filename = p.get("filename", "")
        win.title(f"Podgląd zdjęcia [{idx[0]+1}/{len(photos_list)}]: {filename}")
        lbl_info.config(text=f"Zdjęcie {idx[0]+1} z {len(photos_list)}  —  {filename}")

        w = lbl.winfo_width()
        h = lbl.winfo_height()
        if w < 100 or h < 100:
            w = win.winfo_screenwidth()
            h = win.winfo_screenheight() - px(80)

        raw = p["bytes"]
        if (raw, w, h) == rendered_size[0] and current_pi[0] is not None:
            return

        try:
            orig = Image.open(io.BytesIO(raw))
            orig_w, orig_h = orig.size
            scale = min((w - 20) / orig_w, (h - 20) / orig_h, 1.0)
            target_w = max(1, int(orig_w * scale))
            target_h = max(1, int(orig_h * scale))

            res = orig.resize((target_w, target_h), Image.LANCZOS)
            pi = ImageTk.PhotoImage(res)
            current_pi[0] = pi
            rendered_size[0] = (raw, w, h)
            lbl.config(image=pi)
        except Exception:
            pass

    def _on_win_resize(event):
        if event.widget == win:
            win.after(100, _show_current)

    win.bind("<Configure>", _on_win_resize)

    def _prev_img(e=None):
        idx[0] = (idx[0] - 1) % len(photos_list)
        rendered_size[0] = None
        _show_current()

    def _next_img(e=None):
        idx[0] = (idx[0] + 1) % len(photos_list)
        rendered_size[0] = None
        _show_current()

    bot_bar = tk.Frame(win, bg="#1E1E1E", height=px(55))
    bot_bar.pack(fill="x", side="bottom")

    lbl_info = tk.Label(bot_bar, text="", font=("Segoe UI", 11), bg="#1E1E1E", fg="#CCCCCC")
    lbl_info.pack(side="left", padx=20, pady=10)

    hint = tk.Label(bot_bar, text="Nawigacja: ◄ Poprzednie / Następne ► | Zamknij: ESC lub [X]",
                    font=("Segoe UI", 9), bg="#1E1E1E", fg="#888888")
    hint.pack(side="right", padx=20, pady=10)

    nav_frame = tk.Frame(bot_bar, bg="#1E1E1E")
    nav_frame.pack(side="right", padx=10)

    btn_font = ("Segoe UI", 12, "bold")
    btn_bg   = "#2C3E50"
    btn_fg   = "white"
    btn_active = "#34495E"

    btn_prev = tk.Button(nav_frame, text=" 🡄 ", font=btn_font, bg=btn_bg, fg=btn_fg, 
                          activebackground=btn_active, activeforeground=btn_fg, relief="flat", 
                          command=_prev_img, cursor="hand2", padx=10, pady=5)
    btn_prev.pack(side="left", padx=5, pady=5)
    
    btn_close = tk.Button(nav_frame, text=" ✕ Zamknij ", font=("Segoe UI", 11), bg="#D64545", fg="white", 
                          activebackground="#E74C3C", activeforeground="white", relief="flat", 
                          command=win.destroy, cursor="hand2", padx=10, pady=5)
    btn_close.pack(side="left", padx=5, pady=5)
    
    btn_next = tk.Button(nav_frame, text=" 🡆 ", font=btn_font, bg=btn_bg, fg=btn_fg, 
                          activebackground=btn_active, activeforeground=btn_fg, relief="flat", 
                          command=_next_img, cursor="hand2", padx=10, pady=5)
    btn_next.pack(side="left", padx=5, pady=5)

    win.bind("<Right>", _next_img)
    win.bind("<Left>", _prev_img)
    win.bind("<Escape>", lambda _: win.destroy())
    lbl.bind("<Double-Button-1>", lambda _: win.destroy())

    _show_current()

ICON_EXT = {
    "pdf": "📄", "doc": "📝", "docx": "📝",
    "xls": "📊", "xlsx": "📊", "csv": "📊",
    "txt": "📋", "zip": "📦", "7z": "📦"
}

def _fmt_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024*1024: return f"{n/1024:.1f} KB"
    return f"{n/(1024*1024):.1f} MB"

def _open_document(raw_bytes: bytes, filename: str):
    """Zapisuje dokument do pliku tymczasowego i otwiera w domyślnym programie systemowym."""
    suffix = Path(filename).suffix or ".bin"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name
        os.startfile(tmp_path)
    except Exception as e:
        messagebox.showerror(APP_TITLE, f"Nie udało się otworzyć dokumentu:\n{e}")

# ═══════════════════════════════════════════════════════════════════
# DIALOGI LOGOWANIA, UŻYTKOWNIKÓW I NAPRAWY
# ═══════════════════════════════════════════════════════════════════

class _LoginDlg(tk.Toplevel):
    """Okno logowania do systemu."""
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.title("Logowanie — Rejestr Usterek")
        self._on_success = on_success
        pal = _get_theme_palette(UI.get("theme") == "dark")
        w, h = px(430), px(510)
        self.geometry(f"{w}x{h}")
        self.minsize(px(390), px(470))
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self.lift()
        self.focus_force()

        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Rejestr Usterek", font=FONT_TITLE).pack(pady=(0, 2))
        ttk.Label(frm, text="Zaloguj się, aby kontynuować", font=FONT_MUTED, foreground=pal["dim"]).pack(pady=(0, 16))

        ttk.Label(frm, text="Login:", font=FONT_LABEL).pack(anchor="w")
        self._user_var = tk.StringVar(value=UI.get("last_username", ""))
        self._user_entry = ttk.Entry(frm, textvariable=self._user_var, font=FONT_REGULAR)
        self._user_entry.pack(fill="x", pady=(2, 10))

        ttk.Label(frm, text="Hasło:", font=FONT_LABEL).pack(anchor="w")
        self._pw_var = tk.StringVar()
        self._pw_entry = ttk.Entry(frm, textvariable=self._pw_var, show="*", font=FONT_REGULAR)
        self._pw_entry.pack(fill="x", pady=(2, 8))

        self._remember_var = tk.BooleanVar(value=UI.get("remember_user", True))
        ttk.Checkbutton(frm, text="Zapamiętaj logowanie na tym komputerze",
                        variable=self._remember_var).pack(anchor="w", pady=(0, 14))

        self._btn_login = ttk.Button(frm, text="Zaloguj się", command=self._login)
        self._btn_login.pack(fill="x", pady=(0, 8))

        sub_frm = ttk.Frame(frm)
        sub_frm.pack(fill="x")
        btn_reset = ttk.Label(sub_frm, text="Nie pamiętam hasła", font=FONT_SMALL,
                              foreground=_get_link_color(), cursor="hand2")
        btn_reset.pack(side="left")
        btn_reset.bind("<Button-1>", lambda _: _ResetPasswordDlg(self))

        # Opcje połączenia z serwerem (QNAP / LAN / Lokalny) — zawsze otwarte
        curr_srv = UI.get("server_url", "")
        if not curr_srv and 'API' in globals() and getattr(API, 'base', '') and not API.base.startswith("http://127.0.0.1"):
            curr_srv = API.base
        self._server_var = tk.StringVar(value=curr_srv)

        srv_lf = ttk.LabelFrame(frm, text="⚙ Serwer sieciowy (QNAP / LAN)", padding=(12, 8))
        srv_lf.pack(fill="x", pady=(14, 0))

        ttk.Label(srv_lf, text="Adres URL (zostaw puste dla bazy lokalnej na tym komputerze):",
                  font=("Segoe UI", 8), foreground=pal["dim"]).pack(anchor="w", pady=(0, 3))
        self._server_entry = ttk.Entry(srv_lf, textvariable=self._server_var, font=FONT_REGULAR)
        self._server_entry.pack(fill="x")
        self._server_entry.bind("<Return>", lambda _: self._login())

        self._user_entry.bind("<Return>", lambda _: self._pw_entry.focus())
        self._pw_entry.bind("<Return>", lambda _: self._login())

        if self._user_var.get():
            self._pw_entry.focus()
        else:
            self._user_entry.focus()

        self._user_entry.bind("<Return>", lambda _: self._pw_entry.focus())
        self._pw_entry.bind("<Return>", lambda _: self._login())

        if self._user_var.get():
            self._pw_entry.focus()
        else:
            self._user_entry.focus()

    def _login(self):
        global API
        u = self._user_var.get().strip()
        p = self._pw_var.get()
        if not u or not p:
            messagebox.showwarning(self.title(), "Wprowadź login i hasło.", parent=self)
            return

        srv = self._server_var.get().strip().rstrip("/")
        if srv:
            if API is None:
                API = _Api(srv)
            else:
                API.base = srv
            UI["server_url"] = srv
        else:
            port = _start_backend()
            local_url = f"http://127.0.0.1:{port}"
            if API is None:
                API = _Api(local_url)
            else:
                API.base = local_url
            UI["server_url"] = ""

        try:
            resp = API.post("/api/auth/login", {"username": u, "password": p})
            token = resp.get("token")
            user  = resp.get("user")
            API.set_token(token)

            UI["last_username"] = u
            UI["remember_user"] = self._remember_var.get()
            if self._remember_var.get():
                UI["auth_token"] = token
            else:
                UI["auth_token"] = ""
            _save_cfg(UI)

            self.destroy()
            self._on_success(user, token)
        except Exception as e:
            err_msg = "Nieprawidłowy login lub hasło lub brak połączenia z serwerem."
            try:
                if hasattr(e, 'response') and e.response is not None:
                    err_msg = e.response.json().get("error", err_msg)
            except Exception:
                pass
            srv_name = API.base if API is not None else (srv or "Lokalny")
            messagebox.showerror(self.title(), f"{err_msg}\n(Serwer: {srv_name})", parent=self)

    def _on_close(self):
        self.destroy()
        if not CURRENT_USER:
            self.master.destroy()
            sys.exit(0)


class _QuickSwitchUserDlg(tk.Toplevel):
    """Szybkie przełączanie aktywnego technika na współdzielonym laptopie."""
    def __init__(self, parent, users_list, on_switch):
        super().__init__(parent)
        self.title("Szybkie przełączenie technika")
        self.geometry(f"{px(380)}x{px(260)}")
        self.minsize(px(340), px(220))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Wybierz pracującego technika", font=FONT_SECTION).pack(anchor="w", pady=(0, 4))
        ttk.Label(frm,
                  text="Ustawia aktualną osobę jako domyślnego autora nowych zgłoszeń i zatwierdzanych napraw na tym stanowisku.",
                  font=FONT_MUTED, foreground=DIM, wraplength=px(320)).pack(anchor="w", pady=(0, 10))

        ttk.Label(frm, text="Technik / Użytkownik:", font=FONT_LABEL).pack(anchor="w", pady=(2, 2))
        self._user_var = tk.StringVar()
        user_names = [u.get("full_name") or u.get("username") for u in users_list if u.get("full_name") or u.get("username")]
        
        self._cb = ttk.Combobox(frm, textvariable=self._user_var, values=user_names, state="readonly")
        self._cb.pack(fill="x", pady=(0, 14))
        curr_name = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or ""
        if curr_name in user_names:
            self._user_var.set(curr_name)
        elif user_names:
            self._user_var.set(user_names[0])

        ttk.Button(frm, text="Ustaw jako aktywnego", command=lambda: self._apply(users_list, on_switch)).pack(fill="x")

    def _apply(self, users_list, on_switch):
        selected_name = self._user_var.get()
        user_obj = next((u for u in users_list if (u.get("full_name") or u.get("username")) == selected_name), None)
        if user_obj:
            on_switch(user_obj)
            self.destroy()


class _MarkFixedDlg(tk.Toplevel):
    """Okno oznaczania usterki jako naprawionej z wyborem technika i opisem naprawy."""
    def __init__(self, parent, record, users_list, on_success):
        super().__init__(parent)
        self.title("Oznacz jako naprawioną")
        self.geometry(f"{px(560)}x{px(520)}")
        self.minsize(px(480), px(440))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._record = record
        self._on_success = on_success

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Potwierdzenie i szczegóły usunięcia usterki", font=FONT_SECTION).pack(anchor="w", pady=(0, 6))

        info_box = ttk.Labelframe(frm, text="Identyfikacja usterki", padding=8)
        info_box.pack(fill="x", pady=(0, 10))
        summary = f"{record.get('klient','')} | {record.get('model','')} | Projekt: {record.get('projekt','—')}\nTyp: {record.get('typ','')}  |  Element: {record.get('element','—')}"
        ttk.Label(info_box, text=summary, font=FONT_MUTED, foreground=DIM).pack(anchor="w")
        prob = record.get("opisProblem","")
        if len(prob) > 120: prob = prob[:117] + "…"
        ttk.Label(info_box, text=f"Problem: {prob}", font=FONT_REGULAR, wraplength=px(480)).pack(anchor="w", pady=(2,0))

        ttk.Label(frm, text="Kto dokonał naprawy? *", font=FONT_LABEL).pack(anchor="w", pady=(4, 2))
        self._tech_var = tk.StringVar()
        user_names = [u.get("full_name") or u.get("username") for u in users_list if u.get("full_name") or u.get("username")]
        curr_name = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or ""
        if curr_name and curr_name not in user_names:
            user_names.insert(0, curr_name)

        self._tech_cb = ttk.Combobox(frm, textvariable=self._tech_var, values=user_names, state="normal")
        self._tech_cb.pack(fill="x", pady=(0, 8))
        self._tech_var.set(curr_name or (user_names[0] if user_names else ""))

        ttk.Label(frm, text="Opis wykonanej naprawy / Przyczyna usterki:", font=FONT_LABEL).pack(anchor="w", pady=(4, 2))
        self._fix_txt = tk.Text(frm, height=5, wrap="word", font=FONT_REGULAR)
        self._fix_txt.pack(fill="both", expand=True, pady=(0, 12))
        if record.get("opisNaprawa"):
            self._fix_txt.insert("1.0", record.get("opisNaprawa"))

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="✓ Zatwierdź naprawę", command=self._submit).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Anuluj", command=self.destroy).pack(side="left")

    def _submit(self):
        tech = self._tech_var.get().strip()
        if not tech:
            messagebox.showwarning(self.title(), "Wybierz lub wpisz osobę, która wykonała naprawę.", parent=self); return
        fix_desc = self._fix_txt.get("1.0", "end").strip()

        try:
            now_str = datetime.now().isoformat(timespec="seconds")
            rec_copy = dict(self._record)
            rec_copy["opisNaprawa"] = fix_desc
            rec_copy["status"] = "fixed"
            rec_copy["fixed_by"] = tech
            rec_copy["fixed_at"] = now_str
            API.put(f"/api/records/{self._record['id']}", rec_copy)

            self.destroy()
            if self._on_success: self._on_success()
        except Exception as e:
            messagebox.showerror(self.title(), f"Błąd zapisu naprawy:\n{e}", parent=self)


class _ChangePasswordDlg(tk.Toplevel):
    """Zmiana własnego hasła przez zalogowanego użytkownika."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Zmiana hasła")
        self.geometry(f"{px(400)}x{px(360)}")
        self.minsize(px(360), px(320))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Aktualne hasło:", font=FONT_LABEL).pack(anchor="w")
        self._old_pw = tk.StringVar()
        self._old_entry = ttk.Entry(frm, textvariable=self._old_pw, show="*", font=FONT_REGULAR)
        self._old_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Nowe hasło (min. 4 znaki):", font=FONT_LABEL).pack(anchor="w")
        self._new_pw = tk.StringVar()
        self._new_entry = ttk.Entry(frm, textvariable=self._new_pw, show="*", font=FONT_REGULAR)
        self._new_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Powtórz nowe hasło:", font=FONT_LABEL).pack(anchor="w")
        self._rep_pw = tk.StringVar()
        self._rep_entry = ttk.Entry(frm, textvariable=self._rep_pw, show="*", font=FONT_REGULAR)
        self._rep_entry.pack(fill="x", pady=(2, 14))

        self._old_entry.bind("<Return>", lambda _: self._new_entry.focus())
        self._new_entry.bind("<Return>", lambda _: self._rep_entry.focus())
        self._rep_entry.bind("<Return>", lambda _: self._save())

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", side="bottom")
        ttk.Button(btn_row, text="✓ Zmień hasło", command=self._save).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(btn_row, text="Anuluj", command=self.destroy).pack(side="right")

    def _save(self):
        old_p = self._old_pw.get()
        new_p = self._new_pw.get()
        rep_p = self._rep_pw.get()

        if not old_p or not new_p:
            messagebox.showwarning(self.title(), "Wypełnij wszystkie pola.", parent=self); return
        if new_p != rep_p:
            messagebox.showwarning(self.title(), "Nowe hasła nie są identyczne.", parent=self); return
        if len(new_p) < 4:
            messagebox.showwarning(self.title(), "Nowe hasło musi mieć co najmniej 4 znaki.", parent=self); return

        try:
            API.post("/api/auth/change-password", {"old_password": old_p, "new_password": new_p})
            messagebox.showinfo(self.title(), "Hasło zostało pomyślnie zmienione.", parent=self)
            self.destroy()
        except Exception as e:
            err = "Błąd zmiany hasła."
            try: err = e.response.json().get("error", err)
            except Exception: pass
            messagebox.showerror(self.title(), err, parent=self)


class _ResetPasswordDlg(tk.Toplevel):
    """Reset hasła (kod e-mail lub kontakt z adminem)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Resetowanie hasła")
        self.geometry(f"{px(440)}x{px(440)}")
        self.minsize(px(400), px(380))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._frm = ttk.Frame(self, padding=16)
        self._frm.pack(fill="both", expand=True)

        self._step1()

    def _step1(self):
        for w in self._frm.winfo_children(): w.destroy()

        ttk.Label(self._frm, text="Odzyskiwanie dostępu do konta", font=FONT_SECTION).pack(anchor="w", pady=(0, 8))
        ttk.Label(self._frm,
                  text="Podaj swój login lub adres e-mail zarejestrowany w systemie.\n"
                       "Jeśli Twój profil posiada skonfigurowany e-mail, otrzymasz kod PIN.",
                  font=FONT_REGULAR, wraplength=px(380), justify="left").pack(anchor="w", pady=(0, 12))

        ttk.Label(self._frm, text="Login lub E-mail:", font=FONT_LABEL).pack(anchor="w")
        self._ident_var = tk.StringVar()
        e = ttk.Entry(self._frm, textvariable=self._ident_var, font=FONT_REGULAR)
        e.pack(fill="x", pady=(2, 12))
        e.bind("<Return>", lambda _: self._request_code())

        ttk.Button(self._frm, text="Wyślij kod weryfikacyjny", command=self._request_code).pack(fill="x", pady=(0, 10))

        tip_box = ttk.Labelframe(self._frm, text="Wskazówka warsztatowa", padding=10)
        tip_box.pack(fill="x", pady=(8, 0))
        ttk.Label(tip_box,
                  text="Jeśli nie masz podanego adresu e-mail, podejdź do Administratora (np. lidera zmiany) — może on w 5 sekund nadać Ci nowe hasło w panelu użytkowników.",
                  font=FONT_SMALL, foreground=DIM, wraplength=px(360), justify="left").pack(anchor="w")

    def _request_code(self):
        ident = self._ident_var.get().strip()
        if not ident:
            messagebox.showwarning(self.title(), "Wpisz login lub e-mail.", parent=self); return

        try:
            resp = API.post("/api/auth/request-reset", {"identifier": ident})
            if resp.get("email_sent"):
                messagebox.showinfo(self.title(), "Kod weryfikacyjny został wysłany na Twój e-mail.", parent=self)
                self._step2()
            else:
                msg = resp.get("message", "Nie można wysłać e-mail.")
                messagebox.showinfo(self.title(),
                    f"{msg}\n\nSkontaktuj się z Administratorem, aby zresetować hasło jednym kliknięciem.", parent=self)
        except Exception as e:
            messagebox.showerror(self.title(), f"Błąd: {e}", parent=self)

    def _step2(self):
        for w in self._frm.winfo_children(): w.destroy()

        ttk.Label(self._frm, text="Wpisz kod i nowe hasło", font=FONT_SECTION).pack(anchor="w", pady=(0, 10))

        ttk.Label(self._frm, text="6-cyfrowy kod z e-maila:", font=FONT_LABEL).pack(anchor="w")
        self._code_var = tk.StringVar()
        code_e = ttk.Entry(self._frm, textvariable=self._code_var, font=FONT_REGULAR)
        code_e.pack(fill="x", pady=(2, 8))

        ttk.Label(self._frm, text="Nowe hasło:", font=FONT_LABEL).pack(anchor="w")
        self._new_pw = tk.StringVar()
        pw_e = ttk.Entry(self._frm, textvariable=self._new_pw, show="*", font=FONT_REGULAR)
        pw_e.pack(fill="x", pady=(2, 8))

        ttk.Label(self._frm, text="Powtórz nowe hasło:", font=FONT_LABEL).pack(anchor="w")
class _UserManagementDlg(tk.Toplevel):
    """Panel zarządzania użytkownikami dla Administratora."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Zarządzanie Użytkownikami")
        self.geometry(f"{px(880)}x{px(520)}")
        self.minsize(px(700), px(400))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._users = []

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        top_row = ttk.Frame(frm)
        top_row.pack(fill="x", pady=(0, 8))
        ttk.Label(top_row, text="Konta użytkowników i uprawnienia", font=FONT_SECTION).pack(side="left")
        ttk.Button(top_row, text="＋ Dodaj użytkownika", command=self._add_user).pack(side="right")

        cols = ("login", "name", "role", "email", "status", "created")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", selectmode="browse")
        hdrs = {
            "login": "Login", "name": "Imię i Nazwisko", "role": "Rola",
            "email": "E-mail", "status": "Status", "created": "Data utworzenia"
        }
        wids = {"login": 100, "name": 160, "role": 110, "email": 170, "status": 80, "created": 120}
        for c in cols:
            self._tree.heading(c, text=hdrs[c])
            self._tree.column(c, width=px(wids[c]), anchor="w")

        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<Double-1>", lambda _: self._edit_user())

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_row, text="✎ Edytuj dane", command=self._edit_user).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🔑 Resetuj hasło", command=self._reset_pw).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="🔄 Aktywuj / Dezaktywuj", command=self._toggle_active).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="✕ Usuń konto", command=self._delete_user).pack(side="left")
        ttk.Button(btn_row, text="Zamknij", command=self.destroy).pack(side="right")

        self._refresh()

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        try:
            self._users = API.get("/api/users")
            for u in self._users:
                role_pl = ROLE_PL.get(u.get("role"), u.get("role"))
                status_pl = "Aktywny" if u.get("is_active") else "Nieaktywny"
                created_dt = u.get("created_at", "")[:16].replace("T", " ")
                self._tree.insert("", "end", iid=u["id"], values=(
                    u.get("username", ""),
                    u.get("full_name", ""),
                    role_pl,
                    u.get("email") or "—",
                    status_pl,
                    created_dt
                ))
        except Exception as e:
            messagebox.showerror(self.title(), f"Błąd wczytywania użytkowników:\n{e}", parent=self)

    def _selected(self):
        sel = self._tree.selection()
        if not sel: return None
        return next((u for u in self._users if u["id"] == sel[0]), None)

    def _add_user(self):
        _UserEditDlg(self, mode="add", on_save=self._refresh)

    def _edit_user(self):
        u = self._selected()
        if not u:
            messagebox.showinfo(self.title(), "Zaznacz użytkownika na liście.", parent=self); return
        _UserEditDlg(self, mode="edit", user=u, on_save=self._refresh)

    def _reset_pw(self):
        u = self._selected()
        if not u:
            messagebox.showinfo(self.title(), "Zaznacz użytkownika.", parent=self); return
        new_p = simpledialog.askstring(
            self.title(),
            f"Wprowadź nowe hasło dla pracownika:\n{u.get('full_name')} ({u.get('username')})",
            parent=self
        )
        if not new_p or not new_p.strip(): return
        if len(new_p.strip()) < 4:
            messagebox.showwarning(self.title(), "Hasło musi mieć co najmniej 4 znaki.", parent=self); return
        try:
            API.post(f"/api/users/{u['id']}/reset-password", {"new_password": new_p.strip()})
            messagebox.showinfo(self.title(), f"Hasło dla użytkownika {u['username']} zostało zmienione.", parent=self)
        except Exception as e:
            messagebox.showerror(self.title(), f"Błąd: {e}", parent=self)

    def _toggle_active(self):
        u = self._selected()
        if not u:
            messagebox.showinfo(self.title(), "Zaznacz użytkownika.", parent=self); return
        new_active = not bool(u.get("is_active"))
        try:
            API.put(f"/api/users/{u['id']}", {
                "username": u["username"],
                "full_name": u["full_name"],
                "email": u["email"] or "",
                "role": u["role"],
                "is_active": new_active
            })
            self._refresh()
        except Exception as e:
            err = "Błąd zmiany statusu."
            try: err = e.response.json().get("error", err)
            except Exception: pass
            messagebox.showerror(self.title(), err, parent=self)

    def _delete_user(self):
        u = self._selected()
        if not u:
            messagebox.showinfo(self.title(), "Zaznacz użytkownika.", parent=self); return
        if not messagebox.askyesno(self.title(),
                f"Czy na pewno chcesz usunąć konto użytkownika:\n{u['full_name']} ({u['username']})?", parent=self):
            return
        try:
            API.delete(f"/api/users/{u['id']}")
            self._refresh()
        except Exception as e:
            err = "Nie udało się usunąć użytkownika."
            try: err = e.response.json().get("error", err)
            except Exception: pass
            messagebox.showerror(self.title(), err, parent=self)


class _UserEditDlg(tk.Toplevel):
    """Okno dodawania/edycji użytkownika."""
    def __init__(self, parent, mode="add", user=None, on_save=None):
        super().__init__(parent)
        self._mode = mode
        self._user = user or {}
        self._on_save = on_save
        self.title("Nowy użytkownik" if mode == "add" else f"Edycja: {self._user.get('username')}")
        w, h = (px(450), px(540)) if mode == "add" else (px(450), px(490))
        self.geometry(f"{w}x{h}")
        self.minsize(px(380), px(440) if mode == "add" else px(400))
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        content_frm = ttk.Frame(frm)
        content_frm.pack(fill="both", expand=True)

        ttk.Label(content_frm, text="Login (unikalny):", font=FONT_LABEL).pack(anchor="w")
        self._login_var = tk.StringVar(value=self._user.get("username", ""))
        self._login_entry = ttk.Entry(content_frm, textvariable=self._login_var, font=FONT_REGULAR)
        self._login_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(content_frm, text="Imię i Nazwisko:", font=FONT_LABEL).pack(anchor="w")
        self._name_var = tk.StringVar(value=self._user.get("full_name", ""))
        self._name_entry = ttk.Entry(content_frm, textvariable=self._name_var, font=FONT_REGULAR)
        self._name_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(content_frm, text="Adres E-mail (opcjonalny):", font=FONT_LABEL).pack(anchor="w")
        self._email_var = tk.StringVar(value=self._user.get("email", ""))
        self._email_entry = ttk.Entry(content_frm, textvariable=self._email_var, font=FONT_REGULAR)
        self._email_entry.pack(fill="x", pady=(2, 8))

        ttk.Label(content_frm, text="Rola:", font=FONT_LABEL).pack(anchor="w")
        self._role_var = tk.StringVar(value=ROLE_PL.get(self._user.get("role", "technik"), "Technik"))
        role_cb = ttk.Combobox(content_frm, textvariable=self._role_var, state="readonly",
                               values=["Technik", "Administrator", "Podgląd"])
        role_cb.pack(fill="x", pady=(2, 8))

        ttk.Label(content_frm, text="Status konta:", font=FONT_LABEL).pack(anchor="w")
        is_act = self._user.get("is_active", 1) if mode == "edit" else 1
        self._status_var = tk.StringVar(value="Aktywny" if is_act else "Nieaktywny")
        status_cb = ttk.Combobox(content_frm, textvariable=self._status_var, state="readonly",
                                 values=["Aktywny", "Nieaktywny"])
        status_cb.pack(fill="x", pady=(2, 8))

        if mode == "add":
            ttk.Label(content_frm, text="Początkowe hasło (min. 4 znaki):", font=FONT_LABEL).pack(anchor="w")
            self._pw_var = tk.StringVar()
            self._pw_entry = ttk.Entry(content_frm, textvariable=self._pw_var, show="*", font=FONT_REGULAR)
            self._pw_entry.pack(fill="x", pady=(2, 10))
            self._pw_entry.bind("<Return>", lambda _: self._save())
        else:
            self._pw_var = None

        self._login_entry.bind("<Return>", lambda _: self._name_entry.focus())
        self._name_entry.bind("<Return>", lambda _: self._email_entry.focus())
        self._email_entry.bind("<Return>", lambda _: (self._pw_entry.focus() if mode == "add" else self._save()))

        btn_box = ttk.Frame(frm)
        btn_box.pack(fill="x", pady=(10, 0), side="bottom")

        if mode == "edit":
            btn_del = ttk.Button(btn_box, text="✕ Usuń", command=self._delete_self)
            btn_del.pack(side="left", padx=(0, 6))

        btn_save = ttk.Button(btn_box, text="✓ Zapisz użytkownika" if mode == "add" else "✓ Zapisz zmiany",
                              command=self._save)
        btn_save.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_cancel = ttk.Button(btn_box, text="Anuluj", command=self.destroy)
        btn_cancel.pack(side="right")

        self._login_entry.focus()

    def _delete_self(self):
        login = self._user.get("username", "")
        name = self._user.get("full_name", "")
        if not messagebox.askyesno(self.title(),
                f"Czy na pewno chcesz usunąć konto użytkownika:\n{name} ({login})?", parent=self):
            return
        try:
            API.delete(f"/api/users/{self._user['id']}")
            if self._on_save: self._on_save()
            self.destroy()
        except Exception as e:
            err = "Nie udało się usunąć użytkownika."
            try: err = e.response.json().get("error", err)
            except Exception: pass
            messagebox.showerror(self.title(), err, parent=self)

    def _save(self):
        login = self._login_var.get().strip()
        name  = self._name_var.get().strip()
        email = self._email_var.get().strip()
        role_map = {"Technik": "technik", "Administrator": "admin", "Podgląd": "podglad"}
        role = role_map.get(self._role_var.get(), "technik")
        is_active = 1 if self._status_var.get() == "Aktywny" else 0

        if not login or not name:
            messagebox.showwarning(self.title(), "Uzupełnij Login oraz Imię i Nazwisko.", parent=self); return

        try:
            if self._mode == "add":
                pw = self._pw_var.get() if self._pw_var else ""
                if not pw or len(pw) < 4:
                    messagebox.showwarning(self.title(), "Hasło musi mieć co najmniej 4 znaki.", parent=self); return
                API.post("/api/users", {
                    "username": login,
                    "full_name": name,
                    "email": email,
                    "role": role,
                    "is_active": is_active,
                    "password": pw
                })
            else:
                API.put(f"/api/users/{self._user['id']}", {
                    "username": login,
                    "full_name": name,
                    "email": email,
                    "role": role,
                    "is_active": is_active
                })
            if self._on_save: self._on_save()
            self.destroy()
        except Exception as e:
            err = "Błąd zapisu użytkownika."
            try: err = e.response.json().get("error", err)
            except Exception: pass
            messagebox.showerror(self.title(), err, parent=self)

# ═══════════════════════════════════════════════════════════════════
# DIALOGI ZARZĄDZANIA LISTAMI
# ═══════════════════════════════════════════════════════════════════
class _ListDlg(tk.Toplevel):
    def __init__(self, parent, title, items, on_save):
        super().__init__(parent)
        self.title(title); self.geometry(f"{px(400)}x{px(480)}")
        self.minsize(px(340), px(380))
        self.resizable(True, True); self.transient(parent); self.grab_set()
        self._items = sorted(items, key=str.casefold); self._on_save = on_save
        frm = ttk.Frame(self, padding=12); frm.pack(fill="both", expand=True)
        self._lb = tk.Listbox(frm, font=FONT_REGULAR, activestyle="dotbox")
        self._lb.pack(fill="both", expand=True); self._refresh()
        row = ttk.Frame(frm); row.pack(fill="x", pady=(8,4))
        self._var = tk.StringVar()
        e = ttk.Entry(row, textvariable=self._var)
        e.pack(side="left", fill="x", expand=True, padx=(0,6))
        e.bind("<Return>", lambda _: self._add())
        ttk.Button(row, text="Dodaj", command=self._add).pack(side="left")
        brow = ttk.Frame(frm); brow.pack(fill="x", pady=(0,8))
        ttk.Button(brow, text="Zmień", command=self._rename).pack(side="left", padx=(0,6))
        ttk.Button(brow, text="Usuń",  command=self._delete).pack(side="left")
        ttk.Button(frm, text="Zapisz i zamknij", command=self._save).pack(fill="x")
    def _refresh(self):
        self._lb.delete(0, tk.END)
        for v in self._items: self._lb.insert(tk.END, v)
    def _sel(self):
        s = self._lb.curselection(); return s[0] if s else None
    def _add(self):
        v = self._var.get().strip()
        if not v: return
        if v in self._items: messagebox.showwarning(self.title(),"Taka pozycja już istnieje.",parent=self); return
        self._items.append(v); self._items.sort(key=str.casefold); self._var.set(""); self._refresh()
    def _rename(self):
        i = self._sel()
        if i is None: messagebox.showwarning(self.title(),"Zaznacz pozycję.",parent=self); return
        new = simpledialog.askstring(self.title(),"Nowa nazwa:",initialvalue=self._items[i],parent=self)
        if new and new.strip() and new.strip()!=self._items[i]:
            self._items[i]=new.strip(); self._items.sort(key=str.casefold); self._refresh()
    def _delete(self):
        i = self._sel()
        if i is None: messagebox.showwarning(self.title(),"Zaznacz pozycję.",parent=self); return
        if messagebox.askyesno(self.title(),f'Usunąć "{self._items[i]}"?',parent=self):
            del self._items[i]; self._refresh()
    def _save(self):
        self._on_save(self._items); self.destroy()

class _ProjDlg(tk.Toplevel):
    def __init__(self, parent, klienci, proj_by_klient, on_save):
        super().__init__(parent)
        self.title("Projekty"); self.geometry(f"{px(460)}x{px(520)}")
        self.minsize(px(380), px(420))
        self.resizable(True, True); self.transient(parent); self.grab_set()
        self._data = {k: list(v) for k, v in proj_by_klient.items()}
        self._on_save = on_save
        frm = ttk.Frame(self, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Klient", font=FONT_LABEL).pack(anchor="w")
        self._kv = tk.StringVar()
        self._kcb = ttk.Combobox(frm, textvariable=self._kv, values=klienci, state="readonly")
        self._kcb.pack(fill="x", pady=(2,10))
        if klienci: self._kcb.set(klienci[0])
        self._kcb.bind("<<ComboboxSelected>>", lambda _: self._refresh())
        self._lb = tk.Listbox(frm, font=FONT_REGULAR, activestyle="dotbox")
        self._lb.pack(fill="both", expand=True); self._refresh()
        row = ttk.Frame(frm); row.pack(fill="x", pady=(8,4))
        self._var = tk.StringVar()
        e = ttk.Entry(row, textvariable=self._var)
        e.pack(side="left", fill="x", expand=True, padx=(0,6))
        e.bind("<Return>", lambda _: self._add())
        ttk.Button(row, text="Dodaj", command=self._add).pack(side="left")
        brow = ttk.Frame(frm); brow.pack(fill="x", pady=(0,8))
        ttk.Button(brow, text="Zmień", command=self._rename).pack(side="left", padx=(0,6))
        ttk.Button(brow, text="Usuń",  command=self._delete).pack(side="left")
        ttk.Button(frm, text="Zapisz i zamknij", command=self._save).pack(fill="x")
    def _k(self): return self._kv.get()
    def _refresh(self):
        self._lb.delete(0, tk.END)
        for v in self._data.get(self._k(),[]): self._lb.insert(tk.END, v)
    def _sel(self):
        s = self._lb.curselection(); return s[0] if s else None
    def _add(self):
        k=self._k()
        if not k: messagebox.showwarning(self.title(),"Wybierz klienta.",parent=self); return
        v=self._var.get().strip()
        if not v: return
        arr=self._data.setdefault(k,[])
        if v in arr: messagebox.showwarning(self.title(),"Taki projekt już istnieje.",parent=self); return
        arr.append(v); self._var.set(""); self._refresh()
    def _rename(self):
        k=self._k(); i=self._sel()
        if i is None: messagebox.showwarning(self.title(),"Zaznacz projekt.",parent=self); return
        new=simpledialog.askstring(self.title(),"Nowa nazwa:",initialvalue=self._data[k][i],parent=self)
        if new and new.strip(): self._data[k][i]=new.strip(); self._refresh()
    def _delete(self):
        k=self._k(); i=self._sel()
        if i is None: messagebox.showwarning(self.title(),"Zaznacz projekt.",parent=self); return
        if messagebox.askyesno(self.title(),f'Usunąć "{self._data[k][i]}"?',parent=self):
            del self._data[k][i]; self._refresh()
    def _save(self):
        self._on_save(self._data)
        self.destroy()

# ═══════════════════════════════════════════════════════════════════
# WIDGET GALERII ZDJĘĆ
# ═══════════════════════════════════════════════════════════════════
class PhotoGallery(ttk.Frame):
    MAX = 6

    def __init__(self, parent, mode="panel", **kw):
        super().__init__(parent, **kw)
        assert mode in ("panel", "form")
        self._mode        = mode
        self._record_id   = None
        self._photos: list[dict] = []
        self._current_idx = 0
        self._thumb_refs  = []
        self._last_preview_w = 0
        self._readonly = (mode == "panel")

        self._hdr = ttk.Frame(self)
        self._hdr.pack(fill="x")

        if self._mode == "form":
            ttk.Label(self._hdr, text="Zdjęcia", font=FONT_LABEL,
                      foreground=DIM).pack(side="left")
            self._paste_btn = ttk.Button(self._hdr, text="📋 Wklej", width=8,
                                         command=self._paste_image)
            self._paste_btn.pack(side="right", padx=(0, 4))
            self._add_btn = ttk.Button(self._hdr, text="＋ Dodaj", width=8,
                                       command=self._pick_file)
            self._add_btn.pack(side="right")
        else:
            self._paste_btn = None
            self._add_btn = None
            self._title_lbl = ttk.Label(self._hdr, text="Zdjęcia", font=FONT_LABEL,
                                        foreground=DIM)
            self._title_lbl.pack(side="left")
            self._nav_frame = ttk.Frame(self._hdr)
            self._nav_frame.pack(side="right")
            self._prev_btn = ttk.Button(self._nav_frame, text="◀ Poprzednie",
                                        command=self._show_prev)
            self._counter_lbl = ttk.Label(self._nav_frame, text="", font=FONT_MUTED,
                                          foreground=DIM)
            self._next_btn = ttk.Button(self._nav_frame, text="Następne ▶",
                                        command=self._show_next)

        if not _PIL:
            ttk.Label(self, text="(Pillow niedostępny — zainstaluj: pip install pillow)",
                      font=("Segoe UI", 7), foreground=RED).pack(anchor="w")

        self._body_frame = ttk.Frame(self)
        self._body_frame.pack(fill="x", pady=(4, 0))

        if self._mode == "panel":
            self.bind("<Configure>", self._on_panel_resize)

        self._refresh_ui()

    def set_readonly(self, readonly=True):
        self._readonly = readonly
        if self._mode == "form":
            if readonly:
                self._paste_btn.pack_forget()
                self._add_btn.pack_forget()
            else:
                self._add_btn.pack(side="right")
                self._paste_btn.pack(side="right", padx=(0, 4))
        self._refresh_ui()

    def _on_panel_resize(self, event):
        if self._mode != "panel" or not self._photos: return
        w = event.width
        if abs(w - self._last_preview_w) > px(50):
            self._last_preview_w = w
            self._refresh_ui()

    def load_for_record(self, record_id: str | None, force: bool = False):
        if self._record_id == record_id and not force:
            return
        self._record_id = record_id
        self._photos = []
        self._current_idx = 0
        if not record_id:
            self._refresh_ui(); return
        try:
            metas = API.get(f"/api/records/{record_id}/photos")
            for m in metas:
                resp = API.get(f"/api/photos/{m['id']}")
                raw  = base64.b64decode(resp["data"])
                self._photos.append({
                    "id": m["id"], "filename": m["filename"],
                    "bytes": raw, "thumb": _make_thumb(raw)
                })
        except Exception:
            pass
        self._refresh_ui()

    def get_pending(self) -> list[dict]:
        return [{"filename": p["filename"], "bytes": p["bytes"]}
                for p in self._photos if p.get("id") is None]

    def clear(self):
        self._record_id = None
        self._photos = []
        self._current_idx = 0
        self._refresh_ui()

    def _show_prev(self):
        if not self._photos: return
        self._current_idx = (self._current_idx - 1) % len(self._photos)
        self._refresh_ui()

    def _show_next(self):
        if not self._photos: return
        self._current_idx = (self._current_idx + 1) % len(self._photos)
        self._refresh_ui()

    def _pick_file(self):
        if len(self._photos) >= self.MAX:
            messagebox.showwarning(APP_TITLE, f"Maksymalnie {self.MAX} zdjęć na usterkę."); return
        path = filedialog.askopenfilename(
            title="Wybierz zdjęcie",
            filetypes=[("Obrazy","*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                       ("Wszystkie","*.*")])
        if not path: return
        raw = Path(path).read_bytes()
        raw = _optimize_image_bytes(raw)
        entry = {"id": None, "filename": Path(path).name,
                 "bytes": raw, "thumb": _make_thumb(raw)}
        self._photos.append(entry)
        if self._mode == "panel" and self._record_id:
            self._upload_one(entry)
        self._refresh_ui()

    def _paste_image(self):
        if len(self._photos) >= self.MAX:
            messagebox.showwarning(APP_TITLE, f"Maksymalnie {self.MAX} zdjęć na usterkę."); return
        if not _PIL:
            messagebox.showwarning(APP_TITLE, "Wklejanie wymaga biblioteki Pillow.\nZainstaluj: pip install pillow"); return
        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Błąd odczytu schowka:\n{e}"); return
        if img is None:
            messagebox.showinfo(APP_TITLE,
                "Schowek nie zawiera obrazu.\n"
                "Skopiuj zdjęcie (PrintScreen lub Ctrl+C w przeglądarce) i spróbuj ponownie.")
            return
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=85, optimize=True)
        raw = buf.getvalue()
        raw = _optimize_image_bytes(raw)
        filename = f"wklejone_{datetime.now().strftime('%H%M%S')}.jpg"
        entry = {"id": None, "filename": filename, "bytes": raw, "thumb": _make_thumb(raw)}
        self._photos.append(entry)
        if self._mode == "panel" and self._record_id:
            self._upload_one(entry)
        self._refresh_ui()

    def _upload_one(self, entry: dict):
        try:
            resp = API.post(f"/api/records/{self._record_id}/photos", {
                "filename": entry["filename"],
                "data": base64.b64encode(entry["bytes"]).decode()
            })
            entry["id"] = resp.get("id")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Nie udało się zapisać zdjęcia:\n{e}")

    def _delete_photo(self, idx: int):
        p = self._photos[idx]
        if not messagebox.askyesno(APP_TITLE, "Usunąć to zdjęcie?"): return
        if p.get("id"):
            try: API.delete(f"/api/photos/{p['id']}")
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Błąd usuwania zdjęcia:\n{e}"); return
        del self._photos[idx]
        if self._current_idx >= len(self._photos):
            self._current_idx = max(0, len(self._photos) - 1)
        self._refresh_ui()

    def _refresh_ui(self):
        for w in self._body_frame.winfo_children(): w.destroy()
        self._thumb_refs.clear()

        if self._mode == "form":
            self._refresh_form_ui()
        else:
            self._refresh_panel_ui()

    def _refresh_form_ui(self):
        pal = _get_theme_palette(UI.get("theme") == "dark")
        if not self._photos:
            ttk.Label(self._body_frame, text="Brak zdjęć (maksymalnie 6)",
                      font=FONT_MUTED, foreground=pal["dim"]).pack(anchor="w", pady=4)
            return
        row = ttk.Frame(self._body_frame)
        row.pack(fill="x", pady=2)
        for idx, p in enumerate(self._photos):
            card = ttk.Frame(row, padding=2)
            card.pack(side="left", padx=(0, px(8)))
            if p["thumb"]:
                self._thumb_refs.append(p["thumb"])
                lbl = tk.Label(card, image=p["thumb"], relief="groove", bd=1, cursor="hand2")
                lbl.pack()
                lbl.bind("<Button-1>", lambda e, i=idx: _open_full(self.winfo_toplevel(), self._photos, i))
            else:
                lbl = ttk.Label(card, text=f"📷 {p['filename'][:15]}",
                                font=FONT_REGULAR, foreground=_get_link_color(), cursor="hand2")
                lbl.pack()
                lbl.bind("<Button-1>", lambda e, i=idx: _open_full(self.winfo_toplevel(), self._photos, i))

            if not self._readonly:
                ttk.Button(card, text="✕ Usuń", width=8,
                           command=lambda i=idx: self._delete_photo(i)).pack(pady=(2,0))

    def _refresh_panel_ui(self):
        pal = _get_theme_palette(UI.get("theme") == "dark")
        n = len(self._photos)
        if n == 0:
            self._nav_frame.pack_forget()
            ttk.Label(self._body_frame, text="Brak zdjęć",
                      font=FONT_MUTED, foreground=pal["dim"]).pack(anchor="w", pady=4)
            return

        self._nav_frame.pack(side="right")
        self._counter_lbl.config(text=f" {self._current_idx + 1} / {n} ", foreground=pal["dim"])
        for w in (self._prev_btn, self._counter_lbl, self._next_btn): w.pack_forget()
        if n > 1:
            self._prev_btn.pack(side="left", padx=(0, 2))
            self._counter_lbl.pack(side="left", padx=2)
            self._next_btn.pack(side="left", padx=(2, 0))
        else:
            self._counter_lbl.pack(side="left")

        p = self._photos[self._current_idx]
        card = ttk.Frame(self._body_frame)
        card.pack(fill="x", anchor="w")

        w_avail = self.winfo_width()
        if w_avail > px(150):
            target_w = max(px(250), w_avail - px(20))
            target_h = int(target_w * 0.62)
            dyn_size = (target_w, target_h)
        else:
            dyn_size = PANEL_PREVIEW_SIZE

        preview_img = _make_panel_preview(p["bytes"], size=dyn_size)
        if preview_img:
            self._thumb_refs.append(preview_img)
            lbl = tk.Label(card, image=preview_img, relief="flat", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e: _open_full(self.winfo_toplevel(), self._photos, self._current_idx))
            lbl.bind("<Double-Button-1>", lambda e: _open_full(self.winfo_toplevel(), self._photos, self._current_idx))

        fn_row = ttk.Frame(card)
        fn_row.pack(fill="x", pady=(2, 0))
        fn_lbl = ttk.Label(fn_row, text=f"🔍 {p['filename']} (kliknij, aby powiększyć)",
                           font=FONT_MUTED, foreground=_get_link_color(), cursor="hand2")
        fn_lbl.pack(side="left")
        fn_lbl.bind("<Button-1>", lambda e: _open_full(self.winfo_toplevel(), self._photos, self._current_idx))

        if not self._readonly:
            del_btn = ttk.Button(fn_row, text="✕ Usuń", width=6,
                                 command=lambda: self._delete_photo(self._current_idx))
            del_btn.pack(side="right", padx=(8, 0))


# ═══════════════════════════════════════════════════════════════════
# WIDGET DOKUMENTÓW (PDF, RAPORTY VSWR, HVAC)
# ═══════════════════════════════════════════════════════════════════
class DocGallery(ttk.Frame):
    def __init__(self, parent, mode="panel", **kw):
        super().__init__(parent, **kw)
        assert mode in ("panel", "form")
        self._mode      = mode
        self._record_id = None
        self._docs: list[dict] = []
        self._thumb_refs = []
        self._readonly = (mode == "panel")

        self._hdr = ttk.Frame(self)
        self._hdr.pack(fill="x")
        self._title_lbl = ttk.Label(self._hdr, text="Dokumenty / Załączniki", font=FONT_LABEL,
                                    foreground=_get_theme_palette(UI.get("theme") == "dark")["dim"])
        self._title_lbl.pack(side="left")

        if self._mode == "form":
            self._add_btn = ttk.Button(self._hdr, text="＋ Dodaj plik", width=12,
                                       command=self._pick_file)
            self._add_btn.pack(side="right")
        else:
            self._add_btn = None

        self._list_frame = ttk.Frame(self)
        self._list_frame.pack(fill="x", pady=(4, 0))

        self._refresh_ui()

    def set_readonly(self, readonly=True):
        self._readonly = readonly
        if self._mode == "form":
            if readonly:
                self._add_btn.pack_forget()
            else:
                self._add_btn.pack(side="right")
        self._refresh_ui()

    def load_for_record(self, record_id: str | None, force: bool = False):
        if self._record_id == record_id and not force:
            return
        self._record_id = record_id
        self._docs = []
        if not record_id:
            self._refresh_ui(); return
        try:
            metas = API.get(f"/api/records/{record_id}/documents")
            for m in metas:
                entry = {"id": m["id"], "filename": m["filename"],
                         "filesize": m["filesize"], "bytes": None, "thumb": None}
                if m["filename"].lower().endswith(".pdf"):
                    try:
                        resp = API.get(f"/api/documents/{m['id']}")
                        raw  = base64.b64decode(resp["data"])
                        entry["bytes"] = raw
                        entry["thumb"] = _make_pdf_thumb(raw, size=(px(100), px(130)))
                    except Exception:
                        pass
                self._docs.append(entry)
        except Exception:
            pass
        self._refresh_ui()

    def get_pending(self):
        return [{"filename": d["filename"], "bytes": d["bytes"]}
                for d in self._docs if d.get("id") is None]

    def clear(self):
        self._record_id = None
        self._docs = []
        self._refresh_ui()

    def _pick_file(self):
        paths = filedialog.askopenfilenames(
            title="Wybierz dokumenty",
            filetypes=[("PDF","*.pdf"),("Word","*.doc *.docx"),
                       ("Excel","*.xls *.xlsx"),("Tekstowe","*.txt *.csv"),
                       ("Wszystkie","*.*")])
        if not paths: return
        for path in paths:
            raw = Path(path).read_bytes()
            fn  = Path(path).name
            thumb = _make_pdf_thumb(raw, size=(px(100), px(130))) if fn.lower().endswith(".pdf") else None
            entry = {"id": None, "filename": fn,
                     "filesize": len(raw), "bytes": raw, "thumb": thumb}
            self._docs.append(entry)
            if self._mode == "panel" and self._record_id:
                self._upload_one(entry)
        self._refresh_ui()

    def _upload_one(self, entry):
        try:
            resp = API.post(f"/api/records/{self._record_id}/documents", {
                "filename": entry["filename"],
                "data": base64.b64encode(entry["bytes"]).decode()
            })
            entry["id"] = resp.get("id")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Nie udało się zapisać dokumentu:\n{e}")

    def _open_doc(self, idx):
        d = self._docs[idx]
        if d.get("bytes"):
            _open_document(d["bytes"], d["filename"]); return
        try:
            resp = API.get(f"/api/documents/{d['id']}")
            raw  = base64.b64decode(resp["data"])
            d["bytes"] = raw
            _open_document(raw, d["filename"])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Nie udało się otworzyć:\n{e}")

    def _delete_doc(self, idx):
        d = self._docs[idx]
        if not messagebox.askyesno(APP_TITLE,
                f'Usunąć dokument „{d["filename"]}"?'): return
        if d.get("id"):
            try: API.delete(f"/api/documents/{d['id']}")
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Błąd usuwania:\n{e}"); return
        del self._docs[idx]
        self._refresh_ui()

    def _refresh_ui(self):
        pal = _get_theme_palette(UI.get("theme") == "dark")
        if hasattr(self, '_title_lbl'):
            self._title_lbl.configure(foreground=pal["dim"])

        for w in self._list_frame.winfo_children(): w.destroy()
        self._thumb_refs.clear()

        if not self._docs:
            ttk.Label(self._list_frame, text="Brak dokumentów",
                      font=FONT_MUTED, foreground=pal["dim"]).pack(anchor="w", pady=2)
            return

        pdf_docs = [d for d in self._docs if d.get("thumb")]
        other_docs = [d for d in self._docs if not d.get("thumb")]

        if pdf_docs:
            cards = ttk.Frame(self._list_frame)
            cards.pack(fill="x", pady=(2, 6))
            for idx, d in enumerate(self._docs):
                if not d.get("thumb"): continue
                self._thumb_refs.append(d["thumb"])
                card = ttk.Frame(cards, padding=2)
                card.pack(side="left", padx=(0, px(12)), anchor="nw")

                btn = tk.Button(card, image=d["thumb"], relief="flat", bd=1,
                                cursor="hand2", command=lambda i=idx: self._open_doc(i))
                btn.pack(anchor="center", pady=(0, 2))

                name = d["filename"]
                if len(name) > 20: name = name[:17] + "…"
                lbl = ttk.Label(card, text=f"📄 {name}", font=FONT_REGULAR,
                                cursor="hand2", foreground=_get_link_color())
                lbl.pack(anchor="center")
                lbl.bind("<Button-1>", lambda e, i=idx: self._open_doc(i))
                ttk.Label(card, text=_fmt_size(d.get("filesize", 0)),
                          font=FONT_MUTED, foreground=pal["dim"]).pack(anchor="center")

                if not self._readonly:
                    ttk.Button(card, text="✕ Usuń", width=8,
                               command=lambda i=idx: self._delete_doc(i)).pack(anchor="center", pady=(2, 0))

        if other_docs:
            for idx, d in enumerate(self._docs):
                if d.get("thumb"): continue
                ext  = d["filename"].rsplit(".", 1)[-1].lower() if "." in d["filename"] else ""
                icon = ICON_EXT.get(ext, "📎")
                row  = ttk.Frame(self._list_frame)
                row.pack(fill="x", pady=2)
                lbl = ttk.Label(row, text=f"{icon} {d['filename']}",
                                font=FONT_REGULAR, cursor="hand2", foreground=_get_link_color())
                lbl.pack(side="left")
                lbl.bind("<Button-1>", lambda e, i=idx: self._open_doc(i))
                ttk.Label(row, text=f"  {_fmt_size(d.get('filesize', 0))}",
                          font=FONT_MUTED, foreground=pal["dim"]).pack(side="left")
                if not self._readonly:
                    ttk.Button(row, text="✕", width=3,
                               command=lambda i=idx: self._delete_doc(i)).pack(side="right")

# ═══════════════════════════════════════════════════════════════════
# GŁÓWNE OKNO APLIKACJI
# ═══════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root, on_logout=None):
        self.root = root
        self.root.title(APP_TITLE)
        self._on_logout = on_logout
        self._records  = []
        self._lists    = {}
        self._users_list = []
        self._edit_id  = None
        self._form_mode = "new"
        self._sort_col = "data"
        self._sort_rev = True
        self._tree_style = ttk.Style()
        self._last_tree_w = 0
        self._last_prob_w = 0
        self._resize_job = None

        self._dim_labels = []
        self._build()
        self._apply_theme()
        self._reload()
        self._poll()

        self.root.after(60, self._render)
        self.root.after(200, self._render)

    # ── budowa UI ─────────────────────────────────────────────────
    def _build(self):
        root = self.root

        # GÓRNY PASEK
        top = ttk.Frame(root, padding=(14, 8))
        top.pack(fill="x")

        # Lewa strona nagłówka
        lbox = ttk.Frame(top)
        lbox.pack(side="left")
        ttk.Label(lbox, text=APP_TITLE, font=FONT_TITLE).pack(anchor="w")

        conn_row = ttk.Frame(lbox)
        conn_row.pack(anchor="w")
        self._conn_var = tk.StringVar(value="● Połączono")
        self._conn_lbl = ttk.Label(conn_row, textvariable=self._conn_var,
                                   font=FONT_MUTED, foreground=GREEN)
        self._conn_lbl.pack(side="left", padx=(0, 12))

        # Informacja o zalogowanym użytkowniku + przycisk szybkiego przełączania
        self._user_badge_var = tk.StringVar()
        self._update_user_badge_text()
        self._user_badge = ttk.Label(conn_row, textvariable=self._user_badge_var,
                                     font=FONT_LABEL, foreground=NAVY if UI.get("theme")!="dark" else "#79b8ff")
        self._user_badge.pack(side="left")

        # Przycisk szybkiego przełączania technika na wspólnym laptopie
        self._switch_btn = ttk.Button(conn_row, text="🔄 Przełącz technika", width=17,
                                      command=self._open_quick_switch)
        self._switch_btn.pack(side="left", padx=(10, 0))

        # Prawa strona nagłówka
        rbox = ttk.Frame(top)
        rbox.pack(side="right")

        if CURRENT_USER.get("role") == "admin":
            ttk.Button(rbox, text="👥 Użytkownicy", command=self._open_user_management).pack(side="left", padx=3)

        ttk.Button(rbox, text="🔑 Zmień hasło", command=self._open_change_pw).pack(side="left", padx=3)

        if CURRENT_USER.get("role") != "podglad":
            ttk.Button(rbox, text="Zarządzaj listami", command=self._open_lists_menu).pack(side="left", padx=3)

        ttk.Button(rbox, text="Eksport CSV",    command=self._export_csv).pack(side="left", padx=3)

        if CURRENT_USER.get("role") == "admin":
            ttk.Button(rbox, text="Kopia zapasowa", command=self._backup_menu).pack(side="left", padx=3)

        ttk.Button(rbox, text="Wyloguj", command=self._logout).pack(side="left", padx=(8, 0))

        ttk.Separator(root).pack(fill="x")

        # ZAKŁADKI
        self._nb = ttk.Notebook(root)
        self._nb.pack(fill="both", expand=True)
        tab_lista = ttk.Frame(self._nb, padding=(12,10))
        tab_form  = ttk.Frame(self._nb, padding=(12,10))
        self._nb.add(tab_lista, text="  Lista usterek  ")
        self._nb.add(tab_form,  text="  Dodaj usterkę  ")
        self._build_list_tab(tab_lista)
        self._build_form_tab(tab_form)

        # DOLNY PASEK
        bot = ttk.Frame(root, padding=(14,4))
        bot.pack(fill="x", side="bottom")
        ttk.Separator(root).pack(fill="x", side="bottom")
        ttk.Label(bot, text="Rejestr Usterek v2.0   Created by ad.luka",
                   font=FONT_MUTED, foreground=DIM).pack(side="left")
        if _BOOT:
            self._dark_var = tk.BooleanVar(value=UI.get("theme")=="dark")
            ttk.Checkbutton(bot, text="Dark mode", variable=self._dark_var,
                            command=self._toggle_theme).pack(side="right")

    def _update_user_badge_text(self):
        user_name = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or "Użytkownik"
        role_name = ROLE_PL.get(CURRENT_USER.get("role"), CURRENT_USER.get("role", "technik"))
        self._user_badge_var.set(f"👤 {user_name}  ({role_name})")

    # ══════════════════════════════════════════════════════════════
    # ZAKŁADKA 1 — LISTA
    # ══════════════════════════════════════════════════════════════
    def _build_list_tab(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # Filtry
        frow = ttk.Frame(parent)
        frow.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,8))
        ttk.Label(frow, text="Szukaj:", font=FONT_LABEL).pack(side="left", padx=(0,4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render())
        ttk.Entry(frow, textvariable=self._search_var, width=24).pack(side="left", padx=(0,12))

        ttk.Label(frow, text="Klient:", font=FONT_LABEL).pack(side="left", padx=(0,4))
        self._fklient_var = tk.StringVar(value="Wszyscy")
        self._fklient_cb  = ttk.Combobox(frow, textvariable=self._fklient_var, state="readonly", width=22)
        self._fklient_cb.pack(side="left", padx=(0,12))
        self._fklient_cb.bind("<<ComboboxSelected>>", lambda _: self._render())

        ttk.Label(frow, text="Typ:", font=FONT_LABEL).pack(side="left", padx=(0,4))
        self._ftyp_var = tk.StringVar(value="Wszystkie")
        self._ftyp_cb  = ttk.Combobox(frow, textvariable=self._ftyp_var, state="readonly", width=18)
        self._ftyp_cb.pack(side="left", padx=(0,12))
        self._ftyp_cb.bind("<<ComboboxSelected>>", lambda _: self._render())

        ttk.Label(frow, text="Status:", font=FONT_LABEL).pack(side="left", padx=(0,4))
        self._fstat_var = tk.StringVar(value="Wszystkie")
        fstat = ttk.Combobox(frow, textvariable=self._fstat_var, state="readonly",
                              width=14, values=["Wszystkie","Otwarta","Naprawiona"])
        fstat.pack(side="left")
        fstat.bind("<<ComboboxSelected>>", lambda _: self._render())

        # Podział na tabelę i panel szczegółów
        pw = ttk.Panedwindow(parent, orient="horizontal")
        pw.grid(row=1, column=0, columnspan=3, sticky="nsew")

        # Lewy panel: Tabela
        table_frame = ttk.Frame(pw)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("data","klient","model","projekt","typ","prob","status")
        self._tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        hdrs = {"data":"Data","klient":"Klient","model":"Model","projekt":"Projekt",
                "typ":"Typ","prob":"Opis problemu","status":"Status"}
        base_wids = {"data":130,"klient":110,"model":100,"projekt":90,
                     "typ":110,"prob":350,"status":95}
        for c in cols:
            w = px(base_wids[c])
            self._tree.heading(c, text=hdrs[c], command=lambda _c=c: self._sort(_c))
            self._tree.column(c, width=w, anchor="w",
                              stretch=(c == "prob"),
                              minwidth=w if c == "status" else px(40))

        pal = _get_theme_palette(UI.get("theme") == "dark")
        self._tree_style.configure("Treeview", font=FONT_REGULAR, rowheight=px(32))
        self._tree_style.configure("Treeview.Heading", font=FONT_LABEL)
        self._tree.tag_configure("open",  foreground=pal["open"])
        self._tree.tag_configure("fixed", foreground=pal["green"])
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_select())
        self._tree.bind("<Double-1>",          self._on_double_click)
        self._tree.bind("<Configure>",         self._on_tree_resize)
        self._tree.bind("<ButtonRelease-1>",   lambda e: self.root.after(60, self._check_col_resize))
        sc = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sc.set)
        sc.grid(row=0, column=1, sticky="ns")

        pw.add(table_frame, weight=3)

        # Prawy panel: Szczegóły usterki
        detail_outer = ttk.Labelframe(pw, text="Szczegóły", padding=0)

        canvas = tk.Canvas(detail_outer, highlightthickness=0)
        sb = ttk.Scrollbar(detail_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        detail = ttk.Frame(canvas, padding=px(12))
        _cwin  = canvas.create_window((0,0), window=detail, anchor="nw")

        def _update_detail_wrap(w):
            avail_w = max(px(250), w - px(36))
            if hasattr(self, '_det_prob_lbl'):
                self._det_prob_lbl.configure(wraplength=avail_w)
            if hasattr(self, '_det_fix_lbl'):
                self._det_fix_lbl.configure(wraplength=avail_w)
            if hasattr(self, '_det_typ_lbl'):
                self._det_typ_lbl.configure(wraplength=max(px(120), avail_w // 2 - px(16)))
            if hasattr(self, '_det_elem_lbl'):
                self._det_elem_lbl.configure(wraplength=max(px(120), avail_w // 2 - px(16)))

        def _on_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            w = canvas.winfo_width()
            canvas.itemconfig(_cwin, width=w)
            _update_detail_wrap(w)

        detail.bind("<Configure>", _on_conf)
        canvas.bind("<Configure>", lambda e: (canvas.itemconfig(_cwin, width=e.width), _update_detail_wrap(e.width)))

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        detail_outer.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        detail_outer.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        self._dv = {k: tk.StringVar() for k in
            ["klient","model","projekt","vin","typ","elem","status","data","prob","fix", "created_by", "fixed_by"]}

        # Identyfikacja i Odpowiedzialność
        meta_grid = ttk.Frame(detail)
        meta_grid.pack(fill="x", pady=(0, 6))
        meta_grid.columnconfigure(0, weight=1)
        meta_grid.columnconfigure(1, weight=1)

        pal = _get_theme_palette(UI.get("theme") == "dark")

        f_cb = ttk.Frame(meta_grid)
        f_cb.grid(row=0, column=0, sticky="nw", padx=(0, px(8)))
        l_cb = ttk.Label(f_cb, text="Zgłosił:", font=FONT_LABEL, foreground=pal["dim"])
        l_cb.pack(anchor="w")
        self._dim_labels.append(l_cb)
        ttk.Label(f_cb, textvariable=self._dv["created_by"], font=FONT_REGULAR).pack(anchor="w")

        f_fb = ttk.Frame(meta_grid)
        f_fb.grid(row=0, column=1, sticky="nw", padx=(px(8), 0))
        l_fb = ttk.Label(f_fb, text="Naprawił:", font=FONT_LABEL, foreground=pal["dim"])
        l_fb.pack(anchor="w")
        self._dim_labels.append(l_fb)
        ttk.Label(f_fb, textvariable=self._dv["fixed_by"], font=FONT_REGULAR).pack(anchor="w")

        ttk.Separator(detail).pack(fill="x", pady=(6,6))

        # Typ usterki i Element
        grid = ttk.Frame(detail)
        grid.pack(fill="x", pady=(0,4))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        f_typ = ttk.Frame(grid)
        f_typ.grid(row=0, column=0, sticky="nw", padx=(0,px(16)), pady=(2,0))
        l_typ = ttk.Label(f_typ, text="Typ usterki", font=FONT_LABEL, foreground=pal["dim"])
        l_typ.pack(anchor="w")
        self._dim_labels.append(l_typ)
        self._det_typ_lbl = ttk.Label(f_typ, textvariable=self._dv["typ"], font=FONT_REGULAR, justify="left")
        self._det_typ_lbl.pack(anchor="w")

        f_elem = ttk.Frame(grid)
        f_elem.grid(row=0, column=1, sticky="nw", padx=(0,px(16)), pady=(2,0))
        l_elem = ttk.Label(f_elem, text="Element", font=FONT_LABEL, foreground=pal["dim"])
        l_elem.pack(anchor="w")
        self._dim_labels.append(l_elem)
        self._det_elem_lbl = ttk.Label(f_elem, textvariable=self._dv["elem"], font=FONT_REGULAR, justify="left")
        self._det_elem_lbl.pack(anchor="w")

        ttk.Separator(detail).pack(fill="x", pady=(6,2))

        # Opisy
        def _lbl(t):
            lbl_w = ttk.Label(detail, text=t, font=FONT_LABEL, foreground=pal["dim"])
            lbl_w.pack(anchor="w", pady=(4,0))
            self._dim_labels.append(lbl_w)

        _lbl("Opis problemu")
        self._det_prob_lbl = ttk.Label(detail, textvariable=self._dv["prob"],
                                       justify="left", font=FONT_REGULAR)
        self._det_prob_lbl.pack(anchor="w")

        ttk.Separator(detail).pack(fill="x", pady=(6,2))

        _lbl("Opis naprawy / Przyczyna")
        self._det_fix_lbl = ttk.Label(detail, textvariable=self._dv["fix"],
                                      justify="left", font=FONT_REGULAR)
        self._det_fix_lbl.pack(anchor="w")

        ttk.Separator(detail).pack(fill="x", pady=(6,2))

        # Galeria zdjęć i Dokumentów w panelu szczegółów
        self._panel_gallery = PhotoGallery(detail, mode="panel")
        self._panel_gallery.pack(fill="x", pady=(4,0))

        ttk.Separator(detail).pack(fill="x", pady=(8,2))

        self._panel_docs = DocGallery(detail, mode="panel")
        self._panel_docs.pack(fill="x", pady=(4,0))

        self._clear_detail()
        pw.add(detail_outer, weight=2)

        # Dolny pasek przycisków
        arow = ttk.Frame(parent)
        arow.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8,0))

        is_podglad = (CURRENT_USER.get("role") == "podglad")
        if not is_podglad:
            ttk.Button(arow, text="✎ Edytuj",       command=self._edit_selected).pack(side="left", padx=(0,4))
            ttk.Button(arow, text="⇄ Zmień status / Oznacz naprawę", command=self._toggle_status).pack(side="left", padx=(0,4))
            ttk.Button(arow, text="✕ Usuń",         command=self._delete_selected).pack(side="left")
            ttk.Button(arow, text="＋ Nowa usterka", command=self._new_record).pack(side="right")
        else:
            ttk.Button(arow, text="🔍 Podgląd", command=self._view_selected).pack(side="left")

    # ══════════════════════════════════════════════════════════════
    # ZAKŁADKA 2 — FORMULARZ
    # ══════════════════════════════════════════════════════════════
    def _build_form_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=1)

        self._form_title_var = tk.StringVar(value="Nowa usterka")
        ttk.Label(parent, textvariable=self._form_title_var,
                  font=FONT_SUBTITLE).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Identyfikacja
        left_top = ttk.Labelframe(parent, text="Identyfikacja", padding=12)
        left_top.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=(0, 10))
        left_top.columnconfigure(1, weight=1)

        def lrow(frm, label, w_fn, r):
            ttk.Label(frm, text=label, font=FONT_LABEL).grid(
                row=r, column=0, sticky="w", padx=(0, 10), pady=(3, 2))
            w = w_fn(frm)
            w.grid(row=r, column=1, sticky="ew", pady=(3, 2))
            return w

        r = 0
        self._klient_var = tk.StringVar()
        self._klient_cb  = lrow(left_top, "Klient",
            lambda p: ttk.Combobox(p, textvariable=self._klient_var, state="readonly"), r); r += 1
        self._klient_cb.bind("<<ComboboxSelected>>", lambda _: self._on_klient_changed())

        self._model_var = tk.StringVar()
        self._model_cb  = lrow(left_top, "Model",
            lambda p: ttk.Combobox(p, textvariable=self._model_var), r); r += 1
        self._model_cb.bind("<<ComboboxSelected>>", lambda _: self._on_model_changed())

        self._proj_var = tk.StringVar()
        self._proj_cb  = lrow(left_top, "Projekt",
            lambda p: ttk.Combobox(p, textvariable=self._proj_var), r); r += 1
        self._proj_cb.bind("<<ComboboxSelected>>", lambda _: self._on_projekt_changed())

        self._vin_var = tk.StringVar()
        self._vin_entry = lrow(left_top, "VIN (opcjonalnie)",
            lambda p: ttk.Entry(p, textvariable=self._vin_var), r); r += 1

        self._typ_var = tk.StringVar()
        self._typ_cb  = lrow(left_top, "Typ usterki",
            lambda p: ttk.Combobox(p, textvariable=self._typ_var, state="readonly"), r); r += 1

        self._elem_var = tk.StringVar()
        self._elem_entry = lrow(left_top, "Element / urządzenie",
            lambda p: ttk.Entry(p, textvariable=self._elem_var), r); r += 1

        self._created_by_var = tk.StringVar()
        self._created_by_cb = lrow(left_top, "Zgłaszający (Technik)",
            lambda p: ttk.Combobox(p, textvariable=self._created_by_var), r); r += 1

        self._status_var = tk.StringVar(value="Otwarta")
        self._status_cb = lrow(left_top, "Status",
            lambda p: ttk.Combobox(p, textvariable=self._status_var, state="readonly",
                                   values=["Otwarta", "Naprawiona"]), r); r += 1
        self._status_cb.bind("<<ComboboxSelected>>", lambda _: self._on_status_changed())

        self._fixed_by_var = tk.StringVar()
        self._fixed_by_cb = lrow(left_top, "Naprawił (Technik)",
            lambda p: ttk.Combobox(p, textvariable=self._fixed_by_var, state="disabled"), r)

        # Opisy
        right_top = ttk.Labelframe(parent, text="Opisy", padding=12)
        right_top.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=(0, 10))
        right_top.columnconfigure(0, weight=1)
        right_top.rowconfigure(1, weight=3)
        right_top.rowconfigure(3, weight=2)

        ttk.Label(right_top, text="Opis problemu *",
                  font=FONT_LABEL).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._prob_txt = tk.Text(right_top, height=5, wrap="word", font=FONT_REGULAR)
        self._prob_txt.grid(row=1, column=0, sticky="nsew", pady=(0, 6))

        ttk.Label(right_top, text="Opis naprawy / Rozwiązanie",
                  font=FONT_LABEL).grid(row=2, column=0, sticky="w", pady=(0, 2))
        self._fix_txt = tk.Text(right_top, height=3, wrap="word", font=FONT_REGULAR)
        self._fix_txt.grid(row=3, column=0, sticky="nsew")

        # Zdjęcia i Dokumenty
        left_bot = ttk.Labelframe(parent, text="Zdjęcia", padding=12)
        left_bot.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
        self._form_gallery = PhotoGallery(left_bot, mode="form")
        self._form_gallery.pack(fill="both", expand=True)

        right_bot = ttk.Labelframe(parent, text="Dokumenty", padding=12)
        right_bot.grid(row=2, column=1, sticky="nsew", padx=(6, 0))
        self._form_docs = DocGallery(right_bot, mode="form")
        self._form_docs.pack(fill="both", expand=True)

        # Przyciski
        brow = ttk.Frame(parent)
        brow.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._save_btn = ttk.Button(brow, text="Zapisz usterkę", command=self._save_form)
        self._save_btn.pack(side="left", padx=(0, 8))
        self._cancel_btn = ttk.Button(brow, text="Wyczyść", command=self._confirm_clear)
        self._cancel_btn.pack(side="left")

        if CURRENT_USER.get("role") == "podglad":
            self._save_btn.configure(state="disabled")

    def _on_status_changed(self):
        st = self._status_var.get()
        if st == "Naprawiona":
            self._fixed_by_cb.configure(state="normal")
            if not self._fixed_by_var.get():
                curr_name = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or ""
                self._fixed_by_var.set(curr_name)
        else:
            self._fixed_by_cb.configure(state="disabled")
            self._fixed_by_var.set("")

    # ── panel szczegółów ─────────────────────────────────────────
    def _clear_detail(self):
        for v in self._dv.values(): v.set("—")
        self._panel_gallery.clear()
        self._panel_docs.clear()

    def _on_select(self):
        r = self._selected()
        if not r:
            self._clear_detail(); return
        self._dv["klient"].set(r.get("klient") or "—")
        self._dv["model"].set(r.get("model") or "—")
        self._dv["projekt"].set(r.get("projekt") or "—")
        self._dv["vin"].set(r.get("vin") or "—")
        self._dv["typ"].set(r.get("typ") or "—")
        self._dv["elem"].set(r.get("element") or "—")
        self._dv["status"].set(STATUS_PL.get(r.get("status","open"),r.get("status","")))
        self._dv["data"].set(self._fmt_dt(r.get("created","")))
        self._dv["prob"].set(r.get("opisProblem") or "—")
        self._dv["fix"].set(r.get("opisNaprawa") or "—")

        self._dv["created_by"].set(r.get("created_by") or "—")
        fixed_str = r.get("fixed_by") or ""
        if fixed_str and r.get("fixed_at"):
            fixed_str += f"  ({self._fmt_dt(r.get('fixed_at'))})"
        self._dv["fixed_by"].set(fixed_str or "—")

        self._panel_gallery.load_for_record(r["id"])
        self._panel_docs.load_for_record(r["id"])

    # ── obsługa zdarzeń formularza ───────────────────────────────
    def _on_klient_changed(self):
        k = self._klient_var.get()
        projekty = self._lists.get("projektyByKlient",{}).get(k,[])
        self._proj_cb.configure(values=projekty)
        if projekty: self._proj_var.set(projekty[0])
        else: self._proj_var.set("")
        UI["last_klient"] = k
        _save_cfg(UI)

    def _on_model_changed(self):
        UI["last_model"] = self._model_var.get()
        _save_cfg(UI)

    def _on_projekt_changed(self):
        UI["last_projekt"] = self._proj_var.get()
        _save_cfg(UI)

    def _get_prob_col_width(self):
        try:
            tree_w = self._tree.winfo_width()
            if tree_w > px(300):
                fixed_w = sum(self._tree.column(c, "width") for c in
                              ("data","klient","model","projekt","typ","status"))
                calc_w = tree_w - fixed_w - px(20)
                if calc_w > px(150):
                    return calc_w
        except Exception:
            pass

        try:
            screen_w = self.root.winfo_width()
            if screen_w < 200:
                screen_w = self.root.winfo_screenwidth()
            est_tree_w = int(screen_w * 0.6)
            fixed_w = px(130 + 110 + 100 + 90 + 110 + 95)
            est_prob = est_tree_w - fixed_w - px(20)
            if est_prob > px(150):
                return est_prob
        except Exception:
            pass

        col_w = self._tree.column("prob", "width")
        return max(px(200), col_w - px(20))

    def _on_tree_resize(self, event):
        w = event.width
        if abs(w - self._last_tree_w) > px(15):
            self._last_tree_w = w
            if self._resize_job:
                try: self.root.after_cancel(self._resize_job)
                except Exception: pass
            self._resize_job = self.root.after(30, self._render)

    def _check_col_resize(self):
        col_w = self._tree.column("prob", "width")
        if abs(col_w - self._last_prob_w) > px(15):
            self._last_prob_w = col_w
            self._render()

    # ── renderowanie tabeli ───────────────────────────────────────
    def _render(self):
        sel = self._tree.selection()
        sel_id = sel[0] if sel else None

        self._tree.delete(*self._tree.get_children())
        q  = self._search_var.get().strip().lower()
        kf = self._fklient_var.get()
        tf = self._ftyp_var.get()
        sf = self._fstat_var.get()
        rows = []
        for r in self._records:
            if kf != "Wszyscy"    and r.get("klient") != kf:      continue
            if tf != "Wszystkie"  and r.get("typ")    != tf:      continue
            if sf == "Otwarta"    and r.get("status") != "open":  continue
            if sf == "Naprawiona" and r.get("status") != "fixed": continue
            if q:
                hay = " ".join(str(r.get(k,"")) for k in
                    ["klient","model","projekt","vin","element",
                     "opisProblem","opisNaprawa","typ","created_by","fixed_by"]).lower()
                if q not in hay: continue
            rows.append(r)
        col_key = "created" if self._sort_col == "data" else self._sort_col
        rows.sort(key=lambda r: str(r.get(col_key,"")), reverse=self._sort_rev)
        arrow = " ▼" if self._sort_rev else " ▲"
        hdrs  = {"data":"Data","klient":"Klient","model":"Model","projekt":"Projekt",
                 "typ":"Typ","prob":"Opis problemu","status":"Status"}
        for c in hdrs:
            self._tree.heading(c, text=hdrs[c]+(arrow if c==self._sort_col else ""))

        avail_px = self._get_prob_col_width()
        self._last_prob_w = self._tree.column("prob", "width")

        font = _get_tree_font()

        max_lines_needed = 1
        rendered_items = []
        for r in rows:
            prob_wrapped = _wrap_to_pixels(r.get("opisProblem",""), avail_px, max_lines=3, font=font)
            lines_cnt = prob_wrapped.count("\n") + 1 if prob_wrapped else 1
            if lines_cnt > max_lines_needed:
                max_lines_needed = lines_cnt
            rendered_items.append((r, prob_wrapped))

        for r, prob_wrapped in rendered_items:
            self._tree.insert("","end", iid=r["id"], tags=(r.get("status","open"),),
                values=(self._fmt_dt(r.get("created","")),
                        r.get("klient",""), r.get("model",""),
                        r.get("projekt",""), r.get("typ",""),
                        prob_wrapped,
                        STATUS_PL.get(r.get("status","open"),r.get("status",""))))

        # Dynamiczne dopasowanie wysokości wierszy tabeli (1 wiersz = px(32), 2 wiersze = px(52), 3 wiersze = px(72))
        if max_lines_needed == 1:
            target_rowheight = px(32)
        elif max_lines_needed == 2:
            target_rowheight = px(52)
        else:
            target_rowheight = px(72)

        self._tree_style.configure("Treeview", font=FONT_REGULAR, rowheight=target_rowheight)
        self._tree_style.configure("Treeview.Heading", font=FONT_LABEL)

        if sel_id and self._tree.exists(sel_id):
            self._tree.selection_set(sel_id)

    def _sort(self, col):
        if self._sort_col == col: self._sort_rev = not self._sort_rev
        else: self._sort_col = col; self._sort_rev = False
        self._render()

    @staticmethod
    def _fmt_dt(iso):
        try:   return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
        except: return iso

    def _selected(self):
        s = self._tree.selection()
        if not s: return None
        return next((r for r in self._records if r["id"]==s[0]), None)

    # ── formularz zapisu ──────────────────────────────────────────
    def _save_form(self):
        if CURRENT_USER.get("role") == "podglad":
            messagebox.showwarning(APP_TITLE, "Konto o roli 'Podgląd' nie posiada uprawnień do edycji."); return

        klient = self._klient_var.get().strip()
        model  = self._model_var.get().strip()
        typ    = self._typ_var.get().strip()
        prob   = self._prob_txt.get("1.0","end").strip()
        if not all([klient, model, typ, prob]):
            messagebox.showwarning(APP_TITLE,
                "Uzupełnij wymagane pola: Klient, Model, Typ, Opis problemu."); return

        status = "open" if self._status_var.get()=="Otwarta" else "fixed"
        rec_id = self._edit_id or str(uuid.uuid4())
        is_edit = bool(self._edit_id)

        created_by = self._created_by_var.get().strip()
        if not created_by:
            created_by = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or ""

        fixed_by = self._fixed_by_var.get().strip() if status == "fixed" else ""

        payload = dict(
            klient=klient, model=model,
            projekt=self._proj_var.get().strip(),
            vin=self._vin_var.get().strip(),
            typ=typ, element=self._elem_var.get().strip(),
            opisProblem=prob,
            opisNaprawa=self._fix_txt.get("1.0","end").strip(),
            status=status,
            created_by=created_by
        )

        if status == "fixed":
            payload["fixed_by"] = fixed_by or (CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or "")
            payload["fixed_at"] = datetime.now().isoformat(timespec="seconds")
        else:
            payload["fixed_by"] = ""
            payload["fixed_at"] = None

        try:
            if is_edit:
                API.put(f"/api/records/{rec_id}", payload)
            else:
                payload["id"]      = rec_id
                payload["created"] = datetime.now().isoformat(timespec="seconds")
                API.post("/api/records", payload)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Błąd zapisu usterki:\n{e}"); return

        for p in self._form_gallery.get_pending():
            try:
                API.post(f"/api/records/{rec_id}/photos", {
                    "filename": p["filename"],
                    "data": base64.b64encode(p["bytes"]).decode()
                })
            except Exception as e:
                messagebox.showwarning(APP_TITLE, f"Usterka zapisana, ale zdjęcie „{p['filename']}\" nie:\n{e}")

        for d in self._form_docs.get_pending():
            try:
                API.post(f"/api/records/{rec_id}/documents", {
                    "filename": d["filename"],
                    "data": base64.b64encode(d["bytes"]).decode()
                })
            except Exception as e:
                messagebox.showwarning(APP_TITLE, f"Usterka zapisana, ale dokument „{d['filename']}\" nie:\n{e}")

        self._auto_add_to_lists(klient, model, typ, payload["projekt"])
        self._clear_form()
        self._reload(force=True)
        self._nb.select(0)

        # Zaznacz nowo utworzony / zaktualizowany rekord w tabeli
        try:
            if self._tree.exists(rec_id):
                self._tree.selection_set(rec_id)
                self._tree.see(rec_id)
                self._on_select()
        except Exception:
            pass

        msg = "Zmiany w usterce zostały zapisane." if is_edit else "Nowa usterka została zarejestrowana."
        messagebox.showinfo(APP_TITLE, msg)

    def _auto_add_to_lists(self, klient, model, typ, projekt):
        changed = False
        def _add(key, val):
            nonlocal changed
            if val and val not in self._lists.setdefault(key,[]):
                self._lists[key].append(val); changed = True
        _add("klienci",klient); _add("modele",model); _add("typy",typ)
        if klient and projekt:
            arr = self._lists.setdefault("projektyByKlient",{}).setdefault(klient,[])
            if projekt not in arr: arr.append(projekt); changed = True
        if changed:
            try: API.put("/api/lists", self._lists)
            except Exception: pass

    def _new_record(self):
        if self._edit_id and self._form_mode == "edit":
            if not messagebox.askyesno(APP_TITLE,
                    "Trwa edycja usterki.\n\nOdrzucić zmiany i otworzyć formularz nowej usterki?"):
                return
        self._clear_form()
        self._set_form_mode("new")
        self._nb.select(1)

    def _confirm_clear(self):
        if self._edit_id and self._form_mode == "edit":
            if not messagebox.askyesno(APP_TITLE,
                    "Trwa edycja usterki.\n\nOdrzucić zmiany i wyczyścić formularz?"):
                return
        self._clear_form()
        self._set_form_mode("new")

    def _clear_form(self):
        self._edit_id = None
        self._prob_txt.configure(state="normal")
        self._fix_txt.configure(state="normal")
        for v in [self._vin_var, self._typ_var, self._elem_var]:
            v.set("")
        self._prob_txt.delete("1.0","end")
        self._fix_txt.delete("1.0","end")
        self._status_var.set("Otwarta")
        self._fixed_by_var.set("")
        self._fixed_by_cb.configure(state="disabled")

        curr_name = CURRENT_USER.get("full_name") or CURRENT_USER.get("username") or ""
        self._created_by_var.set(curr_name)

        self._form_gallery.clear()
        self._form_docs.clear()
        klienci  = self._lists.get("klienci",[])
        modele   = self._lists.get("modele",[])
        last_k   = UI.get("last_klient","")
        self._klient_var.set(last_k if last_k in klienci else "")
        last_m   = UI.get("last_model","")
        self._model_var.set(last_m if last_m in modele else "")
        projekty = self._lists.get("projektyByKlient",{}).get(self._klient_var.get(),[])
        self._proj_cb.configure(values=projekty)
        last_p   = UI.get("last_projekt","")
        self._proj_var.set(last_p if last_p in projekty else "")

    def _set_form_mode(self, mode="new", record=None):
        self._form_mode = mode
        is_view = (mode == "view")

        cb_state = "disabled" if is_view else "readonly"
        entry_state = "disabled" if is_view else "normal"
        text_state = "disabled" if is_view else "normal"

        self._klient_cb.configure(state=cb_state)
        self._model_cb.configure(state="disabled" if is_view else "normal")
        self._proj_cb.configure(state="disabled" if is_view else "normal")
        self._vin_entry.configure(state=entry_state)
        self._typ_cb.configure(state=cb_state)
        self._elem_entry.configure(state=entry_state)
        self._created_by_cb.configure(state="disabled" if is_view else "normal")
        self._status_cb.configure(state=cb_state)

        if not is_view and self._status_var.get() == "Naprawiona":
            self._fixed_by_cb.configure(state="normal")
        else:
            self._fixed_by_cb.configure(state="disabled")

        self._prob_txt.configure(state=text_state)
        self._fix_txt.configure(state=text_state)

        self._form_gallery.set_readonly(is_view)
        self._form_docs.set_readonly(is_view)

        if mode == "new":
            self._form_title_var.set("Nowa usterka")
            self._save_btn.configure(text="Zapisz usterkę", state="normal", command=self._save_form)
            self._cancel_btn.configure(text="Wyczyść", command=self._confirm_clear)
        elif mode == "edit":
            self._form_title_var.set("Edycja usterki")
            self._save_btn.configure(text="Zapisz zmiany", state="normal", command=self._save_form)
            self._cancel_btn.configure(text="Anuluj edycję", command=self._cancel_edit)
        else: # view
            self._form_title_var.set("Podgląd usterki (tylko do odczytu)")
            self._save_btn.configure(text="✎ Edytuj tę usterkę", state="normal", command=self._switch_to_edit)
            self._cancel_btn.configure(text="Zamknij podgląd", command=lambda: self._nb.select(0))

        if CURRENT_USER.get("role") == "podglad":
            self._save_btn.configure(state="disabled")

    def _fill_form_with_record(self, r):
        self._edit_id = r["id"]
        self._klient_var.set(r.get("klient",""))
        self._on_klient_changed()
        self._model_var.set(r.get("model",""))
        self._proj_var.set(r.get("projekt",""))
        self._vin_var.set(r.get("vin",""))
        self._typ_var.set(r.get("typ",""))
        self._elem_var.set(r.get("element",""))
        self._created_by_var.set(r.get("created_by",""))
        self._fixed_by_var.set(r.get("fixed_by",""))
        self._status_var.set(STATUS_PL.get(r.get("status","open"),"Otwarta"))

        self._prob_txt.configure(state="normal")
        self._prob_txt.delete("1.0","end")
        self._prob_txt.insert("1.0", r.get("opisProblem",""))

        self._fix_txt.configure(state="normal")
        self._fix_txt.delete("1.0","end")
        self._fix_txt.insert("1.0", r.get("opisNaprawa",""))

        self._form_gallery.clear()
        try:
            metas = API.get(f"/api/records/{r['id']}/photos")
            for m in metas:
                resp = API.get(f"/api/photos/{m['id']}")
                raw  = base64.b64decode(resp["data"])
                self._form_gallery._photos.append({
                    "id": m["id"], "filename": m["filename"],
                    "bytes": raw, "thumb": _make_thumb(raw)
                })
            self._form_gallery._refresh_ui()
        except Exception:
            pass

        self._form_docs.clear()
        try:
            metas = API.get(f"/api/records/{r['id']}/documents")
            for m in metas:
                entry = {"id": m["id"], "filename": m["filename"],
                         "filesize": m["filesize"], "bytes": None, "thumb": None}
                if m["filename"].lower().endswith(".pdf"):
                    try:
                        resp = API.get(f"/api/documents/{m['id']}")
                        raw  = base64.b64decode(resp["data"])
                        entry["bytes"] = raw
                        entry["thumb"] = _make_pdf_thumb(raw, size=(px(100), px(130)))
                    except Exception:
                        pass
                self._form_docs._docs.append(entry)
            self._form_docs._refresh_ui()
        except Exception:
            pass

    def _on_double_click(self, event):
        iid = self._tree.identify_row(event.y)
        if not iid: return
        self._tree.selection_set(iid)
        self._view_selected()

    def _view_selected(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę na liście."); return
        self._fill_form_with_record(r)
        self._set_form_mode("view", r)
        self._nb.select(1)

    def _edit_selected(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę na liście."); return
        self._fill_form_with_record(r)
        self._set_form_mode("edit", r)
        self._nb.select(1)

    def _switch_to_edit(self):
        r = self._selected()
        if r: self._set_form_mode("edit", r)

    def _cancel_edit(self):
        r = self._selected()
        if r:
            self._fill_form_with_record(r)
            self._set_form_mode("view", r)
        else:
            self._clear_form()
            self._set_form_mode("new")

    def _toggle_status(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę."); return

        if r.get("status") == "open":
            # Otwórz okno oznaczania jako naprawiona z wyborem technika
            _MarkFixedDlg(self.root, r, self._users_list, on_success=lambda: self._reload(force=True))
        else:
            # Ponowne otwarcie usterki
            if not messagebox.askyesno(APP_TITLE, "Czy chcesz ponownie otworzyć tę usterkę?"):
                return
            try:
                API.patch(f"/api/records/{r['id']}/status", {
                    "status": "open",
                    "fixed_by": "",
                    "fixed_at": None
                })
            except Exception as e:
                messagebox.showerror(APP_TITLE, str(e)); return
            self._reload(force=True)

    def _delete_selected(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę."); return
        if not messagebox.askyesno(APP_TITLE,"Usunąć tę usterkę wraz ze zdjęciami? Operacja jest nieodwracalna."): return
        try:
            API.delete(f"/api/records/{r['id']}")
        except Exception as e: messagebox.showerror(APP_TITLE, str(e)); return
        self._reload(force=True)

    # ── menu profilu i administracji ──────────────────────────────
    def _open_quick_switch(self):
        def on_switch(new_user):
            global CURRENT_USER
            CURRENT_USER = new_user
            self._update_user_badge_text()
            if self._form_mode == "new" and not self._edit_id:
                curr_name = new_user.get("full_name") or new_user.get("username") or ""
                self._created_by_var.set(curr_name)
            messagebox.showinfo(APP_TITLE, f"Aktywny technik został zmieniony na:\n{new_user.get('full_name')} ({new_user.get('username')})")

        _QuickSwitchUserDlg(self.root, self._users_list, on_switch=on_switch)

    def _open_user_management(self):
        _UserManagementDlg(self.root)

    def _open_change_pw(self):
        _ChangePasswordDlg(self.root)

    def _logout(self):
        if not messagebox.askyesno(APP_TITLE, "Czy na pewno chcesz się wylogować?"):
            return
        try:
            API.post("/api/auth/logout", {})
        except Exception:
            pass
        UI["auth_token"] = ""
        _save_cfg(UI)
        API.set_token("")
        self.root.destroy()
        if self._on_logout:
            self._on_logout()

    # ── zarządzanie listami ───────────────────────────────────────
    def _open_lists_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Klienci",      command=lambda: self._open_list_dlg("Klienci","klienci"))
        m.add_command(label="Modele",       command=lambda: self._open_list_dlg("Modele","modele"))
        m.add_command(label="Typy usterek", command=lambda: self._open_list_dlg("Typy usterek","typy"))
        m.add_command(label="Projekty",     command=self._open_proj_dlg)
        try:   m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally: m.grab_release()

    def _open_list_dlg(self, title, key):
        def on_save(items):
            self._lists[key]=items
            try: API.put("/api/lists", self._lists)
            except Exception as e: messagebox.showerror(APP_TITLE, str(e))
            self._rebuild_combos()
        _ListDlg(self.root, title, self._lists.get(key,[]), on_save)

    def _open_proj_dlg(self):
        def on_save(data):
            self._lists["projektyByKlient"]=data
            try: API.put("/api/lists", self._lists)
            except Exception as e: messagebox.showerror(APP_TITLE, str(e))
            self._rebuild_combos()
        _ProjDlg(self.root, self._lists.get("klienci",[]),
                 self._lists.get("projektyByKlient",{}), on_save)

    # ── eksport / backup ──────────────────────────────────────────
    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV","*.csv")],
            initialfile="rejestr_usterek.csv")
        if not path: return
        cols = ["created","klient","model","projekt","vin","typ",
                "element","opisProblem","opisNaprawa","status","created_by","fixed_by","fixed_at"]
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(cols)
                for r in self._records:
                    w.writerow([r.get(c,"") for c in cols])
            messagebox.showinfo(APP_TITLE,"Plik CSV zapisany.")
        except Exception as e:
            messagebox.showerror(APP_TITLE, str(e))

    def _backup_menu(self):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="⚡ Optymalizuj zdjęcia i odchudź bazę", command=self._optimize_photos_action)
        m.add_separator()
        m.add_command(label="Eksportuj kopię (JSON)",  command=self._backup_export)
        m.add_command(label="Importuj kopię — scal",   command=lambda: self._backup_import("merge"))
        m.add_command(label="Importuj kopię — zastąp", command=lambda: self._backup_import("replace"))
        try:   m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally: m.grab_release()

    def _optimize_photos_action(self):
        if not messagebox.askyesno(APP_TITLE,
                "Czy chcesz zoptymalizować wszystkie zdjęcia w bazie?\n\n"
                "Operacja przeskaluje duże zdjęcia (do max 1920px, jakość 85%), "
                "zmniejszy rozmiar bazy o ~90% i odzyska wolne miejsce na dysku."):
            return
        try:
            resp = API.post("/api/admin/optimize-photos", {})
            messagebox.showinfo(APP_TITLE,
                f"Optymalizacja zakończona sukcesem!\n\n"
                f"Przetworzono zdjęć: {resp.get('total_photos', 0)}\n"
                f"Zoptymalizowano: {resp.get('updated_photos', 0)}\n"
                f"Rozmiar zdjęć: {resp.get('before_mb', 0)} MB  ➔  {resp.get('after_mb', 0)} MB\n"
                f"Zaoszczędzono: {resp.get('saved_percent', 0)}% miejsca.")
            self._reload(force=True)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Błąd optymalizacji:\n{e}")

    def _backup_export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON","*.json")],
            initialfile=f"kopia_{datetime.now().strftime('%Y-%m-%d')}.json")
        if not path: return
        data = {"records": self._records, "lists": self._lists}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        messagebox.showinfo(APP_TITLE,"Kopia zapasowa zapisana.")

    def _backup_import(self, mode):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            data  = json.loads(Path(path).read_text("utf-8"))
            recs  = data.get("records",[])
            lists = data.get("lists",{})
        except Exception as e:
            messagebox.showerror(APP_TITLE,f"Błąd odczytu pliku:\n{e}"); return
        verb = "zastąpić" if mode=="replace" else "scalić z"
        if not messagebox.askyesno(APP_TITLE,
                f"Plik zawiera {len(recs)} rekordów.\n"
                f"Czy chcesz {verb} aktualną bazą na serwerze?"): return
        try:
            resp = API.post(f"/api/import?mode={mode}", data)
            imported = resp.get("imported", len(recs))
            messagebox.showinfo(APP_TITLE, f"Import zakończony sukcesem!\nDodano nowych rekordów: {imported}")
            self._reload(force=True)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Błąd importu na serwer:\n{e}")

    def _apply_theme(self):
        dark = (UI.get("theme") == "dark")
        pal = _get_theme_palette(dark)

        if hasattr(self, '_user_badge'):
            self._user_badge.configure(foreground=pal["navy"])
        if hasattr(self, '_conn_lbl'):
            self._conn_lbl.configure(foreground=pal["green"] if self._conn_var.get().startswith("●") else RED)

        if hasattr(self, '_tree'):
            self._tree.tag_configure("open",  foreground=pal["open"])
            self._tree.tag_configure("fixed", foreground=pal["green"])

        if hasattr(self, '_dim_labels'):
            for lbl in self._dim_labels:
                try: lbl.configure(foreground=pal["dim"])
                except Exception: pass

        if hasattr(self, '_tree_style'):
            self._tree_style.configure("Treeview", font=FONT_REGULAR)
            self._tree_style.configure("Treeview.Heading", font=FONT_LABEL)

        if hasattr(self, '_panel_gallery'):
            try: self._panel_gallery._refresh_ui()
            except Exception: pass

        if hasattr(self, '_panel_docs'):
            try: self._panel_docs._refresh_ui()
            except Exception: pass

        if hasattr(self, '_form_gallery'):
            try: self._form_gallery._refresh_ui()
            except Exception: pass

        if hasattr(self, '_form_docs'):
            try: self._form_docs._refresh_ui()
            except Exception: pass

        self._render()

    def _toggle_theme(self):
        if not _BOOT: return
        dark = self._dark_var.get()
        UI["theme"] = "dark" if dark else "light"
        _save_cfg(UI)
        try:
            self.root.style.theme_use("darkly" if dark else "litera")
        except Exception:
            pass
        self._apply_theme()

    # ── przeładowanie danych i polling ─────────────────────────────
    def _reload(self, force=False):
        pal = _get_theme_palette(UI.get("theme") == "dark")
        try:
            self._records = API.get("/api/records")
            self._lists   = API.get("/api/lists")
            try:
                self._users_list = API.get("/api/users/list")
            except Exception:
                self._users_list = []

            self._conn_var.set("● Połączono")
            self._conn_lbl.configure(foreground=pal["green"])
            self._rebuild_combos()
            self._render()
        except Exception:
            self._conn_var.set("○ Brak połączenia")
            self._conn_lbl.configure(foreground=RED)

    def _rebuild_combos(self):
        klienci = self._lists.get("klienci",[])
        modele  = self._lists.get("modele",[])
        typy    = self._lists.get("typy",[])
        user_names = [u.get("full_name") or u.get("username") for u in self._users_list if u.get("full_name") or u.get("username")]

        self._fklient_cb.configure(values=["Wszyscy"] + klienci)
        self._ftyp_cb.configure(values=["Wszystkie"] + typy)
        self._klient_cb.configure(values=klienci)
        self._model_cb.configure(values=modele)
        self._typ_cb.configure(values=typy)
        if user_names:
            self._created_by_cb.configure(values=user_names)
            self._fixed_by_cb.configure(values=user_names)

        k = self._klient_var.get()
        if k:
            self._proj_cb.configure(values=self._lists.get("projektyByKlient",{}).get(k,[]))

    def _poll(self):
        def _bg():
            try:
                new_recs = API.get("/api/records")
                if new_recs != self._records:
                    self._records = new_recs
                    self.root.after(0, self._render)
            except Exception:
                pass
            self.root.after(5000, self._poll)
        threading.Thread(target=_bg, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════
# GŁÓWNY PUNKT WEJŚCIA (START PROGRAMU I LOGOWANIE)
# ═══════════════════════════════════════════════════════════════════
def main():
    global API, CURRENT_USER, AUTH_TOKEN
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

        if not server_url:
            server_url = UI.get("server_url", "").strip().rstrip("/")

    if is_local_forced or not server_url:
        port = _start_backend()
        API  = _Api(f"http://127.0.0.1:{port}")
    else:
        API  = _Api(server_url)


    if _BOOT:
        theme = "darkly" if UI.get("theme")=="dark" else "litera"
        root  = _TkWindow(title=APP_TITLE, themename=theme, hdpi=True, scaling=TK_SCALING)
    else:
        root = tk.Tk(); root.title(APP_TITLE)
        try: root.tk.call('tk', 'scaling', TK_SCALING)
        except Exception: pass

    root.minsize(px(1000), px(650))

    saved_token = UI.get("auth_token", "")
    auto_logged_in = False
    if saved_token:
        API.set_token(saved_token)
        try:
            resp = API.get("/api/auth/me")
            if resp.get("user"):
                CURRENT_USER = resp.get("user")
                AUTH_TOKEN   = saved_token
                auto_logged_in = True
        except Exception:
            API.set_token("")

    def show_app():
        root.deiconify()
        root.wm_state("zoomed")
        for child in root.winfo_children():
            try: child.destroy()
            except Exception: pass
        App(root, on_logout=show_login)

    def show_login():
        root.withdraw()
        def on_success(user, token):
            global CURRENT_USER, AUTH_TOKEN
            CURRENT_USER = user
            AUTH_TOKEN   = token
            show_app()
        dlg = _LoginDlg(root, on_success=on_success)
        dlg.lift()
        dlg.focus_force()

    if auto_logged_in:
        show_app()
    else:
        show_login()

    root.mainloop()


if __name__ == "__main__":
    main()