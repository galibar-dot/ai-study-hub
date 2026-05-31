@echo off
title Open Admin Panel

echo.
echo Opening admin panel...
echo.

start http://localhost:8000/admin.html

echo Admin panel opened in browser
timeout /t 2 >nul
