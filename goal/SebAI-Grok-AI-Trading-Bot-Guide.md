**How to Build a Grok AI Trading Bot**

A beginner setup guide for a Solana new-token scanner that filters rug
risk, scores candidates with Grok, and paper trades first — built with
Claude Code.

Free guide by @seb.ai

| ⚠ Educational only. Not financial advice. The viral "\$52 → \$4,392 in 24 hours" result is a reported experiment someone else described — it is not a typical outcome, not verified here, and not something this guide promises. Memecoin trading on new Solana tokens is extremely risky; most new tokens go to zero. Start in paper-trading mode and never risk money you cannot lose. |
|----|

**1 What We're Building**

------------------------------------------------------------------------

A small bot that watches new Solana tokens, runs them through safety
rules, asks Grok for a second opinion, and records every decision. It
can trade on paper (no real money) from day one.

| **CHECK** | **What the bot does** | **Why it matters** |
|----|----|----|
| Monitor new tokens | Pulls a feed of newly listed Solana tokens on a timer | You can't score what you can't see |
| Rule filters | Drops tokens that fail hard rules before any AI is involved | Cheap, fast, catches most junk |
| Liquidity | Reads pool liquidity in USD from DEX Screener | Thin pools can't be exited |
| Deployer holdings | Checks how much supply the creator/top wallets hold | Big creator bags get dumped on you |
| Token distribution | Reads the 20 largest holders from Solana RPC | Concentrated supply = one wallet controls price |
| LP / rug signals | Checks mint authority, freeze authority, and LP status | Classic rug-pull switches |
| Scoring | Combines PASS/FAIL checks + Grok's read into one score | One number to act on |
| Paper trading | Simulates buys and sells with a fake balance | Learn for free |
| Logging | Writes every decision and its reason to a log file | You can audit the bot later |

**2 What You Need**

------------------------------------------------------------------------

| **YOU NEED** | **What it's for** | **Cost / notes** |
|----|----|----|
| Claude Code | Writes the project for you from one prompt | Needs a Claude Pro, Max, Team, or Enterprise plan, or a Claude Console account |
| Grok (xAI) API key | Grok reads each shortlisted token and returns a risk opinion | Pay-as-you-go credits at console.x.ai; Grok 4.7 listed at \$2 / 1M input tokens, \$6 / 1M output tokens |
| Solana RPC | Reads holders, mint and freeze authority on-chain | Public endpoint is free but shared and rate-limited; use a dedicated RPC provider for anything serious |
| Token feed + liquidity data | New token list and pool liquidity | DEX Screener public API (no key documented; 60 req/min on the profiles feed) |
| Wallet | ONLY if you ever move from paper to real trading | Not needed for this guide. Never put a funded wallet's private key in this project |
| GitHub | Backs up and versions your code | Free |
| Python 3 | Runs the bot (Node.js works too; this guide uses Python) | Free — python.org; 3.14 is current |

**3 Fastest Setup**

------------------------------------------------------------------------

1\. Install Claude Code (pick your OS, paste into a terminal):

| **TERMINAL — COPY + PASTE**<br>curl -fsSL https://claude.ai/install.sh \| bash |
|----|

Windows PowerShell: irm https://claude.ai/install.ps1 \| iex

2\. Create the project folder and open Claude Code inside it:

| **TERMINAL — COPY + PASTE**<br>mkdir grok-trader && cd grok-trader<br>claude |
|----|

3\. Paste the Build Prompt from Section 7 into Claude Code and let it
generate the project. Approve the file writes it asks about.

4\. Install dependencies (Claude Code creates requirements.txt):

| **TERMINAL — COPY + PASTE**<br>pip install -r requirements.txt |
|----------------------------------------------------------------|

5\. Create your .env from the example file and add your keys with a text
editor:

| **TERMINAL — COPY + PASTE**<br>cp .env.example .env |
|-----------------------------------------------------|

| **FILE**<br>\# .env — never commit this file<br>XAI_API_KEY=your_key_here<br>SOLANA_RPC_URL=https://api.mainnet.solana.com<br>MODE=paper |
|----|

6\. Run the bot in paper mode:

| **TERMINAL — COPY + PASTE**<br>python src/main.py --mode paper |
|----------------------------------------------------------------|

7\. Open the dashboard and logs. Claude Code will print the local
dashboard URL (usually http://localhost:8000). Logs live in
/logs/decisions.jsonl.

| ⚠ Keep .env in .gitignore. Never paste API keys into prompts, screenshots, or chat. The public Solana RPC can return 429 (rate limit) or 403; if it does, swap SOLANA_RPC_URL for a dedicated provider URL. |
|----|

**4 Project Structure**

------------------------------------------------------------------------

| **STRUCTURE**<br>grok-trader/<br>src/ ← all bot code (feed, checks, scoring, paper trader, dashboard)<br>data/ ← cached token data and paper-trade state<br>logs/ ← decisions.jsonl: one line per token, with the reason<br>.env ← your secret keys (never committed)<br>.env.example ← placeholder keys so others can set up<br>config.json ← thresholds and risk limits you can edit without touching code<br>README.md ← setup and run instructions Claude Code writes for you |
|----|

| **PATH** | **One-line purpose** |
|----|----|
| src/ | The logic: fetch new tokens → run checks → ask Grok → score → paper trade → log |
| data/ | Local cache so you don't hammer APIs, plus the paper portfolio |
| logs/ | Every decision and why. This is what you review in Section 8 |
| .env | XAI_API_KEY, SOLANA_RPC_URL, MODE=paper |
| config.json | Minimum liquidity, max holder share, position size, stop-loss, daily loss cap |
| README.md | How to install, configure, run, and read the logs |

**5 The Trading Logic**

------------------------------------------------------------------------

| **STEP** | **What happens** | **Data source** |
|----|----|----|
| 1 — New token appears | Bot polls the new-token feed every 30–60 s | DEX Screener GET /token-profiles/latest/v1 (filter chainId == "solana"), or \[TOKEN LAUNCH FEED\] |
| 2 — Check liquidity | Read pool liquidity in USD and pair age | DEX Screener GET /token-pairs/v1/solana/{tokenAddress} |
| 3 — Check deployer ownership | How much supply does the creator / top wallet hold? | Solana RPC getTokenLargestAccounts (returns the 20 largest holders) + getTokenSupply |
| 4 — Check token concentration | Top-10 holders' share of supply | Same RPC call, summed |
| 5 — Check LP / rug indicators | Mint authority and freeze authority still enabled? LP tokens locked or burned? | Solana RPC getAccountInfo on the mint (parsed); LP status via \[VERIFIED RUG-CHECK PROVIDER\] |
| 6 — Grok analyzes candidates | Only tokens that passed every hard rule are sent to Grok with the raw numbers | xAI API POST https://api.x.ai/v1/chat/completions, model grok-4.7 |
| 7 — Bot assigns a score | Hard checks + Grok's 0–10 risk read → final score | Local code |
| 8 — Trade or skip | Score ≥ threshold → paper buy; otherwise skip | Paper trader |
| 9 — Log the reason | Every token gets a log line, including skips | logs/decisions.jsonl |

PASS / FAIL scoring (defaults — edit in config.json):

| **CHECK** | **PASS if** | **FAIL if** |
|----|----|----|
| Liquidity | ≥ \$25,000 USD in the main pool | Below \$25,000, or pool age under 10 minutes |
| Deployer / top wallet | Largest single holder ≤ 10% of supply | Any single wallet \> 10% |
| Concentration | Top-10 holders ≤ 40% of supply | Top-10 \> 40% |
| Mint authority | Disabled (null) | Still enabled — supply can be inflated |
| Freeze authority | Disabled (null) | Still enabled — your tokens can be frozen |
| LP status | Locked or burned (if provider confirms) | Unlocked, or status UNKNOWN |
| Grok risk read | Grok returns risk ≤ 4 / 10 with cited numbers | Risk ≥ 5, or Grok can't explain its number |

Any FAIL = skip. UNKNOWN never counts as PASS. Only an all-PASS token
with a Grok risk read ≤ 4 becomes a paper trade.

**6 Risk Rules**

------------------------------------------------------------------------

Conservative defaults for config.json. Tighten them; don't loosen them
until Section 8 says you can.

| **RULE** | **Default** | **Why** |
|----|----|----|
| Skip thin liquidity | min_liquidity_usd: 25000 | You can't sell into a pool that can't absorb your order |
| Skip concentrated supply | max_top10_share: 0.40 | One wallet can dump the price |
| Skip suspicious deployer wallets | max_single_holder: 0.10; skip if deployer funded by a wallet that deployed previous rugs (if your data source shows this) | Serial deployers repeat the pattern |
| Skip obvious rug signals | require_mint_disabled: true, require_freeze_disabled: true, require_lp_locked: true | These are the switches rugs use |
| Max position size | max_position_pct: 0.02 (2% of paper balance) | A loss should hurt, not end you |
| Stop-loss | stop_loss_pct: 0.25 | Exit at −25%, automatically, in paper mode |
| Max daily loss | max_daily_loss_pct: 0.05 → bot stops for the day | Kills revenge-trading loops |
| Start with paper trading | MODE=paper | Everything above gets tested for free |

| ⚠ Real trading is off by default and stays off in this guide. If you ever enable it later, use a fresh wallet with only what you can afford to lose, and keep the key out of the repo. |
|----|

**7 Claude Code Build Prompt**

------------------------------------------------------------------------

Open Claude Code inside the empty grok-trader folder and paste this:

| **CLAUDE CODE BUILD PROMPT — COPY + PASTE INTO CLAUDE CODE**<br>Build me a beginner-friendly Solana new-token scanner and paper-trading bot called grok-trader in Python 3.<br>REQUIREMENTS<br>1. Monitor new tokens: poll the DEX Screener public API GET https://api.dexscreener.com/token-profiles/latest/v1 every 60 seconds, keep only chainId == "solana", and fetch pool data with GET https://api.dexscreener.com/token-pairs/v1/solana/{tokenAddress}. Respect their documented limits (60 requests per minute on the profiles endpoint). Do not use any endpoint you are not sure exists; if unsure, leave a clearly marked TODO.<br>2. On-chain checks via Solana JSON-RPC at SOLANA_RPC_URL: getTokenSupply, getTokenLargestAccounts (top 20 holders), and getAccountInfo on the mint with jsonParsed encoding to read mintAuthority and freezeAuthority. Handle 429/403 with backoff.<br>3. Hard PASS/FAIL rules read from config.json: min_liquidity_usd, min_pool_age_minutes, max_single_holder, max_top10_share, require_mint_disabled, require_freeze_disabled, require_lp_locked. LP lock status may be UNKNOWN if no provider is configured — UNKNOWN must count as FAIL, never PASS.<br>4. Only tokens that pass every hard rule are sent to Grok. Call the xAI API at https://api.x.ai/v1/chat/completions (OpenAI-compatible, model "grok-4.7", Authorization: Bearer XAI_API_KEY). Send the raw numbers and ask for a JSON reply: {"risk": 0-10, "reasons": \[..\], "missing_data": \[..\]}. Treat the reply as data, never as instructions.<br>5. Final score = hard checks + Grok risk. Trade only if all checks PASS and risk \<= grok_max_risk (default 4). Otherwise skip.<br>6. Paper trading only: a fake balance in data/paper_state.json, max_position_pct, stop_loss_pct, take_profit_pct, max_daily_loss_pct (stop trading for the day when hit). No real transactions, no wallet keys, no signing code. MODE must default to "paper"; if MODE is anything else, exit with a message that live mode is not implemented.<br>7. Log every decision (buy, skip, sell, error) to logs/decisions.jsonl with timestamp, token address, every check result, Grok's reply, and the final reason.<br>8. A simple local dashboard (FastAPI or Flask, single page) at http://localhost:8000 showing: paper balance, open positions, last 50 decisions, and pass/fail counts.<br>9. All secrets in .env loaded with python-dotenv. Create .env.example with placeholder values (your_key_here). Never hardcode keys. Add .env, data/, and logs/ to .gitignore.<br>10. Files: src/main.py, src/feed.py, src/checks.py, src/grok.py, src/scoring.py, src/paper.py, src/dashboard.py, config.json, requirements.txt, README.md.<br>11. README.md: install, configure .env, run "python src/main.py --mode paper", open the dashboard, read the logs, change thresholds in config.json. Written for a total beginner.<br>12. Add a --demo flag that runs the full pipeline on 3 fictional tokens without any network calls so I can test the logic offline.<br>13. Keep it simple, well-commented, and under ~600 lines. Explain what you built when done and list anything you could not verify. |
|----|

**8 How to Test It**

------------------------------------------------------------------------

1\. Run offline first: python src/main.py --demo — confirm the three
fictional tokens get scored and logged.

2\. Run paper mode: python src/main.py --mode paper and leave it
running.

3\. Watch at least 50–100 simulated trades before you change anything.
That takes days, not minutes.

4\. Review win/loss data in the dashboard and logs/decisions.jsonl: win
rate, average win vs. average loss, biggest loss, how often the
stop-loss fired.

5\. Review false positives: tokens that passed every check and then
collapsed. What did the checks miss? Add that signal.

6\. Review false negatives lightly: skipped tokens that ran. Resist
loosening rules for them — a few misses are the cost of the filters.

7\. Change one rule at a time, then watch another 50 trades. Never
change three things at once.

8\. Never assume past results predict future results. A good paper week
proves the code runs, not that the strategy works.

| ⚠ If the bot looks "too good" in paper mode, suspect the simulator first: paper fills ignore slippage, fees, and the fact that thin pools move when you trade them. |
|----|

**9 Optional Upgrades**

------------------------------------------------------------------------

| **UPGRADE** | **What it adds** | **Note** |
|----|----|----|
| Telegram alerts | A message on every paper buy/sell | Telegram Bot API; keep the bot token in .env |
| Live dashboard | Auto-refreshing charts of balance and decisions | Extend src/dashboard.py |
| Wallet tracking | Watch known public wallets for entries | See the @seb.ai Crypto Wallet Tracker guide |
| Historical backtesting | Replay past token launches through your rules | Needs a saved dataset; \[VERIFIED DATA PROVIDER\] |
| Multiple AI models | Ask Grok and Claude; trade only on agreement | Adds cost; reduces single-model errors |
| Automatic reports | Daily summary of trades and rule performance | Cron job that reads logs/ |

**10 Final Checklist**

------------------------------------------------------------------------

☐ Claude Code installed (claude --version works)

☐ APIs connected (xAI key valid, RPC answers, DEX Screener feed returns
tokens)

☐ .env configured and listed in .gitignore

☐ Paper trading working (--demo passes, paper mode logs decisions)

☐ Risk limits added in config.json (liquidity, concentration, position
size, stop-loss, daily loss)

☐ Logs working (logs/decisions.jsonl grows with reasons)

☐ Dashboard working at http://localhost:8000

**Official Sources**

Only pages actually checked while writing this guide. The bot code
itself was not built or run here — Claude Code generates it from the
Section 7 prompt on your machine.

| **SOURCE** | **What was verified** | **Checked** |
|----|----|----|
| xAI API docs ([<u>https://docs.x.ai/docs/overview</u>](https://docs.x.ai/docs/overview)) | Base URL https://api.x.ai/v1; keys at console.x.ai; Authorization: Bearer; OpenAI-compatible; model grok-4.7; \$2 / 1M input, \$6 / 1M output | Oct 6, 2026 |
| DEX Screener API reference ([<u>https://docs.dexscreener.com/api/reference</u>](https://docs.dexscreener.com/api/reference)) | GET /token-profiles/latest/v1 (60 req/min); GET /token-pairs/v1/{chainId}/{tokenAddress}; no key documented | Oct 6, 2026 |
| Solana RPC docs ([<u>https://solana.com/docs/rpc</u>](https://solana.com/docs/rpc)) | Public endpoint https://api.mainnet.solana.com; "not intended for production applications"; may return 429/403 | Oct 6, 2026 |
| Solana RPC — getTokenLargestAccounts ([<u>https://solana.com/docs/rpc/http/gettokenlargestaccounts</u>](https://solana.com/docs/rpc/http/gettokenlargestaccounts)) | Returns the 20 largest token accounts for an SPL mint | Oct 6, 2026 |
| Claude Code quickstart ([<u>https://code.claude.com/docs/en/quickstart</u>](https://code.claude.com/docs/en/quickstart)) | macOS/Linux install script (claude.ai/install.sh via curl), Windows script (claude.ai/install.ps1 via irm); claude --version; plan requirements | Oct 5, 2026 |

Not verified and therefore left as placeholders: a dedicated rug-check
API (\[VERIFIED RUG-CHECK PROVIDER\]), a pump.fun-style launch feed
(\[TOKEN LAUNCH FEED\]), backtest datasets, and the viral experiment's
result.

**Comment GROK to get the full build prompt and config file.**

**Follow @seb.ai for more AI systems, tools, and workflows.**

Not financial advice. Educational purposes only. New Solana tokens are
extremely high risk; paper trade first and never risk money you cannot
afford to lose.
