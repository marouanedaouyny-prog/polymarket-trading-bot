#!/usr/bin/env python3
import asyncio
import random
from datetime import datetime

# Simple $10 trading demo
class SimpleTradingDemo:
    def __init__(self):
        self.balance = 10.0  # Start with $10

    async def run_demo(self):
        print(f"Starting balance: $10.00")
        balance = self.balance

        # Simulate a few trades
        for i in range(3):
            # Simulate buying and selling
            if random.choice([True, False]):
                # Buy trade
                amount = random.uniform(1, 3)
                price = random.uniform(0.3, 0.7)
                cost = amount * price
                balance -= cost
                print(f"Trade {i+1}: BUY {amount:.2f} at ${price:.2f} = -${cost:.2f}, Balance: ${balance:.2f}")
            else:
                # Sell trade
                amount = random.uniform(1, 3)
                price = random.uniform(0.4, 0.8)
                earnings = amount * price
                balance += earnings
                print(f"Trade {i+1}: SELL {amount:.2f} at ${price:.2f} = +${earnings:.2f}, Balance: ${balance:.2f}")

        print(f"Final balance: ${balance:.2f}")
        profit = balance - 10.0
        print(f"Profit: ${profit:.2f}")
        print(f"ROI: {(profit/10.0)*100:.2f}%")

demo = SimpleTradingDemo()
asyncio.run(demo.run_demo())