#!/bin/bash

# Script to run the Flask app for SimpleSyntenyViewer

echo "============================================================"
echo "Starting SimpleSyntenyViewer Flask Server"
echo "============================================================"
echo ""
echo "Prerequisites:"
echo "  - Python 3 with Flask installed (pip install -r requirements.txt)"
echo "  - minimap2 installed and in PATH"
echo "  - samtools installed and in PATH"
echo ""
echo "Server will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Flask not found. Installing requirements..."
    pip3 install -r requirements.txt
fi

# Run Flask app
python3 app.py
