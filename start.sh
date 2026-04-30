#!/bin/bash
# COT Analyzer Dashboard Start Script

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Error: .venv directory not found. Please create it first."
    exit 1
fi

# Activate virtual environment and run streamlit
echo "Starting COT Analyzer Dashboard..."
source .venv/bin/activate
streamlit run app.py
