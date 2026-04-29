#!/bin/bash
cd "$(dirname "$0")"

echo "================================================"
echo "  MBC2 Dashboard - mic-LABO Motor Boot Camp 2"
echo "================================================"
echo ""

# Kill any existing process using port 8766
echo "Checking for existing server on port 8766..."
EXISTING_PID=$(lsof -ti tcp:8766 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo "Killing existing process PID: $EXISTING_PID"
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 2
fi

# Check for Python and launch
if command -v python3 &>/dev/null; then
    echo "Starting server..."
    echo ""
    python3 server.py
elif command -v python &>/dev/null; then
    echo "Starting server..."
    echo ""
    python server.py
else
    echo "ERROR: Python not found."
    echo "Please install Python from https://python.org/downloads"
    echo ""
    read -p "Press Enter to close..."
fi
