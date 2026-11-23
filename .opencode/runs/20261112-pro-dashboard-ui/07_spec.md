# S7 SPEC — design tokens & layout (Level L3 product dashboard)

Level: L3 product dashboard (internal trading tool). 3D/motion rejected — does not improve communication for a trading readout; plain HTML/CSS/JS.

Color tokens (:root):
- --ink #070a14 (base bg), --surface #0f172a (cards), --surface-lift #131b28 (inputs/buttons)
- --border #1e293b, --border-hover #334155
- --text #f1f5f9, --text-dim #cbd5e1, --muted #64748b
- --accent #22d3ee (cyan, live data), --up #34d399, --down #fb7185, --warn #fbbf24 (SIMULATED banner, kill switch)
- --sim-bg / --sim-border, --live-bg / --live-border (mode pills)
- --radius 6px

Type: Inter (single family), sentence-case labels (no ALL-CAPS tell), tabular-nums for money, tracking on small labels.

Layout:
- Top band: brand mark + title | center: SIMULATED/LIVE pill + mode pill + server time | right: kill switch + refresh.
- Prominent SIMULATED pill (yellow, always visible in paper mode).
- Stat band (5/2 grid mobile): balance, 24h P&L, win rate, drawdown, positions.
- Main grid 2/1: open positions table + recent trades table.
- Full-width canvas equity curve below.
- Circuit-breaker alert bar (red) when triggered; kill switch disables itself when active.

Principles:
- Left-aligned, borders/whitespace for structure (no rounded-card soup, no shadows, no gradient decoration).
- Motion only on user action + one page-load fade; respects prefers-reduced-motion.
- No external deps; single file; canvas equity curve.

Build-vs-extend: extend existing HTML template (minimal diff), not the empty Next.js shell.
