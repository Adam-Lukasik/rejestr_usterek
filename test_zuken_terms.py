"""Test słownika tłumaczeń tekstów schematu (zuken_translations) — temp-DB."""
import os, sys, tempfile
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import zuken_service as z

tmp = tempfile.mkdtemp()
z.DB_PATH = os.path.join(tmp, "t.db")
z.init_zuken_tables()
z._invalidate_terms_cache()

ok = True
def check(name, cond, extra=""):
    global ok
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond: ok = False

# seed testowy
for d in [
    {"form": "versorgung zentralverriegelung", "pl": "Zasilanie centralnego zamka", "en": "central locking supply", "de": "Versorgung Zentralverriegelung"},
    {"form": "sirene", "kind": "token", "pl": "syrena", "en": "siren", "de": "Sirene"},
    {"form": "aktiv", "kind": "token", "pl": "aktywna", "en": "active", "de": "aktiv"},
    {"form": "ecorun", "kind": "jargon", "pl": "ECORUN", "en": "ECORUN", "de": "ECORUN"},
]:
    z.upsert_term(d)

check("fraza 1:1", z.translate_term("Versorgung Zentralverriegelung", "pl") == "Zasilanie centralnego zamka")
check("fraza en", z.translate_term("Versorgung Zentralverriegelung", "en") == "Central locking supply")
check("ALL-CAPS", z.translate_term("SIRENE AKTIV", "pl") == "SYRENA AKTYWNA")
check("tokeny mieszane", z.translate_term("Data Sirene Aktiv", "pl") == "Data Syrena Aktywna")
check("jargon", z.translate_term("ECORUN FEED", "de") == "ECORUN FEED" or z.translate_term("ECORUN", "de") == "ECORUN")
check("kod zostaje", "X133" in z.translate_term("GND_X133", "pl") and "#5996" in z.translate_term("#5996, Sirene", "pl"))
check("bez słownika dla zh", z.translate_term("Sirene", "zh") == "Syrena" or z.translate_term("Sirene", "zh") == "Sirene")

# kolejka unknown: 'niczane' powinno trafić do zuken_term_unknown
z._localize_payload({"signal_name": "Ganzneu"}, "pl")
r = z.list_unknown_terms()
check("unknown kolejka", any(i["form"] == "ganzneu" for i in r["items"]), str(r["items"][:3]))

# _localize_payload: pola _t + specjalne
p = {"signal_name": "Sirene", "circuits": {"Sirene 1": [{"x": 1}]}, "more_signals": ["SIRENE AKTIV"], "resolved": {"label": "Sirene"}}
z._localize_payload(p, "pl")
check("signal_name_t", p["signal_name_t"] == "Syrena", p.get("signal_name_t"))
check("circuits_t map", p["circuits_t"] == {"Sirene 1": "Syrena 1"}, p.get("circuits_t"))
check("more_signals_t", p["more_signals_t"] == ["SYRENA AKTYWNA"], p.get("more_signals_t"))
check("label_t", p["resolved"].get("label_t") == "Syrena", p["resolved"])

# conn_meta: desc/label nietłumaczone (katalog)
p2 = {"conn_meta": {"X1": {"desc": "Sirene Plug", "function": "Sirene"}}}
z._localize_payload(p2, "pl")
check("conn_meta desc nietknięty", "desc_t" not in p2["conn_meta"]["X1"], p2)
check("conn_meta function tak", p2["conn_meta"]["X1"].get("function_t") == "Syrena")

# CRUD + bramka source=local
z.delete_term("sirene")
check("delete", z.translate_term("Sirene", "pl") == "Sirene")

# explain_device_code de -> przez słownik (brak desc_de w glossary)
z.upsert_term({"form": "gnd", "kind": "token", "pl": "masa", "en": "GND", "de": "Masse"})
print("\nALL OK" if ok else "\nSOME FAILURES")
sys.exit(0 if ok else 1)
