#!/usr/bin/env python3
# tools/zabezpiecz_systemowe.py — ochrona lokalnych wierszy tabel systemowych
# przy aktualizacji paczki release.
#
# Migracje paczki (migrations/NNNN_system_data.sql) robią DELETE+INSERT na
# tabelach zarządzanych centralnie:
#   - zuken_conn_pinouts   : DELETE * (pełne czyszczenie)
#   - zuken_query_aliases  : DELETE * (pełne czyszczenie)
#   - zuken_translations   : DELETE tylko wierszy source != 'local'
# Wiersze dopisane lokalnie w innej bazie (np. w pracy, gdy dev-baza była
# nieaktualna) zniknęłyby przy pierwszym starcie nowej wersji.
#
# Użycie:
#   PRZED aktualizacją (na bazie, którą chcesz ochronić):
#       python tools/zabezpiecz_systemowe.py dump <baza.db> <zrzut.json>
#   PO aktualizacji — sprawdzenie, co zniknęło:
#       python tools/zabezpiecz_systemowe.py diff <baza.db> <zrzut.json>
#   PO aktualizacji — przywrócenie brakujących wierszy:
#       python tools/zabezpiecz_systemowe.py restore <baza.db> <zrzut.json>
#
# restore wstawia wyłącznie wiersze, których klucza nie ma w bazie — dane
# dostarczone przez migrację zostają nienaruszone.

import json
import os
import sqlite3
import sys
from datetime import datetime

# Tabela -> kolumna klucza naturalnego (deduplikacja przy diff/restore).
TABLE_KEYS = {
    "zuken_conn_pinouts": "article",
    "zuken_query_aliases": "phrase",
    "zuken_translations": "form",
}


def _table_cols(conn, table):
    info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in info] if info else None


def cmd_dump(db_path, out_path):
    conn = sqlite3.connect(db_path)
    dump = {"created_at": datetime.now().isoformat(timespec="seconds"),
            "db": os.path.abspath(db_path), "tables": {}}
    for table, key in TABLE_KEYS.items():
        cols = _table_cols(conn, table)
        if cols is None:
            print(f"[DUMP] {table}: brak tabeli — pomijam")
            continue
        rows = [tuple(r) for r in conn.execute(
            f"SELECT {', '.join(cols)} FROM {table}").fetchall()]
        dump["tables"][table] = {"key": key, "cols": cols, "rows": rows}
        print(f"[DUMP] {table}: {len(rows)} wierszy")
    conn.close()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print(f"[DUMP] zapisano {out_path}")
    return 0


def _missing(conn, entry):
    table_cols = _table_cols(conn, entry["table"])
    if table_cols is None:
        return entry["rows"]  # tabela zniknęła — wszystko do przywrócenia
    cols, key = entry["cols"], entry["key"]
    ki = cols.index(key)
    existing = {r[0] for r in conn.execute(
        f"SELECT {key} FROM {entry['table']}").fetchall()}
    return [r for r in entry["rows"] if r[ki] not in existing]


def _load_dump(dump_path):
    with open(dump_path, "r", encoding="utf-8") as f:
        dump = json.load(f)
    entries = []
    for table, data in dump.get("tables", {}).items():
        entries.append({"table": table, "key": data["key"],
                        "cols": data["cols"], "rows": [tuple(r) for r in data["rows"]]})
    return entries


def cmd_diff(db_path, dump_path):
    conn = sqlite3.connect(db_path)
    total = 0
    for e in _load_dump(dump_path):
        missing = _missing(conn, e)
        total += len(missing)
        print(f"[DIFF] {e['table']}: {len(missing)} wierszy ze zrzutu nie ma w bazie")
        ki = e["cols"].index(e["key"])
        for r in missing[:50]:
            print(f"    - {e['key']}={r[ki]!r}")
        if len(missing) > 50:
            print(f"    ... i {len(missing) - 50} więcej")
    conn.close()
    print(f"[DIFF] razem: {total}")
    return 0


def cmd_restore(db_path, dump_path):
    conn = sqlite3.connect(db_path)
    for e in _load_dump(dump_path):
        missing = _missing(conn, e)
        if not missing:
            print(f"[RESTORE] {e['table']}: nic do przywrócenia")
            continue
        cols = _table_cols(conn, e["table"])
        if cols is None:
            print(f"[RESTORE] {e['table']}: brak tabeli — POMINIĘTO")
            continue
        # Wstawiamy tylko kolumny istniejące w docelowej tabeli; sztuczny
        # klucz 'id' pomijamy, gdy kluczem naturalnym jest inna kolumna
        # (AUTOINCREMENT nada nowy, UNIQUE(klucz) pilnuje duplikatów).
        src_idx = [i for i, c in enumerate(e["cols"]) if c in cols
                   and not (c == "id" and e["key"] != "id")]
        dst_cols = [e["cols"][i] for i in src_idx]
        sql = (f"INSERT OR IGNORE INTO {e['table']} ({', '.join(dst_cols)}) "
               f"VALUES ({', '.join('?' for _ in dst_cols)})")
        conn.executemany(sql, ([r[i] for i in src_idx] for r in missing))
        print(f"[RESTORE] {e['table']}: przywrócono {len(missing)} wierszy")
    conn.commit()
    conn.close()
    return 0


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("dump", "diff", "restore"):
        print(__doc__ or "użycie: zabezpiecz_systemowe.py dump|diff|restore <baza.db> <zrzut.json>")
        return 2
    cmd, db_path, dump_path = sys.argv[1], sys.argv[2], sys.argv[3]
    if not os.path.exists(db_path):
        sys.exit(f"[BLAD] brak bazy: {db_path}")
    if cmd != "dump" and not os.path.exists(dump_path):
        sys.exit(f"[BLAD] brak zrzutu: {dump_path}")
    return {"dump": cmd_dump, "diff": cmd_diff, "restore": cmd_restore}[cmd](db_path, dump_path)


if __name__ == "__main__":
    sys.exit(main())
