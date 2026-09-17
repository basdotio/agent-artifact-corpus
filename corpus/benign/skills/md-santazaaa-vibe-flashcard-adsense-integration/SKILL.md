---
name: adsense-integration
description: Integrate Google AdSense ads with placements, privacy, and component reuse.
license: MIT
compatibility: opencode
metadata:
  audience: developers
  monetization: adsense
---

## What I do
- Use the Ad component (src/components/Ad.tsx) for banner ads.
- Place ads in layout or specific components (e.g., Header, Footer, CardList).
- Update privacy page (/privacy) with AdSense links.
- Replace placeholder pub IDs and ad slots with real values.

## When to use me
Use for adding ads. Specify placement (e.g., header banner) and ad type (banner, rectangle).

## Examples
For a header banner:

```tsx
// In src/components/Header.tsx
import Ad from './Ad';

export default function Header() {
  return (
    <header>
      <Ad className="ad-banner" data-ad-slot="1234567890" />
      {/* other header content */}
    </header>
  );
}
```

Ensure AdSense script is in layout.tsx and privacy links are added.