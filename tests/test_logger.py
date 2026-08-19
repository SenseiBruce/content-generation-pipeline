import json
import logging

from pipeline.logger import JsonLogFormatter, extra_fields


def test_extra_fields_include_stage_and_run_id():
    extra = extra_fields("watchtower", "run-abc", duration_ms=1500)
    assert extra["stage"] == "watchtower"
    assert extra["run_id"] == "run-abc"
    assert extra["duration_ms"] == 1500


def test_json_log_record_contains_stage_and_run_id():
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="orchestrator",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Stage %s started",
        args=("watchtower",),
        exc_info=None,
    )
    record.stage = "watchtower"
    record.run_id = "run-abc"
    record.duration_ms = 42

    payload = json.loads(formatter.format(record))
    assert payload["stage"] == "watchtower"
    assert payload["run_id"] == "run-abc"
    assert payload["duration_ms"] == 42
    assert payload["level"] == "INFO"
    assert payload["message"] == "Stage watchtower started"
    assert "timestamp" in payload
