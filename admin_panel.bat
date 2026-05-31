@echo off
chcp 65001 > nul
cd /d "%~dp0"
title Server Management Panel
echo Starting server management panel...
"C:\Users\Lenovo\AppData\Local\Python\bin\python.exe" server_manager.py
pause
