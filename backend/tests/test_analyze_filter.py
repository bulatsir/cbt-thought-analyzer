import pytest

from app.groq_client import GroqClient, _Reply
from app.schemas import AnalyzeRequest


@pytest.fixture
def client(monkeypatch):
    gc = GroqClient(api_key="test-key")

    def set_reply(parsed: dict):
        async def fake_call(system_prompt, user_prompt, max_tokens=512, schema=None, model=None):
            return _Reply(parsed, "test/model")
        monkeypatch.setattr(gc, "_call", fake_call)

    gc.set_reply = set_reply  # type: ignore[attr-defined]
    return gc


async def test_drops_non_canonical_names(client):
    client.set_reply(
        {
            "distortions": [
                {"name": "Катастрофизация", "explanation": "ok"},
                {"name": "Made Up Distortion", "explanation": "nope"},
            ]
        }
    )
    resp = await client.analyze(AnalyzeRequest(thought="всё пропало", language="ru"))
    assert [d.name for d in resp.distortions] == ["Катастрофизация"]


async def test_caps_at_three(client):
    client.set_reply(
        {"distortions": [{"name": "Катастрофизация"} for _ in range(5)]}
    )
    resp = await client.analyze(AnalyzeRequest(thought="x", language="ru"))
    assert len(resp.distortions) == 3


async def test_en_mode_uses_english_canonical_list(client):
    client.set_reply(
        {
            "distortions": [
                {"name": "Catastrophizing", "explanation": "english"},
                {"name": "Катастрофизация", "explanation": "ru drift, drop me"},
            ]
        }
    )
    resp = await client.analyze(AnalyzeRequest(thought="all is lost", language="en"))
    assert [d.name for d in resp.distortions] == ["Catastrophizing"]


async def test_missing_or_bad_fields_are_tolerated(client):
    # Note: the [:3] cap is applied to the raw list before validity
    # filtering, so the valid entry must sit within the first 3 to survive.
    client.set_reply(
        {
            "distortions": [
                "not a dict",
                {"name": "   "},
                {"name": "Катастрофизация"},  # no explanation key
                {"explanation": "no name"},
            ]
        }
    )
    resp = await client.analyze(AnalyzeRequest(thought="x", language="ru"))
    assert len(resp.distortions) == 1
    assert resp.distortions[0].name == "Катастрофизация"
    assert resp.distortions[0].explanation == ""


async def test_non_list_distortions_yields_empty(client):
    client.set_reply({"distortions": "broken"})
    resp = await client.analyze(AnalyzeRequest(thought="x", language="ru"))
    assert resp.distortions == []
