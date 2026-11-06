#define MyAppName "ndhmdSuite"
#define MyAppVersion "4.35"
#define MyAppPublisher "ndhmd"
#define MyAppExeName "ndhmdwriter.exe"

[Setup]
AppId={{8F5B3C71-9A2E-4C23-8B3B-5F1A8A7A6E9D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 모든 사용자 / 현재 사용자 선택 옵션 활성화
PrivilegesRequiredOverridesAllowed=commandline dialog
PrivilegesRequired=admin
OutputBaseFilename=ndhmdSuite_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; 기존 dist 폴더 복사 구문
Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 1. Resources 폴더를 %userprofile%\ndhmd4tex\resources\ 아래로 복사
Source: "Resources\*"; DestDir: "{%USERPROFILE}\ndhmd4tex\"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. ksruncltex 폴더 복사
Source: "ksruncltex\*"; DestDir: "{app}\ksruncltex"; Flags: ignoreversion recursesubdirs createallsubdirs

; 3. initconfig.exe 복사 (install.iss와 같은 폴더에 위치한 파일 대상)[cite: 1]
; Source: "initconfig.exe"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; 기존 GUI 앱 실행 구문
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; 2. install.bat 실행 (관리자 권한 처리 적용)
Filename: "{app}\ksruncltex\install.bat"; \
  StatusMsg: "ksruncltex 설치 요소를 등록 중입니다..."; \
  Flags: runhidden runascurrentuser;

; 3. initconfig.exe 설치 후 실행 (관리자 권한 불필요)[cite: 1]
; Filename: "{app}\initconfig.exe"; \
;  StatusMsg: "환경 설정을 초기화하는 중입니다..."; \
;  Flags: waituntilterminated;

[Icons]
; 시작 메뉴 및 바탕화면 아이콘 (GUI인 ndhmdwriter.exe 기준)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Code]
// =========================================================================
// 1. 기존 설치 버전 감지 및 자동 삭제 (재설치 처리)
// =========================================================================
function InitializeSetup(): Boolean;
var
  UninstallPath: String;
  ResultCode: Integer;
begin
  Result := True;
  
  // HKLM 및 HKCU 양쪽에서 기존 설치 언인스톨 경로 확인
  if not RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F5B3C71-9A2E-4C23-8B3B-5F1A8A7A6E9D}_is1', 'UninstallString', UninstallPath) then
  begin
    RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F5B3C71-9A2E-4C23-8B3B-5F1A8A7A6E9D}_is1', 'UninstallString', UninstallPath);
  end;

  if UninstallPath <> '' then
  begin
    if MsgBox('이전에 설치된 {#MyAppName} 버전이 존재합니다.' + #13#10 + 
              '이전 버전을 삭제하고 계속 진행하시겠습니까?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // 큰따옴표 제거 처리
      UninstallPath := RemoveQuotes(UninstallPath);
      // 기존 언인스톨러 조용히 실행 (/SILENT)
      if Exec(UninstallPath, '/SILENT /NORESTART', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        Result := True;
      end
      else
      begin
        MsgBox('기존 버전 삭제 실패. 설치를 중단합니다.', mbError, MB_OK);
        Result := False;
      end;
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// =========================================================================
// 2. PATH 환경 변수 추가/삭제 도우미 함수들
// =========================================================================
function GetPathRootKey(): Integer;
begin
  if IsAdminInstallMode then
    Result := HKEY_LOCAL_MACHINE
  else
    Result := HKEY_CURRENT_USER;
end;

function GetPathSubKey(): String;
begin
  if IsAdminInstallMode then
    Result := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
  else
    Result := 'Environment';
end;

procedure AddToPath(PathToAdd: String);
var
  OldPath, NewPath: String;
  RootKey: Integer;
  SubKey: String;
begin
  RootKey := GetPathRootKey();
  SubKey := GetPathSubKey();

  if not RegQueryStringValue(RootKey, SubKey, 'Path', OldPath) then
    OldPath := '';

  // 이미 PATH에 포함되어 있는지 검사 (대소문자 미구분)
  if Pos(';' + Uppercase(PathToAdd) + ';', ';' + Uppercase(OldPath) + ';') = 0 then
  begin
    if (OldPath <> '') and (Copy(OldPath, Length(OldPath), 1) <> ';') then
      OldPath := OldPath + ';';
    
    NewPath := OldPath + PathToAdd;
    RegWriteStringValue(RootKey, SubKey, 'Path', NewPath);
  end;
end;

procedure RemoveFromPath(PathToRemove: String);
var
  OldPath, NewPath: String;
  P, L: Integer;
  RootKey: Integer;
  SubKey: String;
begin
  RootKey := GetPathRootKey();
  SubKey := GetPathSubKey();

  if RegQueryStringValue(RootKey, SubKey, 'Path', OldPath) then
  begin
    P := Pos(Uppercase(PathToRemove), Uppercase(OldPath));
    if P > 0 then
    begin
      L := Length(PathToRemove);
      
      // 경로 뒤에 세미콜론이 붙어있는 경우 함께 제거
      if (P + L <= Length(OldPath)) and (OldPath[P + L] = ';') then
        L := L + 1;
        
      Delete(OldPath, P, L);
      
      // 맨 앞이나 맨 뒤에 세미콜론 남는 현상 정리
      if (Length(OldPath) > 0) and (OldPath[1] = ';') then
        Delete(OldPath, 1, 1);
      if (Length(OldPath) > 0) and (OldPath[Length(OldPath)] = ';') then
        Delete(OldPath, Length(OldPath), 1);
        
      NewPath := OldPath;
      RegWriteStringValue(RootKey, SubKey, 'Path', NewPath);
    end;
  end;
end;

// =========================================================================
// 3. 설치 완료 시 PATH 추가 & 언인스톨 시 PATH 제거 이벤트 처리
// =========================================================================
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 설치 폴더({app})를 PATH에 추가
    AddToPath(ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // 언인스톨 완료 후 PATH에서 제거
    RemoveFromPath(ExpandConstant('{app}'));
  end;
end;