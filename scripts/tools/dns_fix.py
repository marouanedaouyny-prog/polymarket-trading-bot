import socket
import os

# Override DNS for specific hosts
def patch_dns():
    # Create a custom resolver that bypasses system DNS
    
    original_getaddrinfo = socket.getaddrinfo
    
    def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if 'polymarket' in host.lower():
            print(f"[DNS FIX] Redirecting {host} to 104.18.34.205")
            return [(socket.AF_INET, socket.SOCK_STREAM, proto, '', ('104.18.34.205', port))]
        if 'nvidia' in host.lower() and 'api' in host.lower():
            print(f"[DNS FIX] Redirecting {host} to 99.83.136.103")
            return [(socket.AF_INET, socket.SOCK_STREAM, proto, '', ('99.83.136.103', port))]
        if 'telegram' in host.lower():
            print(f"[DNS FIX] Redirecting {host} to 149.154.167.99")
            return [(socket.AF_INET, socket.SOCK_STREAM, proto, '', ('149.154.167.99', port))]
        return original_getaddrinfo(host, port, family, type, proto, flags)
    
    socket.getaddrinfo = custom_getaddrinfo
    print("[DNS] Custom resolver active - redirecting API calls")
    return True

if __name__ == "__main__":
    patch_dns()
    
    # Test
    try:
        print("\nTesting Polymarket...")
        result = socket.getaddrinfo("gamma-api.polymarket.com", 443)
        print(f"Polymarket resolved to: {result[0][4]}")
    except Exception as e:
        print(f"Polymarket error: {e}")
    
    try:
        print("\nTesting NVIDIA...")
        result = socket.getaddrinfo("integrate.api.nvidia.com", 443)
        print(f"NVIDIA resolved to: {result[0][4]}")
    except Exception as e:
        print(f"NVIDIA error: {e}")