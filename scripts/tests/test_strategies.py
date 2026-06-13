import random
import json
import csv

random.seed(42)

STRATEGIES = [
    {"name": "ML_Hybrid", "max_pos": 0.20, "stop_loss": 0.04, "min_edge": 0.03, "min_conf": 55, "take_mult": 2.5},
    {"name": "Momentum_Bias", "max_pos": 0.18, "stop_loss": 0.06, "min_edge": 0.04, "min_conf": 50, "take_mult": 2.2},
    {"name": "Low_Risk_High_Freq", "max_pos": 0.12, "stop_loss": 0.03, "min_edge": 0.02, "min_conf": 45, "take_mult": 1.8},
    {"name": "Mean_Reversion", "max_pos": 0.15, "stop_loss": 0.05, "min_edge": 0.06, "min_conf": 65, "take_mult": 2.0},
    {"name": "Volatility_Adjusted", "max_pos": 0.17, "stop_loss": 0.07, "min_edge": 0.05, "min_conf": 60, "take_mult": 2.3},
]

FEE = 0.07

def simulate_trade(strategy, markets):
    if not markets:
        return None

    for _ in range(5):
        m = random.choice(markets)
        price = m['yes_price']
        edge = abs(price - 0.5) + random.uniform(0, 0.1)
        confidence = int(edge * 100) + random.randint(0, 20)

        if edge >= strategy['min_edge'] and confidence >= strategy['min_conf']:
            pos_size = random.uniform(0.05, strategy['max_pos'])
            won = random.random() < (0.5 + edge * 0.5)
            payout = pos_size * (1/price - FEE) if won else -pos_size
            return {'payout': payout, 'won': won, 'price': price, 'edge': edge}

    return None

def run_strategy(strategy_name, config, iterations=500):
    balance = 10.0
    trades = []
    wins = 0

    fake_markets = [{'yes_price': random.uniform(0.2, 0.8)} for _ in range(50)]

    for i in range(iterations):
        result = simulate_trade(config, fake_markets)
        if result:
            balance += result['payout']
            wins += 1 if result['won'] else 0
            trades.append({'iteration': i+1, 'balance': balance, 'won': result['won']})

    return {
        'config_name': strategy_name,
        'total_trades': len(trades),
        'win_rate': (wins / len(trades) * 100) if trades else 0,
        'final_balance': balance,
        'profit': balance - 10.0,
        'return_pct': ((balance - 10.0) / 10.0) * 100,
    }

results = []
for s in STRATEGIES:
    r = run_strategy(s['name'], s)
    results.append(r)
    print(f"{s['name']:20} | Trades: {r['total_trades']:3} | Win: {r['win_rate']:.1f}% | Balance: ${r['final_balance']:.2f}")

with open('data/tests/new_strategies.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nSaved to data/tests/new_strategies.json")