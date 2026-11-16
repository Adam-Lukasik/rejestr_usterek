"""Walidator niezmienników odpowiedzi trace_circuit (etap 2 megaplanu).

Dla zadanego zestawu zapytań uruchamia trace_circuit i sprawdza twarde
niezmienniki topologii odpowiedzi:

  DUP-END       ten sam (device,pin) jest 2x końcem w jednej grupie pinu
  X-PIN         ten sam (device,pin) jest końcem w DWÓCH pinach tego
                samego odbiornika (bug F18/RT17 — koniec widoczny z obu
                stron elementu); WARN dla nie--F (szyna może być legalna)
  CYCLE         węzeł (dev,pin) powtarza się na ścieżce końca
  EDGE-KIND     krawędź ścieżki z nieznanym typem syntetycznym
  EDGE-DATA     krawędź niesyntetyczna bez danych przewodu (ani sygnał,
                ani nr przewodu) — podejrzenie toru "z powietrza"
  BLIND-TERM    koniec roli 'terminal' bez via_stud/batt — ślepa końcówka
                -RT powinna być 'load', nie 'terminal' (post-pass w
                trace_circuit miał to wyłapać)
  FEED-NOANCHOR pin roli 'feed' bez końca do bieguna/stud/source/
                terminal/fuse/relay — "zasilanie" z niczego
  SELF-FUSE     koniec osiągnięty przez WŁASNĄ krawędź 'fuse' zapytanego
                elementu -F (końce strony B widoczne po stronie A)

Użycie:
  python test_circuit_invariants.py                 # złote listy zapytań
  python test_circuit_invariants.py --sample 20     # + top-N urządzeń wg
                                                    #   stopnia z raportu
  python test_circuit_invariants.py PS012732 F18    # tylko wskazane
  python test_circuit_invariants.py --strict        # exit 1 przy ERROR
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import zuken_service as z  # noqa: E402

KNOWN_INTERNAL = {"", "fuse", "relay", "mate", "busbar", "stud",
                  "battery", "switch", "device", "block", "stub"}

# reprezentatywne zapytania per projekt (złote + typowe konstrukcje)
GOLDEN = {
    "PS012732": ["RT110", "F18", "F21", "F7", "F20", "F27", "K1", "K2",
                 "K6", "K7", "K4", "X303", "A3", "U2", "X187", "RT64"],
    "PS011871": ["394", "K1", "F9", "F11", "F49", "X164", "X132", "X303",
                 "emergency start", "F10", "F41", "A15", "U2", "RT21"],
    "PS012055": ["F18", "F1", "F5", "F6", "F7", "F8", "F10", "RT25",
                 "RT26", "RT29", "X25", "K1"],
}


def _top_devices(ps, n):
    """Top-N urządzeń projektu wg liczby połączeń w raporcie."""
    try:
        conn = z.get_db()
        cur = conn.cursor()
        conn_ids, _ = z._ps_project_ids(cur, ps)
        if not conn_ids:
            return []
        ph = ",".join("?" * len(conn_ids))
        rows = cur.execute(f"""
            SELECT dev, COUNT(*) c FROM (
                SELECT from_device dev FROM zuken_connections
                WHERE project_id IN ({ph})
                UNION ALL
                SELECT to_device FROM zuken_connections
                WHERE project_id IN ({ph}))
            GROUP BY dev ORDER BY c DESC LIMIT ?""",
            (*conn_ids, *conn_ids, n * 3)).fetchall()
        out, seen = [], set()
        for r in rows:
            c = z.clean_device_code(r["dev"]) or r["dev"]
            if c and c not in seen:
                seen.add(c)
                out.append(c)
            if len(out) >= n:
                break
        conn.close()
        return out
    except Exception as e:
        print("   (sample error:", e, ")")
        return []


_ADJ_CACHE = {}
_RAW_ADJ_CACHE = {}


def _raw_adjacency(ps):
    """Surowy graf z raportu połączeń (bez krawędzi syntetycznych)."""
    if ps in _RAW_ADJ_CACHE:
        return _RAW_ADJ_CACHE[ps]
    adj = {}
    try:
        conn = z.get_db()
        cur = conn.cursor()
        conn_ids, _ = z._ps_project_ids(cur, ps)
        adj = z._wire_adjacency(cur, conn_ids) or {}
        conn.close()
    except Exception as e:
        print("   (raw adj error:", e, ")")
    _RAW_ADJ_CACHE[ps] = adj
    return adj


def _ext_adjacency(ps):
    """Rozszerzony graf projektu (jak w trace_circuit) — cache per PS."""
    if ps in _ADJ_CACHE:
        return _ADJ_CACHE[ps]
    adj = None
    try:
        conn = z.get_db()
        cur = conn.cursor()
        conn_ids, bom_ids = z._ps_project_ids(cur, ps)
        adj = z._wire_adjacency(cur, conn_ids)
        if adj:
            dev_funcs = z._device_function_map(cur, bom_ids)
            bom_names = z._device_bom_name_map(cur, bom_ids)
            adj, _, _ = z._circuit_extend_adjacency(
                cur, adj, ps, dev_funcs, bom_names)
        conn.close()
    except Exception as e:
        print("   (adj error:", e, ")")
    _ADJ_CACHE[ps] = adj or {}
    return _ADJ_CACHE[ps]


def _edge_in_report(radj, fr, to):
    """Krawędź w surowym grafie raportu. Sloty -U mają w raporcie pin ''
    (E3 scala zaciski w jeden węzeł), a tor pokazuje kołki '1'/'2'
    (u_split) — więc na każdym końcu próbujemy też pin ''."""
    (fd, fp), (td, tp) = fr, to
    for fp2 in {fp, ""}:
        for tp2 in {tp, ""}:
            if (td, tp2) in (radj.get((fd, fp2)) or {}):
                return True
    return False


def _node_has_anchor(adj, dev, pin):
    """Czy węzeł końca ma krawędź stud/battery/busbar — wtedy 'terminal'
    to realny zacisk aparatu, nie ślepa końcówka."""
    return any(isinstance(rr, dict)
               and rr.get("_internal") in ("stud", "battery", "busbar")
               for rr in (adj.get((dev, pin)) or {}).values())


def validate(ps, q, cp):
    """Zwraca listę naruszeń (severity, kod, opis)."""
    v = []

    def add(sev, code, msg):
        v.append((sev, code, msg))

    for l in cp.get("loads") or []:
        lclean = l.get("clean") or ""
        end_pins = {}  # (device,pin) -> [pin grupy]
        for p in l.get("pins") or []:
            seen = set()
            for e in p.get("ends") or []:
                k = (e.get("device"), e.get("pin"))
                if k in seen:
                    add("ERROR", "DUP-END",
                        f"{lclean}:{p['pin']} koniec {e.get('device')}:{e.get('pin')} x2")
                seen.add(k)
                for other in end_pins.get(k, []):
                    if e.get("device") == l.get("device"):
                        continue  # koniec na własnym pinie modułu
                    # dla nie--F: złącza-magistrale (łańcuch pinów w
                    # raporcie jak X353') legalnie współdzielą końce —
                    # INFO, nie WARN
                    sev = "ERROR" if re.match(r"^F\d", lclean) else "INFO"
                    add(sev, "X-PIN",
                        f"{lclean}: koniec {e.get('device')}:{e.get('pin')} "
                        f"w pinach {sorted(set(other.split(',') + [str(p['pin'])]))}")
                end_pins.setdefault(k, []).append(str(p["pin"]))
                # CYCLE + EDGE na ścieżce końca
                path = e.get("path") or []
                nodes = []
                for h in path:
                    fp = (h.get("from"), h.get("from_pin"))
                    tp = (h.get("to"), h.get("to_pin"))
                    if not nodes or nodes[-1] != fp:
                        if fp[0]:
                            nodes.append(fp)
                    if tp[0]:
                        nodes.append(tp)
                    kind = h.get("internal") or ""
                    if kind not in KNOWN_INTERNAL:
                        add("ERROR", "EDGE-KIND",
                            f"{lclean}:{p['pin']} -> {e.get('clean')}:{e.get('pin')} "
                            f"internal={kind!r} na {h.get('from_clean')}"
                            f"->{h.get('to_clean')}")
                    elif not kind:
                        # krawędź raportowa musi istnieć w surowym grafie
                        fr = (h.get("from"), h.get("from_pin"))
                        to = (h.get("to"), h.get("to_pin"))
                        if not _edge_in_report(_raw_adjacency(ps), fr, to):
                            add("ERROR", "EDGE-UNSUPPORTED",
                                f"{lclean}:{p['pin']} -> {e.get('clean')}:"
                                f"{e.get('pin')} krawędź spoza raportu "
                                f"{h.get('from_clean')}:{h.get('from_pin')}"
                                f"->{h.get('to_clean')}:{h.get('to_pin')}")
                if len(nodes) != len(set(nodes)):
                    dup = [n for n in set(nodes) if nodes.count(n) > 1]
                    add("ERROR", "CYCLE",
                        f"{lclean}:{p['pin']} -> {e.get('clean')}:{e.get('pin')} "
                        f"cykl przez {dup[:3]}")
                # BLIND-TERM
                if (e.get("role") == "terminal" and not e.get("via_stud")
                        and not e.get("batt")
                        and not _node_has_anchor(_ext_adjacency(ps),
                                                 e.get("device") or "",
                                                 e.get("pin") or "")):
                    add("ERROR", "BLIND-TERM",
                        f"{lclean}:{p['pin']} -> {e.get('device')}:{e.get('pin')} "
                        f"terminal bez stud/batt")
            # SELF-FUSE dla odbiorników -F
            if re.match(r"^F\d", lclean):
                fd = l.get("device") or ""
                for e in p.get("ends") or []:
                    for h in e.get("path") or []:
                        if (h.get("internal") == "fuse"
                                and (h.get("internal_label") or "").split()
                                and (h.get("internal_label") or "").split()[0] == lclean
                                and h.get("from") != fd and h.get("to") != fd):
                            add("ERROR", "SELF-FUSE",
                                f"{lclean}:{p['pin']} -> {e.get('clean')}:{e.get('pin')}"
                                f" przez własną krawędź")
                            break
            # FEED-NOANCHOR
            if p.get("role") == "feed":
                anchors = [e for e in p.get("ends") or []
                           if e.get("batt") or e.get("via_stud")
                           or e.get("role") in ("source", "terminal", "fuse",
                                                "relay", "gnd")]
                if not anchors:
                    add("WARN", "FEED-NOANCHOR",
                        f"{lclean}:{p['pin']} feed bez kotwicy "
                        f"({len(p.get('ends') or [])} końców)")

    # to samo dla końców obwodów cewek
    for l in cp.get("loads") or []:
        for rc in l.get("relay_coils") or []:
            rcl = rc.get("clean") or "?"
            seen = {}
            for e in rc.get("ends") or []:
                k = (e.get("device"), e.get("pin"))
                cpin = e.get("coil_pin") or "?"
                if k in seen and seen[k] == cpin:
                    add("ERROR", "DUP-END",
                        f"cewka {rcl}:{cpin} koniec {e.get('device')}:"
                        f"{e.get('pin')} x2")
                seen[k] = cpin
                nodes = []
                for h in e.get("path") or []:
                    fp = (h.get("from"), h.get("from_pin"))
                    tp = (h.get("to"), h.get("to_pin"))
                    if not nodes or nodes[-1] != fp:
                        if fp[0]:
                            nodes.append(fp)
                    if tp[0]:
                        nodes.append(tp)
                    kind = h.get("internal") or ""
                    if kind not in KNOWN_INTERNAL:
                        add("ERROR", "EDGE-KIND",
                            f"cewka {rcl}:{cpin} -> {e.get('clean')}:{e.get('pin')} "
                            f"internal={kind!r}")
                if len(nodes) != len(set(nodes)):
                    add("ERROR", "CYCLE",
                        f"cewka {rcl}:{cpin} -> {e.get('clean')}:{e.get('pin')} cykl")
    return v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    sample = 0
    for a in sys.argv[1:]:
        if a.startswith("--sample"):
            sample = int(a.split("=")[-1] if "=" in a else 20)

    if args:
        queries = {args[0]: args[1:]} if len(args) > 1 else {
            ps: qs for ps, qs in GOLDEN.items() if ps == args[0]}
    else:
        queries = dict(GOLDEN)
    if sample:
        for ps in queries or GOLDEN:
            extra = [d for d in _top_devices(ps, sample)
                     if d not in queries.get(ps, [])]
            queries.setdefault(ps, []).extend(extra[:sample])

    n_err = n_warn = n_traced = n_skip = 0
    for ps, qs in queries.items():
        print(f"\n== {ps} ({len(qs)} zapytań)")
        for q in qs:
            try:
                cp = z.trace_circuit(ps, q)
            except Exception as e:
                print(f"   {q:18s} TRACE-ERROR {e}")
                n_err += 1
                continue
            if not (cp and cp.get("ok") and cp.get("loads")):
                print(f"   {q:18s} SKIP (brak toru)")
                n_skip += 1
                continue
            n_traced += 1
            viol = validate(ps, q, cp)
            if not viol:
                print(f"   {q:18s} ok")
                continue
            infos = sum(1 for s, _, _ in viol if s == "INFO")
            printed = 0
            for sev, code, msg in viol:
                if sev == "INFO":
                    continue  # agregowane niżej
                print(f"   {q:18s} {sev:5s} {code:14s} {msg}")
                printed += 1
                if sev == "ERROR":
                    n_err += 1
                else:
                    n_warn += 1
            if infos:
                print(f"   {q:18s} INFO  X-PIN          {infos}x współdzielony"
                      f" koniec (złącze-magistrala/moduł)")

    print(f"\n== PODSUMOWANIE: {n_traced} torów, {n_skip} pominiętych, "
          f"{n_err} ERROR, {n_warn} WARN")
    sys.exit(1 if (strict and n_err) else 0)


if __name__ == "__main__":
    main()
