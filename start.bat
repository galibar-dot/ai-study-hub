@echo off
chcp 65001 > nul
cd /d "%~dp0"
"C:\Users\Lenovo\AppData\Local\Python\bin\python.exe" server.py
pause
