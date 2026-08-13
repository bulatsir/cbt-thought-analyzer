"""Контекст цепочки («техника стрелки») в /analyze.

Без него глубокое звено уезжает на разбор обрывком: модель не знает, что это
ответ на «и что с того?» к предыдущей мысли. Тесты сторожат две вещи —
что цепочка доезжает до промпта и что БЕЗ цепочки промпт не изменился.
"""

import pytest
from pydantic import ValidationError

from app.groq_client import GroqClient, _Reply
from app.prompts import build_user_prompt
from app.schemas import AnalyzeRequest


# ── промпт ──


def test_no_chain_keeps_prompt_unchanged():
    # Одиночная мысль должна получить ровно прежний промпт: любые слова про
    # цепочку в нём — это регрессия для 99% запросов.
    plain = build_user_prompt("всё пропало", "уволили", "паника")
    assert "цепочк" not in plain.lower()
    assert "техника стрелки" not in plain.lower()
    assert plain == build_user_prompt("всё пропало", "уволили", "паника", preceding=[])


def test_chain_is_listed_in_order():
    prompt = build_user_prompt(
        "значит я никому не нужен",
        preceding=["меня не позвали", "значит я не часть команды"],
    )
    assert '1. "меня не позвали"' in prompt
    assert '2. "значит я не часть команды"' in prompt
    # порядок именно такой: первое звено первым
    assert prompt.index("меня не позвали") < prompt.index("значит я не часть команды")


def test_chain_says_analyze_only_the_last_thought():
    # Главный риск: модель разберёт всю цепочку разом и вернёт метки
    # предыдущих звеньев для текущего.
    prompt = build_user_prompt("значит я никому не нужен", preceding=["меня не позвали"])
    assert "ТОЛЬКО" in prompt
    assert "И что с того?" in prompt


def test_chain_block_is_english_in_en_mode():
    prompt = build_user_prompt("so I'm worthless", preceding=["they didn't invite me"], language="en")
    assert "downward-arrow chain" in prompt
    assert "ONLY" in prompt
    assert "техника стрелки" not in prompt


def test_blank_links_are_dropped():
    prompt = build_user_prompt("x", preceding=["  ", "", "реальное звено"])
    assert '1. "реальное звено"' in prompt
    assert '2.' not in prompt


def test_all_blank_links_mean_no_chain():
    assert build_user_prompt("x", preceding=["  ", ""]) == build_user_prompt("x")


def test_chain_goes_before_context_blocks():
    # A и C относятся ко всей записи, цепочка — к этой конкретной мысли;
    # держим её ближе к мысли, чем общий контекст.
    prompt = build_user_prompt("x", situation="уволили", emotions="паника", preceding=["y"])
    assert prompt.index("Предыдущие звенья") < prompt.index("Контекст ситуации (A)")


# ── схема запроса ──


def test_preceding_defaults_to_empty():
    assert AnalyzeRequest(thought="x").preceding == []


def test_preceding_is_capped():
    with pytest.raises(ValidationError):
        AnalyzeRequest(thought="x", preceding=[f"link {i}" for i in range(9)])


def test_preceding_item_length_is_capped():
    with pytest.raises(ValidationError):
        AnalyzeRequest(thought="x", preceding=["a" * 2001])


# ── сквозняк через клиент ──


@pytest.fixture
def capturing_client(monkeypatch):
    """GroqClient, который не ходит в сеть, а запоминает промпты."""
    gc = GroqClient(api_key="test-key")
    seen: dict[str, str] = {}

    async def fake_call(system_prompt, user_prompt, max_tokens=512, schema=None, model=None):
        seen["system"] = system_prompt
        seen["user"] = user_prompt
        return _Reply({"distortions": []}, "test/model")

    monkeypatch.setattr(gc, "_call", fake_call)
    gc.seen = seen  # type: ignore[attr-defined]
    return gc


async def test_analyze_forwards_chain_to_prompt(capturing_client):
    await capturing_client.analyze(
        AnalyzeRequest(
            thought="значит я никому не нужен",
            preceding=["меня не позвали"],
            language="ru",
        )
    )
    assert '1. "меня не позвали"' in capturing_client.seen["user"]


async def test_analyze_without_chain_sends_no_chain_text(capturing_client):
    await capturing_client.analyze(AnalyzeRequest(thought="всё пропало", language="ru"))
    assert "цепочк" not in capturing_client.seen["user"].lower()
