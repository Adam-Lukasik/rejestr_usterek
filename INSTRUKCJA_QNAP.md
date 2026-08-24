# Instrukcja wdrożenia Rejestru Usterek na serwerze QNAP NAS

Ten dokument jest przeznaczony dla Administratora Sieci / Informatyka w celu jednorazowego uruchomienia usługi **Rejestr Usterek** na firmowym serwerze QNAP NAS (`srv_ost`).

---

## 📌 Założenia i Architektura
- Usługa to lekki mikroserwis Python/Flask z bazą SQLite (tryb WAL) oraz produkcyjnym serwerem WSGI (Waitress).
- Wszystkie pliki aplikacji i baza SQLite znajdują się w **folderze współdzielonym na dysku NAS** (np. `\\srv_ost\Pomiary\rejestr_usterek`).
- **Dzięki temu:** kolejne aktualizacje kodu czy kopie zapasowe wykonuje zespół produkcyjny bez angażowania Administratora.
- **Port usługi:** **`5050`** (wybrany celowo, aby wykluczyć kolizję z wbudowanym w QTS serwerem Apache/multimedia na porcie 5000).

---

## 🚀 Metoda 1: Uruchomienie w Container Station (Docker) — ZALECANA

### 1. Przygotowanie folderu na QNAP
1. W zasobie sieciowym `\\srv_ost\Pomiary` (lub ścieżce systemowej `/share/Pomiary/` / `/share/CACHEDEV1_DATA/Pomiary/`) utwórz katalog:
   ```text
   rejestr_usterek
   ```
2. Skopiuj do niego pliki aplikacji: `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `app.py`, `config.json`, `rejestr_usterek.html` oraz bazę `rejestr_usterek.db`.

### 2. Uruchomienie w Container Station (GUI)
1. Otwórz **Container Station** na QNAP.
2. Przejdź do zakładki **Aplikacje (Applications)** $\rightarrow$ kliknij **Utwórz (Create)**.
3. Nazwa aplikacji: `rejestr-usterek`
4. Wklej zawartość pliku `docker-compose.yml` (lub wskaż folder z plikiem).
5. Kliknij **Utwórz (Create)**.

*Alternatywnie przez terminal SSH:*
```bash
cd /share/Pomiary/rejestr_usterek
docker-compose up -d --build
```

---

## 🛠️ Metoda 2: Alternatywna — Uruchomienie bezpośrednio przez Pythona (bez Dockera)
Gdyby Container Station nie był używany, aplikację można uruchomić natywnie:
1. Zainstaluj środowisko Python (lub Entware) na QNAP.
2. Zainstaluj pakiety:
   ```bash
   pip install flask flask-cors waitress
   ```
3. Uruchom usługę w tle:
   ```bash
   nohup python -c "import app; app.init_db(); from waitress import serve; serve(app.app, host='0.0.0.0', port=5050, threads=8)" >> server.log 2>&1 &
   ```

---

## ⚙️ Parametry sieciowe i dostęp

- **Protokół:** HTTP
- **Port:** `5050` (TCP)
- **Autostart:** włączony domyślnie (`restart: unless-stopped`). Kontener wstaje automatycznie po restarcie QNAP-a.
- **Dostęp z przeglądarek w sieci LAN:**  
  👉 `http://srv_ost:5050` (lub `http://<IP_SERWERA_QNAP>:5050`)
- **Dostęp z aplikacji stanowiskowych (laptopy):**  
  Stanowiska łączą się automatycznie przez plik startowy `uruchom_srv_ost.bat`.

---

## ✉️ Konfiguracja powiadomień E-mail (Opcjonalnie)
W pliku `config.json` w folderze aplikacji można opcjonalnie podać dane firmowego serwera SMTP (np. do wysyłki kodów resetu haseł):
```json
"SMTP": {
  "ENABLED": true,
  "SERVER": "smtp.twojafirma.pl",
  "PORT": 587,
  "USE_TLS": true,
  "USER": "rejestr-usterek@twojafirma.pl",
  "PASSWORD": "haslo_skrzynki",
  "SENDER_NAME": "Rejestr Usterek — Powiadomienia"
}
```

---

## 🔄 Jak przebiegają późniejsze aktualizacje?
Informatyk nie musi być angażowany do bieżących zmian w kodzie. Zespół podmienia plik `app.py` lub `rejestr_usterek.html` bezpośrednio w folderze `\\srv_ost\Pomiary\rejestr_usterek` i w razie potrzeby klika „Restart” w Container Station.
