#!/bin/bash
# Quick install script for PhotoFiler

echo "PhotoFiler Installation"
echo "======================="
echo ""

# Check if .app bundle exists
if [ -d "dist/PhotoFiler.app" ]; then
    echo "Found PhotoFiler.app bundle"
    APP_PATH="dist/PhotoFiler.app"
else
    echo "No .app bundle found. Using standalone executable."
    APP_PATH="dist/PhotoFiler"
fi

# Copy to Applications
echo "Installing to /Applications..."
if [ -d "$APP_PATH" ]; then
    sudo cp -R "$APP_PATH" /Applications/
else
    # Create wrapper app for standalone executable
    echo "Creating app wrapper..."
    mkdir -p "/Applications/PhotoFiler.app/Contents/MacOS"
    cp "$APP_PATH" "/Applications/PhotoFiler.app/Contents/MacOS/PhotoFiler"
    chmod +x "/Applications/PhotoFiler.app/Contents/MacOS/PhotoFiler"
    
    # Create Info.plist
    cat > "/Applications/PhotoFiler.app/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PhotoFiler</string>
    <key>CFBundleName</key>
    <string>PhotoFiler</string>
    <key>CFBundleIdentifier</key>
    <string>com.tcd.photofiler</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
EOF
fi

echo ""
echo "✓ PhotoFiler installed!"
echo ""
echo "To run:"
echo "  - Open from Applications folder"
echo "  - Or: open /Applications/PhotoFiler.app"
echo ""
