import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from count_runs import count_runs, main  # noqa: E402


def test_counts_runs():
    assert count_runs({"runs": [{}, {}]}) == 2


def test_missing_field():
    assert count_runs({}) == 0


def test_cli(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(json.dumps({"runs": [{"status": "ok"}]}), encoding="utf-8")
    assert main(["--state-file", str(state)]) == 0
    assert json.loads(capsys.readouterr().out)["runs"] == 1


def test_cli_missing(tmp_path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
