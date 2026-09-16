---
name: data-analysis
description: Patterns for data loading, exploration, and statistical analysis
---

# Data Analysis Patterns

## When to Use
Load this skill when working with datasets that require exploration, cleaning, and statistical analysis.

## Data Loading
```python
print("[DATA] Loading dataset")
df = pd.read_csv("data.csv")
print(f"[SHAPE] {df.shape[0]} rows, {df.shape[1]} columns")
print(f"[DTYPE] {dict(df.dtypes)}")
print(f"[MISSING] {df.isnull().sum().to_dict()}")
```

## Exploratory Data Analysis (EDA)

### Descriptive Statistics
```python
print("[STAT] Descriptive statistics:")
print(df.describe())

print(f"[RANGE] {col}: {df[col].min()} to {df[col].max()}")
```

### Distribution Analysis
```python
print("[ANALYSIS] Checking distribution normality")
from scipy import stats
stat, p_value = stats.shapiro(df[col])
print(f"[STAT] Shapiro-Wilk p-value: {p_value:.4f}")
```

### Correlation Analysis
```python
print("[CORR] Correlation matrix:")
print(df.corr())
```

## Statistical Tests

### T-Test
```python
from scipy.stats import ttest_ind
stat, p = ttest_ind(group1, group2)
print(f"[STAT] T-test: t={stat:.3f}, p={p:.4f}")
```

### ANOVA
```python
from scipy.stats import f_oneway
stat, p = f_oneway(group1, group2, group3)
print(f"[STAT] ANOVA: F={stat:.3f}, p={p:.4f}")
```

## Confidence Interval Patterns

### Parametric CI for Means
```python
import numpy as np
from scipy import stats

def mean_ci(data, confidence=0.95):
    """Calculate parametric confidence interval for mean."""
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)  # Standard error of mean
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, mean - h, mean + h

mean, ci_low, ci_high = mean_ci(df[col])
print(f"[STAT:estimate] mean = {mean:.3f}")
print(f"[STAT:ci] 95% CI [{ci_low:.3f}, {ci_high:.3f}]")
```

### Bootstrap CI for Medians/Complex Statistics
```python
import numpy as np

def bootstrap_ci(data, stat_func=np.median, n_bootstrap=10000, confidence=0.95):
    """Calculate bootstrap confidence interval for any statistic."""
    boot_stats = []
    n = len(data)
    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        boot_stats.append(stat_func(sample))

    alpha = 1 - confidence
    ci_low = np.percentile(boot_stats, 100 * alpha / 2)
    ci_high = np.percentile(boot_stats, 100 * (1 - alpha / 2))
    return stat_func(data), ci_low, ci_high

median, ci_low, ci_high = bootstrap_ci(df[col], stat_func=np.median)
print(f"[STAT:estimate] median = {median:.3f}")
print(f"[STAT:ci] 95% Bootstrap CI [{ci_low:.3f}, {ci_high:.3f}]")
```

### Wilson CI for Proportions
```python
from scipy import stats

def wilson_ci(successes, trials, confidence=0.95):
    """Calculate Wilson score interval for proportions (better for small n)."""
    p = successes / trials
    z = stats.norm.ppf((1 + confidence) / 2)

    denominator = 1 + z**2 / trials
    center = (p + z**2 / (2 * trials)) / denominator
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * trials)) / trials) / denominator

    return p, center - spread, center + spread

prop, ci_low, ci_high = wilson_ci(successes=45, trials=100)
print(f"[STAT:estimate] proportion = {prop:.3f}")
print(f"[STAT:ci] 95% Wilson CI [{ci_low:.3f}, {ci_high:.3f}]")
```

## Effect Size Calculation

### Cohen's d for Group Comparisons
```python
import numpy as np

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size for two independent groups."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    d = (np.mean(group1) - np.mean(group2)) / pooled_std

    # Interpretation
    magnitude = "small" if abs(d) < 0.5 else "medium" if abs(d) < 0.8 else "large"
    return d, magnitude

d, magnitude = cohens_d(treatment, control)
print(f"[STAT:effect_size] Cohen's d = {d:.3f} ({magnitude})")
```

### r² for Correlations
```python
from scipy import stats

def correlation_r2(x, y):
    """Calculate Pearson r and r² with interpretation."""
    r, p = stats.pearsonr(x, y)
    r2 = r ** 2

    # Interpretation (based on Cohen's guidelines for r)
    magnitude = "small" if abs(r) < 0.3 else "medium" if abs(r) < 0.5 else "large"
    return r, r2, p, magnitude

r, r2, p, magnitude = correlation_r2(df[x_col], df[y_col])
print(f"[STAT:estimate] r = {r:.3f}")
print(f"[STAT:effect_size] r² = {r2:.3f} ({magnitude} effect, {r2*100:.1f}% variance explained)")
print(f"[STAT:p_value] p = {p:.4f}")
```

### Cliff's Delta for Non-Parametric Comparisons
```python
import numpy as np

def cliffs_delta(group1, group2):
    """Calculate Cliff's delta (non-parametric effect size)."""
    n1, n2 = len(group1), len(group2)

    # Count dominance
    more = sum(1 for x in group1 for y in group2 if x > y)
    less = sum(1 for x in group1 for y in group2 if x < y)
    delta = (more - less) / (n1 * n2)

    # Interpretation (Romano et al., 2006)
    abs_d = abs(delta)
    magnitude = "negligible" if abs_d < 0.147 else "small" if abs_d < 0.33 else "medium" if abs_d < 0.474 else "large"
    return delta, magnitude

delta, magnitude = cliffs_delta(treatment, control)
print(f"[STAT:effect_size] Cliff's delta = {delta:.3f} ({magnitude})")
```

## Assumption Checking

### Normality: Shapiro-Wilk and Q-Q Plot
```python
from scipy import stats
import matplotlib.pyplot as plt

def check_normality(data, col_name="variable", alpha=0.05):
    """Check normality assumption with Shapiro-Wilk test and Q-Q plot."""
    # Shapiro-Wilk test (best for n < 5000)
    stat, p = stats.shapiro(data)
    is_normal = p > alpha

    print(f"[CHECK:normality] Shapiro-Wilk W={stat:.4f}, p={p:.4f}")
    print(f"[CHECK:normality] {'PASS' if is_normal else 'FAIL'}: Data {'is' if is_normal else 'is NOT'} normally distributed (α={alpha})")

    # Q-Q plot for visual inspection
    fig, ax = plt.subplots(figsize=(6, 6))
    stats.probplot(data, dist="norm", plot=ax)
    ax.set_title(f"Q-Q Plot: {col_name}")
    plt.savefig(f"reports/figures/qq_plot_{col_name}.png", dpi=150, bbox_inches="tight")
    plt.close()

    return is_normal, stat, p

is_normal, stat, p = check_normality(df[col], col_name=col)
```

### Homogeneity of Variance: Levene's Test
```python
from scipy import stats

def check_homogeneity(*groups, alpha=0.05):
    """Check homogeneity of variance (homoscedasticity) with Levene's test."""
    stat, p = stats.levene(*groups)
    is_homogeneous = p > alpha

    print(f"[CHECK:homogeneity] Levene's W={stat:.4f}, p={p:.4f}")
    print(f"[CHECK:homogeneity] {'PASS' if is_homogeneous else 'FAIL'}: Variances {'are' if is_homogeneous else 'are NOT'} equal (α={alpha})")

    if not is_homogeneous:
        print("[CHECK:homogeneity] Recommendation: Use Welch's t-test instead of Student's t-test")

    return is_homogeneous, stat, p

is_homogeneous, stat, p = check_homogeneity(group1, group2)
```

### Independence: Durbin-Watson Test (for Regression Residuals)
```python
from statsmodels.stats.stattools import durbin_watson

def check_independence(residuals):
    """Check independence of residuals with Durbin-Watson test."""
    dw_stat = durbin_watson(residuals)

    # Interpretation: DW ≈ 2 means no autocorrelation
    # DW < 1.5 suggests positive autocorrelation
    # DW > 2.5 suggests negative autocorrelation
    if dw_stat < 1.5:
        status = "FAIL - positive autocorrelation detected"
    elif dw_stat > 2.5:
        status = "FAIL - negative autocorrelation detected"
    else:
        status = "PASS - no significant autocorrelation"

    print(f"[CHECK:independence] Durbin-Watson = {dw_stat:.3f}")
    print(f"[CHECK:independence] {status}")

    return dw_stat, status

dw_stat, status = check_independence(model.resid)
```

## Robust Alternatives

### Welch's t-test (Instead of Student's t-test)
```python
from scipy import stats

def welchs_ttest(group1, group2, alpha=0.05):
    """
    Welch's t-test - DEFAULT choice for comparing two groups.
    Does NOT assume equal variances (more robust than Student's t-test).
    """
    stat, p = stats.ttest_ind(group1, group2, equal_var=False)  # equal_var=False for Welch's

    print(f"[DECISION] Using Welch's t-test: Does not assume equal variances")
    print(f"[STAT:estimate] t-statistic = {stat:.3f}")
    print(f"[STAT:p_value] p = {p:.4f}")

    # Effect size
    from numpy import sqrt, var, mean
    n1, n2 = len(group1), len(group2)
    pooled_std = sqrt(((n1-1)*var(group1, ddof=1) + (n2-1)*var(group2, ddof=1)) / (n1+n2-2))
    d = (mean(group1) - mean(group2)) / pooled_std
    magnitude = "small" if abs(d) < 0.5 else "medium" if abs(d) < 0.8 else "large"
    print(f"[STAT:effect_size] Cohen's d = {d:.3f} ({magnitude})")

    return stat, p, d

t_stat, p_value, effect_size = welchs_ttest(treatment, control)
```

### Mann-Whitney U Test (for Non-Normal Data)
```python
from scipy import stats
import numpy as np

def mann_whitney_test(group1, group2, alpha=0.05):
    """
    Mann-Whitney U test - Non-parametric alternative to t-test.
    Use when normality assumption is violated.
    """
    stat, p = stats.mannwhitneyu(group1, group2, alternative='two-sided')

    print(f"[DECISION] Using Mann-Whitney U: Non-parametric, does not assume normality")
    print(f"[STAT:estimate] U-statistic = {stat:.3f}")
    print(f"[STAT:p_value] p = {p:.4f}")

    # Effect size: Cliff's delta (appropriate for non-parametric)
    n1, n2 = len(group1), len(group2)
    more = sum(1 for x in group1 for y in group2 if x > y)
    less = sum(1 for x in group1 for y in group2 if x < y)
    delta = (more - less) / (n1 * n2)
    magnitude = "negligible" if abs(delta) < 0.147 else "small" if abs(delta) < 0.33 else "medium" if abs(delta) < 0.474 else "large"
    print(f"[STAT:effect_size] Cliff's delta = {delta:.3f} ({magnitude})")

    return stat, p, delta

u_stat, p_value, effect_size = mann_whitney_test(treatment, control)
```

### Permutation Test (for Complex Designs)
```python
import numpy as np

def permutation_test(group1, group2, n_permutations=10000, stat_func=None):
    """
    Permutation test - Most robust, makes minimal assumptions.
    Use when parametric assumptions are violated or for complex statistics.
    """
    if stat_func is None:
        stat_func = lambda x, y: np.mean(x) - np.mean(y)

    observed = stat_func(group1, group2)
    combined = np.concatenate([group1, group2])
    n1 = len(group1)

    # Generate permutation distribution
    perm_stats = []
    for _ in range(n_permutations):
        np.random.shuffle(combined)
        perm_stat = stat_func(combined[:n1], combined[n1:])
        perm_stats.append(perm_stat)

    # Two-tailed p-value
    p_value = np.mean(np.abs(perm_stats) >= np.abs(observed))

    print(f"[DECISION] Using permutation test: Assumption-free, {n_permutations} permutations")
    print(f"[STAT:estimate] Observed difference = {observed:.4f}")
    print(f"[STAT:p_value] p = {p_value:.4f} (permutation-based)")

    # Bootstrap CI for the observed statistic
    boot_diffs = []
    for _ in range(n_permutations):
        b1 = np.random.choice(group1, size=len(group1), replace=True)
        b2 = np.random.choice(group2, size=len(group2), replace=True)
        boot_diffs.append(stat_func(b1, b2))
    ci_low, ci_high = np.percentile(boot_diffs, [2.5, 97.5])
    print(f"[STAT:ci] 95% Bootstrap CI [{ci_low:.4f}, {ci_high:.4f}]")

    return observed, p_value, ci_low, ci_high

obs, p_val, ci_low, ci_high = permutation_test(treatment, control)
```

## Memory Management
```python
print(f"[MEMORY] DataFrame size: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
# Clean up
del large_df
import gc; gc.collect()
```
