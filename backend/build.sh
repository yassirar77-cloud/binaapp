#!/bin/bash
set -e

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Build complete!"
