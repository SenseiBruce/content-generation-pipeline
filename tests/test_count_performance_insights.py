import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from count_performance_insights import count_performance_insights, main  # noqa: E402


def test_counts_nonempty_strings():
    assert (
        count_performance_insights(
            {"performance_insights": [" Gold holds. ", "", 1, "RBI wins"]}
        )
        == 2
    )


def test_missing_field():
    assert count_performance_insights({}) == 0


def test_cli(tmp_path, capsys):
    path = tmp_path / "analytics_feedback.json"
    path.write_text(json.dumps({"performance_insights": ["Tax update"]}), encoding="utf-8")
    assert main(["--feedback-file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["performance_insights"] == 1


def test_cli_missing(tmp_path):
    assert main(["--feedback-file", str(tmp_path / "missing.json")]) == 1
