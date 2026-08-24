@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist tryb.json del tryb.json

echo Tryb zresetowany. Uruchamiam aplikacje ponownie...
call uruchom.bat
