
import os
import time
from datetime import datetime

# Path to the .env file in the config folder
env_path = os.path.join('config', '.env')

# Ensure the directory exists
os.makedirs('config', exist_ok=True)

# Configuration for Paper Trading
env_content = """
# Trading Config
TRADING_MODE=paper
STARTING_BALANCE=20.00
MAX_POSITION_PCT=0.15
MIN_EDGE=0.65
MIN_CONFIDENCE=65

# Risk Config  
STOP_LOSS_PCT=0.25
TAKE_PROFIT_PCT=2.0
DAILY_LOSS_LIMIT=0.10
MAX_DAILY_TRADES=100
"""

with open(env_path, 'w') as f:
    f.write(env_content)

print(f"Paper trading configuration initialized at {env_path}")
print("Mode set to PAPER_TRADING. Bot will now run against live data without risk.")
