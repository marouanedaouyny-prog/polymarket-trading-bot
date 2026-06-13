"""
1-Hour Empire Simulation - 2400 trades (40 trades/min x 60 min)
Save results to CSV with $10 starting balance
"""
from empire_llm_demo import EmpireBotLLM
import time

def run_1hour_simulation():
    print("=" * 60)
    print("EMPIRE 1-HOUR SIMULATION (2400 trades)")
    print("=" * 60)
    
    bot = EmpireBotLLM(initial_balance=10.0)
    
    # Run 2400 trades (1 hour at 40 trades/min NVIDIA limit)
    start_time = time.time()
    trades = bot.run_simulation(num_trades=2400)
    end_time = time.time()
    
    # Save to CSV
    bot.export_to_csv('empire_1hour_trades.csv')
    
    # Calculate results
    profit = bot.balance - bot.initial_balance
    win_rate = (bot.win_count / bot.total_count * 100) if bot.total_count > 0 else 0
    total_fees = sum(t.get('fee', 0) + t.get('gas_fee', 0) for t in bot.trades)
    
    print(f"\n{'=' * 60}")
    print("1-HOUR RESULTS (REAL-MONEY MODEL)")
    print(f"{'=' * 60}")
    print(f"Starting Balance: $10.00")
    print(f"Final Balance: ${bot.balance:.4f}")
    print(f"Total Profit: ${profit:.4f} ({profit/10*100:.1f}%)")
    print(f"Trades Executed: {bot.total_count}/2400")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Total Fees Paid: ${total_fees:.4f}")
    print(f"Simulation Time: {end_time-start_time:.1f}s")
    print(f"{'=' * 60}")
    
    # 30-day projection
    print(f"\n30-DAY PROJECTION (1 hour/day):")
    print(f"{'=' * 60}")
    daily_profit = profit
    monthly_profit = daily_profit * 30
    print(f"Daily Profit: ${daily_profit:.4f}")
    print(f"30-Day Profit: ${monthly_profit:.4f} ({(monthly_profit/10)*100:.0f}%)")
    print(f"Projected Balance: ${10 + monthly_profit:.4f}")
    print(f"{'=' * 60}")
    print(f"\nSaved to: empire_1hour_trades.csv")

if __name__ == "__main__":
    run_1hour_simulation()
