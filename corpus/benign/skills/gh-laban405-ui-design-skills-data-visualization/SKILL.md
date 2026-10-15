---
name: data-visualization
description: Design, review, and implement effective data visualizations using practical principles for chart selection, data ordering, visual hierarchy, colors, tooltips, legends, gridlines, trend lines, and realistic data. Use when creating charts, dashboards, analytics interfaces, or reviewing existing data visualizations.
---

# Data Visualization

Use these principles when designing, reviewing, or implementing data visualizations. Source rationale and extended examples live in `references/chart-principles.md` — read it when a decision needs more justification than the checklist below gives.

## 1. Choose a familiar chart type

Prefer chart types users already know how to read: bar/column, line, area, pie/donut. Don't invent a novel chart type (streamgraphs, etc.) unless there's a clear, specific usability win over a familiar one.

## 2. Limit pie charts to 5 slices

If a pie chart is the right call, cap it at 5 slices. Past that, switch to a bar chart — it handles more categories and comparison is easier than eyeballing angles.

## 3. Order categorical data

Sort bar/column data ascending or descending unless there's an inherent order (e.g. time). Time-series data stays chronological — never re-sorted by value.

## 4. No 3D charts

3D effects distort area/angle perception and add nothing. Never use them for decoration.

## 5. Use an intentional color palette

Don't rely on auto-generated/random series colors. Pick a deliberate palette that fits the product's visual language, keeps series distinguishable, holds contrast, and is consistent in meaning across the app (e.g. the same category is always the same color). Never make color the only channel carrying essential information — pair it with position, label, or pattern.

## 6. Don't depend on tooltips

Tooltips are supplementary. Primary values and the key comparison the chart is making must be legible without hovering.

## 7. Skip unnecessary legends

A single-series chart doesn't need a legend — use the chart title or a direct label instead. Add a legend only when there are multiple series that need disambiguating.

## 8. Use gridlines deliberately

Add gridlines only where they help the user map a data point back to an axis value. Don't default to gridlines on both axes — often one axis (or none) is enough.

## 9. Be skeptical of trend lines

Add a trend line only when it reveals something the raw plotted data doesn't already show. If it's optional insight rather than core to the point, make it toggleable.

## 10. Design and test with realistic data

Never finalize a chart design against idealized sample data. Stress-test with: very small datasets, very large datasets, long labels, missing values, zero values, negative values, wide numeric ranges, duplicate/near-identical categories, and outliers. Keep a "pretty" version for portfolio/presentation purposes separate from the "real data" version used for implementation handoff — don't let developers build off the idealized one.

## 11. Exceptions are allowed

These are guidelines, not laws. Break one when there's a clear, user-centered reason — and say what that reason is, so the exception reads as a decision rather than an oversight.

## Review checklist

- Is the chart type familiar, or is there a specific reason not to be?
- Is data ordered appropriately (sorted vs. chronological)?
- Is the palette intentional, not auto-generated, and not the sole carrier of meaning?
- Does the chart work without hovering?
- Is the legend actually needed?
- Are gridlines earning their place?
- Does a trend line add information, and can it be toggled if optional?
- Has this been checked against small, large, missing, zero, negative, and outlier data — not just the ideal sample?
- Does it still hold up at mobile/narrow widths?
