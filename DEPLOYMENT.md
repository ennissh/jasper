# Jasper Web Interface Deployment Guide

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
