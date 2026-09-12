; Inno Setup script for HP-12C Simulator.
; Requires Inno Setup (ISCC.exe) to compile: https://jrsoftware.org/isinfo.php
; This project's own build does not depend on this file -- the .exe in
; dist/ already runs standalone with no installation. This installer is an
; optional convenience wrapper (Start Menu shortcut, uninstaller entry).
;
; Build with:  ISCC installer\setup.iss
; Output:      installer\Output\HP12C-Simulator-Setup.exe

#define MyAppName "HP-12C Simulator"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Projeto HP-12C Simulator (não oficial)"
#define MyAppExeName "HP12C-Simulator.exe"

[Setup]
AppId={{B4E9E9D9-6B7B-4B7B-9C1D-9F1F6B0E4C21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HP12C-Simulator
DefaultGroupName=HP-12C Simulator
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=HP12C-Simulator-Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\assets\icon.ico
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\HP12C-Simulator.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\HP-12C Simulator"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar HP-12C Simulator"; Filename: "{uninstallexe}"
Name: "{autodesktop}\HP-12C Simulator"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir HP-12C Simulator"; Flags: nowait postinstall skipifsilent
