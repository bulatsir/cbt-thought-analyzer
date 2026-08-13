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
#
# Explanation shape (v2, 2026-08-09): each explanation must name what the
# thought *treats as evidence* and what it *leaves unchecked* — never restate
# the distortion's definition. Restating ("приписывание чужих мыслей без
# проверки") reads as an explanation but carries no information about this
# particular thought, and 13 of 15 👎 verdicts in the first 2.5 months of real
# use were exactly that. Test for a bad explanation: delete the quote — if what
# remains fits any other thought with the same label, rewrite it.
_POSITIVE_EXAMPLES: tuple[
    tuple[str, str, tuple[tuple[int, str, str], ...]], ...
] = (
    (
        "я завалил собеседование, меня теперь вообще никуда не возьмут",
        "I failed the interview, now nobody will ever hire me anywhere",
        (
            (
                1,
                "Одно собеседование взято как выборка, по которой уже можно судить обо всех остальных: «никуда» охватывает и тех работодателей, с которыми разговора ещё не было.",
                'A single interview is treated as a sample big enough to judge all the others: "anywhere" covers employers there has not even been a conversation with yet.',
            ),
            (
                5,
                "«Не возьмут» — прогноз, у которого единственное основание — один уже прошедший отказ; ни одного ответа на будущие отклики ещё не приходило.",
                '"Nobody will hire me" is a forecast whose only basis is one rejection that already happened; no answer to any future application has come in yet.',
            ),
        ),
    ),
    (
        "он не поздоровался — наверное, считает меня никчёмным",
        "he didn't say hi — he probably thinks I'm worthless",
        (
            (
                4,
                "Всё основание здесь — что человек не поздоровался; из этого достраивается конкретная формулировка у него в голове, хотя спешка или невнимательность объясняют молчание не хуже.",
                'The whole basis here is that he didn\'t say hi; from that, a specific verdict inside his head is reconstructed — though being in a hurry or simply not noticing explains the silence just as well.',
            ),
        ),
    ),
    (
        "я полное ничтожество",
        "I'm a complete nobody",
        (
            (
                10,
                "«Полное ничтожество» подводит итог человеку целиком, не называя ни одного конкретного поступка, к которому этот итог можно было бы отнести и проверить.",
                '"A complete nobody" sums up the whole person without naming a single concrete action the verdict could be attached to and checked against.',
            ),
        ),
    ),
    (
        "если сделано не идеально — лучше вообще не делать",
        "if it's not done perfectly, better not do it at all",
        (
            (
                13,
                "Ценность работы измеряется единственной отметкой «идеально», а промежуточный исход — сделать частично, сделать неплохо — заранее выведен из списка вариантов.",
                'The work\'s worth is measured against the single mark "perfectly", while the in-between outcome — doing part of it, doing it decently — is removed from the list of options in advance.',
            ),
        ),
    ),
    (
        "либо всё получилось, либо это полный провал",
        "either everything worked out, or it's a total failure",
        (
            (
                0,
                "Между «всё получилось» и «полный провал» не оставлено места исходу «часть вышла, часть нет», хотя именно туда попадает большинство результатов.",
                'Between "everything worked out" and "a total failure" no room is left for "some of it worked, some didn\'t" — which is where most results actually land.',
            ),
        ),
    ),
    (
        "мне сделали одно замечание, и теперь весь день испорчен",
        "I got one piece of criticism and now the whole day is ruined",
        (
            (
                2,
                "Оценка целого дня построена на одном замечании; всё остальное, что за этот день происходило, в подсчёт просто не попало.",
                'The verdict on an entire day rests on one piece of criticism; everything else that happened that day never entered the count.',
            ),
        ),
    ),
    (
        "в этой работе вообще нет ничего хорошего",
        "there's nothing good about this job at all",
        (
            (
                12,
                "«Вообще ничего» — вывод обо всей работе, при котором не названо ни одной её стороны, кроме той, что сейчас в фокусе.",
                '"Nothing at all" is a verdict on the entire job that names not one of its sides except the one currently in focus.',
            ),
        ),
    ),
    (
        "меня похвалили просто из вежливости, это не считается",
        "they praised me just out of politeness, it doesn't count",
        (
            (
                3,
                "Похвала объясняется вежливостью — догадкой о чужом мотиве, которую никто не проверял, и именно эта догадка позволяет вычесть похвалу из результата.",
                'The praise is explained away as politeness — a guess about someone else\'s motive that nobody verified, and it is that guess which lets the praise be subtracted from the result.',
            ),
        ),
    ),
    (
        "да, я пробежал марафон, но это ерунда, любой может",
        "yeah I ran a marathon, but it's no big deal, anyone could",
        (
            (
                7,
                "«Любой может» — допущение, а не наблюдение: оно не опирается ни на какие сведения о других людях, но именно им обнуляется собственный результат.",
                '"Anyone could" is an assumption, not an observation: it rests on no information about other people, yet it is what reduces one\'s own result to nothing.',
            ),
        ),
    ),
    (
        "мне страшно — значит, точно случится что-то плохое",
        "I'm scared — so something bad is definitely going to happen",
        (
            (
                8,
                "Единственный довод в пользу «случится» — собственный страх; никакого внешнего признака, что событие приближается, в мысли не названо.",
                'The only argument for "it will happen" is one\'s own fear; the thought names no external sign that the event is actually approaching.',
            ),
        ),
    ),
    (
        "если я ошибусь на работе — меня уволят и всё рухнет",
        "if I make a mistake at work, I'll get fired and everything will collapse",
        (
            (
                6,
                "Цепочка обрывается на худшем звене — «всё рухнет», — минуя всё, что обычно стоит между ошибкой и крахом: возможность заметить, исправить, договориться, найти другое место.",
                'The chain stops at its worst link — "everything will collapse" — skipping everything that normally sits between a mistake and ruin: noticing it, fixing it, talking it through, finding another job.',
            ),
            (
                5,
                "«Ошибусь → уволят» подан как единственный ход событий, хотя за рабочей ошибкой обычно следует разговор или правка, и как решат в этот раз — пока неизвестно.",
                '"Make a mistake → get fired" is presented as the only way events can run, though a work mistake is usually followed by a conversation or a correction — and what will be decided this time is not yet known.',
            ),
        ),
    ),
    (
        "я никогда не должен ошибаться",
        "I must never make mistakes",
        (
            (
                9,
                "«Никогда не должен» — правило без исключений и без автора: не сказано, кем оно установлено и что происходит при нарушении, а нарушено оно будет обязательно.",
                '"Must never" is a rule with no exceptions and no author: it is not said who set it or what happens when it is broken — and broken it certainly will be.',
            ),
        ),
    ),
    (
        "команда сорвала срок — это всё из-за меня",
        "the team missed the deadline — it's all because of me",
        (
            (
                11,
                "Из всего, что влияло на срок — объём работы, состав команды, внешние задержки, — в объяснении оставлен один человек, и вся причина сведена к нему.",
                'Of everything that affected the deadline — the scope, the team, outside delays — the explanation keeps one person, and the entire cause is reduced to them.',
            ),
        ),
    ),
    (
        "все ровесники добились большего, я на их фоне пустое место",
        "all my peers have achieved more, next to them I'm a nobody",
        (
            (
                14,
                "«Все ровесники» — обобщение по той части чужих жизней, которая видна снаружи; собственная ценность выводится из этого сопоставления, а не из чего-либо своего.",
                '"All my peers" generalizes from the part of other people\'s lives that is visible from outside; one\'s own worth is derived from that comparison rather than from anything of one\'s own.',
            ),
            (
                10,
                "«Пустое место» переводит исход сравнения в постоянное свойство себя: уже не «отстаю вот в этом», а «являюсь этим».",
                '"A nobody" converts the outcome of a comparison into a permanent property of oneself: no longer "I\'m behind in this particular thing" but "this is what I am".',
            ),
        ),
    ),
    (
        "это несправедливо: я работаю больше всех, а повысили другого",
        "it's not fair: I work harder than everyone, and someone else got promoted",
        (
            (
                15,
                "Решение меряется одной меркой — кто больше работал, — как будто она единственная и общая для всех; по каким критериям решали на самом деле, в мысли не сказано.",
                'The decision is measured by a single yardstick — who worked hardest — as though it were the only one and shared by everyone; what criteria were actually used is not stated anywhere in the thought.',
            ),
        ),
    ),
    (
        "от меня всё равно ничего не зависит, всё решают другие",
        "nothing depends on me anyway, others decide everything",
        (
            (
                16,
                "«Ничего не зависит» — вывод обо всём сразу; ни одного конкретного места, где выбор всё-таки оставался, мысль не рассматривает.",
                '"Nothing depends on me" is a verdict on everything at once; the thought examines not one specific place where a choice did in fact remain.',
            ),
        ),
    ),
    (
        "я несчастен только из-за них — это они во всём виноваты",
        "I'm unhappy only because of them — it's all their fault",
        (
            (
                17,
                "Слово «только» закрывает вопрос: всё, что человек делал или мог сделать сам, вынесено за скобки, и причина остаётся ровно одна.",
                'The word "only" closes the question: everything the person did or could have done is set aside, and exactly one cause is left standing.',
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
- In the explanation, anchor to a concrete phrasing from the thought — quote it (close paraphrase is fine, an exact substring is not required). The explanation must add something the thought does not already say: name what the thought treats as evidence (a specific fact, word, or detail) and what it leaves out — what stayed unchecked, or which other explanation fits just as well.
- Do NOT restate the distortion's definition instead of analysing the thought. "Attributing thoughts to someone without checking", "states the future as a settled fact", "a fixed label on the whole person" are names of mechanisms, not explanations: they say nothing new about this particular thought. Test yourself: delete the quote from your explanation — if what remains would fit any other thought carrying the same label, rewrite it.
- Do not invent circumstances that are not in the input. Rely only on the thought's text and the provided A and C context.
- Describe the cognitive operation of THIS distortion only: do not describe the resulting emotion ("...and that's why it feels unfair") and do not restate another distortion's mechanism. With several distortions, each gets its own explanation about its own part of the thought.
- 1–2 sentences, plain language.
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
- В пояснении (explanation) опирайся на конкретную формулировку из мысли — приведи её (можно близко к тексту, дословность не требуется). Пояснение обязано добавлять то, чего в самой мысли нет: назови, что мысль принимает за доказательство (конкретный факт, слово, деталь), и чего она при этом не учитывает — что осталось непроверенным или какое объяснение подходит не хуже.
- НЕ пересказывай определение искажения вместо разбора мысли. «Приписывание чужих мыслей без проверки», «подаёт будущее как решённый факт», «фиксированный ярлык на всю личность» — это названия механизмов, а не пояснения: о конкретной мысли они не сообщают ничего нового. Проверь себя: убери из пояснения цитату — если оставшееся подойдёт к любой другой мысли с тем же искажением, перепиши.
- Не придумывай обстоятельств, которых нет во вводе. Опирайся только на текст мысли и переданный контекст A и C.
- Объясняй когнитивную операцию ИМЕННО этого искажения: не описывай эмоцию-следствие («…и поэтому обидно/виновато») и не пересказывай механику другого искажения. Если искажений несколько, у каждого своё пояснение про свою часть мысли.
- 1–2 предложения, живым языком.
- Если мысль не содержит искажений, верни пустой массив
- Отвечай ТОЛЬКО на русском языке
- Отвечай ТОЛЬКО в формате JSON
- В пояснении (explanation) НЕ используй слова «пациент», «клиент», «пользователь». Можно обращаться на «ты», но не присваивать ярлык «пациент».

Примеры (изучи их и следуй такому же стилю; формат ответа — строго JSON как ниже):
{examples}

Формат ответа:
{{"distortions": [{{"name": "Название из списка", "explanation": "Краткое пояснение, почему это искажение"}}]}}"""


def build_analyze_schema(language: str = "ru") -> dict:
    """json_schema для /analyze: имя искажения — enum по каноническому списку.

    Зачем: без схемы имя держится только просьбой в промпте, и дрейф ловится
    постфактум фильтром в `groq_client.analyze()` — то есть молча выбрасывается,
    и пользователь видит «искажений не найдено» вместо сбоя. С enum чужое имя
    вернуть просто нельзя. Особенно важно при смене модели: дрейф появляется
    именно там.

    ВНИМАНИЕ, переносимость: набор ключей JSON Schema у провайдеров разный.
    `maxItems` здесь нет намеренно — Anthropic отклоняет его четырёхсоткой
    («For 'array' type, property 'maxItems' is not supported»), а OpenAI
    принимает. Всё, что тут остаётся, проверено на обоих. Лимит в 3 искажения
    держат промпт и срез `raw[:3]` в клиенте, схема за него не отвечает.
    """
    names = DISTORTIONS_EN if language == "en" else DISTORTIONS
    return {
        "name": "distortions",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["distortions"],
            "properties": {
                "distortions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "explanation"],
                        "properties": {
                            "name": {"type": "string", "enum": list(names)},
                            "explanation": {"type": "string"},
                        },
                    },
                }
            },
        },
    }


def build_beliefs_schema() -> dict:
    """json_schema для /beliefs: area — enum по BELIEF_AREAS.

    Те же ограничения переносимости, что и у `build_analyze_schema`.
    """
    return {
        "name": "beliefs",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["beliefs", "summary"],
            "properties": {
                "beliefs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["belief", "area", "evidence"],
                        "properties": {
                            "belief": {"type": "string"},
                            "area": {"type": "string", "enum": list(BELIEF_AREAS)},
                            "evidence": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "summary": {"type": "string"},
            },
        },
    }


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


# ── Подсказка голоса и тем для момента (вкладка «Голоса», iOS) ──
#
# Темы — те же 4 эмоциональные темы, что и у мыслей (rawValue из iOS-enum
# ThoughtTheme). Модель отвечает КЛЮЧАМИ, не локализованными названиями —
# клиент декодит их напрямую.

THEME_KEYS: tuple[str, ...] = ("selfCriticism", "threat", "loss", "injustice")

_THEME_DESCRIPTIONS_RU: dict[str, str] = {
    "selfCriticism": "самокритика — «я плохой / ничтожество» (стыд, вина)",
    "threat": "угроза — «случится плохое» (тревога, страх)",
    "loss": "потеря — «всё кончено / безнадёжно» (грусть, апатия)",
    "injustice": "несправедливость — «так нельзя, он не должен» (злость, обида)",
}

_THEME_DESCRIPTIONS_EN: dict[str, str] = {
    "selfCriticism": "self-criticism — \"I'm bad / worthless\" (shame, guilt)",
    "threat": "threat — \"something bad will happen\" (anxiety, fear)",
    "loss": "loss — \"it's over / hopeless\" (sadness, apathy)",
    "injustice": "injustice — \"this is wrong, they shouldn't\" (anger, resentment)",
}


def _theme_listing(language: str) -> str:
    desc = _THEME_DESCRIPTIONS_EN if language == "en" else _THEME_DESCRIPTIONS_RU
    return "\n".join(f"- {k}: {desc[k]}" for k in THEME_KEYS)


def build_suggest_system_prompt(voice_names: list[str], language: str = "ru") -> str:
    themes = _theme_listing(language)
    if language == "en":
        roster = (
            "\n".join(f"- {n}" for n in voice_names)
            if voice_names
            else "(the roster is empty)"
        )
        return f"""You help with a self-compassion practice. The person keeps a roster of named "inner voices" (externalized inner critics) and jots down brief moments of distress as free text. Your task: read one moment and suggest which voice is speaking and which emotional themes are present.

Inner voice roster (suggest a name ONLY from this list, verbatim):
{roster}

Emotional themes (use ONLY these keys in "themes"):
{themes}

Rules:
- "voice_name": exactly one name from the roster, or null if no voice clearly fits, the text is too vague, or the roster is empty. When unsure — null. Never invent a name.
- "themes": 0 to 2 theme KEYS (e.g. "threat"), only when clearly present. Empty array is a normal answer.
- The text may be raw, fragmented, emotional — that's expected. Gibberish or empty meaning → null and [].
- Reply ONLY as JSON.

Response format:
{{"voice_name": "name from roster or null", "themes": ["key"]}}"""

    roster = (
        "\n".join(f"- {n}" for n in voice_names)
        if voice_names
        else "(ростер пуст)"
    )
    return f"""Ты помогаешь в практике самосострадания. Человек ведёт ростер именованных «внутренних голосов» (экстернализованные внутренние критики) и записывает короткие моменты дистресса свободным текстом. Твоя задача: прочитать один момент и предположить, какой голос звучит и какие эмоциональные темы присутствуют.

Ростер внутренних голосов (предлагай имя ТОЛЬКО из этого списка, дословно):
{roster}

Эмоциональные темы (в "themes" используй ТОЛЬКО эти ключи):
{themes}

Правила:
- "voice_name": ровно одно имя из ростера, либо null — если ни один голос явно не подходит, текст слишком расплывчатый или ростер пуст. Сомневаешься — null. Никогда не выдумывай имя.
- "themes": от 0 до 2 КЛЮЧЕЙ тем (например "threat"), только если тема явно присутствует. Пустой массив — нормальный ответ.
- Текст может быть сырым, обрывочным, эмоциональным — это ожидаемо. Бессмыслица или пустой смысл → null и [].
- Отвечай ТОЛЬКО в формате JSON.

Формат ответа:
{{"voice_name": "имя из ростера или null", "themes": ["ключ"]}}"""


def build_suggest_user_prompt(text: str) -> str:
    return f'Запись момента: "{text.strip()}"'


# ── Обзор недели (синтез паттернов по моментам) ──


def build_review_system_prompt(language: str = "ru") -> str:
    if language == "en":
        return """You help with a self-compassion practice. The person has been jotting down brief moments of distress (free text, sometimes with a named "inner voice" and emotional themes attached). You receive their recent moments and write a short, warm review of patterns.

Rules:
- Note which voices and themes recur, and in what situations or times they tend to show up. Ground every observation in the actual entries — do not invent patterns.
- Tone: warm, even, side-by-side — like a kind friend reflecting back what they noticed. Address the person as "you".
- End with ONE gentle observation or question to sit with. Not advice, not homework.
- Do NOT: diagnose, suggest therapy or treatment, evaluate the person, praise or scold, use clinical jargon, use the words "patient"/"client"/"user".
- If there are too few entries to see a pattern, say so honestly and warmly instead of forcing one.
- Length: 120–200 words, plain text (no markdown headings or lists).
- Reply ONLY as JSON.

Response format:
{"review": "the review text"}"""

    return """Ты помогаешь в практике самосострадания. Человек записывает короткие моменты дистресса (свободный текст, иногда с именованным «внутренним голосом» и эмоциональными темами). Ты получаешь его недавние записи и пишешь короткий тёплый обзор паттернов.

Правила:
- Отметь, какие голоса и темы повторяются и в каких ситуациях или в какое время они обычно всплывают. Каждое наблюдение опирай на реальные записи — не выдумывай паттерны.
- Тон: тёплый, ровный, «рядом, а не сверху» — как добрый друг, который отражает то, что заметил. Обращайся на «ты».
- Закончи ОДНИМ мягким наблюдением или вопросом, с которым можно побыть. Не советом, не домашним заданием.
- НЕЛЬЗЯ: ставить диагнозы, советовать терапию или лечение, оценивать человека, хвалить или ругать, использовать клинический жаргон, использовать слова «пациент», «клиент», «пользователь».
- Если записей слишком мало, чтобы увидеть паттерн, — честно и тепло скажи об этом, не натягивай.
- Объём: 120–200 слов, простой текст (без markdown-заголовков и списков).
- Отвечай ТОЛЬКО на русском языке и ТОЛЬКО в формате JSON.

Формат ответа:
{"review": "текст обзора"}"""


# ── Глубинные убеждения (синтез по сохранённым разборам) ──
#
# Слой под автоматическими мыслями: общие безусловные представления, из
# которых мысли вырастают. Клиент открывает это по кнопке в «Сохранено» и
# только когда записей достаточно (>= 10) — на трёх записях паттерна нет, а
# натянутая гипотеза о себе вредна. Тот же гейт продублирован в схеме.
#
# Области — ключи, не локализованные названия (как THEME_KEYS): клиент
# рендерит их сам.

BELIEF_AREAS: tuple[str, ...] = ("self", "others", "world")

_AREA_DESCRIPTIONS_RU: dict[str, str] = {
    "self": "о себе — какой я",
    "others": "о других людях — чего от них ждать",
    "world": "о мире и жизни в целом — как всё устроено",
}

_AREA_DESCRIPTIONS_EN: dict[str, str] = {
    "self": "about yourself — what you are like",
    "others": "about other people — what to expect from them",
    "world": "about the world and life in general — how things work",
}


def _area_listing(language: str) -> str:
    desc = _AREA_DESCRIPTIONS_EN if language == "en" else _AREA_DESCRIPTIONS_RU
    return "\n".join(f"- {k}: {desc[k]}" for k in BELIEF_AREAS)


def build_beliefs_system_prompt(language: str = "ru") -> str:
    areas = _area_listing(language)
    if language == "en":
        return f"""You help someone with their CBT practice. You are given their saved automatic-thought analyses from some period of time. Your task: suggest which core beliefs might sit underneath those thoughts.

What a core belief is: a general, unconditional idea about oneself, about other people, or about the world — usually never said out loud, but the soil the specific automatic thoughts grow from. "They'll tear my work apart in the meeting" and "he thought I was an idiot" can both grow from one "something is wrong with me, and it shows".

Three areas (in the "area" field use ONLY these keys):
{areas}

Rules:
- Offer 1 to 3 beliefs. Fewer is better than forced.
- Word each belief in the first person, as a short phrase, in the person's own vocabulary where possible — the way they might say it if they said it out loud.
- Ground every belief in "evidence": 2 to 4 quotes from their own entries, verbatim. Never invent a quote — use only what is in the input.
- Keep each quote short — 15 words at most. If the fragment runs longer, take its core and mark the omission with an ellipsis, leaving the wording untouched.
- These are hypotheses, not a diagnosis. Keep the tentative mood in the wording and in the summary: "it sounds like", "this comes up often", "maybe". Never "you have the belief that", "your problem is".
- Do NOT: diagnose, name disorders, recommend therapy or treatment, judge the person, praise or scold, or explain the origin through childhood and parents unless they wrote about it themselves.
- Do not use the words "patient", "client", or "user". Address the person as "you".
- "summary": 2–4 sentences, warm and even in tone — what recurs overall. End with one gentle question to sit with. Not advice.
- If there are too few entries, or they are too scattered to show a repeat, return an empty beliefs array and say so honestly and warmly in the summary.
- Reply ONLY as JSON.

Response format:
{{"beliefs": [{{"belief": "short first-person phrase", "area": "self", "evidence": ["quote", "quote"]}}], "summary": "the summary text"}}"""

    return f"""Ты помогаешь человеку в практике КПТ. У тебя есть его сохранённые разборы автоматических мыслей за какое-то время. Твоя задача — предположить, какие глубинные убеждения могут стоять за этими мыслями.

Что такое глубинное убеждение: это общее безусловное представление о себе, о других людях или о мире, которое человек обычно не проговаривает, но из которого вырастают конкретные автоматические мысли. «Меня разнесут на встрече» и «он подумал, что я тупой» могут расти из одного «со мной что-то не так, и это заметно».

Три области (в поле "area" используй ТОЛЬКО эти ключи):
{areas}

Правила:
- Предложи от 1 до 3 убеждений. Меньше — лучше, чем натянуто.
- Формулируй убеждение от первого лица, короткой фразой, по возможности словами самого человека — так, как он сказал бы это вслух.
- Каждое убеждение опирай на "evidence" — от 2 до 4 цитат из его же записей, дословно. Не выдумывай цитат: бери только то, что есть во вводе.
- Цитата короткая — до 15 слов. Если фрагмент длиннее, возьми из него самую суть и обозначь пропуск многоточием, не меняя формулировок.
- Это гипотезы, а не диагноз. Держи предположительную модальность и в формулировках, и в summary: «похоже», «часто звучит», «может быть». Никаких «у тебя убеждение», «твоя проблема в том, что».
- НЕЛЬЗЯ: ставить диагнозы, называть расстройства, советовать терапию или лечение, оценивать человека, хвалить или ругать, объяснять происхождение через детство и родителей, если человек сам об этом не писал.
- Не используй слова «пациент», «клиент», «пользователь». Обращайся на «ты».
- "summary": 2–4 предложения тёплым ровным тоном — что повторяется в целом. Закончи одним мягким вопросом, с которым можно побыть. Не советом.
- Если записей мало или они слишком разные, чтобы увидеть повтор, — верни пустой массив beliefs и честно, тепло скажи об этом в summary.
- Отвечай ТОЛЬКО на русском языке и ТОЛЬКО в формате JSON.

Формат ответа:
{{"beliefs": [{{"belief": "короткая фраза от первого лица", "area": "self", "evidence": ["цитата", "цитата"]}}], "summary": "текст обзора"}}"""


def build_beliefs_user_prompt(
    entries: list[tuple[str, str, str, list[str], list[str]]],
    language: str = "ru",
) -> str:
    """entries: (date, situation, emotions, thoughts, distortions) — validated upstream."""
    if language == "en":
        header = "Saved analyses (oldest first):"
        labels = ("situation", "emotions", "thoughts", "distortions found")
    else:
        header = "Сохранённые разборы (от старых к новым):"
        labels = ("ситуация", "эмоции", "мысли", "найденные искажения")

    lines = [header]
    for date, situation, emotions, thoughts, distortions in entries:
        lines.append(f"\n[{date}]")
        if situation.strip():
            lines.append(f"  {labels[0]}: {situation.strip()}")
        if emotions.strip():
            lines.append(f"  {labels[1]}: {emotions.strip()}")
        for t in thoughts:
            if t.strip():
                lines.append(f'  {labels[2]}: "{t.strip()}"')
        if distortions:
            lines.append(f"  {labels[3]}: {', '.join(distortions)}")
    return "\n".join(lines)


def build_review_user_prompt(
    moments: list[tuple[str, list[str], list[str], str]],
    language: str = "ru",
) -> str:
    """moments: (text, voices, themes, date) — already validated upstream."""
    if language == "en":
        header = "Recent moments (oldest first):"
        empty_text = "(no text)"
        voices_label, themes_label = "voices", "themes"
    else:
        header = "Недавние моменты (от старых к новым):"
        empty_text = "(без текста)"
        voices_label, themes_label = "голоса", "темы"

    lines = [header]
    for text, voices, themes, date in moments:
        parts = [f"[{date}]"]
        parts.append(f'"{text.strip()}"' if text.strip() else empty_text)
        if voices:
            parts.append(f"{voices_label}: {', '.join(voices)}")
        if themes:
            parts.append(f"{themes_label}: {', '.join(themes)}")
        lines.append("- " + " — ".join(parts))
    return "\n".join(lines)
