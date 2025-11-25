# Rebuild Installer from Local Directory
# This script copies everything to C:\Temp first, then builds the installer

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Rebuilding Installer from Local Path" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Clean and create build directory
$buildDir = "C:\Temp\photofiler-final-build"
Write-Host "Creating clean build directory at: $buildDir" -ForegroundColor Cyan

if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
New-Item -ItemType Directory -Path "$buildDir\dist\PhotoFiler" -Force | Out-Null
New-Item -ItemType Directory -Path "$buildDir\packaging\icons" -Force | Out-Null

Write-Host ""
Write-Host "Copying files..." -ForegroundColor Cyan

# Copy dist folder
Write-Host "  - Executable and dependencies (this will take a minute)..."
Copy-Item "dist\PhotoFiler\*" "$buildDir\dist\PhotoFiler\" -Recurse -Force

# Copy packaging files
Write-Host "  - Installer script..."
Copy-Item "packaging\windows_installer.iss" "$buildDir\" -Force

Write-Host "  - Icons..."
Copy-Item "packaging\icons\*" "$buildDir\packaging\icons\" -Force

Write-Host ""
Write-Host "? Files copied to local directory" -ForegroundColor Green
Write-Host ""

# Find Inno Setup
$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)
$iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "ERROR: Inno Setup not found" -ForegroundColor Red
    exit 1
}

Write-Host "Building installer from local directory..." -ForegroundColor Cyan
Write-Host "This will take 2-3 minutes..." -ForegroundColor Yellow
Write-Host ""

# Build from local directory
Push-Location $buildDir
try {
    & $iscc "windows_installer.iss"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "====================================" -ForegroundColor Green
        Write-Host "SUCCESS!" -ForegroundColor Green
        Write-Host "====================================" -ForegroundColor Green
        Write-Host ""
        
        # Copy to C:\Temp root for easy access
        $installerPath = "$buildDir\packaging\Output\PhotoFiler-Setup.exe"
        if (Test-Path $installerPath) {
            Copy-Item $installerPath "C:\Temp\PhotoFiler-Setup.exe" -Force
            $installer = Get-Item "C:\Temp\PhotoFiler-Setup.exe"
            
            Write-Host "? Installer created successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Location: C:\Temp\PhotoFiler-Setup.exe" -ForegroundColor Cyan
            Write-Host "Size: $([math]::Round($installer.Length / 1MB, 1)) MB" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "You can now run the installer from C:\Temp\" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Launch installer now? (Y/N)" -ForegroundColor Cyan
            $response = Read-Host
            if ($response -eq "Y" -or $response -eq "y") {
                Start-Process -FilePath "C:\Temp\PhotoFiler-Setup.exe"
            }
        }
    }
    else {
        Write-Host ""
        Write-Host "ERROR: Build failed with exit code $LASTEXITCODE" -ForegroundColor Red
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Press Enter to exit..."
Read-Host
