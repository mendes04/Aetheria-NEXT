@echo off
setlocal
cd /d "%~dp0"
where git >nul 2>&1
if errorlevel 1 (
    echo Git is not installed. Install Git for Windows first.
    pause
    exit /b 1
)
echo Publish AETHERIA NEXT to a DEDICATED GitHub repository.
echo IMPORTANT: Create an empty repository in your GitHub account first.
echo Do not use your unrelated CHURNIQ repository.
set /p REPO_URL=Paste the full Aetheria repository HTTPS URL: 
if "%REPO_URL%"=="" (
    echo Cancelled: missing repository URL.
    exit /b 1
)
if not exist .git\NUL git init
git add .
git diff --cached --quiet
if errorlevel 1 git commit -m "feat: Aetheria NEXT motion arcade expansion"
git branch -M main
git remote get-url origin >nul 2>&1
if not errorlevel 1 (
    echo This folder already has an origin remote. Review it manually before pushing.
    git remote -v
    pause
    exit /b 1
)
git remote add origin "%REPO_URL%"
echo Confirm that this is YOUR AETHERIA repo: %REPO_URL%
choice /M "Push main branch to this GitHub remote"
if errorlevel 2 exit /b 1
git push -u origin main
if errorlevel 1 (
    echo Push failed: verify repo URL and GitHub account permissions.
    pause
    exit /b 1
)
echo Published successfully.
pause
