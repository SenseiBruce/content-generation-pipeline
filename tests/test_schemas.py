import pytest
from pydantic import ValidationError

from pipeline.errors import PipelineValidationError
from pipeline.schemas import ScriptSchema
from tests.helpers import make_valid_script


def test_script_schema_accepts_valid_script():
    script = make_valid_script()
    parsed = ScriptSchema.model_validate(script)
    assert parsed.project_name == "RBI Rate Shock"
    assert len(parsed.scenes) == 5
    assert parsed.title.startswith("RBI")


def test_script_schema_rejects_malformed_script():
    bad = make_valid_script()
    bad["scenes"] = []
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_short_voice_over():
    bad = make_valid_script()
    bad["scenes"][0]["voice_over"] = "Too short."
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_forbidden_image_prompt():
    bad = make_valid_script()
    bad["scenes"][0]["image_prompt"] = "A banner with watermark text overlay"
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_long_title():
    bad = make_valid_script(title="x" * 71)
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_long_project_name():
    bad = make_valid_script(project_name="x" * 31)
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_short_description():
    bad = make_valid_script(description="too short")
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_script_schema_rejects_short_caption():
    bad = make_valid_script()
    bad["scenes"][0]["caption"]["text"] = "hi"
    with pytest.raises(ValidationError):
        ScriptSchema.model_validate(bad)


def test_pipeline_validation_error_wraps_schema_failure():
    from agents.scriptwriter import _validate_script

    with pytest.raises(PipelineValidationError):
        _validate_script({"project_name": "x"})
