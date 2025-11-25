# Create Portable Distribution
# This creates a zip file of the working PhotoFiler application

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Creating Portable Distribution" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

$distFolder = "dist\PhotoFiler"
$outputZip = "PhotoFiler-Portable-Windows.zip"

if (-not (Test-Path $distFolder)) {
    Write-Host "ERROR: dist\PhotoFiler not found" -ForegroundColor Red
    Write-Host "Please build the executable first with: .\build-windows-runner.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating portable zip from: $distFolder" -ForegroundColor Cyan
Write-Host "This may take 1-2 minutes..." -ForegroundColor Yellow
Write-Host ""

# Remove old zip if exists
if (Test-Path $outputZip) {
    Remove-Item $outputZip -Force
}

# Create zip
Compress-Archive -Path $distFolder -DestinationPath $outputZip -CompressionLevel Optimal -Force

if (Test-Path $outputZip) {
    $zip = Get-Item $outputZip
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host "SUCCESS!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "? Portable distribution created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "File: $outputZip" -ForegroundColor Cyan
    Write-Host "Size: $([math]::Round($zip.Length / 1MB, 1)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Distribution Instructions:" -ForegroundColor Yellow
    Write-Host "1. Users download and extract the zip file" -ForegroundColor White
    Write-Host "2. Run PhotoFiler.exe from the extracted folder" -ForegroundColor White
    Write-Host "3. No installation required!" -ForegroundColor White
    Write-Host ""
    Write-Host "This works on any Windows PC (no admin rights needed)" -ForegroundColor Cyan
}
else {
    Write-Host "ERROR: Failed to create zip file" -ForegroundColor Red
}

Write-Host ""
