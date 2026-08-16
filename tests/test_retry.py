"""Tests for the retry helper."""

from plugins.retry import retry_with_backoff


def test_retry_succeeds_after_transient_failures():
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def flaky() -> str:
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert call_count["n"] == 3


def test_retry_exhausts_and_raises():
    call_count = {"n": 0}

    @retry_with_backoff(max_retries=2, base_delay=0.01)
    def always_fails() -> str:
        call_count["n"] += 1
        raise RuntimeError("boom")

    try:
        always_fails()
    except RuntimeError as exc:
        assert str(exc) == "boom"
    assert call_count["n"] == 3  # initial + 2 retries


def test_retry_respects_predicate():
    call_count = {"n": 0}

    @retry_with_backoff(
        max_retries=2, base_delay=0.01, predicate=lambda e: "transient" in str(e)
    )
    def maybe_retry() -> str:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("transient failure")
        raise RuntimeError("fatal failure")

    try:
        maybe_retry()
    except RuntimeError as exc:
        assert "fatal failure" in str(exc)
    assert call_count["n"] == 2
