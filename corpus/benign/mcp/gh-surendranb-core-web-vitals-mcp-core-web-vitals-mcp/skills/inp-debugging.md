# Interaction to Next Paint (INP) Debugging Playbook

A structured engineering playbook for diagnosing, profiling, and mitigating Interaction to Next Paint (INP) latency using Google CrUX real-user data and web performance profiling techniques.

## 1. INP Thresholds & Targets

INP replaced First Input Delay (FID) as a Core Web Vital in March 2024. INP assesses overall page responsiveness by observing the latency of all discrete user interactions (clicks, taps, and key presses) throughout the lifespan of a page visit.

| Assessment | INP Duration (p75) | User Experience |
|---|---|---|
| **Good** | $\le 200\text{ ms}$ | Immediate visual feedback |
| **Needs Improvement** | $200\text{ ms} - 500\text{ ms}$ | Laggy responsiveness, sluggish inputs |
| **Poor** | $> 500\text{ ms}$ | Froze/unresponsive UI, input dropping |

## 2. Anatomy of an Interaction

An interaction's duration is divided into three distinct phases:

$$\text{INP} = \text{Input Delay} + \text{Processing Duration} + \text{Presentation Delay}$$

1. **Input Delay**:
   - Time between user physical interaction (finger tap, mouse click) and event callbacks firing.
   - Root Cause: Main thread saturated by long background tasks or heavy script compilation.
2. **Processing Duration**:
   - Total time executed by event listener callbacks (`click`, `pointerdown`, `keydown`).
   - Root Cause: Expensive calculations, synchronous DOM reads/writes, heavy client-side state recalculations.
3. **Presentation Delay**:
   - Time after event callbacks complete until the browser recalculates layout/styles and paints the next visual frame.
   - Root Cause: Large DOM sizes (>1,500 nodes), complex CSS recalculations, synchronous canvas or SVG repaints.

## 3. Diagnostic Workflow

### Step 1: Check CrUX Real-User Field Metrics
Run `get_crux_metrics(url, form_factor="PHONE")` to inspect the 75th percentile of real-user INP.
- Note whether the percentage of Good interactions is $\ge 75\%$.
- Compare `PHONE` vs `DESKTOP`. Mobile devices with constrained CPU power typically exhibit significantly higher INP than desktop machines.

### Step 2: Correlate with Lab Total Blocking Time (TBT)
Run `audit_pagespeed(url, strategy="mobile")` and inspect Total Blocking Time (TBT).
- While INP requires real human interaction, TBT in lab tests measures main-thread blocking time during load and strongly correlates with poor initial INP.

## 4. Remediation Strategies

### Strategy A: Yield to the Main Thread (`scheduler.yield()` & `setTimeout`)
Break monolithic long tasks (>50ms) into discrete micro-chunks to let the browser process pending inputs and paint visual updates.
```javascript
// Modern yielding with scheduler.yield() fallback
async function yieldToMain() {
  if ('scheduler' in window && 'yield' in window.scheduler) {
    return await window.scheduler.yield();
  }
  return new Promise((resolve) => setTimeout(resolve, 0));
}

async function handleComplexFilter(items) {
  // 1. Give immediate visual feedback (e.g. show spinner or update button state)
  setLoadingState(true);
  await yieldToMain();

  // 2. Perform chunked processing
  for (let i = 0; i < items.length; i += 100) {
    processBatch(items.slice(i, i + 100));
    await yieldToMain();
  }

  setLoadingState(false);
}
```

### Strategy B: Optimize Event Callbacks
- **Debounce / Throttle Frequent Inputs**: Always debounce keystrokes in search autocomplete and throttle resize/scroll handlers.
- **Move Heavy Work to Web Workers**: Heavy mathematical parsing, sorting of thousands of rows, or JSON transforms should execute off the main thread.
- **Avoid Forced Synchronous Layout / Layout Thrashing**: Never alternate reading geometric properties (`offsetWidth`, `getBoundingClientRect()`) with writing styles in a loop.

### Strategy C: Optimize Presentation Delay
- **Keep DOM Size Lean**: Reduce DOM trees exceeding 1,500 nodes. Use virtualized lists for long feeds or tables.
- **CSS `content-visibility: auto`**: Defer rendering of off-screen elements.
  ```css
  .feed-card {
    content-visibility: auto;
    contain-intrinsic-size: 0 450px;
  }
  ```

## 5. Verification Checklist

1. Verify lab TBT is $\le 200\text{ ms}$ via `audit_pagespeed(url)`.
2. Inspect field trends via `get_crux_history(url)` to verify that 75th percentile INP shifts into the $\le 200\text{ ms}$ green bracket.
