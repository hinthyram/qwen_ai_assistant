@echo off
cd /d "%~dp0"
py -m assistant.main
if errorlevel 1 pause
