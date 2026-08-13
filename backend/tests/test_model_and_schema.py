"""Выбор модели и переносимость json_schema между провайдерами."""

import pytest

from app.groq_client import ALLOWED_MODELS, MODEL, _resolve_model
from app.prompts import (
    BELIEF_AREAS,
    DISTORTIONS,
    DISTORTIONS_EN,
    build_analyze_schema,
    build_beliefs_schema,
)


# ── белый список моделей ──


def test_none_gives_default():
    assert _resolve_model(None) == MODEL


@pytest.mark.parametrize("model", ALLOWED_MODELS)
def test_allowed_model_passes_through(model):
    assert _resolve_model(model) == model


def test_unknown_model_falls_back_instead_of_erroring():
    # Тихий откат намеренный: клиент может быть старее или новее бэка, и разбор
    # мысли важнее точности выбора модели.
    assert _resolve_model("evil/free-model") == MODEL


def test_default_is_itself_allowed():
    assert MODEL in ALLOWED_MODELS


# ── схема: enum по каноническому списку ──


@pytest.mark.parametrize(
    "language,names", [("ru", DISTORTIONS), ("en", DISTORTIONS_EN)]
)
def test_analyze_schema_enum_matches_canonical_list(language, names):
    schema = build_analyze_schema(language)
    props = schema["schema"]["properties"]["distortions"]["items"]["properties"]
    assert props["name"]["enum"] == list(names)


def test_beliefs_schema_enum_matches_areas():
    schema = build_beliefs_schema()
    props = schema["schema"]["properties"]["beliefs"]["items"]["properties"]
    assert props["area"]["enum"] == list(BELIEF_AREAS)


# ── переносимость между провайдерами ──
#
# Anthropic отклоняет часть ключей JSON Schema, которые OpenAI принимает. Схема
# у нас одна на всех моделей из ALLOWED_MODELS, поэтому в ней должно остаться
# только пересечение. `maxItems` уже ловил 400 от Anthropic на живом запросе:
# «For 'array' type, property 'maxItems' is not supported». Отправь мы это в
# прод — /analyze отдавал бы 400 на каждый вызов.

_UNSUPPORTED_BY_ANTHROPIC = (
    "maxItems", "minItems", "uniqueItems",
    "minLength", "maxLength", "pattern",
    "minimum", "maximum", "multipleOf",
)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


@pytest.mark.parametrize(
    "schema",
    [build_analyze_schema("ru"), build_analyze_schema("en"), build_beliefs_schema()],
)
def test_schema_uses_only_portable_keywords(schema):
    for node in _walk(schema):
        for keyword in _UNSUPPORTED_BY_ANTHROPIC:
            assert keyword not in node, f"{keyword} ломает Anthropic — см. комментарий выше"


@pytest.mark.parametrize(
    "schema",
    [build_analyze_schema("ru"), build_beliefs_schema()],
)
def test_objects_are_closed_and_required(schema):
    # strict-режим требует additionalProperties=false и полный required
    # на каждом объекте; без этого провайдер отклоняет схему.
    assert schema["strict"] is True
    for node in _walk(schema["schema"]):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False
            assert set(node.get("required", [])) == set(node.get("properties", {}))
