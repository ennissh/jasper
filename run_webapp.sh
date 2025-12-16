#!/bin/bash
# Jasper Web Interface Startup Script
# Ensures dependencies are installed and starts the web interface

set -e

# Check if running in virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    PYTHON_CMD="python"
else
    # Use system Python
    PYTHON_CMD="python3"
fi

# Check if Flask is installed
if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo "Flask is not installed. Installing required dependencies..."
    pip3 install flask==3.0.0 flask-login==0.6.3 flask-cors==4.0.0
fi

# Start webapp
echo "Starting Jasper Web Interface..."
echo "Access at: http://localhost:5000"
echo "Default credentials: admin / admin"
echo ""
$PYTHON_CMD webapp.py
