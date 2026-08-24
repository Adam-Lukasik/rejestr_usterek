import json
import requests
import sys

SERVER = "http://127.0.0.1:5050"


def import_file(path, mode="merge", server=None):
    srv = server or SERVER
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("records"), list) or not isinstance(data.get("lists"), dict):
        print("Błąd: plik nie ma oczekiwanej struktury kopii zapasowej.")
        return False
    r = requests.post(f"{srv.rstrip('/')}/api/import?mode={mode}", json=data)
    if r.ok:
        print(f"OK: {r.json()}")
        return True
    print(f"Błąd: {r.status_code} {r.text}")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python importuj_kopie.py <plik.json> [merge|replace] [url_serwera]")
        sys.exit(1)
    mode = sys.argv[2] if len(sys.argv) > 2 else "merge"
    srv = sys.argv[3] if len(sys.argv) > 3 else SERVER
    import_file(sys.argv[1], mode, srv)
