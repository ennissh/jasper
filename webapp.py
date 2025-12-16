#!/usr/bin/env python3
"""
Jasper Voice Assistant Web Interface
Flask application with authentication and real-time log streaming
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from functools import wraps

# Check for required dependencies
try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
    from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
    from flask_cors import CORS
except ImportError as e:
    print("ERROR: Required dependencies are not installed.", file=sys.stderr)
    print(f"Missing module: {e.name}", file=sys.stderr)
    print("", file=sys.stderr)
    print("To fix this issue, run ONE of the following:", file=sys.stderr)
    print("  1. Install dependencies: pip3 install flask==3.0.0 flask-login==0.6.3 flask-cors==4.0.0", file=sys.stderr)
    print("  2. Run the installation script: ./install.sh", file=sys.stderr)
    print("  3. Use the startup script: ./run_webapp.sh", file=sys.stderr)
    print("", file=sys.stderr)
    sys.exit(1)

# Configuration
CONFIG_FILE = "config.json"
LOG_DIR = "logs"
SECRET_KEY = "jasper-voice-assistant-secret-key-change-in-production"

# Create Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class User(UserMixin):
    """Simple user model for authentication."""

    def __init__(self, user_id, username, password):
        self.id = user_id
        self.username = username
        self.password = password


# Hardcoded user (admin/admin) - in production, use proper database
USERS = {
    "admin": User("1", "admin", "admin")
}


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    for user in USERS.values():
        if user.id == user_id:
            return user
    return None


def load_config():
    """Load configuration from JSON file."""
    try:
        if Path(CONFIG_FILE).exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Return default config
            return {
                "enabled": False,
                "ollama_server": "localhost",
                "ollama_port": 11434,
                "ollama_model": "llama2",
                "volume": 75,
                "conversation_history_enabled": True,
                "max_conversation_turns": 10,
                "wake_word": "jasper",
                "log_max_size_mb": 2048,
                "log_retention_days": 30,
                "audio_input_device": "default",
                "audio_output_device": "default",
                "sample_rate": 16000,
                "vad_aggressiveness": 3
            }
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def save_config(config):
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def get_latest_log_file():
    """Get the most recent log file."""
    log_dir = Path(LOG_DIR)
    if not log_dir.exists():
        return None

    log_files = sorted(log_dir.glob("jasper_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    return log_files[0] if log_files else None


def get_system_status():
    """Get system status information."""
    import subprocess

    try:
        # Check if jasperd service is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'jasperd'],
            capture_output=True,
            text=True
        )
        service_status = result.stdout.strip()

        # Get system info
        uptime_result = subprocess.run(['uptime'], capture_output=True, text=True)
        uptime = uptime_result.stdout.strip()

        return {
            "service_running": service_status == "active",
            "service_status": service_status,
            "uptime": uptime,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "service_running": False,
            "service_status": "unknown",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = USERS.get(username)
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    """Get current configuration."""
    config = load_config()
    return jsonify(config)


@app.route('/api/config', methods=['POST'])
@login_required
def update_config():
    """Update configuration."""
    try:
        config = load_config()
        data = request.json

        # Update config with provided values
        if 'enabled' in data:
            config['enabled'] = bool(data['enabled'])
        if 'ollama_server' in data:
            config['ollama_server'] = str(data['ollama_server'])
        if 'ollama_port' in data:
            config['ollama_port'] = int(data['ollama_port'])
        if 'ollama_model' in data:
            config['ollama_model'] = str(data['ollama_model'])
        if 'volume' in data:
            config['volume'] = max(0, min(100, int(data['volume'])))
        if 'conversation_history_enabled' in data:
            config['conversation_history_enabled'] = bool(data['conversation_history_enabled'])
        if 'max_conversation_turns' in data:
            config['max_conversation_turns'] = int(data['max_conversation_turns'])

        # Save config
        if save_config(config):
            return jsonify({"success": True, "config": config})
        else:
            return jsonify({"success": False, "error": "Failed to save configuration"}), 500

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    """Get system status."""
    status = get_system_status()
    config = load_config()
    status['enabled'] = config.get('enabled', False)
    return jsonify(status)


@app.route('/api/logs/stream')
@login_required
def stream_logs():
    """Stream logs in real-time using Server-Sent Events."""

    def generate():
        """Generate log stream."""
        last_position = 0
        log_file = None

        while True:
            try:
                # Get latest log file
                current_log_file = get_latest_log_file()

                # If log file changed, reset position
                if current_log_file != log_file:
                    log_file = current_log_file
                    last_position = 0

                if log_file and log_file.exists():
                    with open(log_file, 'r') as f:
                        # Seek to last position
                        f.seek(last_position)

                        # Read new lines
                        new_lines = f.readlines()

                        if new_lines:
                            for line in new_lines:
                                yield f"data: {json.dumps({'log': line.strip()})}\n\n"

                            last_position = f.tell()

                time.sleep(1)  # Poll every second

            except Exception as e:
                logger.error(f"Error streaming logs: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    """Get recent log entries."""
    try:
        lines = int(request.args.get('lines', 100))
        log_file = get_latest_log_file()

        if not log_file or not log_file.exists():
            return jsonify({"logs": []})

        # Read last N lines
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

        return jsonify({"logs": [line.strip() for line in recent_lines]})

    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversation_history', methods=['GET'])
@login_required
def get_conversation_history():
    """Get conversation history."""
    try:
        history_file = Path("data") / "conversation_history.json"

        if not history_file.exists():
            return jsonify({"history": []})

        with open(history_file, 'r') as f:
            history = json.load(f)

        return jsonify({"history": history})

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/conversation_history', methods=['DELETE'])
@login_required
def clear_conversation_history():
    """Clear conversation history."""
    try:
        history_file = Path("data") / "conversation_history.json"

        if history_file.exists():
            with open(history_file, 'w') as f:
                json.dump([], f)

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/service/<action>', methods=['POST'])
@login_required
def control_service(action):
    """Control jasperd service (start/stop/restart)."""
    import subprocess

    try:
        if action not in ['start', 'stop', 'restart']:
            return jsonify({"error": "Invalid action"}), 400

        result = subprocess.run(
            ['sudo', 'systemctl', action, 'jasperd'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return jsonify({"success": True, "action": action})
        else:
            return jsonify({
                "success": False,
                "error": result.stderr
            }), 500

    except Exception as e:
        logger.error(f"Error controlling service: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Create necessary directories
    Path(LOG_DIR).mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)

    # Run Flask app
    logger.info("Starting Jasper Web Interface on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
