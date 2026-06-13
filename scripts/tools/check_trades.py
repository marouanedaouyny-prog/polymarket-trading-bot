import csv

with open('data/results/training_trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    trades = list(reader)

print(f'Total trades in CSV: {len(trades)}')
wins = sum(1 for t in trades if t['won'] == 'True')
print(f'Wins: {wins}')
print(f'Losses: {len(trades) - wins}')
print(f'\nSample trades:')
for t in trades[:5]:
    print(f"  {t['timestamp'][:19]} price={t['price']} edge={t['edge']} won={t['won']} payout={t['payout']}")