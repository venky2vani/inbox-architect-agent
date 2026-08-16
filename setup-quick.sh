#!/bin/bash

# Inbox Architect Agent - Quick Non-Interactive Setup

set -e

echo "======================================"
echo "Inbox Architect Agent - Quick Setup"
echo "======================================"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install
source .venv/bin/activate
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create .env
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "Next step: Add your Google credentials"
echo ""
echo "1. Go to: https://console.cloud.google.com/apis/credentials"
echo "2. Create OAuth 2.0 Client ID (Desktop app)"
echo "3. Download JSON → Save as: credentials/credentials.json"
echo ""
echo "Then run:"
echo "  source .venv/bin/activate"
echo "  python agent.py --dry-run --limit 5"
echo ""
