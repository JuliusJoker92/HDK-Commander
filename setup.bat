@echo off
title HDK Commander - First Time Setup
color 0b
echo ===================================================
echo      PlayStation Home HDK Commander - Setup
echo         Windows All-In-One Installer
echo ===================================================
echo.

:: =====================================================
:: 1. CHECK PREREQUISITES
:: =====================================================

:: Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo   Download it from: https://www.python.org/downloads/
    echo   IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause
    exit
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i found.

:: Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed!
    echo.
    echo   Download it from: https://git-scm.com/downloads/win
    echo.
    pause
    exit
)
for /f "tokens=*" %%i in ('git --version 2^>^&1') do echo [OK] %%i found.

:: Rust / Cargo
cargo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Rust is not installed. Installing Rustup...
    echo.
    curl -sSf -o rustup-init.exe https://win.rustup.rs/x86_64
    if not exist rustup-init.exe (
        echo [ERROR] Failed to download Rust installer.
        echo   Please install manually from: https://rustup.rs/
        pause
        exit
    )
    echo ===================================================
    echo   Rust Installer will now launch.
    echo   When prompted, press 1 and then Enter.
    echo ===================================================
    echo.
    rustup-init.exe
    del rustup-init.exe 2>nul
    echo.
    echo ===================================================
    echo   Rust has been installed, but your terminal needs
    echo   to reload the PATH before we can continue.
    echo.
    echo   CLOSE THIS WINDOW and run setup.bat AGAIN.
    echo ===================================================
    pause
    exit
)
for /f "tokens=*" %%i in ('cargo --version 2^>^&1') do echo [OK] %%i found.

echo.
echo [OK] All prerequisites satisfied!
echo.

:: =====================================================
:: 2. CONFIGURE RUST NIGHTLY TOOLCHAIN
:: =====================================================
echo ---------------------------------------------------
echo   Configuring Rust Nightly Toolchain (required)
echo ---------------------------------------------------
rustup toolchain install nightly >nul 2>&1
rustup default nightly >nul 2>&1
echo [OK] Rust nightly toolchain active.
echo.

:: =====================================================
:: 3. CLONE OR UPDATE hdk-cli
:: =====================================================
echo ---------------------------------------------------
echo   Setting up hdk-cli (main HDK tool)
echo ---------------------------------------------------
if exist "hdk-cli" (
    echo [INFO] hdk-cli folder exists. Pulling latest...
    cd hdk-cli
    git pull
    cd ..
) else (
    echo [INFO] Cloning hdk-cli...
    git clone https://github.com/ZephyrCodesStuff/hdk-cli
)
if not exist "hdk-cli" (
    echo [ERROR] Failed to clone hdk-cli!
    pause
    exit
)
echo.

:: =====================================================
:: 4. BUILD hdk-cli
:: =====================================================
echo ---------------------------------------------------
echo   Building hdk-cli (this may take a few minutes)
echo ---------------------------------------------------
cd hdk-cli
cargo +nightly build --release
cd ..

if not exist "hdk-cli\target\release\hdk.exe" (
    echo.
    echo [ERROR] hdk-cli build failed!
    echo   Check the error messages above.
    pause
    exit
)
echo [OK] hdk-cli built successfully!
echo     Location: hdk-cli\target\release\hdk.exe
echo.

:: =====================================================
:: 5. CLONE OR UPDATE hdk-resharc
:: =====================================================
echo ---------------------------------------------------
echo   Setting up hdk-resharc (BAR to SHARC normalizer)
echo ---------------------------------------------------
if exist "hdk-resharc" (
    echo [INFO] hdk-resharc folder exists. Pulling latest...
    cd hdk-resharc
    git pull
    cd ..
) else (
    echo [INFO] Cloning hdk-resharc...
    git clone https://github.com/ZephyrCodesStuff/hdk-resharc
)
if not exist "hdk-resharc" (
    echo [ERROR] Failed to clone hdk-resharc!
    pause
    exit
)
echo.

:: =====================================================
:: 6. BUILD hdk-resharc
:: =====================================================
echo ---------------------------------------------------
echo   Building hdk-resharc (this may take a few minutes)
echo ---------------------------------------------------
cd hdk-resharc
cargo +nightly build --release
cd ..

if not exist "hdk-resharc\target\release\hdk-resharc.exe" (
    echo.
    echo [ERROR] hdk-resharc build failed!
    echo   Check the error messages above.
    pause
    exit
)
echo [OK] hdk-resharc built successfully!
echo     Location: hdk-resharc\target\release\hdk-resharc.exe
echo.

:: =====================================================
:: 7. VERIFY & LAUNCH
:: =====================================================
echo.
echo ===================================================
echo               SETUP COMPLETE!
echo ===================================================
echo.
echo   hdk-cli:     hdk-cli\target\release\hdk.exe
echo   hdk-resharc: hdk-resharc\target\release\hdk-resharc.exe
echo.
echo   Launching HDK Commander...
echo.

if exist "hdk_commander.py" (
    python hdk_commander.py
) else if exist "hdk_launcher.py" (
    python hdk_launcher.py
) else (
    echo [ERROR] Cannot find hdk_commander.py or hdk_launcher.py!
    echo   Make sure the Python script is in the same folder as this setup.bat
    pause
    exit
)
