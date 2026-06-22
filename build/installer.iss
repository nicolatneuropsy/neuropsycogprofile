; ============================================================
; Inno Setup script: wraps the PyInstaller output folder into a single
; per-user installer (no administrator rights needed).
;   Compile on Windows:  iscc build\installer.iss
;   Output:              dist\NeuroCogProfile-windows-setup.exe
;
; Note: the app needs the Microsoft Edge WebView2 runtime, which ships
; with current Windows 10 and 11. If a target machine lacks it, install
; the free Evergreen runtime from Microsoft once.
; ============================================================

#define AppName "NeuroCogProfile"
#define AppVersion "1.0.0"
#define AppPublisher "NeuroCogProfile"
#define AppExe "NeuroCogProfile.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename={#AppName}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
