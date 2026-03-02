; Instagiffer Installer

#define MyAppName "Instagiffer"
; #define MyAppVersion ; passed as /dMyAppVersion= on the ISCC command line
#define MyAppPublisher "Justin Todd"
#define MyAppURL "https://github.com/ex-hale/instagiffer"
#define MyAppExeName "Instagiffer.exe"

[Setup]
; Instagiffer's UUID - do not change
AppId={{13DEF8F8-5280-4555-95A4-E815C3F9540F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=instagiffer-{#MyAppVersion}-setup
SetupIconFile=..\instagiffer.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile=..\assets\installer_icon.bmp
WizardImageFile=..\assets\installer_side.bmp
WizardImageBackColor=$395976

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Instagiffer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\uninstall.ico"
Name: "{group}\Visit GitHub"; Filename: "{#MyAppURL}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
