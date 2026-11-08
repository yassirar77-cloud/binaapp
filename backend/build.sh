#!/bin/bash
set -e
echo "Upgrading pip..."
pip install --upgrade pip
echo "Installing dependencies..."
pip install -r requirements.txt

# Chromium for the visual QA gate (services/visual_gate.py) and the design
# critique. Render keeps only the project folder from the build to the
# running service: a browser downloaded into ~/.cache or /opt/render/.cache
# during the build is gone when the service starts (every generation so far
# logged "Executable doesn't exist"). So the browser goes inside the
# project, and the service's PLAYWRIGHT_BROWSERS_PATH must point at the
# same folder at runtime.
#
# Only the headless shell (what a headless launch uses) is downloaded, and
# without --with-deps: installing system packages needs root, which Render's
# native runtime does not have ("su: Authentication failure"). The
# self-test below says whether the shell runs with the libraries present.
#
# Best-effort throughout: a browser problem never fails the build. Without
# a working browser the gate logs it and pages ship ungated, as before.
PROJECT_BROWSERS="$(pwd)/.playwright-browsers"
echo "Build directory: $(pwd)"
if [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ]; then
  export PLAYWRIGHT_BROWSERS_PATH="$PROJECT_BROWSERS"
fi
case "$PLAYWRIGHT_BROWSERS_PATH" in
  "$(pwd)"/*|/opt/render/project/src/*) ;;
  *)
    echo "WARNING: PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH is outside the project folder;"
    echo "WARNING: Render discards it after the build. Set PLAYWRIGHT_BROWSERS_PATH=$PROJECT_BROWSERS on the service."
    ;;
esac
echo "Installing the Chromium headless shell into $PLAYWRIGHT_BROWSERS_PATH (best-effort)..."
python -m playwright install --only-shell chromium \
  || python -m playwright install chromium \
  || echo "Playwright browser install failed: the gate will report it and pages ship ungated"

echo "Visual gate self-test (one gate run on the agp page)..."
python scripts/gate_selftest.py || echo "GATE_SELFTEST could not run"
echo "Build complete!"
