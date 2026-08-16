"""Tests for configuration loading and environment mapping."""

import os
import tempfile
from pathlib import Path

import yaml

from agent import apply_config, load_config


def test_load_config_reads_yaml():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"agent": {"daily_digest": {"limit": 25}}}, f)
        path = f.name

    config = load_config(path)
    assert config["agent"]["daily_digest"]["limit"] == 25

    Path(path).unlink()


def test_load_config_missing_file_returns_empty():
    config = load_config("/nonexistent/config.yaml")
    assert config == {}


def test_apply_config_sets_env_vars():
    # Clear any existing values first.
    for var in [
        "GMAIL_CREDENTIALS_PATH",
        "PERSISTENCE_SHEET_NAME",
        "HIGH_PRIORITY_SENDERS",
    ]:
        os.environ.pop(var, None)

    config = {
        "gmail": {"credentials_path": "/tmp/cred.json"},
        "persistence": {"sheet_name": "Test Sheet"},
        "processor": {
            "rules": {
                "high_priority_senders": "boss@example.com",
                "custom": "Treat invoices as priority 3.",
            }
        },
    }

    apply_config(config)

    assert os.environ["GMAIL_CREDENTIALS_PATH"] == "/tmp/cred.json"
    assert os.environ["PERSISTENCE_SHEET_NAME"] == "Test Sheet"
    assert os.environ["HIGH_PRIORITY_SENDERS"] == "boss@example.com"
    assert "invoices as priority 3" in os.environ["CUSTOM_RULES"]
