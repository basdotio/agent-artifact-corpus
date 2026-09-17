---
name: angular-theme
description: Implements a global ThemeService for managing light/dark mode using Signals, LocalStorage, and SSR compatibility.
---

# Angular Theme Service

This skill provides a plug-and-play service to manage application theming (Light/Dark mode).
It handles:

1.  **State Management**: Uses Angular `signal` for reactive updates.
2.  **Persistence**: Saves preference to `localStorage`.
3.  **DOM Manipulation**: Updates the `data-theme` attribute on the `<html>` tag.
4.  **SSR Compatibility**: Checks `isPlatformBrowser` to avoid errors during server-side rendering.

## Implementation

Create the service file in `src/services/theme.service.ts`.

```typescript
import { Injectable, signal, inject, effect, PLATFORM_ID } from "@angular/core";
import { DOCUMENT, isPlatformBrowser } from "@angular/common";

type Theme = "light" | "dark";

@Injectable({
  providedIn: "root",
})
export class ThemeService {
  private document = inject(DOCUMENT);
  private platformId = inject(PLATFORM_ID);

  // Signal to hold the current theme state
  private _theme = signal<Theme>("light");

  // Public readonly signal for consumers
  readonly theme = this._theme.asReadonly();

  constructor() {
    // Only access DOM and localStorage in the browser
    if (isPlatformBrowser(this.platformId)) {
      this.loadTheme();

      // Reactively update the DOM whenever the signal changes
      effect(() => {
        const htmlElement = this.document.documentElement;
        htmlElement.setAttribute("data-theme", this._theme());
      });
    }
  }

  setTheme(theme: Theme): void {
    this._theme.set(theme);
    localStorage.setItem("theme", theme);
  }

  toggleTheme(): void {
    const newTheme = this._theme() === "light" ? "dark" : "light";
    this.setTheme(newTheme);
  }

  loadTheme(): void {
    const savedTheme = localStorage.getItem("theme") as Theme | null;
    this.setTheme(savedTheme ?? "light");
  }
}
```

## Usage

Inject `ThemeService` in your main layout or navbar component to bind the toggle action.

```typescript
export class NavbarComponent {
  themeService = inject(ThemeService);

  toggle() {
    this.themeService.toggleTheme();
  }
}
```

## Global Styles (`src/styles.css`)

```css
@import "tailwindcss";
@custom-variant dark (&:where(.dark, .dark *));

:root {
  /* Initial Theme Variables (Light) */
  --color-primary: #35b2c0;
  --color-secondary: #a8be04;
  --color-accent: #f2788f;
  --color-background: #ffffff;
  --color-text: #000000;

  --color-danger: #c90d0d;
  --color-warning: #f8a50d;
  --color-success: #34a851;
  --color-info: #4590f2;
}

/* Dark Mode Overrides */
[data-theme="dark"] {
  --color-primary: #3fbcca;
  --color-secondary: #e5fb41;
  --color-accent: #870d24;
  --color-background: #000000;
  --color-text: #ffffff;

  --color-danger: #f05252;
  --color-warning: #c27803;
  --color-success: #0e9f6e;
  --color-info: #3f83f8;
}

/* Tailwind Configuration linking CSS variables */
@theme {
  --color-primary: var(--color-primary);
  --color-secondary: var(--color-secondary);
  --color-accent: var(--color-accent);
  --color-background: var(--color-background);
  --color-text: var(--color-text);

  --color-danger: var(--color-danger);
  --color-warning: var(--color-warning);
  --color-success: var(--color-success);
  --color-info: var(--color-info);
}
```
