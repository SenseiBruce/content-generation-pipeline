import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from list_losing_keywords import list_losing_keywords, main  # noqa: E402


def test_lists_string_keywords():
    assert list_losing_keywords({"losing_keywords": ["ipo", 1, "nifty"]}) == ["ipo", "nifty"]


def test_missing_field():
    assert list_losing_keywords({}) == []


def test_cli(tmp_path, capsys):
    path = tmp_path / "analytics_feedback.json"
    path.write_text(json.dumps({"losing_keywords": ["ipo"]}), encoding="utf-8")
    assert main(["--feedback-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["losing_keywords"] == ["ipo"]


def test_cli_missing(tmp_path):
    assert main(["--feedback-file", str(tmp_path / "missing.json")]) == 1
