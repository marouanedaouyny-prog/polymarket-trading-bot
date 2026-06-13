import requests
import socket
import asyncio
import aiohttp

# Pre-resolved IPs from DNS-over-HTTPS
RESOLVED_IPS = {
    "gamma-api.polymarket.com": "172.64.153.51",
    "api.polymarket.com": "172.64.153.51", 
    "integrate.api.nvidia.com": "75.2.113.119",
    "api.telegram.org": "149.154.166.110"
}

# Monkey-patch socket to use resolved IPs
_original_getaddrinfo = socket.getaddrinfo

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host in RESOLVED_IPS:
        print(f"[DNS PATCH] Using {RESOLVED_IPS[host]} for {host}")
        return [(socket.AF_INET, type, proto, '', (RESOLVED_IPS[host], port))]
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _patched_getaddrinfo

# Now test requests
print("Testing with patched DNS...")

# Test Polymarket
print("\n1. Polymarket:")
try:
    r = requests.get("https://gamma-api.polymarket.com/markets", 
                   headers={"Host": "gamma-api.polymarket.com"}, 
                   verify=False, timeout=10)
    print(f"   Status: {r.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Test NVIDIA
print("\n2. NVIDIA:")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv('config/.env')
    api_key = os.getenv('NVIDIA_API_KEY')
    r = requests.get("https://integrate.api.nvidia.com/v1/chat/completions",
                     headers={"Host": "integrate.api.nvidia.com"},
                     params={"model": "mistralai/mixtral-8x7b-instruct-v0.1"},
                     auth=("Bearer", api_key),
                     verify=False, timeout=10)
    print(f"   Status: {r.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Test Telegram
print("\n3. Telegram:")
try:
    r = requests.get("https://api.telegram.org/bot/test/sendMessage",
                     headers={"Host": "api.telegram.org"},
                     verify=False, timeout=10)
    print(f"   Status: {r.status_code}")
except Exception as e:
    print(f"   Error: {e}")