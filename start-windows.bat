@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup-windows.bat or setup-bank-only-windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py
pause
