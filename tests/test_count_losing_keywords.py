import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from count_losing_keywords import count_losing_keywords, main  # noqa: E402


def test_counts_keywords():
    assert count_losing_keywords({"losing_keywords": ["ipo", "nifty"]}) == 2


def test_missing_field():
    assert count_losing_keywords({}) == 0


def test_cli(tmp_path, capsys):
    path = tmp_path / "analytics_feedback.json"
    path.write_text(json.dumps({"losing_keywords": ["ipo"]}), encoding="utf-8")
    assert main(["--feedback-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["losing_keywords"] == 1


def test_cli_missing(tmp_path):
    assert main(["--feedback-file", str(tmp_path / "missing.json")]) == 1
