# 🎤 Jasper Voice Assistant

A privacy-focused, local voice assistant for Raspberry Pi 4B with ReSpeaker 2-Mics Pi HAT. Jasper provides an Alexa-like experience with voice commands processed entirely on your local network using Ollama LLMs.

## 🌟 Features

- **Wake Word Detection**: Responds only when "Jasper" is detected in your query
- **Local Speech Recognition**: Uses Vosk for offline speech-to-text
- **LLM Integration**: Connects to Ollama server on your LAN for intelligent responses
- **Text-to-Speech**: Festival TTS for natural voice responses
- **Web Interface**: Full-featured dashboard for configuration and monitoring
- **Conversation History**: Maintains context across multiple interactions
- **Real-time Logs**: Monitor system activity through the web interface
- **Volume Control**: Adjustable output volume through web UI
- **Automatic Log Rotation**: Manages logs with 30-day retention or 2GB size limit

## 🔧 Hardware Requirements

- **Raspberry Pi 4B** (8GB RAM recommended)
- **ReSpeaker 2-Mics Pi HAT** (for audio input/output)
- **MicroSD Card** (32GB+ recommended)
- **Power Supply** (USB-C, 5V 3A)
- **Network Connection** (WiFi or Ethernet)

## 💻 Software Requirements

- **OS**: Raspberry Pi OS Bookworm (Debian 12)
- **Ollama Server**: Running on local network (can be same Pi or another machine)
- **Python**: 3.11+ (included with Raspberry Pi OS Bookworm)

## 📦 Installation

### 1. Clone the Repository

```bash
cd ~
git clone https://github.com/yourusername/jasper.git
cd jasper
```

### 2. Run Installation Script

```bash
chmod +x install.sh
./install.sh
```

The installation script will:
- Update system packages
- Install system dependencies (Festival, ALSA, PortAudio, etc.)
- Install ReSpeaker 2-Mics HAT drivers
- Create Python virtual environment
- Install Python packages
- Download Vosk speech recognition model
- Download wake word detection models
- Configure ALSA audio
- Create systemd services
- Enable services for auto-start

**Note**: You may need to reboot after installation for audio drivers to fully load:

```bash
sudo reboot
```

### 3. Configure Ollama

Ensure Ollama is installed and running on your network:

```bash
# On your Ollama server (can be same Pi or another machine)
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (e.g., llama2)
ollama pull llama2

# Run Ollama server
ollama serve
```

## 🚀 Usage

### Starting the Services

The services are automatically enabled and will start on boot. To manually control them:

```bash
# Start Jasper daemon
sudo systemctl start jasperd

# Start Web interface
sudo systemctl start jasper-webapp

# Check status
sudo systemctl status jasperd
sudo systemctl status jasper-webapp
```

### Accessing the Web Interface

1. Open your browser and navigate to:
   ```
   http://<raspberry-pi-ip>:5000
   ```

2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`

### Configuring Jasper

Through the web interface, you can:

1. **Enable/Disable Jasper**: Use the global on/off toggle
2. **Configure Ollama**:
   - Server address (e.g., `localhost` or `192.168.1.100`)
   - Port (default: `11434`)
   - Model name (e.g., `llama2`, `mistral`, `codellama`)
3. **Adjust Volume**: Use the volume slider (0-100%)
4. **Enable/Disable Conversation History**: Toggle context retention
5. **Monitor Logs**: View real-time system logs
6. **View Conversations**: See recent interactions

### Using Voice Commands

1. Ensure Jasper is enabled in the web interface
2. Wait for the wake word detector to initialize (check logs)
3. Speak clearly: **"Hey, Jasper, what's the weather like today?"**
4. Important: The query must contain the word "Jasper" to be processed
5. Wait for the response to be spoken back

**Example Commands**:
- "Jasper, what time is it?"
- "Hey Jasper, tell me a joke"
- "Jasper, what's 25 times 16?"
- "Can you help me with Python, Jasper?"

## 📁 Project Structure

```
jasper/
├── install.sh              # Installation script
├── jasperd.py             # Main daemon (voice assistant logic)
├── webapp.py              # Flask web interface
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html        # Main dashboard
│   └── login.html        # Login page
├── logs/                  # Application logs (auto-created)
├── data/                  # Conversation history (auto-created)
└── models/                # Vosk models (auto-downloaded)
```

## ⚙️ Configuration Reference

### config.json

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled` | boolean | `false` | Master on/off switch for Jasper |
| `ollama_server` | string | `"localhost"` | Ollama server hostname/IP |
| `ollama_port` | integer | `11434` | Ollama server port |
| `ollama_model` | string | `"llama2"` | Ollama model to use |
| `volume` | integer | `75` | Audio output volume (0-100) |
| `conversation_history_enabled` | boolean | `true` | Enable conversation context |
| `max_conversation_turns` | integer | `10` | Number of turns to remember |
| `wake_word` | string | `"jasper"` | Wake word to listen for |
| `log_max_size_mb` | integer | `2048` | Maximum total log size (MB) |
| `log_retention_days` | integer | `30` | Days to keep logs |
| `audio_input_device` | string | `"default"` | ALSA input device |
| `audio_output_device` | string | `"default"` | ALSA output device |
| `sample_rate` | integer | `16000` | Audio sample rate (Hz) |
| `vad_aggressiveness` | integer | `3` | Voice Activity Detection level (0-3) |

## 🔧 Troubleshooting

### Audio Issues

**No sound output:**
```bash
# Test speaker
speaker-test -t wav -c 2

# Check audio devices
arecord -l
aplay -l

# Verify ALSA configuration
cat /etc/asound.conf
```

**Microphone not working:**
```bash
# Test microphone
arecord -d 5 test.wav
aplay test.wav

# Check volume levels
alsamixer
```

### Service Issues

**Check service status:**
```bash
sudo systemctl status jasperd
sudo journalctl -u jasperd -f
```

**Restart services:**
```bash
sudo systemctl restart jasperd
sudo systemctl restart jasper-webapp
```

### Wake Word Not Detecting

1. Check microphone is working (see above)
2. Speak clearly and at moderate volume
3. Ensure "Jasper" is pronounced distinctly
4. The wake word model uses "hey_jarvis" which responds well to "Jasper"
5. Check logs for wake word detection attempts

### Ollama Connection Issues

**Test Ollama connection:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Hello",
  "stream": false
}'
```

**Check Ollama is running:**
```bash
ps aux | grep ollama
```

### Web Interface Not Accessible

**Check if service is running:**
```bash
sudo systemctl status jasper-webapp
```

**Check firewall:**
```bash
sudo ufw status
sudo ufw allow 5000
```

**Check port binding:**
```bash
sudo netstat -tulpn | grep 5000
```

## 🔒 Security Considerations

1. **Change Default Password**: The web interface uses hardcoded credentials (`admin/admin`). For production use, modify `webapp.py` to use proper authentication.

2. **Network Security**: The web interface is accessible to anyone on your network. Consider:
   - Using a firewall to restrict access
   - Setting up HTTPS with a reverse proxy (nginx/Apache)
   - Implementing proper user authentication

3. **API Security**: The Ollama API should not be exposed to the internet. Keep it on your local network.

## 📊 System Requirements

- **RAM**: 2GB minimum, 4GB+ recommended
- **Storage**: 8GB minimum for OS + models
- **CPU**: Raspberry Pi 4B or newer
- **Network**: Stable LAN connection for Ollama queries

## 🔄 Updating

To update Jasper:

```bash
cd ~/jasper
git pull origin main
./install.sh  # Re-run installation to update dependencies
sudo systemctl restart jasperd
sudo systemctl restart jasper-webapp
```

## 📝 Logs

Logs are stored in the `logs/` directory with automatic rotation:

```bash
# View latest logs
tail -f logs/jasper_*.log

# View systemd logs
sudo journalctl -u jasperd -f
sudo journalctl -u jasper-webapp -f
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **Vosk**: Offline speech recognition
- **OpenWakeWord**: Wake word detection
- **Festival**: Text-to-speech synthesis
- **Ollama**: Local LLM inference
- **ReSpeaker**: Audio HAT hardware
- **Flask**: Web framework

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check the troubleshooting section
- Review system logs for errors

## 🗺️ Roadmap

Future enhancements planned:
- [ ] Multi-user authentication
- [ ] Custom wake word training
- [ ] Plugin system for custom commands
- [ ] Mobile app interface
- [ ] Multi-room audio support
- [ ] Voice profiles for different users
- [ ] Scheduled tasks/reminders
- [ ] Smart home integration (Home Assistant, etc.)

## 💡 Tips

1. **Performance**: For better response times, run Ollama on a separate machine with GPU
2. **Models**: Smaller models (like `mistral:7b-instruct`) respond faster than larger ones
3. **Wake Word**: Practice pronunciation for better detection rates
4. **Conversation History**: Disable if you want each query to be independent
5. **Log Rotation**: Adjust retention settings if storage is limited

## 🎯 Example Use Cases

- **Home Automation**: "Jasper, what's the temperature in the living room?"
- **Information**: "Jasper, who won the World Series in 2020?"
- **Calculations**: "Jasper, what's 15% of 250?"
- **Programming Help**: "Jasper, how do I reverse a list in Python?"
- **General Chat**: "Jasper, tell me an interesting fact"
- **Planning**: "Jasper, help me plan a dinner menu"

---

**Built with ❤️ for the Raspberry Pi and IoT community**
