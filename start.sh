#!/bin/bash
# COT Analyzer Dashboard Start Script

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if .venv exists, create it if not
if [ ! -d ".venv" ]; then
    echo ".venv not found. Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Please ensure python3 is installed."
        exit 1
    fi
    
    echo "Installing requirements..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install requirements."
        exit 1
    fi
else
    # Even if .venv exists, let's make sure it's activated
    source .venv/bin/activate
fi

# Activate virtual environment and run streamlit
echo "Starting COT Analyzer Dashboard..."
streamlit run app.py
