import csv
with open('data/results/demo_1000_trades.csv') as f:
    r = csv.DictReader(f)
    trades = list(r)
print('Sample trades (first 10):')
for t in trades[:10]:
    print(f"  #{t['iteration']} price={t['price']} edge={t['edge']} conf={t['confidence']} won={t['won']} payout={t['payout']}")

print('\n... last 5 trades:')
for t in trades[-5:]:
    print(f"  #{t['iteration']} price={t['price']} edge={t['edge']} conf={t['confidence']} won={t['won']} payout={t['payout']}")