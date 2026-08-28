@echo off
rem Talkar RPG launcher (Windows). First run installs dependencies.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% -m pip install -q -r requirements.txt
%PY% server.py
pause
