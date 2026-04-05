#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.local/share/applications"
mkdir -p "$DEST_DIR"

# Create desktop file with correct path
cat > "$DEST_DIR/classic-note.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Classic Note
Comment=Simple offline notes app
Exec=/usr/bin/python3 $APP_DIR/main.py
Icon=utilities-text-editor
Terminal=false
Categories=Utility;Office;
StartupNotify=true
EOF

chmod +x "$APP_DIR/main.py"
chmod +x "$DEST_DIR/classic-note.desktop"

echo "Installed Classic Note launcher to $DEST_DIR"
echo "App directory: $APP_DIR"
echo "You can now find it in your desktop environment menu as 'Classic Note'."
