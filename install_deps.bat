@echo off
echo Installing automation dependencies...
"%~dp0.venv\Scripts\pip.exe" install pywin32 pyautogui pygetwindow paddleocr
echo.
echo Dependencies installed successfully!
pause