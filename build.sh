#!/usr/bin/env bash
# Railway build script for backend deployment
# This script runs from the root directory and handles the backend build

set -o errexit  # Exit immediately on error

echo "Railway build script starting..."
echo "Current directory: $(pwd)"

# Change to backend directory
cd backend || { echo "ERROR: backend directory not found"; exit 1; }

echo "Changed to backend directory: $(pwd)"

# Create and activate virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "Skipping Playwright browser installation (not needed for Railway)"
echo "Build completed successfully!"

# Return to root directory
cd ..
echo "Returned to root directory"
