@echo off
set PYTHONPATH=%~dp0
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\api_capture.py"
pause