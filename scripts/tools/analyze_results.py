import json

with open('data/tests/all_test_results.json', 'r') as f:
    results = json.load(f)

print('=== STRATEGY COMPARISON ===\n')
for r in sorted(results, key=lambda x: x['final_balance'], reverse=True):
    print(f"{r['config_name']:20} | Trades: {r['total_trades']:3} | Win: {r['win_rate']:.1f}% | Balance: ${r['final_balance']:.2f} | Return: {r['return_pct']:.1f}%")

print('\n=== TOP 3 ===')
top = sorted(results, key=lambda x: x['final_balance'], reverse=True)[:3]
for i, t in enumerate(top, 1):
    print(f"{i}. {t['config_name']}: ${t['final_balance']:.2f} ({t['return_pct']:.1f}%)")