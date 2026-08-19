"""
Thin HTTP wrapper so agents never call requests directly.

Tests monkeypatch `pipeline.http_client.post` / `.get` instead of hitting
OpenRouter, Runware, Voicebox, or any other live endpoint.
"""

from __future__ import annotations

from typing import Any

import requests
from requests import RequestException, Response

DEFAULT_TIMEOUT = 60

__all__ = ["DEFAULT_TIMEOUT", "RequestException", "Response", "get", "post"]


def post(url: str, **kwargs: Any) -> Response:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return requests.post(url, **kwargs)


def get(url: str, **kwargs: Any) -> Response:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return requests.get(url, **kwargs)
