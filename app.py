import os
import sys
import sqlite3
import json
import base64
import hashlib
import secrets
import smtplib
import io
import urllib.request
import urllib.parse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid as _uuid
from datetime import datetime as _dt, timedelta as _td
from functools import wraps
from flask import Flask, send_from_directory, request, jsonify, Response


def translate_pl_to_en(text: str) -> str:
    """Automatycznie tłumaczy tekst z języka polskiego na angielski."""
    if not text or not str(text).strip():
        return ""
    text_str = str(text).strip()
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=pl&tl=en&dt=t&q=" + urllib.parse.quote(text_str)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode("utf-8"))
            translated = "".join([segment[0] for segment in data[0] if segment and segment[0]])
            return translated.strip()
    except Exception as e:
        print(f"[TRANSLATE ERROR] Nie udało się przetłumaczyć na EN: {e}")
        return ""


try:
    from PIL import Image as _PILImage
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

def generate_pdf_thumb_bytes(raw_pdf_bytes: bytes, max_size=(160, 200)) -> bytes:
    """Generuje miniaturkę JPG 1. strony PDF przy użyciu pypdfium2."""
    if not _PIL_OK or not raw_pdf_bytes:
        return None
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(raw_pdf_bytes)
        if len(pdf) == 0:
            return None
        page = pdf[0]
        pil_img = page.render(scale=1.5).to_pil()
        pil_img.thumbnail(max_size, _PILImage.Resampling.LANCZOS)
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception as e:
        return None

def optimize_image_bytes(raw_bytes: bytes, max_dim: int = 1920, quality: int = 85) -> bytes:
    """Automatycznie przeskalowuje i kompresuje zdjęcie (JPEG 85%, max 1920px), redukując rozmiar o ~90%."""
    if not _PIL_OK or not raw_bytes:
        return raw_bytes
    try:
        img = _PILImage.open(io.BytesIO(raw_bytes))
        if img.mode in ('RGBA', 'P', 'LA'):
            bg = _PILImage.new('RGB', img.size, (255, 255, 255))
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
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        res = buf.getvalue()
        if len(res) < len(raw_bytes):
            return res
        return raw_bytes
    except Exception:
        return raw_bytes

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    cfg = {
        "DB_PATH": "rejestr_usterek.db",
        "HOST": "0.0.0.0",
        "PORT": 5000,
        "SECRET_BACKUP_DIR": "",
        "SMTP": {
            "ENABLED": False,
            "SERVER": "smtp.twojafirma.pl",
            "PORT": 587,
            "USE_TLS": True,
            "USER": "rejestr-usterek@twojafirma.pl",
            "PASSWORD": "",
            "SENDER_NAME": "Rejestr Usterek — Powiadomienia"
        }
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print(f"[CFG] Błąd wczytywania config.json: {e}")
    return cfg

CFG = load_config()

# Ścieżka do pliku bazy SQLite
DB_PATH = CFG.get("DB_PATH", "rejestr_usterek.db")
if not os.path.isabs(DB_PATH):
    DB_PATH = os.path.join(BASE_DIR, DB_PATH)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ═══════════════════════════════════════════════════════════════════
# BEZPIECZEŃSTWO I HASZOWANIE HASEŁ
# ═══════════════════════════════════════════════════════════════════
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Zwraca (hash_hex, salt_hex) używając PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100_000
    ).hex()
    return pw_hash, salt

def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Weryfikuje hasło względem zapisanego hasha i soli."""
    pw_hash, _ = hash_password(password, stored_salt)
    return secrets.compare_digest(pw_hash, stored_hash)

def get_user_from_token(token: str):
    """Zwraca słownik z danymi użytkownika lub None jeśli token jest nieprawidłowy/wygasł."""
    if not token:
        return None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, u.email, u.phone, u.role, u.is_active, u.must_change_password, t.expires_at
            FROM auth_tokens t
            JOIN users u ON t.user_id = u.id
            WHERE t.token = ? AND u.is_active = 1
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return None
        expires_at = _dt.fromisoformat(row["expires_at"])
        if _dt.now() > expires_at:
            cursor.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
            conn.commit()
            return None
        return dict(row)
    finally:
        conn.close()

def get_current_user():
    """Pobiera aktualnie zalogowanego użytkownika z nagłówka Authorization lub parametru token."""
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "X-Auth-Token" in request.headers:
        token = request.headers.get("X-Auth-Token", "").strip()
    else:
        token = request.args.get("token", "").strip()
    return get_user_from_token(token)

def send_reset_email(to_email: str, username: str, code: str) -> tuple[bool, str]:
    """Wysyła 6-cyfrowy kod resetu hasła przez SMTP."""
    smtp_cfg = CFG.get("SMTP", {})
    if not smtp_cfg.get("ENABLED"):
        return False, "Obsługa SMTP jest wyłączona w konfiguracji serwera."
    if not to_email or "@" not in to_email:
        return False, "Użytkownik nie posiada prawidłowego adresu e-mail."

    server_host = smtp_cfg.get("SERVER", "")
    port = smtp_cfg.get("PORT", 587)
    user = smtp_cfg.get("USER", "")
    password = smtp_cfg.get("PASSWORD", "")
    sender_name = smtp_cfg.get("SENDER_NAME", "Rejestr Usterek")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Kod resetowania hasła — Rejestr Usterek: {code}"
    msg["From"] = f"{sender_name} <{user}>"
    msg["To"] = to_email

    text_content = f"""Witaj {username},

Otrzymaliśmy prośbę o zresetowanie hasła do Twojego konta w systemie Rejestr Usterek.

Twój jednorazowy kod weryfikacyjny to:
====================
   {code}
====================

Kod jest ważny przez 15 minut.
Jeśli to nie Ty prosiłeś o reset hasła, zignoruj tę wiadomość.

Pozdrawiamy,
Zespół Rejestru Usterek
"""
    msg.attach(MIMEText(text_content, "plain", "utf-8"))

    try:
        if smtp_cfg.get("USE_TLS", True):
            server = smtplib.SMTP(server_host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(server_host, port, timeout=10)

        if user and password:
            server.login(user, password)
        server.sendmail(user, [to_email], msg.as_string())
        server.quit()
        return True, "Wiadomość z kodem została wysłana."
    except Exception as e:
        return False, f"Błąd wysyłania e-mail: {str(e)}"

# ═══════════════════════════════════════════════════════════════════
# INICJALIZACJA BAZY DANYCH I MIGRACJE
# ═══════════════════════════════════════════════════════════════════
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabela rekordów usterek
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            created TEXT NOT NULL,
            klient TEXT NOT NULL,
            model TEXT NOT NULL,
            projekt TEXT NOT NULL,
            vin TEXT,
            typ TEXT NOT NULL,
            element TEXT,
            opisProblem TEXT NOT NULL,
            opisNaprawa TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_by TEXT,
            fixed_by TEXT,
            fixed_at TEXT,
            opisProblem_en TEXT,
            opisNaprawa_en TEXT
        )
    """)

    # Sprawdzenie czy istnieją nowe kolumny w starych bazach (migracja w locie)
    cursor.execute("PRAGMA table_info(records)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "created_by" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN created_by TEXT")
    if "fixed_by" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN fixed_by TEXT")
    if "fixed_at" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN fixed_at TEXT")
    if "opisProblem_en" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN opisProblem_en TEXT")
    if "opisNaprawa_en" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN opisNaprawa_en TEXT")

    # 2. Tabela słowników
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lists (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # 3. Tabela zdjęć
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            record_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            data BLOB NOT NULL,
            created TEXT NOT NULL
        )
    """)

    # 4. Tabela dokumentów
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            record_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filesize INTEGER NOT NULL DEFAULT 0,
            data BLOB NOT NULL,
            created TEXT NOT NULL
        )
    """)

    # 5. Tabela użytkowników
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'technik',
            is_active INTEGER NOT NULL DEFAULT 1,
            must_change_password INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # 6. Tabela tokenów sesji
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    # 7. Tabela kodów resetu hasła
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_codes (
            code TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    # 8. Warianty rozwiązań usterki
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solutions (
            id TEXT PRIMARY KEY,
            record_id TEXT NOT NULL,
            numer INTEGER NOT NULL DEFAULT 1,
            tytul TEXT NOT NULL,
            opis TEXT,
            created_by TEXT,
            created TEXT NOT NULL,
            tytul_en TEXT,
            opis_en TEXT,
            FOREIGN KEY (record_id) REFERENCES records(id)
        )
    """)

    cursor.execute("PRAGMA table_info(solutions)")
    sol_columns = [col["name"] for col in cursor.fetchall()]
    if "tytul_en" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN tytul_en TEXT")
    if "opis_en" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN opis_en TEXT")

    # 9. Zdjęcia przypisane do wariantu rozwiązania
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solution_photos (
            id TEXT PRIMARY KEY,
            solution_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            data BLOB NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY (solution_id) REFERENCES solutions(id)
        )
    """)

    # 10. Dokumenty przypisane do wariantu rozwiązania
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solution_documents (
            id TEXT PRIMARY KEY,
            solution_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filesize INTEGER NOT NULL DEFAULT 0,
            data BLOB NOT NULL,
            created TEXT NOT NULL,
            FOREIGN KEY (solution_id) REFERENCES solutions(id)
        )
    """)

    # Migracja: przenieś opisNaprawa do tabeli solutions jako "Wariant 1"
    # oraz przypisz pierwsze zdjęcie do usterki, a kolejne zdjęcia (od 2 wzwyż) do Wariantu 1
    # (tylko dla rekordów które mają opis naprawy, a nie mają jeszcze żadnych wariantów)
    cursor.execute("""
        SELECT r.id, r.opisNaprawa, r.fixed_by, r.fixed_at
        FROM records r
        WHERE r.opisNaprawa IS NOT NULL AND r.opisNaprawa != ''
          AND NOT EXISTS (SELECT 1 FROM solutions s WHERE s.record_id = r.id)
    """)
    to_migrate = cursor.fetchall()
    migrated_photos_count = 0
    for row in to_migrate:
        sol_id = str(_uuid.uuid4())
        cursor.execute("""
            INSERT INTO solutions (id, record_id, numer, tytul, opis, created_by, created)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sol_id,
            row["id"],
            1,
            "Wariant 1",
            row["opisNaprawa"],
            row["fixed_by"] or "",
            row["fixed_at"] or _dt.now().isoformat(timespec="seconds")
        ))

        # Migracja zdjęć: 1. zdjęcie zostaje w 'photos' (opis problemu),
        # a zdjęcia 2..N trafiają do 'solution_photos' (Wariant 1)
        cursor.execute("""
            SELECT id, filename, data, created
            FROM photos
            WHERE record_id = ?
            ORDER BY created ASC, id ASC
        """, (row["id"],))
        rec_photos = cursor.fetchall()
        if len(rec_photos) > 1:
            for p in rec_photos[1:]:
                cursor.execute("""
                    INSERT INTO solution_photos (id, solution_id, filename, data, created)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    p["id"],
                    sol_id,
                    p["filename"],
                    p["data"],
                    p["created"]
                ))
                cursor.execute("DELETE FROM photos WHERE id = ?", (p["id"],))
                migrated_photos_count += 1

    if to_migrate:
        print(f"[MIGRATION] Zmigrowano opisNaprawa do tabeli solutions: {len(to_migrate)} rekordów, przeniesiono {migrated_photos_count} zdjęć do wariantów.")

    # Migracja dokumentów: przenieś istniejące dokumenty z tabeli 'documents' do 'solution_documents' (Wariant 1)
    cursor.execute("SELECT id, record_id, filename, filesize, data, created FROM documents")
    docs_to_migrate = cursor.fetchall()
    migrated_docs_count = 0
    for doc in docs_to_migrate:
        cursor.execute("SELECT id FROM solutions WHERE record_id = ? ORDER BY numer ASC LIMIT 1", (doc["record_id"],))
        sol_row = cursor.fetchone()
        if sol_row:
            cursor.execute("""
                INSERT OR REPLACE INTO solution_documents (id, solution_id, filename, filesize, data, created)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (doc["id"], sol_row["id"], doc["filename"], doc["filesize"], doc["data"], doc["created"]))
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc["id"],))
            migrated_docs_count += 1
    if migrated_docs_count > 0:
        print(f"[MIGRATION] Przeniesiono {migrated_docs_count} dokumentów z usterki do 'solution_documents' (Wariant 1).")

    # Migracja kolumn w tabeli users
    cursor.execute("PRAGMA table_info(users)")
    u_cols = [c["name"] for c in cursor.fetchall()]
    if "email" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "phone" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "must_change_password" not in u_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0")

    # Bootstrap domyślnego administratora jeśli brak użytkowników
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()["count"] == 0:
        admin_id = str(_uuid.uuid4())
        pw_hash, salt = hash_password("admin123")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, salt, full_name, email, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            admin_id,
            "admin",
            pw_hash,
            salt,
            "Administrator Główny",
            "",
            "admin",
            1,
            _dt.now().isoformat(timespec="seconds")
        ))
        print("[AUTH] Utworzono początkowe konto administratora (login: admin, hasło: admin123)")

    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════
# ENDPOINTY AUTORYZACJI I PROFILU
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "rejestr_usterek.html")

@app.route("/translations.js")
def translations_js():
    return send_from_directory(BASE_DIR, "translations.js")

@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json() or {}
    text = data.get("text", "")
    translated = translate_pl_to_en(text)
    return jsonify({"translated": translated})

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Podaj login i hasło."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, password_hash, salt, full_name, email, phone, role, is_active, must_change_password
        FROM users
        WHERE LOWER(username) = ?
    """, (username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "Nieprawidłowy login lub hasło."}), 401

    if not user["is_active"]:
        conn.close()
        return jsonify({"error": "To konto zostało zablokowane. Skontaktuj się z Administratorem."}), 403

    if not verify_password(password, user["password_hash"], user["salt"]):
        conn.close()
        return jsonify({"error": "Nieprawidłowy login lub hasło."}), 401

    # Wygeneruj token (ważny np. 30 dni)
    token = secrets.token_urlsafe(32)
    now = _dt.now()
    expires = now + _td(days=30)

    cursor.execute("""
        INSERT INTO auth_tokens (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """, (token, user["id"], now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")))
    conn.commit()
    conn.close()

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"] or "",
            "phone": user["phone"] or "",
            "role": user["role"],
            "must_change_password": bool(user["must_change_password"])
        }
    })

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Niezalogowany lub sesja wygasła."}), 401
    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"] or "",
            "phone": user.get("phone") or "",
            "role": user["role"],
            "must_change_password": bool(user.get("must_change_password", 0))
        }
    })

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if token:
        conn = get_db_connection()
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/auth/change-password", methods=["POST"])
def auth_change_password():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Wymagane zalogowanie."}), 401

    data = request.get_json() or {}
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")

    if not new_pw or len(new_pw) < 4:
        return jsonify({"error": "Nowe hasło musi mieć co najmniej 4 znaki."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, must_change_password FROM users WHERE id = ?", (user["id"],))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Nie znaleziono użytkownika."}), 404

    # Jeśli użytkownik nie jest w trybie wymuszonej zmiany, wymagaj podania poprawnego starego hasła
    if not row["must_change_password"]:
        if not old_pw or not verify_password(old_pw, row["password_hash"], row["salt"]):
            conn.close()
            return jsonify({"error": "Aktualne hasło jest nieprawidłowe."}), 400

    new_hash, new_salt = hash_password(new_pw)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
                   (new_hash, new_salt, user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Hasło zostało pomyślnie zmienione."})

@app.route("/api/auth/request-reset", methods=["POST"])
def auth_request_reset():
    """Generuje 6-cyfrowy kod i opcjonalnie wysyła e-mail."""
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip().lower()
    if not identifier:
        return jsonify({"error": "Podaj login lub adres e-mail."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, full_name, email, is_active
        FROM users
        WHERE LOWER(username) = ? OR LOWER(email) = ?
    """, (identifier, identifier))
    user = cursor.fetchone()

    if not user or not user["is_active"]:
        conn.close()
        # Ze względów bezpieczeństwa nie ujawniamy czy użytkownik istnieje
        return jsonify({
            "status": "ok",
            "message": "Jeśli podany login/e-mail istnieje w bazie, wysłano kod weryfikacyjny lub skontaktuj się z Administratorem."
        })

    # Wygeneruj 6-cyfrowy kod PIN
    code = f"{secrets.randbelow(900000) + 100000}"
    now = _dt.now()
    expires = now + _td(minutes=15)

    # Wyczyść stare kody dla tego usera
    cursor.execute("DELETE FROM password_reset_codes WHERE user_id = ?", (user["id"],))
    cursor.execute("""
        INSERT INTO password_reset_codes (code, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    """, (code, user["id"], now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")))
    conn.commit()
    conn.close()

    sent, msg = send_reset_email(user["email"], user["full_name"], code)
    return jsonify({
        "status": "ok",
        "email_sent": sent,
        "has_email": bool(user["email"]),
        "message": msg if sent else "Kod został wygenerowany. W przypadku braku skonfigurowanej poczty poproś Administratora o bezpośredni reset hasła."
    })

@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip()
    new_pw = data.get("new_password", "")

    if not code or not new_pw:
        return jsonify({"error": "Podaj kod weryfikacyjny i nowe hasło."}), 400
    if len(new_pw) < 4:
        return jsonify({"error": "Nowe hasło musi mieć co najmniej 4 znaki."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT code, user_id, expires_at FROM password_reset_codes WHERE code = ?
    """, (code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Nieprawidłowy lub wygasły kod weryfikacyjny."}), 400

    expires_at = _dt.fromisoformat(row["expires_at"])
    if _dt.now() > expires_at:
        cursor.execute("DELETE FROM password_reset_codes WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return jsonify({"error": "Kod weryfikacyjny wygasł (ważność 15 minut)."}), 400

    user_id = row["user_id"]
    new_hash, new_salt = hash_password(new_pw)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
                   (new_hash, new_salt, user_id))
    cursor.execute("DELETE FROM password_reset_codes WHERE user_id = ?", (user_id,))
    # Unieważnij wszystkie aktywne sesje tego użytkownika
    cursor.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": "Hasło zostało pomyślnie zresetowane. Możesz się zalogować."})

# ═══════════════════════════════════════════════════════════════════
# ZARZĄDZANIE UŻYTKOWNIKAMI
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/users/list", methods=["GET"])
def get_public_users_list():
    """Zwraca listę aktywnych użytkowników do wyboru w formularzach i przy oznaczaniu naprawy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, full_name, role
        FROM users
        WHERE is_active = 1
        ORDER BY full_name ASC, username ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/users", methods=["GET"])

def get_users():
    user = get_current_user()
    if not user or user.get("role") != "admin":
        return jsonify({"error": "Wymagane uprawnienia administratora."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, full_name, email, phone, role, is_active, must_change_password, created_at
        FROM users
        ORDER BY role ASC, username ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/users", methods=["POST"])
def create_user():
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": "Wymagane uprawnienia administratora."}), 403

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = data.get("role", "technik")
    password = data.get("password", "")
    must_change = 1 if data.get("must_change_password", True) else 0

    if not username or not full_name:
        return jsonify({"error": "Pola 'Login' oraz 'Imię i Nazwisko' są wymagane."}), 400
    if not password or len(password) < 4:
        return jsonify({"error": "Hasło musi mieć co najmniej 4 znaki."}), 400
    if role not in ("admin", "technik", "podglad"):
        return jsonify({"error": "Nieprawidłowa rola użytkownika."}), 400

    new_id = str(_uuid.uuid4())
    pw_hash, salt = hash_password(password)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, salt, full_name, email, phone, role, is_active, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id,
            username,
            pw_hash,
            salt,
            full_name,
            email,
            phone,
            role,
            1,
            must_change,
            _dt.now().isoformat(timespec="seconds")
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Użytkownik o loginie '{username}' już istnieje."}), 409
    finally:
        conn.close()

    return jsonify({"status": "ok", "id": new_id}), 201

@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": "Wymagane uprawnienia administratora."}), 403

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = data.get("role", "technik")
    is_active = 1 if data.get("is_active", True) else 0
    must_change = 1 if data.get("must_change_password") else 0

    if not full_name:
        return jsonify({"error": "Pole 'Imię i Nazwisko' jest wymagane."}), 400
    if not username:
        return jsonify({"error": "Pole 'Login' jest wymagane."}), 400
    if role not in ("admin", "technik", "podglad"):
        return jsonify({"error": "Nieprawidłowa rola."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    # Zabezpieczenie przed odebraniem sobie uprawnień admina lub zablokowaniem jedynego admina
    if current_user["id"] == user_id and (role != "admin" or is_active == 0):
        conn.close()
        return jsonify({"error": "Nie możesz odebrać sobie uprawnień administratora ani zablokować własnego konta."}), 400

    # Sprawdzenie czy nowy login nie jest już zajęty przez inne konto
    cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"Login '{username}' jest już zajęty przez innego użytkownika."}), 409

    cursor.execute("""
        UPDATE users
        SET username = ?, full_name = ?, email = ?, phone = ?, role = ?, is_active = ?, must_change_password = ?
        WHERE id = ?
    """, (username, full_name, email, phone, role, is_active, must_change, user_id))
    conn.commit()
    conn.close()

    # Jeśli zmieniono dane bieżącego zalogowanego admina, zaktualizuj też kontekst sesji
    if current_user["id"] == user_id:
        current_user["username"] = username
        current_user["full_name"] = full_name
        current_user["email"] = email
        current_user["phone"] = phone
        current_user["role"] = role

    return jsonify({"status": "ok"})

@app.route("/api/users/<user_id>/reset-password", methods=["POST"])
def admin_reset_user_password(user_id):
    """Bezpośredni reset hasła użytkownika przez administratora."""
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": "Wymagane uprawnienia administratora."}), 403

    data = request.get_json() or {}
    new_password = data.get("new_password", "")
    must_change = 1 if data.get("must_change_password", True) else 0

    if not new_password or len(new_password) < 4:
        return jsonify({"error": "Nowe hasło musi mieć co najmniej 4 znaki."}), 400

    pw_hash, salt = hash_password(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET password_hash = ?, salt = ?, must_change_password = ? WHERE id = ?
    """, (pw_hash, salt, must_change, user_id))
    cursor.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Hasło zostało pomyślnie zmienione."})

@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": "Wymagane uprawnienia administratora."}), 403

    if current_user["id"] == user_id:
        return jsonify({"error": "Nie możesz usunąć własnego konta."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    cursor.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ═══════════════════════════════════════════════════════════════════
# SŁOWNIKI (LISTS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/lists", methods=["GET"])
def get_lists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM lists WHERE key = 'lists'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(json.loads(row["value"]))
    return jsonify({})

@app.route("/api/lists", methods=["PUT"])
def save_lists():
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO lists (key, value) VALUES ('lists', ?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ═══════════════════════════════════════════════════════════════════
# USTERKI (RECORDS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/records", methods=["GET"])
def get_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records ORDER BY created DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records", methods=["POST"])
def create_record():
    data = request.get_json() or {}
    required = ["klient", "model", "opisProblem", "typ"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Pole {f} jest wymagane."}), 400

    status = data.get("status", "open")
    fixed_at = data.get("fixed_at")
    if status == "fixed" and not fixed_at:
        fixed_at = _dt.now().isoformat(timespec="seconds")

    opis_prob = data.get("opisProblem", "")
    opis_nap = data.get("opisNaprawa", "")
    opis_prob_en = (data.get("opisProblem_en") or "").strip()
    opis_nap_en = (data.get("opisNaprawa_en") or "").strip()

    if not opis_prob_en and opis_prob:
        opis_prob_en = translate_pl_to_en(opis_prob)
    if not opis_nap_en and opis_nap:
        opis_nap_en = translate_pl_to_en(opis_nap)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (
            id, created, klient, model, projekt, vin, typ, element,
            opisProblem, opisNaprawa, status, created_by, fixed_by, fixed_at,
            opisProblem_en, opisNaprawa_en
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        data.get("created", _dt.now().isoformat(timespec="seconds")),
        data.get("klient", ""),
        data.get("model", ""),
        data.get("projekt", ""),
        data.get("vin", ""),
        data.get("typ", ""),
        data.get("element", ""),
        opis_prob,
        opis_nap,
        status,
        data.get("created_by", ""),
        data.get("fixed_by", ""),
        fixed_at,
        opis_prob_en,
        opis_nap_en
    ))
    conn.commit()
    conn.close()

    data["opisProblem_en"] = opis_prob_en
    data["opisNaprawa_en"] = opis_nap_en
    return jsonify(data), 201

@app.route("/api/records/<rec_id>", methods=["PUT"])
def update_record(rec_id):
    data = request.get_json() or {}
    status = data.get("status", "open")
    fixed_at = data.get("fixed_at")
    fixed_by = data.get("fixed_by", "")
    
    if status == "fixed" and not fixed_at:
        fixed_at = _dt.now().isoformat(timespec="seconds")
    elif status == "open":
        fixed_at = None
        fixed_by = ""

    opis_prob = data.get("opisProblem", "")
    opis_nap = data.get("opisNaprawa", "")
    opis_prob_en = (data.get("opisProblem_en") or "").strip()
    opis_nap_en = (data.get("opisNaprawa_en") or "").strip()

    if not opis_prob_en and opis_prob:
        opis_prob_en = translate_pl_to_en(opis_prob)
    if not opis_nap_en and opis_nap:
        opis_nap_en = translate_pl_to_en(opis_nap)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE records 
        SET klient=?, model=?, projekt=?, vin=?, typ=?, element=?,
            opisProblem=?, opisNaprawa=?, status=?,
            created_by=COALESCE(NULLIF(?, ''), created_by),
            fixed_by=?, fixed_at=?,
            opisProblem_en=?, opisNaprawa_en=?
        WHERE id=?
    """, (
        data.get("klient", ""),
        data.get("model", ""),
        data.get("projekt", ""),
        data.get("vin", ""),
        data.get("typ", ""),
        data.get("element", ""),
        opis_prob,
        opis_nap,
        status,
        data.get("created_by", ""),
        fixed_by,
        fixed_at,
        opis_prob_en,
        opis_nap_en,
        rec_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "opisProblem_en": opis_prob_en, "opisNaprawa_en": opis_nap_en})

@app.route("/api/records/<rec_id>/status", methods=["PATCH"])
def update_status(rec_id):
    data = request.get_json() or {}
    status = data.get("status", "open")
    fixed_by = data.get("fixed_by", "")
    fixed_at = data.get("fixed_at")
    
    if status == "fixed" and not fixed_at:
        fixed_at = _dt.now().isoformat(timespec="seconds")
    elif status == "open":
        fixed_at = None
        fixed_by = ""

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE records
        SET status=?, fixed_by=?, fixed_at=?
        WHERE id=?
    """, (status, fixed_by, fixed_at, rec_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/records/<rec_id>", methods=["DELETE"])
def delete_record(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Usuń zdjęcia i dokumenty wariantów rozwiązań należących do tej usterki
    cursor.execute("""
        DELETE FROM solution_documents WHERE solution_id IN
        (SELECT id FROM solutions WHERE record_id=?)
    """, (rec_id,))
    cursor.execute("""
        DELETE FROM solution_photos WHERE solution_id IN
        (SELECT id FROM solutions WHERE record_id=?)
    """, (rec_id,))
    cursor.execute("DELETE FROM solutions WHERE record_id=?", (rec_id,))
    cursor.execute("DELETE FROM records WHERE id=?", (rec_id,))
    cursor.execute("DELETE FROM photos WHERE record_id=?", (rec_id,))
    cursor.execute("DELETE FROM documents WHERE record_id=?", (rec_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/import", methods=["POST"])
def import_data():
    mode = request.args.get("mode", "merge")
    data = request.get_json() or {}
    recs = data.get("records", [])
    lists = data.get("lists", {})

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if mode == "replace":
            cursor.execute("DELETE FROM solution_documents")
            cursor.execute("DELETE FROM solution_photos")
            cursor.execute("DELETE FROM solutions")
            cursor.execute("DELETE FROM records")
            cursor.execute("DELETE FROM photos")
            cursor.execute("DELETE FROM documents")
            cursor.execute("DELETE FROM lists")

        imported_count = 0
        for r in recs:
            cursor.execute("""
                INSERT OR IGNORE INTO records
                (id, created, klient, model, projekt, vin, typ, element,
                 opisProblem, opisNaprawa, status, created_by, fixed_by, fixed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("id"),
                r.get("created", _dt.now().isoformat(timespec="seconds")),
                r.get("klient", ""),
                r.get("model", ""),
                r.get("projekt", ""),
                r.get("vin", ""),
                r.get("typ", ""),
                r.get("element", ""),
                r.get("opisProblem", ""),
                r.get("opisNaprawa", ""),
                r.get("status", "open"),
                r.get("created_by", ""),
                r.get("fixed_by", ""),
                r.get("fixed_at")
            ))
            if cursor.rowcount > 0:
                imported_count += 1

        if lists:
            cursor.execute("SELECT value FROM lists WHERE key = 'lists'")
            existing_row = cursor.fetchone()
            if existing_row and mode == "merge":
                try:
                    cur_lists = json.loads(existing_row["value"])
                    for k, v in lists.items():
                        if isinstance(v, list):
                            cur_arr = cur_lists.setdefault(k, [])
                            for item in v:
                                if item not in cur_arr:
                                    cur_arr.append(item)
                        elif isinstance(v, dict):
                            cur_dict = cur_lists.setdefault(k, {})
                            for sub_k, sub_v in v.items():
                                if isinstance(sub_v, list):
                                    sub_arr = cur_dict.setdefault(sub_k, [])
                                    for item in sub_v:
                                        if item not in sub_arr:
                                            sub_arr.append(item)
                    lists = cur_lists
                except Exception:
                    pass
            cursor.execute(
                "INSERT OR REPLACE INTO lists (key, value) VALUES ('lists', ?)",
                (json.dumps(lists),)
            )

        conn.commit()
        return jsonify({"status": "ok", "imported": imported_count, "total": len(recs)})
    finally:
        conn.close()

# ═══════════════════════════════════════════════════════════════════
# WARIANTY ROZWIĄZAŃ (SOLUTIONS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/records/<rec_id>/solutions", methods=["GET"])
def get_solutions(rec_id):
    """Zwraca listę wariantów rozwiązań dla danej usterki (bez danych zdjęć)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, record_id, numer, tytul, opis, tytul_en, opis_en, created_by, created "
        "FROM solutions WHERE record_id=? ORDER BY numer ASC",
        (rec_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records/<rec_id>/solutions", methods=["POST"])
def add_solution(rec_id):
    """Dodaje nowy wariant rozwiązania do usterki."""
    data = request.get_json() or {}
    conn = get_db_connection()
    # Wyznacz kolejny numer wariantu
    max_num = conn.execute(
        "SELECT COALESCE(MAX(numer), 0) FROM solutions WHERE record_id=?",
        (rec_id,)).fetchone()[0]
    sol_id = str(_uuid.uuid4())
    tytul = data.get("tytul", "").strip() or f"Wariant {max_num + 1}"
    opis = data.get("opis", "")
    tytul_en = (data.get("tytul_en") or "").strip()
    opis_en = (data.get("opis_en") or "").strip()

    if not tytul_en and tytul:
        tytul_en = translate_pl_to_en(tytul)
    if not opis_en and opis:
        opis_en = translate_pl_to_en(opis)

    conn.execute("""
        INSERT INTO solutions (id, record_id, numer, tytul, opis, created_by, created, tytul_en, opis_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sol_id, rec_id, max_num + 1, tytul,
        opis,
        data.get("created_by", ""),
        _dt.now().isoformat(timespec="seconds"),
        tytul_en,
        opis_en
    ))
    conn.commit()
    conn.close()
    return jsonify({"id": sol_id, "numer": max_num + 1, "tytul": tytul, "tytul_en": tytul_en, "opis_en": opis_en}), 201

@app.route("/api/solutions/<sol_id>", methods=["PUT"])
def update_solution(sol_id):
    """Edytuje tytuł i opis wariantu rozwiązania."""
    data = request.get_json() or {}
    tytul = data.get("tytul", "").strip()
    opis = data.get("opis", "")
    tytul_en = (data.get("tytul_en") or "").strip()
    opis_en = (data.get("opis_en") or "").strip()

    if not tytul_en and tytul:
        tytul_en = translate_pl_to_en(tytul)
    if not opis_en and opis:
        opis_en = translate_pl_to_en(opis)

    conn = get_db_connection()
    conn.execute("""
        UPDATE solutions SET tytul=?, opis=?, tytul_en=?, opis_en=? WHERE id=?
    """, (tytul, opis, tytul_en, opis_en, sol_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "tytul_en": tytul_en, "opis_en": opis_en})

@app.route("/api/solutions/<sol_id>", methods=["DELETE"])
def delete_solution(sol_id):
    """Usuwa wariant rozwiązania wraz z jego zdjęciami i dokumentami."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_photos WHERE solution_id=?", (sol_id,))
    conn.execute("DELETE FROM solution_documents WHERE solution_id=?", (sol_id,))
    conn.execute("DELETE FROM solutions WHERE id=?", (sol_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/solutions/<sol_id>/photos", methods=["GET"])
def get_solution_photos(sol_id):
    """Zwraca listę metadanych zdjęć wariantu (bez danych binarnych)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, filename, created FROM solution_photos WHERE solution_id=? ORDER BY created",
        (sol_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/solutions/<sol_id>/photos", methods=["POST"])
def add_solution_photo(sol_id):
    """Dodaje zdjęcie do wariantu rozwiązania."""
    data = request.get_json() or {}
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM solution_photos WHERE solution_id=?", (sol_id,)).fetchone()[0]
    if count >= 6:
        conn.close()
        return jsonify({"error": "Maksymalnie 6 zdjęć na wariant rozwiązania."}), 400
    photo_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    img_data = optimize_image_bytes(raw)
    conn.execute(
        "INSERT INTO solution_photos (id, solution_id, filename, data, created) VALUES (?,?,?,?,?)",
        (photo_id, sol_id, data.get("filename", "foto.jpg"),
         img_data, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"id": photo_id}), 201

@app.route("/api/solution-photos/<photo_id>", methods=["GET"])
def get_solution_photo(photo_id):
    """Zwraca dane binarne (base64) jednego zdjęcia wariantu."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM solution_photos WHERE id=?", (photo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/solution-photos/<photo_id>", methods=["DELETE"])
def delete_solution_photo(photo_id):
    """Usuwa zdjęcie wariantu rozwiązania."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ═══════════════════════════════════════════════════════════════════
# DOKUMENTY WARIANTÓW ROZWIĄZAŃ (SOLUTION DOCUMENTS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/solutions/<sol_id>/documents", methods=["GET"])
def get_solution_documents(sol_id):
    """Zwraca listę metadanych dokumentów wariantu (bez BLOB)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, filename, filesize, created FROM solution_documents WHERE solution_id=? ORDER BY created",
        (sol_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/solutions/<sol_id>/documents", methods=["POST"])
def add_solution_document(sol_id):
    """Dodaje dokument (PDF, DOC itp.) do wariantu rozwiązania."""
    data = request.get_json() or {}
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM solution_documents WHERE solution_id=?", (sol_id,)).fetchone()[0]
    if count >= 6:
        conn.close()
        return jsonify({"error": "Maksymalnie 6 dokumentów na wariant."}), 400
    doc_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    conn.execute(
        "INSERT INTO solution_documents (id, solution_id, filename, filesize, data, created) VALUES (?,?,?,?,?,?)",
        (doc_id, sol_id, data.get("filename", "dokument.pdf"), len(raw),
         raw, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"id": doc_id}), 201

@app.route("/api/solution-documents/<doc_id>", methods=["GET"])
def get_solution_document(doc_id):
    """Zwraca zawartość binarną (base64) jednego dokumentu wariantu."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, filesize, data FROM solution_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono dokumentu."}), 404
    return jsonify({
        "filename": row["filename"],
        "filesize": row["filesize"],
        "data": base64.b64encode(row["data"]).decode()
    })

@app.route("/api/solution-documents/<doc_id>/thumb", methods=["GET"])
def get_solution_document_thumb(doc_id):
    """Zwraca miniaturkę JPG pierwszej strony PDF dla dokumentu wariantu."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM solution_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return "Nie znaleziono", 404
    if row["filename"].lower().endswith(".pdf"):
        thumb = generate_pdf_thumb_bytes(row["data"])
        if thumb:
            return Response(thumb, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    return "Brak miniaturki", 404

@app.route("/api/solution-documents/<doc_id>/raw", methods=["GET"])
def get_solution_document_raw(doc_id):
    """Zwraca bezpośredni strumień pliku (inline) dla wbudowanego podglądu PDF."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM solution_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return "Nie znaleziono", 404
    fn = row["filename"]
    mimetype = "application/pdf" if fn.lower().endswith(".pdf") else "application/octet-stream"
    resp = Response(row["data"], mimetype=mimetype)
    resp.headers["Content-Disposition"] = f'inline; filename="{fn}"'
    return resp

@app.route("/api/solution-documents/<doc_id>/open", methods=["POST"])
def open_solution_document(doc_id):
    """Zapisuje dokument do pliku tymczasowego i otwiera go w domyślnej aplikacji Windows."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM solution_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono pliku."}), 404
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "rejestr_usterek_docs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / row["filename"]
    temp_file.write_bytes(row["data"])
    try:
        os.startfile(str(temp_file))
        return jsonify({"status": "ok", "path": str(temp_file)})
    except Exception as e:
        return jsonify({"error": f"Błąd otwierania: {e}"}), 500

@app.route("/api/solution-documents/<doc_id>", methods=["DELETE"])
def delete_solution_document(doc_id):
    """Usuwa dokument wariantu rozwiązania."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════════════════
# ZDJĘCIA (PHOTOS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/records/<rec_id>/photos", methods=["GET"])
def get_photos(rec_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, filename, created FROM photos WHERE record_id=? ORDER BY created",
        (rec_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records/<rec_id>/photos", methods=["POST"])
def add_photo(rec_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM photos WHERE record_id=?", (rec_id,)).fetchone()[0]
    if count >= 6:
        conn.close()
        return jsonify({"error": "Maksymalnie 6 zdjęć na usterkę."}), 400
    photo_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    img_data = optimize_image_bytes(raw)
    conn.execute(
        "INSERT INTO photos (id, record_id, filename, data, created) VALUES (?,?,?,?,?)",
        (photo_id, rec_id, data.get("filename","foto.jpg"),
         img_data, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"id": photo_id}), 201

@app.route("/api/photos/<photo_id>", methods=["GET"])
def get_photo(photo_id):
    conn = get_db_connection()
    row = conn.execute("SELECT filename, data FROM photos WHERE id=?", (photo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/photos/<photo_id>", methods=["DELETE"])
def delete_photo(photo_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/optimize-photos", methods=["POST"])
def admin_optimize_photos():
    """Optymalizuje wszystkie istniejące zdjęcia w bazie (usterki i warianty) i odzyskuje miejsce (VACUUM)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, data FROM photos")
    rows_photos = cursor.fetchall()

    cursor.execute("SELECT id, filename, data FROM solution_photos")
    rows_sol_photos = cursor.fetchall()

    before_total = 0
    after_total = 0
    updated_count = 0

    for r in rows_photos:
        raw = r["data"]
        before_total += len(raw)
        optimized = optimize_image_bytes(raw)
        after_total += len(optimized)
        if len(optimized) < len(raw):
            cursor.execute("UPDATE photos SET data = ? WHERE id = ?", (optimized, r["id"]))
            updated_count += 1

    for r in rows_sol_photos:
        raw = r["data"]
        before_total += len(raw)
        optimized = optimize_image_bytes(raw)
        after_total += len(optimized)
        if len(optimized) < len(raw):
            cursor.execute("UPDATE solution_photos SET data = ? WHERE id = ?", (optimized, r["id"]))
            updated_count += 1

    conn.commit()
    conn.execute("VACUUM;")
    conn.close()

    total_photos = len(rows_photos) + len(rows_sol_photos)
    return jsonify({
        "status": "ok",
        "total_photos": total_photos,
        "updated_photos": updated_count,
        "before_mb": round(before_total / (1024 * 1024), 2),
        "after_mb": round(after_total / (1024 * 1024), 2),
        "saved_percent": round((1 - (after_total / max(1, before_total))) * 100, 1)
    })

# ═══════════════════════════════════════════════════════════════════
# DOKUMENTY (DOCUMENTS - PDF, RAPORTY VSWR, HVAC)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/records/<rec_id>/documents", methods=["GET"])
def get_documents(rec_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, filename, filesize, created FROM documents WHERE record_id=? ORDER BY created",
        (rec_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records/<rec_id>/documents", methods=["POST"])
def add_document(rec_id):
    data = request.get_json() or {}
    doc_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO documents (id, record_id, filename, filesize, data, created) VALUES (?,?,?,?,?,?)",
        (doc_id, rec_id, data.get("filename", "dokument"),
         len(raw), raw, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"id": doc_id, "filesize": len(raw)}), 201

@app.route("/api/documents/<doc_id>", methods=["GET"])
def get_document(doc_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/documents/<doc_id>/thumb", methods=["GET"])
def get_document_thumb(doc_id):
    """Zwraca miniaturkę JPG pierwszej strony PDF."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return "Nie znaleziono", 404
    if row["filename"].lower().endswith(".pdf"):
        thumb = generate_pdf_thumb_bytes(row["data"])
        if thumb:
            return Response(thumb, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    return "Brak miniaturki", 404

@app.route("/api/documents/<doc_id>/raw", methods=["GET"])
def get_document_raw(doc_id):
    """Zwraca bezpośredni strumień pliku dla wbudowanego podglądu PDF."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return "Nie znaleziono", 404
    fn = row["filename"]
    mimetype = "application/pdf" if fn.lower().endswith(".pdf") else "application/octet-stream"
    resp = Response(row["data"], mimetype=mimetype)
    resp.headers["Content-Disposition"] = f'inline; filename="{fn}"'
    return resp

@app.route("/api/documents/<doc_id>/open", methods=["POST"])
def open_document(doc_id):
    """Zapisuje dokument do pliku tymczasowego i otwiera go w domyślnej aplikacji Windows."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono pliku."}), 404
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "rejestr_usterek_docs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / row["filename"]
    temp_file.write_bytes(row["data"])
    try:
        os.startfile(str(temp_file))
        return jsonify({"status": "ok", "path": str(temp_file)})
    except Exception as e:
        return jsonify({"error": f"Błąd otwierania: {e}"}), 500

@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})



if __name__ == "__main__":
    init_db()
    port = CFG.get("PORT", 5000)
    host = CFG.get("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=True)