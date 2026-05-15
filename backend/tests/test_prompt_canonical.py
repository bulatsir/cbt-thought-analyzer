"""B3 delivery-gate: every distortion name embedded in the few-shot block of
the rendered system prompt must belong to the canonical tuple for that
language. A mistranslated EN name would be silently dropped to empty by the
canonical filter in groq_client (WARN only) — this catches it before build."""

import re

from app.prompts import (
    DISTORTIONS,
    DISTORTIONS_EN,
    build_system_prompt,
)

_NAME_RE = re.compile(r'\{"name": "(?P<name>[^"]+)", "explanation":')

# Markers bounding the few-shot block (exclude the response-format template,
# which carries a placeholder "name").
_BOUNDS = {
    "ru": ("Примеры (изучи", "\n\nФормат ответа:"),
    "en": ("Examples (study", "\n\nResponse format:"),
}


def _few_shot_block(language: str) -> str:
    prompt = build_system_prompt(language)
    start, end = _BOUNDS[language]
    return prompt.split(start, 1)[1].split(end, 1)[0]


def _names_in_prompt(language: str) -> list[str]:
    return _NAME_RE.findall(_few_shot_block(language))


def test_ru_few_shot_names_are_canonical():
    names = _names_in_prompt("ru")
    assert names, "no example names found in RU prompt"
    canonical = set(DISTORTIONS)
    assert all(n in canonical for n in names), [
        n for n in names if n not in canonical
    ]


def test_en_few_shot_names_are_canonical():
    names = _names_in_prompt("en")
    assert names, "no example names found in EN prompt"
    canonical = set(DISTORTIONS_EN)
    assert all(n in canonical for n in names), [
        n for n in names if n not in canonical
    ]


def test_every_distortion_is_demonstrated_once():
    # Coverage guard: each of the 18 distortions appears in at least one
    # positive example, in both languages.
    assert set(_names_in_prompt("ru")) == set(DISTORTIONS)
    assert set(_names_in_prompt("en")) == set(DISTORTIONS_EN)


def test_negative_examples_present_and_empty():
    # The five negative inputs must appear with an empty distortions array.
    ru = build_system_prompt("ru")
    assert ru.count('{"distortions": []}') == 5
    assert 'Ввод: "усталость"' in ru
    en = build_system_prompt("en")
    assert en.count('{"distortions": []}') == 5
    assert 'Input: "tired"' in en


def test_no_clinical_words_in_examples():
    # The "no patient/client" rule must not be contradicted by our own
    # example explanations.
    ru = build_system_prompt("ru").lower()
    # Words allowed in the *rule* sentence; assert they don't leak into
    # explanation text by checking the example block specifically.
    block = ru.split("примеры (изучи")[1]
    for bad in ("пациент", "клиент", "пользовател"):
        assert bad not in block, bad
