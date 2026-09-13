#!/bin/bash
set -e
echo "Upgrading pip..."
pip install --upgrade pip
echo "Installing dependencies..."
pip install -r requirements.txt
# Chromium for the design critique gate's screenshots (design_critique.py).
# Best-effort: a failed browser install must not fail the build — the gate
# degrades to a text-only critique when no browser is present.
echo "Installing Playwright Chromium (best-effort)..."
python -m playwright install chromium --with-deps || python -m playwright install chromium || echo "Playwright browser install skipped"
echo "Build complete!"
