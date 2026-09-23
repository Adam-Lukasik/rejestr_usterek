"""
backup_service.py — Kopie zapasowe, paczki synchronizacyjne i scalanie baz SQLite.

Zasada działania:
- Pełna kopia bazy to spójny snapshot przez SQLite Online Backup API
  (bezpieczny przy WAL i działającej aplikacji — nie trzeba zamykać programu).
- Paczka (ZIP) = snapshot rejestr_usterek.db + manifest.json + opcjonalnie
  pliki Bazy Wiedzy (wszystkie albo delta od ostatniego eksportu sync).
- Scalanie DB<->DB przez ATTACH: nowe wiersze po UUID, konflikty rozstrzyga
  updated_at (nowsza wygrywa), usunięcia propagują sync_tombstones.
- Tabele Zuken są pochodne plików z Bazy Wiedzy — po imporcie paczki
  wystarczy reindeksacja (sync_all_knowledge_base), scalane są tylko
  zuken_glossary i zuken_bom_items.local_image.
"""

import os
import json
import shutil
import sqlite3
import zipfile
import platform
import tempfile
import time
from datetime import datetime as _dt
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rejestr_usterek.db")
BAZA_WIEDZY_DIR = os.path.join(BASE_DIR, "Baza wiedzy")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
AUTO_BACKUP_ENABLED = True
AUTO_BACKUP_KEEP = 15

APP_ID = "rejestr_usterek"
PACKAGE_FORMAT = 1
KB_ARCHIVE_PREFIX = "baza_wiedzy"

# Tabele scalane wierszowo z rozstrzyganiem konfliktów po updated_at
MERGED_ROW_TABLES = ("records", "solutions")
# Tabele z niezmienną zawartością (BLOB) — to samo UUID = ta sama zawartość
BLOB_TABLES = ("photos", "documents", "solution_photos", "solution_documents")
# Tabele objęte rejestrem usunięć (tombstone)
TOMBSTONED_TABLES = ("records", "solutions") + BLOB_TABLES


def configure(db_path=None, cfg=None, base_dir=None):
    """Ustawia ścieżki/opcje modułu na podstawie konfiguracji aplikacji."""
    global DB_PATH, BACKUP_DIR, AUTO_BACKUP_ENABLED, AUTO_BACKUP_KEEP, BAZA_WIEDZY_DIR
    if base_dir:
        BAZA_WIEDZY_DIR = os.path.join(base_dir, "Baza wiedzy")
    if db_path:
        DB_PATH = db_path
    if cfg:
        bd = (cfg.get("BACKUP_DIR") or "").strip()
        if bd:
            BACKUP_DIR = bd if os.path.isabs(bd) else os.path.join(BASE_DIR, bd)
        AUTO_BACKUP_ENABLED = bool(cfg.get("AUTO_BACKUP_ENABLED", True))
        try:
            AUTO_BACKUP_KEEP = max(1, int(cfg.get("AUTO_BACKUP_KEEP", 15)))
        except Exception:
            AUTO_BACKUP_KEEP = 15


def _now_iso():
    return _dt.now().isoformat(timespec="seconds")


def _stamp():
    return _dt.now().strftime("%Y%m%d_%H%M%S")


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _tables(conn, schema="main"):
    return {r[0] for r in conn.execute(
        f"SELECT name FROM {schema}.sqlite_master WHERE type='table'")}


def _table_cols(conn, table, schema="main"):
    return [r[1] for r in conn.execute(f"PRAGMA {schema}.table_info({table})")]


# ═══════════════════════════════════════════════════════════════════
# SNAPSHOT / WERYFIKACJA
# ═══════════════════════════════════════════════════════════════════

def quick_check_db(path):
    """Sprawdza, czy plik jest poprawną bazą aplikacji. Zwraca (ok, komunikat)."""
    try:
        with open(path, "rb") as f:
            if f.read(16) != b"SQLite format 3\x00":
                return False, "not_sqlite"
        conn = sqlite3.connect(path)
        row = conn.execute("PRAGMA quick_check(1)").fetchone()
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        if not row or row[0] != "ok":
            return False, f"quick_check: {row[0] if row else '?'}"
        if "records" not in tables:
            return False, "missing_records_table"
        return True, ""
    except Exception as e:
        return False, str(e)


def snapshot_db(dest_path):
    """Spójna kopia rejestr_usterek.db przez SQLite Backup API (online, WAL-safe)."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dest_path


def snapshot_into_backup_dir():
    """Ręczny snapshot .db do katalogu backupów."""
    dest = os.path.join(BACKUP_DIR, f"snapshot_{_stamp()}.db")
    return snapshot_db(dest)


# ═══════════════════════════════════════════════════════════════════
# AUTO-BACKUP PRZY STARCIE + ROTACJA
# ═══════════════════════════════════════════════════════════════════

def auto_backup_if_due():
    """Snapshot bazy do backups/auto/ przy starcie aplikacji + rotacja starych kopii."""
    if not AUTO_BACKUP_ENABLED:
        return None
    auto_dir = os.path.join(BACKUP_DIR, "auto")
    dest = os.path.join(auto_dir, f"rejestr_usterek_{_stamp()}.db")
    try:
        snapshot_db(dest)
        _rotate_auto(auto_dir)
        print(f"[BACKUP] Auto-backup: {dest}")
        return dest
    except Exception as e:
        print(f"[BACKUP] Błąd auto-backupu: {e}")
        return None


def _rotate_auto(auto_dir):
    try:
        files = sorted(
            Path(auto_dir).glob("rejestr_usterek_*.db"),
            key=lambda p: p.stat().st_mtime)
        while len(files) > AUTO_BACKUP_KEEP:
            files.pop(0).unlink(missing_ok=True)
    except Exception as e:
        print(f"[BACKUP] Błąd rotacji auto-kopii: {e}")


def list_backups():
    """Lista plików kopii w BACKUP_DIR (wraz z podkatalogiem auto/)."""
    out = []
    bdir = Path(BACKUP_DIR)
    if not bdir.is_dir():
        return out
    for p in bdir.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".db", ".zip"):
            continue
        rel = str(p.relative_to(bdir)).replace("\\", "/")
        if p.parent.name == "auto":
            kind = "auto"
        elif p.name.startswith("sync_"):
            kind = "sync"
        elif p.name.startswith(("pre_merge", "pre_restore")):
            kind = "safety"
        elif p.name.startswith("snapshot_"):
            kind = "snapshot"
        else:
            kind = "backup"
        st = p.stat()
        out.append({"name": rel, "size": st.st_size,
                    "mtime": st.st_mtime, "kind": kind})
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


# ═══════════════════════════════════════════════════════════════════
# BAZA WIEDZY — WYLICZANIE PLIKÓW I STAN SYNC
# ═══════════════════════════════════════════════════════════════════

def _kb_files():
    """Pliki Bazy Wiedzy: [(relpath_posix, abspath, size, mtime_epoch)]."""
    out = []
    if not os.path.isdir(BAZA_WIEDZY_DIR):
        return out
    for root, _, files in os.walk(BAZA_WIEDZY_DIR):
        for f in files:
            if f.startswith("~$"):
                continue
            ap = os.path.join(root, f)
            rel = os.path.relpath(ap, BAZA_WIEDZY_DIR).replace("\\", "/")
            try:
                st = os.stat(ap)
            except OSError:
                continue
            out.append((rel, ap, st.st_size, st.st_mtime))
    return out


def _get_sync_state():
    try:
        conn = _connect(DB_PATH)
        row = conn.execute(
            "SELECT value FROM lists WHERE key='sync_meta'").fetchone()
        conn.close()
        return json.loads(row["value"]) if row else {}
    except Exception:
        return {}


def _set_sync_state(**kw):
    st = _get_sync_state()
    st.update(kw)
    conn = _connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO lists (key, value) VALUES ('sync_meta', ?)",
        (json.dumps(st),))
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# PACZKI ZIP — BACKUP I SYNC
# ═══════════════════════════════════════════════════════════════════

def create_backup_package(kb_mode="none", kind="backup"):
    """Tworzy paczkę ZIP: snapshot .db + manifest + pliki Bazy Wiedzy wg kb_mode.

    kb_mode: "none" | "delta" (zmienione od ostatniego eksportu sync) | "all"
    kind:    "backup" | "sync"  (sync aktualizuje znacznik last_export_ts)
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    prefix = "sync" if kind == "sync" else "backup"
    zip_path = os.path.join(BACKUP_DIR, f"{prefix}_{_stamp()}.zip")

    tmpdir = tempfile.mkdtemp(prefix="ru_pkg_")
    try:
        tmp_db = os.path.join(tmpdir, "rejestr_usterek.db")
        snapshot_db(tmp_db)

        conn = _connect(tmp_db)
        counts = {}
        for t in ("records", "solutions", "photos", "documents",
                  "solution_photos", "solution_documents", "users"):
            try:
                counts[t] = conn.execute(
                    f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                pass
        conn.close()

        kb = _kb_files()
        ref_ts = 0.0
        if kb_mode == "delta":
            try:
                ref_ts = float(_get_sync_state().get("last_export_ts") or 0)
            except Exception:
                ref_ts = 0.0
        if kb_mode == "all":
            included = kb
        elif kb_mode == "delta":
            included = [x for x in kb if x[3] > ref_ts]
        else:
            included = []

        manifest = {
            "app": APP_ID,
            "format": PACKAGE_FORMAT,
            "kind": kind,
            "created": _now_iso(),
            "machine": platform.node(),
            "db_size": os.path.getsize(tmp_db),
            "tables": counts,
            "kb_mode": kb_mode,
            "kb_files_total": len(kb),
            "kb_included": [{"path": r, "size": s, "mtime": m}
                            for r, _, s, m in included],
        }

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as z:
            z.write(tmp_db, "rejestr_usterek.db")
            z.writestr("manifest.json",
                       json.dumps(manifest, ensure_ascii=False, indent=1))
            for rel, ap, _, _ in included:
                z.write(ap, f"{KB_ARCHIVE_PREFIX}/{rel}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if kind == "sync":
        try:
            _set_sync_state(last_export_ts=time.time())
        except Exception:
            pass

    return {"path": zip_path, "size": os.path.getsize(zip_path),
            "kb_included": len(included), "manifest": manifest}


# ═══════════════════════════════════════════════════════════════════
# IMPORT PACZKI — KOPIA PLIKÓW BW + MERGE BAZY + REINDEKSACJA
# ═══════════════════════════════════════════════════════════════════

def _kb_dest_path(rel):
    """Bezpieczna ścieżka docelowa pliku BW (ochrona przed zip-slip)."""
    dest = os.path.realpath(os.path.join(BAZA_WIEDZY_DIR, *rel.split("/")))
    root = os.path.realpath(BAZA_WIEDZY_DIR)
    if not dest.startswith(root + os.sep) and dest != root:
        return None
    return dest


def _extract_kb_from_zip(z, report):
    """Kopiuje pliki baza_wiedzy/* z paczki inkrementalnie do katalogu BW."""
    kb = report.setdefault("kb", {"copied": [], "overwritten": [], "skipped": []})
    for info in z.infolist():
        if info.is_dir() or not info.filename.startswith(KB_ARCHIVE_PREFIX + "/"):
            continue
        rel = info.filename[len(KB_ARCHIVE_PREFIX) + 1:]
        dest = _kb_dest_path(rel)
        if not dest:
            kb["skipped"].append(rel)
            continue
        action = None
        if not os.path.exists(dest):
            action = "copied"
        else:
            local_size = os.path.getsize(dest)
            if local_size != info.file_size:
                remote_ts = _dt(*info.date_time).timestamp()
                action = ("overwritten" if remote_ts > os.path.getmtime(dest)
                          else "skipped")
            else:
                action = "skipped"
        if action in ("copied", "overwritten"):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(info) as src_f, open(dest, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
            try:
                ts = _dt(*info.date_time).timestamp()
                os.utime(dest, (ts, ts))
            except Exception:
                pass
        kb.setdefault(action, []).append(rel)


def import_package(zip_path):
    """Importuje paczkę ZIP (lub surowy plik .db) i scala dane.

    Zwraca raport: {status, added, updated, conflicts, kb, reindex, ...}.
    """
    if not zipfile.is_zipfile(zip_path):
        # Surowy plik .db z drugiego komputera — tylko scalanie bazy
        return merge_database(zip_path)

    report = {"status": "ok"}
    tmpdir = tempfile.mkdtemp(prefix="ru_sync_")
    try:
        src_db = None
        manifest = {}
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            db_name = next((n for n in names if n.lower().endswith(".db")), None)
            if not db_name:
                return {"status": "error", "error": "no_db_in_package"}
            z.extract(db_name, tmpdir)
            src_db = os.path.join(tmpdir, db_name)
            if "manifest.json" in names:
                try:
                    manifest = json.loads(
                        z.read("manifest.json").decode("utf-8"))
                except Exception:
                    manifest = {}
            _extract_kb_from_zip(z, report)

        merge_rep = merge_database(src_db)
        for k, v in merge_rep.items():
            if k == "kb":
                continue
            report[k] = v
        report["manifest"] = manifest

        kb = report.get("kb", {})
        if kb.get("copied") or kb.get("overwritten"):
            try:
                import zuken_service
                report["reindex"] = zuken_service.sync_all_knowledge_base()
            except Exception as e:
                report["reindex_error"] = str(e)
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return report


# ═══════════════════════════════════════════════════════════════════
# SCALANIE BAZA ↔ BAZA
# ═══════════════════════════════════════════════════════════════════

def merge_database(src_path):
    """Scala dane z obcej bazy (drugi komputer) do bieżącej.

    Nowe wiersze po UUID; konflikt rozstrzyga updated_at (nowsza wygrywa);
    usunięcia propagowane przez sync_tombstones. Przed scaleniem robiony
    jest snapshot bezpieczeństwa backups/pre_merge_*.db.
    """
    ok, err = quick_check_db(src_path)
    if not ok:
        return {"status": "error", "error": err}

    os.makedirs(BACKUP_DIR, exist_ok=True)
    pre = os.path.join(BACKUP_DIR, f"pre_merge_{_stamp()}.db")
    try:
        snapshot_db(pre)
    except Exception:
        pre = ""

    report = {"status": "ok", "pre_backup": os.path.basename(pre) if pre else "",
              "added": {}, "updated": {}, "conflicts": [], "skipped": {}}

    conn = _connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("ATTACH DATABASE ? AS src", (src_path,))
    try:
        conn.execute("BEGIN IMMEDIATE")
        _merge_tombstones(conn, report)
        for t in MERGED_ROW_TABLES:
            _merge_row_table(conn, t, report)
        for t in BLOB_TABLES:
            _merge_insert_ignore(conn, t, report)
        _merge_lists(conn, report)
        _merge_users(conn, report)
        _merge_glossary(conn, report)
        _merge_bom_local_images(conn, report)
        _apply_tombstones(conn, report)
        _delete_orphans(conn, report)
        conn.commit()
    except Exception as e:
        conn.rollback()
        report["status"] = "error"
        report["error"] = str(e)
    finally:
        try:
            conn.execute("DETACH DATABASE src")
        except Exception:
            pass
        conn.close()

    # Zapisz raport scalania do backups/reports/
    try:
        rdir = os.path.join(BACKUP_DIR, "reports")
        os.makedirs(rdir, exist_ok=True)
        with open(os.path.join(rdir, f"merge_{_stamp()}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1, default=str)
    except Exception:
        pass
    return report


def _merge_tombstones(conn, report):
    if "sync_tombstones" not in _tables(conn, "src"):
        report["skipped"]["sync_tombstones"] = "no_src_table"
        return
    n = conn.execute("""
        INSERT OR IGNORE INTO sync_tombstones (table_name, row_id, deleted_at)
        SELECT table_name, row_id, deleted_at FROM src.sync_tombstones
    """).rowcount
    # Nowszy znacznik usunięcia wygrywa
    conn.execute("""
        UPDATE sync_tombstones
        SET deleted_at = (
            SELECT s.deleted_at FROM src.sync_tombstones s
            WHERE s.table_name = sync_tombstones.table_name
              AND s.row_id = sync_tombstones.row_id)
        WHERE EXISTS (
            SELECT 1 FROM src.sync_tombstones s
            WHERE s.table_name = sync_tombstones.table_name
              AND s.row_id = sync_tombstones.row_id
              AND s.deleted_at > sync_tombstones.deleted_at)
    """)
    report["added"]["sync_tombstones"] = n


def _merge_row_table(conn, table, report):
    """Scala records/solutions: INSERT nowych, UPDATE gdy źródło nowsze."""
    if table not in _tables(conn, "src"):
        report["skipped"][table] = "no_src_table"
        return
    src_cols = set(_table_cols(conn, table, "src"))
    cols = [c for c in _table_cols(conn, table, "main") if c in src_cols]
    if "id" not in cols:
        report["skipped"][table] = "no_id_column"
        return

    added = updated = 0
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM src.{table}").fetchall()
    for r in rows:
        local = conn.execute(
            f"SELECT * FROM {table} WHERE id=?", (r["id"],)).fetchone()
        if not local:
            conn.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) "
                f"VALUES ({', '.join('?' for _ in cols)})",
                tuple(r[c] for c in cols))
            added += 1
            continue

        local_keys = local.keys()
        src_ts = r["updated_at"] if ("updated_at" in cols and r["updated_at"]) \
            else (r["created"] if "created" in cols and r["created"] else "")
        loc_ts = local["updated_at"] if ("updated_at" in local_keys and local["updated_at"]) \
            else (local["created"] if "created" in local_keys and local["created"] else "")
        changed = any(
            (r[c] or "") != (local[c] or "")
            for c in cols if c not in ("id", "updated_at"))
        if not changed:
            continue
        label = ""
        for lc in ("klient", "opisProblem", "tytul"):
            if lc in cols and r[lc]:
                label = str(r[lc])[:60]
                break
        conflict = {"table": table, "id": r["id"], "label": label,
                    "remote_ts": src_ts, "local_ts": loc_ts}
        if src_ts > loc_ts:
            set_cols = [c for c in cols if c != "id"]
            conn.execute(
                f"UPDATE {table} SET "
                f"{', '.join(f'{c}=?' for c in set_cols)} WHERE id=?",
                tuple(r[c] for c in set_cols) + (r["id"],))
            updated += 1
            conflict["kept"] = "remote"
        else:
            conflict["kept"] = "local"
        report["conflicts"].append(conflict)

    report["added"][table] = added
    report["updated"][table] = updated


def _merge_insert_ignore(conn, table, report):
    """Scala tabele BLOB: to samo UUID = ta sama zawartość."""
    if table not in _tables(conn, "src"):
        report["skipped"][table] = "no_src_table"
        return
    src_cols = set(_table_cols(conn, table, "src"))
    cols = [c for c in _table_cols(conn, table, "main") if c in src_cols]
    n = conn.execute(
        f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM src.{table}").rowcount
    report["added"][table] = n if n and n > 0 else 0


def _merge_lists(conn, report):
    """Union-merge słowników (list rozwijanych) — jak w starym /api/import."""
    try:
        src_row = conn.execute(
            "SELECT value FROM src.lists WHERE key='lists'").fetchone()
    except Exception:
        return
    if not src_row:
        return
    try:
        new_lists = json.loads(src_row["value"])
    except Exception:
        return
    cur_row = conn.execute(
        "SELECT value FROM lists WHERE key='lists'").fetchone()
    try:
        cur_lists = json.loads(cur_row["value"]) if cur_row else {}
    except Exception:
        cur_lists = {}
    merged_items = 0
    for k, v in new_lists.items():
        if isinstance(v, list):
            arr = cur_lists.setdefault(k, [])
            for item in v:
                if item not in arr:
                    arr.append(item)
                    merged_items += 1
        elif isinstance(v, dict):
            d = cur_lists.setdefault(k, {})
            for sub_k, sub_v in v.items():
                if isinstance(sub_v, list):
                    sarr = d.setdefault(sub_k, [])
                    for item in sub_v:
                        if item not in sarr:
                            sarr.append(item)
                            merged_items += 1
    conn.execute(
        "INSERT OR REPLACE INTO lists (key, value) VALUES ('lists', ?)",
        (json.dumps(cur_lists),))
    report["lists_merged_items"] = merged_items


def _merge_users(conn, report):
    """Dopisuje brakujących użytkowników; nigdy nie nadpisuje haseł."""
    if "users" not in _tables(conn, "src"):
        return
    src_cols = set(_table_cols(conn, "users", "src"))
    cols = [c for c in _table_cols(conn, "users", "main") if c in src_cols]
    n = conn.execute(
        f"INSERT OR IGNORE INTO users ({', '.join(cols)}) "
        f"SELECT {', '.join(cols)} FROM src.users").rowcount
    report["added"]["users"] = n if n and n > 0 else 0
    for c in conn.execute("""
            SELECT s.username FROM src.users s
            JOIN users u ON u.username = s.username AND u.id != s.id
            """).fetchall():
        report["conflicts"].append(
            {"table": "users", "id": c["username"], "kept": "local",
             "label": c["username"]})


def _merge_glossary(conn, report):
    """Scala słownik skrótów Zuken po prefiksie (edytowany ręcznie)."""
    if "zuken_glossary" not in _tables(conn, "src") \
            or "zuken_glossary" not in _tables(conn, "main"):
        return
    n = conn.execute("""
        INSERT OR IGNORE INTO zuken_glossary (prefix, category, desc_pl, desc_en)
        SELECT prefix, category, desc_pl, desc_en FROM src.zuken_glossary
    """).rowcount
    report["added"]["zuken_glossary"] = n if n and n > 0 else 0
    for d in conn.execute("""
            SELECT g.prefix FROM zuken_glossary g
            JOIN src.zuken_glossary s ON s.prefix = g.prefix
            WHERE COALESCE(g.desc_pl,'') != COALESCE(s.desc_pl,'')
               OR COALESCE(g.desc_en,'') != COALESCE(s.desc_en,'')
            """).fetchall():
        report["conflicts"].append(
            {"table": "zuken_glossary", "id": d["prefix"], "kept": "local",
             "label": d["prefix"]})


def _merge_bom_local_images(conn, report):
    """Uzupełnia puste local_image w zuken_bom_items z drugiej bazy."""
    if "zuken_bom_items" not in _tables(conn, "src") \
            or "zuken_bom_items" not in _tables(conn, "main"):
        return
    n = conn.execute("""
        UPDATE zuken_bom_items
        SET local_image = (
            SELECT s.local_image FROM src.zuken_bom_items s
            WHERE s.article_number = zuken_bom_items.article_number
              AND s.local_image IS NOT NULL AND s.local_image != ''
            LIMIT 1)
        WHERE (local_image IS NULL OR local_image = '')
          AND EXISTS (
            SELECT 1 FROM src.zuken_bom_items s
            WHERE s.article_number = zuken_bom_items.article_number
              AND s.local_image IS NOT NULL AND s.local_image != '')
    """).rowcount
    report["updated"]["zuken_bom_items_local_image"] = n if n and n > 0 else 0


def _apply_tombstones(conn, report):
    """Usuwa lokalne wiersze starsze niż tombstone (usunięcie wygrywa)."""
    applied = 0
    for t in TOMBSTONED_TABLES:
        ts_col = "updated_at" if t in ("records", "solutions") else "created"
        cur = conn.execute(f"""
            DELETE FROM {t} WHERE id IN (
                SELECT tb.row_id FROM sync_tombstones tb
                JOIN {t} r ON r.id = tb.row_id
                WHERE tb.table_name = '{t}'
                  AND tb.deleted_at > COALESCE(r.{ts_col}, r.created, ''))
        """)
        if cur.rowcount and cur.rowcount > 0:
            applied += cur.rowcount
    report["tombstones_applied"] = applied


def _delete_orphans(conn, report):
    """Sprząta wiersze-dzieci bez rodzica (kaskada po scaleniu/usunięciu)."""
    n = 0
    for sql in (
        "DELETE FROM photos WHERE record_id NOT IN (SELECT id FROM records)",
        "DELETE FROM documents WHERE record_id NOT IN (SELECT id FROM records)",
        "DELETE FROM solutions WHERE record_id NOT IN (SELECT id FROM records)",
        "DELETE FROM solution_photos WHERE solution_id NOT IN (SELECT id FROM solutions)",
        "DELETE FROM solution_documents WHERE solution_id NOT IN (SELECT id FROM solutions)",
    ):
        try:
            cur = conn.execute(sql)
            if cur.rowcount and cur.rowcount > 0:
                n += cur.rowcount
        except Exception:
            pass
    report["orphans_removed"] = n


# ═══════════════════════════════════════════════════════════════════
# PRZYWRACANIE
# ═══════════════════════════════════════════════════════════════════

def restore_from_db(src_db_path):
    """Przywraca bazę z pliku .db (snapshot lub z paczki).

    Robi snapshot bezpieczeństwa obecnej bazy, potem nadpisuje żywą bazę
    przez SQLite Backup API (działa bez restartu aplikacji).
    """
    ok, err = quick_check_db(src_db_path)
    if not ok:
        return {"status": "error", "error": err}
    os.makedirs(BACKUP_DIR, exist_ok=True)
    pre = os.path.join(BACKUP_DIR, f"pre_restore_{_stamp()}.db")
    try:
        snapshot_db(pre)
    except Exception:
        pre = ""
    src = sqlite3.connect(src_db_path)
    dst = sqlite3.connect(DB_PATH)
    try:
        src.backup(dst)
        try:
            dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
    finally:
        dst.close()
        src.close()
    return {"status": "ok",
            "pre_backup": os.path.basename(pre) if pre else "",
            "requires_reload": True}


def restore_from_package(path, include_kb=True):
    """Przywraca z paczki ZIP (db + opcjonalnie pliki BW) lub z surowego .db."""
    if not zipfile.is_zipfile(path):
        return restore_from_db(path)

    report = {"status": "ok"}
    tmpdir = tempfile.mkdtemp(prefix="ru_restore_")
    try:
        src_db = None
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            db_name = next((n for n in names if n.lower().endswith(".db")), None)
            if not db_name:
                return {"status": "error", "error": "no_db_in_package"}
            z.extract(db_name, tmpdir)
            src_db = os.path.join(tmpdir, db_name)
            if include_kb:
                _extract_kb_from_zip(z, report)
        res = restore_from_db(src_db)
        report.update(res)
        if include_kb and (report.get("kb", {}).get("copied")
                           or report.get("kb", {}).get("overwritten")):
            try:
                import zuken_service
                report["reindex"] = zuken_service.sync_all_knowledge_base()
            except Exception as e:
                report["reindex_error"] = str(e)
    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return report


def backup_status():
    """Podsumowanie stanu kopii dla UI (ostatnia kopia, liczba, folder)."""
    items = list_backups()
    auto_items = [b for b in items if b["kind"] == "auto"]
    return {
        "backup_dir": BACKUP_DIR,
        "auto_enabled": AUTO_BACKUP_ENABLED,
        "auto_keep": AUTO_BACKUP_KEEP,
        "total": len(items),
        "auto_count": len(auto_items),
        "last_backup": items[0] if items else None,
        "last_auto": auto_items[0] if auto_items else None,
    }
