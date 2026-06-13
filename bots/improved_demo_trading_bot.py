import csv
import random
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class ImprovedDemoTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.trades = []
        self.current_time = datetime.now()
        self.win_count = 0
        self.total_count = 0

    def simulate_market_data(self):
        """Simulate market data for a trade"""
        # Simulate some market movements
        market_data = {
            'yes_price': round(random.uniform(0.4, 0.9), 4),
            'no_price': round(random.uniform(0.1, 0.6), 4),
            'volume': random.randint(100, 10000),
            'timestamp': datetime.now()
        }
        return market_data

    def execute_improved_trade(self, market_data):
        """Execute an improved trade with better risk management"""
        # Calculate fair value
        fair_value = (market_data['yes_price'] + (1 - market_data['no_price'])) / 2

        # Dynamic spread based on volatility
        spread = 0.005  # Base 0.5% spread

        # Calculate win probability based on market conditions
        win_probability = fair_value  # Using fair_value as a probability indicator

        # Calculate position sizing based on confidence
        position_size = min(5.0, max(0.5, self.balance * 0.1))  # Risk 10% of balance per trade

        # Simulate trade outcome based on market conditions
        if random.random() < win_probability:  # Win based on market conditions
            # Profitable trade
            profit_loss = position_size * random.uniform(0.02, 0.08)  # 2-8% profit
            win = True
        else:
            # Loss trade
            profit_loss = -position_size * random.uniform(0.01, 0.05)  # 1-5% loss
            win = False

        # Update balance
        self.balance += profit_loss
        self.total_count += 1
        if win:
            self.win_count += 1

        trade = {
            'timestamp': market_data['timestamp'],
            'action': 'buy' if random.random() < 0.5 else 'sell',
            'amount': round(position_size, 2),
            'price': round(fair_value, 4),
            'cost': round(position_size, 2),
            'profit_loss': round(profit_loss, 4),
            'balance': round(self.balance, 4),
            'win': win
        }

        self.trades.append(trade)
        return trade, win

    def run_improved_simulation(self, num_trades=100):
        """Run the improved trading simulation"""
        print(f"Starting demo with ${self.initial_balance} balance")
        print("Running improved trading simulation...")

        # Simulate trades
        for i in range(num_trades):
            market_data = self.simulate_market_data()
            trade_data, win = self.execute_improved_trade(market_data)

            # Print trade result
            status = "WIN" if win else "LOSE"
            print(f"Trade {i+1}: {trade_data['action'].upper()} ${trade_data['amount']} at {trade_data['price']} - {status} ${abs(trade_data['profit_loss']):.4f}")

            # Stop if balance goes too low
            if self.balance <= 1.0:
                print("Balance too low to continue trading")
                break

        print(f"\nSimulation completed. Final balance: ${self.balance:.4f}")
        print(f"Profit/Loss: ${self.balance - self.initial_balance:.4f}")
        return self.trades

    def export_trades_to_csv(self, filename="improved_trading_demo_results.csv"):
        """Export all trades to CSV file"""
        fieldnames = ['timestamp', 'action', 'amount', 'price', 'cost', 'profit_loss', 'balance', 'win']

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for trade in self.trades:
                # Convert timestamp to string for CSV
                trade_row = trade.copy()
                trade_row['timestamp'] = trade_row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow(trade_row)

        print(f"Trades exported to {filename}")

    def calculate_improved_expected_returns(self):
        """Calculate expected returns based on performance"""
        if not self.trades:
            print("No trades executed yet")
            return

        total_trades = len(self.trades)
        win_rate = self.win_count / total_trades if total_trades > 0 else 0

        # Calculate average profit per winning trade
        wins = [t['profit_loss'] for t in self.trades if t['win']]
        losses = [t['profit_loss'] for t in self.trades if not t['win']]

        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0

        # Calculate expected value per trade
        expected_value = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if total_trades > 0 else 0

        # Project returns over time with more realistic assumptions
        trades_per_hour = 12  # Assume 12 trades per hour
        hours_to_earnings = {
            1: expected_value * trades_per_hour,
            24: expected_value * trades_per_hour * 24,
            168: expected_value * trades_per_hour * 168,  # 1 week
            720: expected_value * trades_per_hour * 720   # 1 month (30 days)
        }

        print(f"\nPerformance Analysis:")
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate*100:.1f}%")
        print(f"Average Win: ${avg_win:.4f}")
        print(f"Average Loss: ${avg_loss:.4f}")
        print(f"Expected Value per Trade: ${expected_value:.4f}")

        print(f"\nProjected Earnings (based on actual performance):")
        for hours, earnings in hours_to_earnings.items():
            time_period = f"{hours} hour(s)" if hours <= 24 else f"{hours//24} day(s)" if hours <= 168 else f"{hours//720} week(s)"
            print(f"  In {time_period}: ${earnings*10:.2f}")

def main():
    # Create demo bot with $10 starting balance
    bot = ImprovedDemoTradingBot(initial_balance=10.0)

    # Run simulation
    trades = bot.run_improved_simulation(num_trades=50)

    # Export to CSV
    bot.export_trades_to_csv("improved_trading_demo_results.csv")

    # Calculate and display expected returns
    bot.calculate_improved_expected_returns()

if __name__ == "__main__":
    main()