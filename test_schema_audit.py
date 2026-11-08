"""Test modułu Kontrola schematów (schema_audit) — łatki, adjacency, eml/xlsx, observe.
Temp-DB jak test_zuken_terms.py."""
import os, sys, tempfile, sqlite3
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import zuken_service as zs
import schema_audit as sa

tmp = tempfile.mkdtemp()
zs.DB_PATH = os.path.join(tmp, "t.db")
zs.init_zuken_tables()
sa.init_audit_tables()

ok = True
def check(name, cond, extra=""):
    global ok
    print(("PASS" if cond else "FAIL"), name, extra)
    if not cond: ok = False

conn = zs.get_db()
cur = conn.cursor()
cur.execute("INSERT INTO zuken_projects (filename, project_name, ps_codes, imported_at, is_active) "
            "VALUES ('rep.xlsx', 'Test PS', 'PS9', '2026-01-01', 1)")
PID = cur.lastrowid
for i, (fd, fp, td, tp) in enumerate([
        ("=BOX+TWR-RT88", "1", "=CAB+TWR-X10", "1"),
        ("=BOX+TWR-RT167", "1", "=CAB+MOR-U1", "1"),
        ("=BOX+TWR-RT124", "2", "=CAB+TWR-X98", "1"),
        ("=BOX+TWR-A359", "B", "=CAB+TWR-X99", "1")]):
    cur.execute("""INSERT INTO zuken_connections (project_id, signal, from_device, from_pin,
                   to_device, to_pin, wire_number) VALUES (?,?,?,?,?,?,?)""",
                (PID, f"S{i}", fd, fp, td, tp, f"w{i}"))
conn.commit()

# ── walidacja łatek ──
def expect_err(fn):
    try:
        fn()
        return False
    except ValueError:
        return True

check("connection ok", bool(sa.save_patch("PS9", "connection",
      {"from_device": "=BOX+TWR-RT124", "from_pin": "1",
       "to_device": "=BOX+TWR-A359", "to_pin": "A"})))
check("connection wymagane", expect_err(lambda: sa.save_patch("PS9", "connection", {"from_device": "X"})))
check("fuse_holder ok", bool(sa.save_patch("PS9", "fuse_holder", {"fuse": "F19", "holder": "=CAB+TWR-FH15"})))
check("fuse_holder wymagane", expect_err(lambda: sa.save_patch("PS9", "fuse_holder", {"fuse": "F19"})))
BB = sa.save_patch("PS9", "busbar", {"members": [["F9", "1", "=BOX+TWR-RT167"], {"fuse": "F11", "pin": "1", "term": "=BOX+TWR-RT167"}]})
check("busbar ok (2 człony)", bool(BB))
check("busbar wymaga 2 członów", expect_err(lambda: sa.save_patch("PS9", "busbar", {"members": [["F9", "1"]]})))
BF = sa.save_patch("PS9", "box_fuse", {"box_name": "comms ign", "cell": "a1", "rating": "5A", "out_dev": "=CAB+TWR-X206"})
check("box_fuse ok + normalizacja", bool(BF))
pl = dict(cur.execute("SELECT payload FROM zuken_data_patches WHERE id=?", (BF,)).fetchone())
import json as _j2
check("box_fuse UPPER", _j2.loads(pl["payload"])["cell"] == "A1")
check("box_fuse wymagane", expect_err(lambda: sa.save_patch("PS9", "box_fuse", {"box_name": "X"})))
check("device_location ok", bool(sa.save_patch("PS9", "device_location", {"device": "-A359", "full_code": "=BOX+TWR-A359"})))
check("device_location wymaga =+", expect_err(lambda: sa.save_patch("PS9", "device_location", {"device": "-A359", "full_code": "A359"})))
check("bad kind", expect_err(lambda: sa.save_patch("PS9", "nope", {})))
check("device_link ok", bool(sa.save_patch("PS9", "device_link",
      {"device": "-A359", "pin_a": "A", "pin_b": "B", "label": "ML-RBS"})))
check("device_link wymagane", expect_err(lambda: sa.save_patch("PS9", "device_link", {"device": "-A359", "pin_a": "A"})))
check("device_link pin != pin", expect_err(lambda: sa.save_patch("PS9", "device_link", {"device": "-A359", "pin_a": "A", "pin_b": "A"})))
check("power_rail ok", bool(sa.save_patch("PS9", "power_rail",
      {"members": [{"dev": "=BOX+TWR-RT88", "pin": "1"}, "=BOX+TWR-RT167:1"], "label": "szyna 1"})))
check("power_rail wymaga 2 członów", expect_err(lambda: sa.save_patch("PS9", "power_rail", {"members": [{"dev": "=BOX+TWR-RT88"}]})))

# ── nakładka connection w _wire_adjacency ──
adj_p = zs._wire_adjacency(cur, [PID], with_patches=True)
adj_r = zs._wire_adjacency(cur, [PID], with_patches=False)
A = ("=BOX+TWR-RT124", "1")
check("łatka widoczna z with_patches", ("=BOX+TWR-A359", "A") in adj_p.get(A, {}))
check("łatki nie ma bez patchy", ("=BOX+TWR-A359", "A") not in adj_r.get(A, {}))
row_p = adj_p[A][("=BOX+TWR-A359", "A")]
check("patch_id propagowane", int(row_p["patch_id"] or 0) > 0)

# ── nakładka busbar w _ps_fuse_rails (brak schematu → wczesne wyjście raw) ──
zs._invalidate_patch_caches()
rails = zs._ps_fuse_rails(cur, [PID], "PS9", adj_r)
bars = rails.get("bars") or {}
check("busbar łatka w rails", "F9" in bars and "F11" in bars, list(bars))
bi = (bars.get("F9") or {}).get("=BOX+TWR-RT167") or {}
check("busbar bar_info", bi.get("pin") == "1" and "ZW" in (bi.get("node") or ""), bi)
check("busbar sibs", any("F11" in s[0] for s in bi.get("sibs") or []), bi.get("sibs"))
rails_raw = zs._ps_fuse_rails_raw(cur, [PID], "PS9", adj_r)
check("raw bez łatki", not (rails_raw.get("bars") or {}))

# ── fuse_holder łatka w rails ──
check("fuse_holder łatka", (rails.get("holders") or {}).get("F19") == "=CAB+TWR-FH15")

# ── łatki device_link / power_rail w _circuit_extend_adjacency ──
zs._invalidate_patch_caches()
adj_e, int_devs, _rc = zs._circuit_extend_adjacency(cur, adj_p, "PS9", {}, {})
_eA = adj_e.get(("=BOX+TWR-A359", "A"), {}).get(("=BOX+TWR-A359", "B"))
check("device_link wewnętrzny switch", (_eA or {}).get("_internal") == "switch", _eA)
check("device_link aparat przechodni", "=BOX+TWR-A359" in int_devs)
_eR = adj_e.get(("=BOX+TWR-RT88", "1"), {}).get(("=BOX+TWR-RT167", "1"))
check("power_rail krawędź busbar", (_eR or {}).get("_internal") == "busbar", _eR)
check("power_rail etykieta", (_eR or {}).get("_internal_label") == "szyna 1", _eR)

# ── redundant: połączenie łatki pojawia się w surowym raporcie ──
ctx = sa.Ctx(cur, "PS9")
sa._mark_redundant_patches(cur, "PS9", ctx)
st = cur.execute("SELECT status FROM zuken_data_patches WHERE kind='connection'").fetchone()[0]
check("connection jeszcze active (brak w raporcie)", st == "active", st)
cur.execute("""INSERT INTO zuken_connections (project_id, from_device, from_pin, to_device, to_pin)
               VALUES (?,?,?,?,?)""", (PID, "=BOX+TWR-RT124", "1", "=BOX+TWR-A359", "A"))
conn.commit()
ctx2 = sa.Ctx(cur, "PS9")
sa._mark_redundant_patches(cur, "PS9", ctx2)
st = cur.execute("SELECT status FROM zuken_data_patches WHERE kind='connection'").fetchone()[0]
check("connection redundant po poprawce", st == "redundant", st)

# ── D02: końcówka PE/GND to poprawny punkt masowy — nie zgłaszamy ──
for i, (fd, fp, td, tp, wc, sn) in enumerate([
        ("=P-RT50", "1", "=P-X1", "1", "6.0-GNYE", "PE"),
        ("=P-RT52", "1", "=P-X3", "1", "", "GND Sterling"),
        ("=P-RT51", "1", "=P-X2", "1", "16.0-RD", "BAT+")]):
    cur.execute("""INSERT INTO zuken_connections (project_id, from_device, from_pin,
                   to_device, to_pin, wire_number, wire_color, signal_name)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (PID, fd, fp, td, tp, f"pe{i}", wc, sn))
conn.commit()
_ctx_pe = sa.Ctx(cur, "PS9")
found = sa.det_dangling_terminal(_ctx_pe)
fps = {f["fp"] for f in found}
check("D02 pomija PE (GNYE)", "D02|=P-RT50:1" not in fps, fps)
check("D02 pomija GND (nazwa)", "D02|=P-RT52:1" not in fps, fps)
check("D02 zgłasza zwykły przewód", "D02|=P-RT51:1" in fps, fps)

# ── report_pinout_missing idempotentne ──
conn.commit()
r1 = sa.report_pinout_missing("1-171880-1", "Test plug 3 way", "PS9", "adam")
r2 = sa.report_pinout_missing("1-171880-1", "", "PS9")
check("observe insert", r1["ok"] and not r1["existed"])
check("observe idempotentne", r2["ok"] and r2["existed"] and r2["id"] == r1["id"])
n = cur.execute("SELECT COUNT(*) FROM zuken_issues WHERE fingerprint LIKE 'D14|OBS|%'").fetchone()[0]
check("observe jedno zgłoszenie", n == 1, n)

# ── xlsx + eml ──
xb = sa.xlsx_bytes(["Lp", "ID"], [[1, "A359"], [2, "RT124"]])
xp = os.path.join(tmp, "l.xlsx")
open(xp, "wb").write(xb)
rows = zs.parse_xlsx_fast(xp)
check("xlsx round-trip", "A359" in str(rows) and "Lp" in str(rows))
eml = sa.build_eml("inz@x.pl", "Temat", "treść", "<b>t</b>", [("l.xlsx", xb, "application", "vnd.ms-excel")])
check("eml X-Unsent", b"X-Unsent: 1" in eml)
check("eml załącznik", b"l.xlsx" in eml)
check("eml adresat", b"inz@x.pl" in eml)

# ── cykl życia: upsert fingerprintu nie duplikuje ──
cur.execute("SELECT COUNT(*) FROM zuken_issues WHERE fingerprint LIKE 'D14|OBS|%'")
before = cur.fetchone()[0]
f = {"fp": "D14|OBS|1-171880-1", "category": "pinout_missing", "severity": "warn",
     "msg_key": "pinout_missing", "params": {}, "devices": [], "location": None,
     "evidence": {}, "suggestion": None, "workaround": None}
res = sa._upsert_finding(cur, "PS9", "D14", f, "rev1", sa._now(), sa.Ctx(cur, "PS9"))
conn.commit()
cur.execute("SELECT COUNT(*) FROM zuken_issues WHERE fingerprint LIKE 'D14|OBS|%'")
check("upsert nie duplikuje", cur.fetchone()[0] == before and res == "updated", res)

# ── reset_issues: dev-reset auto-zgłoszeń, ręczne zostają ──
conn.commit()
man = sa.create_manual_issue({"ps_code": "PS9", "category": "manual", "title": "ręczne"}, "adam")
cur.execute("UPDATE zuken_issues SET status='rejected' WHERE detector='D14'")
conn.commit()
n_del = sa.reset_issues("PS9")
conn = zs.get_db(); cur = conn.cursor()
left = cur.execute("SELECT detector IS NULL, COUNT(*) FROM zuken_issues WHERE ps_code='PS9' GROUP BY detector IS NULL").fetchall()
check("reset usuwa auto (też rejected)", n_del == 1 and all(d[0] == 1 for d in left), (n_del, left))
check("reset zostawia ręczne", any(d[1] == 1 and d[0] == 1 for d in left), left)

conn.close()
print("\nALL OK" if ok else "\nSOME FAILURES")
sys.exit(0 if ok else 1)
