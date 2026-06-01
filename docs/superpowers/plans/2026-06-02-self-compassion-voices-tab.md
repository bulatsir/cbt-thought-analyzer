# Вкладка «Голоса» (самосострадание) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в Cogi вторую вкладку «Голоса» — быстрая фиксация моментов внутреннего критика (текст опц. + выбор голоса + 2 опциональные оценки 0–10) с историей и счётчиками-паттернами, локально, без AI.

**Architecture:** Новые value-типы (`VoiceColor`, `InnerVoice`, `CompassionMoment`, `VoicesState`) + `@Observable @MainActor VoicesStore` (один файл `voices_state.json`, паттерн `EntryStore`, но строже: forward-compat `decodeIfPresent`, поэлементный декод moments, no-wipe-guard). UI — стандартный SwiftUI: `VoicesView` (история + чипы-сводка + закреплённая кнопка), `CaptureSheet` (модальный черновик), `VoiceEditor`, `MomentDetail`, `RatingScale` (tap-scale). Всё в одном файле `ContentView.swift`, как остальной клиент.

**Tech Stack:** SwiftUI (iOS 17.6), `@Observable`, Xcode 16. XCTest в проекте нет → верификация = `xcodebuild build` (или ⌘B) + ручной прогон. Симулятор не используем — сборку/прогон делает пользователь на устройстве.

**Spec:** `docs/superpowers/specs/2026-06-01-self-compassion-voices-tab-design.md`

---

## Контекст кода (якоря в `~/Projects/cogi_ios/Cogi/Cogi/ContentView.swift`)

- `enum AppLanguage` (61), `AppSettings` (75), `enum L10n` (90–155).
- `SavedThought` Codable + backward-compat `init(from:)`/`decodeIfPresent` (159–201) — эталон Codable.
- `EntryStore` (214–313): `makeCoder()` (223), `load()` (232), `save/delete` (249–262), `persist()` (290).
- `ContentView` + TabView (425–453); `.task { await store.load() }` (449–451).
- `WrapLayout: Layout` (955–1003) — flow-ряд для чипов.
- `SavedListView` (1061–1108): `ContentUnavailableView`, `List/ForEach/swipeActions(allowsFullSwipe:false)`.
- `SavedRow` (1110–1135): relative-дата `Date.RelativeFormatStyle(.named).locale(ruLocale/enLocale)`.
- Хаптика `.sensoryFeedback(.success, trigger: lastSavedId)` (577).

Номера строк ориентировочны — искать по якорям (имена типов/функций).

Все правки — в этом единственном файле (конвенцию не ломаем). Билд:
`cd ~/Projects/cogi_ios && xcodebuild -project Cogi/Cogi.xcodeproj -scheme Cogi -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -3` → ждём `** BUILD SUCCEEDED **`. Пользователь может вместо этого ⌘B/⌘R на устройстве.

---

## Pre-step 0: Ветка

- [ ] **Создать feature-ветку в iOS-репо**

```bash
cd ~/Projects/cogi_ios && git checkout -b feature/voices-tab && git status
```
Ожидаем: clean, на `feature/voices-tab`.

---

## Task 1: Доменные модели

**Files:** Modify `ContentView.swift` — вставить новый раздел сразу после блока тем (после `enum ThoughtTheme`/`struct Thought`, перед `enum AnalysisStatus` ~line 34; либо рядом с `// MARK: - Persistence models` ~157).

- [ ] **Step 1: Добавить `VoiceColor`, `InnerVoice`, `CompassionMoment`, `VoicesState`**

```swift
// MARK: - Voices (self-compassion) models

/// Курируемая палитра голосов — пресет, а не произвольный hex.
/// Гарантирует валидный цвет и контраст-пару; рендерится как tint.opacity(0.18) фон + семантический текст.
enum VoiceColor: String, Codable, CaseIterable, Identifiable {
    case rose, amber, sky, violet, teal, lime, slate, coral
    var id: String { rawValue }

    static let fallback: VoiceColor = .slate

    var tint: Color {
        switch self {
        case .rose:   return Color(red: 0.88, green: 0.27, blue: 0.45)
        case .amber:  return Color(red: 0.90, green: 0.60, blue: 0.10)
        case .sky:    return Color(red: 0.20, green: 0.55, blue: 0.90)
        case .violet: return Color(red: 0.55, green: 0.35, blue: 0.85)
        case .teal:   return Color(red: 0.10, green: 0.60, blue: 0.55)
        case .lime:   return Color(red: 0.45, green: 0.65, blue: 0.20)
        case .slate:  return Color(red: 0.40, green: 0.45, blue: 0.52)
        case .coral:  return Color(red: 0.95, green: 0.45, blue: 0.35)
        }
    }

    /// Декод неизвестного/отсутствующего rawValue → fallback (не throw) — forward-compat.
    init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = VoiceColor(rawValue: raw) ?? .fallback
    }
}

/// Внутренний голос-критик. Создаётся и редактируется пользователем.
struct InnerVoice: Codable, Identifiable, Hashable {
    let id: UUID
    var name: String
    var emoji: String        // ровно 1 grapheme; пусто → "🗣"
    var color: VoiceColor

    init(id: UUID = UUID(), name: String, emoji: String = "🗣", color: VoiceColor = .fallback) {
        self.id = id
        self.name = name
        self.emoji = emoji.isEmpty ? "🗣" : emoji
        self.color = color
    }

    private enum CodingKeys: String, CodingKey { case id, name, emoji, color }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try c.decode(UUID.self, forKey: .id)
        self.name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        let e = try c.decodeIfPresent(String.self, forKey: .emoji) ?? "🗣"
        self.emoji = e.isEmpty ? "🗣" : e
        self.color = try c.decodeIfPresent(VoiceColor.self, forKey: .color) ?? .fallback
    }
}

/// Зафиксированный момент. Хранит и voiceID (для группировки), и снимок голоса (для целостности истории).
struct CompassionMoment: Codable, Identifiable {
    let id: UUID
    let createdAt: Date
    let voiceID: UUID
    let voiceName: String
    let voiceEmoji: String
    let voiceColor: VoiceColor
    let text: String?        // опц.; "" → nil на сохранении
    let emotion: Int?        // 0–10, опц. (выше = сильнее)
    let presence: Int?       // 0–10, опц. (выше = на опоре)

    init(id: UUID = UUID(), createdAt: Date = Date(), voiceID: UUID,
         voiceName: String, voiceEmoji: String, voiceColor: VoiceColor,
         text: String?, emotion: Int?, presence: Int?) {
        self.id = id; self.createdAt = createdAt; self.voiceID = voiceID
        self.voiceName = voiceName; self.voiceEmoji = voiceEmoji; self.voiceColor = voiceColor
        self.text = text; self.emotion = emotion; self.presence = presence
    }

    private enum CodingKeys: String, CodingKey {
        case id, createdAt, voiceID, voiceName, voiceEmoji, voiceColor, text, emotion, presence
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try c.decode(UUID.self, forKey: .id)
        self.createdAt = try c.decode(Date.self, forKey: .createdAt)
        self.voiceID = try c.decode(UUID.self, forKey: .voiceID)
        self.voiceName = try c.decodeIfPresent(String.self, forKey: .voiceName) ?? ""
        self.voiceEmoji = try c.decodeIfPresent(String.self, forKey: .voiceEmoji) ?? "🗣"
        self.voiceColor = try c.decodeIfPresent(VoiceColor.self, forKey: .voiceColor) ?? .fallback
        self.text = try c.decodeIfPresent(String.self, forKey: .text)
        self.emotion = try c.decodeIfPresent(Int.self, forKey: .emotion)
        self.presence = try c.decodeIfPresent(Int.self, forKey: .presence)
    }
}

/// Контейнер для одного файла persist — одна точка отказа, нет гонки двух файлов.
struct VoicesState: Codable {
    var voices: [InnerVoice]
    var moments: [CompassionMoment]

    init(voices: [InnerVoice] = [], moments: [CompassionMoment] = []) {
        self.voices = voices; self.moments = moments
    }

    private enum CodingKeys: String, CodingKey { case voices, moments }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.voices = try c.decodeIfPresent([InnerVoice].self, forKey: .voices) ?? []
        self.moments = try c.decodeIfPresent([CompassionMoment].self, forKey: .moments) ?? []
    }
}
```

- [ ] **Step 2: Сборка**

Run билд (см. Контекст). Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): domain models (VoiceColor, InnerVoice, CompassionMoment, VoicesState)"
```

---

## Task 2: `VoicesStore`

**Files:** Modify `ContentView.swift` — после `EntryStore` (после ~313), перед `// MARK: - API DTOs`.

- [ ] **Step 1: Добавить стор**

```swift
// MARK: - VoicesStore

@Observable
@MainActor
final class VoicesStore {
    private(set) var voices: [InnerVoice] = []
    private(set) var moments: [CompassionMoment] = []   // всегда createdAt desc
    private(set) var didLoad = false
    private(set) var lastAddedID: UUID?                 // только для хаптики на addMoment

    private var fileURL: URL {
        URL.documentsDirectory.appending(path: "voices_state.json")
    }

    nonisolated private static func makeCoder() -> (JSONEncoder, JSONDecoder) {
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        return (enc, dec)
    }

    /// Поэлементный декод: битая запись отбрасывается, а не роняет весь файл.
    private struct FailableMoment: Decodable {
        let value: CompassionMoment?
        init(from decoder: Decoder) throws {
            value = try? CompassionMoment(from: decoder)
        }
    }
    private struct LenientState: Decodable {
        let voices: [InnerVoice]
        let moments: [CompassionMoment]
        private enum CodingKeys: String, CodingKey { case voices, moments }
        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            let rawVoices = try c.decodeIfPresent([FailableVoice].self, forKey: .voices) ?? []
            let rawMoments = try c.decodeIfPresent([FailableMoment].self, forKey: .moments) ?? []
            voices = rawVoices.compactMap(\.value)
            moments = rawMoments.compactMap(\.value)
        }
        struct FailableVoice: Decodable {
            let value: InnerVoice?
            init(from decoder: Decoder) throws { value = try? InnerVoice(from: decoder) }
        }
    }

    func load() async {
        defer { didLoad = true }
        let url = fileURL
        let data: Data? = await Task.detached { try? Data(contentsOf: url) }.value
        guard let data, !data.isEmpty else {
            voices = []; moments = []
            return
        }
        let (_, decoder) = Self.makeCoder()
        guard let parsed = try? decoder.decode(LenientState.self, from: data) else {
            // НЕ перезаписываем файл: данные есть, но не распарсились — оставляем шанс на recovery.
            // В рантайме показываем пусто, но persist() не вызываем здесь.
            voices = []; moments = []
            return
        }
        voices = parsed.voices
        moments = parsed.moments.sorted { $0.createdAt > $1.createdAt }
    }

    func addVoice(_ v: InnerVoice) async {
        voices.append(v)
        await persist()
    }

    func updateVoice(_ v: InnerVoice) async {
        guard let i = voices.firstIndex(where: { $0.id == v.id }) else { return }
        voices[i] = v
        await persist()
    }

    func deleteVoice(id: UUID) async {
        voices.removeAll { $0.id == id }   // моменты остаются (снимок)
        await persist()
    }

    func addMoment(_ m: CompassionMoment) async {
        moments.insert(m, at: 0)           // createdAt desc: новейший сверху
        lastAddedID = m.id                 // триггер хаптики только на добавление, не на delete
        await persist()
    }

    func deleteMoment(id: UUID) async {
        moments.removeAll { $0.id == id }
        await persist()
    }

    private func persist() async {
        let snapshot = VoicesState(voices: voices, moments: moments)
        let url = fileURL
        await Task.detached {
            let (encoder, _) = VoicesStore.makeCoder()
            if let data = try? encoder.encode(snapshot) {
                try? data.write(to: url, options: [.atomic])
            }
        }.value
    }
}
```

- [ ] **Step 2: Сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): VoicesStore (single-file, lenient decode, no-wipe guard)"
```

---

## Task 3: Локализация — новые ключи `L10n`

**Files:** Modify `ContentView.swift` — внутри `enum L10n` (90–155), добавить секцию перед закрывающей `}` (после блока Themes ~154).

- [ ] **Step 1: Добавить ключи**

```swift
    // Voices tab
    static func tabVoices(_ l: AppLanguage)        -> String { l == .russian ? "Голоса"               : "Voices" }
    static func captureButton(_ l: AppLanguage)    -> String { l == .russian ? "Зафиксировать"        : "Capture" }
    static func captureTitle(_ l: AppLanguage)     -> String { l == .russian ? "Новый момент"         : "New moment" }
    static func fieldThought(_ l: AppLanguage)     -> String { l == .russian ? "Что произошло / какая мысль" : "What happened / which thought" }
    static func fieldVoice(_ l: AppLanguage)       -> String { l == .russian ? "Чей это голос?"       : "Whose voice?" }
    static func scaleEmotion(_ l: AppLanguage)     -> String { l == .russian ? "Сила эмоции"          : "Emotion intensity" }
    static func scalePresence(_ l: AppLanguage)    -> String { l == .russian ? "Присутствие"          : "Presence" }
    static func emotionLow(_ l: AppLanguage)       -> String { l == .russian ? "слабо"                : "mild" }
    static func emotionHigh(_ l: AppLanguage)      -> String { l == .russian ? "сильно"               : "strong" }
    static func presenceLow(_ l: AppLanguage)      -> String { l == .russian ? "захлёстывает"         : "overwhelmed" }
    static func presenceHigh(_ l: AppLanguage)     -> String { l == .russian ? "на опоре"             : "grounded" }
    static func newVoice(_ l: AppLanguage)         -> String { l == .russian ? "Новый голос"          : "New voice" }
    static func voiceNameField(_ l: AppLanguage)   -> String { l == .russian ? "Имя"                  : "Name" }
    static func voiceEmojiField(_ l: AppLanguage)  -> String { l == .russian ? "Эмодзи"               : "Emoji" }
    static func voiceColorField(_ l: AppLanguage)  -> String { l == .russian ? "Цвет"                 : "Color" }
    static func deleteVoice(_ l: AppLanguage)      -> String { l == .russian ? "Удалить голос"        : "Delete voice" }
    static func cancel(_ l: AppLanguage)           -> String { l == .russian ? "Отмена"               : "Cancel" }
    static func noWords(_ l: AppLanguage)          -> String { l == .russian ? "(без слов)"           : "(no words)" }
    static func momentTitle(_ l: AppLanguage)      -> String { l == .russian ? "Момент"               : "Moment" }
    static func voicesEmptyTitle(_ l: AppLanguage) -> String { l == .russian ? "Пока нет голосов"     : "No voices yet" }
    static func voicesEmptyDesc(_ l: AppLanguage)  -> String { l == .russian ? "Создай первый голос — например «Стыдобист»." : "Create your first voice — e.g. \"Inner Critic\"." }
    static func createVoiceCTA(_ l: AppLanguage)   -> String { l == .russian ? "Создать голос"        : "Create a voice" }
    static func momentsEmptyHint(_ l: AppLanguage) -> String { l == .russian ? "Зафиксируй первый момент." : "Capture your first moment." }
    static func emotionShort(_ l: AppLanguage)     -> String { l == .russian ? "эмоция"               : "emotion" }
    static func presenceShort(_ l: AppLanguage)    -> String { l == .russian ? "присутствие"          : "presence" }
```

(Кнопку сохранения в листе берём из существующей `L10n.done`, удаление момента — `L10n.deleteAction`.)

- [ ] **Step 2: Сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): L10n keys (RU/EN)"
```

---

## Task 4: Подключить стор + 4-я вкладка (второй) со стабом

**Files:** Modify `ContentView` (425–453). Добавить временный `VoicesView` стаб (заменим в Task 7).

- [ ] **Step 1: Стаб `VoicesView`**

Вставить рядом с другими View (например после `AnalyzeView`-блока):

```swift
// MARK: - Voices tab (stub — заменяется в Task 7)
struct VoicesView: View {
    @Environment(AppSettings.self) private var settings
    @Environment(VoicesStore.self) private var store

    var body: some View {
        Text(L10n.tabVoices(settings.language))
            .navigationTitle(L10n.tabVoices(settings.language))
    }
}
```

- [ ] **Step 2: Добавить стор и вкладку в `ContentView`**

В `ContentView` добавить `@State private var voicesStore = VoicesStore()` рядом с `store` (427).
Вставить вкладку **вторым** элементом TabView (между «Анализ» и «Сохранено»):

```swift
            NavigationStack { VoicesView() }
                .tabItem {
                    Label(L10n.tabVoices(settings.language), systemImage: "quote.bubble")
                }
```

Добавить `.environment(voicesStore)` рядом с `.environment(store)` (448).
Заменить `.task { await store.load() }` (449–451) на параллельную загрузку:

```swift
        .task {
            async let a: Void = store.load()
            async let b: Void = voicesStore.load()
            _ = await (a, b)
        }
```

- [ ] **Step 3: Сборка** → `** BUILD SUCCEEDED **`. Ручной: появилась 2-я вкладка «Голоса».

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): wire VoicesStore + add Voices tab (second) with stub"
```

---

## Task 5: `VoiceEditor` (создание/редактирование голоса)

**Files:** Modify `ContentView.swift` — добавить View рядом с остальными.

- [ ] **Step 1: Добавить редактор**

```swift
// MARK: - VoiceEditor

struct VoiceEditor: View {
    @Environment(AppSettings.self) private var settings
    @Environment(VoicesStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    /// nil → создаём новый; иначе редактируем существующий.
    let existing: InnerVoice?
    /// Колбэк с id сохранённого голоса (для пред-выбора в CaptureSheet после inline-создания).
    var onSaved: ((UUID) -> Void)? = nil

    @State private var name: String = ""
    @State private var emoji: String = "🗣"
    @State private var color: VoiceColor = .fallback
    @State private var showDeleteConfirm = false

    private var canSave: Bool {
        !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField(L10n.voiceNameField(settings.language), text: $name)
                    HStack {
                        Text(L10n.voiceEmojiField(settings.language))
                        Spacer()
                        TextField("🗣", text: $emoji)
                            .multilineTextAlignment(.trailing)
                            .frame(width: 60)
                            .onChange(of: emoji) { _, new in
                                emoji = new.isEmpty ? "" : String(new.prefix(1))
                            }
                    }
                }
                Section(L10n.voiceColorField(settings.language)) {
                    WrapLayout(spacing: 12) {
                        ForEach(VoiceColor.allCases) { c in
                            Circle()
                                .fill(c.tint)
                                .frame(width: 34, height: 34)
                                .overlay(
                                    Circle().strokeBorder(.primary,
                                        lineWidth: c == color ? 3 : 0)
                                )
                                .onTapGesture { color = c }
                                .accessibilityLabel(c.rawValue)
                                .accessibilityAddTraits(c == color ? [.isSelected] : [])
                        }
                    }
                    .padding(.vertical, 4)
                }
                if existing != nil {
                    Section {
                        Button(role: .destructive) {
                            showDeleteConfirm = true
                        } label: {
                            Text(L10n.deleteVoice(settings.language))
                        }
                    }
                }
            }
            .navigationTitle(existing == nil
                             ? L10n.newVoice(settings.language)
                             : existing!.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(L10n.cancel(settings.language)) { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button(L10n.done(settings.language)) {
                        Task { await save() }
                    }
                    .disabled(!canSave)
                }
            }
            .confirmationDialog(L10n.deleteVoice(settings.language),
                                isPresented: $showDeleteConfirm, titleVisibility: .visible) {
                Button(L10n.deleteAction(settings.language), role: .destructive) {
                    if let existing { Task { await store.deleteVoice(id: existing.id); dismiss() } }
                }
                Button(L10n.cancel(settings.language), role: .cancel) {}
            }
        }
        .onAppear {
            if let existing {
                name = existing.name; emoji = existing.emoji; color = existing.color
            }
        }
    }

    @MainActor
    private func save() async {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let finalEmoji = emoji.isEmpty ? "🗣" : String(emoji.prefix(1))
        if let existing {
            let updated = InnerVoice(id: existing.id, name: trimmed, emoji: finalEmoji, color: color)
            await store.updateVoice(updated)
            onSaved?(existing.id)
        } else {
            let v = InnerVoice(name: trimmed, emoji: finalEmoji, color: color)
            await store.addVoice(v)
            onSaved?(v.id)
        }
        dismiss()
    }
}
```

- [ ] **Step 2: Сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): VoiceEditor (name/emoji/curated palette, delete)"
```

---

## Task 6: `RatingScale` + `CaptureSheet` (лист фиксации)

**Files:** Modify `ContentView.swift`.

- [ ] **Step 1: Добавить `RatingScale` (опциональный tap-scale 0–10)**

```swift
// MARK: - RatingScale (optional 0–10 tap-scale)

struct RatingScale: View {
    @Binding var value: Int?          // nil = не задано
    let tint: Color

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0...10, id: \.self) { i in
                Circle()
                    .fill(fillColor(for: i))
                    .frame(height: 22)
                    .frame(maxWidth: .infinity)
                    .frame(height: 44)            // hit-area повыше для пальца
                    .contentShape(Rectangle())
                    .onTapGesture {
                        // Повторный тап по текущему значению — сброс в nil.
                        value = (value == i) ? nil : i
                    }
            }
        }
        .accessibilityElement()
        .accessibilityValue(value.map { "\($0)" } ?? "—")
    }

    private func fillColor(for i: Int) -> Color {
        guard let value else { return Color.secondary.opacity(0.25) }
        return i <= value ? tint : Color.secondary.opacity(0.25)
    }
}
```

- [ ] **Step 2: Добавить `CaptureSheet`**

```swift
// MARK: - CaptureSheet

struct CaptureSheet: View {
    @Environment(AppSettings.self) private var settings
    @Environment(VoicesStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var text: String = ""
    @State private var selectedVoiceID: UUID?
    @State private var emotion: Int?
    @State private var presence: Int?
    @State private var showNewVoice = false

    private var selectedVoice: InnerVoice? {
        store.voices.first { $0.id == selectedVoiceID }
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(L10n.fieldThought(settings.language)) {
                    TextField(L10n.fieldThought(settings.language), text: $text, axis: .vertical)
                        .lineLimit(2...6)
                }

                Section(L10n.fieldVoice(settings.language)) {
                    WrapLayout(spacing: 8) {
                        ForEach(store.voices) { v in
                            voiceChip(v)
                        }
                        Button { showNewVoice = true } label: {
                            Text("＋").font(.body.weight(.semibold))
                                .padding(.horizontal, 12).padding(.vertical, 7)
                                .overlay(Capsule().strokeBorder(.secondary))
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.vertical, 4)
                }

                Section {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.scaleEmotion(settings.language)).font(.subheadline)
                        RatingScale(value: $emotion, tint: .accentColor)
                        poles(L10n.emotionLow(settings.language), L10n.emotionHigh(settings.language))
                    }
                    VStack(alignment: .leading, spacing: 6) {
                        Text(L10n.scalePresence(settings.language)).font(.subheadline)
                        RatingScale(value: $presence, tint: .green)
                        poles(L10n.presenceLow(settings.language), L10n.presenceHigh(settings.language))
                    }
                }
            }
            .navigationTitle(L10n.captureTitle(settings.language))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button(L10n.cancel(settings.language)) { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button(L10n.done(settings.language)) {
                        Task { await save() }
                    }
                    .disabled(selectedVoiceID == nil)
                }
            }
            .sheet(isPresented: $showNewVoice) {
                VoiceEditor(existing: nil) { newID in selectedVoiceID = newID }
            }
        }
        .onAppear {
            // Пред-выбор последнего использованного голоса (по самому свежему моменту),
            // если он ещё в ростере; иначе первый голос, если есть.
            if selectedVoiceID == nil {
                let lastUsed = store.moments.first?.voiceID
                if let lastUsed, store.voices.contains(where: { $0.id == lastUsed }) {
                    selectedVoiceID = lastUsed
                } else {
                    selectedVoiceID = store.voices.first?.id
                }
            }
        }
    }

    @ViewBuilder
    private func voiceChip(_ v: InnerVoice) -> some View {
        let selected = v.id == selectedVoiceID
        Button { selectedVoiceID = v.id } label: {
            Text("\(v.emoji) \(v.name)")
                .font(.subheadline)
                .padding(.horizontal, 12).padding(.vertical, 7)
                .background(
                    Capsule().fill(v.color.tint.opacity(selected ? 0.30 : 0.18))
                )
                .overlay(
                    Capsule().strokeBorder(v.color.tint, lineWidth: selected ? 1.5 : 0)
                )
        }
        .buttonStyle(.plain)
    }

    @ViewBuilder
    private func poles(_ low: String, _ high: String) -> some View {
        HStack {
            Text(low); Spacer(); Text(high)
        }
        .font(.caption2).foregroundStyle(.secondary)
    }

    @MainActor
    private func save() async {
        guard let v = selectedVoice else { return }   // снимок свежим из стора
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let moment = CompassionMoment(
            voiceID: v.id,
            voiceName: v.name, voiceEmoji: v.emoji, voiceColor: v.color,
            text: trimmed.isEmpty ? nil : trimmed,
            emotion: emotion, presence: presence
        )
        await store.addMoment(moment)
        dismiss()
    }
}
```

- [ ] **Step 3: Сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): RatingScale + CaptureSheet (optional ratings, last-voice preselect)"
```

---

## Task 7: `VoicesView` (главный экран, раскладка B) + `MomentRow`

**Files:** Modify `ContentView.swift` — **заменить** стаб `VoicesView` из Task 4.

- [ ] **Step 1: Заменить стаб полноценным экраном + строкой истории**

```swift
// MARK: - Voices tab (main)

struct VoicesView: View {
    @Environment(AppSettings.self) private var settings
    @Environment(VoicesStore.self) private var store

    @State private var showCapture = false
    @State private var editingVoice: InnerVoice?
    @State private var showNewVoiceFromEmpty = false

    // Счётчики — derived, НЕ кэш в @State.
    private var voicesWithCounts: [(voice: InnerVoice, count: Int)] {
        store.voices.compactMap { v in
            let n = store.moments.filter { $0.voiceID == v.id }.count
            return n > 0 ? (v, n) : nil
        }
    }

    var body: some View {
        Group {
            if !store.didLoad {
                Color.clear
            } else if store.voices.isEmpty {
                ContentUnavailableView {
                    Label(L10n.voicesEmptyTitle(settings.language), systemImage: "quote.bubble")
                } description: {
                    Text(L10n.voicesEmptyDesc(settings.language))
                } actions: {
                    Button(L10n.createVoiceCTA(settings.language)) {
                        showNewVoiceFromEmpty = true
                    }
                }
            } else {
                content
            }
        }
        .navigationTitle(L10n.tabVoices(settings.language))
        .safeAreaInset(edge: .bottom) {
            if store.didLoad && !store.voices.isEmpty {
                Button {
                    showCapture = true
                } label: {
                    Label(L10n.captureButton(settings.language), systemImage: "plus")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .padding(.horizontal)
                .padding(.bottom, 6)
            }
        }
        .sheet(isPresented: $showCapture) {
            CaptureSheet()
        }
        .sheet(item: $editingVoice) { v in
            VoiceEditor(existing: v)
        }
        .sheet(isPresented: $showNewVoiceFromEmpty) {
            VoiceEditor(existing: nil)
        }
        .sensoryFeedback(.success, trigger: store.lastAddedID)
    }

    @ViewBuilder
    private var content: some View {
        List {
            if !voicesWithCounts.isEmpty {
                Section {
                    WrapLayout(spacing: 8) {
                        ForEach(voicesWithCounts, id: \.voice.id) { item in
                            Button { editingVoice = item.voice } label: {
                                Text("\(item.voice.emoji) \(item.voice.name) · \(item.count)")
                                    .font(.footnote)
                                    .padding(.horizontal, 10).padding(.vertical, 6)
                                    .background(Capsule().fill(item.voice.color.tint.opacity(0.18)))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
                }
            }

            if store.moments.isEmpty {
                Section {
                    Text(L10n.momentsEmptyHint(settings.language))
                        .foregroundStyle(.secondary)
                }
            } else {
                Section {
                    ForEach(store.moments) { m in
                        NavigationLink {
                            MomentDetail(moment: m)
                        } label: {
                            MomentRow(moment: m, uiLanguage: settings.language)
                        }
                        .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                            Button(role: .destructive) {
                                Task { await store.deleteMoment(id: m.id) }
                            } label: {
                                Label(L10n.deleteAction(settings.language), systemImage: "trash")
                            }
                        }
                    }
                }
            }
        }
    }
}

struct MomentRow: View {
    let moment: CompassionMoment
    let uiLanguage: AppLanguage

    private static let ruLocale = Locale(identifier: "ru_RU")
    private static let enLocale = Locale(identifier: "en_US")
    private var locale: Locale { uiLanguage == .russian ? Self.ruLocale : Self.enLocale }

    var body: some View {
        HStack(spacing: 10) {
            RoundedRectangle(cornerRadius: 2)
                .fill(moment.voiceColor.tint)
                .frame(width: 4)
            VStack(alignment: .leading, spacing: 3) {
                if let text = moment.text, !text.isEmpty {
                    Text(text).font(.body).lineLimit(2)
                } else {
                    Text(L10n.noWords(uiLanguage)).font(.body).italic()
                        .foregroundStyle(.secondary)
                }
                Text(metaLine).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private var metaLine: String {
        var parts = ["\(moment.voiceEmoji) \(moment.voiceName)"]
        if let e = moment.emotion { parts.append("\(L10n.emotionShort(uiLanguage)) \(e)") }
        if let p = moment.presence { parts.append("\(L10n.presenceShort(uiLanguage)) \(p)") }
        parts.append(moment.createdAt.formatted(
            Date.RelativeFormatStyle(presentation: .named).locale(locale)))
        return parts.joined(separator: " · ")
    }
}
```

- [ ] **Step 2: Сборка** → `** BUILD SUCCEEDED **`. Ручной прогон: создать голос, зафиксировать момент, увидеть его в истории и чип-сводку.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): VoicesView main screen (summary chips, history, capture button)"
```

---

## Task 8: `MomentDetail`

**Files:** Modify `ContentView.swift`.

- [ ] **Step 1: Добавить экран деталей**

```swift
// MARK: - MomentDetail

struct MomentDetail: View {
    @Environment(AppSettings.self) private var settings
    @Environment(VoicesStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let moment: CompassionMoment

    private static let ruLocale = Locale(identifier: "ru_RU")
    private static let enLocale = Locale(identifier: "en_US")
    private var locale: Locale { settings.language == .russian ? Self.ruLocale : Self.enLocale }

    var body: some View {
        Form {
            Section {
                HStack(spacing: 8) {
                    Text(moment.voiceEmoji)
                    Text(moment.voiceName)
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(Capsule().fill(moment.voiceColor.tint.opacity(0.18)))
                }
            }
            if let text = moment.text, !text.isEmpty {
                Section(L10n.fieldThought(settings.language)) { Text(text) }
            }
            Section {
                if let e = moment.emotion {
                    LabeledContent(L10n.scaleEmotion(settings.language), value: "\(e) / 10")
                }
                if let p = moment.presence {
                    LabeledContent(L10n.scalePresence(settings.language), value: "\(p) / 10")
                }
                LabeledContent(L10n.momentTitle(settings.language),
                               value: moment.createdAt.formatted(
                                Date.RelativeFormatStyle(presentation: .named).locale(locale)))
            }
            Section {
                Button(role: .destructive) {
                    Task { await store.deleteMoment(id: moment.id); dismiss() }
                } label: {
                    Text(L10n.deleteAction(settings.language))
                }
            }
        }
        .navigationTitle(L10n.momentTitle(settings.language))
        .navigationBarTitleDisplayMode(.inline)
    }
}
```

- [ ] **Step 2: Сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "feat(voices): MomentDetail screen"
```

---

## Task 9: Финальная верификация + CHANGELOG

**Files:** Modify `CHANGELOG.md` (репо `cogi_ios`).

- [ ] **Step 1: Добавить в `[Unreleased]` → `### Added`**

```markdown
- New **Voices** tab (second, after Analyze) for self-compassion practice: quickly log a
  moment when an inner critic ("voice") shows up. Voices are user-created (name + emoji +
  curated color). A moment = optional thought text + chosen voice + two optional 0–10
  tap-scales (Emotion intensity, Presence). Local-only, no AI. History list with per-voice
  color and pattern-count chips. Capture sheet pre-selects the last-used voice for one-tap logging.
```

- [ ] **Step 2: Полная сборка** → `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Ручная верификация на устройстве (пользователь)**
  - Создать голос «Стыдобист» (эмодзи + цвет), затем «Тревожник».
  - Зафиксировать момент: текст + голос + обе оценки → «Готово»; появился в истории, чип-сводка `· 1`.
  - Зафиксировать без слов и без оценок (только голос) → «(без слов)», без чисел оценок в строке.
  - Открыть лист повторно → пред-выбран последний голос; сейв в один тап.
  - Свайп-делит момента; тап → детали → удаление.
  - Переименовать голос → старые моменты показывают прежнее имя (снимок), новые — новое.
  - Удалить голос с моментами → моменты в истории целы, чип-сводка пропала.
  - Перезапустить приложение → данные на месте; язык RU/EN переключает чрому, даты в нужной локали.
  - Вкладка «Анализ»/«Сохранено» не затронуты, `entries.json` цел.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/cogi_ios && git add -A && git commit -m "docs: changelog — Voices self-compassion tab"
```

---

## Финал

- [ ] Слить ветку `feature/voices-tab` (или оставить для ревью — см. superpowers:finishing-a-development-branch).
- [ ] Обновить память `ios-app-in-progress` (фича выкатана).
