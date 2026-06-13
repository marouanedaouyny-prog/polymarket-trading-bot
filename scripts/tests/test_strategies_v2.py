import random
import json

random.seed(123)

STRATEGIES = [
    {"name": "Best_HF_Tuned", "max_pos": 0.20, "stop_loss": 0.05, "min_edge": 0.03, "min_conf": 50, "take_mult": 2.0},
    {"name": "Aggressive_Mix", "max_pos": 0.25, "stop_loss": 0.04, "min_edge": 0.02, "min_conf": 45, "take_mult": 2.5},
    {"name": "Large_Mix", "max_pos": 0.30, "stop_loss": 0.06, "min_edge": 0.04, "min_conf": 55, "take_mult": 2.2},
    {"name": "Safe_HF", "max_pos": 0.15, "stop_loss": 0.03, "min_edge": 0.02, "min_conf": 40, "take_mult": 1.9},
    {"name": "Smart_Entry", "max_pos": 0.18, "stop_loss": 0.05, "min_edge": 0.05, "min_conf": 60, "take_mult": 2.1},
]

FEE = 0.07

def simulate_trade(strategy, markets):
    if not markets:
        return None

    for _ in range(10):
        m = random.choice(markets)
        price = m['yes_price']
        edge = abs(price - 0.5) + random.uniform(0, 0.15)
        confidence = int(edge * 100) + random.randint(0, 25)

        if edge >= strategy['min_edge'] and confidence >= strategy['min_conf']:
            pos_size = random.uniform(0.05, strategy['max_pos'])
            base_prob = 0.5 + edge * 0.6
            won = random.random() < min(base_prob, 0.85)
            payout = pos_size * (1/price - FEE) if won else -pos_size
            return {'payout': payout, 'won': won, 'price': price, 'edge': edge}
    return None

def run_strategy(name, cfg, iterations=500):
    balance = 10.0
    wins = 0
    trades = 0
    fake_markets = [{'yes_price': random.uniform(0.15, 0.85)} for _ in range(60)]

    for _ in range(iterations):
        result = simulate_trade(cfg, fake_markets)
        if result:
            balance += result['payout']
            wins += 1 if result['won'] else 0
            trades += 1

    return {
        'config_name': name,
        'total_trades': trades,
        'win_rate': (wins / trades * 100) if trades else 0,
        'final_balance': balance,
        'profit': balance - 10.0,
        'return_pct': ((balance - 10.0) / 10.0) * 100,
    }

results = []
for s in STRATEGIES:
    r = run_strategy(s['name'], s)
    results.append(r)
    print(f"{s['name']:20} | Trades: {r['total_trades']:3} | Win: {r['win_rate']:.1f}% | Balance: ${r['final_balance']:.2f} | Return: {r['return_pct']:.1f}%")

with open('data/tests/strategies_v2.json', 'w') as f:
    json.dump(results, f, indent=2)