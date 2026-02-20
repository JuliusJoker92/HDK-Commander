#!/bin/bash

# ===================================================
#   PlayStation Home HDK Commander - Setup
#   macOS / Linux All-In-One Installer
# ===================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "==================================================="
echo "   PlayStation Home HDK Commander - Setup"
echo "   macOS / Linux All-In-One Installer"
echo "==================================================="
echo ""

# =====================================================
# 1. CHECK PREREQUISITES
# =====================================================

# Python 3
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}[OK]${NC} $PY_VERSION found."
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PY_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}[OK]${NC} $PY_VERSION found."
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR]${NC} Python 3 is not installed!"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Install with Homebrew:  brew install python3"
        echo "  Or download from:       https://www.python.org/downloads/"
    else
        echo "  Install with:  sudo apt install python3 python3-tk"
        echo "  Or:            sudo dnf install python3 python3-tkinter"
    fi
    exit 1
fi

# tkinter check (needed for the GUI)
if ! $PYTHON_CMD -c "import tkinter" &>/dev/null; then
    echo -e "${YELLOW}[WARNING]${NC} tkinter is not available!"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  macOS: Reinstall Python with Homebrew:"
        echo "    brew install python-tk@3.12"
    else
        echo "  Linux: Install tkinter:"
        echo "    Ubuntu/Debian: sudo apt install python3-tk"
        echo "    Fedora:        sudo dnf install python3-tkinter"
        echo "    Arch:          sudo pacman -S tk"
    fi
    echo ""
    echo "  Continuing setup — fix tkinter before launching the GUI."
    echo ""
fi

# Git
if command -v git &>/dev/null; then
    GIT_VERSION=$(git --version 2>&1)
    echo -e "${GREEN}[OK]${NC} $GIT_VERSION found."
else
    echo -e "${RED}[ERROR]${NC} Git is not installed!"
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Install with:  xcode-select --install"
        echo "  Or:            brew install git"
    else
        echo "  Install with:  sudo apt install git"
    fi
    exit 1
fi

# Rust / Cargo
if command -v cargo &>/dev/null; then
    CARGO_VERSION=$(cargo --version 2>&1)
    echo -e "${GREEN}[OK]${NC} $CARGO_VERSION found."
else
    echo -e "${BLUE}[INFO]${NC} Rust is not installed. Installing via rustup..."
    echo ""
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"

    if command -v cargo &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Rust installed successfully."
    else
        echo -e "${RED}[ERROR]${NC} Rust installation failed."
        echo "  Please install manually from: https://rustup.rs/"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}[OK] All prerequisites satisfied!${NC}"
echo ""

# =====================================================
# 2. CONFIGURE RUST NIGHTLY TOOLCHAIN
# =====================================================
echo "---------------------------------------------------"
echo "  Configuring Rust Nightly Toolchain (required)"
echo "---------------------------------------------------"
rustup toolchain install nightly 2>/dev/null
rustup default nightly 2>/dev/null
echo -e "${GREEN}[OK]${NC} Rust nightly toolchain active."
echo ""

# =====================================================
# 3. CLONE OR UPDATE hdk-cli
# =====================================================
echo "---------------------------------------------------"
echo "  Setting up hdk-cli (main HDK tool)"
echo "---------------------------------------------------"
if [ -d "hdk-cli" ]; then
    echo -e "${BLUE}[INFO]${NC} hdk-cli folder exists. Pulling latest..."
    cd hdk-cli
    git pull
    cd ..
else
    echo -e "${BLUE}[INFO]${NC} Cloning hdk-cli..."
    git clone https://github.com/ZephyrCodesStuff/hdk-cli
fi

if [ ! -d "hdk-cli" ]; then
    echo -e "${RED}[ERROR]${NC} Failed to clone hdk-cli!"
    exit 1
fi
echo ""

# =====================================================
# 4. BUILD hdk-cli
# =====================================================
echo "---------------------------------------------------"
echo "  Building hdk-cli (this may take a few minutes)"
echo "---------------------------------------------------"
cd hdk-cli
cargo +nightly build --release
cd ..

if [ ! -f "hdk-cli/target/release/hdk" ]; then
    echo ""
    echo -e "${RED}[ERROR]${NC} hdk-cli build failed!"
    echo "  Check the error messages above."
    exit 1
fi
echo -e "${GREEN}[OK]${NC} hdk-cli built successfully!"
echo "    Location: hdk-cli/target/release/hdk"
echo ""

# =====================================================
# 5. CLONE OR UPDATE hdk-resharc
# =====================================================
echo "---------------------------------------------------"
echo "  Setting up hdk-resharc (BAR to SHARC normalizer)"
echo "---------------------------------------------------"
if [ -d "hdk-resharc" ]; then
    echo -e "${BLUE}[INFO]${NC} hdk-resharc folder exists. Pulling latest..."
    cd hdk-resharc
    git pull
    cd ..
else
    echo -e "${BLUE}[INFO]${NC} Cloning hdk-resharc..."
    git clone https://github.com/ZephyrCodesStuff/hdk-resharc
fi

if [ ! -d "hdk-resharc" ]; then
    echo -e "${RED}[ERROR]${NC} Failed to clone hdk-resharc!"
    exit 1
fi
echo ""

# =====================================================
# 6. BUILD hdk-resharc
# =====================================================
echo "---------------------------------------------------"
echo "  Building hdk-resharc (this may take a few minutes)"
echo "---------------------------------------------------"
cd hdk-resharc
cargo +nightly build --release
cd ..

if [ ! -f "hdk-resharc/target/release/hdk-resharc" ]; then
    echo ""
    echo -e "${RED}[ERROR]${NC} hdk-resharc build failed!"
    echo "  Check the error messages above."
    exit 1
fi
echo -e "${GREEN}[OK]${NC} hdk-resharc built successfully!"
echo "    Location: hdk-resharc/target/release/hdk-resharc"
echo ""

# =====================================================
# 7. VERIFY & LAUNCH
# =====================================================
echo ""
echo "==================================================="
echo "              SETUP COMPLETE!"
echo "==================================================="
echo ""
echo "  hdk-cli:     hdk-cli/target/release/hdk"
echo "  hdk-resharc: hdk-resharc/target/release/hdk-resharc"
echo ""
echo "  Launching HDK Commander..."
echo ""

if [ -f "hdk_commander.py" ]; then
    $PYTHON_CMD hdk_commander.py
elif [ -f "hdk_launcher.py" ]; then
    $PYTHON_CMD hdk_launcher.py
else
    echo -e "${RED}[ERROR]${NC} Cannot find hdk_commander.py or hdk_launcher.py!"
    echo "  Make sure the Python script is in the same folder as this setup script."
    exit 1
fi
