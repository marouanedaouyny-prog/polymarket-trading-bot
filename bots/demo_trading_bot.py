import csv
import random
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

class DemoTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.trades = []
        self.current_time = datetime.now()

    def simulate_market_data(self):
        """Simulate market data for a trade"""
        # Simulate some market movements
        market_data = {
            'yes_price': round(random.uniform(0.4, 0.9), 4),
            'no_price': round(random.uniform(0.1, 0.6), 4),
            'volume': random.randint(100, 10000),
            'timestamp': self.current_time
        }
        self.current_time += timedelta(minutes=5)
        return market_data

    def execute_trade(self, market_data):
        """Simulate executing a trade"""
        # Simulate a simple market making strategy
        fair_value = (market_data['yes_price'] + (1 - market_data['no_price'])) / 2
        spread = 0.005  # 0.5% spread

        # Simulate buying low and selling high
        buy_price = fair_value - spread/2
        sell_price = fair_value + spread/2

        # Randomly decide to buy or sell
        action = random.choice(['buy', 'sell'])
        trade_amount = round(random.uniform(1, 5), 2)  # Trade $1-$5

        if action == 'buy':
            price = buy_price
            cost = trade_amount
            # Simulate profit/loss when selling later
            profit_loss = round((sell_price - buy_price) * trade_amount * 100, 4)
        else:
            price = sell_price
            cost = trade_amount
            # Simulate profit/loss when buying back
            profit_loss = round((buy_price - sell_price) * trade_amount * 100, 4)

        # Add some randomness to profit/loss
        profit_loss = profit_loss + random.uniform(-0.5, 0.5)

        # Update balance
        self.balance += profit_loss

        trade = {
            'timestamp': market_data['timestamp'],
            'action': action,
            'amount': trade_amount,
            'price': round(price, 4),
            'cost': cost,
            'profit_loss': round(profit_loss, 4),
            'balance': round(self.balance, 4),
            'win': profit_loss > 0
        }

        self.trades.append(trade)
        return trade

    def run_simulation(self, num_trades=50):
        """Run the trading simulation"""
        print(f"Starting demo with ${self.initial_balance} balance")
        print("Running trading simulation...")

        for i in range(num_trades):
            market_data = self.simulate_market_data()
            trade = self.execute_trade(market_data)

            # Print trade result
            status = "WIN" if trade['win'] else "LOSE"
            print(f"Trade {i+1}: {trade['action'].upper()} ${trade['amount']} at {trade['price']} - {status} ${abs(trade['profit_loss']):.4f}")

            # Stop if balance goes too low
            if self.balance <= 1.0:
                print("Balance too low to continue trading")
                break

        print(f"\nSimulation completed. Final balance: ${self.balance:.4f}")
        print(f"Profit/Loss: ${self.balance - self.initial_balance:.4f}")
        return self.trades

    def export_trades_to_csv(self, filename="trading_demo_results.csv"):
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

    def calculate_expected_returns(self):
        """Calculate expected returns based on performance"""
        if not self.trades:
            print("No trades executed yet")
            return

        wins = [t for t in self.trades if t['win']]
        losses = [t for t in self.trades if not t['win']]

        total_trades = len(self.trades)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0

        # Calculate average profit per winning trade
        avg_win = np.mean([t['profit_loss'] for t in wins]) if wins else 0

        # Calculate average loss per losing trade
        avg_loss = np.mean([t['profit_loss'] for t in losses]) if losses else 0

        # Calculate expected value per trade
        expected_value = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if total_trades > 0 else 0

        # Project returns over time
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

        print(f"\nProjected Earnings:")
        for hours, earnings in hours_to_earnings.items():
            time_period = f"{hours} hour(s)" if hours <= 24 else f"{hours//24} day(s)" if hours <= 168 else f"{hours//720} week(s)"
            print(f"  In {time_period}: ${earnings*10:.2f} (based on 10x actual performance)")

        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expected_value': expected_value
        }

def main():
    # Create demo bot with $10 starting balance
    bot = DemoTradingBot(initial_balance=10.0)

    # Run simulation
    trades = bot.run_simulation(num_trades=50)

    # Export to CSV
    bot.export_trades_to_csv("trading_demo_results.csv")

    # Calculate and display expected returns
    bot.calculate_expected_returns()

if __name__ == "__main__":
    main()