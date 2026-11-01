#!/usr/bin/env python3
"""Wgrywa data/terms_seed.json do tabeli zuken_translations w dev-bazie.

Wpisy z seeda -> source='core', auto=1 (do weryfikacji przez Adama).
Potem: tools/export_migrations.py wygeneruje migrację do paczki.
"""
import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("RU_DB_PATH") or os.path.join(BASE_DIR, "rejestr_usterek.db")
SEED = os.path.join(BASE_DIR, "data", "terms_seed.json")

sys.path.insert(0, BASE_DIR)
import zuken_service  # noqa: E402


def main():
    data = json.load(open(SEED, encoding="utf-8"))
    entries = data["entries"]
    zuken_service.DB_PATH = DB_PATH
    zuken_service.init_zuken_tables()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n = 0
    for e in entries:
        cur.execute("""
            INSERT INTO zuken_translations (form, kind, pl, en, de, sample, source, auto, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'core', 1, datetime('now'))
            ON CONFLICT(form) DO UPDATE SET
                kind = excluded.kind, pl = excluded.pl, en = excluded.en,
                de = excluded.de, sample = excluded.sample,
                source = 'core', updated_at = datetime('now');
        """, (e["form"], e["kind"], e["pl"], e["en"], e["de"], e.get("sample", "")))
        n += 1
    conn.commit()
    conn.close()
    zuken_service._invalidate_terms_cache()
    print(f"[SEED] {n} wpisów -> {DB_PATH}")


if __name__ == "__main__":
    sys.exit(main())
