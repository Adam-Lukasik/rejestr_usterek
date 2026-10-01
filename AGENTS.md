# Rejestr Usterek — kontekst dla agenta

## Co to jest

Lokalna aplikacja desktopowa (Flask + WebView2) do rejestru usterek i diagnostyki
serwisowej maszyn. Frontend to jeden duży plik `rejestr_usterek.html`
(HTML+CSS+JS inline). Backend: `app.py` (Flask, port 5050), `zuken_service.py`
(import danych Zuken E3: schematy, przewody, BOM, listy połączeń),
`backup_service.py` (pakiety backup/eksport), `desktop_web.py` (okno WebView2).

Wersja wielojęzykowa: `SUPPORTED_LANGS = ("pl", "en", "de")`, tłumaczenia w
`translations.js`, weryfikacja kompletności kluczy: `node check_i18n.js`.

## Uruchamianie

- `uruchom_nowe_ui.bat` — wykrywa Pythona: `python-embed\<WinPython>\python\python.exe`,
  potem `python\`, `venv\`, systemowy. Do-instaluje `requirements.txt`, startuje
  `desktop_web.py --local` przez `pythonw.exe`.
- Interpreter skonfigurowany w `.vscode/settings.json`:
  `${workspaceFolder}/python-embed/WPy64-312101/python/python.exe` (nie w repo).
- Baza: `rejestr_usterek.db` (SQLite, ~91 MB) — ścieżka w `config.json` → `DB_PATH`.
- Auto-backupy: `backup_service.py` → `backups/`, konfiguracja w `config.json`
  (`AUTO_BACKUP_*`).

## Struktura danych / katalogi poza gitem

- `rejestr_usterek.db` — baza SQLite (gitignored)
- `Baza wiedzy/` — PDF-y schematów Zuken, dokumenty projektu (~658 MB, gitignored)
- `backups/` — paczki backupu (~1.3 GB, gitignored)
- `python-embed/` — przenośny WinPython (~303 MB, gitignored, per maszyna)
- `sumatrapdfcache/`, `SumatraPDF*` — podgląd PDF (gitignored)
- `webview_profile/` — trwały profil WebView2 (`private_mode=False` w `desktop_web.py`);
  trzyma localStorage UI: `ru_last_ps` (domyślny projekt PS), `ru_theme`,
  `ru_active_user`, stan paneli (gitignored)
- `config.json` — **jest w repo** i zawiera hasło SMTP (app password Gmail).
  Repozytorium prywatne, ale rozważyć rotację hasła lub wyniesienie sekretów
  do pliku nieśledzonego (np. `config.local.json` / env).

## Workflow (Adam, 2 komputery, bez OneDrive)

- **Kod** — git/GitHub: repo `Adam-Lukasik/rejestr_usterek`, aktywny branch
  `feature/v2.0-bilingual`. Przed pracą `git pull`, po `commit` + `push`.
- **Cały katalog** (z db, Bazą wiedzy, backupami) — Adam przenosi na pendrive
  między pracą a domem: na docelowym kompie zmienia nazwę starego katalogu na
  `..._old`, kopiuje całość z pendrive. Rutyna, nie optymalizować bez pytania.
  Uwaga: program zmienia mtime `rejestr_usterek.db` przy KAŻDYM starcie, więc
  kopiowanie na istniejący katalog z opcją „Zastąp wszystkie starsze” (Total
  Commander) potrafi pominąć nowszą treściowo bazę (incydent 29.09: 88 vs 87
  usterek). Kopiując na istniejący katalog — „Zastąp wszystkie”.
- Komunikaty commitów po polsku, krótko, konwencja jak w `git log`.
- Konwersacje Devina NIE migrują między maszynami — ten plik jest pamięcią
  długoterminową; aktualizować przy zmianach workflow/struktury.

## Konwencje kodu

- Backend: Flask, proste funkcje `api_*`, odpowiedzi `jsonify`, komunikaty przez
  `smsg()` (i18n). DB przez `sqlite3` + `Row`.
- Frontend: vanilla JS w jednym HTML-u, `t()` dla i18n, `escapeHtml()`,
  helpery typu `wireLabelAttrs()` współdzielone między widokami.
- Nowe typy bazy wiedzy: tablica `KB_TYPES` w HTML + obsługa w backendzie.
- Ścieżki plików KB: zawsze przez `zuken_service.resolve_kb_filepath(..., heal_db=True)`
  — naprawia ścieżki po przeniesieniu katalogu projektu.
- Prace nad obwodami/przewodami: sygnały mają `wire_number`, `signal`,
  `signal_name`, `wire_color`, `cross_section`, `length` — używać
  `wireLabelAttrs()` do etykiet.

- Rysunki złączy (widok od strony przewodów): `connFaceLayout()` rozpoznaje rodzinę
  po artykule/opisie z `zuken_ps_connectors`/BOM, `connFacePinAt()` numeruje gniazda,
  `connFaceSvg()` rysuje. Rodziny: JPT, MCP (AMP 2.8 3-rzędowe), MINIFIT,
  MICROFIT, MOLEXSR (Micro-Fit 1-rzędowy), SUPERSEAL, MATENLOK, TE2P (MQS/MCON
  2p), CIRC7 (TE okrągłe 7p, komórki kołowe), DF11 (Hirose 2-rzęd.),
  FASTIN/FF250 (2-kolumnowe pionowe), TBP, RELAY9 (Hella 5/9), RCA,
  ROW (ogólny 1-rząd, `unverified`), USER (ręczny pinout, `/api/zuken/conn-pinouts`).
  Nowe rodziny dodawać tylko ze zweryfikowaną numeracją (rysunek katalogowy/zdjęcie
  od Adama); niepewny kierunek → `unverified: true` (ostrzeżenie w oknie złącza).
  Typ bez rysunku: węzeł i tak klikalny — okno pokazuje przewody i pinout.
  Wariant obrysu: `CONN_LEVER_ARTS` = artykuły z blokadą dźwigniową
  (rama Π + ramiona ze sworzniami; VAG 4H0 906 231 / osłona 1-968321-2, X168).
  Podgląd SVG bez UI: wyciągnąć funkcje z HTML-a w node i zrzut przez headless Edge.

- Klikalność w asystencie: `entLink(q, label)` (jawny link) i `entText(raw)` (escape +
  kody aparatów znane w PS → linki; zbiór z `/api/zuken/known-devices`). Jeden handler
  `click` w fazie capture na `[data-ent-q]` → `goZukenEntity(q)` (nowe zapytanie,
  zamyka okna złącza/ścieżki). Historia ◀ ▶ + ścieżka: `ZUKEN_STATE.nav`,
  `zukenNavPush/zukenNavGo`. Ctrl+klik na węźle diagramu = od razu obwód.
- Listy kategorii: `zuken_service.assistant_list()` → `/api/zuken/assist-list`
  (bezpieczniki z prądem „7,5A”, przekaźniki + filtr słowami); karta `assistListCardHtml()`.
  Plan dalej: etap 3 — edytowalne aliasy firmowe (NAK = gniazdo zewnętrzne 115/230V →
  SHORELINE/EJECT/AUTO-EJECT) w tabeli DB + ekran w Słownikach, listy gniazd USB/12V/
  zapalniczka; tylko wybrany PS.
- Test UI bez klikania: headless Edge + CDP (node 22 ma globalny WebSocket),
  `openAiDiagnosisModal({projekt, default_query})`, zrzut `Page.captureScreenshot`.

## Weryfikacja

- `node check_i18n.js` — kompletność tłumaczeń
- `python test_multilang.py` — testy wielojęzyczności
- Brak formalnego test runnera; testować ręcznie przez UI.
