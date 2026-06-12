from typing import Literal

from pydantic import BaseModel, Field


class Distortion(BaseModel):
    name: str
    explanation: str = ""


class AnalyzeRequest(BaseModel):
    thought: str = Field(min_length=1, max_length=2000)
    situation: str | None = Field(default=None, max_length=2000)
    emotions: str | None = Field(default=None, max_length=2000)
    language: Literal["ru", "en"] = "ru"


class AnalyzeResponse(BaseModel):
    distortions: list[Distortion]


class SuggestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice_names: list[str] = Field(default_factory=list, max_length=20)
    language: Literal["ru", "en"] = "ru"


class SuggestResponse(BaseModel):
    # Voice name from the request roster, or None if the model is unsure.
    voice_name: str | None = None
    # ThoughtTheme rawValues (selfCriticism / threat / loss / injustice).
    themes: list[str] = Field(default_factory=list)


class ReviewMoment(BaseModel):
    text: str = Field(default="", max_length=4000)
    voices: list[str] = Field(default_factory=list, max_length=20)
    themes: list[str] = Field(default_factory=list, max_length=10)
    date: str = Field(max_length=40)  # ISO-8601, rendered into the prompt as-is


class ReviewRequest(BaseModel):
    moments: list[ReviewMoment] = Field(min_length=1, max_length=100)
    language: Literal["ru", "en"] = "ru"


class ReviewResponse(BaseModel):
    review: str
