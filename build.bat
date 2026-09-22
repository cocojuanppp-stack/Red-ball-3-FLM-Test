@echo off
cd /d "%~dp0"
echo Organizando juegos en carpetas independientes...
python build-index.py
if errorlevel 1 (
    py build-index.py
)
echo.
pause
