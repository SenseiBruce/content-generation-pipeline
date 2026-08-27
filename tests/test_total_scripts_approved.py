from pathlib import Path

from scripts.total_scripts_approved import load_state, main, total_scripts_approved


def test_total_scripts_approved_sums_runs():
    state = {
        "runs": [
            {"scripts_approved": 2},
            {"scripts_approved": 3},
            {"scripts_approved": "1"},
            {"scripts_approved": "nope"},
            "skip-me",
        ]
    }
    assert total_scripts_approved(state) == 6


def test_total_scripts_approved_empty():
    assert total_scripts_approved({}) == 0
    assert total_scripts_approved({"runs": None}) == 0


def test_load_state_and_cli(tmp_path: Path, capsys):
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        '{"runs": [{"scripts_approved": 4}, {"scripts_approved": 1}]}', encoding="utf-8"
    )
    assert load_state(path)["runs"][0]["scripts_approved"] == 4
    assert main(["--state-file", str(path)]) == 0
    out = capsys.readouterr().out
    assert '"scripts_approved": 5' in out
