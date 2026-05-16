# Distortion Feedback (👍/👎) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user mark each detected cognitive distortion 👍/👎 (👎 with a reason), persist verdicts into saved entries so the existing JSON export becomes an eval set — preceded by a reproduce-first fix of backlog bug #3 (phantom re-analysis).

**Architecture:** iOS-only, single file. Pre-step 0 instruments `runAnalysis`, the user reproduces the phantom in the simulator, then a signature guard (idempotent network call) plus a settled-thought stable id remove spurious re-analysis. The feature then adds a small feedback model carried on `Thought` and `SavedThought`, a refactored `DistortionCard` with rating controls, and an `EntryStore` mutator so ratings persist and export automatically.

**Tech Stack:** Swift 5.10, SwiftUI, `@Observable`, iOS 17, Xcode 16. No backend changes. No XCTest target exists — verification is `xcodebuild` build + manual simulator check, matching this codebase's established practice.

---

## Conventions for every task

- **Single file:** all code changes are in
  `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift`
  unless stated otherwise.
- **Build check command:**
  ```bash
  cd ~/Projects/abc_app_ios/CBTAnalyzer && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' build 2>&1 | tail -5
  ```
  Expected: a line containing `** BUILD SUCCEEDED **`.
- **Commit:** the iOS code lives in its own git repo at
  `~/Projects/abc_app_ios`. Commit there (not in `abc_app`).
- Every commit message ends with:
  `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`
- Simulator steps are performed by the user; the plan states the exact
  action and the exact expected observation.
- **Line numbers are approximate against the pristine file.** Earlier
  tasks insert lines, so every later `~line N` / `lines X–Y` reference
  drifts. **Always locate an edit by its quoted textual anchor and
  enclosing type/function name, never by absolute line number.** Where a
  task says "replace lines X–Y", it means "replace the named construct in
  full".

## File responsibility map

`ContentView.swift` is the whole app. Within it, the regions touched:

- **Domain models** (`Distortion`, `Thought`, `AnalysisInput`) — add feedback
  types + `Thought.feedback` + `Thought.lastAnalyzedSignature`.
- **Persistence models** (`SavedThought`, `SavedEntry`) — `SavedThought`
  gains `feedback` with backward-compatible `Codable`.
- **`EntryStore`** — add `updateFeedback(...)`.
- **`L10n`** — add feedback strings.
- **`AnalyzeView`** — committed-context snapshots; pass into `ThoughtRow`.
- **`ThoughtRow` / `runAnalysis`** — signature guard, settled-id, feedback
  binding, reset-on-real-reanalysis.
- **`DistortionCard`** — de-Button refactor + rating UI.
- **`SavedListView` / `SavedDetailView`** — store-backed detail, ratable
  cards persisting via `EntryStore`.

---

# Pre-step 0 — Bug #3: phantom re-analysis (reproduce first)

### Task 1: Add diagnostic logging to `runAnalysis` (no behaviour change)

**Files:**
- Modify: `ContentView.swift` — top of file (add import/logger) and
  `ThoughtRow.runAnalysis()` (~line 521).

- [ ] **Step 1: Add a logger near the top of the file**

Directly after `import SwiftUI` (line 1), add:

```swift
import OSLog

private let analysisLog = Logger(subsystem: "com.bulsir.cbtanalyzer", category: "analysis")
```

- [ ] **Step 2: Log every entry into `runAnalysis`**

In `runAnalysis()`, as the very first lines inside the method (before
`let trimmed = ...`), insert. `status` is logged as a **coarse case name
only** — never the associated error string (it can echo backend response
bodies; the analyzed thought is private mental-health content). `hashValue`
is per-process seeded, so only compare hashes **within one app run**, never
across launches:

```swift
        let dbgText = thought.text.trimmingCharacters(in: .whitespacesAndNewlines)
        let statusName: String
        switch thought.status {
        case .idle:    statusName = "idle"
        case .loading: statusName = "loading"
        case .error:   statusName = "error"
        }
        analysisLog.debug("""
        runAnalysis id=\(String(thought.id.uuidString.prefix(4)), privacy: .public) \
        textHash=\(dbgText.hashValue, privacy: .public) \
        sitHash=\(self.situation.hashValue, privacy: .public) \
        feelHash=\(self.feelings.hashValue, privacy: .public) \
        didAnalyze=\(thought.didAnalyze, privacy: .public) \
        status=\(statusName, privacy: .public)
        """)
```

- [ ] **Step 3: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "debug: instrument runAnalysis to diagnose phantom re-analysis (bug #3)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Reproduce the phantom and confirm the cause (diagnostic gate)

**Files:** none (observation only).

This task produces a decision: **Hypothesis A**, **B**, or **both**. Record
the answer in the commit message of Task 5.

- [ ] **Step 1: Launch the app on the simulator with the console open**

Run from Xcode (⌘R) on iPhone 16 so the Xcode console shows `analysisLog`
lines, or run:
```bash
cd ~/Projects/abc_app_ios/CBTAnalyzer && xcodebuild -scheme CBTAnalyzer -destination 'platform=iOS Simulator,name=iPhone 16' -derivedDataPath /tmp/cbtdd build 2>&1 | tail -3
xcrun simctl boot "iPhone 16" 2>/dev/null; open -a Simulator
xcrun simctl install "iPhone 16" $(find /tmp/cbtdd -name CBTAnalyzer.app -type d | head -1)
xcrun simctl launch --console-pty "iPhone 16" com.bulsir.cbtanalyzer
```
Console must stream `runAnalysis id=...` lines.

- [ ] **Step 2: Scenario A — context fan-out**

Type a thought, wait for the distortion cards to appear. Note its
`id=XXXX`. Now type several characters into "What happened?". Watch the
console. **Hypothesis A confirmed if:** `runAnalysis` fires for the
thought's `id=XXXX` again (with `didAnalyze=true`) although you never
touched the thought field.

- [ ] **Step 3: Scenario B — `.task` lifecycle**

Type a thought, wait for cards. Touch nothing else. Switch to the "Saved"
tab, then back to "Analyze". Then background the app (Home), reopen.
**Hypothesis B confirmed if:** `runAnalysis` fires for the same `id=XXXX`
after the tab switch and/or after foregrounding, with identical
`textHash`/`sitHash`/`feelHash` to the prior run.

- [ ] **Step 4: Record the verdict**

Write down which of A / B / both reproduced. This decides which fixes in
Tasks 3–4 are load-bearing (apply both regardless — see note — but the
verdict is recorded for the backlog memory and Task 5 commit).

> Note: Task 3 (signature guard) is applied **unconditionally** — it is the
> robust core and a safety net even if only A reproduced. Task 4
> (settled-id) is applied unconditionally too because the spec's end state
> recommends both; it additionally removes wasteful debounce churn. The
> diagnostic still matters: it confirms the phantom is real and tells us
> which scenario to use as the regression check in Task 5.

---

### Task 3: Idempotent signature guard (covers Hypothesis B + any id thrash)

**Files:**
- Modify: `ContentView.swift` — `struct Thought` (~line 17) and
  `runAnalysis()` (~line 521).

- [ ] **Step 1: Add a last-analyzed signature to `Thought`**

In `struct Thought`, add a stored property after `var didAnalyze`:

```swift
    var didAnalyze: Bool = false   // true только после успешного анализа (включая success-empty)
    var lastAnalyzedSignature: String? = nil   // вход, для которого уже сходили в сеть
```

- [ ] **Step 2: Compute the signature and short-circuit unchanged re-runs**

**Do NOT delete the Task 1 diagnostic block.** Leave the `dbgText` /
`statusName` / `analysisLog.debug(...)` lines added in Task 1 exactly where
they are (the first lines of `runAnalysis()`). Replace **from the line
`let trimmed = ...` (immediately after that diagnostic block) through the
`thought.status = .loading` line** with the following. The guard is a
**pure function of the input signature** — independent of `didAnalyze`,
`status`, and the `.task` id. This is the spec's contract: `/analyze` fires
iff the analyzed input genuinely changed, regardless of why `.task` re-ran.

```swift
        let trimmed = thought.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            thought.distortions = []
            thought.status = .idle
            thought.didAnalyze = false
            thought.lastAnalyzedSignature = nil
            return
        }

        let signature = "\(trimmed)\u{1F}\(situation)\u{1F}\(feelings)\u{1F}\(settings.language.rawValue)"

        // .task restarts for reasons unrelated to input (tab switch,
        // foreground, isSettled flipping the id). Network fires ONLY when the
        // signature changed. An errored input is retried only when the user
        // edits it (→ new signature), never on a bare lifecycle restart.
        if thought.lastAnalyzedSignature == signature { return }

        do {
            try await Task.sleep(for: .milliseconds(1500))
        } catch {
            return
        }

        thought.status = .loading
```

**Build-order note:** Task 3 must NOT reference `thought.feedback` — that
property is introduced only in Task 6. Pre-step 0 (Tasks 1–5) stays a
standalone, independently-shippable bug fix. All `feedback`-reset wiring is
added later in Task 10 Step 3 (after Task 6 defines the type).

- [ ] **Step 3: Record the signature on success AND on error**

Replace the whole `do/catch` of `runAnalysis()` with the following. The
signature is stored on **both** success and error so an errored input is
not auto-retried on every lifecycle `.task` restart — only a real edit
(new signature) re-attempts. Cancel branches touch nothing.

```swift
        do {
            let distortions = try await BackendClient.shared.analyze(req)
            thought.distortions = distortions
            thought.status = .idle
            thought.didAnalyze = true         // включая success-empty
            thought.lastAnalyzedSignature = signature
        } catch is CancellationError {
            // не трогаем didAnalyze / lastAnalyzedSignature
        } catch let urlError as URLError where urlError.code == .cancelled {
            // не трогаем didAnalyze / lastAnalyzedSignature
        } catch {
            thought.status = .error(error.localizedDescription)
            thought.lastAnalyzedSignature = signature   // do not auto-retry same input on lifecycle
        }
```

- [ ] **Step 4: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 5: Simulator verification**

Reproduce Scenario B from Task 2 (type thought → wait for cards → switch to
Saved and back → background/foreground). **Expected:** the console shows
`runAnalysis` entered but it returns immediately — **no** new `/analyze`
network call, cards unchanged. Then add a word to the same thought:
**Expected:** `runAnalysis` proceeds, cards refresh (legitimate
re-analysis still works).

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "fix(#3): idempotent signature guard — no /analyze unless input changed

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: Settled-thought stable id (removes Hypothesis A churn)

**Files:**
- Modify: `ContentView.swift` — `AnalyzeView` (`@State` block ~line 322,
  `body` situation/feelings Sections ~line 344–360, the `ForEach($thoughts)`
  ~line 363), and `ThoughtRow` (`.task(id:)` ~line 512).

- [ ] **Step 1: Add committed-context snapshots to `AnalyzeView`**

In `AnalyzeView`, after `@State private var feelings = ""` (line 323) add:

```swift
    @State private var feelings = ""
    @State private var committedSituation = ""
    @State private var committedFeelings = ""
```

- [ ] **Step 2: Commit context only when its field loses focus**

On the root `Form` in `AnalyzeView.body`, add an `.onChange` for focus
transitions. Place it directly after `.scrollDismissesKeyboard(.interactively)`
(line 386):

```swift
            .scrollDismissesKeyboard(.interactively)
            .onChange(of: focusedField) { old, new in
                if old == .situation { committedSituation = situation }
                if old == .feelings  { committedFeelings  = feelings  }
                // Entering a thought field: ensure the latest context is
                // committed even if the user never blurred situation/feelings
                // (typed context → tapped straight into the thought).
                if case .thought = new {
                    committedSituation = situation
                    committedFeelings  = feelings
                }
            }
            .onAppear {
                committedSituation = situation
                committedFeelings  = feelings
            }
```

Without the `if case .thought = new` commit, a thought analyzed right
after typing context (without blurring it) would be sent with **stale
empty context** — a quality regression CLAUDE.md explicitly warns against.

- [ ] **Step 3: Pass committed context (not live) into `ThoughtRow`**

In the `ForEach($thoughts)` block, change the `ThoughtRow` init args from
`situation: situation, feelings: feelings` to:

```swift
                    ForEach($thoughts) { $thought in
                        ThoughtRow(
                            thought: $thought,
                            situation: committedSituation,
                            feelings: committedFeelings,
                            focusedField: $focusedField
                        )
                    }
```

- [ ] **Step 4: Make a settled row's analysis id independent of context**

In `ThoughtRow`, add a computed id and use it for `.task`. Replace the
`.task(id: AnalysisInput(...))` call (lines 512–517) with:

```swift
        .task(id: analysisID) {
            await runAnalysis()
        }
    }

    private var isSettled: Bool {
        thought.didAnalyze
            && thought.status == .idle
            && focusedField != .thought(thought.id)
    }

    private var analysisID: AnalysisInput {
        AnalysisInput(
            text: thought.text,
            situation: isSettled ? "" : situation,
            feelings:  isSettled ? "" : feelings,
            language:  settings.language.rawValue
        )
    }
```

(Delete the old inline `AnalysisInput(...)` argument; `.task(id: analysisID)`
replaces it. `runAnalysis()` already uses `situation`/`feelings` props —
now the committed values — so the request and signature stay consistent.)

- [ ] **Step 5: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 6: Simulator verification**

Reproduce Scenario A (type thought → wait for cards → type into "What
happened?"). **Expected:** the settled thought does **not** re-fire
`/analyze` on each keystroke (console shows no `runAnalysis` proceeding for
its id). Tap into the thought field and edit it: **Expected:** it
re-analyzes with the latest committed context.

- [ ] **Step 7: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "fix(#3): settled thought keeps stable analysis id; context committed on blur

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Gate the diagnostic log behind DEBUG; record verdict

**Files:**
- Modify: `ContentView.swift` — the logging block in `runAnalysis` (Task 1
  Step 2).

- [ ] **Step 1: Wrap the diagnostic log in `#if DEBUG`**

Surround the **entire** Task 1 diagnostic block — the `dbgText` line, the
`statusName` switch, and the `analysisLog.debug(""" ... """)` call — with
`#if DEBUG` / `#endif`. It is the contiguous block at the very top of
`runAnalysis()`, immediately above `let trimmed = ...`:

```swift
        #if DEBUG
        let dbgText = thought.text.trimmingCharacters(in: .whitespacesAndNewlines)
        let statusName: String
        switch thought.status {
        case .idle:    statusName = "idle"
        case .loading: statusName = "loading"
        case .error:   statusName = "error"
        }
        analysisLog.debug("""
        ... (unchanged body from Task 1 Step 2) ...
        """)
        #endif
```

- [ ] **Step 2: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Update the backlog memory**

Edit `/Users/bulat/.claude/projects/-Users-bulat-Projects-abc-app/memory/v1_improvement_backlog.md`:
mark item **3** as `[СДЕЛАНО 2026-05-16]` with a one-line note stating which
hypothesis (A / B / both) reproduced in Task 2 and that the fix is
signature-guard + settled-id.

- [ ] **Step 4: Commit (record the verdict here)**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "chore(#3): DEBUG-gate analysis diagnostics. Repro verdict: <A|B|both>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

# Feature — Distortion feedback 👍/👎

### Task 6: Feedback domain model + `Thought.feedback`

**Files:**
- Modify: `ContentView.swift` — after `struct Distortion` (line 9) and in
  `struct Thought` (~line 17).

- [ ] **Step 1: Add the feedback types**

Immediately after the closing `}` of `struct Distortion` (line 9), add:

```swift
enum DistortionVerdict: String, Codable, Hashable { case up, down }

enum DownReason: String, Codable, CaseIterable, Identifiable, Hashable {
    case wrongLabel       // не то искажение
    case weakExplanation  // слабое объяснение
    var id: String { rawValue }
}

struct DistortionFeedback: Codable, Hashable {
    var verdict: DistortionVerdict
    var reasons: Set<DownReason> = []   // пусто для .up; для .down — что не так
}
```

- [ ] **Step 2: Add the feedback map to `Thought`**

In `struct Thought`, after `var lastAnalyzedSignature: String? = nil` (added
in Task 3), add:

```swift
    var feedback: [String: DistortionFeedback] = [:]   // ключ = Distortion.name
```

- [ ] **Step 3: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: distortion feedback model + Thought.feedback

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: `SavedThought.feedback` with backward-compatible Codable

**Files:**
- Modify: `ContentView.swift` — `struct SavedThought` (~line 105).

- [ ] **Step 1: Replace `struct SavedThought` entirely**

Replace the whole `struct SavedThought { ... }` (lines 105–115) with:

```swift
struct SavedThought: Codable, Identifiable {
    let id: UUID
    let text: String
    let distortions: [Distortion]
    let feedback: [String: DistortionFeedback]

    init(id: UUID = UUID(),
         text: String,
         distortions: [Distortion],
         feedback: [String: DistortionFeedback] = [:]) {
        self.id = id
        self.text = text
        self.distortions = distortions
        self.feedback = feedback
    }

    private enum CodingKeys: String, CodingKey { case id, text, distortions, feedback }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try c.decode(UUID.self, forKey: .id)
        self.text = try c.decode(String.self, forKey: .text)
        self.distortions = try c.decode([Distortion].self, forKey: .distortions)
        // Old entries.json has no `feedback` key — default to empty.
        self.feedback = try c.decodeIfPresent([String: DistortionFeedback].self,
                                              forKey: .feedback) ?? [:]
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(id, forKey: .id)
        try c.encode(text, forKey: .text)
        try c.encode(distortions, forKey: .distortions)
        try c.encode(feedback, forKey: .feedback)
    }
}
```

- [ ] **Step 2: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Simulator verification — old data still loads**

If `entries.json` already has saved entries (from prior use), launch the
app and open the "Saved" tab. **Expected:** all previously saved entries
still appear (the missing `feedback` key decodes to `[:]`, no crash). If
there is no prior data, create an entry with an earlier build first, or
skip — the `decodeIfPresent` path is exercised by Task 13's export check.

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: SavedThought.feedback (backward-compatible Codable)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Localized feedback strings

**Files:**
- Modify: `ContentView.swift` — `enum L10n` (~line 64), before the
  `// Accessibility` comment (line 93).

- [ ] **Step 1: Add the strings**

Just before the `// Accessibility` comment inside `enum L10n`, add:

```swift
    // Feedback
    static func feedbackWhatsWrong(_ l: AppLanguage) -> String { l == .russian ? "Что не так?" : "What's wrong?" }
    static func reasonWrongLabel(_ l: AppLanguage)   -> String { l == .russian ? "Не то искажение" : "Wrong distortion" }
    static func reasonWeakExplanation(_ l: AppLanguage) -> String { l == .russian ? "Слабое объяснение" : "Weak explanation" }
    static func feedbackUpA11y(_ l: AppLanguage)     -> String { l == .russian ? "Верно" : "Correct" }
    static func feedbackDownA11y(_ l: AppLanguage)   -> String { l == .russian ? "Неверно" : "Incorrect" }

    static func reasonLabel(_ l: AppLanguage, _ r: DownReason) -> String {
        switch r {
        case .wrongLabel:      return reasonWrongLabel(l)
        case .weakExplanation: return reasonWeakExplanation(l)
        }
    }
```

- [ ] **Step 2: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: localized feedback strings

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Refactor `DistortionCard` (de-Button) + rating UI; keep call sites compiling

**Files:**
- Modify: `ContentView.swift` — `struct DistortionCard` (~line 562),
  `ThoughtRow.body` call site (~line 489), `SavedDetailView` call site
  (~line 710).

- [ ] **Step 1: Replace `struct DistortionCard` entirely**

Replace the whole `struct DistortionCard { ... }` (lines 562–601) with:

```swift
struct DistortionCard: View {
    let distortion: Distortion
    let language: AppLanguage
    let ratable: Bool
    @Binding var feedback: DistortionFeedback?

    @State private var isExpanded = false

    private var verdict: DistortionVerdict? { feedback?.verdict }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(distortion.name)
                    .font(.body.weight(.semibold))
                    .foregroundStyle(Color.accentColor)
                Spacer(minLength: 4)
                Image(systemName: "chevron.down")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .rotationEffect(.degrees(isExpanded ? 180 : 0))
            }
            .contentShape(Rectangle())
            .onTapGesture { isExpanded.toggle() }

            Text(distortion.explanation)
                .font(.callout)
                .foregroundStyle(.secondary)
                .lineLimit(isExpanded ? nil : 2)
                .multilineTextAlignment(.leading)

            if ratable {
                feedbackControls
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(.tertiarySystemFill))
        )
        .animation(.smooth, value: isExpanded)
        .animation(.smooth, value: feedback)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(distortion.name)")
    }

    @ViewBuilder private var feedbackControls: some View {
        HStack(spacing: 16) {
            Button {
                setVerdict(.up)
            } label: {
                Image(systemName: verdict == .up ? "hand.thumbsup.fill" : "hand.thumbsup")
                    .foregroundStyle(verdict == .up ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(L10n.feedbackUpA11y(language))
            .accessibilityAddTraits(verdict == .up ? [.isSelected] : [])

            Button {
                setVerdict(.down)
            } label: {
                Image(systemName: verdict == .down ? "hand.thumbsdown.fill" : "hand.thumbsdown")
                    .foregroundStyle(verdict == .down ? Color.accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(L10n.feedbackDownA11y(language))
            .accessibilityAddTraits(verdict == .down ? [.isSelected] : [])

            Spacer()
        }
        .font(.callout)
        .padding(.top, 2)
        .sensoryFeedback(.selection, trigger: feedback?.verdict)

        if verdict == .down {
            VStack(alignment: .leading, spacing: 6) {
                Text(L10n.feedbackWhatsWrong(language))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                HStack(spacing: 8) {
                    ForEach(DownReason.allCases) { reason in
                        reasonChip(reason)
                    }
                }
            }
            .padding(.top, 4)
        }
    }

    private func reasonChip(_ reason: DownReason) -> some View {
        let on = feedback?.reasons.contains(reason) ?? false
        return Button {
            toggleReason(reason)
        } label: {
            Text(L10n.reasonLabel(language, reason))
                .font(.caption)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    Capsule().fill(on ? Color.accentColor.opacity(0.18)
                                       : Color(.quaternarySystemFill))
                )
                .foregroundStyle(on ? Color.accentColor : .secondary)
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(on ? [.isSelected] : [])
    }

    private func setVerdict(_ v: DistortionVerdict) {
        if feedback?.verdict == v {
            feedback = nil                      // tap active verdict → clear
        } else if v == .up {
            feedback = DistortionFeedback(verdict: .up)
        } else {
            feedback = DistortionFeedback(verdict: .down,
                                          reasons: feedback?.reasons ?? [])
        }
    }

    private func toggleReason(_ r: DownReason) {
        guard var fb = feedback, fb.verdict == .down else { return }
        if fb.reasons.contains(r) { fb.reasons.remove(r) } else { fb.reasons.insert(r) }
        feedback = fb
    }
}
```

- [ ] **Step 2: Update the `ThoughtRow` call site (compile-safe stub)**

In `ThoughtRow.body`, replace the `DistortionCard(distortion: d)` call
(~line 489) with:

```swift
                        DistortionCard(distortion: d,
                                       language: settings.language,
                                       ratable: false,
                                       feedback: .constant(nil))
```

- [ ] **Step 3: Update the `SavedDetailView` call site (compile-safe stub)**

In `SavedDetailView.body`, replace the `DistortionCard(distortion: d)`
call (~line 710) with:

```swift
                            DistortionCard(distortion: d,
                                           language: entry.language,
                                           ratable: false,
                                           feedback: .constant(nil))
```

- [ ] **Step 4: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 5: Simulator verification**

Type a thought, get cards. **Expected:** tapping a card still expands/
collapses the explanation (now via the header), no rating controls visible
yet (ratable is still `false`). No visual regression.

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "refactor: DistortionCard de-Button + rating UI (not wired yet)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: Wire rating in `ThoughtRow` — settled gate + reset on real re-analysis

**Files:**
- Modify: `ContentView.swift` — `ThoughtRow` (call site ~line 489, add a
  binding helper) and `runAnalysis()` reset points.

- [ ] **Step 1: Add a feedback binding helper to `ThoughtRow`**

In `ThoughtRow`, after the `analysisID` computed property (added Task 4
Step 4), add:

```swift
    private func feedbackBinding(_ name: String) -> Binding<DistortionFeedback?> {
        Binding(
            get: { thought.feedback[name] },
            set: { newValue in thought.feedback[name] = newValue }
        )
    }
```

- [ ] **Step 2: Pass the real binding + settled gate into the card**

Replace the `DistortionCard(...)` stub in `ThoughtRow.body` (from Task 9
Step 2) with:

```swift
                        DistortionCard(distortion: d,
                                       language: settings.language,
                                       ratable: isSettled,
                                       feedback: feedbackBinding(d.name))
```

- [ ] **Step 3: Add the feedback-reset points in `runAnalysis()`**

`Thought.feedback` now exists (Task 6), so wire the reset. Add
`thought.feedback = [:]` in **exactly two** places in `runAnalysis()` and
nowhere else:

1. In the **empty-guard branch** — alongside the other resets:

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

2. In the **success branch only**, immediately after
   `thought.distortions = distortions`:

```swift
        do {
            let distortions = try await BackendClient.shared.analyze(req)
            thought.distortions = distortions
            thought.feedback = [:]            // results changed → prior verdicts no longer apply
            thought.status = .idle
            thought.didAnalyze = true         // включая success-empty
            thought.lastAnalyzedSignature = signature
        } catch is CancellationError {
            // не трогаем didAnalyze / lastAnalyzedSignature / feedback
        } catch let urlError as URLError where urlError.code == .cancelled {
            // не трогаем didAnalyze / lastAnalyzedSignature / feedback
        } catch {
            thought.status = .error(error.localizedDescription)
            thought.lastAnalyzedSignature = signature   // do not auto-retry same input on lifecycle
        }
```

Do **not** add a reset before/around the 1.5 s debounce or after the
signature guard. The resulting behaviour (intended — do not "fix"):

- Signature guard returns before reaching either reset → tab-switch /
  foreground keeps verdicts. ✓
- A failed re-analysis goes to the `catch` (no reset) → verdicts survive a
  network error instead of vanishing. ✓
- No pre-debounce reset → verdicts do not flicker away while a new analysis
  is in flight. ✓

- [ ] **Step 4: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 5: Simulator verification**

1. Type a thought, wait for cards, then move focus away (tap "New
   thought" or another field). **Expected:** 👍/👎 appear under each card.
2. Tap 👎. **Expected:** "Что не так?" + two reason chips appear; tap both,
   they highlight. Tap 👎 again. **Expected:** verdict + chips clear.
3. Tap 👍. **Expected:** thumbs-up fills, no reason chips.
4. Go back into the thought, add a word. **Expected:** after re-analysis
   the cards refresh and the previous verdict is **gone** (reset).
5. Set a verdict, switch to "Saved" tab and back. **Expected:** verdict
   is **still there** (signature guard prevented re-analysis, no reset).

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: rate distortions inline on settled thought; reset on real re-analysis

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: Carry feedback into the saved entry on Save

**Files:**
- Modify: `ContentView.swift` — `AnalyzeView.performSave()` (~line 430).

- [ ] **Step 1: Include feedback when building `SavedThought`s**

In `performSave()`, change the `filteredThoughts` map to pass feedback:

```swift
        let filteredThoughts = thoughts
            .filter { !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
            .map { SavedThought(text: $0.text,
                                distortions: $0.distortions,
                                feedback: $0.feedback) }
```

- [ ] **Step 2: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 3: Simulator verification**

Type a thought, rate a distortion 👎 with a reason, tap "Save". Open
"Saved" → tap the entry. **Expected:** the entry detail shows the
distortion (rating controls wired in Task 12; for now just confirm Save
did not crash and the entry/thought is present).

- [ ] **Step 4: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: persist distortion feedback into saved entry on Save

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: `EntryStore.updateFeedback` + store-backed ratable `SavedDetailView`

**Files:**
- Modify: `ContentView.swift` — `EntryStore` (add method ~after line 176),
  `SavedListView` NavigationLink (~line 622), `SavedDetailView` (~line 681).

- [ ] **Step 1: Add the mutator to `EntryStore`**

In `final class EntryStore`, after `func delete(id:) async` (line 176),
add:

```swift
    func updateFeedback(entryID: UUID,
                        thoughtID: UUID,
                        distortionName: String,
                        _ feedback: DistortionFeedback?) async {
        guard let ei = entries.firstIndex(where: { $0.id == entryID }) else { return }
        let entry = entries[ei]
        guard let ti = entry.thoughts.firstIndex(where: { $0.id == thoughtID }) else { return }

        var thoughts = entry.thoughts
        let st = thoughts[ti]
        var fb = st.feedback
        if let feedback { fb[distortionName] = feedback } else { fb[distortionName] = nil }
        thoughts[ti] = SavedThought(id: st.id,
                                    text: st.text,
                                    distortions: st.distortions,
                                    feedback: fb)
        entries[ei] = SavedEntry(id: entry.id,
                                 createdAt: entry.createdAt,
                                 situation: entry.situation,
                                 feelings: entry.feelings,
                                 thoughts: thoughts,
                                 language: entry.language)
        await persist()
    }
```

- [ ] **Step 2: Pass entry id (not the value) to the detail view**

In `SavedListView.body`, change the `NavigationLink` destination from
`SavedDetailView(entry: entry)` to:

```swift
                        NavigationLink {
                            SavedDetailView(entryID: entry.id)
                        } label: {
                            SavedRow(entry: entry, uiLanguage: settings.language)
                        }
```

- [ ] **Step 3: Replace `SavedDetailView` entirely**

Replace the whole `struct SavedDetailView { ... }` (lines 681–721) with:

```swift
struct SavedDetailView: View {
    let entryID: UUID
    @Environment(AppSettings.self) private var settings
    @Environment(EntryStore.self) private var store

    private var entry: SavedEntry? {
        store.entries.first(where: { $0.id == entryID })
    }

    var body: some View {
        Group {
            if let entry {
                Form {
                    if !entry.situation.isEmpty {
                        Section(L10n.whatHappened(entry.language)) {
                            Text(entry.situation)
                        }
                    }
                    if !entry.feelings.isEmpty {
                        Section(L10n.howAreYouFeeling(entry.language)) {
                            Text(entry.feelings)
                        }
                    }
                    Section(L10n.thoughts(entry.language)) {
                        ForEach(entry.thoughts) { thought in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(thought.text).font(.body)
                                if thought.distortions.isEmpty {
                                    Text(L10n.noDistortions(entry.language))
                                        .font(.callout)
                                        .foregroundStyle(.secondary)
                                } else {
                                    ForEach(thought.distortions) { d in
                                        DistortionCard(
                                            distortion: d,
                                            language: entry.language,
                                            ratable: true,
                                            feedback: feedbackBinding(entry, thought, d.name)
                                        )
                                    }
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                .navigationTitle(entry.createdAt.formatted(date: .abbreviated, time: .shortened))
                .navigationBarTitleDisplayMode(.inline)
            } else {
                ProgressView()
            }
        }
    }

    private func feedbackBinding(_ entry: SavedEntry,
                                 _ thought: SavedThought,
                                 _ name: String) -> Binding<DistortionFeedback?> {
        Binding(
            get: { store.entries.first(where: { $0.id == entry.id })?
                        .thoughts.first(where: { $0.id == thought.id })?
                        .feedback[name] },
            set: { newValue in
                Task {
                    await store.updateFeedback(entryID: entry.id,
                                               thoughtID: thought.id,
                                               distortionName: name,
                                               newValue)
                }
            }
        )
    }
}
```

- [ ] **Step 4: Build**

Run the Build check command. Expected: `** BUILD SUCCEEDED **`.

- [ ] **Step 5: Simulator verification**

Open a saved entry. **Expected:** 👍/👎 appear under each distortion. Tap
👎 + a reason. Go back to the list, re-open the same entry. **Expected:**
the verdict and reason are still there (persisted). Kill and relaunch the
app, open the entry again. **Expected:** still there (read from
`entries.json`).

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios && git add CBTAnalyzer/CBTAnalyzer/ContentView.swift && git commit -m "feat: rate distortions in Saved detail; EntryStore.updateFeedback persists

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: Export verification + polish pass

**Files:** none (verification), unless polish fixes are needed.

- [ ] **Step 1: Verify the export carries feedback (the eval set)**

In the app: create an entry, rate distortions (mix of 👍 and 👎+reasons),
Save. On "Saved" tap the Share button, save `cbt-entries.json` to Files.
Then inspect it:

```bash
xcrun simctl get_app_container booted com.bulsir.cbtanalyzer data 2>/dev/null
# locate entries.json under .../Documents/entries.json and:
python3 -m json.tool < "$(find "$(xcrun simctl get_app_container booted com.bulsir.cbtanalyzer data)" -name entries.json)"
```

**Expected:** each rated `thoughts[].feedback` is an object keyed by the
distortion name, e.g.
`"feedback": { "Катастрофизация": { "verdict": "down", "reasons": ["wrongLabel"] } }`.
Dates are ISO-8601. Unrated distortions simply have no key.

- [ ] **Step 2: Polish — Dynamic Type**

In the simulator: Settings → Accessibility → Larger Text → max. Open a
card with feedback. **Expected:** thumbs and reason chips stay usable
(wrap, not clipped). If chips overflow horizontally, change their `HStack`
in `reasonChip`'s parent to wrap — replace the `HStack(spacing: 8) { ForEach... }`
in `feedbackControls` with:

```swift
                FlowReasons(reasons: DownReason.allCases) { reason in
                    reasonChip(reason)
                }
```

only if overflow is observed. If no overflow, skip (YAGNI — do not add
`FlowReasons` speculatively).

- [ ] **Step 3: Polish — Dark Mode**

Toggle Dark Mode in the simulator. **Expected:** selected/unselected
thumbs and chips have adequate contrast (uses `.accentColor` /
`.secondary` / system fills only — should pass). Note any issue; fix only
if a real contrast problem is visible.

- [ ] **Step 4: Final commit**

```bash
cd ~/Projects/abc_app_ios && git add -A && git commit -m "polish: verify feedback export, Dynamic Type & Dark Mode for rating UI

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

- [ ] **Step 5: Update memory**

Append to `/Users/bulat/.claude/projects/-Users-bulat-Projects-abc-app/memory/v1_improvement_backlog.md`
a note that the feedback feature shipped (date 2026-05-16), export is the
eval set keyed by distortion name, and add a pointer in `MEMORY.md` if a
new memory file is warranted (e.g. `feedback-eval-set.md` describing where
the eval data comes from for future prompt-tuning iterations).

---

## Self-Review

**Spec coverage:**

- Pre-step 0 reproduce-first (instrument → reproduce → confirm → fix → gate):
  Tasks 1–5. ✓ (signature guard = Hypothesis B/thrash; settled-id =
  Hypothesis A churn; both applied, diagnostic recorded in Task 5 commit).
- Data model (`DistortionVerdict`/`DownReason`/`DistortionFeedback`,
  `Thought.feedback`): Task 6. ✓
- `SavedThought.feedback` + backward-compatible decode: Task 7. ✓
- "Settled" gate (`didAnalyze && status==.idle && !focused`): Task 10
  (`isSettled` in Task 4, reused). ✓
- Reset on re-analysis, surviving phantom via signature guard: Task 10
  Step 3 (reset placed *after* the guard). ✓
- DistortionCard de-Button + 👍/👎 + reason chips + toggle-off + haptic +
  a11y: Task 9. ✓
- Carry into entry on Save: Task 11. ✓
- Ratable Saved detail + `EntryStore` mutator + store-backed lookup: Task
  12. ✓
- Export = eval set (no code change): Task 13 Step 1 verifies. ✓
- Scope boundary "no rating of empty result": honored — controls render
  only inside `DistortionCard` (per-distortion), never on the
  `noDistortions` text. ✓
- Backend untouched: no task modifies `abc_app/backend`. ✓

**Placeholder scan:** no TBD/TODO; every code step shows full code; the
only conditional ("add FlowReasons only if overflow") is gated on an
observation with explicit skip instruction, not a deferred design hole.

**Type consistency:** `DistortionFeedback`, `DistortionVerdict`,
`DownReason` defined Task 6, used identically in Tasks 7/9/10/12.
`SavedThought` initializer signature `(id:text:distortions:feedback:)` is
defined Task 7 and called with exactly those labels in Tasks 11 and 12.
`feedbackBinding` returns `Binding<DistortionFeedback?>` in both ThoughtRow
(Task 10) and SavedDetailView (Task 12), matching `DistortionCard`'s
`@Binding var feedback: DistortionFeedback?` (Task 9). `isSettled` defined
Task 4, reused Task 10. `lastAnalyzedSignature` defined Task 3, used Tasks
3 and 10.

**Post-review revisions (ios-code-reviewer pass, 2026-05-16):** The initial
self-review's "no drift" claim was wrong and is superseded. Fixes applied
to this plan:

- **B6:** added the line-numbers-are-approximate banner; Task 3 Step 2
  rewritten so it preserves the Task 1 diagnostic block (it previously
  deleted it, breaking Task 5).
- **B1:** the signature guard is now signature-only
  (`lastAnalyzedSignature == signature`), `didAnalyze`/`.error` exception
  removed; signature is stored on the error branch too. This is what
  actually delivers the spec's "fires iff input changed" contract for
  errored/edge thoughts.
- **B2:** context is committed on entering a thought field, not only on
  blur — prevents analysis with stale-empty context.
- **S1:** feedback reset moved into the success branch only (+ empty-guard
  branch); no pre-debounce reset → no verdict flicker, survives a failed
  re-analysis.
- **S3:** haptic triggers on `feedback?.verdict`, not the whole feedback
  object, so reason-chip toggles don't double-buzz.
- **B5:** `status` logged as a coarse case name (no raw backend error
  string at `.public`); per-process hash caveat documented.

B4 was withdrawn by the reviewer after verification (`DistortionFeedback`
is `Hashable` ⇒ `.sensoryFeedback` trigger is `Equatable`). S5/N2 confirmed
sound. Reviewer verdict after these edits: architecture sound, remaining
items are polish.

---

## Post-implementation notes (2026-05-16, all 13 tasks done)

Implemented via subagent-driven development; per-task spec + quality
review; verified on a real device.

**Bug #3 fix evolved during device testing.** Pre-step 0 shipped as
planned (diagnostic → signature guard → settled-id), but on-device the
`isSettled`-in-`analysisID` lever caused a status↔id feedback loop:
`runAnalysis` mutates `thought.status` → `isSettled` flips → `analysisID`
changes → `.task` restarts → endless idle/loading storm that also wiped
feedback. Fix: `analysisID` is now a **pure function of genuine inputs**
(`thought.text` + committed situation/feelings + language), with NO
dependence on `isSettled`/status. Bug #3 remains fixed by committed-context
-on-blur (kills per-keystroke fan-out) + the signature guard (absorbs
lifecycle re-fires). `isSettled` is retained solely as the `ratable:` gate.
Lesson: never tie `.task(id:)` to state the task itself mutates.

**Extra robustness fixes applied during review (beyond the plan):**
- `feedbackBinding` captures the projected `$thought` binding (not a `self`
  snapshot).
- `DistortionCard` got an optimistic local `@State` (`local`) synced via
  `.onChange(of: feedback)`/`.onAppear` so rapid taps over the async store
  (Saved-detail) aren't lost.
- `performSave` clears `committedSituation/Feelings` (no ghost context).
- `DistortionCardA11y` ViewModifier: `.combine`+hint for read-only,
  `.contain` for ratable; 44pt touch targets on thumbs/chips.

**Final whole-feature review dispositions:**
- *Reset of all `thought.feedback` on any re-analysis* — flagged by the
  final reviewer as "must fix", but this is the **agreed design**
  (brainstorming: "тронул мысль → повторный анализ → оценка слетает") and
  was explicitly confirmed by the user on-device ("так задумано"). Kept
  intentionally; not a defect. The reviewer lacked that context.
- *Saved-detail rapid-tap Task race* — known **minor**: optimistic `local`
  shows the correct value, the store converges to the last tap's value
  (no data loss); only a brief visual flicker is possible under very rapid
  taps. Accepted; logged in `v1_improvement_backlog` for a later
  cancel-previous-Task serialization.
- Minors (redundant `onAppear` init; manual struct rebuild in
  `updateFeedback`) — backlog.
