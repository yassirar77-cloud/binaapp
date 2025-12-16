#!/usr/bin/env bash
# Railway build script for backend deployment
# This script runs from the root directory and handles the backend build

set -o errexit  # Exit immediately on error

echo "Railway build script starting..."
echo "Current directory: $(pwd)"

# Change to backend directory
cd backend || { echo "ERROR: backend directory not found"; exit 1; }

echo "Changed to backend directory: $(pwd)"

# Bootstrap pip if not available
echo "Ensuring pip is available..."
python3 -m ensurepip --default-pip 2>/dev/null || echo "ensurepip not needed or unavailable"

echo "Upgrading pip..."
python3 -m pip install --upgrade pip

echo "Installing Python dependencies from requirements.txt..."
python3 -m pip install --no-cache-dir -r requirements.txt

echo "Skipping Playwright browser installation (not needed for Railway)"
echo "Build completed successfully!"

# Return to root directory
cd ..
echo "Returned to root directory"
