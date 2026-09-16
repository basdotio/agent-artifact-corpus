#!/bin/bash

# Responsive Breakpoints Reference — bmad-ux planning skill
# Outputs the standard breakpoint reference to embed in DESIGN.md.
#
# Run from the plugin root:
#   bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/responsive-breakpoints.sh"
#
# Copy the output into the Breakpoints section of DESIGN.md (design tokens).

cat << 'EOF'
================================================================================
                  RESPONSIVE BREAKPOINTS REFERENCE  (bmad-ux planning)
================================================================================

STANDARD BREAKPOINTS (Mobile-First)
--------------------------------------------------------------------------------

Mobile (Extra Small)
  Range:        320px - 767px
  Target:       Phones in portrait and landscape
  Columns:      1 column layout
  Container:    100% width, 16px padding
  Font base:    16px (prevents iOS zoom)
  Touch target: >= 44px x 44px
  Media query:  @media (min-width: 320px) { /* base styles */ }

Tablet (Medium)
  Range:        768px - 1023px
  Target:       Tablets in portrait, large phones in landscape
  Columns:      2 column layout
  Container:    100% width, 24px padding
  Font base:    16px
  Touch target: >= 44px x 44px (still touch-capable)
  Media query:  @media (min-width: 768px) { /* tablet styles */ }

Desktop (Large)
  Range:        1024px - 1439px
  Target:       Laptops, small desktops
  Columns:      3-4 column layout
  Container:    960px - 1200px max-width, centered
  Font base:    18px
  Click target: >= 40px x 40px (mouse-capable)
  Media query:  @media (min-width: 1024px) { /* desktop styles */ }

Desktop XL (Extra Large)
  Range:        1440px+
  Target:       Large desktops, high-res displays
  Columns:      4-6 column layout
  Container:    1200px - 1440px max-width, centered
  Font base:    18px
  Click target: >= 40px x 40px
  Media query:  @media (min-width: 1440px) { /* xl desktop styles */ }

================================================================================

RESPONSIVE TYPOGRAPHY SCALE (for DESIGN.md tokens)
--------------------------------------------------------------------------------

Mobile (320px+):
  H1:     28px / 1.75rem  (line-height: 1.2)
  H2:     24px / 1.5rem   (line-height: 1.25)
  H3:     20px / 1.25rem  (line-height: 1.3)
  H4:     18px / 1.125rem (line-height: 1.4)
  Body:   16px / 1rem     (line-height: 1.5)
  Small:  14px / 0.875rem (line-height: 1.5)

Tablet (768px+):
  H1:     36px / 2.25rem  (line-height: 1.2)
  H2:     28px / 1.75rem  (line-height: 1.25)
  H3:     22px / 1.375rem (line-height: 1.3)
  H4:     18px / 1.125rem (line-height: 1.4)
  Body:   16px / 1rem     (line-height: 1.5)
  Small:  14px / 0.875rem (line-height: 1.5)

Desktop (1024px+):
  H1:     48px / 3rem     (line-height: 1.2)
  H2:     36px / 2.25rem  (line-height: 1.25)
  H3:     24px / 1.5rem   (line-height: 1.3)
  H4:     20px / 1.25rem  (line-height: 1.4)
  Body:   18px / 1.125rem (line-height: 1.6)
  Small:  16px / 1rem     (line-height: 1.5)

Desktop XL (1440px+):
  H1:     56px / 3.5rem   (line-height: 1.2)
  H2:     40px / 2.5rem   (line-height: 1.25)
  H3:     28px / 1.75rem  (line-height: 1.3)
  H4:     22px / 1.375rem (line-height: 1.4)
  Body:   18px / 1.125rem (line-height: 1.6)
  Small:  16px / 1rem     (line-height: 1.5)

================================================================================

COMPONENT LAYOUT BY BREAKPOINT (for EXPERIENCE.md screen specs)
--------------------------------------------------------------------------------

Navigation:
  Mobile:   Hamburger menu (>=), full-screen overlay or bottom drawer
  Tablet:   Expanded menu or visible sidebar
  Desktop:  Horizontal navigation bar with dropdowns / mega-menu

Cards:
  Mobile:   1 column, 100% width, stacked
  Tablet:   2 columns, 50% width each (minus gap)
  Desktop:  3-4 columns, equal width grid

Forms:
  Mobile:   100% width inputs, stacked; large submit (full width)
  Tablet:   Some inline fields (e.g., first/last name)
  Desktop:  Max 400-600px width, inline where appropriate

Modals:
  Mobile:   Full screen or slide from bottom
  Tablet:   80% width, centered overlay
  Desktop:  Max 600px width, centered overlay

Tables:
  Mobile:   Card view or horizontal scroll with sticky first column
  Tablet:   Visible key columns; scroll for extras
  Desktop:  Full table layout

Sidebar:
  Mobile:   Hidden (drawer or bottom sheet)
  Tablet:   Collapsible
  Desktop:  Always visible, sticky

================================================================================

DESIGN.md SPACING SCALE (8px base unit)
--------------------------------------------------------------------------------

  --space-0:   0
  --space-1:   4px   (0.25rem)
  --space-2:   8px   (0.5rem)
  --space-3:   12px  (0.75rem)
  --space-4:   16px  (1rem)
  --space-6:   24px  (1.5rem)
  --space-8:   32px  (2rem)
  --space-12:  48px  (3rem)
  --space-16:  64px  (4rem)
  --space-24:  96px  (6rem)

  Container padding:  mobile 16px | tablet 24px | desktop 32px
  Component gap:      mobile 16px | tablet 24px | desktop 32px
  Section margin:     mobile 32px | tablet 48px | desktop 64px

================================================================================

WCAG REFLOW REQUIREMENT
--------------------------------------------------------------------------------

  No horizontal scrolling at 320px viewport width (WCAG 1.4.10).
  Test every screen at 320px during EXPERIENCE.md screen spec review.

  Contrast reminder:
    bash "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/wcag-checklist.sh"
    python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #fg #bg

================================================================================

PLANNING BEST PRACTICES
--------------------------------------------------------------------------------

  Specify in DESIGN.md (tokens):
    - Exact breakpoint values (320 / 768 / 1024 / 1440)
    - Container max-widths and padding at each breakpoint
    - Typography scale per breakpoint
    - Component layout rules per breakpoint

  Specify in EXPERIENCE.md (screens):
    - Which layout applies to each screen at each breakpoint
    - Navigation pattern used per breakpoint
    - Any breakpoint-specific interactions (swipe, hover, etc.)

================================================================================
EOF
