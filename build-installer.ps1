# Build Windows Installer Script
# This script copies files to C:\Temp to avoid UNC path issues with Inno Setup

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "PhotoFiler Installer Builder" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if Inno Setup is installed
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)
$iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "ERROR: Inno Setup not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Inno Setup from:" -ForegroundColor Yellow
    Write-Host "https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found Inno Setup at: $iscc" -ForegroundColor Green
Write-Host ""

# Check if executable exists
if (-not (Test-Path "dist\PhotoFiler\PhotoFiler.exe")) {
    Write-Host "ERROR: PhotoFiler.exe not found in dist\PhotoFiler\" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please build the executable first by running:" -ForegroundColor Yellow
    Write-Host "  .\build-windows-runner.ps1" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "? Found PhotoFiler.exe" -ForegroundColor Green
Write-Host ""

# Create temp directory
$tempDir = "C:\Temp\photofiler-installer-build"
Write-Host "Setting up temporary build directory..." -ForegroundColor Cyan
Write-Host "Location: $tempDir"

if (Test-Path $tempDir) {
    Write-Host "Cleaning old temp directory..."
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\packaging\icons" -Force | Out-Null
New-Item -ItemType Directory -Path "$tempDir\dist\PhotoFiler" -Force | Out-Null

# Copy necessary files
Write-Host ""
Write-Host "Copying files to temp directory..." -ForegroundColor Cyan

Write-Host "  - Installer script..."
Copy-Item "packaging\windows_installer.iss" "$tempDir\" -Force

Write-Host "  - Icons..."
Copy-Item "packaging\icons\*" "$tempDir\packaging\icons\" -Force -Recurse

Write-Host "  - Executable and dependencies..."
Copy-Item "dist\PhotoFiler\*" "$tempDir\dist\PhotoFiler\" -Force -Recurse

Write-Host ""
Write-Host "? Files copied successfully" -ForegroundColor Green
Write-Host ""

# Build installer
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Compiling installer..." -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

Push-Location $tempDir
try {
    & $iscc "windows_installer.iss"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "====================================" -ForegroundColor Green
        Write-Host "INSTALLER BUILD COMPLETE!" -ForegroundColor Green
        Write-Host "====================================" -ForegroundColor Green
        Write-Host ""
        
        # Copy installer back to project directory
        $installerSource = "$tempDir\packaging\Output\PhotoFiler-Setup.exe"
        $installerDest = "$PSScriptRoot\PhotoFiler-Setup.exe"
        
        if (Test-Path $installerSource) {
            Write-Host "Copying installer to project directory..." -ForegroundColor Cyan
            Copy-Item $installerSource $installerDest -Force
            
            $size = (Get-Item $installerDest).Length / 1MB
            Write-Host ""
            Write-Host "? Installer created: PhotoFiler-Setup.exe" -ForegroundColor Green
            Write-Host "  Location: $installerDest"
            Write-Host "  Size: $([math]::Round($size, 1)) MB"
            Write-Host ""
            Write-Host "You can now distribute PhotoFiler-Setup.exe to install on Windows PCs." -ForegroundColor Cyan
        }
        else {
            Write-Host "WARNING: Installer file not found at expected location" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host ""
        Write-Host "ERROR: Installer compilation failed" -ForegroundColor Red
        Write-Host "Check the output above for errors." -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
