#!/bin/bash
set -e

echo "=== image-to-3d setup ==="

# COLMAP
if ! command -v colmap &>/dev/null; then
    echo "Installing COLMAP..."
    sudo apt-get update -q
    sudo apt-get install -y colmap
else
    echo "COLMAP already installed: $(colmap --version 2>&1 | head -1)"
fi

# Python deps
echo "Installing Python dependencies..."
pip3 install --break-system-packages -r requirements.txt

# Working directories
mkdir -p output temp

echo ""
echo "Setup complete. Run the app with:"
echo "  python3 app.py"
