"""
zuken_service.py - Moduł integracji danych Zuken E3.series oraz asystenta diagnostycznego.
Działa w 100% lokalnie (offline) na bazie SQLite i plikach XLSX z katalogu Baza wiedzy.
Obsługuje wiele projektów PS (np. EoE, LAS) oraz wersjonowanie/rewizje wiązek w ramach serii.
"""

import os
import re
import io
import csv
import json
import sqlite3
import zipfile
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from collections import defaultdict


try:
    import pypdf
except ImportError:
    pypdf = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BAZA_WIEDZY_DIR = os.path.join(BASE_DIR, "Baza wiedzy")
BOM_IMAGES_DIR = os.path.join(BAZA_WIEDZY_DIR, "zdjecia_komponentow")
os.makedirs(BOM_IMAGES_DIR, exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, "rejestr_usterek.db")


# ═══════════════════════════════════════════════════════════════════
# WBUDOWANY SŁOWNIK SKRÓTÓW I OZNACZEŃ (DIN EN 81346 / E3.SERIES)
# ═══════════════════════════════════════════════════════════════════
DEFAULT_GLOSSARY = [
    # Systemy (=)
    ("=CAB", "System", "Kabina pojazdu bazowego (szoferka / Fahrerhaus)", "Vehicle base cab"),
    ("=BOX", "System", "Zabudowa kontenerowa medyczna (Patientensalon)", "Ambulance box container"),
    ("=ACETECH", "System", "System sterowania i telematyki Acetech", "Acetech control & telematics"),
    ("=CHA", "System", "Podwozie i rama pojazdu (Chassis)", "Vehicle chassis"),
    
    # Lokalizacje (+)
    ("+PS", "Lokalizacja", "Przedział chorych / medyczny (Patientensalon)", "Patient saloon / medical compartment"),
    ("+MID", "Lokalizacja", "Moduł interkomu medycznego (Medical Intercom Device)", "Medical intercom device / speaker area"),
    ("+BOM", "Lokalizacja", "Panel dachowy / podsufitka (Bedienobermodul)", "Roof control module / ceiling console"),
    ("+BPRT", "Lokalizacja", "Drzwi prawe pasażera / personelu (Beifahrertür Rechts)", "Passenger / attendant side door right"),
    ("+BPLT", "Lokalizacja", "Drzwi lewe personelu (Begleitertür Links)", "Attendant side door left"),
    ("+TW", "Lokalizacja", "Ściana grodziowa (Trennwand)", "Bulkhead partition wall"),
    ("+TWL", "Lokalizacja", "Ściana grodziowa lewa (Trennwand Links)", "Bulkhead wall left"),
    ("+TWR", "Lokalizacja", "Ściana grodziowa prawa (Trennwand Rechts)", "Bulkhead wall right"),
    ("+TWM", "Lokalizacja", "Ściana grodziowa środek (Trennwand Mitte)", "Bulkhead wall middle"),
    ("+BSI", "Lokalizacja", "Złącze zabudowy / podstawa fotela", "Bodybuilder seat interface"),
    ("+RO3", "Lokalizacja", "Dach / podsufitka zabudowy (Roof)", "Ceiling / roof area"),
    ("+RO", "Lokalizacja", "Dach / podsufitka", "Roof area"),
    ("+MIK", "Lokalizacja", "Konsola środkowa / mikrofon (Mittelkonsole)", "Center console / microphone"),
    ("+ARL", "Lokalizacja", "Narożnik tylny lewy / oświetlenie tył lewy", "Rear corner left"),
    ("+ARR", "Lokalizacja", "Narożnik tylny prawy / oświetlenie tył prawy", "Rear corner right"),
    ("+ARM", "Lokalizacja", "Tył pojazdu środek", "Rear middle area"),
    ("+DPR", "Lokalizacja", "Drzwi boczne przesuwne prawe (Door Passenger Right)", "Side sliding door right"),
    ("+DPL", "Lokalizacja", "Drzwi boczne lewe", "Side door left"),
    ("+DRR", "Lokalizacja", "Drzwi tylne prawe (Door Rear Right)", "Rear door right"),
    ("+DRL", "Lokalizacja", "Drzwi tylne lewe (Door Rear Left)", "Rear door left"),
    ("+GND", "Lokalizacja", "Punkty masowe / magistrala masy (Ground)", "Ground / chassis earth points"),
    ("+BL1", "Lokalizacja", "Główny blok rozdzielczy zasilania 1", "Main power distribution block 1"),
    ("+BL2", "Lokalizacja", "Główny blok rozdzielczy zasilania 2", "Main power distribution block 2"),
    ("+REL", "Lokalizacja", "Panel przekaźników", "Relay board panel"),
    ("+NAK", "Lokalizacja", "Panel dodatkowy / konsola", "Auxiliary console"),

    # Urządzenia / Aparaty (-) wg DIN EN 81346
    ("-A", "Aparat", "Moduł elektroniczny / sterownik / urządzenie (np. Carnation, Ortus, KFG)", "Electronic module / ECU"),
    ("-X", "Aparat", "Złącze / wtyczka wiązki przewodów (Stecker)", "Connector / plug"),
    ("-FH", "Aparat", "Oprawka bezpiecznika (Fuse Holder)", "Fuse holder"),
    ("-F", "Aparat", "Bezpiecznik (Sicherung)", "Fuse"),
    ("-RT", "Aparat", "Przekaźnik (Relay)", "Relay"),
    ("-K", "Aparat", "Stycznik / przekaźnik mocy", "Power relay / contactor"),
    ("-S", "Aparat", "Włącznik / przycisk sterujący (Schalter)", "Switch / pushbutton"),
    ("-H", "Aparat", "Sygnalizator świetlny lub dźwiękowy", "Indicator light / optical signaling"),
    ("-E", "Aparat", "Urządzenie oświetleniowe / lampa (Beleuchtung, np. Whelen, AMX)", "Lighting unit / lamp"),
    ("-M", "Aparat", "Silnik elektryczny / wentylator / pompa (Motor)", "Electric motor / fan / pump"),
    ("-B", "Aparat", "Czujnik / przetwornik (Sensor)", "Sensor / transducer"),
    ("-W", "Aparat", "Wiązka przewodów / kabel zewnętrzny (Kabel)", "Wiring harness / external cable"),

    # Sygnały i linie audio / sterowania
    ("LT", "Sygnał", "Linia głośnika / audio (Lautsprecher)", "Speaker / audio line"),
    ("LT-CAB", "Sygnał", "Głośnik w kabinie kierowcy (Lautsprecher Cabine)", "Driver cab speaker line"),
    ("LT SALOON", "Sygnał", "Głośnik w przedziale medycznym (Lautsprecher Saloon)", "Patient saloon speaker line"),
    ("LT FH", "Sygnał", "Głośnik w szoferce (Lautsprecher Fahrerhaus)", "Driver cab speaker"),
    ("LT PR", "Sygnał", "Głośnik w przedziale chorych (Lautsprecher Patientenraum)", "Patient saloon speaker")
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_zuken_tables():
    """Inicjalizuje tabele dla bazy Zuken i słownika skrótów."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            project_name TEXT,
            client TEXT,
            ps_codes TEXT,
            revision_date TEXT,
            revision_name TEXT,
            total_connections INTEGER DEFAULT 0,
            imported_at TEXT,
            is_active INTEGER DEFAULT 1,
            notes TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            signal TEXT,
            from_device TEXT,
            from_component TEXT,
            from_pin TEXT,
            to_device TEXT,
            to_component TEXT,
            to_pin TEXT,
            wire_number TEXT,
            wire_type TEXT,
            wire_color TEXT,
            cross_section TEXT,
            cable_name TEXT,
            length TEXT,
            FOREIGN KEY (project_id) REFERENCES zuken_projects (id) ON DELETE CASCADE
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_signal ON zuken_connections (signal);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_from_dev ON zuken_connections (from_device);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_to_dev ON zuken_connections (to_device);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_proj ON zuken_connections (project_id);")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_glossary (
            prefix TEXT PRIMARY KEY,
            category TEXT,
            desc_pl TEXT,
            desc_en TEXT
        );
    """)

    # Tabele dla wektorowych schematów PDF wyeksportowanych z Zuken E3
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_pdf_schematics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            filepath TEXT,
            project_name TEXT,
            ps_code TEXT,
            revision_date TEXT,
            revision_name TEXT,
            total_pages INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_mtime REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            indexed_at TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_pdf_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schematic_id INTEGER,
            page_number INTEGER,
            sheet_number TEXT,
            sheet_title TEXT,
            section_code TEXT,
            raw_text TEXT,
            FOREIGN KEY (schematic_id) REFERENCES zuken_pdf_schematics (id) ON DELETE CASCADE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_pdf_symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schematic_id INTEGER,
            sheet_id INTEGER,
            page_number INTEGER,
            symbol_type TEXT,
            symbol_name TEXT,
            symbol_clean TEXT,
            context_info TEXT,
            FOREIGN KEY (schematic_id) REFERENCES zuken_pdf_schematics (id) ON DELETE CASCADE,
            FOREIGN KEY (sheet_id) REFERENCES zuken_pdf_sheets (id) ON DELETE CASCADE
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_pdf_sym_clean ON zuken_pdf_symbols (symbol_clean);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_pdf_sym_name ON zuken_pdf_symbols (symbol_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_pdf_sym_sch ON zuken_pdf_symbols (schematic_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_pdf_sheets_sch ON zuken_pdf_sheets (schematic_id, page_number);")

    # Tabele dla zestawienia materiałowego BOM (Bill of Material) i artykułów
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_bom_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            article_number TEXT,
            supplier TEXT,
            description TEXT,
            amount INTEGER DEFAULT 1,
            category TEXT,
            datasheet_url TEXT,
            local_image TEXT,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES zuken_projects (id) ON DELETE CASCADE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_bom_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bom_item_id INTEGER,
            device_code TEXT,
            device_clean TEXT,
            function TEXT,
            FOREIGN KEY (bom_item_id) REFERENCES zuken_bom_items (id) ON DELETE CASCADE
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_art ON zuken_bom_items (article_number);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_sup ON zuken_bom_items (supplier);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_cat ON zuken_bom_items (category);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_proj ON zuken_bom_items (project_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_dev_code ON zuken_bom_devices (device_code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_dev_clean ON zuken_bom_devices (device_clean);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_bom_dev_item ON zuken_bom_devices (bom_item_id);")

    # Tabele dla zestawień technicznych per projekt PS (złącza z pinoutem, bezpieczniki, przekaźniki)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_ps_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT UNIQUE,
            project_name TEXT,
            client TEXT,
            connectors_count INTEGER DEFAULT 0,
            fuses_count INTEGER DEFAULT 0,
            relays_count INTEGER DEFAULT 0,
            generated_at TEXT,
            source_files TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_ps_connectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT,
            device_code TEXT,
            device_clean TEXT,
            system TEXT,
            location TEXT,
            system_desc TEXT,
            location_desc TEXT,
            article_number TEXT,
            supplier TEXT,
            description TEXT,
            image_url TEXT,
            pin_count INTEGER DEFAULT 0,
            pins_json TEXT,
            FOREIGN KEY (ps_code) REFERENCES zuken_ps_summaries (ps_code) ON DELETE CASCADE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_ps_fuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT,
            device_code TEXT,
            device_clean TEXT,
            rating TEXT,
            fuse_type TEXT,
            article_number TEXT,
            supplier TEXT,
            description TEXT,
            holder_code TEXT,
            box_code TEXT,
            system TEXT,
            location TEXT,
            circuits TEXT,
            details_json TEXT,
            FOREIGN KEY (ps_code) REFERENCES zuken_ps_summaries (ps_code) ON DELETE CASCADE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_ps_relays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT,
            device_code TEXT,
            device_clean TEXT,
            function TEXT,
            relay_type TEXT,
            article_number TEXT,
            supplier TEXT,
            description TEXT,
            socket_code TEXT,
            system TEXT,
            location TEXT,
            contacts_json TEXT,
            FOREIGN KEY (ps_code) REFERENCES zuken_ps_summaries (ps_code) ON DELETE CASCADE
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_ps_conn_ps ON zuken_ps_connectors (ps_code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_ps_conn_dev ON zuken_ps_connectors (device_clean);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_ps_fuse_ps ON zuken_ps_fuses (ps_code);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_ps_relay_ps ON zuken_ps_relays (ps_code);")


    # Wypełnij / zaktualizuj domyślny słownik skrótów
    cur.executemany("""
        INSERT INTO zuken_glossary (prefix, category, desc_pl, desc_en)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(prefix) DO UPDATE SET
            category = excluded.category,
            desc_pl = excluded.desc_pl,
            desc_en = excluded.desc_en;
    """, DEFAULT_GLOSSARY)

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# PARSER PLIKÓW XLSX Z ZUKEN E3 (BEZ ZEWNĘTRZNYCH ZALEŻNOŚCI)
# ═══════════════════════════════════════════════════════════════════
def _clean_val(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s.startswith(":"):
        s = s[1:].strip()
    return s


def parse_xlsx_fast(filepath):
    """
    Szybki parser pliku XLSX bez konieczności instalowania openpyxl/pandas.
    Korzysta z wbudowanego zipfile i xml.etree.
    Zwraca (metadata, list_of_rows).
    """
    with zipfile.ZipFile(filepath, "r") as z:
        sst = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in tree.findall("m:si", ns):
                text = "".join([t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")])
                sst.append(text)

        # Znajdź arkusz roboczy
        sheet_file = "xl/worksheets/sheet1.xml"
        if sheet_file not in z.namelist():
            for f in z.namelist():
                if f.startswith("xl/worksheets/sheet") and f.endswith(".xml"):
                    sheet_file = f
                    break

        tree = ET.fromstring(z.read(sheet_file))
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows_data = []

        for r in tree.findall("m:sheetData/m:row", ns):
            cells = {}
            for c in r.findall("m:c", ns):
                ref = c.get("r", "")
                col = "".join(filter(str.isalpha, ref))
                t = c.get("t")
                v = c.find("m:v", ns)
                val = v.text if v is not None else ""
                if t == "s" and val.isdigit():
                    idx = int(val)
                    val = sst[idx] if idx < len(sst) else ""
                cells[col] = val
            if any(cells.values()):
                rows_data.append(cells)

    return rows_data


def extract_project_info_from_filename(filename, raw_rows):
    """Wyodrębnia nazwę projektu, klienta, rewizję i powiązane numery PS."""
    fn_lower = filename.lower()
    
    # Rozpoznanie klienta
    client = "Inny"
    ps_codes = ""
    if "eoe" in fn_lower:
        client = "EOE - East of England Ambulance Service"
        ps_codes = "PS011871" # Domyślny PS dla aktualnej serii EoE
    elif "las" in fn_lower:
        client = "LAS - London Ambulance Service"
    elif "was" in fn_lower:
        client = "WAS Standard"

    # Wykrywanie nazwy projektu i rewizji z wierszy nagłówkowych
    proj_name = os.path.splitext(filename)[0]
    rev_date = ""
    rev_name = ""

    for r in raw_rows[:8]:
        for col, val in r.items():
            val_s = str(val).strip()
            if "project name:" in val_s.lower() or "connection list:" in val_s.lower():
                # w następnych kolumnach jest nazwa
                for next_col in ["B", "C", "D"]:
                    if r.get(next_col):
                        proj_name = r[next_col].strip()
                        break
            if "creation date:" in val_s.lower():
                for next_col in ["B", "C", "D"]:
                    if r.get(next_col):
                        rev_date = r[next_col].strip()
                        break

    # Próba wyciągnięcia daty z nazwy pliku jeśli brak
    date_match = re.search(r"(\d{1,2}[\._]\d{1,2}[\._]\d{4})", filename)
    if date_match and not rev_date:
        rev_date = date_match.group(1).replace("_", ".")

    # Konwersja daty na format ISO (YYYY-MM-DD) do pewnego sortowania
    iso_date = ""
    if rev_date:
        dm = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", rev_date)
        if dm:
            d, m, y = dm.groups()
            iso_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    if not iso_date:
        iso_date = rev_date

    # Nazwa rewizji (np. "poprawka drzwi" lub "Wersja bazowa")
    if "poprawka_drzwi" in fn_lower or "drzwi" in fn_lower:
        rev_name = f"Poprawka instalacji drzwi ({rev_date or '2026'})"
    elif "2025" in filename:
        rev_name = f"Wersja bazowa serii ({rev_date or '2025'})"
    else:
        rev_name = f"Rewizja {rev_date}" if rev_date else "Wersja schematu"

    # Wykrywanie kodu PS z nazwy pliku lub folderu
    ps_match = re.search(r"(PS\d{4,})", filename, re.IGNORECASE)
    if ps_match and not ps_codes:
        ps_codes = ps_match.group(1).upper()

    return {
        "project_name": proj_name,
        "client": client,
        "ps_codes": ps_codes,
        "revision_date": iso_date,
        "revision_name": rev_name
    }


def import_zuken_xlsx(filepath, ps_code=None):
    """Importuje plik XLSX z listy połączeń Zuken E3 do bazy SQLite."""
    filename = os.path.basename(filepath)
    raw_rows = parse_xlsx_fast(filepath)
    if not raw_rows:
        return 0, "Plik jest pusty lub niepoprawny."

    meta = extract_project_info_from_filename(filename, raw_rows)
    if ps_code:
        meta["ps_codes"] = ps_code


    # Wykrywanie wiersza nagłówkowego
    header_idx = -1
    col_map = {}
    is_format_a = False  # format z kolumną 'Signal' na początku
    is_format_b = False  # format z 'From Device designation' na początku

    for idx, r in enumerate(raw_rows[:15]):
        row_vals = {k: str(v).strip().lower() for k, v in r.items()}
        joined = " ".join(row_vals.values())
        if "signal" in joined and "device" in joined:
            header_idx = idx
            is_format_a = True
            break
        elif "device designation" in joined:
            header_idx = idx
            is_format_b = True
            break

    if header_idx == -1:
        # Domyślnie załóżmy wiersz 4 lub 6
        header_idx = 4
        is_format_a = True

    header_row = raw_rows[header_idx]

    conn = get_db()
    cur = conn.cursor()

    # Zapisz lub zaktualizuj wpis projektu
    cur.execute("""
        INSERT INTO zuken_projects (filename, project_name, client, ps_codes, revision_date, revision_name, imported_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            project_name=excluded.project_name,
            client=excluded.client,
            revision_date=excluded.revision_date,
            revision_name=excluded.revision_name,
            imported_at=excluded.imported_at;
    """, (
        filename,
        meta["project_name"],
        meta["client"],
        meta["ps_codes"],
        meta["revision_date"],
        meta["revision_name"],
        datetime.now().isoformat(),
        f"Automatyczny import z {filename}"
    ))
    conn.commit()

    cur.execute("SELECT id FROM zuken_projects WHERE filename = ?", (filename,))
    project_id = cur.fetchone()[0]

    # Usuń stare połączenia dla tego projektu
    cur.execute("DELETE FROM zuken_connections WHERE project_id = ?", (project_id,))

    connections_to_insert = []

    # Parsowanie poszczególnych formatów Zukena
    for r in raw_rows[header_idx + 1:]:
        # Sprawdź czy to nie wiersz pusty
        if not any(r.values()):
            continue

        if is_format_a:
            # Format: A=Signal, B=Device From, C=Pin From, D=Device To, E=Pin To, F=Wire Num, G=Wire Type, H=Colour, I=Cross-sec, J=Cable, K=Length
            sig = _clean_val(r.get("A"))
            from_dev = _clean_val(r.get("B"))
            from_pin = _clean_val(r.get("C"))
            to_dev = _clean_val(r.get("D"))
            to_pin = _clean_val(r.get("E"))
            w_num = _clean_val(r.get("F"))
            w_type = _clean_val(r.get("G"))
            w_col = _clean_val(r.get("H"))
            w_cross = _clean_val(r.get("I"))
            w_cable = _clean_val(r.get("J"))
            w_len = _clean_val(r.get("K"))
            from_comp = ""
            to_comp = ""
        else:
            # Format: A=Dev From, C=Comp From, D=Pin From, E=Dev To, G=Comp To, H=Pin To, I=Wire/Signal Name, L=Type, M=Colour, N=Cross-sec, O=Cable
            from_dev = _clean_val(r.get("A"))
            from_comp = _clean_val(r.get("C"))
            from_pin = _clean_val(r.get("D"))
            to_dev = _clean_val(r.get("E"))
            to_comp = _clean_val(r.get("G"))
            to_pin = _clean_val(r.get("H"))
            sig = _clean_val(r.get("I"))
            w_type = _clean_val(r.get("L"))
            w_col = _clean_val(r.get("M"))
            w_cross = _clean_val(r.get("N"))
            w_cable = _clean_val(r.get("O"))
            w_num = ""
            w_len = _clean_val(r.get("Q"))

        # Ignoruj wiersze nagłówkowe powtórzone w arkuszu
        if "device" in from_dev.lower() or "signal" in sig.lower():
            continue

        if from_dev or to_dev or sig:
            connections_to_insert.append((
                project_id, sig, from_dev, from_comp, from_pin,
                to_dev, to_comp, to_pin, w_num, w_type, w_col,
                w_cross, w_cable, w_len
            ))

    if connections_to_insert:
        cur.executemany("""
            INSERT INTO zuken_connections (
                project_id, signal, from_device, from_component, from_pin,
                to_device, to_component, to_pin, wire_number, wire_type,
                wire_color, cross_section, cable_name, length
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, connections_to_insert)

    cur.execute("UPDATE zuken_projects SET total_connections = ? WHERE id = ?", (len(connections_to_insert), project_id))
    conn.commit()
    conn.close()

    return len(connections_to_insert), f"Zaimportowano {len(connections_to_insert)} połączeń."


# ═══════════════════════════════════════════════════════════════════
# MODUŁ BOM (BILL OF MATERIAL) - ARTYKUŁY, ZŁĄCZA, DOSTAWCY, ZDJĘCIA
# ═══════════════════════════════════════════════════════════════════

def clean_device_code(code):
    """
    Czyści pełny kod aparatu Zukena (np. '=BOX+TWL-X52' lub '-X434') do formy bazowej (np. 'X52', 'X434', 'FH49').
    """
    if not code:
        return ""
    c = str(code).strip()
    if "-" in c:
        c = c.split("-")[-1]
    c = re.sub(r"^[=+\-:]+", "", c)
    c = c.rstrip("'\"").strip()
    return c


def categorize_bom_item(desc, code, supplier):
    """Klasyfikuje artykuł z BOM do czytelnej kategorii komponentów."""
    d = (desc or "").lower()
    s = (supplier or "").lower()
    c = (code or "").lower()

    if any(k in d for k in ["fuse box", "fuse holder", "gniazdo bezpiecznika", "oprawka bezpiecznika"]):
        return "Gniazdo / Skrzynka bezpieczników"
    elif any(k in d for k in ["housing", "obudowa", "złącze", "zlacze", "connector", "tab header", "mate-n-lok", "fastin"]):
        return "Złącze / Obudowa"
    elif any(k in d for k in ["terminal", "pin", "konektor", "styk", "contact", "receptacle wire"]):
        return "Pin / Terminal"
    elif any(k in d for k in ["receptacle", "plug"]):
        return "Złącze / Obudowa"
    elif "gniazdo" in d or "socket" in d:
        return "Gniazdo zasilające"
    elif "fuse" in d or "bezpiecznik" in d:
        return "Bezpiecznik"
    elif any(k in d for k in ["relay", "przekaźnik", "przekaznik", "stycznik"]):
        return "Przekaźnik"
    elif any(k in d for k in ["lampa", "light", "led", "blitzer", "scene", "beacon", "warning", "ostrzegawcza"]):
        return "Oświetlenie / Sygnalizacja"
    elif any(k in d for k in ["charger", "ładowarka", "ladowarka", "inverter", "przetwornica", "distribution block", "blok"]):
        return "Zasilanie / Rozdział mocy"
    elif any(k in d for k in ["switch", "przełącznik", "przelacznik", "button", "przycisk"]):
        return "Włącznik / Przełącznik"
    elif any(k in d for k in ["sensor", "czujnik", "camera", "kamera", "recorder", "rejestrator", "mikrofon", "mic", "radio", "acetech", "ortus", "satel", "kfg", "mdvs", "syrena", "siren"]):
        return "Moduł / Urządzenie"
    elif any(k in d for k in ["uchwyt", "wspornik", "mocowanie", "klips", "bracket", "cover", "pokrywa"]):
        return "Element montażowy"
    return "Inne komponenty"


def sanitize_article_code(code):
    """Zwraca bezpieczną nazwę pliku dla danego kodu artykułu."""
    if not code:
        return ""
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', str(code).strip())
    return sanitized


def find_local_component_image(article_number):
    """
    Sprawdza, czy w katalogu Baza wiedzy/zdjecia_komponentow/ istnieje zdjęcie dla artykułu.
    Zwraca ścieżkę względną URL (/api/zuken/bom/image/<filename>) lub None.
    """
    if not article_number:
        return None
    sanitized = sanitize_article_code(article_number)
    if not os.path.exists(BOM_IMAGES_DIR):
        return None

    # Przeszukaj popularne rozszerzenia
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
        candidate = f"{sanitized}{ext}"
        full_path = os.path.join(BOM_IMAGES_DIR, candidate)
        if os.path.isfile(full_path):
            return f"/api/zuken/bom/image/{candidate}"

    # Sprawdź też dokładną nazwę w katalogu (case-insensitive)
    try:
        for fname in os.listdir(BOM_IMAGES_DIR):
            name_without_ext, ext = os.path.splitext(fname)
            if name_without_ext.lower() == sanitized.lower() and ext.lower() in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
                return f"/api/zuken/bom/image/{fname}"
    except Exception:
        pass

    return None


def get_supplier_links(article_number, supplier=""):
    """
    Generuje bezpośrednie odnośniki do kart produktów u dostawców i dystrybutorów.
    """
    code = (article_number or "").strip()
    sup = (supplier or "").strip()
    sup_upper = sup.upper()

    links = []

    # 1. Producent (bezpośrednie karty katalogowe)
    if any(k in sup_upper for k in ["TE", "AMP", "DEUTSCH", "TYCO"]):
        links.append({
            "name": "TE Connectivity",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.te.com/usa-en/product-{code}.html",
            "tooltip": "Karta produktu TE.com (rysunki 2D/3D, specyfikacja i pinout)"
        })
    elif "MOLEX" in sup_upper:
        links.append({
            "name": "Molex",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.molex.com/en-us/search?q={urllib.parse.quote_plus(code)}",
            "tooltip": "Karta produktu na Molex.com"
        })
    elif "LITTELFUSE" in sup_upper:
        links.append({
            "name": "Littelfuse",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.littelfuse.com/search-results.aspx?q={urllib.parse.quote_plus(code)}",
            "tooltip": "Szukaj produktu na Littelfuse.com"
        })
    elif "ANDERSON" in sup_upper:
        links.append({
            "name": "Anderson Power",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.andersonpower.com/us/en/search.html?q={urllib.parse.quote_plus(code)}",
            "tooltip": "Szukaj na AndersonPower.com"
        })
    elif "MTA" in sup_upper:
        links.append({
            "name": "MTA Automotive",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.google.com/search?q=MTA+automotive+{urllib.parse.quote_plus(code)}",
            "tooltip": "Szukaj katalogu MTA Automotive"
        })
    elif "VICTRON" in sup_upper:
        links.append({
            "name": "Victron Energy",
            "type": "manufacturer",
            "icon": "🏭",
            "url": f"https://www.victronenergy.pl/search?q={urllib.parse.quote_plus(code)}",
            "tooltip": "Katalog Victron Energy"
        })

    # 2. Dystrybutorzy z natychmiastowym podglądem kart PDF, zdjęć i magazynu (Polska/Europa)
    links.append({
        "name": "TME.eu",
        "type": "distributor",
        "icon": "🛒",
        "url": f"https://www.tme.eu/pl/katalog/?search={urllib.parse.quote_plus(code)}",
        "tooltip": "Katalog TME.eu (zdjęcia, karty PDF, dostępność)"
    })
    links.append({
        "name": "Mouser",
        "type": "distributor",
        "icon": "🔍",
        "url": f"https://www.mouser.pl/c/?q={urllib.parse.quote_plus(code)}",
        "tooltip": "Mouser Electronics (karty katalogowe komponentów)"
    })

    # 3. Google Grafika 1-kliknięciem
    search_q = f"{sup} {code}".strip() if sup and sup != "Nieznany" else f"connector {code}"
    search_enc = urllib.parse.quote_plus(search_q)
    links.append({
        "name": "Google Grafika",
        "type": "images",
        "icon": "🖼️",
        "url": f"https://www.google.com/search?tbm=isch&q={search_enc}",
        "tooltip": "Otwórz zdjęcia tego artykułu w Google Grafika (możesz skopiować i wkleić Ctrl+V)"
    })

    return links


def import_zuken_bom_xlsx(filepath, ps_code=None):
    """
    Importuje zestawienie materiałowe BOM (Device-/Quantity-Bill of material) z Zukena do bazy SQLite.
    Zapisuje artykuły, dostawców, ilości oraz powiązania z aparatami (=BOX+... / -X...).
    """
    filename = os.path.basename(filepath)
    raw_rows = parse_xlsx_fast(filepath)
    if not raw_rows:
        return 0, 0, "Plik BOM jest pusty lub niepoprawny."

    meta = extract_project_info_from_filename(filename, raw_rows)
    if ps_code:
        meta["ps_codes"] = ps_code

    conn = get_db()
    cur = conn.cursor()

    # Zapisz lub pobierz projekt
    cur.execute("""
        INSERT INTO zuken_projects (filename, project_name, client, ps_codes, revision_date, revision_name, imported_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(filename) DO UPDATE SET
            project_name=excluded.project_name,
            client=excluded.client,
            revision_date=excluded.revision_date,
            revision_name=excluded.revision_name,
            imported_at=excluded.imported_at;
    """, (
        filename,
        meta["project_name"],
        meta["client"],
        meta["ps_codes"],
        meta["revision_date"],
        meta["revision_name"],
        datetime.now().isoformat(),
        f"Automatyczny import raportu BOM z {filename}"
    ))
    conn.commit()

    cur.execute("SELECT id FROM zuken_projects WHERE filename = ?", (filename,))
    project_id = cur.fetchone()[0]

    # Usuń poprzednie wpisy BOM dla tego projektu
    cur.execute("DELETE FROM zuken_bom_items WHERE project_id = ?", (project_id,))

    parsed_articles = []
    current_art = None

    start_row = 4
    for idx, r in enumerate(raw_rows[:10]):
        if "device designation" in str(r.get("B", "")).lower() or "function" in str(r.get("D", "")).lower():
            start_row = idx + 1
            break

    for r in raw_rows[start_row:]:
        amt_str = str(r.get("A", "")).strip()
        if amt_str and amt_str.isdigit():
            code = _clean_val(r.get("B"))
            desc = _clean_val(r.get("D"))
            # Poprawa typowych błędów znaków diakrytycznych
            desc = desc.replace("\ufffd", "ł").replace("zcze", "złącze")
            sup = _clean_val(r.get("J"))
            sup = sup.replace("\ufffd", "Ś")
            if sup.upper() in ["WA", "WA"]:
                sup = "WAŚ"
            elif sup.upper() in ["ZCZE", "ZCZE"]:
                sup = "Złącze"

            cat = categorize_bom_item(desc, code, sup)
            local_img = find_local_component_image(code)
            local_img_file = os.path.basename(local_img) if local_img else None

            current_art = {
                "article_number": code,
                "supplier": sup or "Nieznany",
                "description": desc,
                "amount": int(amt_str),
                "category": cat,
                "local_image": local_img_file,
                "devices": []
            }
            parsed_articles.append(current_art)
        elif current_art and r.get("B"):
            dev = _clean_val(r.get("B"))
            func = _clean_val(r.get("D"))
            if dev and not dev.lower().startswith("device"):
                current_art["devices"].append({
                    "device_code": dev,
                    "device_clean": clean_device_code(dev),
                    "function": func
                })

    total_devices = 0
    for art in parsed_articles:
        cur.execute("""
            INSERT INTO zuken_bom_items (project_id, article_number, supplier, description, amount, category, local_image)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            project_id,
            art["article_number"],
            art["supplier"],
            art["description"],
            art["amount"],
            art["category"],
            art["local_image"]
        ))
        item_id = cur.lastrowid

        dev_rows = [
            (item_id, d["device_code"], d["device_clean"], d["function"])
            for d in art["devices"]
        ]
        if dev_rows:
            cur.executemany("""
                INSERT INTO zuken_bom_devices (bom_item_id, device_code, device_clean, function)
                VALUES (?, ?, ?, ?);
            """, dev_rows)
            total_devices += len(dev_rows)

    conn.commit()
    conn.close()

    return len(parsed_articles), total_devices, f"Zaimportowano {len(parsed_articles)} artykułów BOM ({total_devices} przypisań aparatów)."


def find_bom_components_for_devices(device_codes, ps_code=None):
    """
    Dla podanej listy kodów aparatów (np. ['=BOX+TWL-X52', '-X434', '=BOX+TWR-FH49'])
    odnajduje powiązane artykuły z BOM wraz z dostawcami, linkami i zdjęciami.
    """
    if not device_codes:
        return []

    search_codes = set()
    for d in device_codes:
        if not d:
            continue
        c_str = str(d).strip()
        search_codes.add(c_str)
        c_clean = clean_device_code(c_str)
        if c_clean:
            search_codes.add(c_clean)
            search_codes.add(f"-{c_clean}")

    if not search_codes:
        return []

    conn = get_db()
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in search_codes)
    sql = f"""
        SELECT 
            i.id as item_id, i.article_number, i.supplier, i.description, i.amount, i.category, i.local_image,
            d.device_code, d.device_clean, d.function,
            p.project_name, p.revision_name
        FROM zuken_bom_devices d
        JOIN zuken_bom_items i ON d.bom_item_id = i.id
        JOIN zuken_projects p ON i.project_id = p.id
        WHERE (d.device_code IN ({placeholders}) OR d.device_clean IN ({placeholders}))
        ORDER BY i.category, i.supplier, i.article_number;
    """
    cur.execute(sql, list(search_codes) + list(search_codes))
    rows = cur.fetchall()

    grouped_items = {}
    for r in rows:
        art_num = r["article_number"]
        if art_num not in grouped_items:
            img_url = find_local_component_image(art_num)
            supplier = r["supplier"]
            grouped_items[art_num] = {
                "item_id": r["item_id"],
                "article_number": art_num,
                "supplier": supplier,
                "description": r["description"],
                "amount": r["amount"],
                "category": r["category"],
                "image_url": img_url,
                "has_image": bool(img_url),
                "supplier_links": get_supplier_links(art_num, supplier),
                "matched_devices": [],
                "project_rev": r["revision_name"]
            }
        dev_entry = {
            "device_code": r["device_code"],
            "device_clean": r["device_clean"],
            "function": r["function"]
        }
        if dev_entry not in grouped_items[art_num]["matched_devices"]:
            grouped_items[art_num]["matched_devices"].append(dev_entry)

    # Dla złączek poszukaj pasujących pinów/terminali z tego samego projektu BOM
    result_list = list(grouped_items.values())
    for item in result_list:
        if "Złącze" in item["category"] or "Obudowa" in item["category"]:
            conn_terms = []
            for term_type in ["MQS", "MCON", "MATE-N-LOK", "FASTIN", "DEUTSCH", "AMP", "TERMINAL"]:
                if term_type in item["description"].upper() or term_type in item["article_number"].upper():
                    cur.execute("""
                        SELECT article_number, supplier, description, local_image
                        FROM zuken_bom_items
                        WHERE category = 'Pin / Terminal' AND (description LIKE ? OR article_number LIKE ?)
                        LIMIT 4;
                    """, (f"%{term_type}%", f"%{term_type}%"))
                    for tr in cur.fetchall():
                        t_num = tr["article_number"]
                        conn_terms.append({
                            "article_number": t_num,
                            "supplier": tr["supplier"],
                            "description": tr["description"],
                            "image_url": find_local_component_image(t_num),
                            "supplier_links": get_supplier_links(t_num, tr["supplier"])
                        })
                    break
            item["related_terminals"] = conn_terms

    conn.close()
    return result_list


def get_bom_catalog(query="", supplier="", category="", ps_code="", limit=100, offset=0):
    """Zwraca listę artykułów z BOM z filtrowaniem i paginacją."""
    conn = get_db()
    cur = conn.cursor()

    conditions = []
    params = []

    if query:
        q_like = f"%{query.strip()}%"
        conditions.append("""
            (i.article_number LIKE ? OR i.description LIKE ? OR i.supplier LIKE ? OR
             EXISTS (SELECT 1 FROM zuken_bom_devices d WHERE d.bom_item_id = i.id AND (d.device_code LIKE ? OR d.device_clean LIKE ?)))
        """)
        params.extend([q_like, q_like, q_like, q_like, q_like])

    if supplier:
        conditions.append("i.supplier = ?")
        params.append(supplier.strip())

    if category:
        conditions.append("i.category = ?")
        params.append(category.strip())

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    cur.execute(f"SELECT COUNT(*) FROM zuken_bom_items i {where_clause};", params)
    total_count = cur.fetchone()[0]

    sql = f"""
        SELECT i.*, p.project_name, p.revision_name
        FROM zuken_bom_items i
        JOIN zuken_projects p ON i.project_id = p.id
        {where_clause}
        ORDER BY i.supplier, i.article_number
        LIMIT ? OFFSET ?;
    """
    cur.execute(sql, params + [limit, offset])
    rows = cur.fetchall()

    items = []
    for r in rows:
        art_num = r["article_number"]
        sup = r["supplier"]
        img_url = find_local_component_image(art_num)

        cur.execute("SELECT device_code, device_clean, function FROM zuken_bom_devices WHERE bom_item_id = ? LIMIT 20;", (r["id"],))
        devs = [dict(d) for d in cur.fetchall()]

        items.append({
            "id": r["id"],
            "article_number": art_num,
            "supplier": sup,
            "description": r["description"],
            "amount": r["amount"],
            "category": r["category"],
            "image_url": img_url,
            "has_image": bool(img_url),
            "supplier_links": get_supplier_links(art_num, sup),
            "devices": devs,
            "project_name": r["project_name"],
            "revision_name": r["revision_name"]
        })

    conn.close()
    return {
        "items": items,
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


def get_bom_suppliers():
    """Zwraca listę dostawców z liczbą artykułów."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT supplier, COUNT(*) as count
        FROM zuken_bom_items
        GROUP BY supplier
        ORDER BY count DESC, supplier ASC;
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_bom_categories():
    """Zwraca listę kategorii artykułów z liczbą."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT category, COUNT(*) as count
        FROM zuken_bom_items
        GROUP BY category
        ORDER BY count DESC, category ASC;
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def save_component_image(article_number, image_bytes, ext="png"):
    """
    Zapisuje plik zdjęcia złączki/artykułu w Baza wiedzy/zdjecia_komponentow/
    i aktualizuje referencję w tabeli zuken_bom_items.
    """
    if not article_number or not image_bytes:
        return False, "Brak numeru artykułu lub danych obrazu."

    os.makedirs(BOM_IMAGES_DIR, exist_ok=True)
    sanitized = sanitize_article_code(article_number)
    clean_ext = ext.lstrip(".").lower()
    if clean_ext not in ["png", "jpg", "jpeg", "webp"]:
        clean_ext = "png"

    filename = f"{sanitized}.{clean_ext}"
    target_path = os.path.join(BOM_IMAGES_DIR, filename)

    with open(target_path, "wb") as f:
        f.write(image_bytes)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE zuken_bom_items
        SET local_image = ?
        WHERE article_number = ?;
    """, (filename, article_number))
    conn.commit()
    conn.close()

    return True, f"/api/zuken/bom/image/{filename}"


# ═══════════════════════════════════════════════════════════════════
# INDEKSOWANIE SCHEMATÓW PDF Z ZUKEN E3
# ═══════════════════════════════════════════════════════════════════

def index_zuken_pdf(filepath, ps_code=None):
    """
    Indeksuje wektorowy plik PDF ze schematem wyeksportowanym z Zuken E3.
    Wyciąga spisy arkuszy, numery stron oraz symbole aparatów i przewodów.
    Zwraca (schematic_id, total_symbols, message).
    """
    if pypdf is None:
        return None, 0, "Biblioteka pypdf nie jest zainstalowana."
    
    if not os.path.exists(filepath):
        return None, 0, f"Plik {filepath} nie istnieje."

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    file_mtime = os.path.getmtime(filepath)

    conn = get_db()
    cur = conn.cursor()

    # Sprawdź czy plik był już zaindeksowany i nie uległ modyfikacji
    cur.execute("""
        SELECT id, total_pages FROM zuken_pdf_schematics
        WHERE (filepath = ? OR filename = ?) AND file_size = ? AND abs(file_mtime - ?) < 1
    """, (filepath, filename, file_size, file_mtime))
    cached = cur.fetchone()
    if cached:
        conn.close()
        return cached["id"], 0, f"Schemat {filename} jest już zaindeksowany (bez zmian)."

    # Jeśli podano lub wykryto z katalogu nadrzędnego PS code
    if not ps_code:
        parent_dir = os.path.basename(os.path.dirname(filepath))
        if re.match(r"^PS\d+", parent_dir, re.I):
            ps_code = parent_dir.upper()

    info = extract_project_info_from_filename(filename, [])
    if ps_code:
        info["ps_codes"] = ps_code

    try:
        reader = pypdf.PdfReader(filepath)
        total_pages = len(reader.pages)
    except Exception as e:
        conn.close()
        return None, 0, f"Błąd odczytu PDF {filename}: {e}"

    # Wyciągnij strukturę zakładek
    outline_map = {}
    def extract_outlines(items):
        for it in items:
            if isinstance(it, list):
                extract_outlines(it)
            else:
                title = getattr(it, "title", "")
                try:
                    p_idx = reader.get_destination_page_number(it)
                    outline_map[p_idx] = title
                except Exception:
                    pass
    try:
        if reader.outline:
            extract_outlines(reader.outline)
    except Exception:
        pass

    # Usuń stary wpis jeśli był o tej samej nazwie pliku
    cur.execute("DELETE FROM zuken_pdf_schematics WHERE filepath = ? OR filename = ?", (filepath, filename))

    now_iso = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO zuken_pdf_schematics (
            filename, filepath, project_name, ps_code, revision_date, revision_name,
            total_pages, file_size, file_mtime, is_active, indexed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        filename, filepath, info["project_name"], info["ps_codes"],
        info["revision_date"], info["revision_name"],
        total_pages, file_size, file_mtime, 1, now_iso
    ))
    schematic_id = cur.lastrowid

    total_symbols_count = 0
    symbols_to_insert = []
    
    # Przejdź stronę po stronie
    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = page.extract_text() or ""
        bookmark = outline_map.get(idx, "")

        sheet_num = str(page_num)
        sheet_title = f"Arkusz {page_num}"
        section_code = ""

        if bookmark:
            parts = [p.strip() for p in bookmark.split("|") if p.strip()]
            if parts:
                sheet_num = parts[0]
                if len(parts) > 1:
                    sheet_title = " | ".join(parts[1:])
                else:
                    sheet_title = parts[0]
            m_sec = re.search(r"(=[A-Za-z0-9_]+|\+[A-Za-z0-9_]+)", bookmark)
            if m_sec:
                section_code = m_sec.group(1)

        # Wstaw arkusz
        cur.execute("""
            INSERT INTO zuken_pdf_sheets (schematic_id, page_number, sheet_number, sheet_title, section_code, raw_text)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (schematic_id, page_num, sheet_num, sheet_title, section_code, raw_text))
        sheet_id = cur.lastrowid

        # Ekstrakcja symboli z tekstu strony
        seen_on_page = set()

        devs = re.findall(r"(?:\b|\s)(-[A-Za-z0-9_]+)\b", raw_text)
        full_devs = re.findall(r"((?:=[A-Za-z0-9_]+)?(?:\+[A-Za-z0-9_]+)?-[A-Za-z0-9_]+)", raw_text)
        wire_matches = re.findall(r"\b([0-9]{1,4}[A-Za-z]{0,2}(?:_[0-9A-Za-z]+)?)\b", raw_text)

        for d in devs + full_devs:
            d = d.strip()
            if not d or len(d) < 2 or d in seen_on_page:
                continue
            if d.startswith("-") and d[1:].isdigit() and len(d[1:]) < 2:
                continue
            seen_on_page.add(d)

            sym_clean = re.sub(r"^[=+\-:]+", "", d)
            sym_type = "device"
            if d.startswith("-X") or "-X" in d:
                sym_type = "connector"
            elif d.startswith("-F") or "-F" in d:
                sym_type = "fuse"
            elif d.startswith("-RT") or "-RT" in d or d.startswith("-K") or "-K" in d:
                sym_type = "relay"
            elif d.startswith("-S") or "-S" in d:
                sym_type = "switch"
            elif d.startswith("-A") or "-A" in d:
                sym_type = "module"
            elif d.startswith("-SP") or "-SP" in d:
                sym_type = "splice"

            symbols_to_insert.append((schematic_id, sheet_id, page_num, sym_type, d, sym_clean, ""))

        for w in wire_matches:
            w = w.strip()
            if not w or len(w) < 2 or w in seen_on_page:
                continue
            if w in ["2025", "2026", "2024", "87654321", "12345678", "00", "01"]:
                continue
            seen_on_page.add(w)
            symbols_to_insert.append((schematic_id, sheet_id, page_num, "wire_signal", w, w, ""))

    if symbols_to_insert:
        cur.executemany("""
            INSERT INTO zuken_pdf_symbols (schematic_id, sheet_id, page_number, symbol_type, symbol_name, symbol_clean, context_info)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, symbols_to_insert)
        total_symbols_count = len(symbols_to_insert)

    # Ustal status is_active: dla danego projektu / PS najnowsza rewizja ma is_active = 1, starsze mają is_active = 0
    ps_val = info["ps_codes"]
    if ps_val:
        cur.execute("""
            SELECT id FROM zuken_pdf_schematics
            WHERE ps_code = ?
            ORDER BY revision_date DESC, id DESC;
        """, (ps_val,))
        rows = cur.fetchall()
        if rows:
            newest_id = rows[0][0]
            cur.execute("UPDATE zuken_pdf_schematics SET is_active = 0 WHERE ps_code = ?", (ps_val,))
            cur.execute("UPDATE zuken_pdf_schematics SET is_active = 1 WHERE id = ?", (newest_id,))

    conn.commit()
    conn.close()
    return schematic_id, total_symbols_count, f"Zaindeksowano {total_pages} arkuszy i {total_symbols_count} symboli."


def get_pdf_schematics():
    """Zwraca listę zaindeksowanych schematów PDF z informacją o rewizjach."""
    init_zuken_tables()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, filepath, project_name, ps_code, revision_date, revision_name,
               total_pages, is_active, indexed_at
        FROM zuken_pdf_schematics
        ORDER BY is_active DESC, revision_date DESC, id DESC;
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def find_zuken_executable():
    """Wyszukuje ścieżkę do Zuken E3.series (E3.series.exe) w rejestrze Windows lub typowych folderach."""
    if os.name != "nt":
        return None
    try:
        import winreg
        # 1. Sprawdź HKCR\E3S\shell\open\command
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"E3S\shell\open\command") as k:
                val = winreg.QueryValue(k, None)
                if val:
                    m = re.search(r'"([^"]+\.exe)"', val, re.I) or re.search(r'([^\s]+\.exe)', val, re.I)
                    if m and os.path.exists(m.group(1)):
                        return m.group(1)
        except Exception:
            pass

        # 2. Sprawdź App Paths
        for key_path in [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\E3.series.exe",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\E3.series.exe",
        ]:
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(root, key_path) as k:
                        val = winreg.QueryValue(k, None)
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    pass

        # 3. Sprawdź wpisy deinstalatora
        for uninstall_key in [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as k_un:
                    for i in range(winreg.QueryInfoKey(k_un)[0]):
                        try:
                            subkey_name = winreg.EnumKey(k_un, i)
                            with winreg.OpenKey(k_un, subkey_name) as subk:
                                disp, _ = winreg.QueryValueEx(subk, "DisplayName")
                                if "zuken" in str(disp).lower() or "e3.series" in str(disp).lower():
                                    try:
                                        loc, _ = winreg.QueryValueEx(subk, "InstallLocation")
                                        if loc:
                                            cand = os.path.join(loc, "E3.series.exe")
                                            if os.path.exists(cand):
                                                return cand
                                    except Exception:
                                        pass
                        except Exception:
                            continue
            except Exception:
                pass
    except Exception:
        pass

    # 4. Sprawdź typowe foldery instalacyjne
    import glob
    candidates = [
        r"C:\Program Files\Zuken\E3.series_2027\E3.series.exe",
        r"C:\Program Files\Zuken\E3.series_2026\E3.series.exe",
        r"C:\Program Files\Zuken\E3.series_2025\E3.series.exe",
        r"C:\Program Files\Zuken\E3.series_2024\E3.series.exe",
    ]
    candidates.extend(glob.glob(r"C:\Program Files\Zuken\E3.series_*\E3.series.exe"))
    candidates.extend(glob.glob(r"C:\Program Files (x86)\Zuken\E3.series_*\E3.series.exe"))
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def find_sumatra_executable():
    """Wyszukuje ścieżkę do programu SumatraPDF.exe (najpierw w katalogu aplikacji, potem w systemie)."""
    # 1. Główny priorytet: SumatraPDF wgrana do katalogu programu rejestru usterek
    local_sumatra = os.path.join(BASE_DIR, "SumatraPDF.exe")
    if os.path.exists(local_sumatra):
        return local_sumatra

    cwd_sumatra = os.path.join(os.getcwd(), "SumatraPDF.exe")
    if os.path.exists(cwd_sumatra):
        return cwd_sumatra

    if os.name != "nt":
        return None

    try:
        import winreg
        for key_path in [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\SumatraPDF.exe",
        ]:
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(root, key_path) as k:
                        val = winreg.QueryValue(k, None)
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    pass
    except Exception:
        pass

    common_paths = [
        r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
        r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\SumatraPDF\SumatraPDF.exe"),
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def find_acrobat_executable():
    """Wyszukuje ścieżkę do Adobe Acrobat / Acrobat Reader w rejestrze Windows lub typowych folderach."""
    if os.name != "nt":
        return None
    try:
        import winreg
        for key_path in [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Acrobat.exe",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\AcroRd32.exe",
        ]:
            for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    with winreg.OpenKey(root, key_path) as k:
                        val = winreg.QueryValue(k, None)
                        if val and os.path.exists(val):
                            return val
                except Exception:
                    pass
    except Exception:
        pass

    common_paths = [
        r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe",
        r"C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe",
        r"C:\Program Files\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
        r"C:\Program Files (x86)\Adobe\Acrobat 2020\Acrobat\Acrobat.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def find_e3s_counterpart(pdf_filepath):
    """
    Dla wskazanego pliku PDF wyszukuje odpowiadający mu plik projektu Zuken (.e3s).
    Szuka najpierw pliku o tej samej nazwie w tym samym folderze,
    następnie pasującego pliku w podkatalogu projektu lub Bazie wiedzy.
    """
    if not pdf_filepath:
        return None

    # 1. Ten sam katalog i ten sam rdzeń nazwy z rozszerzeniem .e3s
    p = Path(pdf_filepath)
    direct_e3s = p.with_suffix(".e3s")
    if direct_e3s.exists():
        return str(direct_e3s)

    parent_dir = p.parent
    if parent_dir.exists():
        # 2. Inny plik .e3s w tym samym katalogu
        e3s_in_dir = list(parent_dir.glob("*.e3s"))
        if len(e3s_in_dir) == 1:
            return str(e3s_in_dir[0])
        elif len(e3s_in_dir) > 1:
            # Dopasuj najbardziej zbliżoną nazwę
            stem_clean = re.sub(r"[_\-\s]+", "", p.stem).lower()
            for cand in e3s_in_dir:
                cand_clean = re.sub(r"[_\-\s]+", "", cand.stem).lower()
                if cand_clean == stem_clean or cand_clean in stem_clean or stem_clean in cand_clean:
                    return str(cand)
            return str(e3s_in_dir[0])

    # 3. Szukanie w Bazie wiedzy
    fname_stem = p.stem
    kb_path = Path(BAZA_WIEDZY_DIR)
    if kb_path.exists():
        matches = list(kb_path.glob(f"**/{fname_stem}.e3s"))
        if matches and matches[0].exists():
            return str(matches[0])

    return None


def detect_zuken_edition():
    """
    Automatycznie rozpoznaje czy na danej stacji roboczej zainstalowano pełną wersję projektancką
    (Zuken E3.series Designer/Editor), czy wersję przeglądarki (E3.view).

    Sprawdza:
    1. Rejestr Windows (domyślne powiązanie HKCR\\E3S\\shell\\open\\command):
       - obecność przełącznika /view oznacza wersję Viewer
       - brak /view oznacza pełną wersję Designer
    2. Plik licencji wskazany w ZUKEN_LICENSE_FILE lub w folderze Zuken:
       - cechy E3schematic, E3cable, E3enterprise, E3designer -> pełna wersja Designer
       - tylko E3view -> Viewer
    Zwraca krotkę: (is_viewer: bool, mode_label: str)
    """
    if os.name != "nt":
        return True, "Zuken E3.view (Viewer)"

    # 1. Sprawdź powiązanie powłoki w rejestrze Windows
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"E3S\shell\open\command") as k:
            cmd = (winreg.QueryValue(k, None) or "").lower()
            if cmd:
                if "/view" in cmd:
                    return True, "Zuken E3.view (Viewer)"
                else:
                    return False, "Zuken E3.series (Designer)"
    except Exception:
        pass

    # 2. Sprawdź cechy pliku licencji
    try:
        lic_paths = []
        env_lic = os.environ.get("ZUKEN_LICENSE_FILE")
        if env_lic:
            lic_paths.append(env_lic)

        for p in [
            r"C:\Program Files\Zuken\E3.series_2027\license.dat",
            r"C:\Program Files\Zuken\E3.series_2027\licence.dat",
            r"C:\Program Files\Zuken\license.dat",
            r"C:\Program Files\Zuken\licence.dat",
        ]:
            if p not in lic_paths:
                lic_paths.append(p)

        for lp in lic_paths:
            if os.path.exists(lp):
                with open(lp, "r", errors="ignore") as f:
                    content = f.read()
                if re.search(r"FEATURE\s+(E3schematic|E3cable|E3enterprise|E3series|E3designer)", content, re.I):
                    return False, "Zuken E3.series (Designer)"
                if re.search(r"FEATURE\s+E3view", content, re.I):
                    return True, "Zuken E3.view (Viewer)"
    except Exception:
        pass

    # Domyślnie, jeśli nie udało się precyzyjnie ustalić
    return True, "Zuken E3.view (Viewer)"


def open_in_zuken(e3s_filepath, sheet_number=None, sheet_title=None):
    """
    Otwiera projekt .e3s w programie Zuken E3.
    Automatycznie dostosowuje tryb do stanowiska:
    - Projektant (pełna licencja): uruchamia pełny Zuken E3.series (Designer)
    - Przeglądarka (warsztat/serwis): uruchamia w trybie Zuken E3.view z licencją viewer
    """
    if not os.path.exists(e3s_filepath):
        return False, f"Plik projektu Zuken {e3s_filepath} nie istnieje."

    is_viewer, mode_label = detect_zuken_edition()

    sheet_info = f"Arkusz {sheet_number}" if sheet_number else "Wskazany arkusz"
    if sheet_title:
        sheet_info += f" ({sheet_title})"

    # 1. Metoda główna: Systemowe powiązanie Windows dla plików .e3s (os.startfile)
    # Na komputerze projektanta Windows domyślnie uruchamia pełnego Designera.
    # Na komputerze z licencją przeglądarki Windows domyślnie uruchamia E3.view.
    try:
        if hasattr(os, "startfile"):
            os.startfile(e3s_filepath)
            return True, f"Otwarto schemat w {mode_label} [{sheet_info}]"
    except Exception:
        pass

    # 2. Bezpośrednie wywołanie E3.series.exe z odpowiednimi flagami
    zuken_exe = find_zuken_executable()
    if zuken_exe and os.path.exists(zuken_exe):
        try:
            import ctypes
            # Dla Viewera konieczne /view /plus; dla pełnego Designera /plus (bez /view)
            args = f'/view /plus "{e3s_filepath}"' if is_viewer else f'/plus "{e3s_filepath}"'
            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", zuken_exe, args, None, 1)
            if ret > 32:
                return True, f"Otwarto schemat w {mode_label} [{sheet_info}]"
        except Exception:
            pass

        try:
            import subprocess
            flags = 0x00000008 | 0x00000200 # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            cmd_args = [zuken_exe, "/view", "/plus", e3s_filepath] if is_viewer else [zuken_exe, "/plus", e3s_filepath]
            subprocess.Popen(cmd_args, creationflags=flags)
            return True, f"Otwarto schemat w {mode_label} [{sheet_info}]"
        except Exception as e:
            return False, f"Błąd uruchamiania {mode_label}: {e}"

    return False, f"Nie udało się uruchomić programu {mode_label}."


def open_in_sumatra(pdf_filepath, page_number=1):
    """Otwiera plik PDF w programie SumatraPDF na określonej stronie."""
    sumatra_exe = find_sumatra_executable()
    if not sumatra_exe or not os.path.exists(sumatra_exe):
        return False, "Nie odnaleziono programu SumatraPDF."

    if not os.path.exists(pdf_filepath):
        return False, f"Plik {pdf_filepath} nie istnieje."

    page_arg = int(page_number) if page_number and int(page_number) > 0 else 1

    try:
        import ctypes
        args = f'-reuse-instance -page {page_arg} "{pdf_filepath}"'
        ret = ctypes.windll.shell32.ShellExecuteW(None, "open", sumatra_exe, args, None, 1)
        if ret > 32:
            return True, f"Otwarto w SumatraPDF na stronie {page_arg}"
    except Exception:
        pass

    try:
        import subprocess
        flags = 0x00000008 | 0x00000200
        subprocess.Popen([sumatra_exe, "-reuse-instance", "-page", str(page_arg), pdf_filepath], creationflags=flags)
        return True, f"Otwarto w SumatraPDF na stronie {page_arg}"
    except Exception as e:
        return False, f"Błąd uruchamiania SumatraPDF: {e}"


def open_schematic_in_system(filepath, page_number=1, sheet_number=None, sheet_title=None):
    """
    Inteligentne otwieranie schematu z zachowaniem priorytetów:
    1. Zuken E3.series (jeśli program jest zainstalowany i istnieje plik .e3s)
    2. SumatraPDF na wskazanym numerze strony (z katalogu programu)
    3. Adobe Acrobat (jeśli zainstalowany)
    4. Domyślny program PDF systemu Windows
    """
    # 1. Sprawdź czy plik istnieje pod wskazaną ścieżką; jeśli nie, poszukaj go w Bazie wiedzy
    if not os.path.exists(filepath):
        fname = os.path.basename(filepath)
        candidates = list(Path(BAZA_WIEDZY_DIR).glob(f"**/{fname}"))
        if candidates and candidates[0].exists():
            filepath = str(candidates[0])
            try:
                conn_up = get_db()
                conn_up.execute("UPDATE zuken_pdf_schematics SET filepath = ? WHERE filename = ?", (filepath, fname))
                conn_up.commit()
                conn_up.close()
            except Exception:
                pass
        else:
            return False, f"Plik {filepath} nie istnieje."

    # PRIORYTET 1: Zuken E3.series + plik .e3s
    zuken_exe = find_zuken_executable()
    if zuken_exe:
        e3s_file = find_e3s_counterpart(filepath)
        if e3s_file and os.path.exists(e3s_file):
            ok, msg = open_in_zuken(e3s_file, sheet_number=sheet_number, sheet_title=sheet_title)
            if ok:
                return True, msg

    # PRIORYTET 2: SumatraPDF na wskazanym arkuszu
    sumatra_exe = find_sumatra_executable()
    if sumatra_exe:
        ok, msg = open_in_sumatra(filepath, page_number=page_number)
        if ok:
            return True, msg

    # PRIORYTET 3: Adobe Acrobat
    acro = find_acrobat_executable()
    if acro and os.path.exists(acro):
        try:
            import ctypes
            args = f'/A "page={page_number}" "{filepath}"' if page_number and int(page_number) > 0 else f'"{filepath}"'
            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", acro, args, None, 1)
            if ret > 32:
                return True, f"Otwarto w Adobe Acrobat na stronie {page_number}"
        except Exception:
            pass

        try:
            import subprocess
            flags = 0x00000008 | 0x00000200
            if page_number and int(page_number) > 0:
                subprocess.Popen([acro, "/A", f"page={page_number}", filepath], creationflags=flags)
            else:
                subprocess.Popen([acro, filepath], creationflags=flags)
            return True, f"Otwarto w Adobe Acrobat na stronie {page_number}"
        except Exception:
            pass

    # PRIORYTET 4: Domyślna aplikacja systemowa Windows
    try:
        if hasattr(os, "startfile"):
            os.startfile(filepath)
            return True, "Otwarto w domyślnej aplikacji systemu Windows"
        else:
            import subprocess
            subprocess.Popen(["xdg-open", filepath])
            return True, "Otwarto w domyślnej przeglądarce dokumentów"
    except Exception as e:
        return False, str(e)


def open_pdf_in_system(filepath, page_number=1):
    """
    Otwiera plik PDF w natywnej aplikacji Windows (SumatraPDF na wskazanym arkuszu,
    Adobe Acrobat lub programie domyślnym).
    """
    # 1. SumatraPDF
    sumatra_exe = find_sumatra_executable()
    if sumatra_exe:
        ok, msg = open_in_sumatra(filepath, page_number=page_number)
        if ok:
            return True, msg

    # 2. Adobe Acrobat
    acro = find_acrobat_executable()
    if acro and os.path.exists(acro):
        try:
            import ctypes
            args = f'/A "page={page_number}" "{filepath}"' if page_number and int(page_number) > 0 else f'"{filepath}"'
            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", acro, args, None, 1)
            if ret > 32:
                return True, f"Otwarto w Adobe Acrobat na arkuszu {page_number}"
        except Exception:
            pass
        try:
            import subprocess
            flags = 0x00000008 | 0x00000200
            if page_number and int(page_number) > 0:
                subprocess.Popen([acro, "/A", f"page={page_number}", filepath], creationflags=flags)
            else:
                subprocess.Popen([acro, filepath], creationflags=flags)
            return True, f"Otwarto w Adobe Acrobat na arkuszu {page_number}"
        except Exception:
            pass

    # 3. Domyślne skojarzenie Windows
    try:
        if hasattr(os, "startfile"):
            os.startfile(filepath)
            return True, "Otwarto w domyślnej aplikacji PDF systemu Windows"
        else:
            import subprocess
            subprocess.Popen(["xdg-open", filepath])
            return True, "Otwarto w domyślnej przeglądarce PDF"
    except Exception as e:
        return False, str(e)


# Słownik synonimów dla wyszukiwania w arkuszach PDF
PDF_SYNONYMS = {
    "DRZWI": ["DOOR", "CAB DOORS", "DPR", "DPL", "CENTRAL LOCKING"],
    "DOOR": ["CAB DOORS", "DOOR", "CENTRAL LOCKING"],
    "PRZESUW": ["DOOR", "DPR", "CENTRAL LOCKING"],
    "ZAMEK": ["CENTRAL LOCKING", "LOCK"],
    "RYGIEL": ["CENTRAL LOCKING", "LOCK"],
    "LOCK": ["CENTRAL LOCKING", "LOCK"],
    "CENTRALNY": ["CENTRAL LOCKING"],
    "12V": ["12V", "12V SUPPLY", "SOCKET", "OUTLETS"],
    "110V": ["110V", "110V SUPPLY", "110V FUSE"],
    "GNIAZDO": ["OUTLETS", "SOCKET"],
    "OUTLETS": ["OUTLETS", "SOCKET"],
    "WENTYLATOR": ["HVAC", "FAN"],
    "KLIMATYZACJA": ["HVAC"],
    "HVAC": ["HVAC", "FAN"],
    "SYRENA": ["SIREN"],
    "SIREN": ["SIREN"],
    "OŚWIETLENIE": ["LIGHT", "SCENE LIGHT", "INNER LIGHT", "BLUES"],
    "OSWIETLENIE": ["LIGHT", "SCENE LIGHT", "INNER LIGHT", "BLUES"],
    "ŚWIATŁA": ["LIGHT", "BLUES", "CENTRAL LOCKING", "WARNING", "STEP LIGHT"],
    "SWIATLA": ["LIGHT", "BLUES", "CENTRAL LOCKING", "WARNING", "STEP LIGHT"],
    "BLUES": ["BLUES", "BODY BLUES", "REAR BLUES", "FRONT BLUES"],
    "NIEBIESKIE": ["BLUES", "FRONT BLUES", "BODY BLUES"],
    "ANTYKOLIZYJNE": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
    "ANTYKOLIZYJNA": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
    "ANTYKOLIZYJNYCH": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
    "KOLIZYJNE": ["CENTRAL LOCKING", "DOOR", "BLUES", "WARNING"],
    "KRAŃCÓWKA": ["DOOR SWITCH", "SWITCH", "DOOR", "CENTRAL LOCKING"],
    "KRANCOWKA": ["DOOR SWITCH", "SWITCH", "DOOR", "CENTRAL LOCKING"],
    "KRAŃCÓWKI": ["DOOR SWITCH", "SWITCH", "DOOR", "CENTRAL LOCKING"],
    "KRANCOWKI": ["DOOR SWITCH", "SWITCH", "DOOR", "CENTRAL LOCKING"],
    "DIODA": ["DIODE", "X245", "X246", "X248"],
    "DIODY": ["DIODE", "X245", "X246", "X248"],
    "OSTRZEGAWCZE": ["WARNING", "BLUES", "BEACON", "LIGHT"],
    "STOPNIA": ["STEP LIGHT", "CENTRAL LOCKING"],
    "STOPNIE": ["STEP LIGHT", "CENTRAL LOCKING"],
    "SCHOWKA": ["LOCKER LIGHT"],
    "SCHOWEK": ["LOCKER LIGHT"],
    "RADIO": ["ENTERTAIMENT RADIO", "RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "304", "305", "306"],
    "RADIA": ["ENTERTAIMENT RADIO", "RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "304", "305", "306"],
    "INTERCOM": ["INTERCOM", "MID", "X45", "X49", "X39", "X40", "A101", "SPEAKER INTERCOM", "O1.14"],
    "INTERKOM": ["INTERCOM", "MID", "X45", "X49", "X39", "X40", "A101", "SPEAKER INTERCOM", "O1.14"],
    "DOMOFON": ["INTERCOM", "MID", "X45", "X49", "X39", "X40", "A101", "SPEAKER INTERCOM"],
    "GŁOŚNIK": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "GLOSNIK": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "GŁOŚNIKA": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "GLOSNIKA": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "GŁOŚNIKI": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "GLOSNIKI": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "SPEAKER": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "SPEAKERS": ["SPEAKERS", "SPEAKER", "LAUTSPRECHER"],
    "LAUTSPRECHER": ["SPEAKERS", "SPEAKER"],
    "LT": ["LT", "LT-CAB", "LT CAB +", "LT CAB -", "LT SALOON"],
    "AUDIO": ["SPEAKERS", "SPEAKER", "RADIO", "INTERCOM"],
    "DŹWIĘK": ["SPEAKERS", "SPEAKER", "SIREN", "REVERSE ALARM", "LT"],
    "DZWIĘK": ["SPEAKERS", "SPEAKER", "SIREN", "REVERSE ALARM", "LT"],
    "TRENNWAND": ["BOX-CAB INTERFACE", "CAB", "TWM", "TWL", "TWR", "X292", "X296", "X10"],
    "GRODZIOWA": ["BOX-CAB INTERFACE", "CAB", "TWM", "TWL", "TWR", "X292", "X296", "X10"],
    "ŚCIANKA": ["BOX-CAB INTERFACE", "CAB", "TWM", "TWL", "TWR", "X292", "X296", "X10"],
    "BEZPIECZNIK": ["FUSE", "110V FUSE", "COMMS FUSE"],
    "FUSE": ["FUSE"],
    "PRZEKAŹNIK": ["RELAY"],
    "PRZEKAZNIK": ["RELAY"],
    "RELAY": ["RELAY"],
    "KFG": ["KFG"],
    "CARNATION": ["CARNATION", "A15", "SPEAKER CARNATION", "X244", "X258", "LT CAB", "LT SALOON"],
    "MDVS": ["MDVS"],
    "ORTUS": ["ORTUS"],
    "ECORUN": ["ECORUN", "ECO RUN INTERFACE"],
    "PANIC": ["PIR|PANIC", "PANIC"],
    "PIR": ["PIR|PANIC"],
    "COFANIA": ["REVERSE ALARM"],
    "REVERSE": ["REVERSE ALARM"],
    "KAMERA": ["MDVS", "RECORDER", "MONITOR", "CCTV"],
    "CZUJNIK": ["SENSOR", "EXTERNAL SENSOR", "HVAC"],
    "TEMPERATURA": ["HVAC", "EXTERNAL SENSOR", "HEATER"],
    "TEMPERATURY": ["HVAC", "EXTERNAL SENSOR", "HEATER"],
    "EBERSPACHER": ["HVAC", "HEATER", "47 =BOX"],
    "EBERSPÄCHER": ["HVAC", "HEATER", "47 =BOX"],
    "OBRYSOWE": ["MARKER LIGHT", "SIDELIGHT"],
    "OBRYSOWY": ["MARKER LIGHT", "SIDELIGHT"],
    "OBRYSÓWKA": ["MARKER LIGHT", "SIDELIGHT"],
    "OBRYSOWKA": ["MARKER LIGHT", "SIDELIGHT"],
    "MARKER": ["MARKER LIGHT", "SIDELIGHT"],
    "SIDELIGHT": ["MARKER LIGHT", "SIDELIGHT"],
    "SENSOR": ["EXTERNAL SENSOR", "HVAC"]
}

GENERIC_TERMS = {"12V", "230V", "110V", "115V", "24V", "12", "24", "110", "115", "230", "GND", "MASA", "CAN", "0V"}


def extract_query_phrases_and_tokens(query, extra_tokens=None):
    """
    Wyciąga frazy złożone (np. '12V SOCKET 3', 'MARKER LIGHT'), specyficzne słowa kluczowe oraz oddziela ogólne symbole napięć/mas.
    """
    q_raw = (query or "").strip()
    q_upper = q_raw.upper()

    compound_phrases = []
    specific_tokens = set()
    generic_tokens = set()

    # 1. Wzorce dla gniazd z numerem (np. "gniazdo 3/12V", "gniazdo 3", "socket 3", "3/12V", "12V socket 3")
    m_sock_num = re.search(r"(?:GNIAZDO|GNIAZDKO|SOCKET|OUTLET)\s*([0-9]+)(?:\s*[\/\-]\s*12V)?", q_upper)
    if m_sock_num:
        num = m_sock_num.group(1)
        compound_phrases.extend([f"12V SOCKET {num}", f"12 V SOCKET {num}", f"SOCKET {num}", f"OUTLET {num}"])
        specific_tokens.add(f"SOCKET {num}")
        specific_tokens.add("OUTLETS")
        specific_tokens.add("SOCKET")

    m_num_12v = re.search(r"\b([0-9]+)\s*[\/\-]\s*12V\b", q_upper)
    if m_num_12v:
        num = m_num_12v.group(1)
        compound_phrases.extend([f"12V SOCKET {num}", f"12 V SOCKET {num}", f"SOCKET {num}"])
        specific_tokens.add(f"SOCKET {num}")
        specific_tokens.add("OUTLETS")
        specific_tokens.add("SOCKET")

    # Wzorce dla fraz złożonych systemów audio, oświetlenia, czujników i złączy
    for p_phrase in [
        "MARKER LIGHT", "EXTERNAL SENSOR", "SIDELIGHT RH", "SIDELIGHT LH", "SIDELIGHT",
        "FRONT BLUES", "REAR BLUES", "CENTRAL LOCKING", "SPEAKER CARNATION",
        "IONV MAP LIGHT SPEAKERS", "MAP LIGHT", "BOX-CAB INTERFACE", "LT CAB", "LT SALOON"
    ]:
        if p_phrase in q_upper:
            if p_phrase not in compound_phrases:
                compound_phrases.append(p_phrase)
            specific_tokens.add(p_phrase)

    # Detekcja usterki głośników / audio: rozróżnienie Carnation vs Interkom vs Radio samochodowe
    is_carnation_intent = any(k in q_upper for k in ["CARNATION", "EVPSS", "KOMUNIKAT", "OSTRZEŻ", "OSTRZEZ"])
    is_intercom_intent = any(k in q_upper for k in ["INTERCOM", "INTERKOM", "DOMOFON", "WOLFELEC"])
    is_radio_intent = any(k in q_upper for k in ["RADIO", "RADIA", "RADIOW", "LEWY", "PRAWY", "LEFT", "RIGHT", "ENTERTAINMENT", "ENTERTAIMENT", "BALANS"])
    is_speaker_intent = any(k in q_upper for k in ["GŁOŚNIK", "GLOSNIK", "SPEAKER", "LAUTSPRECHER", "LT", "AUDIO"])

    if is_radio_intent:
        for sp_p in ["ENTERTAIMENT RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "RADIO VOLUME", "RADIO INTERFACE"]:
            if sp_p not in compound_phrases:
                compound_phrases.append(sp_p)
        specific_tokens.update(["ENTERTAIMENT RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "-304", "-305", "-306", "304", "305", "306", "HPL", "HPR"])
    elif is_intercom_intent:
        for sp_p in ["SPEAKER INTERCOM CAB", "SPEAKER INTERCOM BOX", "INTERCOM"]:
            if sp_p not in compound_phrases:
                compound_phrases.append(sp_p)
        specific_tokens.update(["INTERCOM", "X45", "X49", "X39", "X40", "X306", "A101", "-A101", "1612", "1613", "264", "267", "O1.14"])
    elif is_carnation_intent or is_speaker_intent:
        for sp_p in ["SPEAKER CARNATION", "IONV MAP LIGHT SPEAKERS", "LT CAB", "LT SALOON"]:
            if sp_p not in compound_phrases:
                compound_phrases.append(sp_p)
        specific_tokens.update(["SPEAKER CARNATION", "X244", "X258", "-X244", "-X258", "A15", "-A15", "LT CAB", "LT SALOON", "304_1", "472", "473"])

    # Detekcja ścianki grodziowej / przejść kabina-zabudowa
    if any(k in q_upper for k in ["TRENNWAND", "GRODZIOW", "ŚCIANK", "SCIAN"]):
        if "BOX-CAB INTERFACE" not in compound_phrases:
            compound_phrases.append("BOX-CAB INTERFACE")
        specific_tokens.update(["BOX-CAB INTERFACE", "TWM", "TWL", "TWR", "X296", "X292", "X10"])

    # Wzorce dla innych obwodów z numerami (np. X132, X179, X175, F18, RT127)
    for m_code in re.findall(r"\b([XFKM][0-9]{1,4}[A-Z]?|RT[0-9]{1,4}|SP[0-9]{1,4})\b", q_upper):
        specific_tokens.add(m_code)

    all_raw_tokens = re.findall(r"[A-Za-z0-9ĄĆĘŁŃÓŚŹŻ_\-\+]+", q_upper)
    if extra_tokens:
        for et in extra_tokens:
            all_raw_tokens.extend(re.findall(r"[A-Za-z0-9ĄĆĘŁŃÓŚŹŻ_\-\+]+", et.upper()))

    for t in all_raw_tokens:
        clean = re.sub(r"^[=+\-:]+", "", t)
        if t in GENERIC_TERMS or clean in GENERIC_TERMS:
            generic_tokens.add(t)
            if clean:
                generic_tokens.add(clean)
        elif len(t) >= 2:
            specific_tokens.add(t)
            if clean:
                specific_tokens.add(clean)
            for k, syns in PDF_SYNONYMS.items():
                if k in t or t in k:
                    for s in syns:
                        if s in GENERIC_TERMS:
                            generic_tokens.add(s)
                        else:
                            specific_tokens.add(s)

    has_specific = len(specific_tokens) > 0 or len(compound_phrases) > 0
    return compound_phrases, specific_tokens, generic_tokens, has_specific


def find_pdf_sheets_for_query(query, ps_code=None, limit=25, extra_tokens=None, explicit_sheet_numbers=None, circuit_devices=None, circuit_signals=None, primary_symbols=None, category=None):
    """
    Przeszukuje zaindeksowane arkusze PDF z inteligentnym scoringiem relewancji:
    - Pełnotekstowe przeszukiwanie treści arkuszy PDF (raw_text) dla precyzyjnych fraz (np. '12V SOCKET 3', 'MARKER LIGHT').
    - Promowanie arkuszy tematycznych (np. 'OUTLETS', 'HVAC' dla zapytania o gniazda/klimatyzację).
    - Silne faworyzowanie kluczowych złączy podanych w wariancie lub zgłoszeniu (primary_symbols).
    - Powiązanie ze zidentyfikowanymi aparatami i złączami obwodu (np. X392).
    - Eliminacja szumu: arkusze pasujące jedynie do powszechnego '12V' są odrzucane, jeśli zapytanie dotyczyło konkretnej funkcji.
    - Oznaczanie głównego rekomendowanego arkusza flagą is_primary_match.
    """
    if not query and not extra_tokens and not explicit_sheet_numbers and not circuit_devices and not primary_symbols:
        return []

    compound_phrases, specific_tokens, generic_tokens, has_specific = extract_query_phrases_and_tokens(query, extra_tokens)

    conn = get_db()
    cur = conn.cursor()

    ps_filter = "AND (sch.ps_code = ? OR sch.ps_code LIKE ?)" if ps_code else ""
    ps_params = [ps_code, f"%{ps_code}%"] if ps_code else []

    cur.execute(f"""
        SELECT sh.id as sheet_id, sh.schematic_id, sh.page_number, sh.sheet_number, sh.sheet_title,
               sh.section_code, sh.raw_text, sch.filename, sch.project_name, sch.revision_name,
               sch.revision_date, sch.is_active
        FROM zuken_pdf_sheets sh
        JOIN zuken_pdf_schematics sch ON sh.schematic_id = sch.id
        WHERE 1=1 {ps_filter}
        ORDER BY sch.is_active DESC, sh.page_number ASC;
    """, ps_params)
    all_sheets = [dict(r) for r in cur.fetchall()]

    # Przygotowanie listy symboli do zbadania
    sym_tokens = set(specific_tokens)
    if circuit_devices:
        for cd in circuit_devices:
            sym_tokens.add(cd)
            clean_cd = re.sub(r"^[=+\-:]+", "", cd)
            if clean_cd:
                sym_tokens.add(clean_cd)
            # Wyciągnij pod-kody aparatów (np. ze złożonego =BOX+CRNR-X179 -> -X179, X179)
            m_dev = re.search(r"(-[A-Za-z0-9_]+)", cd)
            if m_dev:
                d_val = m_dev.group(1)
                sym_tokens.add(d_val)
                sym_tokens.add(d_val.lstrip("-"))
            for m in re.findall(r"\b([XFKM]-?[0-9]{1,4}[A-Z]?|RT-?[0-9]{1,4}|SP-?[0-9]{1,4})\b", cd.upper()):
                m_clean = m.lstrip("-")
                sym_tokens.add(m_clean)
                sym_tokens.add(f"-{m_clean}")

    if primary_symbols:
        for ps in primary_symbols:
            clean_ps = re.sub(r"^[=+\-:]+", "", ps)
            if clean_ps:
                sym_tokens.add(clean_ps)
                sym_tokens.add(f"-{clean_ps}")

    # Jeśli użytkownik szukał TYLKO ogólnego hasła (np. 12V), dopuszczamy generic_tokens
    if not has_specific and generic_tokens:
        sym_tokens.update(generic_tokens)

    sheet_sym_map = {}
    if sym_tokens:
        placeholders = ",".join("?" for _ in sym_tokens)
        cur.execute(f"""
            SELECT sym.sheet_id, sym.symbol_name, sym.symbol_clean, sym.symbol_type
            FROM zuken_pdf_symbols sym
            WHERE (sym.symbol_clean IN ({placeholders}) OR sym.symbol_name IN ({placeholders}))
        """, list(sym_tokens) + list(sym_tokens))
        for r in cur.fetchall():
            sh_id = r["sheet_id"]
            if sh_id not in sheet_sym_map:
                sheet_sym_map[sh_id] = []
            sheet_sym_map[sh_id].append(dict(r))

    conn.close()

    explicit_set = set(str(s) for s in (explicit_sheet_numbers or []))
    circuit_dev_set = set()
    for d in (circuit_devices or []):
        d_clean = re.sub(r"^[=+\-:]+", "", d.upper())
        if d_clean:
            circuit_dev_set.add(d_clean)
        m_dev = re.search(r"(-[A-Za-z0-9_]+)", d)
        if m_dev:
            d_val = m_dev.group(1).upper()
            circuit_dev_set.add(d_val)
            circuit_dev_set.add(d_val.lstrip("-"))
        for m in re.findall(r"\b([XFKM]-?[0-9]{1,4}[A-Z]?|RT-?[0-9]{1,4}|SP-?[0-9]{1,4})\b", d.upper()):
            m_clean = m.lstrip("-")
            circuit_dev_set.add(m_clean)
            circuit_dev_set.add(f"-{m_clean}")

    primary_sym_set = set()
    for ps in (primary_symbols or []):
        clean_p = re.sub(r"^[=+\-:]+", "", ps.upper())
        if clean_p:
            primary_sym_set.add(clean_p)
            primary_sym_set.add(f"-{clean_p}")
        for m in re.findall(r"\b([XFKM]-?[0-9]{1,4}[A-Z]?|RT-?[0-9]{1,4}|SP-?[0-9]{1,4})\b", ps.upper()):
            m_clean = m.lstrip("-")
            primary_sym_set.add(m_clean)
            primary_sym_set.add(f"-{m_clean}")

    scored_results = []
    max_score = 0

    OVERVIEW_SHEET_REGEX = re.compile(
        r'(=\s*BOX|=\s*CAB|BOX-CAB|INTERCONNECT|INTERFACE|OVERVIEW|HARNESS|TOPOLOGY|TOPOLOGIA|ZESTAWIENIE|ZŁĄCZA WIĄZKI)',
        re.IGNORECASE
    )

    for sh in all_sheets:
        sh_id = sh["sheet_id"]
        score = 0
        reasons = []
        matched_syms = []
        raw_upper = (sh.get("raw_text") or "").upper()
        title_upper = (sh.get("sheet_title") or "").upper()

        syms_on_sheet = sheet_sym_map.get(sh_id, [])
        sym_count = len(syms_on_sheet)
        is_overview = False
        if OVERVIEW_SHEET_REGEX.search(title_upper):
            is_overview = True
        elif sym_count >= 180 and not any(k in title_upper for k in ['DOOR', 'LIGHT', 'HVAC', 'PUMP', 'RADIO', 'LOCKING', 'SIREN', 'RELAY', 'FUSE']):
            is_overview = True

        # 1. Jawne wskazanie arkusza z bazy wiedzy napraw
        if str(sh.get("sheet_number")) in explicit_set or str(sh.get("page_number")) in explicit_set:
            score += 250
            reasons.append("Wskazany w dokumentacji naprawy")

        # 2. Frazy złożone w tytule lub treści PDF (np. '12V SOCKET 3', 'MARKER LIGHT')
        for cp in compound_phrases:
            if cp in title_upper:
                score += 350 if not is_overview else 100
                reasons.append(f"Tytuł: {sh['sheet_title']}")
            elif cp in raw_upper:
                score += 120 if not is_overview else 40
                reasons.append(f"W treści arkusza: {cp}")

        # 3. Zgodność z kategorią usterki lub głównym układem problemu
        is_primary_system_match = False
        query_upper = (query or "").upper()
        is_speaker_query = any(k in query_upper for k in ['GŁOŚNIK', 'GLOSNIK', 'SPEAKER', 'LAUTSPRECHER', 'LT'])

        if category and str(category).strip().upper() in title_upper:
            # Jeśli kategoria to ogólne CARNATION, ale użytkownik szuka głośnika (SPEAKER),
            # to dedykowany arkusz głośnika ma priorytet nad ogólnym arkuszem sterownika Carnation (Arkusz 5)
            if str(category).strip().upper() == "CARNATION" and is_speaker_query:
                is_primary_system_match = False
            else:
                is_primary_system_match = True
        elif any(k in title_upper for k in ['HVAC', 'KLIMATYZACJA', 'OGRZEWANIE']) and any(tok in query_upper for tok in ['TEMPERATUR', 'CZUJNIK', 'E1', 'EBERSPACHER', 'HVAC']):
            is_primary_system_match = True

        if is_primary_system_match:
            score += 2800 if not is_overview else 100
            reasons.append(f"Główny układ usterki: {sh['sheet_title']}")

        # 3b. Dedykowane dopasowanie obwodów audio i głośników (rozróżnienie Radio vs Interkom vs Carnation)
        is_radio_intent = any(k in query_upper for k in ["RADIO", "RADIA", "RADIOW", "LEWY", "PRAWY", "LEFT", "RIGHT", "ENTERTAINMENT", "ENTERTAIMENT", "BALANS"])
        is_intercom_intent = any(k in query_upper for k in ["INTERCOM", "INTERKOM", "DOMOFON", "WOLFELEC"])
        is_carnation_intent = any(k in query_upper for k in ["CARNATION", "EVPSS", "KOMUNIKAT", "OSTRZEŻ", "OSTRZEZ"])

        if is_speaker_query or is_radio_intent or is_intercom_intent or is_carnation_intent:
            if is_radio_intent:
                if 'ENTERTAIMENT RADIO' in title_upper or str(sh.get('sheet_number')) == '9':
                    score += 6500
                    reasons.append("Dedykowany arkusz nagłośnienia radia samochodowego: ENTERTAIMENT RADIO (Arkusz 9)")
                elif any(k in raw_upper for k in ['SPEAKER LEFT', 'SPEAKER RIGHT', 'X239', 'X240', '-304', '-305']):
                    score += 4200
                    reasons.append("Arkusz zawiera głośniki radia (-304/-305) lub złącza X239/X240")
                elif 'CAB' in title_upper and is_overview and any(k in raw_upper for k in ['QC5', 'QC6', 'QC7', 'QC8', 'X305']):
                    score += 2500
                    reasons.append("Złącza OEM radia w kabinie (-QC5..-QC8 / X305)")
            elif is_intercom_intent:
                if 'INTERCOM' in title_upper or str(sh.get('sheet_number')) == '27':
                    score += 6500
                    reasons.append("Dedykowany arkusz instalacji interkomu: INTERCOM (Arkusz 27)")
                elif any(k in raw_upper for k in ['SPEAKER INTERCOM', 'X45', 'X49', '-A101', 'LS PR', 'LS FH']):
                    score += 4200
                    reasons.append("Arkusz zawiera głośniki interkomu (X45/X49) lub centralę -A101")
            elif is_carnation_intent:
                if 'IONV MAP LIGHT SPEAKERS' in title_upper or str(sh.get('sheet_number')) == '13':
                    score += 6500
                    reasons.append("Dedykowany arkusz głośnika komunikatów Carnation w kabinie: IONV MAP LIGHT SPEAKERS (Arkusz 13 / X244)")
                elif 'PIR | PANIC' in title_upper or str(sh.get('sheet_number')) == '30':
                    score += 6000
                    reasons.append("Dedykowany arkusz głośnika komunikatów Carnation w przedziale pacjenta: PIR | PANIC (Arkusz 30 / X258)")
                elif any(k in raw_upper for k in ['SPEAKER CARNATION', '+MID-X244', '+WAA-X258', 'LT-CAB', 'LT SALOON']):
                    score += 4500
                    reasons.append("Arkusz zawiera złącze głośnika Carnation (X244 w kabinie lub X258 w przedziale)")
            else:
                # Ogólne zapytanie o głośniki (bez sprecyzowania systemu)
                if any(k in title_upper for k in ['SPEAKER', 'SPEAKERS', 'IONV MAP LIGHT SPEAKERS', 'INTERCOM', 'ENTERTAIMENT RADIO']):
                    score += 4000
                    reasons.append(f"Arkusz obwodów audio: {sh['sheet_title']}")
                elif any(k in raw_upper for k in ['SPEAKER CARNATION', 'SPEAKER INTERCOM', 'SPEAKER LEFT', 'SPEAKER RIGHT']):
                    score += 3000
                    reasons.append("Arkusz zawiera instalacje głośnikowe pojazdu")

        # 4. Dopasowanie tematu/tytułu arkusza (np. 'OUTLETS', 'HVAC', 'MARKER', 'SPEAKERS')
        for st in specific_tokens:
            if len(st) >= 3 and st in title_upper:
                score += 200 if not is_overview else 50
                reasons.append(f"Temat arkusza: {sh['sheet_title']}")
                break

        # 5. Aparaty i złącza z obwodu lub zapytania
        matched_circuit_devs = set()
        matched_primary_devices = set()
        for s in syms_on_sheet:
            sc = s["symbol_clean"].upper()
            sn = s["symbol_name"]
            if sn not in matched_syms:
                matched_syms.append(sn)

            # Sprawdź czy pasuje do kluczowych aparatów z usterki/wariantu
            is_primary = False
            if sc in primary_sym_set or sn.upper() in primary_sym_set:
                is_primary = True
            else:
                for ps_tok in primary_sym_set:
                    if len(ps_tok) >= 3 and (ps_tok == sc or ps_tok == sn.upper() or sc.endswith(ps_tok)):
                        is_primary = True
                        break

            is_circuit = False
            if sc in circuit_dev_set or sn.upper() in circuit_dev_set:
                is_circuit = True
            else:
                for cd_token in circuit_dev_set:
                    if len(cd_token) >= 3 and (cd_token == sc or cd_token == sn.upper() or sc.endswith(cd_token)):
                        is_circuit = True
                        break

            m_root = re.search(r"([XFKM][0-9]{1,4}[A-Z]?|RT[0-9]{1,4}|SP[0-9]{1,4})", sc)
            root_code = m_root.group(1) if m_root else sc

            if is_primary:
                # Dodawaj punkty tylko raz na unikalny aparat/złącze
                if root_code not in matched_primary_devices:
                    score += 500 if not is_overview else 150
                    matched_primary_devices.add(root_code)
                    reasons.append(f"Kluczowe złącze wariantu/usterki: {sn}")
                matched_circuit_devs.add(root_code)
            elif is_circuit:
                score += 80 if not is_overview else 30
                reasons.append(f"Złącze obwodu: {sn}")
                matched_circuit_devs.add(root_code)
            elif sc in specific_tokens or sn.upper() in specific_tokens:
                score += 40 if not is_overview else 15
                reasons.append(f"Aparat: {sn}")
                matched_circuit_devs.add(root_code)
            elif not has_specific and sc in generic_tokens:
                score += 10
                reasons.append(f"Sygnał: {sn}")

        # Trafienie bezpośrednie (arkusz zawiera kluczowe złącze ORAZ właściwy temat/kategorię układu)
        has_topic_match = (
            (category and str(category).strip().upper() in title_upper) or
            any(cp in title_upper for cp in compound_phrases if len(cp) >= 4) or
            any(st in title_upper for st in specific_tokens if len(st) >= 4 and st not in ["LIGHT", "SOCKET", "DOOR"]) or
            any(k in title_upper for k in ['HVAC', 'KLIMATYZACJA', 'OGRZEWANIE', 'MARKER'])
        )

        if not is_overview:
            # Schemat ideowy obwodu funkcjonalnego
            if len(matched_primary_devices) > 0:
                score += 4000
                reasons.append("Schemat ideowy obwodu funkcjonalnego")

                if has_topic_match:
                    score += 2000
                    reasons.append("Trafienie bezpośrednie (kluczowe złącze + właściwy obwód roboczy)")

            # Jeśli arkusz funkcjonalny zawiera WIĘCEJ NIŻ JEDNO UNIKALNE kluczowe złącze
            if len(matched_primary_devices) >= 2:
                score += 2500 * (len(matched_primary_devices) - 1)
                reasons.append(f"Arkusz łączący kluczowe złącza ({len(matched_primary_devices)} złączy: {', '.join(sorted(matched_primary_devices))})")

            # Premia synergii wielopunktowej (tylko gdy arkusz ma powiązanie tematyczne)
            if len(matched_circuit_devs) >= 2 and has_topic_match:
                score += 120 * min(len(matched_circuit_devs) - 1, 10)
                reasons.append(f"Wielopunktowe złącza obwodu ({len(matched_circuit_devs)} aparatów)")

        else:
            # Arkusze zestawienia / topologii wiązki (np. =BOX, =CAB)
            # Zawierają złącza z natury spisu wiązki, więc otrzymują umiarkowaną punktację i NIE dostają bonusu synergii
            if len(matched_primary_devices) > 0:
                score += 300
                reasons.append(f"Topologia wiązki zawiera złącze: {', '.join(sorted(matched_primary_devices))}")

            if len(matched_primary_devices) >= 2:
                score += 400
                reasons.append(f"Tabela złączy wiązki ({len(matched_primary_devices)} złączy)")

            if len(matched_circuit_devs) >= 2:
                score += min(20 * len(matched_circuit_devs), 150)

        # 5. Słowa kluczowe w treści arkusza (raw_text)
        for st in specific_tokens:
            if len(st) >= 4 and st in raw_upper:
                cnt = raw_upper.count(st)
                score += min(cnt * 5, 30)

        # Bonus dla aktywnej roboczej wiązki
        if sh["is_active"]:
            score += 50

        # Filtrowanie szumu: jeśli zapytanie było specyficzne, arkusze o znikomej punktacji odrzucamy
        min_threshold = 40 if has_specific else 5
        if score >= min_threshold:
            if score > max_score and sh["is_active"]:
                max_score = score
            scored_results.append({
                "schematic_id": sh["schematic_id"],
                "filename": sh["filename"],
                "project_name": sh["project_name"],
                "revision_name": sh["revision_name"],
                "revision_date": sh["revision_date"],
                "is_active": sh["is_active"],
                "page_number": sh["page_number"],
                "sheet_number": sh["sheet_number"],
                "sheet_title": sh["sheet_title"],
                "section_code": sh["section_code"],
                "sheet_type": "overview" if is_overview else "circuit",
                "relevance_score": score,
                "match_reasons": list(dict.fromkeys(reasons))[:3],
                "matched_symbols": matched_syms[:8],
                "pdf_url": f"/api/zuken/pdf/view/{sh['schematic_id']}#page={sh['page_number']}"
            })

    # Sortowanie: najpierw aktywna wersja wiązki, potem najwyższy wynik relewancji, potem numer strony
    scored_results.sort(key=lambda x: (-x["is_active"], -x["relevance_score"], x["page_number"]))

    # Oznaczamy bezwzględnego zwycięzcę jako główny rekomendowany arkusz
    if scored_results:
        top_item = scored_results[0]
        if top_item["is_active"] and top_item["relevance_score"] >= 90:
            top_item["is_primary_match"] = True

    return scored_results[:limit]


def sync_all_knowledge_base():
    """Skanuje katalog Baza wiedzy (wraz z podfolderami) i importuje pliki XLSX oraz PDF."""
    init_zuken_tables()
    if not os.path.exists(BAZA_WIEDZY_DIR):
        return {"status": "error", "message": f"Katalog {BAZA_WIEDZY_DIR} nie istnieje."}

    results = []
    for root, dirs, files in os.walk(BAZA_WIEDZY_DIR):
        parent_dir = os.path.basename(root)
        ps_code_hint = parent_dir if re.match(r"^PS\d+", parent_dir, re.I) else None

        for f in files:
            full_path = os.path.join(root, f)
            if f.endswith(".xlsx") and not f.startswith("~$"):
                f_lower = f.lower()
                if f_lower.startswith("bom") or "bom" in f_lower:
                    items_cnt, devs_cnt, msg = import_zuken_bom_xlsx(full_path, ps_code=ps_code_hint)
                    results.append({"type": "bom_xlsx", "file": f, "articles": items_cnt, "devices": devs_cnt, "message": msg})
                else:
                    count, msg = import_zuken_xlsx(full_path)
                    results.append({"type": "xlsx", "file": f, "connections": count, "message": msg})
            elif f.endswith(".pdf") and not f.startswith("~$"):
                sch_id, sym_count, msg = index_zuken_pdf(full_path, ps_code=ps_code_hint)
                results.append({"type": "pdf", "file": f, "schematic_id": sch_id, "symbols": sym_count, "message": msg})

    return {"status": "success", "results": results}


# ═══════════════════════════════════════════════════════════════════
# SŁOWNIK SKRÓTÓW - WYJAŚNIANIE OZNACZEŃ
# ═══════════════════════════════════════════════════════════════════
def get_glossary_dict():
    """Zwraca słownik skrótów z bazy."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT prefix, category, desc_pl, desc_en FROM zuken_glossary;")
    rows = cur.fetchall()
    conn.close()
    return {r["prefix"]: dict(r) for r in rows}


def explain_device_code(code, glossary_map=None):
    """
    Rozbija kod aparatu/złącza (np. '=BOX+TWL-X346') na czytelny opis.
    Zwraca słownik z opisem systemu, lokalizacji i typu aparatu.
    """
    if not code:
        return ""
    if glossary_map is None:
        glossary_map = get_glossary_dict()

    parts = []
    # Sprawdź system (=)
    m_sys = re.search(r"(=[A-Za-z0-9_]+)", code)
    if m_sys and m_sys.group(1) in glossary_map:
        parts.append(glossary_map[m_sys.group(1)]["desc_pl"])

    # Sprawdź lokalizację (+)
    m_loc = re.search(r"(\+[A-Za-z0-9_]+)", code)
    if m_loc and m_loc.group(1) in glossary_map:
        parts.append(glossary_map[m_loc.group(1)]["desc_pl"])

    # Sprawdź typ aparatu (-)
    m_dev = re.search(r"(-[A-Za-z]+)", code)
    if m_dev:
        # dopasuj najdłuższy pasujący prefiks (np. -FH przed -F)
        dev_prefix = m_dev.group(1)
        found_desc = None
        for k in sorted(glossary_map.keys(), key=lambda x: -len(x)):
            if dev_prefix.startswith(k):
                found_desc = glossary_map[k]["desc_pl"]
                break
        if found_desc:
            parts.append(found_desc)

    return " → ".join(parts) if parts else code


# ═══════════════════════════════════════════════════════════════════
# PARSER RAPORTÓW KONFIGURACYJNYCH STEROWNIKA CARNATION GENESIS (EVPSS)
# ═══════════════════════════════════════════════════════════════════
_CARNATION_CACHE = {}


def parse_carnation_html(file_path):
    """Parsuje plik raportu konfiguracyjnego Carnation Genesis EVPSS (HTML)."""
    if not os.path.exists(file_path):
        return None

    mtime = os.path.getmtime(file_path)
    if file_path in _CARNATION_CACHE and _CARNATION_CACHE[file_path].get("_mtime") == mtime:
        return _CARNATION_CACHE[file_path]

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        info = {
            "_mtime": mtime,
            "filename": os.path.basename(file_path),
            "filepath": file_path,
            "version": "",
            "vehicle": "",
            "outputs": {},
            "inputs": {},
            "notifications": {},
            "rules": []
        }

        # Wersja konfiguracji
        m_ver = re.search(r"Configuration Version:.*?<td>([^<]+)</td>", content, re.DOTALL)
        if m_ver:
            info["version"] = m_ver.group(1).strip()

        # Pojazd
        m_veh = re.search(r"Vehicle:.*?<td>([^<]+)</td>", content, re.DOTALL)
        if m_veh:
            info["vehicle"] = m_veh.group(1).strip()

        # Wyjścia cyfrowe (Output Modules)
        for m in re.finditer(r"<td>(O[1-3]\.[0-9]+:\s*[^<]+)</td>\s*<td>([0-9]+A)", content):
            name = m.group(1).strip()
            current = m.group(2).strip()
            code = name.split(":")[0].strip()
            func_name = name.split(":", 1)[1].strip() if ":" in name else name
            info["outputs"][code] = {
                "code": code,
                "full_name": name,
                "function": func_name,
                "max_current": current
            }

        # Wejścia cyfrowe (Digital Inputs)
        for m in re.finditer(r"<td>([0-9]+)</td><td>(I[1-3]\.[0-9]+:\s*[^<]*)</td>", content):
            num = m.group(1).strip()
            name = m.group(2).strip()
            code = name.split(":")[0].strip()
            func_name = name.split(":", 1)[1].strip() if ":" in name else name
            info["inputs"][code] = {
                "num": num,
                "code": code,
                "full_name": name,
                "function": func_name
            }

        # Komunikaty (Notifications N...)
        for m in re.finditer(r"<td>(N[0-9]+:\s*[^<]+)</td>", content):
            n_full = m.group(1).strip()
            n_code = n_full.split(":")[0].strip()
            n_desc = n_full.split(":", 1)[1].strip() if ":" in n_full else ""
            if n_desc:
                info["notifications"][n_code] = {
                    "code": n_code,
                    "full_name": n_full,
                    "description": n_desc
                }

        # Reguły automatyki (Auto-Functions AF...)
        for m in re.finditer(r"<tr align=[\"']center[\"']><td>([0-9]+)</td><td>(AF[0-9]+:[^<]*)</td>(.*?)</tr>", content, re.DOTALL):
            af_idx = m.group(1).strip()
            af_name = m.group(2).strip()
            body = m.group(3)
            actions = [re.sub(r"<[^>]+>", "", act).strip() for act in re.findall(r"<p>(.*?)</p>", body)]
            info["rules"].append({
                "index": af_idx,
                "name": af_name,
                "actions": actions
            })

        _CARNATION_CACHE[file_path] = info
        return info
    except Exception as e:
        print(f"[CARNATION PARSER ERROR] Błąd parsowania {file_path}: {e}")
        return None


def get_carnation_diagnostic_info(ps_code=None, query_text=""):
    """
    Odnajduje plik konfiguracyjny Carnation Genesis w Bazie wiedzy
    i wyciąga z niego kontekstowe informacje dla podanego zapytania diagnostycznego.
    """
    html_files = []
    if os.path.exists(BAZA_WIEDZY_DIR):
        for root, _, files in os.walk(BAZA_WIEDZY_DIR):
            for f in files:
                if f.lower().endswith(".html"):
                    html_files.append(os.path.join(root, f))

    if not html_files:
        return None

    selected_file = None
    if ps_code:
        for hf in html_files:
            if str(ps_code).upper() in hf.upper():
                selected_file = hf
                break
    if not selected_file:
        selected_file = html_files[0]

    parsed = parse_carnation_html(selected_file)
    if not parsed:
        return None

    q_upper = (query_text or "").upper()
    tokens = re.findall(r"[A-Za-z0-9_]+", q_upper)

    result = {
        "version": parsed.get("version", ""),
        "filename": parsed.get("filename", ""),
        "vehicle": parsed.get("vehicle", ""),
        "relevant_outputs": [],
        "relevant_inputs": [],
        "controlling_rules": [],
        "audio_messages": [],
        "battery_thresholds": [],
        "diagnostic_summary": ""
    }

    # ═══════════════════════════════════════════════════════════════
    # 1. DOPASOWYWANIE WYJŚĆ CYFROWYCH (OUTPUT MODULES O1.1 - O3.16)
    # ═══════════════════════════════════════════════════════════════
    OUTPUT_KEYWORDS = {
        # Oświetlenie
        "MAP LIGHT": ["O1.3"],
        "MAPA": ["O1.3"],
        "OŚWIETLENIE MAPOWE": ["O1.3"],
        "LIGHTBAR": ["O1.4"],
        "BELKA": ["O1.4"],
        "LOW PWR": ["O1.4"],
        "HEADLAMP": ["O2.2"],
        "DŁUGIE": ["O2.2"],
        "BŁYSK DROGOWYCH": ["O2.2"],
        "GRILLE": ["O2.4"],
        "WING": ["O2.4"],
        "GRILL": ["O2.4"],
        "FRONT BLUES": ["O2.5"],
        "BLUES": ["O2.4", "O2.5", "O2.7", "O2.8", "O2.13"],
        "NIEBIESKIE": ["O2.4", "O2.5", "O2.7", "O2.8", "O2.13"],
        "PUDDLE": ["O2.6"],
        "PROG": ["O2.6"],
        "STOPIEŃ": ["O2.6"],
        "BLAST": ["O2.7"],
        "BODY BLUES": ["O2.8"],
        "BOCZNE NIEBIESKIE": ["O2.8"],
        "REAR REDS": ["O2.11", "O2.16"],
        "CZERWONE": ["O2.11", "O2.16"],
        "REAR BLUES": ["O2.13"],
        "TYLNE NIEBIESKIE": ["O2.13"],
        "AIRPORT": ["O2.14"],
        "LOTNISKOWE": ["O2.14"],
        "SCENE": ["O2.15", "O3.6", "O3.14"],
        "ROBOCZE": ["O2.15", "O3.6", "O3.7", "O3.14", "O3.15"],
        "REAR SCENE": ["O2.15"],
        "SALOON BRIGHT": ["O3.2"],
        "JASNE": ["O3.2"],
        "ŚWIATŁO GŁÓWNE": ["O3.2"],
        "SWIATLO GLOWNE": ["O3.2"],
        "SALOON DIM": ["O3.3"],
        "PRZYCIEMNIONE": ["O3.3"],
        "NOCNE": ["O3.3"],
        "TRAUMA": ["O3.4"],
        "SALOON BLUE": ["O3.4"],
        "LOCKER LIGHT": ["O3.5"],
        "SCHOWEK": ["O3.5"],
        "SCHOWKA": ["O3.5"],
        "LEFT SCENE": ["O3.6"],
        "LEFT ALLEY": ["O3.7"],
        "ALLEY": ["O3.7", "O3.15"],
        "SPOTS": ["O3.12"],
        "SPOT": ["O3.12"],
        "PUNKTY ŚWIETLNE": ["O3.12"],
        "RIGHT SCENE": ["O3.14"],
        "RIGHT ALLEY": ["O3.15"],

        # Gniazda i zasilania
        "GNIAZDO 1": ["O1.11"],
        "GNIAZDKO 1": ["O1.11"],
        "JACK 1": ["O1.11"],
        "JACK SKT 1": ["O1.11"],
        "GNIAZDO 2": ["O2.3"],
        "GNIAZDKO 2": ["O2.3"],
        "JACK 2": ["O2.3"],
        "JACK SKT 2": ["O2.3"],
        "GNIAZDO 3": ["O2.12"],
        "GNIAZDKO 3": ["O2.12"],
        "JACK 3": ["O2.12"],
        "JACK SKT 3": ["O2.12"],
        "GNIAZDO 4": ["O3.16"],
        "GNIAZDKO 4": ["O3.16"],
        "JACK 4": ["O3.16"],
        "JACK SKT 4": ["O3.16"],
        "GNIAZDO": ["O1.11", "O2.3", "O2.12", "O3.16", "O2.10"],
        "GNIAZDKO": ["O1.11", "O2.3", "O2.12", "O3.16", "O2.10"],
        "SOCKET": ["O1.11", "O2.3", "O2.12", "O3.16", "O2.10"],
        "USB": ["O2.10"],
        "ŁADOWARKA": ["O2.10"],
        "POWER LOAD": ["O1.5"],
        "IGN TIMED": ["O1.6"],
        "ZASILANIE CZASOWE": ["O1.6"],

        # Wentylacja, klimatyzacja i ogrzewanie
        "HEATER": ["O1.2"],
        "WEBASTO": ["O1.2"],
        "EBERSPACHER": ["O1.2"],
        "OGRZEWANIE": ["O1.2"],
        "INTAKE": ["O1.7", "O1.16"],
        "NAWIEW": ["O1.7", "O1.16"],
        "EXTRACT": ["O1.8", "O1.15"],
        "WYCIĄG": ["O1.8", "O1.15"],
        "WYCIAG": ["O1.8", "O1.15"],
        "WENTYLATOR": ["O1.7", "O1.8", "O1.15", "O1.16", "O3.10"],
        "FAN": ["O1.7", "O1.8", "O1.15", "O1.16", "O3.10"],
        "FLOOR FAN": ["O3.10"],
        "PODŁOGOWY": ["O3.10"],
        "A/C": ["O1.9"],
        "KLIMATYZACJA": ["O1.9", "O1.10"],
        "CLIMATE": ["O1.10"],

        # Sprzęt medyczny i wyposażenie
        "INKUBATOR": ["O1.1", "O2.1"],
        "INCUBATOR": ["O1.1", "O2.1"],
        "STRYKER": ["O3.1"],
        "NOSZE": ["O3.1"],
        "STRETCHER": ["O3.1"],
        "CORPULS": ["O3.8", "O3.9"],
        "C3": ["O3.8", "O3.9"],
        "DEFIBRYLATOR": ["O3.8"],
        "MONITOR C3": ["O3.9"],
        "LSU": ["O3.11"],
        "SSAK": ["O3.11"],
        "PRZETWORNICA": ["O3.13"],
        "INVERTER": ["O3.13"],
        "230V": ["O3.13"],

        # Interkom pokładowy Wolfelec (zasilanie z wyjścia O1.14)
        "INTERCOM": ["O1.14"],
        "INTERKOM": ["O1.14"],
        "DOMOFON": ["O1.14"],
        "WOLFELEC": ["O1.14"],
        "REVERSE ALARM": ["O1.12"],
        "BRZĘCZYK COFANIA": ["O1.12"],
        "BRZECZYK": ["O1.12"],
        "RWS": ["O1.12"],
        "PARKING SENSOR": ["O1.13"],
        "CZUJNIKI COFANIA": ["O1.13"],
        "CZUJNIKI PARKOWANIA": ["O1.13"],
        "SYRENA": ["O2.9"],
        "SIREN": ["O2.9"]
    }

    matched_output_codes = set()
    for kw, codes in OUTPUT_KEYWORDS.items():
        if kw in q_upper:
            matched_output_codes.update(codes)

    # Bezpośrednie numery wyjść (np. O1.14, O3.2)
    for tok in tokens:
        if re.match(r"^O[1-3]\.[0-9]+$", tok):
            matched_output_codes.add(tok)

    for oc in matched_output_codes:
        if oc in parsed["outputs"]:
            result["relevant_outputs"].append(parsed["outputs"][oc])

    # ═══════════════════════════════════════════════════════════════
    # 2. DOPASOWYWANIE WEJŚĆ Z POJAZDU BAZOWEGO (DIGITAL INPUTS I1.1 - I1.24)
    # ═══════════════════════════════════════════════════════════════
    INPUT_KEYWORDS = {
        "ZAPŁON": ["I1.8"],
        "ZAPLON": ["I1.8"],
        "IGNITION": ["I1.8"],
        "KL15": ["I1.8"],
        "STACYJK": ["I1.8"],
        "D+": ["I1.4"],
        "LADOWAN": ["I1.4"],
        "ŁADOWAN": ["I1.4"],
        "ALTERNATOR": ["I1.4"],
        "WSTECZN": ["I1.5"],
        "REVERSE": ["I1.5"],
        "BIEG WSTECZN": ["I1.5"],
        "RĘCZN": ["I1.9"],
        "RECZN": ["I1.9"],
        "HANDBRAKE": ["I1.9"],
        "NOŻN": ["I1.3"],
        "NOZN": ["I1.3"],
        "FOOTBRAKE": ["I1.3"],
        "HAMULEC": ["I1.3", "I1.9"],
        "DRZWI KABINY": ["I1.13"],
        "CAB DOORS": ["I1.13"],
        "DRZWI SZOFERKI": ["I1.13"],
        "DRZWI TYLNE LEWE": ["I1.17"],
        "DRZWI TYLNE PRAWE": ["I1.18"],
        "DRZWI TYLNE": ["I1.17", "I1.18"],
        "REAR DOOR": ["I1.17", "I1.18"],
        "DRZWI BOCZNE": ["I1.19"],
        "SIDE DOOR": ["I1.19"],
        "PRZESUW": ["I1.19"],
        "WIND": ["I1.7"],
        "TAIL LIFT": ["I1.7"],
        "PRĘDKOŚ": ["I1.15"],
        "PREDKOS": ["I1.15"],
        "SPEED": ["I1.15"],
        "TACHOGRAF": ["I1.15"],
        "V-IMPULS": ["I1.15"],
        "BRZEGOW": ["I1.16"],
        "RETTBOX": ["I1.16"],
        "SHORE LINE": ["I1.16"],
        "SHORELINE": ["I1.16"],
        "PIR": ["I1.6", "I1.11"],
        "RUCHU": ["I1.6", "I1.11"],
        "ECO RUN": ["I1.12"],
        "ECORUN": ["I1.12"],
        "PANIC": ["I1.22"],
        "NAPADOW": ["I1.22"],
        "PAS": ["I1.24"],
        "PASY": ["I1.24"],
        "PASÓW": ["I1.24"],
        "SEATBELT": ["I1.24"],
        "WŁĄCZNIK ŚWIATEŁ PRZEDZIAŁU": ["I1.23"],
        "SALOON LT SW": ["I1.23"]
    }

    matched_input_codes = set()
    for kw, codes in INPUT_KEYWORDS.items():
        if kw in q_upper:
            matched_input_codes.update(codes)

    for tok in tokens:
        if re.match(r"^I[1-3]\.[0-9]+$", tok):
            matched_input_codes.add(tok)

    for ic in matched_input_codes:
        if ic in parsed["inputs"]:
            result["relevant_inputs"].append(parsed["inputs"][ic])

    # ═══════════════════════════════════════════════════════════════
    # 3. WYKRYWANIE POWIĄZANYCH REGUŁ LOGIKI (AF...) I KOMUNIKATÓW (N...)
    # ═══════════════════════════════════════════════════════════════
    all_matched_codes = list(matched_output_codes) + list(matched_input_codes)
    for r in parsed["rules"]:
        actions_txt = " ".join(r["actions"])
        if any(code in actions_txt or code in r["name"] for code in all_matched_codes):
            # Wykryj powiązane powiadomienia
            m_notif = re.search(r"\b(N[0-9]+)\b", actions_txt)
            if m_notif and m_notif.group(1) in parsed["notifications"]:
                result["audio_messages"].append(parsed["notifications"][m_notif.group(1)]["full_name"])

            result["controlling_rules"].append({
                "rule": r["name"],
                "actions": r["actions"][:3]
            })

    # Specyficzne komunikaty głosowe powiązane z głośnikiem Carnation
    is_carnation_speaker = any(k in q_upper for k in ["CARNATION", "EVPSS", "KOMUNIKAT", "OSTRZEŻ", "OSTRZEZ"]) or (
        any(k in q_upper for k in ["GŁOŚNIK", "GLOSNIK", "SPEAKER"]) and not any(k in q_upper for k in ["RADIO", "RADIA", "INTERCOM", "INTERKOM"])
    )
    if is_carnation_speaker:
        voice_keys = ["N26", "N42", "N51", "N24", "N25", "N20", "N21"]
        for vk in voice_keys:
            if vk in parsed["notifications"]:
                fn = parsed["notifications"][vk]["full_name"]
                if fn not in result["audio_messages"]:
                    result["audio_messages"].append(fn)

    # Informacje o akumulatorach i odcięciach (Load Shedding)
    is_battery_query = any(k in q_upper for k in ["AKUMULATOR", "BATERIA", "BATTERY", "NAPIĘCIE", "NAPIECIE", "LOAD SHED", "ODCIĘCIE"])
    if is_battery_query:
        result["battery_thresholds"] = [
            {"name": "Aux. Bat (Akumulator medyczny)", "cutoff": "12.1V (ostrzeżenie) / 12.2V (powrót)"},
            {"name": "Chass. Batt (Akumulator podwozia)", "cutoff": "12.0V (ostrzeżenie) / 12.2V (powrót)"},
            {"name": "Comms. Bat (Akumulator łączności)", "cutoff": "12.1V (ostrzeżenie) / 12.2V (powrót)"}
        ]

    # ═══════════════════════════════════════════════════════════════
    # 4. SYNTEZA PODSUMOWANIA DIAGNOSTYCZNEGO
    # ═══════════════════════════════════════════════════════════════
    summary_parts = []
    if is_carnation_speaker and not any(k in q_upper for k in ["INTERCOM", "INTERKOM", "RADIO", "RADIA"]):
        summary_parts.append(
            "Głośniki komunikatów Carnation w kabinie (=CAB+MID-X244) oraz w przedziale medycznym (=BOX+WAA-X258) "
            "odtwarzają komunikaty głosowe i ostrzeżenia sterownika Carnation Genesis EVPSS (m.in. niezapięte pasy, otwarte drzwi, stan zasilania)."
        )

    if result["relevant_outputs"]:
        outs_desc = ", ".join(f"{o['code']} ({o['function']}, {o['max_current']})" for o in result["relevant_outputs"][:4])
        summary_parts.append(f"Zidentyfikowano wyjścia modułów OPM Carnation: {outs_desc}.")

    if result["relevant_inputs"]:
        ins_desc = ", ".join(f"{i['code']} ({i['function']})" for i in result["relevant_inputs"][:4])
        summary_parts.append(f"Sygnały wejściowe z pojazdu bazowego: {ins_desc}.")

    if result["controlling_rules"]:
        rules_desc = ", ".join(r["rule"].split(":")[0] for r in result["controlling_rules"][:3])
        summary_parts.append(f"Układ sterowany automatyką EVPSS: reguły {rules_desc}.")

    if is_battery_query:
        summary_parts.append("Aktywny system 3-stopniowego odcinania odbiorników (Load Shedding 1/2/3 po spadku napięcia Aux < 12.1V).")

    if not summary_parts:
        summary_parts.append(
            f"Zarejestrowano pełną konfigurację sterownika Carnation Genesis EVPSS (v{parsed.get('version', '1.81a')}): "
            f"3 moduły wyjściowe ({len(parsed['outputs'])} wyjść O1.1-O3.16), {len(parsed['inputs'])} wejść cyfrowych auta bazowego, "
            f"{len(parsed['rules'])} reguł automatyki i {len(parsed['notifications'])} komunikatów."
        )

    result["diagnostic_summary"] = " ".join(summary_parts)
    return result


# ═══════════════════════════════════════════════════════════════════
# SILNIK DIAGNOSTYCZNY (LOCAL SMART DIAGNOSTICS ENGINE)
# ═══════════════════════════════════════════════════════════════════
def find_matching_projects(ps_code=None, client=None):
    """Zwraca listę projektów Zukena pasujących do podanego PS lub klienta."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM zuken_projects ORDER BY revision_date DESC, id DESC;")
    all_projs = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not all_projs:
        return []

    matched = []
    # 1. Dopasowanie po PS
    if ps_code:
        ps_clean = str(ps_code).strip().upper()
        for p in all_projs:
            if ps_clean in (p.get("ps_codes") or "").upper() or ps_clean in (p.get("project_name") or "").upper():
                matched.append(p)

    # 2. Dopasowanie po Kliencie
    if not matched and client:
        cl_clean = str(client).strip().upper()
        for p in all_projs:
            p_cl = (p.get("client") or "").upper()
            if any(k in cl_clean for k in ["EOE", "EAST OF ENGLAND"]) and "EOE" in p_cl:
                matched.append(p)
            elif any(k in cl_clean for k in ["LAS", "LONDON"]) and "LAS" in p_cl:
                matched.append(p)

    # 3. Jeśli brak specyficznego dopasowania, zwróć aktywne projekty
    return matched if matched else all_projs


def format_wire_length(val):
    """
    Formatuje długość przewodu w mm do czytelnego formatu (m i mm/cm)
    wraz z podpowiedzią lokalizacyjną (np. krótka zworka vs wiązka wzdłużna pojazdu).
    """
    if not val:
        return ""
    try:
        val_clean = str(val).replace(",", ".").strip()
        num = float(val_clean)
        if num <= 0:
            return ""
        if num >= 1000:
            meters = num / 1000.0
            mm_int = int(round(num))
            hint = "wiązka długa / wzdłużna" if meters >= 3.0 else "wiązka średnia"
            return f"{meters:.2f} m ({mm_int} mm) • {hint}"
        elif num >= 100:
            cm = num / 10.0
            mm_int = int(round(num))
            return f"{cm:.0f} cm ({mm_int} mm) • odcinek lokalny"
        else:
            mm_int = int(round(num))
            return f"{mm_int} mm • krótka zworka / mostek"
    except Exception:
        return str(val)


def diagnose_defect(element="", typ="", opisProblem="", ps_code=None, client=None, vin=None, record_id=None, solution_id=None):
    """
    Główna funkcja diagnostyczna:
    - Analizuje opis usterki oraz powiązane warianty naprawy (solutions),
    - Odnajduje właściwy schemat i powiązane obwody w tabeli Zuken,
    - Buduje trasę przewodów i wskazuje punkty pomiarowe (złącza, piny, kolory kabli),
    - Porównuje rewizje schematów dla danej serii (np. zmiany wiązki w trakcie produkcji!),
    - Przeszukuje historię napraw pod kątem sprawdzonych rozwiązań,
    - Wyjaśnia kody techniczne aparatów za pomocą słownika.
    """
    init_zuken_tables()
    glossary_map = get_glossary_dict()

    conn = get_db()
    cur = conn.cursor()

    # ═══════════════════════════════════════════════════════════════
    # POBRANIE WARIANTÓW ROZWIĄZAŃ DLA TEJ USTERKI (JEŚLI ISTNIEJĄ)
    # ═══════════════════════════════════════════════════════════════
    current_record_solutions = []
    focused_solution = None

    if record_id:
        cur.execute("""
            SELECT id, record_id, numer, tytul, opis, created_by, created, tytul_en, opis_en
            FROM solutions
            WHERE record_id = ?
            ORDER BY numer ASC;
        """, (record_id,))
        current_record_solutions = [dict(r) for r in cur.fetchall()]
        if solution_id:
            focused_solution = next((s for s in current_record_solutions if str(s.get("id")) == str(solution_id)), None)

    # Ekstrakcja symboli i złączy ze wszystkich wariantów bieżącej usterki
    variant_symbols = set()
    variant_phrases = []
    sols_to_extract = [focused_solution] if focused_solution else current_record_solutions
    for sol in sols_to_extract:
        s_text = f"{sol.get('tytul', '')} {sol.get('opis', '')}"
        found_s = re.findall(r"\b(?:[XFKM]-?[0-9]{1,4}[A-Z]?|X[0-9]{2,4}|FH[0-9]+|RT[0-9]+|[=+\-][A-Z0-9_\+\-]+)\b", s_text.upper())
        for s in found_s:
            clean_s = s.lstrip("-+=:")
            if len(clean_s) >= 2:
                variant_symbols.add(clean_s)
                variant_symbols.add(s)
        for ph in ["EXTERNAL SENSOR", "MARKER LIGHT", "SIDELIGHT RH", "SIDELIGHT LH", "SIDELIGHT", "TEMPERATURA", "CZUJNIK", "EBERSPACHER", "HVAC", "FRONT BLUES"]:
            if ph in s_text.upper() and ph not in variant_phrases:
                variant_phrases.append(ph)

    # Wybór projektów Zukena
    candidate_projects = find_matching_projects(ps_code, client)
    if not candidate_projects:
        # Uruchom synchronizację jeśli pusto
        sync_all_knowledge_base()
        candidate_projects = find_matching_projects(ps_code, client)

    # Ekstrakcja słów kluczowych do zapytań (z uwzględnieniem wariantu)
    base_search = f"{element} {typ} {opisProblem}".strip()
    if focused_solution:
        search_text = f"{element} {focused_solution.get('tytul', '')} {focused_solution.get('opis', '')}".strip()
    elif current_record_solutions:
        combined_sols = " ".join(f"{s.get('tytul', '')} {s.get('opis', '')}" for s in current_record_solutions)
        search_text = f"{base_search} {combined_sols}".strip()
    else:
        search_text = base_search

    tokens = re.findall(r"[A-Za-z0-9ĄĆĘŁŃÓŚŹŻ_\-\.\:\+]+", search_text.upper())
    for vs in variant_symbols:
        clean_vs = vs.lstrip("-+=:")
        if clean_vs not in tokens:
            tokens.append(clean_vs)
    
    # Słowa kluczowe i mapowania na sygnały/aparaty Zuken
    SIGNAL_SYNONYMS = {
        "12V": ["12V", "12 V", "SOCKET"],
        "GNIAZDO": ["SOCKET", "12V"],
        "RUN": ["RUN", "ECORUN", "RUN LOCK"],
        "LOCK": ["RUN", "ECORUN", "RUN LOCK"],
        "ORTUS": ["ORTUS", "-A", "COMMS", "RFID"],
        "RFID": ["RFID", "ORTUS"],
        "WENTYLATOR": ["FAN", "SCAVENGING", "HVAC"],
        "HVAC": ["HVAC", "FAN", "HEATER"],
        "NIEBIESKA": ["BLUES", "FRONBLITZERS", "FRONT BLUES"],
        "WING": ["WING", "BLUES"],
        "GRILLE": ["FRONBLITZERS", "BLUES"],
        "OŚWIETLENIE": ["LIGHT", "BLUES", "LED"],
        "OSWIETLENIE": ["LIGHT", "BLUES", "LED"],
        "ŚWIATŁA": ["LIGHT", "BLUES", "CENTRAL LOCKING", "WARNING", "STEP LIGHT"],
        "SWIATLA": ["LIGHT", "BLUES", "CENTRAL LOCKING", "WARNING", "STEP LIGHT"],
        "ANTYKOLIZYJNE": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
        "ANTYKOLIZYJNA": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
        "ANTYKOLIZYJNYCH": ["CENTRAL LOCKING", "DOOR", "DIODE", "X245", "X246", "X248", "BLUES", "WARNING", "LIGHT", "STEP LIGHT"],
        "KOLIZYJNE": ["CENTRAL LOCKING", "DOOR", "DIODE", "BLUES", "WARNING"],
        "KRAŃCÓWKA": ["DOOR SWITCH", "SWITCH", "DOOR", "DPR", "DPL", "DRR", "DRL", "CENTRAL LOCKING"],
        "KRANCOWKA": ["DOOR SWITCH", "SWITCH", "DOOR", "DPR", "DPL", "DRR", "DRL", "CENTRAL LOCKING"],
        "KRAŃCÓWKI": ["DOOR SWITCH", "SWITCH", "DOOR", "DPR", "DPL", "DRR", "DRL", "CENTRAL LOCKING"],
        "KRANCOWKI": ["DOOR SWITCH", "SWITCH", "DOOR", "DPR", "DPL", "DRR", "DRL", "CENTRAL LOCKING"],
        "DIODA": ["DIODE", "X245", "X246", "X248"],
        "DIODY": ["DIODE", "X245", "X246", "X248"],
        "OSTRZEGAWCZE": ["WARNING", "BLUES", "BEACON", "LIGHT"],
        "STOPNIA": ["STEP LIGHT", "STEP", "DOOR"],
        "STOPNIE": ["STEP LIGHT", "STEP", "DOOR"],
        "SCHOWKA": ["LOCKER LIGHT", "LOCKER"],
        "SCHOWEK": ["LOCKER LIGHT", "LOCKER"],
        "DRZWI": ["DOOR", "DPR", "DPL", "DRR", "DRL", "CENTRAL LOCKING"],
        "DOOR": ["DOOR", "DPR", "DPL", "CENTRAL LOCKING"],
        "KFG": ["KFG", "-A15", "BSI"],
        "BSI": ["BSI", "CAB FEED", "KL 15"],
        "KAMERA": ["CAM", "CAMERA", "MONITOR"],
        "MONITOR": ["MONITOR", "DISPLAY", "CAM"],
        "REJESTRATOR": ["RECORDER", "CCTV", "CAM"],
        "EXTERNAL": ["EXTERNAL SENSOR", "X179", "HVAC"],
        "SENSOR": ["EXTERNAL SENSOR", "X179", "HVAC"],
        "MARKER": ["MARKER LIGHT", "SIDELIGHT", "X175"],
        "SIDELIGHT": ["MARKER LIGHT", "SIDELIGHT", "X175"],
        "CZUJNIK": ["EXTERNAL SENSOR", "X179", "HVAC", "SENSOR"],
        "TEMPERATURY": ["EXTERNAL SENSOR", "X179", "HVAC", "TEMP"],
        "TEMPERATURA": ["EXTERNAL SENSOR", "X179", "HVAC", "TEMP"],
        "EBERSPACHER": ["HVAC", "HEATER", "47 =BOX"],
        "GŁOŚNIK": ["SPEAKER", "LAUTSPRECHER"],
        "GLOSNIK": ["SPEAKER", "LAUTSPRECHER"],
        "GŁOŚNIKA": ["SPEAKER", "LAUTSPRECHER"],
        "GLOSNIKA": ["SPEAKER", "LAUTSPRECHER"],
        "GŁOŚNIKI": ["SPEAKER", "LAUTSPRECHER"],
        "GLOSNIKI": ["SPEAKER", "LAUTSPRECHER"],
        "SPEAKER": ["SPEAKER", "LAUTSPRECHER"],
        "SPEAKERS": ["SPEAKER", "LAUTSPRECHER"],
        "LAUTSPRECHER": ["SPEAKER"],
        "LT": ["LT", "LT-CAB", "LT CAB +", "LT CAB -", "LT SALOON"],
        "AUDIO": ["SPEAKER", "RADIO", "INTERCOM"],
        "INTERCOM": ["INTERCOM", "MID", "X45", "X49", "X39", "X40", "A101", "1612", "1613", "264", "267", "O1.14"],
        "INTERKOM": ["INTERCOM", "MID", "X45", "X49", "X39", "X40", "A101", "1612", "1613", "264", "267", "O1.14"],
        "TRENNWAND": ["TWM", "TWL", "TWR", "X296", "X292", "X10", "X11", "X43"],
        "GRODZIOWA": ["TWM", "TWL", "TWR", "X296", "X292", "X10", "X11", "X43"],
        "ŚCIANKA": ["TWM", "TWL", "TWR", "X296", "X292", "X10", "X11", "X43"],
        "X244": ["X244", "SPEAKER CARNATION", "LT CAB", "304_1"],
        "X258": ["X258", "Speaker Carnation", "LT SALOON", "472", "473"],
        "X45": ["X45", "SPEAKER INTERCOM CAB", "1612", "1613"],
        "X49": ["X49", "SPEAKER INTERCOM BOX", "264", "267"],
        "X239": ["X239", "SPEAKER LEFT", "300", "302", "304"],
        "X240": ["X240", "SPEAKER RIGHT", "298", "296", "305"],
        "X238": ["X238", "RADIO VOLUME", "306"],
        "A294": ["A294", "X244", "SPEAKER CARNATION", "LT CAB"],
        "X292": ["X292", "X296", "TWM", "BOX-CAB INTERFACE"],
        "X296": ["X296", "X292", "TWM", "BOX-CAB INTERFACE"],
        "X10": ["X10", "TWL", "LT CAB", "LT SALOON"],
        "CARNATION": ["CARNATION", "A15", "SPEAKER CARNATION", "LT CAB", "LT SALOON", "X244", "X258", "304_1", "472", "473"],
        "RADIO": ["ENTERTAIMENT RADIO", "RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "304", "305", "306"],
        "RADIA": ["ENTERTAIMENT RADIO", "RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "304", "305", "306"],
        "RADIOWE": ["ENTERTAIMENT RADIO", "RADIO", "SPEAKER LEFT", "SPEAKER RIGHT", "X239", "X240", "X238", "X305", "QC5", "QC6", "QC7", "QC8", "304", "305", "306"],
        "LEWY": ["SPEAKER LEFT", "Speaker LEFT 1", "Speaker LEFT 2", "X239", "QC5", "QC6", "300", "302"],
        "PRAWY": ["SPEAKER RIGHT", "Speaker RIGHT 1", "Speaker RIGHT 2", "X240", "QC7", "QC8", "298", "296"]
    }

    conn = get_db()
    cur = conn.cursor()

    # ═══════════════════════════════════════════════════════════════
    # HISTORIA NAPRAW I DOKUMENTY (Wyszukiwanie kontekstowe w bazie)
    # ═══════════════════════════════════════════════════════════════
    history_solutions = []
    st_upper = search_text.upper()
    is_carnation_query = any(k in st_upper for k in ["CARNATION", "EVPSS", "KOMUNIKAT", "OSTRZEŻ", "OSTRZEZ"])
    is_intercom_query = any(k in st_upper for k in ["INTERCOM", "INTERKOM", "DOMOFON", "WOLFELEC"])
    is_radio_query = any(k in st_upper for k in ["RADIO", "RADIA", "RADIOW", "LEWY", "PRAWY", "LEFT", "RIGHT", "BALANS"])

    if is_carnation_query:
        hist_sql = """
            SELECT r.id as record_id, r.projekt, r.element, r.opisProblem, s.id as solution_id, s.tytul, s.opis, s.created_by
            FROM records r
            JOIN solutions s ON s.record_id = r.id
            WHERE (r.element LIKE '%carnation%' OR r.opisProblem LIKE '%carnation%' OR s.tytul LIKE '%carnation%' OR s.opis LIKE '%carnation%' OR s.tytul LIKE '%X258%')
            ORDER BY r.created DESC
            LIMIT 6;
        """
        cur.execute(hist_sql)
    elif is_intercom_query:
        hist_sql = """
            SELECT r.id as record_id, r.projekt, r.element, r.opisProblem, s.id as solution_id, s.tytul, s.opis, s.created_by
            FROM records r
            JOIN solutions s ON s.record_id = r.id
            WHERE (r.element LIKE '%interkom%' OR r.opisProblem LIKE '%interkom%' OR r.element LIKE '%intercom%' OR s.tytul LIKE '%interkom%')
            ORDER BY r.created DESC
            LIMIT 6;
        """
        cur.execute(hist_sql)
    elif is_radio_query:
        hist_sql = """
            SELECT r.id as record_id, r.projekt, r.element, r.opisProblem, s.id as solution_id, s.tytul, s.opis, s.created_by
            FROM records r
            JOIN solutions s ON s.record_id = r.id
            WHERE (r.element LIKE '%radi%' OR r.opisProblem LIKE '%radi%' OR s.tytul LIKE '%radi%' OR s.tytul LIKE '%głośnik%')
            ORDER BY r.created DESC
            LIMIT 6;
        """
        cur.execute(hist_sql)
    else:
        hist_sql = """
            SELECT r.id as record_id, r.projekt, r.element, r.opisProblem, s.id as solution_id, s.tytul, s.opis, s.created_by
            FROM records r
            JOIN solutions s ON s.record_id = r.id
            WHERE r.element LIKE ? OR r.opisProblem LIKE ? OR r.typ LIKE ?
            ORDER BY r.created DESC
            LIMIT 6;
        """
        sample_q = f"%{element}%" if element else (f"%{tokens[0]}%" if tokens else "%")
        cur.execute(hist_sql, (sample_q, sample_q, sample_q))

    for r in cur.fetchall():
        history_solutions.append(dict(r))

    # Pobierz również powiązane dokumenty/schematy PDF z tabeli solution_documents
    schema_pdf_references = []
    extracted_sheet_numbers = set()
    extracted_history_symbols = set()

    if history_solutions:
        sol_ids = [h["record_id"] for h in history_solutions]
        s_placeholders = ",".join("?" for _ in sol_ids)
        cur.execute(f"""
            SELECT sd.id, sd.solution_id, sd.filename, sd.filesize, s.tytul, r.element
            FROM solution_documents sd
            JOIN solutions s ON sd.solution_id = s.id
            JOIN records r ON s.record_id = r.id
            WHERE r.id IN ({s_placeholders});
        """, sol_ids)
        for r in cur.fetchall():
            doc = dict(r)
            fn = doc.get("filename") or ""
            # Wykryj powiązany numer arkusza z nazwy pliku (np. "EoE arkusz 25 z 54...")
            m_sheet = re.search(r"(?:arkusz|ark|sheet|strona)\s*([0-9]+)", fn, re.IGNORECASE)
            if m_sheet:
                sh_num = m_sheet.group(1)
                doc["sheet_number"] = sh_num
                extracted_sheet_numbers.add(sh_num)
                # Odszukaj powiązanie w głównym schemacie Zuken danej serii
                cur.execute("""
                    SELECT sh.page_number, sch.id as schematic_id, sch.filename
                    FROM zuken_pdf_sheets sh
                    JOIN zuken_pdf_schematics sch ON sh.schematic_id = sch.id
                    WHERE sh.sheet_number = ?
                    ORDER BY sch.is_active DESC
                    LIMIT 1;
                """, (sh_num,))
                m_row = cur.fetchone()
                if m_row:
                    doc["master_schematic_id"] = m_row["schematic_id"]
                    doc["master_page_number"] = m_row["page_number"]
                    doc["master_filename"] = m_row["filename"]
            schema_pdf_references.append(doc)

        # Wyciągnij aparaty i symbole z potwierdzonych rozwiązań naprawczych
        for h in history_solutions:
            txt = f"{h.get('tytul', '')} {h.get('opis', '')}"
            found_syms = re.findall(r"\b(?:[XFKM]-?[0-9]{1,4}[A-Z]?|X[0-9]{2,4}|FH[0-9]+|RT[0-9]+|[=+\-][A-Z0-9_\+\-]+)\b", txt.upper())
            for s in found_syms:
                clean_s = s.lstrip("-+=:")
                if len(clean_s) >= 2:
                    # Ochrona przed pomyłkami w historycznych wpisach (np. X258 wpisany przy interkomie)
                    if is_intercom_query and clean_s in ["X258", "X244"]:
                        continue
                    if is_carnation_query and clean_s in ["X45", "X49", "X260", "A101"]:
                        continue
                    if is_radio_query and clean_s in ["X258", "X244", "X45", "X49", "X260", "A101"]:
                        continue
                    extracted_history_symbols.add(clean_s)

    expanded_queries = set()
    for tok in tokens:
        if len(tok) >= 3:
            expanded_queries.add(tok)
        for k, syns in SIGNAL_SYNONYMS.items():
            if k in tok or tok in k:
                for syn in syns:
                    expanded_queries.add(syn)

    # Priorytetyzacja zapytań o połączenia wiązki:
    # Wyodrębnienie fraz złożonych (np. '12V SOCKET 3', 'MARKER LIGHT') i kategoryzacja tokenów
    compound_phrases, specific_tokens, generic_tokens, has_specific = extract_query_phrases_and_tokens(search_text, expanded_queries)

    # 1. Dokładne frazy z wariantu, złożone (np. MARKER LIGHT, 12V SOCKET 3) oraz aparaty z historii i zapytania
    primary_queries = []
    for vp in variant_phrases:
        if vp not in primary_queries:
            primary_queries.append(vp)
    for vs in variant_symbols:
        clean_vs = vs.lstrip("-+=:")
        if clean_vs not in primary_queries:
            primary_queries.append(clean_vs)
    for cp in compound_phrases:
        if cp not in primary_queries:
            primary_queries.append(cp)
    for hs in extracted_history_symbols:
        if hs not in primary_queries:
            primary_queries.append(hs)
    for tok in tokens:
        if re.match(r"^[XFKM]-?[0-9]+", tok) or tok in ["X245", "X246", "X248"]:
            if tok not in primary_queries:
                primary_queries.append(tok)

    # 2. Specyficzne sygnały (dłuższe frazy i nazwy funkcji)
    secondary_queries = [q for q in expanded_queries if q not in primary_queries and len(q) >= 4]
    general_queries = [q for q in expanded_queries if q not in primary_queries and q not in secondary_queries]

    ordered_queries = primary_queries + secondary_queries + general_queries

    # Szukamy połączeń w wybranych projektach
    proj_ids = [p["id"] for p in candidate_projects] if candidate_projects else []
    proj_placeholders = ",".join("?" for _ in proj_ids) if proj_ids else "0"

    matched_connections = []
    seen_conn_keys = set()

    for q in ordered_queries[:16]:
        query_pattern = f"%{q}%"
        sql = f"""
            SELECT c.*, p.project_name, p.revision_name, p.revision_date
            FROM zuken_connections c
            JOIN zuken_projects p ON c.project_id = p.id
            WHERE c.project_id IN ({proj_placeholders})
              AND (c.signal LIKE ? OR c.from_device LIKE ? OR c.to_device LIKE ? OR c.cable_name LIKE ?)
            LIMIT 40;
        """
        params = proj_ids + [query_pattern, query_pattern, query_pattern, query_pattern]
        cur.execute(sql, params)
        for row in cur.fetchall():
            r_dict = dict(row)
            key = (r_dict["signal"], r_dict["from_device"], r_dict["from_pin"], r_dict["to_device"], r_dict["to_pin"])
            if key not in seen_conn_keys:
                seen_conn_keys.add(key)
                matched_connections.append(r_dict)

    # Posortuj połączenia tak, aby obwody powiązane z kluczowymi aparatami, historią i frazami były na samej górze
    def _conn_priority(c):
        score = 0
        txt = f"{c.get('from_device', '')} {c.get('to_device', '')} {c.get('signal', '')}".upper()
        for vp in variant_phrases:
            if vp.upper() in txt:
                score += 80
        for vs in variant_symbols:
            clean_vs = vs.lstrip("-+=:")
            if clean_vs.upper() in txt:
                score += 60
        for cp in compound_phrases:
            if cp.upper() in txt:
                score += 50
        for pq in primary_queries:
            if pq.upper() in txt:
                score += 15
        for sq in secondary_queries:
            if sq.upper() in txt:
                score += 2
        return score

    matched_connections.sort(key=lambda c: -_conn_priority(c))

    # Wyciągnij aparaty i sygnały z czołowych zidentyfikowanych obwodów do wyszukiwania w PDF
    candidate_circuit_devices = set()
    candidate_circuit_signals = set()
    for c in matched_connections[:15]:
        if c.get("from_device"):
            candidate_circuit_devices.add(c["from_device"])
        if c.get("to_device"):
            candidate_circuit_devices.add(c["to_device"])
        if c.get("signal"):
            candidate_circuit_signals.add(c["signal"])

    # ═══════════════════════════════════════════════════════════════
    # ANALIZA RÓŻNIC REWIZJI (REVISION DIFF)
    # ═══════════════════════════════════════════════════════════════
    revision_notes = []
    if len(candidate_projects) > 1:
        # Sprawdzamy czy są różne rewizje (np. 2025 vs 2026 poprawka drzwi)
        p_base = min(candidate_projects, key=lambda x: x.get("revision_date") or "")
        p_new = max(candidate_projects, key=lambda x: x.get("revision_date") or "")
        
        # Jeśli usterka dotyczy drzwi lub styków
        if any(k in search_text.upper() for k in ["DRZWI", "DOOR", "DPR", "DPL", "PRZESUW", "KRAŃCÓW", "KRANCOW"]):
            revision_notes.append({
                "type": "warning",
                "title": "Zmiana wiązki w trakcie serii (Poprawka drzwi)",
                "text": f"W projekcie {p_new['project_name']} wprowadzono rewizję instalacji drzwi ({p_new['revision_name']}). Nowe złącza wiązki to m.in. =BOX+DPR-X121. Upewnij się, który numer seryjny/datę produkcji ma sprawdzany ambulans."
            })
        else:
            revision_notes.append({
                "type": "info",
                "title": "Dostępne rewizje wiązki dla tego projektu",
                "text": f"W bazie zarejestrowano wersję bazową ({p_base['revision_name']}) oraz nowszą rewizję ({p_new['revision_name']})."
            })

    # ═══════════════════════════════════════════════════════════════
    # WYSZUKIWANIE W ARKUSZACH SCHEMATU PDF
    # ═══════════════════════════════════════════════════════════════
    all_circuit_devices = set(candidate_circuit_devices)
    all_circuit_devices.update(variant_symbols)
    all_extra_tokens = set(expanded_queries).union(variant_symbols).union(variant_phrases)

    # Kluczowe symbole priorytetowe z wariantu i zapytania
    primary_key_symbols = set(variant_symbols)
    for tok in tokens:
        if re.match(r"^[XFKM]-?[0-9]+", tok):
            primary_key_symbols.add(tok)

    pdf_sheet_matches = find_pdf_sheets_for_query(
        search_text,
        ps_code=ps_code,
        extra_tokens=all_extra_tokens,
        explicit_sheet_numbers=list(extracted_sheet_numbers) if extracted_sheet_numbers else None,
        circuit_devices=list(all_circuit_devices),
        circuit_signals=list(candidate_circuit_signals),
        primary_symbols=list(primary_key_symbols),
        category=typ
    )

    # ═══════════════════════════════════════════════════════════════
    # PRZYGOTOWANIE PUNTÓW KONTROLNYCH (TEST POINTS & CIRCUITS)
    # ═══════════════════════════════════════════════════════════════
    circuits_grouped = {}
    test_points = []
    involved_devices = set()

    for c in matched_connections[:25]:
        sig = c["signal"] or "ZASILANIE / SYGNAŁ BEZ NAZWY"
        if sig not in circuits_grouped:
            circuits_grouped[sig] = []

        from_desc = explain_device_code(c["from_device"], glossary_map)
        to_desc = explain_device_code(c["to_device"], glossary_map)

        # Znajdź arkusze w aktywnym schemacie PDF powiązane z tym połączeniem
        link_sheets = []
        item_tokens = []
        for dev_val in [c["from_device"], c["to_device"]]:
            if dev_val:
                item_tokens.append(dev_val)
                clean_d = re.sub(r"^[=+\-:]+", "", dev_val)
                if clean_d:
                    item_tokens.append(clean_d)
                m_dev = re.search(r"(-[A-Za-z0-9_]+)", dev_val)
                if m_dev:
                    item_tokens.append(m_dev.group(1))
                    item_tokens.append(m_dev.group(1).lstrip("-"))
        if sig and sig != "ZASILANIE / SYGNAŁ BEZ NAZWY":
            item_tokens.append(sig)
        if c.get("wire_number"):
            item_tokens.append(c["wire_number"])

        if item_tokens:
            tokens_p = ",".join("?" for _ in item_tokens)
            cur.execute(f"""
                SELECT DISTINCT sh.page_number, sh.sheet_number, sh.sheet_title, sch.id as schematic_id
                FROM zuken_pdf_symbols sym
                JOIN zuken_pdf_sheets sh ON sym.sheet_id = sh.id
                JOIN zuken_pdf_schematics sch ON sym.schematic_id = sch.id
                WHERE sch.is_active = 1
                  AND (sym.symbol_clean IN ({tokens_p}) OR sym.symbol_name IN ({tokens_p}))
                ORDER BY (
                    CASE 
                        WHEN sh.sheet_title LIKE '%OUTLET%' OR sh.sheet_title LIKE '%SOCKET%' THEN 0
                        WHEN sh.sheet_title LIKE '%DOOR%' THEN 0
                        WHEN sh.sheet_title LIKE '%BLUES%' THEN 0
                        WHEN sh.sheet_title LIKE '%HVAC%' THEN 0
                        WHEN sh.sheet_title LIKE '%MARKER%' THEN 0
                        ELSE 1
                    END
                ), sh.page_number ASC
                LIMIT 4;
            """, item_tokens + item_tokens)
            for r in cur.fetchall():
                link_sheets.append({
                    "page": r[0],
                    "sheet": r[1],
                    "title": r[2],
                    "schematic_id": r[3],
                    "url": f"/api/zuken/pdf/view/{r[3]}#page={r[0]}"
                })

        circuits_grouped[sig].append({
            "from": c["from_device"],
            "from_pin": c["from_pin"],
            "from_desc": from_desc,
            "to": c["to_device"],
            "to_pin": c["to_pin"],
            "to_desc": to_desc,
            "wire_color": c["wire_color"],
            "wire_type": c["wire_type"],
            "cross_section": c["cross_section"],
            "wire_number": c["wire_number"],
            "length": c.get("length", ""),
            "length_formatted": format_wire_length(c.get("length", "")),
            "project_rev": c["revision_name"],
            "sheets": link_sheets
        })

        if c["from_device"]:
            involved_devices.add((c["from_device"], from_desc))
        if c["to_device"]:
            involved_devices.add((c["to_device"], to_desc))

    # Wygenerowanie listy urządzeń i ich objaśnień
    device_glossary_list = [
        {"code": dev, "description": desc}
        for dev, desc in sorted(involved_devices) if desc and desc != dev
    ]

    conn.close()

    # ═══════════════════════════════════════════════════════════════
    # DEDYKOWANE KOMPONENTY Z BOM (ZŁĄCZA, BEZPIECZNIKI, OPRAWKI)
    # ═══════════════════════════════════════════════════════════════
    bom_dev_codes = set()
    for c in matched_connections:
        if c.get("from_device"):
            bom_dev_codes.add(c["from_device"])
        if c.get("to_device"):
            bom_dev_codes.add(c["to_device"])
    for tok in tokens:
        if len(tok) >= 2:
            bom_dev_codes.add(tok)
    for hs in extracted_history_symbols:
        bom_dev_codes.add(hs)
    for vs in variant_symbols:
        clean_vs = vs.lstrip("-+=:")
        if clean_vs:
            bom_dev_codes.add(clean_vs)

    bom_components = find_bom_components_for_devices(list(bom_dev_codes), ps_code=ps_code)

    # Informacje logiczne z kontrolera Carnation Genesis EVPSS (jeśli dostępne)
    carnation_logic = get_carnation_diagnostic_info(ps_code=ps_code, query_text=search_text)

    # Podsumowanie i wygenerowanie zaleceń krok po kroku
    recommendations = []
    if carnation_logic and carnation_logic.get("diagnostic_summary"):
        recommendations.append(f"🧠 Logika sterownika Carnation Genesis (EVPSS): {carnation_logic['diagnostic_summary']}")

    if focused_solution:
        recommendations.append(f"Ukierunkowano na Wariant {focused_solution.get('numer', '')}: {focused_solution.get('tytul', '')}. Sprawdź dedykowane arkusze schematu i złącza poniżej.")
    elif current_record_solutions:
        top_sol = current_record_solutions[0]
        sol_hint = f" ({top_sol.get('tytul')})" if top_sol.get("tytul") else ""
        recommendations.append(f"Uwzględniono {len(current_record_solutions)} warianty naprawy dla tej usterki{sol_hint}. Poniżej rekomendowane arkusze powiązanych obwodów.")
    elif history_solutions:
        top_sol = history_solutions[0]
        sol_hint = f" ({top_sol.get('tytul')})" if top_sol.get("tytul") else ""
        recommendations.append(f"Znaleziono w bazie wiedzy {len(history_solutions)} sprawdzone warianty naprawy dla tej usterki{sol_hint}. Sprawdź szczegółowy opis i dołączone arkusze.")

    if circuits_grouped:
        recommendations.append("Sprawdź obecność napięcia zasilania i masy na punktach początkowych i końcowych zidentyfikowanego obwodu.")
        recommendations.append("Sprawdź ciągłość przewodów pomiędzy złączami pośrednimi (zwróć uwagę na kolory i numery żył).")
        recommendations.append("Upewnij się, że wszystkie wtyczki wiązki są poprawnie zatrzaśnięte (brak wysuniętych pinów).")
        if bom_components:
            recommendations.append(f"Zidentyfikowano {len(bom_components)} komponentów i złączek w BOM dla tego obwodu. Sprawdź numery katalogowe, zdjęcia oraz karty produktów dostawców poniżej.")
        if pdf_sheet_matches:
            recommendations.append(f"Odnaleziono {len(pdf_sheet_matches)} arkuszy w schemacie PDF powiązanych z zapytaniem. Możesz otworzyć je bezpośrednio poniżej.")
    elif pdf_sheet_matches:
        recommendations.append(f"Odnaleziono {len(pdf_sheet_matches)} arkuszy w schemacie PDF odpowiadających szukanemu aparatowi/przewodowi. Zobacz szczegóły w sekcji lokalizacji arkuszy.")
    else:
        recommendations.append("Brak bezpośredniego dopasowania w schemacie Zuken dla tego hasła. Sprawdź oznaczenie złącza lub bezpiecznika bezpośrednio na schemacie PDF.")

    return {
        "status": "success",
        "search_query": search_text,
        "matched_projects": candidate_projects,
        "circuits": circuits_grouped,
        "total_circuits": len(circuits_grouped),
        "bom_components": bom_components,
        "total_bom_components": len(bom_components),
        "pdf_sheet_matches": pdf_sheet_matches,
        "device_glossary": device_glossary_list[:15],
        "history_solutions": history_solutions,
        "current_solutions": current_record_solutions,
        "focused_solution": focused_solution,
        "schema_pdf_references": schema_pdf_references,
        "revision_notes": revision_notes,
        "carnation_logic": carnation_logic,
        "recommendations": recommendations
    }


# ═══════════════════════════════════════════════════════════════════
# ZESTAWIENIA ZUKEN E3: SPIS ZŁĄCZY Z PINOUTEM, BEZPIECZNIKI, PRZEKAŹNIKI (PS)
# ═══════════════════════════════════════════════════════════════════

def _natural_sort_key(s):
    """Klucz sortowania naturalnego (np. '1', '2', '10', 'A', 'B')."""
    p = str(s or "").strip()
    if p.isdigit():
        return (0, int(p), "")
    m = re.match(r"^(\d+)(.*)$", p)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, p.lower())


def get_available_ps_projects():
    """
    Zwraca listę projektów PS wykrytych w katalogu Baza wiedzy oraz w bazie danych SQLite.
    Dla każdego projektu zwraca status dostępnych plików (BOM, Connection, PDF, E3S)
    oraz liczbę wygenerowanych złączy, bezpieczników i przekaźników.
    """
    init_zuken_tables()
    conn = get_db()
    cur = conn.cursor()

    # 1. Projekty z tabeli zuken_ps_summaries
    cur.execute("""
        SELECT ps_code, project_name, client, connectors_count, fuses_count, relays_count, generated_at, source_files
        FROM zuken_ps_summaries;
    """)
    summaries_map = {r["ps_code"]: dict(r) for r in cur.fetchall()}

    # 2. Projekty z tabeli zuken_projects
    cur.execute("""
        SELECT DISTINCT ps_codes, project_name, client
        FROM zuken_projects
        WHERE ps_codes IS NOT NULL AND ps_codes != '';
    """)
    db_projects = {}
    for r in cur.fetchall():
        for ps in r["ps_codes"].split(","):
            ps_clean = ps.strip().upper()
            if ps_clean and ps_clean not in db_projects:
                db_projects[ps_clean] = {
                    "project_name": r["project_name"],
                    "client": r["client"]
                }

    # 3. Projekty wykryte w strukturze podfolderów Baza wiedzy
    kb_projects = {}
    if os.path.exists(BAZA_WIEDZY_DIR):
        for entry in os.listdir(BAZA_WIEDZY_DIR):
            folder_path = os.path.join(BAZA_WIEDZY_DIR, entry)
            if os.path.isdir(folder_path) and entry != "zdjecia_komponentow":
                ps_code = entry.upper()
                try:
                    files = os.listdir(folder_path)
                except Exception:
                    files = []
                has_bom = any(f.lower().startswith("bom") and f.endswith(".xlsx") for f in files)
                has_conn = any(("connection" in f.lower() or f.lower().endswith("_con.xlsx")) and f.endswith(".xlsx") for f in files)
                has_pdf = any(f.lower().endswith(".pdf") for f in files)
                has_e3s = any(f.lower().endswith(".e3s") for f in files)

                kb_projects[ps_code] = {
                    "folder_name": entry,
                    "folder_path": folder_path,
                    "has_bom": has_bom,
                    "has_conn": has_conn,
                    "has_pdf": has_pdf,
                    "has_e3s": has_e3s,
                    "files_count": len(files)
                }

    all_ps_codes = sorted(set(list(db_projects.keys()) + list(kb_projects.keys()) + list(summaries_map.keys())))
    if not all_ps_codes and os.path.exists(os.path.join(BAZA_WIEDZY_DIR, "PS011871")):
        all_ps_codes = ["PS011871"]

    result = []
    for ps in all_ps_codes:
        kb_info = kb_projects.get(ps, {
            "folder_name": ps,
            "folder_path": os.path.join(BAZA_WIEDZY_DIR, ps),
            "has_bom": False,
            "has_conn": False,
            "has_pdf": False,
            "has_e3s": False,
            "files_count": 0
        })
        db_info = db_projects.get(ps, {})
        summ_info = summaries_map.get(ps, {})

        result.append({
            "ps_code": ps,
            "project_name": summ_info.get("project_name") or db_info.get("project_name") or f"Projekt {ps}",
            "client": summ_info.get("client") or db_info.get("client") or ("EOE Ambulance" if "EOE" in ps or ps == "PS011871" else "Pojazd specjalny"),
            "folder_name": kb_info["folder_name"],
            "exists_in_kb": os.path.exists(kb_info["folder_path"]),
            "has_bom": kb_info["has_bom"],
            "has_connection": kb_info["has_conn"],
            "has_pdf": kb_info["has_pdf"],
            "has_e3s": kb_info["has_e3s"],
            "files_count": kb_info["files_count"],
            "has_summaries": bool(summ_info.get("generated_at")),
            "connectors_count": summ_info.get("connectors_count", 0),
            "fuses_count": summ_info.get("fuses_count", 0),
            "relays_count": summ_info.get("relays_count", 0),
            "generated_at": summ_info.get("generated_at", "")
        })

    conn.close()
    return result


def generate_ps_technical_summaries(ps_code):
    """
    Ekstrahuje i generuje do bazy SQLite zestawienia dla wybranego projektu PS:
    1. Złącza z kompletnym pinoutem (Device, kody artykułów BOM, piny, sygnały, przewody, cele)
    2. Bezpieczniki (kod aparatu, wartość A, typ, oprawka, chronione obwody)
    3. Przekaźniki (kod aparatu, funkcja, typ, oprawka, rozpiska styków)
    """
    if not ps_code:
        return {"status": "error", "message": "Nie podano numeru PS."}

    ps_code = str(ps_code).strip().upper()
    init_zuken_tables()

    # Sprawdź czy pliki dla tego PS są w katalogu Baza wiedzy i zaimportuj jeśli potrzeba
    kb_ps_dir = os.path.join(BAZA_WIEDZY_DIR, ps_code)
    if os.path.exists(kb_ps_dir):
        try:
            for f in os.listdir(kb_ps_dir):
                full_path = os.path.join(kb_ps_dir, f)
                if f.endswith(".xlsx") and not f.startswith("~$"):
                    f_lower = f.lower()
                    if f_lower.startswith("bom") or "bom" in f_lower:
                        import_zuken_bom_xlsx(full_path, ps_code=ps_code)
                    else:
                        import_zuken_xlsx(full_path, ps_code=ps_code)
                elif f.endswith(".pdf") and not f.startswith("~$"):
                    index_zuken_pdf(full_path, ps_code=ps_code)
        except Exception as ex:
            print(f"[ZUKEN IMPORT WARNING] Błąd skanowania katalogu {kb_ps_dir}: {ex}")

    conn = get_db()
    cur = conn.cursor()

    # Znajdź projekty powiązane z tym PS
    cur.execute("""
        SELECT id, filename, project_name, client, revision_name
        FROM zuken_projects
        WHERE ps_codes LIKE ? OR filename LIKE ?
        ORDER BY id DESC;
    """, (f"%{ps_code}%", f"%{ps_code}%"))
    projects = [dict(r) for r in cur.fetchall()]

    if not projects:
        # Fallback jeśli domyślny projekt nie ma przypisanego numeru PS w nazwie
        cur.execute("SELECT id, filename, project_name, client, revision_name FROM zuken_projects ORDER BY id DESC;")
        projects = [dict(r) for r in cur.fetchall()]

    conn_proj_ids = [p["id"] for p in projects if "bom" not in p["filename"].lower()]
    bom_proj_ids = [p["id"] for p in projects if "bom" in p["filename"].lower()]

    if not conn_proj_ids and not bom_proj_ids:
        conn.close()
        return {"status": "error", "message": f"Brak zaimportowanych projektów Zuken dla {ps_code}."}

    # Wykryj format każdego projektu połączeń:
    # - format "CON" (*_CON.xlsx): kolumna wire_number wypełniona, signal = nazwa sygnału
    # - format "Connection" (Connection_*.xlsx): wire_number zawsze pusty, signal = numer przewodu
    con_format_ids = set()
    if conn_proj_ids:
        ph_fmt = ",".join("?" for _ in conn_proj_ids)
        cur.execute(f"""
            SELECT project_id FROM zuken_connections
            WHERE project_id IN ({ph_fmt}) AND wire_number IS NOT NULL AND wire_number != ''
            GROUP BY project_id;
        """, conn_proj_ids)
        con_format_ids = {r[0] for r in cur.fetchall()}

    def _norm_sig_wire(row):
        """Normalizuje parę (numer_przewodu, nazwa_sygnału) wg formatu projektu źródłowego."""
        sig = (row["signal"] or "").strip()
        wn = (row["wire_number"] or "").strip()
        if row["project_id"] in con_format_ids:
            return wn, sig
        return (wn or sig), (sig if wn else "")

    glossary = get_glossary_dict()

    # Usuń stare wpisy zestawień dla tego PS
    cur.execute("DELETE FROM zuken_ps_connectors WHERE ps_code = ?;", (ps_code,))
    cur.execute("DELETE FROM zuken_ps_fuses WHERE ps_code = ?;", (ps_code,))
    cur.execute("DELETE FROM zuken_ps_relays WHERE ps_code = ?;", (ps_code,))

    # ═══════════════════════════════════════════════════════════════
    # 1. GENEROWANIE SPISU ZŁĄCZY Z PINOUTEM
    # ═══════════════════════════════════════════════════════════════
    connectors_map = {}

    if conn_proj_ids:
        ph_conn = ",".join("?" for _ in conn_proj_ids)
        cur.execute(f"""
            SELECT project_id, signal, from_device, from_component, from_pin,
                   to_device, to_component, to_pin,
                   wire_number, wire_type, wire_color, cross_section, cable_name, length
            FROM zuken_connections
            WHERE project_id IN ({ph_conn});
        """, conn_proj_ids)
        conn_rows = cur.fetchall()

        for r in conn_rows:
            f_dev = (r["from_device"] or "").strip()
            t_dev = (r["to_device"] or "").strip()
            f_pin = (r["from_pin"] or "").strip()
            t_pin = (r["to_pin"] or "").strip()
            w_num, sig = _norm_sig_wire(r)
            w_col = (r["wire_color"] or "").strip()
            w_cs = (r["cross_section"] or "").strip()
            w_type = (r["wire_type"] or "").strip()
            w_len = (r["length"] or "").strip()
            w_cab = (r["cable_name"] or "").strip()
            if not (w_num or sig or w_col or w_cs or w_type or w_len or w_cab):
                # "Ślepy" zapis bez żadnych danych przewodu — artefakt schematu
                continue

            for dev, pin, target_dev, target_pin in [
                (f_dev, f_pin, t_dev, t_pin),
                (t_dev, t_pin, f_dev, f_pin)
            ]:
                if not dev or not pin:
                    continue
                # Filtrujemy tylko rzeczywiste złącza (-X)
                dev_up = dev.upper()
                is_conn = ("-X" in dev_up or ":X" in dev_up or dev_up.startswith("X") or "/-X" in dev_up)
                if not is_conn:
                    continue

                if dev not in connectors_map:
                    clean_code = clean_device_code(dev)
                    m_sys = re.search(r"(=[A-Za-z0-9_]+)", dev)
                    sys_code = m_sys.group(1) if m_sys else ""
                    m_loc = re.search(r"(\+[A-Za-z0-9_]+)", dev)
                    loc_code = m_loc.group(1) if m_loc else ""

                    sys_desc = glossary.get(sys_code, {}).get("desc_pl", "") if sys_code else ""
                    loc_desc = glossary.get(loc_code, {}).get("desc_pl", "") if loc_code else ""

                    connectors_map[dev] = {
                        "device_code": dev,
                        "device_clean": clean_code,
                        "system": sys_code,
                        "location": loc_code,
                        "system_desc": sys_desc,
                        "location_desc": loc_desc,
                        "article_number": "",
                        "supplier": "",
                        "description": "",
                        "image_url": "",
                        "pins": defaultdict(list)
                    }

                pin_entry = {
                    "wire_number": w_num,
                    "signal": sig,
                    "wire_color": w_col,
                    "cross_section": w_cs,
                    "wire_type": w_type,
                    "target_device": target_dev,
                    "target_pin": target_pin,
                    "target_desc": explain_device_code(target_dev, glossary) if target_dev else ""
                }
                existing = connectors_map[dev]["pins"][pin]
                dup = next((e for e in existing
                            if e["wire_number"] == w_num and e["target_device"] == target_dev
                            and e["target_pin"] == target_pin), None)
                if dup is None:
                    existing.append(pin_entry)
                else:
                    # Ten sam przewód opisany w innym pliku projektu — dopełnij brakujące pola
                    for fld in ("signal", "wire_color", "cross_section", "wire_type"):
                        if not dup[fld] and pin_entry[fld]:
                            dup[fld] = pin_entry[fld]

    # Skojarz z artykułami z BOM
    if bom_proj_ids and connectors_map:
        ph_bom = ",".join("?" for _ in bom_proj_ids)
        cur.execute(f"""
            SELECT d.device_code, d.device_clean, d.function,
                   i.article_number, i.supplier, i.description, i.local_image, i.category
            FROM zuken_bom_devices d
            JOIN zuken_bom_items i ON d.bom_item_id = i.id
            WHERE i.project_id IN ({ph_bom});
        """, bom_proj_ids)
        for br in cur.fetchall():
            d_code = br["device_code"]
            d_clean = br["device_clean"]
            art_num = br["article_number"]
            target_keys = [k for k in connectors_map if k == d_code or connectors_map[k]["device_clean"] == d_clean or connectors_map[k]["device_clean"] == d_code.lstrip("=+-:")]
            for k in target_keys:
                if not connectors_map[k]["article_number"]:
                    connectors_map[k]["article_number"] = art_num
                    connectors_map[k]["supplier"] = br["supplier"]
                    connectors_map[k]["description"] = br["description"]
                    img = find_local_component_image(art_num)
                    connectors_map[k]["image_url"] = img or ""

    conn_inserts = []
    for dev_code, cdata in connectors_map.items():
        sorted_pins = []
        for p_key in sorted(cdata["pins"].keys(), key=_natural_sort_key):
            sorted_pins.append({
                "pin": p_key,
                "connections": cdata["pins"][p_key]
            })

        conn_inserts.append((
            ps_code,
            cdata["device_code"],
            cdata["device_clean"],
            cdata["system"],
            cdata["location"],
            cdata["system_desc"],
            cdata["location_desc"],
            cdata["article_number"],
            cdata["supplier"],
            cdata["description"],
            cdata["image_url"],
            len(sorted_pins),
            json.dumps(sorted_pins, ensure_ascii=False)
        ))

    if conn_inserts:
        cur.executemany("""
            INSERT INTO zuken_ps_connectors (
                ps_code, device_code, device_clean, system, location, system_desc, location_desc,
                article_number, supplier, description, image_url, pin_count, pins_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, conn_inserts)

    # ═══════════════════════════════════════════════════════════════
    # 2. GENEROWANIE ZESTAWU BEZPIECZNIKÓW
    # ═══════════════════════════════════════════════════════════════
    fuses_map = {}

    if bom_proj_ids:
        ph_bom = ",".join("?" for _ in bom_proj_ids)
        cur.execute(f"""
            SELECT DISTINCT i.article_number, i.supplier, i.description, d.device_code, d.device_clean, d.function
            FROM zuken_bom_items i
            JOIN zuken_bom_devices d ON d.bom_item_id = i.id
            WHERE i.project_id IN ({ph_bom})
              AND (i.category = 'Bezpiecznik' OR i.description LIKE '%fuse%' OR i.description LIKE '%bezpiecz%')
              AND i.description NOT LIKE '%fuse box%' AND i.description NOT LIKE '%gniazdo%' AND i.description NOT LIKE '%terminal%';
        """, bom_proj_ids)
        fuse_rows = cur.fetchall()

        for fr in fuse_rows:
            d_code = fr["device_code"].strip()
            if not d_code or d_code in fuses_map:
                continue

            desc = fr["description"] or ""
            m_rating = re.search(r"(\d+(?:[,\.]\d+)?\s*A)", desc, re.IGNORECASE)
            rating = m_rating.group(1).replace(" ", "") if m_rating else ""

            m_type = re.search(r"\b(MEGA|MIDI|MINI|MAXI|UNI|ATO|UNIVAL)\b", desc, re.IGNORECASE)
            fuse_type = m_type.group(1).upper() if m_type else "UNI"

            clean_num = re.search(r"F(\d+)", d_code)
            holder_candidate = ""
            box_candidate = ""
            if clean_num:
                f_num = clean_num.group(1)
                holder_candidate = re.sub(r"-F\d+", f"-FH{f_num}", d_code)

            m_sys = re.search(r"(=[A-Za-z0-9_]+)", d_code)
            sys_code = m_sys.group(1) if m_sys else ""
            m_loc = re.search(r"(\+[A-Za-z0-9_]+)", d_code)
            loc_code = m_loc.group(1) if m_loc else ""

            circuits_found = set()
            details = []
            if conn_proj_ids:
                search_devs = [d_code]
                if holder_candidate:
                    search_devs.append(holder_candidate)
                ph_devs = ",".join("?" for _ in search_devs)
                ph_conn = ",".join("?" for _ in conn_proj_ids)
                cur.execute(f"""
                    SELECT project_id, signal, wire_number, wire_color, cross_section, length, to_device, to_pin, from_device, from_pin
                    FROM zuken_connections
                    WHERE (from_device IN ({ph_devs}) OR to_device IN ({ph_devs}))
                      AND project_id IN ({ph_conn});
                """, search_devs + search_devs + conn_proj_ids)
                details_seen = {}
                circuits_map = {}   # numer przewodu (lub sygnał) -> nazwa sygnału
                for conn_row in cur.fetchall():
                    wn, s = _norm_sig_wire(conn_row)
                    fd = conn_row["from_device"]
                    td = conn_row["to_device"]
                    target = td if fd in search_devs else fd

                    if target and not (wn or s or (conn_row["wire_color"] or "").strip()
                                       or (conn_row["cross_section"] or "").strip() or (conn_row["length"] or "").strip()):
                        # "Ślepy" zapis bez żadnych danych przewodu — artefakt schematu
                        continue

                    ckey = wn or s
                    if ckey:
                        if ckey not in circuits_map:
                            circuits_map[ckey] = s
                        elif s and not circuits_map[ckey]:
                            circuits_map[ckey] = s
                    if target:
                        dkey = (target, wn)
                        if dkey not in details_seen:
                            details_seen[dkey] = {
                                "target": target,
                                "target_desc": explain_device_code(target, glossary),
                                "signal": s,
                                "wire": wn
                            }
                            details.append(details_seen[dkey])
                        elif not details_seen[dkey]["signal"] and s:
                            details_seen[dkey]["signal"] = s

                for ckey, s_val in circuits_map.items():
                    if s_val and not s_val.isdigit():
                        circuits_found.add(s_val)
                    elif ckey:
                        circuits_found.add(f"Przewód {ckey}")

            circuits_str = ", ".join(sorted(circuits_found)) if circuits_found else (fr["function"] or "Obwód instalacji")

            fuses_map[d_code] = {
                "device_code": d_code,
                "device_clean": clean_device_code(d_code),
                "rating": rating,
                "fuse_type": fuse_type,
                "article_number": fr["article_number"],
                "supplier": fr["supplier"],
                "description": desc,
                "holder_code": holder_candidate,
                "box_code": box_candidate,
                "system": sys_code,
                "location": loc_code,
                "circuits": circuits_str,
                "details": details
            }

    fuse_inserts = [
        (
            ps_code,
            fdata["device_code"],
            fdata["device_clean"],
            fdata["rating"],
            fdata["fuse_type"],
            fdata["article_number"],
            fdata["supplier"],
            fdata["description"],
            fdata["holder_code"],
            fdata["box_code"],
            fdata["system"],
            fdata["location"],
            fdata["circuits"],
            json.dumps(fdata["details"], ensure_ascii=False)
        )
        for fdata in sorted(fuses_map.values(), key=lambda x: _natural_sort_key(x["device_clean"]))
    ]

    if fuse_inserts:
        cur.executemany("""
            INSERT INTO zuken_ps_fuses (
                ps_code, device_code, device_clean, rating, fuse_type, article_number,
                supplier, description, holder_code, box_code, system, location,
                circuits, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, fuse_inserts)

    # ═══════════════════════════════════════════════════════════════
    # 3. GENEROWANIE ZESTAWU PRZEKAŹNIKÓW
    # ═══════════════════════════════════════════════════════════════
    relays_map = {}

    if bom_proj_ids:
        ph_bom = ",".join("?" for _ in bom_proj_ids)
        cur.execute(f"""
            SELECT DISTINCT i.article_number, i.supplier, i.description, d.device_code, d.device_clean, d.function
            FROM zuken_bom_items i
            JOIN zuken_bom_devices d ON d.bom_item_id = i.id
            WHERE i.project_id IN ({ph_bom})
              AND (i.category = 'Przekaźnik' OR i.description LIKE '%relay%' OR i.description LIKE '%przeka%'
                   OR i.description LIKE '%stycznik%' OR d.device_code LIKE '%-K%' OR d.device_code LIKE '%REL-X%');
        """, bom_proj_ids)
        relay_rows = cur.fetchall()

        # Pomiń aparaty z pseudo-systemu "=BOM", jeśli to samo urządzenie
        # (identyczna część kodu +LOKALIZACJA-APARAT) występuje pod właściwym systemem
        def _dev_suffix(code):
            m = re.match(r"^=[A-Za-z0-9_]+(.*)$", code or "")
            return (m.group(1) if m else (code or "")).rstrip("'\"").strip()

        non_bom_suffixes = {
            _dev_suffix(rr["device_code"])
            for rr in relay_rows
            if rr["device_code"] and not rr["device_code"].strip().startswith("=BOM")
        }

        for rr in relay_rows:
            d_code = rr["device_code"].strip()
            if not d_code or d_code in relays_map:
                continue
            if d_code.startswith("=BOM") and _dev_suffix(d_code) in non_bom_suffixes:
                continue

            func = rr["function"] or ""
            desc = rr["description"] or ""
            art = rr["article_number"] or ""
            sup = rr["supplier"] or ""

            m_sys = re.search(r"(=[A-Za-z0-9_]+)", d_code)
            sys_code = m_sys.group(1) if m_sys else ""
            m_loc = re.search(r"(\+[A-Za-z0-9_]+)", d_code)
            loc_code = m_loc.group(1) if m_loc else ""

            contacts = []
            if conn_proj_ids:
                ph_conn = ",".join("?" for _ in conn_proj_ids)
                # Wiersze z formatu CON najpierw — zawierają nazwy sygnałów i jednostki (mm²)
                con_prio = ""
                con_params = ()
                if con_format_ids:
                    ph_cfmt = ",".join("?" for _ in con_format_ids)
                    con_prio = f"ORDER BY CASE WHEN project_id IN ({ph_cfmt}) THEN 0 ELSE 1 END"
                    con_params = tuple(con_format_ids)
                cur.execute(f"""
                    SELECT project_id, from_pin, to_pin, signal, wire_number, wire_color,
                           cross_section, wire_type, length, cable_name, to_device, from_device
                    FROM zuken_connections
                    WHERE (from_device = ? OR to_device = ?) AND project_id IN ({ph_conn})
                    {con_prio};
                """, (d_code, d_code) + tuple(conn_proj_ids) + con_params)

                relay_std_pins = {"30", "85", "86", "87", "87A", "87B"}
                pin_map = {}      # pin gniazda -> (styk przekaźnika, nazwa sygnału)
                raw_contacts = []
                for cr in cur.fetchall():
                    is_from = ((cr["from_device"] or "").strip() == d_code)
                    pin = (cr["from_pin"] if is_from else cr["to_pin"] or "").strip()
                    target = (cr["to_device"] if is_from else cr["from_device"] or "").strip()
                    target_p = (cr["to_pin"] if is_from else cr["from_pin"] or "").strip()
                    w_num, sig = _norm_sig_wire(cr)

                    if not target:
                        # Wiersz mapowania pinu gniazda na styk przekaźnika (np. "X145:2 -> :30")
                        if target_p.upper() in relay_std_pins:
                            pin_map[pin] = (target_p, sig)
                        continue
                    c_len = (cr["length"] or "").strip()
                    try:
                        c_len = str(int(round(float(c_len))))
                    except (ValueError, TypeError):
                        pass
                    c_col = (cr["wire_color"] or "").strip()
                    c_cs = (cr["cross_section"] or "").strip()
                    c_type = (cr["wire_type"] or "").strip()
                    if not (w_num or sig or c_col or c_cs or c_len or c_type):
                        # "Ślepy" zapis bez żadnych danych przewodu — artefakt schematu
                        continue
                    raw_contacts.append({
                        "pin": pin, "target": target, "target_pin": target_p,
                        "wire_number": w_num, "signal": sig,
                        "wire_color": c_col,
                        "cross_section": c_cs,
                        "wire_type": c_type,
                        "length": c_len
                    })

                # Scal ten sam fizyczny przewód opisany w kilku plikach projektu
                seen_contacts = {}
                for rc in raw_contacts:
                    if not rc["pin"]:
                        continue
                    key = (rc["pin"], rc["target"], rc["target_pin"], rc["wire_number"])
                    if key in seen_contacts:
                        for fld in ("signal", "wire_color", "cross_section", "wire_type", "length"):
                            if not seen_contacts[key][fld] and rc[fld]:
                                seen_contacts[key][fld] = rc[fld]
                        continue
                    relay_pin, map_sig = pin_map.get(rc["pin"], ("", ""))
                    if not rc["signal"] and map_sig:
                        rc["signal"] = map_sig
                    rp = (relay_pin or rc["pin"]).upper()
                    if rp in ["85", "86"]:
                        role = "Cewka (Coil 85/86)"
                    elif rp == "30":
                        role = "Zasilanie (Common 30)"
                    elif rp == "87":
                        role = "Styk zwierny (NO 87)"
                    elif rp in ["87A", "87B"]:
                        role = "Styk rozwierny (NC 87a)"
                    else:
                        role = "Styk roboczy"
                    entry = {
                        "pin": rc["pin"],
                        "relay_pin": relay_pin,
                        "role": role,
                        "signal": rc["signal"],
                        "wire_number": rc["wire_number"],
                        "wire_color": rc["wire_color"],
                        "cross_section": rc["cross_section"],
                        "wire_type": rc["wire_type"],
                        "length": rc["length"],
                        "target_device": rc["target"],
                        "target_pin": rc["target_pin"],
                        "target_desc": explain_device_code(rc["target"], glossary) if rc["target"] else ""
                    }
                    seen_contacts[key] = entry
                    contacts.append(entry)

            relay_pin_order = {"30": 0, "85": 1, "86": 2, "87": 3, "87A": 4, "87B": 4}
            contacts.sort(key=lambda c: (
                relay_pin_order.get((c["relay_pin"] or c["pin"]).upper(), 9),
                _natural_sort_key(c["pin"]),
                _natural_sort_key(c["target_device"] or "")
            ))
            relay_type_name = f"{sup} {desc}".strip() if sup else desc

            relays_map[d_code] = {
                "device_code": d_code,
                "device_clean": clean_device_code(d_code),
                "function": func or "Przekaźnik sterujący",
                "relay_type": relay_type_name,
                "article_number": art,
                "supplier": sup,
                "description": desc,
                "socket_code": d_code if "REL-X" in d_code or "BSI-X" in d_code else "",
                "system": sys_code,
                "location": loc_code,
                "contacts": contacts
            }

    relay_inserts = [
        (
            ps_code,
            rdata["device_code"],
            rdata["device_clean"],
            rdata["function"],
            rdata["relay_type"],
            rdata["article_number"],
            rdata["supplier"],
            rdata["description"],
            rdata["socket_code"],
            rdata["system"],
            rdata["location"],
            json.dumps(rdata["contacts"], ensure_ascii=False)
        )
        for rdata in sorted(relays_map.values(), key=lambda x: _natural_sort_key(x["device_clean"]))
    ]

    if relay_inserts:
        cur.executemany("""
            INSERT INTO zuken_ps_relays (
                ps_code, device_code, device_clean, function, relay_type, article_number,
                supplier, description, socket_code, system, location, contacts_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, relay_inserts)

    # ═══════════════════════════════════════════════════════════════
    # 4. ZAPIS W ZUKEN_PS_SUMMARIES
    # ═══════════════════════════════════════════════════════════════
    proj_name = projects[0]["project_name"] if projects else f"Projekt {ps_code}"
    client_name = projects[0]["client"] if projects else "Klient specjalny"
    source_files_list = ", ".join([p["filename"] for p in projects[:4]])

    cur.execute("""
        INSERT INTO zuken_ps_summaries (
            ps_code, project_name, client, connectors_count, fuses_count, relays_count, generated_at, source_files
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ps_code) DO UPDATE SET
            project_name=excluded.project_name,
            client=excluded.client,
            connectors_count=excluded.connectors_count,
            fuses_count=excluded.fuses_count,
            relays_count=excluded.relays_count,
            generated_at=excluded.generated_at,
            source_files=excluded.source_files;
    """, (
        ps_code,
        proj_name,
        client_name,
        len(conn_inserts),
        len(fuse_inserts),
        len(relay_inserts),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source_files_list
    ))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "ps_code": ps_code,
        "project_name": proj_name,
        "connectors_count": len(conn_inserts),
        "fuses_count": len(fuse_inserts),
        "relays_count": len(relay_inserts),
        "message": f"Wygenerowano zestawienia dla {ps_code}: {len(conn_inserts)} złączy, {len(fuse_inserts)} bezpieczników, {len(relay_inserts)} przekaźników."
    }


def get_ps_connectors(ps_code, search="", system_filter="", limit=100, offset=0):
    """Pobiera listę złączy z pinoutem dla projektu PS z filtrowaniem i paginacją."""
    if not ps_code:
        return {"items": [], "total": 0}
    ps_code = str(ps_code).strip().upper()
    init_zuken_tables()

    conn = get_db()
    cur = conn.cursor()

    # Sprawdź czy tabela zawiera już dane dla tego PS
    cur.execute("SELECT COUNT(*) FROM zuken_ps_connectors WHERE ps_code = ?;", (ps_code,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        # Automatyczne wygenerowanie przy pierwszym odczycie
        conn.close()
        generate_ps_technical_summaries(ps_code)
        conn = get_db()
        cur = conn.cursor()

    conditions = ["ps_code = ?"]
    params = [ps_code]

    if system_filter:
        conditions.append("system = ?")
        params.append(system_filter.strip())

    if search:
        q_like = f"%{search.strip()}%"
        conditions.append("""
            (device_code LIKE ? OR device_clean LIKE ? OR article_number LIKE ? OR
             supplier LIKE ? OR description LIKE ? OR location_desc LIKE ? OR pins_json LIKE ?)
        """)
        params.extend([q_like, q_like, q_like, q_like, q_like, q_like, q_like])

    where_str = "WHERE " + " AND ".join(conditions)

    cur.execute(f"SELECT COUNT(*) FROM zuken_ps_connectors {where_str};", params)
    total_count = cur.fetchone()[0]

    cur.execute(f"""
        SELECT * FROM zuken_ps_connectors
        {where_str}
        ORDER BY system, location, device_clean
        LIMIT ? OFFSET ?;
    """, params + [limit, offset])

    rows = cur.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["pins"] = json.loads(d.get("pins_json") or "[]")
        items.append(d)

    conn.close()
    return {
        "items": items,
        "total": total_count,
        "ps_code": ps_code,
        "limit": limit,
        "offset": offset
    }


def get_ps_fuses(ps_code, search="", limit=100, offset=0):
    """Pobiera zestaw bezpieczników dla projektu PS z filtrowaniem."""
    if not ps_code:
        return {"items": [], "total": 0}
    ps_code = str(ps_code).strip().upper()
    init_zuken_tables()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM zuken_ps_fuses WHERE ps_code = ?;", (ps_code,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        conn.close()
        generate_ps_technical_summaries(ps_code)
        conn = get_db()
        cur = conn.cursor()

    conditions = ["ps_code = ?"]
    params = [ps_code]

    if search:
        q_like = f"%{search.strip()}%"
        conditions.append("""
            (device_code LIKE ? OR device_clean LIKE ? OR rating LIKE ? OR
             fuse_type LIKE ? OR circuits LIKE ? OR holder_code LIKE ? OR description LIKE ?)
        """)
        params.extend([q_like, q_like, q_like, q_like, q_like, q_like, q_like])

    where_str = "WHERE " + " AND ".join(conditions)

    cur.execute(f"SELECT COUNT(*) FROM zuken_ps_fuses {where_str};", params)
    total_count = cur.fetchone()[0]

    cur.execute(f"""
        SELECT * FROM zuken_ps_fuses
        {where_str}
        ORDER BY system, location, device_clean
        LIMIT ? OFFSET ?;
    """, params + [limit, offset])

    rows = cur.fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d.get("details_json") or "[]")
        items.append(d)

    conn.close()
    return {
        "items": items,
        "total": total_count,
        "ps_code": ps_code,
        "limit": limit,
        "offset": offset
    }


def get_ps_relays(ps_code, search="", limit=100, offset=0):
    """Pobiera zestaw przekaźników dla projektu PS z filtrowaniem."""
    if not ps_code:
        return {"items": [], "total": 0}
    ps_code = str(ps_code).strip().upper()
    init_zuken_tables()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM zuken_ps_relays WHERE ps_code = ?;", (ps_code,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        conn.close()
        generate_ps_technical_summaries(ps_code)
        conn = get_db()
        cur = conn.cursor()

    conditions = ["ps_code = ?"]
    params = [ps_code]

    if search:
        q_like = f"%{search.strip()}%"
        conditions.append("""
            (device_code LIKE ? OR device_clean LIKE ? OR function LIKE ? OR
             relay_type LIKE ? OR supplier LIKE ? OR description LIKE ? OR socket_code LIKE ?)
        """)
        params.extend([q_like, q_like, q_like, q_like, q_like, q_like, q_like])

    where_str = "WHERE " + " AND ".join(conditions)

    cur.execute(f"SELECT COUNT(*) FROM zuken_ps_relays {where_str};", params)
    total_count = cur.fetchone()[0]

    cur.execute(f"""
        SELECT * FROM zuken_ps_relays
        {where_str}
        ORDER BY system, location, function, device_clean
        LIMIT ? OFFSET ?;
    """, params + [limit, offset])

    rows = cur.fetchall()

    glossary = get_glossary_dict()

    def _gdesc(prefix, lang="desc_pl"):
        entry = glossary.get(prefix)
        if not entry:
            return ""
        return entry.get(lang) or entry.get("desc_pl") or ""

    items = []
    for r in rows:
        d = dict(r)
        d["contacts"] = json.loads(d.get("contacts_json") or "[]")
        d["system_desc"] = _gdesc(d.get("system"))
        d["location_desc"] = _gdesc(d.get("location"))
        d["system_desc_en"] = _gdesc(d.get("system"), "desc_en")
        d["location_desc_en"] = _gdesc(d.get("location"), "desc_en")
        items.append(d)

    conn.close()
    return {
        "items": items,
        "total": total_count,
        "ps_code": ps_code,
        "limit": limit,
        "offset": offset
    }


def export_ps_summary_csv(ps_code, summary_type="connectors"):
    """
    Generuje plik CSV z zestawieniem (złącza z pinoutem, bezpieczniki lub przekaźniki).
    Zawiera znacznik BOM UTF-8 (\ufeff) dla bezproblemowego otwierania w polskim MS Excel.
    """
    if not ps_code:
        return ""
    ps_code = str(ps_code).strip().upper()

    output = io.StringIO()
    output.write("\ufeff") # UTF-8 BOM
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    if summary_type == "connectors":
        writer.writerow([
            "Projekt PS", "Kod aparatu złącza", "Kod skrócony", "System", "Lokalizacja",
            "Opis lokalizacji", "Kod artykułu BOM", "Dostawca / Producent", "Opis katalogowy złącza",
            "Liczba pinów", "Pin", "Nazwa sygnału", "Numer przewodu", "Kolor",
            "Przekrój (mm2)", "Typ przewodu", "Urządzenie docelowe", "Pin docelowy", "Opis urządzenia docelowego"
        ])
        data = get_ps_connectors(ps_code, limit=5000)
        for item in data.get("items", []):
            pins = item.get("pins", [])
            if not pins:
                writer.writerow([
                    ps_code, item["device_code"], item["device_clean"], item["system"], item["location"],
                    item["location_desc"], item["article_number"], item["supplier"], item["description"],
                    item["pin_count"], "", "", "", "", "", "", "", "", ""
                ])
            else:
                for p_group in pins:
                    pin_num = p_group.get("pin", "")
                    for conn_info in p_group.get("connections", []):
                        writer.writerow([
                            ps_code, item["device_code"], item["device_clean"], item["system"], item["location"],
                            item["location_desc"], item["article_number"], item["supplier"], item["description"],
                            item["pin_count"], pin_num, conn_info.get("signal", ""), conn_info.get("wire_number", ""),
                            conn_info.get("wire_color", ""), conn_info.get("cross_section", ""),
                            conn_info.get("wire_type", ""), conn_info.get("target_device", ""),
                            conn_info.get("target_pin", ""), conn_info.get("target_desc", "")
                        ])

    elif summary_type == "fuses":
        writer.writerow([
            "Projekt PS", "Bezpiecznik (Aparat)", "Kod skrócony", "Prąd znamionowy (A)", "Typ bezpiecznika",
            "Oprawka (-FH)", "Skrzynka / Blok", "System", "Lokalizacja", "Chronione sygnały i obwody",
            "Kod artykułu BOM", "Dostawca", "Opis katalogowy"
        ])
        data = get_ps_fuses(ps_code, limit=2000)
        for item in data.get("items", []):
            writer.writerow([
                ps_code, item["device_code"], item["device_clean"], item["rating"], item["fuse_type"],
                item["holder_code"], item["box_code"], item["system"], item["location"],
                item["circuits"], item["article_number"], item["supplier"], item["description"]
            ])

    elif summary_type == "relays":
        writer.writerow([
            "Projekt PS", "Przekaźnik (Aparat)", "Kod skrócony", "Funkcja przekaźnika", "Typ / Model",
            "Dostawca", "Gniazdo / Podstawa", "System", "Lokalizacja", "Lokalizacja (opis)", "Pin / Rola",
            "Sygnał", "Numer przewodu", "Kolor", "Przekrój (mm2)", "Długość (mm)",
            "Aparat docelowy", "Pin docelowy", "Opis celu"
        ])
        data = get_ps_relays(ps_code, limit=2000)
        for item in data.get("items", []):
            loc_desc = item.get("location_desc") or ""
            contacts = item.get("contacts", [])
            if not contacts:
                writer.writerow([
                    ps_code, item["device_code"], item["device_clean"], item["function"], item["relay_type"],
                    item["supplier"], item["socket_code"], item["system"], item["location"], loc_desc,
                    "", "", "", "", "", "", "", "", ""
                ])
            else:
                for c in contacts:
                    pin_lbl = c.get("pin", "")
                    if c.get("relay_pin") and c["relay_pin"] != pin_lbl:
                        pin_lbl = f"{pin_lbl}/{c['relay_pin']}"
                    writer.writerow([
                        ps_code, item["device_code"], item["device_clean"], item["function"], item["relay_type"],
                        item["supplier"], item["socket_code"], item["system"], item["location"], loc_desc,
                        f"Pin {pin_lbl} ({c.get('role', '')})".strip(),
                        c.get("signal", ""), c.get("wire_number", ""), c.get("wire_color", ""),
                        c.get("cross_section", ""), c.get("length", ""),
                        c.get("target_device", ""), c.get("target_pin", ""), c.get("target_desc", "")
                    ])

    return output.getvalue()


