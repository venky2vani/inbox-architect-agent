#!/bin/bash

# Inbox Architect Agent - Interactive Setup Script
# This script automates the entire project setup process

set -e

echo "======================================"
echo "Inbox Architect Agent - Setup"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}[1/5]${NC} Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo -e "${BLUE}[2/5]${NC} Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi
source .venv/bin/activate
echo ""

# Install dependencies
echo -e "${BLUE}[3/5]${NC} Installing dependencies..."
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# Create .env file
echo -e "${BLUE}[4/5]${NC} Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
else
    echo -e "${YELLOW}⚠${NC}  .env already exists (skipping)"
fi
echo ""

# Check for Google credentials
echo -e "${BLUE}[5/5]${NC} Checking Google credentials..."
if [ ! -f "credentials/credentials.json" ]; then
    echo -e "${YELLOW}⚠${NC}  credentials/credentials.json not found"
    echo ""
    echo "You need to set up Google OAuth credentials:"
    echo ""
    echo "  1. Go to: https://console.cloud.google.com/apis/credentials"
    echo "  2. Click '+ Create Credentials' → 'OAuth 2.0 Client ID'"
    echo "  3. Choose 'Desktop application'"
    echo "  4. Click 'Create', then 'Download JSON'"
    echo "  5. Save as: credentials/credentials.json"
    echo ""
    echo -e "${YELLOW}Tip:${NC} Open the link above now and follow the steps."
    echo ""
    read -p "Press Enter when you've downloaded credentials.json and saved it to credentials/..."

    if [ ! -f "credentials/credentials.json" ]; then
        echo -e "${YELLOW}⚠${NC}  credentials.json still not found."
        echo "You can add it manually later and run: python agent.py"
        echo ""
    else
        echo -e "${GREEN}✓${NC} credentials.json found"
    fi
else
    echo -e "${GREEN}✓${NC} credentials.json already exists"
fi
echo ""

# Optionally add OpenAI API key
echo "Do you have an OpenAI API key? (optional, for LLM categorization)"
read -p "Enter your OpenAI API key (or press Enter to skip): " openai_key
if [ -n "$openai_key" ]; then
    # Safely update .env without exposing the key
    sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$openai_key|" .env
    echo -e "${GREEN}✓${NC} OpenAI API key added to .env"
else
    echo -e "${YELLOW}ℹ${NC}  Skipping OpenAI key (rule-based processing will be used)"
fi
echo ""

# Final summary
echo "======================================"
echo -e "${GREEN}Setup complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
if [ ! -f "credentials/credentials.json" ]; then
    echo "  1. Download Google credentials.json and save to credentials/"
    echo "  2. Run: source .venv/bin/activate"
    echo "  3. Test: python agent.py --dry-run --limit 5"
else
    echo "  1. Test the agent with: python agent.py --dry-run --limit 5"
    echo "  2. On first run, a browser window opens to authorize Gmail"
    echo "  3. Click 'Allow' and the agent will process emails"
fi
echo ""
echo "  Helpful commands:"
echo "    python agent.py                    # Process emails (live)"
echo "    python agent.py --dry-run          # Test without side effects"
echo "    python agent.py --dry-run --limit 5  # Test with just 5 emails"
echo "    python agent.py --help             # See all options"
echo ""
