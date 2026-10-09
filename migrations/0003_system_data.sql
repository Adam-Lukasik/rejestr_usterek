-- Wygenerowano automatycznie przez tools/export_migrations.py
-- Data: 2026-10-09T20:16:35
-- UWAGA: DELETE+INSERT — tabele systemowe są zarządzane centralnie,
-- ich stan po migracji jest identyczny jak w dev-bazie.

CREATE TABLE IF NOT EXISTS zuken_conn_pinouts (
            article TEXT PRIMARY KEY,
            rows INTEGER NOT NULL,
            cols INTEGER NOT NULL,
            gender TEXT DEFAULT 'F',
            pins_map TEXT NOT NULL,
            note TEXT DEFAULT '',
            updated_at TEXT
        );
DELETE FROM zuken_conn_pinouts;
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('7-968972-1', 3, 4, 'F', '["1", "4", "7", "10", "2", "5", "8", "11", "3", "6", "9", "12"]', 'KFG VW/MAN St.2 (obudowa VAG 4F0 973 712) — podręcznik VW Crafter KFG, Abb. 2.2 + tab. Connector 2; widok od strony przewodów, zatrzask u góry (na module ryglik od strony pinów 1/4/7/10)', '2026-09-30T21:17:33');
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('1-968321-2', 4, 10, 'F', '["31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]', 'KFG VW/MAN St.3 (obudowa VAG 4H0 906 231; 1-968321-2 to osłona odprowadzenia) — podręcznik VW Crafter KFG, Abb. 2.2 + tab. Connector 3; widok od strony przewodów = rzut czoła modułu KFG', '2026-09-30T20:52:50');
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('4H0906231', 4, 10, 'F', '["31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]', 'KFG VW/MAN St.3 — podręcznik VW Crafter KFG, Abb. 2.2 + tab. Connector 3; widok od strony przewodów = rzut czoła modułu KFG', '2026-09-30T20:52:50');
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('RBA2', 2, 18, 'F', '{"map": ["1", "2", "3", "4", "x", "9", "11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "31", "33", "5", "6", "7", "8", "x", "10", "12", "14", "16", "18", "20", "22", "24", "26", "28", "30", "32", "34"], "devices": {"QC12": {"1": "3"}, "QC13": {"1": "4"}, "QC14": {"1": "23"}}, "unverified": true}', 'RBA 2 - wtyk Body Controllera Mercedes Sprinter VS30 (BCM V2, A907 900 08 06), widok od strony przewodow. Lewa wkladka MCP 2.8 2x4 (piny 1-8), prawa MQS 2x13 (piny 9-34). Geometria wg zdjecia modulu - do weryfikacji orientacji numeracji.', '2026-10-09T19:09:28');
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('171898-1', 2, 3, 'F', '{"map": ["6", "7", "8", "1", "2", "3"], "devices": {"X158": {"1": "1", "2": "2", "3": "3", "4": "6", "5": "7", "6": "8"}, "X86": {"1": "1", "2": "2", "3": "3", "4": "6", "5": "7", "6": "8"}}}', 'TE FASTIN-FASTON 250 plug 6p - wtyk modulu centralki WAECO/Dometic MagicLock ML-22/44 (X158 w PS012732, X86 w PS011871). Widok od strony przewodow = jak czolo modulu wg instrukcji: dolny rzad 1,2,3 / gorny 6,7,8. Producent numeruje dwie wtyczki jak jedno zlacze 1-10 (druga wtyczka 2x2 = poz. 4,5,9,10), stad piny Zuken 4,5,6 siedza w komorach 6,7,8. Geometria wg rys. TE C-171898 i kat. 1654369-1.', '2026-10-09T19:52:37');
INSERT OR REPLACE INTO zuken_conn_pinouts (article, rows, cols, gender, pins_map, note, updated_at) VALUES ('172134-1', 2, 2, 'F', '{"map": ["9", "10", "4", "5"], "devices": {"X87": {"1": "4", "2": "5", "3": "9", "4": "10"}}, "unverified": true}', 'TE FASTIN-FASTON 250 plug 4p - druga wtyk modulu WAECO ML-22/44 (X87 w PS011871): sterowanie zewnetrzne ZV. Pozycje na czole modulu: dolny rzad 4,5 / gorny 9,10 (numeracja ciagla 1-10 obu wtyczek wg instrukcji). Mapowanie pinow Zuken na komory domniemane - DO WERYFIKACJI ze zdjecia. Geometria wg kat. TE 1654369-1.', '2026-10-09T19:52:37');

CREATE TABLE IF NOT EXISTS zuken_query_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT NOT NULL UNIQUE COLLATE NOCASE,
            terms TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
DELETE FROM zuken_query_aliases;
