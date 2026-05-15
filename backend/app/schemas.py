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
