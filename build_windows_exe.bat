@echo off
setlocal enableextensions

REM ASCII-only batch file to avoid Windows codepage issues.
REM PySide6/PyInstaller may not support bleeding-edge Python immediately (e.g. 3.14).

set PY_CMD=

echo [1/5] Detecting supported Python...
call :try_py 3.12
if not defined PY_CMD call :try_py 3.11
if not defined PY_CMD call :try_py 3.10
if not defined PY_CMD call :try_python

if not defined PY_CMD (
    echo No supported Python found.
    echo Install Python 3.10/3.11/3.12 from https://www.python.org/downloads/
    echo Tip: run "py -0p" to list installed interpreters for py launcher.
    goto :fail
)

echo Using: %PY_CMD%
%PY_CMD% -c "import sys; print(sys.version)"
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

:try_py
where py >nul 2>nul
if errorlevel 1 goto :eof
py -%~1 -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) else 1)" >nul 2>nul
if errorlevel 1 goto :eof
set PY_CMD=py -%~1
goto :eof

:try_python
where python >nul 2>nul
if errorlevel 1 goto :eof
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3,10),(3,11),(3,12)) else 1)" >nul 2>nul
if errorlevel 1 goto :eof
set PY_CMD=python
goto :eof

:fail
echo Build failed. Please check the errors above.
pause
exit /b 1

:end
pause
endlocal
