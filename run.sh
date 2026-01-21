#!/bin/bash

# Script to run the synteny visualization
# Starts a local web server and optionally opens the visualization in a browser

PORT=8000
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="http://localhost:$PORT"

echo "============================================================"
echo "Starting Synteny Visualization Server"
echo "============================================================"
echo "Directory: $DIR"
echo "Port: $PORT"
echo "URL: $URL"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Kill any existing Python http.server processes on this port
echo "Checking for existing server instances..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Found existing server on port $PORT. Killing..."
    kill $(lsof -t -i:$PORT) 2>/dev/null
    sleep 1
fi

# Also kill any Python http.server processes that might be running
PIDS=$(ps aux | grep "[p]ython.*http.server.*$PORT" | awk '{print $2}')
if [ ! -z "$PIDS" ]; then
    echo "Killing other Python http.server instances..."
    echo "$PIDS" | xargs kill 2>/dev/null
    sleep 1
fi

# Open browser after a short delay (in background)
(sleep 2 && open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || echo "Please open $URL in your browser") &

# Start the server
cd "$DIR"
python3 -m http.server $PORT
