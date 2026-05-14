import json
import logging
import os
from typing import Any

import httpx
from fastapi import HTTPException

from app.prompts import (
    DISTORTIONS,
    DISTORTIONS_EN,
    build_downward_arrow_system_prompt,
    build_downward_arrow_user_prompt,
    build_socratic_system_prompt,
    build_socratic_user_prompt,
    build_system_prompt,
    build_user_prompt,
)
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    Distortion,
    DownwardArrowResponse,
    SocraticResponse,
    TechniqueRequest,
)

_CANONICAL_NAMES_BY_LANG: dict[str, set[str]] = {
    "ru": set(DISTORTIONS),
    "en": set(DISTORTIONS_EN),
}

logger = logging.getLogger(__name__)

UPSTREAM_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct"
TIMEOUT_SECONDS = 20.0


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
                    "provider": {"order": ["groq", "sambanova-turbo"], "allow_fallbacks": True},
                },
            )
        except httpx.TimeoutException as e:
            logger.warning("Groq timeout: %s", e)
            raise HTTPException(status_code=504, detail="Upstream timeout")
        except httpx.HTTPError as e:
            logger.exception("Groq request failed")
            raise HTTPException(status_code=502, detail="Upstream unavailable") from e

        if response.status_code == 401:
            logger.error("Groq returned 401 — check GROQ_API_KEY")
            raise HTTPException(status_code=500, detail="Upstream auth failure")
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail="Upstream rate-limited")
        if response.status_code >= 500:
            logger.error("Groq 5xx: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=502, detail="Upstream error")
        if response.status_code >= 400:
            logger.error("Groq 4xx: %s %s", response.status_code, response.text)
            raise HTTPException(status_code=502, detail="Upstream error")

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise HTTPException(status_code=502, detail="Empty response from upstream")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Non-JSON from Groq: %s", content[:200])
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

    async def downward_arrow(self, req: TechniqueRequest) -> DownwardArrowResponse:
        parsed = await self._call(
            build_downward_arrow_system_prompt(),
            build_downward_arrow_user_prompt(
                req.thought, req.distortions, req.history, req.situation, req.emotions
            ),
        )
        question = parsed.get("question")
        if not isinstance(question, str) or not question.strip():
            question = "И что это значит для тебя?"
        is_core = parsed.get("isCoreBelief") is True
        return DownwardArrowResponse(question=question, isCoreBelief=is_core)

    async def socratic(self, req: TechniqueRequest) -> SocraticResponse:
        parsed = await self._call(
            build_socratic_system_prompt(),
            build_socratic_user_prompt(
                req.thought, req.distortions, req.history, req.situation, req.emotions
            ),
        )
        question = parsed.get("question")
        if not isinstance(question, str) or not question.strip():
            question = "Какие факты подтверждают эту мысль?"
        return SocraticResponse(question=question)
