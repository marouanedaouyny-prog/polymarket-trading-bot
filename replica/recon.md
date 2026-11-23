# Vembit bot-desk clean-room recon map

Source: `https://vembit.com/bots/desk` (public first-party page, resolved to `https://vembit.com/` landing). Clean-room only — no JS bundles, no private APIs, no network-call logging, no source inspection. Per Vembit Terms §12: no scraping/reverse-engineering/automated interference.

## Scope
- App: Vembit social-first trading web app (desktop + mobile)
- Platform: web
- Slice: bot desk / AI trading desk workflow — plain-English bot idea input, backtest-then-live flow, AI desk with RISK veto, copy trading, leaderboard
- Who it's for: retail traders (crypto/forex/commodities/indices) who want AI-assisted or copy-trading automation with human confirmation

## Sources table

| source | what it gives you |
|---|---|
| vembit.com/bots/desk (landing) | full feature list, AI desk agent roles, copy-trading mechanics, leverage, risk disclosures |
| vembit.com/terms | Terms of Service §12 (no scraping/reverse-engineering/automated interference) — clean-room boundary |
| vembit.com/privacy-policy | privacy practices (linked from footer) |

## Screen inventory

| ID | screen | route / how to get there | purpose | key components | states seen |
|---|---|---|---|---|---|
| S01 | Landing / hero | `https://vembit.com/` | value prop, CTA "Start trading" | hero image, CTA button, market stats (38 markets, 1000x leverage, 12 chart intervals) | loaded, mobile |
| S02 | Markets list | from landing "Find the markets moving right now" | browse 38 markets with price/range/volume | market cards (BTC/USD, XAU/USD, EUR/USD, NAS100...), CTA button | loaded, empty?, error |
| S03 | Market chart / trade screen | open any market | live price, 24h change/range, TradingView chart, TP/SL | TradingView chart (12 intervals), buy/sell buttons, leverage selector, TP/SL inputs, liquidation price | loading, filled, error |
| S04 | Bot desk / AI desk | "Hire your AI trading desk" / bot desk | build bot in plain English, backtest, start live, monitor | bot idea input, backtest result, start-live toggle, bot desk list | empty, loading, filled, error |
| S05 | AI coach (chart) | "Should I buy gold now?" | ask in plain English, get direction/entry/stop/target | AI composer input, AI response card, Confirm/Cancel buttons | empty, loading, filled |
| S06 | Leaderboard | leaderboard 24H/7D/30D | top trader ranking by P&L | leaderboard rows (rank, trader, P&L, win rate, markets) | loaded, mobile |
| S07 | Trader profile | open any trader's profile | positions, rank, theses, copy | profile header, position list, thesis text, copy button with margin/leverage cap/TP/SL | loaded, empty, permission denied |
| S08 | Copy trade flow | from trader profile "copy" | copy with own margin, leverage cap, optional TP/SL | margin input, leverage cap slider, TP/SL toggles, confirm | loading, filled, error |
| S09 | Login / account | "Login or create an account" | auth via Google or email | Continue with Google, Create account, Log in with email | loaded, error, permission denied |
| S10 | FAQ / risk disclosure | footer FAQ | what is Vembit, markets, leverage, copy trading, risk | FAQ accordions, risk disclosure text | loaded |

## User flows

```
F01 Build and start a bot (plain English)
    S04 bot desk -> describe idea in a sentence -> check backtest -> start it live -> bot sits on bot desk
    edge: backtest fails, user declines to start live, practice money vs real cash choice

F02 Get AI coaching on a market
    S05 AI coach -> ask "Should I buy gold now?" -> AI reads live chart -> direction/entry/stop/target -> user confirms or cancels
    edge: AI says no setup, market data stale, user ignores confirmation

F03 Copy a top trader
    S06 leaderboard -> S07 trader profile -> S08 copy flow (own margin, leverage cap, TP/SL) -> confirm
    edge: leader closes trade -> copy closes too, leverage cap breached, insufficient margin

F04 Monitor AI desk (eight agents)
    S04 AI desk -> watch CRAWLER/SOCIAL/SCAN/VET/SIZE/RISK/FILLS/CHIEF -> RISK can say no
    edge: RISK vetoes a setup, FILLS places order after approval
```

Click counts on happy path: F01 = 4 clicks (desk, describe, backtest, start-live). F02 = 3 clicks (coach, ask, confirm). F03 = 4 clicks (leaderboard, profile, copy, confirm).

## Components
- Market card: symbol, price, 24h change, 24h range, volume — used on S02, S03
- TradingView chart: 12 intervals (1 min to 1 month), drawing tools — S03
- Buy/sell buttons with leverage selector — S03, S08
- TP/SL inputs with liquidation price shown before open — S03, S08
- AI composer: text/voice input, response card with Confirm/Cancel — S05
- Bot desk list: bots with status, backtest result, start-live toggle — S04
- Leaderboard row: rank, trader, P&L, win rate, markets — S06
- Trader profile: positions, rank 24H/7D/30D, thesis — S07

## Inferred data model
```
Bot  id, idea_text, backtest_result (edge/win-rate), status (draft|backtested|live|stopped),
     margin, leverage_cap, stop_loss, take_profit, created_at, user_id
     evidence: S04 bot desk (plain-English idea, backtest check, start live)
     confidence: medium (marketing claims, no technical spec)

Trade  id, market_id, side, entry, stop, target, size, margin, leverage, status (open|closed),
       pnl, opened_at, closed_at, leader_id (if copy), user_id
       evidence: S03 trade screen, S07 positions, S08 copy flow
       confidence: medium

LeaderboardEntry  rank, trader_id, pnl_24h, pnl_7d, pnl_30d, win_rate, markets, user_id
                  evidence: S06 leaderboard (24H/7D/30D)
                  confidence: high

AISetup  market_id, direction, entry, stop, target, ai_confidence, user_confirmed, executed_at
         evidence: S05 AI coach (direction/entry/stop/target, confirm before place)
         confidence: medium
```

## Feature matrix (replica/features.csv columns: feature, area, priority, original, clone, notes)
- clone column starts at `no` for every row; filled during build at `/replica-build`.

| feature | area | priority | original | clone | notes |
|---|---|---|---|---|---|
| Plain-English bot idea input | bot desk | must | yes | no | S04 — describe idea in a sentence |
| Backtest check before live | bot desk | must | yes | no | S04 — check its backtest, then start live |
| Bot desk (list of bots) | bot desk | must | yes | no | S04 — every bot sits on your bot desk |
| Eight-agent AI desk (CRAWLER/SOCIAL/SCAN/VET/SIZE/RISK/FILLS/CHIEF) | AI desk | must | yes | no | S04 — RISK can always say no |
| RISK veto on every setup | AI desk | must | yes | no | S04 — RISK can always say no |
| AI coach: direction/entry/stop/target | AI coach | must | yes | no | S05 — reads live chart, nothing placed until confirm |
| Confirm-before-place (human-in-the-loop) | execution | must | yes | no | S05 Confirm/Cancel; nothing placed until you confirm |
| Copy trading with own margin + leverage cap + TP/SL | copy trading | must | yes | no | S08 — copy with own margin, leverage cap, optional TP/SL |
| Leaderboard 24H/7D/30D | social | should | yes | no | S06 — rank by P&L |
| Trader profile + positions | social | should | yes | no | S07 — open any trader's profile |
| Leverage 1x–1000x | trading | must | yes | no | S03 — 1x to 1000x on every market |
| Cross margin + liquidation price shown before open | trading | should | yes | no | S03 — cross margin, liquidation price shown |
| Practice money or real cash mode | execution | should | yes | no | S04/S09 — run with practice money or real cash |

## What cannot be cloned
- Vembit's actual trading venue, market data, and order execution (the platform itself)
- Copy-trading network and its users (top traders, leaderboard data) — "the network and its users"
- Vembit's AI models and agent implementations (CRAWLER, SOCIAL, SCAN, etc.) — proprietary
- 1000x leverage and copy-trading automation: excluded from live execution in this project (unsafe per Vembit risk warning; prediction-market rule)

## Size
S (a weekend) for the recon-mapped feature set as a UI prototype; the actual trading backend integration is M–L. The clone targets UX patterns and workflow, not Vembit's platform or data.

## Next step
`/replica-architect` — turn this recon map + inferred data model into `replica/architecture.md`, then `/replica-build`.
