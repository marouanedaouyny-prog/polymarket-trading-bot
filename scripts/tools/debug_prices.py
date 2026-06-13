import json
from data.polymarket_client import PolymarketClient

client = PolymarketClient()
markets = client.get_markets(30)

print("Sample market prices:")
prices_list = []
for m in markets:
    try:
        prices = json.loads(m.get('outcomePrices', '[]'))
        if prices and len(prices) >= 1:
            yes_price = float(prices[0])
            volume = float(m.get('volume', 0) or 0)
            prices_list.append((yes_price, volume, m.get('question', 'N/A')[:40]))
    except:
        pass

prices_list.sort()
print(f"\nPrice distribution (sorted):")
for p, v, q in prices_list[:20]:
    print(f"  ${p:.2f} | Vol: ${v/1000:.0f}K | {q}")
print(f"\nTotal markets: {len(prices_list)}")
print(f"Min price: {min(p for p, v, q in prices_list):.2f}")
print(f"Max price: {max(p for p, v, q in prices_list):.2f}")