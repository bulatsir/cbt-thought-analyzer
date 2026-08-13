from typing import Annotated, Literal

from pydantic import BaseModel, Field


class Distortion(BaseModel):
    name: str
    explanation: str = ""


class AnalyzeRequest(BaseModel):
    thought: str = Field(min_length=1, max_length=2000)
    situation: str | None = Field(default=None, max_length=2000)
    emotions: str | None = Field(default=None, max_length=2000)
    language: Literal["ru", "en"] = "ru"
    # Предыдущие звенья «техники стрелки», от первого к последнему. Без них
    # глубокое звено («значит я никому не нужен») уезжает на разбор обрывком:
    # модель не знает, что это ответ на «и что с того?» к предыдущей мысли, и
    # ставит метки беднее. Пусто — обычная одиночная мысль, поведение прежнее.
    preceding: list[Annotated[str, Field(max_length=2000)]] = Field(
        default_factory=list, max_length=8
    )
    # Необязательный выбор модели. Проверяется по ALLOWED_MODELS в groq_client:
    # строку из запроса в апстрим не пускаем. Не из списка → тихий откат на
    # дефолт, а не ошибка (см. _resolve_model).
    model: str | None = Field(default=None, max_length=120)


class AnalyzeResponse(BaseModel):
    distortions: list[Distortion]
    # Кто РЕАЛЬНО ответил — из ответа OpenRouter, а не то, что мы просили:
    # он может увести запрос на другого провайдера. Клиент кладёт это в
    # сохранённую мысль, чтобы потом можно было честно посчитать долю 👎
    # по каждой модели. Без этого переключатель моделей портит разметку.
    model: str = ""


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


class TranscribeResponse(BaseModel):
    text: str


class BeliefEntry(BaseModel):
    date: str = Field(max_length=40)  # ISO-8601, rendered into the prompt as-is
    situation: str = Field(default="", max_length=2000)
    emotions: str = Field(default="", max_length=2000)
    thoughts: list[str] = Field(default_factory=list, max_length=50)
    # Canonical distortion names already resolved by the client from its own store.
    distortions: list[str] = Field(default_factory=list, max_length=50)


class BeliefsRequest(BaseModel):
    # min_length mirrors the client-side gate: below ~10 entries there is no
    # pattern to find, and a forced hypothesis about yourself does harm.
    entries: list[BeliefEntry] = Field(min_length=10, max_length=200)
    language: Literal["ru", "en"] = "ru"


class CoreBelief(BaseModel):
    belief: str
    # BELIEF_AREAS rawValue: self / others / world.
    area: str
    evidence: list[str] = Field(default_factory=list)


class BeliefsResponse(BaseModel):
    beliefs: list[CoreBelief] = Field(default_factory=list)
    summary: str = ""
