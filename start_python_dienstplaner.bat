@echo off
setlocal

rem Startet die Python-Version des Dienstplaners unter Windows.
rem Das Arbeitsverzeichnis wird auf den Ordner dieser Batch-Datei gesetzt,
rem damit relative Pfade wie python_dienstplaner\data stabil funktionieren.
cd /d "%~dp0"

if not exist "start_python_dienstplaner.py" (
    echo Fehler: start_python_dienstplaner.py wurde nicht gefunden.
    echo Bitte starten Sie diese Datei aus dem Projektordner.
    pause
    exit /b 1
)

set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>&1 && set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Fehler: Es wurde keine Python-Installation gefunden.
    echo Installieren Sie Python 3 und aktivieren Sie optional "Add python.exe to PATH".
    pause
    exit /b 1
)

%PYTHON_CMD% "start_python_dienstplaner.py"
set "APP_EXIT_CODE=%ERRORLEVEL%"

if not "%APP_EXIT_CODE%"=="0" (
    echo.
    echo Die Anwendung wurde mit Fehlercode %APP_EXIT_CODE% beendet.
)

pause
exit /b %APP_EXIT_CODE%
