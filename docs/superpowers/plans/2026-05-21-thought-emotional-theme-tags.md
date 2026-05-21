# Эмоциональные метки на мысли — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Дать возможность вручную помечать каждую автоматическую мысль (поле B) одной или несколькими эмоциональными темами (Самокритика / Угроза / Потеря / Несправедливость) — вторая ось разметки поверх авто-искажений, без LLM и без бэкенда.

**Architecture:** Новое значение-перечисление `ThoughtTheme` + поле `Set<ThoughtTheme>` на `Thought` (runtime) и `SavedThought` (persistence, backward-compat Codable). Единый view `ThemeBar(themes:editable:language:)` рендерит ряд капсул через ручной flow-`WrapLayout`: `editable:true` — тогглы в «Анализе», `editable:false` — read-only выбранные в «Сохранено». Метки пишутся напрямую в `$thought.themes` (локальный @State формы, без async-store). Сохраняются в `entries.json` через существующий экспорт.

**Tech Stack:** SwiftUI (iOS 17), `@Observable`, единый файл `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift`. В проекте нет XCTest — верификация = `xcodebuild build` + ручной прогон в симуляторе/на устройстве.

**Spec:** `docs/superpowers/specs/2026-05-21-thought-emotional-theme-tags-design.md`

---

## File Structure

Все правки — в единственном файле `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (так устроен весь клиент, конвенцию не ломаем). Новых файлов нет. Затрагиваемые единицы:

- **Domain model** (`~line 11–38`): `ThoughtTheme`, `Thought.themes`
- **Persistence** (`~line 134–169`): `SavedThought.themes` + Codable; **`EntryStore.updateFeedback`** (`~line 232`) — должен сохранять `themes` при пересборке
- **L10n** (`~line 79–130`): `themeLabel`, `themeA11y`
- **Новые views**: `WrapLayout` (flow-layout), `ThemeBar` (капсулы)
- **ThoughtRow** (`~line 564`): встроить `ThemeBar` (editable) + гейт показа; сброс `themes` в `runAnalysis`
- **performSave** (`~line 522`): проброс `themes` в `SavedThought`
- **SavedDetailView** (`~line 938`): встроить `ThemeBar` (read-only)

Номера строк ориентировочны — искать по якорям (имена типов/функций), не по номерам.

---

## Pre-step 0: Ветка

- [ ] **Создать feature-ветку в iOS-репозитории**

Репозиторий iOS локальный, отдельный от текущего. Работаем в нём.

```bash
cd ~/Projects/abc_app_ios
git checkout -b feature/thought-themes
git status   # ожидаем: clean, на feature/thought-themes
```

- [ ] **Узнать имя scheme для сборки (один раз)**

```bash
cd ~/Projects/abc_app_ios && xcodebuild -list 2>/dev/null | sed -n '/Schemes/,$p'
```
Ожидаем строку со scheme (вероятно `CBTAnalyzer`). Использовать её в командах сборки ниже. Если destination `iPhone 16` недоступен — подставить любой установленный (`xcrun simctl list devices available`). Пользователь также может собирать в Xcode (⌘B) — это эквивалент.

---

## Task 1: Модель — `ThoughtTheme` + `Thought.themes`

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (рядом с `DistortionFeedback` ~line 22 и `struct Thought` ~line 30)

- [ ] **Step 1: Добавить enum `ThoughtTheme`**

Вставить сразу после `struct DistortionFeedback { ... }` (после `~line 22`), перед `enum AnalysisStatus`:

```swift
/// Эмоциональная тема мысли — вторая ось разметки поверх авто-искажений.
/// Ставится вручную пользователем, не зависит от LLM.
enum ThoughtTheme: String, Codable, CaseIterable, Identifiable, Hashable {
    case selfCriticism   // «я плохой / ничтожество» → стыд, вина (внутренний критик)
    case threat          // «случится плохое» → тревога, страх
    case loss            // «всё кончено / безнадёжно» → грусть, апатия
    case injustice       // «так нельзя, он не должен» → злость, обида
    var id: String { rawValue }
}
```

- [ ] **Step 2: Добавить поле `themes` на `Thought`**

В `struct Thought` после строки `var feedback: [String: DistortionFeedback] = [:]   // ключ = Distortion.name` добавить:

```swift
    var themes: Set<ThoughtTheme> = []   // эмоциональные темы, проставленные вручную
```

- [ ] **Step 3: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **` (новое поле имеет дефолт, существующие инициализаторы `Thought` не ломаются).

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): add ThoughtTheme enum + Thought.themes field"
```

---

## Task 2: Persistence — `SavedThought.themes` + Codable + updateFeedback

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`struct SavedThought` ~line 134; `EntryStore.updateFeedback` ~line 232)

- [ ] **Step 1: Добавить поле + параметр init + CodingKeys + decode/encode**

Заменить весь блок `struct SavedThought` (от `struct SavedThought: Codable, Identifiable {` до закрывающей `}` перед `struct SavedEntry`) на:

```swift
struct SavedThought: Codable, Identifiable {
    let id: UUID
    let text: String
    let distortions: [Distortion]
    let feedback: [String: DistortionFeedback]
    let themes: Set<ThoughtTheme>

    init(id: UUID = UUID(),
         text: String,
         distortions: [Distortion],
         feedback: [String: DistortionFeedback] = [:],
         themes: Set<ThoughtTheme> = []) {
        self.id = id
        self.text = text
        self.distortions = distortions
        self.feedback = feedback
        self.themes = themes
    }

    private enum CodingKeys: String, CodingKey { case id, text, distortions, feedback, themes }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try c.decode(UUID.self, forKey: .id)
        self.text = try c.decode(String.self, forKey: .text)
        self.distortions = try c.decode([Distortion].self, forKey: .distortions)
        // Old entries.json has no `feedback` key — default to empty.
        self.feedback = try c.decodeIfPresent([String: DistortionFeedback].self,
                                              forKey: .feedback) ?? [:]
        // Old entries.json has no `themes` key — default to empty.
        self.themes = try c.decodeIfPresent(Set<ThoughtTheme>.self,
                                            forKey: .themes) ?? []
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(text, forKey: .text)
        try c.encode(distortions, forKey: .distortions)
        try c.encode(feedback, forKey: .feedback)
        try c.encode(themes, forKey: .themes)
    }
}
```

- [ ] **Step 2: Сохранять `themes` при пересборке в `updateFeedback`**

В `EntryStore.updateFeedback` (~line 244) пересборка `SavedThought` сейчас НЕ передаёт `themes` → редактирование 👍/👎 в Saved-detail затёрло бы метки дефолтным `[]`. Найти:

```swift
        thoughts[ti] = SavedThought(id: st.id,
                                    text: st.text,
                                    distortions: st.distortions,
                                    feedback: fb)
```

Заменить на (добавить `themes: st.themes`):

```swift
        thoughts[ti] = SavedThought(id: st.id,
                                    text: st.text,
                                    distortions: st.distortions,
                                    feedback: fb,
                                    themes: st.themes)
```

- [ ] **Step 3: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): persist SavedThought.themes (backward-compat Codable); preserve in updateFeedback"
```

---

## Task 3: Локализация — `themeLabel` + `themeA11y`

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`enum L10n` ~line 79–130)

- [ ] **Step 1: Добавить строки тем**

В `enum L10n`, перед закрывающей `}` (после блока `// Accessibility`, ~line 129), добавить:

```swift
    // Themes
    static func themeLabel(_ l: AppLanguage, _ t: ThoughtTheme) -> String {
        switch t {
        case .selfCriticism: return l == .russian ? "Самокритика"      : "Self-criticism"
        case .threat:        return l == .russian ? "Угроза"           : "Threat"
        case .loss:          return l == .russian ? "Потеря"           : "Loss"
        case .injustice:     return l == .russian ? "Несправедливость" : "Injustice"
        }
    }
    static func themeA11y(_ l: AppLanguage, _ t: ThoughtTheme) -> String {
        (l == .russian ? "Тема: " : "Theme: ") + themeLabel(l, t)
    }
```

- [ ] **Step 2: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): L10n theme labels + a11y (RU/EN)"
```

---

## Task 4: Views — `WrapLayout` + `ThemeBar`

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (вставить перед `// MARK: - Saved tab` ~line 860, после `DistortionCardA11y`)

- [ ] **Step 1: Добавить flow-`WrapLayout`**

Вставить после `private struct DistortionCardA11y { ... }` (~line 858), перед `// MARK: - Saved tab`:

```swift
// MARK: - Theme tags

/// Простой flow-layout: складывает subview слева направо, переносит на новую
/// строку когда не влезает в доступную ширину. Для ряда меток-капсул — длинная
/// «Несправедливость» переносится, а не обрезается (в т.ч. на Dynamic Type XXXL).
/// Сознательно НЕ LazyVGrid (тот обрезает) и не горизонтальный скролл.
struct WrapLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        let rows = computeRows(maxWidth: maxWidth, subviews: subviews)
        let height = rows.reduce(0) { $0 + $1.height } + spacing * CGFloat(max(0, rows.count - 1))
        let width = rows.map(\.width).max() ?? 0
        return CGSize(width: min(width, maxWidth), height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let rows = computeRows(maxWidth: bounds.width, subviews: subviews)
        var y = bounds.minY
        for row in rows {
            var x = bounds.minX
            for index in row.items {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(at: CGPoint(x: x, y: y),
                                      anchor: .topLeading,
                                      proposal: ProposedViewSize(size))
                x += size.width + spacing
            }
            y += row.height + spacing
        }
    }

    private struct Row { var items: [Int] = []; var width: CGFloat = 0; var height: CGFloat = 0 }

    private func computeRows(maxWidth: CGFloat, subviews: Subviews) -> [Row] {
        var rows: [Row] = []
        var current = Row()
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let needed = current.items.isEmpty ? size.width : current.width + spacing + size.width
            if needed > maxWidth, !current.items.isEmpty {
                rows.append(current)
                current = Row(items: [index], width: size.width, height: size.height)
            } else {
                if !current.items.isEmpty { current.width += spacing }
                current.items.append(index)
                current.width += size.width
                current.height = max(current.height, size.height)
            }
        }
        if !current.items.isEmpty { rows.append(current) }
        return rows
    }
}
```

- [ ] **Step 2: Добавить `ThemeBar`**

Сразу после `WrapLayout` добавить. Контраст/паддинги/44pt — зеркалят `DistortionCard.reasonChip` (~line 797):

```swift
/// Единый компонент ряда меток. editable:true — тогглы (Анализ);
/// editable:false — read-only, рендерит только выбранные темы (Сохранено),
/// при пустом множестве не рендерит ничего.
struct ThemeBar: View {
    @Binding var themes: Set<ThoughtTheme>
    let editable: Bool
    let language: AppLanguage

    var body: some View {
        let shown = editable
            ? ThoughtTheme.allCases
            : ThoughtTheme.allCases.filter { themes.contains($0) }
        if !shown.isEmpty {
            WrapLayout(spacing: 8) {
                ForEach(shown) { theme in
                    chip(theme)
                }
            }
            .sensoryFeedback(.selection, trigger: themes)
        }
    }

    @ViewBuilder private func chip(_ theme: ThoughtTheme) -> some View {
        let on = themes.contains(theme)
        if editable {
            Button { toggle(theme) } label: { capsule(theme, on: on) }
                .buttonStyle(.plain)
                .frame(minHeight: 44)
                .contentShape(Capsule())
                .accessibilityLabel(L10n.themeA11y(language, theme))
                .accessibilityAddTraits(on ? [.isSelected] : [])
        } else {
            capsule(theme, on: true)
                .accessibilityLabel(L10n.themeA11y(language, theme))
        }
    }

    private func capsule(_ theme: ThoughtTheme, on: Bool) -> some View {
        Text(L10n.themeLabel(language, theme))
            .font(.caption)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                Capsule().fill(on ? Color.accentColor.opacity(0.18)
                                  : Color(.quaternarySystemFill))
            )
            .foregroundStyle(on ? Color.accentColor : .secondary)
    }

    private func toggle(_ theme: ThoughtTheme) {
        if themes.contains(theme) { themes.remove(theme) } else { themes.insert(theme) }
    }
}
```

- [ ] **Step 3: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **` (компоненты определены, ещё нигде не используются — это нормально).

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): WrapLayout flow + unified ThemeBar(themes:editable:)"
```

---

## Task 5: Встроить `ThemeBar` в «Анализ» (`ThoughtRow`)

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`ThoughtRow.body` ~line 572; computed-свойства ~line 620)

- [ ] **Step 1: Добавить гейт показа меток**

В `ThoughtRow`, рядом с `private var isSettled: Bool { ... }` (~line 620), добавить отдельный гейт (НЕ переиспользуем `isSettled` — метки не зависят от `didAnalyze`):

```swift
    // Метки видны когда мысль непустая и не в фокусе. Сознательно БЕЗ didAnalyze:
    // тема не зависит от LLM, должна быть доступна даже офлайн/при ошибке сети.
    private var themesVisible: Bool {
        !thought.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && focusedField != .thought(thought.id)
    }
```

- [ ] **Step 2: Вставить `ThemeBar` под TextField, выше карточек искажений**

В `ThoughtRow.body`, сразу после закрывающей `}` блока `HStack { TextField ... }` (~line 584, перед `if !thought.distortions.isEmpty {`) добавить:

```swift
            if themesVisible {
                ThemeBar(themes: $thought.themes, editable: true, language: settings.language)
                    .padding(.top, 2)
            }
```

- [ ] **Step 3: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Ручная проверка в симуляторе**

Запустить (Xcode ⌘R или симулятор). Сценарий:
1. Ввести мысль «я лох», нажать «Готово» (снять фокус) → под мыслью появляется ряд из 4 капсул («Самокритика», «Угроза», «Потеря», «Несправедливость»), выше карточек искажений.
2. Пока поле в фокусе (печатаешь) — капсул нет.
3. Тап по «Самокритика» → подсвечивается (accent-fill); тап ещё раз → гаснет. Можно выбрать несколько.
4. Капсулы выше карточек искажений — иерархия «мысль → метки → карточки».

Ожидаемо: всё так. Если капсулы не появляются — проверить, что гейт не требует `didAnalyze`.

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): editable ThemeBar in ThoughtRow, gated on non-empty + defocused"
```

---

## Task 6: Сброс `themes` при стирании текста

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`runAnalysis` empty-guard ~line 646)

- [ ] **Step 1: Очищать `themes` в empty-guard**

В `runAnalysis()` найти empty-guard:

```swift
        guard !trimmed.isEmpty else {
            thought.distortions = []
            thought.status = .idle
            thought.didAnalyze = false
            thought.lastAnalyzedSignature = nil
            thought.feedback = [:]
            return
        }
```

Добавить строку `thought.themes = []` (мысли больше нет — метки очищаются):

```swift
        guard !trimmed.isEmpty else {
            thought.distortions = []
            thought.status = .idle
            thought.didAnalyze = false
            thought.lastAnalyzedSignature = nil
            thought.feedback = [:]
            thought.themes = []
            return
        }
```

**ВАЖНО:** НЕ добавлять сброс `themes` в success-ветке (где `thought.feedback = [:]`). Метки — суждение о самой мысли, повторный анализ их не сбрасывает (отличие от feedback). Success-ветку не трогаем.

- [ ] **Step 2: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Ручная проверка**

1. Проставить метку на мысль → сменить язык в Настройках (триггерит повторный анализ той же мысли) → вернуться → **метки на месте** (не сбросились).
2. Стереть текст мысли в пусто → метки исчезают.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): clear themes only on emptied text, never on re-analysis"
```

---

## Task 7: Проброс `themes` при сохранении (`performSave`)

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`performSave` ~line 528)

- [ ] **Step 1: Передать `themes` в `SavedThought`**

В `performSave()` найти:

```swift
            .map { SavedThought(text: $0.text,
                                distortions: $0.distortions,
                                feedback: $0.feedback) }
```

Заменить на (добавить `themes: $0.themes`):

```swift
            .map { SavedThought(text: $0.text,
                                distortions: $0.distortions,
                                feedback: $0.feedback,
                                themes: $0.themes) }
```

- [ ] **Step 2: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): carry themes into saved entry on Save"
```

---

## Task 8: Read-only `ThemeBar` в «Сохранено» (`SavedDetailView`)

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift` (`SavedDetailView` ForEach ~line 962)

- [ ] **Step 1: Вставить read-only `ThemeBar` под текстом мысли**

В `SavedDetailView.body`, в `ForEach(entry.thoughts) { thought in ... }`, найти:

```swift
                            VStack(alignment: .leading, spacing: 8) {
                                Text(thought.text).font(.body)
                                if thought.distortions.isEmpty {
```

Вставить `ThemeBar` между `Text(thought.text)` и `if thought.distortions.isEmpty`:

```swift
                            VStack(alignment: .leading, spacing: 8) {
                                Text(thought.text).font(.body)
                                ThemeBar(themes: .constant(thought.themes),
                                         editable: false,
                                         language: entry.language)
                                if thought.distortions.isEmpty {
```

(При пустом `thought.themes` `ThemeBar` не рендерит ничего — пустого ряда не будет.)

- [ ] **Step 2: Сборка**

Run: `cd ~/Projects/abc_app_ios && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3`
Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Ручная проверка**

1. Проставить метки на мысль в «Анализе» → «Сохранить» → вкладка «Сохранено» → тап на запись.
2. В detail под мыслью видны выбранные метки (read-only, без интеракции), выше карточек искажений.
3. Мысль без меток → ряда нет (не пустая полоса).
4. Поставить 👍/👎 на искажение в detail → метки НЕ исчезают (updateFeedback сохраняет `themes`).

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer/ContentView.swift
git commit -m "feat(themes): read-only ThemeBar in SavedDetailView"
```

---

## Task 9: Финальная верификация (HIG / backward-compat / экспорт)

**Files:** нет правок кода (если что-то всплывёт — чинить и коммитить отдельно).

- [ ] **Step 1: Backward-compat со старым `entries.json`**

Если есть старый экспорт без ключа `themes` (или сохранить запись на коммите до Task 2 — но проще взять любой имеющийся `entries.json`): положить его в `Documents` приложения симулятора, открыть «Сохранено». Ожидаем: открывается без краша, у мыслей нет меток (пусто). Если старого файла нет — пропустить, backward-compat гарантирован `decodeIfPresent ?? []`.

- [ ] **Step 2: Экспорт содержит `themes`**

Сохранить запись с проставленными метками → вкладка «Сохранено» → ShareLink → сохранить `entries.json` (в Files/на мак). Открыть, проверить:
```json
"themes" : [ "selfCriticism", "loss" ]
```
Темы — массив строк rawValue. Неотмеченные мысли — `"themes" : [ ]`.

- [ ] **Step 3: HIG — Dynamic Type XXXL + перенос (главная проверка wrap)**

Симулятор: Settings → Accessibility → Display & Text Size → Larger Text → передвинуть в максимум (XXXL). Язык приложения — **русский** (длинная «Несправедливость»). В «Анализе» на мысли с метка* убедиться: капсулы **переносятся на несколько строк, не обрезаются, без горизонтального скролла**. Сделать скриншот.

- [ ] **Step 4: HIG — Dark Mode + контраст**

Переключить симулятор в Dark Mode. Выбранная капсула (`accentColor.opacity(0.18)` fill + `accentColor` текст) читаема; невыбранная (`quaternarySystemFill` + secondary) светлее карточек искажений. Обе темы — текст не сливается с фоном.

- [ ] **Step 5: HIG — VoiceOver + touch target**

Включить VoiceOver. Капсула озвучивается как «Тема: Самокритика» + состояние selected для выбранных. Тап-зона ≥ 44pt (легко попасть пальцем).

- [ ] **Step 6: Финальный commit (если были фиксы) и подготовка к merge**

Если на шагах 1–5 нашлись дефекты — починить, собрать, закоммитить. Затем:

```bash
cd ~/Projects/abc_app_ios
git log --oneline main..feature/thought-themes   # обзор всех коммитов фичи
```

Слияние в `main` — отдельным шагом по решению пользователя (см. finishing-a-development-branch). НЕ мёржить автоматически.

---

## Self-Review (выполнено при написании плана)

**Spec coverage:**
- 4 метки + enum → Task 1 ✅
- `Thought.themes` / `SavedThought.themes` + backward-compat Codable → Task 1, 2 ✅
- Reset только в empty-guard, не в success → Task 6 ✅
- Гейт без `isSettled` (non-empty + defocused) → Task 5 ✅
- Контраст как `reasonChip` (0.18 fill / quaternary unselected) → Task 4 ✅
- Ручной flow-`Layout`, не LazyVGrid → Task 4 ✅
- Единый `ThemeBar(themes:editable:)` → Task 4, 5, 8 ✅
- Проброс в Save + экспорт → Task 7, Task 9 step 2 ✅
- `updateFeedback` сохраняет themes (иначе затёр бы) → Task 2 step 2 ✅
- Read-only в Saved-detail → Task 8 ✅
- L10n RU/EN → Task 3 ✅
- Verification: backward-compat, экспорт, XXXL+RU wrap, Dark Mode, VoiceOver, 44pt → Task 9 ✅

**Placeholder scan:** код приведён полностью в каждом шаге, плейсхолдеров нет.

**Type consistency:** `ThoughtTheme` / `Thought.themes` / `SavedThought.themes` / `ThemeBar(themes:editable:language:)` / `WrapLayout(spacing:)` / `themesVisible` / `L10n.themeLabel`/`themeA11y` — имена согласованы между задачами.
