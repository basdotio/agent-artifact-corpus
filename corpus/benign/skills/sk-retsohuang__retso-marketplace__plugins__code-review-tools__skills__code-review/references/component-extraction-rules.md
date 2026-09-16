# Component Extraction Verification Rules

When changes involve extracting shared components, verify the following:

## Rule 1: Component Parity

**What to check**: All sub-components included in the extracted component were present in ALL original implementations.

**How to verify**:

```bash
# View original file before extraction
git show <commit-hash>^:<file-path>
```

**Example issue**:

```tsx
// Extracted component includes PlatformMetricsSummary
<PlatformMetricsSummary platform={platform} metrics={metrics} />

// But original page A had it, page B didn't
// ❌ This breaks page B's behavior
```

**What to flag**: If a sub-component wasn't in ALL original files, flag it as a component extraction issue.

---

## Rule 2: Conditional Rendering

**What to check**: Blocks like `{condition && <Component />}` were present in ALL original files.

**Example pattern**:

```tsx
{statisticPlatformSupport.metricPerformance.includes(platform.shortcode) && (
  <PlatformMetricsSummary ... />
)}
```

**How to verify**:

- Check each original file before extraction
- Confirm the exact same condition existed in each file
- If conditions differed, flag as an issue

**What to flag**: If conditional rendering logic wasn't uniform across all original files.

---

## Rule 3: Props/Config Validation

**What to check**: Page-specific differences are handled via props or configuration flags, not assumptions.

**Good pattern**:

```tsx
// Component accepts prop to control visibility
<OverviewSection showMetricsSummary={true} />
```

**Bad pattern**:

```tsx
// Component assumes all pages need this feature
<OverviewSection /> // Always shows metrics summary
```

**What to flag**: When extracted components make assumptions about usage without providing configuration options.

---

## Comment Format

When flagging component extraction issues:

````markdown
**Line X-Y:**

```tsx
{
  /* problematic code */
}
```
````

> **⚠️ Component Extraction Issue**: [Brief description of what's wrong]. [Suggestion to fix it].

````

## Examples

### Example 1: Different Conditions in Originals

```markdown
**Line 45:**
```tsx
{platform.hasAnalytics && <AnalyticsPanel />}
````

> **⚠️ Component Extraction Issue**: Original files had different conditions. Page A checked `platform.hasAnalytics`, Page B checked `user.canViewAnalytics`. Add both conditions or a configuration prop.

```

```
