import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from count_seen import count_seen_hashes, main  # noqa: E402


def test_counts_list():
    assert count_seen_hashes({"seen_hashes": ["a", "b", "c"]}) == 3


def test_missing_or_invalid_field():
    assert count_seen_hashes({}) == 0
    assert count_seen_hashes({"seen_hashes": "nope"}) == 0


def test_cli_prints_count(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(json.dumps({"seen_hashes": ["h1", "h2"]}), encoding="utf-8")
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["seen_hashes"] == 2


def test_cli_missing_file(tmp_path):
    missing = tmp_path / "missing.json"
    assert main(["--state-file", str(missing)]) == 1
