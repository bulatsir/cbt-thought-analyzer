# Переименование приложения в «Cogi» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переименовать iOS-приложение в **Cogi** (display-имя `Cogi`, по-русски «Коги») — пользовательское имя + внутренние имена (target/scheme/файлы/struct/папки/папка репо), сохранив bundle ID и ключи `cbt.*`, чтобы данные на устройстве не потерялись.

**Architecture:** Проект — `PBXFileSystemSynchronizedRootGroup` (Xcode 16, `objectVersion 77`): отдельные `.swift` не перечислены в `project.pbxproj`, scheme автогенерируется, workspace ссылается на `self:`. Поэтому ренейм = переименование файлов/папок на диске + 4 точечные правки в `project.pbxproj` + добавление `CFBundleDisplayName`. Весь ренейм делается правкой файлов; верификация — сборка пользователем на устройстве (XCTest в проекте нет, симулятор не используем).

**Tech Stack:** SwiftUI (iOS 17), Xcode 16, `project.pbxproj` (objectVersion 77, sync-group).

**Spec:** `docs/superpowers/specs/2026-06-01-rename-app-cogi-design.md`

---

## Карта переименований

Текущее дерево (репо `~/Projects/abc_app_ios`):

```
~/Projects/abc_app_ios/              (R: репо)        → ~/Projects/cogi_ios
  CBTAnalyzer/                       (A: контейнер)   → Cogi/
    CBTAnalyzer.xcodeproj/           (B: проект)      → Cogi.xcodeproj/
      project.pbxproj                                 (4 правки + display name)
    CBTAnalyzer/                     (C: исходники)   → Cogi/
      CBTAnalyzerApp.swift           (entry)          → CogiApp.swift  (struct → CogiApp)
      ContentView.swift                               (только header-комментарий)
      Assets.xcassets/                                (без изменений)
```

**Неизменно (критично):** `PRODUCT_BUNDLE_IDENTIFIER = com.bulsir.cbtanalyzer`, ключи UserDefaults `cbt.*` (язык, Device ID). `PRODUCT_NAME = $(TARGET_NAME)` оставляем как есть — он автоматически станет `Cogi` после ренейма target.

**Якоря в `project.pbxproj`** (номера строк ориентировочны — искать по строкам):
- `path = CBTAnalyzer.app;` (PBXFileReference продукта) → `path = Cogi.app;`
- `path = CBTAnalyzer;` (PBXFileSystemSynchronizedRootGroup, единственное вхождение `path = CBTAnalyzer;` без `.app`) → `path = Cogi;`
- `name = CBTAnalyzer;` (PBXNativeTarget) → `name = Cogi;`
- `productName = CBTAnalyzer;` → `productName = Cogi;`
- В обоих блоках `XCBuildConfiguration` (Debug + Release) добавить `INFOPLIST_KEY_CFBundleDisplayName = Cogi;`

---

## Pre-step 0: Подготовка рабочего дерева

- [ ] **Развязаться с незакоммиченной работой по ретраю**

В iOS-репозитории есть незакоммиченные правки (`ContentView.swift` — авто-ретрай) и untracked `CHANGELOG.md`. Ренейм почти не пересекается с ними (трогает pbxproj, `CogiApp.swift`, header-комментарий `ContentView.swift`), но чтобы коммиты были чистыми — сначала закоммить или отложи ретрай.

```bash
cd ~/Projects/abc_app_ios && git status --short
```

Решение пользователя: либо `git add -A && git commit` ретрая (после проверки на устройстве), либо `git stash`. Не продолжать, пока не выбрано.

- [ ] **Закрыть Xcode**, если открыт (на шаге переименования `.xcodeproj`/папок проект не должен быть открыт).

---

## Task 1: Display-имя `Cogi` (самый видимый результат, минимальный риск)

**Files:**
- Modify: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj`

- [ ] **Step 1: Прочитать оба блока `XCBuildConfiguration`**

Read `project.pbxproj`. Найти два блока build-настроек (заканчиваются `name = Debug;` и `name = Release;`). В каждом есть группа `INFOPLIST_KEY_*` и строки `PRODUCT_BUNDLE_IDENTIFIER = "com.bulsir.cbtanalyzer";` / `PRODUCT_NAME = "$(TARGET_NAME)";`.

- [ ] **Step 2: Добавить `CFBundleDisplayName` в Debug-блок**

В Debug-блоке (тот, что заканчивается `name = Debug;`) сразу перед `PRODUCT_BUNDLE_IDENTIFIER = "com.bulsir.cbtanalyzer";` добавить строку (сохранив табы-отступы файла):

```
				INFOPLIST_KEY_CFBundleDisplayName = Cogi;
```

Чтобы old_string был уникален для Debug, включить в него достаточный контекст этого блока (напр. предшествующую `INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "...";` вместе со следующей `PRODUCT_BUNDLE_IDENTIFIER`). Если строки идентичны в обоих блоках — расширить контекст до уникального (вплоть до `name = Debug;`).

- [ ] **Step 3: Добавить `CFBundleDisplayName` в Release-блок**

Аналогично в Release-блоке (заканчивается `name = Release;`) добавить ту же строку `INFOPLIST_KEY_CFBundleDisplayName = Cogi;`.

- [ ] **Step 4: Проверить, что добавлено ровно дважды**

Run: `grep -c "INFOPLIST_KEY_CFBundleDisplayName = Cogi;" ~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj`
Expected: `2`

- [ ] **Step 5: Сборка на устройстве (пользователь)**

Пользователь: открыть проект в Xcode, ⌘R на устройстве. Ожидаем: на домашнем экране подпись под иконкой — **«Cogi»**. Сохранённые мысли/язык на месте (bundle ID не менялся).

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios
git add CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj
git commit -m "rename: set CFBundleDisplayName to Cogi"
```

---

## Task 2: Переименовать entry-point (`CogiApp`)

**Files:**
- Rename: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/CBTAnalyzerApp.swift` → `CogiApp.swift`
- Modify: содержимое (struct + header-комментарии)

- [ ] **Step 1: Переименовать файл (git-aware)**

```bash
cd ~/Projects/abc_app_ios
git mv CBTAnalyzer/CBTAnalyzer/CBTAnalyzerApp.swift CBTAnalyzer/CBTAnalyzer/CogiApp.swift
```
(Sync-group проект — ссылок на файл в pbxproj нет, правки pbxproj не нужны.)

- [ ] **Step 2: Переименовать struct и шапку**

В `CBTAnalyzer/CBTAnalyzer/CogiApp.swift`:
- `struct CBTAnalyzerApp: App {` → `struct CogiApp: App {`
- В шапке-комментарии `//  CBTAnalyzerApp.swift` → `//  CogiApp.swift`, `//  CBTAnalyzer` → `//  Cogi`

- [ ] **Step 3: Убедиться, что других ссылок на `CBTAnalyzerApp` нет**

Run: `grep -rn "CBTAnalyzerApp" ~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/`
Expected: пусто (вхождений не осталось).

- [ ] **Step 4: Header-комментарий в `ContentView.swift`**

Если в шапке `ContentView.swift` есть `//  CBTAnalyzer` — заменить на `//  Cogi`. (Тело файла не трогаем.)

Run для проверки остатков: `grep -rn "CBTAnalyzer" ~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/*.swift`
Expected: пусто.

- [ ] **Step 5: Сборка на устройстве (пользователь)**

Пользователь: ⌘R. Ожидаем: `** BUILD SUCCEEDED **`, приложение запускается (`@main struct CogiApp`).

- [ ] **Step 6: Commit**

```bash
cd ~/Projects/abc_app_ios
git add -A
git commit -m "rename: CBTAnalyzerApp -> CogiApp (entry point)"
```

---

## Task 3: Переименовать папку исходников `C` → `Cogi`

**Files:**
- Rename dir: `~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer/` → `~/Projects/abc_app_ios/CBTAnalyzer/Cogi/`
- Modify: `project.pbxproj` (sync-group `path`)

- [ ] **Step 1: Переименовать папку исходников**

```bash
cd ~/Projects/abc_app_ios
git mv CBTAnalyzer/CBTAnalyzer CBTAnalyzer/Cogi
```

- [ ] **Step 2: Обновить `path` синхронизированной группы в pbxproj**

В `CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj` в блоке `PBXFileSystemSynchronizedRootGroup` заменить:
```
			path = CBTAnalyzer;
```
на:
```
			path = Cogi;
```
(Это единственное вхождение `path = CBTAnalyzer;` без суффикса `.app`. Не задеть `path = CBTAnalyzer.app;`.)

- [ ] **Step 3: Проверка путей**

Run: `grep -n "path = CBTAnalyzer;" ~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj`
Expected: пусто.
Run: `ls ~/Projects/abc_app_ios/CBTAnalyzer/Cogi/`
Expected: `Assets.xcassets  CogiApp.swift  ContentView.swift`

- [ ] **Step 4: Сборка на устройстве (пользователь)**

Пользователь: ⌘R. Ожидаем: `** BUILD SUCCEEDED **` (sync-group нашёл исходники по новому `path`).

- [ ] **Step 5: Commit**

```bash
cd ~/Projects/abc_app_ios
git add -A
git commit -m "rename: source folder CBTAnalyzer -> Cogi (sync-group path)"
```

---

## Task 4: Переименовать target, продукт, контейнер и `.xcodeproj`

**Files:**
- Modify: `project.pbxproj` (target `name`, `productName`, product `path`)
- Rename dir: контейнер `CBTAnalyzer/` → `Cogi/`
- Rename bundle: `CBTAnalyzer.xcodeproj` → `Cogi.xcodeproj`

> ⚠️ Xcode должен быть закрыт. Это самый рискованный шаг — всё в git, при неудачной сборке `git restore`/`git reset --hard` откатывает.

- [ ] **Step 1: Переименовать target в pbxproj**

В `project.pbxproj` (внутри `PBXNativeTarget`) заменить:
```
			name = CBTAnalyzer;
```
на:
```
			name = Cogi;
```
(Единственное `name = CBTAnalyzer;` — у нативного target. Блоки `XCBuildConfiguration` заканчиваются `name = Debug;`/`name = Release;`, их не трогаем.)

- [ ] **Step 2: Переименовать `productName`**

Заменить:
```
			productName = CBTAnalyzer;
```
на:
```
			productName = Cogi;
```

- [ ] **Step 3: Переименовать ссылку на продукт `.app`**

Заменить `path = CBTAnalyzer.app;` на `path = Cogi.app;` (в PBXFileReference продукта). `PRODUCT_NAME = "$(TARGET_NAME)";` НЕ трогаем — он подставит `Cogi`.

- [ ] **Step 4: Проверить, что в pbxproj не осталось функциональных `CBTAnalyzer`**

Run: `grep -n "CBTAnalyzer" ~/Projects/abc_app_ios/CBTAnalyzer/CBTAnalyzer.xcodeproj/project.pbxproj`
Expected: остаться могут ТОЛЬКО комментарии в кавычках вида `/* ... "CBTAnalyzer" */` (имена build-configuration-list — игнорируются Xcode). Функциональных присваиваний (`name =`, `path =`, `productName =`) с `CBTAnalyzer` быть не должно. Комментарии можно опционально заменить на `Cogi` для чистоты (необязательно, на сборку не влияет).

- [ ] **Step 5: Переименовать `.xcodeproj` и папку-контейнер**

```bash
cd ~/Projects/abc_app_ios
git mv CBTAnalyzer/CBTAnalyzer.xcodeproj CBTAnalyzer/Cogi.xcodeproj
git mv CBTAnalyzer Cogi
```
(workspace ссылается на `self:` — внутренних правок не требуется; xcuserdata/scheme Xcode перегенерирует.)

- [ ] **Step 6: Проверка структуры**

Run: `ls ~/Projects/abc_app_ios/Cogi/ && ls ~/Projects/abc_app_ios/Cogi/Cogi/`
Expected: `Cogi.xcodeproj  Cogi` и затем `Assets.xcassets  CogiApp.swift  ContentView.swift`.

- [ ] **Step 7: Сборка на устройстве (пользователь)**

Пользователь: открыть `~/Projects/abc_app_ios/Cogi/Cogi.xcodeproj`, выбрать автосозданную схему **Cogi**, ⌘R на устройстве. Ожидаем: сборка успешна, продукт `Cogi.app`, на экране «Cogi», данные на месте.

- [ ] **Step 8: Commit**

```bash
cd ~/Projects/abc_app_ios
git add -A
git commit -m "rename: target/product/project bundle CBTAnalyzer -> Cogi"
```

---

## Task 5: Переименовать папку репозитория → `cogi_ios`

**Files:**
- Rename dir: `~/Projects/abc_app_ios` → `~/Projects/cogi_ios`

- [ ] **Step 1: Закрыть Xcode** (проект из старого пути не должен быть открыт).

- [ ] **Step 2: Переименовать папку репо**

```bash
mv ~/Projects/abc_app_ios ~/Projects/cogi_ios
```
(git хранит историю внутри `.git`, имя папки не важно — перенос безопасен.)

- [ ] **Step 3: Проверка**

Run: `cd ~/Projects/cogi_ios && git status --short && git log --oneline -1`
Expected: репозиторий читается по новому пути, история на месте.

- [ ] **Step 4: Сборка на устройстве (пользователь)**

Пользователь: открыть `~/Projects/cogi_ios/Cogi/Cogi.xcodeproj`, ⌘R. Ожидаем: успешная сборка по новому пути.

(Коммита нет — `mv` папки не меняет содержимое репозитория.)

---

## Task 6: Обновить пути и имя в документации/памяти (репо `abc_app`)

**Files:**
- Modify: `/Users/bulat/Projects/abc_app/CLAUDE.md`
- Modify: memory-файлы под `/Users/bulat/.claude/projects/-Users-bulat-Projects-abc-app/memory/`, ссылающиеся на старый путь

- [ ] **Step 1: Найти все вхождения старого пути и имени**

Run: `grep -rn "abc_app_ios\|CBTAnalyzer" /Users/bulat/Projects/abc_app/CLAUDE.md`
Run: `grep -rln "abc_app_ios" /Users/bulat/.claude/projects/-Users-bulat-Projects-abc-app/memory/`

- [ ] **Step 2: Обновить `CLAUDE.md`**

Заменить пути `~/Projects/abc_app_ios/` → `~/Projects/cogi_ios/` (и `CBTAnalyzer/CBTAnalyzer/ContentView.swift` → `Cogi/Cogi/ContentView.swift` в путях). Упоминания display-имени iOS-приложения (`CBTAnalyzer` как имя приложения) — на «Cogi». Концептуальное имя продукта/бэкенда «CBT Thought Analyzer» оставить как есть (вне scope).

- [ ] **Step 3: Обновить memory-файлы**

В найденных на Step 1 memory-файлах заменить путь `~/Projects/abc_app_ios` → `~/Projects/cogi_ios`. Если упоминается старый путь к `ContentView.swift` — обновить на `Cogi/Cogi/ContentView.swift`.

- [ ] **Step 4: Проверка отсутствия остатков пути**

Run: `grep -rn "abc_app_ios" /Users/bulat/Projects/abc_app/CLAUDE.md /Users/bulat/.claude/projects/-Users-bulat-Projects-abc-app/memory/`
Expected: пусто.

- [ ] **Step 5: Commit (репо `abc_app`)**

```bash
cd /Users/bulat/Projects/abc_app
git add CLAUDE.md
git commit -m "docs: rename iOS app/path to Cogi / cogi_ios"
```
(Memory-файлы вне git-репо `abc_app` — отдельный коммит не нужен, они под `~/.claude`.)

---

## Финальная верификация

- [ ] **Сборка на устройстве** (пользователь): `~/Projects/cogi_ios/Cogi/Cogi.xcodeproj`, схема **Cogi**, ⌘R → `** BUILD SUCCEEDED **`.
- [ ] **Домашний экран**: подпись под иконкой — **«Cogi»**.
- [ ] **Данные целы**: сохранённые мысли (вкладка «Сохранено») на месте; выбранный язык не сбросился (ключи `cbt.*` и bundle ID не менялись).
- [ ] **Bundle ID не изменился**: `grep "PRODUCT_BUNDLE_IDENTIFIER" ~/Projects/cogi_ios/Cogi/Cogi.xcodeproj/project.pbxproj` → всё ещё `com.bulsir.cbtanalyzer`.
- [ ] **Чистота имён**: `grep -rn "CBTAnalyzer" ~/Projects/cogi_ios/Cogi/` → только опциональные комментарии в pbxproj (если не заменены), функциональных вхождений нет.
- [ ] **Бэкенд не затронут**: `baseURL`/домен `api-abc.bulsir.com` без изменений, приложение анализирует мысли как раньше.
