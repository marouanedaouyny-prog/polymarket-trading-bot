from src.data.polymarket_client import PolymarketClient
import json

client = PolymarketClient()
markets = client.get_markets(5)
print(json.dumps(markets, indent=2))
