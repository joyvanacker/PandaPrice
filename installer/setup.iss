; Inno Setup script voor Bambu Price Calculator
; Vereist: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)

#define AppName "Bambu Price Calculator"
#define AppVersion "0.1.0"
#define AppPublisher "joyvanacker"
#define AppExeName "BambuPriceCalculator.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/joyvanacker/PandaPrice
AppSupportURL=https://github.com/joyvanacker/PandaPrice/issues
AppUpdatesURL=https://github.com/joyvanacker/PandaPrice/releases
DefaultDirName={autopf}\BambuPriceCalculator
DefaultGroupName={#AppName}
OutputDir=..\dist\installer
OutputBaseFilename=BambuPriceCalculator-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
