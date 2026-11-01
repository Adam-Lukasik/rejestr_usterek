#!/usr/bin/env python3
"""Zbiera unikalne teksty schematu do przetłumaczenia z dev-bazy.

Wynik: data/terms_raw.json
  {"forms": [{form, sample, sources}], "tokens": [{token, count, samples}]}
- forms: znormalizowane frazy (signal_name, function, sheet_title, części
  circuits, system_desc/location_desc, wire_color, desc_en/desc_pl glossary)
- tokens: statystyka pojedynczych słów (do słownika tokenowego)

Następnie: uzupełnić pl/en/de w data/terms_seed.json i wgrać przez
tools/seed_terms.py.
"""
import os
import re
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("RU_DB_PATH") or os.path.join(BASE_DIR, "rejestr_usterek.db")
OUT_PATH = os.path.join(BASE_DIR, "data", "terms_raw.json")

TOKEN_RE = re.compile(r"[A-Za-zÀ-ž]{2,}")
CODE_RE = re.compile(r"\d")


def tnorm(s):
    s = re.sub(r"[_–—]+", " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    forms = {}   # norm -> {"sample": str, "sources": set, "count": int}

    def add(raw, source, n=1):
        raw = (raw or "").strip()
        if not raw:
            return
        nf = tnorm(raw)
        if not nf or len(nf) < 2:
            return
        e = forms.setdefault(nf, {"form": nf, "sample": raw, "sources": set(), "count": 0})
        e["sources"].add(source)
        e["count"] += n
        if len(raw) > len(e["sample"]):
            e["sample"] = raw

    for r in cur.execute("""
            SELECT signal_name, COUNT(*) c FROM zuken_connections
            WHERE TRIM(COALESCE(signal_name,'')) != ''
            GROUP BY signal_name"""):
        add(r["signal_name"], "signal_name", r["c"])

    for r in cur.execute("""
            SELECT function, COUNT(*) c FROM zuken_bom_devices
            WHERE TRIM(COALESCE(function,'')) != ''
            GROUP BY function"""):
        add(r["function"], "function", r["c"])

    for r in cur.execute("""
            SELECT sheet_title, COUNT(*) c FROM zuken_pdf_sheets
            WHERE TRIM(COALESCE(sheet_title,'')) != ''
            GROUP BY sheet_title"""):
        add(r["sheet_title"], "sheet_title", r["c"])

    for r in cur.execute("""
            SELECT circuits FROM zuken_ps_fuses
            WHERE TRIM(COALESCE(circuits,'')) != ''"""):
        for part in re.split(r"\s*,\s*", r["circuits"] or ""):
            add(part, "circuits")

    for t in ("zuken_ps_connectors", "zuken_ps_fuses", "zuken_ps_relays"):
        try:
            for col in ("system_desc", "location_desc"):
                for r in cur.execute(f"""
                        SELECT DISTINCT {col} FROM {t}
                        WHERE TRIM(COALESCE({col},'')) != ''"""):
                    add(r[0], col)
        except sqlite3.OperationalError:
            pass

    for r in cur.execute("""
            SELECT wire_color, COUNT(*) c FROM zuken_connections
            WHERE TRIM(COALESCE(wire_color,'')) != ''
            GROUP BY wire_color"""):
        add(r["wire_color"], "wire_color", r["c"])

    for r in cur.execute("SELECT desc_pl, desc_en FROM zuken_glossary"):
        add(r["desc_en"], "glossary")
        add(r["desc_pl"], "glossary")

    # statystyka tokenów słownych (nie-kodowych)
    toks = {}
    for f in forms.values():
        for w in TOKEN_RE.findall(f["sample"]):
            if CODE_RE.search(w):
                continue
            e = toks.setdefault(w.casefold(), {"token": w.casefold(), "count": 0, "samples": set()})
            e["count"] += f["count"]
            if len(e["samples"]) < 6:
                e["samples"].add(f["sample"])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    out_forms = [{"form": e["form"], "sample": e["sample"],
                  "sources": sorted(e["sources"]), "count": e["count"]}
                 for e in sorted(forms.values(), key=lambda e: (-e["count"], e["form"]))]
    out_toks = [{"token": t["token"], "count": t["count"],
                 "samples": sorted(t["samples"])}
                for t in sorted(toks.values(), key=lambda e: (-e["count"], e["token"]))]
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"forms": out_forms, "tokens": out_toks}, f,
                  ensure_ascii=False, indent=1)
    print(f"forms: {len(out_forms)}  tokens: {len(out_toks)}  -> {OUT_PATH}")


if __name__ == "__main__":
    sys.exit(main())
