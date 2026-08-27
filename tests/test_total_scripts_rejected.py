from pathlib import Path

from scripts.total_scripts_rejected import main, total_scripts_rejected


def test_total_scripts_rejected():
    assert (
        total_scripts_rejected({"runs": [{"scripts_rejected": 2}, {"scripts_rejected": "3"}]}) == 5
    )
    assert total_scripts_rejected({}) == 0


def test_cli(tmp_path: Path, capsys):
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        '{"runs": [{"scripts_rejected": 1}, {"scripts_rejected": 4}]}', encoding="utf-8"
    )
    assert main(["--state-file", str(path)]) == 0
    assert '"scripts_rejected": 5' in capsys.readouterr().out
