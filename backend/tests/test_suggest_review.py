import pytest
from fastapi import HTTPException

from app.groq_client import GroqClient, _strip_fences
from app.schemas import ReviewMoment, ReviewRequest, SuggestRequest


@pytest.fixture
def client(monkeypatch):
    gc = GroqClient(api_key="test-key")

    def set_reply(parsed: dict):
        async def fake_call(system_prompt, user_prompt, max_tokens=512):
            return parsed
        monkeypatch.setattr(gc, "_call", fake_call)

    gc.set_reply = set_reply  # type: ignore[attr-defined]
    return gc


ROSTER = ["тревожник", "стыдобист", "злобник"]


def _req(**kwargs) -> SuggestRequest:
    defaults = dict(text="опять всё завалю", voice_names=ROSTER, language="ru")
    defaults.update(kwargs)
    return SuggestRequest(**defaults)


# ── /suggest filtering ──


async def test_suggest_passes_roster_voice_and_canonical_themes(client):
    client.set_reply({"voice_name": "тревожник", "themes": ["threat"]})
    resp = await client.suggest(_req())
    assert resp.voice_name == "тревожник"
    assert resp.themes == ["threat"]


async def test_suggest_drops_non_roster_voice(client):
    client.set_reply({"voice_name": "перфекционист", "themes": []})
    resp = await client.suggest(_req())
    assert resp.voice_name is None


async def test_suggest_null_voice_is_valid(client):
    client.set_reply({"voice_name": None, "themes": ["selfCriticism"]})
    resp = await client.suggest(_req())
    assert resp.voice_name is None
    assert resp.themes == ["selfCriticism"]


async def test_suggest_drops_non_canonical_themes_and_dedupes(client):
    client.set_reply(
        {"voice_name": None, "themes": ["threat", "made-up", "threat", "loss"]}
    )
    resp = await client.suggest(_req())
    # Cap [:2] applies to the raw list: ["threat", "made-up"] → one survives.
    assert resp.themes == ["threat"]


async def test_suggest_caps_themes_at_two(client):
    client.set_reply(
        {"voice_name": None, "themes": ["threat", "loss", "injustice"]}
    )
    resp = await client.suggest(_req())
    assert resp.themes == ["threat", "loss"]


async def test_suggest_tolerates_garbage_shapes(client):
    client.set_reply({"voice_name": 42, "themes": "broken"})
    resp = await client.suggest(_req())
    assert resp.voice_name is None
    assert resp.themes == []


async def test_suggest_empty_roster_forces_null(client):
    client.set_reply({"voice_name": "тревожник", "themes": []})
    resp = await client.suggest(_req(voice_names=[]))
    assert resp.voice_name is None


# ── /review ──


def _review_req() -> ReviewRequest:
    return ReviewRequest(
        moments=[
            ReviewMoment(
                text="накрыло перед созвоном",
                voices=["тревожник"],
                themes=["threat"],
                date="2026-06-10T09:00:00Z",
            )
        ],
        language="ru",
    )


async def test_review_returns_text(client):
    client.set_reply({"review": "  За неделю чаще всего звучал тревожник.  "})
    resp = await client.review(_review_req())
    assert resp.review == "За неделю чаще всего звучал тревожник."


async def test_review_empty_text_is_502(client):
    client.set_reply({"review": "   "})
    with pytest.raises(HTTPException) as e:
        await client.review(_review_req())
    assert e.value.status_code == 502


async def test_review_missing_key_is_502(client):
    client.set_reply({"summary": "wrong key"})
    with pytest.raises(HTTPException) as e:
        await client.review(_review_req())
    assert e.value.status_code == 502


# ── fence stripping ──


def test_strip_fences_plain_json_untouched():
    assert _strip_fences('{"a": 1}') == '{"a": 1}'


def test_strip_fences_markdown_block():
    assert _strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_fences_with_preamble():
    assert _strip_fences('Here you go:\n{"a": {"b": 2}}\nDone.') == '{"a": {"b": 2}}'


def test_strip_fences_no_braces_passthrough():
    assert _strip_fences("not json at all") == "not json at all"
