import json
from pathlib import Path

from agents.analyst import update_feedback


def test_update_feedback_creates_file(monkeypatch, tmp_path: Path):
    feedback_file = tmp_path / "analytics_feedback.json"
    monkeypatch.setattr("agents.analyst.FEEDBACK_FILE", feedback_file)

    assert update_feedback(winners=["tax", "rbi"], losers=["ipo"]) is True
    data = json.loads(feedback_file.read_text(encoding="utf-8"))
    assert data["winning_keywords"] == ["tax", "rbi"]
    assert data["losing_keywords"] == ["ipo"]
    assert "last_updated" in data
    assert "tax" in data["performance_insights"][0]
