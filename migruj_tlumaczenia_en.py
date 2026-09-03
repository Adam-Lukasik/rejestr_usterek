# migruj_tlumaczenia_en.py — Narzędzie migracji i automatycznego tłumaczenia bazy na język angielski
# Rejestr Usterek v2.0

import os
import sys
import time
import json
import shutil
import sqlite3
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def translate_pl_to_en(text: str) -> str:
    """Tłumaczy tekst z języka polskiego na angielski przy użyciu endpointu Google Translate."""
    if not text or not str(text).strip():
        return ""
    text_str = str(text).strip()
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=pl&tl=en&dt=t&q=" + urllib.parse.quote(text_str)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5.0) as res:
            data = json.loads(res.read().decode("utf-8"))
            translated = "".join([segment[0] for segment in data[0] if segment and segment[0]])
            return translated.strip()
    except Exception as e:
        print(f"    [BŁĄD TŁUMACZENIA] {e}")
        return ""

def migrate_database(db_path: Path):
    print("=" * 65)
    print("  REJESTR USTEREK v2.0 — MIGRACJA BAZY DANYCH DO WERSJI PL/EN")
    print("=" * 65)
    print(f"Ścieżka do bazy: {db_path}")

    if not db_path.exists():
        print(f"[BŁĄD] Plik bazy nie istnieje: {db_path}")
        sys.exit(1)

    # 1. Kopia zapasowa
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak_{ts}")
    print(f"\n[1/4] Tworzenie kopii zapasowej bazy...")
    shutil.copy2(db_path, backup_path)
    print(f"      Utworzono kopię: {backup_path.name}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Migracja struktury tabel
    print(f"\n[2/4] Weryfikacja i aktualizacja kolumn w bazie SQLite...")
    cursor.execute("PRAGMA table_info(records)")
    rec_cols = [c["name"] for c in cursor.fetchall()]
    if "opisProblem_en" not in rec_cols:
        cursor.execute("ALTER TABLE records ADD COLUMN opisProblem_en TEXT")
        print("      + Dodano kolumnę records.opisProblem_en")
    if "opisNaprawa_en" not in rec_cols:
        cursor.execute("ALTER TABLE records ADD COLUMN opisNaprawa_en TEXT")
        print("      + Dodano kolumnę records.opisNaprawa_en")

    cursor.execute("PRAGMA table_info(solutions)")
    sol_cols = [c["name"] for c in cursor.fetchall()]
    if "tytul_en" not in sol_cols:
        cursor.execute("ALTER TABLE solutions ADD COLUMN tytul_en TEXT")
        print("      + Dodano kolumnę solutions.tytul_en")
    if "opis_en" not in sol_cols:
        cursor.execute("ALTER TABLE solutions ADD COLUMN opis_en TEXT")
        print("      + Dodano kolumnę solutions.opis_en")
    conn.commit()

    # 3. Tłumaczenie rekordów usterek
    print(f"\n[3/4] Analiza i tłumaczenie usterek (tabela 'records')...")
    cursor.execute("SELECT id, opisProblem, opisNaprawa, opisProblem_en, opisNaprawa_en FROM records")
    all_records = cursor.fetchall()

    translated_records = 0
    total_records = len(all_records)
    print(f"      Łącznie rekordów w bazie: {total_records}")

    for idx, r in enumerate(all_records, 1):
        rec_id = r["id"]
        prob = r["opisProblem"] or ""
        nap = r["opisNaprawa"] or ""
        prob_en = (r["opisProblem_en"] or "").strip()
        nap_en = (r["opisNaprawa_en"] or "").strip()

        need_update = False

        if prob and not prob_en:
            print(f"      [{idx}/{total_records}] Tłumaczenie problemu dla usterki {rec_id}...")
            prob_en = translate_pl_to_en(prob)
            need_update = True
            time.sleep(0.15)

        if nap and not nap_en:
            print(f"      [{idx}/{total_records}] Tłumaczenie naprawy dla usterki {rec_id}...")
            nap_en = translate_pl_to_en(nap)
            need_update = True
            time.sleep(0.15)

        if need_update:
            cursor.execute(
                "UPDATE records SET opisProblem_en = ?, opisNaprawa_en = ? WHERE id = ?",
                (prob_en, nap_en, rec_id)
            )
            translated_records += 1
            if translated_records % 10 == 0:
                conn.commit()

    conn.commit()
    print(f"      Zaktualizowano rekordów usterek: {translated_records}")

    # 4. Tłumaczenie wariantów rozwiązań
    print(f"\n[4/4] Analiza i tłumaczenie wariantów rozwiązań (tabela 'solutions')...")
    cursor.execute("SELECT id, tytul, opis, tytul_en, opis_en FROM solutions")
    all_solutions = cursor.fetchall()
    total_solutions = len(all_solutions)
    translated_solutions = 0
    print(f"      Łącznie wariantów w bazie: {total_solutions}")

    for idx, s in enumerate(all_solutions, 1):
        sol_id = s["id"]
        tytul = s["tytul"] or ""
        opis = s["opis"] or ""
        tytul_en = (s["tytul_en"] or "").strip()
        opis_en = (s["opis_en"] or "").strip()

        need_update = False

        if tytul and not tytul_en:
            print(f"      [{idx}/{total_solutions}] Tłumaczenie tytułu wariantu {sol_id}...")
            tytul_en = translate_pl_to_en(tytul)
            need_update = True
            time.sleep(0.15)

        if opis and not opis_en:
            print(f"      [{idx}/{total_solutions}] Tłumaczenie opisu wariantu {sol_id}...")
            opis_en = translate_pl_to_en(opis)
            need_update = True
            time.sleep(0.15)

        if need_update:
            cursor.execute(
                "UPDATE solutions SET tytul_en = ?, opis_en = ? WHERE id = ?",
                (tytul_en, opis_en, sol_id)
            )
            translated_solutions += 1
            if translated_solutions % 10 == 0:
                conn.commit()

    conn.commit()
    conn.close()
    print(f"      Zaktualizowano wariantów rozwiązań: {translated_solutions}")

    print("\n" + "=" * 65)
    print("  MIGRACJA ZAKOŃCZONA POMYŚLNIE!")
    print(f"  - Kopie bazy zapisano w: {backup_path.name}")
    print(f"  - Uzupełniono tłumaczenia dla {translated_records} usterek i {translated_solutions} wariantów.")
    print("=" * 65)

if __name__ == "__main__":
    db_name = sys.argv[1] if len(sys.argv) > 1 else "rejestr_usterek.db"
    db_file = BASE_DIR / db_name
    migrate_database(db_file)
