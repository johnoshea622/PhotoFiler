@echo off
REM Windows Build Script for PhotoFiler
REM Run this from the project root in Windows

echo ====================================
echo PhotoFiler Windows Build Script
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo SOLUTION:
    echo 1. Download Python 3.12 from: https://www.python.org/downloads/windows/
    echo    - Choose "Windows installer (64-bit)"
    echo.
    echo 2. During installation:
    echo    - CHECK "Add Python to PATH" checkbox at the bottom
    echo    - Click "Install Now"
    echo.
    echo 3. After installation:
    echo    - Close this window
    echo    - Open a NEW Command Prompt
    echo    - Navigate back to this folder
    echo    - Run build-windows.bat again
    echo.
    echo NOTE: If Python is already installed but not found:
    echo    - Open Windows search and type "environment variables"
    echo    - Click "Edit the system environment variables"
    echo    - Click "Environment Variables" button
    echo    - Under "User variables", find "Path" and click "Edit"
    echo    - Click "New" and add: C:\Users\YourUsername\AppData\Local\Programs\Python\Python312
    echo    - Click "New" again and add: C:\Users\YourUsername\AppData\Local\Programs\Python\Python312\Scripts
    echo    - Click OK on all windows
    echo    - Close and reopen Command Prompt
    echo.
    pause
    exit /b 1
)

echo Found Python:
python --version
echo.

REM Check Python version
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYTHON_VERSION=%%V
echo Checking Python version...
python -c "import sys; v = sys.version_info; exit(0 if v.major == 3 and v.minor >= 10 else 1)"
if errorlevel 1 (
    echo.
    echo WARNING: Python 3.10 or higher is required
    echo You have Python %PYTHON_VERSION%
    echo.
    echo Please install Python 3.12 from: https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)
echo Python version OK
echo.

REM Check Python architecture
echo Checking Python architecture...
python -c "import platform; arch = platform.machine(); print(f'Architecture: {arch}'); exit(0 if arch in ['AMD64', 'x86_64'] else 1)"
if errorlevel 1 (
    echo.
    echo ERROR: Wrong Python architecture detected
    echo.
    echo You have ARM64 Python installed, but Windows on Parallels needs x86-64.
    echo.
    echo SOLUTION:
    echo 1. Uninstall current Python from "Add or remove programs"
    echo 2. Download Python 3.12 Windows x86-64 installer:
    echo    https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
    echo 3. Run installer and check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo.

REM Check if Tkinter is available
echo Checking Tkinter availability...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Tkinter is not available in your Python installation
    echo.
    echo SOLUTION:
    echo 1. Uninstall current Python:
    echo    - Go to "Add or remove programs"
    echo    - Find Python and uninstall it
    echo.
    echo 2. Download Python 3.12 from: https://www.python.org/downloads/windows/
    echo    - IMPORTANT: Download from python.org, NOT from Microsoft Store
    echo    - The python.org version includes Tkinter by default
    echo.
    echo 3. Install with "Add Python to PATH" checked
    echo.
    pause
    exit /b 1
)
echo Tkinter is available
echo.

echo Found Python:
python --version
echo.

REM Get current directory and handle UNC paths
set PROJECT_DIR=%~dp0

REM Check if we're on a UNC path
echo %PROJECT_DIR% | find "\\" >nul
if not errorlevel 1 (
    echo Detected UNC path, mapping to temporary drive...
    pushd "%PROJECT_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to map UNC path to drive letter
        echo.
        echo Please copy the project folder to a local drive like C:\PhotoFiler
        echo.
        pause
        exit /b 1
    )
    set PROJECT_DIR=%CD%
) else (
    cd /d "%PROJECT_DIR%"
)

echo Current directory: %CD%
echo.

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in current directory
    echo Please run this script from the Photo Filer project root folder
    echo.
    pause
    exit /b 1
)

REM Check for Microsoft C++ Build Tools (required for numpy/opencv)
echo Checking for C++ compiler...
where cl.exe >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Microsoft C++ Build Tools not found in PATH
    echo.
    echo Python 3.12 has pre-built wheels, so this should work anyway.
    echo If installation fails, you may need Visual Studio Build Tools.
    echo.
    echo To install later ^(optional^):
    echo https^:^/^/visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
    echo.
    timeout /t 3 >nul
) else (
    echo C++ compiler found
)
echo.

REM Use temp directory for venv (not OneDrive)
set VENV_DIR=C:\Temp\photofiler-venv
echo Using virtual environment at: %VENV_DIR%
echo.

REM Clean up old venv if exists
if exist "%VENV_DIR%" (
    echo Cleaning up old virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

REM Create virtual environment
echo Creating virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    echo.
    pause
    exit /b 1
)
echo Virtual environment created
echo.

REM Activate virtual environment
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo.
    pause
    exit /b 1
)
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo WARNING: pip upgrade failed, continuing anyway...
)
echo.

REM Install dependencies
echo Installing dependencies...
echo This may take 5-10 minutes (downloading pre-built packages)...
echo.

REM Install numpy and other binary packages first using pre-built wheels
echo [1/3] Installing numpy (pre-built wheel)...
pip install --only-binary :all: "numpy>=1.26.0,<3.0.0" --quiet
if errorlevel 1 (
    echo ERROR: Failed to install numpy pre-built wheel
    echo.
    echo This usually means:
    echo 1. No pre-built wheel available for Python 3.13 yet
    echo 2. Try Python 3.12 instead: https://www.python.org/downloads/release/python-3120/
    echo.
    pause
    exit /b 1
)

echo [2/3] Installing remaining requirements...
pip install Pillow opencv-python transformers torch torchvision numpy tqdm --only-binary :all: --quiet
if errorlevel 1 (
    echo WARNING: Some packages failed with --only-binary, retrying without restriction...
    pip install Pillow opencv-python transformers torch torchvision numpy tqdm --quiet
    if errorlevel 1 (
        echo ERROR: Failed to install core requirements
        echo.
        echo Make sure you have x86-64 Python installed ^(not ARM64^)
        echo.
        pause
        exit /b 1
    )
)

echo [2.5/3] Installing optional HEIC support...
pip install pillow-heif --quiet
if errorlevel 1 (
    echo WARNING: pillow-heif installation failed ^(HEIC support disabled^)
    echo This is optional - build will continue
)

echo [3/3] Installing GUI and build tools...
pip install tkinterdnd2 pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: Failed to install tkinterdnd2 and pyinstaller
    echo.
    pause
    exit /b 1
)
echo All dependencies installed!
echo.

REM Build executable
echo ====================================
echo Building Windows executable...
echo This will take 5-10 minutes...
echo ====================================
echo.

python -m PyInstaller --clean --noconfirm packaging\pyinstaller_photo_filer.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo ====================================
echo BUILD COMPLETE!
echo ====================================
echo.
echo Executable created at: dist\PhotoFiler.exe
echo Size: ~1.3GB (includes AI model)
echo.
echo To test:
echo   dist\PhotoFiler.exe --help
echo   dist\PhotoFiler.exe
echo.
echo The executable is standalone and can be copied to any Windows PC.
echo.

REM Clean up temporary venv
echo Cleaning up temporary files...
rmdir /s /q "%VENV_DIR%"
echo.
echo Cleanup complete!
echo.

REM Restore original directory if we used pushd
popd >nul 2>&1

pause
