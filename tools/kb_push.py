#!/usr/bin/env python3
# tools/kb_push.py — wysyła deltę Bazy wiedzy na udział aktualizacji
"""
Skanuje lokalny katalog „Baza wiedzy", liczy manifest (rel_path -> size+sha256,
z cache po size+mtime) i kopiuje tylko nowe/zmienione pliki do <dest>\\kb\\.
Na <dest> zapisuje kb_manifest.json — klienci (/api/kb-sync) dociągają z niego deltę.

Użycie:  python tools/kb_push.py --dest "\\\\NAS\\RejestrUsterek"
         (--dest = katalog nadrzędny updates\\, tam powstaje kb\\ i kb_manifest.json)

Pliki usunięte lokalnie trafiają na listę „removed" w manifeście — klienci
przenoszą je do data\\.kb_removed\\ (zamiast kasować).
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime as _dt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, "Baza wiedzy")
CACHE_PATH = os.path.join(BASE_DIR, "tools", ".kb_cache.json")
CHUNK = 1 << 20


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_kb():
    """Zwraca {rel_path: {size, mtime}} dla wszystkich plików Bazy wiedzy."""
    out = {}
    for root, _dirs, files in os.walk(KB_DIR):
        for fn in files:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, KB_DIR).replace("\\", "/")
            try:
                st = os.stat(fp)
                out[rel] = {"size": st.st_size, "mtime": st.st_mtime}
            except OSError:
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True,
                    help="katalog główny udziału (np. \\\\NAS\\RejestrUsterek)")
    args = ap.parse_args()

    if not os.path.isdir(KB_DIR):
        sys.exit(f"[KB] Brak katalogu {KB_DIR}")
    kb_dest = os.path.join(args.dest, "kb")
    manifest_path = os.path.join(args.dest, "kb_manifest.json")
    os.makedirs(kb_dest, exist_ok=True)

    try:
        cache = json.load(open(CACHE_PATH, "r", encoding="utf-8"))
    except Exception:
        cache = {}

    try:
        old_manifest = json.load(open(manifest_path, "r", encoding="utf-8"))
    except Exception:
        old_manifest = {"files": {}}

    files = scan_kb()
    print(f"[KB] Plików lokalnie: {len(files)}")

    manifest_files = {}
    copied = skipped = 0
    for rel, meta in sorted(files.items()):
        src = os.path.join(KB_DIR, rel.replace("/", os.sep))
        c = cache.get(rel)
        if c and c.get("size") == meta["size"] and c.get("mtime") == meta["mtime"]:
            digest = c["sha256"]
        else:
            digest = sha256(src)
            cache[rel] = {"size": meta["size"], "mtime": meta["mtime"], "sha256": digest}
        manifest_files[rel] = {"size": meta["size"], "sha256": digest}

        dst = os.path.join(kb_dest, rel.replace("/", os.sep))
        om = old_manifest.get("files", {}).get(rel)
        if om and om.get("sha256") == digest and os.path.exists(dst):
            skipped += 1
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        print(f"[KB] -> {rel}")
        shutil.copy2(src, dst)
        copied += 1

    removed = sorted(set(old_manifest.get("files", {})) - set(files))

    manifest = {
        "generated": _dt.now().isoformat(timespec="seconds"),
        "files": manifest_files,
        "removed": removed,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)

    # Sprzątanie usuniętych plików na udziale
    for rel in removed:
        p = os.path.join(kb_dest, rel.replace("/", os.sep))
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    print(f"[KB] Skopiowano: {copied}, bez zmian: {skipped}, usunięte: {len(removed)}")
    print(f"[KB] Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
