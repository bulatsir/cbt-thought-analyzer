# Эмоциональные метки на мысли (iOS)

**Дата:** 2026-05-21
**Репозиторий:** `~/Projects/abc_app_ios/` (единый файл `CBTAnalyzer/CBTAnalyzer/ContentView.swift`)
**Бэкенд:** не трогаем. Без LLM, без сети, без новых эндпоинтов.

## Цель

Дать возможность вручную помечать каждую автоматическую мысль (поле B) по **эмоциональной теме**. Это вторая ось разметки поверх уже существующих авто-искажений: искажения — *как* мысль искажена (логическая ошибка, детектит LLM), темы — *про что* мысль (эмоциональная тема, ставит пользователь).

Изначальная задача пользователя — «просто замечать, где всплывает внутренний критик». Метки решают её и расширяют до 4 клинически обоснованных тем (гипотеза специфичности содержания, Бек): какая тема в мысли → такая эмоция.

**Не цель v1:** тёплый ответ (loving-friend rewrite), якорь common humanity, отметка backdraft, отдельная вкладка «Сострадание», график/тренд, любой LLM-ассист. Всё это сознательно отложено — это другая школа (self-compassion / MSC), приложение остаётся чистым КПТ-инструментом. См. «Отложено» ниже.

## Метки (4 темы)

Множественный выбор — у мысли может быть несколько тем одновременно.

| case | RU | EN | Тема / эмоция |
|---|---|---|---|
| `selfCriticism` | Самокритика | Self-criticism | «я плохой / ничтожество» → стыд, вина (это «внутренний критик») |
| `threat` | Угроза | Threat | «случится плохое» → тревога, страх |
| `loss` | Потеря | Loss | «всё кончено / безнадёжно» → грусть, апатия |
| `injustice` | Несправедливость | Injustice | «так нельзя, он не должен» → злость, обида |

Порядок фиксирован (`selfCriticism, threat, loss, injustice`) — он же порядок отображения капсул.

SF Symbols подбираются при реализации (кандидаты: `exclamationmark.bubble`, `exclamationmark.triangle`, `cloud.rain`, `scalemass`). Emoji в UI не используем — только SF Symbols, по конвенции проекта (HIG, [[apple_hig_reference]]).

## Модель данных

```swift
enum ThoughtTheme: String, Codable, CaseIterable, Identifiable, Hashable {
    case selfCriticism
    case threat
    case loss
    case injustice
    var id: String { rawValue }
}
```

- `Thought.themes: Set<ThoughtTheme> = []` — новое поле на runtime-модели.
- `SavedThought.themes: Set<ThoughtTheme>` — новое поле на persistence-модели.

`SavedThought` уже имеет ручной `Codable` (из-за backward-compat `feedback`). Добавляем `themes` тем же паттерном:
- `CodingKeys` += `themes`
- `init(from:)`: `self.themes = try c.decodeIfPresent(Set<ThoughtTheme>.self, forKey: .themes) ?? []` — старые `entries.json` без ключа читаются как пустое множество.
- `encode(to:)`: `try c.encode(themes, forKey: .themes)`
- `init(...)`: добавить параметр `themes: Set<ThoughtTheme> = []`.

`Set<ThoughtTheme>` кодируется как JSON-массив строк rawValue — стабильно и читаемо в экспорте:
```json
"themes": ["selfCriticism", "loss"]
```

## Поведение при повторном анализе (важное отличие от feedback)

Метки — это **суждение пользователя о самой мысли**, а не оценка работы LLM. Поэтому, в отличие от `feedback` (👍/👎), они **НЕ сбрасываются** при успешном повторном анализе.

В `runAnalysis()`:
- **success-ветка** (`thought.feedback = [:]`): `themes` НЕ трогаем — текст мысли тот же, тема всё ещё валидна.
- **empty-guard** (текст стёрт в пусто): `themes = []` — мысли больше нет, метки очищаются (рядом с уже существующими сбросами `distortions`/`feedback`/`didAnalyze`).
- cancel/error-ветки: `themes` не трогаем.

Редактирование текста без обнуления → метки сохраняются (перетегировать дёшево, не вынуждаем).

## UI

### Вкладка «Анализ» — `ThoughtRow`

Ряд из 4 капсул-тогглов **прямо под TextField мысли, ВЫШЕ карточек искажений**:

```
[ TextField: "я лох" ]
  Самокритика  Угроза  Потеря  Несправедливость   ← ряд тогглов
  ┌─────────────────────────┐
  │ Катастрофизация   👍 👎 │   ← карточки искажений (ниже, без изменений)
  └─────────────────────────┘
```

- Гейт показа: тот же `isSettled` (`didAnalyze && status == .idle && focusedField != .thought(id)`), что у `ratable` для 👍/👎. Пока печатаешь — меток нет, не мешают.
- Капсула: выбранная — залита `Color.accentColor`-tint + текст контрастный; невыбранная — `Color(.tertiarySystemFill)` + `.secondary` (WCAG-safe, как чипы искажений). Тап = toggle членства в `Set`.
- Перенос на несколько строк при необходимости (4 капсулы + Dynamic Type XXXL): использовать перенос (например `Layout`/wrap), не горизонтальный скролл, не обрезку.
- Touch target ≥ 44pt (`.frame(minHeight: 44).contentShape(Capsule())`), как у chips в `DistortionCard`.
- Биндинг: метки пишутся напрямую в `$thought.themes` (toggle через `Binding`), без async-store — это локальный @State формы, гонок нет (в отличие от Saved-detail feedback).

Новый компонент `ThemeBar` (или inline-`ForEach(ThoughtTheme.allCases)`), малый и самодостаточный.

### Вкладка «Сохранено» — `SavedDetailView`

Метки показываются **read-only** под текстом каждой мысли (выше карточек искажений), теми же капсулами, но без интеракции (выбранные подсвечены, невыбранные не показываются вовсе — read-only-режим показывает только проставленные темы, чтобы не зашумлять).

**v1-решение:** в Saved-detail метки НЕ редактируются. Они ставятся в момент разбора на вкладке «Анализ» («заметить, где всплывает»), а сохранённая запись — снимок. Это сознательно проще, чем feedback (который в detail редактируется): экономит `EntryStore.updateThemes` + биндинг + optimistic-state. Если позже захочется править — добавим отдельно.

## Сохранение / экспорт

- `performSave()` (в `AnalyzeView`): в `.map { SavedThought(...) }` добавить `themes: $0.themes`.
- `themes` автоматически уезжают в `entries.json` через существующий `makeExportFile()` / ShareLink — это и есть накопление данных «со временем заметить паттерн».

## Локализация

Через существующий `enum L10n`, по образцу feedback-строк:

```swift
static func themeLabel(_ l: AppLanguage, _ t: ThoughtTheme) -> String { ... }   // switch по case
static func themeA11y(_ l: AppLanguage, _ t: ThoughtTheme) -> String { ... }     // "Тема: Самокритика" / "Theme: Self-criticism"
```

Read-only / toggle капсулы озвучивают состояние для VoiceOver (`.accessibilityAddTraits(.isSelected)` на выбранных, `accessibilityLabel` = тема).

## Затрагиваемые места (карта правок)

1. **Модель** (`~line 30`): `enum ThoughtTheme`, `Thought.themes`.
2. **`runAnalysis()`** (`~line 644`): сброс `themes` только в empty-guard.
3. **`SavedThought`** (`~line 134`): поле + `CodingKeys`/`init(from:)`/`encode`/`init`.
4. **`performSave()`** (`~line 528`): проброс `themes`.
5. **`ThoughtRow.body`** (`~line 585`): `ThemeBar` под TextField, выше блока distortions, гейт `isSettled`.
6. **`SavedDetailView`** (`~line 962`): read-only показ тем над карточками искажений.
7. **`L10n`** (`~line 130`): `themeLabel` + `themeA11y`.
8. **Новый view** `ThemeBar` (toggle) + read-only вариант (или флаг `editable`).

Номера строк ориентировочны (файл ~1036 строк) — при реализации искать по якорям, не по номерам.

## Verification

XCTest в проекте нет — проверка через `xcodebuild build` + ручной прогон в симуляторе:

1. **Сборка** без warnings.
2. **Гейт:** печатаешь мысль → меток нет; после анализа и снятия фокуса («Готово») → ряд из 4 капсул появляется под мыслью, выше карточек искажений.
3. **Toggle:** тап по «Самокритика» → подсвечивается; тап ещё раз → гаснет. Несколько меток одновременно — работают.
4. **Ре-анализ не сбрасывает:** проставил метки → сменил язык/контекст (повторный анализ той же мысли) → метки на месте (в отличие от 👍/👎, которые слетают).
5. **Стирание сбрасывает:** очистил текст мысли в пусто → метки исчезают.
6. **Save + Saved-detail:** сохранил запись с метками → в detail метки видны (read-only) под мыслью.
7. **Backward-compat:** старый `entries.json` без ключа `themes` открывается без краша, метки = пусто.
8. **Экспорт:** ShareLink `entries.json` содержит `"themes": [...]` строками rawValue.
9. **HIG:** Dynamic Type XXXL — капсулы переносятся, не обрезаются; Dark Mode корректен; VoiceOver читает тему и selected-состояние; touch target ≥ 44pt.

## Отложено (не v1)

- Тёплый ответ (loving-friend rewrite), общая человечность, backdraft — другая школа (MSC), возможно отдельная вкладка позже.
- LLM-ассист любой формы (подсказка/разбор тона) — пользователь решит позже.
- График/тренд по темам и backdraft.
- Редактирование меток в Saved-detail.
- Авто-предложение темы по тексту мысли.
