@echo off
title HDK Commander - First Time Setup (Nightly)
color 0b
echo ===================================================
echo      PlayStation Home HDK - All-In-One Setup
echo ===================================================
echo.

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Please install Python from https://www.python.org/
    pause
    exit
)
echo [OK] Python found.

:: 2. Check for Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed!
    echo Please install Git from https://git-scm.com/
    pause
    exit
)
echo [OK] Git found.

:: 3. Check for Rust (Cargo)
cargo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Rust is missing. Installing Rustup...
    curl -sSf -o rustup-init.exe https://win.rustup.rs/x86_64
    echo [INFO] Launching Rust Installer...
    echo.
    echo [IMPORTANT] PRESS '1' AND ENTER WHEN PROMPTED.
    echo.
    rustup-init.exe
    del rustup-init.exe
    
    echo.
    echo [IMPORTANT] Rust installed. 
    echo We need to restart the script to load the new path.
    echo Please CLOSE this window and run setup.bat again.
    pause
    exit
)
echo [OK] Rust found.

:: 4. Configure Rust Nightly (REQUIRED for HDK)
echo [INFO] Configuring Rust Nightly Toolchain...
rustup toolchain install nightly
rustup default nightly
echo [OK] Rust Nightly active.

:: 5. Clone or Update hdk-cli
if exist "hdk-cli" (
    echo [INFO] hdk-cli folder found. Updating...
    cd hdk-cli
    git pull
    cd ..
) else (
    echo [INFO] Cloning hdk-cli repository...
    git clone https://github.com/ZephyrCodesStuff/hdk-cli
)

:: 6. Build the Tool
echo.
echo [INFO] Building HDK Binary (Release Mode)...
echo This might take a few minutes. Please wait.
cd hdk-cli
cargo +nightly build --release
cd ..

:: 7. Verify and Launch
if exist "hdk-cli\target\release\hdk.exe" (
    echo.
    echo ===================================================
    echo      SETUP COMPLETE! LAUNCHING COMMANDER...
    echo ===================================================
    echo.
    python hdk_launcher.py
) else (
    echo.
    echo [ERROR] Build failed. 
    echo Please check the error messages above.
    pause
)