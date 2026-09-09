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
      open: "Oczekuje na wariant",
      fixed: "Z wariantami",
      all: "Wszystkie usterki",
      withSolutions: "Z wariantami napraw",
      withoutSolutions: "Bez wariantów"
    },
    kpi: {
      total: "Łącznie usterek",
      open: "Bez wariantów",
      fixed: "Z wariantami",
      rate: "Pokrycie rozwiązaniami",
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
      thStatus: "Warianty naprawy",
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
      empty: "Brak dodanych wariantów naprawy.",
      addedBy: "dodał:",
      noSolutions: "Brak wariantów",
      solutionCount: "wariantów"
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
    },
    zuken: {
      navItem: "Asystent Zuken E3",
      btnDiagnose: "✨ Asystent Zuken",
      btnDiagnoseLong: "✨ Podpowiedz ze schematu Zuken",
      btnSolutionSchematic: "📐 Schemat Zuken",
      focusedVariant: "Kontekst wariantu:",
      clearVariantFilter: "Pokaż całą usterkę",
      modalTitle: "Asystent Diagnostyczny Zuken E3 (Offline)",
      modalSubtitle: "Lokalna analiza wiązek elektrycznych, punktów pomiarowych i historii napraw",
      searchPlaceholder: "Wpisz numer przewodu (np. 185D, 30B), złącze (X132), bezpiecznik (F18), odbiornik...",
      btnSearch: "🔍 Analizuj obwód",
      btnSync: "🔄 Skanuj Bazę wiedzy",
      searching: "Analizowanie topologii wiązki...",
      noResults: "Brak bezpośrednich połączeń dla tego zapytania. Sprawdź pisownię lub zajrzyj do słownika skrótów.",
      circuitsFound: "Zidentyfikowane obwody i punkty pomiarowe",
      historyFound: "Podobne usterki i rozwiązania techników",
      glossaryTab: "Słownik oznaczeń Zuken",
      wireInfo: "Przewód",
      copyToSolution: "Wstaw do rozwiązania",
      revisionAlert: "Uwaga: Wykryto zmianę wiązki w trakcie trwania serii",
      sheetsFound: "Lokalizacja na arkuszach schematu PDF",
      openSheetPdf: "Otwórz arkusz w PDF",
      activeRevision: "Aktualna robocza wiązka",
      archivalRevision: "Wersja archiwalna",
      sheet: "Arkusz",
      elementsOnSheet: "Znalezione elementy",
      tabCircuits: "⚡ Analiza obwodu",
      tabBom: "📦 Złączki i Komponenty (BOM)",
      tabGlossary: "📖 Słownik skrótów",
      bomSectionTitle: "Zidentyfikowane komponenty i złączki z BOM",
      bomFilterSupplier: "Wszyscy dostawcy",
      bomFilterCategory: "Wszystkie kategorie",
      bomSearchPlaceholder: "Szukaj w BOM: kod artykułu, dostawca, aparat (-X434), opis...",
      bomAmountLabel: "Ilość w pojeździe:",
      bomSupplierLabel: "Dostawca / Producent:",
      bomCategoryLabel: "Kategoria:",
      bomDeviceLabel: "Użyte w aparacie:",
      bomRelatedTerminals: "Pasujące konektory / terminale (z BOM):",
      bomUploadPhoto: "📷 Dodaj / Zmień zdjęcie",
      bomPastePhotoHelp: "Wklej ze schowka (Ctrl+V) lub wybierz plik",
      bomNoPhoto: "Brak zdjęcia",
      bomNoPhotoSub: "Kliknij, aby dodać lub wkleić zdjęcie",
      bomSavePhoto: "Zapisz zdjęcie w Bazie wiedzy",
      bomPhotoSaved: "Zapisano zdjęcie w Bazie wiedzy."
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
      open: "Pending solution",
      fixed: "Has solutions",
      all: "All defects",
      withSolutions: "With solutions",
      withoutSolutions: "No solutions"
    },
    kpi: {
      total: "Total Defects",
      open: "No solutions",
      fixed: "With solutions",
      rate: "Solution coverage",
      todayFixed: "Solved this week"
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
      thStatus: "Repair Solutions",
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
      empty: "No repair solution variants added yet.",
      addedBy: "added by:",
      noSolutions: "No solutions",
      solutionCount: "solutions"
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
    },
    zuken: {
      navItem: "Zuken E3 Assistant",
      btnDiagnose: "✨ Zuken Assistant",
      btnDiagnoseLong: "✨ Diagnose from Zuken Schematic",
      btnSolutionSchematic: "📐 Zuken Schematic",
      focusedVariant: "Variant Context:",
      clearVariantFilter: "Show entire defect",
      modalTitle: "Zuken E3 Diagnostic Assistant (Offline)",
      modalSubtitle: "Local wiring harness topology, test points, and repair history analysis",
      searchPlaceholder: "Enter wire number (e.g. 185D, 30B), connector (X132), fuse (F18), device...",
      btnSearch: "🔍 Trace Circuit",
      btnSync: "🔄 Scan Knowledge Base",
      searching: "Analyzing wiring topology...",
      noResults: "No direct connections found for this query. Check spelling or browse the glossary.",
      circuitsFound: "Identified circuits and measurement points",
      historyFound: "Similar defects and technician solutions",
      glossaryTab: "Zuken Designation Glossary",
      wireInfo: "Wire",
      copyToSolution: "Insert into solution",
      revisionAlert: "Warning: Harness revision change detected in series",
      sheetsFound: "Location on PDF Schematic Sheets",
      openSheetPdf: "Open Sheet in PDF",
      activeRevision: "Active production harness",
      archivalRevision: "Archival revision",
      sheet: "Sheet",
      elementsOnSheet: "Found elements",
      tabCircuits: "⚡ Circuit Trace",
      tabBom: "📦 Connectors & Components (BOM)",
      tabGlossary: "📖 Glossary",
      bomSectionTitle: "Identified BOM Connectors & Components",
      bomFilterSupplier: "All Suppliers",
      bomFilterCategory: "All Categories",
      bomSearchPlaceholder: "Search BOM: part number, supplier, device (-X434), desc...",
      bomAmountLabel: "Qty in vehicle:",
      bomSupplierLabel: "Supplier / Manufacturer:",
      bomCategoryLabel: "Category:",
      bomDeviceLabel: "Used in device:",
      bomRelatedTerminals: "Matching mating terminals (from BOM):",
      bomUploadPhoto: "📷 Add / Change Photo",
      bomPastePhotoHelp: "Paste from clipboard (Ctrl+V) or browse file",
      bomNoPhoto: "No photo",
      bomNoPhotoSub: "Click to add or paste a photo",
      bomSavePhoto: "Save Photo to Knowledge Base",
      bomPhotoSaved: "Photo saved in Knowledge Base."
    }
  },

  de: {
    nav: {
      appName: "Mängelregister",
      appSubtitle: "Diagnose- und Servicepanel",
      sectionMain: "Hauptmenü",
      sectionConfig: "Konfiguration",
      defects: "Mängelregister",
      newDefect: "Neuer Mangel",
      projects: "Projektdatenbank (PS)",
      dictionaries: "Wörterbücher",
      users: "Benutzer",
      backup: "Datensicherung & Export",
      langLabel: "Sprache / Lang:",
      themeDark: "Dunkelmodus",
      themeLight: "Hellmodus",
      changePassword: "Passwort ändern",
      logout: "Abmelden",
      roleAdmin: "Administrator",
      roleTech: "Techniker"
    },
    status: {
      open: "Wartet auf Lösung",
      fixed: "Mit Lösungen",
      all: "Alle Mängel",
      withSolutions: "Mit Reparaturlösungen",
      withoutSolutions: "Ohne Lösungen"
    },
    kpi: {
      total: "Mängel gesamt",
      open: "Ohne Lösungen",
      fixed: "Mit Lösungen",
      rate: "Lösungsquote",
      todayFixed: "Diese Woche behoben"
    },
    filters: {
      searchPlaceholder: "Suche: PS-Projekt, Kunde, Modell, FIN, Problembeschreibung, Autor...",
      allClients: "Alle Kunden",
      allTypes: "Alle Kategorien",
      allProjects: "Alle Projekte",
      clear: "Filter zurücksetzen",
      showing: "Anzeige",
      of: "von",
      defectsCount: "Mängeln"
    },
    table: {
      thVehicle: "Fahrzeug / Projekt",
      thProblem: "Problem & Kategorie",
      thStatus: "Reparaturlösungen",
      thDate: "Datum",
      thActions: "Aktionen",
      empty: "Keine Mängel entsprechen den ausgewählten Suchkriterien.",
      emptySub: "Versuchen Sie, die Filter anzupassen oder die Suchanfrage zu ändern.",
      btnDetails: "Details",
      btnEdit: "Bearbeiten",
      btnDelete: "Löschen",
      photosCount: "Fotos",
      docsCount: "Dokumente",
      solutionsCount: "Lösungen"
    },
    detail: {
      title: "Mangeldetails",
      noSelection: "Kein Mangel ausgewählt",
      noSelectionSub: "Klicken Sie links auf eine Zeile, um Details, Fotos und Reparaturlösungen anzuzeigen.",
      togglePanelHide: "Seitenleiste ausblenden",
      togglePanelShow: "Seitenleiste anzeigen",
      exportCsv: "CSV exportieren",
      headerVehicle: "Fahrzeug- & Projektinformationen",
      client: "Kunde",
      model: "Modell",
      project: "PS-Projekt",
      vin: "FIN / Fahrgestellnummer",
      category: "Kategorie",
      element: "Bauteil / Komponente",
      problem: "Problembeschreibung",
      repair: "Reparaturbeschreibung / Durchgeführte Maßnahmen",
      author: "Gemeldet von",
      fixedBy: "Behoben von",
      fixedDate: "Behebungsdatum",
      createdDate: "Meldedatum",
      photos: "Mängelfotos",
      documents: "Technische Dokumente (PDF)",
      solutions: "Reparaturlösungen & Varianten",
      btnEdit: "Mangel bearbeiten",
      btnPrint: "Mängelprotokoll drucken",
      btnMarkFixed: "Als behoben markieren",
      btnMarkOpen: "Mangel wiedereröffnen",
      btnClose: "Vorschau schließen",
      emptyPhotos: "Keine Fotos für diesen Mangel angehängt",
      emptyDocs: "Keine PDF-Dokumente angehängt",
      emptySolutions: "Noch keine Reparaturlösungen eingetragen. Klicken Sie auf 'Bearbeiten', um eine hinzuzufügen.",
      viewFullPhoto: "Klicken zum Vergrößern",
      openPdf: "PDF-Dokument öffnen",
      openInWindows: "In Windows-App öffnen",
      download: "Herunterladen",
      closeModal: "✕ Schließen (ESC)",
      badgeOriginalPl: "Original [PL]",
      badgeTranslatedEn: "Übersetzung [EN]"
    },
    solutions: {
      title: "Reparaturlösungen & Varianten",
      addBtn: "+ Lösungsvariante hinzufügen",
      variant: "Variante",
      solutionTitle: "Lösungstitel",
      solutionDesc: "Schritt-für-Schritt Reparaturanleitung / Beschreibung",
      solutionTitleEn: "Titel (EN)",
      solutionDescEn: "Beschreibung (EN)",
      addPhoto: "Foto hinzufügen",
      addDoc: "PDF-Dokument hinzufügen",
      save: "Variante speichern",
      delete: "Variante löschen",
      confirmDelete: "Möchten Sie diese Reparaturvariante wirklich löschen?",
      photos: "Fotos zur Variante",
      docs: "Dokumente zur Variante",
      empty: "Noch keine Reparaturvarianten eingetragen.",
      addedBy: "hinzugefügt von:",
      noSolutions: "Keine Lösungen",
      solutionCount: "Lösungen"
    },
    form: {
      newTitle: "Neuer Mangel",
      editTitle: "Mangel bearbeiten",
      subtitle: "Geben Sie Fahrzeugdaten und eine klare Beschreibung des Mangels ein.",
      client: "Kunde",
      clientPlaceholder: "-- Kunde auswählen --",
      model: "Fahrzeugmodell",
      modelPlaceholder: "-- Modell auswählen --",
      project: "PS-Projekt",
      projectPlaceholder: "z. B. PS011871",
      vin: "FIN / Fahrgestellnummer",
      vinPlaceholder: "z. B. WAUZZZ... oder die letzten 6 Ziffern",
      category: "Mangelkategorie",
      categoryPlaceholder: "-- Kategorie auswählen --",
      element: "Bauteil / Komponente",
      elementPlaceholder: "z. B. Deckenbeleuchtung, Einstiegsstufe...",
      problem: "Problembeschreibung",
      problemHelp: "Die englische Übersetzung wird automatisch im Hintergrund erstellt.",
      repair: "Reparaturbeschreibung / Durchgeführte Maßnahmen",
      repairHelp: "Optional — nach Abschluss der Reparatur ausfüllen.",
      status: "Mangelstatus",
      fixedBy: "Behoben von",
      fixedByPlaceholder: "Name des Technikers",
      btnSave: "Mangel speichern",
      btnSaveAndAddSolution: "Speichern & Reparaturlösung hinzufügen",
      btnCancel: "Abbrechen",
      attachPhotos: "Fotos anhängen (max. 6)",
      attachDocs: "PDF-Dokumente anhängen (max. 6)",
      dropPhotoHelp: "Fotos hierher ziehen oder klicken zum Hochladen",
      dropDocHelp: "PDF-Dateien hierher ziehen oder klicken zum Hochladen"
    },
    print: {
      sheetTitle: "DIAGNOSE- UND REPARATURPROTOKOLL",
      sheetSubtitle: "W.A.S. — Qualitäts- und Mängelverwaltung",
      defectId: "Mangel-ID",
      reportDate: "Druckdatum",
      sectionVehicle: "1. FAHRZEUG- UND PROJEKTDATEN",
      sectionProblem: "2. MANGEL- / PROBLEMBESCHREIBUNG",
      sectionRepair: "3. REPARATURVERFAHREN UND LÖSUNGEN",
      sectionSignatures: "4. TECHNISCHE ABNAHME UND UNTERSCHRIFTEN",
      client: "Kunde",
      model: "Modell",
      project: "PS-Projekt",
      vin: "FIN-Nummer",
      category: "Kategorie",
      element: "Bauteil",
      status: "Status",
      createdDate: "Meldedatum",
      author: "Gemeldet von",
      fixedBy: "Behoben von",
      fixedDate: "Behebungsdatum",
      solutionsList: "Dokumentierte Reparaturlösungen:",
      signTech: "Unterschrift Techniker:",
      signQuality: "Unterschrift Qualitätsprüfer:",
      signDate: "Abnahmedatum:"
    },
    projects: {
      title: "Projektdatenbank",
      subtitle: "Übersicht über alle registrierten PS-Ausbauprojekte.",
      thProject: "PS-Projekt",
      thClient: "Kunde",
      thModel: "Fahrzeugmodell",
      thDefectsTotal: "Mängel gesamt",
      thDefectsOpen: "Offen",
      thDefectsFixed: "Behoben",
      thEfficiency: "Lösungsquote"
    },
    dictionaries: {
      title: "Systemwörterbücher",
      subtitle: "Auswahllisten für Kunden, Modelle und Mangelkategorien verwalten.",
      tabClients: "Kunden",
      tabModels: "Fahrzeugmodelle",
      tabCategories: "Mangelkategorien",
      btnAdd: "+ Neuen Eintrag hinzufügen",
      promptNew: "Neuen Wert eingeben:",
      confirmDelete: "Möchten Sie diesen Eintrag wirklich löschen:",
      saveSuccess: "Wörterbuchänderungen erfolgreich gespeichert."
    },
    users: {
      title: "Benutzerverwaltung",
      subtitle: "Systemkonten für Techniker und Administratoren.",
      btnAdd: "+ Benutzer hinzufügen",
      thUser: "Benutzer",
      thRole: "Rolle",
      thStatus: "Status",
      thEmail: "E-Mail",
      thPhone: "Telefon",
      thActions: "Aktionen",
      active: "Aktiv",
      inactive: "Deaktiviert",
      btnResetPw: "Passwort zurücksetzen",
      btnToggleActive: "Aktivieren / Deaktivieren"
    },
    messages: {
      savedSuccess: "Mangel erfolgreich gespeichert.",
      savedSolutionSuccess: "Reparaturlösungsvariante erfolgreich gespeichert.",
      deletedSuccess: "Mangel erfolgreich gelöscht.",
      statusChanged: "Mangelstatus erfolgreich aktualisiert.",
      confirmDeleteDefect: "Möchten Sie diesen Mangel inklusive aller Fotos und Lösungen wirklich dauerhaft löschen?",
      fillRequired: "Bitte füllen Sie alle erforderlichen Felder aus (Kunde, Modell, Kategorie, Problembeschreibung).",
      autoTranslateInfo: "Englische Übersetzung automatisch synchronisiert.",
      copied: "In die Zwischenablage kopiert."
    },
    zuken: {
      navItem: "Zuken E3 Assistent",
      btnDiagnose: "✨ Zuken Assistent",
      btnDiagnoseLong: "✨ Diagnose aus Zuken-Schaltplan",
      btnSolutionSchematic: "📐 Zuken Schaltplan",
      focusedVariant: "Fokussierte Variante:",
      clearVariantFilter: "Gesamten Mangel anzeigen",
      modalTitle: "Zuken E3 Diagnose-Assistent (Offline)",
      modalSubtitle: "Lokale Kabelbaum-Topologie, Messpunkte und Reparaturhistorie",
      searchPlaceholder: "Leitungsnummer (z. B. 185D, 30B), Stecker (X132), Sicherung (F18), Gerät eingeben...",
      btnSearch: "🔍 Stromkreis analysieren",
      btnSync: "🔄 Wissensbasis scannen",
      searching: "Kabelbaum-Topologie wird analysiert...",
      noResults: "Keine direkten Verbindungen für diese Abfrage gefunden. Bitte Schreibweise prüfen oder das Glossar nutzen.",
      circuitsFound: "Identifizierte Stromkreise und Messpunkte",
      historyFound: "Ähnliche Mängel und Techniker-Lösungen",
      glossaryTab: "Zuken Abkürzungsverzeichnis",
      wireInfo: "Ader",
      copyToSolution: "In Lösung übernehmen",
      revisionAlert: "Achtung: Kabelbaum-Revisionsänderung in Serie erkannt",
      sheetsFound: "Position auf PDF-Schaltplanblättern",
      openSheetPdf: "Blatt in PDF öffnen",
      activeRevision: "Aktiver Produktions-Kabelbaum",
      archivalRevision: "Archivierte Revision",
      sheet: "Blatt",
      elementsOnSheet: "Gefundene Elemente",
      tabCircuits: "⚡ Stromkreisanalyse",
      tabBom: "📦 Steckverbinder & Komponenten (BOM)",
      tabGlossary: "📖 Abkürzungsverzeichnis",
      bomSectionTitle: "Identifizierte BOM-Steckverbinder & Bauteile",
      bomFilterSupplier: "Alle Lieferanten",
      bomFilterCategory: "Alle Kategorien",
      bomSearchPlaceholder: "BOM durchsuchen: Artikelnummer, Lieferant, Gerät (-X434), Beschreibung...",
      bomAmountLabel: "Menge im Fahrzeug:",
      bomSupplierLabel: "Lieferant / Hersteller:",
      bomCategoryLabel: "Kategorie:",
      bomDeviceLabel: "Verwendet im Gerät:",
      bomRelatedTerminals: "Passende Gegenstecker / Kontakte (aus BOM):",
      bomUploadPhoto: "📷 Foto hinzufügen / ändern",
      bomPastePhotoHelp: "Aus Zwischenablage einfügen (Strg+V) oder Datei auswählen",
      bomNoPhoto: "Kein Foto",
      bomNoPhotoSub: "Klicken zum Hinzufügen oder Einfügen",
      bomSavePhoto: "Foto in Wissensbasis speichern",
      bomPhotoSaved: "Foto in Wissensbasis gespeichert."
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

// ── SŁOWNIK FRAZ WIELOWYRAZOWYCH (Exact Multi-Word Technical Phrases) ──
const PHRASE_SYNONYMS = [
  {
    pl: ["włącznik główny", "wyłącznik główny", "odłącznik główny", "główny włącznik", "główny wyłącznik", "hebel", "odłącznik akumulatora"],
    en: ["main switch", "master switch", "battery master switch", "battery isolator", "isolator switch"]
  },
  {
    pl: ["brak masy", "zwarcie", "brak zasilania", "utrata zasilania"],
    en: ["ground fault", "short circuit", "no power", "loss of power", "dead circuit"]
  },
  {
    pl: ["przedział medyczny", "zabudowa medyczna", "przedział pacjenta"],
    en: ["medical compartment", "saloon", "patient area", "patient saloon"]
  },
  {
    pl: ["gniazdo 12v", "gniazdko 12v"],
    en: ["12v socket", "12v outlet", "12 volt socket"]
  },
  {
    pl: ["gniazdo 230v", "gniazdko 230v", "gniazdo 115v", "gniazdko 115v"],
    en: ["230v socket", "230v outlet", "115v socket", "115v outlet"]
  },
  {
    pl: ["drzwi przesuwne", "drzwi boczne"],
    en: ["sliding door", "side door"]
  },
  {
    pl: ["drzwi tylne"],
    en: ["rear door", "rear doors"]
  },
  {
    pl: ["lampa robocza", "oświetlenie pola pracy", "światła robocze"],
    en: ["scene light", "work light", "alley light"]
  }
];

// ── SŁOWNIK SYNONIMÓW TECHNICZNYCH DLA WYSZUKIWARKI (Bilingual Search Expansion) ──
const TECHNICAL_SYNONYMS = [
  // Przełączniki i sterowanie
  { pl: ["włącznik", "wyłącznik", "przełącznik", "przycisk", "odłącznik"], en: ["switch", "button", "toggle", "isolator", "pushbutton"] },
  { pl: ["główny", "główna", "główne", "głównego", "głównym"], en: ["main", "master", "primary"] },

  // Oświetlenie i elektryka
  { pl: ["światło", "światła", "oświetlenie", "lampa", "lampy", "led", "reflektor"], en: ["light", "lights", "lighting", "lamp", "lamps", "headlight", "beam"] },
  { pl: ["bezpiecznik", "bezpieczniki"], en: ["fuse", "fuses", "breaker", "fusebox"] },
  { pl: ["gniazdo", "gniazdko", "gniazda", "wtyczka"], en: ["socket", "outlet", "plug", "receptacle"] },
  { pl: ["przekaźnik", "przekaźniki"], en: ["relay", "relays"] },
  { pl: ["przewód", "przewody", "kabel", "kable", "wiązka"], en: ["wire", "wires", "cable", "cables", "harness", "loom"] },
  { pl: ["akumulator", "bateria", "zasilanie"], en: ["battery", "accumulator", "power", "supply"] },
  { pl: ["przetwornica", "falownik", "inwerter"], en: ["inverter", "converter", "transformer"] },
  { pl: ["zwarcie", "brak masy", "brak zasilania"], en: ["short circuit", "ground fault", "no power", "dead"] },

  // Elementy nadwozia i wnętrza karetki
  { pl: ["drzwi", "wrota", "klamka", "rygiel", "zamek"], en: ["door", "doors", "handle", "lock", "latch"] },
  { pl: ["stopień", "schodek", "stopnie"], en: ["step", "footstep", "steps"] },
  { pl: ["nosze", "stół noszy", "laweta"], en: ["stretcher", "cot", "ramp", "tray"] },
  { pl: ["fotel", "fotele", "siedzenie", "pas", "pasy"], en: ["seat", "chair", "belt", "seatbelt"] },
  { pl: ["szafka", "szuflada", "półka", "schowek"], en: ["cabinet", "drawer", "shelf", "compartment", "locker"] },
  { pl: ["wentylator", "dmuchawa", "nawiew", "wentylacja", "klimatyzacja", "ogrzewanie"], en: ["fan", "blower", "ventilation", "hvac", "ac", "air conditioning", "heating", "heater"] },
  { pl: ["syrena", "klakson", "głośnik"], en: ["siren", "horn", "speaker", "sounder"] },
  { pl: ["kogut", "belka", "flesz", "stroboskop"], en: ["lightbar", "beacon", "flash", "strobe", "grille light"] },
  { pl: ["przedział medyczny", "zabudowa"], en: ["saloon", "medical compartment", "patient area"] },
  { pl: ["szyba", "okno", "lusterko"], en: ["window", "glass", "mirror"] },
  { pl: ["czujnik", "sensor"], en: ["sensor", "probe", "detector"] },
  { pl: ["kamera", "rejestrator"], en: ["camera", "cctv", "recorder", "dashcam"] }
];

// ── AKTUALNY JĘZYK I FUNKCJE POMOCNICZE ──
let CURRENT_LANG = (typeof localStorage !== 'undefined' && localStorage.getItem('app_lang')) || 'pl';

function getLanguage() {
  return CURRENT_LANG;
}

if (typeof window !== 'undefined') {
  try {
    Object.defineProperty(window, 'isEn', {
      get: function() {
        return typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG === 'en';
      },
      configurable: true
    });
  } catch (e) {}
}

function setLanguage(lang) {
  if (lang !== 'pl' && lang !== 'en') lang = 'pl';
  CURRENT_LANG = lang;
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('app_lang', lang);
  }
  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.lang = lang;
  }

  // Zapisz preferencję do desktop_config.json przez opcjonalny endpoint
  try {
    if (typeof fetch === 'function') {
      fetch('/api/user-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      }).catch(() => {});
    }
  } catch (e) {}

  applyLanguage(lang);
}

function t(key, params = {}) {
  if (!key) return '';
  const keys = key.split('.');
  const activeDict = (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS[CURRENT_LANG]) || {};
  const plDict = (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS['pl']) || {};
  let val = keys.reduce((obj, k) => obj?.[k], activeDict)
         || keys.reduce((obj, k) => obj?.[k], plDict)
         || key;

  if (typeof val === 'string' && params) {
    for (const [pKey, pVal] of Object.entries(params)) {
      val = val.replaceAll(`{${pKey}}`, pVal);
    }
  }
  return val;
}

function translateCategory(categoryName, lang = CURRENT_LANG) {
  if (!categoryName) return '';
  if (lang === 'en' && typeof CATEGORY_MAP_PL_TO_EN !== 'undefined') {
    return CATEGORY_MAP_PL_TO_EN[categoryName] || categoryName;
  }
  return categoryName;
}

/**
 * Upraszcza wyraz obcinając typowe końcówki fleksyjne w języku polskim i angielskim.
 */
function stemWord(w) {
  if (!w || w.length <= 3) return w;
  return w.replace(/(ego|emu|ami|ach|ów|em|ie|ym|ych|om|owi|e|a|y|o|u|i|s|es|ed|ing)$/i, '');
}

/**
 * Inteligentna funkcja dopasowania wyszukiwarki:
 * 1. Zapewnia logikę koniunkcji (AND): przy zapytaniu wielowyrazowym (np. "włącznik główny")
 *    każde słowo musi być spełnione w rekordzie (poprzez to słowo, jego odmianę lub synonim).
 * 2. Obsługuje całe frazy idiomatyczne (np. "włącznik główny" <-> "main switch").
 * 3. Eliminuje szum (nie zwraca innych włączników, jeśli szukano głównego).
 */
function matchSearchQuery(haystack, query) {
  if (!query) return true;
  const hay = String(haystack || '').toLowerCase();
  const q = String(query || '').toLowerCase().trim();

  // 1. Bezpośrednie dopasowanie frazy
  if (hay.includes(q)) return true;

  // 2. Frazy wielowyrazowe (Phrase Synonyms)
  for (const group of PHRASE_SYNONYMS) {
    const inPl = group.pl.some(p => p === q || q.includes(p));
    const inEn = group.en.some(p => p === q || q.includes(p));
    if (inPl || inEn) {
      if (group.pl.some(p => hay.includes(p)) || group.en.some(p => hay.includes(p))) {
        return true;
      }
    }
  }

  // 3. Wielowyrazowe zapytanie: każde słowo z zapytania musi wystąpić w rekordzie (koniunkcja AND)
  const words = q.split(/\s+/).filter(w => w.length > 0);
  if (words.length > 1) {
    return words.every(word => {
      const wStem = stemWord(word);
      const syns = new Set([word, wStem]);

      for (const group of TECHNICAL_SYNONYMS) {
        if (group.pl.some(p => p === word || p.startsWith(wStem)) || group.en.some(e => e === word || e.startsWith(wStem))) {
          group.pl.forEach(p => { syns.add(p); syns.add(stemWord(p)); });
          group.en.forEach(e => { syns.add(e); });
        }
      }

      // Sprawdzenie czy w rekordzie znajduje się choć jeden synonim/rdzeń tego konkretnego słowa
      return Array.from(syns).some(syn => hay.includes(syn));
    });
  }

  // 4. Pojedyncze słowo (z synonimami)
  const wStem = stemWord(q);
  const syns = new Set([q, wStem]);
  for (const group of TECHNICAL_SYNONYMS) {
    if (group.pl.some(p => p === q || p.startsWith(wStem)) || group.en.some(e => e === q || e.startsWith(wStem))) {
      group.pl.forEach(p => { syns.add(p); syns.add(stemWord(p)); });
      group.en.forEach(e => { syns.add(e); });
    }
  }

  // Rozszerz o przetłumaczone kategorie
  for (const [pl, en] of Object.entries(CATEGORY_MAP_PL_TO_EN)) {
    if (q === pl.toLowerCase() || q === en.toLowerCase()) {
      syns.add(pl.toLowerCase());
      syns.add(en.toLowerCase());
    }
  }

  return Array.from(syns).some(syn => hay.includes(syn));
}

// Dla wstecznej kompatybilności
function expandSearchQuery(query) {
  if (!query) return [];
  const q = query.toLowerCase().trim();
  const terms = new Set([q]);

  for (const group of TECHNICAL_SYNONYMS) {
    const matchedEn = group.en.some(word => q === word || word.includes(q));
    const matchedPl = group.pl.some(word => q === word || word.includes(q));

    if (matchedEn || matchedPl) {
      group.pl.forEach(w => terms.add(w.toLowerCase()));
      group.en.forEach(w => terms.add(w.toLowerCase()));
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
