# HTML Preview Structure & Design System

Complete spec for generating plan preview HTML. Follow this structure exactly. Every preview = one self-contained `.html` file, zero external dependencies.

## Document Shell

```html
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{PROJECT_NAME}} — Plan Preview</title>
  <style>/* ALL CSS INLINE — see § CSS below */</style>
</head>
<body>
  <header><!-- project title, metadata bar, theme toggle --></header>
  <nav><!-- tab bar --></nav>
  <main><!-- tab panels --></main>
  <footer><!-- generated timestamp, version --></footer>
  <script>/* ALL JS INLINE — see § JS below */</script>
</body>
</html>
```

## Header

```html
<header class="pp-header">
  <div class="pp-header-left">
    <h1 class="pp-title">{{PROJECT_NAME}}</h1>
    <p class="pp-subtitle">{{PROJECT_DESCRIPTION}}</p>
  </div>
  <div class="pp-header-right">
    <div class="pp-progress">
      <div class="pp-progress-bar" style="width: {{PERCENT}}%"></div>
      <span class="pp-progress-label">{{DONE}}/{{TOTAL}} phases</span>
    </div>
    <div class="pp-meta">
      <span class="pp-badge pp-badge--{{SCOPE}}">{{SCOPE}}</span>
      <span class="pp-meta-item">Generated: {{TIMESTAMP}}</span>
    </div>
    <button class="pp-theme-toggle" onclick="toggleTheme()" title="Toggle theme">◐</button>
  </div>
</header>
```

## Tab Navigation

Five top-level tabs. Active tab gets `aria-selected="true"` + `pp-tab--active` class.

```html
<nav class="pp-tabs" role="tablist">
  <button role="tab" class="pp-tab pp-tab--active" data-panel="overview">Overview</button>
  <button role="tab" class="pp-tab" data-panel="architecture">Architecture</button>
  <button role="tab" class="pp-tab" data-panel="sequence">Build Sequence</button>
  <button role="tab" class="pp-tab" data-panel="phases">Phases</button>
  <button role="tab" class="pp-tab" data-panel="status">Status</button>
</nav>
```

## Tab Panels

### Overview Panel

Project summary dashboard. Quick-scan in 30 seconds.

```html
<section class="pp-panel" id="panel-overview" role="tabpanel">
  <div class="pp-grid pp-grid--stats">
    <div class="pp-stat">
      <span class="pp-stat-value">{{TOTAL_PHASES}}</span>
      <span class="pp-stat-label">Phases</span>
    </div>
    <div class="pp-stat">
      <span class="pp-stat-value">{{DONE_PHASES}}</span>
      <span class="pp-stat-label">Complete</span>
    </div>
    <div class="pp-stat">
      <span class="pp-stat-value">{{BLOCKED_PHASES}}</span>
      <span class="pp-stat-label">Blocked</span>
    </div>
    <div class="pp-stat">
      <span class="pp-stat-value">{{WAVE_COUNT}}</span>
      <span class="pp-stat-label">Waves</span>
    </div>
  </div>

  <!-- Phase status breakdown -->
  <div class="pp-status-grid">
    {{#each phase}}
    <div class="pp-phase-pill pp-phase-pill--{{status}}">
      <span class="pp-phase-pill-id">{{id}}</span>
      <span class="pp-phase-pill-title">{{title}}</span>
    </div>
    {{/each}}
  </div>

  <!-- Key decisions if available -->
  <div class="pp-section" data-collapsible>
    <h3 class="pp-section-title">Key Decisions</h3>
    <div class="pp-section-body">
      <ul class="pp-decisions">
        {{#each decision}}
        <li><strong>{{what}}</strong> — {{why}}</li>
        {{/each}}
      </ul>
    </div>
  </div>
</section>
```

### Architecture Panel

Tech stack, system design, ASCII art diagrams.

```html
<section class="pp-panel" id="panel-architecture" role="tabpanel" hidden>
  <!-- Tech stack badges -->
  <div class="pp-stack-badges">
    {{#each stack}}
    <span class="pp-badge pp-badge--stack">{{name}}</span>
    {{/each}}
  </div>

  <!-- Architecture diagram (ASCII preserved) -->
  <div class="pp-section" data-collapsible>
    <h3 class="pp-section-title">System Design</h3>
    <div class="pp-section-body">
      <pre class="pp-ascii">{{ASCII_DIAGRAM}}</pre>
    </div>
  </div>

  <!-- Architecture decisions -->
  <div class="pp-section" data-collapsible>
    <h3 class="pp-section-title">Architecture Decisions</h3>
    <div class="pp-section-body">
      {{#each arch_decision}}
      <div class="pp-decision-card">
        <h4>{{title}}</h4>
        <p class="pp-decision-rationale">{{rationale}}</p>
        <div class="pp-decision-tradeoff">
          <span class="pp-pro">✓ {{pro}}</span>
          <span class="pp-con">✗ {{con}}</span>
        </div>
      </div>
      {{/each}}
    </div>
  </div>
</section>
```

### Build Sequence Panel

Visual timeline of phases with dependencies and wave grouping.

```html
<section class="pp-panel" id="panel-sequence" role="tabpanel" hidden>
  {{#each wave}}
  <div class="pp-wave">
    <div class="pp-wave-header">
      <h3>Wave {{number}}</h3>
      <span class="pp-wave-badge">{{phase_count}} phases{{#if parallel}} · parallel{{/if}}</span>
    </div>
    <div class="pp-wave-phases">
      {{#each phase}}
      <div class="pp-sequence-card pp-sequence-card--{{status}}">
        <div class="pp-sequence-card-header">
          <span class="pp-phase-id">{{id}}</span>
          <span class="pp-badge pp-badge--{{status}}">{{status}}</span>
          {{#if mode}}<span class="pp-badge pp-badge--mode">{{mode}}</span>{{/if}}
        </div>
        <h4 class="pp-sequence-card-title">{{title}}</h4>
        <p class="pp-sequence-card-desc">{{description}}</p>
        {{#if depends_on}}
        <div class="pp-deps">
          Depends on: {{#each dep}}<span class="pp-dep-link">{{this}}</span>{{/each}}
        </div>
        {{/if}}
      </div>
      {{/each}}
    </div>
  </div>
  {{/each}}
</section>
```

### Phases Panel

Detailed per-phase breakdown. Each phase = expandable card.

```html
<section class="pp-panel" id="panel-phases" role="tabpanel" hidden>
  {{#each phase}}
  <details class="pp-phase-detail" {{#if in_progress}}open{{/if}}>
    <summary class="pp-phase-summary">
      <span class="pp-phase-id">{{id}}</span>
      <span class="pp-badge pp-badge--{{status}}">{{status}}</span>
      <span class="pp-badge pp-badge--{{priority}}">{{priority}}</span>
      <h3>{{title}}</h3>
      <span class="pp-phase-meta">{{task_count}} tasks · {{file_count}} files</span>
    </summary>

    <div class="pp-phase-body">
      <!-- Goal -->
      <div class="pp-subsection">
        <h4>Goal</h4>
        <p>{{goal}}</p>
      </div>

      <!-- Tasks -->
      <div class="pp-subsection">
        <h4>Tasks</h4>
        {{#each task}}
        <div class="pp-task">
          <div class="pp-task-header">
            <strong>{{title}}</strong>
            <span class="pp-badge pp-badge--model">{{model}}</span>
          </div>
          <div class="pp-task-files">
            {{#each file}}<code class="pp-file">{{this}}</code>{{/each}}
          </div>
          <div class="pp-task-acs">
            <h5>Acceptance Criteria</h5>
            <ul>
              {{#each ac}}<li>{{this}}</li>{{/each}}
            </ul>
          </div>
        </div>
        {{/each}}
      </div>

      <!-- Risks -->
      {{#if risks}}
      <div class="pp-subsection">
        <h4>Risks</h4>
        <ul class="pp-risks">
          {{#each risk}}<li class="pp-risk">{{this}}</li>{{/each}}
        </ul>
      </div>
      {{/if}}

      <!-- Consequence Analysis -->
      <div class="pp-subsection pp-consequences">
        <h4>Consequence Analysis</h4>
        <div class="pp-consequence-grid">
          <div class="pp-consequence pp-consequence--1st">
            <h5>1st Order <span class="pp-consequence-tag">Direct</span></h5>
            <ul>{{#each first_order}}<li>{{this}}</li>{{/each}}</ul>
          </div>
          <div class="pp-consequence pp-consequence--2nd">
            <h5>2nd Order <span class="pp-consequence-tag">Adjacent</span></h5>
            <ul>{{#each second_order}}<li>{{this}}</li>{{/each}}</ul>
          </div>
          <div class="pp-consequence pp-consequence--3rd">
            <h5>3rd Order <span class="pp-consequence-tag">Downstream</span></h5>
            <ul>{{#each third_order}}<li>{{this}}</li>{{/each}}</ul>
          </div>
        </div>
      </div>

      <!-- Smoke Tests -->
      {{#if smoke}}
      <div class="pp-subsection">
        <h4>Smoke Tests</h4>
        <pre class="pp-code"><code>{{smoke}}</code></pre>
      </div>
      {{/if}}
    </div>
  </details>
  {{/each}}
</section>
```

### Status Panel

Current project state + action items.

```html
<section class="pp-panel" id="panel-status" role="tabpanel" hidden>
  <div class="pp-status-current">
    <h3>Current Position</h3>
    <div class="pp-kv-grid">
      <div class="pp-kv"><span class="pp-kv-key">Phase</span><span class="pp-kv-val">{{current_phase}}</span></div>
      <div class="pp-kv"><span class="pp-kv-key">Status</span><span class="pp-kv-val">{{current_status}}</span></div>
      <div class="pp-kv"><span class="pp-kv-key">Last Action</span><span class="pp-kv-val">{{last_action}}</span></div>
    </div>
  </div>

  {{#if blockers}}
  <div class="pp-status-blockers">
    <h3>⚠ Blockers</h3>
    <ul>{{#each blocker}}<li>{{this}}</li>{{/each}}</ul>
  </div>
  {{/if}}

  <div class="pp-status-next">
    <h3>Next Action</h3>
    <p>{{next_action}}</p>
  </div>
</section>
```

## CSS Design System

All CSS goes in a single `<style>` block in `<head>`. Key tokens:

```css
:root {
  /* Light theme (default) */
  --pp-bg: #ffffff;
  --pp-surface: #f6f8fa;
  --pp-surface-hover: #eaeef2;
  --pp-border: #d0d7de;
  --pp-text: #1f2328;
  --pp-text-muted: #656d76;
  --pp-accent: #0969da;
  --pp-success: #1a7f37;
  --pp-warning: #9a6700;
  --pp-danger: #d1242f;
  --pp-info: #0969da;

  /* Spacing */
  --pp-space-xs: 4px;
  --pp-space-sm: 8px;
  --pp-space-md: 16px;
  --pp-space-lg: 24px;
  --pp-space-xl: 32px;

  /* Typography — 16px minimum enforced */
  --pp-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
  --pp-font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  --pp-text-sm: 1rem;
  --pp-text-base: 1.0625rem;
  --pp-text-lg: 1.25rem;
  --pp-text-xl: 1.5rem;
  --pp-text-2xl: 2rem;

  /* Readability */
  --pp-content-max: 65ch;

  /* Borders */
  --pp-radius: 6px;
  --pp-radius-lg: 12px;
}

[data-theme="dark"] {
  --pp-bg: #0d1117;
  --pp-surface: #161b22;
  --pp-surface-hover: #1c2129;
  --pp-border: #30363d;
  --pp-text: #e6edf3;
  --pp-text-muted: #8b949e;
  --pp-accent: #58a6ff;
  --pp-success: #3fb950;
  --pp-warning: #d29922;
  --pp-danger: #f85149;
  --pp-info: #58a6ff;
}

/* --- Style presets (override tokens after :root) --- */

/* Editorial: serif headings, generous whitespace, muted palette */
[data-style="editorial"] {
  --pp-font: 'Georgia', 'Times New Roman', serif;
  --pp-space-md: 20px;
  --pp-space-lg: 32px;
  --pp-space-xl: 48px;
  --pp-radius: 2px;
  --pp-radius-lg: 4px;
}

/* Terminal: dark bg, monospace, green/amber accents */
[data-style="terminal"] {
  --pp-font: var(--pp-font-mono);
  --pp-bg: #0a0a0a;
  --pp-surface: #111111;
  --pp-surface-hover: #1a1a1a;
  --pp-border: #333333;
  --pp-text: #e0e0e0;
  --pp-text-muted: #888888;
  --pp-accent: #4ec9b0;
  --pp-success: #6a9955;
  --pp-warning: #dcdcaa;
  --pp-danger: #f44747;
  --pp-radius: 0;
  --pp-radius-lg: 0;
}
```

### Key Component Styles

```css
/* Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--pp-font);
  font-size: var(--pp-text-base);
  color: var(--pp-text);
  background: var(--pp-bg);
  line-height: 1.6;
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--pp-space-lg);
}

/* Readability: text centered in cards, max 65ch */
.pp-card-text {
  max-width: var(--pp-content-max);
  margin-left: auto;
  margin-right: auto;
}

/* Header */
.pp-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: var(--pp-space-lg);
  border-bottom: 1px solid var(--pp-border);
  margin-bottom: var(--pp-space-lg);
}
.pp-title { font-size: var(--pp-text-2xl); font-weight: 700; }
.pp-subtitle { color: var(--pp-text-muted); margin-top: var(--pp-space-xs); }

/* Progress bar */
.pp-progress {
  width: 200px;
  height: 8px;
  background: var(--pp-border);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}
.pp-progress-bar {
  height: 100%;
  background: var(--pp-success);
  border-radius: 4px;
  transition: width 0.3s ease;
}
.pp-progress-label {
  font-size: var(--pp-text-sm);
  color: var(--pp-text-muted);
  margin-top: var(--pp-space-xs);
  display: block;
}

/* Tabs */
.pp-tabs {
  display: flex;
  gap: var(--pp-space-xs);
  border-bottom: 1px solid var(--pp-border);
  margin-bottom: var(--pp-space-lg);
  overflow-x: auto;
}
.pp-tab {
  padding: var(--pp-space-sm) var(--pp-space-md);
  background: none;
  border: none;
  color: var(--pp-text-muted);
  cursor: pointer;
  font-size: var(--pp-text-base);
  font-family: var(--pp-font);
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: color 0.2s, border-color 0.2s;
}
.pp-tab:hover { color: var(--pp-text); }
.pp-tab--active {
  color: var(--pp-accent);
  border-bottom-color: var(--pp-accent);
  font-weight: 600;
}

/* Badges */
.pp-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--pp-text-sm);
  font-weight: 500;
  white-space: nowrap;
}
.pp-badge--todo { background: var(--pp-border); color: var(--pp-text-muted); }
.pp-badge--in-progress { background: rgba(88,166,255,0.15); color: var(--pp-accent); }
.pp-badge--done { background: rgba(63,185,80,0.15); color: var(--pp-success); }
.pp-badge--blocked { background: rgba(248,81,73,0.15); color: var(--pp-danger); }
.pp-badge--skipped { background: var(--pp-surface); color: var(--pp-text-muted); opacity: 0.6; }
.pp-badge--P0, .pp-badge--critical { background: rgba(248,81,73,0.15); color: var(--pp-danger); }
.pp-badge--P1, .pp-badge--high { background: rgba(210,153,34,0.15); color: var(--pp-warning); }
.pp-badge--P2, .pp-badge--medium { background: rgba(88,166,255,0.15); color: var(--pp-accent); }
.pp-badge--P3, .pp-badge--low { background: var(--pp-surface); color: var(--pp-text-muted); }
.pp-badge--stack { background: var(--pp-surface); color: var(--pp-text); border: 1px solid var(--pp-border); }
.pp-badge--model { background: rgba(63,185,80,0.1); color: var(--pp-success); font-family: var(--pp-font-mono); font-size: var(--pp-text-sm); }
.pp-badge--mode { background: rgba(210,153,34,0.1); color: var(--pp-warning); }
.pp-badge--production { background: rgba(248,81,73,0.15); color: var(--pp-danger); }
.pp-badge--scratch { background: rgba(210,153,34,0.15); color: var(--pp-warning); }

/* Stat grid */
.pp-grid--stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--pp-space-md);
  margin-bottom: var(--pp-space-lg);
}
.pp-stat {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  text-align: center;
}
.pp-stat-value { display: block; font-size: var(--pp-text-2xl); font-weight: 700; color: var(--pp-accent); }
.pp-stat-label { display: block; font-size: var(--pp-text-sm); color: var(--pp-text-muted); }

/* Phase pills (overview) */
.pp-status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--pp-space-sm);
  margin-bottom: var(--pp-space-lg);
}
.pp-phase-pill {
  display: flex;
  align-items: center;
  gap: var(--pp-space-sm);
  padding: var(--pp-space-xs) var(--pp-space-md);
  border-radius: var(--pp-radius);
  border: 1px solid var(--pp-border);
  font-size: var(--pp-text-sm);
}

/* Collapsible sections */
.pp-section { margin-bottom: var(--pp-space-md); }
.pp-section-title {
  cursor: pointer;
  user-select: none;
  font-size: var(--pp-text-lg);
  padding: var(--pp-space-sm) 0;
}
.pp-section-title::before { content: '▸ '; color: var(--pp-text-muted); }
.pp-section[data-open] .pp-section-title::before { content: '▾ '; }
.pp-section-body { display: none; padding-top: var(--pp-space-sm); }
.pp-section[data-open] .pp-section-body { display: block; }

/* Phase details (expandable cards) */
.pp-phase-detail {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius-lg);
  margin-bottom: var(--pp-space-md);
  overflow: hidden;
}
.pp-phase-detail[open] { border-color: var(--pp-accent); }
.pp-phase-summary {
  display: flex;
  align-items: center;
  gap: var(--pp-space-sm);
  padding: var(--pp-space-md);
  cursor: pointer;
  list-style: none;
}
.pp-phase-summary::-webkit-details-marker { display: none; }
.pp-phase-summary h3 { flex: 1; font-size: var(--pp-text-base); }
.pp-phase-body { padding: 0 var(--pp-space-md) var(--pp-space-md); max-width: var(--pp-content-max); margin: 0 auto; }
.pp-phase-id {
  font-family: var(--pp-font-mono);
  font-size: var(--pp-text-sm);
  color: var(--pp-text-muted);
  min-width: 2em;
}
.pp-phase-meta { font-size: var(--pp-text-sm); color: var(--pp-text-muted); }

/* Subsections inside phase */
.pp-subsection { margin-bottom: var(--pp-space-md); }
.pp-subsection h4 {
  font-size: var(--pp-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--pp-text-muted);
  margin-bottom: var(--pp-space-sm);
}

/* Tasks */
.pp-task {
  background: var(--pp-bg);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  margin-bottom: var(--pp-space-sm);
}
.pp-task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--pp-space-sm); }
.pp-task-files { display: flex; flex-wrap: wrap; gap: var(--pp-space-xs); margin-bottom: var(--pp-space-sm); }
.pp-file {
  font-family: var(--pp-font-mono);
  font-size: var(--pp-text-sm);
  background: var(--pp-surface);
  padding: 2px 6px;
  border-radius: 3px;
  color: var(--pp-accent);
}

/* Consequence cards */
.pp-consequence-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--pp-space-md);
}
.pp-consequence {
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  border-left: 3px solid;
}
.pp-consequence--1st { background: rgba(63,185,80,0.05); border-color: var(--pp-success); }
.pp-consequence--2nd { background: rgba(210,153,34,0.05); border-color: var(--pp-warning); }
.pp-consequence--3rd { background: rgba(248,81,73,0.05); border-color: var(--pp-danger); }
.pp-consequence h5 { font-size: var(--pp-text-sm); margin-bottom: var(--pp-space-sm); }
.pp-consequence-tag {
  font-size: var(--pp-text-sm);
  padding: 1px 6px;
  border-radius: 8px;
  margin-left: var(--pp-space-xs);
  vertical-align: middle;
}
.pp-consequence--1st .pp-consequence-tag { background: rgba(63,185,80,0.15); color: var(--pp-success); }
.pp-consequence--2nd .pp-consequence-tag { background: rgba(210,153,34,0.15); color: var(--pp-warning); }
.pp-consequence--3rd .pp-consequence-tag { background: rgba(248,81,73,0.15); color: var(--pp-danger); }
.pp-consequence ul { list-style: none; }
.pp-consequence li { padding-left: 1em; position: relative; font-size: var(--pp-text-sm); margin-bottom: var(--pp-space-xs); max-width: var(--pp-content-max); }
.pp-consequence--1st li::before { content: '✓'; position: absolute; left: 0; color: var(--pp-success); }
.pp-consequence--2nd li::before { content: '◆'; position: absolute; left: 0; color: var(--pp-warning); }
.pp-consequence--3rd li::before { content: '⚠'; position: absolute; left: 0; color: var(--pp-danger); }

/* Wave sections */
.pp-wave { margin-bottom: var(--pp-space-xl); }
.pp-wave-header {
  display: flex;
  align-items: center;
  gap: var(--pp-space-md);
  margin-bottom: var(--pp-space-md);
}
.pp-wave-header h3 { font-size: var(--pp-text-lg); }
.pp-wave-badge { font-size: var(--pp-text-sm); color: var(--pp-text-muted); }
.pp-wave-phases {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--pp-space-md);
}

/* Sequence card */
.pp-sequence-card {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  transition: border-color 0.2s;
}
.pp-sequence-card:hover { border-color: var(--pp-accent); }
.pp-sequence-card--in-progress { border-left: 3px solid var(--pp-accent); }
.pp-sequence-card--done { border-left: 3px solid var(--pp-success); opacity: 0.8; }
.pp-sequence-card--blocked { border-left: 3px solid var(--pp-danger); }
.pp-sequence-card-header { display: flex; gap: var(--pp-space-sm); align-items: center; margin-bottom: var(--pp-space-sm); }
.pp-sequence-card-title { font-weight: 600; margin-bottom: var(--pp-space-xs); }
.pp-sequence-card-desc { font-size: var(--pp-text-sm); color: var(--pp-text-muted); max-width: var(--pp-content-max); }
.pp-deps { font-size: var(--pp-text-sm); color: var(--pp-text-muted); margin-top: var(--pp-space-sm); }
.pp-dep-link {
  font-family: var(--pp-font-mono);
  color: var(--pp-accent);
  cursor: pointer;
}

/* KV grid (status panel) */
.pp-kv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--pp-space-sm); margin-bottom: var(--pp-space-lg); }
.pp-kv { background: var(--pp-surface); padding: var(--pp-space-md); border-radius: var(--pp-radius); border: 1px solid var(--pp-border); }
.pp-kv-key { display: block; font-size: var(--pp-text-sm); color: var(--pp-text-muted); margin-bottom: var(--pp-space-xs); }
.pp-kv-val { font-weight: 600; }

/* Code blocks */
.pp-code, .pp-ascii {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  font-family: var(--pp-font-mono);
  font-size: var(--pp-text-sm);
  overflow-x: auto;
  white-space: pre;
  line-height: 1.5;
}

/* Decision cards */
.pp-decision-card {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  margin-bottom: var(--pp-space-sm);
}
.pp-decision-rationale { color: var(--pp-text-muted); font-size: var(--pp-text-sm); margin: var(--pp-space-sm) 0; max-width: var(--pp-content-max); }
.pp-decision-tradeoff { display: flex; gap: var(--pp-space-md); font-size: var(--pp-text-sm); }
.pp-pro { color: var(--pp-success); }
.pp-con { color: var(--pp-danger); }

/* Blockers */
.pp-status-blockers {
  background: rgba(248,81,73,0.05);
  border: 1px solid var(--pp-danger);
  border-radius: var(--pp-radius);
  padding: var(--pp-space-md);
  margin-bottom: var(--pp-space-lg);
}
.pp-status-blockers h3 { color: var(--pp-danger); margin-bottom: var(--pp-space-sm); }

/* Theme toggle */
.pp-theme-toggle {
  background: var(--pp-surface);
  border: 1px solid var(--pp-border);
  color: var(--pp-text);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Footer */
footer {
  margin-top: var(--pp-space-xl);
  padding-top: var(--pp-space-md);
  border-top: 1px solid var(--pp-border);
  font-size: var(--pp-text-sm);
  color: var(--pp-text-muted);
  text-align: center;
}

/* Print */
@media print {
  :root { --pp-bg: #fff; --pp-surface: #f8f8f8; --pp-text: #000; --pp-text-muted: #666; --pp-border: #ddd; }
  body { max-width: 100%; padding: 0; }
  .pp-theme-toggle { display: none; }
  .pp-phase-detail { break-inside: avoid; }
  details[open] > .pp-phase-body { display: block !important; }
}

/* Responsive */
@media (max-width: 768px) {
  .pp-header { flex-direction: column; gap: var(--pp-space-md); }
  .pp-consequence-grid { grid-template-columns: 1fr; }
  .pp-wave-phases { grid-template-columns: 1fr; }
}
```

## JavaScript

Minimal JS for interactivity. No frameworks, no build step.

```javascript
// Tab switching
document.querySelectorAll('.pp-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.pp-tab').forEach(t => {
      t.classList.remove('pp-tab--active');
      t.removeAttribute('aria-selected');
    });
    document.querySelectorAll('.pp-panel').forEach(p => p.hidden = true);
    tab.classList.add('pp-tab--active');
    tab.setAttribute('aria-selected', 'true');
    document.getElementById('panel-' + tab.dataset.panel).hidden = false;
  });
});

// Collapsible sections
document.querySelectorAll('[data-collapsible]').forEach(section => {
  const title = section.querySelector('.pp-section-title');
  if (title) {
    // Start open by default
    section.setAttribute('data-open', '');
    title.addEventListener('click', () => {
      section.toggleAttribute('data-open');
    });
  }
});

// Theme toggle (light default)
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
  localStorage.setItem('pp-theme', html.getAttribute('data-theme'));
}

// Restore theme preference (default: light)
const saved = localStorage.getItem('pp-theme');
if (saved) document.documentElement.setAttribute('data-theme', saved);

// Keyboard navigation
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    const tabs = [...document.querySelectorAll('.pp-tab')];
    const active = tabs.findIndex(t => t.classList.contains('pp-tab--active'));
    const next = e.key === 'ArrowRight'
      ? (active + 1) % tabs.length
      : (active - 1 + tabs.length) % tabs.length;
    tabs[next].click();
    tabs[next].focus();
  }
});
```

## Design Token System

Styles are applied via `data-style` attribute on `<html>`. Three presets defined in CSS above: default (clean), `editorial`, `terminal`.

### Applying a style

```html
<html lang="en" data-theme="light" data-style="editorial">
```

No `data-style` attribute = Clean (default). Terminal preset forces dark theme regardless of `data-theme`.

### Custom design tokens

If user provides a `design-tokens.json` or CSS file, inject as inline `<style>` after the base tokens:

```html
<style>
  /* Base tokens (from preset) */
</style>
<style>
  /* Custom token overrides */
  :root {
    --pp-accent: #7c3aed;
    --pp-font: 'Inter', sans-serif;
    --pp-radius: 12px;
  }
</style>
```

Custom tokens override preset tokens. Any `--pp-*` variable can be overridden.

### Token reference

All overridable tokens:

| Token | Default (Clean) | Purpose |
|---|---|---|
| `--pp-bg` | #ffffff | Page background |
| `--pp-surface` | #f6f8fa | Card/panel background |
| `--pp-border` | #d0d7de | Borders and dividers |
| `--pp-text` | #1f2328 | Primary text |
| `--pp-text-muted` | #656d76 | Secondary text |
| `--pp-accent` | #0969da | Links, active states |
| `--pp-success` | #1a7f37 | Done, 1st order |
| `--pp-warning` | #9a6700 | In-progress, 2nd order |
| `--pp-danger` | #d1242f | Blocked, 3rd order |
| `--pp-font` | system stack | Body font family |
| `--pp-font-mono` | monospace stack | Code font family |
| `--pp-text-sm` | 1rem (16px) | Smallest allowed size |
| `--pp-text-base` | 1.0625rem (17px) | Body text |
| `--pp-radius` | 6px | Border radius |
| `--pp-content-max` | 65ch | Max text width in cards |

## Template Mustache Notation

The `{{...}}` and `{{#each}}` blocks in this document are **illustrative only**. When generating the actual HTML, Claude replaces these with real data inline. No template engine needed — Claude generates the final HTML directly with all data embedded.

If data is missing for a section, render a placeholder:
```html
<p class="pp-empty">Not yet planned — this section will be populated as the project evolves.</p>
```

Style for empty states:
```css
.pp-empty { color: var(--pp-text-muted); font-style: italic; padding: var(--pp-space-md); text-align: center; }
```
