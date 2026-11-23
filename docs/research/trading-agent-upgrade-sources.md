# Trading Agent Upgrade — Primary-Source Research Report

Saved: `C:\Users\hp\Desktop\New folder\polymarket\docs\research\trading-agent-upgrade-sources.md`
Research date: 2026-11-10 (as-of date requested); retrieved 2026-11-11.

**No investment advice, profit guarantees, or trade recommendations are made herein.** All claims are tied to cited sources; secondary/blog material is labeled as such.

---

## 1. Polymarket official API / CLOB documentation

Source: `https://docs.polymarket.com/` (official docs index), `https://docs.polymarket.com/api-reference/rate-limits`, `https://docs.polymarket.com/trading/place-orders`, `https://docs.polymarket.com/market-data/realtime-data`, `https://docs.polymarket.com/concepts/prices-orderbook`, `https://docs.polymarket.us/api-reference/market/overview` (US documentation), official Python client `https://github.com/Polymarket/py-clob-client`.

### Authentication
- CLOB base URL: `https://clob.polymarket.com`.
- Authentication is via API key endpoints, rate-limited separately at **100 req / 10s**.
- Official Python client: `py-clob-client` (Polymarket GitHub).

### Rate limits (IP-based, Cloudflare throttling, sliding windows; exceeded requests are throttled/queued, not immediately rejected)
| Tier | Endpoint(s) | Limit |
|---|---|---|
| General (IP) | — | 15,000 req / 10s |
| CLOB general | — | 9,000 req / 10s |
| Market data | `/book`, `/price`, `/midpoint` | 1,500 req / 10s |
| Market data | `/prices`, `/midpoints` | 500 req / 10s |
| Market data | tick size | 200 req / 10s |
| Ledger | `/trades`, `/orders`, `/notifications`, `/order` | 900 req / 10s |
| Ledger | `/data/orders` | 500 req / 10s |
| Authentication | API key endpoints | 100 req / 10s |
| Trading | `POST /order` burst | 5,000 req / 10s |
| Trading | `POST /order` sustained | 120,000 req / 10 min |

### Order types / trading
Covered in `docs.polymarket.com/trading/place-orders` (CLOB order placement; per-signer token-bucket limits apply to order/cancel requests separate from IP limits). Market data and prices/orderbook concepts documented under `/market-data` and `/concepts/prices-orderbook`.

### Fees, geoblocking, terms, market resolution, risk
- Not fully retrievable in this session: direct scraping of `docs.polymarket.com` pages was blocked by the session's permission classifier, and the Polymarket API search returned rate-limit content only. The US documentation mirror is at `docs.polymarket.us`.
- **Verification needed**: confirm fee schedule, US/non-US geoblocking, terms of service, market resolution rules, and risk disclosures directly on `docs.polymarket.com` and `docs.polymarket.us` before implementation.

---

## 2. xAI / Grok API — structured signal extraction from X/web content

Source: `https://docs.x.ai` (official Grok API docs, retrieved 2026-11-10).

### Base URL & authentication
- Base URL: `https://api.x.ai/v1`.
- Auth: Bearer token, `XAI_API_KEY` (create at `https://console.x.ai/team/default/api-keys`).
- Official SDKs: JavaScript (`@ai-sdk/xai`), Python (OpenAI-compatible client + `xai_sdk`), cURL.

### Models & pricing (relevant flagship)
- `grok-4.7`: flagship for code and agentic tool calling, configurable reasoning effort, 500k-token context, input $2.00/1M tokens, output $6.00/1M tokens.
- Voice API (STS/TTS/STT) and Imagine API (image/video) also available.

### Capabilities relevant to extracting structured signals from X/web content
- **Responses API**: agentic coding/tool use, powers Grok Build.
- **Function calling** (`docs.x.ai/developers/tools/function-calling`).
- **Web search** (`docs.x.ai/developers/tools/web-search`).
- **Structured outputs** (`docs.x.ai/developers/model-capabilities/text/structured-outputs`).
- **Batch API** (`docs.x.ai/developers/advanced-api-usage/batch-api`).
- Quickstart, models, pricing, REST API reference, release notes all documented.

### Limitations / security (from docs)
- Structured outputs and web search are tool capabilities; no specific accuracy or rate-limit figures for web search/function-calling were exposed on the homepage. Pricing shown only for grok-4.7 text (input/output) and voice/imagine.
- **Verification needed**: confirm web-search result freshness, structured-output schema enforcement, function-calling rate limits, and any content policy restricting automated extraction of X/web content, on `docs.x.ai/developers/...` before implementation.

---

## 3. Vembit bots/desk — bot configuration & monitoring workflow

Source: `https://vembit.com/bots/desk` (public first-party page; resolved to landing `https://vembit.com/`). Clean-room only — no source, JS bundles, private APIs, or network calls inspected.

### Platform scope (first-party)
- Social trading web app: crypto, forex, commodities, indices; 38 markets (18 crypto, 10 forex, 7 commodities, 3 indices); leverage 1x–1000x; cross margin; take-profit/stop-loss; liquidation price shown before opening.
- Copy trading: leaderboard (24H/7D/30D), copy with own margin + leverage cap + optional TP/SL; copy closes when leader closes.

### Vembit AI desk — bot configuration/monitoring workflow (first-party claims)
- "Build a bot in plain English": describe the idea in a sentence, check its backtest, then start it live. Every bot sits on your bot desk.
- AI desk: eight agents acting as one team; **RISK can always say no** to every setup.
  - CRAWLER — reads headlines
  - SOCIAL — reads news mood
  - SCAN — finds setups
  - VET — AI yes/no per setup
  - SIZE — sizes every ticket
  - RISK — can always say no
  - FILLS — places orders
  - CHIEF — writes the call
- Vembit AI (chart coach): reads live chart, answers with direction, entry, stop, target; **nothing is placed until you confirm** — it is an analysis tool, not an execution promise.
- Run with practice money or real cash.
- Terms of Service and Privacy Policy linked (`vembit.com/terms`, `vembit.com/privacy-policy`); risk disclosure for leveraged trading present.

### Caveats
- These are marketing/landing-page claims, not a technical bot API spec or monitoring workflow document. No endpoints, webhook schema, config file format, or monitoring dashboard details were exposed on the public page.
- **Verification needed**: obtain bot configuration schema, backtest API, live-start controls, and monitoring/alerting interface from Vembit's developer/docs channel (if any) before integrating.

---

## 4. Safe paper-to-live validation — algorithmic / prediction-market trading

Sources located (mixed; not all primary to Polymarket):
- Alpaca (official broker docs): "Paper trading that mirrors live execution. The same alpaca-py interface, the same order types, and the same account/position objects. These route to a simulated environment... develop against the real API surface from day one instead of writing a mock layer." Alpaca Paper Trading: `https://docs.alpaca.markets/docs/paper-trading`.
- Alpaca multi-market workflow (blog, secondary): paper US equities → Binance testnet crypto, with same-interface principle.
- QuantInsti (practitioner tips, secondary): "paper trade before trading live"; backtest then paper trade before live execution.
- TradersPost (blog, secondary): "Paper Trading Strategy Development Guide — Best Practices for Strategy Development."
- Marsbridge (case study, secondary): model audit → cloud-deployed paper trading; end-to-end order validation in safe environment; hardening & runbooks.

### No Polymarket-specific primary paper-to-live guidance found
- The Polymarket docs retrieved (rate limits, place-orders, market data) do not document a paper/simulated trading environment or a paper-to-live promotion workflow.
- **Verification needed**: check `docs.polymarket.com` and `docs.polymarket.us` for a sandbox/testnet CLOB, paper-account flow, or simulation mode before assuming one exists.

---

## Top findings (summary)

1. **Polymarket**: official CLOB docs at `docs.polymarket.com`; IP-based Cloudflare rate limits with per-signer token buckets for orders; API-key auth at 100 req/10s; official `py-clob-client` Python client; US mirror at `docs.polymarket.us`. Fees/geoblocking/terms/resolution not yet confirmed (scraping blocked in-session).
2. **Grok API**: `https://api.x.ai/v1`, Bearer `XAI_API_KEY`; `grok-4.7` (500k ctx, $2 in / $6 out per 1M tokens, configurable reasoning); function calling, web search, structured outputs, batch API all documented. Web-search freshness/limits and content-policy constraints need confirmation.
3. **Vembit**: first-party landing page describes plain-English bot building ("check backtest, then start it live"), an eight-agent AI desk where RISK can veto, and confirm-before-place AI coaching. No technical bot-API spec publicly exposed.
4. **Paper-to-live**: Alpaca's same-interface paper-to-live principle is the clearest primary platform guidance; no Polymarket-specific paper/sandbox environment documented yet.

**Recommended next step**: retrieve the missing Polymarket items (fees, geoblocking, terms, market resolution, risk, sandbox/paper trading) from `docs.polymarket.com` and `docs.polymarket.us`, and confirm Grok web-search/structured-output limits, before writing any integration code.
