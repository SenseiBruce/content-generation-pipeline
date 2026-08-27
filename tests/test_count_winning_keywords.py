import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from count_winning_keywords import count_winning_keywords, main  # noqa: E402


def test_counts_keywords():
    assert count_winning_keywords({"winning_keywords": ["tax", "rbi"]}) == 2


def test_missing_field():
    assert count_winning_keywords({}) == 0


def test_cli(tmp_path, capsys):
    path = tmp_path / "analytics_feedback.json"
    path.write_text(json.dumps({"winning_keywords": ["gold"]}), encoding="utf-8")
    assert main(["--feedback-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["winning_keywords"] == 1


def test_cli_missing(tmp_path):
    assert main(["--feedback-file", str(tmp_path / "missing.json")]) == 1
