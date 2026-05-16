# Distortion feedback (👍/👎) — design

Date: 2026-05-16
Scope: iOS client only (`~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/ContentView.swift`).
Backend: **no changes** (feedback stays on-device, confirmed).

## Problem

The user wants to mark each detected cognitive distortion with 👍/👎 so that,
later, they can export the collected verdicts and see *where the model errs* —
material for tuning the LLM prompt (the v1 backlog item #1 is an ongoing
quality effort; this gives it a data source).

Two product constraints emerged in brainstorming:

1. **Feedback needs context to be useful.** A bare "👎 on Катастрофизация"
   is worthless; the thought + situation + emotions must travel with it.
   Therefore feedback lives inside the saved entry (which already carries
   that context) and rides the existing JSON export.
2. **A rating needs a stable target.** Analysis is reactive (debounced, no
   button — a confirmed user preference, `user_prefers_reactive_no_buttons`).
   Cards churn while typing, so you cannot rate a moving result.

## Pre-step 0 — fix backlog bug #3 (phantom re-analysis) FIRST

The user explicitly asked to fix bug #3 before the feature, because the
feature shares its core invariant.

### Approach: reproduce first, fix the confirmed cause

The fix is **gated on reproduction**, not applied blind. Code reading gives
two *hypotheses* (A and B below); the simulator decides which actually
fire. Sequence:

1. **Instrument.** Add a single `print`/`os_log` line at the top of
   `runAnalysis()` logging: thought id (short), `thought.text` hash,
   `situation`/`feelings` hash, `didAnalyze`, and a coarse "trigger" guess.
   No behaviour change — pure observation.
2. **Reproduce.** User exercises the simulator and reproduces the
   "I changed nothing and it re-analyzed" event, capturing the log around
   it. Specifically tries: editing situation/feelings then leaving the
   thoughts alone (tests A); switching to Saved tab and back, backgrounding
   the app, navigating away/in (tests B).
3. **Confirm** which hypothesis the log supports (A, B, or both).
4. **Apply the targeted fix** for the confirmed cause(s) only (see Fix
   below). Re-run step 2 to verify the phantom is gone and legitimate
   re-analysis (continuing to type in the same thought) still works.

### Hypothesis A — context fan-out (from code reading)

`ThoughtRow` carries:

```swift
.task(id: AnalysisInput(text: thought.text,
                        situation: situation,
                        feelings: feelings,
                        language: settings.language.rawValue)) { await runAnalysis() }
```

`situation` and `feelings` are passed **by value into every `ThoughtRow`**.
Any keystroke in the "What happened?" or "How are you feeling?" textarea
changes the `AnalysisInput` id for **every** thought row at once → every
already-analyzed thought re-fires `/analyze` after the 1.5 s debounce.

From the user's point of view: "I'm not touching the thoughts but requests
keep firing on their own" — because the ambient context was edited (or
dictation/autocorrect mutated those fields), silently invalidating all rows.
Secondary harm: N thoughts ⇒ N simultaneous `/analyze` calls ⇒ rate-limit
pressure.

Context *should* influence results (per CLAUDE.md, A/C context is critical to
quality) — the bug under this hypothesis is not that context matters, it is
the **per-keystroke, all-rows churn**, including finished thoughts the user
is not looking at.

### Hypothesis B — `.task` lifecycle re-run (the "I changed nothing" symptom)

SwiftUI re-runs a `.task` whenever its view disappears and reappears, even
if the id is unchanged: tab switch (Analyze → Saved → Analyze), app
background/foreground, navigation push/pop. Nothing the user typed changed,
yet `/analyze` fires again. This matches the user's report of phantom
re-analysis with zero edits, which Hypothesis A alone does not explain.

### Fix (apply only what reproduction confirms)

Two independent levers; pick per confirmed cause. They compose.

- **For Hypothesis A — settled-thought stable id.** A thought that is
  already analyzed and not currently focused derives its `.task` id from
  `thought.text` + `language` only; ambient `situation`/`feelings` edits no
  longer bump it. Active/unanalyzed thoughts still use context, but from a
  **committed snapshot** (situation/feelings captured on focus-loss /
  `.onSubmit`, not per keystroke). Invariant: **settled thought ⇒ stable id.**
- **For Hypothesis B (and a safety net for any id thrash) — idempotent
  signature guard.** `Thought` records the signature it was last analyzed
  for (text + committed context + language). `runAnalysis()` early-returns
  **before the network call** if the current signature equals the
  last-analyzed one. Any `.task` restart for an unchanged input becomes a
  no-op; a real edit (different signature) still analyzes. This alone makes
  `/analyze` fire iff the input genuinely changed, regardless of why
  `.task` re-ran.

Recommended end state: the signature guard is the robust core (covers B and
hardens A); the settled-id refinement additionally removes the wasteful
debounce-sleep churn on every context keystroke. Exact wiring is left to
the implementation plan; the contract is: **`/analyze` fires only when the
analyzed input actually changed.**

### Why this is a true pre-step, not folded in

The feedback feature's "settled" gate (below) assumes a settled thought
stays put. If bug #3 still fires, verdicts silently vanish (Section 3
reset). Fixing #3 first removes that whole class of "my likes disappeared"
reports before the feature can produce them.

## Feature design

### 1. Data model

```swift
enum DistortionVerdict: String, Codable { case up, down }
enum DownReason: String, Codable, CaseIterable { case wrongLabel, weakExplanation }
struct DistortionFeedback: Codable, Hashable {
    var verdict: DistortionVerdict
    var reasons: Set<DownReason> = []   // empty for .up; for .down — what is wrong
}
```

Distortion→feedback mapping is a dictionary keyed by `Distortion.name`
(which is also `Distortion.id`):

- live `Thought` gains `var feedback: [String: DistortionFeedback] = [:]`
- `SavedThought` gains `feedback` with a **custom `init(from:)`** doing
  `decodeIfPresent(.feedback) ?? [:]`, so existing `entries.json` files
  (no `feedback` key) keep loading. Synthesized `Codable` does NOT default
  missing keys — the custom decoder init is mandatory, not optional polish.

`Distortion` (the backend DTO) is **not modified** — feedback lives
alongside it, the `/analyze` contract is untouched.

Keying by name is safe: `Distortion.id == name`, `ForEach` already treats it
as `Identifiable` by that, so duplicate names would already be a pre-existing
UI bug, not introduced here.

### 2. "Settled" — when 👍/👎 appear (Analyze tab)

A card in the Analyze tab becomes ratable iff:

```
thought.didAnalyze == true
  && thought.status == .idle
  && focusedField != .thought(thought.id)
```

No new timer or state — reuses existing `didAnalyze` and `focusedField`.
Focus leaving the row (you moved to a new thought) is the "I finished this
one" signal. Deliberately kept away from fragile new state near bug #3 (now
fixed by Pre-step 0, but the principle holds).

### 3. Reset on re-analysis

At the start of `runAnalysis()` — both the empty-guard branch and before the
network call — set `thought.feedback = [:]`. Any re-entry into analysis means
the (text + context) pair changed, so the old verdict no longer applies to
the new result. This matches the user's mental model exactly ("re-analyzed →
rating drops").

With Pre-step 0 in place, re-analysis only happens on a genuine text/context
change, so resets are no longer spurious.

### 4. UI

`DistortionCard` stops being one large `Button` (nested 👍/👎 Buttons inside
a Button is the classic SwiftUI tap-swallow trap). The expand toggle moves
to `.contentShape(Rectangle()) + .onTapGesture` on the header row only;
feedback controls are independent `Button`s.

Bottom of the card: a thin row — 👍 / 👎 (SF Symbols
`hand.thumbsup` / `hand.thumbsdown`, selected one filled with accent).
Tapping 👎 reveals two reason chips below it (multi-select):
"Не то искажение" / "Слабое объяснение" (EN: "Wrong distortion" /
"Weak explanation"). Tapping the active verdict again clears the rating
(toggle off → no feedback entry). Light `.sensoryFeedback` on setting a
verdict. Accessibility labels on every control; reason chips
VoiceOver-selectable.

`DistortionCard` signature gains a feedback binding (`Binding<DistortionFeedback?>`)
and a `ratable: Bool`. In Analyze, `ratable` follows the Section 2 gate. In
`SavedDetailView`, `ratable` is always true (the entry is frozen).

New L10n strings: reason labels, "What's wrong?" header, 👍/👎 a11y labels.

### 5. Carry into entry + export

On Save, `thought.feedback` copies into `SavedThought`. In
`SavedDetailView`, cards are always ratable; persisting an edit there needs a
new `EntryStore` mutator, e.g.
`updateFeedback(entryID:thoughtID:distortionName:_:) async` that mutates
`entries` and rewrites `entries.json` (reuse the existing `persist()` path).
`SavedDetailView` must look the entry up from `store` by id rather than
holding a value copy, otherwise edits don't persist or reflect.

Export needs no change: `makeExportFile()` encodes the same `entries`
snapshot, so `feedback` lands in the JSON automatically — the export is the
eval set, keyed by distortion name with verdict + reasons + full
thought/situation/emotions context already present in `SavedEntry`.

## Scope boundaries (v1 does NOT do)

- **No rating of the "empty" result.** Rating attaches only to shown
  distortions, as the user framed it. (Whether "no distortions detected" was
  itself a miss is a richer signal — deferred.)
- **No backend changes.** Feedback is on-device only (confirmed). No
  `/feedback` endpoint, no DB.
- **iOS only**, single file `ContentView.swift` in the separate repo
  `~/Projects/abc_app_ios/`.
- No analytics/aggregation UI in-app — review happens by exporting JSON and
  reading it off-device.

## Risks / rollback

- **Bug #3 fix is load-bearing.** If Pre-step 0 regresses analysis
  correctness (e.g., a settled thought fails to re-analyze after a genuine
  context change the user *does* want reflected), the feature still works but
  some entries carry stale analysis. Mitigation: settled rows still
  re-analyze on their own text change; context change is reflected next time
  the thought text is edited or on a fresh entry. Acceptable per the
  reactive-but-stable trade-off the user chose.
- Rollback is per-commit: the iOS repo is local-only; revert the feature
  commit. Pre-step 0 can ship and stand alone (it is a pure bug fix and
  improves the app regardless of the feature).

## Out of scope (future)

- Rating the empty/"no distortion" outcome.
- Server-side feedback collection / cross-device aggregation (would require
  abandoning the deliberate no-thought-persistence backend stance).
- In-app analytics dashboard over collected verdicts.
- Auto-feeding verdicts back into few-shot prompt selection.
