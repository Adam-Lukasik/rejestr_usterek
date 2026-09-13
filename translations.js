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
      bomNoPhoto: "Brak zdjęcia",
      bomNoPhotoSub: "Kliknij, aby dodać lub wkleić zdjęcie",
      bomSavePhoto: "Zapisz zdjęcie w Bazie wiedzy",
      bomPhotoSaved: "Zapisano zdjęcie w Bazie wiedzy.",
      navSummaries: "Spis Złączy & Bezp.",
      summariesTitle: "Zestawienia Zuken E3 — Spis Złączy, Bezpieczników i Przekaźników (PS)",
      summariesSubtitle: "Automatycznie wyodrębniane z plików XLSX (BOM i Connection) dla wybranego projektu PS",
      selectProject: "Wybierz projekt PS:",
      btnGenerateSummaries: "⚡ Wygeneruj z XLSX",
      tabConnectors: "🔌 Spis złączy & Pinout",
      tabFuses: "🛡️ Zestaw bezpieczników",
      tabRelays: "🔀 Zestaw przekaźników",
      btnExportCsv: "📥 Pobierz CSV",
      btnPrint: "🖨️ Drukuj",
      searchConnectors: "Szukaj złącza (np. X431, Molex, TWR-X129)...",
      searchFuses: "Szukaj bezpiecznika (np. 5A, F49, centralny zamek)...",
      searchRelays: "Szukaj przekaźnika (np. AUX IGN, D+, Hella, K1)...",
      systemFilterAll: "Wszystkie systemy",
      fuseFilterAll: "Wszystkie typy bezpieczników",
      pinoutColPin: "Pin",
      pinoutColSignal: "Sygnał / Obwód",
      pinoutColWire: "Przewód",
      pinoutColColor: "Kolor",
      pinoutColCross: "Przekrój",
      pinoutColTarget: "Cel połączenia",
      pinoutColTargetDesc: "Opis urządzenia docelowego",
      noSummariesFound: "Brak wygenerowanych zestawień dla tego projektu. Kliknij 'Wygeneruj z XLSX', aby utworzyć spis.",
      generatingWait: "Trwa analizowanie plików XLSX i generowanie zestawień..."
    },
    ui: {
      common: {
        cancel: "Anuluj",
        save: "Zapisz",
        back: "◄ Wróć",
        close: "Zamknij",
        closeEsc: "✕ Zamknij (ESC)",
        edit: "Edytuj",
        delete: "Usuń",
        detailsArrow: "Szczegóły →",
        backToList: "✕ Wróć do listy"
      },
      form: {
        heading: "Nowe zgłoszenie usterki",
        subtitlePage: "Wprowadź dane z kontroli jakości linii produkcyjnej",
        projectAuto: "Projekt PS * <span>(wybór automatycznie uzupełnia klienta i model)</span>",
        btnNewProject: "＋ Nowy projekt PS",
        btnMultiPs: "+ Wiele PS",
        clientStar: "Klient *",
        btnNewClient: "＋ Nowy klient",
        baseModel: "Model auta bazowego *",
        btnNewModel: "＋ Nowy model",
        defectType: "Typ usterki *",
        btnNewType: "＋ Nowy typ",
        vinOptional: "VIN / Nr nadwozia <span>(opcjonalnie)</span>",
        elementOptional: "Element / urządzenie <span>(opcjonalnie)</span>",
        elementPh: "np. gniazdo 230V, wiązka drzwi lewych, HVAC...",
        problemStar: "Opis problemu *",
        problemPh: "Dokładny opis zaobserwowanej nieprawidłowości...",
        photosLabel: "Zdjęcia problemu (max 6) <span>— wklejaj ze schowka Ctrl+V</span>",
        dropClick: "Kliknij, aby wybrać zdjęcie z dysku",
        dropOr: "lub przeciągnij zdjęcie / wklej zrzut ekranu (Ctrl+V)",
        pasteBtn: "📋 Wklej ze schowka",
        attachLabel: "Załączniki (PDF, Raporty VSWR) <span>(opcjonalnie)</span>",
        addDocBtn: "📎 Dodaj dokument z dysku",
        btnSaveCheck: "✓ Zapisz usterkę",
        btnSaveFirst: "💡 Zapisz usterkę i dodaj pierwszy wariant naprawy"
      },
      projects: {
        pageTitle: "Baza Projektów (PS)",
        pageSubtitle: "Każdy projekt PS ma przypisanego jednego klienta i jeden bazowy model pojazdu.",
        btnNew: "+ Nowy Projekt PS",
        searchPh: "Filtruj projekty PS...",
        thActions: "Akcje",
        empty: "Brak zdefiniowanych projektów PS. Kliknij „+ Nowy Projekt PS”.",
        dblTitle: "Kliknij dwukrotnie, aby edytować projekt PS",
        modalTitle: "Projekt PS",
        modalNew: "Nowy Projekt PS",
        modalEdit: "Edycja Projektu: {v}",
        psNumber: "Numer projektu PS * (np. PS011871)",
        addClientTitle: "Dodaj nowego klienta do listy",
        addClientLabel: "Dodaj nowego klienta:",
        clientNamePh: "Wpisz nazwę klienta...",
        addModelTitle: "Dodaj nowy model do listy",
        addModelLabel: "Dodaj nowy model auta:",
        modelNamePh: "np. MAN TGE 2024, Mercedes Sprinter...",
        saveProject: "Zapisz projekt",
        selectClient: "— Wybierz klienta —",
        selectModel: "— Wybierz model —",
        addNewClient: "➕ Dodaj nowego klienta...",
        addNewModel: "➕ Dodaj nowy model..."
      },
      dict: {
        pageTitle: "Zarządzanie Słownikami",
        listClients: "Lista Klientów",
        listModels: "Modele Aut Bazowych",
        listTypes: "Typy Usterek",
        newClientPh: "np. EOE - East of England Ambulance Service",
        newModelPh: "Nazwa nowego modelu...",
        newTypePh: "Nazwa nowego typu usterki...",
        btnAdd: "+ Dodaj",
        btnRename: "Zmień",
        added: "Pozycja dodana!",
        updated: "Zaktualizowano",
        removed: "Pozycja usunięta",
        newNamePrompt: "Nowa nazwa:",
        confirmDeleteItem: "Usunąć pozycję \"{v}\"?",
        promptNewType: "Wpisz nazwę nowego typu usterki (np. \"Zabudowa meblowa\", \"Ogrzewanie\"):",
        promptNewClient: "Wpisz nazwę nowego klienta (np. \"LAS - London Ambulance Service\"):",
        promptNewModel: "Wpisz nazwę nowego modelu pojazdu (np. \"MAN TGE 2025\", \"Mercedes Sprinter 2024\"):",
        addedType: "Dodano nowy typ usterki: {v}",
        addedClient: "Dodano nowego klienta: {v}",
        addedModel: "Dodano nowy model: {v}",
        alreadyExistsType: "Typ \"{v}\" jest już na liście i został wybrany.",
        alreadyExistsClient: "Klient \"{v}\" jest już na liście i został wybrany.",
        alreadyExistsModel: "Model \"{v}\" jest już na liście i został wybrany.",
        saveError: "Błąd zapisu: {v}"
      },
      users: {
        pageTitle: "Użytkownicy i Uprawnienia",
        pageSubtitle: "Zarządzaj kontami techników i administratorów w systemie.",
        btnNew: "+ Nowy Użytkownik",
        thLogin: "Login",
        thFullName: "Imię i Nazwisko",
        thContact: "Kontakt",
        mustChangeBadge: "⚠️ Wymaga zmiany hasła",
        active: "Aktywny",
        inactive: "Nieaktywny",
        pwBtn: "Hasło",
        adminOnly: "Wymagane uprawnienia administratora.",
        dblTitle: "Kliknij dwukrotnie, aby edytować użytkownika",
        modalNew: "Nowy Użytkownik",
        modalEdit: "Edycja użytkownika: {v}",
        username: "Login *",
        usernamePh: "np. j.kowalski",
        fullName: "Imię i Nazwisko *",
        fullNamePh: "np. Jan Kowalski",
        emailLabel: "Adres e-mail (do odzyskiwania hasła)",
        emailPh: "np. jan.kowalski@gmail.com",
        phoneLabel: "Numer telefonu (opcjonalny)",
        phonePh: "np. 600 100 200",
        role: "Rola",
        roleTech: "Technik (zgłoszenia i naprawy)",
        roleAdmin: "Administrator (pełny dostęp)",
        roleViewer: "Podgląd (tylko odczyt)",
        initialPw: "Hasło początkowe",
        pwHintNew: "(wymagane min. 4 znaki)",
        pwHintEdit: "(zostaw puste aby nie zmieniać)",
        pwPh: "Wpisz hasło...",
        mustChange: "Wymuś zmianę hasła przy pierwszym logowaniu",
        saveUser: "Zapisz użytkownika",
        quickTitle: "🔄 Przełącz technika na tym stanowisku",
        quickDesc: "Wybierz użytkownika, aby natychmiast przypisywać nowe zgłoszenia i naprawy do Twojego profilu:"
      },
      backup: {
        pageTitle: "Kopie Zapasowe i Narzędzia Bazy",
        walTitle: "💾 Przygotuj bazę do skopiowania na pendrive (Scal plik rejestr_usterek.db)",
        walDesc: "Wymusza natychmiastowe zrzucenie wszystkich bieżących transakcji i wpisów (bufora WAL) bezpośrednio do głównego pliku <code>rejestr_usterek.db</code>.",
        walNote: "Dzięki temu plik <code>rejestr_usterek.db</code> jest w 100% kompletny i możesz go bezpiecznie skopiować do domu.",
        walBtn: "Scal plik bazy teraz",
        exportTitle: "Pobierz kopię zapasową (Backup JSON)",
        exportDesc: "Eksportuje całą bazę usterek, słowników i powiązań do pliku JSON.",
        exportBtn: "⬇ Pobierz kopię JSON",
        importTitle: "Wczytaj kopię zapasową (Import JSON)",
        importDesc: "Wgraj dane z pliku JSON (scal z obecnymi danymi lub zastąp bazę).",
        importMerge: "Scal z bieżącą bazą",
        importReplace: "Zastąp całą bazę",
        optTitle: "Optymalizacja zdjęć i VACUUM bazy",
        optDesc: "Automatycznie kompresuje zdjęcia archiwalne i zmniejsza rozmiar pliku SQLite na dysku.",
        optBtn: "⚡ Uruchom optymalizację"
      },
      auth: {
        loginSubtitle: "Zaloguj się, aby uzyskać dostęp",
        username: "Login",
        usernamePh: "Wpisz login...",
        password: "Hasło",
        passwordPh: "Wpisz hasło...",
        forgot: "Nie pamiętasz hasła?",
        loginBtn: "Zaloguj się",
        helpLine: "W razie problemów z programem lub kontem:",
        authorLabel: "Autor:",
        resetTitle: "Resetowanie hasła",
        resetDesc: "Wpisz swój <strong>login</strong> lub <strong>adres e-mail</strong> przypisany do Twojego konta. Prześlemy Ci 6-cyfrowy kod weryfikacyjny.",
        identifier: "Login lub E-mail *",
        identifierPh: "np. j.kowalski lub jan@gmail.com",
        backToLogin: "Wróć do logowania",
        sendCode: "Wyślij kod weryfikacyjny ►",
        step2Desc: "Wprowadź 6-cyfrowy kod weryfikacyjny (wysłany na e-mail) oraz ustaw nowe hasło.",
        code: "Kod weryfikacyjny PIN (6 cyfr) *",
        newPw: "Nowe hasło (min. 4 znaki) *",
        newPwPh: "Wpisz nowe hasło...",
        confirmPw: "Powtórz nowe hasło *",
        confirmPwPh: "Powtórz nowe hasło...",
        saveNewPw: "✓ Zapisz nowe hasło",
        forceTitle: "Wymagana zmiana hasła",
        forceDesc: "To Twoje pierwsze logowanie lub hasło tymczasowe. Ustaw własne, bezpieczne hasło, aby uzyskać dostęp do aplikacji.",
        forceSave: "Zapisz hasło i rozpocznij pracę"
      },
      multiPs: {
        title: "Wybór projektów (PS)",
        desc: "Zaznacz projekty, których dotyczy ta usterka:",
        filterPh: "Filtruj listę projektów...",
        customLabel: "Dodatkowy projekt PS (wpisz ręcznie, rozdziel przecinkami):",
        apply: "✓ Zastosuj wybrane"
      },
      lightbox: {
        title: "Podgląd zdjęcia",
        prev: "◄ Poprzednie",
        next: "Następne ►",
        download: "⬇ Pobierz",
        prevTitle: "Poprzednie zdjęcie (Strzałka w lewo)",
        nextTitle: "Następne zdjęcie (Strzałka w prawo)",
        dlTitle: "Pobierz zdjęcie na dysk",
        closeTitle: "Zamknij podgląd zdjęcia (ESC)"
      },
      zuken: {
        kpiConnSub: "Wszystkie wtyczki i gniazda wiązek",
        kpiFusesSub: "UNI, MIDI, MEGA i oprawki",
        kpiRelaysSub: "Styczniki, podstawy i obsada styków",
        kpiStatus: "📁 Status Bazy Wiedzy",
        statusChecking: "Sprawdzanie danych...",
        statusReady: "✓ Gotowe",
        statusGeneratedAt: "wygenerowano: {v}",
        statusNeedsGen: "⚠️ Wymaga wygenerowania z XLSX",
        noProjectSelected: "Brak wybranego projektu",
        sysLabel: "System:",
        sysAll: "Wszystkie",
        sysBox: "=BOX (Zabudowa)",
        sysCab: "=CAB (Kabina)",
        sysCha: "=CHA (Podwozie)",
        sysBom: "=BOM (Dach)",
        loadingConnectors: "Ładowanie złączy...",
        loadingFuses: "Ładowanie bezpieczników...",
        loadingRelays: "Ładowanie przekaźników...",
        loadingConnectorsLong: "Ładowanie złączy i pinoutów...",
        loadingFusesLong: "Ładowanie zestawu bezpieczników...",
        loadingRelaysLong: "Ładowanie zestawu przekaźników...",
        shownConnectors: "Wyświetlono {n} z {total} złączy",
        shownFuses: "Wyświetlono {n} z {total} bezpieczników",
        shownRelays: "Wyświetlono {n} z {total} przekaźników",
        emptyConnectors: "Brak złączy spełniających wybrane kryteria.",
        emptyFuses: "Brak bezpieczników spełniających wybrane kryteria.",
        emptyRelays: "Brak przekaźników spełniających wybrane kryteria.",
        errLoadConnectors: "Błąd ładowania złączy: {v}",
        errLoadFuses: "Błąd ładowania bezpieczników: {v}",
        errLoadRelays: "Błąd ładowania przekaźników: {v}",
        fuseColDevice: "Bezpiecznik",
        fuseColRatingType: "Prąd — Typ",
        fuseColWires: "Przewody & obwody zasilane",
        fuseExternalHarness: "wiązka {name} — w komplecie z urządzeniem",
        fuseColLocation: "Lokalizacja",
        fuseColBom: "Artykuł BOM & Producent",
        pinoutTargetFull: "Cel połączenia (Aparat:Pin)",
        wirePathTitle: "Ścieżka sygnału",
        wirePathJump: "Znajdź w spisie",
        wirePathClose: "Zamknij",
        pinCount: "{n} pinów",
        noBomCode: "Brak kodu w BOM",
        expandPinout: "Rozwiń pinout ({n}) ▼",
        collapsePinout: "Zwiń pinout ▲",
        expandPinoutShort: "Rozwiń pinout ▼",
        relayFuncDefault: "Przekaźnik",
        relayColPin: "Pin / Styk",
        relayColRole: "Rola stykowa",
        relayColSignal: "Sygnał",
        relayColWire: "Przewód",
        relayColTarget: "Drugi koniec przewodu",
        relayColCross: "Przekrój",
        relayColLength: "Długość",
        relaySocketCaption: "Gniazdo widziane z góry · gn. = pin gniazda",
        relayNoContacts: "Brak bezpośrednich połączeń styków w pliku połączeń.",
        relayRoleCoil: "Cewka (85/86)",
        relayRoleCommon: "Zasilanie (30)",
        relayRoleNO: "Styk zwierny (87)",
        relayRoleNC: "Styk rozwierny (87A)",
        relayRoleWorking: "Styk roboczy",
        selectPsFirst: "Wybierz projekt PS z listy.",
        generating: "Generowanie...",
        analyzingXlsx: "Trwa analizowanie plików XLSX dla {ps}...",
        errGenerate: "Błąd generowania zestawień: {v}",
        errLoadProjects: "Błąd ładowania projektów PS: {v}",
        csvDownloading: "Pobieranie pliku CSV ({type}) dla {ps}...",
        unknownGenError: "Nieznany błąd generowania",
        generatedFor: "Wygenerowano zestawienia dla {ps}.",
        csvExportTitle: "Pobierz aktualną tabelę w formacie CSV z polskimi znakami (dla Excela)",
        printTitle: "Drukuj zestawienie",
        componentPhoto: "Zdjęcie komponentu",
        changePhoto: "Zmień zdjęcie",
        articleLabel: "Artykuł katalogowy:",
        pasteCtrlV1: "Wciśnij",
        pasteCtrlV2: ", aby wkleić zdjęcie ze schowka",
        orClickFile: "lub kliknij tutaj, aby wybrać plik (JPG, PNG, WebP) z dysku",
        offlineFooter: "Lokalny silnik Zuken E3 & Raport BOM (100% Offline)"
      }
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
      bomNoPhoto: "No photo",
      bomNoPhotoSub: "Click to add or paste a photo",
      bomSavePhoto: "Save Photo to Knowledge Base",
      bomPhotoSaved: "Photo saved in Knowledge Base.",
      navSummaries: "Connectors & Fuses",
      summariesTitle: "Zuken E3 Technical Lists — Connectors, Fuses & Relays (PS)",
      summariesSubtitle: "Automatically extracted from XLSX files (BOM and Connection) for the selected PS project",
      selectProject: "Select PS project:",
      btnGenerateSummaries: "⚡ Generate from XLSX",
      tabConnectors: "🔌 Connectors & Pinout",
      tabFuses: "🛡️ Fuses",
      tabRelays: "🔀 Relays",
      btnExportCsv: "📥 Download CSV",
      btnPrint: "🖨️ Print",
      searchConnectors: "Search connector (e.g. X431, Molex, TWR-X129)...",
      searchFuses: "Search fuse (e.g. 5A, F49, central lock)...",
      searchRelays: "Search relay (e.g. AUX IGN, D+, Hella, K1)...",
      systemFilterAll: "All systems",
      fuseFilterAll: "All fuse types",
      pinoutColPin: "Pin",
      pinoutColSignal: "Signal / Circuit",
      pinoutColWire: "Wire",
      pinoutColColor: "Color",
      pinoutColCross: "Cross-section",
      pinoutColTarget: "Destination",
      pinoutColTargetDesc: "Target Device Description",
      noSummariesFound: "No generated summaries found for this project. Click 'Generate from XLSX' to create them.",
      generatingWait: "Analyzing XLSX files and compiling lists..."
    },
    ui: {
      common: {
        cancel: "Cancel",
        save: "Save",
        back: "◄ Back",
        close: "Close",
        closeEsc: "✕ Close (ESC)",
        edit: "Edit",
        delete: "Delete",
        detailsArrow: "Details →",
        backToList: "✕ Back to list"
      },
      form: {
        heading: "New defect report",
        subtitlePage: "Enter the production line quality control data",
        projectAuto: "PS Project * <span>(selection auto-fills customer and model)</span>",
        btnNewProject: "＋ New PS project",
        btnMultiPs: "+ Multiple PS",
        clientStar: "Client *",
        btnNewClient: "＋ New client",
        baseModel: "Base vehicle model *",
        btnNewModel: "＋ New model",
        defectType: "Defect type *",
        btnNewType: "＋ New type",
        vinOptional: "VIN / Body number <span>(optional)</span>",
        elementOptional: "Element / device <span>(optional)</span>",
        elementPh: "e.g. 230V socket, left door harness, HVAC...",
        problemStar: "Problem description *",
        problemPh: "Detailed description of the observed defect...",
        photosLabel: "Problem photos (max 6) <span>— paste from clipboard Ctrl+V</span>",
        dropClick: "Click to choose a photo from disk",
        dropOr: "or drag a photo / paste a screenshot (Ctrl+V)",
        pasteBtn: "📋 Paste from clipboard",
        attachLabel: "Attachments (PDF, VSWR reports) <span>(optional)</span>",
        addDocBtn: "📎 Add document from disk",
        btnSaveCheck: "✓ Save defect",
        btnSaveFirst: "💡 Save defect and add first repair variant"
      },
      projects: {
        pageTitle: "Projects Database (PS)",
        pageSubtitle: "Each PS project has one assigned client and one base vehicle model.",
        btnNew: "+ New PS Project",
        searchPh: "Filter PS projects...",
        thActions: "Actions",
        empty: "No PS projects defined. Click \"+ New PS Project\".",
        dblTitle: "Double-click to edit the PS project",
        modalTitle: "PS Project",
        modalNew: "New PS Project",
        modalEdit: "Edit Project: {v}",
        psNumber: "PS project number * (e.g. PS011871)",
        addClientTitle: "Add a new client to the list",
        addClientLabel: "Add new client:",
        clientNamePh: "Enter client name...",
        addModelTitle: "Add a new model to the list",
        addModelLabel: "Add new vehicle model:",
        modelNamePh: "e.g. MAN TGE 2024, Mercedes Sprinter...",
        saveProject: "Save project",
        selectClient: "— Select client —",
        selectModel: "— Select model —",
        addNewClient: "➕ Add new client...",
        addNewModel: "➕ Add new model..."
      },
      dict: {
        pageTitle: "Dictionary Management",
        listClients: "Client List",
        listModels: "Base Vehicle Models",
        listTypes: "Defect Types",
        newClientPh: "e.g. EOE - East of England Ambulance Service",
        newModelPh: "New model name...",
        newTypePh: "New defect type name...",
        btnAdd: "+ Add",
        btnRename: "Rename",
        added: "Item added!",
        updated: "Updated",
        removed: "Item removed",
        newNamePrompt: "New name:",
        confirmDeleteItem: "Delete item \"{v}\"?",
        promptNewType: "Enter a new defect type name (e.g. \"Furniture conversion\", \"Heating\"):",
        promptNewClient: "Enter a new client name (e.g. \"LAS - London Ambulance Service\"):",
        promptNewModel: "Enter a new vehicle model name (e.g. \"MAN TGE 2025\", \"Mercedes Sprinter 2024\"):",
        addedType: "New defect type added: {v}",
        addedClient: "New client added: {v}",
        addedModel: "New model added: {v}",
        alreadyExistsType: "Type \"{v}\" is already on the list and has been selected.",
        alreadyExistsClient: "Client \"{v}\" is already on the list and has been selected.",
        alreadyExistsModel: "Model \"{v}\" is already on the list and has been selected.",
        saveError: "Save error: {v}"
      },
      users: {
        pageTitle: "Users & Permissions",
        pageSubtitle: "Manage technician and administrator accounts in the system.",
        btnNew: "+ New User",
        thLogin: "Username",
        thFullName: "Full Name",
        thContact: "Contact",
        mustChangeBadge: "⚠️ Password change required",
        active: "Active",
        inactive: "Inactive",
        pwBtn: "Password",
        adminOnly: "Administrator privileges required.",
        dblTitle: "Double-click to edit the user",
        modalNew: "New User",
        modalEdit: "Edit user: {v}",
        username: "Username *",
        usernamePh: "e.g. j.smith",
        fullName: "Full Name *",
        fullNamePh: "e.g. John Smith",
        emailLabel: "E-mail address (for password recovery)",
        emailPh: "e.g. john.smith@gmail.com",
        phoneLabel: "Phone number (optional)",
        phonePh: "e.g. 600 100 200",
        role: "Role",
        roleTech: "Technician (reports & repairs)",
        roleAdmin: "Administrator (full access)",
        roleViewer: "Viewer (read-only)",
        initialPw: "Initial password",
        pwHintNew: "(required, min. 4 characters)",
        pwHintEdit: "(leave empty to keep unchanged)",
        pwPh: "Enter password...",
        mustChange: "Force password change at first login",
        saveUser: "Save user",
        quickTitle: "🔄 Switch technician on this workstation",
        quickDesc: "Select a user to immediately assign new reports and repairs to your profile:"
      },
      backup: {
        pageTitle: "Backups & Database Tools",
        walTitle: "💾 Prepare the database for USB copy (Merge rejestr_usterek.db file)",
        walDesc: "Forces an immediate flush of all pending transactions and entries (WAL buffer) directly into the main <code>rejestr_usterek.db</code> file.",
        walNote: "This makes the <code>rejestr_usterek.db</code> file 100% complete and safe to copy.",
        walBtn: "Merge database file now",
        exportTitle: "Download backup (Backup JSON)",
        exportDesc: "Exports the entire defect, dictionary and relationship database to a JSON file.",
        exportBtn: "⬇ Download JSON backup",
        importTitle: "Restore backup (JSON Import)",
        importDesc: "Load data from a JSON file (merge with current data or replace the database).",
        importMerge: "Merge with current database",
        importReplace: "Replace entire database",
        optTitle: "Photo optimization & database VACUUM",
        optDesc: "Automatically compresses archived photos and reduces the SQLite file size on disk.",
        optBtn: "⚡ Run optimization"
      },
      auth: {
        loginSubtitle: "Sign in to get access",
        username: "Username",
        usernamePh: "Enter username...",
        password: "Password",
        passwordPh: "Enter password...",
        forgot: "Forgot password?",
        loginBtn: "Sign in",
        helpLine: "In case of problems with the app or your account:",
        authorLabel: "Author:",
        resetTitle: "Password Reset",
        resetDesc: "Enter your <strong>username</strong> or <strong>e-mail address</strong> assigned to your account. We will send you a 6-digit verification code.",
        identifier: "Username or E-mail *",
        identifierPh: "e.g. j.smith or john@gmail.com",
        backToLogin: "Back to sign in",
        sendCode: "Send verification code ►",
        step2Desc: "Enter the 6-digit verification code (sent by e-mail) and set a new password.",
        code: "Verification PIN code (6 digits) *",
        newPw: "New password (min. 4 characters) *",
        newPwPh: "Enter new password...",
        confirmPw: "Repeat new password *",
        confirmPwPh: "Repeat new password...",
        saveNewPw: "✓ Save new password",
        forceTitle: "Password Change Required",
        forceDesc: "This is your first sign-in or a temporary password. Set your own secure password to access the application.",
        forceSave: "Save password and start working"
      },
      multiPs: {
        title: "Select Projects (PS)",
        desc: "Select the projects this defect applies to:",
        filterPh: "Filter the project list...",
        customLabel: "Additional PS project (enter manually, comma-separated):",
        apply: "✓ Apply selected"
      },
      lightbox: {
        title: "Photo preview",
        prev: "◄ Previous",
        next: "Next ►",
        download: "⬇ Download",
        prevTitle: "Previous photo (Left arrow)",
        nextTitle: "Next photo (Right arrow)",
        dlTitle: "Download photo to disk",
        closeTitle: "Close photo preview (ESC)"
      },
      zuken: {
        kpiConnSub: "All harness plugs and sockets",
        kpiFusesSub: "UNI, MIDI, MEGA and holders",
        kpiRelaysSub: "Contactors, sockets and contact assignment",
        kpiStatus: "📁 Knowledge Base Status",
        statusChecking: "Checking data...",
        statusReady: "✓ Ready",
        statusGeneratedAt: "generated: {v}",
        statusNeedsGen: "⚠️ Requires generation from XLSX",
        noProjectSelected: "No project selected",
        sysLabel: "System:",
        sysAll: "All",
        sysBox: "=BOX (Body)",
        sysCab: "=CAB (Cab)",
        sysCha: "=CHA (Chassis)",
        sysBom: "=BOM (Roof)",
        loadingConnectors: "Loading connectors...",
        loadingFuses: "Loading fuses...",
        loadingRelays: "Loading relays...",
        loadingConnectorsLong: "Loading connectors and pinouts...",
        loadingFusesLong: "Loading fuse set...",
        loadingRelaysLong: "Loading relay set...",
        shownConnectors: "Showing {n} of {total} connectors",
        shownFuses: "Showing {n} of {total} fuses",
        shownRelays: "Showing {n} of {total} relays",
        emptyConnectors: "No connectors match the selected criteria.",
        emptyFuses: "No fuses match the selected criteria.",
        emptyRelays: "No relays match the selected criteria.",
        errLoadConnectors: "Connector loading error: {v}",
        errLoadFuses: "Fuse loading error: {v}",
        errLoadRelays: "Relay loading error: {v}",
        fuseColDevice: "Fuse",
        fuseColRatingType: "Rating — Type",
        fuseColWires: "Wires & supplied circuits",
        fuseExternalHarness: "{name} harness — supplied with the device",
        fuseColLocation: "Location",
        fuseColBom: "BOM article & Manufacturer",
        pinoutTargetFull: "Connection target (Device:Pin)",
        wirePathTitle: "Signal path",
        wirePathJump: "Find in list",
        wirePathClose: "Close",
        pinCount: "{n} pins",
        noBomCode: "No BOM code",
        expandPinout: "Expand pinout ({n}) ▼",
        collapsePinout: "Collapse pinout ▲",
        expandPinoutShort: "Expand pinout ▼",
        relayFuncDefault: "Relay",
        relayColPin: "Pin / Contact",
        relayColRole: "Contact role",
        relayColSignal: "Signal",
        relayColWire: "Wire",
        relayColTarget: "Other end of wire",
        relayColCross: "Cross-section",
        relayColLength: "Length",
        relaySocketCaption: "Socket top view · gn. = socket pin",
        relayNoContacts: "No direct contact connections found in the connections file.",
        relayRoleCoil: "Coil (85/86)",
        relayRoleCommon: "Supply (30)",
        relayRoleNO: "NO contact (87)",
        relayRoleNC: "NC contact (87A)",
        relayRoleWorking: "Working contact",
        selectPsFirst: "Select a PS project from the list.",
        generating: "Generating...",
        analyzingXlsx: "Analyzing XLSX files for {ps}...",
        errGenerate: "Summary generation error: {v}",
        errLoadProjects: "PS projects loading error: {v}",
        csvDownloading: "Downloading CSV file ({type}) for {ps}...",
        unknownGenError: "Unknown generation error",
        generatedFor: "Summaries generated for {ps}.",
        csvExportTitle: "Download the current table as CSV (Excel-friendly)",
        printTitle: "Print summary",
        componentPhoto: "Component photo",
        changePhoto: "Change photo",
        articleLabel: "Catalogue article:",
        pasteCtrlV1: "Press",
        pasteCtrlV2: "to paste a photo from the clipboard",
        orClickFile: "or click here to choose a file (JPG, PNG, WebP) from disk",
        offlineFooter: "Local Zuken E3 engine & BOM Report (100% Offline)"
      }
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
      bomNoPhoto: "Kein Foto",
      bomNoPhotoSub: "Klicken zum Hinzufügen oder Einfügen",
      bomSavePhoto: "Foto in Wissensbasis speichern",
      bomPhotoSaved: "Foto in Wissensbasis gespeichert.",
      navSummaries: "Stecker & Sicherungen",
      summariesTitle: "Zuken E3 Technische Listen — Stecker, Sicherungen & Relais (PS)",
      summariesSubtitle: "Automatisch aus XLSX-Dateien (BOM und Connection) für das ausgewählte PS-Projekt extrahiert",
      selectProject: "PS-Projekt wählen:",
      btnGenerateSummaries: "⚡ Aus XLSX generieren",
      tabConnectors: "🔌 Stecker & Pinbelegung",
      tabFuses: "🛡️ Sicherungen",
      tabRelays: "🔀 Relais",
      btnExportCsv: "📥 CSV herunterladen",
      btnPrint: "🖨️ Drucken",
      searchConnectors: "Stecker suchen (z. B. X431, Molex, TWR-X129)...",
      searchFuses: "Sicherung suchen (z. B. 5A, F49, Zentralverriegelung)...",
      searchRelays: "Relais suchen (z. B. AUX IGN, D+, Hella, K1)...",
      systemFilterAll: "Alle Systeme",
      fuseFilterAll: "Alle Sicherungstypen",
      pinoutColPin: "Pin",
      pinoutColSignal: "Signal / Stromkreis",
      pinoutColWire: "Leitung",
      pinoutColColor: "Farbe",
      pinoutColCross: "Querschnitt",
      pinoutColTarget: "Ziel",
      pinoutColTargetDesc: "Beschreibung des Zielgeräts",
      noSummariesFound: "Keine generierten Übersichten für dieses Projekt gefunden. Klicken Sie auf 'Aus XLSX generieren'.",
      generatingWait: "XLSX-Dateien werden analysiert und Listen erstellt..."
    },
    ui: {
      common: {
        cancel: "Abbrechen",
        save: "Speichern",
        back: "◄ Zurück",
        close: "Schließen",
        closeEsc: "✕ Schließen (ESC)",
        edit: "Bearbeiten",
        delete: "Löschen",
        detailsArrow: "Details →",
        backToList: "✕ Zurück zur Liste"
      },
      form: {
        heading: "Neue Mängelmeldung",
        subtitlePage: "Geben Sie die Daten aus der Qualitätskontrolle der Produktionslinie ein",
        projectAuto: "PS-Projekt * <span>(Auswahl füllt Kunde und Modell automatisch aus)</span>",
        btnNewProject: "＋ Neues PS-Projekt",
        btnMultiPs: "+ Mehrere PS",
        clientStar: "Kunde *",
        btnNewClient: "＋ Neuer Kunde",
        baseModel: "Basisfahrzeugmodell *",
        btnNewModel: "＋ Neues Modell",
        defectType: "Mangeltyp *",
        btnNewType: "＋ Neuer Typ",
        vinOptional: "FIN / Karosserienr. <span>(optional)</span>",
        elementOptional: "Bauteil / Gerät <span>(optional)</span>",
        elementPh: "z. B. 230V-Steckdose, Leitungssatz Tür links, HVAC...",
        problemStar: "Problembeschreibung *",
        problemPh: "Genaue Beschreibung der festgestellten Abweichung...",
        photosLabel: "Fotos des Mangels (max. 6) <span>— aus Zwischenablage einfügen Strg+V</span>",
        dropClick: "Klicken, um ein Foto vom Datenträger zu wählen",
        dropOr: "oder Foto hierher ziehen / Screenshot einfügen (Strg+V)",
        pasteBtn: "📋 Aus Zwischenablage einfügen",
        attachLabel: "Anhänge (PDF, VSWR-Berichte) <span>(optional)</span>",
        addDocBtn: "📎 Dokument vom Datenträger hinzufügen",
        btnSaveCheck: "✓ Mangel speichern",
        btnSaveFirst: "💡 Mangel speichern und erste Reparaturvariante hinzufügen"
      },
      projects: {
        pageTitle: "Projektdatenbank (PS)",
        pageSubtitle: "Jedes PS-Projekt hat einen zugewiesenen Kunden und ein Basisfahrzeugmodell.",
        btnNew: "+ Neues PS-Projekt",
        searchPh: "PS-Projekte filtern...",
        thActions: "Aktionen",
        empty: "Keine PS-Projekte definiert. Klicken Sie auf „+ Neues PS-Projekt“.",
        dblTitle: "Doppelklicken, um das PS-Projekt zu bearbeiten",
        modalTitle: "PS-Projekt",
        modalNew: "Neues PS-Projekt",
        modalEdit: "Projekt bearbeiten: {v}",
        psNumber: "PS-Projektnummer * (z. B. PS011871)",
        addClientTitle: "Neuen Kunden zur Liste hinzufügen",
        addClientLabel: "Neuen Kunden hinzufügen:",
        clientNamePh: "Kundenname eingeben...",
        addModelTitle: "Neues Modell zur Liste hinzufügen",
        addModelLabel: "Neues Fahrzeugmodell hinzufügen:",
        modelNamePh: "z. B. MAN TGE 2024, Mercedes Sprinter...",
        saveProject: "Projekt speichern",
        selectClient: "— Kunde wählen —",
        selectModel: "— Modell wählen —",
        addNewClient: "➕ Neuen Kunden hinzufügen...",
        addNewModel: "➕ Neues Modell hinzufügen..."
      },
      dict: {
        pageTitle: "Wörterbuchverwaltung",
        listClients: "Kundenliste",
        listModels: "Basisfahrzeugmodelle",
        listTypes: "Mangeltypen",
        newClientPh: "z. B. EOE - East of England Ambulance Service",
        newModelPh: "Name des neuen Modells...",
        newTypePh: "Name des neuen Mangeltyps...",
        btnAdd: "+ Hinzufügen",
        btnRename: "Umbenennen",
        added: "Eintrag hinzugefügt!",
        updated: "Aktualisiert",
        removed: "Eintrag entfernt",
        newNamePrompt: "Neuer Name:",
        confirmDeleteItem: "Eintrag \"{v}\" löschen?",
        promptNewType: "Namen des neuen Mangeltyps eingeben (z. B. \"Möbelausbau\", \"Heizung\"):",
        promptNewClient: "Namen des neuen Kunden eingeben (z. B. \"LAS - London Ambulance Service\"):",
        promptNewModel: "Namen des neuen Fahrzeugmodells eingeben (z. B. \"MAN TGE 2025\", \"Mercedes Sprinter 2024\"):",
        addedType: "Neuer Mangeltyp hinzugefügt: {v}",
        addedClient: "Neuer Kunde hinzugefügt: {v}",
        addedModel: "Neues Modell hinzugefügt: {v}",
        alreadyExistsType: "Typ \"{v}\" ist bereits in der Liste und wurde ausgewählt.",
        alreadyExistsClient: "Kunde \"{v}\" ist bereits in der Liste und wurde ausgewählt.",
        alreadyExistsModel: "Modell \"{v}\" ist bereits in der Liste und wurde ausgewählt.",
        saveError: "Speicherfehler: {v}"
      },
      users: {
        pageTitle: "Benutzer & Berechtigungen",
        pageSubtitle: "Verwalten Sie Techniker- und Administratorkonten im System.",
        btnNew: "+ Neuer Benutzer",
        thLogin: "Benutzername",
        thFullName: "Vor- und Nachname",
        thContact: "Kontakt",
        mustChangeBadge: "⚠️ Passwortänderung erforderlich",
        active: "Aktiv",
        inactive: "Inaktiv",
        pwBtn: "Passwort",
        adminOnly: "Administratorrechte erforderlich.",
        dblTitle: "Doppelklicken, um den Benutzer zu bearbeiten",
        modalNew: "Neuer Benutzer",
        modalEdit: "Benutzer bearbeiten: {v}",
        username: "Benutzername *",
        usernamePh: "z. B. j.mustermann",
        fullName: "Vor- und Nachname *",
        fullNamePh: "z. B. Max Mustermann",
        emailLabel: "E-Mail-Adresse (zur Passwortwiederherstellung)",
        emailPh: "z. B. max.mustermann@gmail.com",
        phoneLabel: "Telefonnummer (optional)",
        phonePh: "z. B. 600 100 200",
        role: "Rolle",
        roleTech: "Techniker (Meldungen & Reparaturen)",
        roleAdmin: "Administrator (Vollzugriff)",
        roleViewer: "Betrachter (nur Lesen)",
        initialPw: "Initialpasswort",
        pwHintNew: "(erforderlich, min. 4 Zeichen)",
        pwHintEdit: "(leer lassen, um es nicht zu ändern)",
        pwPh: "Passwort eingeben...",
        mustChange: "Passwortänderung bei erster Anmeldung erzwingen",
        saveUser: "Benutzer speichern",
        quickTitle: "🔄 Techniker an diesem Arbeitsplatz wechseln",
        quickDesc: "Wählen Sie einen Benutzer, um neue Meldungen und Reparaturen sofort Ihrem Profil zuzuweisen:"
      },
      backup: {
        pageTitle: "Backups & Datenbankwerkzeuge",
        walTitle: "💾 Datenbank für USB-Kopie vorbereiten (Datei rejestr_usterek.db zusammenführen)",
        walDesc: "Schreibt sofort alle ausstehenden Transaktionen und Einträge (WAL-Puffer) direkt in die Hauptdatei <code>rejestr_usterek.db</code>.",
        walNote: "Dadurch ist die Datei <code>rejestr_usterek.db</code> zu 100 % vollständig und kann sicher kopiert werden.",
        walBtn: "Datenbankdatei jetzt zusammenführen",
        exportTitle: "Backup herunterladen (JSON-Backup)",
        exportDesc: "Exportiert die gesamte Mängel-, Wörterbuch- und Verknüpfungsdatenbank in eine JSON-Datei.",
        exportBtn: "⬇ JSON-Backup herunterladen",
        importTitle: "Backup einspielen (JSON-Import)",
        importDesc: "Daten aus einer JSON-Datei laden (mit aktuellen Daten zusammenführen oder Datenbank ersetzen).",
        importMerge: "Mit aktueller Datenbank zusammenführen",
        importReplace: "Gesamte Datenbank ersetzen",
        optTitle: "Fotooptimierung & Datenbank-VACUUM",
        optDesc: "Komprimiert archivierte Fotos automatisch und verkleinert die SQLite-Datei auf dem Datenträger.",
        optBtn: "⚡ Optimierung starten"
      },
      auth: {
        loginSubtitle: "Anmelden für Zugriff",
        username: "Benutzername",
        usernamePh: "Benutzername eingeben...",
        password: "Passwort",
        passwordPh: "Passwort eingeben...",
        forgot: "Passwort vergessen?",
        loginBtn: "Anmelden",
        helpLine: "Bei Problemen mit dem Programm oder Ihrem Konto:",
        authorLabel: "Autor:",
        resetTitle: "Passwort zurücksetzen",
        resetDesc: "Geben Sie Ihren <strong>Benutzernamen</strong> oder Ihre <strong>E-Mail-Adresse</strong> ein, die Ihrem Konto zugeordnet ist. Wir senden Ihnen einen 6-stelligen Bestätigungscode.",
        identifier: "Benutzername oder E-Mail *",
        identifierPh: "z. B. j.mustermann oder max@gmail.com",
        backToLogin: "Zurück zur Anmeldung",
        sendCode: "Bestätigungscode senden ►",
        step2Desc: "Geben Sie den 6-stelligen Bestätigungscode (per E-Mail gesendet) ein und vergeben Sie ein neues Passwort.",
        code: "Bestätigungs-PIN (6 Ziffern) *",
        newPw: "Neues Passwort (min. 4 Zeichen) *",
        newPwPh: "Neues Passwort eingeben...",
        confirmPw: "Neues Passwort wiederholen *",
        confirmPwPh: "Neues Passwort wiederholen...",
        saveNewPw: "✓ Neues Passwort speichern",
        forceTitle: "Passwortänderung erforderlich",
        forceDesc: "Dies ist Ihre erste Anmeldung oder ein temporäres Passwort. Vergeben Sie ein eigenes, sicheres Passwort, um Zugriff auf die Anwendung zu erhalten.",
        forceSave: "Passwort speichern und starten"
      },
      multiPs: {
        title: "Projekte wählen (PS)",
        desc: "Wählen Sie die Projekte, für die dieser Mangel gilt:",
        filterPh: "Projektliste filtern...",
        customLabel: "Zusätzliches PS-Projekt (manuell eingeben, kommagetrennt):",
        apply: "✓ Auswahl übernehmen"
      },
      lightbox: {
        title: "Fotovorschau",
        prev: "◄ Zurück",
        next: "Weiter ►",
        download: "⬇ Herunterladen",
        prevTitle: "Vorheriges Foto (Pfeil links)",
        nextTitle: "Nächstes Foto (Pfeil rechts)",
        dlTitle: "Foto auf Datenträger herunterladen",
        closeTitle: "Fotovorschau schließen (ESC)"
      },
      zuken: {
        kpiConnSub: "Alle Stecker und Buchsen der Kabelbäume",
        kpiFusesSub: "UNI, MIDI, MEGA und Halter",
        kpiRelaysSub: "Schütze, Sockel und Kontaktbelegung",
        kpiStatus: "📁 Wissensdatenbank-Status",
        statusChecking: "Daten werden geprüft...",
        statusReady: "✓ Bereit",
        statusGeneratedAt: "erstellt: {v}",
        statusNeedsGen: "⚠️ Erfordert Generierung aus XLSX",
        noProjectSelected: "Kein Projekt ausgewählt",
        sysLabel: "System:",
        sysAll: "Alle",
        sysBox: "=BOX (Aufbau)",
        sysCab: "=CAB (Kabine)",
        sysCha: "=CHA (Fahrgestell)",
        sysBom: "=BOM (Dach)",
        loadingConnectors: "Stecker werden geladen...",
        loadingFuses: "Sicherungen werden geladen...",
        loadingRelays: "Relais werden geladen...",
        loadingConnectorsLong: "Stecker und Pinbelegungen werden geladen...",
        loadingFusesLong: "Sicherungssatz wird geladen...",
        loadingRelaysLong: "Relaissatz wird geladen...",
        shownConnectors: "{n} von {total} Steckern angezeigt",
        shownFuses: "{n} von {total} Sicherungen angezeigt",
        shownRelays: "{n} von {total} Relais angezeigt",
        emptyConnectors: "Keine Stecker entsprechen den gewählten Kriterien.",
        emptyFuses: "Keine Sicherungen entsprechen den gewählten Kriterien.",
        emptyRelays: "Keine Relais entsprechen den gewählten Kriterien.",
        errLoadConnectors: "Fehler beim Laden der Stecker: {v}",
        errLoadFuses: "Fehler beim Laden der Sicherungen: {v}",
        errLoadRelays: "Fehler beim Laden der Relais: {v}",
        fuseColDevice: "Sicherung",
        fuseColRatingType: "Strom — Typ",
        fuseColWires: "Leitungen & Stromkreise",
        fuseExternalHarness: "{name}-Kabelbaum — im Lieferumfang des Geräts",
        fuseColLocation: "Standort",
        fuseColBom: "BOM-Artikel & Hersteller",
        pinoutTargetFull: "Verbindungsziel (Gerät:Pin)",
        wirePathTitle: "Signalpfad",
        wirePathJump: "In Liste suchen",
        wirePathClose: "Schließen",
        pinCount: "{n} Pins",
        noBomCode: "Kein BOM-Code",
        expandPinout: "Pinbelegung aufklappen ({n}) ▼",
        collapsePinout: "Pinbelegung zuklappen ▲",
        expandPinoutShort: "Pinbelegung aufklappen ▼",
        relayFuncDefault: "Relais",
        relayColPin: "Pin / Kontakt",
        relayColRole: "Kontaktfunktion",
        relayColSignal: "Signal",
        relayColWire: "Leitung",
        relayColTarget: "Anderes Kabelende",
        relayColCross: "Querschnitt",
        relayColLength: "Länge",
        relaySocketCaption: "Relaissockel von oben · gn. = Sockelpin",
        relayNoContacts: "Keine direkten Kontaktverbindungen in der Verbindungsdatei gefunden.",
        relayRoleCoil: "Spule (85/86)",
        relayRoleCommon: "Versorgung (30)",
        relayRoleNO: "Schließer (87)",
        relayRoleNC: "Öffner (87A)",
        relayRoleWorking: "Arbeitskontakt",
        selectPsFirst: "Wählen Sie ein PS-Projekt aus der Liste.",
        generating: "Generierung...",
        analyzingXlsx: "XLSX-Dateien für {ps} werden analysiert...",
        errGenerate: "Fehler bei der Listenerstellung: {v}",
        errLoadProjects: "Fehler beim Laden der PS-Projekte: {v}",
        csvDownloading: "CSV-Datei ({type}) für {ps} wird heruntergeladen...",
        unknownGenError: "Unbekannter Generierungsfehler",
        generatedFor: "Listen für {ps} erstellt.",
        csvExportTitle: "Aktuelle Tabelle als CSV herunterladen (Excel-kompatibel)",
        printTitle: "Liste drucken",
        componentPhoto: "Bauteilfoto",
        changePhoto: "Foto ändern",
        articleLabel: "Katalogartikel:",
        pasteCtrlV1: "Drücken Sie",
        pasteCtrlV2: ", um ein Foto aus der Zwischenablage einzufügen",
        orClickFile: "oder hier klicken, um eine Datei (JPG, PNG, WebP) vom Datenträger zu wählen",
        offlineFooter: "Lokale Zuken-E3-Engine & BOM-Report (100% Offline)"
      }
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
        // Dla języków innych niż polski używamy angielskich treści dynamicznych
        // (baza danych przechowuje tłumaczenia PL -> EN).
        return typeof CURRENT_LANG !== 'undefined' && CURRENT_LANG !== 'pl';
      },
      configurable: true
    });
  } catch (e) {}
}

function setLanguage(lang) {
  if (typeof TRANSLATIONS === 'undefined' || !TRANSLATIONS[lang]) lang = 'pl';
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
  const enDict = (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS['en']) || {};
  const plDict = (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS['pl']) || {};
  // Kolejność fallbacku: język aktywny -> EN -> PL -> klucz
  let val = keys.reduce((obj, k) => obj?.[k], activeDict)
         || keys.reduce((obj, k) => obj?.[k], enDict)
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
  if (lang !== 'pl' && typeof CATEGORY_MAP_PL_TO_EN !== 'undefined') {
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
  // Odśwież aktywny widok, aby treści renderowane przez JS
  // (projekty, słowniki, użytkownicy, zestawienia Zuken) zmieniły język
  if (window.STATE && STATE.currentView && typeof switchView === 'function') {
    switchView(STATE.currentView);
  }
  if (window.STATE && window.STATE.selectedRecordId) {
    if (typeof selectRecord === 'function') selectRecord(window.STATE.selectedRecordId);
    const modalPreview = document.getElementById('modal-defect-preview');
    if (modalPreview && (modalPreview.style.display === 'flex' || modalPreview.classList.contains('active')) && typeof openDefectPreview === 'function') {
      openDefectPreview(window.STATE.selectedRecordId);
    }
  }
}
