"""Test trójjęzycznych pól usterek/rozwiązań — fałszywy tłumacz, tymczasowa baza."""
import os, sys, tempfile, json

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import app as A

tmp = tempfile.mkdtemp()
A.DB_PATH = os.path.join(tmp, "test.db")
A.init_db()

# Fałszywy tłumacz: [dst] tekst
calls = []
def fake_translate(text, src, dst):
    calls.append((src, dst, text))
    return f"[{dst}]{text}"
A.translate_text = fake_translate

cli = A.app.test_client()
ok = True
def check(name, cond, extra=""):
    global ok
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond: ok = False

# 1. Utworzenie usterki w PL
r = cli.post("/api/records", json={"id": "r1", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Pęknięty przewód", "opisNaprawa": ""},
             headers={"X-App-Lang": "pl"})
d = r.get_json()
check("create pl", d["opisProblem"] == "Pęknięty przewód" and d["opisProblem_en"] == "[en]Pęknięty przewód" and d["opisProblem_de"] == "[de]Pęknięty przewód")

# 2. Utworzenie usterki w DE — tekst trafia do _de, PL/EN tłumaczone
r = cli.post("/api/records", json={"id": "r2", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Gerissenes Kabel", "opisNaprawa": "Kabel ersetzt"},
             headers={"X-App-Lang": "de"})
d = r.get_json()
check("create de", d["opisProblem_de"] == "Gerissenes Kabel" and d["opisProblem"] == "[pl]Gerissenes Kabel" and d["opisProblem_en"] == "[en]Gerissenes Kabel")
check("create de naprawa", d["opisNaprawa_de"] == "Kabel ersetzt" and d["opisNaprawa"] == "[pl]Kabel ersetzt")

# 3. Utworzenie w EN
r = cli.post("/api/records", json={"id": "r3", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Broken wire"}, headers={"X-App-Lang": "en"})
d = r.get_json()
check("create en", d["opisProblem_en"] == "Broken wire" and d["opisProblem"] == "[pl]Broken wire" and d["opisProblem_de"] == "[de]Broken wire")

# 4. Edycja bez zmian treści (DE user zapisuje niezmieniony tekst DE) — brak re-tłumaczeń
calls.clear()
r = cli.put("/api/records/r2", json={"klient": "K", "model": "M", "typ": "T",
                                     "opisProblem": "Gerissenes Kabel", "opisNaprawa": "Kabel ersetzt",
                                     "status": "open"}, headers={"X-App-Lang": "de"})
check("edit unchanged -> no translate", len(calls) == 0, f"calls={calls}")

# 5. Edycja treści w EN — regeneracja PL i DE
calls.clear()
r = cli.put("/api/records/r3", json={"klient": "K", "model": "M", "typ": "T",
                                     "opisProblem": "Broken wire v2", "status": "open"},
            headers={"X-App-Lang": "en"})
d = r.get_json()
check("edit en", d["opisProblem_en"] == "Broken wire v2" and d["opisProblem"] == "[pl]Broken wire v2" and d["opisProblem_de"] == "[de]Broken wire v2")

# 6. Prefill fallback: DE user otwiera rekord PL-only (r4) i zapisuje bez zmian -> backfill
r = cli.post("/api/records", json={"id": "r4", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Tylko po polsku"}, headers={"X-App-Lang": "pl"})
calls.clear()
r = cli.put("/api/records/r4", json={"klient": "K", "model": "M", "typ": "T",
                                     "opisProblem": "Tylko po polsku", "status": "open"},
            headers={"X-App-Lang": "de"})
d = r.get_json()
check("prefill fallback stays pl", d["opisProblem"] == "Tylko po polsku" and d["opisProblem_en"] == "[en]Tylko po polsku" and d["opisProblem_de"] == "[de]Tylko po polsku")

# 7. Solutions: create w DE + update w PL
r = cli.post("/api/records/r1/solutions", json={"tytul": "Kabelwechsel", "opis": "Neues Kabel verlegt"},
             headers={"X-App-Lang": "de"})
d = r.get_json()
check("sol create de", d["tytul_de"] == "Kabelwechsel" and d["tytul"] == "[pl]Kabelwechsel" and d["tytul_en"] == "[en]Kabelwechsel" and d["opis_de"] == "Neues Kabel verlegt")
sol_id = d["id"]

r = cli.put(f"/api/solutions/{sol_id}", json={"tytul": "Wymiana kabla", "opis": "[pl]Neues Kabel verlegt"},
            headers={"X-App-Lang": "pl"})
d = r.get_json()
check("sol update pl", d["tytul"] == "Wymiana kabla" and d["tytul_en"] == "[en]Wymiana kabla" and d["tytul_de"] == "[de]Wymiana kabla")

# 8. GET solutions zwraca _de
r = cli.get("/api/records/r1/solutions")
row = r.get_json()[0]
check("sol GET has de", "tytul_de" in row and "opis_de" in row)

# 9. Błąd tłumacza -> stara wartość zostaje, zapis przechodzi
def failing(text, src, dst):
    return ""
A.translate_text = failing
r = cli.post("/api/records", json={"id": "r5", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Awaria X"}, headers={"X-App-Lang": "pl"})
d = r.get_json()
check("translate fail tolerated", r.status_code == 201 and d["opisProblem"] == "Awaria X" and not d["opisProblem_en"] and not d["opisProblem_de"])

# 10. Edycja EN przy martwym tłumaczu nie niszczy istniejącego DE
A.translate_text = fake_translate
r = cli.post("/api/records", json={"id": "r6", "klient": "K", "model": "M", "typ": "T",
                                   "opisProblem": "Fehler Y"}, headers={"X-App-Lang": "de"})
A.translate_text = failing
r = cli.put("/api/records/r6", json={"klient": "K", "model": "M", "typ": "T",
                                     "opisProblem": "Fehler Y2", "status": "open"},
            headers={"X-App-Lang": "de"})
d = r.get_json()
check("fail keeps old translations", d["opisProblem_de"] == "Fehler Y2" and d["opisProblem"] == "[pl]Fehler Y" and d["opisProblem_en"] == "[en]Fehler Y", str(d))

# 11. Migracja starej bazy: tabela bez _de -> ALTER dodaje kolumny
import sqlite3
db2 = os.path.join(tmp, "old.db")
c = sqlite3.connect(db2)
c.execute("""CREATE TABLE records (id TEXT PRIMARY KEY, created TEXT NOT NULL, klient TEXT NOT NULL,
             model TEXT NOT NULL, projekt TEXT NOT NULL, vin TEXT, typ TEXT NOT NULL, element TEXT,
             opisProblem TEXT NOT NULL, opisNaprawa TEXT, status TEXT NOT NULL DEFAULT 'open',
             created_by TEXT, fixed_by TEXT, fixed_at TEXT, opisProblem_en TEXT, opisNaprawa_en TEXT)""")
c.execute("""CREATE TABLE solutions (id TEXT PRIMARY KEY, record_id TEXT NOT NULL, numer INTEGER NOT NULL DEFAULT 1,
             tytul TEXT NOT NULL, opis TEXT, created_by TEXT, created TEXT NOT NULL, tytul_en TEXT, opis_en TEXT)""")
c.commit(); c.close()
A.DB_PATH = db2
A.init_db()
c = sqlite3.connect(db2)
rec_cols = {r[1] for r in c.execute("PRAGMA table_info(records)")}
sol_cols = {r[1] for r in c.execute("PRAGMA table_info(solutions)")}
c.close()
check("migration records _de", {"opisProblem_de", "opisNaprawa_de"} <= rec_cols)
check("migration solutions _de", {"tytul_de", "opis_de"} <= sol_cols)

print("\nALL OK" if ok else "\nSOME FAILURES")
sys.exit(0 if ok else 1)
