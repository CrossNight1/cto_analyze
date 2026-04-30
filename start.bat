@echo off
REM COT Analyzer Dashboard Start Script for Windows

SET SCRIPT_DIR=%~dp0
CD /D "%SCRIPT_DIR%"

IF NOT EXIST ".venv" (
    echo .venv not found. Creating virtual environment...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
    
    echo Installing requirements...
    call .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install requirements.
        pause
        exit /b 1
    )
) ELSE (
    call .venv\Scripts\activate
)

echo Starting COT Analyzer Dashboard...
call .venv\Scripts\activate
streamlit run app.py
pause
