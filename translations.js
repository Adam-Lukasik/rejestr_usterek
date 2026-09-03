// translations.js — Moduł wielojęzyczności (i18n) dla Rejestr Usterek v2.0
// Obsługa języka polskiego (PL) i angielskiego (EN)

const TRANSLATIONS = {
  pl: {
    nav: {
      appName: "Rejestr Usterek",
      appSubtitle: "Panel Diagnostyki i Serwisu",
      sectionMain: "Główne Menu",
      sectionConfig: "Konfiguracja",
      defects: "Rejestr usterek",
      newDefect: "Nowe zgłoszenie",
      projects: "Baza projektów (PS)",
      dictionaries: "Słowniki",
      users: "Użytkownicy",
      backup: "Kopie & Eksport",
      langLabel: "Język / Lang:",
      themeDark: "Tryb ciemny",
      themeLight: "Tryb jasny",
      changePassword: "Zmień hasło",
      logout: "Wyloguj",
      roleAdmin: "Administrator",
      roleTech: "Technik"
    },
    status: {
      open: "Otwarta",
      fixed: "Naprawiona",
      all: "Wszystkie statusy"
    },
    kpi: {
      total: "Łącznie usterek",
      open: "Do naprawy",
      fixed: "Naprawione",
      rate: "Skuteczność napraw",
      todayFixed: "Naprawione w tym tygodniu"
    },
    filters: {
      searchPlaceholder: "Szukaj: projekt PS, klient, model, VIN, opis problemu, autor...",
      allClients: "Wszyscy klienci",
      allTypes: "Wszystkie kategorie",
      allProjects: "Wszystkie projekty",
      clear: "Wyczyść filtry",
      showing: "Wyświetlanie",
      of: "z",
      defectsCount: "usterek"
    },
    table: {
      thVehicle: "Pojazd / Projekt",
      thProblem: "Problem i Kategoria",
      thStatus: "Status",
      thDate: "Data",
      thActions: "Akcje",
      empty: "Brak usterek spełniających wybrane kryteria wyszukiwania.",
      emptySub: "Spróbuj zmienić parametry filtrów lub wyszukiwaną frazę.",
      btnDetails: "Szczegóły",
      btnEdit: "Edytuj",
      btnDelete: "Usuń",
      photosCount: "zdjęć",
      docsCount: "dok.",
      solutionsCount: "wariantów"
    },
    detail: {
      title: "Szczegóły usterki",
      noSelection: "Brak wybranej usterki",
      noSelectionSub: "Kliknij dowolny wiersz na liście po lewej stronie, aby wyświetlić szczegóły, zdjęcia i warianty rozwiązań.",
      togglePanelHide: "Ukryj panel",
      togglePanelShow: "Pokaż panel",
      exportCsv: "Eksport CSV",
      headerVehicle: "Dane pojazdu i zlecenia",
      client: "Klient",
      model: "Model",
      project: "Projekt PS",
      vin: "VIN",
      category: "Kategoria",
      element: "Element / Podzespół",
      problem: "Opis problemu",
      repair: "Opis naprawy / Wykonane czynności",
      author: "Zgłosił",
      fixedBy: "Naprawił",
      fixedDate: "Data naprawy",
      createdDate: "Data zgłoszenia",
      photos: "Zdjęcia usterki",
      documents: "Dokumenty techniczne (PDF)",
      solutions: "Warianty rozwiązań i napraw",
      btnEdit: "Edytuj usterkę",
      btnPrint: "Drukuj kartę usterki",
      btnMarkFixed: "Oznacz jako naprawioną",
      btnMarkOpen: "Przywróć jako otwartą",
      btnClose: "Zamknij podgląd",
      emptyPhotos: "Brak dołączonych zdjęć usterki",
      emptyDocs: "Brak dołączonych dokumentów PDF",
      emptySolutions: "Brak wprowadzonych wariantów naprawy. Możesz dodać wariant klikając 'Edytuj usterkę'.",
      viewFullPhoto: "Kliknij, aby powiększyć",
      openPdf: "Otwórz dokument PDF",
      openInWindows: "Otwórz w aplikacji Windows",
      download: "Pobierz",
      closeModal: "✕ Zamknij (ESC)",
      badgeOriginalPl: "Oryginał PL",
      badgeTranslatedEn: "Przetłumaczono na EN"
    },
    solutions: {
      title: "Warianty rozwiązań i napraw",
      addBtn: "+ Dodaj wariant naprawy",
      variant: "Wariant",
      solutionTitle: "Tytuł rozwiązania",
      solutionDesc: "Instrukcja / Opis rozwiązania krok po kroku",
      solutionTitleEn: "Tytuł (EN)",
      solutionDescEn: "Opis (EN)",
      addPhoto: "Dodaj zdjęcie",
      addDoc: "Dodaj dokument PDF",
      save: "Zapisz wariant",
      delete: "Usuń wariant",
      confirmDelete: "Czy na pewno chcesz usunąć ten wariant rozwiązania?",
      photos: "Zdjęcia wariantu",
      docs: "Dokumenty wariantu",
      empty: "Brak dodanych wariantów naprawy."
    },
    form: {
      newTitle: "Nowa usterka",
      editTitle: "Edycja usterki",
      subtitle: "Wypełnij dane pojazdu oraz szczegółowy opis problemu.",
      client: "Klient",
      clientPlaceholder: "-- Wybierz klienta --",
      model: "Model pojazdu",
      modelPlaceholder: "-- Wybierz model --",
      project: "Projekt PS",
      projectPlaceholder: "np. PS011871",
      vin: "Numer VIN",
      vinPlaceholder: "np. WAUZZZ... lub ostatnie 6 cyfr",
      category: "Kategoria usterki",
      categoryPlaceholder: "-- Wybierz kategorię --",
      element: "Element / Podzespół",
      elementPlaceholder: "np. Oświetlenie kabiny, stopień wejściowy...",
      problem: "Opis problemu (PL)",
      problemHelp: "Wpisz opis po polsku — wersja angielska zostanie wygenerowana automatycznie w tle.",
      repair: "Opis naprawy / Wykonane czynności (PL)",
      repairHelp: "Opcjonalnie — uzupełnij po wykonaniu naprawy.",
      status: "Status usterki",
      fixedBy: "Kto naprawił",
      fixedByPlaceholder: "Imię i nazwisko serwisanta",
      btnSave: "Zapisz usterkę",
      btnSaveAndAddSolution: "Zapisz i dodaj wariant naprawy",
      btnCancel: "Anuluj",
      attachPhotos: "Załącz zdjęcia (maks. 6)",
      attachDocs: "Załącz dokumenty PDF (maks. 6)",
      dropPhotoHelp: "Przeciągnij zdjęcia lub kliknij tutaj",
      dropDocHelp: "Przeciągnij pliki PDF lub kliknij tutaj"
    },
    print: {
      sheetTitle: "KARTA DIAGNOSTYKI I NAPRAWY USTERKI",
      sheetSubtitle: "W.A.S. — Rejestr Usterek i Jakości Produkcji",
      defectId: "ID Zgłoszenia",
      reportDate: "Data wydruku",
      sectionVehicle: "1. DANE POJAZDU I ZLECENIA",
      sectionProblem: "2. OPIS USTERKI / PROBLEMU",
      sectionRepair: "3. SPOSÓB NAPRAWY I WARIANTY ROZWIĄZAŃ",
      sectionSignatures: "4. POTWIERDZENIE I ODBIÓR TECHNICZNY",
      client: "Klient",
      model: "Model",
      project: "Projekt PS",
      vin: "Numer VIN",
      category: "Kategoria",
      element: "Element",
      status: "Status",
      createdDate: "Data zgłoszenia",
      author: "Zgłaszający",
      fixedBy: "Naprawił",
      fixedDate: "Data naprawy",
      solutionsList: "Wprowadzone warianty naprawy:",
      signTech: "Podpis technika / serwisanta:",
      signQuality: "Podpis kontrolera jakości:",
      signDate: "Data odbioru:"
    },
    projects: {
      title: "Baza projektów",
      subtitle: "Lista wszystkich zarejestrowanych projektów PS wraz ze statystykami usterek.",
      thProject: "Projekt PS",
      thClient: "Klient",
      thModel: "Model pojazdu",
      thDefectsTotal: "Wszystkie usterki",
      thDefectsOpen: "Otwarte",
      thDefectsFixed: "Naprawione",
      thEfficiency: "Skuteczność"
    },
    dictionaries: {
      title: "Zarządzanie słownikami",
      subtitle: "Konfiguracja list wyboru dla klientów, modeli i kategorii usterek.",
      tabClients: "Klienci",
      tabModels: "Modele pojazdów",
      tabCategories: "Kategorie usterek",
      btnAdd: "+ Dodaj nową pozycję",
      promptNew: "Podaj nową wartość:",
      confirmDelete: "Czy na pewno chcesz usunąć pozycję:",
      saveSuccess: "Zapisano zmiany w słownikach."
    },
    users: {
      title: "Zarządzanie użytkownikami",
      subtitle: "Konta techników i administratorów systemu.",
      btnAdd: "+ Dodaj użytkownika",
      thUser: "Użytkownik",
      thRole: "Rola",
      thStatus: "Status",
      thEmail: "E-mail",
      thPhone: "Telefon",
      thActions: "Akcje",
      active: "Aktywny",
      inactive: "Zablokowany",
      btnResetPw: "Resetuj hasło",
      btnToggleActive: "Zablokuj/Odblokuj"
    },
    messages: {
      savedSuccess: "Usterka została pomyślnie zapisana.",
      savedSolutionSuccess: "Wariant naprawy został pomyślnie zapisany.",
      deletedSuccess: "Usterka została usunięta.",
      statusChanged: "Status usterki został zmieniony.",
      confirmDeleteDefect: "Czy na pewno chcesz bezpowrotnie usunąć tę usterkę wraz ze zdjęciami i wariantami?",
      fillRequired: "Proszę wypełnić wymagane pola (Klient, Model, Kategoria, Opis problemu).",
      autoTranslateInfo: "Wersja angielska została automatycznie zsynchronizowana.",
      copied: "Skopiowano do schowka."
    }
  },

  en: {
    nav: {
      appName: "Defect Registry",
      appSubtitle: "Diagnostic & Service Panel",
      sectionMain: "Main Menu",
      sectionConfig: "Configuration",
      defects: "Defects",
      newDefect: "New Defect",
      projects: "Projects Database",
      dictionaries: "Dictionaries",
      users: "Users",
      backup: "Database Backup",
      langLabel: "Language:",
      themeDark: "Dark Mode",
      themeLight: "Light Mode",
      changePassword: "Change Password",
      logout: "Log out",
      roleAdmin: "Administrator",
      roleTech: "Technician"
    },
    status: {
      open: "Open",
      fixed: "Resolved",
      all: "All Statuses"
    },
    kpi: {
      total: "Total Defects",
      open: "To Resolve",
      fixed: "Resolved",
      rate: "Resolution Rate",
      todayFixed: "Resolved this week"
    },
    filters: {
      searchPlaceholder: "Search: PS project, client, model, VIN, problem, author...",
      allClients: "All Clients",
      allTypes: "All Categories",
      allProjects: "All Projects",
      clear: "Clear filters",
      showing: "Showing",
      of: "of",
      defectsCount: "defects"
    },
    table: {
      thVehicle: "Vehicle / Project",
      thProblem: "Problem & Category",
      thStatus: "Status",
      thDate: "Date",
      thActions: "Actions",
      empty: "No defects match the selected search criteria.",
      emptySub: "Try adjusting filter parameters or your search query.",
      btnDetails: "Details",
      btnEdit: "Edit",
      btnDelete: "Delete",
      photosCount: "photos",
      docsCount: "docs",
      solutionsCount: "solutions"
    },
    detail: {
      title: "Defect Details",
      noSelection: "No Defect Selected",
      noSelectionSub: "Click any row on the left to display details, photos, and repair solutions.",
      togglePanelHide: "Hide panel",
      togglePanelShow: "Show panel",
      exportCsv: "Export CSV",
      headerVehicle: "Vehicle & Project Information",
      client: "Client",
      model: "Model",
      project: "PS Project",
      vin: "VIN",
      category: "Category",
      element: "Component / Element",
      problem: "Problem Description",
      repair: "Repair Description / Actions Performed",
      author: "Reported by",
      fixedBy: "Resolved by",
      fixedDate: "Resolution Date",
      createdDate: "Report Date",
      photos: "Defect Photos",
      documents: "Technical Documents (PDF)",
      solutions: "Repair Solutions & Variants",
      btnEdit: "Edit Defect",
      btnPrint: "Print Defect Sheet",
      btnMarkFixed: "Mark as Resolved",
      btnMarkOpen: "Reopen Defect",
      btnClose: "Close Preview",
      emptyPhotos: "No photos attached to this defect",
      emptyDocs: "No PDF documents attached",
      emptySolutions: "No repair solution variants entered yet. Click 'Edit Defect' to add one.",
      viewFullPhoto: "Click to enlarge",
      openPdf: "Open PDF Document",
      openInWindows: "Open in Windows App",
      download: "Download",
      closeModal: "✕ Close (ESC)",
      badgeOriginalPl: "Original [PL]",
      badgeTranslatedEn: "Translated to [EN]"
    },
    solutions: {
      title: "Repair Solutions & Variants",
      addBtn: "+ Add Repair Variant",
      variant: "Variant",
      solutionTitle: "Solution Title",
      solutionDesc: "Step-by-step Solution Instructions / Description",
      solutionTitleEn: "Title (EN)",
      solutionDescEn: "Description (EN)",
      addPhoto: "Add Photo",
      addDoc: "Add PDF Document",
      save: "Save Variant",
      delete: "Delete Variant",
      confirmDelete: "Are you sure you want to delete this repair variant?",
      photos: "Variant Photos",
      docs: "Variant Documents",
      empty: "No repair solution variants added yet."
    },
    form: {
      newTitle: "New Defect",
      editTitle: "Edit Defect",
      subtitle: "Enter vehicle details and a clear description of the defect.",
      client: "Client",
      clientPlaceholder: "-- Select client --",
      model: "Vehicle Model",
      modelPlaceholder: "-- Select model --",
      project: "PS Project",
      projectPlaceholder: "e.g. PS011871",
      vin: "VIN Number",
      vinPlaceholder: "e.g. WAUZZZ... or last 6 digits",
      category: "Defect Category",
      categoryPlaceholder: "-- Select category --",
      element: "Element / Component",
      elementPlaceholder: "e.g. Saloon lighting, step entrance...",
      problem: "Problem Description",
      problemHelp: "English translation is automatically generated in the background.",
      repair: "Repair Description / Actions Taken",
      repairHelp: "Optional — fill in once repair is completed.",
      status: "Defect Status",
      fixedBy: "Resolved By",
      fixedByPlaceholder: "Technician full name",
      btnSave: "Save Defect",
      btnSaveAndAddSolution: "Save & Add Repair Solution",
      btnCancel: "Cancel",
      attachPhotos: "Attach Photos (max 6)",
      attachDocs: "Attach PDF Documents (max 6)",
      dropPhotoHelp: "Drag photos or click here to upload",
      dropDocHelp: "Drag PDF files or click here to upload"
    },
    print: {
      sheetTitle: "DEFECT DIAGNOSTIC & REPAIR SHEET",
      sheetSubtitle: "W.A.S. — Quality & Defect Management Registry",
      defectId: "Defect ID",
      reportDate: "Print Date",
      sectionVehicle: "1. VEHICLE & PROJECT DATA",
      sectionProblem: "2. DEFECT / PROBLEM DESCRIPTION",
      sectionRepair: "3. REPAIR METHOD & SOLUTIONS",
      sectionSignatures: "4. TECHNICAL ACCEPTANCE & SIGNATURES",
      client: "Client",
      model: "Model",
      project: "PS Project",
      vin: "VIN Number",
      category: "Category",
      element: "Element",
      status: "Status",
      createdDate: "Report Date",
      author: "Reported by",
      fixedBy: "Resolved by",
      fixedDate: "Resolution Date",
      solutionsList: "Documented repair solutions:",
      signTech: "Technician Signature:",
      signQuality: "Quality Inspector Signature:",
      signDate: "Acceptance Date:"
    },
    projects: {
      title: "Projects Database",
      subtitle: "Overview of all registered PS vehicle conversion projects.",
      thProject: "PS Project",
      thClient: "Client",
      thModel: "Vehicle Model",
      thDefectsTotal: "Total Defects",
      thDefectsOpen: "Open",
      thDefectsFixed: "Resolved",
      thEfficiency: "Resolution Rate"
    },
    dictionaries: {
      title: "System Dictionaries",
      subtitle: "Manage selection lists for clients, models, and defect categories.",
      tabClients: "Clients",
      tabModels: "Vehicle Models",
      tabCategories: "Defect Categories",
      btnAdd: "+ Add new item",
      promptNew: "Enter new value:",
      confirmDelete: "Are you sure you want to delete item:",
      saveSuccess: "Dictionary changes saved successfully."
    },
    users: {
      title: "User Management",
      subtitle: "System accounts for technicians and administrators.",
      btnAdd: "+ Add User",
      thUser: "User",
      thRole: "Role",
      thStatus: "Status",
      thEmail: "E-mail",
      thPhone: "Phone",
      thActions: "Actions",
      active: "Active",
      inactive: "Disabled",
      btnResetPw: "Reset Password",
      btnToggleActive: "Enable / Disable"
    },
    messages: {
      savedSuccess: "Defect saved successfully.",
      savedSolutionSuccess: "Repair solution variant saved successfully.",
      deletedSuccess: "Defect deleted successfully.",
      statusChanged: "Defect status updated successfully.",
      confirmDeleteDefect: "Are you sure you want to permanently delete this defect, including its photos and solutions?",
      fillRequired: "Please fill in all required fields (Client, Model, Category, Problem Description).",
      autoTranslateInfo: "English translation synchronized automatically.",
      copied: "Copied to clipboard."
    }
  }
};

// ── MAPOWANIE KATEGORII SŁOWNIKOWYCH (PL <-> EN) ──
const CATEGORY_MAP_PL_TO_EN = {
  "Oświetlenie": "Lighting",
  "Sygnalizacja dźwiękowa": "Sirens & Sound Warning",
  "Zabudowa medyczna": "Medical Conversion / Saloon",
  "Pojazd bazowy": "Base Vehicle",
  "Instalacja 115V": "115V Electrical System",
  "Instalacja 12V": "12V Electrical System",
  "Instalacja 230V": "230V Electrical System",
  "Instalacja antenowa GPS": "GPS Antenna System",
  "Instalacja antenowa GSM": "GSM Antenna System",
  "Instalacja antenowa WLAN": "WLAN Antenna System",
  "Rejestrator": "Event Recorder",
  "Interkom": "Intercom System",
  "HVAC": "HVAC (Climate Control)",
  "ACETECH": "ACETECH",
  "CAN": "CAN Bus",
  "Carnation": "Carnation",
  "OPSES": "OPSES",
  "ORTUS": "ORTUS"
};

const CATEGORY_MAP_EN_TO_PL = Object.fromEntries(
  Object.entries(CATEGORY_MAP_PL_TO_EN).map(([pl, en]) => [en.toLowerCase(), pl.toLowerCase()])
);

// ── SŁOWNIK SYNONIMÓW TECHNICZNYCH DLA WYSZUKIWARKI (Bilingual Search Expansion) ──
const TECHNICAL_SYNONYMS = [
  // Oświetlenie i elektryka
  { pl: ["światło", "światła", "oświetlenie", "lampa", "lampy", "led", "reflektor"], en: ["light", "lights", "lighting", "lamp", "lamps", "headlight", "beam"] },
  { pl: ["bezpiecznik", "bezpieczniki"], en: ["fuse", "fuses", "breaker", "fusebox"] },
  { pl: ["gniazdo", "gniazdko", "gniazda", "wtyczka"], en: ["socket", "outlet", "plug", "receptacle"] },
  { pl: ["przekaźnik", "przekaźniki"], en: ["relay", "relays"] },
  { pl: ["włącznik", "przełącznik", "wyłącznik"], en: ["switch", "button", "toggle"] },
  { pl: ["przewód", "przewody", "kabel", "kable", "wiązka"], en: ["wire", "wires", "cable", "cables", "harness", "loom"] },
  { pl: ["akumulator", "bateria", "zasilanie"], en: ["battery", "accumulator", "power", "supply"] },
  { pl: ["przetwornica", "falownik", "inwerter"], en: ["inverter", "converter", "transformer"] },
  { pl: ["zwarcie", "brak masy", "brak zasilania"], en: ["short circuit", "ground fault", "no power", "dead"] },

  // Elementy nadwozia i wnętrza karetki
  { pl: ["drzwi", "wrota", "klamka", "zamek"], en: ["door", "doors", "handle", "lock", "latch"] },
  { pl: ["stopień", "schodek", "stopnie"], en: ["step", "footstep", "steps"] },
  { pl: ["nosze", "stół noszy", "laweta"], en: ["stretcher", "cot", "ramp", "tray"] },
  { pl: ["fotel", "fotele", "siedzenie", "pas", "pasy"], en: ["seat", "chair", "belt", "seatbelt"] },
  { pl: ["szafka", "szuflada", "półka", "schowek"], en: ["cabinet", "drawer", "shelf", "compartment", "locker"] },
  { pl: ["klimatyzacja", "ogrzewanie", "nawiew", "wentylacja"], en: ["hvac", "ac", "air conditioning", "heating", "heater", "ventilation", "blower"] },
  { pl: ["syrena", "klakson", "głośnik"], en: ["siren", "horn", "speaker", "sounder"] },
  { pl: ["kogut", "belka", "flesz", "stroboskop"], en: ["lightbar", "beacon", "flash", "strobe", "grille light"] },
  { pl: ["przedział medyczny", "zabudowa"], en: ["saloon", "medical compartment", "patient area"] },
  { pl: ["szyba", "okno", "lusterko"], en: ["window", "glass", "mirror"] },
  { pl: ["czujnik", "sensor"], en: ["sensor", "probe", "detector"] },
  { pl: ["kamera", "rejestrator"], en: ["camera", "cctv", "recorder", "dashcam"] }
];

// ── AKTUALNY JĘZYK I FUNKCJE POMOCNICZE ──
let CURRENT_LANG = localStorage.getItem('app_lang') || 'pl';

function getLanguage() {
  return CURRENT_LANG;
}

function setLanguage(lang) {
  if (lang !== 'pl' && lang !== 'en') lang = 'pl';
  CURRENT_LANG = lang;
  localStorage.setItem('app_lang', lang);
  document.documentElement.lang = lang;

  // Zapisz preferencję do desktop_config.json przez opcjonalny endpoint
  try {
    fetch('/api/user-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: lang })
    }).catch(() => {});
  } catch (e) {}

  applyLanguage(lang);
}

function t(key, params = {}) {
  const keys = key.split('.');
  let val = keys.reduce((obj, k) => obj?.[k], TRANSLATIONS[CURRENT_LANG])
         || keys.reduce((obj, k) => obj?.[k], TRANSLATIONS['pl'])
         || key;

  if (typeof val === 'string') {
    for (const [pKey, pVal] of Object.entries(params)) {
      val = val.replaceAll(`{${pKey}}`, pVal);
    }
  }
  return val;
}

function translateCategory(categoryName, lang = CURRENT_LANG) {
  if (!categoryName) return '';
  if (lang === 'en') {
    return CATEGORY_MAP_PL_TO_EN[categoryName] || categoryName;
  }
  return categoryName;
}

/**
 * Rozwija zapytanie wyszukiwarki o odpowiedniki w drugim języku (PL <-> EN)
 * np. wpisanie "fuse" zwraca ["fuse", "bezpiecznik", "bezpieczniki"]
 */
function expandSearchQuery(query) {
  if (!query) return [];
  const q = query.toLowerCase().trim();
  const terms = new Set([q]);

  for (const group of TECHNICAL_SYNONYMS) {
    const matchedEn = group.en.some(word => q.includes(word) || word.includes(q));
    const matchedPl = group.pl.some(word => q.includes(word) || word.includes(q));

    if (matchedEn || matchedPl) {
      group.pl.forEach(w => terms.add(w.toLowerCase()));
      group.en.forEach(w => terms.add(w.toLowerCase()));
    }
  }

  // Rozszerz o przetłumaczone kategorie
  for (const [pl, en] of Object.entries(CATEGORY_MAP_PL_TO_EN)) {
    if (q.includes(pl.toLowerCase()) || pl.toLowerCase().includes(q)) {
      terms.add(en.toLowerCase());
    }
    if (q.includes(en.toLowerCase()) || en.toLowerCase().includes(q)) {
      terms.add(pl.toLowerCase());
    }
  }

  return Array.from(terms);
}

/**
 * Aplikuje tłumaczenia do wszystkich elementów w DOM z atrybutami data-i18n
 */
function applyLanguage(lang = CURRENT_LANG) {
  CURRENT_LANG = lang;
  document.documentElement.lang = lang;

  // 1. Zwykła zawartość tekstowa (data-i18n)
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (key) {
      const translated = t(key);
      if (typeof translated === 'string') el.textContent = translated;
    }
  });

  // 2. data-i18n-html dla elementów z tagami HTML (np. SVG + tekst)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.dataset.i18nHtml;
    if (key) {
      const translated = t(key);
      if (typeof translated === 'string') el.innerHTML = translated;
    }
  });

  // 3. Placeholder dla pól wejściowych
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (key) el.placeholder = t(key);
  });

  // 4. Tooltipy title
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.dataset.i18nTitle;
    if (key) el.title = t(key);
  });

  // 5. Aktualizacja selektora języka w nagłówku
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  // 6. Odświeżenie dynamicznych komponentów
  const pageTitle = `${t('nav.appName')} v2.0 - ${t('nav.appSubtitle')}`;
  document.title = pageTitle;
  if (window.pywebview && window.pywebview.api && window.pywebview.api.set_title) {
    try { window.pywebview.api.set_title(pageTitle); } catch(e) {}
  }

  if (typeof updateConnectionStatus === 'function') {
    const lamp = document.getElementById('conn-lamp');
    updateConnectionStatus(lamp ? !lamp.classList.contains('offline') : true);
  }
  if (typeof updateDetailToggleBtn === 'function') {
    const dp = document.getElementById('detail-pane');
    updateDetailToggleBtn(dp ? dp.classList.contains('hidden') : false);
  }
  if (typeof updateUserBadge === 'function') {
    updateUserBadge();
  }
  if (typeof applyTheme === 'function') {
    const curTheme = (window.STATE && window.STATE.theme) || localStorage.getItem('ru_theme') || 'light';
    applyTheme(curTheme);
  }
  if (typeof populateDropdowns === 'function') {
    populateDropdowns();
  }

  if (typeof renderKPIs === 'function') renderKPIs();
  if (typeof renderDefectsTable === 'function') renderDefectsTable();
  if (window.STATE && window.STATE.selectedRecordId) {
    if (typeof selectRecord === 'function') selectRecord(window.STATE.selectedRecordId);
    const modalPreview = document.getElementById('modal-defect-preview');
    if (modalPreview && (modalPreview.style.display === 'flex' || modalPreview.classList.contains('active')) && typeof openDefectPreview === 'function') {
      openDefectPreview(window.STATE.selectedRecordId);
    }
  }
}
