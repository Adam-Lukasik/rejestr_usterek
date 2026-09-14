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
import zuken_service


SUPPORTED_LANGS = ("pl", "en", "de")


def translate_text(text: str, src: str, dst: str) -> str:
    """Automatycznie tłumaczy tekst z języka `src` na język `dst`."""
    if not text or not str(text).strip() or src == dst:
        return ""
    text_str = str(text).strip()
    try:
        url = ("https://translate.googleapis.com/translate_a/single?client=gtx"
               f"&sl={src}&tl={dst}&dt=t&q=" + urllib.parse.quote(text_str))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode("utf-8"))
            translated = "".join([segment[0] for segment in data[0] if segment and segment[0]])
            return translated.strip()
    except Exception as e:
        print(f"[TRANSLATE ERROR] Nie udało się przetłumaczyć {src}->{dst}: {e}")
        return ""


def translate_pl_to_en(text: str) -> str:
    """Automatycznie tłumaczy tekst z języka polskiego na angielski."""
    return translate_text(text, "pl", "en")


def _sync_lang_fields(typed, lang, old_pl="", old_en="", old_de=""):
    """Rozdziela wpisany tekst na kolumnę jego języka i tłumaczy na pozostałe.

    `typed` – tekst wpisany przez użytkownika, `lang` – język interfejsu.
    Zwraca krotkę (pl, en, de) do zapisu w kolumnach. Gdy tekst się nie zmienił,
    zachowuje istniejące tłumaczenia; puste kolumny są uzupełniane (backfill).
    """
    cols = {"pl": old_pl or "", "en": old_en or "", "de": old_de or ""}
    src = (typed or "").strip()
    if lang not in cols:
        lang = "pl"
    # Tekst może być prefillem z innej kolumny językowej (fallback w formularzu)
    if src and src != cols[lang].strip():
        for other in cols:
            if other != lang and src == cols[other].strip():
                lang = other
                break
    changed = src != cols[lang].strip()
    if changed:
        cols[lang] = src
        if not src and lang == "pl":
            cols["en"] = ""
            cols["de"] = ""
    if src:
        for tgt in cols:
            if tgt == lang:
                continue
            if changed or not cols[tgt].strip():
                tr = translate_text(src, lang, tgt)
                if tr:
                    cols[tgt] = tr
    return cols["pl"], cols["en"], cols["de"]


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

def checkpoint_wal(conn=None):
    """Wymusza natychmiastowe przepisanie zmian z pliku WAL do pliku rejestr_usterek.db."""
    close_after = False
    if conn is None:
        try:
            conn = get_db_connection()
            close_after = True
        except Exception:
            return
    try:
        conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
    except Exception as e:
        pass
    finally:
        if close_after:
            try:
                conn.close()
            except Exception:
                pass


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


# ═══════════════════════════════════════════════════════════════════
# KOMUNIKATY SERWEROWE (PL / EN / DE) — wybór wg nagłówka X-App-Lang
# ═══════════════════════════════════════════════════════════════════
SRV_MSG = {
    "smtpDisabled": {"pl": "Obsługa SMTP jest wyłączona w konfiguracji serwera.", "en": "SMTP support is disabled in the server configuration.", "de": "SMTP-Unterstützung ist in der Serverkonfiguration deaktiviert."},
    "noEmail": {"pl": "Użytkownik nie posiada prawidłowego adresu e-mail.", "en": "The user has no valid e-mail address.", "de": "Der Benutzer hat keine gültige E-Mail-Adresse."},
    "codeSent": {"pl": "Wiadomość z kodem została wysłana.", "en": "The code message has been sent.", "de": "Die Nachricht mit dem Code wurde gesendet."},
    "emailErr": {"pl": "Błąd wysyłania e-mail: {v}", "en": "E-mail sending error: {v}", "de": "Fehler beim E-Mail-Versand: {v}"},
    "resetEmailSubject": {"pl": "Kod resetowania hasła — Rejestr Usterek: {v}", "en": "Password reset code — Defect Registry: {v}", "de": "Passwort-Reset-Code — Mängelregister: {v}"},
    "resetEmailBody": {
        "pl": "Witaj {u},\n\nOtrzymaliśmy prośbę o zresetowanie hasła do Twojego konta w systemie Rejestr Usterek.\n\nTwój jednorazowy kod weryfikacyjny to:\n====================\n   {c}\n====================\n\nKod jest ważny przez 15 minut.\nJeśli to nie Ty prosiłeś o reset hasła, zignoruj tę wiadomość.\n\nPozdrawiamy,\nZespół Rejestru Usterek\n",
        "en": "Hello {u},\n\nWe received a request to reset the password for your Defect Registry account.\n\nYour one-time verification code is:\n====================\n   {c}\n====================\n\nThe code is valid for 15 minutes.\nIf you did not request a password reset, ignore this message.\n\nRegards,\nThe Defect Registry Team\n",
        "de": "Hallo {u},\n\nWir haben eine Anfrage zum Zurücksetzen des Passworts für Ihr Mängelregister-Konto erhalten.\n\nIhr einmaliger Bestätigungscode lautet:\n====================\n   {c}\n====================\n\nDer Code ist 15 Minuten gültig.\nFalls Sie kein Zurücksetzen angefordert haben, ignorieren Sie diese Nachricht.\n\nMit freundlichen Grüßen,\nIhr Mängelregister-Team\n",
    },
    "loginRequired": {"pl": "Podaj login i hasło.", "en": "Enter username and password.", "de": "Benutzername und Passwort eingeben."},
    "badLogin": {"pl": "Nieprawidłowy login lub hasło.", "en": "Invalid username or password.", "de": "Ungültiger Benutzername oder Passwort."},
    "accountBlocked": {"pl": "To konto zostało zablokowane. Skontaktuj się z Administratorem.", "en": "This account has been blocked. Contact the Administrator.", "de": "Dieses Konto wurde gesperrt. Wenden Sie sich an den Administrator."},
    "sessionExpired": {"pl": "Niezalogowany lub sesja wygasła.", "en": "Not logged in or session expired.", "de": "Nicht angemeldet oder Sitzung abgelaufen."},
    "pwTooShort": {"pl": "Nowe hasło musi mieć co najmniej 4 znaki.", "en": "The new password must be at least 4 characters.", "de": "Das neue Passwort muss mindestens 4 Zeichen haben."},
    "userNotFound": {"pl": "Nie znaleziono użytkownika.", "en": "User not found.", "de": "Benutzer nicht gefunden."},
    "currentPwWrong": {"pl": "Aktualne hasło jest nieprawidłowe.", "en": "The current password is incorrect.", "de": "Das aktuelle Passwort ist falsch."},
    "pwChanged": {"pl": "Hasło zostało pomyślnie zmienione.", "en": "Password changed successfully.", "de": "Passwort erfolgreich geändert."},
    "resetInfoMsg": {"pl": "Jeśli podany login/e-mail istnieje w bazie, wysłano kod weryfikacyjny lub skontaktuj się z Administratorem.", "en": "If the given username/e-mail exists, a verification code has been sent — otherwise contact the Administrator.", "de": "Falls der angegebene Benutzername/die E-Mail existiert, wurde ein Bestätigungscode gesendet — andernfalls wenden Sie sich an den Administrator."},
    "codeGeneratedNoMail": {"pl": "Kod został wygenerowany. W przypadku braku skonfigurowanej poczty poproś Administratora o bezpośredni reset hasła.", "en": "The code has been generated. If no mail is configured, ask the Administrator for a direct password reset.", "de": "Der Code wurde generiert. Falls keine E-Mail konfiguriert ist, bitten Sie den Administrator um ein direktes Zurücksetzen des Passworts."},
    "codeAndPwRequired": {"pl": "Podaj kod weryfikacyjny i nowe hasło.", "en": "Enter the verification code and new password.", "de": "Bestätigungscode und neues Passwort eingeben."},
    "badCode": {"pl": "Nieprawidłowy lub wygasły kod weryfikacyjny.", "en": "Invalid or expired verification code.", "de": "Ungültiger oder abgelaufener Bestätigungscode."},
    "codeExpired": {"pl": "Kod weryfikacyjny wygasł (ważność 15 minut).", "en": "Verification code expired (valid for 15 minutes).", "de": "Bestätigungscode abgelaufen (15 Minuten gültig)."},
    "pwReset": {"pl": "Hasło zostało pomyślnie zresetowane. Możesz się zalogować.", "en": "Password reset successfully. You can now sign in.", "de": "Passwort erfolgreich zurückgesetzt. Sie können sich jetzt anmelden."},
    "userFieldsRequired": {"pl": "Pola 'Login' oraz 'Imię i Nazwisko' są wymagane.", "en": "'Login' and 'Full name' fields are required.", "de": "Die Felder 'Login' und 'Vor- und Nachname' sind erforderlich."},
    "badRole": {"pl": "Nieprawidłowa rola użytkownika.", "en": "Invalid user role.", "de": "Ungültige Benutzerrolle."},
    "badRole2": {"pl": "Nieprawidłowa rola.", "en": "Invalid role.", "de": "Ungültige Rolle."},
    "userExists": {"pl": "Użytkownik o loginie '{v}' już istnieje.", "en": "User with login '{v}' already exists.", "de": "Benutzer mit Login '{v}' existiert bereits."},
    "fullNameRequired": {"pl": "Pole 'Imię i Nazwisko' jest wymagane.", "en": "'Full name' field is required.", "de": "Das Feld 'Vor- und Nachname' ist erforderlich."},
    "cantSelfDemote": {"pl": "Nie możesz odebrać sobie uprawnień administratora ani zablokować własnego konta.", "en": "You cannot revoke your own administrator rights or block your own account.", "de": "Sie können sich nicht selbst die Administratorrechte entziehen oder Ihr eigenes Konto sperren."},
    "loginTaken": {"pl": "Login '{v}' jest już zajęty przez innego użytkownika.", "en": "Login '{v}' is already taken by another user.", "de": "Login '{v}' ist bereits von einem anderen Benutzer vergeben."},
    "cantSelfDelete": {"pl": "Nie możesz usunąć własnego konta.", "en": "You cannot delete your own account.", "de": "Sie können Ihr eigenes Konto nicht löschen."},
    "maxPhotosVariant": {"pl": "Maksymalnie 6 zdjęć na wariant rozwiązania.", "en": "Maximum 6 photos per solution variant.", "de": "Maximal 6 Fotos pro Lösungsvariante."},
    "maxDocsVariant": {"pl": "Maksymalnie 6 dokumentów na wariant.", "en": "Maximum 6 documents per variant.", "de": "Maximal 6 Dokumente pro Variante."},
    "maxPhotosDefect": {"pl": "Maksymalnie 6 zdjęć na usterkę.", "en": "Maximum 6 photos per defect.", "de": "Maximal 6 Fotos pro Mangel."},
    "openErr": {"pl": "Błąd otwierania: {v}", "en": "Opening error: {v}", "de": "Fehler beim Öffnen: {v}"},
    "walMerged": {"pl": "Baza została w 100% scalona do pliku rejestr_usterek.db. Możesz bezpiecznie skopiować ten plik na pendrive!", "en": "The database has been 100% merged into rejestr_usterek.db. You can safely copy this file to a USB drive!", "de": "Die Datenbank wurde zu 100% in die Datei rejestr_usterek.db zusammengeführt. Sie können diese Datei sicher auf einen USB-Stick kopieren!"},
    "schematicNotFound": {"pl": "Schemat PDF nie został znaleziony w bazie.", "en": "PDF schematic not found in the database.", "de": "PDF-Schaltplan nicht in der Datenbank gefunden."},
    "schematicNotFound2": {"pl": "Schemat nie został odnaleziony w bazie.", "en": "Schematic not found in the database.", "de": "Schaltplan nicht in der Datenbank gefunden."},
    "prefixDescRequired": {"pl": "Prefiks i opis PL są wymagane.", "en": "Prefix and PL description are required.", "de": "Präfix und PL-Beschreibung sind erforderlich."},
    "prefixSaved": {"pl": "Zapisano skrót {v}", "en": "Abbreviation {v} saved", "de": "Abkürzung {v} gespeichert"},
    "photoNotFound": {"pl": "Plik zdjęcia nie istnieje.", "en": "Photo file does not exist.", "de": "Fotodatei existiert nicht."},
    "artNrPhotoRequired": {"pl": "Wymagany numer artykułu oraz dane zdjęcia.", "en": "Article number and photo data are required.", "de": "Artikelnummer und Fotodaten sind erforderlich."},
    "photoSavedKb": {"pl": "Zapisano zdjęcie komponentu w Bazie wiedzy.", "en": "Component photo saved in the Knowledge Base.", "de": "Komponentenfoto in der Wissensdatenbank gespeichert."},
    "artNrRequired": {"pl": "Wymagany numer artykułu.", "en": "Article number is required.", "de": "Artikelnummer ist erforderlich."},
    "photoFetched": {"pl": "Pobrano i zoptymalizowano zdjęcie.", "en": "Photo downloaded and optimized.", "de": "Foto heruntergeladen und optimiert."},
    "fetchFail": {"pl": "Nie udało się pobrać zdjęcia.", "en": "Failed to download the photo.", "de": "Foto konnte nicht heruntergeladen werden."},
    "psQRequired": {"pl": "Parametry ps i q są wymagane.", "en": "Parameters ps and q are required.", "de": "Parameter ps und q sind erforderlich."},
    "mustLogin": {"pl": "Wymagane zalogowanie.", "en": "Login required.", "de": "Anmeldung erforderlich."},
    "loginOrEmail": {"pl": "Podaj login lub adres e-mail.", "en": "Enter username or e-mail address.", "de": "Benutzername oder E-Mail-Adresse eingeben."},
    "adminRequired": {"pl": "Wymagane uprawnienia administratora.", "en": "Administrator privileges required.", "de": "Administratorrechte erforderlich."},
    "loginFieldRequired": {"pl": "Pole 'Login' jest wymagane.", "en": "'Login' field is required.", "de": "Das Feld 'Login' ist erforderlich."},
    "fieldRequired": {"pl": "Pole {v} jest wymagane.", "en": "Field {v} is required.", "de": "Feld {v} ist erforderlich."},
    "variantN": {"pl": "Wariant {n}", "en": "Variant {n}", "de": "Variante {n}"},
    "notFound": {"pl": "Nie znaleziono.", "en": "Not found.", "de": "Nicht gefunden."},
    "docNotFound": {"pl": "Nie znaleziono dokumentu.", "en": "Document not found.", "de": "Dokument nicht gefunden."},
    "noThumb": {"pl": "Brak miniaturki", "en": "No thumbnail", "de": "Keine Miniaturansicht"},
    "fileNotFound": {"pl": "Nie znaleziono pliku.", "en": "File not found.", "de": "Datei nicht gefunden."},
    "physFileMissing": {"pl": "Plik fizyczny {v} nie istnieje.", "en": "Physical file {v} does not exist.", "de": "Physische Datei {v} existiert nicht."},
    "noE3sFile": {"pl": "Nie znaleziono pliku projektu .e3s dla tego schematu.", "en": "No .e3s project file found for this schematic.", "de": "Keine .e3s-Projektdatei für diesen Schaltplan gefunden."},
    "articleOrQuery": {"pl": "Wymagany parametr 'article' lub 'query'.", "en": "Parameter 'article' or 'query' is required.", "de": "Parameter 'article' oder 'query' ist erforderlich."},
    "psRequired": {"pl": "Wymagany numer projektu PS.", "en": "PS project number is required.", "de": "PS-Projektnummer ist erforderlich."},
    "psParamRequired": {"pl": "Parametr ps jest wymagany.", "en": "Parameter ps is required.", "de": "Parameter ps ist erforderlich."},
    "batchStopSignal": {"pl": "Wysłano sygnał zatrzymania zadania.", "en": "Stop signal sent to the task.", "de": "Stoppsignal an die Aufgabe gesendet."},
    "noBatchRunning": {"pl": "Żadne zadanie masowe nie jest obecnie uruchomione.", "en": "No batch task is currently running.", "de": "Derzeit läuft keine Stapelaufgabe."},
}

def _app_lang():
    """Język UI z nagłówka X-App-Lang (domyślnie 'pl')."""
    try:
        lang = request.headers.get("X-App-Lang", "pl")
    except Exception:
        lang = "pl"
    return lang if lang in ("pl", "en", "de") else "pl"


def smsg(key, **kw):
    """Zwraca komunikat serwerowy w języku z nagłówka X-App-Lang (domyślnie PL)."""
    entry = SRV_MSG.get(key)
    if not entry:
        return key
    txt = entry.get(_app_lang()) or entry["pl"]
    return txt.format(**kw) if kw else txt

def send_reset_email(to_email: str, username: str, code: str) -> tuple[bool, str]:
    """Wysyła 6-cyfrowy kod resetu hasła przez SMTP."""
    smtp_cfg = CFG.get("SMTP", {})
    if not smtp_cfg.get("ENABLED"):
        return False, smsg("smtpDisabled")
    if not to_email or "@" not in to_email:
        return False, smsg("noEmail")

    server_host = smtp_cfg.get("SERVER", "")
    port = smtp_cfg.get("PORT", 587)
    user = smtp_cfg.get("USER", "")
    password = smtp_cfg.get("PASSWORD", "")
    sender_name = smtp_cfg.get("SENDER_NAME", "Rejestr Usterek")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = smsg("resetEmailSubject", v=code)
    msg["From"] = f"{sender_name} <{user}>"
    msg["To"] = to_email

    text_content = smsg("resetEmailBody", u=username, c=code)
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
        return True, smsg("codeSent")
    except Exception as e:
        return False, smsg("emailErr", v=str(e))

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
            opisNaprawa_en TEXT,
            opisProblem_de TEXT,
            opisNaprawa_de TEXT
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
    if "opisProblem_de" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN opisProblem_de TEXT")
    if "opisNaprawa_de" not in columns:
        cursor.execute("ALTER TABLE records ADD COLUMN opisNaprawa_de TEXT")

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
            tytul_de TEXT,
            opis_de TEXT,
            FOREIGN KEY (record_id) REFERENCES records(id)
        )
    """)

    cursor.execute("PRAGMA table_info(solutions)")
    sol_columns = [col["name"] for col in cursor.fetchall()]
    if "tytul_en" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN tytul_en TEXT")
    if "opis_en" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN opis_en TEXT")
    if "tytul_de" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN tytul_de TEXT")
    if "opis_de" not in sol_columns:
        cursor.execute("ALTER TABLE solutions ADD COLUMN opis_de TEXT")

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

    # Migracja: Uzupełnienie autorów wariantów (solutions.created_by) z pola records.fixed_by
    # Osoby wpisane w usterce jako 'Naprawił' stają się autorami przypisanych do danej usterki wariantów (jeśli brak autora).
    cursor.execute("""
        UPDATE solutions
        SET created_by = (
            SELECT TRIM(r.fixed_by) FROM records r WHERE r.id = solutions.record_id
        ),
        created = COALESCE(
            (SELECT NULLIF(TRIM(r.fixed_at), '') FROM records r WHERE r.id = solutions.record_id),
            solutions.created
        )
        WHERE (created_by IS NULL OR TRIM(created_by) = '' OR TRIM(created_by) = 'Technik')
          AND EXISTS (
            SELECT 1 FROM records r
            WHERE r.id = solutions.record_id
              AND r.fixed_by IS NOT NULL
              AND TRIM(r.fixed_by) != ''
        )
    """)

    # Dla wariantów, których usterka nie miała wypełnionego fixed_by, uzupełnij z records.created_by jeśli brak
    cursor.execute("""
        UPDATE solutions
        SET created_by = (
            SELECT COALESCE(NULLIF(TRIM(r.created_by), ''), 'Adam Łukasik')
            FROM records r WHERE r.id = solutions.record_id
        )
        WHERE (created_by IS NULL OR TRIM(created_by) = '' OR TRIM(created_by) = 'Technik')
          AND EXISTS (
            SELECT 1 FROM records r WHERE r.id = solutions.record_id
          )
    """)

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

    # Inicjalizacja bazy i słownika Zuken E3
    try:
        zuken_service.init_zuken_tables()
    except Exception as e:
        print(f"[ZUKEN] Błąd inicjalizacji tabel Zuken: {e}")

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

@app.route("/api/user-settings", methods=["GET", "POST"])
def api_user_settings():
    desktop_cfg_path = os.path.join(BASE_DIR, "desktop_config.json")
    if request.method == "POST":
        data = request.get_json() or {}
        cfg = {}
        if os.path.exists(desktop_cfg_path):
            try:
                with open(desktop_cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        if "language" in data:
            cfg["language"] = data["language"]
        try:
            with open(desktop_cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.warning(f"Nie udało się zapisać desktop_config.json: {e}")
        return jsonify({"ok": True, "settings": cfg})
    else:
        cfg = {}
        if os.path.exists(desktop_cfg_path):
            try:
                with open(desktop_cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        return jsonify(cfg)

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": smsg("loginRequired")}), 400

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
        return jsonify({"error": smsg("badLogin")}), 401

    if not user["is_active"]:
        conn.close()
        return jsonify({"error": smsg("accountBlocked")}), 403

    if not verify_password(password, user["password_hash"], user["salt"]):
        conn.close()
        return jsonify({"error": smsg("badLogin")}), 401

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
        return jsonify({"error": smsg("sessionExpired")}), 401
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
        return jsonify({"error": smsg("mustLogin")}), 401

    data = request.get_json() or {}
    old_pw = data.get("old_password", "")
    new_pw = data.get("new_password", "")

    if not new_pw or len(new_pw) < 4:
        return jsonify({"error": smsg("pwTooShort")}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt, must_change_password FROM users WHERE id = ?", (user["id"],))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": smsg("userNotFound")}), 404

    # Jeśli użytkownik nie jest w trybie wymuszonej zmiany, wymagaj podania poprawnego starego hasła
    if not row["must_change_password"]:
        if not old_pw or not verify_password(old_pw, row["password_hash"], row["salt"]):
            conn.close()
            return jsonify({"error": smsg("currentPwWrong")}), 400

    new_hash, new_salt = hash_password(new_pw)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
                   (new_hash, new_salt, user["id"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": smsg("pwChanged")})

@app.route("/api/auth/request-reset", methods=["POST"])
def auth_request_reset():
    """Generuje 6-cyfrowy kod i opcjonalnie wysyła e-mail."""
    data = request.get_json() or {}
    identifier = (data.get("identifier") or "").strip().lower()
    if not identifier:
        return jsonify({"error": smsg("loginOrEmail")}), 400

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
            "message": smsg("resetInfoMsg")
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
        "message": msg if sent else smsg("codeGeneratedNoMail")
    })

@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    data = request.get_json() or {}
    code = (data.get("code") or "").strip()
    new_pw = data.get("new_password", "")

    if not code or not new_pw:
        return jsonify({"error": smsg("codeAndPwRequired")}), 400
    if len(new_pw) < 4:
        return jsonify({"error": smsg("pwTooShort")}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT code, user_id, expires_at FROM password_reset_codes WHERE code = ?
    """, (code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": smsg("badCode")}), 400

    expires_at = _dt.fromisoformat(row["expires_at"])
    if _dt.now() > expires_at:
        cursor.execute("DELETE FROM password_reset_codes WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return jsonify({"error": smsg("codeExpired")}), 400

    user_id = row["user_id"]
    new_hash, new_salt = hash_password(new_pw)
    cursor.execute("UPDATE users SET password_hash = ?, salt = ?, must_change_password = 0 WHERE id = ?",
                   (new_hash, new_salt, user_id))
    cursor.execute("DELETE FROM password_reset_codes WHERE user_id = ?", (user_id,))
    # Unieważnij wszystkie aktywne sesje tego użytkownika
    cursor.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "message": smsg("pwReset")})

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
        return jsonify({"error": smsg("adminRequired")}), 403

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
        return jsonify({"error": smsg("adminRequired")}), 403

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = data.get("role", "technik")
    password = data.get("password", "")
    must_change = 1 if data.get("must_change_password", True) else 0

    if not username or not full_name:
        return jsonify({"error": smsg("userFieldsRequired")}), 400
    if not password or len(password) < 4:
        return jsonify({"error": smsg("pwTooShort")}), 400
    if role not in ("admin", "technik", "podglad"):
        return jsonify({"error": smsg("badRole")}), 400

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
        return jsonify({"error": smsg("userExists", v=username)}), 409
    finally:
        conn.close()

    return jsonify({"status": "ok", "id": new_id}), 201

@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": smsg("adminRequired")}), 403

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = data.get("role", "technik")
    is_active = 1 if data.get("is_active", True) else 0
    must_change = 1 if data.get("must_change_password") else 0

    if not full_name:
        return jsonify({"error": smsg("fullNameRequired")}), 400
    if not username:
        return jsonify({"error": smsg("loginFieldRequired")}), 400
    if role not in ("admin", "technik", "podglad"):
        return jsonify({"error": smsg("badRole2")}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    # Zabezpieczenie przed odebraniem sobie uprawnień admina lub zablokowaniem jedynego admina
    if current_user["id"] == user_id and (role != "admin" or is_active == 0):
        conn.close()
        return jsonify({"error": smsg("cantSelfDemote")}), 400

    # Sprawdzenie czy nowy login nie jest już zajęty przez inne konto
    cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": smsg("loginTaken", v=username)}), 409

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
        return jsonify({"error": smsg("adminRequired")}), 403

    data = request.get_json() or {}
    new_password = data.get("new_password", "")
    must_change = 1 if data.get("must_change_password", True) else 0

    if not new_password or len(new_password) < 4:
        return jsonify({"error": smsg("pwTooShort")}), 400

    pw_hash, salt = hash_password(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET password_hash = ?, salt = ?, must_change_password = ? WHERE id = ?
    """, (pw_hash, salt, must_change, user_id))
    cursor.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": smsg("pwChanged")})

@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    current_user = get_current_user()
    if not current_user or current_user.get("role") != "admin":
        return jsonify({"error": smsg("adminRequired")}), 403

    if current_user["id"] == user_id:
        return jsonify({"error": smsg("cantSelfDelete")}), 400

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
    checkpoint_wal(conn)
    conn.close()
    return jsonify({"status": "ok"})

# ═══════════════════════════════════════════════════════════════════
# USTERKI (RECORDS)
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/records", methods=["GET"])
def get_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*,
               (SELECT COUNT(*) FROM solutions s WHERE s.record_id = r.id) AS solutions_count
        FROM records r
        ORDER BY r.created DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records", methods=["POST"])
def create_record():
    data = request.get_json() or {}
    required = ["klient", "model", "opisProblem", "typ"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": smsg("fieldRequired", v=f)}), 400

    status = data.get("status", "open")
    fixed_at = data.get("fixed_at")
    if status == "fixed" and not fixed_at:
        fixed_at = _dt.now().isoformat(timespec="seconds")

    lang = _app_lang()
    opis_prob, opis_prob_en, opis_prob_de = _sync_lang_fields(data.get("opisProblem", ""), lang)
    opis_nap, opis_nap_en, opis_nap_de = _sync_lang_fields(data.get("opisNaprawa", ""), lang)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (
            id, created, klient, model, projekt, vin, typ, element,
            opisProblem, opisNaprawa, status, created_by, fixed_by, fixed_at,
            opisProblem_en, opisNaprawa_en, opisProblem_de, opisNaprawa_de
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        opis_nap_en,
        opis_prob_de,
        opis_nap_de
    ))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()

    data["opisProblem"] = opis_prob
    data["opisNaprawa"] = opis_nap
    data["opisProblem_en"] = opis_prob_en
    data["opisNaprawa_en"] = opis_nap_en
    data["opisProblem_de"] = opis_prob_de
    data["opisNaprawa_de"] = opis_nap_de
    return jsonify(data), 201

@app.route("/api/records/<rec_id>", methods=["PUT"])
def update_record(rec_id):
    data = request.get_json() or {}
    status = data.get("status", "open")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""SELECT fixed_by, fixed_at, created_by,
                             opisProblem, opisNaprawa,
                             opisProblem_en, opisNaprawa_en,
                             opisProblem_de, opisNaprawa_de
                      FROM records WHERE id=?""", (rec_id,))
    old_row = cursor.fetchone()
    old_fixed_by = (old_row["fixed_by"] if old_row else "") or ""
    old_fixed_at = old_row["fixed_at"] if old_row else None
    old_created_by = (old_row["created_by"] if old_row else "") or ""

    if "fixed_by" in data:
        fixed_by = data.get("fixed_by", "")
    else:
        fixed_by = old_fixed_by

    if "fixed_at" in data and data.get("fixed_at") is not None:
        fixed_at = data.get("fixed_at")
    else:
        fixed_at = old_fixed_at
    
    if status == "fixed" and not fixed_at:
        fixed_at = _dt.now().isoformat(timespec="seconds")
    elif status == "open":
        fixed_at = None
        fixed_by = ""

    created_by = data.get("created_by") if "created_by" in data else old_created_by

    lang = _app_lang()
    if "opisProblem" in data:
        opis_prob, opis_prob_en, opis_prob_de = _sync_lang_fields(
            data.get("opisProblem", ""), lang,
            old_row["opisProblem"] if old_row else "",
            old_row["opisProblem_en"] if old_row else "",
            old_row["opisProblem_de"] if old_row else "")
    else:
        opis_prob = old_row["opisProblem"] if old_row else ""
        opis_prob_en = old_row["opisProblem_en"] if old_row else ""
        opis_prob_de = old_row["opisProblem_de"] if old_row else ""
    if "opisNaprawa" in data:
        opis_nap, opis_nap_en, opis_nap_de = _sync_lang_fields(
            data.get("opisNaprawa", ""), lang,
            old_row["opisNaprawa"] if old_row else "",
            old_row["opisNaprawa_en"] if old_row else "",
            old_row["opisNaprawa_de"] if old_row else "")
    else:
        opis_nap = old_row["opisNaprawa"] if old_row else ""
        opis_nap_en = old_row["opisNaprawa_en"] if old_row else ""
        opis_nap_de = old_row["opisNaprawa_de"] if old_row else ""

    cursor.execute("""
        UPDATE records
        SET klient=?, model=?, projekt=?, vin=?, typ=?, element=?,
            opisProblem=?, opisNaprawa=?, status=?,
            created_by=COALESCE(NULLIF(?, ''), created_by),
            fixed_by=?, fixed_at=?,
            opisProblem_en=?, opisNaprawa_en=?, opisProblem_de=?, opisNaprawa_de=?
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
        created_by,
        fixed_by,
        fixed_at,
        opis_prob_en,
        opis_nap_en,
        opis_prob_de,
        opis_nap_de,
        rec_id
    ))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()
    return jsonify({"status": "ok", "opisProblem": opis_prob, "opisNaprawa": opis_nap,
                    "opisProblem_en": opis_prob_en, "opisNaprawa_en": opis_nap_en,
                    "opisProblem_de": opis_prob_de, "opisNaprawa_de": opis_nap_de})

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
    checkpoint_wal(conn)
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
    checkpoint_wal(conn)
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
        checkpoint_wal(conn)
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
        "SELECT id, record_id, numer, tytul, opis, tytul_en, opis_en, tytul_de, opis_de, created_by, created "
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
    lang = _app_lang()
    tytul_typed = data.get("tytul", "").strip() or smsg("variantN", n=max_num + 1)
    tytul, tytul_en, tytul_de = _sync_lang_fields(tytul_typed, lang)
    opis, opis_en, opis_de = _sync_lang_fields(data.get("opis", ""), lang)
    created_by = (data.get("created_by") or "").strip()
    if not created_by:
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if token:
            u_row = conn.execute("""
                SELECT u.full_name, u.username FROM users u
                JOIN auth_tokens t ON t.user_id = u.id
                WHERE t.token = ? AND t.expires_at > ?
            """, (token, _dt.now().isoformat())).fetchone()
            if u_row:
                created_by = u_row["full_name"] or u_row["username"] or ""
        if not created_by:
            created_by = "Technik"

    now_str = _dt.now().isoformat(timespec="seconds")

    conn.execute("""
        INSERT INTO solutions (id, record_id, numer, tytul, opis, created_by, created, tytul_en, opis_en, tytul_de, opis_de)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sol_id, rec_id, max_num + 1, tytul,
        opis,
        created_by,
        now_str,
        tytul_en,
        opis_en,
        tytul_de,
        opis_de
    ))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()
    return jsonify({
        "id": sol_id,
        "numer": max_num + 1,
        "tytul": tytul,
        "tytul_en": tytul_en,
        "opis_en": opis_en,
        "tytul_de": tytul_de,
        "opis_de": opis_de,
        "created_by": created_by,
        "created": now_str
    }), 201

@app.route("/api/solutions/<sol_id>", methods=["PUT"])
def update_solution(sol_id):
    """Edytuje tytuł, opis i opcjonalnie autora wariantu rozwiązania."""
    data = request.get_json() or {}
    created_by = data.get("created_by")
    lang = _app_lang()

    conn = get_db_connection()
    old = conn.execute(
        "SELECT tytul, opis, tytul_en, opis_en, tytul_de, opis_de FROM solutions WHERE id=?",
        (sol_id,)).fetchone()

    if "tytul" in data:
        tytul, tytul_en, tytul_de = _sync_lang_fields(
            data.get("tytul", "").strip(), lang,
            old["tytul"] if old else "", old["tytul_en"] if old else "", old["tytul_de"] if old else "")
    else:
        tytul = old["tytul"] if old else ""
        tytul_en = old["tytul_en"] if old else ""
        tytul_de = old["tytul_de"] if old else ""
    if "opis" in data:
        opis, opis_en, opis_de = _sync_lang_fields(
            data.get("opis", ""), lang,
            old["opis"] if old else "", old["opis_en"] if old else "", old["opis_de"] if old else "")
    else:
        opis = old["opis"] if old else ""
        opis_en = old["opis_en"] if old else ""
        opis_de = old["opis_de"] if old else ""

    if created_by is not None:
        conn.execute("""
            UPDATE solutions SET tytul=?, opis=?, tytul_en=?, opis_en=?, tytul_de=?, opis_de=?, created_by=? WHERE id=?
        """, (tytul, opis, tytul_en, opis_en, tytul_de, opis_de, str(created_by).strip(), sol_id))
    else:
        conn.execute("""
            UPDATE solutions SET tytul=?, opis=?, tytul_en=?, opis_en=?, tytul_de=?, opis_de=? WHERE id=?
        """, (tytul, opis, tytul_en, opis_en, tytul_de, opis_de, sol_id))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()
    return jsonify({"status": "ok", "tytul": tytul, "opis": opis,
                    "tytul_en": tytul_en, "opis_en": opis_en,
                    "tytul_de": tytul_de, "opis_de": opis_de,
                    "created_by": created_by})

@app.route("/api/solutions/<sol_id>", methods=["DELETE"])
def delete_solution(sol_id):
    """Usuwa wariant rozwiązania wraz z jego zdjęciami i dokumentami."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_photos WHERE solution_id=?", (sol_id,))
    conn.execute("DELETE FROM solution_documents WHERE solution_id=?", (sol_id,))
    conn.execute("DELETE FROM solutions WHERE id=?", (sol_id,))
    conn.commit()
    checkpoint_wal(conn)
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
        return jsonify({"error": smsg("maxPhotosVariant")}), 400
    photo_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    img_data = optimize_image_bytes(raw)
    conn.execute(
        "INSERT INTO solution_photos (id, solution_id, filename, data, created) VALUES (?,?,?,?,?)",
        (photo_id, sol_id, data.get("filename", "foto.jpg"),
         img_data, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    checkpoint_wal(conn)
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
        return jsonify({"error": smsg("notFound")}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/solution-photos/<photo_id>", methods=["DELETE"])
def delete_solution_photo(photo_id):
    """Usuwa zdjęcie wariantu rozwiązania."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_photos WHERE id=?", (photo_id,))
    conn.commit()
    checkpoint_wal(conn)
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
        return jsonify({"error": smsg("maxDocsVariant")}), 400
    doc_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    conn.execute(
        "INSERT INTO solution_documents (id, solution_id, filename, filesize, data, created) VALUES (?,?,?,?,?,?)",
        (doc_id, sol_id, data.get("filename", "dokument.pdf"), len(raw),
         raw, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    checkpoint_wal(conn)
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
        return jsonify({"error": smsg("docNotFound")}), 404
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
        return smsg("notFound"), 404
    if row["filename"].lower().endswith(".pdf"):
        thumb = generate_pdf_thumb_bytes(row["data"])
        if thumb:
            return Response(thumb, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    return smsg("noThumb"), 404

@app.route("/api/solution-documents/<doc_id>/raw", methods=["GET"])
def get_solution_document_raw(doc_id):
    """Zwraca bezpośredni strumień pliku (inline) dla wbudowanego podglądu PDF."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM solution_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return smsg("notFound"), 404
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
        return jsonify({"error": smsg("fileNotFound")}), 404
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "rejestr_usterek_docs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / row["filename"]
    temp_file.write_bytes(row["data"])
    try:
        if row["filename"].lower().endswith(".pdf"):
            ok, msg = zuken_service.open_pdf_in_system(str(temp_file), lang=_app_lang())
            if ok:
                return jsonify({"status": "ok", "path": str(temp_file), "message": msg})
        os.startfile(str(temp_file))
        return jsonify({"status": "ok", "path": str(temp_file)})
    except Exception as e:
        return jsonify({"error": smsg("openErr", v=e)}), 500

@app.route("/api/solution-documents/<doc_id>", methods=["DELETE"])
def delete_solution_document(doc_id):
    """Usuwa dokument wariantu rozwiązania."""
    conn = get_db_connection()
    conn.execute("DELETE FROM solution_documents WHERE id=?", (doc_id,))
    conn.commit()
    checkpoint_wal(conn)
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
        return jsonify({"error": smsg("maxPhotosDefect")}), 400
    photo_id = str(_uuid.uuid4())
    raw = base64.b64decode(data.get("data", ""))
    img_data = optimize_image_bytes(raw)
    conn.execute(
        "INSERT INTO photos (id, record_id, filename, data, created) VALUES (?,?,?,?,?)",
        (photo_id, rec_id, data.get("filename","foto.jpg"),
         img_data, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()
    return jsonify({"id": photo_id}), 201

@app.route("/api/photos/<photo_id>", methods=["GET"])
def get_photo(photo_id):
    conn = get_db_connection()
    row = conn.execute("SELECT filename, data FROM photos WHERE id=?", (photo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": smsg("notFound")}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/photos/<photo_id>", methods=["DELETE"])
def delete_photo(photo_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit()
    checkpoint_wal(conn)
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/admin/flush-db", methods=["POST"])
def api_admin_flush_db():
    """Wymusza natychmiastowe scalenie dziennika WAL (TRUNCATE) do pliku rejestr_usterek.db."""
    try:
        conn = get_db_connection()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.close()
        return jsonify({
            "status": "success",
            "message": smsg("walMerged")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        return jsonify({"error": smsg("notFound")}), 404
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
        return smsg("notFound"), 404
    if row["filename"].lower().endswith(".pdf"):
        thumb = generate_pdf_thumb_bytes(row["data"])
        if thumb:
            return Response(thumb, mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    return smsg("noThumb"), 404

@app.route("/api/documents/<doc_id>/raw", methods=["GET"])
def get_document_raw(doc_id):
    """Zwraca bezpośredni strumień pliku dla wbudowanego podglądu PDF."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT filename, data FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return smsg("notFound"), 404
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
        return jsonify({"error": smsg("fileNotFound")}), 404
    import tempfile
    temp_dir = Path(tempfile.gettempdir()) / "rejestr_usterek_docs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / row["filename"]
    temp_file.write_bytes(row["data"])
    try:
        if row["filename"].lower().endswith(".pdf"):
            ok, msg = zuken_service.open_pdf_in_system(str(temp_file), lang=_app_lang())
            if ok:
                return jsonify({"status": "ok", "path": str(temp_file), "message": msg})
        os.startfile(str(temp_file))
        return jsonify({"status": "ok", "path": str(temp_file)})
    except Exception as e:
        return jsonify({"error": smsg("openErr", v=e)}), 500

@app.route("/api/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})



# ═══════════════════════════════════════════════════════════════════
# ENDPOINTY ZUKEN E3 I LOKALNEGO ASYSTENTA DIAGNOSTYCZNEGO
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/zuken/projects", methods=["GET"])
def api_zuken_projects():
    """Zwraca listę zaimportowanych schematów/projektów Zuken E3 oraz ich rewizji."""
    try:
        conn = zuken_service.get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, filename, project_name, client, ps_codes, revision_date, revision_name, total_connections, imported_at, is_active, notes
            FROM zuken_projects
            ORDER BY revision_date DESC, id DESC;
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"projects": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/sync", methods=["POST"])
def api_zuken_sync():
    """Skanuje katalog Baza wiedzy i synchronizuje pliki XLSX oraz PDF ze schematami."""
    try:
        res = zuken_service.sync_all_knowledge_base(lang=_app_lang())
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/pdf/schematics", methods=["GET"])
def api_zuken_pdf_schematics():
    """Zwraca listę zarejestrowanych schematów PDF z informacją o wersjach."""
    try:
        schematics = zuken_service.get_pdf_schematics()
        return jsonify({"schematics": schematics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/pdf/view/<int:schematic_id>")
def api_zuken_pdf_view(schematic_id):
    """Serwuje plik PDF ze schematem do podglądu inline w przeglądarce."""
    try:
        conn = zuken_service.get_db()
        cur = conn.cursor()
        cur.execute("SELECT filepath, filename FROM zuken_pdf_schematics WHERE id = ?", (schematic_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({"error": smsg("schematicNotFound")}), 404
        
        filepath = row["filepath"]
        if not os.path.exists(filepath):
            return jsonify({"error": smsg("physFileMissing", v=filepath)}), 404

        dir_path = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        response = send_from_directory(dir_path, file_name, mimetype="application/pdf", as_attachment=False)
        response.headers["Content-Disposition"] = f'inline; filename="{file_name}"'
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/pdf/open", methods=["POST"])
def api_zuken_pdf_open():
    """Otwiera wskazany schemat w Zuken E3.series (jeśli zainstalowany) lub w SumatraPDF / Acrobat na właściwym arkuszu."""
    try:
        data = request.get_json() or {}
        schematic_id = data.get("schematic_id")
        page = int(data.get("page", 1))

        conn = zuken_service.get_db()
        cur = conn.cursor()
        cur.execute("SELECT filepath, filename FROM zuken_pdf_schematics WHERE id = ?", (schematic_id,))
        row = cur.fetchone()

        sheet_number = None
        sheet_title = None
        if row:
            cur.execute(
                "SELECT sheet_number, sheet_title FROM zuken_pdf_sheets WHERE schematic_id = ? AND page_number = ?",
                (schematic_id, page)
            )
            sheet_row = cur.fetchone()
            if sheet_row:
                sheet_number = sheet_row["sheet_number"]
                sheet_title = sheet_row["sheet_title"]

        conn.close()

        if not row:
            return jsonify({"error": smsg("schematicNotFound2")}), 404

        filepath = row["filepath"]
        target = (data.get("target") or "").lower()

        if target == "pdf":
            ok, msg = zuken_service.open_pdf_in_system(filepath, page_number=page, lang=_app_lang())
        elif target == "zuken":
            e3s_file = zuken_service.find_e3s_counterpart(filepath)
            if e3s_file and os.path.exists(e3s_file):
                ok, msg = zuken_service.open_in_zuken(e3s_file, sheet_number=sheet_number, sheet_title=sheet_title, lang=_app_lang())
            else:
                ok, msg = False, smsg("noE3sFile")
        else:
            ok, msg = zuken_service.open_schematic_in_system(
                filepath,
                page_number=page,
                sheet_number=sheet_number,
                sheet_title=sheet_title,
                lang=_app_lang()
            )

        if ok:
            return jsonify({"status": "success", "message": msg})
        else:
            return jsonify({"status": "error", "message": msg}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/glossary", methods=["GET", "POST"])
def api_zuken_glossary():
    """Pobiera lub dodaje/aktualizuje wpis w słowniku skrótów Zuken."""
    if request.method == "GET":
        try:
            conn = zuken_service.get_db()
            cur = conn.cursor()
            cur.execute("SELECT prefix, category, desc_pl, desc_en FROM zuken_glossary ORDER BY category, prefix;")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return jsonify({"glossary": rows})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        data = request.get_json() or {}
        prefix = (data.get("prefix") or "").strip().upper()
        category = (data.get("category") or "Ogólne").strip()
        desc_pl = (data.get("desc_pl") or "").strip()
        desc_en = (data.get("desc_en") or "").strip()

        if not prefix or not desc_pl:
            return jsonify({"error": smsg("prefixDescRequired")}), 400

        try:
            conn = zuken_service.get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO zuken_glossary (prefix, category, desc_pl, desc_en)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(prefix) DO UPDATE SET
                    category=excluded.category,
                    desc_pl=excluded.desc_pl,
                    desc_en=excluded.desc_en;
            """, (prefix, category, desc_pl, desc_en))
            conn.commit()
            conn.close()
            return jsonify({"ok": True, "message": smsg("prefixSaved", v=prefix)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/ai/diagnose", methods=["POST"])
def api_ai_diagnose():
    """Główny endpoint podpowiedzi diagnostycznej (100% lokalny offline)."""
    data = request.get_json() or {}
    element = data.get("element", "")
    typ = data.get("typ", "")
    opis = data.get("opisProblem", "") or data.get("opis", "")
    ps_code = data.get("projekt", "") or data.get("ps_code", "")
    client = data.get("klient", "") or data.get("client", "")
    vin = data.get("vin", "")
    record_id = data.get("record_id") or data.get("recordId", "")
    solution_id = data.get("solution_id") or data.get("solutionId", "")

    try:
        result = zuken_service.diagnose_defect(
            element=element,
            typ=typ,
            opisProblem=opis,
            ps_code=ps_code,
            client=client,
            vin=vin,
            record_id=record_id,
            solution_id=solution_id,
            lang=_app_lang()
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTY API DLA BOM (BILL OF MATERIAL) I ZDJĘĆ KOMPONENTÓW
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/zuken/bom/catalog", methods=["GET"])
def api_zuken_bom_catalog():
    """Zwraca katalog artykułów z BOM z filtrowaniem i paginacją."""
    try:
        query = request.args.get("q", "") or request.args.get("query", "")
        supplier = request.args.get("supplier", "")
        category = request.args.get("category", "")
        ps_code = request.args.get("ps_code", "") or request.args.get("projekt", "")
        has_image = request.args.get("has_image", "")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        data = zuken_service.get_bom_catalog(
            query=query,
            supplier=supplier,
            category=category,
            ps_code=ps_code,
            has_image=has_image,
            limit=limit,
            offset=offset,
            lang=_app_lang()
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/suppliers", methods=["GET"])
def api_zuken_bom_suppliers():
    """Zwraca listę dostawców z BOM."""
    try:
        suppliers = zuken_service.get_bom_suppliers()
        return jsonify({"suppliers": suppliers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/categories", methods=["GET"])
def api_zuken_bom_categories():
    """Zwraca listę kategorii komponentów z BOM."""
    try:
        categories = zuken_service.get_bom_categories()
        return jsonify({"categories": categories})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/image/<path:filename>")
def api_zuken_bom_image(filename):
    """Serwuje lokalne zdjęcie złączki lub komponentu z folderu Baza wiedzy/zdjecia_komponentow/."""
    try:
        clean_name = os.path.basename(filename)
        img_dir = zuken_service.BOM_IMAGES_DIR
        if not os.path.exists(os.path.join(img_dir, clean_name)):
            return jsonify({"error": smsg("photoNotFound")}), 404

        response = send_from_directory(img_dir, clean_name)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/upload-image", methods=["POST"])
def api_zuken_bom_upload_image():
    """
    Zapisuje zdjęcie złączki w folderze lokalnym Bazy Wiedzy.
    Obsługuje zarówno wklejanie ze schowka (Base64) jak i wysyłanie pliku (Multipart).
    """
    try:
        article_number = ""
        img_bytes = None
        ext = "jpg"

        if request.is_json:
            data = request.get_json() or {}
            article_number = (data.get("article_number") or "").strip()
            image_data = data.get("image_data") or ""
            if "base64," in image_data:
                header, b64_str = image_data.split("base64,", 1)
                img_bytes = base64.b64decode(b64_str)
                if "png" in header:
                    ext = "png"
                elif "webp" in header:
                    ext = "webp"
            elif image_data:
                img_bytes = base64.b64decode(image_data)
        elif "file" in request.files:
            f = request.files["file"]
            article_number = request.form.get("article_number", "").strip()
            if f and f.filename:
                _, f_ext = os.path.splitext(f.filename)
                ext = f_ext.lstrip(".") or "jpg"
                img_bytes = f.read()

        if not article_number or not img_bytes:
            return jsonify({"error": smsg("artNrPhotoRequired")}), 400

        ok, res = zuken_service.save_component_image(article_number, img_bytes, ext=ext, lang=_app_lang())
        if ok:
            return jsonify({"status": "success", "image_url": res, "message": smsg("photoSavedKb")})
        else:
            return jsonify({"error": res}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/search", methods=["GET"])
def api_zuken_bom_images_search():
    """Wyszukuje w sieci propozycje zdjęć dla wskazanego artykułu."""
    try:
        article = (request.args.get("article") or "").strip()
        supplier = (request.args.get("supplier") or "").strip()
        category = (request.args.get("category") or "").strip()
        desc = (request.args.get("desc") or "").strip()
        query = (request.args.get("query") or request.args.get("q") or "").strip()

        if not article and not query:
            return jsonify({"error": smsg("articleOrQuery")}), 400

        candidates = zuken_service.search_component_image_candidates(
            article_number=article,
            supplier=supplier,
            category=category,
            desc=desc,
            max_results=8,
            custom_query=query
        )
        return jsonify({
            "status": "success",
            "article_number": article,
            "query": query,
            "candidates": candidates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/fetch-one", methods=["POST"])
def api_zuken_bom_images_fetch_one():
    """
    Pobiera wybrane zdjęcie z URL lub automatycznie najlepsze z sieci
    i zapisuje je w Bazie wiedzy dla danego artykułu.
    """
    try:
        data = request.get_json() or {}
        article = (data.get("article_number") or "").strip()
        image_url = (data.get("image_url") or "").strip()
        supplier = (data.get("supplier") or "").strip()
        category = (data.get("category") or "").strip()
        desc = (data.get("description") or "").strip()
        custom_query = (data.get("query") or "").strip()

        if not article:
            return jsonify({"error": smsg("artNrRequired")}), 400

        if image_url:
            ok, res, fname = zuken_service.download_and_optimize_component_image(article, image_url, lang=_app_lang())
            if ok:
                return jsonify({"status": "success", "image_url": res, "filename": fname, "message": smsg("photoFetched")})
            return jsonify({"error": res}), 400
        else:
            ok, res, msg = zuken_service.auto_fetch_single_component_image(article, supplier, category, desc, custom_query=custom_query, lang=_app_lang())
            if ok:
                return jsonify({"status": "success", "image_url": res, "message": msg})
            return jsonify({"error": msg or smsg("fetchFail")}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/delete", methods=["POST", "DELETE"])
def api_zuken_bom_images_delete():
    """Usuwa przypisane zdjęcie komponentu z Bazy wiedzy."""
    try:
        data = request.get_json() or {}
        article = (data.get("article_number") or request.args.get("article") or "").strip()
        if not article:
            return jsonify({"error": smsg("artNrRequired")}), 400

        ok, msg = zuken_service.delete_component_image(article, lang=_app_lang())
        if ok:
            return jsonify({"status": "success", "message": msg})
        return jsonify({"error": msg}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/batch-count", methods=["GET"])
def api_zuken_bom_images_batch_count():
    """Zwraca dokładną zdeduplikowaną liczbę komponentów do pobrania dla danego zakresu."""
    try:
        scope = request.args.get("scope", "all")
        ps_code = request.args.get("ps_code", "")
        only_missing = request.args.get("only_missing", "true").lower() in ["true", "1", "yes"]
        items = zuken_service.get_batch_target_items(scope=scope, ps_code=ps_code if ps_code else None, only_missing=only_missing)
        return jsonify({
            "status": "success",
            "scope": scope,
            "count": len(items)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/batch-start", methods=["POST"])
def api_zuken_bom_images_batch_start():
    """Uruchamia masowe pobieranie brakujących zdjęć komponentów w tle."""
    try:
        data = request.get_json() or {}
        ps_code = data.get("ps_code") or None
        category = data.get("category") or None
        scope = data.get("scope") or "all"
        only_missing = bool(data.get("only_missing", True))
        delay_sec = float(data.get("delay_sec", 1.0))

        ok, msg = zuken_service.start_batch_image_download(
            ps_code=ps_code,
            category=category,
            scope=scope,
            only_missing=only_missing,
            delay_sec=delay_sec,
            lang=_app_lang()
        )
        if ok:
            return jsonify({"status": "success", "message": msg})
        return jsonify({"error": msg}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/batch-status", methods=["GET"])
def api_zuken_bom_images_batch_status():
    """Zwraca bieżący stan masowego pobierania zdjęć."""
    try:
        st = zuken_service.get_batch_image_download_status()
        return jsonify(st)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/bom/images/batch-stop", methods=["POST"])
def api_zuken_bom_images_batch_stop():
    """Zatrzymuje masowe pobieranie zdjęć."""
    try:
        ok, _msg = zuken_service.stop_batch_image_download()
        return jsonify({"status": "success" if ok else "error",
                        "message": smsg("batchStopSignal" if ok else "noBatchRunning")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════
# ENDPOINTY DLA ZESTAWIEŃ TECHNICZNYCH ZUKEN E3 (PS)
# ═══════════════════════════════════════════════════════════════════


@app.route("/api/zuken/ps-projects", methods=["GET"])
def api_zuken_ps_projects():
    """Zwraca listę projektów PS z Bazy wiedzy oraz stan ich zestawień."""
    try:
        projs = zuken_service.get_available_ps_projects(lang=_app_lang())
        return jsonify({"projects": projs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/summaries/generate", methods=["POST"])
def api_zuken_summaries_generate():
    """Generuje zestawienia (złącza z pinoutem, bezpieczniki, przekaźniki) dla wybranego PS."""
    try:
        data = request.get_json() or {}
        ps_code = data.get("ps_code") or request.form.get("ps_code") or ""
        if not ps_code:
            return jsonify({"error": smsg("psRequired")}), 400

        res = zuken_service.generate_ps_technical_summaries(ps_code, lang=_app_lang())
        if res.get("status") == "error":
            return jsonify(res), 400
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/summaries/connectors", methods=["GET"])
def api_zuken_summaries_connectors():
    """Zwraca listę złączy wraz z kompletnym pinoutem dla projektu PS."""
    try:
        ps_code = request.args.get("ps", "") or request.args.get("ps_code", "")
        search = request.args.get("q", "") or request.args.get("search", "")
        system_filter = request.args.get("system", "")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        if not ps_code:
            return jsonify({"error": smsg("psParamRequired")}), 400

        data = zuken_service.get_ps_connectors(
            ps_code=ps_code,
            search=search,
            system_filter=system_filter,
            limit=limit,
            offset=offset,
            lang=_app_lang()
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/summaries/fuses", methods=["GET"])
def api_zuken_summaries_fuses():
    """Zwraca zestaw bezpieczników dla projektu PS."""
    try:
        ps_code = request.args.get("ps", "") or request.args.get("ps_code", "")
        search = request.args.get("q", "") or request.args.get("search", "")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        if not ps_code:
            return jsonify({"error": smsg("psParamRequired")}), 400

        data = zuken_service.get_ps_fuses(
            ps_code=ps_code,
            search=search,
            limit=limit,
            offset=offset,
            lang=_app_lang()
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/summaries/relays", methods=["GET"])
def api_zuken_summaries_relays():
    """Zwraca zestaw przekaźników dla projektu PS."""
    try:
        ps_code = request.args.get("ps", "") or request.args.get("ps_code", "")
        search = request.args.get("q", "") or request.args.get("search", "")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        if not ps_code:
            return jsonify({"error": smsg("psParamRequired")}), 400

        data = zuken_service.get_ps_relays(
            ps_code=ps_code,
            search=search,
            limit=limit,
            offset=offset,
            lang=_app_lang()
        )
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/signal-path", methods=["GET"])
def api_zuken_signal_path():
    """Śledzenie sygnału przez graf połączeń — 'skąd dokąd jakim przewodem'.
    q przyjmuje formy: X429, X429:3, 'X429 pin 3', FH12, RT94..."""
    try:
        ps_code = request.args.get("ps", "") or request.args.get("ps_code", "")
        query = request.args.get("q", "") or request.args.get("query", "")
        if not ps_code or not query:
            return jsonify({"error": smsg("psQRequired")}), 400
        return jsonify(zuken_service.trace_signal_net(ps_code, query, lang=_app_lang()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zuken/summaries/export", methods=["GET"])
def api_zuken_summaries_export():
    """Eksportuje zestawienie do pliku CSV z kodowaniem UTF-8 BOM dla Excela."""
    try:
        ps_code = request.args.get("ps", "") or request.args.get("ps_code", "")
        summary_type = request.args.get("type", "connectors").lower()
        if not ps_code:
            return jsonify({"error": smsg("psParamRequired")}), 400

        if summary_type not in ["connectors", "fuses", "relays"]:
            summary_type = "connectors"

        csv_content = zuken_service.export_ps_summary_csv(ps_code, summary_type=summary_type, lang=_app_lang())
        type_names = {
            "connectors": "zlacza_pinout",
            "fuses": "bezpieczniki",
            "relays": "przekazniki"
        }
        filename = f"{ps_code}_{type_names.get(summary_type, 'zestawienie')}.csv"

        response = Response(csv_content, mimetype="text/csv", content_type="text/csv; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":

    init_db()
    port = CFG.get("PORT", 5000)
    host = CFG.get("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=True)