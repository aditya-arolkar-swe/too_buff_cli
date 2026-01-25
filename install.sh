#!/bin/bash
# Toobuff CLI Installer
# This script installs toobuff using pipx (recommended) or pip

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing toobuff CLI...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check Python version (need 3.8+)
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8 or higher is required. Found Python $PYTHON_VERSION${NC}"
    exit 1
fi

# Try to use pipx (recommended)
if command -v pipx &> /dev/null; then
    echo -e "${GREEN}Using pipx to install toobuff...${NC}"
    pipx install toobuff
    echo -e "${GREEN}✓ toobuff installed successfully!${NC}"
    echo -e "${GREEN}Run 'toobuff --help' to get started.${NC}"
    exit 0
fi

# pipx not found, try to install it
echo -e "${YELLOW}pipx not found. Attempting to install pipx first...${NC}"

# Try installing pipx
if python3 -m pip install --user pipx 2>/dev/null; then
    python3 -m pipx ensurepath 2>/dev/null || true
    # Try to use pipx now
    if command -v pipx &> /dev/null; then
        echo -e "${GREEN}Using pipx to install toobuff...${NC}"
        pipx install toobuff
        echo -e "${GREEN}✓ toobuff installed successfully!${NC}"
        echo -e "${YELLOW}Note: You may need to restart your terminal or run 'source ~/.bashrc' (or ~/.zshrc) for pipx to be in your PATH.${NC}"
        echo -e "${GREEN}Run 'toobuff --help' to get started.${NC}"
        exit 0
    fi
fi

# Fallback to pip with --user flag
echo -e "${YELLOW}Installing toobuff using pip (user install)...${NC}"
python3 -m pip install --user toobuff

# Check if installation was successful
if python3 -m toobuff --version &> /dev/null; then
    echo -e "${GREEN}✓ toobuff installed successfully!${NC}"
    echo -e "${YELLOW}Note: You may need to add ~/.local/bin to your PATH if it's not already there.${NC}"
    echo -e "${YELLOW}Add this to your ~/.bashrc or ~/.zshrc: export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo -e "${GREEN}Run 'toobuff --help' to get started.${NC}"
    exit 0
else
    echo -e "${RED}Installation completed but 'toobuff' command not found.${NC}"
    echo -e "${YELLOW}Try adding ~/.local/bin to your PATH:${NC}"
    echo -e "${YELLOW}  export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    exit 1
fi

