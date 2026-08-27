from pathlib import Path

from scripts.total_stories_prioritized import main, total_stories_prioritized


def test_total_stories_prioritized():
    assert (
        total_stories_prioritized(
            {"runs": [{"stories_prioritized": 2}, {"stories_prioritized": "3"}]}
        )
        == 5
    )
    assert total_stories_prioritized({}) == 0
    assert total_stories_prioritized({"runs": [{"stories_prioritized": "nope"}]}) == 0


def test_cli(tmp_path: Path, capsys):
    path = tmp_path / "pipeline_state.json"
    path.write_text(
        '{"runs": [{"stories_prioritized": 1}, {"stories_prioritized": 4}]}',
        encoding="utf-8",
    )
    assert main(["--state-file", str(path)]) == 0
    assert '"stories_prioritized": 5' in capsys.readouterr().out
