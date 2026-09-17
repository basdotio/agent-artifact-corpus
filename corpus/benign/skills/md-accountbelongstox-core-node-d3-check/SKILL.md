---
name: d3-check
description: When working on pyapps/d3-check (Diablo III/IV macro and automation), prefer pycore libraries and put D3/D4 constants and variables in CONFIG (config package and providor/app_constants).
---

# d3-check Sub-App Skill

Use this skill when editing or adding code under **pyapps/d3-check** (Diablo III/IV macro, Battle.net automation, grid/screenshot, D4 extensions).

## When to Use

- Editing or adding code under `pyapps/d3-check/` (controller, d3utils, d4utils, ui, share, config, providor, etc.).
- Adding or changing Diablo III / Diablo IV / Battle.net related behavior.
- Choosing where to put constants, config, or shared utilities used by d3-check.

## Instructions

### 1. Reuse existing logic; no redundant definitions

- **Reuse before adding.** Before writing new code, search the codebase for existing logic that can be extended: same module, `d3utils` (e.g. ocr_helper, key_send, smart_echo, game_window_region, screenshot_provider), `timers.one_shot_tasks`, controller, pycore. Prefer extending or parameterizing existing functions/classes over adding new ones. Example: new one-off task → add to `timers.one_shot_tasks` or extend a similar `do_*`; new key send → extend `d3utils.key_send`; new crop region → extend `d3utils.d3u_common.game_window_region`.
- **No redundant definitions.** Do not duplicate stdlib or project-wide APIs: no local redefinitions of the same constant, same helper, or thin wrapper that only forwards. Use `providor.app_constants` for literals; use existing d3utils/pycore helpers; do not add a second constant or function that does the same thing in another file.

### 2. Prefer pycore

- Use pycore first; direct imports from `pycore.pyfoundations` / `pycore.pyutils`; no `providor.common_imports`.

### 3. Constants → CONFIG

- Literals → `providor.app_constants`; structured → `config` (unified_config, grid_config). No new literals in feature modules.

### 4. New standards

Add by priority: (1) `.cursor/rules` (2) `.cursor/skills` (3) `AGENTS.md`. No duplicate; canonical = `docs/PROJECT_STANDARDS.md`.

### 5. ttk Notebook Tab (equal height)

Selected/unselected same height. Ref: `ui/diablo3_macro_ui.py` (_apply_tab_layout, _apply_notebook_theme). Layout: Notebook.tab → padding → label only; padding identical for selected/!selected; expand map; tabmargins [1,3,1,0]; theme clam.

### 6. Threads

No cross-thread blocking (no queue.get/join at runtime); event center only; init all at startup; one-shot via timer_manager.submit_one_shot; native Thread (run() implements loop). See `docs/THREAD_BUS_AND_REGISTRY.md`.

### 7. No secondary encapsulation

No re-exports, wrappers, or one-class-forwards-to-another. Direct calls and imports only.
- **Imports:** pycore direct; constants from `providor.app_constants`; shared data from `share.game_interface_data`/`share.project_path` (迁移后 `share.values`); shared functions from `share.common`; D3 matcher from `d3utils.d3_scaled_template_matcher`; controller from `controller.ctl_func.*`; grid from `config.grid_config.get_grid_config()`. See PROJECT_STANDARDS §1.3.
- **One-shot:** `timers.timer_manager.submit_one_shot` + **`timers.one_shot_tasks.do_*`** only.
- **Do not** add wrapper functions or classes that only forward one layer.

### 8. Offset values

Subtract border → compute (content scale) → add border back. Frame fixed; content scales. No raw ratio without subtract/add border.

### 9. Prompt persistence

d3-check prompts → `pyapps/d3-check/.prompts/` (append log or timestamped file).

### 10. Change checklist (every edit)

(1) Redundant → merge. (2) Similar existing code → extend, do not duplicate. (3) Architecture → fit event center, CONFIG, direct imports. Apply to current diff.

### 11. Exception handling: remove unnecessary catch

- **Remove try/except unless truly required.** Keep catch only where necessary for basic program operation: e.g. websocket/network lifecycle, task/worker thread so one failure does not kill the process, Tk lifecycle (`tk.TclError` when widget may be destroyed), queue (`queue.Full`/`queue.Empty` in producer/consumer), COM/OS (e.g. `CoInitialize`), or similar. Else let exceptions propagate so failures are visible.
- **No broad catch that only logs or passes.** Do not add or keep `except Exception:` that only `pass` or log; narrow to specific exception types and handle only where required (UI teardown, queues, websocket, signal handlers).

### 12. Updating rules/skills

Check existing rules/skills/AGENTS; no conflict or duplicate; merge into one; canonical = PROJECT_STANDARDS.md.

### 13. How to update Cursor skills (规范)

Per Cursor docs (https://docs.cursor.com/context/skills):

- **Location:** Skills live under `.cursor/skills/<skill-name>/`. Each skill is a folder that must contain `SKILL.md`. Optional: `scripts/`, `references/`, `assets/`.
- **SKILL.md format:** YAML frontmatter (required: `name`, `description`) then Markdown body. Use sections such as "When to Use" and "Instructions". Keep `name` matching the parent folder (e.g. `d3-check`).
- **Adding or changing a norm:** (1) Add or edit the relevant subsection under Instructions in this SKILL.md. (2) If it is a project-wide standard, also add to `.cursor/rules` (e.g. `d3-check.mdc`) and keep `docs/PROJECT_STANDARDS.md` as canonical. (3) No duplicate wording across rules/skills/AGENTS; reference by section (e.g. §11) where possible.

### 15. Flow library vs. controllers（流程类库 vs 第三方）

- **单一流程类库**：流程开关与所有步骤/节点状态只由 `d3utils.rosbot_flow*` 持有（见 `docs/FLOW_STATE_OWNERSHIP_DESIGN.md`、`docs/FLOW_ARCHITECTURE_DIRECTORY.md`、`docs/FLOW_IMPLEMENTATION_PROGRESS.md`）。  
  - BN-only：`d3utils/rosbot_flow/flow_bn_only_state.py` + `flow_bn_only.py`  
  - Flow-master：`d3utils/rosbot_flow/flow_master_driver.py` + `extension_flow_state.py`
- **Tick 入口职责**：`d3utils.rosbot_task_processor.process_task()` 只读 `rosbot_flow_state`（flow_master_enabled / bn_only_enabled 等）并根据二次读结果调用 `tick_bn_only_flow()` / `tick_flow_master()`；**不在此新建流程状态**。
- **controller / timers / UI 一律视为第三方**：例如 `controller/login_try_screenshot_controller.py`、`timers/one_shot_tasks.py`、`ui/panels/*`：  
  - 只能调用 flow 层公开的 API（tick、F 步、BN helper 等），  
  - **不得**自行维护 flow_master/bn_only/BN 步骤/extension_phase 等流程状态，也不得在流程外直接改这些状态。
- 若需要新增流程步骤或状态：**只在 `d3utils.rosbot_flow*` 内扩展**，并同步上述三份文档；不要在 controller / timers / UI 里「补一个状态变量」。

### 14. Code language and i18n (PROJECT_STANDARDS §11)

- **Code**: Comments, docstrings, log messages, and identifiers in **English**.
- **User-facing text**: Use **i18n** (e.g. `i18n_manager.get_ui_text(...)`); do not hardcode Chinese or other locale strings in feature code.
- **Constants excepted**: Literal constants used for matching (e.g. UI keywords, window titles in `providor.constants`) remain as-is; do not change them for “code in English.”

- **i18n single place**: Import only `from providor.i18n_manager import i18n_manager`; single init in providor.
- **Reference UI JSON**: Docs reference JSON (e.g. Battle.net UI snapshot) is for human reference only; do not load at runtime; hardcode detection features in code (providor.constants).

### 16. Summary

| Need | Where |
|------|--------|
| Constants | `providor.app_constants` |
| Config | `config` (unified_config, grid_config) |
| Shared data | share/values (§1.3); 迁移前 share 根 |
| Shared functions | share/common (§1.3) |
| One-shot | timers.one_shot_tasks.do_* |
| Lifecycle/threads/events | runtime; CODE_TREE.md |
| All standards | **docs/PROJECT_STANDARDS.md** |
| Code language / i18n | §14 = PROJECT_STANDARDS §11: code English; UI via i18n; constants excepted |
| i18n / reference JSON | §14: providor.i18n_manager only; do not load reference UI JSON; hardcode features |
| Threads | THREAD_BUS_AND_REGISTRY.md |
| Exception handling | §11: remove unnecessary catch; keep only websocket/task thread/Tk/queue/COM/network essentials |
| Updating Cursor skills | §13: `.cursor/skills/<name>/SKILL.md`; frontmatter name+description; sync rules, PROJECT_STANDARDS |
