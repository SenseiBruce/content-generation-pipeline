"""Tests for WhatsApp STATUS health output."""

from __future__ import annotations

import whatsapp_listener


def test_status_prints_inspect_health(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        whatsapp_listener,
        "inspect_health",
        lambda: {
            "ok": False,
            "last_run": "2026-08-24T01:00:00",
            "age_hours": 9.2,
            "stale": True,
            "abort_reason": None,
            "reason": "stale last_run (9.2h > 8.0h)",
        },
    )
    whatsapp_listener.handle_message("STATUS")
    out = capsys.readouterr().out
    assert "PIPELINE STATUS: unhealthy" in out
    assert "last_run: 2026-08-24T01:00:00" in out
    assert "stale: True" in out
    assert "stale last_run" in out


def test_status_ok(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        whatsapp_listener,
        "inspect_health",
        lambda: {
            "ok": True,
            "last_run": "2026-08-24T10:00:00",
            "age_hours": 1.0,
            "stale": False,
            "abort_reason": None,
            "reason": "ok",
        },
    )
    whatsapp_listener.handle_message("status please")
    out = capsys.readouterr().out
    assert "PIPELINE STATUS: ok" in out
    assert "reason: ok" in out
