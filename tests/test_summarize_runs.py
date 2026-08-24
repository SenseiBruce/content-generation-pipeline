import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summarize_runs import main, summarize_runs  # noqa: E402


def test_summarize_counts_statuses():
    payload = {
        "runs": [
            {"status": "success"},
            {"status": "success"},
            {"status": "idle"},
            {"status": "  "},
        ]
    }
    summary = summarize_runs(payload)
    assert summary["total"] == 4
    assert summary["by_status"]["success"] == 2
    assert summary["by_status"]["idle"] == 1
    assert summary["by_status"]["unknown"] == 1


def test_cli(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(json.dumps({"runs": [{"status": "success"}]}), encoding="utf-8")
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 1
    assert out["by_status"]["success"] == 1
