#!/bin/bash

# Script to run the Flask app for SimpleSyntenyViewer

echo "============================================================"
echo "Starting SimpleSyntenyViewer Flask Server"
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

# Check for required tools
echo "Checking for required tools (minimap2 required, samtools optional)..."
python3 install.py --check-only
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠ Warning: Required tools are missing!"
    echo "Run './install.py' to install minimap2 automatically, or install manually."
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Server will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Run Flask app
python3 app.py
