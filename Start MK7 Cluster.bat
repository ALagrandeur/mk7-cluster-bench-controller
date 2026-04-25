@echo off
setlocal
title MK7 Cluster Bench Controller

REM ---- Kill any existing server holding port 5000 (otherwise new server can't bind) ----
echo Stopping any existing MK7 Cluster server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000 .*LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
REM Give Windows a moment to release the port
ping -n 2 127.0.0.1 >nul

REM ---- Launch the Python server in a separate console (minimized, with logs) ----
start "MK7 Cluster Server" /MIN cmd /c "cd /d "%~dp0webui" && (where py >nul 2>&1 && (py -3 -m pip install --quiet --disable-pip-version-check -r requirements.txt && py -3 server.py) || (python -m pip install --quiet --disable-pip-version-check -r requirements.txt && python server.py)) & pause"

REM ---- Wait for the server to be reachable, then open the browser ----
echo Waiting for server to start...
set /a tries=0
:wait
set /a tries+=1
if %tries% gtr 30 (
  echo Server did not start in time. Open http://127.0.0.1:5000/ manually once it is up.
  pause
  exit /b 1
)
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 http://127.0.0.1:5000/).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto wait
)

start "" "http://127.0.0.1:5000/"
endlocal
