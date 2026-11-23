import random

# More realistic polymarket simulation
# When you buy YES at price 0.65, you typically risk $0.65 to gain $0.35
# PnL = +0.35 if win, -0.65 if lose (per $1 stake)
# Or per share: price is the cost per share, and you get $1 per share if win

random.seed(42)

starting_balance = 100.0
balance = starting_balance
win_count = 0
lose_count = 0
total_profit = 0.0
total_loss = 0.0

trade_details = []

for i in range(100):
    # Price between 0.01 and 0.35 (project criteria)
    price = round(random.uniform(0.01, 0.35), 4)
    
    # Edge > 65% determines win probability
    edge = round(random.uniform(0.65, 0.90), 3)
    
    # Win probability: if edge = 0.65, ~65% win rate; if edge = 0.90, ~90% win rate
    win_prob = min(0.95, max(0.65, edge))  # Clamp 65-95%
    
    # Position: risk 15% of balance per trade
    risk_pct = 0.15
    stake = balance * risk_pct  # Amount at risk
    
    # Per-$1-staked PnL: win = (1-price), lose = -price
    # For $stake stake: win_profit = stake * (1-price), loss = stake * price
    
    if random.random() < win_prob:
        # WIN: profit = stake * (1 - price)
        profit = stake * (1 - price)
        total_profit += profit
        win_count += 1
        balance += profit
        trade_details.append(f'Trade {i+1}: price={price}, edge={edge}, WIN, profit={profit:.2f}, balance={balance:.2f}')
    else:
        # LOSS: lose stake * price (you lose the cost basis)
        loss = stake * price
        total_loss += loss
        lose_count += 1
        balance -= loss
        trade_details.append(f'Trade {i+1}: price={price}, edge={edge}, LOSS, loss={loss:.2f}, balance={balance:.2f}')

win_rate = win_count / 100
profit_factor = total_profit / total_loss if total_loss > 0 else 0

print(f'Starting balance: {starting_balance}')
print(f'Final balance: {balance:.4f}')
print(f'Total profit: {total_profit:.4f}')
print(f'Total loss: {total_loss:.4f}')
print(f'Win rate: {win_rate*100:.1f}%')
print(f'Profit factor: {profit_factor:.2f}')
print(f'Total trades: 100')
print()
print('Project strategy parameters:')
print(f'  - Price range: $0.01-$0.35')
print(f'  - Max position: 15% of balance per trade')
print(f'  - Edge > 65% (win prob 65-95%)')
print()
print('Results:')
print(f'  {win_rate*100:.1f}% win rate')
print(f'  Profit factor: {profit_factor:.2f}x')
print(f'  Total PnL: ${balance - starting_balance:.2f}')
print()
if win_rate >= 75 and profit_factor > 2:
    print('✓ Strategy is PROFITABLE')
elif win_rate >= 65:
    print('✓ Strategy is BREAK-EVEN to MODERATELY PROFITABLE')
else:
    print('✗ Strategy needs improvement')