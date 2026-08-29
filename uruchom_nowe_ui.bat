@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Rejestr Usterek - Uruchamianie

set PYTHON=
set PYTHONW=

for /f "delims=" %%f in ('dir /b /ad "python-embed" 2^>nul') do (
  if exist "python-embed\%%f\python\python.exe" (
    set PYTHON=python-embed\%%f\python\python.exe
    set PYTHONW=python-embed\%%f\python\pythonw.exe
  )
)

if "%PYTHON%"=="" if exist python\python.exe (
  set PYTHON=python\python.exe
  set PYTHONW=python\pythonw.exe
)
if "%PYTHON%"=="" if exist venv\Scripts\python.exe (
  set PYTHON=venv\Scripts\python.exe
  set PYTHONW=venv\Scripts\pythonw.exe
)
if "%PYTHON%"=="" (
  python --version >nul 2>&1
  if not errorlevel 1 (
    set PYTHON=python
    set PYTHONW=pythonw
  )
)

if "%PYTHON%"=="" (
  echo [BLAD] Nie znaleziono srodowiska Python.
  echo.
  echo Mozliwe rozwiazania:
  echo 1. Zainstaluj Pythona ze Sklepu Windows lub z python.org.
  echo 2. Skopiuj folder python-embed do glownego katalogu programu.
  pause
  exit /b 1
)

%PYTHON% -c "import flask, requests, webview, waitress" >nul 2>&1
if errorlevel 1 (
  echo ========================================================
  echo   Instalowanie brakujacych bibliotek dla WebView2...
  echo ========================================================
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [BLAD] Nie udalo sie zainstalowac zaleznosci.
    pause
    exit /b 1
  )
)

echo ========================================================
echo   Rejestr Usterek v5.0 - Nowoczesny Interfejs
echo ========================================================
echo.
echo [1/2] Inicjalizacja serwera lokalnego i bazy danych...
echo [2/2] Otwieranie okna aplikacji...
echo.

:: Uruchomienie okna aplikacji w tle
start "" "%PYTHONW%" "%~dp0desktop_web.py" --local
exit
