from __future__ import annotations

import pytest
from app.services.contractions import expand


@pytest.mark.parametrize("input_text, expected", [
    # Standard negations
    ("don't", "do not"),
    ("doesn't", "does not"),
    ("can't", "cannot"),
    ("won't", "will not"),
    ("shouldn't", "should not"),
    # Person + be
    ("we're", "we are"),
    ("I'm", "I am"),
    ("he's", "he is"),
    ("it's", "it is"),
    # Person + have
    ("I've", "I have"),
    ("we've", "we have"),
    # Person + will
    ("I'll", "I will"),
    ("they'll", "they will"),
    # Full sentences
    ("We're going to the store.", "We are going to the store."),
    ("I don't know what it's about.", "I do not know what it is about."),
    # No contraction
    ("hello world", "hello world"),
    # Empty
    ("", ""),
    # Archaic forms
    ("'tis the season", "it is the season"),
    ("'twas the night", "it was the night"),
    # Informal
    ("gonna do it", "going to do it"),
    ("wanna go", "want to go"),
])
def test_expand_contractions(input_text, expected):
    assert expand(input_text) == expected


def test_expand_preserves_whitespace():
    result = expand("  don't  ")
    assert "do not" in result


def test_case_insensitive():
    assert expand("DON'T") == "Do not"
    assert expand("Don't") == "Do not"
