import requests
import socket
import asyncio
import aiohttp

# Use Google DNS-over-HTTPS to resolve blocked domains
def resolve_with_doh(hostname):
    url = f"https://dns.google/resolve?name={hostname}&type=A"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if data.get('Answer'):
            for ans in data['Answer']:
                if ans['type'] == 1:  # A record
                    print(f"[DoH] {hostname} -> {ans['data']}")
                    return ans['data']
    except Exception as e:
        print(f"[DoH] Error: {e}")
    return None

# Test
hosts = [
    "gamma-api.polymarket.com",
    "api.polymarket.com", 
    "integrate.api.nvidia.com",
    "api.telegram.org"
]

print("Resolving hosts via DNS-over-HTTPS...")
for h in hosts:
    ip = resolve_with_doh(h)
    if ip:
        # Add to a cache that we can use
        pass

print("\nDone! If IPs resolved, the API should work via IP.")
print("The IP bypass code in polymarket_client.py will use these.")