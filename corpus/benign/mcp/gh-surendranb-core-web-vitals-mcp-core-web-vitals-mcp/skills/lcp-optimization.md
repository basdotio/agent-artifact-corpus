# Largest Contentful Paint (LCP) Optimization Playbook

A structured engineering playbook for diagnosing and resolving Largest Contentful Paint (LCP) bottlenecks using CrUX real-user data and Lighthouse lab diagnostics.

## 1. LCP Thresholds & Targets

Largest Contentful Paint measures perceived load speed by reporting the render time of the largest image or text block visible within the initial viewport.

| Assessment | LCP Duration (p75) | User Experience |
|---|---|---|
| **Good** | $\le 2.5\text{ s}$ (2500 ms) | Fast, responsive visual rendering |
| **Needs Improvement** | $2.5\text{ s} - 4.0\text{ s}$ | Noticeable visual lag |
| **Poor** | $> 4.0\text{ s}$ (4000 ms) | Significant abandonment risk |

## 2. The 4 Sub-Parts of LCP

Every LCP duration is composed of 4 discrete phases:

$$\text{LCP} = \text{TTFB} + \text{Resource Load Delay} + \text{Resource Load Duration} + \text{Element Render Delay}$$

1. **Time to First Byte (TTFB)** (~40% of budget, target $\le 800\text{ ms}$):
   - Time from navigation start until browser receives first byte of HTML.
2. **Resource Load Delay** (<10% of budget):
   - Time between HTML arrival and browser discovering the LCP resource (e.g., hero image URL).
3. **Resource Load Duration** (~40% of budget):
   - Time spent downloading the LCP image or font asset over the network.
4. **Element Render Delay** (<10% of budget):
   - Time between resource download completing and element actually rendering onto the screen (blocked by JavaScript execution, CSSOM parsing, or layout recalculations).

## 3. Diagnostic Workflow

### Step 1: Query CrUX Field Real-User Data
Run `get_crux_metrics(url, form_factor="PHONE")` to inspect the 75th percentile LCP distribution across real mobile visitors.
- If $p75 \le 2500\text{ ms}$: LCP passes the Google Core Web Vitals assessment.
- If $p75 > 2500\text{ ms}$: Determine if issue is device-specific by checking `DESKTOP` vs `PHONE`.

### Step 2: Audit with PageSpeed Insights
Run `audit_pagespeed(url, strategy="mobile")` to identify:
- Exact LCP element (image, text node, SVG, video poster).
- TTFB / Server Response Time (`server-response-time`).
- Render-blocking resources (`render-blocking-resources`).
- Image compression and modern format opportunities (`modern-image-formats`, `uses-optimized-images`).

## 4. Remediation Strategies

### Strategy A: Eliminate Resource Load Delay
- **Preload Critical Hero Assets**: Never hide the LCP image behind external CSS classes or lazy loaders.
  ```html
  <!-- Head preload with fetchpriority="high" -->
  <link rel="preload" fetchpriority="high" as="image" href="/assets/hero-banner.webp" type="image/webp">
  ```
- **Disable Lazy Loading on LCP Image**: Never place `loading="lazy"` on above-the-fold hero elements.
  ```html
  <!-- BAD: delays LCP by up to 1-2 seconds -->
  <img src="/hero.jpg" loading="lazy">

  <!-- GOOD: immediate discovery & fetch -->
  <img src="/hero.webp" fetchpriority="high" decoding="async" alt="Hero">
  ```

### Strategy B: Optimize Resource Load Duration
- **Modern Next-Gen Formats**: Convert large JPEGs/PNGs to AVIF or WebP. Typical bandwidth reduction is 50-70%.
- **Responsive Images (`srcset` & `sizes`)**: Ensure mobile devices do not download desktop 4K banners.
  ```html
  <picture>
    <source srcset="/hero-mobile.avif" media="(max-width: 640px)" type="image/avif">
    <source srcset="/hero-desktop.avif" media="(min-width: 641px)" type="image/avif">
    <img src="/hero-desktop.jpg" alt="Hero" fetchpriority="high">
  </picture>
  ```
- **CDN Edge Caching**: Serve assets with `Cache-Control: public, max-age=31536000, immutable`.

### Strategy C: Eliminate Render Delay
- **Inline Critical CSS**: Defer non-critical stylesheets or load asynchronously.
- **Defer Non-Critical JavaScript**: Add `defer` or `type="module"` to all third-party and application scripts.
  ```html
  <script src="/app.js" defer></script>
  ```
- **Font Display Swap**: Avoid invisible text during font loading (FOIT).
  ```css
  @font-face {
    font-family: 'Inter';
    font-display: swap;
    src: url('/fonts/inter.woff2') format('woff2');
  }
  ```

## 5. Verification Checklist

1. Run `audit_pagespeed(url)` in lab mode to ensure LCP under simulated throttling is $< 2.5\text{ s}$.
2. Run `get_crux_history(url)` after 14-28 days to confirm p75 improvements in production real-user data.
