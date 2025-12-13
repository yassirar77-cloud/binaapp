#!/usr/bin/env bash
# Build script for Render deployment
# Uses pip + Python 3.11 (no Poetry, no sudo)

set -o errexit  # Exit immediately on error

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Skipping Playwright browser installation on Render"
echo "Build completed successfully!"
