import json
import logging
import os
from typing import Any, NamedTuple

import httpx
from fastapi import HTTPException

from app.prompts import (
    BELIEF_AREAS,
    build_analyze_schema,
    build_beliefs_schema,
    DISTORTIONS,
    DISTORTIONS_EN,
    THEME_KEYS,
    build_beliefs_system_prompt,
    build_beliefs_user_prompt,
    build_review_system_prompt,
    build_review_user_prompt,
    build_suggest_system_prompt,
    build_suggest_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BeliefsRequest,
    BeliefsResponse,
    CoreBelief,
    Distortion,
    ReviewRequest,
    ReviewResponse,
    SuggestRequest,
    SuggestResponse,
)

_CANONICAL_NAMES_BY_LANG: dict[str, set[str]] = {
    "ru": set(DISTORTIONS),
    "en": set(DISTORTIONS_EN),
}

logger = logging.getLogger(__name__)

UPSTREAM_URL = "https://openrouter.ai/api/v1/chat/completions"
# Sonnet 5 since 2026-08-09 (was Sonnet 4.6). Cheaper than 4.6 on OpenRouter
# right now — $2/$10 per MTok intro through 2026-08-31, $3/$15 after, i.e. never
# worse than what 4.6 cost. Opus 5 ($5/$25) was considered and rejected: the
# real /analyze failure is explanation *style*, not label accuracy (85% of user
# verdicts are 👍, and 13 of 15 👎 say "weak explanation", only 1 "wrong label"),
# so it is a prompting problem a bigger model does not fix. Opus 5 also runs
# adaptive thinking by default, which shares max_tokens with the answer and
# would blow the reactive 1.5s-debounce UX on the client.
MODEL = "anthropic/claude-sonnet-5"

# Клиент может выбрать модель, но только из этого списка: строку из запроса в
# апстрим пускать нельзя — это чужие деньги и чужие модели. Все проверены на
# нашей задаче: держат канонические имена, слушаются json_schema, отвечают
# по-русски. Замеры 2026-08-12 на 12 реальных мыслях (100 вызовов):
#   sonnet-5      10.0s  127¢   — качество эталонное
#   luna           4.7s    5¢   — вдвое быстрее, в 24 раза дешевле
#   luna-pro      11.6s   16¢   — медленнее и дороже luna без выигрыша
ALLOWED_MODELS: tuple[str, ...] = (
    "anthropic/claude-sonnet-5",
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-luna-pro",
)

TIMEOUT_SECONDS = 30.0

# Speech-to-text (voice-to-text). OpenAI gpt-4o-transcribe: best Russian
# transcription with punctuation, ~$0.006/min. Same OpenRouter key.
TRANSCRIBE_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
TRANSCRIBE_MODEL = "openai/gpt-4o-transcribe"
TRANSCRIBE_TIMEOUT_SECONDS = 60.0


def _strip_fences(content: str) -> str:
    """Claude occasionally wraps JSON in a ```json fence despite
    response_format — cut from the first '{' to the last '}'."""
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        return content[start : end + 1]
    return content


def _raise_for_upstream(status: int, data: Any, text: str) -> None:
    """Map an OpenRouter error response to an HTTPException, or return if OK.

    OpenRouter (and the providers behind it) report errors as a JSON
    {"error": {"code", "message"}} object — sometimes even with HTTP 200,
    when a provider fails after accepting the request. So treat a present
    "error" key as failure regardless of status."""
    err = data.get("error") if isinstance(data, dict) else None
    if err is None and status < 400:
        return
    err = err if isinstance(err, dict) else {}
    code = err.get("code", status)
    message = err.get("message") or text[:300]
    blob = f"{code} {message}".lower()
    # Groq returns "invalid_api_key" (not 403) when the key is scoped or its
    # Allowed Models list excludes the model — looks like a generic upstream
    # failure unless we name it. See memory: groq_key_scope_gotcha.
    is_auth = (
        status in (401, 403)
        or code in (401, 403)
        or "invalid_api_key" in blob
        or "invalid api key" in blob
    )
    if is_auth:
        logger.error(
            "Upstream auth failure (status=%s code=%s): %s — check "
            "GROQ_API_KEY scope / Allowed Models",
            status,
            code,
            message,
        )
        raise HTTPException(status_code=500, detail="Upstream auth failure")
    if status == 429 or code == 429:
        logger.warning("Upstream rate-limited: %s", message)
        raise HTTPException(status_code=429, detail="Upstream rate-limited")
    logger.error("Upstream error (status=%s code=%s): %s", status, code, message)
    raise HTTPException(status_code=502, detail="Upstream error")


def _resolve_model(requested: str | None) -> str:
    """Модель из запроса, если она в белом списке; иначе дефолтная.

    Неизвестную не отклоняем четырёхсоткой намеренно: клиент может быть старее
    или новее бэка, и разбор мысли важнее, чем точность выбора модели — лучше
    ответить дефолтной и оставить след в логах, чем показать человеку ошибку.
    """
    if requested is None:
        return MODEL
    if requested in ALLOWED_MODELS:
        return requested
    logger.warning("Requested model %r not allowed, falling back to %s", requested, MODEL)
    return MODEL


class _Reply(NamedTuple):
    """Разобранный ответ + модель, которая его фактически выдала."""

    data: dict[str, Any]
    model: str


class _Unusable(Exception):
    """Апстрим ответил, но ответ непригоден: пустой content или не-JSON.

    Отличается от ошибок в `_raise_for_upstream` тем, что это плавающий сбой,
    а не отказ: один и тот же ввод на повторе обычно проходит (замеряли — на
    некоторых мыслях примерно 1 из 5 падал, остальные 4 отвечали нормально).
    Поэтому такой сбой ретраится внутри `_call`, а не летит наружу как 502.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class GroqClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Title": "CBT Thought Analyzer",
        }
        # Optional: tag requests in OpenRouter analytics with your public URL.
        # Set PUBLIC_URL env var if you want this; left blank by default so the
        # source repo doesn't hardcode a personal deployment URL.
        if referer := os.environ.get("PUBLIC_URL"):
            headers["HTTP-Referer"] = referer
        self._client = httpx.AsyncClient(timeout=TIMEOUT_SECONDS, headers=headers)

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        schema: dict | None = None,
        model: str | None = None,
    ) -> "_Reply":
        """Один осмысленный ответ от апстрима, с повтором на непригодный.

        temperature=0.3, так что повтор — это новая выборка, а не тот же ответ
        ещё раз. Два захода выбраны сознательно: сбой независимый и редкий, так
        что второй заход закрывает подавляющую часть, а третий уже заметно бьёт
        по времени ответа там, где пользователь ждёт вживую.
        """
        for attempt in range(2):
            try:
                return await self._call_once(
                    system_prompt, user_prompt, max_tokens, schema, model
                )
            except _Unusable as unusable:
                if attempt == 0:
                    logger.info("Retrying after unusable upstream reply: %s", unusable.detail)
                    continue
                logger.error("Upstream unusable twice: %s", unusable.detail)
                raise HTTPException(status_code=502, detail=unusable.detail)
        raise AssertionError("unreachable")

    async def _call_once(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        schema: dict | None = None,
        model: str | None = None,
    ) -> "_Reply":
        # json_schema, когда схема есть: провайдер сам не даст вернуть имя вне
        # enum. Без схемы — json_object: гарантирует валидный JSON, но не форму.
        response_format: dict[str, Any] = (
            {"type": "json_schema", "json_schema": schema}
            if schema
            else {"type": "json_object"}
        )
        try:
            response = await self._client.post(
                UPSTREAM_URL,
                json={
                    "model": model or MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": response_format,
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                },
            )
        except httpx.TimeoutException as e:
            logger.warning("Groq timeout: %s", e)
            raise HTTPException(status_code=504, detail="Upstream timeout")
        except httpx.HTTPError as e:
            logger.exception("Groq request failed")
            raise HTTPException(status_code=502, detail="Upstream unavailable") from e

        # Parse the body once; _raise_for_upstream inspects it for an "error"
        # key even on HTTP 200 (providers can fail after accepting the request).
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            data = None

        _raise_for_upstream(response.status_code, data, response.text)

        if not isinstance(data, dict):
            logger.warning("Non-JSON from upstream: %s", response.text[:200])
            raise _Unusable("Invalid response from upstream")

        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        content = message.get("content")
        finish = choices[0].get("finish_reason") if choices else None
        if not content:
            logger.warning(
                "Empty content from upstream (finish_reason=%s): %s",
                finish,
                str(data)[:200],
            )
            raise _Unusable("Empty response from upstream")

        try:
            # `model` в ответе — кто РЕАЛЬНО отвечал: OpenRouter может увести
            # запрос на другого провайдера, и в метаданные клиента должно уехать
            # то, что было на самом деле, а не то, что мы просили.
            return _Reply(json.loads(_strip_fences(content)), data.get("model") or model or MODEL)
        except json.JSONDecodeError:
            # Логируем длину и finish_reason: по одному обрезанному до 200
            # символов куску не отличить «обрыв по max_tokens» (finish_reason
            # == "length") от «модель вернула мусор» — на этом я один раз уже
            # поставил неверный диагноз.
            logger.warning(
                "Non-JSON from upstream (len=%d, finish_reason=%s): %s",
                len(content),
                finish,
                content[:200],
            )
            raise _Unusable("Invalid JSON from upstream")

    async def analyze(self, req: AnalyzeRequest) -> AnalyzeResponse:
        reply = await self._call(
            build_system_prompt(req.language),
            build_user_prompt(req.thought, req.situation, req.emotions),
            schema=build_analyze_schema(req.language),
            model=_resolve_model(req.model),
            # 2048, не 512: пояснения v2 называют, на чём мысль стоит и чего в ней
            # не хватает, и вышли заметно длиннее прежних однострочников. Три таких
            # по-русски (~150 токенов каждое) упирались ровно в 512 — JSON обрывался
            # на середине строки, json.loads падал, наружу шёл 502. Клиент ретраит
            # 5xx трижды, поэтому одна длинная мысль стоила трёх обрезанных вызовов.
            # max_tokens — потолок, а не счёт: типичный ответ прежний, платим столько же.
            max_tokens=2048,
        )
        parsed = reply.data
        raw = parsed.get("distortions", [])
        if not isinstance(raw, list):
            raw = []
        canonical = _CANONICAL_NAMES_BY_LANG.get(req.language, set(DISTORTIONS))
        distortions: list[Distortion] = []
        dropped: list[str] = []
        for item in raw[:3]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            name = name.strip()
            # Hard-filter: name must be from the canonical list for the requested
            # language. The model occasionally drifts (e.g. returns Russian name
            # in EN mode) — drop those so the client gets a clean contract.
            if name not in canonical:
                dropped.append(name)
                continue
            explanation = item.get("explanation") or ""
            if not isinstance(explanation, str):
                explanation = ""
            distortions.append(Distortion(name=name, explanation=explanation))
        if dropped:
            logger.warning(
                "analyze dropped non-canonical names (lang=%s): %s",
                req.language,
                dropped,
            )
        return AnalyzeResponse(distortions=distortions, model=reply.model)

    async def suggest(self, req: SuggestRequest) -> SuggestResponse:
        parsed = (await self._call(
            build_suggest_system_prompt(req.voice_names, req.language),
            build_suggest_user_prompt(req.text),
            max_tokens=256,
        )).data

        # Hard-filter: voice must come from the request's roster, themes from
        # the canonical key list — same contract pattern as /analyze.
        voice_name = parsed.get("voice_name")
        if not isinstance(voice_name, str) or voice_name not in set(req.voice_names):
            if voice_name is not None and voice_name != "null":
                logger.warning("suggest dropped non-roster voice: %r", voice_name)
            voice_name = None

        raw_themes = parsed.get("themes", [])
        if not isinstance(raw_themes, list):
            raw_themes = []
        themes: list[str] = []
        for t in raw_themes[:2]:
            if isinstance(t, str) and t in THEME_KEYS and t not in themes:
                themes.append(t)
            elif isinstance(t, str):
                logger.warning("suggest dropped non-canonical theme: %r", t)

        return SuggestResponse(voice_name=voice_name, themes=themes)

    async def review(self, req: ReviewRequest) -> ReviewResponse:
        parsed = (await self._call(
            build_review_system_prompt(req.language),
            build_review_user_prompt(
                [(m.text, m.voices, m.themes, m.date) for m in req.moments],
                req.language,
            ),
            max_tokens=1024,
        )).data
        review = parsed.get("review")
        if not isinstance(review, str) or not review.strip():
            logger.warning("review returned empty/invalid text: %s", str(parsed)[:200])
            raise HTTPException(status_code=502, detail="Empty review from upstream")
        return ReviewResponse(review=review.strip())

    async def beliefs(self, req: BeliefsRequest) -> BeliefsResponse:
        reply = await self._call(
            build_beliefs_system_prompt(req.language),
            build_beliefs_user_prompt(
                [
                    (e.date, e.situation, e.emotions, e.thoughts, e.distortions)
                    for e in req.entries
                ],
                req.language,
            ),
            # 4096, не 1536: цитаты берутся дословно из записей, и на корпусе
            # от ~25 записей ответ обрывался на середине JSON-строки → json.loads
            # падал → наш же 502 «Non-JSON from upstream». Промпт дополнительно
            # ограничивает длину цитат, но потолок должен иметь запас.
            max_tokens=4096,
            schema=build_beliefs_schema(),
        )
        parsed = reply.data

        raw = parsed.get("beliefs", [])
        if not isinstance(raw, list):
            raw = []
        beliefs: list[CoreBelief] = []
        for item in raw[:3]:
            if not isinstance(item, dict):
                continue
            text = item.get("belief")
            if not isinstance(text, str) or not text.strip():
                continue
            # Hard-filter: area must be a canonical key — same contract pattern
            # as /analyze names and /suggest themes.
            area = item.get("area")
            if not isinstance(area, str) or area not in BELIEF_AREAS:
                logger.warning("beliefs dropped non-canonical area: %r", area)
                continue
            raw_evidence = item.get("evidence", [])
            if not isinstance(raw_evidence, list):
                raw_evidence = []
            evidence = [
                q.strip()
                for q in raw_evidence[:4]
                if isinstance(q, str) and q.strip()
            ]
            beliefs.append(
                CoreBelief(belief=text.strip(), area=area, evidence=evidence)
            )

        summary = parsed.get("summary")
        if not isinstance(summary, str):
            summary = ""
        summary = summary.strip()
        # An empty beliefs list is a valid, honest answer ("too few entries to
        # see a pattern") — but only when the summary explains it. Both empty
        # means the model returned nothing usable.
        if not beliefs and not summary:
            logger.warning("beliefs returned nothing usable: %s", str(parsed)[:200])
            raise HTTPException(status_code=502, detail="Empty beliefs from upstream")
        return BeliefsResponse(beliefs=beliefs, summary=summary)

    async def transcribe(
        self,
        audio: bytes,
        filename: str,
        content_type: str,
        language: str,
    ) -> str:
        """Speech-to-text via OpenRouter's transcription API (multipart).
        Returns the transcript text; maps upstream failures to HTTPException."""
        try:
            response = await self._client.post(
                TRANSCRIBE_URL,
                files={"file": (filename, audio, content_type)},
                data={
                    "model": TRANSCRIBE_MODEL,
                    "language": language,
                    "response_format": "json",
                },
                timeout=TRANSCRIBE_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as e:
            logger.warning("Transcribe timeout: %s", e)
            raise HTTPException(status_code=504, detail="Upstream timeout")
        except httpx.HTTPError as e:
            logger.exception("Transcribe request failed")
            raise HTTPException(status_code=502, detail="Upstream unavailable") from e

        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            data = None

        _raise_for_upstream(response.status_code, data, response.text)

        if not isinstance(data, dict):
            logger.warning("Non-JSON from transcribe upstream: %s", response.text[:200])
            raise HTTPException(status_code=502, detail="Invalid response from upstream")

        text = data.get("text")
        if not isinstance(text, str):
            logger.warning("Transcribe returned no text field: %s", str(data)[:200])
            raise HTTPException(status_code=502, detail="Invalid transcription from upstream")
        # Empty text = silence / no speech, NOT an upstream failure — return it
        # (200) and let the client no-op. Only a missing/!str field is a 502.
        return text.strip()
