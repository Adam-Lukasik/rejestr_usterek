@echo off
chcp 65001 >nul
cd /d "%~dp0"

title Rejestr Usterek v2.0 - Migracja do wersji dwujęzycznej (PL / EN)

set PYTHON=

for /f "delims=" %%f in ('dir /b /ad "python-embed" 2^>nul') do (
  if exist "python-embed\%%f\python\python.exe" (
    set PYTHON=python-embed\%%f\python\python.exe
  )
)

if "%PYTHON%"=="" if exist python\python.exe set PYTHON=python\python.exe
if "%PYTHON%"=="" if exist venv\Scripts\python.exe set PYTHON=venv\Scripts\python.exe
if "%PYTHON%"=="" (
  python --version >nul 2>&1
  if not errorlevel 1 set PYTHON=python
)

if "%PYTHON%"=="" (
  echo [BLAD] Nie znaleziono srodowiska Python.
  pause
  exit /b 1
)

echo ===================================================================
echo   Rejestr Usterek v2.0 — Migracja i tlumaczenie bazy na EN
echo ===================================================================
echo.
echo Ten program utworzy kopie bezpieczenstwa Twojej bazy rejestr_usterek.db
echo a nastepnie wygeneruje automatyczne tlumaczenia EN dla wszystkich
echo istniejacych usterek i wariantow napraw.
echo.
set /p POTWIERDZ="Czy chcesz rozpoczac migracje teraz? (T/N): "
if /i not "%POTWIERDZ%"=="T" (
  echo Anulowano przez uzytkownika.
  pause
  exit /b 0
)

echo.
"%PYTHON%" "%~dp0migruj_tlumaczenia_en.py"
echo.
pause
