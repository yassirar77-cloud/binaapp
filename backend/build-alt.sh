#!/usr/bin/env bash
# Alternative build script that prevents Poetry detection
# Use this if Render keeps trying to use Poetry

# Disable Poetry auto-detection
export POETRY_ACTIVE=0
export POETRY_VERSION=""

# Force pip installation
echo "=== BinaApp Build Script ==="
echo "Forcing pip installation (NOT Poetry)"
echo "Python version: $(python --version)"

pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

echo "Installing Playwright..."
playwright install chromium
playwright install-deps chromium

echo "=== Build Complete ==="
