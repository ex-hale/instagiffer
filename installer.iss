; Instagiffer Installer

#define MyAppName "Instagiffer"
; #define MyAppVersion ; passed as compiler option
#define MyAppPublisher "Justin Todd"
#define MyAppURL "http://www.instagiffer.com"
#define MyAppExeName "instagiffer.exe"

[Setup]
; Instagiffer's uuid
AppId={{13DEF8F8-5280-4555-95A4-E815C3F9540F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName}-{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=.\
OutputBaseFilename=instagiffer-{#MyAppVersion}-setup
SetupIconFile=.\Instagiffer.ico
Compression=lzma
SolidCompression=yes

WizardSmallImageFile=.\doc\graphics\installer_icon.bmp
;WizardSmallImageBackColor=$395976
WizardImageBackColor=$395976
WizardImageStretch=yes
WizardImageFile=.\doc\graphics\installer_side.bmp


[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
;Source: ".\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify
Source: ".\build\exe.win32-2.7\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Permissions: users-modify

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Instagiffer"; Filename: "{uninstallexe}"; IconFilename: "{app}\uninstall.ico"
Name: "{group}\Visit www.instagiffer.com"; Filename: "http://www.instagiffer.com"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
;[Run]
;Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

