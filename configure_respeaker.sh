#!/bin/bash
# Configure /boot/firmware/config.txt for ReSpeaker 2-Mics HAT
# This adds the necessary dtoverlay and I2S/I2C parameters

set -e

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Please run: sudo ./configure_respeaker.sh"
    exit 1
fi

CONFIG=/boot/firmware/config.txt
if [ ! -f "$CONFIG" ]; then
    CONFIG=/boot/config.txt
fi

echo "================================================"
echo "  Configuring ReSpeaker in $CONFIG"
echo "================================================"
echo ""

# Backup config.txt
cp "$CONFIG" "${CONFIG}.backup-$(date +%Y%m%d-%H%M%S)"
echo "✓ Backed up config.txt"

# Check if seeed-2mic-voicecard overlay is already configured
if grep -q "^dtoverlay=seeed-2mic-voicecard" "$CONFIG"; then
    echo "✓ seeed-2mic-voicecard overlay already configured"
else
    echo "Adding dtoverlay=seeed-2mic-voicecard..."
    echo "" >> "$CONFIG"
    echo "# ReSpeaker 2-Mics HAT" >> "$CONFIG"
    echo "dtoverlay=seeed-2mic-voicecard" >> "$CONFIG"
    echo "✓ Added dtoverlay=seeed-2mic-voicecard"
fi

# Enable I2S if not already enabled
if grep -q "^dtparam=i2s=on" "$CONFIG"; then
    echo "✓ I2S already enabled"
else
    # Check if it's commented out
    if grep -q "^#dtparam=i2s=on" "$CONFIG"; then
        echo "Uncommenting dtparam=i2s=on..."
        sed -i 's/^#dtparam=i2s=on/dtparam=i2s=on/' "$CONFIG"
    else
        echo "Adding dtparam=i2s=on..."
        echo "dtparam=i2s=on" >> "$CONFIG"
    fi
    echo "✓ Enabled I2S"
fi

# Enable I2C if not already enabled
if grep -q "^dtparam=i2c_arm=on" "$CONFIG"; then
    echo "✓ I2C already enabled"
else
    # Check if it's commented out
    if grep -q "^#dtparam=i2c_arm=on" "$CONFIG"; then
        echo "Uncommenting dtparam=i2c_arm=on..."
        sed -i 's/^#dtparam=i2c_arm=on/dtparam=i2c_arm=on/' "$CONFIG"
    else
        echo "Adding dtparam=i2c_arm=on..."
        echo "dtparam=i2c_arm=on" >> "$CONFIG"
    fi
    echo "✓ Enabled I2C"
fi

echo ""
echo "================================================"
echo "  Configuration Complete"
echo "================================================"
echo ""
echo "Relevant config.txt entries:"
grep -E "dtparam=i2s|dtparam=i2c_arm|dtoverlay=seeed" "$CONFIG" | grep -v "^#"
echo ""
echo "Next steps:"
echo "1. Ensure DKMS modules are installed (check with: dkms status)"
echo "2. If no DKMS modules, run: cd seeed-voicecard && sudo ./install_arm64.sh"
echo "3. Reboot: sudo reboot"
echo "4. After reboot, verify: arecord -l"
echo ""
