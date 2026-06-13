---
name: Polymarket Technical Console
colors:
  surface: '#0b1326'
  surface-dim: '#0b1326'
  surface-bright: '#31394d'
  surface-container-lowest: '#060e20'
  surface-container-low: '#131b2e'
  surface-container: '#171f33'
  surface-container-high: '#222a3d'
  surface-container-highest: '#2d3449'
  on-surface: '#dae2fd'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#dae2fd'
  inverse-on-surface: '#283044'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#ffb3ad'
  on-tertiary: '#68000a'
  tertiary-container: '#ff817a'
  on-tertiary-container: '#7e000f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#0b1326'
  on-background: '#dae2fd'
  surface-variant: '#2d3449'
typography:
  h1:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  h2:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  data-lg:
    fontFamily: IBM Plex Mono
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
  data-md:
    fontFamily: IBM Plex Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0em
  data-sm:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-caps:
    fontFamily: IBM Plex Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 12px
  margin: 16px
---

## Brand & Style

The design system is engineered for mission-critical trading operations where clarity and speed of interpretation are paramount. The brand personality is clinical, authoritative, and high-performance, evoking the feel of a modern aerospace cockpit or a quantitative trading floor. 

The aesthetic follows a **Technical Minimalist** approach. It prioritizes information density without sacrificing legibility. Every visual element serves a functional purpose, utilizing a "data-first" hierarchy that minimizes cognitive load during high-volatility market events. The style avoids unnecessary ornamentation, relying instead on structural grid alignment, crisp borders, and purposeful motion to guide the operator's eye to risk-on or risk-off signals.

## Colors

The color palette of the design system is anchored in a deep, dark-neutral base (#0F172A) to provide a stable, low-strain background for prolonged monitoring sessions. 

- **Primary (Cyan #06B6D4):** Represents 'Success,' 'Execution,' and 'Active' states. Used for primary calls to action, profitable trade indicators, and connected status.
- **Secondary (Amber #F59E0B):** Reserved exclusively for 'Warning,' 'Risk,' and 'Pending' states. It signals market volatility warnings or capital exposure thresholds.
- **Tertiary (Red #EF4444):** Used sparingly for critical failures, stopped bots, or liquidated positions.
- **Surface Strategy:** Employs a tonal layering system. The base background is the darkest, with containers becoming progressively lighter (#1E293B, #334155) as they rise in functional importance.

## Typography

The typography in the design system is a dual-font configuration optimized for different cognitive tasks:

1. **Space Grotesk (Headings):** Used for structural navigation and major section headers. Its geometric, slightly futuristic character provides a modern technical feel and establishes a clear hierarchy.
2. **IBM Plex Mono (Telemetry & Data):** Used for all numeric values, logs, and body text. As a monospaced font, it ensures that numbers align perfectly in tables and price feeds, allowing traders to scan for changes in digit positions (e.g., price movements) instantly.

Letter spacing is tightened for large headings to maintain density and widened for small uppercase labels to ensure legibility on dark backgrounds.

## Layout & Spacing

The design system utilizes a **Fixed Grid** model on desktop to ensure that critical telemetry widgets remain in a predictable location. A 12-column grid is standard, but the system favors "dense" layouts where gutters are kept to a minimum (12px) to pack more data into a single viewport.

- **Desktop (1440px+):** 12 columns, 12px gutters, 24px outer margins.
- **Tablet (768px-1023px):** 6 columns, 8px gutters, 16px margins.
- **Mobile (Below 768px):** 2 columns, 8px gutters, 12px margins; primary focus shifts to singular "Alert" and "Manual Killswitch" views.

Spacing follows a strict 4px base unit. Internal component padding is typically tight (8px or 12px) to maintain the professional, data-rich environment required for high-frequency trading.

## Elevation & Depth

Visual hierarchy in the design system is achieved through **Tonal Layers and Bold Borders** rather than shadows. This maintains a sharp, technical aesthetic and ensures high contrast on low-quality or high-brightness monitors.

- **Level 0 (Base):** #0F172A - The main canvas.
- **Level 1 (Panels):** #1E293B with a 1px border of #334155.
- **Level 2 (Modals/Popovers):** #334155 with a 1px border of #475569.

To indicate "active" or "focused" status, the design system utilizes a 1px solid Cyan border. Risk-sensitive areas or warning states utilize a 1px Amber border. Depth is conveyed by the subtle lightening of the background color as an element "rises" closer to the user.

## Shapes

The design system employs a **Soft (1)** roundedness strategy. A subtle 4px radius is applied to standard components (buttons, input fields, and panels). This softens the "industrial" feel just enough to make the UI feel modern and premium while maintaining the rigid structure of a professional tool.

- **Small Components (Chips/Tags):** 2px radius.
- **Standard Components (Buttons/Cards):** 4px radius.
- **Large Components (Modals/Dashboard Sections):** 8px radius.

Elements like status indicators (pips) and toggle switches may utilize a full "pill" radius to distinguish them from data-entry fields.

## Components

The design system defines the following component behaviors:

- **Buttons:** High-contrast containers. Primary buttons use solid Cyan with Navy text. Secondary buttons use an outline style with a 1px border. "Killswitch" buttons are solid Red with high-contrast White text.
- **Data Tables:** These are the core of the console. Row heights are condensed (32px-40px). Borders are only used for horizontal separation. Numbers are right-aligned to the decimal point for rapid comparison.
- **Input Fields:** Dark backgrounds (#0F172A) with a #334155 border. On focus, the border transitions to #06B6D4 with a subtle inner glow.
- **Telemetry Chips:** Small labels used for "Market Open," "Live," or "Paused." They include a small circular status pip that pulses when a process is active.
- **Risk Indicators:** Gauges and progress bars that transition from Cyan to Amber as exposure limits are approached.
- **Cards:** Used for grouping market pairs (e.g., "Yes/No" outcomes). They feature a distinct header area using Space Grotesk and a high-density body for price telemetry using IBM Plex Mono.