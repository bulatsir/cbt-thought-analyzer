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


# ── Few-shot examples ──
#
# Negative examples teach restraint (return []); positive examples teach the
# explanation style (anchor to a phrase from the thought + name the cognitive
# operation of *that* distortion only). Distortion names are referenced by
# index into DISTORTIONS / DISTORTIONS_EN, so RU/EN names are canonical by
# construction and stay parallel. See
# docs/superpowers/specs/2026-05-16-llm-prompt-few-shot-design.md.

# (ru_input, en_input) — both must yield an empty distortions array.
_NEGATIVE_EXAMPLES: tuple[tuple[str, str], ...] = (
    ("усталость", "tired"),
    (
        "мне тревожно перед собеседованием",
        "I'm anxious before the interview",
    ),
    (
        "мало готовился, могу плохо сдать экзамен — сегодня позанимаюсь",
        "I didn't prepare much, I might do poorly on the exam — I'll study today",
    ),
    ("завтра встреча в три часа", "I have a meeting at three tomorrow"),
    ("asdf", "asdf"),
)

# (ru_input, en_input, ((idx, ru_explanation, en_explanation), ...))
# Multi-label examples give each distortion its OWN focused explanation —
# never the same string twice.
_POSITIVE_EXAMPLES: tuple[
    tuple[str, str, tuple[tuple[int, str, str], ...]], ...
] = (
    (
        "я завалил собеседование, меня теперь вообще никуда не возьмут",
        "I failed the interview, now nobody will ever hire me anywhere",
        (
            (
                1,
                "Слово «никуда» раздувает один отказ до бесконечного правила: одна неудача приравнена к «так будет всегда».",
                'The word "ever" inflates a single rejection into an endless rule: one failure is equated with "it will always be like this".',
            ),
            (
                5,
                "«Не возьмут» подаёт ещё не случившееся будущее как уже решённый факт.",
                '"Nobody will hire me" states an unhappened future as an already-settled fact.',
            ),
        ),
    ),
    (
        "он не поздоровался — наверное, считает меня никчёмным",
        "he didn't say hi — he probably thinks I'm worthless",
        (
            (
                4,
                "«Считает меня никчёмным» — приписывание чужих мыслей без проверки: молчание истолковано как доказательство негативного отношения.",
                '"He thinks I\'m worthless" attributes thoughts to someone else without checking: silence is read as proof of a negative attitude.',
            ),
        ),
    ),
    (
        "я полное ничтожество",
        "I'm a complete nobody",
        (
            (
                10,
                "«Полное ничтожество» — фиксированный ярлык на всю личность вместо описания конкретной ситуации; человек приравнивается к одной оценке.",
                '"A complete nobody" is a fixed label on the whole person instead of describing a specific situation; a person is equated with a single judgment.',
            ),
        ),
    ),
    (
        "если сделано не идеально — лучше вообще не делать",
        "if it's not done perfectly, better not do it at all",
        (
            (
                13,
                "Планка «идеально» задаёт недостижимый стандарт, при котором любой результат ниже совершенства не имеет ценности.",
                'The bar "perfectly" sets an unreachable standard under which any result short of flawless has no value.',
            ),
        ),
    ),
    (
        "либо всё получилось, либо это полный провал",
        "either everything worked out, or it's a total failure",
        (
            (
                0,
                "«Либо… либо… полный провал» — только две крайние корзины без промежуточных оценок; середина исключена.",
                '"Either... or... a total failure" allows only two extreme buckets with nothing in between; the middle ground is excluded.',
            ),
        ),
    ),
    (
        "мне сделали одно замечание, и теперь весь день испорчен",
        "I got one piece of criticism and now the whole day is ruined",
        (
            (
                2,
                "Одна деталь — «одно замечание» — заслоняет весь день: внимание застряло на единственном негативе, остальное не учитывается.",
                'One detail — "one piece of criticism" — overshadows the whole day: attention is stuck on a single negative while everything else is ignored.',
            ),
        ),
    ),
    (
        "в этой работе вообще нет ничего хорошего",
        "there's nothing good about this job at all",
        (
            (
                12,
                "«Вообще нет ничего хорошего» — обзор сужен до одной негативной стороны, любые плюсы заранее не попадают в поле зрения.",
                '"Nothing good at all" narrows the view to a single negative side; any positives never enter the field of view.',
            ),
        ),
    ),
    (
        "меня похвалили просто из вежливости, это не считается",
        "they praised me just out of politeness, it doesn't count",
        (
            (
                3,
                "«Это не считается» активно аннулирует реальную похвалу, объясняя её вежливостью, — положительное переводится в ноль.",
                '"It doesn\'t count" actively nullifies real praise by explaining it away as politeness — the positive is reduced to zero.',
            ),
        ),
    ),
    (
        "да, я пробежал марафон, но это ерунда, любой может",
        "yeah I ran a marathon, but it's no big deal, anyone could",
        (
            (
                7,
                "Достижение признаётся, но «ерунда, любой может» сжимает его до незначительного — масштаб собственного результата занижен.",
                'The achievement is acknowledged, but "no big deal, anyone could" shrinks it to trivial — the scale of one\'s own result is downplayed.',
            ),
        ),
    ),
    (
        "мне страшно — значит, точно случится что-то плохое",
        "I'm scared — so something bad is definitely going to happen",
        (
            (
                8,
                "Связка «страшно — значит случится» выводит факт из чувства: эмоция принимается за доказательство реальности.",
                'The link "scared, so it will happen" derives a fact from a feeling: emotion is taken as proof of reality.',
            ),
        ),
    ),
    (
        "если я ошибусь на работе — меня уволят и всё рухнет",
        "if I make a mistake at work, I'll get fired and everything will collapse",
        (
            (
                6,
                "«Всё рухнет» разгоняет возможную ошибку до предельной катастрофы — худший исход подаётся как масштаб всей жизни.",
                '"Everything will collapse" escalates a possible mistake into an ultimate catastrophe — the worst case is presented as the scale of one\'s whole life.',
            ),
            (
                5,
                "Цепочка «ошибусь → уволят» подаётся как неизбежный прогноз, а не как одна из возможностей.",
                'The chain "make a mistake → get fired" is presented as an inevitable prediction rather than one of several possibilities.',
            ),
        ),
    ),
    (
        "я никогда не должен ошибаться",
        "I must never make mistakes",
        (
            (
                9,
                "«Никогда не должен» — жёсткое абсолютное требование к себе вместо гибкого предпочтения; ошибка превращается из обычного события в недопустимое нарушение правила.",
                '"Must never" is a rigid absolute demand on oneself instead of a flexible preference; a mistake turns from an ordinary event into an inadmissible rule violation.',
            ),
        ),
    ),
    (
        "команда сорвала срок — это всё из-за меня",
        "the team missed the deadline — it's all because of me",
        (
            (
                11,
                "«Всё из-за меня» берёт единоличную вину за общий результат, который зависел не только от одного человека.",
                '"All because of me" takes sole blame for a shared outcome that did not depend on one person alone.',
            ),
        ),
    ),
    (
        "все ровесники добились большего, я на их фоне пустое место",
        "all my peers have achieved more, next to them I'm a nobody",
        (
            (
                14,
                "Мерило «на их фоне» оценивает собственную ценность через сравнение с другими.",
                'The yardstick "next to them" judges one\'s own worth through comparison with others.',
            ),
            (
                10,
                "«Пустое место» закрепляет это фиксированным ярлыком на всю личность.",
                '"A nobody" locks that in as a fixed label on the whole person.',
            ),
        ),
    ),
    (
        "это несправедливо: я работаю больше всех, а повысили другого",
        "it's not fair: I work harder than everyone, and someone else got promoted",
        (
            (
                15,
                "«Несправедливо» применяет личный эталон справедливости как объективное мерило мира — ситуация судится по правилу «мир обязан быть честным ко мне».",
                '"Not fair" applies a personal standard of fairness as an objective measure of the world — the situation is judged by the rule "the world owes me fairness".',
            ),
        ),
    ),
    (
        "от меня всё равно ничего не зависит, всё решают другие",
        "nothing depends on me anyway, others decide everything",
        (
            (
                16,
                "«Ничего не зависит, всё решают другие» — позиция полной внешней управляемости, отрицающая собственное влияние.",
                '"Nothing depends on me, others decide everything" is a stance of total external control that denies any influence of one\'s own.',
            ),
        ),
    ),
    (
        "я несчастен только из-за них — это они во всём виноваты",
        "I'm unhappy only because of them — it's all their fault",
        (
            (
                17,
                "«Только из-за них», «они во всём виноваты» — ответственность за своё состояние целиком вынесена на других.",
                '"Only because of them", "all their fault" — responsibility for one\'s own state is placed entirely on others.',
            ),
        ),
    ),
)


def _render_examples(language: str) -> str:
    """Render the few-shot block. Positive examples first, negative examples
    last (closest to the live input) so the most recent demonstrations before
    real input include the "return empty" behaviour."""
    names = DISTORTIONS_EN if language == "en" else DISTORTIONS
    in_label = "Input" if language == "en" else "Ввод"
    out_label = "Answer" if language == "en" else "Ответ"
    lines: list[str] = []

    for ru_in, en_in, parts in _POSITIVE_EXAMPLES:
        text = en_in if language == "en" else ru_in
        items = ", ".join(
            '{"name": "%s", "explanation": "%s"}'
            % (names[i], en_exp if language == "en" else ru_exp)
            for i, ru_exp, en_exp in parts
        )
        lines.append(f'{in_label}: "{text}"')
        lines.append(f'{out_label}: {{"distortions": [{items}]}}')

    for ru_in, en_in in _NEGATIVE_EXAMPLES:
        text = en_in if language == "en" else ru_in
        lines.append(f'{in_label}: "{text}"')
        lines.append(f'{out_label}: {{"distortions": []}}')

    return "\n".join(lines)


# ── Анализ когнитивных искажений ──


def build_system_prompt(language: str = "ru") -> str:
    if language == "en":
        listing = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(DISTORTIONS_EN))
        examples = _render_examples("en")
        return f"""You are a CBT (cognitive-behavioral therapy) expert. Your task is to identify cognitive distortions in an automatic thought.

Here is the full list of cognitive distortions. Pick names ONLY from this list:
{listing}

Rules:
- Identify 0 to 3 distortions from the list above
- Use ONLY names from the list, verbatim — do not invent variations
- Both "name" and "explanation" must be in English
- A cognitive distortion can exist only inside an automatic thought — a judgment, appraisal, interpretation or prediction about yourself, other people, or the future. If the input is NOT such a thought, return an empty distortions array. Do not force a distortion onto a non-thought. A non-thought is:
  - a single word or a short state label ("tired", "work", "anxiety");
  - naming an emotion with no appraisal ("I feel sad", "I'm anxious before the interview");
  - a neutral statement of fact or a plan ("I have a meeting at three", "it's raining");
  - a proportionate, reality-based concern or a coping plan ("I didn't prepare much, I might do poorly — I'll study today") — a realistic, balanced thought is not a distortion;
  - a question with no embedded belief ("what should I cook for dinner?");
  - a preference or taste ("I like coffee");
  - gibberish or test input ("asdf", "test test").
  Key separator: a distortion lives in an appraisal, not in a fact or an emotion. "I didn't eat" → empty; "I didn't eat because I'm a worthless nobody who doesn't deserve care" → has a distortion.
- In the explanation, anchor to a concrete phrasing from the thought — quote it (close paraphrase is fine, an exact substring is not required) and explain why that phrasing makes the thought this distortion. Describe the cognitive operation of THIS distortion only: do not describe the resulting emotion ("...and that's why it feels unfair") and do not restate another distortion's mechanism. 1–2 sentences, plain language.
- If the thought contains no distortions, return an empty distortions array
- Reply ONLY as JSON
- In the explanation do NOT use the words "patient", "client", or "user".

Examples (study them and follow the same style; the response format is strictly the JSON shown below):
{examples}

Response format:
{{"distortions": [{{"name": "Name from the list above, verbatim", "explanation": "Brief explanation in English"}}]}}"""

    # default: ru
    listing = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(DISTORTIONS))
    examples = _render_examples("ru")
    return f"""Ты — опытный специалист в КПТ (когнитивно-поведенческая терапия). Твоя задача — определить когнитивные искажения в автоматической мысли.

Вот полный список когнитивных искажений. Выбирай ТОЛЬКО из этого списка:
{listing}

Правила:
- Определи от 0 до 3 искажений из списка выше
- Используй ТОЛЬКО названия из списка, не придумывай свои
- Когнитивное искажение может существовать только внутри автоматической мысли — суждения, оценки, интерпретации или прогноза о себе, других людях или будущем. Если ввод не является такой мыслью — верни пустой массив distortions. Не натягивай искажение на не-мысль. Не-мысль это:
  - одно слово или короткая пометка состояния/темы («усталость», «работа», «тревога»);
  - называние эмоции без оценки («мне грустно», «мне тревожно перед собеседованием»);
  - нейтральная констатация факта или плана («завтра встреча в три», «идёт дождь», «я не поел»);
  - соразмерное реальности беспокойство или план действий («мало готовился, могу плохо сдать — сегодня позанимаюсь») — реалистичная, взвешенная мысль не является искажением;
  - вопрос без заложенного убеждения («что приготовить на ужин?»);
  - предпочтение или вкус («я люблю кофе»);
  - бессмыслица или тестовый ввод («asdf», «ыыы», «test test»).
  Ключевой разделитель: искажение живёт в оценке, а не в факте или эмоции. «я не поел» → пусто; «я не поел, потому что я ничтожество, не заслуживающее заботы» → есть искажение.
- В пояснении (explanation) опирайся на конкретную формулировку из мысли — приведи её (можно близко к тексту, дословность не требуется) и объясни, почему именно она делает мысль этим искажением. Объясняй когнитивную операцию ИМЕННО этого искажения: не описывай эмоцию-следствие («…и поэтому обидно/виновато») и не пересказывай механику другого искажения. 1–2 предложения, живым языком.
- Если мысль не содержит искажений, верни пустой массив
- Отвечай ТОЛЬКО на русском языке
- Отвечай ТОЛЬКО в формате JSON
- В пояснении (explanation) НЕ используй слова «пациент», «клиент», «пользователь». Можно обращаться на «ты», но не присваивать ярлык «пациент».

Примеры (изучи их и следуй такому же стилю; формат ответа — строго JSON как ниже):
{examples}

Формат ответа:
{{"distortions": [{{"name": "Название из списка", "explanation": "Краткое пояснение, почему это искажение"}}]}}"""


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
