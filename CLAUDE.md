# CBT Thought Analyzer

## Описание проекта

CBT Thought Analyzer — десктопное приложение для разбора автоматических мыслей по технике ABC из когнитивно-поведенческой терапии (КПТ).

- **A** (Activating event) — ситуация, триггер
- **B** (Beliefs) — автоматические мысли, убеждения
- **C** (Consequences) — последствия: эмоции и поведение

Приложение помогает пользователю записать свои мысли и автоматически определяет когнитивные искажения с помощью AI (Llama 3.3 70B через OpenRouter с маршрутизацией на Groq/SambaNova-Turbo). Запросы идут через собственный FastAPI-бэкенд — API-ключ хранится на сервере, фронт его не видит.

## UX-концепция

### Порядок заполнения: C → A → B

Не стандартный A → B → C, а **C → A → B**:

1. **C (эмоции)** заполняется первым — эмоции ближе всего, с них проще начать
2. **A (ситуация)** — вспоминаешь контекст, что произошло
3. **B (мысли)** — основная рабочая зона с AI-анализом когнитивных искажений

### Layout

```
┌─────────────────────┬─────────────────────┐
│  C — Последствия    │  A — Ситуация       │
│  (эмоции)           │  (что произошло)    │
├─────────────────────┴─────────────────────┤
│  B — Автоматические мысли                 │
│  (основное пространство, инлайн-анализ)   │
│                                           │
│                                           │
└───────────────────────────────────────────┘
```

- **Верхний ряд:** `[C — Последствия]` и `[A — Ситуация]` — два блока 50/50
- **Нижний ряд:** `[B — Автоматические мысли]` — полная ширина, основное пространство

### Поля A и C

Простые textarea, свободный текст, без анализа.

### Поле B — список input-ов

**Нет кнопки "Анализировать"** — анализ запускается автоматически.

Поле B — вертикальный список строк ввода (input):

- Каждая мысль — отдельный `<input>` в списке
- Внизу списка всегда есть пустой input для новой мысли
- Пользователь печатает мысль, нажимает **Enter** → фокус переходит на новый пустой input ниже
- Справа от каждого input — место для **лейбла-тега** с когнитивным искажением
- Backspace в пустом input → удаление строки, фокус на предыдущую
- Каждая строка имеет стабильный `id` (nanoid/crypto.randomUUID)

**Триггер анализа:** debounce ~1.5 сек после Enter или после паузы в редактировании существующей строки.

## Техническая архитектура

### Стратегия: web first, потом iOS

Сначала полноценное веб-приложение + бэкенд. Затем iOS-приложение, которое ходит на тот же бэк (бэк выдаёт OpenAPI-спеку → генерится Swift-клиент).

### Клиенты

- Веб-фронта в этом репозитории **нет** (выпилен 2026-05-15 — основной клиент теперь iOS-приложение)
- iOS-клиент (SwiftUI) живёт в отдельном репозитории `~/Projects/abc_app_ios/`. Он шлёт `X-Device-Id` (UUID в UserDefaults) в каждом запросе — для rate-limit

### Бэкенд

- **FastAPI** (Python 3.12) + uvicorn — async-прокси к Groq
- **httpx** — async-клиент к Groq API
- **pydantic** — валидация запросов/ответов, авто-OpenAPI
- Ключ Groq в env (`GROQ_API_KEY`), в k8s — через Secret
- Rate-limit по `X-Device-Id` (in-memory sliding window, 30/мин по умолчанию)
- Эндпоинты: `/analyze`, `/health`
- Промпты живут на бэке (`backend/app/prompts.py`) — можно править без передеплоя фронта

### Деплой

- Бэкенд деплоится Docker-образом в любой среде (локально / k8s / etc.)
- Реальные production-манифесты (k8s ingress, secrets) живут вне публичного репо
- TLS — на стороне инфраструктуры (например, edge proxy)

## Groq API — анализ когнитивных искажений

### Модель

`meta-llama/llama-3.3-70b-instruct` через OpenRouter с провайдер-preference `[groq, sambanova-turbo]` и включёнными fallbacks. Среднее время `/analyze` ~1 сек, цена ~$0.00004 за вызов (см. https://openrouter.ai/meta-llama/llama-3.3-70b-instruct). Менять в `backend/app/groq_client.py` (константы `UPSTREAM_URL`, `MODEL` и блок `provider` в body).

### Подход

Список когнитивных искажений захардкожен в `backend/app/prompts.py` (кортеж `DISTORTIONS`). Промпт явно ограничивает LLM этим списком — это даёт предсказуемые, консистентные результаты.

### Промпт (формируется в `backend/app/prompts.py`)

Промпт включает:
- **system**: роль ("ты — специалист в КПТ"), задача (определить когнитивные искажения), формат ответа (JSON)
- **user**: мысль из поля B + контекст из полей A (ситуация) и C (эмоции), если они заполнены

Контекст A и C передаётся при каждом анализе строки B — это критически важно для качества. Без контекста фраза "всё пропало" может быть чем угодно, а с контекстом "увольнение" + "паника" — очевидная катастрофизация.

С v0.1.6 промпт принимает параметр `language` (`"ru"` или `"en"`):
- RU-режим — explanation на русском, имена искажений на русском (канонические из `DISTORTIONS`)
- EN-режим — explanation на английском, **имена всё равно на русском** (модели явно сказано "Pick name ONLY from this Russian list ... keep names in Russian exactly as written"). Это держит JSON-контракт стабильным — iOS-клиент использует один RU→EN mapping (`DistortionDisplayName`), независимо от языка
- Server-side в `groq_client.analyze()` фильтрует не-канонические имена и логирует drift на WARN — защита от того что Llama 3.3 70B иногда дрейфует на английские имена в EN-режиме

Текущий полный текст системного промпта (актуальная версия `backend/app/prompts.py:build_system_prompt`):

```
# language="ru" (default)
Ты — опытный специалист в КПТ (когнитивно-поведенческая терапия). Твоя задача — определить когнитивные искажения в автоматической мысли.

Вот полный список когнитивных искажений. Выбирай ТОЛЬКО из этого списка:
1. Чёрно-белое мышление
2. Сверхобобщение
3. Ментальный фильтр
4. Обесценивание положительного
5. Поспешные выводы: чтение мыслей
6. Поспешные выводы: предсказание будущего
7. Катастрофизация
8. Минимизация
9. Эмоциональное обоснование
10. Долженствование
11. Навешивание ярлыков
12. Персонализация
13. Туннельное зрение
14. Перфекционизм
15. Сравнение
16. Ошибка справедливости
17. Ошибка контроля
18. Обвинение

Правила:
- Определи от 0 до 3 искажений из списка выше
- Используй ТОЛЬКО названия из списка, не придумывай свои
- Если мысль не содержит искажений, верни пустой массив
- Если ввод бессмысленный, нечитаемый или не содержит мысли (набор букв, случайные символы, тестовый ввод вроде «asdf», «ыыы», «zzz» и т.п.) — верни пустой массив distortions. НЕ пытайся натянуть искажения на бессмыслицу.
- Отвечай ТОЛЬКО на русском языке
- Отвечай ТОЛЬКО в формате JSON
- В пояснении (explanation) НЕ используй слова «пациент», «клиент», «пользователь». Описывай саму мысль и почему искажение подходит. Например: «Мысль преувеличивает последствия...» вместо «Пациент преувеличивает...». Можно обращаться на «ты», но не присваивать ярлык «пациент».

Формат ответа:
{
  "distortions": [
    { "name": "Название из списка", "explanation": "Краткое пояснение, почему это искажение" }
  ]
}
```

```
# language="en"
You are a CBT (cognitive-behavioral therapy) expert. Your task is to identify cognitive distortions in an automatic thought.

Here is the full list of cognitive distortions. Pick name ONLY from this Russian list (do not translate names, keep them in Russian exactly as written):
{18 наименований из DISTORTIONS}

Rules:
- Identify 0 to 3 distortions from the list above
- Use ONLY names from the list, do not invent new ones
- The "name" field MUST be the Russian name from the list above, verbatim
- The "explanation" field MUST be in English, describing why this distortion applies to the thought
- If the thought contains no distortions, return an empty distortions array
- If the input is gibberish, random characters, test input like "asdf", "zzz", or otherwise meaningless — return an empty distortions array. DO NOT force distortions onto nonsense.
- Reply ONLY as JSON
- In the explanation do NOT use the words "patient", "client", or "user". Describe the thought itself and why the distortion applies.

Response format:
{
  "distortions": [
    { "name": "Name from the list above in Russian", "explanation": "Brief explanation in English of why this distortion applies" }
  ]
}
```

Менять промпт без передеплоя фронта: правишь `backend/app/prompts.py` → `cbt-backend:vX.Y.Z` build → `git push` в Gitea → ArgoCD синкает за минуту. Никаких изменений iOS/web не нужно.

### Формат ответа

```json
{
  "distortions": [
    { "name": "Катастрофизация", "explanation": "краткое пояснение" }
  ]
}
```

Массив от 0 до 3 искажений — лимит задаётся в промпте. Пустой массив — мысль без искажений.

## Структура проекта

```
abc_app/
├── CLAUDE.md
├── README.md
├── backend/                     # FastAPI бэкенд (единственный код в репо)
│   ├── app/
│   │   ├── main.py              # FastAPI приложение, эндпоинты
│   │   ├── schemas.py           # Pydantic-модели запросов/ответов
│   │   ├── prompts.py           # Промпты для LLM
│   │   ├── groq_client.py       # httpx-обёртка над OpenRouter (имя историческое)
│   │   └── rate_limit.py        # In-memory rate-limiter
│   ├── Dockerfile
│   ├── docker-compose.yml       # Локальный запуск бэка
│   ├── requirements.txt
│   └── .env.example
└── deploy/                      # gitignored, реальные k8s манифесты хранятся отдельно
```

iOS-клиент: отдельный репозиторий `~/Projects/abc_app_ios/`.

## Команды разработки (только бэкенд)

```bash
cd backend

# Локально без Docker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000

# Через Docker
docker compose up
```

## iOS-клиент

Нативный SwiftUI-клиент живёт в **отдельном репозитории**: `~/Projects/abc_app_ios/` (не на GitHub — только локально, плюс возможно потом отдельный публичный репо).

**Стек:** SwiftUI + `@Observable` + `URLSession async/await`, никаких сторонних библиотек. Минимум iOS 17.0, Xcode 16+.

**Архитектура (после pivot 2026-05-14, всё в одном файле `CBTAnalyzer/CBTAnalyzer/ContentView.swift`):**
- TabView с тремя вкладками: **Анализ / Сохранено / Настройки**
- **Анализ** — `Form` с тремя секциями (ситуация, эмоции, мысли), реактивный анализ через `.task(id: AnalysisInput(...))` с debounce 1.5 сек, кнопка **Сохранить** в `.topBarTrailing`
- **Сохранено** — `List` сохранённых entries с relative-датами, swipe-to-delete (`allowsFullSwipe: false`), `ShareLink` для экспорта всего JSON
- **Настройки** — `Picker(.inline)` для языка (Russian / English)
- Локализация через `enum L10n` со switch по `AppLanguage` (UserDefaults), отдельная карта `DistortionDisplayName` (RU→EN)
- Хранение: `Documents/entries.json` через `@Observable @MainActor EntryStore`, I/O через `Task.detached`, даты в ISO-8601

**Технические нюансы (важно держать в голове):**
- `EntryStore` создаётся в `ContentView` как `@State` — НЕ в каждой вкладке (иначе пересоздаётся при переключении табов)
- Tab labels читают `settings.language` прямо в `ContentView.body` — это регистрирует @Observable-зависимость, нельзя выносить в helper-метод
- `@FocusState` нужно объявлять с enum-per-field, иначе `focusedField = nil` не сработает (см. `AnalyzeView.Field`)
- `ShareLink` URL регенерится в `.task(id: store.entries.map(\.id))` — иначе экспорт устаревает после save/delete
- Haptic Save триггерится по `lastSavedId: UUID?`, а не по `entries.count` — иначе delete тоже buzzит «success»
- `Thought.didAnalyze: Bool` сбрасывается на `false` когда текст пустой → empty-state «Когнитивные искажения не найдены» не висит над пустым полем

**Backend контракт:**
- `AnalyzeRequest.emotions` (не `feelings` — UI-лейбл другой!)
- `AnalyzeRequest.language: "ru" | "en"`
- **НЕ** включать `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase` — ключи бэка отдаются как есть
- Имена искажений в ответе — из канонического списка `DISTORTIONS` (RU) / `DISTORTIONS_EN` (EN), по выбранному `language`

## Шаринг приложения (для одного человека, без App Store)

Когда захочется поделиться приложением (например, с близким), есть три пути по возрастанию формальности:

1. **Веб-версия на Vercel** (бесплатно, ~30 минут) — деплоим React-фронт из публичного `bulatsir/cbt-thought-analyzer` на Vercel, человек открывает URL в Safari → «Добавить на экран Домой» → выглядит почти как приложение. Минус: без нативного UX и без локальных сохранений (веб-версия пока не имеет фичей iOS-pivot). Плюс: ноль денег, мгновенно, автообновления при push.
2. **TestFlight** ($99/год Apple Developer Program) — закрытое тестирование до 90 дней, инвайт по Apple ID, нативное iOS-приложение со всеми фичами. Без App Store Review. Платится один раз, после этого можно неограниченно обновлять.
3. **Free provisioning через мак** (бесплатно, неудобно) — подключаешь iPhone человека к маку, ⌘R в Xcode. Билд работает **7 дней**, потом надо подключать заново. Только если человек физически рядом.

**Apple Developer Program ($99/год)** обязателен для App Store **и** TestFlight. Без него — только варианты 1 и 3.

**Privacy Policy URL** — нужен только для App Store publication, не для TestFlight/Vercel/free provisioning.

## Будущие улучшения

- **Локализация веб-версии** — сейчас web-фронт на русском, для шаринга на Vercel желательно сделать EN/RU как в iOS
- **Локальная история entries на бэке** — Postgres (SQLAlchemy/asyncpg) рядом с FastAPI. Сейчас сохранения только на устройстве (iOS app), при переустановке приложения теряются. Для веба сохранений вообще нет.
- **Аккаунты + опциональная история** — Apple Sign In / email magic link, флаг "анонимный режим" в каждом запросе
- **Платная подписка** — Stripe для веба / StoreKit для iOS, тарифы = разные лимиты в rate-limiter
- **Экспорт PDF** — пока iOS экспортирует только JSON через ShareLink, для работы с терапевтом нужен читаемый формат
- **App icon** — пока на iOS дефолтная пустая сетка, перед App Store Review обязательно сделать
