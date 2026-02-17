#!/bin/bash
# Wrapper script to run Obsidian Mobile QA Agent with venv activated

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "   Creating venv and installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Run the QA agent
python3 run_qa.py "$@"
