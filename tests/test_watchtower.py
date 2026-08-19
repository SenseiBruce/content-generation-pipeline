from agents.voicer import _sanitize_text
from agents.watchtower import _story_hash


def test_story_hash_is_stable_and_unique():
    a = _story_hash("RBI hikes rates", "https://example.com/1")
    b = _story_hash("RBI hikes rates", "https://example.com/1")
    c = _story_hash("RBI hikes rates", "https://example.com/2")
    assert a == b
    assert a != c
    assert len(a) == 32


def test_sanitize_text_strips_emoji_and_extra_space():
    clean = _sanitize_text("RBI hikes 🚀  repo   rate")
    assert "🚀" not in clean
    assert "  " not in clean
    assert "RBI hikes" in clean
