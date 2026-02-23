@echo off
setlocal enableextensions

REM ASCII-only batch file to avoid Windows codepage issues.

echo [1/4] Checking Python launcher...
where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py -3
) else (
    set PY_CMD=python
)

echo [2/4] Installing dependencies...
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail

%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [3/4] Building online.exe...
%PY_CMD% -m PyInstaller --noconfirm --onefile --windowed --name online main.py
if errorlevel 1 goto :fail

echo [4/4] Done.
echo Output: dist\online.exe

goto :end

:fail
echo Build failed. Please check the errors above.
exit /b 1

:end
pause
endlocal
