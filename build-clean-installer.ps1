# Complete Clean Build from C:\Temp
# This script does EVERYTHING from C:\Temp - no UNC path access at all

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Clean Build from C:\Temp" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Copy only necessary source files to C:\Temp
$sourceDir = $PSScriptRoot
$buildDir = "C:\Temp\photofiler-clean-build"

Write-Host "Step 1: Copying source files to C:\Temp..." -ForegroundColor Cyan

if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Copy only what we need (not the broken dist folders)
Write-Host "  - Python source files..."
Copy-Item "$sourceDir\*.py" $buildDir -Force -ErrorAction SilentlyContinue
Copy-Item "$sourceDir\requirements.txt" $buildDir -Force -ErrorAction SilentlyContinue

Write-Host "  - Packaging files..."
Copy-Item "$sourceDir\packaging" "$buildDir\packaging" -Recurse -Force -Exclude "Output"

Write-Host "  - Copying dist folder (this may take 2 minutes)..."
Copy-Item "$sourceDir\dist\PhotoFiler" "$buildDir\dist\PhotoFiler" -Recurse -Force

Write-Host ""
Write-Host "? Files copied to: $buildDir" -ForegroundColor Green
Write-Host ""

# Step 2: Update installer script paths
Write-Host "Step 2: Updating installer script..." -ForegroundColor Cyan

$issPath = "$buildDir\packaging\windows_installer.iss"
$content = Get-Content $issPath -Raw

# Fix paths to be relative from packaging folder
$content = $content -replace 'Source: "dist\\', 'Source: "..\dist\'
$content = $content -replace 'Source: "packaging\\icons\\', 'Source: "icons\'
$content = $content -replace ';SetupIconFile=', 'SetupIconFile='

$content | Set-Content $issPath -NoNewline

Write-Host "? Paths updated" -ForegroundColor Green
Write-Host ""

# Step 3: Build installer
Write-Host "Step 3: Building installer with Inno Setup..." -ForegroundColor Cyan

$isccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\iscc.exe",
    "C:\Program Files\Inno Setup 6\iscc.exe"
)
$iscc = $isccPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    Write-Host "ERROR: Inno Setup not found" -ForegroundColor Red
    exit 1
}

Write-Host "Using: $iscc" -ForegroundColor Green
Write-Host "This will take 2-3 minutes..." -ForegroundColor Yellow
Write-Host ""

# Change to packaging directory and build
Set-Location "$buildDir\packaging"
& $iscc "windows_installer.iss"

if ($LASTEXITCODE -eq 0 -and (Test-Path "Output\PhotoFiler-Setup.exe")) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    
    $installer = Get-Item "Output\PhotoFiler-Setup.exe"
    Write-Host "? Installer created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Size: $([math]::Round($installer.Length / 1MB, 1)) MB" -ForegroundColor Cyan
    Write-Host ""
    
    # Copy to desktop for easy access
    $desktop = [Environment]::GetFolderPath("Desktop")
    $finalPath = "$desktop\PhotoFiler-Setup.exe"
    
    Copy-Item $installer.FullName $finalPath -Force
    
    Write-Host "? Installer copied to your Desktop!" -ForegroundColor Green
    Write-Host ""
    Write-Host "File: $finalPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This installer should work without corruption errors." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Test it now? (Y/N)" -ForegroundColor Cyan
    $response = Read-Host
    
    if ($response -eq "Y" -or $response -eq "y") {
        Write-Host ""
        Write-Host "Running installer from Desktop..." -ForegroundColor Cyan
        Start-Process -FilePath $finalPath -Wait
        
        Write-Host ""
        if (Test-Path "$env:LOCALAPPDATA\Programs\PhotoFiler\PhotoFiler.exe") {
            Write-Host "? PhotoFiler installed successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Launch PhotoFiler? (Y/N)" -ForegroundColor Cyan
            $launch = Read-Host
            if ($launch -eq "Y" -or $launch -eq "y") {
                Start-Process "$env:LOCALAPPDATA\Programs\PhotoFiler\PhotoFiler.exe"
            }
        }
    }
}
else {
    Write-Host ""
    Write-Host "ERROR: Build failed" -ForegroundColor Red
    Write-Host "Check the output above for errors" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press Enter to exit..."
Read-Host
