from pathlib import Path

from scripts.total_stories_fetched import load_state, main, total_stories_fetched


def test_total_stories_fetched_sums_runs():
    state = {
        "runs": [
            {"stories_fetched": 10},
            {"stories_fetched": "5"},
            {"stories_fetched": "nope"},
            "skip",
        ]
    }
    assert total_stories_fetched(state) == 15
    assert total_stories_fetched({}) == 0


def test_cli(tmp_path: Path, capsys):
    path = tmp_path / "pipeline_state.json"
    path.write_text('{"runs": [{"stories_fetched": 2}, {"stories_fetched": 7}]}', encoding="utf-8")
    assert load_state(path)["runs"][0]["stories_fetched"] == 2
    assert main(["--state-file", str(path)]) == 0
    assert '"stories_fetched": 9' in capsys.readouterr().out
