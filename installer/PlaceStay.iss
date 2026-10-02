#define MyAppName "Place. Stay."
#define MyAppShortcut "Place Stay"
#define MyAppExeName "PlaceStay.exe"
#ifndef MyAppVersion
  #include "version.iss"
#endif

[Setup]
AppId={{A7E4C91B-3F2A-4D18-9C6E-8B1F5A2D7E03}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Place. Stay.
AppCopyright=Place. Stay.
AppMutex=PlaceStay.SingleInstance
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} Setup
DefaultDirName={autopf}\Place Stay
DefaultGroupName=Place Stay
DisableProgramGroupPage=yes
DisableReadyPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=out
OutputBaseFilename=PlaceStay-{#MyAppVersion}-Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
WizardStyle=modern dark includetitlebar
WizardSizePercent=110,100
WizardImageFile=assets\wizard-side-*.png
WizardSmallImageFile=assets\wizard-small-*.png
WizardImageBackColor=$101112
WizardSmallImageBackColor=$101112
WizardBackColor=$101112
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
SetupMutex=PlaceStay.Setup
ShowLanguageDialog=no
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppTitle=Place. Stay.
SetupWindowTitle=Install Place. Stay.
UninstallAppTitle=Remove Place. Stay.
WelcomeLabel1=Place. Stay.
WelcomeLabel2=This puts the app on this PC. After that, save a layout and your windows come back to the screens you chose.
FinishedHeadingLabel=Place. Stay. is ready
FinishedLabel=You can open it from the Start menu. It can wait in the tray and put windows back when they open.
ClickFinish=Click Finish to open Place. Stay.
ConfirmUninstall=Remove Place. Stay. from this PC? Your saved layouts stay in your user folder.
ExitSetupMessage=Setup is not complete. If you stop now, Place. Stay. will not be installed.%n%nYou can run Setup again later.%n%nStop Setup?
WizardInstalling=Installing
StatusExtractFiles=Putting files in place…
ButtonInstall=&Install
ButtonBrowse=&Browse…

[Tasks]
Name: "desktopicon"; Description: "Put a shortcut on the desktop"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\PlaceStay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppShortcut}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Keep windows on the screens you chose"
Name: "{autodesktop}\{#MyAppShortcut}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Keep windows on the screens you chose"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open Place. Stay."; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userstartup}\Place Stay.lnk"
Type: files; Name: "{userstartup}\Sticky Desktop.lnk"

[Code]
const
  WebView2Guid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

var
  DownloadPage: TDownloadWizardPage;

function WebView2Installed: Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WebView2Guid, 'pv', Version) or
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2Guid, 'pv', Version) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WebView2Guid, 'pv', Version);
  if Result then
    Result := (Version <> '') and (Version <> '0.0.0.0');
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if Progress = ProgressMax then
    Log(Format('Downloaded %s', [FileName]))
  else if ProgressMax > 0 then
    Log(Format('Downloading %s: %d of %d', [FileName, Progress, ProgressMax]));
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  Installer: String;
begin
  Result := '';
  NeedsRestart := False;
  if WebView2Installed then
    Exit;

  if DownloadPage = nil then
    DownloadPage := CreateDownloadPage('Almost there', 'Place. Stay. needs the Edge WebView2 runtime, which is missing on this PC.', @OnDownloadProgress);

  DownloadPage.Clear;
  DownloadPage.Add('https://go.microsoft.com/fwlink/p/?LinkId=2124703', 'MicrosoftEdgeWebView2Setup.exe', '');
  DownloadPage.Show;
  try
    try
      DownloadPage.Download;
      Installer := ExpandConstant('{tmp}\MicrosoftEdgeWebView2Setup.exe');
      if not FileExists(Installer) then
      begin
        Result := 'Could not download Microsoft Edge WebView2.';
        Exit;
      end;
      if not Exec(Installer, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        if not ShellExec('runas', Installer, '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
        begin
          Result := 'Could not start the WebView2 installer.';
          Exit;
        end;
      end;
      if (ResultCode <> 0) and (ResultCode <> 3010) then
        Result := 'WebView2 setup did not finish cleanly. Install it from Microsoft, then run Place. Stay. Setup again.';
    except
      Result := GetExceptionMessage;
    end;
  finally
    DownloadPage.Hide;
  end;
end;
