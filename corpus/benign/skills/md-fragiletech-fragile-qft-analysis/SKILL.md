---
name: qft-analysis
description: Analyze QFT experiment results from RunHistory files. Computes particle masses and fundamental constants using multiple mass scale anchors (electron, Z boson, tau), validates against Standard Model values, and generates comprehensive comparison reports. Use when analyzing QFT simulation results or validating calibrations.
allowed-tools: Bash(python:*), Read, Write, Glob
argument-hint: [--history-path PATTERN] [--anchors ANCHORS] [--anchor-mass MASS] [--anchor-label LABEL]
disable-model-invocation: false
---

# QFT Analysis Skill

Orchestrate QFT experiment analysis, calibration validation, and multi-run comparison workflows.

## Your Task

Process QFT experiment RunHistory files to:
1. Calibrate algorithmic parameters from Standard Model constants using different mass scale anchors
2. Analyze particle masses and field correlations from simulation data
3. Compare results to measured Standard Model values
4. Generate comprehensive comparison reports with quality assessments

## Available Scripts

You orchestrate these existing Python scripts:
- `src/experiments/calibrate_fractal_gas_qft.py` - Maps SM constants → algorithmic parameters
- `src/experiments/analyze_fractal_gas_qft.py` - Computes particle masses & observables from RunHistory
- `src/experiments/constants_check.py` - Reference SM constants for validation

## Mass Scale Anchors

| Anchor   | Mass (GeV)      | Label      | Use Case                          |
|----------|-----------------|------------|-----------------------------------|
| Electron | 0.000510998950  | `electron` | Light fermion scale               |
| Z Boson  | 91.1876         | `z`        | Electroweak scale (default)       |
| Tau      | 1.77686         | `tau`      | Heavy lepton scale                |
| Custom   | User-specified  | User-set   | Experimental (e.g., Higgs: 125.1) |

## Standard Model Reference Constants

From `src/experiments/constants_check.py`:
- α_em = 1/137.035999084 ≈ 0.007297352564 (fine structure constant)
- sin²θ_W = 0.23121 (weak mixing angle at M_Z)
- α_s(M_Z) = 0.1179 (strong coupling at M_Z)

## Workflow

### Step 1: Parse Arguments

Extract parameters from `$ARGUMENTS`:

**History Path:**
- `--history-path <path>` - Single file, glob pattern, or omit for auto-detect latest
- Examples:
  - `outputs/my_run_history.pt` (single file)
  - `"outputs/sweep_*.pt"` (glob pattern - quote it!)
  - Omit to auto-detect latest `.pt` file in `outputs/`

**Anchors:**
- `--anchors <list>` - Comma-separated: `electron,z,tau,custom,all`
- Default: `z` (Z boson scale)
- `all` expands to `electron,z,tau` (+ custom if provided)

**Custom Anchor:**
- `--anchor-mass <float>` - Required if `custom` in anchors
- `--anchor-label <string>` - Default: "Custom"

**Optional Flags:**
- `--no-particles` - Skip particle mass computation (faster, field correlations only)
- `--particle-max-lag <int>` - Override default lag points
- `--particle-fit-stop <int>` - Override default fit range

**Example Parsing:**
```
$ARGUMENTS = "--history-path outputs/sweep_*.pt --anchors z,electron"
→ history_pattern = "outputs/sweep_*.pt"
→ anchors = ["z", "electron"]
```

### Step 2: Pre-flight Validation

Before running analysis:

1. **Ensure output directories exist:**
   ```bash
   mkdir -p outputs/qft_calibration
   mkdir -p outputs/fractal_gas_potential_well_analysis
   mkdir -p outputs/qft_analysis_reports
   ```

2. **Resolve history files:**
   ```bash
   # If glob pattern
   ls outputs/sweep_*.pt

   # If auto-detect latest
   ls -t outputs/*history*.pt | head -1
   ```

   Verify all files exist and are readable.

3. **Validate custom anchor:**
   If `custom` in anchors and no `--anchor-mass`, error:
   ```
   Error: --anchor-mass required when using custom anchor
   Example: /qft-analysis --anchors custom --anchor-mass 125.1 --anchor-label Higgs
   ```

4. **Verify scripts are executable:**
   ```bash
   python src/experiments/calibrate_fractal_gas_qft.py --help >/dev/null 2>&1
   ```

### Step 3: Run Calibration Pipeline

For each `(history_file, anchor)` pair:

**Generate unique run_id:**
```
Format: <anchor_label>_<timestamp>
Example: z_boson_170125
```

**Map anchor to mass/label:**
```python
ANCHORS = {
    'electron': (0.000510998950, 'Electron'),
    'z': (91.1876, 'Z_Boson'),
    'tau': (1.77686, 'Tau'),
    'custom': (user_mass, user_label)
}
```

**Run calibration:**
```bash
python src/experiments/calibrate_fractal_gas_qft.py \
  --history-path <history_file> \
  --m-gev <anchor_mass> \
  --scale-label <anchor_label> \
  --run-id <unique_run_id> \
  --qsd-iter 4
```

**Output location:**
```
outputs/qft_calibration/<run_id>_calibration.json
```

**Error Handling:**
- If calibration fails for one (history, anchor) pair, log error and continue with others
- Collect all errors to report at end

### Step 4: Run Analysis Pipeline

For each unique history file (once per file, not per anchor):

**Generate unique analysis_id:**
```
Format: <basename>_<timestamp>
Example: sweep_nu10_170125
```

**Build command:**
```bash
python src/experiments/analyze_fractal_gas_qft.py \
  --history-path <history_file> \
  --analysis-id <unique_analysis_id> \
  --compute-particles \
  --build-fractal-set \
  --particle-operators "baryon,meson,glueball" \
  --use-connected \
  --use-local-fields
```

**Optional flags (based on user input):**
- If `--no-particles`: Omit `--compute-particles` and particle-related flags
- If `--particle-max-lag N`: Add `--particle-max-lag N`
- If `--particle-fit-stop N`: Add `--particle-fit-stop N`

**Output location:**
```
outputs/fractal_gas_potential_well_analysis/<analysis_id>_metrics.json
```

**Error Handling:**
- If particle computation fails but field analysis succeeds, accept partial results
- If entire analysis fails, skip this history file and continue with others

### Step 5: Load and Parse Results

**Load calibration JSONs:**

For each successful calibration, read JSON from `outputs/qft_calibration/<run_id>_calibration.json`:

Key fields:
```json
{
  "algorithmic_parameters": {
    "epsilon_c": float,
    "epsilon_d": float,
    "rho": float,
    "tau": float,
    "nu": float,
    "epsilon_F": float
  },
  "couplings": {
    "e_em": float,
    "g1": float,
    "g2": float,
    "g3": float,
    "sin_theta_w": float,
    "cos_theta_w": float
  },
  "inputs": {
    "constants": {
      "alpha_em": float,
      "sin2_theta_w": float,
      "alpha_s": float,
      "scale_label": string
    },
    "calibration": {
      "m_gev": float,
      "lambda_gap": float
    }
  },
  "stability": {
    "stable": bool,
    "alive_fraction": float,
    "finite_positions": bool,
    "finite_velocities": bool,
    "finite_fitness": bool
  },
  "qsd_estimates": {
    "samples": int
  }
}
```

**Compute gauge couplings from couplings:**
- α_em = e_em² / (4π)
- sin²θ_W = sin_theta_w²
- α_s = g3² / (4π)

**Load analysis JSONs:**

For each analysis, read JSON from `outputs/fractal_gas_potential_well_analysis/<analysis_id>_metrics.json`:

Key fields (may be nested deeper):
```json
{
  "particle_masses": {
    "meson": {"mass": float, "r_squared": float},
    "baryon": {"mass": float, "r_squared": float},
    "glueball": {"mass": float, "r_squared": float}
  },
  "correlations": {
    "d_prime": {"xi": float, "r_squared": float},
    "r_prime": {"xi": float, "r_squared": float},
    "density": {"xi": float},
    "kinetic": {"xi": float}
  },
  "lyapunov_ratio": float,
  "plots": {
    "correlations": string,
    "wilson_loops": string
  }
}
```

**Note:** The actual JSON structure may be nested. Navigate carefully and handle missing fields.

**Match calibrations to analyses:**
- Group by history file basename
- For each history file: collect all anchor calibrations + single analysis result

### Step 6: Generate Terminal Tables

Display these five tables in the terminal:

#### Table 1: Run Summary

```
QFT Analysis Run Summary
========================

| Run ID              | History File                  | Anchor    | Stable | Alive % | QSD Samples |
|---------------------|-------------------------------|-----------|--------|---------|-------------|
| electron_170125     | sweep_nu10_history.pt         | Electron  | ✓      | 100.0%  | 200         |
| z_boson_170125      | sweep_nu10_history.pt         | Z Boson   | ✓      | 100.0%  | 200         |
| tau_170125          | sweep_nu10_history.pt         | Tau       | ✓      | 100.0%  | 200         |
```

**Data sources:**
- Run ID: From calibration filename
- History File: From calibration JSON `inputs.calibration` or command
- Anchor: From calibration JSON `inputs.constants.scale_label`
- Stable: ✓ if `stability.stable == true`, ✗ otherwise
- Alive %: `stability.alive_fraction * 100`
- QSD Samples: `qsd_estimates.samples`

#### Table 2: Gauge Coupling Validation

```
Gauge Coupling Validation
=========================
(Input couplings should match exactly; validates inversion formulas)

| Run ID          | Anchor    | α_em      | sin²θ_W   | α_s      | Match Quality |
|-----------------|-----------|-----------|-----------|----------|---------------|
| electron_170125 | Electron  | 0.007297  | 0.2312    | 0.1179   | ✓✓✓ Exact     |
| z_boson_170125  | Z Boson   | 0.007297  | 0.2312    | 0.1179   | ✓✓✓ Exact     |
| tau_170125      | Tau       | 0.007297  | 0.2312    | 0.1179   | ✓✓✓ Exact     |
```

**Data sources:**
- From calibration JSON `inputs.constants`
- Compare to reference values

**Match Quality:**
```python
def match_quality(alpha_em, sin2_theta_w, alpha_s):
    ref = {"alpha_em": 0.007297352564, "sin2_theta_w": 0.23121, "alpha_s": 0.1179}

    max_error = max(
        abs(alpha_em - ref["alpha_em"]) / ref["alpha_em"],
        abs(sin2_theta_w - ref["sin2_theta_w"]) / ref["sin2_theta_w"],
        abs(alpha_s - ref["alpha_s"]) / ref["alpha_s"]
    )

    if max_error < 0.001: return "✓✓✓ Exact"
    if max_error < 0.01: return "✓✓ Good"
    if max_error < 0.05: return "✓ Fair"
    return "✗ Poor"
```

#### Table 3: Algorithmic Parameters by Anchor

```
Algorithmic Parameters by Anchor
=================================

| Parameter | Electron Scale | Z Boson Scale | Tau Scale | Physical Meaning           |
|-----------|----------------|---------------|-----------|----------------------------|
| ε_c       | 1.684          | 1.684         | 1.684     | Clone coupling scale       |
| ε_d       | 2.799          | 2.799         | 2.799     | Distance coupling scale    |
| ρ         | 1742.9         | 0.0096        | 0.540     | Mass-field coupling        |
| τ         | 0.000725       | 1317.8        | 0.833     | Time scale                 |
| ν         | 84.5           | 84.5          | 84.5      | Viscosity parameter        |
| ε_F       | 0.00557        | 10123         | 63.9      | Fermion mass scale         |
```

**Data sources:**
- From calibration JSON `algorithmic_parameters`
- One column per anchor
- Parameters: epsilon_c, epsilon_d, rho, tau, nu, epsilon_F

**Formatting:**
- Use scientific notation if |value| < 0.001 or |value| > 10000
- Otherwise 3-4 significant figures

**Physical meanings (hardcoded):**
```python
PARAM_MEANINGS = {
    "epsilon_c": "Clone coupling scale",
    "epsilon_d": "Distance coupling scale",
    "rho": "Mass-field coupling",
    "tau": "Time scale",
    "nu": "Viscosity parameter",
    "epsilon_F": "Fermion mass scale"
}
```

#### Table 4: Particle Mass Predictions

```
Particle Mass Predictions
=========================

| Run ID          | Anchor   | Meson Mass | Meson R² | Baryon Mass | Baryon R² | Glueball Mass | Glueball R² | Quality    |
|-----------------|----------|------------|----------|-------------|-----------|---------------|-------------|------------|
| electron_170125 | Electron | 70.0       | 0.128    | 60.2        | 0.178     | 3.37          | 0.243       | Poor       |
| z_boson_170125  | Z Boson  | 63.9       | 0.867    | 58.4        | 0.791     | 3.21          | 0.682       | Good       |
| tau_170125      | Tau      | 65.1       | 0.654    | 59.3        | 0.612     | 3.28          | 0.571       | Fair       |
```

**Data sources:**
- From analysis JSON `particle_masses.{meson,baryon,glueball}`
- Match analysis to calibration via history file

**Quality Scoring:**
```python
def particle_quality(r2_meson, r2_baryon, r2_glueball):
    avg_r2 = (r2_meson + r2_baryon + r2_glueball) / 3

    if avg_r2 > 0.8: return "Excellent"
    if avg_r2 > 0.5: return "Good"
    if avg_r2 > 0.3: return "Fair"
    return "Poor"
```

**Missing data:**
- If `--no-particles` used, show "N/A" for all masses/R²
- If specific operator missing, show "—"

#### Table 5: Correlation & Field Diagnostics

```
Correlation & Field Diagnostics
================================

| Run ID          | d_prime ξ | d_prime R² | r_prime ξ | r_prime R² | Density ξ | Kinetic ξ | Lyapunov Ratio |
|-----------------|-----------|------------|-----------|------------|-----------|-----------|----------------|
| electron_170125 | 0.0       | 0.0        | 0.426     | 0.973      | 0.125     | 0.016     | 0.0084         |
```

**Data sources:**
- From analysis JSON `correlations` and `lyapunov_ratio`
- One row per unique history file (analysis run once per file)

**Note:**
Correlation length ξ indicates spatial structure strength. R² indicates exponential fit quality.

### Step 7: Generate Summary Assessment

Compute overall quality:

**1. Stability Check:**
```python
all_stable = all(cal["stability"]["stable"] for cal in calibrations)
unstable_runs = [cal["run_id"] for cal in calibrations if not cal["stability"]["stable"]]
```

**2. Particle Fit Quality:**
```python
r2_values = []
for analysis in analyses:
    for operator in ["meson", "baryon", "glueball"]:
        if operator in analysis["particle_masses"]:
            r2_values.append(analysis["particle_masses"][operator]["r_squared"])

avg_particle_r2 = sum(r2_values) / len(r2_values) if r2_values else 0

if avg_particle_r2 > 0.8: particle_quality = "EXCELLENT"
elif avg_particle_r2 > 0.5: particle_quality = "GOOD"
elif avg_particle_r2 > 0.3: particle_quality = "MODERATE"
else: particle_quality = "POOR"
```

**3. Field Correlation Quality:**
```python
correlation_r2 = []
for analysis in analyses:
    for field in ["r_prime", "d_prime"]:
        if field in analysis["correlations"] and "r_squared" in analysis["correlations"][field]:
            correlation_r2.append(analysis["correlations"][field]["r_squared"])

avg_correlation_r2 = sum(correlation_r2) / len(correlation_r2) if correlation_r2 else 0

if avg_correlation_r2 > 0.8: correlation_quality = "EXCELLENT"
elif avg_correlation_r2 > 0.5: correlation_quality = "GOOD"
elif avg_correlation_r2 > 0.3: correlation_quality = "MODERATE"
else: correlation_quality = "POOR"
```

**4. QSD Convergence:**
```python
lyapunov_ratios = [analysis["lyapunov_ratio"] for analysis in analyses if "lyapunov_ratio" in analysis]
max_lyapunov = max(lyapunov_ratios) if lyapunov_ratios else 0
qsd_convergent = max_lyapunov < 0.01
```

**Overall Quality:**
```python
qualities = [particle_quality, correlation_quality]
if "POOR" in qualities: overall = "POOR"
elif "MODERATE" in qualities: overall = "MODERATE"
elif "GOOD" in qualities: overall = "GOOD"
else: overall = "EXCELLENT"
```

**Display Assessment:**

```
Calibration Quality Assessment
===============================

Overall: GOOD

- Stability: ✓ All runs stable (100% alive, finite positions/velocities)
- Particle Masses: MODERATE (Average R² = 0.46, some operators have poor fits)
- Field Correlations: EXCELLENT (Average R² = 0.85, strong exponential decay)
- QSD Convergence: ✓ Lyapunov ratio 0.0084 << 1

Recommendations:
- Increase simulation time for better particle mass statistics
- Consider higher N for baryon operator (currently low R²)
- Correlation lengths indicate well-formed QSD structure
```

**Recommendation Logic:**

Generate 2-4 specific recommendations:

```python
recommendations = []

if avg_particle_r2 < 0.5:
    recommendations.append("Increase simulation time for better particle mass statistics")

    # Check which operator is worst
    worst_operator = min(particle_masses.items(), key=lambda x: x[1]["r_squared"])
    if worst_operator[1]["r_squared"] < 0.3:
        recommendations.append(f"Consider higher N for {worst_operator[0]} operator (currently low R²)")

if avg_correlation_r2 < 0.5:
    recommendations.append("Check spatial boundary conditions")

if max_lyapunov > 0.01:
    recommendations.append("Increase QSD iterations (--qsd-iter) for better convergence")

if unstable_runs:
    recommendations.append("Review parameter ranges for unstable runs")

if not recommendations:
    recommendations.append("Results are robust; consider production runs")

# Also check correlation lengths
avg_xi = sum(analysis["correlations"][f]["xi"]
             for analysis in analyses
             for f in ["r_prime", "density", "kinetic"]
             if f in analysis["correlations"] and "xi" in analysis["correlations"][f])
avg_xi /= (3 * len(analyses))

if avg_xi > 0.05:
    recommendations.append("Correlation lengths indicate well-formed QSD structure")
```

### Step 8: Generate Markdown Report

Create report at `outputs/qft_analysis_reports/<timestamp>_qft_analysis_report.md`:

**Timestamp format:** `YYYYMMDD_HHMMSS` (e.g., `20260125_170000`)

**Report Structure:**

````markdown
# QFT Analysis Report

**Generated:** 2026-01-25 17:00:00

## Executive Summary

{Overall quality assessment from Step 7}

## Run Configuration

- **History Files:** {list of files}
- **Anchors:** {list of anchors}
- **Analysis Options:** {particle computation enabled/disabled, etc.}

## Results

### Run Summary

{Table 1 in markdown format}

### Gauge Coupling Validation

{Table 2 in markdown format}

### Algorithmic Parameters

{Table 3 in markdown format}

### Particle Mass Predictions

{Table 4 in markdown format}

### Correlation & Field Diagnostics

{Table 5 in markdown format}

## Detailed Analysis

### QSD Convergence

- **Lyapunov Ratios:** {list values for each run}
- **QSD Samples:** {list samples for each run}
- **Convergence Quality:** {assessment}

### Stability Checks

- **Stable Runs:** {count}
- **Unstable Runs:** {list if any}
- **Alive Fractions:** {range across all runs}

### Plot References

{For each analysis, list plot links}

**Run: {analysis_id}**
- Correlations: `{plot_path}`
- Wilson Loops: `{plot_path}`

## Recommendations

{Detailed recommendations from Step 7}

## Appendix

### Calibration Parameters (JSON)

<details>
<summary>Run: {run_id}</summary>

```json
{full calibration JSON}
```

</details>

### Analysis Metrics (JSON)

<details>
<summary>Analysis: {analysis_id}</summary>

```json
{full analysis JSON}
```

</details>
````

After generating report, inform user:

```
✓ Analysis complete!

Report saved to: outputs/qft_analysis_reports/{timestamp}_qft_analysis_report.md

Summary: {One-sentence overall assessment}
```

## Error Handling

### Common Errors and Solutions

**1. History file not found:**
```
Error: History file not found: {path}

Available history files in outputs/:
{list .pt files}

Suggestion: Use --history-path to specify correct file, or omit to auto-detect latest
```

**2. Calibration script failure:**
```
Error: Calibration failed for run {run_id}
Details: {stderr from script}

Troubleshooting:
- Check history file is valid RunHistory object
- Verify QSD data exists in history
- Try reducing --qsd-iter if convergence issues

Continuing with remaining runs...
```

**3. Analysis script failure:**
```
Error: Analysis failed for {history_file}
Details: {stderr from script}

Troubleshooting:
- Ensure --build-fractal-set if using glueball operator
- Check simulation has sufficient data (N > 10, steps > 100)
- Try --no-particles for faster field-only analysis

Skipping this history file...
```

**4. Missing JSON outputs:**
```
Warning: Expected calibration JSON not found: {path}
This may indicate the calibration script didn't complete successfully.
Check script output above for errors.
```

**5. Custom anchor without mass:**
```
Error: --anchor-mass required when using 'custom' anchor

Example usage:
/qft-analysis --anchors custom --anchor-mass 125.1 --anchor-label Higgs
```

### Graceful Degradation

**Partial Calibration Failure:**
- Continue with successful calibrations
- Generate tables with available data
- Note missing runs in report

**Partial Analysis Failure:**
- Use field correlations if particle computation failed
- Show "N/A" for missing particle data in tables

**All Calibrations Failed:**
- Display clear error message
- Show troubleshooting steps
- Do not generate report

**All Analyses Failed:**
- Show calibration results only
- Note particle/correlation data unavailable
- Provide troubleshooting guidance

## Quality Thresholds Reference

| Metric          | Excellent | Good  | Fair  | Poor  |
|-----------------|-----------|-------|-------|-------|
| R² (fit)        | > 0.8     | > 0.5 | > 0.3 | ≤ 0.3 |
| Lyapunov ratio  | < 0.005   | < 0.01| < 0.05| ≥ 0.05|
| Correlation ξ   | > 0.1     | > 0.05| > 0.01| ≤ 0.01|
| Alive %         | 100%      | > 95% | > 90% | ≤ 90% |
| Gauge match     | < 0.1%    | < 1%  | < 5%  | ≥ 5%  |

## Example Invocations

### Basic Usage

```bash
# Analyze latest run with default Z anchor
/qft-analysis

# Analyze specific run with electron anchor
/qft-analysis --history-path outputs/sweep_nu1.00_vls1.00_history.pt --anchors electron

# Compare all anchors for one run
/qft-analysis --history-path outputs/my_run_history.pt --anchors all
```

### Multi-Run Comparison

```bash
# Compare parameter sweep with Z boson anchor
/qft-analysis --history-path "outputs/sweep_nu*.pt" --anchors z

# Compare sweep across multiple anchors (QUOTE the glob!)
/qft-analysis --history-path "outputs/sweep_*.pt" --anchors electron,z,tau
```

### Advanced Options

```bash
# Custom anchor (Higgs mass)
/qft-analysis --anchors custom --anchor-mass 125.1 --anchor-label Higgs

# Skip particle computation (faster, field correlations only)
/qft-analysis --no-particles

# High-resolution particle analysis
/qft-analysis --particle-max-lag 200 --particle-fit-stop 50
```

## Output Format

Always conclude with:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QFT ANALYSIS COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary: {one-line overall quality}

Report: outputs/qft_analysis_reports/{timestamp}_qft_analysis_report.md

{If errors occurred, list them here}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Implementation Tips

**JSON Parsing:**
Use Python one-liners or small scripts:
```bash
python -c "import json; data = json.load(open('file.json')); print(data['field'])"
```

**Timestamp Generation:**
```bash
date +"%Y%m%d_%H%M%S"
```

**Glob Expansion:**
```bash
ls outputs/sweep_*.pt 2>/dev/null
```

**Table Formatting:**
Use simple string formatting or Python's tabulate. Ensure columns align properly.

**Error Collection:**
Keep a list of errors during processing, display summary at end if any occurred.
