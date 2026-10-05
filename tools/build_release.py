#!/usr/bin/env python3
# tools/build_release.py — pipeline budowania paczki release Rejestru Usterek
"""
Kroki:
  1. Weryfikacja: node check_i18n.js, python test_multilang.py (--skip-tests pomija)
  2. Eksport danych systemowych -> migrations/
  3. Minifikacja frontendu -> build/stage/
  4. Kompilacja Nuitka -> build/nuitka/desktop_web.dist (--skip-nuitka pomija)
  5. Złożenie RejestrUsterek/ (app/ + Updater.exe + data/)
  6. ZIP + latest.json -> build/dist/ ; --deploy <udzial> kopiuje na NAS

Użycie:
  venv\\Scripts\\python.exe tools\\build_release.py [--deploy "\\\\NAS\\RejestrUsterek\\updates"] [--notes "opis"]
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime as _dt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE_DIR, "build")
STAGE_DIR = os.path.join(BUILD_DIR, "stage")
NUITKA_OUT = os.path.join(BUILD_DIR, "nuitka")
DIST_NAME = "desktop_web.dist"
RELEASE_DIR = os.path.join(BUILD_DIR, "release", "RejestrUsterek")
DIST_DIR = os.path.join(BUILD_DIR, "dist")
UPDATER_CACHE = os.path.join(BUILD_DIR, "updater")

VENV_PY = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
PYTHON = VENV_PY if os.path.exists(VENV_PY) else sys.executable

APP_FILES = ("rejestr_usterek.html", "translations.js")


def sh(cmd, **kw):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=BASE_DIR, **kw)
    if r.returncode != 0:
        sys.exit(f"[BUILD] Polecenie nie powiodło się (kod {r.returncode})")


def read_version():
    with open(os.path.join(BASE_DIR, "app.py"), "r", encoding="utf-8") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        sys.exit("[BUILD] Nie znaleziono VERSION w app.py")
    return m.group(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_config_template(dst):
    """config.json dla nowej instalacji — bez sekretów, HOST tylko localhost."""
    src = os.path.join(BASE_DIR, "config.json")
    cfg = {}
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["HOST"] = "127.0.0.1"
    smtp = cfg.get("SMTP")
    if isinstance(smtp, dict):
        smtp["PASSWORD"] = ""
        smtp["ENABLED"] = False
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def build_updater():
    """Kompiluje tools/updater.py -> build/updater/Updater.exe (cache)."""
    src = os.path.join(BASE_DIR, "tools", "updater.py")
    if not os.path.exists(src):
        print("[BUILD] Brak tools/updater.py — pomijam Updater.exe")
        return
    exe = os.path.join(UPDATER_CACHE, "Updater.exe")
    src_mtime = os.path.getmtime(src)
    stamp = os.path.join(UPDATER_CACHE, "updater.stamp")
    if os.path.exists(exe) and os.path.exists(stamp):
        try:
            if float(open(stamp).read().strip()) >= src_mtime:
                print("[BUILD] Updater.exe aktualny (cache)")
                return
        except Exception:
            pass
    os.makedirs(UPDATER_CACHE, exist_ok=True)
    sh([PYTHON, "-m", "nuitka", "--onefile", "--mingw64",
        "--assume-yes-for-downloads",
        "--output-filename=Updater.exe",
        "--windows-console-mode=disable",
        f"--output-dir={UPDATER_CACHE}", src])
    if not os.path.exists(exe):
        sys.exit("[BUILD] Kompilacja Updater.exe nie powiodła się")
    with open(stamp, "w") as f:
        f.write(str(src_mtime))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--skip-nuitka", action="store_true",
                    help="pomiń kompilację (użyj istniejącego build/nuitka/*.dist)")
    ap.add_argument("--deploy", metavar="UDZIAL", default=os.environ.get("RU_UPDATE_SHARE"),
                    help="katalog docelowy paczki (np. \\\\NAS\\RejestrUsterek\\updates)")
    ap.add_argument("--notes", default="", help="opis zmian do latest.json")
    ap.add_argument("--console", action="store_true",
                    help="exe z oknem konsoli (debugowanie builda)")
    ap.add_argument("--no-minify", action="store_true",
                    help="pomiń minifikację — do paczki idą oryginalne pliki frontendu")
    args = ap.parse_args()

    version = read_version()
    print(f"[BUILD] Wersja: {version}")

    if not args.skip_tests:
        sh(["node", "check_i18n.js"])
        sh([PYTHON, "test_multilang.py"])

    sh([sys.executable, os.path.join("tools", "export_migrations.py")])
    if args.no_minify:
        os.makedirs(STAGE_DIR, exist_ok=True)
        for f in APP_FILES:
            shutil.copy2(os.path.join(BASE_DIR, f), os.path.join(STAGE_DIR, f))
        print("[BUILD] --no-minify: oryginalne pliki frontendu")
    else:
        sh(["node", os.path.join("tools", "minify.js"), "--out", STAGE_DIR])

    if not args.skip_nuitka:
        nuitka_args = [
            PYTHON, "-m", "nuitka", "--standalone", "--mingw64",
            "--assume-yes-for-downloads",
            "--enable-plugin=tk-inter",
            "--windows-console-mode=disable" if not args.console else "--windows-console-mode=attach",
            f"--output-dir={NUITKA_OUT}",
            "--output-filename=RejestrUsterek.exe",
            f"--product-name=Rejestr Usterek",
            f"--file-version={version}",
            "--include-package=clr_loader",
            "--include-package=pythonnet",
            "--include-package-data=webview",
            "--include-package-data=pypdfium2",
            f"--include-data-files={os.path.join(STAGE_DIR, 'rejestr_usterek.html')}=rejestr_usterek.html",
            f"--include-data-files={os.path.join(STAGE_DIR, 'translations.js')}=translations.js",
            f"--include-data-dir={os.path.join(BASE_DIR, 'migrations')}=migrations",
            f"--include-data-files={os.path.join(BASE_DIR, 'SumatraPDF.exe')}=SumatraPDF.exe",
            os.path.join(BASE_DIR, "desktop_web.py"),
        ]
        sh(nuitka_args)

    dist_src = os.path.join(NUITKA_OUT, DIST_NAME)
    if not os.path.isdir(dist_src):
        sys.exit(f"[BUILD] Brak katalogu {dist_src} — kompilacja się nie powiodła?")

    build_updater()

    # ── Złożenie pakietu ──
    if os.path.isdir(RELEASE_DIR):
        shutil.rmtree(RELEASE_DIR)
    os.makedirs(RELEASE_DIR)
    shutil.copytree(dist_src, os.path.join(RELEASE_DIR, "app"))

    upd_exe = os.path.join(UPDATER_CACHE, "Updater.exe")
    if os.path.exists(upd_exe):
        shutil.copy2(upd_exe, os.path.join(RELEASE_DIR, "Updater.exe"))

    data_dir = os.path.join(RELEASE_DIR, "data")
    for sub in ("", "Baza wiedzy", "backups", "updates"):
        os.makedirs(os.path.join(data_dir, sub), exist_ok=True)
    make_config_template(os.path.join(data_dir, "config.json"))

    # ── ZIP + latest.json ──
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_name = f"rejestr_usterek_v{version}.zip"
    zip_path = os.path.join(DIST_DIR, zip_name)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    print(f"\n[BUILD] Pakowanie {zip_name} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _dirs, files in os.walk(RELEASE_DIR):
            for fn in files:
                fp = os.path.join(root, fn)
                arc = os.path.join("RejestrUsterek", os.path.relpath(fp, RELEASE_DIR))
                z.write(fp, arc)
    digest = sha256(zip_path)
    size = os.path.getsize(zip_path)
    latest = {
        "version": version,
        "file": zip_name,
        "sha256": digest,
        "size": size,
        "released": _dt.now().isoformat(timespec="seconds"),
        "notes": args.notes,
    }
    latest_path = os.path.join(DIST_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2, ensure_ascii=False)
    print(f"[BUILD] {zip_name}: {size / 1e6:.1f} MB, sha256 {digest[:16]}…")
    print(f"[BUILD] {latest_path}")

    if args.deploy:
        os.makedirs(args.deploy, exist_ok=True)
        shutil.copy2(zip_path, os.path.join(args.deploy, zip_name))
        shutil.copy2(latest_path, os.path.join(args.deploy, "latest.json"))
        print(f"[BUILD] Wdrożono na {args.deploy}")

    print("\n[BUILD] GOTOWE.")


if __name__ == "__main__":
    main()
