@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
start "" /D "%~dp0." ".venv\Scripts\pythonw.exe" -m place_stay
