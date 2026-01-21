#!/bin/bash

# Script to run the synteny visualization with ngrok
# Starts a local web server and creates an ngrok tunnel

PORT=8000
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="http://localhost:$PORT"

echo "============================================================"
echo "Starting Synteny Visualization Server with ngrok"
echo "============================================================"
echo "Directory: $DIR"
echo "Port: $PORT"
echo "Local URL: $URL"
echo ""
echo "Press Ctrl+C to stop both server and ngrok"
echo "============================================================"
echo ""

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port $PORT is already in use. Killing existing process..."
    kill $(lsof -t -i:$PORT) 2>/dev/null
    sleep 1
fi

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok is not installed."
    echo "Install it from: https://ngrok.com/download"
    echo "Or use: brew install ngrok/ngrok/ngrok"
    exit 1
fi

# Start the server in background
cd "$DIR"
python3 -m http.server $PORT &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Start ngrok
echo "Starting ngrok tunnel..."
ngrok http $PORT

# Cleanup: kill server when ngrok exits
trap "kill $SERVER_PID 2>/dev/null" EXIT
