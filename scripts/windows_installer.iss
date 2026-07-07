; Inno Setup script for the Dienstplaner Windows installer.
;
; Prerequisites (Windows only):
;   1. Build the PyInstaller distribution first:
;        py -3 -m pip install pyinstaller
;        py -3 scripts\build_windows_pyinstaller.py
;      This produces dist\Dienstplaner\Dienstplaner.exe.
;   2. Install Inno Setup 6 (https://jrsoftware.org/isinfo.php).
;   3. Compile this script, passing the current app version:
;        iscc /DAppVersion=0.6.0 scripts\windows_installer.iss
;      (Read the version from python_dienstplaner\__init__.py so the
;      installer, the window title and the release tag stay in sync.)
;
; The compiled installer is written to dist\installer\Dienstplaner-Setup-<version>.exe.
;
; This script has been reviewed for correct Inno Setup syntax but has not
; been compiled in this environment (no Windows/Inno Setup available here).
; Verify it with a real build on Windows before shipping it to customers.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Dienstplaner"
#define AppPublisher "Dienstplanung Pro"
#define DistDir "..\dist\Dienstplaner"
#define ExeName "Dienstplaner.exe"

[Setup]
AppId={{6F2C1D8E-6E2A-4C7B-9A3D-3B7B3E7C9A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=Dienstplaner-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName} {#AppVersion}
; Requires the PyInstaller build to exist before compiling this script.
SourceDir=.

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Deliberately no [UninstallDelete] section: uninstalling must never remove
; %APPDATA%\Dienstplaner\data (the SQLite database, backups and license
; file). Only the program files installed above are removed on uninstall.
