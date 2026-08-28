import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from list_performance_insights import list_performance_insights, main  # noqa: E402


def test_lists_insights():
    assert list_performance_insights(
        {"performance_insights": [" Gold holds. ", "", 1, "RBI wins"]}
    ) == ["Gold holds.", "RBI wins"]


def test_missing_field():
    assert list_performance_insights({}) == []


def test_cli(tmp_path, capsys):
    path = tmp_path / "analytics_feedback.json"
    path.write_text(json.dumps({"performance_insights": ["Tax update"]}), encoding="utf-8")
    assert main(["--feedback-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["performance_insights"] == ["Tax update"]


def test_cli_missing(tmp_path):
    assert main(["--feedback-file", str(tmp_path / "missing.json")]) == 1
