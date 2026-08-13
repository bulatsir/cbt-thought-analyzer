import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.groq_client import GroqClient, _Reply
from app.prompts import BELIEF_AREAS, build_beliefs_system_prompt
from app.schemas import BeliefEntry, BeliefsRequest


@pytest.fixture
def client(monkeypatch):
    gc = GroqClient(api_key="test-key")

    def set_reply(parsed: dict):
        async def fake_call(system_prompt, user_prompt, max_tokens=512, schema=None, model=None):
            return _Reply(parsed, "test/model")

        monkeypatch.setattr(gc, "_call", fake_call)

    gc.set_reply = set_reply  # type: ignore[attr-defined]
    return gc


def _entries(n: int = 10) -> list[BeliefEntry]:
    return [
        BeliefEntry(
            date=f"2026-06-{i + 1:02d}T09:00:00Z",
            situation="созвон с командой",
            emotions="тревога",
            thoughts=[f"я опять всё завалю ({i})"],
            distortions=["Поспешные выводы: предсказание будущего"],
        )
        for i in range(n)
    ]


def _req(**kwargs) -> BeliefsRequest:
    defaults: dict = dict(entries=_entries(), language="ru")
    defaults.update(kwargs)
    return BeliefsRequest(**defaults)


# ── request gate ──


def test_fewer_than_ten_entries_rejected():
    # Mirrors the client-side gate: no pattern below ~10 entries.
    with pytest.raises(ValidationError):
        BeliefsRequest(entries=_entries(9), language="ru")


def test_exactly_ten_entries_accepted():
    assert len(BeliefsRequest(entries=_entries(10)).entries) == 10


# ── response filtering ──


async def test_canonical_area_passes_with_evidence(client):
    client.set_reply(
        {
            "beliefs": [
                {
                    "belief": "со мной что-то не так",
                    "area": "self",
                    "evidence": ["я опять всё завалю (0)", "я опять всё завалю (1)"],
                }
            ],
            "summary": "Похоже, это повторяется.",
        }
    )
    resp = await client.beliefs(_req())
    assert len(resp.beliefs) == 1
    assert resp.beliefs[0].area == "self"
    assert len(resp.beliefs[0].evidence) == 2
    assert resp.summary == "Похоже, это повторяется."


async def test_drops_non_canonical_area(client):
    client.set_reply(
        {
            "beliefs": [
                {"belief": "x", "area": "самооценка", "evidence": []},
                {"belief": "y", "area": "others", "evidence": []},
            ],
            "summary": "s",
        }
    )
    resp = await client.beliefs(_req())
    assert [b.area for b in resp.beliefs] == ["others"]


async def test_caps_beliefs_at_three(client):
    client.set_reply(
        {
            "beliefs": [
                {"belief": f"b{i}", "area": "world", "evidence": []} for i in range(6)
            ],
            "summary": "s",
        }
    )
    resp = await client.beliefs(_req())
    assert len(resp.beliefs) == 3


async def test_caps_evidence_at_four(client):
    client.set_reply(
        {
            "beliefs": [
                {
                    "belief": "b",
                    "area": "self",
                    "evidence": [f"q{i}" for i in range(9)],
                }
            ],
            "summary": "s",
        }
    )
    resp = await client.beliefs(_req())
    assert len(resp.beliefs[0].evidence) == 4


async def test_empty_beliefs_with_summary_is_valid(client):
    # The honest "too few entries to see a pattern" answer — not an error.
    client.set_reply({"beliefs": [], "summary": "Записей пока мало, чтобы увидеть повтор."})
    resp = await client.beliefs(_req())
    assert resp.beliefs == []
    assert resp.summary


async def test_empty_beliefs_and_empty_summary_is_502(client):
    client.set_reply({"beliefs": [], "summary": "   "})
    with pytest.raises(HTTPException) as e:
        await client.beliefs(_req())
    assert e.value.status_code == 502


async def test_tolerates_garbage_shapes(client):
    client.set_reply({"beliefs": "broken", "summary": 42})
    with pytest.raises(HTTPException) as e:
        await client.beliefs(_req())
    assert e.value.status_code == 502


async def test_drops_blank_belief_text(client):
    client.set_reply(
        {
            "beliefs": [
                {"belief": "   ", "area": "self", "evidence": []},
                {"belief": "реальное", "area": "self", "evidence": []},
            ],
            "summary": "s",
        }
    )
    resp = await client.beliefs(_req())
    assert [b.belief for b in resp.beliefs] == ["реальное"]


# ── prompt shape ──


@pytest.mark.parametrize("language", ["ru", "en"])
def test_prompt_lists_every_area_key(language):
    prompt = build_beliefs_system_prompt(language)
    for key in BELIEF_AREAS:
        assert f"- {key}:" in prompt, key


@pytest.mark.parametrize("language", ["ru", "en"])
def test_prompt_forbids_clinical_framing(language):
    prompt = build_beliefs_system_prompt(language).lower()
    # The safety rules must actually be present — this feature names beliefs
    # about the person, so the no-diagnosis guard is load-bearing.
    needles = (
        ("диагноз", "гипотезы") if language == "ru" else ("diagnos", "hypotheses")
    )
    for needle in needles:
        assert needle in prompt, needle
