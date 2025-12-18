#!/usr/bin/env bash
# Build script for Render deployment
# Uses pip + Python 3.11 (no Poetry, no sudo)

set -o errexit  # Exit immediately on error

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Installing Playwright Chromium browser..."
playwright install chromium
playwright install-deps chromium

echo "Build completed successfully!"
