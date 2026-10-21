@echo off
rem EasyRead launcher for Windows. First run creates .venv and installs; later runs just start.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
rem Share data (library, config, prefs) with the installed desktop app
set EASYREAD_HOME=%USERPROFILE%\EasyRead
if exist ".venv\Scripts\pythonw.exe" goto run

echo Setting up EasyRead (first run only, about a minute)...
where uv >nul 2>nul
if %errorlevel%==0 (
  uv venv .venv --python 3.12 || goto fail
  uv pip install --python .venv\Scripts\python.exe -e . || goto fail
  goto run
)
where py >nul 2>nul
if %errorlevel%==0 ( py -3 -m venv .venv ) else ( python -m venv .venv )
if not exist ".venv\Scripts\python.exe" goto nopython
".venv\Scripts\python.exe" -m pip install -q -e . || goto fail

:run
rem Optional Google Drive sync via rclone: sync in the background right after start, again after 10 minutes without changes, push after EasyRead closes.
rem Skipped unless rclone is installed and the remote (default "gdrive") is set up with "rclone config".
if not defined EASYREAD_REMOTE set "EASYREAD_REMOTE=gdrive:EasyRead/library"
set "SYNC_LOCAL=%EASYREAD_HOME%\library"
set "SYNC_MARK=%EASYREAD_HOME%\.rclone-bisync-ready"
rem "start.cmd --sync" runs one sync only; scripts\sync_watch.py calls it while EasyRead is open.
if /i "%~1"=="--sync" goto sync
where rclone >nul 2>nul || goto launch
for /f "tokens=1 delims=:" %%r in ("%EASYREAD_REMOTE%") do set "SYNC_NAME=%%r"
rclone listremotes | findstr /b /i /c:"%SYNC_NAME%:" >nul || goto launch
rem Reopen this script in a minimized window; it stays in the taskbar until the last sync is done.
if /i not "%~1"=="--min" (
  start "EasyRead sync" /min "%ComSpec%" /c ""%~f0" --min"
  exit /b 0
)
echo EasyRead is running. Leave this window minimized: the library syncs now in the background, after 10 minutes without changes, and again after EasyRead closes.
".venv\Scripts\python.exe" scripts\sync_watch.py "%SYNC_LOCAL%" "%~f0" -- ".venv\Scripts\pythonw.exe" -m easyread serve --open --exit-on-close
echo Syncing library back to %EASYREAD_REMOTE% ...
call :sync
if not errorlevel 1 exit /b 0
echo.
echo Sync after exit failed, see above. Changes are kept locally and will sync next time.
pause
exit /b 1

:launch
start "" ".venv\Scripts\pythonw.exe" -m easyread serve --open --exit-on-close
exit /b 0

:sync
if not exist "%SYNC_LOCAL%" mkdir "%SYNC_LOCAL%"
rclone mkdir "%EASYREAD_REMOTE%" || exit /b 1
rem First run on this computer needs --resync to build the baseline; newer copy wins on both sides.
set "SYNC_FIRST="
if not exist "%SYNC_MARK%" set "SYNC_FIRST=--resync --resync-mode newer"
rclone bisync "%EASYREAD_REMOTE%" "%SYNC_LOCAL%" %SYNC_FIRST% --resilient --recover --max-lock 5m --conflict-resolve newer --transfers 16 --checkers 16 --fast-list --exclude ".easyread-lock.json" --exclude ".easyread-probe-*" --exclude ".easyread-copy-*/**" || exit /b 1
if not exist "%SYNC_MARK%" type nul > "%SYNC_MARK%"
exit /b 0

:nopython
echo.
echo Python 3.10 or newer is required. Download it from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH" during install), then double-click start.cmd again.
pause
exit /b 1

:fail
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
