@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Rejestr Usterek - Build release

rem Buduje paczke release (Nuitka + minifikacja + migracje + latest.json).
rem Uzycie:
rem   uruchom_release.bat                          - pelny build
rem   uruchom_release.bat --deploy "\\NAS\RejestrUsterek\updates"  - build + kopia na NAS
rem   uruchom_release.bat --skip-nuitka            - bez rekompilacji (szybkie testy paczki)

if exist venv\Scripts\python.exe (
  set PYTHON=venv\Scripts\python.exe
) else (
  set PYTHON=python
)

%PYTHON% tools\build_release.py %*
if errorlevel 1 (
  echo.
  echo [BLAD] Build nie powiodl sie - szczegoly wyzej.
  pause
  exit /b 1
)
echo.
pause
