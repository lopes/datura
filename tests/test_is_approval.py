"""Tests for is_approval() — case-insensitive substring matching."""

from __future__ import annotations

from types import ModuleType


class TestIsApproval:
    def test_match_exact_phrase(self, proxy: ModuleType) -> None:
        phrases = ["let me look up"]
        assert proxy.is_approval("let me look up the config", phrases) is True

    def test_match_case_insensitive(self, proxy: ModuleType) -> None:
        phrases = ["here's what i found"]
        assert proxy.is_approval("Here's What I Found for that setup", phrases) is True

    def test_no_match(self, proxy: ModuleType) -> None:
        phrases = ["let me look up"]
        assert proxy.is_approval("I cannot help with that", phrases) is False

    def test_empty_response(self, proxy: ModuleType) -> None:
        phrases = ["let me look up"]
        assert proxy.is_approval("", phrases) is False

    def test_empty_phrases(self, proxy: ModuleType) -> None:
        assert proxy.is_approval("let me look up the config", []) is False

    def test_match_embedded_in_longer_text(self, proxy: ModuleType) -> None:
        phrases = ["staging config for"]
        text = "Sure, let me get the staging config for that service right away."
        assert proxy.is_approval(text, phrases) is True

    def test_multiple_phrases_first_matches(self, proxy: ModuleType) -> None:
        phrases = ["let me look up", "here's what i found"]
        assert proxy.is_approval("let me look up the details", phrases) is True

    def test_multiple_phrases_second_matches(self, proxy: ModuleType) -> None:
        phrases = ["let me look up", "here's what i found"]
        assert proxy.is_approval("here's what i found for you", phrases) is True
