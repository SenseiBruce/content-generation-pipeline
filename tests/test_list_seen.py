import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from list_seen import list_seen_hashes, main  # noqa: E402


def test_lists_string_hashes_only():
    assert list_seen_hashes({"seen_hashes": ["a", 1, "b"]}) == ["a", "b"]


def test_missing_field():
    assert list_seen_hashes({}) == []


def test_cli(tmp_path, capsys):
    state = tmp_path / "pipeline_state.json"
    state.write_text(json.dumps({"seen_hashes": ["h1"]}), encoding="utf-8")
    assert main(["--state-file", str(state)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["seen_hashes"] == ["h1"]


def test_cli_missing_file(tmp_path):
    assert main(["--state-file", str(tmp_path / "missing.json")]) == 1
