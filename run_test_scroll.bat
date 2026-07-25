@echo off
set PYTHONPATH=%~dp0
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\test_scroll_drag.py"
pause