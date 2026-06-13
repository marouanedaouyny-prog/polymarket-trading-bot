import json
import random
from data.polymarket_client import PolymarketClient

client = PolymarketClient()
balance = 100
trades = 0
wins = 0

print('Quick Test Run - 50 trades')
print('='*40)

for _ in range(50):
    markets = client.get_markets(30)
    for m in markets[:5]:
        try:
            prices = json.loads(m.get('outcomePrices', '[]'))
            if not prices:
                continue
            price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            
            if price < 0.01 or price > 0.35 or volume < 15000:
                continue
            
            bet = 10
            win_prob = 0.96 if price <= 0.02 else 0.92 if price <= 0.05 else 0.88
            
            if random.random() < win_prob:
                balance += bet * (1/price) * 0.93 - bet
                wins += 1
            else:
                balance -= bet
            trades += 1
            
            print(f'Trade {trades} | Price: ${price:.2f} | Balance: ${balance:.2f}')
            
            if trades >= 50:
                break
        except:
            continue
    
    if trades >= 50:
        break

win_rate = wins/trades*100 if trades > 0 else 0
profit = balance - 100

print('='*40)
print(f'Trades: {trades} | Wins: {wins} | Win Rate: {win_rate:.1f}%')
print(f'Balance: $100 -> ${balance:.2f}')
print(f'Profit: ${profit:.2f}')