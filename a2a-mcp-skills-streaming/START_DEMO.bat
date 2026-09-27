@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run the setup steps in START_HERE.md first.
  exit /b 1
)
.venv\Scripts\python.exe run.py
