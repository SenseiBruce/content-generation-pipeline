"""Tests for rerun_approved --list catalog."""

from __future__ import annotations

import json
from pathlib import Path

import rerun_approved
from tests.helpers import make_valid_script


def test_list_approved_missing_dir_returns_empty(tmp_path: Path) -> None:
    assert rerun_approved.list_approved(tmp_path / "missing") == []


def test_list_approved_empty_dir_returns_empty(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    assert rerun_approved.list_approved(approved) == []


def test_list_approved_catalogs_scripts(tmp_path: Path, monkeypatch) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    script = make_valid_script()
    script["judge_score"] = 87
    path = approved / "approved_abc123.json"
    path.write_text(json.dumps(script), encoding="utf-8")

    monkeypatch.setattr(rerun_approved, "APPROVED_DIR", approved)
    rows = rerun_approved.list_approved()
    assert len(rows) == 1
    row = rows[0]
    assert row["filename"] == "approved_abc123.json"
    assert row["story_hash"] == "abc123"
    assert row["title"] == script["title"]
    assert row["project_name"] == "RBI Rate Shock"
    assert row["judge_score"] == 87
    assert row["scene_count"] == 5
    assert "T" in row["modified_at"]


def test_list_approved_skips_malformed_json(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "approved_bad.json").write_text("{not-json", encoding="utf-8")
    (approved / "approved_ok.json").write_text(json.dumps(make_valid_script()), encoding="utf-8")
    rows = rerun_approved.list_approved(approved)
    assert [row["filename"] for row in rows] == ["approved_ok.json"]


def test_main_list_prints_json(tmp_path: Path, monkeypatch, capsys) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    (approved / "approved_abc123.json").write_text(
        json.dumps(make_valid_script()), encoding="utf-8"
    )
    monkeypatch.setattr(rerun_approved, "APPROVED_DIR", approved)
    assert rerun_approved.main(["--list"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["story_hash"] == "abc123"


def test_main_without_args_prints_usage(capsys) -> None:
    assert rerun_approved.main([]) == 1
    assert "Usage:" in capsys.readouterr().out
