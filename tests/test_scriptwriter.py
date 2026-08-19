import json
from pathlib import Path

from agents.scriptwriter import _extract_json, _validate_script, generate_script
from pipeline.errors import PipelineValidationError
from pipeline.schemas import ScriptSchema
from tests.helpers import make_valid_script


def test_extract_json_direct():
    script = make_valid_script()
    parsed = _extract_json(json.dumps(script))
    assert parsed["project_name"] == script["project_name"]
    assert len(parsed["scenes"]) == 5


def test_extract_json_from_markdown_fence():
    script = make_valid_script()
    raw = "```json\n" + json.dumps(script) + "\n```"
    parsed = _extract_json(raw)
    assert parsed["title"] == script["title"]


def test_extract_json_from_noisy_wrapper():
    script = make_valid_script()
    raw = "Here is the script:\n" + json.dumps(script) + "\nThanks."
    parsed = _extract_json(raw)
    assert parsed["metadata"]["story_hash"] == "abc123"


def test_validate_script_accepts_valid_dict():
    parsed = _validate_script(make_valid_script())
    assert isinstance(parsed, ScriptSchema)
    assert parsed.project_name == "RBI Rate Shock"


def test_validate_script_raises_on_malformed():
    try:
        _validate_script({"title": "nope"})
        raise AssertionError("expected PipelineValidationError")
    except PipelineValidationError:
        pass


def test_generate_script_uses_openrouter_fixture(monkeypatch, tmp_path, fixture_dir: Path):
    payload = json.loads((fixture_dir / "openrouter_response.json").read_text(encoding="utf-8"))

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return payload

    monkeypatch.setattr("pipeline.http_client.post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("agents.scriptwriter.OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("agents.scriptwriter.SCRIPTS_DIR", tmp_path)

    story = {
        "title": "RBI changes repo rate",
        "source": "Economic Times",
        "link": "https://example.com/rbi",
        "hash": "abc123",
        "priority_score": 88,
    }
    script = generate_script(story)

    assert script is not None
    assert script["project_name"] == "RBI Rate Shock"
    assert script["metadata"]["story_hash"] == "abc123"
    assert script["metadata"]["source_url"] == "https://example.com/rbi"
    draft = tmp_path / "draft_abc123.json"
    assert draft.exists()
    saved = json.loads(draft.read_text(encoding="utf-8"))
    assert saved["title"] == script["title"]
