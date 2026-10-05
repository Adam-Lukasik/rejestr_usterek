-- Wygenerowano automatycznie przez tools/export_migrations.py
-- Data: 2026-10-04T15:52:20
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

CREATE TABLE IF NOT EXISTS zuken_query_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT NOT NULL UNIQUE COLLATE NOCASE,
            terms TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
DELETE FROM zuken_query_aliases;
