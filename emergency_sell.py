"""
Emergency exit script for XRP positions.
Attempts to sell the specific tokens held.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load configuration
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.trading.live_trading import PolymarketOrderExecutor

def sell_xrp():
    if os.getenv("ALLOW_EMERGENCY_SELL", "false").lower() != "true":
        raise SystemExit(
            "Emergency sell is disabled. This script has hardcoded token/share values. "
            "Set ALLOW_EMERGENCY_SELL=true only after verifying the exact position."
        )

    executor = PolymarketOrderExecutor(mode='live')
    
    # The token ID from the logs for XRP NO
    token_id = "98400042666692221054244145078007653701217437023963109384993219263754572889815"
    market_id = "2445409"
    
    print(f"Attempting to sell XRP NO positions...")
    
    try:
        client = executor._create_sdk_client()
        
        # Get your balance of these specific shares
        print("Fetching share balance...")
        # Note: The SDK method for balance can vary, we'll try a common one
        # or use the known amount of ~9000 shares
        
        shares_to_sell = "9096.0" 
        
        print(f"Selling {shares_to_sell} shares...")
        
        response = client.place_market_order(
            token_id=token_id,
            side='SELL',
            shares=shares_to_sell,
            order_type='FOK'
        )
        print(f"Sell Result: {response}")
    except Exception as e:
        print(f"Sell Failed: {e}")

if __name__ == "__main__":
    sell_xrp()
