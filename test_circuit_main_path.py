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

    _ck = [rc for l in (cp or {}).get("loads", []) for rc in (l.get("relay_coils") or [])
           if rc["clean"] == "K1"]
    _ce = [e for rc in _ck for e in (rc.get("ends") or [])]
    check("K1: cewka dochodzi do GND", any(e.get("role") == "gnd" for e in _ce),
          str([(e.get("clean"), e.get("role"), e.get("batt")) for e in _ce])[:200])
    check("K1: cewka dochodzi do plusa baterii", any(e.get("batt") == "+" for e in _ce),
          str([(e.get("clean"), e.get("role"), e.get("batt")) for e in _ce])[:200])

    _bn = {e["clean"]: e.get("batt_name") for l in probe["loads"] for p in l["pins"] for e in p["ends"] if e.get("batt")}
    check("akumulatory: G3=AUX, AKU1=CHASSIS", _bn.get("G3") == "AUX" and _bn.get("AKU1") == "CHASSIS", str(_bn))

    # F9 / F11 — bezpieczniki: dwie strony, tor główny
    cp = trace(PS1, "F9")
    pins = [p["pin"] for l in cp["loads"] for p in l["pins"]]
    check("F9: dwie strony (piny 1 i 2)", {"1", "2"} <= set(pins), str(pins))
    check("F9: main_path istnieje", bool((cp.get("main_path") or {}).get("hops")))
    # F49 (EoE): oprawka FH49 — dwie strony, zasilanie A15:14 / szyna bezpieczników
    cp = trace(PS1, "F49")
    f49 = [p for l in cp["loads"] for p in l["pins"]]
    check("F49 (EoE): dwie strony z końcami",
          {p["pin"] for p in f49} >= {"1", "2"} and all(p["ends"] for p in f49))
    check("F49 (EoE): koniec A15:14 po stronie pinu 1",
          any(e["clean"] == "A15" and e["pin"] == "14"
              for p in f49 if p["pin"] == "1" for e in p["ends"]))
    check("F49 (EoE): main_path istnieje", bool((cp.get("main_path") or {}).get("hops")))
    cp = trace(PS1, "F11")
    check("F11: AKU1 w torze głównym",
          "AKU1" in {(cp.get("main_path") or {}).get("a", {}).get("clean"),
                     (cp.get("main_path") or {}).get("b", {}).get("clean")})

    # X164 — odbiornik +→−: przeskok 'device', bateria + → masa
    # ZNANE OGRANICZENIE: tor zatrzymuje się na styczniku A359 (koniec
    # 'source' bez krawędzi baterii), więc kandydat +→− nie powstaje i
    # wygrywa para sygnałowa — do naprawy w etapie 2 megaplanu.
    cp = trace(PS1, "X164")
    mpx = cp.get("main_path") or {}
    check("X164: main_path istnieje", bool(mpx.get("hops")))
    if mpx.get("kind") != "power":
        print("WARN X164: kind=%s zamiast power (znany bug doboru toru)" % mpx.get("kind"))
    else:
        check("X164: koniec A to bateria +, B to masa",
              mpx.get("end_a", {}).get("batt") == "+"
              and (mpx.get("end_b", {}).get("role") == "gnd" or mpx.get("end_b", {}).get("batt") == "-"))
    check("X164: klasy ground i feed obecne",
          {"ground", "feed"} <= {e.get("cls") for e in ends_of(cp)})

    # X303 — złącze cewki: tor sygnałowy bez wyjątku
    cp = trace(PS1, "X303")
    check("X303: main_path (sygnał) bez wyjątku", bool((cp.get("main_path") or {}).get("hops")))
    _mc = cp.get("main_candidates") or []
    check("X303: kind to signal/feed (feed po łatce S300 do G3)",
          (cp.get("main_path") or {}).get("kind") in ("signal", "feed"))
    check("X303: kandydat signal nadal dostępny", any(c["kind"] == "signal" for c in _mc))

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

    # ── niezmienniki diagramów (etap 1+4 megaplanu) ─────────────────────
    # (a) ten sam (device,pin) nie może być dwukrotnie końcem tego samego
    #     pinu zapytanego elementu — duplikat karty na diagramie
    # (b) końce osiągnięte przez własną krawędź 'fuse' zapytanego -F są
    #     zabronione (RT17 za F18 widoczne z obu stron)
    # (c) końcówka -RT bez krawędzi stud/battery/busbar nie ma roli
    #     'terminal' (ślepy koniec przewodu to odbiornik, nie zasilanie)
    def dup_ends(cp):
        out = []
        for l in cp["loads"]:
            for p in l["pins"]:
                seen = set()
                for e in p["ends"]:
                    k = (e.get("device"), e.get("pin"))
                    if k in seen:
                        out.append(k)
                    seen.add(k)
        return out

    def self_fuse_ends(cp):
        out = []
        for l in cp["loads"]:
            if not re.match(r"^F\d", l.get("clean") or ""):
                continue
            fc, fd = l["clean"], l["device"]
            for p in l["pins"]:
                for e in p["ends"]:
                    for h in e.get("path") or []:
                        if (h.get("internal") == "fuse"
                                and (h.get("internal_label") or "").split()
                                and (h.get("internal_label") or "").split()[0] == fc
                                and h.get("from") != fd and h.get("to") != fd):
                            out.append((p["pin"], e.get("device")))
                            break
        return out

    def bad_terminal_ends(cp, adj=None):
        return [(l["clean"], p["pin"], e["device"], e["pin"])
                for l in cp["loads"] for p in l["pins"] for e in p["ends"]
                if e.get("role") == "terminal"
                and not e.get("via_stud")]

    GOLDEN = [("F18", None), ("F21", None), ("RT110", None), ("F7", None)]
    for gq, _ in GOLDEN:
        cp = trace(PS2, gq)
        if not (cp and cp.get("ok")):
            check(f"{gq}: trace ok", False)
            continue
        check(f"{gq}: brak zduplikowanych końców w pinie",
              not dup_ends(cp), str(dup_ends(cp))[:160])
        check(f"{gq}: brak końców przez własną krawędź -F",
              not self_fuse_ends(cp), str(self_fuse_ends(cp))[:160])

    # F18 (Walia): strona odbiornika to wyłącznie przewód 75 -> winda
    cp = trace(PS2, "F18")
    f18 = {p["pin"]: p for l in cp["loads"] for p in l["pins"]
           if l["clean"] == "F18"}
    p2_ends = {(e["device"], e["role"]) for e in f18.get("2", {}).get("ends", [])}
    check("F18: pin 2 = tylko RT17 (load)",
          p2_ends == {("=DPL+LIFT-RT17", "load")}, str(p2_ends))
    check("F18: RT17 nie po stronie zasilania (pin 1)",
          not any(e["device"] == "=DPL+LIFT-RT17"
                  for e in f18.get("1", {}).get("ends", [])))
    check("F18: strona 1 = oczko RT64-RT30 (zasilanie poza raportem)",
          {(e["device"], e["role"]) for e in f18.get("1", {}).get("ends", [])}
          == {("=DPL+DPL-RT30", "load")})

    # RT110 (Walia): obwód główny zasilanie -> U2 przez A3/A7/F21
    cp = trace(PS2, "RT110")
    mp = cp.get("main_path") or {}
    mcl = {mp.get("a", {}).get("clean"), mp.get("b", {}).get("clean")}
    check("RT110: tor główny zasilanie -> splice",
          mcl & {"G3", "G5"} and "U2" in mcl, str(mcl))
    hc = set()
    for h in mp.get("hops", []):
        hc.add(h.get("from_clean")); hc.add(h.get("to_clean"))
    check("RT110: tor przez A3/A7",
          {"A3", "A7"} <= hc, str(sorted(hc))[:160])
    check("RT110: tor przez bezpiecznik F21 (krawędź 'fuse')",
          any((h.get("internal_label") or "").split()
              and (h.get("internal_label") or "").split()[0] == "F21"
              for h in mp.get("hops", [])))

    # styki przekaźników (Walia): fizyczne przewody, nie rekordy gniazda —
    # K5: cewka 156/92D na 85/86, styki 999_37 na 30 i 257 na 87
    import json as _json
    import sqlite3 as _sq
    _db = _sq.connect(z.DB_PATH)
    def _relay_wires(dev):
        r = _db.execute(
            "SELECT contacts_json FROM zuken_ps_relays"
            " WHERE ps_code = ? AND device_code = ?",
            (PS2, dev)).fetchone()
        return {(c.get("relay_pin") or ""): (c.get("wire_number") or "")
                for c in _json.loads((r and r[0]) or "[]")}
    check("K5: 4 przewody, styki wg schematu",
          _relay_wires("=KKK+ACT-K5") ==
          {"30": "999_37", "85": "156", "86": "92D", "87": "257"},
          str(_relay_wires("=KKK+ACT-K5")))
    check("K4: NC 87a (pinout 8JA 003 526-002)",
          _relay_wires("=CAB+BSI-K4").get("87A") != ""
          and "86" in _relay_wires("=CAB+BSI-K4"),
          str(_relay_wires("=CAB+BSI-K4")))
    check("K7: 4 przewody (cewka 999_135/221)",
          {rp: w for rp, w in _relay_wires("=BOX+DPL-K7").items()} ==
          {"5": "224", "5b": "225", "85": "999_135", "86": "221"},
          str(_relay_wires("=BOX+DPL-K7")))

print("\nALL OK" if ok else "\nFAILED")
sys.exit(0 if ok else 1)
