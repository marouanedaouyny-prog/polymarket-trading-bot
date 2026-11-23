## Parity: 20.0 / 100

features 20.0  (13 counted, must-haves 0 of 9 done)

Not shippable yet: 9 must-have features are not done.

## By area, weakest first
- copy trading                   0.0  (1 features)
- social                         0.0  (2 features)
- trading                        0.0  (2 features)
- bot desk                      16.7  (3 features)
- AI desk                       25.0  (2 features)
- AI coach                      50.0  (1 features)
- execution                     50.0  (2 features)

## Missing, in build order
- [must] AI desk: Eight-agent AI desk (CRAWLER/SOCIAL/SCAN/VET/SIZE/RISK/FILLS/CHIEF), no  (S04 — RISK can always say no)
- [must] bot desk: Bot desk (list of bots), no  (S04 — every bot sits on your bot desk)
- [must] bot desk: Plain-English bot idea input, no  (S04 — describe idea in a sentence)
- [must] copy trading: Copy trading with own margin + leverage cap + TP/SL, no  (Excluded from live execution (unsafe); schema supports trades but no copy route built)
- [must] trading: Leverage 1x–1000x, no  (Excluded from live (unsafe); schema leverage_cap default 1.0)
- [must] AI coach: AI coach: direction/entry/stop/target, partial  (grok_extractor.py produces hypothesis; ai_setups schema + confirm route ready)
- [must] AI desk: RISK veto on every setup, partial  (approval_gate.py wraps DynamicRiskManager; manual_approved gate)
- [must] bot desk: Backtest check before live, partial  (paper_evaluator.py evaluates edge before live; no clone backtest screen yet)
- [must] execution: Confirm-before-place (human-in-the-loop), partial  (order_manager.py manual_approved + approval_gate before live_adapter.place_order)
- [should] social: Leaderboard 24H/7D/30D, no  (schema leaderboard_entries + route GET /api/v1/leaderboard ready)
- [should] social: Trader profile + positions, no  (route GET /api/v1/traders/{id} ready)
- [should] trading: Cross margin + liquidation price shown before open, no  (Not built)
- [should] execution: Practice money or real cash mode, partial  (project default is paper mode; live requires fail-closed gate)
