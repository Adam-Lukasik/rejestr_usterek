"""Sklada paczki serwerowe Docker w build/server/.

1. rejestr_usterek_serwer/            - pelny folder startowy (bez data/ - dane dokłada build_server_usb.py / reczne kopiowanie)
2. rejestr_usterek_serwer_update_v<VERSION>.zip - platny ZIP z samym kodem (do wgrania w aplikacji:
   Kopie & Eksport -> "Wgraj aktualizacje serwera"). Bez data/, bez plikow Dockera.

Uzycie:  python tools/build_server_pack.py
"""
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = re.search(r'VERSION\s*=\s*"([^"]+)"', (ROOT / "app.py").read_text("utf-8")).group(1)

OUT = ROOT / "build" / "server"
PACK = OUT / "rejestr_usterek_serwer"

CODE_FILES = [
    "app.py", "zuken_service.py", "backup_service.py", "server_main.py",
    "rejestr_usterek.html", "translations.js",
]
DOCKER_FILES = [
    "Dockerfile", "docker-compose.yml", "requirements-server.txt",
    "config.docker.json", "INSTRUKCJA_DLA_IT.txt", ".dockerignore",
]


def main():
    if PACK.exists():
        shutil.rmtree(PACK)
    (PACK / "migrations").mkdir(parents=True)
    (PACK / "data").mkdir()

    for name in CODE_FILES:
        shutil.copy2(ROOT / name, PACK / name)
    for name in DOCKER_FILES:
        shutil.copy2(ROOT / "docker" / name, PACK / name)
    for mig in sorted((ROOT / "migrations").glob("*.sql")):
        shutil.copy2(mig, PACK / "migrations" / mig.name)

    upd = OUT / f"rejestr_usterek_serwer_update_v{VERSION}.zip"
    upd.unlink(missing_ok=True)
    with zipfile.ZipFile(upd, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in CODE_FILES:
            zf.write(ROOT / name, name)
        for mig in sorted((ROOT / "migrations").glob("*.sql")):
            zf.write(mig, f"migrations/{mig.name}")

    print(f"Folder: {PACK}")
    print(f"ZIP aktualizacji: {upd} ({upd.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
