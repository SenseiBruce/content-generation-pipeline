"""
Pydantic models for pipeline artifacts.

ScriptSchema mirrors SCHEMA_TEMPLATE in agents/scriptwriter.py and enforces
the same word-count / no-text rules the judge expects.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FORBIDDEN_IMAGE_TERMS = (
    "text",
    "letter",
    "word",
    "caption",
    "watermark",
    "banner",
    "title",
    "label",
    "font",
)


def _word_count(value: str) -> int:
    return len(value.split())


class CaptionSchema(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def caption_length(cls, value: str) -> str:
        n = _word_count(value)
        if not (4 <= n <= 10):
            raise ValueError(f"caption has {n} words (need 5-8)")
        return value


class SceneSchema(BaseModel):
    id: int
    voice_over: str
    image_prompt: str
    caption: CaptionSchema

    @field_validator("voice_over")
    @classmethod
    def voice_over_length(cls, value: str) -> str:
        n = _word_count(value)
        if not (15 <= n <= 25):
            raise ValueError(f"voice_over has {n} words (need 15-22 for duration)")
        return value

    @field_validator("image_prompt")
    @classmethod
    def image_prompt_has_no_text(cls, value: str) -> str:
        lowered = value.lower()
        for term in FORBIDDEN_IMAGE_TERMS:
            if term in lowered:
                raise ValueError(f"image_prompt contains forbidden term '{term}'")
        return value


class CategoriesSchema(BaseModel):
    topics: List[str] = Field(default_factory=list)
    emotions: List[str] = Field(default_factory=list)
    audience: List[str] = Field(default_factory=list)


class MetadataSchema(BaseModel):
    source_url: str = ""
    original_title: str = ""
    fact_check_status: str = "pending"
    story_hash: str = ""
    categories: CategoriesSchema = Field(default_factory=CategoriesSchema)


class ScriptSchema(BaseModel):
    """Canonical YouTube Shorts script produced by the scriptwriter agent."""

    model_config = ConfigDict(extra="allow")

    project_name: str
    series_color: str = "#FF6B35"
    title: str
    description: str
    tags: List[str]
    scenes: List[SceneSchema]
    metadata: MetadataSchema = Field(default_factory=MetadataSchema)

    @field_validator("project_name")
    @classmethod
    def project_name_length(cls, value: str) -> str:
        if len(value) > 30:
            raise ValueError("project_name exceeds 30 characters")
        return value

    @field_validator("title")
    @classmethod
    def title_length(cls, value: str) -> str:
        if len(value) > 70:
            raise ValueError(f"Title too long: {len(value)} chars (max 70 for SEO)")
        return value

    @field_validator("description")
    @classmethod
    def description_length(cls, value: str) -> str:
        n = _word_count(value)
        if not (250 <= n <= 400):
            raise ValueError(f"Description word count {n} (need 250-350 for SEO weight)")
        return value

    @model_validator(mode="after")
    def five_scenes(self) -> "ScriptSchema":
        if len(self.scenes) != 5:
            raise ValueError(f"Expected 5 scenes for 30s+ length, got {len(self.scenes)}")
        return self
