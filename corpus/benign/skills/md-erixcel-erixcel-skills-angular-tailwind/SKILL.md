---
name: angular-tailwind
description: Minimal viable guide to setup TailwindCSS v4 with PostCSS in Angular.
---

# Tailwind CSS Setup (Angular)

This skill guides you through the minimal setup to get Tailwind CSS running in an Angular project.

## 1. Install Dependencies

Run the following command to install Tailwind CSS, PostCSS, and the Tailwind PostCSS plugin:

```bash
npm install tailwindcss @tailwindcss/postcss postcss
```

## 2. Configure PostCSS

Create a file named `.postcssrc.json` in the root of your project (where `package.json` is) and add the following content:

**File**: `.postcssrc.json`

```json
{
  "plugins": {
    "@tailwindcss/postcss": {}
  }
}
```

## 3. Configure Styles

Add the Tailwind CSS import to your global styles file.

**File**: `src/styles.css`

```css
@import "tailwindcss";
```

That's it! Tailwind CSS is now ready to use.
