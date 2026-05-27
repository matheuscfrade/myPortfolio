#define MyAppName "Portfolio Profissional"
#define MyAppVersion "1.0.4"
#define MyAppExeName "PortfolioProfissional.exe"

[Setup]
AppId={{3B0D59D8-26F4-4A19-9B0E-72B2F9D2C7A1}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\Portfolio Profissional
DefaultGroupName=Portfolio Profissional
OutputDir=..\dist-installer
OutputBaseFilename=PortfolioProfissionalSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\PortfolioProfissional\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Abrir Portfolio Profissional"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\Portfolio Profissional"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\Abrir pasta de dados"; Filename: "{localappdata}\Portfolio Profissional"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Portfolio Profissional"; Flags: nowait postinstall skipifsilent

[Code]
var
  IdentityPage: TInputQueryWizardPage;

function JsonEscape(Value: String): String;
begin
  StringChangeEx(Value, '\', '\\', True);
  StringChangeEx(Value, '"', '\"', True);
  Result := Value;
end;

procedure InitializeWizard;
begin
  IdentityPage := CreateInputQueryPage(
    wpSelectTasks,
    'Identificação do portfólio',
    'Informe como seu portfólio deve aparecer no aplicativo.',
    'Esses dados são definidos na instalação e usados pelo Admin e pela visualização pública.'
  );
  IdentityPage.Add('Nome exibido:', False);
  IdentityPage.Add('Subtítulo:', False);
  IdentityPage.Add('Título do site:', False);
  IdentityPage.Values[0] := 'Seu Nome';
  IdentityPage.Values[1] := 'Portfolio Profissional';
  IdentityPage.Values[2] := 'Portfolio Documental';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = IdentityPage.ID then
  begin
    if Trim(IdentityPage.Values[0]) = '' then
    begin
      MsgBox('Informe o nome exibido.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: String;
  ConfigFile: String;
  Json: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigDir := ExpandConstant('{localappdata}\Portfolio Profissional\config');
    ForceDirectories(ConfigDir);
    ConfigFile := ConfigDir + '\app.json';
    Json :=
      '{' + #13#10 +
      '  "displayName": "' + JsonEscape(IdentityPage.Values[0]) + '",' + #13#10 +
      '  "subtitle": "' + JsonEscape(IdentityPage.Values[1]) + '",' + #13#10 +
      '  "portfolioTitle": "' + JsonEscape(IdentityPage.Values[2]) + '",' + #13#10 +
      '  "organization": ""' + #13#10 +
      '}';
    SaveStringToFile(ConfigFile, Json, False);
  end;
end;
