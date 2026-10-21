# Worked example: React build for a small company (fictional)

A complete `BadgeConfig` and hero wiring for the React component. Every name and fact here is made up; never copy them into a real site.

## Config (lives next to the hero component, at module level)

```tsx
import { LanyardBadge, type BadgeConfig } from "./LanyardBadge";

const badge: BadgeConfig = {
  company: {
    name: "Northwind Studio",
    descriptor: "Brand and web design",
    tagline: "Small team, sharp work.",
    iconSrc: "/brand/northwind-icon.png", iconSize: [512, 512],
    wordmarkSrc: "/brand/northwind-wordmark.png", wordmarkSize: [840, 260],
  },
  chip: "Portland, OR",
  chipLabel: "Based in",
  people: [
    { name: "Maria Lopez", role: "Founder", photo: "/badge/maria.webp" },
    { name: "Sam Okafor", role: "Lead Designer", photo: "/badge/sam.webp", photoFocusY: "18%" },
  ],
  personBack: {
    heading: "What we do",
    items: [
      { title: "Brand identity", detail: "Logos, type and color systems", icon: <Icon name="sparkle" /> },
      { title: "Websites", detail: "Design and build, start to launch", icon: <Icon name="code" /> },
      { title: "Care plans", detail: "Monthly updates and support", icon: <Icon name="shield" /> },
    ],
  },
  companyFacts: [
    ["Since", "2019"], ["Team", "6 people"], ["Based in", "Portland, OR"], ["Works", "Remote-first"],
  ],
  phone: "555-0100",
  cta: { href: "#contact", label: "Start a project" },
  theme: {
    ink: "#13233f", accent: "#2f6fe0", highlight: "#38bdf8", strap: "#2f6fe0",
    muted: "#4b5563", surface: "#f3f4f6", line: "#dde3ea",
    displayFont: "var(--font-display)", scriptFont: "var(--font-allura)",
  },
};
```

`Icon` stands for the project's own icon component; use whatever the site already has.

## Hero wiring

Use `grid lg:grid-cols-[minmax(0,1fr)_auto]`. The `auto` column matters: with `1.25fr_1fr` the 17.5rem badge left half the column empty and the headline wrapped to 3 lines. On mobile the grid stacks and the badge sits under the CTAs.

## Defaults that held up in real builds

- A hanging ID in a clear holder that spins on its strap: yes. Barcode, QR code, ID number: no.
- Card order: each person, then the company card. People 10 s each (back at 5 s, front at 8 s); company 50 s flipping every 10 s.
- Clicking the badge flips both ways; clicking a link on the back never flips.
- Higgsfield polo portraits came out usable first try (about 30 s each), even from a full-body reference photo.
