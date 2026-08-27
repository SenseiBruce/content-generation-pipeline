from pathlib import Path

from scripts.total_scripts_generated import main, total_scripts_generated


def test_total_scripts_generated():
    assert (
        total_scripts_generated({"runs": [{"scripts_generated": 2}, {"scripts_generated": "3"}]})
        == 5
    )
    assert total_scripts_generated({}) == 0
    assert total_scripts_generated({"runs": [{"scripts_generated": "nope"}]}) == 0


def test_cli(tmp_path: Path, capsys):
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        '{"runs": [{"scripts_generated": 1}, {"scripts_generated": 4}]}', encoding="utf-8"
    )
    assert main(["--state-file", str(path)]) == 0
    assert '"scripts_generated": 5' in capsys.readouterr().out
