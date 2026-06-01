# Вкладка «Голоса» — практика самосострадания (iOS) — Design

**Дата:** 2026-06-01 (ревью-правки 2026-06-02)
**Клиент:** Cogi (iOS, SwiftUI), репозиторий `~/Projects/cogi_ios`, файл `Cogi/Cogi/ContentView.swift`

## Цель

Дать пользователю **за 3–5 секунд** зафиксировать момент, когда проснулся «внутренний голос»
(критик), чтобы тренировать автоматическое замечание. Механизм — КПТ self-monitoring +
экстернализация/дефузия (назвать критика как сущность: «Стыдобист», «Тревожник» — отделить
голос от себя). Главный принцип — **минимум трения**: чем меньше действий до записи, тем чаще
практика и быстрее формируется навык.

v1 — **чистая фиксация + просмотр истории**. Без AI, без бэкенда, без шага «ответа/рефрейма».

## Ключевые решения

| Параметр | Значение |
|---|---|
| Вкладка | Вторая, сразу после «Анализ» (порядок: Анализ → Голоса → Сохранено → Настройки). «Голоса» (EN «Voices»), SF Symbol `quote.bubble` |
| Сущность-голос | Пользовательская, CRUD в приложении: имя + эмодзи + цвет-пресет |
| Поток фиксации | Модальный `Sheet`: текст (опц.) → выбор голоса → 2 оценки (опц.) → «Готово» |
| Оценки | «Сила эмоции» и «Присутствие» — **tap-scale 0–10, опциональные** (`Int?`, не тронул = не записано) |
| Полярность | Эмоция: выше = сильнее (хуже). Присутствие: выше = на опоре (лучше). 0 захлёстывает → 10 можешь применить навыки |
| Текст мысли | Опционален (можно записать момент без слов) |
| Цвет голоса | Курируемая палитра (~8 пресетов), заливка `color.opacity(0.18)` + семантический текст — контраст держится в обеих темах и для дальтоников |
| Пред-выбор | При открытии листа пред-выбран последний использованный голос → возможен 1-тап сейв (открыл → «Готово») |
| Главный экран | Раскладка B: чипы-сводка + история + закреплённая кнопка «Зафиксировать» |
| Кнопки | Низ главного «＋ Зафиксировать» (открыть новую) · в листе «Готово» (сохранить) / «Отмена» |
| Хранение | Новый `VoicesStore`, **один файл** `voices_state.json` = `{voices, moments}`, независимо от `entries.json` |
| AI/бэкенд | Нет (вне scope) |
| UI-kit | Только стандартный SwiftUI |

## Модель данных

Все Codable-типы пишутся с **явными `CodingKeys` + `decodeIfPresent` + дефолтами с самого начала** —
чтобы будущий апдейт модели не уронил декод единственной копии журнала (у `moments` нет источника
правды, в отличие от `entries.json` с бэкендом). Паттерн — как `SavedThought` (ContentView.swift
178–200).

```swift
// Курируемая палитра — пресет, а не произвольный hex: гарантирует валидный цвет и контраст-пару.
enum VoiceColor: String, Codable, CaseIterable, Identifiable {
    case rose, amber, sky, violet, teal, lime, slate, coral
    var id: String { rawValue }
    var tint: Color { /* semantic Color по кейсу */ }
    static let fallback: VoiceColor = .slate
    // декод неизвестного/отсутствующего rawValue → .fallback (не throw)
}

struct InnerVoice: Codable, Identifiable, Hashable {
    let id: UUID
    var name: String
    var emoji: String           // ровно 1 grapheme; пусто → fallback "🗣" (валидация на вводе)
    var color: VoiceColor
    // явные CodingKeys + decodeIfPresent(name ?? "", emoji ?? "🗣", color ?? .fallback)
}

struct CompassionMoment: Codable, Identifiable {
    let id: UUID
    let createdAt: Date
    let voiceID: UUID           // для группировки/сводки-счётчиков
    // снимок голоса на момент записи — история целая при переименовании/удалении голоса
    let voiceName: String
    let voiceEmoji: String
    let voiceColor: VoiceColor
    let text: String?           // опционально; на сохранении "" → nil (trimmed)
    let emotion: Int?           // 0–10, опционально (tap-scale; не тронул → nil)
    let presence: Int?          // 0–10, опционально. Полярность: выше = на опоре
    // явные CodingKeys + decodeIfPresent для voiceColor/text/emotion/presence
}

// Контейнер persist — один файл, одна точка отказа, нет гонки между двумя файлами.
struct VoicesState: Codable {
    var voices: [InnerVoice] = []
    var moments: [CompassionMoment] = []
    // decodeIfPresent для обоих массивов → [] (forward-compat)
}
```

**Снимок vs ссылка (гибрид):** момент хранит и `voiceID`, и денормализованный снимок
(`voiceName/Emoji/Color`). Рендер истории — из снимка (как `entries.json` хранит искажения инлайн):
переименование/смена цвета голоса влияет только на **будущие** записи, прошлое — «как было».
Удаление голоса не рушит историю. Снимок резолвится **свежим на «Готово»** из `store.voices`
(не кэшируется при тапе на чип — иначе инлайн-правка голоса в открытом листе не попадёт в запись).

## Хранение

```swift
@Observable @MainActor
final class VoicesStore {
    private(set) var voices: [InnerVoice] = []
    private(set) var moments: [CompassionMoment] = []   // всегда createdAt desc (в load И в addMoment)
    private(set) var didLoad = false                    // чтобы empty-state не мигал до загрузки

    // один файл voices_state.json в URL.documentsDirectory
    // makeCoder() как EntryStore (.iso8601, .prettyPrinted, .sortedKeys)
    // load()/persist() через Task.detached, write(options: [.atomic])

    // API (мутации только тут, не в локальном @State вью):
    func load() async
    func addVoice(_ v: InnerVoice) async
    func updateVoice(_ v: InnerVoice) async
    func deleteVoice(id: UUID) async       // голос из ростера; моменты остаются (снимок)
    func addMoment(_ m: CompassionMoment) async
    func deleteMoment(id: UUID) async
    private func persist() async           // пишет ВЕСЬ VoicesState из одного snapshot
}
```

**Сохранность данных (из код-ревью, обязательно):**
- **Поэлементный декод `moments`** — одна битая запись отбрасывается, а не роняет весь массив
  (декод в промежуточный «failable» wrapper, битые — пропускаем). Голоса и моменты — единственная
  копия, тихий wipe всего файла неприемлем.
- **Не перезаписывать файл, если `load()` дал пусто при непустом исходном `data`** — иначе
  следующий `persist()` затрёт шанс на восстановление.
- Один файл `VoicesState` → нет параллельных detached-записей двух файлов, нет рассинхрона
  voices↔moments.

**Интеграция в `ContentView`:**
- `@State private var voicesStore = VoicesStore()` в `ContentView` (НЕ в дочерних вью — иначе
  пересоздание при переключении табов и потеря данных). Прокидывается `.environment(voicesStore)`.
- Дочерние вью читают через `@Environment(VoicesStore.self)`.
- Загрузка **параллельно** с entries: `async let a = store.load(); async let b = voicesStore.load(); _ = await (a, b)`.

## Экраны

### Главный (`VoicesView`, раскладка B)
- Заголовок «Голоса».
- **Ряд чипов-сводки**: для каждого голоса ростера с **N ≥ 1** — `эмодзи имя · N`, где
  N = `moments.filter { $0.voiceID == v.id }.count` (**derived computed, НЕ кэш в @State** — иначе
  derived-state wipe, известная грабля проекта). Чипы с N=0 скрыты (не шумят). Стиль чипа —
  `color.tint.opacity(0.18)` фон + семантический текст. Тап по чипу → редактор голоса. Это «паттерны».
- **История** (`List`): строки моментов, цветная полоска слева = `voiceColor.tint` (из снимка).
  Строка: сниппет текста (или «без слов» курсивом, если `text == nil`), мета
  `эмодзи имя · relative-дата`; оценки показываются только если заданы (`эмоция 7` / `присутствие 3`;
  отсутствующая — не показывается). Relative-дата — `Date.RelativeFormatStyle(.named)` с локалью по
  `settings.language` (как `SavedRow` 1114–1128). Свайп-делит → `store.deleteMoment(id:)`
  (`allowsFullSwipe: false`, как «Сохранено»).
- Внизу закреплена **«＋ Зафиксировать»** (`.safeAreaInset(edge: .bottom)`), открывает лист.
- Пустые состояния (только после `didLoad`): нет голосов → «Создай первый голос» (CTA → редактор
  нового голоса); есть голоса, нет моментов → лёгкая подсказка зафиксировать первый.

### Лист фиксации (`CaptureSheet`, модальный)
- Презентация `.sheet(isPresented:)`. Весь черновик — **один** `@State private var draft`
  (`text`, `selectedVoiceID: UUID?`, `emotion: Int?`, `presence: Int?`), наружу — `CompassionMoment`
  через callback на «Готово». Не пробрасывать 4 биндинга.
- `NavigationStack`: слева «Отмена», справа «Готово».
- `TextEditor` «Что произошло / какая мысль» — опционально.
- **Выбор голоса**: ряд чипов-кнопок (`WrapLayout`), выбранный подсвечен своим тоном; «＋» открывает
  редактор нового голоса инлайн. **Пред-выбран последний использованный голос** (по самому свежему
  моменту), если есть.
- **Оценки** — две tap-scale `0…10` (ряд из 11 точек-кнопок), **опциональные**: пока не тапнул —
  «не задано», в модель идёт `nil`. Подписи полюсов: эмоция «слабо → сильно»; присутствие
  «захлёстывает → на опоре».
- **Сохранение**: «Готово» активно, когда выбран голос (`selectedVoiceID != nil`). Текст и оценки не
  обязательны. Снимок голоса резолвится свежим из `store.voices` на «Готово». При пустом ростере
  ряд показывает только «＋» — пока нет голоса, сохранить нельзя. Хаптика `.success` по `lastSavedId`
  (UUID, не по count — иначе delete тоже buzzнет).

### Редактор голоса (`VoiceEditor`, модальный/пуш)
- `TextField` имя.
- `TextField` эмодзи — на вводе `String(input.prefix(1))`, пусто → «🗣» (не пустая строка в модель).
- **Палитра**: ряд из 8 пресет-свотчей (`VoiceColor.allCases`), выбранный с обводкой. Без `ColorPicker`.
- Удаление существующего (через `confirmationDialog`): голос убирается из ростера; его моменты в
  истории остаются (снимок), чип-сводка пропадает (осознанное решение v1 — удалил голос = закрыл тему).

### Детали момента (`MomentDetail`)
- Просмотр: голос (снимок), текст, эмоция/присутствие (если заданы), дата. Удаление момента.

## Локализация
- Чрома через `enum L10n` (RU/EN). Новые ключи: `tabVoices`, `captureTitle`, `fieldThought`,
  `fieldVoice`, `scaleEmotion`, `scalePresence`, `emotionLow`/`emotionHigh`,
  `presenceLow`/`presenceHigh`, `newVoice`, `voiceName`, `voiceEmoji`, `voiceColor`, `deleteVoice`,
  `capture`, `noWords`, empty-state строки.
- Имена голосов — пользовательские, **не** локализуются.

## Вне scope v1
AI-анализ момента; шаг сострадательного ответа/рефрейма; «добрый контр-голос» у сущности;
напоминания/виджеты; графики динамики во времени; экспорт; long-press по чипу → быстрый повтор-лог
(возможное улучшение трения позже); чипы-сводка по удалённым голосам.

## Архитектурные заметки (консистентность с существующим кодом)
- Файл один — `ContentView.swift` (конвенцию не ломаем), новые типы/вью туда же.
- TabView получает новую вкладку **вторым** элементом (между «Анализ» и «Сохранено»); tab label
  читает `settings.language` прямо в `body` (иначе теряется @Observable-tracking).
- Паттерн стора/Codable-бэккомпата — у `EntryStore`/`SavedThought`, **но строже**: forward-compat
  `decodeIfPresent` с самого начала + поэлементный декод moments + no-wipe-guard.
- tap-scale хранит `Int?`; если переиспользовать слайдер где-то — `Slider` отдаёт `Double`,
  конвертить `Int(value.rounded())`.

## Диспозиции ревью (что учтено)
Код-ревью (🔴): forward-compat Codable, поэлементный декод moments + no-wipe-guard, один файл вместо
двух. (🟡): derived-сводка не в @State, полярность presence в доке, draft одним @State + callback,
снимок свежим на «Готово», параллельный load + didLoad, @Environment в детях, API стора, text ""→nil,
сортировка в load и addMoment, locale relative-даты. UI-ревью: tap-scale + опциональные оценки
(нет фантомных 5/5), курируемая палитра + opacity-заливка (контраст/дальтоники), пред-выбор
последнего голоса, раскладка B подтверждена.
