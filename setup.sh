#!/bin/bash
# Setup script for TensorNext - Distributed AI Runtime PoC
# This script sets up a virtual environment and installs dependencies

set -e  # Exit on error

echo "=========================================="
echo "TensorNext Setup Script"
echo "=========================================="
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Extract major.minor version
PYTHON_MAJOR_MINOR=$(echo $PYTHON_VERSION | cut -d. -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

# Check if Python version is 3.11+
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "ERROR: Python 3.11+ is required. Found Python $PYTHON_VERSION"
    exit 1
fi

echo "Python version check passed!"
echo ""

# Check if python3-venv is available
echo "Checking for python3-venv..."
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "ERROR: python3-venv is not available."
    echo ""
    echo "Please install it using:"
    echo "  sudo apt install python3.${PYTHON_MINOR}-venv"
    echo ""
    echo "Or for the specific version:"
    echo "  sudo apt install python3-venv"
    exit 1
fi

echo "python3-venv is available!"
echo ""

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
    echo "Done!"
    echo ""
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "Virtual environment created!"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated!"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "pip upgraded!"
echo ""

# Install requirements
echo "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed!"
else
    echo "WARNING: requirements.txt not found. Skipping dependency installation."
fi
echo ""

# Check if ai-runtime directory exists and install package in editable mode
if [ -d "ai-runtime" ] && [ -f "ai-runtime/pyproject.toml" ]; then
    echo "Installing ai-runtime package in editable mode..."
    cd ai-runtime
    pip install -e .
    cd ..
    echo "Package installed in editable mode!"
    echo ""
fi

# Verify installation
echo "Verifying installation..."
echo ""
echo "Installed packages:"
pip list | grep -E "(fastapi|uvicorn|torch|pydantic|requests)" || true
echo ""

# Check CUDA availability (if torch is installed)
if python -c "import torch" 2>/dev/null; then
    echo "Checking CUDA availability..."
    CUDA_AVAILABLE=$(python -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")
    if [ "$CUDA_AVAILABLE" = "True" ]; then
        echo "✓ CUDA is available!"
        python -c "import torch; print(f'  CUDA Version: {torch.version.cuda}')" 2>/dev/null || true
    else
        echo "⚠ CUDA is not available (CPU-only mode)"
    fi
    echo ""
fi

echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
echo ""
