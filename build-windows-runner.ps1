# PowerShell wrapper for build-windows.bat
# This handles UNC paths and ensures Python is in PATH

$ErrorActionPreference = "Stop"

# Find any Python 3.12 installation
$pythonPath = "C:\Users\johnoshea\AppData\Local\Programs\Python\Python312"

if (-not (Test-Path "$pythonPath\python.exe")) {
    Write-Host "ERROR: Python 3.12 not found at $pythonPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Using Python from: $pythonPath" -ForegroundColor Green
& "$pythonPath\python.exe" --version
$arch = & "$pythonPath\python.exe" -c "import platform; print(platform.machine())"
Write-Host "Architecture: $arch" -ForegroundColor Cyan

if ($arch -eq "ARM64") {
    Write-Host ""
    Write-Host "NOTE: Using ARM64 Python. Some packages may need to compile from source." -ForegroundColor Yellow
    Write-Host "This may take longer but should work on ARM Windows." -ForegroundColor Yellow
    Write-Host ""
}

$env:PATH = "$pythonPath;$pythonPath\Scripts;$env:PATH"

# Get current location
$projectPath = $PSScriptRoot
Write-Host "Project path: $projectPath"

# Change to project directory
Set-Location $projectPath

Write-Host "`nStarting build process..."
Write-Host ""

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "PhotoFiler Windows Build Script" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Use temp directory for venv (not OneDrive)
$venvDir = "C:\Temp\photofiler-venv"
Write-Host "Using virtual environment at: $venvDir"
Write-Host ""

# Clean up old venv if exists
if (Test-Path $venvDir) {
    Write-Host "Cleaning up old virtual environment..."
    Remove-Item -Recurse -Force $venvDir
}

# Create virtual environment
Write-Host "Creating virtual environment..."
& "$pythonPath\python.exe" -m venv $venvDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Virtual environment created"
Write-Host ""

# Activate and get python/pip from venv
$venvPython = "$venvDir\Scripts\python.exe"
$venvPip = "$venvDir\Scripts\pip.exe"

# Upgrade pip
Write-Host "Upgrading pip..."
& $venvPip install --upgrade pip
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies..."
Write-Host "This may take 10-20 minutes (some packages may compile from source on ARM64)..."
Write-Host ""

Write-Host "[1/4] Installing numpy..."
& $venvPip install "numpy>=1.26.0,<3.0.0"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install numpy" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[2/4] Installing image processing libraries..."
& $venvPip install Pillow opencv-python
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install Pillow/opencv" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[3/4] Installing AI libraries (this may take a while)..."
& $venvPip install transformers torch torchvision tqdm
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install AI libraries" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[4/4] Installing build tools..."
& $venvPip install tkinterdnd2 pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install build tools" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "All dependencies installed successfully!" -ForegroundColor Green
Write-Host ""

# Build executable
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Building Windows executable..." -ForegroundColor Cyan
Write-Host "This will take 5-10 minutes..." -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

& $venvPython -m PyInstaller --clean --noconfirm "packaging\pyinstaller_photo_filer.spec"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    Write-Host "Check the output above for errors."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "BUILD COMPLETE!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable created at: dist\PhotoFiler\PhotoFiler.exe"
Write-Host "Size: ~1.3GB (includes AI model)"
Write-Host ""

# Clean up temporary venv
Write-Host "Cleaning up temporary files..."
Remove-Item -Recurse -Force $venvDir -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Build complete!"
Write-Host ""

Read-Host "Press Enter to exit"
