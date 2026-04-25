@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
  py -3 server.py
) else (
  python -m pip install --quiet --disable-pip-version-check -r requirements.txt
  python server.py
)
pause
