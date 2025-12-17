#!/bin/bash
# Fix for missing ReSpeaker device tree overlay files
# Run this script on your Raspberry Pi if you get "failed to open .dtbo" errors

set -e

echo "================================================"
echo "  ReSpeaker Device Tree Overlay Fix"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo ./fix_respeaker_overlay.sh"
    exit 1
fi

# Determine the correct overlays directory
OVERLAYS=/boot/overlays
if [ -d /boot/firmware/overlays ]; then
    OVERLAYS=/boot/firmware/overlays
    echo "Using overlay directory: $OVERLAYS (Bookworm)"
else
    echo "Using overlay directory: $OVERLAYS (Legacy)"
fi

# Create overlays directory if it doesn't exist
if [ ! -d "$OVERLAYS" ]; then
    echo "Creating overlays directory: $OVERLAYS"
    mkdir -p "$OVERLAYS"
fi

# Find seeed-voicecard directory
VOICECARD_DIR=""
if [ -d "seeed-voicecard" ]; then
    VOICECARD_DIR="seeed-voicecard"
elif [ -d "/home/$SUDO_USER/seeed-voicecard" ]; then
    VOICECARD_DIR="/home/$SUDO_USER/seeed-voicecard"
elif [ -d "/root/seeed-voicecard" ]; then
    VOICECARD_DIR="/root/seeed-voicecard"
else
    echo "ERROR: seeed-voicecard directory not found!"
    echo ""
    echo "Cloning fresh copy from GitHub..."
    git clone https://github.com/respeaker/seeed-voicecard.git /tmp/seeed-voicecard
    VOICECARD_DIR="/tmp/seeed-voicecard"
fi

echo "Found seeed-voicecard at: $VOICECARD_DIR"
cd "$VOICECARD_DIR"

# Check if .dtbo files exist
echo ""
echo "Checking for device tree overlay files..."
if [ ! -f "seeed-2mic-voicecard.dtbo" ]; then
    echo "WARNING: Pre-compiled .dtbo files not found"
    echo "Attempting to compile from source..."

    # Check if device-tree-compiler is installed
    if ! command -v dtc &> /dev/null; then
        echo "Installing device-tree-compiler..."
        apt-get update
        apt-get install -y device-tree-compiler
    fi

    # Compile overlays if build script exists
    if [ -f "builddtbo.sh" ]; then
        echo "Running builddtbo.sh to compile overlays..."
        chmod +x builddtbo.sh
        ./builddtbo.sh
    else
        echo "ERROR: Cannot compile overlays - builddtbo.sh not found"
        exit 1
    fi
fi

# Copy overlay files to boot partition
echo ""
echo "Installing device tree overlays..."

for dtbo in seeed-2mic-voicecard.dtbo seeed-4mic-voicecard.dtbo seeed-8mic-voicecard.dtbo; do
    if [ -f "$dtbo" ]; then
        echo "  Copying $dtbo to $OVERLAYS/"
        cp -v "$dtbo" "$OVERLAYS/"
        chmod 644 "$OVERLAYS/$dtbo"
    else
        echo "  WARNING: $dtbo not found, skipping"
    fi
done

# Verify the 2-mic overlay was installed (required for your HAT)
if [ ! -f "$OVERLAYS/seeed-2mic-voicecard.dtbo" ]; then
    echo ""
    echo "ERROR: Failed to install seeed-2mic-voicecard.dtbo"
    exit 1
fi

echo ""
echo "================================================"
echo "  Device Tree Overlays Installed Successfully!"
echo "================================================"
echo ""
echo "Overlay files installed in: $OVERLAYS/"
ls -lh "$OVERLAYS/seeed-"*.dtbo 2>/dev/null || echo "  (No seeed overlays found - this may indicate a problem)"

echo ""
echo "Next steps:"
echo "1. Verify /boot/firmware/config.txt contains: dtoverlay=seeed-2mic-voicecard"
echo "2. Run: sudo reboot"
echo "3. After reboot, check: arecord -l"
echo ""
