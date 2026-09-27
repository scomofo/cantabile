@echo off
setlocal
cd /d "%~dp0"
echo Cantabile bank-only setup: Python packages; no neural voice download.
echo The recorded vowel bank is included. Neural lyrics can be installed later.
if not exist .venv\Scripts\python.exe (
  where py >nul 2>nul
  if errorlevel 1 (python -m venv .venv) else (py -3 -m venv .venv)
)
if not exist .venv\Scripts\python.exe goto failed
.venv\Scripts\python.exe prepare_bank.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open start-windows.bat.
pause
exit /b 0
:failed
echo Setup did not finish. Install Python 3.12 or 3.13 from python.org and retry.
echo The error above may also identify a download or dependency issue.
pause
exit /b 1
