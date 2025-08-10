#!/bin/bash
# ADHDo Quick Start - Just run this!

echo "🧠 Starting ADHDo..."

# Use venv if it exists
if [ -d "venv_beta" ]; then
    ./venv_beta/bin/python adhdo_server.py
elif [ -d "venv" ]; then
    ./venv/bin/python adhdo_server.py
else
    python3 adhdo_server.py
fi
