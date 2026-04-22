"""Tests for load_phrases() — phrase file parsing."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest


class TestLoadPhrases:
    def test_loads_valid_lines(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("let me look up\nhere's what i found\n")
        result = proxy.load_phrases(str(f))
        assert result == ["let me look up", "here's what i found"]

    def test_strips_whitespace(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("  let me look up  \n  here's what i found  \n")
        result = proxy.load_phrases(str(f))
        assert result == ["let me look up", "here's what i found"]

    def test_skips_comments(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("# this is a comment\nlet me look up\n# another comment\n")
        result = proxy.load_phrases(str(f))
        assert result == ["let me look up"]

    def test_skips_empty_lines(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("let me look up\n\n\nhere's what i found\n\n")
        result = proxy.load_phrases(str(f))
        assert result == ["let me look up", "here's what i found"]

    def test_empty_file(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("")
        result = proxy.load_phrases(str(f))
        assert result == []

    def test_only_comments_and_blanks(self, proxy: ModuleType, tmp_path: Path) -> None:
        f = tmp_path / "phrases.txt"
        f.write_text("# comment\n\n# another\n  \n")
        result = proxy.load_phrases(str(f))
        assert result == []

    def test_file_not_found(self, proxy: ModuleType) -> None:
        with pytest.raises(FileNotFoundError):
            proxy.load_phrases("/nonexistent/path/phrases.txt")
