@echo off
REM ============================================================
REM Build the Windows app and wrap it in a one-file installer.
REM Run on Windows:   build\build_windows.bat
REM Output:           dist\NeuroCogProfile-windows-setup.exe
REM                   (plus the portable folder dist\NeuroCogProfile)
REM
REM The result is unsigned. See build\INSTALL_clinicians.md for the
REM one-time SmartScreen "Run anyway" step on the first launch.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

REM PyInstaller cannot run if the obsolete 'pathlib' backport is installed
REM (common in Anaconda base environments). Fail early with the fix.
python -m pip show pathlib >nul 2>nul
if %errorlevel%==0 (
  echo ERROR: the obsolete 'pathlib' backport is installed; PyInstaller cannot run.
  echo Fix it once with:  python -m pip uninstall -y pathlib
  goto :error
)

echo ^>^> Installing dependencies
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements.txt pyinstaller || goto :error

echo ^>^> Building the app with PyInstaller
if exist dist rmdir /s /q dist
if exist build\_pyi_build rmdir /s /q build\_pyi_build
pyinstaller --noconfirm --clean ^
  --workpath build\_pyi_build ^
  --distpath dist ^
  build\NeuroCogProfile.spec || goto :error

if not exist "dist\NeuroCogProfile\NeuroCogProfile.exe" (
  echo ERROR: the app was not produced.
  goto :error
)

echo ^>^> Building the installer with Inno Setup
where iscc >nul 2>nul
if %errorlevel%==0 (
  iscc build\installer.iss || goto :error
  echo ^>^> Done: dist\NeuroCogProfile-windows-setup.exe
) else (
  echo Inno Setup ^(iscc^) not found on PATH.
  echo The portable app is ready in dist\NeuroCogProfile ^(zip it to share^).
  echo Install Inno Setup to also produce the one-file installer.
)
goto :eof

:error
echo Build failed.
exit /b 1
