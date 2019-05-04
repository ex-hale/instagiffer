rem *** Extract version from instagiffer.py ***
FOR /F "delims=" %%i IN ('findstr /r  "^INSTAGIFFER_VERSION" instagiffer.py') DO set INSTAGIFFER_VERSION=%%i
set INSTAGIFFER_VERSION=%INSTAGIFFER_VERSION:~21,4%
FOR /F "delims=" %%i IN ('findstr /r  "^INSTAGIFFER_PRERELEASE" instagiffer.py') DO set INSTAGIFFER_PRERELEASE=%%i
set INSTAGIFFER_PRERELEASE=%INSTAGIFFER_PRERELEASE:~23%
set INSTAGIFFER_PRERELEASE=%INSTAGIFFER_PRERELEASE:~1%
set INSTAGIFFER_PRERELEASE=%INSTAGIFFER_PRERELEASE:~0,-1%

echo *** Building Instagiffer v%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%***

rem *** Creates Windows executable for Instagiffer using cx_freeze

rem ***** get rid of all the old files in the build folder
rd /S /Q build

rem ***** create the exe
python setup-win-cx_freeze.py build

IF NOT ERRORLEVEL 1 GOTO no_error
pause "Freeze failed. See error log"
exit
:no_error

echo Remove unwanted files from distribution
rmdir /S /Q .\build\exe.win32-2.7\tk\demos

rem ***** Create Installer
del instagiffer*setup.exe
"C:\Program Files (x86)\Inno Setup 5\ISCC.exe" installer.iss /dMyAppVersion=%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%

rem *** Test Install. Uninstall first... ***
"C:\Program Files (x86)\Instagiffer\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES

rem *** Run Installer installation ***
instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%-setup.exe /SP- /SILENT /SUPPRESSMSGBOXES
pause "press any key once installation completes"

rem *** Quickly sanity-test the installation - just verify basic app functionality ***
"C:\Program Files (x86)\Instagiffer\instagiffer.exe"

rem *** Generate a portable release ***
xcopy  /Y /I /S  "C:\Program Files (x86)\Instagiffer" instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%
del .\instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%\unins*
copy /Y instagiffer-event.log .\instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%
"C:\Program Files\7-Zip\7z.exe" a -tzip instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%-portable.zip instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%
rmdir /S /Q instagiffer-%INSTAGIFFER_VERSION%%INSTAGIFFER_PRERELEASE%
