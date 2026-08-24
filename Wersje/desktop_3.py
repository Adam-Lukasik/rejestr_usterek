# desktop.py  —  Rejestr Usterek, natywne okno Tkinter + ttkbootstrap
# UI v3 — zdjęcia (BLOB w SQLite, max 3, podgląd w osobnym oknie)

import os, sys, json, sqlite3, threading, csv, base64, io
from pathlib import Path
from datetime import datetime
import uuid

import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog

# ── splash ──────────────────────────────────────────────────────────
_splash = tk.Tk()
_splash.overrideredirect(True)
_W, _H = 380, 110
_sw, _sh = _splash.winfo_screenwidth(), _splash.winfo_screenheight()
_splash.geometry(f"{_W}x{_H}+{(_sw-_W)//2}+{(_sh-_H)//2}")
_splash.configure(bg="#1B2430")
tk.Label(_splash, text="Rejestr Usterek\nUruchamianie, proszę czekać…",
         bg="#1B2430", fg="white", font=("Segoe UI", 11), justify="center"
         ).pack(expand=True, fill="both")
_splash.update()

try:
    import ttkbootstrap as ttk
    from ttkbootstrap import Window as _TkWindow
    _BOOT = True
except ImportError:
    from tkinter import ttk
    _TkWindow = None
    _BOOT = False

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

import requests

# ═══════════════════════════════════════════════════════════════════
APP_TITLE = "Rejestr Usterek"
BASE_DIR  = Path(__file__).resolve().parent
CFG_FILE  = BASE_DIR / "desktop_config.json"
DB_PATH   = BASE_DIR / "rejestr_usterek.db"

GREEN = "#2E8B57"
RED   = "#D64545"
DIM   = "#5B6572"
NAVY  = "#1B2430"
THUMB_SIZE = (90, 68)   # rozmiar miniaturki w panelu

STATUS_PL = {"open": "Otwarta", "fixed": "Naprawiona"}
_DEFAULT_CFG = {"theme": "light", "last_klient": ""}

def _load_cfg():
    if CFG_FILE.exists():
        try: return json.loads(CFG_FILE.read_text("utf-8"))
        except Exception: pass
    return dict(_DEFAULT_CFG)

def _save_cfg(c):
    try: CFG_FILE.write_text(json.dumps(c, indent=2, ensure_ascii=False), "utf-8")
    except Exception: pass

UI = _load_cfg()

# ═══════════════════════════════════════════════════════════════════
# BACKEND
# ═══════════════════════════════════════════════════════════════════
def _start_backend():
    os.chdir(BASE_DIR)
    sys.path.insert(0, str(BASE_DIR))
    from app import app as _flask, init_db, CFG
    init_db()
    port = CFG.get("PORT", 5000)
    def _run():
        _flask.run(host="127.0.0.1", port=port,
                   debug=False, use_reloader=False, threaded=True)
    threading.Thread(target=_run, daemon=True).start()
    return port

# ═══════════════════════════════════════════════════════════════════
# REST-klient
# ═══════════════════════════════════════════════════════════════════
class _Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
    def _url(self, p):     return self.base + p
    def get(self, p):      return requests.get(self._url(p), timeout=5).json()
    def post(self, p, d):  r = requests.post(self._url(p), json=d, timeout=5);  r.raise_for_status(); return r.json()
    def put(self, p, d):   r = requests.put (self._url(p), json=d, timeout=5);  r.raise_for_status(); return r.json()
    def patch(self, p, d): r = requests.patch(self._url(p), json=d, timeout=5); r.raise_for_status(); return r.json()
    def delete(self, p):   return requests.delete(self._url(p), timeout=5).json()

API: _Api

# ═══════════════════════════════════════════════════════════════════
# NARZĘDZIA OBRAZÓW
# ═══════════════════════════════════════════════════════════════════
def _make_thumb(data_bytes, size=THUMB_SIZE):
    """Zwraca PhotoImage miniaturki lub None gdy PIL niedostępny."""
    if not _PIL: return None
    try:
        img = Image.open(io.BytesIO(data_bytes))
        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def _open_full(parent, data_bytes, filename):
    """Otwiera pełne zdjęcie w osobnym oknie."""
    if not _PIL:
        messagebox.showinfo(APP_TITLE,
            "Podgląd pełnego zdjęcia wymaga biblioteki Pillow.\n"
            "Zainstaluj: pip install pillow", parent=parent)
        return
    try:
        img = Image.open(io.BytesIO(data_bytes))
    except Exception as e:
        messagebox.showerror(APP_TITLE, f"Nie można otworzyć zdjęcia:\n{e}", parent=parent)
        return
    win = tk.Toplevel(parent)
    win.title(filename)
    # skaluj do max 90% ekranu
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    max_w, max_h = int(sw*0.9), int(sh*0.9)
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img)
    lbl = tk.Label(win, image=photo, cursor="hand2")
    lbl.image = photo
    lbl.pack()
    lbl.bind("<Button-1>", lambda _: win.destroy())
    win.bind("<Escape>", lambda _: win.destroy())
    win.resizable(False, False)

# ═══════════════════════════════════════════════════════════════════
# DIALOGI ZARZĄDZANIA LISTAMI  (bez zmian)
# ═══════════════════════════════════════════════════════════════════
class _ListDlg(tk.Toplevel):
    def __init__(self, parent, title, items, on_save):
        super().__init__(parent)
        self.title(title); self.geometry("380x440")
        self.resizable(False, True); self.transient(parent); self.grab_set()
        self._items = list(items); self._on_save = on_save
        frm = ttk.Frame(self, padding=12); frm.pack(fill="both", expand=True)
        self._lb = tk.Listbox(frm, font=("Segoe UI", 10), activestyle="dotbox")
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
        self._items.append(v); self._var.set(""); self._refresh()
    def _rename(self):
        i = self._sel()
        if i is None: messagebox.showwarning(self.title(),"Zaznacz pozycję.",parent=self); return
        new = simpledialog.askstring(self.title(),"Nowa nazwa:",initialvalue=self._items[i],parent=self)
        if new and new.strip() and new.strip()!=self._items[i]:
            self._items[i]=new.strip(); self._refresh()
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
        self.title("Projekty"); self.geometry("420x480")
        self.resizable(False, True); self.transient(parent); self.grab_set()
        self._data = {k: list(v) for k, v in proj_by_klient.items()}
        self._on_save = on_save
        frm = ttk.Frame(self, padding=12); frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Klient", font=("Segoe UI",9,"bold")).pack(anchor="w")
        self._kv = tk.StringVar()
        self._kcb = ttk.Combobox(frm, textvariable=self._kv, values=klienci, state="readonly")
        self._kcb.pack(fill="x", pady=(2,10))
        if klienci: self._kcb.set(klienci[0])
        self._kcb.bind("<<ComboboxSelected>>", lambda _: self._refresh())
        self._lb = tk.Listbox(frm, font=("Segoe UI",10), activestyle="dotbox")
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
        v=self._data[k][i]
        if messagebox.askyesno(self.title(),f'Usunąć "{v}"?',parent=self):
            del self._data[k][i]; self._refresh()
    def _save(self):
        self._on_save(self._data); self.destroy()

# ═══════════════════════════════════════════════════════════════════
# WIDGET GALERII ZDJĘĆ  (reużywalny w panelu i formularzu)
# ═══════════════════════════════════════════════════════════════════
class PhotoGallery(ttk.Frame):
    """
    Pasek max 3 miniaturek z przyciskami [+] i [✕].
    Tryb 'panel'  — zdjęcia ładowane z API (record_id), tylko podgląd + usuń.
    Tryb 'form'   — zdjęcia trzymane lokalnie w pamięci (przed zapisem usterki).
    """
    MAX = 3

    def __init__(self, parent, mode="panel", **kw):
        super().__init__(parent, **kw)
        assert mode in ("panel", "form")
        self._mode      = mode
        self._record_id = None
        # lista dict: {id, filename, bytes, thumb}
        self._photos: list[dict] = []
        self._thumb_refs = []   # trzymamy referencje żeby GC nie skasował

        # nagłówek
        hdr = ttk.Frame(self); hdr.pack(fill="x")
        ttk.Label(hdr, text="Zdjęcia", font=("Segoe UI",8,"bold"),
                  foreground=DIM).pack(side="left")
        self._add_btn = ttk.Button(hdr, text="＋ Dodaj", width=8,
                                   command=self._pick_file)
        self._add_btn.pack(side="right")

        if not _PIL:
            ttk.Label(self, text="(Pillow niedostępny — zainstaluj: pip install pillow)",
                      font=("Segoe UI",7), foreground=RED).pack(anchor="w")

        # ramka miniaturek
        self._thumb_frame = ttk.Frame(self)
        self._thumb_frame.pack(fill="x", pady=(4,0))

        self._refresh_ui()

    # ── API ────────────────────────────────────────────────────────
    def load_for_record(self, record_id: str | None):
        """Wczytuje zdjęcia z serwera dla danej usterki (tryb panel)."""
        self._record_id = record_id
        self._photos = []
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
        """Zwraca listę {filename, bytes} do zapisania (tryb form)."""
        return [{"filename": p["filename"], "bytes": p["bytes"]}
                for p in self._photos]

    def clear(self):
        self._record_id = None
        self._photos = []
        self._refresh_ui()

    # ── akcje ──────────────────────────────────────────────────────
    def _pick_file(self):
        if len(self._photos) >= self.MAX:
            messagebox.showwarning(APP_TITLE, f"Maksymalnie {self.MAX} zdjęcia na usterkę."); return
        path = filedialog.askopenfilename(
            title="Wybierz zdjęcie",
            filetypes=[("Obrazy","*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
                       ("Wszystkie","*.*")])
        if not path: return
        raw = Path(path).read_bytes()
        entry = {"id": None, "filename": Path(path).name,
                 "bytes": raw, "thumb": _make_thumb(raw)}
        self._photos.append(entry)
        if self._mode == "panel" and self._record_id:
            self._upload_one(entry)
        self._refresh_ui()

    def _upload_one(self, entry: dict):
        """Wysyła jedno zdjęcie do API (tryb panel — od razu po dodaniu)."""
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
        if not messagebox.askyesno(APP_TITLE, f'Usunąć zdjęcie „{p["filename"]}"?'): return
        if self._mode == "panel" and p.get("id"):
            try: API.delete(f"/api/photos/{p['id']}")
            except Exception as e:
                messagebox.showerror(APP_TITLE, f"Błąd usuwania:\n{e}"); return
        del self._photos[idx]
        self._refresh_ui()

    def _view_photo(self, idx: int):
        p = self._photos[idx]
        _open_full(self.winfo_toplevel(), p["bytes"], p["filename"])

    # ── UI ─────────────────────────────────────────────────────────
    def _refresh_ui(self):
        for w in self._thumb_frame.winfo_children(): w.destroy()
        self._thumb_refs.clear()

        if not self._photos:
            ttk.Label(self._thumb_frame, text="Brak zdjęć",
                      font=("Segoe UI",8), foreground=DIM).pack(anchor="w")
        else:
            for idx, p in enumerate(self._photos):
                cell = ttk.Frame(self._thumb_frame)
                cell.pack(side="left", padx=(0,6), pady=2)

                if p["thumb"] and _PIL:
                    self._thumb_refs.append(p["thumb"])
                    btn = tk.Button(cell, image=p["thumb"], relief="flat",
                                    cursor="hand2", bd=1,
                                    command=lambda i=idx: self._view_photo(i))
                    btn.pack()
                else:
                    # fallback gdy PIL niedostępny
                    btn = ttk.Button(cell, text=f"📷 {p['filename'][:12]}",
                                     command=lambda i=idx: self._view_photo(i))
                    btn.pack()

                name = p["filename"]
                if len(name) > 14: name = name[:11] + "…"
                ttk.Label(cell, text=name, font=("Segoe UI",7),
                          foreground=DIM).pack()
                ttk.Button(cell, text="✕", width=3,
                           command=lambda i=idx: self._delete_photo(i)).pack()

        # przycisk Dodaj — ukryj gdy max
        if len(self._photos) >= self.MAX:
            self._add_btn.configure(state="disabled")
        else:
            self._add_btn.configure(state="normal")

# ═══════════════════════════════════════════════════════════════════
# GŁÓWNE OKNO
# ═══════════════════════════════════════════════════════════════════
class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self._records  = []
        self._lists    = {}
        self._edit_id  = None
        self._sort_col = "data"
        self._sort_rev = True

        self._build()
        self._reload()
        self._poll()

    # ── budowa UI ─────────────────────────────────────────────────
    def _build(self):
        root = self.root

        top = ttk.Frame(root, padding=(14, 8)); top.pack(fill="x")
        lbox = ttk.Frame(top); lbox.pack(side="left")
        ttk.Label(lbox, text=APP_TITLE, font=("Segoe UI",14,"bold")).pack(anchor="w")
        self._conn_var = tk.StringVar(value="● Połączono")
        self._conn_lbl = ttk.Label(lbox, textvariable=self._conn_var,
                                   font=("Segoe UI",8), foreground=GREEN)
        self._conn_lbl.pack(anchor="w")
        rbox = ttk.Frame(top); rbox.pack(side="right")
        ttk.Button(rbox, text="Zarządzaj listami", command=self._open_lists_menu).pack(side="left", padx=3)
        ttk.Button(rbox, text="Eksport CSV",       command=self._export_csv).pack(side="left", padx=3)
        ttk.Button(rbox, text="Kopia zapasowa",    command=self._backup_menu).pack(side="left", padx=3)
        ttk.Separator(root).pack(fill="x")

        self._nb = ttk.Notebook(root)
        self._nb.pack(fill="both", expand=True)
        tab_lista = ttk.Frame(self._nb, padding=(12,10))
        tab_form  = ttk.Frame(self._nb, padding=(12,10))
        self._nb.add(tab_lista, text="  Lista usterek  ")
        self._nb.add(tab_form,  text="  Dodaj usterkę  ")
        self._build_list_tab(tab_lista)
        self._build_form_tab(tab_form)

        bot = ttk.Frame(root, padding=(14,4)); bot.pack(fill="x", side="bottom")
        ttk.Separator(root).pack(fill="x", side="bottom")
        ttk.Label(bot, text="Rejestr Usterek v1.0   Created by ad.luka   email: a.lukasik@was.pl",
                  font=("Segoe UI",8), foreground=DIM).pack(side="left")
        if _BOOT:
            self._dark_var = tk.BooleanVar(value=UI.get("theme")=="dark")
            ttk.Checkbutton(bot, text="Dark mode", variable=self._dark_var,
                            command=self._toggle_theme).pack(side="right")

    # ══════════════════════════════════════════════════════════════
    # ZAKŁADKA 1 — LISTA
    # ══════════════════════════════════════════════════════════════
    def _build_list_tab(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # filtry
        frow = ttk.Frame(parent)
        frow.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,8))
        ttk.Label(frow, text="Szukaj:").pack(side="left", padx=(0,4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._render())
        ttk.Entry(frow, textvariable=self._search_var, width=24).pack(side="left", padx=(0,12))
        ttk.Label(frow, text="Klient:").pack(side="left", padx=(0,4))
        self._fklient_var = tk.StringVar(value="Wszyscy")
        self._fklient_cb  = ttk.Combobox(frow, textvariable=self._fklient_var, state="readonly", width=22)
        self._fklient_cb.pack(side="left", padx=(0,12))
        self._fklient_cb.bind("<<ComboboxSelected>>", lambda _: self._render())
        ttk.Label(frow, text="Typ:").pack(side="left", padx=(0,4))
        self._ftyp_var = tk.StringVar(value="Wszystkie")
        self._ftyp_cb  = ttk.Combobox(frow, textvariable=self._ftyp_var, state="readonly", width=18)
        self._ftyp_cb.pack(side="left", padx=(0,12))
        self._ftyp_cb.bind("<<ComboboxSelected>>", lambda _: self._render())
        ttk.Label(frow, text="Status:").pack(side="left", padx=(0,4))
        self._fstat_var = tk.StringVar(value="Wszystkie")
        fstat = ttk.Combobox(frow, textvariable=self._fstat_var, state="readonly",
                              width=14, values=["Wszystkie","Otwarta","Naprawiona"])
        fstat.pack(side="left")
        fstat.bind("<<ComboboxSelected>>", lambda _: self._render())

        # tabela
        style = ttk.Style()
        style.configure("Treeview", rowheight=36)  # Wysokość wiersza dla 2 linii tekstu

        cols = ("data","klient","model","projekt","typ","prob","fix","status")
        self._tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
        hdrs = {"data":"Data","klient":"Klient","model":"Model","projekt":"Projekt",
                "typ":"Typ","prob":"Opis problemu","fix":"Opis naprawy","status":"Status"}
        wids = {"data":118,"klient":85,"model":100,"projekt":100,
                "typ":130,"prob":260,"fix":220,"status":90}
        for c in cols:
            self._tree.heading(c, text=hdrs[c], command=lambda _c=c: self._sort(_c))
            self._tree.column(c, width=wids[c], anchor="w",
                              stretch=(c in ("prob","fix")))
        self._tree.tag_configure("open",  foreground="#996600")
        self._tree.tag_configure("fixed", foreground=GREEN)
        self._tree.grid(row=1, column=0, sticky="nsew")
        self._tree.bind("<<TreeviewSelect>>", lambda _: self._on_select())
        self._tree.bind("<Double-1>",          lambda _: self._edit_selected())
        sc = ttk.Scrollbar(parent, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sc.set)
        sc.grid(row=1, column=1, sticky="ns")

        # panel szczegółów (z przewijaniem)
        detail_outer = ttk.Labelframe(parent, text="Szczegóły", padding=0)
        detail_outer.grid(row=1, column=2, sticky="nsew", padx=(10,0))
        parent.columnconfigure(2, weight=0, minsize=290)

        canvas = tk.Canvas(detail_outer, width=272, highlightthickness=0)
        sb = ttk.Scrollbar(detail_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        detail = ttk.Frame(canvas, padding=10)
        _cwin  = canvas.create_window((0,0), window=detail, anchor="nw")
        def _on_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(_cwin, width=canvas.winfo_width())
        detail.bind("<Configure>", _on_conf)

        def _lbl(t):
            ttk.Label(detail, text=t, font=("Segoe UI",8,"bold"),
                      foreground=DIM).pack(anchor="w", pady=(8,0))
        def _val(var):
            ttk.Label(detail, textvariable=var, wraplength=240,
                      justify="left", font=("Segoe UI",9)).pack(anchor="w")

        self._dv = {k: tk.StringVar() for k in
            ["klient","model","projekt","vin","typ","elem","status","data","prob","fix"]}
        _lbl("Klient");      _val(self._dv["klient"])
        _lbl("Model");       _val(self._dv["model"])
        _lbl("Projekt");     _val(self._dv["projekt"])
        _lbl("VIN");         _val(self._dv["vin"])
        _lbl("Typ usterki"); _val(self._dv["typ"])
        _lbl("Element");     _val(self._dv["elem"])
        _lbl("Status")
        self._det_st_lbl = ttk.Label(detail, textvariable=self._dv["status"],
                                      font=("Segoe UI",9,"bold"))
        self._det_st_lbl.pack(anchor="w")
        _lbl("Data");        _val(self._dv["data"])
        ttk.Separator(detail).pack(fill="x", pady=(10,2))
        _lbl("Opis problemu"); _val(self._dv["prob"])
        ttk.Separator(detail).pack(fill="x", pady=(8,2))
        _lbl("Opis naprawy");  _val(self._dv["fix"])
        ttk.Separator(detail).pack(fill="x", pady=(8,2))

        # galeria w panelu szczegółów
        self._panel_gallery = PhotoGallery(detail, mode="panel")
        self._panel_gallery.pack(fill="x", pady=(4,0))

        self._clear_detail()

        # przyciski
        arow = ttk.Frame(parent)
        arow.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8,0))
        ttk.Button(arow, text="✎ Edytuj",       command=self._edit_selected).pack(side="left", padx=(0,4))
        ttk.Button(arow, text="⇄ Zmień status", command=self._toggle_status).pack(side="left", padx=(0,4))
        ttk.Button(arow, text="✕ Usuń",         command=self._delete_selected).pack(side="left")

    # ══════════════════════════════════════════════════════════════
    # ZAKŁADKA 2 — FORMULARZ
    # ══════════════════════════════════════════════════════════════
    def _build_form_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        self._form_title_var = tk.StringVar(value="Nowa usterka")
        ttk.Label(parent, textvariable=self._form_title_var,
                  font=("Segoe UI",12,"bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0,14))

        # lewa: identyfikacja
        left = ttk.Labelframe(parent, text="Identyfikacja", padding=14)
        left.grid(row=1, column=0, sticky="nsew", padx=(0,8))
        left.columnconfigure(1, weight=1)

        def lrow(frm, label, w_fn, r):
            ttk.Label(frm, text=label, font=("Segoe UI",9,"bold")).grid(
                row=r, column=0, sticky="w", padx=(0,10), pady=(6,2))
            w = w_fn(frm)
            w.grid(row=r, column=1, sticky="ew", pady=(6,2))
            return w

        r = 0
        self._klient_var = tk.StringVar()
        self._klient_cb  = lrow(left,"Klient",
            lambda p: ttk.Combobox(p, textvariable=self._klient_var, state="readonly"), r); r+=1
        self._klient_cb.bind("<<ComboboxSelected>>", lambda _: self._on_klient_changed())
        self._model_var = tk.StringVar()
        self._model_cb  = lrow(left,"Model",
            lambda p: ttk.Combobox(p, textvariable=self._model_var), r); r+=1
        self._proj_var = tk.StringVar()
        self._proj_cb  = lrow(left,"Projekt",
            lambda p: ttk.Combobox(p, textvariable=self._proj_var), r); r+=1
        self._vin_var = tk.StringVar()
        lrow(left,"VIN  (opcjonalnie)",
            lambda p: ttk.Entry(p, textvariable=self._vin_var), r); r+=1
        self._typ_var = tk.StringVar()
        self._typ_cb  = lrow(left,"Typ usterki",
            lambda p: ttk.Combobox(p, textvariable=self._typ_var, state="readonly"), r); r+=1
        self._elem_var = tk.StringVar()
        lrow(left,"Element / urządzenie",
            lambda p: ttk.Entry(p, textvariable=self._elem_var), r); r+=1
        self._status_var = tk.StringVar(value="Otwarta")
        lrow(left,"Status",
            lambda p: ttk.Combobox(p, textvariable=self._status_var, state="readonly",
                                   values=["Otwarta","Naprawiona"]), r)

        # prawa: opisy + zdjęcia
        right = ttk.Labelframe(parent, text="Opisy i zdjęcia", padding=14)
        right.grid(row=1, column=1, sticky="nsew", padx=(8,0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=2)
        right.rowconfigure(3, weight=1)

        ttk.Label(right, text="Opis problemu *",
                  font=("Segoe UI",9,"bold")).grid(row=0, column=0, sticky="w", pady=(0,4))
        self._prob_txt = tk.Text(right, height=8, wrap="word", font=("Segoe UI",10))
        self._prob_txt.grid(row=1, column=0, sticky="nsew")

        ttk.Label(right, text="Opis naprawy",
                  font=("Segoe UI",9,"bold")).grid(row=2, column=0, sticky="w", pady=(10,4))
        self._fix_txt = tk.Text(right, height=5, wrap="word", font=("Segoe UI",10))
        self._fix_txt.grid(row=3, column=0, sticky="nsew")

        ttk.Separator(right).grid(row=4, column=0, sticky="ew", pady=(10,6))

        # galeria w formularzu
        self._form_gallery = PhotoGallery(right, mode="form")
        self._form_gallery.grid(row=5, column=0, sticky="ew")

        # przyciski
        brow = ttk.Frame(parent)
        brow.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14,0))
        self._save_btn = ttk.Button(brow, text="Zapisz", command=self._save_form)
        self._save_btn.pack(side="left", padx=(0,8))
        ttk.Button(brow, text="Wyczyść", command=self._clear_form).pack(side="left")

    # ── panel szczegółów ─────────────────────────────────────────
    def _clear_detail(self):
        for v in self._dv.values(): v.set("—")
        self._det_st_lbl.configure(foreground=DIM)
        self._panel_gallery.clear()

    def _on_select(self):
        self._show_detail()

    def _show_detail(self):
        r = self._selected()
        if not r: self._clear_detail(); return
        self._dv["klient"] .set(r.get("klient","")  or "—")
        self._dv["model"]  .set(r.get("model","")   or "—")
        self._dv["projekt"].set(r.get("projekt","") or "—")
        self._dv["vin"]    .set(r.get("vin","")      or "—")
        self._dv["typ"]    .set(r.get("typ","")      or "—")
        self._dv["elem"]   .set(r.get("element","") or "—")
        self._dv["data"]   .set(self._fmt_dt(r.get("created","")))
        self._dv["prob"]   .set(r.get("opisProblem","") or "—")
        self._dv["fix"]    .set(r.get("opisNaprawa","") or "—")
        st = r.get("status","open")
        self._dv["status"].set(STATUS_PL.get(st, st))
        self._det_st_lbl.configure(foreground=GREEN if st=="fixed" else "#996600")
        self._panel_gallery.load_for_record(r["id"])

    # ── dane ──────────────────────────────────────────────────────
    def _reload(self):
        sel = self._tree.selection()
        sel_id = sel[0] if sel else None
        try:
            self._records = API.get("/api/records")
            self._lists   = API.get("/api/lists") or {}
            self._set_conn(True)
        except Exception:
            self._set_conn(False); return
        self._rebuild_combos()
        self._render()
        if sel_id and self._tree.exists(sel_id):
            self._tree.selection_set(sel_id)
            self._tree.see(sel_id)
            self._show_detail()

    def _set_conn(self, ok):
        if ok:
            self._conn_var.set("● Połączono");    self._conn_lbl.configure(foreground=GREEN)
        else:
            self._conn_var.set("● Brak połączenia"); self._conn_lbl.configure(foreground=RED)

    def _poll(self):
        self._reload()
        self.root.after(5000, self._poll)

    def _rebuild_combos(self):
        klienci = self._lists.get("klienci",[])
        self._klient_cb .configure(values=klienci)
        self._model_cb  .configure(values=self._lists.get("modele",[]))
        self._typ_cb    .configure(values=self._lists.get("typy",[]))
        self._fklient_cb.configure(values=["Wszyscy"]+klienci)
        self._ftyp_cb   .configure(values=["Wszystkie"]+self._lists.get("typy",[]))
        if not self._edit_id and not self._klient_var.get():
            last = UI.get("last_klient","")
            if last in klienci: self._klient_var.set(last)
        self._rebuild_proj()

    def _rebuild_proj(self):
        k = self._klient_var.get()
        self._proj_cb.configure(values=self._lists.get("projektyByKlient",{}).get(k,[]))

    def _on_klient_changed(self):
        UI["last_klient"] = self._klient_var.get()
        _save_cfg(UI)
        self._rebuild_proj()

    # ── renderowanie ──────────────────────────────────────────────
    def _render(self):
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
                     "opisProblem","opisNaprawa","typ"]).lower()
                if q not in hay: continue
            rows.append(r)
        col_key = "created" if self._sort_col == "data" else self._sort_col
        rows.sort(key=lambda r: str(r.get(col_key,"")), reverse=self._sort_rev)
        arrow = " ▼" if self._sort_rev else " ▲"
        hdrs  = {"data":"Data","klient":"Klient","model":"Model","projekt":"Projekt",
                 "typ":"Typ","prob":"Opis problemu","fix":"Opis naprawy","status":"Status"}
        for c in hdrs:
            self._tree.heading(c, text=hdrs[c]+(arrow if c==self._sort_col else ""))

        def snip_klient(t, n=10):
            t = (t or "").strip()
            return t[:n] + "…" if len(t) > n else t

        def snip_multi(t, n=120):
            if not t:
                return ""
            t = " ".join(t.split())
            if len(t) > n:
                t = t[:n] + "…"
            # Dzielenie tekstu na 2 wiersze w okolicy 55. znaku
            if len(t) > 55 and "\n" not in t:
                space_idx = t.rfind(" ", 0, 55)
                if space_idx > 15:
                    t = t[:space_idx] + "\n" + t[space_idx+1:]
                else:
                    t = t[:55] + "\n" + t[55:]
            return t

        for r in rows:
            self._tree.insert("","end", iid=r["id"], tags=(r.get("status","open"),),
                values=(self._fmt_dt(r.get("created","")),
                        snip_klient(r.get("klient","")),
                        r.get("model",""),
                        r.get("projekt",""), r.get("typ",""),
                        snip_multi(r.get("opisProblem","")),
                        snip_multi(r.get("opisNaprawa","")),
                        STATUS_PL.get(r.get("status","open"),r.get("status",""))))

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

    # ── formularz ─────────────────────────────────────────────────
    def _save_form(self):
        klient = self._klient_var.get().strip()
        model  = self._model_var.get().strip()
        typ    = self._typ_var.get().strip()
        prob   = self._prob_txt.get("1.0","end").strip()
        if not all([klient, model, typ, prob]):
            messagebox.showwarning(APP_TITLE,
                "Uzupełnij wymagane pola: Klient, Model, Typ, Opis problemu."); return
        status = "open" if self._status_var.get()=="Otwarta" else "fixed"
        rec_id = self._edit_id or str(uuid.uuid4())
        payload = dict(klient=klient, model=model,
                       projekt=self._proj_var.get().strip(),
                       vin=self._vin_var.get().strip(),
                       typ=typ, element=self._elem_var.get().strip(),
                       opisProblem=prob,
                       opisNaprawa=self._fix_txt.get("1.0","end").strip(),
                       status=status)
        try:
            if self._edit_id:
                API.put(f"/api/records/{rec_id}", payload)
            else:
                payload["id"]      = rec_id
                payload["created"] = datetime.now().isoformat(timespec="seconds")
                API.post("/api/records", payload)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Błąd zapisu:\n{e}"); return

        # wyślij oczekujące zdjęcia z formularza
        for p in self._form_gallery.get_pending():
            try:
                API.post(f"/api/records/{rec_id}/photos", {
                    "filename": p["filename"],
                    "data": base64.b64encode(p["bytes"]).decode()
                })
            except Exception as e:
                messagebox.showwarning(APP_TITLE, f"Usterka zapisana, ale zdjęcie „{p['filename']}\" nie:\n{e}")

        self._auto_add_to_lists(klient, model, typ, payload["projekt"])
        self._clear_form()
        self._reload()
        self._nb.select(0)

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

    def _clear_form(self):
        self._edit_id = None
        self._form_title_var.set("Nowa usterka")
        self._save_btn.configure(text="Zapisz")
        for v in [self._model_var, self._proj_var, self._vin_var,
                  self._typ_var, self._elem_var]:
            v.set("")
        self._prob_txt.delete("1.0","end")
        self._fix_txt.delete("1.0","end")
        self._status_var.set("Otwarta")
        self._form_gallery.clear()

    def _edit_selected(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę na liście."); return
        self._edit_id = r["id"]
        self._form_title_var.set(f"Edycja — {r.get('klient','')} / {r.get('typ','')}")
        self._save_btn.configure(text="Zapisz zmiany")
        self._klient_var.set(r.get("klient",""))
        self._rebuild_proj()
        self._model_var.set(r.get("model",""))
        self._proj_var.set(r.get("projekt",""))
        self._vin_var.set(r.get("vin",""))
        self._typ_var.set(r.get("typ",""))
        self._elem_var.set(r.get("element",""))
        self._prob_txt.delete("1.0","end"); self._prob_txt.insert("1.0", r.get("opisProblem",""))
        self._fix_txt.delete("1.0","end");  self._fix_txt.insert("1.0",  r.get("opisNaprawa",""))
        self._status_var.set(STATUS_PL.get(r.get("status","open"),"Otwarta"))
        # wczytaj istniejące zdjęcia do galerii formularza
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
        self._nb.select(1)

    def _toggle_status(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę."); return
        new = "fixed" if r.get("status")=="open" else "open"
        try: API.patch(f"/api/records/{r['id']}/status", {"status": new})
        except Exception as e: messagebox.showerror(APP_TITLE, str(e)); return
        self._reload()

    def _delete_selected(self):
        r = self._selected()
        if not r: messagebox.showinfo(APP_TITLE,"Zaznacz usterkę."); return
        if not messagebox.askyesno(APP_TITLE,"Usunąć tę usterkę wraz ze zdjęciami? Operacja jest nieodwracalna."): return
        try: API.delete(f"/api/records/{r['id']}")
        except Exception as e: messagebox.showerror(APP_TITLE, str(e)); return
        self._reload()

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
                "element","opisProblem","opisNaprawa","status"]
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
        m.add_command(label="Eksportuj kopię (JSON)",  command=self._backup_export)
        m.add_command(label="Importuj kopię — scal",   command=lambda: self._backup_import("merge"))
        m.add_command(label="Importuj kopię — zastąp", command=lambda: self._backup_import("replace"))
        try:   m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally: m.grab_release()

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
                f"Czy chcesz {verb} aktualną bazą?"): return
        conn = sqlite3.connect(DB_PATH)
        try:
            if mode=="replace":
                conn.execute("DELETE FROM records"); conn.execute("DELETE FROM lists")
            for r in recs:
                conn.execute("""INSERT OR IGNORE INTO records
                    (id,created,klient,model,projekt,vin,typ,element,opisProblem,opisNaprawa,status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.get("id"),r.get("created"),r.get("klient"),r.get("model"),
                     r.get("projekt"),r.get("vin"),r.get("typ"),r.get("element"),
                     r.get("opisProblem"),r.get("opisNaprawa"),r.get("status","open")))
            conn.execute("INSERT OR REPLACE INTO lists (key,value) VALUES ('lists',?)",
                         (json.dumps(lists),))
            conn.commit()
        finally:
            conn.close()
        messagebox.showinfo(APP_TITLE,"Import zakończony.")
        self._reload()

    def _toggle_theme(self):
        if not _BOOT: return
        dark = self._dark_var.get()
        UI["theme"] = "dark" if dark else "light"
        _save_cfg(UI)
        try: self.root.style.theme_use("darkly" if dark else "litera")
        except Exception: pass

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    global API
    port = _start_backend()
    API  = _Api(f"http://127.0.0.1:{port}")
    _splash.destroy()

    if _BOOT:
        theme = "darkly" if UI.get("theme")=="dark" else "litera"
        root  = _TkWindow(title=APP_TITLE, themename=theme, hdpi=False)
    else:
        root = tk.Tk(); root.title(APP_TITLE)

    root.minsize(1000, 650)
    root.wm_state("zoomed")
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()