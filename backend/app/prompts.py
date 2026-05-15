# Canonical Russian names — also the keys for storage / sorting / filters.
DISTORTIONS: tuple[str, ...] = (
    "Чёрно-белое мышление",
    "Сверхобобщение",
    "Ментальный фильтр",
    "Обесценивание положительного",
    "Поспешные выводы: чтение мыслей",
    "Поспешные выводы: предсказание будущего",
    "Катастрофизация",
    "Минимизация",
    "Эмоциональное обоснование",
    "Долженствование",
    "Навешивание ярлыков",
    "Персонализация",
    "Туннельное зрение",
    "Перфекционизм",
    "Сравнение",
    "Ошибка справедливости",
    "Ошибка контроля",
    "Обвинение",
)

# Parallel English names, same order as DISTORTIONS.
DISTORTIONS_EN: tuple[str, ...] = (
    "All-or-Nothing Thinking",
    "Overgeneralization",
    "Mental Filter",
    "Disqualifying the Positive",
    "Mind Reading",
    "Fortune Telling",
    "Catastrophizing",
    "Minimization",
    "Emotional Reasoning",
    "Should Statements",
    "Labeling",
    "Personalization",
    "Tunnel Vision",
    "Perfectionism",
    "Comparison",
    "Fairness Fallacy",
    "Control Fallacy",
    "Blame",
)


# ── Анализ когнитивных искажений ──


def build_system_prompt(language: str = "ru") -> str:
    if language == "en":
        listing = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(DISTORTIONS_EN))
        return f"""You are a CBT (cognitive-behavioral therapy) expert. Your task is to identify cognitive distortions in an automatic thought.

Here is the full list of cognitive distortions. Pick names ONLY from this list:
{listing}

Rules:
- Identify 0 to 3 distortions from the list above
- Use ONLY names from the list, verbatim — do not invent variations
- Both "name" and "explanation" must be in English
- If the thought contains no distortions, return an empty distortions array
- If the input is gibberish, random characters, test input like "asdf", "zzz", or otherwise meaningless — return an empty distortions array. DO NOT force distortions onto nonsense.
- Reply ONLY as JSON
- In the explanation do NOT use the words "patient", "client", or "user". Describe the thought itself and why the distortion applies. For example: "The thought exaggerates consequences..." instead of "The patient exaggerates...".

Response format:
{{
  "distortions": [
    {{ "name": "Name from the list above, verbatim", "explanation": "Brief explanation in English" }}
  ]
}}"""

    # default: ru
    listing = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(DISTORTIONS))
    return f"""Ты — опытный специалист в КПТ (когнитивно-поведенческая терапия). Твоя задача — определить когнитивные искажения в автоматической мысли.

Вот полный список когнитивных искажений. Выбирай ТОЛЬКО из этого списка:
{listing}

Правила:
- Определи от 0 до 3 искажений из списка выше
- Используй ТОЛЬКО названия из списка, не придумывай свои
- Если мысль не содержит искажений, верни пустой массив
- Если ввод бессмысленный, нечитаемый или не содержит мысли (набор букв, случайные символы, тестовый ввод вроде «asdf», «ыыы», «zzz» и т.п.) — верни пустой массив distortions. НЕ пытайся натянуть искажения на бессмыслицу.
- Отвечай ТОЛЬКО на русском языке
- Отвечай ТОЛЬКО в формате JSON
- В пояснении (explanation) НЕ используй слова «пациент», «клиент», «пользователь». Описывай саму мысль и почему искажение подходит. Например: «Мысль преувеличивает последствия...» вместо «Пациент преувеличивает...». Можно обращаться на «ты», но не присваивать ярлык «пациент».

Формат ответа:
{{
  "distortions": [
    {{ "name": "Название из списка", "explanation": "Краткое пояснение, почему это искажение" }}
  ]
}}"""


def build_user_prompt(
    thought: str,
    situation: str | None = None,
    emotions: str | None = None,
) -> str:
    prompt = f'Автоматическая мысль: "{thought}"'
    if situation and situation.strip():
        prompt += f"\n\nКонтекст ситуации (A): {situation.strip()}"
    if emotions and emotions.strip():
        prompt += f"\n\nЭмоции и последствия (C): {emotions.strip()}"
    return prompt
