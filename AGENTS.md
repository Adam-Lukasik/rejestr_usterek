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
  `pip install -r requirements.txt` + `tools/check_build_deps.py` (twarde
  sprawdzenie zależności venv — Nuitka po cichu pomija moduły nieobecne
  w venv; incydent 2.11: paczki ≤2.2.0 nie miały `pypdf` mimo requirements,
  bo venv był starszy niż wpis w requirements) → check_i18n → eksport danych
  systemowych → minifikacja frontendu → kompilacja Nuitka `--standalone`
  (gcc/MinGW pobierany 1×) → **self-check exe** (`RejestrUsterek.exe
  --selfcheck <plik>` importuje wszystkie wymagane moduły, kod wyjścia ≠0
  lub `ok:false` = STOP builda; w działającej aplikacji to samo daje
  `GET /api/selfcheck`) → `build/release/RejestrUsterek/`
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
  `zuken_query_aliases`, `zuken_translations` — lista `SYSTEM_TABLES`) z dev-bazy jako
  `CREATE IF NOT EXISTS` + `DELETE`+`INSERT` — zmiany w UI u Adama lecą do
  wszystkich baz z aktualizacją. Uwaga: pełny DELETE na pinoutach/aliasach
  usuwa wiersze dopisane lokalnie w innej bazie — przed update na obcej bazie
  zrzut przez `tools/zabezpiecz_systemowe.py dump|diff|restore`.
- **Delta Bazy wiedzy:** `tools/kb_push.py --dest \\NAS\RejestrUsterek` wysyła
  zmiany do `<udział>/kb/` + `kb_manifest.json`; klient `POST /api/kb-sync`
  (przycisk w ustawieniach backupu) dociąga deltę (stan w `data/.kb_sync_state.json`,
  usunięte → `data/.kb_removed/`).
- **Zdjęcia komponentów w paczce:** `Baza wiedzy/zdjecia_komponentow/` jest
  kopiowane do `app/zdjecia_komponentow/` przy buildzie — lookup w
  `find_local_component_image` i `/api/zuken/bom/image/` (przez
  `resolve_bom_image_path`) sprawdza lokalny katalog danych i pakiet —
  **wygrywa nowszy plik (mtime)**, przy remisie lokalny. Update ze świeżym
  zdjęciem przykrywa stare pobrane u klienta; późniejszy upload/fetch
  użytkownika znowu wygrywa.
- **Wersja:** stała `VERSION` w `app.py` — bump przed każdym buildem.
  Odrębna stała `DATA_VERSION` (epoka danych): podbić TYLKO gdy wydanie
  wymaga ponownej generacji zestawień Zuken + skanu kontroli (nowe/
  zmienione detektory, format cache PDF, łatki). Frontend pokazuje
  adminowi modal odświeżania (`checkPostUpdateRefresh`), gdy
  `app_state.data_version` < `DATA_VERSION`; brak klucza przy danych
  w bazie → 0 (wymusza), przy pustej bazie → od razu bieżąca epoka.
  Koniec/Pomiń: `POST /api/zuken/post_update/finish`.
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
  `ru_active_user`, `ru_zuken_nav` (historia zapytań asystenta per projekt:
  `{byPs:{"<PS>":[{q,mode},...]}}`, klucz "" = tryb „Wszystkie schematy",
  po 30 wpisów na projekt; przełączenie projektu w oknie asystenta ładuje
  jego historię — `zukenNavRestore`), stan paneli (gitignored)
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
- Bezpieczniki w asystencie: `trace_circuit` rozwiązuje element -F przez
  `holder_code` (dokładny kod → sufiks tylko jednoznaczny lub bez prefiksu —
  sufiks w obcej lokalizacji brał cudzy obwód: F12 pokazywał =CAB+MIK-FH12),
  potem parowanie -F→-FH/-U z geometrii etykiet PDF (`_ps_fuse_rails` →
  `holders`/`slots`; oprawki przewodowe innego numeru niż element:
  F20→=CAB+TWR-FH1, F19→FH15, F18→FH36, F6@Walia→=CAB+BSI-FH15), na końcu
  sloty -U z `rt_to_u`. Uwaga: `devs_by_clean` ma wpis per pin — dedupe przed
  testem jednoznaczności. Walia: elementy `-F<n>_BOX` siedzą w skrzynce
  `=BOX+ACT-A10` — gniazdo to jej piny `nA`/`nB` (`box_pins`); część
  elementów jest w raporcie z prądem w nazwie (`-F8_3A`, `rated`); oprawka
  nieobecna w raporcie jest dla niego przezroczysta — końce jej przewodów
  to etykiety `-RT` nad/pod kolumną bezpiecznika (`terms`: F1→RT122+RT12,
  F24→RT150+RT145). Zwora/mostek pinów między sąsiednimi -F (uchwyt
  2-stanowiskowy -U147 dla F9:1=F11:1, szyna wyjściowa F10:2=F41:2):
  na stronie bez własnego terminala, w szerszym zasięgu kolumny
  (|dx|<=80), terminal zajęty przez inny -F na TEJ SAMEJ stronie =
  terminal wspólnej szyny — `bars` zapisuje parę dla OBU bezpieczników
  i terminal dokładany jest do `terms`. `bars` bierzemy tylko ze strony
  `terms` — strony-zestawienia mają rozjeżdżające się etykiety i dawały
  złudne pary (F13 łapało cudzy RT1 na str. 56). Numery pinów na tych
  planszach: etykieta terminala POD symbolem -F = pin 1, NAD = pin 2
  (pin zwory narzucany stroną geometrii — F9/F11 zwora na pinie 1,
  F10/F41 na pinie 2). Seed-terminali nie rysujemy jako osobnych
  obciążeń — `trace_circuit` scala je w syntetyczny węzeł -F z pinami
  1/2 (stub-hop `F9:1→RT167:1` + oryginalna ścieżka); pin 1 = terminal
  z końcem roli 'terminal' (stud zasilania), samotny terminal bez
  takiego końca = pin 2. Terminal zwory: tor pin→terminal prowadzony
  przez syntetyczny węzeł `=<lok>-ZW<a>_<b>` (hop `internal='busbar'`
  na segmencie zwora→terminal) + odnoga do sąsiedniego bezpiecznika
  (end role 'fuse', klik → jego obwód). Frontend: węzeł `ZW*`
  (`/^ZW/`) rysowany poziomym prostokątem jak splice-okrąg
  (`nd._bar`), krawędź 'busbar' = przerywana linia + etykieta
  `js.zuken.busbar`. Ponadto pass wektorowy w `_ps_fuse_rails` wykrywa
  szyny NARYsowane w PDF (wszystkie ogniwa mają własne terminale —
  mechanizm brakującego terminala ich nie widzi): `_pdf_page_line_segments`
  (operatory m/l/re) + `_merge_runs_h/_v` (najpierw klaster po y/x —
  sekwencyjny merge wchłaniał biegi obcych współrzędnych) → kandydat to
  poziomy bieg ściśle wewnątrz obrysu skrzynki (obrys = DOMINUJĄCA para
  (top,bot) wśród ścianek ogniw — deduplikowane; medianę zaburzają
  scalone przewody pinowe), przecinający ≥1 ściankę w środku zasięgu x,
  z końcówką pinową ≥2 ogniw; krawędź skrzynki odpada testem
  "końce ścianek > przejścia" (ścianki KOŃCZĄ się na krawędzi, przechodzą
  przez szynę). Ogniwo bez -F z ciągłym pionem = przelotka (FH0) —
  jej etykiety -RT nad/pod dokładane do węzła (`taps`). Podzbiory
  członków z dwóch krawędzi prostokąta scalane w nadzbiór. Wykryte u
  Walii: MOR F9:1↔F11:1 i F10:2↔F41:2 (uchwyty -U147/-U146 = BOM
  'AK 602 010 002 2 WAY BUS-BAR'), szyna BSI F1:2..F4:2 + przelotka FH0
  (zworka MTA 0301226 docinana — brak w BOM jako urządzenie), =BOX
  F33:2..F36:2 (-U210 = '4 WAY BUS-BAR'). Etykieta -U najbliższa szynie
  i obecna w mapie BUS-BAR z BOM trafia do `bars[*]['holder']` → hop
  `bar_holder` → węzeł ZW rysowany jako klikalna oprawka (ent-link na
  clean urządzenia); bez holdera — etykieta `ZW…`. `pitch` rozstawu
  ogniw liczony z samych etykiet -F (`-FH`/`startswith('-F')` łapie też
  -FH!). Bezpiecznik bez toru → karta "rozpoznano, brak
  okablowania" (`js.zuken.circuitNoWires`) — trwałe missy u Walii to
  F5 (125A MEGA, brak etykiety na schemacie i urządzenia w raporcie) i
  A11 (=CAB+MOR-A11 "Comms Fuse Box" — obudowa skrzynki bez reprezentacji;
  jej bezpieczniki F9–F11/F41 śledzone przez terminale RT). Sloty
  jednopinowe (-U z pinem '' w raporcie, E3 scala oba zaciski w jeden
  węzeł — banki Mega/MIDI jak F6–F10@PS011871): `u_split` w
  `_ps_fuse_rails` rozbija pin '' na kołki '1'/'2' geometrią — strona
  rysunku banku = strona z największą liczbą członków grupy
  (strony-zestawienia powielają rząd), szyna = najszerszy poziomy bieg
  przez ≥2 kolumny ≤100 pt od rzędu -F, terminale -RT w kolumnie
  |dx|≤90 sortowane względem mediany fy etykiet (POD etykietą = pin 1,
  NAD = pin 2). `_circuit_extend_adjacency` przenosi raportowe krawędzie
  na kołki i okablowuje grupę: szyna -SZYNA↔kołek `rail_pin`, element
  -F między kołkami. Ręczna łatka `connection` do kołka strony szyny
  (RT3:1↔U9:2 = ta sama szpilka co RT111). Jednopinowy element -F
  dostaje w `trace_circuit` post-pass rozdzielający końce na piny
  '1'/'2' wg kołka slotu pierwszego przeskoku 'fuse' (inaczej diagram
  rysuje jedną grupę ~11 odnóg zamiast dwóch stron jak przy F49).
  Banki narysowane bez etykiet -F (np. =CAB na str. 1 sch.2
  PS011871 — sloty U3–U7 = F11–F15, fabryczne bezpieczniki MAN,
  dolna szyna = akumulator pojazdu bazowego): pass w
  `_ps_fuse_rails_raw` kotwiczy bank łańcuchem >=3 etykiet -RT w
  sąsiednich kolumnach, gdzie każda jest terminalem innego
  jednopinowego slotu -U; etykieta łańcucha = pin '1' (wyjście),
  pozostałe scalone terminale = pin '2' (szyna, np. odczep RT71
  na U4). Członków dokłada tylko do DOKŁADNIE JEDNEJ przeciętej
  grupy (rzędy na stronach-zestawieniach objęłyby kilka banków),
  zero przecięć → nowa grupa (D10|RAIL|SZYNA3 = F11–F15). Diagram:
  `circuitFuseDownPin` musi łapać też DRUGI pin roli 'feed' — oprawki/sloty
  (FH/FR/F/U i zespół -A10) mają oba piny 'feed' (np. FH1:1 zasilanie,
  FH1:2 → przewód 405 → X295 → A15); bez tego rysowała się tylko strona
  wejściowa. Dla pinu-'feed' downEnd = ends[0] (uporządkowane wg
  istotności), dla 'other' — preferencja role 'load'.
- Zestawienie bezpieczników (`get_ps_fuses`) ma własne parowanie geometrią
  (`_pdf_geometry_candidates` + głosowanie między arkuszami + tekstowe
  `_pdf_holder_candidates`). `_resolve_dev_label` przy remisie kandydatów
  wybiera urządzenie okablowane w TYM projekcie (`conn_devs`) — `known_devs`
  łączy BOM-y wszystkich projektów i alfabetycznie wygrywał cudzy kod
  (=CAB+BSI-FH15 z Walii zamiast =CAB+TWR-FH15 z EoE → holder_real bez
  przewodów).
- Oprawki -FH/-FR vs osadzony bezpiecznik: `rating` wiersza oprawki w
  `zuken_ps_fuses` to KATALOGOWY limit gniazda sparsowany z opisu
  ('up to 30A' w 'FUSE HOLDER ... 12/24VDC'), NIE prąd bezpiecznika.
  Adam chce widzieć tylko faktyczny element: `_fuse_holder_fuses()`
  daje mapę oprawka→-F (odwrotność `rails['holders']` + dokładny
  holder_code istniejący w adj) i `ratings` clean→prąd. `trace_circuit`
  post-procesem podmienia `internal_label` krawędzi 'fuse' na 'F19 20A',
  dokłada `ld['fuse_label']` (frontend: etykieta scalonego pinu +
  nagłówki karty/diagramu), tytuł zapytania o oprawkę to 'FH15 → F19 20A
  (obwody)' i tnie 'up to xA' z opisów oprawek (`_strip_holder_rating_text`
  na ld/e.function, e.desc, hop.to_function, conn_meta). W `get_ps_fuses`
  wiersz oprawki scala się z wierszem jej bezpiecznika NIEZALEŻNIE od
  prądu (stary warunek 'różny rating = osobny bezpiecznik' był błędny —
  rating oprawki to limit), więc FH15/FH1 wsiąkają w F19/F20: wiersz
  bezpiecznika dostaje holder_article + obwody oprawki gdy miał tylko
  generyczne 'Obwód instalacji'. Niesparowane oprawki zostają jako
  `is_holder` (+ew. `fuse_in` z odwrotności holder_real) — frontend
  rysuje chip 'gniazdo bezpiecznika' zamiast badge'a prądu/typu; opisy
  oprawek i holder_description też czyszczone.
- Pozycje bezpieczników w skrzynkach NIEWIDOCZNE w raporcie połączeń
  (boxy COMMS IGN/PERM na str. 42 PS011871 — raport agreguje wyjścia do
  -SP31/-SP32): `_pdf_page_text_positions` (tokeny z XY: etykiety + prądy
  'xA' + frazy CAPS jak 'COMMS IGN' — cache `zuken_pdf_textpos`, format
  {'v':2,'items':...}, zapis toleruje lock) + `_pdf_fuse_boxes` (pasmo
  prądów w jednym y → split po przerwie x>40 na osobne boxy; tylko
  standardowe prądy z `_STD_AMPS`; >=3 pozycje; out_dev = najbliższa
  etykieta -X/-RT/-SP w kolumnie poniżej, ale NIE -FH/-FR/-U/-F — to
  modelowane oprawki). `_populate_ps_box_fuses` (w generate_...):
  `zuken_ps_box_fuses` z nazwą boxa z opisów przy wyjściach (out_desc
  'COMMS IGN'/'COMMS PERM', fallback sygnał; suffiks -N przy kolizji).
  Komórka = litera NAD kolumną + cyfra POD nią (końce gniazda siatki
  A-F×1-6 → 'A1'..'F6'); dopasowanie POZYCYJNE i-ty znak→i-ta kolumna
  (okno odległości pudłuje); przypisanie kolumna→etykieta wyjścia jest
  GLOBALNE `_min_cost_pairs` (sąsiednia etykieta bywa bliższa: prąd
  przesunięty w lewo symbolu — bez tego poz.2 łapała -X202 zamiast
  -X203); feed/out w pionie ≤160, etykiety '-X414#1' łapane z '#'.
  Wiersze w get_ps_fuses: `is_box_fuse`, clean 'COMMS IGN A1', wires z
  out_dev (sufiks-match w conn_devs), circuits = sygnał wyjścia.
  `trace_circuit` rozwiązuje 'COMMS IGN A1'/'COMMS IGN 1' → seed
  out_dev (X206), label 'COMMS IGN A1 5A → KL 15 COMMS'. Frontend: chip
  'bezpiecznik w skrzynce' + klik→obwód. Diagnostyka pokrycia:
  `tools/inventory_fuses.py [PS]`. Sortowanie zestawienia: klik w
  nagłówki (sortZukenFuses, cykl asc→desc→domyślne, prąd numerycznie).
- Bieguny akumulatorów: raport E3 nie wiąże oczka -RT ze szpilką baterii
  (wiersz z pustym kodem urządzenia, pin '{4}'/'{5}') — końcówka wygląda
  na wiszącą (D02). `_ps_battery_studs` odtwarza połączenie z geometrii
  schematu: para znaków '+/−' w stałym rozstawie poziomym (8..100 pt,
  EoE ~56, Walia ~14) na stronie z symbolem `-G<n>`; etykieta -G
  przypisywana 1:1 `_min_cost_pairs` (bateria KFZ bez etykiety
  „pożyczała" -G3 sąsiada); bateria bez -G → syntetyczny kod
  `=SYS+LOC-AKU<n>` z tokenów POD biegunami (nad nimi leżą etykiety
  przewodów/końcówek — stąd filtr y<=my+30). -RT do najbliższej pary
  (≤230 pt), biegun '−' gdy obwód GND/PE/MASA, inaczej '+'; tylko oczka
  wiszące albo masowe. `_circuit_extend_adjacency` dokłada krawędź
  `_internal='battery'` (+`_batt_pin`) do węzła (bateria,'+'/'−');
  `_circuit_end_role` → 'gnd' dla '−', 'source' dla '+'. Tokeny
  `_pdf_page_text_positions` (format v4: etykiety `-[A-Z]{1,3}\d+`
  łapią też -A/-Q itd., `/` w słowach CAPS) łapią też `-G\d+`, `=SYS`,
  `+LOC` i znaki '+/−'. Audyt D02 pomija te końcówki (`_bats` w
  schema_audit, wspólny `_wadj` z `_rails`).
- Nazwane szpilki aparatów: `_ps_device_studs` — ten sam mechanizm co
  baterie, dla nagłówków kolumn POSITIVE/NEGATIVE/PE-EARTH/EARTH/GROUND/
  NEUTRAL nad zaciskami aparatu (inwerter -A9 na EoE: RT59→POSITIVE,
  RT60→NEGATIVE, RT63→PE/EARTH). -RT przypisywany do kolumny nagłówka
  (|dx|<=45, pionowo <=220), przy remisie kolumn rozstrzyga
  biegunowość obwodu; urządzenie = najbliższa etykieta
  `-(A|S|Q|M|B|H|P|N|T)<n>` w promieniu 350 pt od nagłówka, kod z BOM
  przez prefiks-score. Krawędź `_internal='stud'`, tylko oczka wiszące.
- Łatki `device_link`/`power_rail` mogą wskazywać urządzenia spoza
  raportu (np. -F6..-F10 z banku bezpieczników): `_patch_dev` ma
  fallback na BOM projektu (pełny kod verbatim albo jednoznaczny
  clean), a brakujące węzły pinów są tworzone — szyna/wiązanie wewn.
  działa też dla urządzeń bez wierszy w `zuken_connections`
  (RT3 na wspólnej szynie F6–F10: power_rail z members RT3:1 +
  F6..F10:1).
- Tłumaczenia tekstów schematu (sygnały/funkcje/arkusze/kolory): tabela
  `zuken_translations` (forma→pl/en/de, kind=phrase/token/jargon,
  source=core/local) — display-time `_localize_payload` dokłada pola `*_t`
  do odpowiedzi API (wrappery nad `*_impl` na końcu zuken_service.py;
  whitelist `_LOCALIZE_KEYS`, bez `description`/`signal`; `conn_meta` bez
  `desc`/`label`). `translate_term`: fraza→n-gram→tokeny; kody z cyframi
  i żargon wprost; ALL-CAPS zachowane; miss → `zuken_term_unknown`
  (lokalna kolejka „Do tłumaczenia" w Słownikach, edycja admin:
  `/api/zuken/terms`). Seed: `tools/author_terms_seed.py` →
  `data/terms_seed.json` → `tools/seed_terms.py`; eksport przez
  `SYSTEM_TABLES` + `DELETE_WHERE`/`TABLE_ROW_OVERRIDES` w
  export_migrations (wpisy `local` przetrwają update). Frontend: `tr()`,
  `origTitle()`. Wyszukiwanie po tłumaczonych nazwach: `_term_token_expand`
  w `_query_token_groups`. `explain_device_code` dla `de` tłumaczy
  `desc_en` słownikiem (glossary nie ma desc_de).
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
  2p), CIRC7 (okrągłe 7p, komórki kołowe) — **dwie numeracje tej samej
  geometrii**, rozróżniane flagą `L.was`: TE 1718230-x (X388/X396 =
  wtyczka do oryginalnej wiązki auta bazowego) wg rys. TE: środek=1,
  pierścień 2-7; wkładka lampy Waś "03 złącze waś" (artykuł `WAS IV.1`,
  X268/X395 — złącze przy samej lampie, nie mylić z X388!): pierścień
  1-6 od góry za ruchem wskazówek, środek=7 — tłoczone numery na zdjęciu
  gniazda lampy (funkcje E3 zgodne: 1=GND, 2=pozycja, 3=cofania,
  4=kierunek, 5=stop, 6=mgła, 7=pozycja2); wypustka pozycjonująca na
  obwodzie między pinami 4 a 5 — trapezowe wcięcie, rysowane TYLKO dla
  `L.was` (dla tej rodziny wyłączona generyczna belka zatrzasku — to
  złącze bagnetowe), DF11 (Hirose 2-rzęd.),
  FASTIN/FF250 — dwie serie: stara 1809xx (2-kolumnowe pionowe, rys. C-163007)
  i nowsza "housing lance" 1721xx/17189x/171433 (poziome 2×n/2: 4p=172134,
  6p=171898+171897, 8p=172135/172136, 10p=172137/172138; 2p=172129/172130
  pionowo 2×1) — `L.lance`, zatrzask na górnej ściance, wbudowana numeracja
  `unverified`; moduł centralki WAECO ML-22/44 ma DWIE wtyczki numerowane
  wspólnie 1-10 (6p: dół 1,2,3 / góra 6,7,8; 4p: dół 4,5 / góra 9,10) —
  pokryte rekordami USER `171898-1` (X158/X86, zweryfikowane z instrukcji)
  i `172134-1` (X87, mapowanie pinów `unverified`); dokumenty w
  `Baza wiedzy/PS012732/TE_*`,
  MIC (TE AMP Multi-Interlock 171892-1, 9p: siatka 2×5, góra 1-5, dół
  6,7,zatrzask,8,9 — środek dolnego rzędu to zatrzask, nie pin; X346/X347/
  X390-X393 = moduły Carnation),
  ROW (ogólny 1-rząd, `unverified`), USER (ręczny pinout, `/api/zuken/conn-pinouts`).
  USER: `pins_map` to lista row-major lub obiekt `{"map": [...], "devices":
  {"QC13": {"1": "4"}}, "unverified": true, "latchSide": "left"}` — `devices`
  wiąże rysunek
  OBUDOWY z urządzeniem, gdy jego artykuł to goły terminal (np. QC12/QC13/QC14
  = terminale MCP/MQS we wtyku `RBA2` Body Controllera Sprintera VS30, BCM V2
  A907 900 08 06: siatka 2×18, MCP 1-8 + odstęp + MQS 9-34); `devmap` tłumaczy pin urządzenia na
  etykietę komory, `'x'` w map = komórka poza wkładką (odstęp, nie rysowana);
  `latchSide` `"left"`/`"right"` = zatrzask na bocznej ściance obudowy, wypustka
  przy dolnym rzędzie zamiast belki u góry/dołu (np. Carling VCH-01 = X133,
  wtyk przełącznika Contura — numery wzdłuż ścianek, zatrzask przy pinie 3).
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
- Diagram obwodu (`circuitSvgForLoad`): węzeł-pin aparatu-seeda na styku toru
  zasilania i masy (ostatni węzeł `trunk` + pierwszy `gndChain`, ten sam `dev`,
  brak krawędzi wewnętrznej) **scalany w JEDEN węzeł** złącza (`nd.pins`,
  `nd._absWire` = krawędź wchłoniętego pinu masy dla koloru w mini) — osobne
  pudełka pinów czytały się jak "dwie połówki" wtyczki (X388 = jedna wtyczka
  w lampę Waś). Ograniczone do złączy (`/^x/i` clean lub znany `connFaceLayout`)
  — pary wtyk/gniazdo (X300/X300' = inny `dev` + krawędź 'mate') i topiki
  (krawędź 'fuse' na pinach oprawki) zostają osobnymi węzłami w ramce seeda.
  `rowOf` dostaje alias `dev:pin` → indeks scalonego węzła dla wszystkich
  `nd.pins`. Piktogramy typu urządzenia: `DEV_KINDS`/`devKind()` (regex na
  info+desc+module_label → lamp/fan/motor/speaker/horn/lock/pump/heater/
  solenoid/antenna/module), `devGlyph()` rysuje symbol schematowy po LEWEJ
  stronie węzła (seed + role load/source), `DEV_KIND_EMOJI` w etykietach odnóg.
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

## Kontrola schematów (schema_audit.py)

Rejestr błędów/braków w danych Zuken + łatki-nakładki dla asystenta + eksport
listy poprawek dla inżyniera E3. Nowy widok „Kontrola schematów"
(`data-view="schema-audit"`), API pod `/api/zuken/audit/*`.

- **Rejestr**: `zuken_issues` (lokalna, NIE tabela systemowa) —
  `fingerprint` = `D<nn>|<klucz>` stabilny między skanami (dedupe/upsert).
  `target` = 'engineer' (do E3) | 'internal' (do uzupełnienia u nas);
  statusy i ważność w `CATEGORIES`/`OPEN_STATUSES`. Komunikaty PL/EN/DE jako
  `msg_key`+`msg_params` w `AUDIT_MSG`, render przez `amsg()`/`render_issue()`
  (nie trzymać gotowych tekstów w bazie). Lokalizacja = `location` JSON
  (schematic_id/page/bbox/grid → `device_location()`, `grid_ref()` siatka
  ramki '2.B'); wycinek PNG `snapshot_png()` (pypdfium2 + PIL, oba w
  SELF_CHECK_MODULES).
- **Skan**: `run_scan(ps, stages)`; DETECTORS D01–D15, etap 'data' (tylko
  baza — leci też w `_audit_autoscan` po generate summaries/import) i 'pdf'
  (geometria schematu — tylko przycisk Skanuj). Nieodtworzone zgłoszenia
  zamykane: internal→'done', engineer→'verified' gdy zmieniła się rewizja
  (`ps_revision_key` = max(imported_at)+mtime schematu). Regresja
  (verified/done → zgłoszenie wróciło) otwiera jako 'new'.
- **D02 dangling_terminal**: końcówka -RT z jednym przewodem PE/GND to
  poprawny punkt masowy w nadwoziu (oczko przykręcane do karoserii) —
  pomijana przez `_is_pe_gnd_wire` (kolor GNYE/YE-GN albo słowo
  PE/GND/GROUND/EARTH/MASSE/MASA w sygnale/funkcji; `wire_color` jest w
  `Ctx.connections` właśnie dla tego).
- **D14 pinout_missing**: `_conn_face_family()` to PORT predykatu
  `connFaceLayout()` z frontendu (rodziny złączy) — przy dodawaniu rodziny
  w JS trzeba zaktualizować tutaj, inaczej fałszywe 'missing'. Grupuje po
  artykuł+opis jak raport rysunków (`get_ps_connector_types`: artykuł z BOM
  halves ma pierwszeństwo); missing→warn, unverified→info; suggestion
  kind 'pinout' → frontend otwiera `openConnPinoutEditor`.
- **D15 pdf_report_label**: etykiety z `zuken_pdf_symbols` nieznane raportowi
  ani BOM. `symbol_clean` trzyma segment +lokalizacji (+BL1-X186) — zawsze
  przez `zs.clean_device_code` przed porównaniem. Pomija RT/SP/W/U/FH/FR/ZW,
  numery przewodów kolorowych (OG193A, P13RD), AWG*, i dopisuje `near`
  (ten sam rdzeń litera+cyfry albo prefiks ≥4 znaki).
- **Łatki**: `zuken_data_patches` (TABELA SYSTEMOWA — w migracjach,
  `uid` UUID stabilny między bazami; eksport nie polega na id). Rodzaje
  (`PATCH_KINDS`, walidacja w `_clean_patch_payload`):
  'connection' (szpilka/pin → `_wire_adjacency(with_patches)`, hop `patched`),
  'fuse_holder' (-F→-FH → `holders`), 'busbar' (members fuse:pin:term →
  syntetyczny `bars` z węzłem -ZW/sibs, hop 'busbar' z 🩹), 'box_fuse'
  (box_name+cell → nakładka READ-TIME w `get_ps_fuses`, NIE do
  `_populate_ps_box_fuses` — ta regeneruje tabelę przy imporcie),
  'device_location' (device→full_code =SYS+LOC-… → alias przy rozwiązywaniu
  zapytania w `_trace_circuit_impl`), 'device_link' (device + pin_a/pin_b →
  wewnętrzna krawędź `_internal='switch'` w `_circuit_extend_adjacency` —
  przejście przez aparat spoza raportu: hebel/stycznik/blok, np. A359
  ML-RBS A↔B; rysunek ⏻, `js.zuken.viaSwitch`), 'power_rail' (members
  dev:pin ≥2 → pełna siatka krawędzi `_internal='busbar'` między zaciskami
  wspólnej szyny śrubowej — Carnation: RT123+RT132 / RT133+…; członkowie
  nie-RT dostają pass przez `internal_devs`). Uwaga: tor przechodzi przez
  aparat dopiero po `device_link` — same łatki 'connection' do jego pinów
  kończą ścieżkę (BFS staje na urządzeniu nie-'pass'). Szynę można
  przybliżyć samymi 'connection' między -RT (RT są przechodnie), ale bez
  węzła szyny w diagramie. `_diagnose_defect_impl` czyta SUROWE
  `zuken_connections` — łatki nie wchodzą do grupowania obwodów w
  diagnozie (znany limit). `_ps_fuse_rails` to WRAPPER:
  `_ps_fuse_rails_raw` (geometria, cache) + nakładki łatek — wykrywacze
  wołają `_ps_fuse_rails_raw` (surowe!). `_mark_redundant_patches` przy
  skanie sprawdza wszystkie rodzaje (connection: wiersz w raporcie;
  fuse_holder/busbar: urządzenia połączone w surowym grafie; box_fuse:
  wiersz w `zuken_ps_box_fuses`; device_location: BOM ma już pełny kod).
  apply_suggestion obsługuje kind translation/alias/patch; kind 'pinout'/
  'photos'/'text' nie mają apply — UI pokazuje własny przycisk. Zakładka
  Łatki ma formularz ręcznego dodania (admin, `auditPatchNew`).
- **Role i flaga dewelopera**: role to `admin`/`technik`/`podglad` (bez
  zmian — wszystkie checki `role=='admin'` nietknięte). `users.is_dev` =
  flaga nad rolą admina: dev dostaje osobne menu „Deweloper"
  (`data-view="developer"`, nav gated przez `_isDev()`) z narzędziami
  destrukcyjnymi (dziś: Skan od zera, selfcheck). Nadanie: `DEV_USERS`
  w config.json (bootstrap przy init_db, po username) albo checkbox w
  edycji użytkownika — tylko dev widzi pole i może zapisać (403 inaczej);
  dev nie może zdjąć flagi sam z siebie. Backend: `_is_dev(u)`, kom.
  `devRequired`; scan z `reset:true` wymaga deva.
- **Dev-reset**: `reset_issues(ps, detectors=None)` usuwa auto-zgłoszenia
  PS (detector IS NOT NULL, wraz z `rejected`/fingerprintami) + ich pliki;
  ręczne zgłoszenia i łatki zostają. `run_scan`/`start_scan` z `reset=True`
  → skan „jak pierwszy raz". Z UI: menu „Deweloper" (is_dev) → „Skan od
  zera". Z API: `POST /api/zuken/audit/scan` z `{"reset": true}` (dev).
  Z terminala: `python -c "import schema_audit;
  print(schema_audit.reset_issues('PS011871'))"`.
- **Observe**: `POST /api/zuken/audit/observe` (zalogowany) → D14a:
  `connFaceLayout()==null` i brak USER pinoutu → `report_pinout_missing`
  (fingerprint `D14|OBS|<art>`, raz na sesję per artykuł, pusty ps pomija).
- **Eksport**: `export_batch` → `DATA_DIR/exports/audit/<PS>_<stamp>_<bid>/`:
  XLSX (własny writer sharedStrings — openpyxl NIE jest zależnością),
  PNG wycinki, szkic .eml (X-Unsent:1). Status→'sent', `zuken_issue_batches`.
- Admin = `_audit_admin()`; wykrywacze liczą zawsze na SUROWYCH danych
  (bez łatek) — łatki to osobna warstwa naprawcza.
- Testy na KOPII bazy: `RU_DATA_DIR` na katalog z kopią db (uwaga: `/tmp`
  w Git Bash ≠ `C:\tmp` — WinPython widzi `C:\tmp`, Git Bash AppData\Temp).

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

## Diagram obwodu głównego — specyfikacja (ustalona z Adamem)

Tor główny (`cp.main_path`, `circuitSvgForLoad` z `srcEnd`/`contPath`) rysujemy
jako schemat ideowy BEZ ramek wokół symboli (skrzynki zostają tylko dla złączy
wielopinowych):
- **Bezpiecznik** (`withFuses`): topik jak w E3 + `F17 250A MEGA` (prąd i typ z
  `zuken_ps_fuses.fuse_type`) + opis funkcji z sąsiednich RT (np. AUX GŁÓWNY
  BEZPIECZNIK) tylko przy symbolu; piny oprawki U8:1/U8:2 przy końcówkach.
- **Akumulator** (`withBatt`): para koniec + terminal RT w jednym symbolu
  płytek, biegun + zwrócony do obwodu, zacisk przy swojej płytce.
- **Przekaźnik** (`withRelays`): styk (piny 14/12 lub 30/87) + cewka 86/85
  obok połączona linią przerywaną; dioda/rezystor/⏱ tylko gdy BOM je zna
  (`relay_coils[*].suppression/timed`); klik w cewkę przewija do `#coil-*`.
- **Zaciski RT/U** na torze: małe kółko + nazwa; opisy zawierające
  bezpiecznik/fuse/Sicherung nie są powtarzane przy RT.
- **Etykieta przewodu**: tylko numer, kolor, przekrój, długość (bez nazw
  sygnałów E3 — idą do tooltipu); przewód z zapytania wyróżniony tłem.
- **Zapytany element**: półprzezroczyste podświetlenie tła, nie ramka.
- Pasek postępu: `zukenLoadingHtml` (+ placeholder `#zuken-circuit-loading`).

## Asystent obwodów: faza 2 i 3 (gotowe)

- Backend `trace_circuit`: każdy koniec ma `cls` (`_end_cls`: feed/load/
  ground/coil/branch); `main_candidates` = do 6 par kotwic (max 2 na rodzaj:
  `bridge` +→+, `power` +→−, `feed` zasilanie→urządzenie, `signal`),
  pierwszy = `main_path`. Para kotwic: biegun baterii `+` (`batt`) ma rangę 0,
  szpilka urządzenia 1; remis rozstrzyga najkrótsza trasa. Odbiornik z
  zasilaniem i masą na różnych pinach dostaje syntetyczny przeskok
  `internal='device'` (frontend zwija go w jeden węzeł z dwoma pinami).
  Kandydaci niosą tylko indeksy końców (`li/pi/ei`) + `hops` — końce są w `loads`.
- Frontend: `circuitMainSelected/circuitMainBlockHtml/circuitSelectMain`
  (`cp._sel` = wybrany kandydat), chipy „Inne obwody przez ten punkt",
  odnogi grupowane nagłówkami klas (ZASILANIE/ODBIORNIKI/MASA/…),
  wachlarze z różnych węzłów nie nachodzą na siebie, sekcja „Obwód sterowania"
  (cewki przekaźników z toru) w `<details>`, klik w cewkę = nakładka
  (`circuitShowCoil`; globalny handler `[data-ent-q]` w fazie capture
  przechwytuje kliknięcia — cewka musi leżeć POZA grupą ent-link).
- Testy: `RU_DATA_DIR=... python test_circuit_main_path.py` (394, K1, F9,
  F11, X164 +→−, X303, emergency start, F27/K4 na Walii, node --check frontu,
  i18n); bez bazy projektów testy danych dają SKIP. UI w prawdziwej
  przeglądarce: `tools/dev_server_5099.py` + `tools/cdp_ui_check.js`.
- Pułapka narzędziowa: heredoc w powłoce zjada `\` i potrafi ciąć długie
  bloki — większe wstawki robić narzędziem edit/write, nie `cat <<EOF`.

