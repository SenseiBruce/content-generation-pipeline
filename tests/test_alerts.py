from pipeline.alerts import notify_failure


def test_notify_failure_noops_without_webhook(monkeypatch):
    monkeypatch.delenv("ERROR_WEBHOOK_URL", raising=False)
    assert notify_failure("boom", {"status": "aborted"}) is False


def test_notify_failure_posts_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse()

    monkeypatch.setenv("ERROR_WEBHOOK_URL", "https://hooks.example.test/abort")
    monkeypatch.setattr("pipeline.http_client.post", fake_post)

    summary = {"status": "aborted", "abort_reason": "Time exceeded"}
    assert notify_failure("Time exceeded", summary) is True
    assert captured["url"] == "https://hooks.example.test/abort"
    assert captured["json"]["event"] == "pipeline_aborted"
    assert captured["json"]["reason"] == "Time exceeded"
    assert captured["json"]["summary"]["status"] == "aborted"


def test_notify_failure_returns_false_on_request_error(monkeypatch):
    from pipeline.http_client import RequestException

    def fake_post(url, **kwargs):
        raise RequestException("timeout")

    monkeypatch.setenv("ERROR_WEBHOOK_URL", "https://hooks.example.test/abort")
    monkeypatch.setattr("pipeline.http_client.post", fake_post)
    assert notify_failure("boom", {"status": "aborted"}) is False
