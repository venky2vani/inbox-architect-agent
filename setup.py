#!/usr/bin/env python3
"""Inbox Architect Agent - Interactive Setup Script"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'


def print_header(text):
    """Print a blue header."""
    print(f"\n{Colors.BLUE}{'='*50}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}\n")


def print_success(text):
    """Print a green success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {text}")


def print_warning(text):
    """Print a yellow warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {text}")


def print_info(text):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ{Colors.NC} {text}")


def check_python():
    """Check Python version."""
    print_info("Checking Python version...")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info < (3, 10):
        print(f"{Colors.RED}✗ Python 3.10+ required, but found {version}{Colors.NC}")
        sys.exit(1)
    print_success(f"Python {version} found")


def setup_venv():
    """Create and activate virtual environment."""
    print_info("Setting up virtual environment...")
    venv_path = Path(".venv")

    if venv_path.exists():
        print_success("Virtual environment already exists")
    else:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_success("Virtual environment created")


def install_dependencies():
    """Install project dependencies."""
    print_info("Installing dependencies...")
    venv_python = Path(".venv") / "bin" / "python"
    subprocess.run([str(venv_python), "-m", "pip", "install", "-q", "-r", "requirements.txt"], check=True)
    print_success("Dependencies installed")


def setup_env_file():
    """Create .env file from example."""
    print_info("Setting up environment file...")
    env_file = Path(".env")
    env_example = Path(".env.example")

    if env_file.exists():
        print_warning(".env already exists (skipping)")
    elif env_example.exists():
        shutil.copy(env_example, env_file)
        print_success(".env file created")
    else:
        print_warning(".env.example not found")


def check_credentials():
    """Check for Google credentials."""
    print_info("Checking Google credentials...")
    creds_path = Path("credentials/credentials.json")

    if creds_path.exists():
        print_success("credentials.json found")
        return True
    else:
        print_warning("credentials.json not found")
        print("\nYou need to set up Google OAuth credentials:\n")
        print("  1. Go to: https://console.cloud.google.com/apis/credentials")
        print("  2. Click '+ Create Credentials' → 'OAuth 2.0 Client ID'")
        print("  3. Choose 'Desktop application'")
        print("  4. Click 'Create', then 'Download JSON'")
        print("  5. Save as: credentials/credentials.json\n")
        return False


def get_openai_key():
    """Optionally get OpenAI API key."""
    try:
        response = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
        if response:
            # Update .env file
            env_path = Path(".env")
            content = env_path.read_text()
            content = content.replace(
                "OPENAI_API_KEY=your_openai_api_key_here",
                f"OPENAI_API_KEY={response}"
            )
            env_path.write_text(content)
            print_success("OpenAI API key added to .env")
        else:
            print_info("Skipping OpenAI key (rule-based processing will be used)")
    except EOFError:
        # Non-interactive mode
        print_info("Skipping OpenAI key (running in non-interactive mode)")


def print_next_steps(has_credentials):
    """Print next steps."""
    print_header("Setup Summary")

    if has_credentials:
        print("✓ Setup is complete! You're ready to go.\n")
        print("Run your first test:")
        print("  source .venv/bin/activate")
        print("  python agent.py --dry-run --limit 5\n")
    else:
        print("⚠ Setup is mostly complete, but you still need Google credentials.\n")
        print("Once you have credentials.json saved to credentials/:\n")
        print("  source .venv/bin/activate")
        print("  python agent.py --dry-run --limit 5\n")

    print("Useful commands:")
    print("  python agent.py                      # Process emails (live)")
    print("  python agent.py --dry-run            # Test without side effects")
    print("  python agent.py --dry-run --limit 5  # Test with just 5 emails")
    print("  python agent.py --help               # See all options\n")


def main():
    """Run the complete setup."""
    print_header("Inbox Architect Agent Setup")

    check_python()
    setup_venv()
    install_dependencies()
    setup_env_file()

    has_credentials = check_credentials()

    try:
        get_openai_key()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted.")
        sys.exit(1)

    print_next_steps(has_credentials)


if __name__ == "__main__":
    main()
