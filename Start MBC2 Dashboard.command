#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo " Starting MBC2 Dashboard..."
echo " Close this window or browser tab to stop."
echo ""
python3 server.py
