import json

import pytest
from fastapi import HTTPException

from app.groq_client import GroqClient


class FakeResponse:
    def __init__(self, status_code: int, body, text: str = ""):
        self.status_code = status_code
        self._body = body
        self.text = text or (json.dumps(body) if body is not None else "")

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def patch_post(monkeypatch, gc: GroqClient, response: FakeResponse):
    async def fake_post(url, json=None):  # noqa: A002 - mirror httpx signature
        return response
    monkeypatch.setattr(gc._client, "post", fake_post)


@pytest.fixture
def gc():
    return GroqClient(api_key="test-key")


async def test_happy_path_returns_parsed_content(monkeypatch, gc):
    inner = {"distortions": [{"name": "Катастрофизация", "explanation": "x"}]}
    body = {"choices": [{"message": {"content": json.dumps(inner)}}]}
    patch_post(monkeypatch, gc, FakeResponse(200, body))
    assert await gc._call("sys", "usr") == inner


async def test_error_object_with_http_200_is_treated_as_failure(monkeypatch, gc):
    patch_post(
        monkeypatch, gc, FakeResponse(200, {"error": {"code": 502, "message": "provider down"}})
    )
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 502


async def test_invalid_api_key_maps_to_500(monkeypatch, gc):
    patch_post(
        monkeypatch,
        gc,
        FakeResponse(400, {"error": {"code": "invalid_api_key", "message": "Invalid API Key"}}),
    )
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 500
    assert e.value.detail == "Upstream auth failure"


async def test_429_maps_to_429(monkeypatch, gc):
    patch_post(
        monkeypatch, gc, FakeResponse(429, {"error": {"code": 429, "message": "slow down"}})
    )
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 429


async def test_non_json_body_maps_to_502(monkeypatch, gc):
    patch_post(
        monkeypatch,
        gc,
        FakeResponse(200, json.JSONDecodeError("boom", "doc", 0), text="<html>502</html>"),
    )
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 502


async def test_content_not_json_maps_to_502(monkeypatch, gc):
    body = {"choices": [{"message": {"content": "not json at all"}}]}
    patch_post(monkeypatch, gc, FakeResponse(200, body))
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 502
    assert e.value.detail == "Invalid JSON from upstream"


async def test_empty_choices_maps_to_502(monkeypatch, gc):
    patch_post(monkeypatch, gc, FakeResponse(200, {"choices": []}))
    with pytest.raises(HTTPException) as e:
        await gc._call("sys", "usr")
    assert e.value.status_code == 502
