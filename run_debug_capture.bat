@echo off
set PYTHONPATH=%~dp0
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\debug_capture.py"
pause