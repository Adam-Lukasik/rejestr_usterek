# -*- coding: utf-8 -*-
"""Kontrola schematów Zuken — wykrywanie błędów/braków w danych projektu
(Connections, BOM, PDF), rejestr problemów do wyjaśnienia, łatki-nakładki
poprawiające pracę asystenta i eksport listy dla inżyniera Zuken
(szkic Outlook .eml + XLSX + wycinki PDF).

Rejestr problemów (zuken_issues*) jest lokalny. Łatki (zuken_data_patches),
dane projektu (zuken_ps_meta) i reguły platform (zuken_platform_terms) są
tabelami systemowymi tworzonymi w zuken_service.init_zuken_tables().
Wykrywacze liczą zawsze na SUROWYCH danych importu (bez łatek)."""
import io
import json
import os
import re
import threading
import uuid
import zipfile
from collections import defaultdict, Counter
from datetime import datetime
from email.message import EmailMessage
from xml.sax.saxutils import escape as _xesc

import zuken_service as zs

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


# ═══════════════════════════════════════════════════════════════════
# KATALOG KATEGORII, STATUSÓW, PLATFORM
# ═══════════════════════════════════════════════════════════════════
# kategoria -> (target, domyślna ważność)
CATEGORIES = {
    "device_unconnected": ("engineer", "warn"),
    "dangling_terminal": ("engineer", "warn"),
    "device_no_location": ("engineer", "info"),
    "bom_conn_mismatch": ("engineer", "info"),
    "typo": ("engineer", "info"),
    "platform_term": ("engineer", "warn"),
    "busbar_unmodeled": ("engineer", "warn"),
    "fuse_holder_unlinked": ("engineer", "warn"),
    "box_fuse_hidden": ("engineer", "warn"),
    "fuse_no_wiring": ("engineer", "error"),
    "pdf_report_label": ("engineer", "info"),
    "pinout_missing": ("internal", "warn"),
    "photo_missing": ("internal", "info"),
    "term_untranslated": ("internal", "info"),
    "kb_document": ("internal", "warn"),
    "manual": ("engineer", "warn"),
}

OPEN_STATUSES = {
    "engineer": ("new", "confirmed", "sent", "fixed"),
    "internal": ("new", "in_progress"),
}
CLOSED_STATUSES = ("verified", "rejected", "wontfix", "done")
ALL_STATUSES = ("new", "confirmed", "sent", "fixed", "verified", "rejected",
                "wontfix", "in_progress", "done")
SEVERITIES = ("info", "warn", "error")

PLATFORMS = {
    "MB_SPRINTER": "Mercedes-Benz Sprinter",
    "VW_CRAFTER": "Volkswagen Crafter",
    "MAN_TGE": "MAN TGE",
    "FIAT_DUCATO": "Fiat Ducato",
    "FORD_TRANSIT": "Ford Transit",
    "RENAULT_MASTER": "Renault Master",
    "IVECO_DAILY": "Iveco Daily",
}
# Autodetekcja pojazdu bazowego: wzorzec -> platforma (propozycja, nie wiąże)
_PLATFORM_HINTS = (
    (re.compile(r"\bSPRINTER\b|\bVS30\b|\bBM ?907\b|\bBM ?910\b", re.I), "MB_SPRINTER"),
    (re.compile(r"\bCRAFTER\b", re.I), "VW_CRAFTER"),
    (re.compile(r"\bTGE\b", re.I), "MAN_TGE"),
    (re.compile(r"\bDUCATO\b", re.I), "FIAT_DUCATO"),
    (re.compile(r"\bTRANSIT\b", re.I), "FORD_TRANSIT"),
    (re.compile(r"\bMASTER\b", re.I), "RENAULT_MASTER"),
    (re.compile(r"\bDAILY\b", re.I), "IVECO_DAILY"),
)

# ═══════════════════════════════════════════════════════════════════
# KOMUNIKATY (PL / EN / DE) — treść zgłoszeń wykrywaczy jako klucz +
# parametry, renderowana w języku widoku/eksportu.
# ═══════════════════════════════════════════════════════════════════
AUDIT_MSG = {
    # kategorie
    "cat.device_unconnected": {"pl": "Aparat bez połączeń", "en": "Device without connections", "de": "Gerät ohne Verbindungen"},
    "cat.dangling_terminal": {"pl": "Niepodłączona końcówka", "en": "Unattached terminal", "de": "Nicht angeschlossener Kabelschuh"},
    "cat.device_no_location": {"pl": "Brak oznaczenia lokalizacji", "en": "Missing location designation", "de": "Fehlende Ortskennzeichnung"},
    "cat.bom_conn_mismatch": {"pl": "Brak w BOM", "en": "Missing in BOM", "de": "Fehlt in Stückliste"},
    "cat.typo": {"pl": "Literówka", "en": "Typo", "de": "Tippfehler"},
    "cat.platform_term": {"pl": "Terminologia pojazdu bazowego", "en": "Base vehicle terminology", "de": "Terminologie Basisfahrzeug"},
    "cat.busbar_unmodeled": {"pl": "Zwora/szyna tylko graficznie", "en": "Bus bar drawn graphically only", "de": "Brücke/Schiene nur grafisch"},
    "cat.fuse_holder_unlinked": {"pl": "Bezpiecznik ↔ gniazdo", "en": "Fuse ↔ holder link", "de": "Sicherung ↔ Halter"},
    "cat.box_fuse_hidden": {"pl": "Skrzynka bezpieczników", "en": "Fuse box", "de": "Sicherungskasten"},
    "cat.fuse_no_wiring": {"pl": "Bezpiecznik bez okablowania", "en": "Fuse without wiring", "de": "Sicherung ohne Verdrahtung"},
    "cat.pdf_report_label": {"pl": "Schemat ≠ raport", "en": "Schematic ≠ report", "de": "Schaltplan ≠ Bericht"},
    "cat.pinout_missing": {"pl": "Brak pinoutu złącza", "en": "Missing connector pinout", "de": "Fehlende Steckerbelegung"},
    "cat.photo_missing": {"pl": "Brak zdjęć komponentów", "en": "Missing component photos", "de": "Fehlende Bauteilfotos"},
    "cat.term_untranslated": {"pl": "Teksty do tłumaczenia", "en": "Texts to translate", "de": "Zu übersetzende Texte"},
    "cat.kb_document": {"pl": "Dokumenty projektu", "en": "Project documents", "de": "Projektdokumente"},
    "cat.manual": {"pl": "Zgłoszenie ręczne", "en": "Manual report", "de": "Manuelle Meldung"},
    # statusy
    "st.new": {"pl": "Nowe", "en": "New", "de": "Neu"},
    "st.confirmed": {"pl": "Do wysłania", "en": "To send", "de": "Zu senden"},
    "st.sent": {"pl": "Wysłane", "en": "Sent", "de": "Gesendet"},
    "st.fixed": {"pl": "Poprawione w Zuken", "en": "Fixed in Zuken", "de": "In Zuken korrigiert"},
    "st.verified": {"pl": "Zweryfikowane", "en": "Verified", "de": "Verifiziert"},
    "st.rejected": {"pl": "Odrzucone", "en": "Rejected", "de": "Abgelehnt"},
    "st.wontfix": {"pl": "Zostaje obejście", "en": "Workaround kept", "de": "Workaround bleibt"},
    "st.in_progress": {"pl": "W toku", "en": "In progress", "de": "In Arbeit"},
    "st.done": {"pl": "Uzupełnione", "en": "Done", "de": "Erledigt"},
    # ważność
    "sev.info": {"pl": "Info", "en": "Info", "de": "Info"},
    "sev.warn": {"pl": "Ostrzeżenie", "en": "Warning", "de": "Warnung"},
    "sev.error": {"pl": "Błąd", "en": "Error", "de": "Fehler"},
    # D01
    "device_unconnected.title": {"pl": "{dev}: aparat bez połączeń w raporcie", "en": "{dev}: device without connections in the report", "de": "{dev}: Gerät ohne Verbindungen im Bericht"},
    "device_unconnected.desc": {
        "pl": "Urządzenie {dev} ({art} — {descr}) jest w BOM i narysowane na schemacie (str. {page}), ale raport połączeń nie zawiera żadnego pinu tego aparatu. Asystent nie pokaże jego obwodów.",
        "en": "Device {dev} ({art} — {descr}) is in the BOM and drawn on the schematic (p. {page}), but the connection report contains none of its pins. The assistant cannot show its circuits.",
        "de": "Gerät {dev} ({art} — {descr}) ist in der Stückliste und im Schaltplan (S. {page}) gezeichnet, aber der Verbindungsbericht enthält keinen seiner Pins. Der Assistent kann seine Stromkreise nicht zeigen."},
    "device_unconnected.fix": {"pl": "Podłączyć piny/szpilki aparatu w E3 (np. końcówki oczkowe), żeby trafiły do raportu Connections.", "en": "Connect the device pins/studs in E3 (e.g. ring terminals) so that they appear in the Connections report.", "de": "Pins/Bolzen des Geräts in E3 anschließen (z. B. Ringkabelschuhe), damit sie im Connections-Bericht erscheinen."},
    # D02
    "dangling_terminal.title": {"pl": "{dev}: końcówka bez podłączenia", "en": "{dev}: terminal not attached", "de": "{dev}: Kabelschuh nicht angeschlossen"},
    "dangling_terminal.desc": {
        "pl": "Końcówka {dev} ({descr}) ma w raporcie tylko przewód {wire} do {peer}; miejsce montażu (szpilka/pin aparatu) nie jest przypisane.{cand}",
        "en": "Terminal {dev} ({descr}) only has wire {wire} to {peer} in the report; its mounting point (stud/device pin) is not assigned.{cand}",
        "de": "Kabelschuh {dev} ({descr}) hat im Bericht nur Leitung {wire} zu {peer}; der Montagepunkt (Bolzen/Gerätepin) ist nicht zugeordnet.{cand}"},
    "dangling_terminal.cand": {"pl": " Prawdopodobnie: {cand} (ta sama strona schematu).", "en": " Probably: {cand} (same schematic page).", "de": " Wahrscheinlich: {cand} (gleiche Schaltplanseite)."},
    "dangling_terminal.fix": {"pl": "Przypisać końcówkę {dev} do pinu aparatu{cand} w E3.", "en": "Assign terminal {dev} to the device pin{cand} in E3.", "de": "Kabelschuh {dev} in E3 dem Gerätepin{cand} zuordnen."},
    # D03
    "device_no_location.title": {"pl": "{dev}: brak oznaczenia =system+lokalizacja", "en": "{dev}: missing =system+location designation", "de": "{dev}: fehlende =Anlage+Ort-Kennzeichnung"},
    "device_no_location.desc": {
        "pl": "Kod {dev} nie ma prefiksu =system+lokalizacja, a {pct}% kodów projektu ma pełne oznaczenie.{sug}",
        "en": "Code {dev} has no =system+location prefix while {pct}% of the project codes are fully designated.{sug}",
        "de": "Code {dev} hat kein =Anlage+Ort-Präfix, obwohl {pct}% der Projektcodes vollständig gekennzeichnet sind.{sug}"},
    "device_no_location.sug": {"pl": " Sąsiednie oznaczenia na stronie: {sug}.", "en": " Neighbouring designations on the page: {sug}.", "de": " Benachbarte Kennzeichnungen auf der Seite: {sug}."},
    "device_no_location.fix": {"pl": "Nadać pełne oznaczenie (np. {sug}{dev}).", "en": "Assign a full designation (e.g. {sug}{dev}).", "de": "Vollständige Kennzeichnung vergeben (z. B. {sug}{dev})."},
    # D04
    "bom_conn_mismatch.title": {"pl": "{dev}: w raporcie połączeń, brak w BOM", "en": "{dev}: in the connection report, missing in the BOM", "de": "{dev}: im Verbindungsbericht, fehlt in der Stückliste"},
    "bom_conn_mismatch.desc": {"pl": "Urządzenie {dev} ma {n} połączeń w raporcie, ale nie ma pozycji w BOM (brak artykułu i opisu).", "en": "Device {dev} has {n} connections in the report but no BOM entry (no article or description).", "de": "Gerät {dev} hat {n} Verbindungen im Bericht, aber keinen Stücklisteneintrag (kein Artikel, keine Beschreibung)."},
    "bom_conn_mismatch.fix": {"pl": "Przypisać artykuł do {dev} w E3.", "en": "Assign an article to {dev} in E3.", "de": "{dev} in E3 einen Artikel zuordnen."},
    # D05
    "typo.title": {"pl": "Literówka: „{form}” → „{target}”", "en": "Typo: “{form}” → “{target}”", "de": "Tippfehler: „{form}“ → „{target}“"},
    "typo.desc": {"pl": "Tekst „{form}” występuje w: {where}. Poprawna forma: „{target}”.{known}", "en": "Text “{form}” occurs in: {where}. Correct form: “{target}”.{known}", "de": "Text „{form}“ kommt vor in: {where}. Richtige Form: „{target}“.{known}"},
    "typo.known": {"pl": " Słownik tłumaczeń już koryguje to do wyświetlania.", "en": " The translation dictionary already corrects it for display.", "de": " Das Übersetzungswörterbuch korrigiert es bereits für die Anzeige."},
    "typo.fix": {"pl": "Poprawić „{form}” na „{target}” ({where}).", "en": "Correct “{form}” to “{target}” ({where}).", "de": "„{form}“ in „{target}“ korrigieren ({where})."},
    # D06
    "photo_missing.title": {"pl": "{n} artykułów BOM bez zdjęcia komponentu", "en": "{n} BOM articles without a component photo", "de": "{n} Stücklistenartikel ohne Bauteilfoto"},
    "photo_missing.desc": {"pl": "Brak zdjęć: {list}", "en": "Missing photos: {list}", "de": "Fehlende Fotos: {list}"},
    # D07
    "term_untranslated.title": {"pl": "{n} nieprzetłumaczonych tekstów schematu", "en": "{n} untranslated schematic texts", "de": "{n} nicht übersetzte Schaltplantexte"},
    "term_untranslated.desc": {"pl": "Kolejka „Do tłumaczenia” w Słownikach: {list}", "en": "“To translate” queue in Dictionaries: {list}", "de": "Warteschlange „Zu übersetzen“ in Wörterbüchern: {list}"},
    # D08
    "platform_term.title": {"pl": "„{term}” na pojeździe {vehicle}", "en": "“{term}” on a {vehicle}", "de": "„{term}“ auf {vehicle}"},
    "platform_term.desc": {
        "pl": "Termin „{term}” ({where}) jest typowy dla: {platforms}. W pojeździe {vehicle} odpowiednikiem jest „{equiv}” — technicy mogą uznać to za poważny błąd projektu.",
        "en": "The term “{term}” ({where}) is typical for: {platforms}. On a {vehicle} the equivalent is “{equiv}” — technicians may suspect a serious design error.",
        "de": "Der Begriff „{term}“ ({where}) ist typisch für: {platforms}. Beim {vehicle} heißt das Gegenstück „{equiv}“ — Techniker könnten einen schweren Konstruktionsfehler vermuten."},
    "platform_term.fix": {"pl": "Zmienić opis „{term}” na „{equiv}” ({where}).", "en": "Rename “{term}” to “{equiv}” ({where}).", "de": "„{term}“ in „{equiv}“ umbenennen ({where})."},
    # D09
    "kb_document.title": {"pl": "Aktywny schemat PS to „{file}” ({pages} str.)", "en": "Active PS schematic is “{file}” ({pages} p.)", "de": "Aktiver PS-Schaltplan ist „{file}“ ({pages} S.)"},
    "kb_document.desc": {
        "pl": "Jako aktywny schemat projektu oznaczony jest dokument „{file}”, a właściwy schemat „{main}” ({mpages} str.) jest nieaktywny. Część funkcji asystenta korzysta z aktywnego schematu.",
        "en": "Document “{file}” is marked as the active project schematic while the real schematic “{main}” ({mpages} p.) is inactive. Some assistant features use the active schematic.",
        "de": "Dokument „{file}“ ist als aktiver Projektschaltplan markiert, der eigentliche Schaltplan „{main}“ ({mpages} S.) ist inaktiv. Einige Assistentenfunktionen nutzen den aktiven Schaltplan."},
    "kb_document.fix": {"pl": "Przenieść dokument do podfolderu instrukcji/dokumentów i ponownie zsynchronizować Bazę wiedzy.", "en": "Move the document to a manuals/documents subfolder and resync the knowledge base.", "de": "Dokument in einen Unterordner für Anleitungen/Dokumente verschieben und die Wissensbasis neu synchronisieren."},
    # D10
    "busbar_unmodeled.title": {"pl": "Zwora {members} bez połączenia elektrycznego", "en": "Bus bar {members} without an electrical connection", "de": "Brücke {members} ohne elektrische Verbindung"},
    "busbar_unmodeled.desc": {
        "pl": "Szyna/zwora łącząca {members} jest narysowana tylko grafiką (prostokąt/linia) albo wynika z brakującego terminala — raport połączeń jej nie zawiera. Asystent odtwarza ją z geometrii PDF. Uchwyt: {holder}. Odczepy: {taps}.",
        "en": "The bus bar/jumper joining {members} is drawn only as graphics (rectangle/line) or follows from a missing terminal — the connection report does not contain it. The assistant rebuilds it from the PDF geometry. Holder: {holder}. Taps: {taps}.",
        "de": "Die Schiene/Brücke zwischen {members} ist nur grafisch gezeichnet (Rechteck/Linie) oder ergibt sich aus einem fehlenden Anschluss — der Verbindungsbericht enthält sie nicht. Der Assistent rekonstruiert sie aus der PDF-Geometrie. Halter: {holder}. Abgriffe: {taps}."},
    "busbar_unmodeled.fix": {"pl": "Zamodelować zworę {members} jako połączenie elektryczne (przewód/mostek/bus-bar z pinami) w E3.", "en": "Model the bus bar {members} as an electrical connection (wire/jumper/bus bar with pins) in E3.", "de": "Brücke {members} in E3 als elektrische Verbindung modellieren (Leitung/Brücke/Sammelschiene mit Pins)."},
    # D11
    "fuse_holder_unlinked.title": {"pl": "{fuse} w oprawce {holder} — brak powiązania w E3", "en": "{fuse} in holder {holder} — no link in E3", "de": "{fuse} im Halter {holder} — keine Verknüpfung in E3"},
    "fuse_holder_unlinked.desc": {
        "pl": "Bezpiecznik {fuse} siedzi w oprawce {holder} o innym numerze; raport nie wiąże elementu z gniazdem — para odtworzona z położenia etykiet na schemacie. Technik szukający „FH” o numerze bezpiecznika trafi w złe gniazdo.",
        "en": "Fuse {fuse} sits in holder {holder} with a different number; the report does not link the element to its socket — the pair was rebuilt from label positions on the schematic. A technician looking for the 'FH' with the fuse number finds the wrong socket.",
        "de": "Sicherung {fuse} sitzt im Halter {holder} mit anderer Nummer; der Bericht verknüpft Element und Sockel nicht — das Paar wurde aus den Etikettenpositionen rekonstruiert. Ein Techniker, der den 'FH' mit der Sicherungsnummer sucht, findet den falschen Sockel."},
    "fuse_holder_unlinked.fix": {"pl": "Powiązać {fuse} z {holder} (podzespół/atrybut) albo ujednolicić numerację oprawki i bezpiecznika.", "en": "Link {fuse} with {holder} (sub-assembly/attribute) or align holder and fuse numbering.", "de": "{fuse} mit {holder} verknüpfen (Baugruppe/Attribut) oder Nummerierung von Halter und Sicherung angleichen."},
    # D12
    "box_fuse_hidden.title": {"pl": "Skrzynka {box}: {n} bezpieczników niewidocznych w raporcie", "en": "Box {box}: {n} fuses invisible in the report", "de": "Kasten {box}: {n} Sicherungen im Bericht unsichtbar"},
    "box_fuse_hidden.desc": {
        "pl": "Pozycje bezpieczników skrzynki {box} nie występują w raporcie połączeń (raport agreguje wyjścia do jednego punktu). Asystent odczytuje je z geometrii PDF: {list}.",
        "en": "The fuse positions of box {box} are not in the connection report (the report aggregates the outputs into one point). The assistant reads them from the PDF geometry: {list}.",
        "de": "Die Sicherungspositionen des Kastens {box} fehlen im Verbindungsbericht (der Bericht fasst die Ausgänge zusammen). Der Assistent liest sie aus der PDF-Geometrie: {list}."},
    "box_fuse_hidden.fix": {"pl": "Zamodelować bezpieczniki skrzynki {box} jako osobne urządzenia z pinami wejścia/wyjścia w E3.", "en": "Model the fuses of box {box} as separate devices with input/output pins in E3.", "de": "Sicherungen des Kastens {box} in E3 als eigene Geräte mit Ein-/Ausgangspins modellieren."},
    "box_fuse_verify.title": {"pl": "Skrzynka {box}: zweryfikuj odczytane pozycje", "en": "Box {box}: verify the detected positions", "de": "Kasten {box}: erkannte Positionen prüfen"},
    "box_fuse_verify.desc": {"pl": "Niepewne dopasowanie pozycji z geometrii PDF: {list}. Sprawdź na schemacie/w aucie.", "en": "Uncertain positions from PDF geometry: {list}. Check on the schematic/in the vehicle.", "de": "Unsichere Positionen aus der PDF-Geometrie: {list}. Im Schaltplan/Fahrzeug prüfen."},
    # D13
    "fuse_no_wiring.title": {"pl": "{dev}: bezpiecznik bez okablowania", "en": "{dev}: fuse without wiring", "de": "{dev}: Sicherung ohne Verdrahtung"},
    "fuse_no_wiring.desc": {
        "pl": "Element {dev} ({descr}{func}) jest w BOM, ale nie ma go w raporcie połączeń ani nie da się go powiązać z oprawką/szyną na schemacie. Asystent pokaże tylko kartę „rozpoznano, brak okablowania”.",
        "en": "Element {dev} ({descr}{func}) is in the BOM but not in the connection report and cannot be linked to a holder/bus bar on the schematic. The assistant only shows a 'recognised, no wiring' card.",
        "de": "Element {dev} ({descr}{func}) ist in der Stückliste, fehlt aber im Verbindungsbericht und lässt sich keinem Halter/keiner Schiene im Schaltplan zuordnen. Der Assistent zeigt nur „erkannt, keine Verdrahtung“."},
    "fuse_no_wiring.fix": {"pl": "Narysować/podłączyć {dev} (etykieta, oprawka, przewody) w E3.", "en": "Draw/connect {dev} (label, holder, wires) in E3.", "de": "{dev} in E3 zeichnen/anschließen (Etikett, Halter, Leitungen)."},
    # D14
    "pinout_missing.title": {"pl": "{art}: {n} złączy bez rysunku pinoutu", "en": "{art}: {n} connectors without a pinout drawing", "de": "{art}: {n} Stecker ohne Belegungszeichnung"},
    "pinout_missing.desc": {
        "pl": "Artykuł {art} ({sup}) — {n} złączy projektu ({devs}), {pins} pinów — nie ma rekordu w słowniku pinoutów ani wbudowanej rodziny rysunku. Opis: {desc}",
        "en": "Article {art} ({sup}) — {n} project connectors ({devs}), {pins} pins — has no entry in the pinout dictionary and no built-in drawing family. Description: {desc}",
        "de": "Artikel {art} ({sup}) — {n} Projektstecker ({devs}), {pins} Pins — kein Eintrag im Belegungswörterbuch und keine eingebaute Zeichenfamilie. Beschreibung: {desc}"},
    "pinout_missing.fix": {"pl": "Zdefiniować pinout artykułu {art} w edytorze pinoutów (Zestawienia → rysunek złącza).", "en": "Define the pinout of article {art} in the pinout editor (Summaries → connector drawing).", "de": "Belegung von Artikel {art} im Belegungseditor definieren (Übersichten → Steckerzeichnung)."},
    "pinout_unverified.title": {"pl": "{art}: pinout niezweryfikowany ({n} złączy)", "en": "{art}: pinout unverified ({n} connectors)", "de": "{art}: Belegung unbestätigt ({n} Stecker)"},
    "pinout_unverified.desc": {
        "pl": "Artykuł {art} ({sup}) — {n} złączy projektu ({devs}), {pins} pinów — ma rysunek oznaczony jako niezweryfikowany (numeracja gniazd wymaga potwierdzenia z dokumentacji). Opis: {desc}",
        "en": "Article {art} ({sup}) — {n} project connectors ({devs}), {pins} pins — its drawing is marked unverified (cavity numbering needs confirmation from documentation). Description: {desc}",
        "de": "Artikel {art} ({sup}) — {n} Projektstecker ({devs}), {pins} Pins — Zeichnung als unbestätigt markiert (Kammernummerierung anhand der Dokumentation prüfen). Beschreibung: {desc}"},
    "pinout_unverified.fix": {"pl": "Zweryfikować numerację gniazd {art} z rysunkiem katalogowym i zdjęciem flagi „niezweryfikowany”.", "en": "Verify the cavity numbering of {art} against the catalogue drawing and clear the “unverified” flag.", "de": "Kammernummerierung von {art} anhand der Katalogzeichnung prüfen und die Markierung „unbestätigt“ entfernen."},
    # D15
    "pdf_report_label.title": {"pl": "{dev}: etykieta na schemacie nieznana raportowi", "en": "{dev}: schematic label unknown to the report", "de": "{dev}: Schaltplan-Etikett dem Bericht unbekannt"},
    "pdf_report_label.desc": {
        "pl": "Oznaczenie -{dev} narysowane jest na schemacie (str. {page}, ark. {sheet}), ale nie występuje w raporcie połączeń ani w BOM.{near} Albo etykieta jest błędna, albo elementu nie ma w danych.",
        "en": "The label -{dev} is drawn on the schematic (p. {page}, sheet {sheet}) but appears neither in the connection report nor in the BOM.{near} Either the label is wrong or the element is missing from the data.",
        "de": "Die Bezeichnung -{dev} ist im Schaltplan gezeichnet (S. {page}, Blatt {sheet}), kommt aber weder im Verbindungsbericht noch in der Stückliste vor.{near} Entweder ist das Etikett falsch oder das Element fehlt in den Daten."},
    "pdf_report_label.near": {"pl": " Podobne w raporcie: {near}.", "en": " Similar in the report: {near}.", "de": " Ähnlich im Bericht: {near}."},
    "pdf_report_label.fix": {"pl": "Zweryfikować etykietę -{dev} w E3 (literówka w oznaczeniu albo brakujący element raportu).", "en": "Verify the label -{dev} in E3 (designation typo or missing report element).", "de": "Bezeichnung -{dev} in E3 prüfen (Tippfehler oder fehlendes Berichtselement)."},
    # eksport
    "x.sheet": {"pl": "Poprawki", "en": "Corrections", "de": "Korrekturen"},
    "x.h.no": {"pl": "Lp.", "en": "No.", "de": "Nr."},
    "x.h.id": {"pl": "ID", "en": "ID", "de": "ID"},
    "x.h.ps": {"pl": "PS", "en": "PS", "de": "PS"},
    "x.h.rev": {"pl": "Rewizja", "en": "Revision", "de": "Revision"},
    "x.h.sheet": {"pl": "Arkusz", "en": "Sheet", "de": "Blatt"},
    "x.h.page": {"pl": "Strona PDF", "en": "PDF page", "de": "PDF-Seite"},
    "x.h.grid": {"pl": "Pole", "en": "Grid", "de": "Feld"},
    "x.h.devices": {"pl": "Oznaczenia", "en": "Designations", "de": "Kennzeichnungen"},
    "x.h.cat": {"pl": "Kategoria", "en": "Category", "de": "Kategorie"},
    "x.h.problem": {"pl": "Opis problemu", "en": "Problem description", "de": "Problembeschreibung"},
    "x.h.fix": {"pl": "Proponowana poprawka w E3", "en": "Proposed correction in E3", "de": "Vorgeschlagene Korrektur in E3"},
    "x.h.sev": {"pl": "Priorytet", "en": "Priority", "de": "Priorität"},
    "x.h.img": {"pl": "Wycinek", "en": "Snapshot", "de": "Ausschnitt"},
    "x.h.reply": {"pl": "Odpowiedź inżyniera", "en": "Engineer reply", "de": "Antwort Ingenieur"},
    "x.subject": {"pl": "{ps} {name} — poprawki schematu E3 ({n} poz.)", "en": "{ps} {name} — E3 schematic corrections ({n} items)", "de": "{ps} {name} — Korrekturen E3-Schaltplan ({n} Pos.)"},
    "x.body": {
        "pl": "Dzień dobry,\n\nw schemacie projektu {ps} ({name}, rewizja: {rev}) znaleźliśmy {n} miejsc wymagających poprawy w Zuken E3 — lista w załączniku (XLSX) wraz z wycinkami schematu.\nProszę o naniesienie poprawek i odesłanie pliku z uzupełnioną kolumną „Odpowiedź inżyniera”.\n\nPozdrawiam\n",
        "en": "Hello,\n\nin the schematic of project {ps} ({name}, revision: {rev}) we found {n} places that need correcting in Zuken E3 — see the attached list (XLSX) with schematic snapshots.\nPlease apply the corrections and send the file back with the “Engineer reply” column filled in.\n\nBest regards\n",
        "de": "Guten Tag,\n\nim Schaltplan des Projekts {ps} ({name}, Revision: {rev}) haben wir {n} Stellen gefunden, die in Zuken E3 korrigiert werden müssen — Liste im Anhang (XLSX) mit Schaltplanausschnitten.\nBitte die Korrekturen einarbeiten und die Datei mit ausgefüllter Spalte „Antwort Ingenieur“ zurücksenden.\n\nMit freundlichen Grüßen\n"},
    # serwer
    "notFound": {"pl": "Nie znaleziono zgłoszenia.", "en": "Issue not found.", "de": "Meldung nicht gefunden."},
    "noSuggestion": {"pl": "Zgłoszenie nie ma propozycji do zastosowania.", "en": "The issue has no suggestion to apply.", "de": "Die Meldung hat keinen anwendbaren Vorschlag."},
    "scanRunning": {"pl": "Skan już trwa.", "en": "A scan is already running.", "de": "Ein Scan läuft bereits."},
    "noIssues": {"pl": "Brak zgłoszeń do eksportu.", "en": "No issues to export.", "de": "Keine Meldungen zum Export."},
}


def amsg(key, lang="pl", **kw):
    if lang not in ("pl", "en", "de"):
        lang = "pl"
    e = AUDIT_MSG.get(key)
    if not e:
        return key
    txt = e.get(lang) or e["pl"]
    if kw:
        try:
            return txt.format(**kw)
        except (KeyError, IndexError, ValueError):
            return txt
    return txt


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _j(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else None


def _uj(s, default=None):
    if not s:
        return default
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════
# TABELE LOKALNE
# ═══════════════════════════════════════════════════════════════════
_TABLES_READY = {"path": None}


def init_audit_tables():
    if _TABLES_READY["path"] == zs.DB_PATH:
        return
    zs.init_zuken_tables()
    conn = zs.get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT NOT NULL,
            category TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT 'engineer',
            severity TEXT DEFAULT 'warn',
            status TEXT DEFAULT 'new',
            msg_key TEXT,
            msg_params TEXT,
            title TEXT,
            description TEXT,
            devices TEXT,
            location TEXT,
            evidence TEXT,
            suggestion TEXT,
            patch_id INTEGER,
            detector TEXT,
            fingerprint TEXT,
            workaround TEXT,
            source_revision TEXT,
            resolved_revision TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            last_seen_at TEXT,
            sent_at TEXT,
            batch_id INTEGER,
            query TEXT,
            note TEXT
        );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_zuken_issues_fp ON zuken_issues (ps_code, fingerprint) WHERE fingerprint IS NOT NULL;")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_issues_ps ON zuken_issues (ps_code, status);")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_issue_files (
            id TEXT PRIMARY KEY,
            issue_id INTEGER NOT NULL,
            filename TEXT,
            mime TEXT,
            data BLOB,
            created TEXT
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_zuken_issue_files ON zuken_issue_files (issue_id);")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zuken_issue_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ps_code TEXT,
            lang TEXT,
            recipient TEXT,
            issue_ids TEXT,
            out_dir TEXT,
            created_by TEXT,
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    _TABLES_READY["path"] = zs.DB_PATH


# ═══════════════════════════════════════════════════════════════════
# POMOCNICZE: REWIZJA, SCHEMAT GŁÓWNY, GEOMETRIA STRONY
# ═══════════════════════════════════════════════════════════════════
def ps_revision_key(cur, ps):
    """Stan rewizji danych PS: najnowszy import raportów + mtime schematu."""
    conn_ids, bom_ids = zs._ps_project_ids(cur, ps)
    ids = list(conn_ids) + list(bom_ids)
    imp = ""
    if ids:
        ph = ",".join("?" * len(ids))
        r = cur.execute(f"SELECT MAX(imported_at) FROM zuken_projects WHERE id IN ({ph}) AND COALESCE(is_active,1)=1", ids).fetchone()
        imp = (r[0] or "") if r else ""
    sch = main_schematic(cur, ps)
    mt = ""
    if sch:
        mt = datetime.fromtimestamp(sch["file_mtime"] or 0).isoformat(timespec="seconds")
    return f"{imp}|{mt}"


def main_schematic(cur, ps):
    """Właściwy schemat E3 projektu: dokument 'schematic' PS z największą
    liczbą symboli (u Walii aktywna bywa karta katalogowa złącza)."""
    r = cur.execute("""
        SELECT s.id, s.filename, s.filepath, s.file_mtime, s.total_pages, s.is_active,
               (SELECT COUNT(*) FROM zuken_pdf_symbols y WHERE y.schematic_id = s.id) AS nsym
        FROM zuken_pdf_schematics s
        WHERE s.ps_code = ? AND COALESCE(s.doc_kind, 'schematic') = 'schematic'
        ORDER BY (nsym >= 100) DESC, s.is_active DESC, nsym DESC, s.id DESC LIMIT 1;
    """, (ps,)).fetchone()
    if not r or not r["nsym"]:
        return None
    d = dict(r)
    try:
        d["filepath"] = zs.resolve_kb_filepath(d["filepath"], heal_db=False) or d["filepath"]
    except Exception:
        pass
    return d


_PAGE_TOKENS = {}
_PAGE_SIZE = {}


def _pdf_reader(filepath):
    if zs.pypdf is None or not filepath or not os.path.exists(filepath):
        return None
    rd = zs._PDF_READERS.get(filepath)
    if rd is None:
        rd = zs.pypdf.PdfReader(filepath)
        zs._PDF_READERS[filepath] = rd
    return rd


def page_tokens(filepath, page):
    """Wszystkie teksty strony z pozycją [(x, y, text)] (współrzędne PDF)."""
    key = (filepath, page)
    if key in _PAGE_TOKENS:
        return _PAGE_TOKENS[key]
    items = []
    try:
        rd = _pdf_reader(filepath)
        if rd and 1 <= page <= len(rd.pages):
            pg = rd.pages[page - 1]
            mb = pg.mediabox
            _PAGE_SIZE[key] = (float(mb.left), float(mb.bottom), float(mb.width), float(mb.height), int(pg.get("/Rotate") or 0))

            def _vis(text, cm, tm, font, size):
                t = (text or "").strip()
                if t:
                    x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                    y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                    items.append((x, y, t))
            pg.extract_text(visitor_text=_vis)
    except Exception:
        items = []
    _PAGE_TOKENS[key] = items
    return items


def page_size(filepath, page):
    key = (filepath, page)
    if key not in _PAGE_SIZE:
        page_tokens(filepath, page)
    return _PAGE_SIZE.get(key)


def find_device_positions(tokens, dev_code):
    """Wszystkie pozycje etykiety urządzenia na stronie (pełny kod albo
    '-<clean>' — etykiety E3 bywają łamane na =SYS / +LOC / -DEV)."""
    full = (dev_code or "").strip()
    clean = zs.clean_device_code(full)
    if not clean:
        return []
    short = "-" + clean
    exact, other = [], []
    for x, y, t in tokens:
        if t == full:
            exact.append((x, y))
        elif t == short or (t.endswith(short) and re.match(r"^[=+]", t)):
            other.append((x, y))
    return exact + other


def find_device_pos(tokens, dev_code):
    p = find_device_positions(tokens, dev_code)
    return p[0] if p else None


def grid_ref(filepath, page, x, y):
    """Pole siatki ramki arkusza ('2.B') z etykiet ramki (cyfry u góry,
    litery z lewej). None gdy ramka nierozpoznana."""
    toks = page_tokens(filepath, page)
    sz = page_size(filepath, page)
    if not toks or not sz:
        return None
    _, _, w, h, _ = sz
    nums = [(tx, ty, int(t)) for tx, ty, t in toks if re.fullmatch(r"\d{1,2}", t) and ty > h * 0.9]
    lets = [(tx, ty, t) for tx, ty, t in toks if re.fullmatch(r"[A-H]", t) and tx < w * 0.06]
    if len({n for _, _, n in nums}) < 4 or len({t for _, _, t in lets}) < 3:
        return None
    col = min(nums, key=lambda n: abs(n[0] - x))[2]
    row = min(lets, key=lambda n: abs(n[1] - y))[2]
    return f"{col}.{row}"


def device_location(ctx, dev_code):
    """Lokalizacja urządzenia na schemacie głównym: strona, arkusz, pole, bbox."""
    sch = ctx.schematic
    if not sch:
        return None
    clean = zs.clean_device_code(dev_code)
    pages = ctx.symbol_pages.get(clean) or []
    if not pages:
        return None
    pos, page = None, pages[0]
    for p in pages:
        pos = find_device_pos(page_tokens(sch["filepath"], p), dev_code)
        if pos:
            page = p
            break
    loc = {"schematic_id": sch["id"], "page": page}
    sh = ctx.sheets.get(page)
    if sh:
        loc["sheet_number"], loc["sheet_title"] = sh
    if pos:
        loc["bbox"] = [pos[0] - 45, pos[1] - 45, pos[0] + 45, pos[1] + 45]
        g = grid_ref(sch["filepath"], page, pos[0], pos[1])
        if g:
            loc["grid"] = g
    return loc


# ═══════════════════════════════════════════════════════════════════
# KONTEKST SKANU (leniwe dane wspólne dla wykrywaczy)
# ═══════════════════════════════════════════════════════════════════
_APP_RE = re.compile(r"^(A|S|K|Q|G|M|B|H|P|N|T)\d", re.I)
_SKIP_BOM_CATS = ("Element montażowy", "Pin / Terminal", "Bezpiecznik",
                  "Gniazdo / Skrzynka bezpieczników")
_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]{4,}")


class Ctx:
    def __init__(self, cur, ps):
        self.cur = cur
        self.ps = ps
        self.conn_ids, self.bom_ids = zs._ps_project_ids(cur, ps)
        self._cache = {}

    def _memo(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    @property
    def schematic(self):
        return self._memo("sch", lambda: main_schematic(self.cur, self.ps))

    @property
    def symbol_pages(self):
        def f():
            out = defaultdict(list)
            sch = self.schematic
            if sch:
                for r in self.cur.execute(
                        "SELECT symbol_clean, page_number FROM zuken_pdf_symbols WHERE schematic_id = ? ORDER BY page_number",
                        (sch["id"],)):
                    pl = out[r[0]]
                    if r[1] not in pl:
                        pl.append(r[1])
            return out
        return self._memo("sympages", f)

    @property
    def sheets(self):
        def f():
            sch = self.schematic
            if not sch:
                return {}
            return {r[0]: (r[1] or "", r[2] or "") for r in self.cur.execute(
                "SELECT page_number, sheet_number, sheet_title FROM zuken_pdf_sheets WHERE schematic_id = ?",
                (sch["id"],))}
        return self._memo("sheets", f)

    @property
    def connections(self):
        def f():
            if not self.conn_ids:
                return []
            ph = ",".join("?" * len(self.conn_ids))
            return [dict(r) for r in self.cur.execute(f"""
                SELECT from_device, from_pin, to_device, to_pin, wire_number, signal, signal_name
                FROM zuken_connections WHERE project_id IN ({ph});""", self.conn_ids)]
        return self._memo("conns", f)

    @property
    def neighbours(self):
        """(dev, pin) -> {(dev, pin): wiersz} — surowy graf bez łatek."""
        def f():
            nb = defaultdict(dict)
            for r in self.connections:
                a = ((r["from_device"] or "").strip(), (r["from_pin"] or "").strip())
                b = ((r["to_device"] or "").strip(), (r["to_pin"] or "").strip())
                if a[0] and b[0]:
                    nb[a][b] = r
                    nb[b][a] = r
            return nb
        return self._memo("nb", f)

    @property
    def conn_cleans(self):
        def f():
            s = Counter()
            for r in self.connections:
                for d in (r["from_device"], r["to_device"]):
                    if d and d.strip():
                        s[zs.clean_device_code(d)] += 1
            return s
        return self._memo("conncl", f)

    @property
    def bom_devices(self):
        def f():
            if not self.bom_ids:
                return []
            ph = ",".join("?" * len(self.bom_ids))
            seen, out = set(), []
            for r in self.cur.execute(f"""
                SELECT d.device_code, d.device_clean, d.function, i.article_number,
                       i.description, i.category, i.supplier
                FROM zuken_bom_devices d JOIN zuken_bom_items i ON i.id = d.bom_item_id
                WHERE i.project_id IN ({ph}) ORDER BY i.project_id DESC;""", self.bom_ids):
                if r["device_code"] in seen:
                    continue
                seen.add(r["device_code"])
                out.append(dict(r))
            return out
        return self._memo("bom", f)

    @property
    def bom_by_clean(self):
        def f():
            m = defaultdict(list)
            for d in self.bom_devices:
                m[d["device_clean"] or zs.clean_device_code(d["device_code"])].append(d)
            return m
        return self._memo("bomcl", f)


def _fmt_where(items, limit=6):
    items = [i for i in dict.fromkeys(items) if i]
    s = ", ".join(items[:limit])
    if len(items) > limit:
        s += f" (+{len(items) - limit})"
    return s


def _short_desc(d, n=60):
    s = re.sub(r"\s+", " ", (d or "")).strip()
    return s if len(s) <= n else s[:n - 1] + "…"


# ═══════════════════════════════════════════════════════════════════
# WYKRYWACZE (etap 'data')
# ═══════════════════════════════════════════════════════════════════
def _f(fp, category, msg_key, params, devices=(), loc_dev=None, location=None,
       evidence=None, suggestion=None, severity=None, workaround=None):
    return {"fp": fp, "category": category, "msg_key": msg_key, "params": params,
            "devices": list(devices), "loc_dev": loc_dev, "location": location,
            "evidence": evidence, "suggestion": suggestion,
            "severity": severity or CATEGORIES[category][1], "workaround": workaround}


def det_device_unconnected(ctx):
    """D01: aparat z BOM narysowany na schemacie, bez żadnego pinu w raporcie."""
    out = []
    conn = ctx.conn_cleans
    syms = ctx.symbol_pages
    for d in ctx.bom_devices:
        code = d["device_code"] or ""
        cl = d["device_clean"] or zs.clean_device_code(code)
        if (not cl or cl in conn or not _APP_RE.match(cl) or d["category"] in _SKIP_BOM_CATS
                or code.startswith("=BOM") or cl not in syms):
            continue
        out.append(_f(f"D01|{code}", "device_unconnected", "device_unconnected",
                      {"dev": code, "art": d["article_number"] or "—",
                       "descr": _short_desc(d["description"]), "page": syms[cl][0]},
                      devices=[code], loc_dev=code,
                      evidence={"bom": {k: d[k] for k in ("article_number", "description", "category", "function")}}))
    return out


def _floating_terminals(ctx):
    """Końcówki -RT o stopniu 1 w surowym grafie: [(node, peer, row)]."""
    res = []
    for node, nb in ctx.neighbours.items():
        cl = zs.clean_device_code(node[0])
        if not re.match(r"^RT\d", cl or "") or len(nb) != 1:
            continue
        peer, row = next(iter(nb.items()))
        res.append((node, peer, row))
    return res


def det_dangling_terminal(ctx):
    """D02: końcówka oczkowa z jednym przewodem — miejsce montażu
    (szpilka aparatu) nieprzypisane. Propozycja: aparat bez połączeń na tej
    samej stronie schematu najbliżej etykiety końcówki."""
    out = []
    sch = ctx.schematic
    unconnected = {}
    for d in ctx.bom_devices:
        cl = d["device_clean"] or zs.clean_device_code(d["device_code"])
        if (cl and cl not in ctx.conn_cleans and _APP_RE.match(cl) and cl in ctx.symbol_pages
                and d["category"] not in _SKIP_BOM_CATS and not (d["device_code"] or "").startswith("=BOM")):
            unconnected[cl] = d["device_code"]
    # terminale przy oprawkach przezroczystych dla raportu i odczepy szyn
    # obsługuje heurystyka bezpieczników (zgłaszane przez D10/D11/D13)
    try:
        rails = _rails(ctx)
    except Exception:
        rails = {}
    fuse_terms = {t for v in (rails.get("terms") or {}).values() for t in v}
    for bars in (rails.get("bars") or {}).values():
        for b in (bars or {}).values():
            fuse_terms |= set(b.get("taps") or [])
    floating = [x for x in _floating_terminals(ctx) if x[0][0] not in fuse_terms]
    fl_nodes = {n for n, _, _ in floating}
    emitted = set()
    for node, peer, row in floating:
        if peer in fl_nodes and peer in emitted:
            continue            # kabel oczko-oczko: jedno zgłoszenie na przewód
        emitted.add(node)
        code = node[0]
        cl = zs.clean_device_code(code)
        bom = (ctx.bom_by_clean.get(cl) or [{}])[0]
        cand, conf, cpin = None, None, ""
        if sch:
            for p in ctx.symbol_pages.get(cl) or []:
                toks = page_tokens(sch["filepath"], p)
                pos = find_device_pos(toks, code)
                best = None
                for ucl, ucode in unconnected.items():
                    if p not in (ctx.symbol_pages.get(ucl) or []):
                        continue
                    for u in (find_device_positions(toks, ucode) or [None]):
                        dist = ((u[0] - pos[0]) ** 2 + (u[1] - pos[1]) ** 2) ** 0.5 if (u and pos) else 9e9
                        if best is None or dist < best[0]:
                            best = (dist, ucode, u)
                if best:
                    cand = best[1]
                    conf = "medium" if best[0] < 400 else "low"
                    # pin aparatu: pojedyncza litera (A/B...) pod etykietą
                    # aparatu, najbliższa końcówce (szpilki ML-RBS: A/B)
                    sz = page_size(sch["filepath"], p)
                    if best[2] and pos and sz:
                        ux, uy = best[2]
                        pins = [(abs(x - pos[0]) + abs(y - pos[1]), t) for x, y, t in toks
                                if re.fullmatch(r"[A-Z]", t) and sz[2] * 0.05 < x < sz[2] * 0.95
                                and abs(x - ux) < 160 and 0 < uy - y < 250]
                        if pins:
                            cpin = min(pins)[1]
                    break
        sugg = None
        cand_dev = cand
        if cand:
            sugg = {"kind": "patch", "confidence": conf,
                    "payload": {"kind": "connection", "from_device": code, "from_pin": node[1] or "1",
                                "to_device": cand, "to_pin": cpin, "link": "stud"},
                    "note": "pin"}
            if cpin:
                cand = f"{cand}:{cpin}"
        wire = row.get("wire_number") or row.get("signal") or "?"
        both = peer in fl_nodes
        out.append(_f(f"D02|{code}:{node[1]}", "dangling_terminal", "dangling_terminal",
                      {"dev": code + (f" ↔ {peer[0]}" if both else ""),
                       "descr": _short_desc(bom.get("function") or bom.get("description") or ""),
                       "wire": wire, "peer": f"{peer[0]}:{peer[1]}", "cand": cand or ""},
                      devices=[code] + ([peer[0]] if both else []) + ([cand_dev] if cand_dev else []), loc_dev=code,
                      evidence={"row": row}, suggestion=sugg))
    return out


def det_device_no_location(ctx):
    """D03: kod bez =system+lokalizacja, gdy większość projektu je ma."""
    devs = [d for d in ctx.bom_devices if d["device_code"]]
    if not devs:
        return []
    full = sum(1 for d in devs if d["device_code"].startswith(("=", "+")))
    pct = round(100 * full / len(devs))
    if pct < 70:
        return []
    out = []
    sch = ctx.schematic
    for d in devs:
        code = d["device_code"]
        cl = d["device_clean"] or zs.clean_device_code(code)
        if code.startswith(("=", "+")) or not cl or cl not in ctx.symbol_pages:
            continue
        if not (_APP_RE.match(cl) or re.match(r"^(X|F|K)\d", cl)):
            continue
        sug = ""
        for p in (ctx.symbol_pages[cl] if sch else []):
            toks = page_tokens(sch["filepath"], p)
            pos = find_device_pos(toks, code)
            if not pos:
                continue

            def _near(rx):
                c = [(abs(x - pos[0]) + abs(y - pos[1]), m.group(0)) for x, y, t in toks
                     for m in [re.match(rx, t)] if m]
                return min(c) if c else None
            a = _near(r"^=[A-Z0-9]+(?:\+[A-Z0-9]+)?")
            b = _near(r"^\+[A-Z0-9]+$")
            if a and a[0] < 300:
                sug = a[1]
                if "+" not in sug and b and b[0] < 300:
                    sug += b[1]
            break
        out.append(_f(f"D03|{code}", "device_no_location", "device_no_location",
                      {"dev": code, "pct": pct, "sug": sug},
                      devices=[code], loc_dev=code))
    return out


def det_bom_conn_mismatch(ctx):
    """D04: urządzenie w raporcie połączeń bez wpisu w BOM."""
    out = []
    if not ctx.bom_ids:
        return out
    bomcl = ctx.bom_by_clean
    full_by_clean = {}
    for r in ctx.connections:
        for d in (r["from_device"], r["to_device"]):
            if d and d.strip():
                full_by_clean.setdefault(zs.clean_device_code(d), d.strip())
    for cl, n in ctx.conn_cleans.items():
        if not cl or cl in bomcl or not re.match(r"^[A-Z]{1,3}\d", cl):
            continue
        if re.match(r"^(SP|W)\d", cl) or cl.startswith(("999", "_")):
            continue
        code = full_by_clean.get(cl, cl)
        out.append(_f(f"D04|{cl}", "bom_conn_mismatch", "bom_conn_mismatch",
                      {"dev": code, "n": n}, devices=[code], loc_dev=code))
    return out


def _dl(a, b):
    """Odległość Damerau-Levenshtein (optimal string alignment)."""
    la, lb = len(a), len(b)
    prev2, prev = None, list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + cost)
        prev2, prev = prev, cur
    return prev[lb]


def _typo_vocab(cur):
    """Słownictwo zaufane = słowa z docelowych tłumaczeń (en/de) słownika
    + mapa token->en dla wpisów pojedynczych (znane literówki)."""
    vocab, tok = set(), {}
    for r in cur.execute("SELECT form, kind, en, de FROM zuken_translations"):
        for v in (r["en"], r["de"]):
            for w in _WORD_RE.findall(v or ""):
                vocab.add(w.upper())
        en = (r["en"] or "").strip()
        if r["kind"] == "token" and en and " " not in en:
            tok[(r["form"] or "").upper()] = en.upper()
    return vocab, tok


def det_typo(ctx):
    """D05: literówki w funkcjach BOM, sygnałach i tytułach arkuszy.
    Znane (słownik koryguje formę do innej o małej odległości) = high;
    kandydaci z porównania ze słownictwem zaufanym = medium."""
    vocab, tok = _typo_vocab(ctx.cur)
    occ = defaultdict(list)
    for d in ctx.bom_devices:
        for w in _WORD_RE.findall(d["function"] or ""):
            occ[w.upper()].append(d["device_code"])
    for r in ctx.connections:
        for fld in ("signal", "signal_name"):
            for w in _WORD_RE.findall(r[fld] or ""):
                occ[w.upper()].append(f"„{r[fld]}”")
    for pg, (num, title) in ctx.sheets.items():
        for w in _WORD_RE.findall(title or ""):
            occ[w.upper()].append(f"ark. {num or pg}")
    vl = list(vocab)
    out = []
    for w, where in sorted(occ.items()):
        if w in vocab:
            continue
        lim = 1 if len(w) <= 6 else 2
        target, known = None, False
        u = tok.get(w)
        if u and re.sub(r"[^A-ZÄÖÜß]", "", u) != w and _dl(w, u) <= lim:
            target, known = u, True
        elif len(w) >= 5:
            cands = [x for x in vl if x[0] == w[0] and abs(len(x) - len(w)) <= lim
                     and x not in (w + "S", w + "ES") and w not in (x + "S", x + "ES")
                     and _dl(w, x) <= lim]
            if len(cands) == 1 or (cands and len(w) >= 7):
                target = sorted(cands, key=lambda x: (_dl(w, x), -len(x)))[0]
        if not target:
            continue
        devs = [x for x in where if x.startswith(("=", "-", "+"))]
        sugg = None
        if not known:
            low = target.lower()
            e = zs._terms_map(ctx.cur).get(low) or {}
            sugg = {"kind": "translation", "confidence": "medium",
                    "payload": {"form": w.lower(), "kind": "token",
                                "pl": e.get("pl") or low, "en": e.get("en") or low,
                                "de": e.get("de") or low}}
        out.append(_f(f"D05|{w}>{target}", "typo", "typo",
                      {"form": w, "target": target, "where": _fmt_where(where), "known": "1" if known else ""},
                      devices=devs[:12], loc_dev=devs[0] if devs else None,
                      evidence={"occurrences": list(dict.fromkeys(where))[:40], "known": known},
                      suggestion=sugg, workaround="dictionary" if known else None))
    return out


def det_photo_missing(ctx):
    """D06: artykuły aparatów/złączy/bezpieczników bez zdjęcia (zbiorczo)."""
    arts = {}
    for d in ctx.bom_devices:
        a = (d["article_number"] or "").strip()
        if not a or a in arts or d["category"] in ("Element montażowy", "Inne komponenty") and not _APP_RE.match(d["device_clean"] or ""):
            continue
        arts[a] = d
    miss = []
    for a in arts:
        try:
            if not zs.find_local_component_image(a):
                miss.append(a)
        except Exception:
            continue
    if not miss:
        return []
    return [_f("D06|photos", "photo_missing", "photo_missing",
               {"n": len(miss), "list": _fmt_where(miss, 15)},
               evidence={"articles": miss[:500]},
               suggestion={"kind": "photos", "confidence": "high", "payload": {"articles": miss[:500]}})]


def det_term_untranslated(ctx):
    """D07: zbiorczo — kolejka nietłumaczonych tekstów schematu."""
    rows = ctx.cur.execute("SELECT form FROM zuken_term_unknown ORDER BY count DESC LIMIT 400").fetchall()
    if not rows:
        return []
    forms = [r[0] for r in rows]
    return [_f("D07|terms", "term_untranslated", "term_untranslated",
               {"n": len(forms), "list": _fmt_where(forms, 12)}, evidence={"forms": forms})]


def det_platform_term(ctx):
    """D08: termin niezgodny z pojazdem bazowym (KFG na Sprinterze)."""
    meta = get_ps_meta(ctx.ps, cur=ctx.cur)
    veh = meta.get("base_vehicle") or ""
    if not veh:
        return []
    out = []
    terms = list_platform_terms(cur=ctx.cur)
    sch = ctx.schematic
    for t in terms:
        plats = t.get("platforms") or []
        if not plats or veh in plats:
            continue
        rx = re.compile(r"(?<![A-Z0-9])" + re.escape(t["term"].upper()) + r"(?![A-Z0-9])")
        where, devs = [], []
        if sch:
            for r in ctx.cur.execute("SELECT page_number, sheet_number, sheet_title, raw_text FROM zuken_pdf_sheets WHERE schematic_id = ? ORDER BY page_number", (sch["id"],)):
                if rx.search((r["sheet_title"] or "").upper()) or rx.search((r["raw_text"] or "").upper()):
                    where.append(f"ark. {r['sheet_number'] or r['page_number']}")
        for d in ctx.bom_devices:
            if rx.search(" ".join((d["function"] or "", d["article_number"] or "", d["description"] or "")).upper()):
                devs.append(d["device_code"])
        for r in ctx.connections:
            if rx.search(((r["signal"] or "") + " " + (r["signal_name"] or "")).upper()):
                where.append(f"„{r['signal'] or r['signal_name']}”")
        if not where and not devs:
            continue
        equiv = (t.get("equivalents") or {}).get(veh) or ""
        alias_terms = [t["term"].upper()]
        if equiv:
            rx_e = re.compile(r"(?<![A-Z0-9])" + re.escape(equiv.upper()) + r"(?![A-Z0-9])")
            for d in ctx.bom_devices:
                if rx_e.search(" ".join((d["function"] or "", d["article_number"] or "")).upper()):
                    alias_terms.append(d["device_clean"] or zs.clean_device_code(d["device_code"]))
        sugg = None
        if equiv:
            sugg = {"kind": "alias", "confidence": "high",
                    "payload": {"phrase": equiv.upper(), "terms": " ".join(dict.fromkeys([equiv.upper()] + alias_terms))}}
        loc = None
        first = next((w for w in where if w.startswith("ark. ")), None)
        if first and sch:
            num = first[5:]
            pg = next((p for p, (n, _) in ctx.sheets.items() if (n or str(p)) == num), None)
            if pg:
                loc = {"schematic_id": sch["id"], "page": pg, "sheet_number": num,
                       "sheet_title": ctx.sheets[pg][1]}
                toks = page_tokens(sch["filepath"], pg)
                hit = next(((x, y) for x, y, tt in toks if rx.search(tt.upper())), None)
                if hit:
                    loc["bbox"] = [hit[0] - 40, hit[1] - 40, hit[0] + 120, hit[1] + 40]
                    g = grid_ref(sch["filepath"], pg, hit[0], hit[1])
                    if g:
                        loc["grid"] = g
        out.append(_f(f"D08|{t['term'].upper()}", "platform_term", "platform_term",
                      {"term": t["term"].upper(), "vehicle": PLATFORMS.get(veh, veh),
                       "platforms": ", ".join(PLATFORMS.get(p, p) for p in plats),
                       "equiv": equiv or "?", "where": _fmt_where(where + devs)},
                      devices=devs[:12], location=loc, loc_dev=None if loc else (devs[0] if devs else None),
                      evidence={"where": where[:40], "devices": devs[:40]}, suggestion=sugg))
    return out


def det_kb_document(ctx):
    """D09: aktywny 'schemat' PS to nie właściwy schemat projektu."""
    act = ctx.cur.execute("""
        SELECT id, filename, total_pages FROM zuken_pdf_schematics
        WHERE ps_code = ? AND is_active = 1 AND COALESCE(doc_kind,'schematic') = 'schematic'
        ORDER BY id DESC LIMIT 1;""", (ctx.ps,)).fetchone()
    main = ctx.schematic
    if not main or not act or act["id"] == main["id"]:
        return []
    return [_f(f"D09|{act['filename']}", "kb_document", "kb_document",
               {"file": act["filename"], "pages": act["total_pages"] or 0,
                "main": main["filename"], "mpages": main["total_pages"] or 0},
               evidence={"active_id": act["id"], "main_id": main["id"]})]


# ═══════════════════════════════════════════════════════════════════
# WYKRYWACZE (etap 'pdf') — emitery z istniejących heurystyk asystenta
# (szyny/zwory, parowanie oprawek, skrzynki bezpieczników). Nie zmieniają
# ich wyników; zgłaszają to, co heurystyka musiała odtworzyć z geometrii.
# ═══════════════════════════════════════════════════════════════════
def _rails(ctx):
    def f():
        adj = zs._wire_adjacency(ctx.cur, ctx.conn_ids, with_patches=False)
        return zs._ps_fuse_rails(ctx.cur, ctx.conn_ids, ctx.ps, adj) or {}
    return ctx._memo("rails", f)


def _loc_for_devices(ctx, devs, pad=40):
    """Lokalizacja obejmująca etykiety kilku urządzeń na wspólnej stronie."""
    sch = ctx.schematic
    if not sch or not devs:
        return None
    pages = None
    for d in devs:
        pg = set(ctx.symbol_pages.get(zs.clean_device_code(d)) or [])
        pages = pg if pages is None else (pages & pg)
    if not pages:
        return device_location(ctx, devs[0])
    for p in sorted(pages):
        toks = page_tokens(sch["filepath"], p)
        pts = [find_device_pos(toks, d) for d in devs]
        pts = [x for x in pts if x]
        if len(pts) >= max(1, len(devs) // 2):
            xs, ys = [x for x, _ in pts], [y for _, y in pts]
            loc = {"schematic_id": sch["id"], "page": p,
                   "bbox": [min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad]}
            sh = ctx.sheets.get(p)
            if sh:
                loc["sheet_number"], loc["sheet_title"] = sh
            g = grid_ref(sch["filepath"], p, sum(xs) / len(xs), sum(ys) / len(ys))
            if g:
                loc["grid"] = g
            return loc
    return device_location(ctx, devs[0])


def det_busbar_unmodeled(ctx):
    """D10: zwora/szyna bezpieczników narysowana grafiką (prostokąt/linia)
    albo wynikająca z brakującego terminala — brak połączenia w raporcie."""
    out, seen = [], set()
    for fc, bars in (_rails(ctx).get("bars") or {}).items():
        for term, b in (bars or {}).items():
            node = b.get("node") or ""
            if not node or node in seen:
                continue
            seen.add(node)
            members = [fc] + [zs.clean_device_code(s[0]) for s in (b.get("sibs") or [])]
            pin = b.get("pin") or ""
            full = [term.rsplit("-", 1)[0] + "-" + m if "-" in term else m for m in members]
            devs = [s[0] for s in (b.get("sibs") or [])]
            loc_devs = [d for d in ([next((x["device_code"] for x in ctx.bom_by_clean.get(fc) or []), None)] + devs) if d]
            out.append(_f(f"D10|{node}", "busbar_unmodeled", "busbar_unmodeled",
                          {"members": " ↔ ".join(f"{m}:{pin}" for m in members), "holder": b.get("holder") or "",
                           "taps": ", ".join(b.get("taps") or [])},
                          devices=loc_devs + ([b["holder"]] if b.get("holder") else []),
                          location=_loc_for_devices(ctx, loc_devs or full),
                          evidence={"bar": b, "fuse": fc}, workaround="heuristic"))
    return out


def det_fuse_holder_unlinked(ctx):
    """D11: bezpiecznik w oprawce o INNYM numerze (F19→FH15) — para
    odtworzona z geometrii PDF; w danych E3 brak powiązania."""
    out = []
    for fc, holder in (_rails(ctx).get("holders") or {}).items():
        hcl = zs.clean_device_code(holder)
        if re.sub(r"\D", "", hcl or "") == re.sub(r"\D", "", fc or ""):
            continue
        fdev = next((x["device_code"] for x in ctx.bom_by_clean.get(fc) or []), fc)
        out.append(_f(f"D11|{fc}>{hcl}", "fuse_holder_unlinked", "fuse_holder_unlinked",
                      {"fuse": fdev, "holder": holder},
                      devices=[fdev, holder], location=_loc_for_devices(ctx, [fdev, holder]),
                      evidence={"fuse": fc, "holder": holder}, workaround="heuristic",
                      suggestion={"kind": "patch", "confidence": "high",
                                  "payload": {"kind": "fuse_holder", "fuse": fc, "holder": holder}}))
    return out


def det_box_fuse_hidden(ctx):
    """D12: bezpieczniki w skrzynce niewidoczne w raporcie połączeń
    (pozycje odczytane z geometrii PDF przez _populate_ps_box_fuses)."""
    rows = ctx.cur.execute("""SELECT box_name, cell, rating, out_dev, out_signal, page_number, pos_x, pos_y, confidence
                              FROM zuken_ps_box_fuses WHERE ps_code = ? ORDER BY box_name, cell""", (ctx.ps,)).fetchall()
    boxes = defaultdict(list)
    for r in rows:
        boxes[r["box_name"]].append(dict(r))
    out = []
    sch = ctx.schematic
    for box, cells in boxes.items():
        xs = [c["pos_x"] for c in cells if c["pos_x"] is not None]
        ys = [c["pos_y"] for c in cells if c["pos_y"] is not None]
        loc = None
        pg = cells[0]["page_number"]
        if sch and pg and xs:
            loc = {"schematic_id": sch["id"], "page": pg,
                   "bbox": [min(xs) - 30, min(ys) - 60, max(xs) + 30, max(ys) + 60]}
            sh = ctx.sheets.get(pg)
            if sh:
                loc["sheet_number"], loc["sheet_title"] = sh
            g = grid_ref(sch["filepath"], pg, sum(xs) / len(xs), sum(ys) / len(ys))
            if g:
                loc["grid"] = g
        listing = ", ".join(f"{c['cell']} {c['rating'] or ''}→{c['out_dev'] or '?'}" for c in cells)
        outs = [c["out_dev"] for c in cells if c["out_dev"]]
        out.append(_f(f"D12|{box}", "box_fuse_hidden", "box_fuse_hidden",
                      {"box": box, "n": len(cells), "list": listing},
                      devices=outs[:12], location=loc, evidence={"cells": cells}, workaround="heuristic"))
        weak = [c for c in cells if (c["confidence"] or "high") != "high"]
        if weak:
            f = _f(f"D12|{box}|verify", "box_fuse_hidden", "box_fuse_verify",
                   {"box": box, "list": ", ".join(f"{c['cell']} {c['rating'] or ''}→{c['out_dev'] or '?'}" for c in weak)},
                   devices=[c["out_dev"] for c in weak if c["out_dev"]], location=loc, evidence={"cells": weak})
            f["target"] = "internal"
            out.append(f)
    return out


def det_fuse_no_wiring(ctx):
    """D13: bezpiecznik/skrzynka bezpieczników z BOM bez żadnego toru:
    brak w raporcie, brak oprawki (holder_code / geometria), brak szyny."""
    r = _rails(ctx)
    known = set()
    for k in ("slots", "holders", "box_pins", "rated", "terms", "bars"):
        known |= set((r.get(k) or {}).keys())
    hold = {}
    for row in ctx.cur.execute("SELECT device_clean, holder_code FROM zuken_ps_fuses WHERE ps_code = ?", (ctx.ps,)):
        hold[row[0]] = zs.clean_device_code(row[1] or "")
    box_out = {zs.clean_device_code(x[0] or "") for x in ctx.cur.execute(
        "SELECT out_dev FROM zuken_ps_box_fuses WHERE ps_code = ?", (ctx.ps,))}
    out = []
    for d in ctx.bom_devices:
        cl = d["device_clean"] or zs.clean_device_code(d["device_code"])
        if d["category"] != "Bezpiecznik" or not cl or (d["device_code"] or "").startswith("=BOM"):
            continue
        if cl in ctx.conn_cleans or cl in known or (hold.get(cl) and hold[cl] in ctx.conn_cleans):
            continue
        if cl.endswith("_BOX") or cl in box_out:
            continue
        out.append(_f(f"D13|{d['device_code']}", "fuse_no_wiring", "fuse_no_wiring",
                      {"dev": d["device_code"], "descr": _short_desc(d["description"]),
                       "func": f" · {d['function']}" if d["function"] else ""},
                      devices=[d["device_code"]], loc_dev=d["device_code"],
                      evidence={"bom": {k: d[k] for k in ("article_number", "description", "function")}}))
    return out


# ── D14: typy złączy bez rysowalnego pinoutu ─────────────────────────
# Port predykatu connFaceLayout() z frontendu (rejestr_usterek.html):
# odpowiada na pytanie "czy artykuł ma rysunek gniazd" — wbudowane
# rodziny + rekordy użytkownika. Zmiana rodzin w JS trzeba tu odzwierciedlić.
_CONN_JPT_COLS = {4: 2, 6: 3, 8: 4, 10: 5, 14: 7, 18: 9, 22: 11}


def _conn_face_family(article, desc, pins):
    """Zwraca {"unverified": bool} gdy typ złącza ma rysowalny układ,
    None gdy nieznany. Spójne z gałęziami connFaceLayout() w UI."""
    art = (article or "").strip()
    desc = desc or ""
    blob = f"{art} {desc}"
    n = int(pins or 0)
    cn = re.search(r"(\d+)\s*circuits?|PIN:\s*(\d+)|(\d+)\s*pos|(\d+)\s*pole|(\d+)[\s-]*way", desc, re.I)
    if cn:
        n = int(next(g for g in cn.groups() if g))
    fam = gender = ""
    rows = cols = 0
    unverified = False
    if re.search(r"junior\s*(power\s*)?timer", desc, re.I) or re.match(r"^(\d+-)?92950[45]-", art):
        fam = "JPT"
        if re.match(r"^(\d+-)?(96564[01]|9676[23]\d)-", art) and n % 3 == 0:
            rows, cols = 3, n // 3
        else:
            rows, cols = 2, _CONN_JPT_COLS.get(n, 0)
        if re.search(r"receptacle", blob, re.I) or re.match(r"^(\d+-)?929504-", art):
            gender = "F"
        if re.search(r"pin\s*housing|pinhousing|tab[-\s]?housing", blob, re.I) or re.match(r"^(\d+-)?9676(2[6-9]|30)-", art):
            gender = "M"
    elif re.search(r"mini[\s-]?fit", desc, re.I) or re.match(r"^39-0[01]-\d{4}", art):
        fam = "MINIFIT"
        rows, cols = 2, n // 2
        if re.search(r"[05]$", art):
            gender = "F"
        elif re.search(r"[12]$", art):
            gender = "M"
        if not gender:
            if re.search(r"receptacle", blob, re.I):
                gender = "F"
            if re.search(r"\bplug\b|wtyk", blob, re.I):
                gender = "M"
    elif re.search(r"micro[\s-]?fit", desc, re.I) or re.match(r"^4302[05]-|^4364[05]-", art):
        if re.search(r"single\s*row", desc, re.I) or re.match(r"^4364[05]-", art):
            g = ("F" if re.match(r"^43645-", art) or re.search(r"receptacle", blob, re.I)
                 else "M" if re.match(r"^43640-", art) or re.search(r"\bplug\b", blob, re.I) else "")
            return {"unverified": False} if g and n else None
        fam = "MICROFIT"
        rows, cols = 2, n // 2
        if re.match(r"^43025-", art) or re.search(r"receptacle", blob, re.I):
            gender = "F"
        if re.match(r"^43020-", art) or re.search(r"\bplug\b|wtyk", blob, re.I):
            gender = "M"
    elif re.search(r"superseal", blob, re.I) or re.match(r"^282[01]\d\d-", art):
        fam = "SUPERSEAL"
        rows, cols = 1, n
        if re.search(r"contact\s*gender\s*receptacle|female|\bplug\b", blob, re.I) or re.match(r"^2820\d\d-", art):
            gender = "F"
        if re.search(r"contact\s*gender\s*tab|\bcap\b|\bmale\b", blob, re.I) or re.match(r"^2821\d\d-", art):
            gender = "M"
    elif re.search(r"mate[\s-]?n[\s-]?lok", desc, re.I) or re.match(r"^1-480\d{3}-|^\d-?480\d{3}$", art):
        fam = "MATENLOK"
        cols, rows = 2, n // 2
        if re.search(r"receptacle|\bplug\b|wtyk|socket", blob, re.I):
            gender = "F"
        if re.search(r"\bcap\b|\bpin\b", blob, re.I):
            gender = "M"
    elif re.search(r"\bMCP\b|96897\d-", blob, re.I):
        if n % 3 == 0 and 6 <= n <= 21:
            fam = "MCP"
            rows, cols = 3, n // 3
        if re.search(r"female|receptacle|socket|buchse|receptaclehousing", blob, re.I):
            gender = "F"
        elif re.search(r"male|tab|pin\s*h(ous|sg)|stift", blob, re.I):
            gender = "M"
        if not gender:
            gender = "F"
    elif (re.search(r"\bMQS\b|\bMCON\b", blob, re.I) or re.match(r"^(\d+-)?(968699|1718333|1703498)-", art)) and n == 2:
        fam = "TE2P"
        rows, cols = 1, 2
        if re.search(r"female|receptacle|socket|buchse", blob, re.I):
            gender = "F"
        if re.search(r"male|tab|stift", blob, re.I):
            gender = "M"
        if not gender:
            gender = "F"
    elif (re.search(r"round\s*connector", blob, re.I) or re.match(r"^171823\d-", art)
          or re.match(r"^was[\s-]*(iv|\d)", art, re.I) or re.search(r"złącze\s*typu\s*waś", blob, re.I)):
        fam = "CIRC7"
        rows, cols, n = 3, 3, 7
        if re.search(r"male\s*term|pin\s*h(ous|sg)|\bpin\b", blob, re.I):
            gender = "M"
        if re.search(r"female|socket|receptacle", blob, re.I):
            gender = "F"
        if not gender:
            gender = "M"
    elif (re.search(r"multi[\s-]?interlock", desc, re.I) or re.search(r"\bMIC\b", desc)
          or re.match(r"^(\d+-)?171892-", art)):
        n = n or 9
        if n >= 4:
            return {"unverified": False}
    elif re.search(r"\bDF11-\d+DS-|\bDF11\b", blob, re.I):
        fam = "DF11"
        rows, cols = 2, -(-n // 2)
        if re.search(r"DS-|socket|żeńsk|female", blob, re.I):
            gender = "F"
        elif re.search(r"DEP-|DP-|plug|header|wtyk|male", blob, re.I):
            gender = "M"
        if not gender:
            gender = "F"
    elif re.search(r"ff\s*250|fastin|faston", blob, re.I) or re.match(r"^1809(0[0-9]|1[0-9]|2[0-4])-?\d*$", art):
        fam = "FASTIN"
        lance = bool(re.match(r"^(\d+-)?(171433|171897|171898|1721(2[7-9]|3[0-8])|17238[34])-\d", art))
        if lance and n >= 4 and n % 2 == 0:
            rows, cols = 2, n // 2
        elif lance and n == 2:
            rows, cols = 2, 1
        elif n in (4, 6, 8, 10):
            cols, rows = 2, n // 2
        else:
            rows, cols = 1, n or 1
        if re.search(r"receptacle", blob, re.I):
            gender = "F"
        elif re.search(r"tab", blob, re.I) or re.search(r"\bplug\b|wtyk", blob, re.I):
            gender = "M"
        if not gender:
            gender = "F"
        unverified = lance
    elif re.search(r"terminal\s*block.*pluggable|pluggable.*terminal\s*block", desc, re.I) or re.match(r"^TBP\d", art, re.I):
        fam = "TBP"
        rows, cols, gender = 1, n, "F"
    elif re.match(r"^(770|890)-\d{3}", art):
        return {"unverified": True}
    elif re.match(r"^DTP0[46]-\dP?S?", art, re.I):
        return {"unverified": True}
    elif re.search(r"relay\s*socket\s*9", desc, re.I) or re.match(r"^8JA\s*003\s*526", art, re.I):
        fam, gender = "RELAY9", "F"
        rows, cols, n = 3, 3, 9
    elif re.search(r"\bRCA\b", desc, re.I) or re.match(r"^ACPR-", art, re.I):
        fam = "RCA"
        rows, cols, n = 1, 2, 2
        gender = "M" if re.search(r"męsk|\bmale\b|wtyk|\bplug\b", desc, re.I) else "F"
    if not fam or not gender or not cols or not rows or cols != int(cols) or rows != int(rows):
        return None
    return {"unverified": unverified}


def det_pinout_missing(ctx):
    """D14: typy złączy projektu bez rysowalnego pinoutu — jak raport
    rysunków w zestawieniu (grupowanie po artykuł+opis, pominięcie
    końcówek 1-pin i SP/RT/U). Do uzupełnienia w edytorze pinoutów."""
    rows = ctx.cur.execute(
        """SELECT device_code, device_clean, article_number, description, pin_count, supplier
           FROM zuken_ps_connectors WHERE ps_code = ?""", (ctx.ps,)).fetchall()
    if not rows:
        return []
    halves = {}
    if ctx.bom_ids:
        ph = ",".join("?" * len(ctx.bom_ids))
        for r in ctx.cur.execute(f"""
            SELECT d.device_code, i.article_number, i.description
            FROM zuken_bom_devices d JOIN zuken_bom_items i ON d.bom_item_id = i.id
            WHERE i.project_id IN ({ph})
              AND i.article_number IS NOT NULL AND TRIM(i.article_number) != ''
            ORDER BY i.project_id DESC""", ctx.bom_ids):
            halves.setdefault(r["device_code"], (r["article_number"], r["description"] or ""))
    user = {}
    for r in ctx.cur.execute("SELECT article, pins_map FROM zuken_conn_pinouts"):
        mp = _uj(r[1])
        user[(r[0] or "").strip().upper()] = mp if isinstance(mp, dict) else {}
    groups = {}
    for r in rows:
        cl = r["device_clean"] or ""
        if re.match(r"^(SP|RT|U)\d", cl, re.I):
            continue
        h = halves.get(r["device_code"])
        art = ((h[0] if h else "") or r["article_number"] or "").strip()
        desc = (h[1] if h else "") or r["description"] or ""
        n = r["pin_count"] or 0
        u = user.get(art.upper()) if art else None
        if u is not None:
            kind = "unverified" if u.get("unverified") else None
        else:
            lay = _conn_face_family(art, desc, n)
            if lay is None:
                kind = "missing" if n > 1 else None   # 1-pin jak w raporcie: terminale
            else:
                kind = "unverified" if lay.get("unverified") else None
        if not kind:
            continue
        key = (kind, art, desc)
        g = groups.setdefault(key, {"art": art, "desc": desc, "sup": r["supplier"] or "",
                                    "pins": set(), "devs": []})
        g["pins"].add(n)
        g["devs"].append(r["device_code"] or cl)
    out = []
    for (kind, art, desc), g in sorted(groups.items()):
        devs = [d for d in g["devs"] if d]
        pins = sorted(p for p in g["pins"] if p)
        artkey = art or (re.sub(r"\W+", "-", desc.strip())[:40] or "?")
        sugg = None
        if art:
            sugg = {"kind": "pinout", "confidence": "high",
                    "payload": {"article": art, "pins": pins[0] if pins else 0,
                                "desc": _short_desc(desc, 120)}}
        f = _f(f"D14|{kind}|{artkey}|{','.join(map(str, pins))}", "pinout_missing",
               "pinout_unverified" if kind == "unverified" else "pinout_missing",
               {"art": art or "—", "n": len(devs), "pins": "/".join(map(str, pins)) or "?",
                "sup": g["sup"], "desc": _short_desc(desc), "devs": _fmt_where(devs)},
               devices=devs[:12], loc_dev=devs[0] if devs else None,
               evidence={"article": art, "desc": desc, "supplier": g["sup"],
                         "pins": pins, "devices": devs[:80]},
               suggestion=sugg)
        if kind == "unverified":
            f["severity"] = "info"
        out.append(f)
    return out


def det_pdf_report_label(ctx):
    """D15: etykieta -DEV narysowana na schemacie, nieobecna w raporcie
    połączeń, w BOM ani w tabelach pomocniczych (bezpieczniki, skrzynki).
    Info dla inżyniera — albo etykieta jest błędna, albo brakuje danych."""
    sch = ctx.schematic
    if not sch:
        return []
    known = set(ctx.conn_cleans) | set(ctx.bom_by_clean)
    hold = set()
    for r in ctx.cur.execute("SELECT device_clean, holder_code FROM zuken_ps_fuses WHERE ps_code = ?", (ctx.ps,)):
        hold.add(r[0])
        hold.add(zs.clean_device_code(r[1] or ""))
    known |= hold | {zs.clean_device_code(x[0] or "") for x in ctx.cur.execute(
        "SELECT out_dev FROM zuken_ps_box_fuses WHERE ps_code = ?", (ctx.ps,))}
    known.discard("")
    known_u = {k.upper() for k in known}
    skip = re.compile(r"^(RT|SP|W|U|FH|FR|ZW)\d|^999|^_|^AWG\d"
                      r"|^(BK|BL|BN|BU|GN|GY|OG|PK|RD|VI|VT|WH|YE)\d")    # numery przewodów kolorowych (OG193A)
    skip_end = re.compile(r"\d(BK|BL|BN|BU|GN|GY|OG|PK|RD|VI|VT|WH|YE)$")  # ...i odwrotnie (P13RD)
    core = {}
    for k in known:
        m = re.match(r"^([A-Z]+)(\d+)", k)
        if m:
            core.setdefault((m.group(1), m.group(2)), k)
    # symbol_clean trzyma segment +lokalizacji (+BL1-X186 → 'BL1-X186');
    # clean_device_code sprowadza go do tej samej postaci co raport ('X186')
    seen = {}
    for r in ctx.cur.execute("""
            SELECT symbol_clean, MIN(page_number) AS pg, COUNT(*) AS n
            FROM zuken_pdf_symbols
            WHERE schematic_id = ? AND symbol_type IN ('device','connector','module','relay','switch','fuse')
            GROUP BY symbol_clean ORDER BY pg""", (sch["id"],)):
        raw = (r["symbol_clean"] or "").strip()
        cl = zs.clean_device_code(raw)
        if not re.match(r"^[A-Z]{1,4}\d", cl or "") or cl.upper() in known_u or skip.match(cl) or skip_end.search(cl):
            continue
        if cl in seen:
            seen[cl]["raw"].append(raw)
            continue
        seen[cl] = {"pg": r["pg"], "n": r["n"], "raw": [raw]}
    out = []
    for cl, info in seen.items():
        near = []
        m = re.match(r"^([A-Z]+)(\d+)", cl)
        if m and (m.group(1), m.group(2)) in core:
            near.append(core[(m.group(1), m.group(2))])
        near += [k for k in known if len(k) >= 4 and len(cl) >= 4
                 and (k.startswith(cl) or cl.startswith(k)) and k not in near]
        sheet = (ctx.sheets.get(info["pg"]) or ("", ""))
        out.append(_f(f"D15|{cl}", "pdf_report_label", "pdf_report_label",
                      {"dev": cl, "page": info["pg"], "sheet": sheet[0] or str(info["pg"]),
                       "near": ", ".join(near[:3])},
                      devices=[cl], loc_dev=cl,
                      evidence={"page": info["pg"], "pages_count": info["n"],
                                "labels": info["raw"][:10], "near": near[:5]}))
    return out


DETECTORS = [
    # (id, stage, fn)
    ("D01", "data", det_device_unconnected),
    ("D02", "data", det_dangling_terminal),
    ("D03", "data", det_device_no_location),
    ("D04", "data", det_bom_conn_mismatch),
    ("D05", "data", det_typo),
    ("D06", "data", det_photo_missing),
    ("D07", "data", det_term_untranslated),
    ("D08", "data", det_platform_term),
    ("D09", "data", det_kb_document),
    ("D10", "pdf", det_busbar_unmodeled),
    ("D11", "pdf", det_fuse_holder_unlinked),
    ("D12", "pdf", det_box_fuse_hidden),
    ("D13", "pdf", det_fuse_no_wiring),
    ("D14", "data", det_pinout_missing),
    ("D15", "data", det_pdf_report_label),
]


# ═══════════════════════════════════════════════════════════════════
# SKAN + CYKL ŻYCIA
# ═══════════════════════════════════════════════════════════════════
SCAN_STATE = {"running": False, "ps": "", "stage": "", "progress": 0, "total": 0,
              "detectors": {}, "error": "", "started_at": "", "finished_at": "",
              "new": 0, "updated": 0, "closed": 0}
_scan_lock = threading.Lock()


def _upsert_finding(cur, ps, det_id, f, rev, now, ctx):
    target = f.get("target") or CATEGORIES[f["category"]][0]
    row = cur.execute("SELECT id, status, patch_id, suggestion, location FROM zuken_issues WHERE ps_code = ? AND fingerprint = ?",
                      (ps, f["fp"])).fetchone()
    loc = f["location"]
    if loc is None and f.get("loc_dev"):
        try:
            loc = device_location(ctx, f["loc_dev"])
        except Exception:
            loc = None
    if row is None:
        cur.execute("""
            INSERT INTO zuken_issues (ps_code, category, target, severity, status, msg_key, msg_params,
                devices, location, evidence, suggestion, detector, fingerprint, workaround,
                source_revision, created_by, created_at, updated_at, last_seen_at)
            VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'auto', ?, ?, ?);""",
                    (ps, f["category"], target, f["severity"], f["msg_key"], _j(f["params"]),
                     _j(f["devices"]), _j(loc), _j(f["evidence"]), _j(f["suggestion"]), det_id,
                     f["fp"], f["workaround"], rev, now, now, now))
        return "new"
    status = row["status"]
    sets = {"msg_params": _j(f["params"]), "devices": _j(f["devices"]), "evidence": _j(f["evidence"]),
            "last_seen_at": now, "workaround": f["workaround"]}
    if loc is not None:
        sets["location"] = _j(loc)
    if not row["patch_id"]:
        sets["suggestion"] = _j(f["suggestion"])
    if status in ("verified", "done"):
        sets["status"] = "new"          # regresja — problem wrócił
        sets["resolved_revision"] = None
        sets["updated_at"] = now
    cols = ", ".join(f"{k} = ?" for k in sets)
    cur.execute(f"UPDATE zuken_issues SET {cols} WHERE id = ?", (*sets.values(), row["id"]))
    return "updated"


def run_scan(ps, stages=("data",), progress=None):
    """Uruchamia wykrywacze dla PS i aktualizuje rejestr. Zwraca podsumowanie."""
    init_audit_tables()
    ps = (ps or "").strip().upper()
    conn = zs.get_db()
    cur = conn.cursor()
    now = _now()
    rev = ps_revision_key(cur, ps)
    ctx = Ctx(cur, ps)
    dets = [d for d in DETECTORS if d[1] in stages]
    summary = {"ps": ps, "revision": rev, "detectors": {}, "new": 0, "updated": 0, "closed": 0}
    ok_dets = []
    for i, (did, stage, fn) in enumerate(dets):
        if progress:
            progress(i, len(dets), did)
        try:
            findings = fn(ctx)
            n_new = n_upd = 0
            for f in findings:
                r = _upsert_finding(cur, ps, did, f, rev, now, ctx)
                n_new += r == "new"
                n_upd += r == "updated"
            conn.commit()
            summary["detectors"][did] = {"ok": True, "count": len(findings), "new": n_new}
            summary["new"] += n_new
            summary["updated"] += n_upd
            ok_dets.append(did)
        except Exception as e:
            conn.rollback()
            summary["detectors"][did] = {"ok": False, "error": str(e)}
    # zamykanie nieodtworzonych (tylko wykrywacze zakończone bez błędu)
    if ok_dets:
        ph = ",".join("?" * len(ok_dets))
        stale = cur.execute(f"""
            SELECT id, target, status, source_revision FROM zuken_issues
            WHERE ps_code = ? AND detector IN ({ph}) AND (last_seen_at IS NULL OR last_seen_at < ?)
              AND status IN ('new','confirmed','sent','fixed','in_progress');""",
                            (ps, *ok_dets, now)).fetchall()
        for r in stale:
            if r["target"] == "internal":
                cur.execute("UPDATE zuken_issues SET status='done', resolved_revision=?, updated_at=? WHERE id=?",
                            (rev, now, r["id"]))
                summary["closed"] += 1
            elif (r["source_revision"] or "") != rev:
                cur.execute("UPDATE zuken_issues SET status='verified', resolved_revision=?, updated_at=? WHERE id=?",
                            (rev, now, r["id"]))
                summary["closed"] += 1
        conn.commit()
    try:
        _mark_redundant_patches(cur, ps, ctx)
        conn.commit()
    except Exception:
        conn.rollback()
    conn.close()
    return summary


def start_scan(ps, stages=("data",)):
    """Skan w tle (stan w SCAN_STATE). False gdy już trwa."""
    with _scan_lock:
        if SCAN_STATE["running"]:
            return False
        SCAN_STATE.update(running=True, ps=ps, stage=",".join(stages), progress=0, total=0,
                          detectors={}, error="", started_at=_now(), finished_at="",
                          new=0, updated=0, closed=0)

    def _prog(i, n, did):
        SCAN_STATE.update(progress=i, total=n, current=did)

    def _run():
        try:
            res = run_scan(ps, stages, progress=_prog)
            SCAN_STATE.update(detectors=res["detectors"], new=res["new"], updated=res["updated"],
                              closed=res["closed"], progress=SCAN_STATE.get("total", 0))
        except Exception as e:
            SCAN_STATE["error"] = str(e)
        finally:
            SCAN_STATE.update(running=False, finished_at=_now())
    threading.Thread(target=_run, daemon=True).start()
    return True


def scan_status():
    return dict(SCAN_STATE)


# ═══════════════════════════════════════════════════════════════════
# ŁATKI (zuken_data_patches) — CRUD; nakładanie w zuken_service
# ═══════════════════════════════════════════════════════════════════
PATCH_KINDS = ("connection", "fuse_holder")


def _patch_dict(r):
    d = dict(r)
    d["payload"] = _uj(d.get("payload"), {})
    return d


def list_patches(ps=None):
    init_audit_tables()
    conn = zs.get_db()
    cur = conn.cursor()
    if ps:
        rows = cur.execute("SELECT * FROM zuken_data_patches WHERE ps_code = ? ORDER BY id DESC", (ps.upper(),)).fetchall()
    else:
        rows = cur.execute("SELECT * FROM zuken_data_patches ORDER BY ps_code, id DESC").fetchall()
    out = [_patch_dict(r) for r in rows]
    conn.close()
    return out


def _clean_patch_payload(kind, payload):
    p = dict(payload or {})
    p.pop("kind", None)
    if kind == "connection":
        for k in ("from_device", "from_pin", "to_device", "to_pin"):
            p[k] = str(p.get(k) or "").strip()
        if not p["from_device"] or not p["to_device"]:
            raise ValueError("from_device/to_device required")
        p.setdefault("link", "stud")
    return p


def save_patch(ps, kind, payload, user="", patch_id=None, issue_id=None, note="", status="active"):
    init_audit_tables()
    if kind not in PATCH_KINDS:
        raise ValueError("bad kind")
    ps = (ps or "").strip().upper()
    p = _clean_patch_payload(kind, payload)
    now = _now()
    conn = zs.get_db()
    cur = conn.cursor()
    if patch_id:
        cur.execute("""UPDATE zuken_data_patches SET kind=?, payload=?, note=?, status=?, updated_at=?, source='local'
                       WHERE id=?""", (kind, _j(p), note or "", status, now, int(patch_id)))
        pid = int(patch_id)
    else:
        cur.execute("""INSERT INTO zuken_data_patches (ps_code, kind, payload, status, source, issue_id, note,
                       created_by, created_at, updated_at, uid) VALUES (?, ?, ?, ?, 'local', ?, ?, ?, ?, ?, ?)""",
                    (ps, kind, _j(p), status, issue_id, note or "", user or "", now, now, uuid.uuid4().hex))
        pid = cur.lastrowid
    conn.commit()
    conn.close()
    zs._invalidate_patch_caches()
    return pid


def set_patch_status(patch_id, status):
    init_audit_tables()
    conn = zs.get_db()
    conn.execute("UPDATE zuken_data_patches SET status=?, updated_at=? WHERE id=?", (status, _now(), int(patch_id)))
    conn.commit()
    conn.close()
    zs._invalidate_patch_caches()


def delete_patch(patch_id):
    init_audit_tables()
    conn = zs.get_db()
    conn.execute("DELETE FROM zuken_data_patches WHERE id=?", (int(patch_id),))
    conn.execute("UPDATE zuken_issues SET patch_id=NULL WHERE patch_id=?", (int(patch_id),))
    conn.commit()
    conn.close()
    zs._invalidate_patch_caches()


def _mark_redundant_patches(cur, ps, ctx):
    """Łatka 'connection', której połączenie jest już w surowym raporcie
    (inżynier poprawił w Zuken) -> redundant; urządzenia nieistniejące ->
    disabled."""
    known = set(ctx.conn_cleans) | set(ctx.bom_by_clean)
    for r in cur.execute("SELECT id, kind, payload, status FROM zuken_data_patches WHERE ps_code=? AND status IN ('active','redundant')", (ps,)).fetchall():
        if r["kind"] != "connection":
            continue
        p = _uj(r["payload"], {})
        a = (p.get("from_device", ""), p.get("from_pin", ""))
        b = (p.get("to_device", ""), p.get("to_pin", ""))
        if b in ctx.neighbours.get(a, {}):
            new = "redundant"
        elif zs.clean_device_code(a[0]) not in known or zs.clean_device_code(b[0]) not in known:
            new = "disabled"
        else:
            new = "active"
        if new != r["status"]:
            cur.execute("UPDATE zuken_data_patches SET status=?, updated_at=? WHERE id=?", (new, _now(), r["id"]))
    zs._invalidate_patch_caches()


# ═══════════════════════════════════════════════════════════════════
# ZGŁOSZENIA — CRUD i renderowanie
# ═══════════════════════════════════════════════════════════════════
def render_issue(d, lang="pl"):
    """Uzupełnia dict zgłoszenia o title_r/description_r/fix_r w języku."""
    key = d.get("msg_key")
    params = d.get("msg_params") or {}
    if key:
        p = dict(params)
        if key == "typo":
            p["known"] = amsg("typo.known", lang) if params.get("known") else ""
        elif key == "dangling_terminal":
            c = params.get("cand") or ""
            p["cand"] = amsg("dangling_terminal.cand", lang, cand=c) if c else ""
            fixp = dict(params, cand=f" ({c})" if c else "")
        elif key == "device_no_location":
            s = params.get("sug") or ""
            p["sug"] = amsg("device_no_location.sug", lang, sug=s) if s else ""
        elif key == "pdf_report_label":
            n = params.get("near") or ""
            p["near"] = amsg("pdf_report_label.near", lang, near=n) if n else ""
        d["title_r"] = amsg(f"{key}.title", lang, **p)
        d["description_r"] = amsg(f"{key}.desc", lang, **p)
        fk = f"{key}.fix"
        if fk in AUDIT_MSG:
            if key == "dangling_terminal":
                d["fix_r"] = amsg(fk, lang, **fixp)
            else:
                d["fix_r"] = amsg(fk, lang, **params)
        else:
            d["fix_r"] = ""
    else:
        d["title_r"] = d.get("title") or ""
        d["description_r"] = d.get("description") or ""
        d["fix_r"] = (d.get("suggestion") or {}).get("text", "") if isinstance(d.get("suggestion"), dict) else ""
    d["category_r"] = amsg(f"cat.{d.get('category')}", lang)
    d["status_r"] = amsg(f"st.{d.get('status')}", lang)
    d["severity_r"] = amsg(f"sev.{d.get('severity')}", lang)
    return d


def _issue_dict(r, lang="pl"):
    d = dict(r)
    for k in ("msg_params", "devices", "location", "evidence", "suggestion"):
        d[k] = _uj(d.get(k), None)
    return render_issue(d, lang)


def meta(lang="pl"):
    return {
        "categories": {c: {"label": amsg(f"cat.{c}", lang), "target": t, "severity": s}
                       for c, (t, s) in CATEGORIES.items()},
        "statuses": {s: amsg(f"st.{s}", lang) for s in ALL_STATUSES},
        "open_statuses": OPEN_STATUSES,
        "severities": {s: amsg(f"sev.{s}", lang) for s in SEVERITIES},
        "platforms": PLATFORMS,
        "patch_kinds": PATCH_KINDS,
    }


def list_issues(ps, target=None, status=None, category=None, q="", lang="pl"):
    init_audit_tables()
    conn = zs.get_db()
    cur = conn.cursor()
    cond, params = ["ps_code = ?"], [(ps or "").upper()]
    if target:
        cond.append("target = ?")
        params.append(target)
    if category:
        cond.append("category = ?")
        params.append(category)
    if status == "open":
        cond.append("status IN ('new','confirmed','sent','fixed','in_progress')")
    elif status == "closed":
        cond.append("status IN ('verified','rejected','wontfix','done')")
    elif status:
        cond.append("status = ?")
        params.append(status)
    rows = cur.execute(f"""SELECT * FROM zuken_issues WHERE {' AND '.join(cond)}
        ORDER BY CASE severity WHEN 'error' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END,
                 category, id DESC""", params).fetchall()
    items = [_issue_dict(r, lang) for r in rows]
    if q:
        ql = q.lower()
        items = [i for i in items if ql in " ".join(str(i.get(k) or "") for k in
                                                     ("title_r", "description_r", "devices", "note")).lower()]
    counts = Counter()
    for r in cur.execute("""SELECT target, category, status, COUNT(*) n FROM zuken_issues WHERE ps_code=?
                            GROUP BY 1,2,3""", ((ps or "").upper(),)):
        open_ = r["status"] in OPEN_STATUSES.get(r["target"], ())
        counts[f"{r['target']}:{'open' if open_ else 'closed'}"] += r["n"]
        if open_:
            counts[f"cat:{r['target']}:{r['category']}"] += r["n"]
    patches = cur.execute("SELECT COUNT(*) FROM zuken_data_patches WHERE ps_code=? AND status='active'",
                          ((ps or "").upper(),)).fetchone()[0]
    conn.close()
    return {"items": items, "counts": dict(counts), "patches_active": patches,
            "revision": None, "meta": meta(lang)}


def badge_count(ps):
    init_audit_tables()
    conn = zs.get_db()
    n = conn.execute("""SELECT COUNT(*) FROM zuken_issues WHERE ps_code=? AND
        ((target='engineer' AND status IN ('new','confirmed')) OR (target='internal' AND status='new'))
        AND severity != 'info'""", ((ps or "").upper(),)).fetchone()[0]
    conn.close()
    return n


def get_issue(issue_id, lang="pl"):
    init_audit_tables()
    conn = zs.get_db()
    r = conn.execute("SELECT * FROM zuken_issues WHERE id=?", (int(issue_id),)).fetchone()
    conn.close()
    return _issue_dict(r, lang) if r else None


def create_manual_issue(data, user=""):
    init_audit_tables()
    ps = (data.get("ps_code") or "").strip().upper()
    cat = data.get("category") if data.get("category") in CATEGORIES else "manual"
    target = data.get("target") if data.get("target") in OPEN_STATUSES else CATEGORIES[cat][0]
    sev = data.get("severity") if data.get("severity") in SEVERITIES else CATEGORIES[cat][1]
    devs = data.get("devices") or []
    if isinstance(devs, str):
        devs = [d for d in re.split(r"[\s,;]+", devs) if d]
    now = _now()
    conn = zs.get_db()
    cur = conn.cursor()
    rev = ps_revision_key(cur, ps)
    loc = data.get("location") if isinstance(data.get("location"), dict) else None
    if loc is None and devs:
        try:
            loc = device_location(Ctx(cur, ps), devs[0])
        except Exception:
            loc = None
    sugg = None
    if (data.get("fix") or "").strip():
        sugg = {"kind": "text", "text": data["fix"].strip()}
    cur.execute("""INSERT INTO zuken_issues (ps_code, category, target, severity, status, title, description,
                   devices, location, suggestion, source_revision, created_by, created_at, updated_at, query)
                   VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ps, cat, target, sev, (data.get("title") or "").strip(), (data.get("description") or "").strip(),
                 _j(devs), _j(loc), _j(sugg), rev, user or "", now, now, (data.get("query") or "").strip()))
    iid = cur.lastrowid
    conn.commit()
    conn.close()
    return get_issue(iid)


_UPDATABLE = ("status", "severity", "target", "note", "title", "description", "devices", "suggestion", "category")


def update_issue(issue_id, fields):
    init_audit_tables()
    sets, params = [], []
    for k in _UPDATABLE:
        if k not in fields:
            continue
        v = fields[k]
        if k == "status" and v not in ALL_STATUSES:
            continue
        if k == "severity" and v not in SEVERITIES:
            continue
        if k == "target" and v not in OPEN_STATUSES:
            continue
        if k == "category" and v not in CATEGORIES:
            continue
        if k in ("devices", "suggestion"):
            v = _j(v)
        sets.append(f"{k} = ?")
        params.append(v)
    if not sets:
        return get_issue(issue_id)
    sets.append("updated_at = ?")
    params.append(_now())
    conn = zs.get_db()
    conn.execute(f"UPDATE zuken_issues SET {', '.join(sets)} WHERE id = ?", (*params, int(issue_id)))
    conn.commit()
    conn.close()
    return get_issue(issue_id)


def bulk_status(ids, status):
    if status not in ALL_STATUSES:
        return 0
    init_audit_tables()
    ids = [int(i) for i in ids or []]
    if not ids:
        return 0
    conn = zs.get_db()
    ph = ",".join("?" * len(ids))
    n = conn.execute(f"UPDATE zuken_issues SET status=?, updated_at=? WHERE id IN ({ph})", (status, _now(), *ids)).rowcount
    conn.commit()
    conn.close()
    return n


def delete_issue(issue_id):
    init_audit_tables()
    conn = zs.get_db()
    conn.execute("DELETE FROM zuken_issue_files WHERE issue_id=?", (int(issue_id),))
    conn.execute("DELETE FROM zuken_issues WHERE id=?", (int(issue_id),))
    conn.commit()
    conn.close()


def list_files(issue_id):
    init_audit_tables()
    conn = zs.get_db()
    rows = [dict(r) for r in conn.execute("SELECT id, filename, mime, created FROM zuken_issue_files WHERE issue_id=? ORDER BY created", (int(issue_id),))]
    conn.close()
    return rows


def add_file(issue_id, filename, data, mime="image/png"):
    init_audit_tables()
    fid = uuid.uuid4().hex
    conn = zs.get_db()
    conn.execute("INSERT INTO zuken_issue_files (id, issue_id, filename, mime, data, created) VALUES (?, ?, ?, ?, ?, ?)",
                 (fid, int(issue_id), filename or "zrzut.png", mime or "image/png", data, _now()))
    conn.commit()
    conn.close()
    return fid


def get_file(file_id):
    init_audit_tables()
    conn = zs.get_db()
    r = conn.execute("SELECT filename, mime, data FROM zuken_issue_files WHERE id=?", (file_id,)).fetchone()
    conn.close()
    return dict(r) if r else None


def delete_file(file_id):
    init_audit_tables()
    conn = zs.get_db()
    conn.execute("DELETE FROM zuken_issue_files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()


def apply_suggestion(issue_id, user="", override=None):
    """Zastosuj propozycję zgłoszenia: wpis słownika / alias / łatka.
    override = edytowany payload z UI. Zwraca {ok, kind, patch_id?}."""
    iss = get_issue(issue_id)
    if not iss:
        return {"ok": False, "error": "notFound"}
    sugg = iss.get("suggestion") or {}
    kind = sugg.get("kind")
    payload = override if isinstance(override, dict) and override else (sugg.get("payload") or {})
    if kind == "translation":
        res = zs.upsert_term(payload)
        if not res.get("ok", True):
            return {"ok": False, "error": res.get("error")}
        update_issue(issue_id, {"status": "confirmed" if iss["status"] == "new" else iss["status"]})
        return {"ok": True, "kind": kind}
    if kind == "alias":
        zs.upsert_query_alias(payload.get("phrase"), payload.get("terms"))
        update_issue(issue_id, {"status": "confirmed" if iss["status"] == "new" else iss["status"]})
        return {"ok": True, "kind": kind}
    if kind == "patch":
        pk = payload.get("kind") or "connection"
        conn = zs.get_db()
        ex = conn.execute("SELECT id FROM zuken_data_patches WHERE id = ? OR issue_id = ? ORDER BY (id = ?) DESC LIMIT 1",
                          (iss.get("patch_id") or -1, iss["id"], iss.get("patch_id") or -1)).fetchone()
        conn.close()
        pid = save_patch(iss["ps_code"], pk, payload, user=user, patch_id=ex[0] if ex else None, issue_id=iss["id"])
        conn = zs.get_db()
        conn.execute("UPDATE zuken_issues SET patch_id=?, status=CASE WHEN status='new' THEN 'confirmed' ELSE status END, updated_at=? WHERE id=?",
                     (pid, _now(), iss["id"]))
        conn.commit()
        conn.close()
        return {"ok": True, "kind": kind, "patch_id": pid}
    return {"ok": False, "error": "noSuggestion"}


# ═══════════════════════════════════════════════════════════════════
# META PS, REGUŁY PLATFORM
# ═══════════════════════════════════════════════════════════════════
def get_ps_meta(ps, cur=None):
    own = cur is None
    if own:
        init_audit_tables()
        conn = zs.get_db()
        cur = conn.cursor()
    r = cur.execute("SELECT * FROM zuken_ps_meta WHERE ps_code=?", ((ps or "").upper(),)).fetchone()
    d = dict(r) if r else {"ps_code": (ps or "").upper(), "base_vehicle": "", "engineer_name": "", "engineer_email": ""}
    if own:
        conn.close()
    return d


def detect_base_vehicle(ps):
    """Propozycja pojazdu bazowego z tekstów schematu i BOM (zliczenia)."""
    init_audit_tables()
    conn = zs.get_db()
    cur = conn.cursor()
    ctx = Ctx(cur, (ps or "").upper())
    texts = [" ".join((d["function"] or "", d["description"] or "", d["article_number"] or "")) for d in ctx.bom_devices]
    sch = ctx.schematic
    if sch:
        texts += [r[0] or "" for r in cur.execute("SELECT raw_text FROM zuken_pdf_sheets WHERE schematic_id=?", (sch["id"],))]
    pname = cur.execute("SELECT project_name, client FROM zuken_ps_summaries WHERE ps_code=?", (ctx.ps,)).fetchone()
    if pname:
        texts.append(" ".join(x or "" for x in pname))
    conn.close()
    cnt = Counter()
    for t in texts:
        for rx, plat in _PLATFORM_HINTS:
            n = len(rx.findall(t))
            if n:
                cnt[plat] += n
    return [{"platform": p, "label": PLATFORMS[p], "hits": n} for p, n in cnt.most_common()]


def set_ps_meta(ps, data):
    init_audit_tables()
    ps = (ps or "").strip().upper()
    cur_m = get_ps_meta(ps)
    vals = {k: (str(data[k]).strip() if k in data else cur_m.get(k) or "")
            for k in ("base_vehicle", "engineer_name", "engineer_email")}
    conn = zs.get_db()
    conn.execute("""INSERT INTO zuken_ps_meta (ps_code, base_vehicle, engineer_name, engineer_email, updated_at)
                    VALUES (?, ?, ?, ?, ?) ON CONFLICT(ps_code) DO UPDATE SET
                    base_vehicle=excluded.base_vehicle, engineer_name=excluded.engineer_name,
                    engineer_email=excluded.engineer_email, updated_at=excluded.updated_at""",
                 (ps, vals["base_vehicle"], vals["engineer_name"], vals["engineer_email"], _now()))
    conn.commit()
    conn.close()
    return get_ps_meta(ps)


def list_platform_terms(cur=None):
    own = cur is None
    if own:
        init_audit_tables()
        conn = zs.get_db()
        cur = conn.cursor()
    out = []
    for r in cur.execute("SELECT * FROM zuken_platform_terms ORDER BY term"):
        d = dict(r)
        d["platforms"] = _uj(d.get("platforms"), [])
        d["equivalents"] = _uj(d.get("equivalents"), {})
        out.append(d)
    if own:
        conn.close()
    return out


def upsert_platform_term(data):
    init_audit_tables()
    term = (data.get("term") or "").strip().upper()
    if not term:
        raise ValueError("term required")
    plats = [p for p in (data.get("platforms") or []) if p in PLATFORMS]
    eq = {k: str(v).strip() for k, v in (data.get("equivalents") or {}).items() if k in PLATFORMS and str(v).strip()}
    conn = zs.get_db()
    conn.execute("""INSERT INTO zuken_platform_terms (term, platforms, equivalents, note, source)
                    VALUES (?, ?, ?, ?, 'local') ON CONFLICT(term) DO UPDATE SET platforms=excluded.platforms,
                    equivalents=excluded.equivalents, note=excluded.note, source='local'""",
                 (term, _j(plats), _j(eq), (data.get("note") or "").strip()))
    conn.commit()
    conn.close()
    return list_platform_terms()


def delete_platform_term(term):
    init_audit_tables()
    conn = zs.get_db()
    conn.execute("DELETE FROM zuken_platform_terms WHERE term = ? COLLATE NOCASE", ((term or "").strip(),))
    conn.commit()
    conn.close()
    return list_platform_terms()


def platform_note(ps, texts, lang="pl", cur=None):
    """Notka dla asystenta: termin innej platformy w wyniku ('KFG' na
    Sprinterze) -> (term, equiv, vehicle) lub None."""
    meta_ = get_ps_meta(ps, cur=cur)
    veh = meta_.get("base_vehicle") or ""
    if not veh:
        return None
    blob = " ".join(t for t in texts if t).upper()
    for t in list_platform_terms(cur=cur):
        plats = t.get("platforms") or []
        eq = (t.get("equivalents") or {}).get(veh)
        if plats and veh not in plats and eq and re.search(r"(?<![A-Z0-9])" + re.escape(t["term"].upper()) + r"(?![A-Z0-9])", blob):
            return {"term": t["term"].upper(), "equiv": eq, "vehicle": PLATFORMS.get(veh, veh)}
    return None


# ═══════════════════════════════════════════════════════════════════
# WYCINEK PDF (PNG z zaznaczeniem)
# ═══════════════════════════════════════════════════════════════════
_SNAP_CACHE = {}


def snapshot_png(issue, margin=(260, 170), scale=2.0):
    """PNG wycinka strony schematu wokół bbox zgłoszenia (czerwona ramka)."""
    loc = (issue or {}).get("location") or {}
    if not loc.get("schematic_id") or not loc.get("page") or pdfium is None or Image is None:
        return None
    key = (issue.get("id"), json.dumps(loc, sort_keys=True))
    if key in _SNAP_CACHE:
        return _SNAP_CACHE[key]
    conn = zs.get_db()
    r = conn.execute("SELECT filepath FROM zuken_pdf_schematics WHERE id=?", (loc["schematic_id"],)).fetchone()
    conn.close()
    if not r:
        return None
    try:
        fp = zs.resolve_kb_filepath(r["filepath"], heal_db=False) or r["filepath"]
    except Exception:
        fp = r["filepath"]
    if not fp or not os.path.exists(fp):
        return None
    sz = page_size(fp, loc["page"])
    pdf = pdfium.PdfDocument(fp)
    try:
        page = pdf[loc["page"] - 1]
        pw, ph = page.get_size()
        ox, oy = (sz[0], sz[1]) if sz else (0.0, 0.0)
        bbox = loc.get("bbox")
        if bbox:
            x0, y0, x1, y1 = [float(v) for v in bbox]
            x0, x1 = x0 - ox, x1 - ox
            y0, y1 = y0 - oy, y1 - oy
            cx0 = max(0.0, x0 - margin[0])
            cx1 = min(pw, x1 + margin[0])
            cy0 = max(0.0, y0 - margin[1])
            cy1 = min(ph, y1 + margin[1])
            crop = (cx0, cy0, pw - cx1, ph - cy1)
        else:
            x0 = y0 = x1 = y1 = None
            cx0, cy1 = 0.0, ph
            crop = (0, 0, 0, 0)
            scale = 1.2
        bmp = page.render(scale=scale, crop=crop)
        img = bmp.to_pil().convert("RGB")
        if bbox:
            dr = ImageDraw.Draw(img)
            rx0 = (x0 - cx0) * scale
            rx1 = (x1 - cx0) * scale
            ry0 = (cy1 - y1) * scale
            ry1 = (cy1 - y0) * scale
            for w in range(4):
                dr.rectangle([rx0 - w, ry0 - w, rx1 + w, ry1 + w], outline=(220, 30, 30))
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
    finally:
        pdf.close()
    if len(_SNAP_CACHE) > 200:
        _SNAP_CACHE.clear()
    _SNAP_CACHE[key] = data
    return data


# ═══════════════════════════════════════════════════════════════════
# XLSX (własny zapis — bez zależności) + .eml
# ═══════════════════════════════════════════════════════════════════
def _col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx_bytes(headers, rows, sheet_name="Sheet1", widths=None):
    """Minimalny XLSX: jeden arkusz, sharedStrings, pogrubiony nagłówek,
    zawijanie tekstu, autofiltr, zamrożony pierwszy wiersz."""
    sst, sst_idx = [], {}

    def cell(ref, v, style):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return f'<c r="{ref}" s="{style}"><v>{v}</v></c>'
        txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(v if v is not None else ""))
        if not txt:
            return f'<c r="{ref}" s="{style}"/>'
        if txt not in sst_idx:
            sst_idx[txt] = len(sst)
            sst.append(txt)
        return f'<c r="{ref}" s="{style}" t="s"><v>{sst_idx[txt]}</v></c>'
    xml_rows = []
    for ri, row in enumerate([headers] + list(rows)):
        st = 1 if ri == 0 else 2
        cells = "".join(cell(f"{_col_letter(ci)}{ri + 1}", v, st) for ci, v in enumerate(row))
        xml_rows.append(f'<row r="{ri + 1}">{cells}</row>')
    last = f"{_col_letter(len(headers) - 1)}{len(rows) + 1}"
    cols = ""
    if widths:
        cols = "<cols>" + "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>'
                                  for i, w in enumerate(widths)) + "</cols>"
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             f'{cols}<sheetData>{"".join(xml_rows)}</sheetData>'
             f'<autoFilter ref="A1:{last}"/></worksheet>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<fonts count="2"><font><sz val="10"/><name val="Calibri"/></font><font><b/><sz val="10"/><name val="Calibri"/></font></fonts>'
              '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFE4E4E7"/><bgColor indexed="64"/></patternFill></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>'
              '</styleSheet>')
    sname = _xesc(sheet_name[:31])
    files = {
        "[Content_Types].xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                                '<Default Extension="xml" ContentType="application/xml"/>'
                                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                                '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
                                '</Types>'),
        "_rels/.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                        '</Relationships>'),
        "xl/workbook.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                            f'<sheets><sheet name="{sname}" sheetId="1" r:id="rId1"/></sheets>'
                            f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">\'{sname}\'!$A$1:${_col_letter(len(headers) - 1)}${len(rows) + 1}</definedName></definedNames>'
                            '</workbook>'),
        "xl/_rels/workbook.xml.rels": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                                       '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                                       '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
                                       '</Relationships>'),
        "xl/worksheets/sheet1.xml": sheet,
        "xl/styles.xml": styles,
        "xl/sharedStrings.xml": ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                 f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(sst)}" uniqueCount="{len(sst)}">'
                                 + "".join(f'<si><t xml:space="preserve">{_xesc(s)}</t></si>' for s in sst) + '</sst>'),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def build_eml(to, subject, body_text, body_html, attachments):
    """Szkic wiadomości (X-Unsent: 1 — Outlook otwiera jako edytowalny szkic).
    attachments: [(filename, bytes, maintype, subtype)]."""
    msg = EmailMessage()
    if to:
        msg["To"] = to
    msg["Subject"] = subject
    msg["X-Unsent"] = "1"
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    for fn, data, mt, st in attachments:
        msg.add_attachment(data, maintype=mt, subtype=st, filename=fn)
    return bytes(msg)


def _safe_name(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "").strip("_")[:60] or "x"


def export_batch(ps, ids, lang="pl", to=None, user=""):
    """Paczka dla inżyniera: XLSX + PNG + szkic .eml w DATA_DIR/exports/audit/.
    Zgłoszenia -> status 'sent'. Zwraca {batch_id, out_dir, eml, xlsx, files}."""
    init_audit_tables()
    ps = (ps or "").strip().upper()
    if lang not in ("pl", "en", "de"):
        lang = "pl"
    issues = [i for i in (get_issue(x, lang) for x in ids or []) if i and i["ps_code"] == ps]
    if not issues:
        raise ValueError(amsg("noIssues", lang))
    conn = zs.get_db()
    cur = conn.cursor()
    rev = ps_revision_key(cur, ps)
    pn = cur.execute("SELECT project_name FROM zuken_ps_summaries WHERE ps_code=?", (ps,)).fetchone()
    pname = (pn[0] if pn else "") or ""
    meta_ = get_ps_meta(ps, cur=cur)
    sch = main_schematic(cur, ps)
    conn.close()
    rev_label = (sch or {}).get("filename") or rev
    to = (to if to is not None else meta_.get("engineer_email")) or ""
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out_root = os.path.join(zs.DATA_DIR, "exports", "audit")
    hdr_keys = ("no", "id", "ps", "rev", "sheet", "page", "grid", "devices", "cat", "problem", "fix", "sev", "img", "reply")
    headers = [amsg(f"x.h.{k}", lang) for k in hdr_keys]
    rows, attach_imgs = [], []
    for n, i in enumerate(issues, 1):
        loc = i.get("location") or {}
        img_name = ""
        try:
            png = snapshot_png(i)
        except Exception:
            png = None
        if png:
            img_name = f"{i['id']}_str{loc.get('page', '')}.png"
            attach_imgs.append((img_name, png))
        sheet = " ".join(x for x in (str(loc.get("sheet_number") or ""), loc.get("sheet_title") or "") if x)
        rows.append([n, i["id"], ps, rev_label, sheet, loc.get("page") or "", loc.get("grid") or "",
                     ", ".join(i.get("devices") or []), i["category_r"], i["description_r"] or i["title_r"],
                     i["fix_r"] or "", i["severity_r"], img_name, ""])
    xlsx = xlsx_bytes(headers, rows, amsg("x.sheet", lang),
                      widths=[5, 7, 10, 22, 22, 8, 7, 26, 20, 60, 45, 11, 18, 30])
    conn = zs.get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO zuken_issue_batches (ps_code, lang, recipient, issue_ids, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (ps, lang, to, _j([i["id"] for i in issues]), user or "", _now()))
    bid = cur.lastrowid
    out_dir = os.path.join(out_root, f"{ps}_{stamp}_{bid}")
    os.makedirs(out_dir, exist_ok=True)
    xname = f"{ps}_E3_{amsg('x.sheet', lang)}_{stamp}.xlsx"
    with open(os.path.join(out_dir, xname), "wb") as fh:
        fh.write(xlsx)
    for fn, data in attach_imgs:
        with open(os.path.join(out_dir, fn), "wb") as fh:
            fh.write(data)
    subj = amsg("x.subject", lang, ps=ps, name=pname, n=len(issues))
    body = amsg("x.body", lang, ps=ps, name=pname, rev=rev_label, n=len(issues))
    th = "".join(f"<th style='border:1px solid #ccc;padding:4px;background:#eee'>{_xesc(h)}</th>"
                 for h in (headers[0], headers[4], headers[6], headers[7], headers[9], headers[10]))
    trs = "".join("<tr>" + "".join(f"<td style='border:1px solid #ccc;padding:4px;vertical-align:top'>{_xesc(str(v))}</td>"
                                   for v in (r[0], r[4], r[6], r[7], r[9], r[10])) + "</tr>" for r in rows)
    html = ("<div style='font-family:Calibri,Arial,sans-serif;font-size:11pt'>" +
            "".join(f"<p>{_xesc(p)}</p>" for p in body.split("\n\n")) +
            f"<table style='border-collapse:collapse;font-size:10pt'><tr>{th}</tr>{trs}</table></div>")
    atts = [(xname, xlsx, "application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")]
    atts += [(fn, data, "image", "png") for fn, data in attach_imgs]
    eml = build_eml(to, subj, body, html, atts)
    ename = f"{ps}_szkic_{stamp}.eml"
    with open(os.path.join(out_dir, ename), "wb") as fh:
        fh.write(eml)
    now = _now()
    ph = ",".join("?" * len(issues))
    cur.execute("UPDATE zuken_issue_batches SET out_dir=? WHERE id=?", (out_dir, bid))
    cur.execute(f"""UPDATE zuken_issues SET status = CASE WHEN status IN ('new','confirmed') THEN 'sent' ELSE status END,
                    sent_at=?, batch_id=?, updated_at=? WHERE id IN ({ph})""",
                (now, bid, now, *[i["id"] for i in issues]))
    conn.commit()
    conn.close()
    return {"batch_id": bid, "out_dir": out_dir, "eml": os.path.join(out_dir, ename),
            "xlsx": os.path.join(out_dir, xname), "files": [xname, ename] + [f for f, _ in attach_imgs],
            "count": len(issues)}


def batch_file(batch_id, kind="eml"):
    init_audit_tables()
    conn = zs.get_db()
    r = conn.execute("SELECT out_dir FROM zuken_issue_batches WHERE id=?", (int(batch_id),)).fetchone()
    conn.close()
    if not r or not r[0] or not os.path.isdir(r[0]):
        return None
    for fn in sorted(os.listdir(r[0])):
        if fn.lower().endswith("." + kind):
            return os.path.join(r[0], fn)
    return None


# ═══════════════════════════════════════════════════════════════════
# PODPOWIEDZI DLA ASYSTENTA
# ═══════════════════════════════════════════════════════════════════
def open_issues_for_devices(ps, devices, lang="pl", cur=None):
    """Otwarte zgłoszenia 'engineer' dotyczące urządzeń z wyniku asystenta."""
    if not ps or not devices:
        return []
    own = cur is None
    try:
        if own:
            init_audit_tables()
            conn = zs.get_db()
            cur = conn.cursor()
        cleans = {zs.clean_device_code(d) for d in devices if d}
        out = []
        for r in cur.execute("""SELECT * FROM zuken_issues WHERE ps_code=? AND target='engineer'
                                AND status IN ('new','confirmed','sent','fixed','wontfix')
                                AND severity != 'info'""", (ps.upper(),)):
            devs = _uj(r["devices"], []) or []
            if any(zs.clean_device_code(d) in cleans for d in devs):
                d = _issue_dict(r, lang)
                out.append({"id": d["id"], "title": d["title_r"], "category": d["category"]})
        if own:
            conn.close()
        return out[:5]
    except Exception:
        return []
