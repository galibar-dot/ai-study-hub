@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 服务器管理面板
echo 正在启动服务器管理面板...
"C:\Users\Lenovo\AppData\Local\Python\bin\python.exe" server_manager.py
pause
