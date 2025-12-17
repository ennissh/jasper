#!/usr/bin/env python3
"""
Jasper Voice Assistant Daemon
Raspberry Pi 4B 8GB with ReSpeaker 2-Mics Pi HAT
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
import wave
import requests

import pyaudio
import vosk
import webrtcvad
import numpy as np
from openwakeword.model import Model

# Configuration
CONFIG_FILE = "config.json"
LOG_DIR = "logs"
DATA_DIR = "data"
MODELS_DIR = "models"

# Global state
config = {}
running = True
conversation_history = []


class LogRotator:
    """Manages log rotation based on size and age."""

    def __init__(self, log_dir, max_size_mb=2048, retention_days=30):
        self.log_dir = Path(log_dir)
        self.max_size_mb = max_size_mb
        self.retention_days = retention_days
        self.log_dir.mkdir(exist_ok=True)

    def get_total_size_mb(self):
        """Calculate total size of all log files."""
        total_size = sum(f.stat().st_size for f in self.log_dir.glob("*.log"))
        return total_size / (1024 * 1024)

    def cleanup_old_logs(self):
        """Remove logs older than retention period or if total size exceeds limit."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        # Remove old logs
        for log_file in self.log_dir.glob("*.log"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                log_file.unlink()
                logging.info(f"Deleted old log: {log_file}")

        # Remove oldest logs if total size exceeds limit
        while self.get_total_size_mb() > self.max_size_mb:
            log_files = sorted(self.log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime)
            if log_files:
                oldest = log_files[0]
                oldest.unlink()
                logging.info(f"Deleted log due to size limit: {oldest}")
            else:
                break


def setup_logging():
    """Configure logging with rotation."""
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"jasper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return LogRotator(LOG_DIR)


def load_config():
    """Load configuration from JSON file."""
    global config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logging.info("Configuration loaded successfully")
        return config
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        # Return default config
        config = {
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
        return config


def save_conversation_history():
    """Save conversation history to file."""
    try:
        data_dir = Path(DATA_DIR)
        data_dir.mkdir(exist_ok=True)

        history_file = data_dir / "conversation_history.json"
        with open(history_file, 'w') as f:
            json.dump(conversation_history, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save conversation history: {e}")


def load_conversation_history():
    """Load conversation history from file."""
    global conversation_history
    try:
        history_file = Path(DATA_DIR) / "conversation_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                conversation_history = json.load(f)
            logging.info(f"Loaded {len(conversation_history)} conversation turns")
    except Exception as e:
        logging.error(f"Failed to load conversation history: {e}")
        conversation_history = []


def add_to_conversation(role, content):
    """Add message to conversation history."""
    global conversation_history

    if not config.get("conversation_history_enabled", True):
        return

    conversation_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })

    # Limit history size
    max_turns = config.get("max_conversation_turns", 10)
    if len(conversation_history) > max_turns * 2:  # *2 for user+assistant pairs
        conversation_history = conversation_history[-(max_turns * 2):]

    save_conversation_history()


class AudioRecorder:
    """Handles audio recording with Voice Activity Detection."""

    def __init__(self, sample_rate=16000, chunk_size=480):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.vad = webrtcvad.Vad(config.get("vad_aggressiveness", 3))
        self.audio = pyaudio.PyAudio()

    def record_audio(self, duration=5, timeout=10):
        """Record audio with VAD for specified duration."""
        frames = []
        stream = None

        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=None  # Use default device
            )

            logging.info("Recording audio...")

            # Wait for speech to start
            speech_started = False
            silence_chunks = 0
            max_silence_chunks = 30  # ~1 second of silence

            start_time = time.time()

            while time.time() - start_time < timeout:
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)

                # Check if chunk contains speech
                is_speech = self.vad.is_speech(chunk, self.sample_rate)

                if is_speech:
                    speech_started = True
                    silence_chunks = 0
                    frames.append(chunk)
                elif speech_started:
                    silence_chunks += 1
                    frames.append(chunk)

                    # Stop if we've had enough silence after speech
                    if silence_chunks > max_silence_chunks:
                        break

            logging.info(f"Recorded {len(frames)} chunks")

        except Exception as e:
            logging.error(f"Error recording audio: {e}")

        finally:
            if stream:
                stream.stop_stream()
                stream.close()

        return b''.join(frames) if frames else None

    def cleanup(self):
        """Clean up audio resources."""
        self.audio.terminate()


class SpeechRecognizer:
    """Handles speech-to-text using Vosk."""

    def __init__(self, model_path="models/vosk-model-small-en-us-0.15"):
        if not Path(model_path).exists():
            raise ValueError(f"Vosk model not found at {model_path}")

        self.model = vosk.Model(model_path)
        logging.info("Vosk speech recognition model loaded")

    def transcribe(self, audio_data, sample_rate=16000):
        """Transcribe audio data to text."""
        try:
            recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
            recognizer.AcceptWaveform(audio_data)

            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "")

            logging.info(f"Transcribed: {text}")
            return text

        except Exception as e:
            logging.error(f"Transcription error: {e}")
            return ""


class WakeWordDetector:
    """Detects wake word using openwakeword."""

    def __init__(self, wake_word="hey_jarvis_v0.1", threshold=0.5):
        # Use pre-trained model (hey_jarvis works well for "Jasper")
        self.model = Model(wakeword_models=[wake_word], inference_framework="onnx")
        self.threshold = threshold
        self.sample_rate = 16000
        self.chunk_size = 1280  # 80ms chunks
        logging.info(f"Wake word detector initialized for '{wake_word}'")

    def detect(self, audio_chunk):
        """Check if wake word is detected in audio chunk."""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0

        # Get predictions
        predictions = self.model.predict(audio_array)

        # Check if any wake word exceeds threshold
        for word, score in predictions.items():
            if score > self.threshold:
                logging.info(f"Wake word detected! ({word}: {score:.2f})")
                return True

        return False


class TextToSpeech:
    """Handles text-to-speech using Festival."""

    def __init__(self):
        self.volume = config.get("volume", 75)

    def speak(self, text):
        """Convert text to speech and play it."""
        try:
            logging.info(f"Speaking: {text}")

            # Use Festival for TTS
            # Create temporary file for audio
            temp_wav = f"/tmp/jasper_tts_{int(time.time())}.wav"

            # Generate speech with Festival
            process = subprocess.Popen(
                ['text2wave', '-o', temp_wav],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=text.encode())

            if Path(temp_wav).exists():
                # Play with volume control using amixer and aplay
                volume_percent = self.volume
                subprocess.run(['amixer', 'sset', 'PCM', f'{volume_percent}%'],
                             check=False, capture_output=True)
                subprocess.run(['aplay', temp_wav], check=True)

                # Clean up
                Path(temp_wav).unlink()
            else:
                logging.error("Failed to generate speech file")

        except Exception as e:
            logging.error(f"Text-to-speech error: {e}")

    def set_volume(self, volume):
        """Set playback volume (0-100)."""
        self.volume = max(0, min(100, volume))


class OllamaClient:
    """Client for Ollama LLM API."""

    def __init__(self, server="localhost", port=11434, model="llama2"):
        self.server = server
        self.port = port
        self.model = model
        self.base_url = f"http://{server}:{port}"

    def query(self, prompt, use_history=True):
        """Send query to Ollama and get response."""
        try:
            url = f"{self.base_url}/api/generate"

            # Build context from conversation history
            context = ""
            if use_history and config.get("conversation_history_enabled", True):
                for msg in conversation_history[-10:]:  # Last 5 turns
                    role = msg["role"]
                    content = msg["content"]
                    context += f"{role}: {content}\n"

            full_prompt = context + f"user: {prompt}\nassistant:"

            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False
            }

            logging.info(f"Querying Ollama: {self.model} on {self.base_url}")

            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            answer = result.get("response", "").strip()

            logging.info(f"Ollama response: {answer}")
            return answer

        except requests.exceptions.ConnectionError:
            logging.error(f"Cannot connect to Ollama at {self.base_url}")
            return "I'm sorry, I cannot connect to the language model server."
        except Exception as e:
            logging.error(f"Ollama query error: {e}")
            return "I'm sorry, I encountered an error processing your request."

    def update_config(self, server=None, port=None, model=None):
        """Update Ollama configuration."""
        if server:
            self.server = server
        if port:
            self.port = port
        if model:
            self.model = model
        self.base_url = f"http://{self.server}:{self.port}"


class JasperAssistant:
    """Main Jasper voice assistant."""

    def __init__(self):
        self.wake_word_detector = WakeWordDetector()
        self.speech_recognizer = SpeechRecognizer()
        self.audio_recorder = AudioRecorder(sample_rate=16000)
        self.tts = TextToSpeech()
        self.ollama = OllamaClient(
            server=config.get("ollama_server", "localhost"),
            port=config.get("ollama_port", 11434),
            model=config.get("ollama_model", "llama2")
        )
        self.audio = pyaudio.PyAudio()
        self.audio_available = self._check_audio_devices()
        self.last_config_reload = 0

    def _check_audio_devices(self):
        """Check if audio input devices are available."""
        try:
            device_count = self.audio.get_device_count()
            if device_count == 0:
                logging.error("No audio devices found")
                return False

            # Check for input devices
            has_input = False
            for i in range(device_count):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels', 0) > 0:
                    has_input = True
                    logging.info(f"Found input device: {device_info.get('name')}")
                    break

            if not has_input:
                logging.error("No audio input devices found")
                return False

            return True
        except Exception as e:
            logging.error(f"Error checking audio devices: {e}")
            return False

    def listen_for_wake_word(self):
        """Continuously listen for wake word."""
        if not self.audio_available:
            return False

        stream = None

        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1280
            )

            logging.info("Listening for wake word...")

            while running and config.get("enabled", False):
                # Reload config periodically (every 5 seconds)
                current_time = time.time()
                if current_time - self.last_config_reload >= 5:
                    load_config()
                    self.update_config()
                    self.last_config_reload = current_time

                try:
                    chunk = stream.read(1280, exception_on_overflow=False)

                    if self.wake_word_detector.detect(chunk):
                        return True

                except Exception as e:
                    logging.error(f"Error reading audio: {e}")
                    time.sleep(0.1)

            return False

        finally:
            if stream:
                stream.stop_stream()
                stream.close()

    def process_command(self, text):
        """Process voice command."""
        # Check if "jasper" is in the query (case insensitive)
        if "jasper" not in text.lower():
            logging.info("Command ignored - 'jasper' not in query")
            return None

        # Query Ollama
        response = self.ollama.query(text)

        # Add to conversation history
        add_to_conversation("user", text)
        add_to_conversation("assistant", response)

        return response

    def update_config(self):
        """Update components with new configuration."""
        self.ollama.update_config(
            server=config.get("ollama_server"),
            port=config.get("ollama_port"),
            model=config.get("ollama_model")
        )
        self.tts.set_volume(config.get("volume", 75))

    def run(self):
        """Main run loop."""
        logging.info("Jasper assistant starting...")

        while running:
            try:
                # Check if enabled
                if not config.get("enabled", False):
                    logging.info("Jasper is disabled. Waiting...")
                    time.sleep(5)
                    load_config()
                    continue

                # Check if audio devices are available
                if not self.audio_available:
                    logging.error("=" * 50)
                    logging.error("HARDWARE REQUIREMENT ERROR")
                    logging.error("=" * 50)
                    logging.error("Jasper requires audio input devices to function.")
                    logging.error("This system has no audio devices available.")
                    logging.error("")
                    logging.error("Jasper is designed to run on:")
                    logging.error("  - Raspberry Pi 4B with ReSpeaker 2-Mics Pi HAT")
                    logging.error("  - Or any system with microphone and speakers")
                    logging.error("")
                    logging.error("If running in Docker, you need to:")
                    logging.error("  1. Pass through audio devices with --device /dev/snd")
                    logging.error("  2. Or run directly on Raspberry Pi hardware")
                    logging.error("")
                    logging.error("Jasper will check again in 30 seconds...")
                    logging.error("=" * 50)
                    time.sleep(30)
                    self.audio_available = self._check_audio_devices()
                    continue

                # Listen for wake word
                if self.listen_for_wake_word():
                    logging.info("Wake word detected!")

                    # Optionally play acknowledgment sound
                    # self.tts.speak("Yes?")

                    # Record command
                    audio_data = self.audio_recorder.record_audio(duration=5, timeout=10)

                    if audio_data:
                        # Transcribe
                        text = self.speech_recognizer.transcribe(audio_data)

                        if text:
                            # Process command
                            response = self.process_command(text)

                            if response:
                                # Speak response
                                self.tts.speak(response)
                        else:
                            logging.info("No speech detected")
                    else:
                        logging.info("No audio recorded")

            except KeyboardInterrupt:
                logging.info("Shutting down...")
                break
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                time.sleep(1)

        # Cleanup
        self.audio_recorder.cleanup()
        self.audio.terminate()
        logging.info("Jasper assistant stopped")


def main():
    """Main entry point."""
    global running

    # Setup logging
    log_rotator = setup_logging()
    logging.info("=" * 50)
    logging.info("Jasper Voice Assistant Starting")
    logging.info("=" * 50)

    # Load configuration
    load_config()

    # Load conversation history
    load_conversation_history()

    # Start log rotation in background
    def rotate_logs():
        while running:
            log_rotator.cleanup_old_logs()
            time.sleep(3600)  # Check every hour

    rotation_thread = threading.Thread(target=rotate_logs, daemon=True)
    rotation_thread.start()

    # Create and run assistant
    try:
        assistant = JasperAssistant()
        assistant.run()
    except KeyboardInterrupt:
        logging.info("Received shutdown signal")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
    finally:
        running = False
        logging.info("Jasper assistant shutdown complete")


if __name__ == "__main__":
    main()
