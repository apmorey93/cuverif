; CuVerif Studio Installer Script
; Uses Inno Setup to create professional Windows installer
; Download Inno Setup from: https://jrsoftware.org/isinfo.php
;
; Usage: 
;   1. Build exe first: python setup_exe.py
;   2. Compile this script with Inno Setup Compiler
;   3. Output: CuVerif_Studio_Setup.exe

#define MyAppName "CuVerif Studio"
#define MyAppVersion "1.0"
#define MyAppPublisher "CuVerif Project"
#define MyAppURL "https://github.com/apmorey93/cuverif"
#define MyAppExeName "CuVerif Studio.exe"

[Setup]
AppId={{YOUR-GUID-HERE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installers
OutputBaseFilename=CuVerif_Studio_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\CuVerif Studio\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\CuVerif Studio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
