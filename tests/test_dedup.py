"""Tests pour UrlDeduplicator."""

import time

from app.utils.dedup import UrlDeduplicator


def test_first_url_not_duplicate():
    dedup = UrlDeduplicator(window_seconds=30)
    assert dedup.is_duplicate("https://example.com/job/1") is False


def test_second_call_same_url_is_duplicate():
    dedup = UrlDeduplicator(window_seconds=30)
    dedup.is_duplicate("https://example.com/job/1")
    assert dedup.is_duplicate("https://example.com/job/1") is True


def test_different_urls_not_duplicate():
    dedup = UrlDeduplicator(window_seconds=30)
    dedup.is_duplicate("https://example.com/job/1")
    assert dedup.is_duplicate("https://example.com/job/2") is False


def test_url_expires_after_window(monkeypatch):
    dedup = UrlDeduplicator(window_seconds=1)
    dedup.is_duplicate("https://example.com/job/1")

    # Avancer le temps monotonic au-delà de la fenêtre
    real_monotonic = time.monotonic
    offset = 5.0
    monkeypatch.setattr(time, "monotonic", lambda: real_monotonic() + offset)

    assert dedup.is_duplicate("https://example.com/job/1") is False


def test_clear_resets_cache():
    dedup = UrlDeduplicator()
    dedup.is_duplicate("https://example.com/job/1")
    dedup.clear()
    assert dedup.is_duplicate("https://example.com/job/1") is False
