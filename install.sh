#!/bin/bash
set -e

# Jasper Voice Assistant Installation Script
# For Raspberry Pi 4B 8GB with ReSpeaker 2-Mics Pi HAT
# OS: Raspberry Pi OS Trixie
# Note: Uses Python 3.11 for compatibility with ML libraries (openwakeword, tflite-runtime)

echo "================================================"
echo "  Jasper Voice Assistant Installation Script"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "WARNING: Running as root. This is not recommended for production systems."
    echo "For production, run as a regular user with sudo privileges."
    echo "Continuing in 3 seconds..."
    sleep 3
    # When running as root, don't use sudo
    SUDO_CMD=""
else
    SUDO_CMD="sudo"
fi

# Update system
echo "[1/10] Updating system packages..."
$SUDO_CMD apt-get update
$SUDO_CMD apt-get upgrade -y

# Install system dependencies
echo "[2/10] Installing system dependencies..."
# Install Python 3.11 packages if not already installed
if ! dpkg -l | grep -q "^ii  python3.11 "; then
    $SUDO_CMD apt-get install -y python3.11 python3.11-venv python3.11-dev
else
    echo "Python 3.11 packages already installed, skipping..."
fi

# Install remaining system dependencies
$SUDO_CMD apt-get install -y \
    python3-pip \
    portaudio19-dev \
    libasound2-dev \
    libopenblas-dev \
    festival \
    festival-dev \
    alsa-utils \
    pulseaudio \
    git \
    curl \
    wget \
    build-essential \
    libjack-jackd2-dev \
    libsndfile1-dev

# Install ReSpeaker 2-Mics HAT drivers
echo "[3/10] Installing ReSpeaker 2-Mics HAT drivers..."
if [ ! -d "seeed-voicecard" ]; then
    git clone https://github.com/respeaker/seeed-voicecard.git
    cd seeed-voicecard
    $SUDO_CMD ./install.sh
    cd ..
else
    echo "ReSpeaker drivers already installed, skipping..."
fi

# Create project directory structure
echo "[4/10] Creating directory structure..."
mkdir -p ~/jasper/logs
mkdir -p ~/jasper/models
mkdir -p ~/jasper/data
mkdir -p ~/jasper/templates
mkdir -p ~/jasper/static

# Create Python virtual environment
echo "[5/10] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "[6/10] Installing Python dependencies..."
pip install vosk==0.3.45
pip install pyaudio==0.2.14
pip install requests==2.31.0
pip install flask==3.0.0
pip install flask-login==0.6.3
pip install flask-cors==4.0.0
pip install python-dotenv==1.0.0
pip install openwakeword==0.5.1
pip install numpy==1.24.3
pip install scipy==1.11.4
pip install webrtcvad==2.0.10
pip install sounddevice==0.4.6

# Download Vosk model
echo "[7/10] Downloading Vosk speech recognition model..."
if [ ! -d "models/vosk-model-small-en-us-0.15" ]; then
    cd models
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip vosk-model-small-en-us-0.15.zip
    rm vosk-model-small-en-us-0.15.zip
    cd ..
else
    echo "Vosk model already installed, skipping..."
fi

# Download openwakeword models
echo "[8/10] Setting up wake word detection..."
venv/bin/python3 << 'PYTHON_SCRIPT'
import openwakeword
from openwakeword.model import Model

# Initialize model to download default models
model = Model(wakeword_models=["hey_jarvis_v0.1"], inference_framework="onnx")
print("Wake word models downloaded successfully!")
PYTHON_SCRIPT

# Configure ALSA for ReSpeaker
echo "[9/10] Configuring audio for ReSpeaker HAT..."
$SUDO_CMD tee /etc/asound.conf > /dev/null << 'EOF'
pcm.!default {
    type asym
    capture.pcm "mic"
    playback.pcm "speaker"
}

pcm.mic {
    type plug
    slave {
        pcm "hw:seeed2micvoicec"
    }
}

pcm.speaker {
    type plug
    slave {
        pcm "hw:seeed2micvoicec"
    }
}
EOF

# Create default config.json if it doesn't exist
echo "[10/10] Creating default configuration..."
if [ ! -f "config.json" ]; then
    cat > config.json << 'EOF'
{
    "enabled": false,
    "ollama_server": "localhost",
    "ollama_port": 11434,
    "ollama_model": "llama2",
    "volume": 75,
    "conversation_history_enabled": true,
    "max_conversation_turns": 10,
    "wake_word": "jasper",
    "log_max_size_mb": 2048,
    "log_retention_days": 30,
    "audio_input_device": "default",
    "audio_output_device": "default",
    "sample_rate": 16000,
    "vad_aggressiveness": 3
}
EOF
fi

# Create systemd service
echo "Creating systemd service..."
$SUDO_CMD tee /etc/systemd/system/jasperd.service > /dev/null << EOF
[Unit]
Description=Jasper Voice Assistant Daemon
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/jasperd.py
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Create webapp systemd service
echo "Creating webapp systemd service..."
$SUDO_CMD tee /etc/systemd/system/jasper-webapp.service > /dev/null << EOF
[Unit]
Description=Jasper Voice Assistant Web Interface
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/webapp.py
Restart=always
RestartSec=10
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
$SUDO_CMD systemctl daemon-reload
$SUDO_CMD systemctl enable jasperd.service
$SUDO_CMD systemctl enable jasper-webapp.service

echo ""
echo "================================================"
echo "  Installation Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review and edit config.json if needed"
echo "2. Start the services:"
echo "   sudo systemctl start jasperd"
echo "   sudo systemctl start jasper-webapp"
echo "3. Access web interface at: http://localhost:5000"
echo "   Default credentials: admin / admin"
echo "4. Configure Ollama settings in the web interface"
echo ""
echo "To check service status:"
echo "   sudo systemctl status jasperd"
echo "   sudo systemctl status jasper-webapp"
echo ""
echo "To view logs:"
echo "   sudo journalctl -u jasperd -f"
echo "   sudo journalctl -u jasper-webapp -f"
echo ""
echo "You may need to reboot for audio drivers to fully load:"
echo "   sudo reboot"
echo ""
