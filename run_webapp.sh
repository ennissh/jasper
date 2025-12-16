#!/bin/bash
# Jasper Web Interface Startup Script
# Ensures dependencies are installed and starts the web interface

set -e

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    # Check if we can create a virtual environment
    echo "Virtual environment not found. Creating one..."
    if python3 -m venv venv 2>/dev/null; then
        echo "Virtual environment created successfully."
        source venv/bin/activate
        PYTHON_CMD="python"
        PIP_CMD="pip"
        # Upgrade pip in the venv
        $PIP_CMD install --upgrade pip
    else
        # Fall back to system Python with --break-system-packages
        echo "Could not create virtual environment. Using system Python."
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    fi
fi

# Check if Flask is installed
if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo "Flask is not installed. Installing required dependencies..."
    if [ "$PIP_CMD" = "pip3" ]; then
        # System pip - use --break-system-packages for embedded systems
        $PIP_CMD install --break-system-packages flask==3.0.0 flask-login==0.6.3 flask-cors==4.0.0
    else
        # Virtual environment pip - no flag needed
        $PIP_CMD install flask==3.0.0 flask-login==0.6.3 flask-cors==4.0.0
    fi
fi

# Start webapp
echo ""
echo "Starting Jasper Web Interface..."
echo "Access at: http://localhost:5000"
echo "Default credentials: admin / admin"
echo ""
$PYTHON_CMD webapp.py
