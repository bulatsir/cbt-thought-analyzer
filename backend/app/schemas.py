from typing import Literal

from pydantic import BaseModel, Field


class Distortion(BaseModel):
    name: str
    explanation: str = ""


class HistoryStep(BaseModel):
    question: str
    answer: str


class AnalyzeRequest(BaseModel):
    thought: str = Field(min_length=1, max_length=2000)
    situation: str | None = Field(default=None, max_length=2000)
    emotions: str | None = Field(default=None, max_length=2000)
    language: Literal["ru", "en"] = "ru"


class AnalyzeResponse(BaseModel):
    distortions: list[Distortion]


class TechniqueRequest(BaseModel):
    thought: str = Field(min_length=1, max_length=2000)
    distortions: list[Distortion] = Field(default_factory=list, max_length=10)
    history: list[HistoryStep] = Field(default_factory=list, max_length=20)
    situation: str | None = Field(default=None, max_length=2000)
    emotions: str | None = Field(default=None, max_length=2000)


class DownwardArrowResponse(BaseModel):
    question: str
    isCoreBelief: bool


class SocraticResponse(BaseModel):
    question: str
