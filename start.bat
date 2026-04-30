@echo off
REM COT Analyzer Dashboard Start Script for Windows

SET SCRIPT_DIR=%~dp0
CD /D "%SCRIPT_DIR%"

IF NOT EXIST ".venv" (
    echo Error: .venv directory not found. Please create it first.
    pause
    exit /b 1
)

echo Starting COT Analyzer Dashboard...
call .venv\Scripts\activate
streamlit run app.py
pause
