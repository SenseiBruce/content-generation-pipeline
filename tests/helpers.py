"""Shared builders for pipeline unit tests."""

from __future__ import annotations

from typing import Any, Dict, List


def filler_description(n: int = 280) -> str:
    words = (
        "Indian households should review home loans deposits and tax saving "
        "options after this policy move from the central bank affecting EMIs"
    ).split()
    out: List[str] = []
    i = 0
    while len(out) < n:
        out.append(words[i % len(words)])
        i += 1
    return " ".join(out) + " #Shorts #Finance #India Subscribe to Capital Architects"


VOICE_OVER = (
    "The Reserve Bank of India has just changed the repo rate affecting "
    "every home loan in the country today."
)

IMAGE_PROMPT = (
    "Cinematic vault of gold coins under dramatic lighting, vertical composition, photorealistic"
)

CAPTIONS = [
    "RBI repo rate hike hits",
    "Home loans get more expensive",
    "Your EMI may rise soon",
    "Check your floating rate now",
    "Subscribe for weekly money alerts",
]


def make_valid_script(**overrides: Any) -> Dict[str, Any]:
    script: Dict[str, Any] = {
        "project_name": "RBI Rate Shock",
        "series_color": "#FF6B35",
        "title": "RBI repo rate hike hits home loans",
        "description": filler_description(),
        "tags": ["rbi", "repo rate", "home loan", "emi", "india finance"],
        "scenes": [
            {
                "id": i,
                "voice_over": VOICE_OVER,
                "image_prompt": IMAGE_PROMPT,
                "caption": {"text": CAPTIONS[i - 1]},
            }
            for i in range(1, 6)
        ],
        "metadata": {
            "source_url": "https://example.com/rbi",
            "original_title": "RBI changes repo rate",
            "fact_check_status": "pending",
            "story_hash": "abc123",
            "categories": {"topics": ["rbi"], "emotions": ["urgency"], "audience": ["salaried"]},
        },
    }
    script.update(overrides)
    return script
