---
name: experiment-design
description: Best practices for designing reproducible experiments
---

# Experiment Design Patterns

## When to Use
Load this skill when designing experiments that need to be reproducible and statistically valid.

## Reproducibility Setup

### Random Seeds
```python
import random
import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

print(f"[DECISION] Using random seed: {SEED}")
```

### Environment Recording
```python
import sys
print(f"[INFO] Python: {sys.version}")
print(f"[INFO] NumPy: {np.__version__}")
print(f"[INFO] Pandas: {pd.__version__}")
```

## Experimental Controls

### Train/Test Split
```python
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=SEED, stratify=y
)
print(f"[EXPERIMENT] Train: {len(X_train)}, Test: {len(X_test)}")
```

### Cross-Validation
```python
from sklearn.model_selection import cross_val_score

scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f"[METRIC] CV Accuracy: {scores.mean():.3f} (+/- {scores.std()*2:.3f})")
```

## A/B Testing Pattern
```python
print("[EXPERIMENT] A/B Test Design")
print(f"[INFO] Control group: {len(control)}")
print(f"[INFO] Treatment group: {len(treatment)}")

# Power analysis
from statsmodels.stats.power import TTestIndPower
power = TTestIndPower()
sample_size = power.solve_power(effect_size=0.5, alpha=0.05, power=0.8)
print(f"[CALC] Required sample size per group: {sample_size:.0f}")
```

## Power Analysis

Power analysis ensures your experiment has sufficient sample size to detect meaningful effects. Without adequate power, you risk false negatives (missing real effects).

### Sample Size Calculation

```python
from statsmodels.stats.power import TTestIndPower, FTestAnovaPower, NormalIndPower
import numpy as np

print("[DECISION] Conducting a priori power analysis before data collection")

# For two-group comparison (t-test)
power_analysis = TTestIndPower()

# Parameters:
# - effect_size: Expected Cohen's d (0.2=small, 0.5=medium, 0.8=large)
# - alpha: Significance level (typically 0.05)
# - power: Desired statistical power (typically 0.80 or 0.90)
# - ratio: Ratio of group sizes (1.0 = equal groups)

effect_size = 0.5  # Medium effect size
alpha = 0.05
desired_power = 0.80

sample_size = power_analysis.solve_power(
    effect_size=effect_size,
    alpha=alpha,
    power=desired_power,
    ratio=1.0,
    alternative='two-sided'
)

print(f"[STAT:estimate] Required n per group: {np.ceil(sample_size):.0f}")
print(f"[STAT:estimate] Total sample needed: {np.ceil(sample_size)*2:.0f}")
print(f"[DECISION] Targeting {effect_size} effect size (Cohen's d = medium)")
```

### Achieved Power (Post-Hoc)

```python
# After data collection, calculate achieved power
actual_n = 50  # Actual sample size per group
achieved_power = power_analysis.solve_power(
    effect_size=effect_size,
    alpha=alpha,
    nobs1=actual_n,
    ratio=1.0,
    alternative='two-sided'
)

print(f"[STAT:estimate] Achieved power: {achieved_power:.3f}")

if achieved_power < 0.80:
    print(f"[LIMITATION] Study is underpowered ({achieved_power:.0%} < 80%)")
    print("[LIMITATION] Negative results may be due to insufficient sample size")
else:
    print(f"[DECISION] Adequate power achieved ({achieved_power:.0%} ≥ 80%)")
```

### Power for Different Tests

```python
# For ANOVA (multiple groups)
from statsmodels.stats.power import FTestAnovaPower
anova_power = FTestAnovaPower()
n_groups = 3
effect_size_f = 0.25  # Cohen's f (0.1=small, 0.25=medium, 0.4=large)
n_per_group = anova_power.solve_power(
    effect_size=effect_size_f,
    alpha=0.05,
    power=0.80,
    k_groups=n_groups
)
print(f"[STAT:estimate] ANOVA: {np.ceil(n_per_group):.0f} per group needed")

# For proportions (chi-square, A/B tests)
from statsmodels.stats.power import GofChisquarePower
from statsmodels.stats.proportion import proportion_effectsize
# Convert expected proportions to effect size
p1, p2 = 0.10, 0.15  # e.g., 10% baseline, 15% expected with treatment
prop_effect = proportion_effectsize(p1, p2)
print(f"[DECISION] Effect size h = {prop_effect:.3f} for proportions test")
```

## Pre-registration Concept

Pre-registration prevents HARKing (Hypothesizing After Results are Known) and distinguishes confirmatory from exploratory analyses.

### Define Analysis Before Data

```python
print("[DECISION] Pre-registering analysis plan before examining data")

# Document your analysis plan BEFORE looking at the data
preregistration = {
    "primary_hypothesis": "H1: Treatment group shows higher conversion rate than control",
    "null_hypothesis": "H0: No difference in conversion rates between groups",
    "primary_endpoint": "conversion_rate",
    "secondary_endpoints": ["time_to_convert", "revenue_per_user"],
    "alpha": 0.05,
    "correction_method": "Bonferroni for secondary endpoints",
    "minimum_effect_size": "5 percentage points (10% → 15%)",
    "planned_sample_size": 500,
    "analysis_method": "Two-proportion z-test",
    "exclusion_criteria": "Users with < 1 day exposure"
}

print(f"[EXPERIMENT] Pre-registered analysis plan:")
for key, value in preregistration.items():
    print(f"  {key}: {value}")
```

### Confirmatory vs Exploratory Findings

```python
# After analysis, clearly label findings
print("[FINDING] Treatment increases conversion by 4.2pp (95% CI: [1.8, 6.6])")
print("[STAT:ci] 95% CI [1.8, 6.6]")
print("[STAT:effect_size] Cohen's h = 0.12 (small)")
print("[STAT:p_value] p = 0.001")
# This is CONFIRMATORY because it tests pre-registered hypothesis

print("[OBSERVATION] Exploratory: Effect stronger for mobile users (+7.1pp)")
print("[LIMITATION] Mobile subgroup analysis was NOT pre-registered")
print("[DECISION] Flagging as exploratory - requires replication before action")

# Document finding type
CONFIRMATORY = True  # Pre-registered hypothesis
EXPLORATORY = False  # Post-hoc discovery

def label_finding(finding: str, is_confirmatory: bool):
    """Label findings appropriately based on pre-registration status."""
    if is_confirmatory:
        print(f"[FINDING] CONFIRMATORY: {finding}")
    else:
        print(f"[OBSERVATION] EXPLORATORY: {finding}")
        print("[LIMITATION] This finding was not pre-registered and requires replication")
```

### Document Deviations from Plan

```python
# When you deviate from the pre-registered plan, document it!
print("[DECISION] DEVIATION FROM PRE-REGISTRATION:")
print("  Original plan: Two-proportion z-test")
print("  Actual analysis: Fisher's exact test")
print("  Reason: Cell counts < 5 in contingency table")
print("  Impact: More conservative, may reduce power")

# Keep a deviation log
deviations = [
    {
        "item": "Statistical test",
        "planned": "z-test",
        "actual": "Fisher's exact",
        "reason": "Low expected cell counts",
        "impact": "Minimal - Fisher's is more conservative"
    },
    {
        "item": "Sample size",
        "planned": 500,
        "actual": 487,
        "reason": "13 users excluded due to technical issues",
        "impact": "Power reduced from 80% to 78%"
    }
]

print("[EXPERIMENT] Deviation log:")
for d in deviations:
    print(f"  - {d['item']}: {d['planned']} → {d['actual']} ({d['reason']})")
```

## Stopping Rules

Define stopping criteria upfront to prevent p-hacking through optional stopping.

### Define Success/Failure Criteria Upfront

```python
print("[DECISION] Defining stopping rules BEFORE experiment starts")

stopping_rules = {
    "success_criterion": "Lower 95% CI bound > 0 (effect is positive)",
    "failure_criterion": "Upper 95% CI bound < minimum_effect (effect too small)",
    "futility_criterion": "Posterior probability of success < 5%",
    "max_sample_size": 1000,
    "interim_analyses": [250, 500, 750],  # Pre-specified checkpoints
    "alpha_spending": "O'Brien-Fleming"  # Preserve overall alpha
}

print(f"[EXPERIMENT] Stopping rules defined:")
for key, value in stopping_rules.items():
    print(f"  {key}: {value}")
```

### Avoid P-Hacking Through Optional Stopping

```python
# BAD: Looking at p-value repeatedly and stopping when significant
# This inflates false positive rate!

# GOOD: Use alpha-spending functions to control Type I error

from scipy import stats
import numpy as np

def obrien_fleming_boundary(alpha: float, n_looks: int, current_look: int) -> float:
    """
    Calculate O'Brien-Fleming spending boundary.
    More conservative early, less conservative late.
    """
    # Information fraction
    t = current_look / n_looks
    # O'Brien-Fleming boundary
    z_boundary = stats.norm.ppf(1 - alpha/2) / np.sqrt(t)
    p_boundary = 2 * (1 - stats.norm.cdf(z_boundary))
    return p_boundary

n_looks = 4  # Number of interim analyses
alpha = 0.05  # Overall significance level

print("[DECISION] Using O'Brien-Fleming alpha-spending to control Type I error")
print("[EXPERIMENT] Adjusted significance thresholds:")
for look in range(1, n_looks + 1):
    boundary = obrien_fleming_boundary(alpha, n_looks, look)
    print(f"  Look {look}/{n_looks}: p < {boundary:.5f} to stop for efficacy")

print("[LIMITATION] Stopping early requires more extreme evidence")
```

### Sequential Analysis Methods (SPRT)

```python
# Sequential Probability Ratio Test (SPRT)
# Allows continuous monitoring with controlled error rates

def sprt_bounds(alpha: float, beta: float) -> tuple:
    """
    Calculate SPRT decision boundaries.
    
    Args:
        alpha: Type I error rate (false positive)
        beta: Type II error rate (false negative)
    
    Returns:
        (lower_bound, upper_bound) for log-likelihood ratio
    """
    A = np.log((1 - beta) / alpha)  # Upper boundary (accept H1)
    B = np.log(beta / (1 - alpha))  # Lower boundary (accept H0)
    return B, A

alpha, beta = 0.05, 0.20  # 5% false positive, 20% false negative (80% power)
lower, upper = sprt_bounds(alpha, beta)

print("[DECISION] Using Sequential Probability Ratio Test (SPRT)")
print(f"[STAT:estimate] Stop for H0 if LLR < {lower:.3f}")
print(f"[STAT:estimate] Stop for H1 if LLR > {upper:.3f}")
print("[EXPERIMENT] Continue sampling if {:.3f} < LLR < {:.3f}".format(lower, upper))

# Example SPRT monitoring
def monitor_sprt(successes: int, trials: int, p0: float, p1: float, bounds: tuple):
    """Monitor SPRT decision status."""
    lower, upper = bounds
    # Log-likelihood ratio
    if successes == 0 or successes == trials:
        llr = 0  # Avoid log(0)
    else:
        p_hat = successes / trials
        llr = successes * np.log(p1/p0) + (trials - successes) * np.log((1-p1)/(1-p0))
    
    if llr > upper:
        return "STOP: Accept H1 (treatment effective)", llr
    elif llr < lower:
        return "STOP: Accept H0 (no effect)", llr
    else:
        return "CONTINUE: Need more data", llr

# Example: Testing if conversion rate > 10% vs = 10%
p_null, p_alt = 0.10, 0.15
status, llr = monitor_sprt(successes=45, trials=350, p0=p_null, p1=p_alt, bounds=(lower, upper))
print(f"[STAT:estimate] Current LLR: {llr:.3f}")
print(f"[DECISION] {status}")
```

### Document Stopping Decision

```python
# When you stop an experiment, document the decision clearly
print("[DECISION] Experiment stopped at interim analysis 2/4")
print("[STAT:estimate] Current effect: 5.2pp (95% CI: [2.1, 8.3])")
print("[STAT:p_value] p = 0.0012 (< O'Brien-Fleming boundary 0.005)")
print("[EXPERIMENT] Decision: STOP FOR EFFICACY")
print("[FINDING] Treatment significantly improves conversion (confirmed at interim)")
print("[LIMITATION] Final sample (n=500) smaller than planned (n=1000)")
print("[LIMITATION] Effect estimate may regress toward null with more data")
```

## Documentation Pattern
```python
print("[DECISION] Chose Random Forest over XGBoost because:")
print("  - Better interpretability for stakeholders")
print("  - Comparable performance (within 1% accuracy)")
print("  - Faster training time for iteration")

print("[LIMITATION] Model may not generalize to:")
print("  - Data from different time periods")
print("  - Users from different demographics")
```
