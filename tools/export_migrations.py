#!/usr/bin/env python3
# tools/export_migrations.py — eksport „danych systemowych" z dev-bazy do migracji
"""
Generuje migrations/NNNN_system_data.sql z bieżącą zawartością tabel systemowych
(pinouty złączy, aliasy firmowe). Plik trafia do paczki aktualizacji i jest
aplikowany przez app._run_migrations() w każdej bazie użytkownika.

Semantyka: DELETE + INSERT — stan tabeli po migracji zawsze zbiega się do stanu
dev-bazy (propagują się też usunięcia wierszy). Jeśli zawartość się nie zmieniła
od ostatniego eksportu, plik nie jest generowany.

Użycie:  python tools/export_migrations.py [--db rejestr_usterek.db]
Wywoływane automatycznie przez tools/build_release.py.
"""
import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime as _dt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")

# Tabele zarządzane centralnie — ich pełna zawartość jest eksportowana do paczki.
SYSTEM_TABLES = ("zuken_conn_pinouts", "zuken_query_aliases")

# Dane zmieniane automatycznie przy imporcie/uzupełnianiu — pomijane w porównaniu
# (nie chcemy wymuszać migracji przez same timestampy).
IGNORED_COLS_FOR_COMPARE = {"created_at", "updated_at"}


def _sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


def export_table(conn, table):
    """Zwraca (ddl_create_if_not_exists, lista_kolumn, lista_wierszy)."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if not cols:
        return None, [], []
    ddl = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone()
    ddl = (ddl[0] if ddl else f"CREATE TABLE {table} ({', '.join(cols)})")
    ddl = re.sub(r"^\s*CREATE TABLE", "CREATE TABLE IF NOT EXISTS", ddl, count=1)
    rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
    return ddl, cols, [tuple(r) for r in rows]


def _compare_key(cols, rows):
    """Klucz porównawczy wierszy — bez kolumn z IGNORED_COLS_FOR_COMPARE."""
    keep = [i for i, c in enumerate(cols) if c not in IGNORED_COLS_FOR_COMPARE]
    return sorted(tuple(r[i] for i in keep) for r in rows)


def generate_sql(exported):
    lines = [
        "-- Wygenerowano automatycznie przez tools/export_migrations.py",
        f"-- Data: {_dt.now().isoformat(timespec='seconds')}",
        "-- UWAGA: DELETE+INSERT — tabele systemowe są zarządzane centralnie,",
        "-- ich stan po migracji jest identyczny jak w dev-bazie.",
        "",
    ]
    for table, ddl, cols, rows in exported:
        lines.append(ddl.rstrip(";") + ";")
        lines.append(f"DELETE FROM {table};")
        for row in rows:
            vals = ", ".join(_sql_literal(v) for v in row)
            lines.append(f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({vals});")
        lines.append("")
    return "\n".join(lines)


def _existing_system_migrations():
    if not os.path.isdir(MIGRATIONS_DIR):
        return []
    return sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if re.match(r"^\d+_system_data\.sql$", f)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(BASE_DIR, "rejestr_usterek.db"))
    ap.add_argument("--force", action="store_true", help="generuj nawet gdy brak zmian")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"[EXPORT] Brak bazy: {args.db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.db)
    exported = []
    for table in SYSTEM_TABLES:
        ddl, cols, rows = export_table(conn, table)
        if ddl is None:
            print(f"[EXPORT] POMINIĘTO {table} — brak tabeli w bazie")
            continue
        exported.append((table, ddl, cols, rows))
        print(f"[EXPORT] {table}: {len(rows)} wierszy")
    conn.close()

    if not exported:
        print("[EXPORT] Brak tabel do eksportu")
        return 0

    new_sql = generate_sql(exported)

    # Porównaj z ostatnim eksportem — jeśli treść bez nagłówka identyczna, pomijamy.
    old_files = _existing_system_migrations()
    if old_files and not args.force:
        old_path = os.path.join(MIGRATIONS_DIR, old_files[-1])
        try:
            with open(old_path, "r", encoding="utf-8") as f:
                old_body = "\n".join(
                    l for l in f.read().splitlines()
                    if l.strip() and not l.startswith("--"))
            new_body = "\n".join(
                l for l in new_sql.splitlines()
                if l.strip() and not l.startswith("--"))
            if old_body == new_body:
                print(f"[EXPORT] Brak zmian — zostaje {old_files[-1]}")
                return 0
        except Exception:
            pass

    os.makedirs(MIGRATIONS_DIR, exist_ok=True)
    used = set()
    for f in os.listdir(MIGRATIONS_DIR):
        m = re.match(r"^(\d+)_", f)
        if m:
            used.add(int(m.group(1)))
    next_num = max(used, default=0) + 1
    fname = f"{next_num:04d}_system_data.sql"

    # Usuń poprzednie eksporty system_data — DELETE+INSERT czyni je redundantnymi.
    for f in _existing_system_migrations():
        os.remove(os.path.join(MIGRATIONS_DIR, f))
        print(f"[EXPORT] Usunięto przestarzały {f}")

    path = os.path.join(MIGRATIONS_DIR, fname)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_sql)
    print(f"[EXPORT] Utworzono migrations/{fname}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
