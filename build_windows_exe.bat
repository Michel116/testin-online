@echo off
setlocal enableextensions

REM ASCII-only batch file to avoid Windows codepage issues.
REM PySide6/PyInstaller may not support bleeding-edge Python immediately (e.g. 3.14).

echo [1/5] Detecting supported Python...
set PY_CMD=

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -V >nul 2>nul
    if %errorlevel%==0 set PY_CMD=py -3.12

    if not defined PY_CMD (
        py -3.11 -V >nul 2>nul
        if %errorlevel%==0 set PY_CMD=py -3.11
    )

    if not defined PY_CMD (
        py -3.10 -V >nul 2>nul
        if %errorlevel%==0 set PY_CMD=py -3.10
    )
)

if not defined PY_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 set PY_CMD=python
)

if not defined PY_CMD (
    echo No supported Python found.
    echo Install Python 3.10/3.11/3.12 from https://www.python.org/downloads/
    goto :fail
)

echo Using: %PY_CMD%
%PY_CMD% -V
if errorlevel 1 goto :fail

echo [2/5] Upgrading pip...
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/5] Installing dependencies...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency install failed.
    echo If you are on Python 3.14, install Python 3.12 and run this script again.
    goto :fail
)

echo [4/5] Building online.exe...
%PY_CMD% -m PyInstaller --noconfirm --onefile --windowed --name online main.py
if errorlevel 1 goto :fail

echo [5/5] Done.
echo Output: dist\online.exe

goto :end

:fail
echo Build failed. Please check the errors above.
pause
exit /b 1

:end
pause
endlocal
