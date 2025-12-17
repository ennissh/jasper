#!/bin/bash
# Diagnostic script for ReSpeaker installation issues
# Run this to see what's wrong before applying fixes

echo "================================================"
echo "  ReSpeaker Installation Diagnostic"
echo "================================================"
echo ""

echo "[1] System Information"
echo "-------------------"
echo "Kernel version: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
echo ""

echo "[2] Overlay Directory Status"
echo "-------------------------"
if [ -d /boot/firmware/overlays ]; then
    echo "✓ /boot/firmware/overlays exists (Bookworm)"
    OVERLAYS=/boot/firmware/overlays
elif [ -d /boot/overlays ]; then
    echo "✓ /boot/overlays exists (Legacy)"
    OVERLAYS=/boot/overlays
else
    echo "✗ No overlays directory found!"
    OVERLAYS=""
fi

if [ -n "$OVERLAYS" ]; then
    echo ""
    echo "Checking for seeed-voicecard overlays in $OVERLAYS:"
    ls -lh "$OVERLAYS/seeed-"*.dtbo 2>/dev/null || echo "  ✗ No seeed overlay files found!"
fi
echo ""

echo "[3] Boot Configuration"
echo "-------------------"
if [ -f /boot/firmware/config.txt ]; then
    CONFIG=/boot/firmware/config.txt
elif [ -f /boot/config.txt ]; then
    CONFIG=/boot/config.txt
else
    echo "✗ config.txt not found!"
    CONFIG=""
fi

if [ -n "$CONFIG" ]; then
    echo "Config file: $CONFIG"
    echo "Checking for seeed-voicecard overlay configuration:"
    grep -E "dtoverlay.*seeed" "$CONFIG" || echo "  ✗ No seeed dtoverlay entry found!"
    echo ""
    echo "Checking I2S/I2C configuration:"
    grep -E "dtparam=i2s|dtparam=i2c" "$CONFIG" || echo "  ⚠ I2S/I2C parameters may not be enabled"
fi
echo ""

echo "[4] Seeed-voicecard Repository"
echo "---------------------------"
for dir in ./seeed-voicecard ~/seeed-voicecard /root/seeed-voicecard; do
    if [ -d "$dir" ]; then
        echo "✓ Found seeed-voicecard at: $dir"
        if [ -f "$dir/seeed-2mic-voicecard.dtbo" ]; then
            echo "  ✓ seeed-2mic-voicecard.dtbo exists in repository"
        else
            echo "  ✗ seeed-2mic-voicecard.dtbo NOT found in repository"
        fi
        break
    fi
done
echo ""

echo "[5] DKMS Modules"
echo "-------------"
if command -v dkms &> /dev/null; then
    echo "DKMS installed modules:"
    dkms status | grep seeed || echo "  ✗ No seeed-voicecard DKMS modules found"
else
    echo "✗ DKMS not installed"
fi
echo ""

echo "[6] Kernel Modules"
echo "---------------"
echo "Loaded sound-related modules:"
lsmod | grep -E "snd_soc|seeed|ac108|wm8960" || echo "  ✗ No seeed-voicecard modules loaded"
echo ""

echo "[7] I2C Devices"
echo "------------"
if command -v i2cdetect &> /dev/null; then
    echo "I2C device scan (bus 1):"
    i2cdetect -y 1 2>/dev/null || echo "  ⚠ Cannot scan I2C bus (may need sudo)"
else
    echo "✗ i2c-tools not installed"
fi
echo ""

echo "[8] Audio Devices"
echo "--------------"
echo "ALSA capture devices:"
arecord -l 2>/dev/null || echo "  ✗ No capture devices found"
echo ""
echo "ALSA playback devices:"
aplay -l 2>/dev/null || echo "  ✗ No playback devices found"
echo ""

echo "[9] Systemd Service"
echo "----------------"
if systemctl list-unit-files | grep -q seeed-voicecard; then
    echo "✓ seeed-voicecard service exists"
    systemctl status seeed-voicecard --no-pager | head -5
else
    echo "✗ seeed-voicecard service not found"
fi
echo ""

echo "================================================"
echo "  Diagnostic Complete"
echo "================================================"
echo ""
echo "Key Issues to Look For:"
echo "  1. Missing .dtbo files in overlays directory"
echo "  2. Missing dtoverlay entry in config.txt"
echo "  3. DKMS modules not compiled"
echo "  4. Kernel modules not loaded"
echo "  5. I2C device not detected (should see 0x1a)"
echo "  6. No audio capture devices"
echo ""
