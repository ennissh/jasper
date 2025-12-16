# Jasper Deployment Guide

## Hardware Requirements

**IMPORTANT:** Jasper requires audio hardware to function. It is designed to run on:
- **Raspberry Pi 4B 8GB with ReSpeaker 2-Mics Pi HAT** (recommended)
- Any Linux system with microphone and speakers/audio output

### Audio Device Requirements

Jasper cannot run without audio input devices. If you see errors like:
```
ERROR - Error in main loop: [Errno -9996] Invalid input device (no default output device)
```

This means:
1. **No audio hardware is available** - Common in Docker containers or headless systems
2. **Audio drivers not loaded** - May need to reboot after installing ReSpeaker drivers
3. **Permissions issue** - User needs access to audio devices

### Running in Docker (Limited Support)

Jasper has **limited Docker support** because it requires audio hardware passthrough:

```bash
# To run in Docker with audio (if host has audio devices):
docker run --device /dev/snd:/dev/snd --group-add audio your-jasper-image

# Note: This still requires the host system to have audio devices
```

**Recommended:** Run Jasper directly on Raspberry Pi hardware, not in containers.

## Quick Fix for "TemplateNotFound" Error

If you're getting this error:
```
jinja2.exceptions.TemplateNotFound: login.html
```

**The Issue:** You're running `webapp.py` from a directory that doesn't have the `templates/` folder.

## Solution: Run from the Jasper Directory

The webapp **must** be run from the jasper repository directory where all the project files are located:

```bash
# Navigate to the jasper directory
cd /path/to/jasper

# Then run the webapp using ONE of these methods:

# Method 1: Use the startup script (RECOMMENDED)
./run_webapp.sh

# Method 2: Run directly with Python
python3 webapp.py
```

## Deployment to Raspberry Pi

If you want to deploy this to your Raspberry Pi at `/home/ennissh/`, follow these steps:

### Option 1: Clone/Copy the Repository

```bash
# On your Raspberry Pi
cd /home/ennissh/
git clone <repository-url> jasper
cd jasper
./run_webapp.sh
```

### Option 2: Copy from Current Location

If you're already working in the jasper repository:

```bash
# Copy the entire jasper directory to your home folder
cp -r /home/user/jasper /home/ennissh/jasper
cd /home/ennissh/jasper
./run_webapp.sh
```

## Required Directory Structure

The webapp expects this structure:
```
jasper/
├── webapp.py           # Main Flask application
├── run_webapp.sh       # Startup script
├── templates/          # HTML templates (REQUIRED!)
│   ├── login.html
│   └── index.html
├── config.json         # Configuration file
├── logs/               # Log files (created automatically)
└── data/               # Data files (created automatically)
```

## Troubleshooting

### Error: "Invalid input device (no default output device)"
- **Cause:** No audio hardware available or not accessible
- **Fix Options:**
  1. **Raspberry Pi:** Reboot after running `install.sh` to load audio drivers
  2. **Docker:** Use `--device /dev/snd` flag or run on bare metal
  3. **Permissions:** Add user to `audio` group: `sudo usermod -aG audio $USER`
  4. **Check devices:** Run `arecord -l` to list audio input devices

### Error: "Jasper is disabled. Waiting..."
- **Cause:** Jasper is disabled in config.json
- **Fix:** Edit `config.json` and set `"enabled": true`

### Error: "TemplateNotFound: login.html"
- **Cause:** Running webapp.py from wrong directory
- **Fix:** Navigate to the jasper directory first, then run the webapp

### Error: "externally-managed-environment"
- **Cause:** System prevents pip install
- **Fix:** Use `./run_webapp.sh` - it handles this automatically

### Error: "ModuleNotFoundError: No module named 'flask'"
- **Cause:** Flask not installed
- **Fix:** Run `./run_webapp.sh` - it installs dependencies automatically

## Production Deployment

For production use with systemd service (as set up by `install.sh`):

```bash
# Ensure you're in the jasper directory
cd /home/ennissh/jasper

# Run the full installation script
./install.sh

# The script will create systemd services that run from the correct directory
sudo systemctl start jasper-webapp
sudo systemctl status jasper-webapp
```

The systemd service automatically uses the correct WorkingDirectory, so templates will be found.
