@echo off
chcp 65001 >nul
cd /d "%~dp0"

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
  echo Nie znalazlem Pythona.
  echo.
  echo Mozliwe rozwiazania:
  echo 1. Uruchom przygotuj_laptop.bat, aby pobrac przenosny Python.
  echo 2. Zainstaluj Pythona ze Sklepu Windows lub z python.org.
  pause
  exit /b 1
)

%PYTHON% -c "import flask, ttkbootstrap, requests" >nul 2>&1
if errorlevel 1 (
  echo Instaluje zaleznosci...
  %PYTHON% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Nie udalo sie zainstalowac zaleznosci.
    pause
    exit /b 1
  )
)

:: Uruchomienie aplikacji na laptopie polaczonej z firmowym serwerem QNAP (srv_ost)
start "" "%PYTHONW%" desktop.py --server http://srv_ost:5050
exit
