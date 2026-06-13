#!/usr/bin/env python3
"""
Demo Polymarket Trading System
Simulates trading without real money and saves transactions for training
"""

import asyncio
import json
import random
import uuid
from datetime import datetime
from typing import Dict, List
import csv
import os

class VirtualTradingSystem:
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.virtual_balance = initial_balance
        self.trades_history = []
        self.positions = {}
        self.trades_file = "demo_trades_history.json"
        self.csv_trades_file = "demo_trades_history.csv"

    async def fetch_market_data(self) -> List[Dict]:
        """Simulate fetching market data from Polymarket"""
        # Simulate market data with random price movements
        markets = []
        for i in range(5):  # Simulate 5 markets
            market = {
                'id': f'market_{i}',
                'name': f'Virtual Market {i}',
                'yes_price': round(random.uniform(0.1, 0.9), 3),
                'no_price': round(1.0 - random.uniform(0.1, 0.9), 3),
                'volume': random.randint(1000, 100000),
                'timestamp': datetime.utcnow().isoformat()
            }
            markets.append(market)
        return markets

    def detect_arbitrage_opportunities(self, markets: List[Dict]) -> List[Dict]:
        """Detect arbitrage opportunities in the markets"""
        opportunities = []
        for market in markets:
            # Simple arbitrage detection: if yes_price + no_price != 1.0, there's an opportunity
            price_sum = market['yes_price'] + market['no_price']
            if abs(price_sum - 1.0) > 0.05:  # 5% threshold for arbitrage
                opportunity = {
                    'id': str(uuid.uuid4()),
                    'market_id': market['id'],
                    'market_name': market['name'],
                    'yes_price': market['yes_price'],
                    'no_price': market['no_price'],
                    'arbitrage_amount': abs(price_sum - 1.0),
                    'confidence': min(abs(price_sum - 1.0) * 20, 1.0),  # Scale confidence
                    'timestamp': datetime.utcnow().isoformat()
                }
                opportunities.append(opportunity)
        return opportunities

    async def execute_trade(self, opportunity: Dict, side: str, amount: float) -> Dict:
        """Execute a virtual trade"""
        trade_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Simulate trade execution
        execution_price = opportunity['yes_price'] if side == 'buy' else opportunity['no_price']
        cost = amount * execution_price

        # Update virtual balance
        if side == 'buy':
            self.virtual_balance -= cost
        else:
            self.virtual_balance += cost

        trade = {
            'trade_id': trade_id,
            'opportunity_id': opportunity['id'],
            'market_id': opportunity['market_id'],
            'side': side,
            'amount': amount,
            'price': execution_price,
            'cost': cost,
            'timestamp': timestamp,
            'balance_after': self.virtual_balance,
            'profit_loss': 0.0  # Will be calculated later
        }

        self.trades_history.append(trade)
        self.save_trade_to_file(trade)
        self.save_trade_to_csv(trade)

        print(f"Executed {side.upper()} trade: {amount} at {execution_price} on {opportunity['market_name']}")
        print(f"Virtual balance: ${self.virtual_balance:.2f}")

        return trade

    def save_trade_to_file(self, trade: Dict):
        """Save trade to JSON file"""
        try:
            # Load existing trades
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r') as f:
                    existing_trades = json.load(f)
            else:
                existing_trades = []

            # Add new trade
            existing_trades.append(trade)

            # Save back to file
            with open(self.trades_file, 'w') as f:
                json.dump(existing_trades, f, indent=2)
        except Exception as e:
            print(f"Error saving trade to file: {e}")

    def save_trade_to_csv(self, trade: Dict):
        """Save trade to CSV file"""
        file_exists = os.path.exists(self.csv_trades_file)

        with open(self.csv_trades_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                # Write header
                writer.writerow([
                    'trade_id', 'opportunity_id', 'market_id', 'side', 'amount',
                    'price', 'cost', 'timestamp', 'balance_after'
                ])

            # Write trade data
            writer.writerow([
                trade['trade_id'], trade['opportunity_id'], trade['market_id'],
                trade['side'], trade['amount'], trade['price'], trade['cost'],
                trade['timestamp'], trade['balance_after']
            ])

    async def run_demo_cycle(self):
        """Run one cycle of the demo trading system"""
        print(f"\n=== Demo Trading Cycle Started ===")
        print(f"Initial virtual balance: ${self.virtual_balance:.2f}")

        # Fetch market data
        print("Fetching market data...")
        markets = await self.fetch_market_data()

        # Detect arbitrage opportunities
        print("Detecting arbitrage opportunities...")
        opportunities = self.detect_arbitrage_opportunities(markets)

        if opportunities:
            print(f"Found {len(opportunities)} arbitrage opportunities")

            # Execute some demo trades
            for opportunity in opportunities[:2]:  # Only take first 2 opportunities
                if opportunity.get('confidence', 0) > 0.7:  # High confidence trades
                    # Simulate a buy/sell decision
                    if random.choice([True, False]):
                        # Simulate a buy
                        amount = random.uniform(10, 100)
                        await self.execute_trade(opportunity, 'buy', amount)
                    else:
                        # Simulate a sell
                        amount = random.uniform(10, 100)
                        await self.execute_trade(opportunity, 'sell', amount)
        else:
            print("No arbitrage opportunities found in this cycle")

        print(f"Current virtual balance: ${self.virtual_balance:.2f}")
        print("=== Demo Trading Cycle Completed ===\n")

    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        total_trades = len(self.trades_history)
        total_profit_loss = self.virtual_balance - 10000.0  # Initial balance was 10000

        return {
            'total_trades': total_trades,
            'current_balance': self.virtual_balance,
            'initial_balance': 10000.0,
            'total_profit_loss': total_profit_loss,
            'roi_percentage': (total_profit_loss / 10000.0) * 100
        }

async def main():
    """Main function to run the demo trading system"""
    print("Starting Demo Trading System...")

    # Create trading system
    trading_system = VirtualTradingSystem()

    # Run demo cycles
    for i in range(3):  # Run 3 cycles of demo
        await trading_system.run_demo_cycle()
        await asyncio.sleep(1)  # Wait 1 second between cycles

    # Print final summary
    summary = trading_system.get_performance_summary()
    print(f"Final Summary: {summary}")

    print("\nDemo Trading System")
    print("==================")
    print("This system simulates trading without using real money.")
    print("All trades are saved to files for training purposes.")
    print("To run with real money, check the Polymarket API documentation")
    print("and ensure you have set up API keys in your .env file.")

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())