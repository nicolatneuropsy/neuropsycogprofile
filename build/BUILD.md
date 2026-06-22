# Building NeuroCogProfile

This produces a standalone desktop application with PyInstaller: a
`.exe` on Windows and a `.app` bundle on macOS. The build is fully
offline at runtime; these instructions only need the network to
`pip install` the build-time dependencies.

Code signing and notarization are the user's responsibility and are
out of scope here. The steps below produce an unsigned build. On macOS
an unsigned `.app` may need a right-click then Open the first time, or
`xattr -dr com.apple.quarantine NeuroCogProfile.app`. On Windows
SmartScreen may warn about an unknown publisher.

## One-click distribution (recommended)

For a downloadable file clinicians can just double-click, use the
prepared scripts and CI instead of the manual commands below.

- `build/NeuroCogProfile.spec` is the shared PyInstaller config (paths
  resolve from the spec, so the working directory does not matter).
- `build/build_macos.sh` builds the `.app` and packages a
  drag-to-Applications `dist/NeuroCogProfile-macos.dmg`.
- `build/build_windows.bat` builds the app and, if Inno Setup is
  installed, a one-file `dist/NeuroCogProfile-windows-setup.exe`.
- `.github/workflows/build.yml` builds both on GitHub's macOS and
  Windows runners and, when you push a version tag, publishes a GitHub
  Release with the files attached (the public download link).
- `build/installer.iss` is the Inno Setup script (per-user install, no
  admin rights).
- `build/INSTALL_clinicians.md` is the bilingual one-page guide to hand
  to end users (covers the one-time unsigned-app prompt).

A macOS `.app` must be built on macOS and a Windows `.exe` on Windows
(no cross-compiling); GitHub Actions does both at once. To cut a
release:

```
git init -b main           # this folder is not a git repo yet
git add -A
git commit -m "NeuroCogProfile"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
git tag v1.0.0
git push origin v1.0.0     # triggers the build + Release
```

Optional app icon: drop `build/icon.icns` (macOS) and `build/icon.ico`
(Windows); the spec picks them up automatically.

The rest of this file documents the manual one-off commands the scripts
wrap.

## 0. Prerequisites

```
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

Windows additionally needs the Microsoft Edge WebView2 runtime. It
ships with current Windows 10 and 11; if missing, install the
Evergreen runtime from Microsoft once on the build and target machines.

Anaconda note: if PyInstaller stops with "The 'pathlib' package is an
obsolete backport ... incompatible with PyInstaller", remove that one
package once and rebuild:

```
python -m pip uninstall -y pathlib    # or: conda remove pathlib
```

This only affects local builds in some Anaconda environments. The
GitHub Actions runners use a clean Python and are not affected. The
build scripts also check for this and print the same fix.

## 1. Development run (no packaging)

```
python app.py
```

The window opens on the bundled local HTML. Nothing is written to disk
unless you save a template or a session through a file dialog.

## 2. Windows build (.exe)

Run from the project root (the folder that contains `app.py`). Note the
`;` separator in `--add-data` on Windows.

```
pyinstaller --noconfirm --clean --windowed --name NeuroCogProfile ^
  --add-data "web;web" ^
  --add-data "templates;templates" ^
  app.py
```

The result is `dist\NeuroCogProfile\NeuroCogProfile.exe` (one-folder).
For a single file add `--onefile` (slower to start because it unpacks
to a temp folder, which `resource_path` in api.py handles).

If the WebView2 bridge fails to import in the frozen app, add:

```
  --hidden-import clr ^
  --collect-all webview ^
```

## 3. macOS build (.app)

Run from the project root. Note the `:` separator in `--add-data` on
macOS and Linux.

```
pyinstaller --noconfirm --clean --windowed --name NeuroCogProfile \
  --osx-bundle-identifier com.example.neurocogprofile \
  --add-data "web:web" \
  --add-data "templates:templates" \
  app.py
```

The result is `dist/NeuroCogProfile.app`. If the WebKit backend is not
picked up automatically, add:

```
  --collect-all webview \
```

## 4. Linux build (development convenience)

Linux is not a required target but works for testing. Install a GTK or
Qt backend first (see requirements.txt), then use the same command as
macOS with the `:` separator.

## 5. Matplotlib note

PyInstaller's matplotlib hook normally bundles the Agg backend and the
DejaVu fonts that the figures use. If a frozen build cannot find
matplotlib data, add `--collect-data matplotlib`. The app forces the
Agg backend in plots.py, so no interactive GUI toolkit is needed for
the figures.

## 6. Verifying the build is offline

After building, disconnect from the network and confirm the app still
launches, computes, plots and exports. There are no update checks,
analytics, or webfont fetches to fail.
