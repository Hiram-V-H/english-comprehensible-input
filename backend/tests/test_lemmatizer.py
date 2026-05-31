from __future__ import annotations

import pytest
from app.services.lemmatizer import lemmatize


@pytest.mark.parametrize("word, expected", [
    # Verbs: -ing
    ("running", "run"),
    ("walking", "walk"),
    ("swimming", "swim"),
    # Verbs: -ed / past
    ("walked", "walk"),
    ("played", "play"),
    # Verbs: irregular past
    ("ran", "run"),
    ("went", "go"),
    ("was", "be"),
    ("were", "be"),
    # Nouns: plurals
    ("stores", "store"),
    ("cats", "cat"),
    ("boxes", "box"),
    # Nouns: irregular plurals
    ("feet", "foot"),
    ("mice", "mouse"),
    ("children", "child"),
    # Adjectives: comparatives
    ("better", "good"),
    ("bigger", "big"),
    # Words that are already base form
    ("run", "run"),
    ("store", "store"),
    ("go", "go"),
    # Already base (contractions already expanded before lemmatizer)
    ("we", "we"),
    ("are", "be"),
    ("do", "do"),
    ("not", "not"),
])
def test_lemmatize(word, expected):
    assert lemmatize(word) == expected


def test_lemmatize_case_insensitive():
    assert lemmatize("Running") == "run"
    assert lemmatize("WENT") == "go"


def test_lemmatize_empty():
    assert lemmatize("") == ""
    assert lemmatize("  ") == ""
