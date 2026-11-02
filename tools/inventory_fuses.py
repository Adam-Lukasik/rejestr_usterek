#!/usr/bin/env python3
# Inwentaryzacja bezpiecznikow per PS: symbole -F/-FH/-FR na aktywnym
# schemacie vs wiersze w zuken_ps_fuses vs boxy wykryte geometria PDF.
# Nierozpoznane symbole klasyfikowane:
#   FERRULE   -FR* (końcówki tulejkowe — nie bezpieczniki)
#   PIN       -FH491 = oprawka FH49 pin 1 (artefakt nazwy symbolu)
#   HOLDER    oprawka scalona z wierszem bezpiecznika / wiersz-gniazdo
#   MISSING   element -F bez wiersza — prawdziwy brak do dopięcia
# Uzycie: python tools/inventory_fuses.py [PS_CODE]
import io
import os
import re
import sqlite3
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import zuken_service as zs  # noqa: E402


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    zs.init_zuken_tables()
    conn = sqlite3.connect(zs.get_db().execute("PRAGMA database_list")
                           .fetchone()[2])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    pss = [r[0] for r in cur.execute(
        "SELECT DISTINCT ps_code FROM zuken_ps_fuses ORDER BY ps_code")]
    for ps in pss:
        if only and ps != only:
            continue
        print("=" * 70)
        print("PS:", ps)
        schem = cur.execute("""
            SELECT id, filepath, file_mtime FROM zuken_pdf_schematics
            WHERE is_active=1 AND COALESCE(doc_kind,'schematic')='schematic'
              AND ps_code=? ORDER BY id DESC LIMIT 1""", (ps,)).fetchone()
        path = zs.resolve_kb_filepath(schem["filepath"], heal_db=True) \
            if schem else None
        print("schemat:", schem["filepath"] if schem else "BRAK")

        sym_re = re.compile(r'^-F[HR]?\d')
        syms = sorted({r[0] for r in cur.execute("""
            SELECT symbol_name FROM zuken_pdf_symbols
            WHERE schematic_id=?""", (schem["id"],))
            if sym_re.match(r[0] or "")}) if schem else []
        rows = cur.execute("""
            SELECT device_clean, holder_code FROM zuken_ps_fuses
            WHERE ps_code=?""", (ps,)).fetchall()
        row_clean = {r["device_clean"] for r in rows}
        # oprawki przypisane do bezpiecznikow (holder_code) + ich sufiksy
        holders = {r["holder_code"].rsplit('-', 1)[-1].rstrip("'\"")
                   for r in rows if r["holder_code"]}
        sym_bare = {s.lstrip('-') for s in syms}

        cats = {'MISSING': [], 'FERRULE': [], 'PIN': [], 'HOLDER': []}
        for s in syms:
            bare = s.lstrip('-')
            if bare in row_clean:
                continue
            if bare.startswith('FR'):
                cats['FERRULE'].append(s)
            elif bare.startswith('FH'):
                if bare in holders:
                    cats['HOLDER'].append(s)
                    continue
                # pin oprawki: -FH<n><d> gdzie -FH<n> istnieje jako
                # symbol/wiersz (FH49:1 -> '-FH491')
                pin_of = None
                for k in range(len(bare) - 1, 2, -1):
                    base = bare[:k]
                    if base in row_clean or base in holders \
                            or base in sym_bare:
                        pin_of = base
                        break
                if pin_of:
                    cats['PIN'].append((s, pin_of))
                else:
                    cats['MISSING'].append(s)
            else:
                cats['MISSING'].append(s)

        print("symbole -F/-FH/-FR:", len(syms), "| wiersze:", len(rows))
        print("MISSING (elementy -F/-FH bez reprezentacji):",
              len(cats['MISSING']))
        for s in cats['MISSING']:
            print("   ", s)
        print("FERRULE (tulejki -FR, nie bezpieczniki):",
              len(cats['FERRULE']))
        print("PIN (etykiety pinow oprawek):", len(cats['PIN']),
              " ".join(f"{s}={b}" for s, b in cats['PIN'][:12]))
        print("HOLDER (oprawki scalone z bezpiecznikami):",
              len(cats['HOLDER']), " ".join(cats['HOLDER'][:12]))

        # boxy — wykrywanie geometryczne na kazdej stronie z tokenami xA
        if schem and path and os.path.exists(path):
            n_found = 0
            pages = [r[0] for r in cur.execute("""
                SELECT page_number FROM zuken_pdf_sheets
                WHERE schematic_id=? AND raw_text LIKE '%A%'""",
                (schem["id"],))]
            for pg in pages:
                for bx in zs._pdf_fuse_boxes(schem["id"], path, pg,
                                             schem["file_mtime"]):
                    cells = bx['cells']
                    outs = [c['out_dev'] for c in cells if c['out_dev']]
                    rats = [c['rating'] for c in cells if c['rating']]
                    n_found += 1
                    print("  box str.{}: {} pozycji | prady:{} | wyjscia:{}"
                          .format(pg, len(cells), rats[:14],
                                  outs[:10]))
            print("wykryte boxy:", n_found)
    conn.close()


if __name__ == '__main__':
    main()
