@echo off
REM Build dist\SpeakDaily.exe on Windows.
REM Needs Python 3.10+ on PATH. Run from this folder:  build.bat
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :error
pyinstaller --noconfirm --clean SpeakDaily.spec || goto :error

echo.
echo Done. Your app is in dist\SpeakDaily.exe
goto :eof

:error
echo.
echo Build failed. Read the messages above.
exit /b 1
