"""Tests for the checkpoint helper."""

import tempfile
from pathlib import Path

from plugins.checkpoint import Checkpoint


def test_checkpoint_starts_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cp = Checkpoint(path=f"{tmp}/checkpoint.json")
        assert cp.processed_count == 0
        assert not cp.is_processed("m1")


def test_checkpoint_marks_processed():
    with tempfile.TemporaryDirectory() as tmp:
        cp = Checkpoint(path=f"{tmp}/checkpoint.json")
        cp.mark_processed("m1")
        cp.mark_processed("m2")
        assert cp.processed_count == 2
        assert cp.is_processed("m1")
        assert cp.is_processed("m2")
        assert not cp.is_processed("m3")


def test_checkpoint_persists_and_reloads():
    with tempfile.TemporaryDirectory() as tmp:
        path = f"{tmp}/checkpoint.json"
        cp = Checkpoint(path=path)
        cp.mark_processed("m1")

        cp2 = Checkpoint(path=path)
        assert cp2.is_processed("m1")
        assert cp2.processed_count == 1


def test_checkpoint_reset_clears_data():
    with tempfile.TemporaryDirectory() as tmp:
        cp = Checkpoint(path=f"{tmp}/checkpoint.json")
        cp.mark_processed("m1")
        cp.reset()
        assert cp.processed_count == 0
        assert not cp.is_processed("m1")
