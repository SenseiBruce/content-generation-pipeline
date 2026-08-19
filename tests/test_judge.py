from agents.judge import _extract_improved_script, _parse_score, judge_script
from tests.helpers import make_valid_script

SAMPLE_APPROVED = """
HOOK_STRENGTH: 28
SEARCH_INTENT: 24
PRACTICAL_VALUE: 23
RETENTION: 9
EMOTIONAL_TRIGGER: 8
TOTAL: 92
VERDICT: APPROVED
FEEDBACK: Strong hook with a specific RBI number and a clear EMI action.
"""

SAMPLE_IMPROVE = """
HOOK_STRENGTH: 20
SEARCH_INTENT: 18
PRACTICAL_VALUE: 20
RETENTION: 7
EMOTIONAL_TRIGGER: 6
TOTAL: 71
VERDICT: IMPROVE
FEEDBACK: Make the first line more specific about EMI impact.
IMPROVED_SCRIPT: %s
"""


def test_parse_score_approved():
    total, verdict, feedback = _parse_score(SAMPLE_APPROVED)
    assert total == 92
    assert verdict == "APPROVED"
    assert "EMI" in feedback


def test_parse_score_falls_back_to_computed_total():
    text = """
HOOK_STRENGTH: 10
SEARCH_INTENT: 10
PRACTICAL_VALUE: 10
RETENTION: 5
EMOTIONAL_TRIGGER: 5
VERDICT: REJECT
FEEDBACK: Off-topic market chatter.
"""
    total, verdict, feedback = _parse_score(text)
    assert total == 40
    assert verdict == "REJECT"
    assert "Off-topic" in feedback


def test_extract_improved_script():
    script = make_valid_script(project_name="Improved RBI Short")
    import json

    raw = SAMPLE_IMPROVE % json.dumps(script)
    improved = _extract_improved_script(raw)
    assert improved is not None
    assert improved["project_name"] == "Improved RBI Short"
    assert len(improved["scenes"]) == 5


def test_extract_improved_script_missing_block():
    assert _extract_improved_script(SAMPLE_APPROVED) is None


def test_judge_script_approves(monkeypatch):
    monkeypatch.setattr("agents.judge.OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "agents.judge._call_judge_llm",
        lambda *args, **kwargs: SAMPLE_APPROVED,
    )
    decision, script, score = judge_script(make_valid_script())
    assert decision == "APPROVED"
    assert score == 92
    assert script["project_name"] == "RBI Rate Shock"


def test_judge_script_rejects_low_score(monkeypatch):
    monkeypatch.setattr("agents.judge.OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(
        "agents.judge._call_judge_llm",
        lambda *args, **kwargs: (
            "HOOK_STRENGTH: 5\nSEARCH_INTENT: 5\nPRACTICAL_VALUE: 5\n"
            "RETENTION: 2\nEMOTIONAL_TRIGGER: 2\nTOTAL: 19\n"
            "VERDICT: REJECT\nFEEDBACK: Off-topic."
        ),
    )
    decision, _script, score = judge_script(make_valid_script())
    assert decision == "REJECTED"
    assert score == 19
