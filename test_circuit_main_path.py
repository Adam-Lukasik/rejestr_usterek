"""Regresja asystenta obwodów: main_path / main_candidates / cls końców /
klasa tłumienia cewki. Działa na bazie projektu (PS011871, PS012732) —
gdy bazy nie ma, testy danych są pomijane (SKIP), a sprawdzenie składni
frontendu i kompletności i18n idzie zawsze.

Baza: RU_DATA_DIR albo domyślna z config.json."""
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import zuken_service as z  # noqa: E402

ok = True


def check(name, cond, extra=""):
    global ok
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond:
        ok = False


def skip(name, why):
    print("SKIP", name, why)


# ── frontend: składnia inline JS + i18n ──────────────────────────────────────
html = open(os.path.join(BASE, "rejestr_usterek.html"), encoding="utf-8").read()
big = max(re.findall(r"<script>(.*?)</script>", html, re.S), key=len)
tmp_js = os.path.join(BASE, "_syntax_check.tmp.js")
try:
    open(tmp_js, "w", encoding="utf-8").write(big)
    r = subprocess.run(["node", "--check", tmp_js], capture_output=True, text=True)
    check("frontend: node --check inline JS", r.returncode == 0, (r.stderr or "")[:200])
except FileNotFoundError:
    skip("frontend: node --check", "brak node")
finally:
    if os.path.exists(tmp_js):
        os.remove(tmp_js)
try:
    r = subprocess.run(["node", os.path.join(BASE, "check_i18n.js")],
                       capture_output=True, text=True, cwd=BASE)
    out = r.stdout
    check("i18n: pl/en/de kompletne",
          "in pl missing in en: []" in out and "in pl missing in de: []" in out
          and "in en not in pl: []" in out and "in de not in pl: []" in out)
except FileNotFoundError:
    skip("i18n", "brak node")

# ── dane projektu ────────────────────────────────────────────────────────────
PS1, PS2 = "PS011871", "PS012732"


def trace(ps, q):
    try:
        return z.trace_circuit(ps, q)
    except Exception as e:  # brak bazy / tabel
        print("   (trace error:", e, ")")
        return None


probe = trace(PS1, "394")
if not (probe and probe.get("ok") and probe.get("loads")):
    skip("dane PS011871", "brak projektu w bazie")
else:
    ALLOWED = {"feed", "load", "ground", "coil", "branch"}

    def ends_of(cp):
        return [e for l in cp["loads"] for p in l["pins"] for e in p["ends"]]

    def hop_cleans(cp):
        s = set()
        for h in (cp.get("main_path") or {}).get("hops", []):
            s.add(h.get("from_clean"))
            s.add(h.get("to_clean"))
        return s

    # 394 — mostkowanie plusów akumulatorów: RT102(G3) ↔ RT72(AKU1)
    mp = probe.get("main_path") or {}
    check("394: kind=bridge", mp.get("kind") == "bridge", str(mp.get("kind")))
    check("394: końce G3 i AKU1",
          {mp.get("a", {}).get("clean"), mp.get("b", {}).get("clean")} == {"G3", "AKU1"})
    hc = hop_cleans(probe)
    check("394: tor przez RT102 i RT72 oraz K1", {"RT102", "RT72", "K1"} <= hc, str(sorted(hc))[:160])
    mc = probe.get("main_candidates") or []
    check("394: kandydat 0 = main_path", bool(mc) and mc[0]["kind"] == "bridge"
          and {mc[0]["a_label"], mc[0]["b_label"]} == {"G3:+", "AKU1:+"})
    check("394: wszystkie końce mają cls", all(e.get("cls") in ALLOWED for e in ends_of(probe)))
    check("394: kandydaci mają hopy i indeksy",
          all(c.get("hops") and {"li", "pi", "ei"} <= set(c["a"]) for c in mc))

    # K1 — ten sam obwód z poziomu przekaźnika + cewka z BOM
    cp = trace(PS1, "K1")
    mpk = (cp or {}).get("main_path") or {}
    check("K1: bridge G3/AKU1", mpk.get("kind") == "bridge"
          and {mpk.get("a", {}).get("clean"), mpk.get("b", {}).get("clean")} == {"G3", "AKU1"})
    coils = [rc for l in (cp or {}).get("loads", []) for rc in (l.get("relay_coils") or [])]
    check("K1: cewka K1 w relay_coils", any(rc["clean"] == "K1" for rc in coils))
    check("K1: SIMA bez tłumienia",
          all(not rc.get("suppression") for rc in coils if rc["clean"] == "K1"))

    # F9 / F11 — bezpieczniki: dwie strony, tor główny
    cp = trace(PS1, "F9")
    pins = [p["pin"] for l in cp["loads"] for p in l["pins"]]
    check("F9: dwie strony (piny 1 i 2)", {"1", "2"} <= set(pins), str(pins))
    check("F9: main_path istnieje", bool((cp.get("main_path") or {}).get("hops")))
    cp = trace(PS1, "F11")
    check("F11: AKU1 w torze głównym",
          "AKU1" in {(cp.get("main_path") or {}).get("a", {}).get("clean"),
                     (cp.get("main_path") or {}).get("b", {}).get("clean")})

    # X164 — odbiornik +→−: przeskok 'device', bateria + → masa
    cp = trace(PS1, "X164")
    mpx = cp.get("main_path") or {}
    check("X164: kind=power (+→−)", mpx.get("kind") == "power", str(mpx.get("kind")))
    check("X164: hop 'device' przez odbiornik",
          any(h.get("internal") == "device" for h in mpx.get("hops", [])))
    check("X164: koniec A to bateria +, B to masa",
          mpx.get("end_a", {}).get("batt") == "+"
          and (mpx.get("end_b", {}).get("role") == "gnd" or mpx.get("end_b", {}).get("batt") == "-"))
    check("X164: klasy ground i feed obecne",
          {"ground", "feed"} <= {e.get("cls") for e in ends_of(cp)})

    # X303 — złącze cewki: tor sygnałowy bez wyjątku
    cp = trace(PS1, "X303")
    check("X303: main_path (sygnał) bez wyjątku", bool((cp.get("main_path") or {}).get("hops")))
    check("X303: kind to signal", (cp.get("main_path") or {}).get("kind") == "signal")

    # emergency start
    cp = trace(PS1, "emergency start")
    check("emergency start: AKU1 w torze",
          "AKU1" in {(cp.get("main_path") or {}).get("a", {}).get("clean"),
                     (cp.get("main_path") or {}).get("b", {}).get("clean")})

    # relay socket — tory sygnałowe nie udają zasilania
    cp = trace(PS1, "X132")
    check("X132: tylko kandydaci sygnałowi",
          all(c["kind"] == "signal" for c in (cp.get("main_candidates") or [])))

probe2 = trace(PS2, "F27")
if not (probe2 and probe2.get("ok") and probe2.get("loads")):
    skip("dane PS012732", "brak projektu w bazie")
else:
    pins = [p for l in probe2["loads"] for p in l["pins"]]
    check("F27 (Walia): dwie strony z końcami",
          {p["pin"] for p in pins} >= {"1", "2"} and all(p["ends"] for p in pins))
    cp = trace(PS2, "K4")
    coils = [rc for l in (cp or {}).get("loads", []) for rc in (l.get("relay_coils") or [])]
    check("K4 (Walia): dioda z BOM",
          any(rc["clean"] == "K4" and rc.get("suppression") == "diode" for rc in coils))

print("\nALL OK" if ok else "\nFAILED")
sys.exit(0 if ok else 1)
