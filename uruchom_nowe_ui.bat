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

%PYTHON% -c "import flask, requests, webview, waitress, pypdfium2" >nul 2>&1
if errorlevel 1 (
  echo ========================================================
  echo   Instalowanie / aktualizacja bibliotek...
  echo ========================================================
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [BLAD] Nie udalo sie zainstalowac zaleznosci.
    pause
    exit /b 1
  )
)

echo ========================================================
echo   Rejestr Usterek v1.5 -- Panel Diagnostyki i Serwisu
echo ========================================================
echo.
echo   [1/2] Inicjalizacja bazy danych i serwera lokalnego...
echo   [2/2] Ladowanie silnika WebView2 i otwieranie okna...
echo.
echo   Trwa uruchamianie aplikacji, prosze czekac...
echo.

if not "%PYTHONW%"=="" (
  start "" "%PYTHONW%" "%~dp0desktop_web.py" --local
) else (
  start "" "%PYTHON%" "%~dp0desktop_web.py" --local
)
exit
