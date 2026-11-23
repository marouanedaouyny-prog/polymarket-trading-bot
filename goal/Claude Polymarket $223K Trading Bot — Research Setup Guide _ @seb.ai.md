Want to build AI agents, automate business workflows, and learn
practical AI systems? Join Prosper AI for step-by-step tutorials,
prompts, and a community of builders.

[<u>https://www.skool.com/prosper-ai-4540/about</u>](https://www.skool.com/prosper-ai-4540/about)

# EXPLORE BTCC — MY REFERRAL LINK

Interested in exploring a cryptocurrency trading platform? You can visit
BTCC here:

[<u>https://www.btcc.com/en-US/market-events/kol/new-standard?name=FS4O5E</u>](https://www.btcc.com/en-US/market-events/kol/new-standard?name=FS4O5E)

# CLAUDE + POLYMARKET: BUILD A MICROSTRUCTURE RESEARCH DASHBOARD

Free educational setup guide by @seb.ai

Instagram keyword: CLAUDE

# WHAT THIS STORY CLAIMS

A viral post says a Polymarket wallet accumulated over \$223,000 in
trading profits while using a bot allegedly built with Claude. It
describes approximately 113 trades per hour, a median trade size of
\$2.12, and three approaches involving near-certain outcomes, cheap
long-shot outcomes, and apparent arbitrage opportunities.

Public wallet: https://polymarket.com/@0x50f7

The wallet and its public trading history can be examined. But the
precise \$223K figure is a historical snapshot, and the claims that
Claude built the bot, that it traded at the stated rate, and that its
trade sizes and strategies match the post are not independently
confirmed.

This document does not provide the trader's original code, credentials,
or strategy. It teaches an original, paper-only research prototype, not
a guaranteed source of income.

# THE THREE IDEAS — IN SIMPLE WORDS

1\. NEAR-SETTLEMENT OUTCOMES: An outcome listed at 98–99.9 cents may pay
\$1 on resolution, but one wrong settlement or bad fill can wipe out
many tiny gains. Apparent certainty does not mean risk-free profit.

2\. CHEAP TAILS: An outcome priced at 1–5 cents can rise sharply if the
underlying market changes at the last second. Most such bets may still
expire worthless. A low price is not automatically a bargain.

3\. APPARENT ARBITRAGE: An imbalance between related outcome prices
might look profitable, but fees, spreads, timing, fill failures, and
settlement risks can eliminate the advantage.

# WHAT YOU WILL BUILD

A local read-only research dashboard with:

• A market-data collector

• A near-settlement price monitor

• A cheap-tail scenario analyzer

• A pricing-discrepancy detector

• A paper execution simulator

• A risk and results report

The system will never submit a real order, request a private key, or
trade on behalf of the viewer.

# STEP 1 — SET UP THE WORKSPACE

Install Claude Code or use another coding assistant with access to a
local project folder.

Use Python 3.11+ and a local dashboard framework such as Streamlit.

Read the official Polymarket documentation at:

https://docs.polymarket.com/

Use only documented public/read-only data endpoints in line with their
access rules, and begin with fabricated mock market snapshots so the
first prototype works offline.

Do not paste private keys, API secrets, passwords, or wallet seed
phrases into a chat.

# STEP 2 — COPY THE MASTER CLAUDE PROMPT

Act as a software engineer and skeptical market-research assistant. I
want to build an original, educational, PAPER-ONLY Polymarket
market-microstructure dashboard inspired by a viral trading account. Do
not assume that the claimed trader's bot code, Claude usage, wallet P&L,
or strategy parameters have been verified.

FIRST: Propose a file tree, source-data requirements, a minimal
architecture, expected API costs, and a test plan. Wait for approval
before generating code.

After approval, implement:

A. Data collector: import mock snapshots first; optionally connect to
documented public/read-only market feeds. Preserve market IDs,
observation timestamps, source links, best bid/ask (when available), and
settlement rules.

B. Near-settlement monitor: identify outcomes priced near 98–99.9 cents
and calculate illustrative payoff after fees under both winning and
losing resolutions. Never call a position guaranteed or risk-free.

C. Tail scenario analyzer: examine hypothetical 1–5-cent outcomes;
calculate break-even probabilities and full-loss scenarios without
inventing predictive accuracy.

D. Discrepancy detector: display candidate pricing inconsistencies
between mutually exclusive outcomes; model spreads, partial fills, stale
quotes, contract terms and settlement uncertainty. Flag candidates for
research only.

E. Paper execution: simulate trades only after the price became
observable, with fees, execution delays, slippage, liquidity limits, and
missed fills. No real-money order functionality.

F. Risk manager: enforce hypothetical position/exposure limits, track
maximum drawdown and daily losses, and stop simulations on unreliable
data.

G. Dashboard: show market cards, trade candidates, sources, a paper
order ledger, hypothetical equity curve and clear SIMULATED labels.

H. Validation: synthetic examples, reproducible unit tests, an
out-of-sample evaluation window and a benchmark against passive/no-trade
baselines.

Rules:

\- Do not invent wallet fills, profits, trading frequencies or private
strategies.

\- Separate source facts, assumptions and simulator outputs.

\- Do not request a wallet connection or trading credentials.

\- Keep every order simulation-only, with a clearly visible label.

\- Show failed and losing scenarios, not just potential wins.

\- Provide a README explaining startup commands, limitations and how to
verify data.

Begin with the implementation plan only.

# STEP 3 — BUILD THE FIRST VERSION

Once Claude proposes a reasonable architecture, instruct:

“Implement the smallest working version with mock snapshots, unit tests,
and a dashboard. Show me how to run it locally. Do not connect to a
trading account.”

Start with five or ten artificial market snapshots that include both
attractive-looking prices and examples where fees or spreads make a
trade unattractive.

# STEP 4 — UNDERSTAND THE MATH

For a hypothetical outcome costing \$0.99 that pays \$1 on a successful
resolution:

\- Winning gross gain = \$0.01 per share before fees.

\- Losing gross amount at risk = \$0.99 per share.

\- A single loss can offset 99 wins of one cent each before costs.

For a hypothetical \$0.02 outcome:

\- Winning gross gain = \$0.98 per share before fees.

\- A losing outcome loses the \$0.02 stake.

\- An outcome is only a bargain when the true probability and executable
price justify it; the price alone proves nothing.

For any apparent arbitrage, test actual executable bid/ask quotes and
each contract's settlement rules rather than comparing last-traded
prices.

# STEP 5 — TRACK A PAPER PORTFOLIO

Choose a fictional starting balance and record every simulated entry,
fill, missed fill, result and cost.

Include the full range of plausible losses. Report realized and
unrealized hypothetical P&L separately.

Keep the process running in paper mode across multiple market sessions;
no one-night results should be treated as predictive.

# STEP 6 — VERIFY WALLET CLAIMS RESPONSIBLY

Open the public @0x50f7 profile and note its displayed statistics and
the date viewed. If using a third-party tracker, document how it defines
realized P&L, open positions, rewards and rebates.

Do not assert that on-chain transactions prove Claude was used. Wallet
data by itself usually cannot prove which code or model executed the
trades.

Do not present the older \$223K number as necessarily current or as a
result you personally achieved.

# STEP 7 — FILM THE INSTAGRAM DEMO

Opening: “Someone reportedly built a Claude trading bot connected to a
wallet with over \$223K in claimed Polymarket profits.”

Show the public account and attribute the results.

Then show the three research modules: near-settlement prices, cheap
tails and pricing discrepancies.

Reveal your simulator dashboard with the SIMULATED label prominently
visible.

Finish: “Comment CLAUDE and I'll send you the full setup guide.”

# COMMON MISTAKES

• Believing a 99-cent outcome is a certain win

• Confusing historical P&L with guaranteed future returns

• Ignoring order-book liquidity and bid/ask spread

• Treating cheap 1-cent outcomes as automatically underpriced

• Misreading market settlement terms

• Claiming trading frequency proves profitability

• Treating a coding model as a replacement for independent risk testing

# IMPORTANT DISCLOSURE

The \$223,000 profit story and the Claude connection are unverified
claims attributed to the original post. Trading and prediction markets
can lose money, including an entire position. This research guide does
not provide real-money automation or financial advice. Eligibility and
laws vary by location.

# FOLLOW @seb.ai

For more build-it-yourself AI systems, join Prosper AI:

https://www.skool.com/prosper-ai-4540/about
