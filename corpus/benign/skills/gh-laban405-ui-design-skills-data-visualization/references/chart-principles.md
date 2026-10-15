# Chart Design Principles — Extended Notes

Source material: Ryan Bales, "Designing Charts — Principles Every Designer Should Know" (UX Collective, 2017).

These notes give the reasoning behind each rule in SKILL.md, for cases where a quick checklist isn't enough to make the call.

## Use a familiar chart type

Novel chart types (streamgraphs, radial variants, etc.) are fun to design but force the user to learn a new visual language before they can read the data at all. Stick to area, bar/column, line, or pie/donut unless a novel form has a specific, demonstrable comprehension advantage for this dataset.

## Pie charts: 5 slices max

Beyond ~5 slices, comparing angles gets unreliable, labeling gets cramped, and hover interactions become a crutch for a chart that should just be a bar chart. If the story is "which category is biggest," a sorted bar chart usually tells it better than a pie chart regardless of slice count.

## Order the data series

Sorting ascending/descending (for non-temporal categorical data) lets the eye immediately see rank and magnitude. Time-series data should never be re-sorted by value — chronological order is itself information.

## Avoid 3D charts

3D perspective distorts the visual encoding (bar height, slice angle, area) that the chart depends on for accurate reading. It adds visual interest at the direct cost of accuracy — there's no dataset where this trade is worth it.

## Don't use randomly generated colors

Auto-palettes from charting libraries optimize for "looks different enough," not for fitting the product's visual language or encoding meaning consistently. Design an explicit palette: enough hues for the max expected series count, sufficient contrast between adjacent series, and stable category→color mapping across every chart in the product. Never make color the sole channel for critical information (colorblind users, print, grayscale contexts).

## Trend lines are usually a distraction

A trend line only earns its place if it shows something not already visible in the plotted points — otherwise it's decoration masquerading as analysis. When it's a nice-to-have rather than load-bearing, let users toggle it off.

## Don't depend on tooltips

Tooltips should expand on information already visible, not be the only way to read the chart's primary values. If a user with a static screenshot of the chart can't get the main point, the tooltip is doing too much work.

## Skip legends when not needed

A legend for a single data series just consumes space to restate the chart title. Use direct labeling or the title instead, and reserve legends for genuinely disambiguating multiple series.

## Grid lines only when helpful

Grid lines help the eye travel from an axis label to a data point — useful on charts where users need to read precise-ish values off an axis, less useful on simple at-a-glance charts. Decide per-axis: many charts only need gridlines on one axis, not both.

## Use real data in mockups

Idealized sample data (evenly spaced, no missing values, short labels) makes for pretty portfolio shots but hides the layout problems that show up with real data: long labels wrapping, missing/null values needing a visual treatment, outliers blowing out the axis scale, near-duplicate categories crowding each other. Keep two versions when needed:
1. An aesthetically optimized version for presentation/portfolio use.
2. A realistic version, built from representative production data, that's the one actually handed to engineering.

## Exceptions are allowed

Every rule above is a default, not a constraint. Data is messy and the story it tells doesn't always fit the common patterns — when you break a rule, be able to say why the exception improves comprehension for this specific case.
