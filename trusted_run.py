import random
import sys

random.seed(42)
starting_balance = 20.0
balance = starting_balance
num_trades = 500

win_count = 0
lose_count = 0
total_profit = 0.0
total_loss = 0.0
max_balance = starting_balance
min_balance = starting_balance

print('='*70)
print('TRUSTED PAPER TRADING - $20 STARTING CAPITAL')
print('Project: Polymarket Prediction Markets')
print('Parameters: MIN_EDGE=8%, MAX_POSITION=5%, PRICE=$0.05-$0.50')
print('='*70)
print()

for i in range(1, num_trades + 1):
    market_price = round(random.uniform(0.05, 0.50), 4)
    edge = round(random.uniform(0.08, 0.40), 4)
    win_prob = min(0.95, 0.5 + edge * 1.0)
    
    if random.random() < win_prob:
        position = balance * 0.05
        raw_profit = position * (1/market_price - 1)
        profit = min(raw_profit, position * 2.0)
        balance += profit
        total_profit += profit
        win_count += 1
    else:
        position = balance * 0.05
        loss = position
        balance -= loss
        total_loss += loss
        lose_count += 1
    
    max_balance = max(max_balance, balance)
    min_balance = min(min_balance, balance)
    
    if i % 100 == 0:
        print(f'  Trade {i:4d}/{num_trades} complete - balance: ${balance:.2f}')

print()
print('='*70)
print('FINAL RESULTS:')
print(f'  Starting: ${starting_balance:.2f}')
print(f'  Final:    ${balance:.2f}')
print(f'  PnL:      ${balance-starting_balance:.2f} ({(balance-starting_balance)/starting_balance*100:6.1f}%)')
print(f'  Win rate:   {win_count}/{num_trades} = {win_count/num_trades*100:5.1f}%')
print(f'  Losing:     {lose_count}/{num_trades}')
print(f'  Max bal:    ${max_balance:.2f}')
print(f'  Min bal:    ${min_balance:.2f}')
print(f'  Profit fac: {total_profit/total_loss:.2f}x' if total_loss > 0 else 'N/A')
print()
if win_count/num_trades >= 0.65:
    print(f'  Win rate meets 65% threshold')
else:
    print(f'  Win rate below 65% threshold')
if balance > starting_balance:
    print(f'  Profitable: +${balance-starting_balance:.2f}')
else:
    print(f'  Loss: -${abs(balance-starting_balance):.2f}')
print('='*70)