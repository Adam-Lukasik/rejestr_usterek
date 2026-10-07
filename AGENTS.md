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

## Dystrybucja dla techników (build skompilowany + updater)

- **Build:** `uruchom_release.bat` → `tools/build_release.py` (venv z Nuitką w `venv/`):
  check_i18n → eksport danych systemowych → minifikacja frontendu → kompilacja
  Nuitka `--standalone` (gcc/MinGW pobierany 1×) → `build/release/RejestrUsterek/`
  → ZIP + `latest.json` w `build/dist/`; `--deploy <udział>` kopiuje na NAS,
  `--skip-nuitka`/`--skip-tests`/`--no-minify`/`--console` do testów.
- **Układ pakietu:** `RejestrUsterek\{app\, data\, Updater.exe}` — `app/` jest
  podmieniane w całości przy update, `data/` (baza, config, Baza wiedzy) nietknięte.
- **Ścieżki:** `STATIC_DIR` (zasoby kodu) i `DATA_DIR` (dane) przez env
  `RU_STATIC_DIR`/`RU_DATA_DIR`/`RU_PKG_DIR` ustawiane w `desktop_web.py`
  (wykrycie builda: `__compiled__`/`sys.frozen`); w dev oba = katalog repo.
- **Updater:** `tools/updater.py` → `Updater.exe` (onefile); podmienia `app/` po
  zakończeniu procesu, status w `data/updates/update_status.json` (czytany raz
  przez UI po restarcie). Endpointy: `/api/version`, `/api/update/check|apply|status`.
  Źródło paczek: `UPDATE_SHARE` w config.json (udział SMB `...\updates` z
  `latest.json`; alternatywnie URL http(s)).
- **Migracje danych:** `migrations/NNNN_*.sql` w paczce, aplikowane przez
  `_run_migrations()` w `init_db` → tabela `schema_migrations`. Skrypty idempotentne;
  `tools/export_migrations.py` eksportuje tabele systemowe (`zuken_conn_pinouts`,
  `zuken_query_aliases` — lista `SYSTEM_TABLES`) z dev-bazy jako
  `CREATE IF NOT EXISTS` + `DELETE`+`INSERT` — zmiany w UI u Adama lecą do
  wszystkich baz z aktualizacją.
- **Delta Bazy wiedzy:** `tools/kb_push.py --dest \\NAS\RejestrUsterek` wysyła
  zmiany do `<udział>/kb/` + `kb_manifest.json`; klient `POST /api/kb-sync`
  dociąga deltę (stan w `data/.kb_sync_state.json`, usunięte → `data/.kb_removed/`).
- **Wersja:** stała `VERSION` w `app.py` — bump przed każdym buildem.
- **DevTools wyłączone** domyślnie (pywebview `debug=False` → AreDevToolsEnabled,
  skróty i menu kontekstowe off); frontend i tak serwowany po localhost —
  realna ochrona = minifikacja. Backend .py nie wchodzi do paczki (binarka Nuitka).
- **Sekrety:** `secrets.json` (gitignored, per-instalacja) nadpisuje klucze
  z `config.json` — trzyma `SMTP.PASSWORD`/`USER`. Stare hasło Gmail jest w
  historii git → **do zrotowania**. Szablon configu w paczce: `HOST=127.0.0.1`,
  SMTP wyłączone, bez haseł.

## Struktura danych / katalogi poza gitem

- `rejestr_usterek.db` — baza SQLite (gitignored)
- `Baza wiedzy/` — PDF-y schematów Zuken, dokumenty projektu (~658 MB, gitignored)
- `backups/` — paczki backupu (~1.3 GB, gitignored)
- `python-embed/` — przenośny WinPython (~303 MB, gitignored, per maszyna)
- `sumatrapdfcache/`, `SumatraPDF*` — podgląd PDF (gitignored)
- `webview_profile/` — trwały profil WebView2 (`private_mode=False` w `desktop_web.py`);
  trzyma localStorage UI: `ru_last_ps` (domyślny projekt PS stanowiska — fallback),
  `ru_last_ps_<username>` (ostatni projekt per użytkownik), `ru_theme`,
  `ru_active_user`, stan paneli (gitignored)
- `config.json` — jest w repo, ale **bez sekretów** (hasło SMTP przeniesione do
  `secrets.json`, gitignored). Stare hasło zostaje w historii git → rotacja w Gmailu.
- `secrets.json` — sekrety lokalne (SMTP), nadpisuje klucze config.json (gitignored)
- `build/` — artefakty builda release (gitignored); `migrations/` — SQL-e systemowe **w repo**
- `venv/` — venv z Nuitką do buildów (gitignored); `node_modules/` — narzędzia minifikacji

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
- Aktualny projekt PS: `STATE.lastSelectedPS` = jedyne źródło prawdy; zapis tylko
  przez `setCurrentPS()` (synchronizuje wszystkie selektory: `global-ps-select` w
  sidebarze, `f-projekt`, `docs-ps-select`, `reworks-ps-select`,
  `zuken-summ-ps-select`, `zuken-context-project-select` + przeładowuje aktywny
  widok). Klucz localStorage z `psStorageKey()` (per user). Po ustaleniu
  użytkownika wołać `loadUserPS()` (login/sesja/quick-switch). Wyjątki: „Wszystkie
  schematy" w asystencie i otwarcie z rekordu usterki NIE ruszają globalu;
  `f-projekt` chroniony gdy `STATE.editingRecordId`.
- Powiązane usterki w asystencie: backend (`diagnose_defect`) oznacza `scope`
  (0=ten projekt, 1=ten sam klient, 2=reszta), sortuje, zwraca `history_context`;
  klient z `_resolve_client_for_ps` (param > lists.projekty > zuken_ps_summaries
  > zuken_projects), porównanie `_clients_match`/`_client_key`.
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
  MIC (TE AMP Multi-Interlock 171892-1, 9p: siatka 2×5, góra 1-5, dół
  6,7,zatrzask,8,9 — środek dolnego rzędu to zatrzask, nie pin; X346/X347/
  X390-X393 = moduły Carnation),
  ROW (ogólny 1-rząd, `unverified`), USER (ręczny pinout, `/api/zuken/conn-pinouts`).
  Nowe rodziny dodawać tylko ze zweryfikowaną numeracją (rysunek katalogowy/zdjęcie
  od Adama); niepewny kierunek → `unverified: true` (ostrzeżenie w oknie złącza).
  Typ bez rysunku: węzeł i tak klikalny — okno pokazuje przewody i pinout.
  Kolory przewodów: `connFaceSvg(L, pin, {wireColors})` — mapa pin→[[baza,prążek]]
  z `wireColorPair(wire_color)`; 1 przewód = baza+prążek po skosie, 2 = podział po
  przekątnej, 3+ = pasy; wybrany pin = gruba niebieska obwódka. Mapę buduje
  `colorsFor()` w `showConnFace` (zestawienie + hopy obwodu) i w
  `showReworkConnFace` (item.pins); mini w diagramie dostaje kolor z `nd.edge`.
  Wariant obrysu: `CONN_LEVER_ARTS` = artykuły z blokadą dźwigniową
  (VAG 4H0 906 231 / osłona 1-968321-2, X168): dźwignia po prawej stronie
  korpusu, wypusty prowadnic i narożne, a dla siatki 4×10 — kwadratowy rastr
  z pasem szczelin między bankami pinów i numerami rzędów na marginesach.
  Podgląd SVG bez UI: wyciągnąć funkcje z HTML-a w node i zrzut przez headless Edge.

- Klikalność w asystencie: `entLink(q, label)` (jawny link) i `entText(raw)` (escape +
  kody aparatów znane w PS → linki; zbiór z `/api/zuken/known-devices`). Jeden handler
  `click` w fazie capture na `[data-ent-q]` → `goZukenEntity(q)` (nowe zapytanie,
  zamyka okna złącza/ścieżki). Historia ◀ ▶ + ścieżka: `ZUKEN_STATE.nav`,
  `zukenNavPush/zukenNavGo`. Ctrl+klik na węźle diagramu = od razu obwód.
- Listy kategorii: `zuken_service.assistant_list()` → `/api/zuken/assist-list`
  (bezpieczniki z prądem „7,5A”, przekaźniki, gniazda — „gniazdo 12V”,
  „gniazdo usb”, „zapalniczka”, „gniazdo NAK”); karta `assistListCardHtml()`.
- Aliasy firmowe: tabela `zuken_query_aliases` + wbudowane `_ASSIST_BUILTIN_ALIASES`
  (NAK → EJECT/SHORELINE/+NAK itd.); edycja w widoku Słowników, API
  `/api/zuken/aliases` (GET/POST/DELETE). „;” w terminach = osobne wymagane
  grupy (`SOCKET;12V` = tylko gniazda 12V). Grupy tokenów z aliasami:
  `_query_token_groups()` używane w `trace_circuit` i `assistant_list`.
- Test UI bez klikania: headless Edge + CDP (node 22 ma globalny WebSocket),
  `openAiDiagnosisModal({projekt, default_query})`, zrzut `Page.captureScreenshot`.

## Serwer centralny (Docker)

- `server_main.py` — headless entrypoint (bez webview/tkinter), env `RU_HOST`/`RU_PORT`/`RU_DATA_DIR`.
- `docker/` — Dockerfile (python:3.12-slim), docker-compose.yml (port 5050, wolumen `./data`),
  requirements-server.txt (bez pywebview), config.docker.json (HOST 0.0.0.0), INSTRUKCJA_DLA_IT.txt.
- `python tools/build_server_pack.py` → `build/server/rejestr_usterek_serwer_v<VERSION>.zip`
  (plaski układ dla Dockerfile, ~360 KB; VERSION brany regexem z app.py).
- Klienci: przeglądarka `http://serwer:5050` lub portable exe z `"server_url"` w
  `desktop_config.json` — wtedy klient jest thin-clientem (bez lokalnej bazy).

## Weryfikacja

- `node check_i18n.js` — kompletność tłumaczeń
- `python test_multilang.py` — testy wielojęzyczności
- Brak formalnego test runnera; testować ręcznie przez UI.
