; Inno Setup script to build a Windows installer for PhotoFiler
; Requirements (on Windows):
; 1) Build the app first with PyInstaller so dist\PhotoFiler\PhotoFiler.exe exists
;    e.g., run build-windows-runner.ps1 from project root (generates the EXE with offline model)
; 2) Install Inno Setup (https://jrsoftware.org/isinfo.php) and ensure iscc.exe is on PATH

[Setup]
AppName=PhotoFiler
AppVersion=1.0.0
AppPublisher=PhotoFiler
DefaultDirName={localappdata}\Programs\PhotoFiler
DefaultGroupName=PhotoFiler
DisableDirPage=no
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64
Compression=lzma
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=PhotoFiler-Setup
SetupIconFile=packaging\icons\photo_filer.ico
UninstallDisplayIcon={app}\PhotoFiler.exe
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
; Main executable and all dependencies (built by PyInstaller)
Source: "dist\PhotoFiler\PhotoFiler.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\PhotoFiler\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; App icon for shortcuts
Source: "packaging\icons\photo_filer.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{autoprograms}\PhotoFiler"; Filename: "{app}\PhotoFiler.exe"; WorkingDir: "{app}"; IconFilename: "{app}\photo_filer.ico"
; Desktop shortcut
Name: "{commondesktop}\PhotoFiler"; Filename: "{app}\PhotoFiler.exe"; WorkingDir: "{app}"; IconFilename: "{app}\photo_filer.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
; Offer to launch after install
Filename: "{app}\PhotoFiler.exe"; Description: "Launch PhotoFiler"; Flags: nowait postinstall skipifsilent unchecked
