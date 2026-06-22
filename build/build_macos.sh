#!/usr/bin/env bash
# ============================================================
# Build the macOS app and package it as a drag-to-Applications .dmg.
# Run on a Mac:   bash build/build_macos.sh
# Output:         dist/NeuroCogProfile-macos.dmg
#
# The result is unsigned. See build/INSTALL_clinicians.md for the
# one-time "right-click > Open" step on the first launch.
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="NeuroCogProfile"
APP="dist/${APP_NAME}.app"
DMG="dist/${APP_NAME}-macos.dmg"
STAGE="build/_dmg_stage"

# PyInstaller cannot run if the obsolete 'pathlib' backport is installed
# (common in Anaconda base environments). Fail early with the fix.
if python3 -m pip show pathlib >/dev/null 2>&1; then
  echo "ERROR: the obsolete 'pathlib' backport is installed; PyInstaller cannot run." >&2
  echo "Fix it once with:  python3 -m pip uninstall -y pathlib   (or: conda remove pathlib)" >&2
  exit 1
fi

echo ">> Installing dependencies"
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt pyinstaller >/dev/null

echo ">> Building the app bundle with PyInstaller"
rm -rf dist "build/_pyi_build"
pyinstaller --noconfirm --clean \
  --workpath "build/_pyi_build" \
  --distpath "dist" \
  "build/${APP_NAME}.spec"

if [ ! -d "$APP" ]; then
  echo "ERROR: $APP was not produced." >&2
  exit 1
fi

echo ">> Packaging the .dmg"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"   # drag-to-Applications target
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" \
  -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

echo ">> Done: $DMG"
