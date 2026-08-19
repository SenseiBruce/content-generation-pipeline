from pipeline import http_client


def test_post_applies_default_timeout(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(http_client.requests, "post", fake_post)
    result = http_client.post("https://example.test/v1", json={"a": 1})
    assert result == "ok"
    assert captured["url"] == "https://example.test/v1"
    assert captured["kwargs"]["timeout"] == http_client.DEFAULT_TIMEOUT
    assert captured["kwargs"]["json"] == {"a": 1}


def test_get_applies_default_timeout(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(http_client.requests, "get", fake_get)
    result = http_client.get("https://example.test/img.png")
    assert result == "ok"
    assert captured["kwargs"]["timeout"] == http_client.DEFAULT_TIMEOUT
