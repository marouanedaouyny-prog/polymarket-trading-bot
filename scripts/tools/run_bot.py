import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_root)
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv('config/.env')

from bots.empire_trading_bot import EmpireTradingBot

print("Starting Empire Trading Bot - Paper Mode")
print("Initial Balance: $10")
print("-" * 40)

bot = EmpireTradingBot(initial_balance=10.0)

trades = bot.run_simulation(num_trades=50)

bot.export_trades_to_csv("data/results/empire_paper_trades.csv")
bot.calculate_empire_performance()

print("\n" + "=" * 40)
print("Paper trading complete!")
print("Results saved to: data/results/empire_paper_trades.csv")