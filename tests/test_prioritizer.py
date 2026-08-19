import json
from pathlib import Path

from agents.prioritizer import _score_story_via_llm, prioritize


def test_score_story_via_llm_uses_fixture(monkeypatch, fixture_dir: Path):
    payload = json.loads(
        (fixture_dir / "openrouter_prioritizer_response.json").read_text(encoding="utf-8")
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    monkeypatch.setattr("pipeline.http_client.post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("agents.prioritizer.OPENROUTER_API_KEY", "test-key")

    story = {"title": "RBI hikes repo rate by 25 bps", "source": "RBI Press Releases"}
    score, returned = _score_story_via_llm(story)
    assert score == 85
    assert returned is story


def test_prioritize_writes_top_stories(monkeypatch, tmp_path: Path, fixture_dir: Path):
    payload = json.loads(
        (fixture_dir / "openrouter_prioritizer_response.json").read_text(encoding="utf-8")
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    monkeypatch.setattr("pipeline.http_client.post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("agents.prioritizer.OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("agents.prioritizer.PRIORITIZED_DIR", tmp_path)

    stories = [
        {"title": "RBI hikes repo rate by 25 bps", "source": "RBI", "hash": "h1"},
        {"title": "Income tax rebate for salaried class", "source": "ET", "hash": "h2"},
    ]
    top = prioritize(stories)
    assert len(top) == 2
    assert all(s["priority_score"] == 85 for s in top)
    out = tmp_path / "selected_stories.json"
    assert out.exists()
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved[0]["priority_score"] == 85
