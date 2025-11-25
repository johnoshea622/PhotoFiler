@echo off
REM Clean up venv-windows folder created in OneDrive

echo Cleaning up venv-windows from OneDrive...

pushd "\\Mac\Home\Library\CloudStorage\OneDrive-TCDGroup\0 TCD MyDocs\01. BMI Projects\96. Photo Filer"

if exist "venv-windows" (
    echo Found venv-windows folder, deleting...
    rmdir /s /q "venv-windows"
    echo Done!
) else (
    echo venv-windows folder not found (already cleaned)
)

popd

echo.
echo Cleanup complete!
pause
