# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# PyInstaller build spec (PyInstaller 6.x).
#
# Shared by the local build scripts and the GitHub Actions workflow so
# the macOS .app and the Windows .exe are produced from one config.
# Run from the project root:
#     pyinstaller build/NeuroCogProfile.spec
# Paths are resolved from the spec location, so the working directory
# does not matter.
# ============================================================

import os
import sys

from PyInstaller.utils.hooks import collect_all

# Project root is the parent of this spec's folder (build/).
ROOT = os.path.dirname(SPECPATH)  # noqa: F821  (SPECPATH injected by PyInstaller)

# Bundle the local web UI and the default template alongside the app.
datas = [
    (os.path.join(ROOT, "web"), "web"),
    (os.path.join(ROOT, "templates"), "templates"),
]
binaries = []
hiddenimports = []

# Pull in the full webview backend (pyobjc on macOS, pythonnet on
# Windows) so the native window works in the frozen app, and the whole
# python-docx package: its part templates (docx/templates/*.xml, used
# for example when a footer is created) are data files that PyInstaller
# does not always pick up on its own, which broke the Word export in
# the packaged app.
for _pkg in ("webview", "docx"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# Optional application icon (drop these files in build/ to use them).
_icon_mac = os.path.join(ROOT, "build", "icon.icns")
_icon_win = os.path.join(ROOT, "build", "icon.ico")
if sys.platform == "darwin":
    icon = _icon_mac if os.path.exists(_icon_mac) else None
elif sys.platform.startswith("win"):
    icon = _icon_win if os.path.exists(_icon_win) else None
else:
    icon = None


a = Analysis(
    [os.path.join(ROOT, "app.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NeuroCogProfile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed: no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NeuroCogProfile",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="NeuroCogProfile.app",
        icon=icon,
        bundle_identifier="com.neurocogprofile.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "1.0.0",
            "LSMinimumSystemVersion": "11.0",
        },
    )
