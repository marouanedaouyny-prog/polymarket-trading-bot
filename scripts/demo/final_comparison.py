import json

with open('data/tests/all_test_results.json', 'r') as f:
    old = json.load(f)

with open('data/tests/strategies_v2.json', 'r') as f:
    new = json.load(f)

print("=== ALL STRATEGIES RANKED ===\n")
all_results = old + new
sorted_results = sorted(all_results, key=lambda x: x['final_balance'], reverse=True)

for i, r in enumerate(sorted_results[:15], 1):
    print(f"{i:2}. {r['config_name']:20} | Trades: {r['total_trades']:3} | Win: {r['win_rate']:.1f}% | Balance: ${r['final_balance']:7.2f} | Return: {r['return_pct']:7.1f}%")

print("\n=== TOP 5 RECOMMENDED ===")
for i, r in enumerate(sorted_results[:5], 1):
    print(f"{i}. {r['config_name']}: ${r['final_balance']:.2f} ({r['return_pct']:.1f}%) - {r['total_trades']} trades, {r['win_rate']:.1f}% win rate")