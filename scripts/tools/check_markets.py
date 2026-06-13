import json
from data.polymarket_client import PolymarketClient

client = PolymarketClient()
markets = client.get_markets(50)

print('Current Market Prices:')
print('='*50)
for i, m in enumerate(markets[:15]):
    try:
        prices = json.loads(m.get('outcomePrices', '[]'))
        if prices:
            price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            print(f'{i+1}. ${price:.2f} | Vol: ${volume/1000:.0f}K')
    except:
        pass

print('='*50)
print('Markets with price 0.01-0.35 and volume >15K:')
low_price_count = 0
for m in markets:
    try:
        prices = json.loads(m.get('outcomePrices', '[]'))
        if prices:
            price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            if price >= 0.01 and price <= 0.35 and volume > 15000:
                low_price_count += 1
    except:
        pass
print(f'Found: {low_price_count} markets')