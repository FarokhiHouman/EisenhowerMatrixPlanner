@echo off
REM Check if the current folder is a Git repository
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo This folder is not a Git repository.
    pause
    exit /b 1
)

REM Define output file path (fixed name in current directory)
set "OUTPUT_FILE=GitDiff.txt"

REM Delete the file if it exists
if exist "%OUTPUT_FILE%" del "%OUTPUT_FILE%"

REM Save unstaged changes
echo =============================== >> "%OUTPUT_FILE%"
echo Unstaged Changes (git diff): >> "%OUTPUT_FILE%"
echo =============================== >> "%OUTPUT_FILE%"
git diff -U2 >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"

REM Save staged changes
echo =============================== >> "%OUTPUT_FILE%"
echo Staged Changes (git diff --cached): >> "%OUTPUT_FILE%"
echo =============================== >> "%OUTPUT_FILE%"
git diff --cached -U2 >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"
echo. >> "%OUTPUT_FILE%"

echo Done. Diff saved to "%OUTPUT_FILE%"

