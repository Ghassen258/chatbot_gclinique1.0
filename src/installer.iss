; installer.iss

[Setup]
AppName=ChatbotApp
AppVersion=1.0
DefaultDirName={pf}\ChatbotApp
DefaultGroupName=ChatbotApp
OutputBaseFilename=ChatbotAppInstaller
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt  ; Optional: Add a license file

[Files]
; Include the onefile executable
Source: "dist\ChatbotApp.exe"; DestDir: "{app}"; Flags: ignoreversion

; Include driver installers
Source: "src\drivers\msodbcsql17.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "src\drivers\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

; Include Visual C++ Redistributable installer
Source: "path\to\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
; Install Visual C++ Redistributable silently
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /install"; StatusMsg: "Installing Visual C++ Redistributables..."; Flags: waituntilterminated

; Install ODBC Driver silently
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\msodbcsql17.msi"" /quiet /norestart"; StatusMsg: "Installing Microsoft ODBC Driver..."; Flags: waituntilterminated

; Install WebView2 Runtime silently
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: waituntilterminated

; Launch the application after installation
Filename: "{app}\ChatbotApp.exe"; Description: "Launch ChatbotApp"; Flags: nowait postinstall skipifsilent
