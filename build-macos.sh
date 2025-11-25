#!/bin/bash
# macOS Build Script for PhotoFiler
# Run this from the project root

echo "===================================="
echo "PhotoFiler macOS Build Script"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo ""
    echo "Please install Python 3.12 from https://www.python.org/downloads/macos/"
    exit 1
fi

echo "Found Python:"
python3 --version
echo ""

# Path to venv
VENV_PATH="/Users/johnoshea/Documents/programming/venvs/photo-sorting"

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv "$VENV_PATH"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt --quiet
pip install tkinterdnd2 pyinstaller --quiet
echo "Dependencies installed!"
echo ""

# Build executable
echo "===================================="
echo "Building macOS executable..."
echo "This will take 5-10 minutes..."
echo "===================================="
echo ""

python3 -m PyInstaller --clean --noconfirm packaging/pyinstaller_photo_filer.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Build failed!"
    echo "Check the output above for errors."
    exit 1
fi

echo ""
echo "===================================="
echo "BUILD COMPLETE!"
echo "===================================="
echo ""
echo "Executable created at: dist/PhotoFiler.app/Contents/MacOS/PhotoFiler"
echo "Size: ~1.3GB (includes AI model)"
echo ""
echo "To install as Mac app:"
echo "  ./install_app.sh"
echo ""
echo "To test:"
echo "  ./dist/PhotoFiler.app/Contents/MacOS/PhotoFiler --help"
echo "  ./dist/PhotoFiler.app/Contents/MacOS/PhotoFiler"
echo ""
echo "The executable is standalone and can be copied to any Mac (arm64)."
echo ""
