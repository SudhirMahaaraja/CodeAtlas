---
name: Modern Engineering
colors:
  surface: '#0e1511'
  surface-dim: '#0e1511'
  surface-bright: '#343b37'
  surface-container-lowest: '#09100c'
  surface-container-low: '#161d19'
  surface-container: '#1a211d'
  surface-container-high: '#252b28'
  surface-container-highest: '#303632'
  on-surface: '#dde4de'
  on-surface-variant: '#bccac0'
  inverse-surface: '#dde4de'
  inverse-on-surface: '#2b322e'
  outline: '#86948b'
  outline-variant: '#3d4a43'
  surface-tint: '#5addaa'
  primary: '#5addaa'
  on-primary: '#003826'
  primary-container: '#23b484'
  on-primary-container: '#003f2b'
  inverse-primary: '#006c4c'
  secondary: '#a1d1b9'
  on-secondary: '#063827'
  secondary-container: '#224f3c'
  on-secondary-container: '#90bfa8'
  tertiary: '#ffb3af'
  on-tertiary: '#620e13'
  tertiary-container: '#f37c78'
  on-tertiary-container: '#6b1519'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#79fac4'
  primary-fixed-dim: '#5addaa'
  on-primary-fixed: '#002115'
  on-primary-fixed-variant: '#005139'
  secondary-fixed: '#bdedd4'
  secondary-fixed-dim: '#a1d1b9'
  on-secondary-fixed: '#002115'
  on-secondary-fixed-variant: '#224f3c'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3af'
  on-tertiary-fixed: '#410005'
  on-tertiary-fixed-variant: '#812627'
  background: '#0e1511'
  on-background: '#dde4de'
  surface-variant: '#303632'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  code-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '450'
    lineHeight: 20px
  label-caps:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1440px
  sidebar-width: 280px
---

## Brand & Style
The design system is engineered for precision, reliability, and technical clarity. It targets developers and architects who require a tool that feels like a natural extension of their existing IDE environment. The aesthetic leans into a "Modern Engineering" approach—a hybrid of high-utility corporate SaaS and sophisticated developer tools.

The visual narrative is built on:
- **Functional Minimalism:** Eliminating visual noise to prioritize codebase structure and data.
- **Organic Precision:** While maintaining a technical core, the interface uses softer geometry and a balanced typeface to reduce visual fatigue.
- **Structural Integrity:** Heavy reliance on grid alignment and subtle borders rather than aggressive shadows to define boundaries.

## Colors
The palette is optimized for long-duration focused work in a dark-mode environment.
- **Primary (Teal-Green):** Denotes "Success," "Active," and "Verified" states. It provides a modern, sophisticated take on the classic terminal "Go" signal.
- **Secondary (Sage-Slate):** Used for informational accents, links, and system-level metadata.
- **Tertiary (Coral-Rose):** Reserved for highlights, warnings, and attention-required states.
- **Neutrals:** A balanced grey-green scale provides the foundation, ensuring high contrast with text while reducing eye strain.

## Typography
The system employs a unified typeface strategy:
1. **Plus Jakarta Sans:** Used for all UI elements, navigation, and long-form prose. Its geometric nature and high x-height ensure exceptional readability at small sizes and a modern technical aesthetic.

Hierarchy is established through weight and color rather than excessive size shifts. Use `label-caps` for section headers in sidebars and table headers to provide a distinct "utility" feel. While the system uses a sans-serif font for the interface, technical data and code blocks should maintain alignment integrity.

## Layout & Spacing
This design system utilizes a strict 4px baseline grid. 
- **The Workbench Layout:** A standard 3-pane layout is preferred. A fixed left navigation (280px), a fluid center for documentation or code, and an optional right-side "Inspector" panel.
- **Gutters:** Standardized 16px (md) gutters between panels.
- **Margins:** 24px (lg) page margins on desktop, scaling down to 16px (md) on mobile.
- **Density:** High density is encouraged for data tables and code browsers, using 8px (sm) padding to maximize information on screen.

## Elevation & Depth
Depth is created through "Layered Flatness." Instead of heavy shadows, use varying surface shades and borders:
- **Level 0 (Background):** The lowest canvas layer.
- **Level 1 (Surface):** For cards, sidebars, and panels. Use a 1px subtle border.
- **Level 2 (Glass):** For modals and popovers, use a semi-transparent background with a 20px backdrop blur and a highlight border.
- **Shadows:** Only used for floating menus to provide a subtle separation from the primary surface. Use sharp, low-opacity shadows.

## Shapes
The design system uses a "Rounded" corner logic (Level 2) to maintain a professional, modern look that is more approachable than traditional sharp-edged tools.
- **Standard (8px / 0.5rem):** Used for buttons, input fields, and small UI elements.
- **Large (16px / 1rem):** Used for cards and containers.
- **Pill:** Reserved exclusively for status indicators (Tags/Chips) to differentiate them from actionable buttons.

## Components
- **Buttons:** Primary buttons use a solid Teal-Green fill. Secondary buttons are outlined with a 1px neutral border.
- **Input Fields:** Dark background, 1px border. Focus state uses a Primary (Teal-Green) glow.
- **Cards:** Defined by a 1px neutral border. For interactive cards, the border transitions to Primary (Teal-Green) on hover.
- **Code Blocks:** Use a slightly darker background than the surface. Syntax highlighting must be accessible.
- **Chips/Status:** Use the palette accents. Success = Teal-Green; Info = Sage-Slate; Warning = Coral-Rose.
- **Lists:** In sidebars, the active state is marked by a 2px vertical Primary stripe on the far left of the item.