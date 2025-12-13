#!/usr/bin/env bash
# Build script for Render deployment
# This ensures we use pip, not Poetry

set -o errexit  # Exit on error

echo "Installing Python dependencies with pip..."
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

echo "Build completed successfully!"
