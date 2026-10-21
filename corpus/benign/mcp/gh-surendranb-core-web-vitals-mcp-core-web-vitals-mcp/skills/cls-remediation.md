# Cumulative Layout Shift (CLS) Remediation Playbook

A structured engineering playbook for identifying, diagnosing, and permanently eliminating layout shifts using Google CrUX field telemetry and Lighthouse diagnostics.

## 1. CLS Thresholds & Targets

Cumulative Layout Shift measures visual stability by aggregating all unexpected layout shifts occurring during the lifespan of a page.

| Assessment | CLS Score (p75) | User Experience |
|---|---|---|
| **Good** | $\le 0.10$ | Stable, predictable reading & clicking |
| **Needs Improvement** | $0.10 - 0.25$ | Disorienting jumping, accidental clicks |
| **Poor** | $> 0.25$ | Severe usability disruption |

## 2. Primary Root Causes of CLS

1. **Images and Video Without Explicit Dimensions**:
   - Browser cannot allocate placeholder space before image headers load, pushing subsequent content downwards upon load.
2. **Dynamic Injected Content (Banners, Ads, Cookie Consents)**:
   - Elements inserted above existing content without reserving layout container heights.
3. **Web Fonts Causing FOIT / FOUT**:
   - Fallback font metrics differing from downloaded custom web font, causing paragraphs to re-wrap.
4. **CSS Animations on Layout-Triggering Properties**:
   - Animating `top`, `left`, `margin`, or `height` instead of hardware-accelerated `transform` and `opacity`.

## 3. Diagnostic Workflow

### Step 1: Query CrUX Field Metrics
Run `get_crux_metrics(url, form_factor="ALL_FORM_FACTORS")` to check the 75th percentile CLS score.
- If $p75 \le 0.10$, the page meets the Core Web Vitals target.
- If $p75 > 0.10$, inspect whether mobile or desktop has higher shifts.

### Step 2: Audit Lab Layout Shifts with PageSpeed
Run `audit_pagespeed(url)` and inspect the `cumulative-layout-shift` audit and `layout-shift-elements` table to pinpoint the exact DOM elements shifting during render.

## 4. Remediation Strategies

### Strategy A: Always Reserve Aspect Ratio on Images & Media
Always declare `width` and `height` attributes on HTML `<img>` and `<video>` tags or specify CSS `aspect-ratio`.
```html
<!-- Explicit HTML dimensions let browser compute aspect ratio immediately -->
<img src="/article-cover.jpg" width="1200" height="630" alt="Cover" style="width: 100%; height: auto;">
```
```css
/* Or declare aspect-ratio in CSS */
.responsive-card-media {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}
```

### Strategy B: Reserve Slot Heights for Ads, Embeds, and Widgets
Never inject ads, cookie banners, or widgets into zero-height containers.
```html
<!-- Pre-allocated ad slot with min-height -->
<div class="ad-slot-container" style="min-height: 250px; min-width: 300px; display: flex; align-items: center; justify-content: center;">
  <!-- Ad scripts will render inside without shifting the page -->
</div>
```

### Strategy C: Modern Font Fallback Metric Overrides
Prevent layout shifts during font swaps using CSS `@font-face` metric override descriptors (`size-adjust`, `ascent-override`, `descent-override`).
```css
@font-face {
  font-family: 'Fallback-Inter';
  src: local('Arial');
  ascent-override: 90%;
  descent-override: 22%;
  line-gap-override: 0%;
  size-adjust: 107%;
}

body {
  font-family: 'Inter', 'Fallback-Inter', sans-serif;
}
```

### Strategy D: Animate Only `transform` and `opacity`
Never animate geometric layout properties.
```css
/* BAD: triggers layout reflows and shifts */
.drawer {
  transition: height 0.3s ease;
}

/* GOOD: GPU-accelerated compositing */
.drawer {
  transition: transform 0.3s ease;
  transform: translateY(0);
}
```

## 5. Verification Checklist

1. Lab check: Run `audit_pagespeed(url)` to ensure synthetic CLS is $0.00$ or $< 0.05$.
2. Field check: Run `get_crux_history(url)` to verify that production 28-day rolling CLS remains firmly below $0.10$.
