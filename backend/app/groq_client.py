import json
import logging
import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.prompts import (
    DISTORTIONS,
    DISTORTIONS_EN,
    THEME_KEYS,
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
MODEL = "anthropic/claude-sonnet-4.6"
TIMEOUT_SECONDS = 30.0


def _strip_fences(content: str) -> str:
    """Claude occasionally wraps JSON in a ```json fence despite
    response_format — cut from the first '{' to the last '}'."""
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        return content[start : end + 1]
    return content


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
    ) -> dict[str, Any]:
        try:
            response = await self._client.post(
                UPSTREAM_URL,
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
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

        # Parse the body once. OpenRouter (and the providers behind it) report
        # errors as a JSON {"error": {"code", "message"}} object — sometimes
        # even with HTTP 200, when a provider fails after accepting the
        # request. So treat a present "error" key as failure regardless of
        # status, and always surface the upstream message in logs.
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            data = None

        status = response.status_code
        err = data.get("error") if isinstance(data, dict) else None

        if err is not None or status >= 400:
            err = err if isinstance(err, dict) else {}
            code = err.get("code", status)
            message = err.get("message") or response.text[:300]
            blob = f"{code} {message}".lower()
            # Groq returns "invalid_api_key" (not 403) when the key is scoped
            # or its Allowed Models list excludes this model — looks like a
            # generic upstream failure unless we name it. See memory:
            # groq_key_scope_gotcha.
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
            logger.error(
                "Upstream error (status=%s code=%s): %s", status, code, message
            )
            raise HTTPException(status_code=502, detail="Upstream error")

        if not isinstance(data, dict):
            logger.warning("Non-JSON from upstream: %s", response.text[:200])
            raise HTTPException(status_code=502, detail="Invalid response from upstream")

        choices = data.get("choices") or []
        content = (
            choices[0].get("message", {}).get("content") if choices else None
        )
        if not content:
            logger.warning("Empty content from upstream: %s", str(data)[:200])
            raise HTTPException(status_code=502, detail="Empty response from upstream")

        try:
            return json.loads(_strip_fences(content))
        except json.JSONDecodeError:
            logger.warning("Non-JSON from upstream: %s", content[:200])
            raise HTTPException(status_code=502, detail="Invalid JSON from upstream")

    async def analyze(self, req: AnalyzeRequest) -> AnalyzeResponse:
        parsed = await self._call(
            build_system_prompt(req.language),
            build_user_prompt(req.thought, req.situation, req.emotions),
        )
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
        return AnalyzeResponse(distortions=distortions)

    async def suggest(self, req: SuggestRequest) -> SuggestResponse:
        parsed = await self._call(
            build_suggest_system_prompt(req.voice_names, req.language),
            build_suggest_user_prompt(req.text),
            max_tokens=256,
        )

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
        parsed = await self._call(
            build_review_system_prompt(req.language),
            build_review_user_prompt(
                [(m.text, m.voices, m.themes, m.date) for m in req.moments],
                req.language,
            ),
            max_tokens=1024,
        )
        review = parsed.get("review")
        if not isinstance(review, str) or not review.strip():
            logger.warning("review returned empty/invalid text: %s", str(parsed)[:200])
            raise HTTPException(status_code=502, detail="Empty review from upstream")
        return ReviewResponse(review=review.strip())
