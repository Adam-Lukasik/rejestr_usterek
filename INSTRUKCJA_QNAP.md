# Instrukcja wdrożenia — Rejestr Usterek na QNAP NAS

> **Dla:** Administratora Sieci / Informatyka  
> **Wersja aplikacji:** aktualna (wrzesień 2026)  
> **Czas wdrożenia:** ok. 15–20 minut

---

## Czym jest ta aplikacja?

**Rejestr Usterek** to wewnętrzna aplikacja webowa do zarządzania usterkami pojazdów.
Składa się z:

| Plik | Rola |
|---|---|
| `app.py` | Backend — serwer REST API (Python / Flask) |
| `rejestr_usterek.html` | Frontend — interfejs użytkownika (jedna strona HTML) |
| `rejestr_usterek.db` | Baza danych SQLite (tworzona automatycznie przy 1. starcie) |
| `config.json` | Konfiguracja (port, SMTP, ścieżka bazy) |

Użytkownicy otwierają aplikację **w przeglądarce** — nie jest potrzebna żadna instalacja na ich komputerach.

---

## Wymagania

- QNAP z zainstalowanym **Container Station** (Docker)
- Dostęp SSH lub terminal w Container Station
- Współdzielony folder na NAS dostępny z sieci LAN (np. `\\srv_ost\Pomiary`)

---

## Krok 1 — Przygotowanie folderu na NAS

W zasobie sieciowym utwórz katalog:

```
\\srv_ost\Pomiary\rejestr_usterek\
```

*(lub dowolna inna ścieżka — ważne, żeby była dostępna z sieci LAN)*

Skopiuj do niego **następujące pliki z archiwum ZIP**:

```
app.py
rejestr_usterek.html
requirements.txt
Dockerfile
docker-compose.yml
config.json
rejestr_usterek.db        ← może być pusty — zostanie zainicjowany automatycznie
```

> **Uwaga:** pliki `desktop.py`, `desktop_web.py`, `uruchom_*.bat` służą wyłącznie
> do lokalnego uruchomienia na komputerze Windows — **na serwer nie są potrzebne**.

---

## Krok 2 — Weryfikacja config.json

Sprawdź plik `config.json` w folderze aplikacji. Powinien wyglądać tak:

```json
{
  "DB_PATH": "rejestr_usterek.db",
  "HOST": "0.0.0.0",
  "PORT": 5050,
  "SECRET_BACKUP_DIR": "",
  "SMTP": {
    "ENABLED": false,
    "SERVER": "smtp.twojafirma.pl",
    "PORT": 587,
    "USE_TLS": true,
    "USER": "rejestr-usterek@twojafirma.pl",
    "PASSWORD": "",
    "SENDER_NAME": "Rejestr Usterek — Powiadomienia"
  }
}
```

Kluczowe: `PORT` musi być `5050` — port 5000 jest domyślnie zajęty przez usługi QNAP.  
Konfiguracja SMTP jest opcjonalna i może być włączona później.

---

## Krok 3 — Uruchomienie przez Container Station

### Opcja A — przez GUI (zalecana)

1. Otwórz **Container Station** w panelu QTS
2. Przejdź do **Aplikacje (Applications)** → **Utwórz (Create)**
3. Wskaż folder z plikiem `docker-compose.yml`  
   *(ścieżka systemowa QNAP, np. `/share/Pomiary/rejestr_usterek`)*
4. Nazwa aplikacji: `rejestr-usterek`
5. Kliknij **Utwórz (Create)**

Container Station automatycznie zbuduje obraz i uruchomi kontener.

### Opcja B — przez terminal SSH

```bash
cd /share/Pomiary/rejestr_usterek
docker-compose up -d --build

# Weryfikacja — w logach powinno pojawić się:
# "Serwer Rejestr Usterek uruchomiony na porcie 5050"
docker logs rejestr_usterek_app
```

---

## Krok 4 — Reguła firewalla

Port **5050 TCP** musi być otwarty dla ruchu w sieci LAN.  
Dostęp z internetu **nie jest wymagany ani zalecany**.

---

## Dostęp dla użytkowników

```
http://srv_ost:5050
```

*(lub `http://<IP_SERWERA_QNAP>:5050` jeśli nazwa DNS nie działa)*

Użytkownicy otwierają ten adres w przeglądarce (Chrome, Edge, Firefox).  
**Żadnej instalacji na komputerach użytkowników nie trzeba wykonywać.**

---

## Autostart po restarcie NAS

Kontener startuje automatycznie dzięki `restart: unless-stopped` w `docker-compose.yml`.  
Nie jest wymagana żadna dodatkowa konfiguracja.

---

## Aktualizacje — bez angażowania informatyka

Użytkownicy mogą samodzielnie aktualizować aplikację:

1. Skopiować nowe pliki (`app.py`, `rejestr_usterek.html`) do folderu  
   `\\srv_ost\Pomiary\rejestr_usterek\`
2. W Container Station kliknąć **Restart** przy `rejestr-usterek`

Baza danych (`rejestr_usterek.db`) nigdy nie jest nadpisywana przy aktualizacji.

---

## Kopia zapasowa

Cała baza danych to jeden plik:

```
\\srv_ost\Pomiary\rejestr_usterek\rejestr_usterek.db
```

Wystarczy objąć go standardowym harmonogramem kopii QNAP (Hybrid Backup Sync).

---

## Rozwiązywanie problemów

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| Strona nie odpowiada | Kontener nie działa | `docker ps` → sprawdź status; `docker logs rejestr_usterek_app` |
| Błąd „port zajęty" | Konflikt z inną usługą | Zmień `PORT` w `config.json` na np. `5051`, zrestartuj kontener |
| Błąd bazy danych | Brak uprawnień do pliku | `chmod 664 rejestr_usterek.db` w folderze aplikacji |
| Kontener nie startuje po restarcie NAS | Container Station nie startuje automatycznie | W ustawieniach QTS włącz autostart Container Station |
