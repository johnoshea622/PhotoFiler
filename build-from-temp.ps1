# Complete Build from C:\Temp (No UNC Path Issues)
# This script copies the project to C:\Temp and builds everything there

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Building from C:\Temp" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$tempProject = "C:\Temp\photofiler-project"

# Clean temp directory
if (Test-Path $tempProject) {
    Write-Host "Cleaning old temp directory..." -ForegroundColor Yellow
    Remove-Item $tempProject -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Copy project files
Write-Host "Copying project to C:\Temp..." -ForegroundColor Cyan
Write-Host "This may take 2-3 minutes..." -ForegroundColor Yellow
Write-Host ""

Copy-Item -Path "." -Destination $tempProject -Recurse -Force -Exclude @("*.git", "build", "*.pyc", "__pycache__", "*.log")

Write-Host "? Project copied" -ForegroundColor Green
Write-Host ""

# Change to temp directory
Set-Location $tempProject

# Find Inno Setup
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)
$iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "ERROR: Inno Setup not found" -ForegroundColor Red
    Write-Host "Installing Inno Setup..." -ForegroundColor Yellow
    
    $innoInstaller = "C:\Temp\innosetup-install.exe"
    if (-not (Test-Path $innoInstaller)) {
        Write-Host "Downloading Inno Setup..."
        Invoke-WebRequest -Uri "https://jrsoftware.org/download.php/is.exe" -OutFile $innoInstaller -UseBasicParsing
    }
    
    Write-Host "Installing..."
    Start-Process -FilePath $innoInstaller -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait
    Start-Sleep -Seconds 3
    
    $iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $iscc) {
    Write-Host "ERROR: Inno Setup installation failed" -ForegroundColor Red
    exit 1
}

Write-Host "Found Inno Setup: $iscc" -ForegroundColor Green
Write-Host ""

# Check if executable already exists
if (-not (Test-Path "dist\PhotoFiler\PhotoFiler.exe")) {
    Write-Host "Building executable with PyInstaller..." -ForegroundColor Cyan
    Write-Host "This will take 5-10 minutes..." -ForegroundColor Yellow
    Write-Host ""
    
    # Create venv in temp
    $venvDir = "C:\Temp\photofiler-venv-final"
    
    if (Test-Path $venvDir) {
        Remove-Item $venvDir -Recurse -Force
    }
    
    Write-Host "Creating virtual environment..."
    & "C:\Users\johnoshea\AppData\Local\Programs\Python\Python312\python.exe" -m venv $venvDir
    
    Write-Host "Installing dependencies..."
    & "$venvDir\Scripts\pip.exe" install --upgrade pip --quiet
    & "$venvDir\Scripts\pip.exe" install -r requirements.txt --quiet
    & "$venvDir\Scripts\pip.exe" install tkinterdnd2 pyinstaller --quiet
    
    Write-Host "Building with PyInstaller..."
    & "$venvDir\Scripts\python.exe" -m PyInstaller --clean --noconfirm "packaging\pyinstaller_photo_filer.spec"
    
    if (-not (Test-Path "dist\PhotoFiler\PhotoFiler.exe")) {
        Write-Host "ERROR: PyInstaller build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "? Executable built" -ForegroundColor Green
    Write-Host ""
}
else {
    Write-Host "? Using existing executable" -ForegroundColor Green
    Write-Host ""
}

# Build installer
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Building Installer" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Compiling with Inno Setup..." -ForegroundColor Cyan
Write-Host "This will take 2-3 minutes..." -ForegroundColor Yellow
Write-Host ""

& $iscc "packaging\windows_installer.iss"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host "BUILD COMPLETE!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    
    $installer = Get-Item "packaging\Output\PhotoFiler-Setup.exe"
    Write-Host "? Installer created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "File: PhotoFiler-Setup.exe" -ForegroundColor Cyan
    Write-Host "Size: $([math]::Round($installer.Length / 1MB, 1)) MB" -ForegroundColor Cyan
    Write-Host "Location: $($installer.FullName)" -ForegroundColor Cyan
    Write-Host ""
    
    # Copy back to original location
    Write-Host "Copying installer back to project directory..." -ForegroundColor Cyan
    Copy-Item $installer.FullName "C:\Temp\PhotoFiler-Setup.exe" -Force
    
    Write-Host ""
    Write-Host "? Installer ready at: C:\Temp\PhotoFiler-Setup.exe" -ForegroundColor Green
    Write-Host ""
    
    # Test the installer
    Write-Host "Test the installer now? (Y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Start-Process -FilePath "C:\Temp\PhotoFiler-Setup.exe"
    }
}
else {
    Write-Host ""
    Write-Host "ERROR: Installer build failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press Enter to exit..."
Read-Host
