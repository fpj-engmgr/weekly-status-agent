#!/bin/bash
# Installation script for Weekly Status Agent

set -e  # Exit on error

echo "Weekly Status Agent - Installation Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python not found. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Check if Python version is 3.10+
REQUIRED_VERSION="3.10"
if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "Error: Python 3.10 or higher is required. You have $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python version check passed"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    $PYTHON_CMD -m venv venv
    echo "✓ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p config/credentials
mkdir -p data
mkdir -p logs
mkdir -p scripts
echo "✓ Directories created"
echo ""

# Copy example files if they don't exist
echo "Setting up configuration files..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file (please edit with your credentials)"
else
    echo "  .env already exists"
fi

if [ ! -f "config/config.yaml" ]; then
    cp config/config.example.yaml config/config.yaml
    echo "✓ Created config.yaml file (please edit with your settings)"
else
    echo "  config.yaml already exists"
fi
echo ""

# Print next steps
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env with your API credentials:"
echo "   nano .env"
echo ""
echo "2. Set up Google OAuth credentials:"
echo "   - Visit https://console.cloud.google.com/"
echo "   - Enable Gmail, Drive, and Docs APIs"
echo "   - Create OAuth 2.0 credentials"
echo "   - Download and save as config/credentials/google_oauth.json"
echo ""
echo "3. Edit config/config.yaml with your settings:"
echo "   nano config/config.yaml"
echo ""
echo "4. Test the setup:"
echo "   source venv/bin/activate"
echo "   python scripts/test_setup.py"
echo ""
echo "5. Run your first report:"
echo "   python src/main.py --dry-run"
echo ""
echo "For detailed instructions, see SETUP.md"
echo ""
