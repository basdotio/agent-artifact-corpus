---
name: code-quality-report
description: Generate a universal code quality report (A-E grades) for any project, any language, zero external dependencies. Analyzes 7 dimensions (Maintainability, Reliability, Security, Test Coverage, Architecture, Documentation, DevOps) and outputs a self-contained HTML report.
---
Generate a universal code quality report for any project, any language, zero dependencies.

## Overview

This skill analyzes any git repository and produces a self-contained HTML report with grades A through E across 7 universal dimensions. No external scripts, no language-specific tooling required.

## Step 1: Project Discovery

Run these commands to detect the project:

```bash
# Enumerate all tracked source files and count by extension
git ls-files --cached | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
```

```bash
# Detect CI configuration
git ls-files -- '.github/workflows/*.yml' '.github/workflows/*.yaml' '.gitlab-ci.yml' 'Jenkinsfile' '.circleci/*' '.travis.yml' 'bitbucket-pipelines.yml' 'azure-pipelines.yml'
```

From the extension counts, identify:
- **Primary language(s)**: largest extension groups (py=Python, go=Go, rs=Rust, ts/tsx=TypeScript, js/jsx=JavaScript, java=Java, cpp/c/h=C/C++, rb=Ruby, swift=Swift, kt=Kotlin)
- **Total source files**: sum of source extensions (exclude .json, .md, .yml, .yaml, .toml, .lock, .svg, .png, .jpg, .gif, .ico)
- **Project name**: from the git remote URL or directory name

## Step 2: Automated Metrics Collection

Run these commands (in parallel where possible):

```bash
# File sizes — top 20 largest source files
git ls-files -- '*.py' '*.go' '*.rs' '*.ts' '*.tsx' '*.js' '*.jsx' '*.java' '*.cpp' '*.c' '*.h' '*.rb' '*.swift' '*.kt' '*.cs' '*.php' | head -200 | xargs wc -l 2>/dev/null | sort -rn | head -21
```

```bash
# TODO/FIXME/HACK/XXX count
git grep -c -E 'TODO|FIXME|HACK|XXX' -- '*.py' '*.go' '*.rs' '*.ts' '*.tsx' '*.js' '*.jsx' '*.java' '*.cpp' '*.c' '*.h' '*.rb' '*.swift' '*.kt' '*.cs' '*.php' 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}'
```

```bash
# Test file count and source file count for ratio
TEST_COUNT=$(git ls-files -- '*test*' '*spec*' '*/tests/*' '*/test/*' '*/__tests__/*' '*_test.go' '*_test.py' '*Test.java' '*_spec.rb' | wc -l)
SRC_COUNT=$(git ls-files -- '*.py' '*.go' '*.rs' '*.ts' '*.tsx' '*.js' '*.jsx' '*.java' '*.cpp' '*.c' '*.rb' '*.swift' '*.kt' '*.cs' '*.php' | wc -l)
echo "TEST_COUNT=$TEST_COUNT SRC_COUNT=$SRC_COUNT RATIO=$(echo "scale=2; $TEST_COUNT / ($SRC_COUNT + 1)" | bc 2>/dev/null || echo 'N/A')"
```

```bash
# Secrets scan (patterns that suggest hardcoded secrets)
git grep -n -E '(password|secret|api.?key|token|private.?key)\s*[:=]\s*["\x27][^\"\x27]{8,}' -- ':!*.lock' ':!*.md' ':!*.txt' ':!package-lock.json' ':!yarn.lock' ':!go.sum' 2>/dev/null | head -20
```

```bash
# Dangerous patterns (eval, exec, innerHTML, SQL concatenation)
git grep -c -E '(eval\(|exec\(|innerHTML\s*=|\.innerHtml|dangerouslySetInnerHTML|raw\s+SQL|string\.Format.*SELECT|f".*SELECT|".*SELECT.*"\s*\+)' -- '*.py' '*.go' '*.rs' '*.ts' '*.tsx' '*.js' '*.jsx' '*.java' '*.cpp' '*.c' '*.rb' '*.cs' '*.php' 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}'
```

```bash
# Last dependency update and commit frequency
git log --since="1 year ago" --oneline -- '*requirements*.txt' 'go.mod' 'Cargo.toml' 'package.json' 'pom.xml' 'Gemfile' '*.csproj' 'Pipfile' 'pyproject.toml' 2>/dev/null | head -5
git log --since="3 months ago" --oneline 2>/dev/null | wc -l
```

```bash
# Directory structure depth
git ls-files | awk -F/ '{print NF-1}' | sort -rn | head -1
```

```bash
# README check
git ls-files -- 'README*' 'readme*' | head -5
# Contributing/Changelog check
git ls-files -- 'CONTRIBUTING*' 'contributing*' 'CHANGELOG*' 'changelog*' 'CHANGES*' 'HISTORY*' | head -5
```

## Step 3: LLM Analysis (File Reading)

Read these files (50-line cap for large files, full read for files under 100 lines):

1. **Top 3 largest source files** — assess nesting depth, error handling patterns, code duplication
2. **README** — assess completeness (sections: description, install, usage, contributing, license, architecture)
3. **CI config** (first workflow file found) — assess lint/test/deploy steps
4. **Entry point** (main.py, main.go, src/index.ts, src/main.rs, App.java, etc.) — assess architecture

Based on file reading, assess these LLM-judgment metrics:
- **Error handling quality**: none/swallowed → some → consistent → comprehensive → comprehensive+recovery
- **Architecture separation**: monolithic → mixed → some separation → clear layers → clean architecture
- **Code duplication estimate**: >30% → 20-30% → 10-20% → 5-10% → <5%
- **Nesting depth**: count files with >4 levels of nesting from the files you read

## Step 4: Grade Computation

Apply these threshold tables. Per-dimension grade = minimum grade across all sub-metrics within that dimension. Missing/unverifiable data = C (not A).

### 1. Maintainability
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| Max file LOC | >1500 | 800-1500 | 400-800 | 200-400 | <200 |
| Avg file LOC (top-20) | >500 | 300-500 | 150-300 | 80-150 | <80 |
| Deep nesting (>4 levels) | >20 files | 10-20 | 5-10 | 1-4 | 0 |
| Duplication (LLM-estimated) | >30% | 20-30% | 10-20% | 5-10% | <5% |

Language-specific bonuses (upgrade +1, never downgrade): TS strict mode, Python type hints (mypy config present), Go vet in CI, Rust clippy in CI. Report as notes.

### 2. Reliability
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| TODO/FIXME/HACK count | >50 | 20-50 | 10-20 | 3-10 | <3 |
| Error handling (LLM) | none/swallowed | some | consistent | comprehensive | comprehensive+recovery |
| Dead code signals (LLM) | extensive | moderate | some | minimal | none |

### 3. Security
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| Hardcoded secrets | found | suspicious patterns | .env no gitignore | .env+gitignored | vault/secrets mgr |
| Dangerous patterns | many (>10) | some (5-10) | few (1-4) | none detected | none+CSP/sandbox |
| Dep freshness (git log) | >2yr no updates | >1yr | 6-12mo | 3-6mo | <3mo or dependabot |

### 4. Test Coverage
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| Test file count | 0 | 1-5 | 5-15 | 15-50 | >50 |
| Test-to-source ratio | 0 | <0.1 | 0.1-0.3 | 0.3-0.7 | >0.7 |
| Tests in CI | no CI | CI no tests | tests in CI | tests+block merge | tests+coverage gate |

### 5. Architecture
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| Directory structure | flat | some org | feature-based | layered+feature | enforced boundaries |
| Max directory depth | >8 | 6-8 | 4-6 | 3-4 | 2-3 |
| Separation of concerns | monolithic | mixed | some separation | clear layers | clean architecture |

### 6. Documentation
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| README | missing | stub (<5 lines) | basic (setup) | comprehensive | comprehensive+arch |
| Contributing/changelog | none | none | one present | both | both+detailed |
| Inline comment ratio | 0% | <2% | 2-5% | 5-10% | 10-15% |

### 7. DevOps & CI
| Metric | E | D | C | B | A |
|--------|---|---|---|---|---|
| CI present | no | manual only | auto on push | multi-stage | full pipeline |
| Lint in CI | no | no | yes | yes+autofix | yes+block merge |
| Deploy automation | none | manual | semi-auto | auto on merge | auto+rollback+preview |

### Overall Grade
**Overall = minimum across all 7 dimensions.** This is the SonarQube quality gate model — one weak area drags the overall grade down to incentivize balanced improvement.

## Step 5: Generate HTML Report

Generate a self-contained HTML file at `reports/code-quality-report.html`.

First, try to read the CSS asset:
```bash
# Try shared repo location
cat "$(git rev-parse --show-toplevel 2>/dev/null)/../claude-skills/assets/report-v3.css" 2>/dev/null || \
cat "$HOME/.claude/assets/report-v3.css" 2>/dev/null || \
echo "CSS_NOT_FOUND"
```

If CSS is found, inline it into the HTML `<style>` tag. If not found, use this minimal fallback:

```css
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#09090f;--bg2:#111118;--bg3:#18181f;--fg:#e8e8f0;--fg2:#8888a0;--fg3:#5c5c72;--green:#34d399;--yellow:#fbbf24;--orange:#fb923c;--red:#f87171;--blue:#60a5fa;--border:rgba(255,255,255,.06);--radius:10px}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--fg);max-width:900px;margin:0 auto;padding:2rem;line-height:1.6}
h1{font-size:1.8rem;font-weight:800;margin-bottom:1rem}
h2{font-size:1.2rem;margin:2rem 0 1rem;padding-bottom:.5rem;border-bottom:1px solid var(--border)}
.grade-box{display:inline-flex;align-items:center;justify-content:center;width:64px;height:64px;border-radius:16px;font-size:1.75rem;font-weight:800}
.grade-A{background:rgba(52,211,153,.1);color:var(--green);border:2px solid rgba(52,211,153,.3)}
.grade-B{background:rgba(96,165,250,.1);color:var(--blue);border:2px solid rgba(96,165,250,.3)}
.grade-C{background:rgba(251,191,36,.1);color:var(--yellow);border:2px solid rgba(251,191,36,.3)}
.grade-D{background:rgba(251,146,60,.1);color:var(--orange);border:2px solid rgba(251,146,60,.3)}
.grade-E{background:rgba(248,113,113,.1);color:var(--red);border:2px solid rgba(248,113,113,.3)}
.dim-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.6rem;margin:1.5rem 0}
.dim-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem;margin:.75rem 0}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:.6rem;margin:.75rem 0}
.stat-card{background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:.85rem 1rem}
.stat-card .label{font-size:.68rem;text-transform:uppercase;color:var(--fg3);margin-bottom:.25rem}
.stat-card .value{font-size:1.25rem;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:.84rem;margin:.75rem 0}
th{text-align:left;font-size:.68rem;text-transform:uppercase;color:var(--fg3);padding:.65rem .85rem;border-bottom:1px solid var(--border)}
td{padding:.6rem .85rem;border-bottom:1px solid var(--border)}
.badge{font-size:.65rem;font-weight:700;padding:.2rem .6rem;border-radius:99px;text-transform:uppercase}
details{margin:.5rem 0}
details summary{cursor:pointer;font-weight:600;padding:.5rem 0;color:var(--fg2)}
details summary:hover{color:var(--fg)}
.checklist{list-style:none;padding:0}
.checklist li{padding:.35rem 0;padding-left:1.5rem;position:relative;color:var(--fg2)}
.checklist li::before{content:'[ ]';position:absolute;left:0;font-family:monospace;color:var(--fg3)}
.hero{text-align:center;padding:2rem 0;margin-bottom:1.5rem;border-bottom:1px solid var(--border)}
.hero .grade-box{width:96px;height:96px;font-size:2.5rem;border-radius:24px;margin-bottom:1rem}
.hero .project-name{font-size:1.4rem;font-weight:700;margin:.5rem 0}
.hero .tech-badges{display:flex;gap:.4rem;justify-content:center;flex-wrap:wrap;margin-top:.75rem}
.hero .tech-badge{background:var(--bg3);border:1px solid var(--border);border-radius:99px;padding:.25rem .75rem;font-size:.72rem;color:var(--fg2)}
.section-header{display:flex;align-items:center;gap:1rem;margin:2rem 0 1rem}
.section-header h2{margin:0;border:none;padding:0}
.section-header .grade-box{width:40px;height:40px;font-size:1.1rem;border-radius:10px}
.recommendations{margin:2rem 0}
.recommendations ol{padding-left:1.5rem}
.recommendations li{margin:.5rem 0;line-height:1.5}
.footer{text-align:center;padding:2rem 0;margin-top:2rem;border-top:1px solid var(--border);color:var(--fg3);font-size:.75rem}
.severity-critical{color:var(--red)}
.severity-high{color:var(--orange)}
.severity-medium{color:var(--yellow)}
.severity-low{color:var(--fg3)}
@media(max-width:600px){
  .dim-grid{grid-template-columns:1fr 1fr}
  .card-grid{grid-template-columns:1fr}
  .hero .grade-box{width:72px;height:72px;font-size:2rem}
}
```

### HTML Structure

Write the HTML report using the Write tool. The HTML structure should be:

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Code Quality Report — {PROJECT_NAME}</title>
  <style>{INLINED_CSS}</style>
</head>
<body>
  <main>
    <!-- Hero: overall grade box + project name + tech stack badges -->
    <div class="hero">
      <div class="grade-box grade-{OVERALL}">{OVERALL}</div>
      <div class="project-name">{PROJECT_NAME}</div>
      <div class="tech-badges">
        <!-- One tech-badge span per detected language -->
      </div>
    </div>

    <!-- Dimension overview grid (7 dim-cards) -->
    <div class="dim-grid">
      <!-- One dim-card per dimension: small grade-box + dimension name -->
    </div>

    <!-- For each of the 7 dimensions: -->
    <div class="section-header">
      <div class="grade-box grade-{DIM_GRADE}">{DIM_GRADE}</div>
      <h2>{DIMENSION_NAME}</h2>
    </div>
    <div class="card">
      <!-- Key metrics as stat-cards in a card-grid -->
      <div class="card-grid">
        <div class="stat-card">
          <div class="label">{METRIC_NAME}</div>
          <div class="value">{METRIC_VALUE}</div>
        </div>
        <!-- ... more stat-cards ... -->
      </div>

      <!-- Findings (if any) in details/accordion grouped by severity -->
      <details>
        <summary>Findings ({COUNT})</summary>
        <table>
          <thead><tr><th>Severity</th><th>Finding</th><th>Location</th></tr></thead>
          <tbody>
            <!-- One row per finding -->
          </tbody>
        </table>
      </details>

      <!-- Upgrade path checklist showing what to improve for next grade -->
      <details>
        <summary>Upgrade Path ({CURRENT} → {NEXT})</summary>
        <ul class="checklist">
          <li>{ACTION_ITEM_1}</li>
          <li>{ACTION_ITEM_2}</li>
          <!-- ... -->
        </ul>
      </details>
    </div>

    <!-- Top 5 Recommendations -->
    <div class="recommendations">
      <h2>Top 5 Recommendations</h2>
      <ol>
        <li><strong>{TITLE}</strong> — {DESCRIPTION} <span class="badge">{IMPACT}</span></li>
        <!-- ... 4 more ... -->
      </ol>
    </div>

    <!-- Footer with generation date -->
    <div class="footer">
      Code Quality Report v3.0 — Generated {DATE} — Powered by LLM analysis
    </div>
  </main>
</body>
</html>
```

For each dimension section, include:
- Section header with dimension name and grade box
- Key metrics as stat-cards in a card-grid
- Findings (if any) in details/accordion grouped by severity
- Upgrade path checklist showing what to improve for next grade

## Step 6: Terminal Summary

After generating the HTML, print a summary to the terminal:

```
Code Quality Report v3.0

Overall Grade: [GRADE]
Report: reports/code-quality-report.html

  Maintainability  [GRADE]    Test Coverage  [GRADE]
  Reliability      [GRADE]    Architecture   [GRADE]
  Security         [GRADE]    Documentation  [GRADE]
  DevOps & CI      [GRADE]

Top 3 Recommendations:
1. [Most impactful improvement]
2. [Second most impactful]
3. [Third most impactful]

Open: file:///{ABSOLUTE_PATH}/reports/code-quality-report.html
```

## Important Notes

- **No external dependencies**: Do not use npm, node, bun, vitest, eslint, or any language-specific tools
- **No subagents**: All analysis is done by the main LLM in a single pass
- **git ls-files only**: Never use `find` — git ls-files respects .gitignore and works cross-platform
- **Missing data = C**: If a metric cannot be measured, grade it C (unverifiable), never A
- **Language bonuses**: Only upgrade, never downgrade. Report as notes, not primary grade
- **Overall = minimum**: The overall grade equals the lowest dimension grade
- **Cross-platform**: Commands work in git-bash (Windows) and standard bash (Unix)
- **Self-contained HTML**: The report file should work when opened directly in any browser, no server needed
- **Create reports/ directory**: Run `mkdir -p reports` before writing the HTML file
- **Absolute paths in file:// links**: Use the full absolute path so the link works when clicked
