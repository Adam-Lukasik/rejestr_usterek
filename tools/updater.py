#!/usr/bin/env python3
# tools/updater.py — kompilowany do Updater.exe (Nuitka --onefile)
"""
Podmienia katalog app/ na nową wersję z rozpakowanej paczki — działa PO zakończeniu
procesu głównego (pliki app/ są wtedy zwolnione). Kompilowany, więc nie wymaga
Pythona na maszynie technika.

Użycie:  Updater.exe <pkg_dir> <app_dir> <exe_path> <wait_pid>
  pkg_dir  — katalog z rozpakowaną paczką (zawiera RejestrUsterek\\app\\)
  app_dir  — docelowy <pakiet>\\app
  exe_path — <pakiet>\\app\\RejestrUsterek.exe (do restartu)
  wait_pid — PID procesu głównego, na którego zakończenie czekamy

Status zapisuje w <pakiet>\\data\\updates\\update_status.json — aplikacja odczytuje
go po restarcie (toast „Zaktualizowano" / „Aktualizacja nie powiodła się").
Poprzednia wersja zostaje w app_old/ do następnej aktualizacji (rollback ręczny).
"""
import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime as _dt

_STILL_ACTIVE = 259  # STILL_ACTIVE


def _pid_alive(pid):
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == _STILL_ACTIVE
    except Exception:
        return False


def _write_status(upd_dir, data):
    data["ts"] = _dt.now().isoformat(timespec="seconds")
    try:
        with open(os.path.join(upd_dir, "update_status.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def main():
    args = sys.argv[1:]
    if len(args) < 4:
        return 2
    pkg_dir, app_dir, exe_path, wait_pid = args[0], args[1], args[2], args[3]

    pkg_root = os.path.dirname(os.path.abspath(app_dir))
    upd_dir = os.path.join(pkg_root, "data", "updates")
    os.makedirs(upd_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(upd_dir, "updater.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8")
    logging.info(f"Start Updater: pkg={pkg_dir} app={app_dir}")

    # Czekaj na zakończenie procesu głównego (max 120 s)
    try:
        pid = int(wait_pid)
    except ValueError:
        pid = 0
    waited = 0.0
    while pid and _pid_alive(pid) and waited < 120:
        time.sleep(0.5)
        waited += 0.5
    logging.info(f"Proces {pid} zakończony (czekano {waited:.1f}s)" if pid else "Brak PID — bez czekania")

    src_app = os.path.join(pkg_dir, "RejestrUsterek", "app")
    app_new = app_dir + "_new"
    app_old = app_dir + "_old"

    if not os.path.isdir(src_app):
        logging.error(f"Brak {src_app} w rozpakowanej paczce")
        _write_status(upd_dir, {"ok": False, "error": "paczka bez katalogu app/"})
    else:
        try:
            if os.path.isdir(app_new):
                shutil.rmtree(app_new)
            shutil.copytree(src_app, app_new)
            if os.path.isdir(app_old):
                shutil.rmtree(app_old)
            os.replace(app_dir, app_old)
            os.replace(app_new, app_dir)
            logging.info("Podmieniono katalog app/")
            _write_status(upd_dir, {"ok": True})
        except Exception as e:
            logging.exception("Błąd podmiany app/")
            try:
                if os.path.isdir(app_old) and not os.path.isdir(app_dir):
                    os.replace(app_old, app_dir)
                    logging.info("Przywrócono app_old/")
            except Exception:
                logging.exception("Rollback nie powiódł się")
            _write_status(upd_dir, {"ok": False, "error": str(e)})

    # Restart aplikacji — zawsze (po błędzie wróci poprzednia wersja)
    try:
        subprocess.Popen(
            [exe_path, "--local"],
            cwd=os.path.dirname(exe_path),
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            close_fds=True)
        logging.info("Uruchomiono ponownie aplikację")
    except Exception as e:
        logging.error(f"Nie udało się uruchomić aplikacji: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
