---
name: Groww Executive Pulse
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f32'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fc'
  on-surface-variant: '#bacac1'
  inverse-surface: '#dae2fc'
  inverse-on-surface: '#283044'
  outline: '#85948c'
  outline-variant: '#3c4a43'
  surface-tint: '#2fe0aa'
  primary: '#44edb7'
  on-primary: '#003828'
  primary-container: '#00d09c'
  on-primary-container: '#00533c'
  inverse-primary: '#006c4f'
  secondary: '#5ddcaf'
  on-secondary: '#003828'
  secondary-container: '#05a47b'
  on-secondary-container: '#003122'
  tertiary: '#ffc98a'
  on-tertiary: '#472a00'
  tertiary-container: '#fda417'
  on-tertiary-container: '#673f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#59fdc5'
  primary-fixed-dim: '#2fe0aa'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#7cf9ca'
  secondary-fixed-dim: '#5ddcaf'
  on-secondary-fixed: '#002116'
  on-secondary-fixed-variant: '#00513b'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#0b1326'
  on-background: '#dae2fc'
  surface-variant: '#2d3449'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  metric-kpi:
    fontFamily: Outfit
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
  code-tabular:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-mobile: 0.75rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system powers an executive product intelligence console designed for high-leverage product leaders, engineering heads, and executive operators. It merges institutional investment-grade precision with consumer-grade clarity.

### Personality & Emotional Resonance
- **Composed & Authoritative:** Conveys unwavering stability and factual confidence, sidestepping frivolous garnish in favor of high-signal data hierarchy.
- **Vibrant Yet Restrained:** Leverages signature growth-oriented emerald accents without visual fatigue or radioactive glow.
- **Analytical & Legible:** Empowers leaders to identify qualitative friction, key NPS inflections, and operational delivery vectors in under 30 seconds.

### Aesthetic Foundation: Modern High-Density Fintech
The interface pairs crisp structural boundaries with subtle surface tonality. It employs flat, crisp 1px borders, muted backdrops, and controlled tabular pacing to deliver an executive-grade dashboard environment suited for sustained analytical work.

## Colors
The color hierarchy establishes an uncompromised distinction between operational status indicators, brand identity, and structural surfaces across both dark and light modes.

### Primary & Brand Accents
- **Primary Emerald (`#00D09C`):** The primary growth indicator, active tab bar accents, and primary action fills.
- **Deep Teal (`#00A37A` / `#00B386`):** Secondary state layer for interactive hover states, sparkline fills, and high-confidence sentiment badges.
- **Forest Slate (`#064E3B` / `#042F2E`):** Low-contrast tinted backing for emerald indicators in dark mode.

### Semantic Status Tokens
- **Friction Alert (`#F59E0B` / `#D97706`):** Reserved strictly for ratings under 3 stars, regression warnings, and user frustration spikes.
- **Critical Blocker (`#EF4444` / `#DC2626`):** Used exclusively for broken user paths, checkout regressions, and deployment blockers.
- **Operational Steady (`#64748B`):** Neutral status pills for queued or in-progress tickets without negative deviance.

### Surface System
- **Dark Mode (Default):**
  - App Canvas: `#0B0F17`
  - Elevated Cards & Panes: `#131B2E`
  - High-Emphasis Overlays: `#182234`
  - Border Structures: `#1E293B` (standard), `#334155` (interactive focus)
  - Typography: `#F8FAFC` (primary), `#94A3B8` (secondary), `#64748B` (muted metadata)
- **Light Mode:**
  - App Canvas: `#F8FAFC`
  - Layer 1 Canvases: `#F1F5F9`
  - Elevated Cards & Panes: `#FFFFFF`
  - Border Structures: `#E2E8F0`
  - Typography: `#0F172A` (primary), `#334155` (secondary), `#64748B` (muted)

## Typography
The system enforces an explicit separation between structural metric delivery (`Outfit`) and analytical copy (`Plus Jakarta Sans`).

### Font Hierarchy & Roles
- **Headings & KPI Readouts (`Outfit`):** Geometric, contemporary, and confident. Headings prioritize high legibility at glance speed. Numeric values must use tabular numerals (`tnum`) to eliminate spatial shifting across weekly comparative sets.
- **Interface Copy & Data Tables (`Plus Jakarta Sans`):** Balanced, open x-height font tuned for screen density, preventing visual fatigue in dense review lists and verbatim quote blocks.

### Numerical & Tabular Integrity
Any element serving financial rates, CSAT percentages, or delivery counts must activate CSS font feature settings: `font-feature-settings: "tnum" 1, "cv05" 1`.

## Layout & Spacing
The console adheres to a fluid, structured 12-column grid system optimized for data density and spatial hierarchy across widescreen workstations and portable laptops.

### Grid Construction
- **Desktop (>= 1280px):** 12-column fluid grid, `2rem` (32px) global edge margin, `1.25rem` (20px) gutters. Top global nav persists with sticky execution, KPI metric trays span equal 4-column or 3-column splits.
- **Tablet (768px - 1279px):** 6-column fluid grid, `1.5rem` (24px) margins, `1rem` (16px) gutters. Metric cards wrap into a 2x2 grid matrix; operational boards toggle to a stacked lane view.
- **Mobile (< 768px):** 4-column reflow, `1rem` (16px) canvas margin, `0.75rem` (12px) gutters. Primary metric cards collapse into horizontally swipable carousels; secondary navigation tabs utilize scrollable horizontal pills.

### Component Spacing Principles
- **Card Padding:** KPI cards and quote containers utilize `space-lg` (24px) internal padding for executive breathing room; high-density review tables reduce padding to `space-sm` (8px) vertical by `space-md` (16px) horizontal.
- **Data Gap Rhythm:** Standard gap between inline labels and values is strictly locked to `space-xs` (4px) or `space-sm` (8px) to preserve cognitive grouping.

## Elevation & Depth
Depth in the console is driven by surface contrast and low-contrast borders rather than stacked physical drop shadows.

### Border-Dominant Hierarchy
- **Level 0 (App Canvas):** Pure background canvas (`#0B0F17` dark / `#F8FAFC` light).
- **Level 1 (Card & Section Containers):** Elevated surface fill (`#131B2E` dark / `#FFFFFF` light) backed by a crisp 1px solid border (`#1E293B` dark / `#E2E8F0` light).
- **Level 2 (Active/Hover Cards & Popovers):** Elevated surface fill (`#182234` dark / `#FFFFFF` light) with an ultra-subtle ambient drop shadow: `0 8px 24px -4px rgba(0, 0, 0, 0.25)`.
- **Level 3 (Modal Dialogs & Command Menus):** Top tier overlays framed with a dual border: 1px inner stroke (`#334155` dark) and a diffuse backdrop blur: `backdrop-filter: blur(8px)`.

### Glass Accents & Glare Prevention
Translucency is reserved exclusively for fixed top navigation headers and filter toolbars (`rgba(19, 27, 46, 0.85)` in dark mode with `12px` blur). Pure saturated colors are prohibited on container backgrounds to eliminate eye fatigue.

## Shapes
The system implements a structured geometry scale (`roundedness: 2`) balancing corporate clarity with modern tactile interfaces.

### Token Applications
- **Base Components (`0.5rem` / 8px):** Primary form controls, text inputs, table cell selections, dropdown menus, and standard utility buttons.
- **Containers & KPI Cards (`rounded-lg` / 16px):** Primary content cards, data tables, quote highlights, and analytical split views.
- **Overlays & Modals (`rounded-xl` / 24px):** Executive insight dialogs, settings drawers, and command overlays.
- **Status Pills & Chips (`9999px` / Full Pill):** Qualitative badges, sentiment tags, NPS range tags, and interactive filter chips.

## Components

### 1. KPI Metric Cards with Sparklines
- **Structure:** 16px rounded surface container with Level 1 borders.
- **Header:** Label metadata (`label-sm`, muted slate) left-aligned with contextual percentage badge right-aligned.
- **Body:** Large tabular metric (`metric-kpi`), accompanied by inline delta indicators: Positive (`#00D09C` with arrow up), Negative Alert (`#F59E0B` or `#EF4444` with arrow down).
- **Sparkline Integration:** Inline SVG path resting along the bottom boundary. Stroke width: `2px`; stroke color matches trajectory status; fill applies a soft vertical gradient fading to transparent.

### 2. Interactive Navigation Tabs
- **Layout:** Horizontal segment bar with `0.5rem` outer radius containing Overview, Themes, Quotes, Actions, Reviews, and Delivery.
- **Inactive State:** Transparent background, muted text (`#94A3B8`), hover transition to secondary text.
- **Active State:** Surface contrast background, high-contrast text (`#F8FAFC` dark), and a persistent 2px emerald bottom edge bar (`#00D09C`).

### 3. Pill Status Badges
- **Dimensions:** Fixed height of 24px, pill roundedness (`9999px`), inline-flex alignment with `space-sm` horizontal padding.
- **Tone Pairing:**
  - *High Impact / Praise:* `#00D09C` text with 12% opacity emerald background fill.
  - *Warning / Friction:* `#F59E0B` text with 12% opacity amber fill.
  - *Critical Blocker:* `#EF4444` text with 12% opacity red fill.
  - *Operational / In Progress:* `#64748B` text with 12% opacity slate fill.

### 4. Qualitative Quote Cards
- **Structure:** Level 1 container styling with a prominent decorative quote glyph (`“`) anchored top-left in low-opacity teal (`#00D09C`, 20% opacity).
- **Typography:** Body text rendered in `body-md` italic slate, accompanied by user metadata (tier, app version, star rating) positioned in the card footer.
- **Sentiment Highlight:** Vertical 3px left border colored to match the verified sentiment.

### 5. Filterable Review Table
- **Header:** Sticky table header row with uppercase `label-sm` text, subtle 1px bottom border, and sort arrows.
- **Rows:** Alternating subtle row backgrounds with a 1px border divider. Row height locked to 48px for density.
- **Interactions:** Subtle hover highlight (`#182234` dark / `#F1F5F9` light). Expandable drawer reveals raw crash logs or unedited verbatim user text.

### 6. Delivery Status Board
- **Kanban Columns:** Backlog, In Flight, Blocked, Deployed.
- **Column Header:** Sticky column title accompanied by ticket count pill and velocity estimate.
- **Task Cards:** Compact 8px rounded cards featuring engineer avatar, milestone badge, and priority pip.

### 7. Global Theme Switcher
- **Pattern:** Segmented pill toggle housing compact Sun and Moon icons.
- **Interaction:** Micro-spring slide transition when toggling between dark canvas (`#0B0F17`) and crisp light canvas (`#F8FAFC`). No full-page flicker or unstyled flashes.