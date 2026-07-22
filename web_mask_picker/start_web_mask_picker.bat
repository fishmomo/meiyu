@echo off
setlocal
cd /d "%~dp0.."
start "Meiyu mask picker" "D:\anaconda\python.exe" "web_mask_picker\app.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"
