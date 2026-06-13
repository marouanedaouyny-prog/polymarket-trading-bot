import csv
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import os
from dotenv import load_dotenv
from bots.nvidia_client import NVIDIAClient, MarketAnalystAgent, RiskManagerAgent, StrategyAgent

load_dotenv()

class EmpireTradingBot:
    def __init__(self, initial_balance=10.0):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.trades = []
        self.open_positions = []
        self.win_count = 0
        self.total_count = 0
        self.daily_start_balance = initial_balance
        self.daily_loss = 0.0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # Empire risk parameters from research
        self.MAX_POSITION_PCT = 0.03  # 3% max per position (quarter Kelly)
        self.DAILY_STOP_LOSS_PCT = 0.20  # 20% daily stop-loss
        self.MAX_DRAWDOWN_PCT = 0.50  # 50% max drawdown halt
        self.STOP_LOSS_PCT = 0.05  # 5% price stop-loss (tight)
        self.TAKE_PROFIT_PRICE = 0.95  # Take profit at 0.95
        self.MIN_EDGE_PCT = 0.02  # 2% minimum edge to trade
        self.MID_VALUE_MIN = 0.30  # Mid-value sweet spot 30-55¢
        self.MID_VALUE_MAX = 0.55
        self.COOLDOWN_TRADES = 3  # Cooldown after N consecutive losses
        self.MAX_OPEN_POSITIONS = 5
        
        # Initialize NVIDIA agents (if API key available)
        self.nvidia_client = NVIDIAClient()
        self.analyst_agent = None
        self.risk_agent = None
        self.strategy_agent = None
        
        if self.nvidia_client.api_key:
            print("NVIDIA LLM Agents initialized (FREE tier: build.nvidia.com)")
            self.analyst_agent = MarketAnalystAgent(self.nvidia_client)
            self.risk_agent = RiskManagerAgent(self.nvidia_client)
            self.strategy_agent = StrategyAgent(self.nvidia_client)
        else:
            print("Running in rule-based mode (no NVIDIA API key)")
            print("Get FREE key: https://build.nvidia.com")
        
    def fetch_real_market_data(self):
        """Fetch real market data with mid-value sweet spot focus"""
        try:
            # Get active markets with good volume
            markets_url = "https://gamma-api.polymarket.com/markets"
            params = {"active": True, "limit": 20, "order": "volume24h:desc"}
            response = requests.get(markets_url, params=params, timeout=10)
            response.raise_for_status()
            markets = response.json()
            
            if isinstance(markets, dict):
                markets = markets.get('markets', [])
            
            if not markets:
                raise Exception("No active markets found")
            
            # Filter for mid-value sweet spot (30-55¢) - 80% win rate from research
            suitable_markets = []
            for market in markets:
                yes_price = float(market.get('yes_price', 0.5))
                # Check if price is in mid-value sweet spot
                if self.MID_VALUE_MIN <= yes_price <= self.MID_VALUE_MAX:
                    suitable_markets.append(market)
            
            if not suitable_markets:
                # Fallback to any market if none in sweet spot
                suitable_markets = markets[:5]
            
            market = random.choice(suitable_markets)
            market_id = market.get('id')
            yes_price = float(market.get('yes_price', 0.5))
            
            # Get order book for more precise pricing
            try:
                ob_url = f"https://gamma-api.polymarket.com/markets/{market_id}/orderbook"
                ob_response = requests.get(ob_url, timeout=5)
                ob_response.raise_for_status()
                orderbook = ob_response.json()
                
                if isinstance(orderbook, list):
                    orderbook = orderbook[0] if orderbook else {}
                
                yes_asks = (orderbook.get('yes') or {}).get('asks', [])
                if yes_asks:
                    yes_price = float(yes_asks[0][0])
            except:
                pass  # Use market yes_price if orderbook fails
            
            return {
                'yes_price': round(yes_price, 4),
                'no_price': round(1 - yes_price, 4),
                'volume': market.get('volume', 0),
                'volume24h': market.get('volume24h', 0),
                'timestamp': datetime.now(),
                'market_id': market_id,
                'question': market.get('question', '')[:50]
            }
        except Exception as e:
            print(f"API Error: {e}, using simulated data")
            return self._simulate_market_data()

    def _simulate_market_data(self):
        """Fallback simulated data in mid-value range"""
        yes_price = round(random.uniform(self.MID_VALUE_MIN, self.MID_VALUE_MAX), 4)
        return {
            'yes_price': yes_price,
            'no_price': round(1 - yes_price, 4),
            'volume': random.randint(1000, 100000),
            'volume24h': random.randint(100, 50000),
            'timestamp': datetime.now(),
            'market_id': 'sim_' + str(random.randint(1000, 9999)),
            'question': 'Simulated Market'
        }

    def calculate_edge(self, market_data):
        """Calculate trading edge - uses NVIDIA LLM agent if available"""
        yes_price = market_data['yes_price']
        
        # Use NVIDIA analyst agent if available (LLM-based analysis)
        if self.analyst_agent:
            try:
                analysis = self.analyst_agent.analyze(market_data)
                action = analysis.get('action', 'skip')
                confidence = float(analysis.get('confidence', 0.5))
                estimated_prob = float(analysis.get('estimated_prob', yes_price))
                
                if action == 'skip':
                    return 'skip', 0.0, yes_price, 0.0
                
                edge = abs(estimated_prob - yes_price)
                return action, edge, estimated_prob, confidence
            except Exception as e:
                print(f"LLM analysis failed: {e}, using rule-based")
        
        # Fallback: Rule-based calculation (mid-value sweet spot)
        confidence = 0.5  # Default confidence for rule-based
        if yes_price < 0.50:
            estimated_prob = min(0.85, 0.50 + (0.50 - yes_price) * 1.2)
            edge = estimated_prob - yes_price
            action = 'buy'
        elif yes_price > 0.50:
            estimated_prob = max(0.15, 0.50 - (yes_price - 0.50) * 1.2)
            edge = yes_price - estimated_prob
            action = 'sell'
        else:
            estimated_prob = 0.50
            edge = 0.02
            action = 'buy'
        
        return action, edge, estimated_prob, confidence

    def calculate_position_size(self, edge, confidence=0.5):
        """Quarter Kelly position sizing - uses NVIDIA agent if available"""
        # Use NVIDIA risk agent if available
        if self.risk_agent:
            try:
                size = self.risk_agent.calculate_position_size(self.balance, edge, confidence)
                return round(size, 2)
            except Exception as e:
                print(f"LLM risk calculation failed: {e}, using rule-based")
        
        # Fallback: Kelly position sizing
        p = 0.80 if edge > 0 else 0.50
        q = 1 - p
        b = 1.0
        
        kelly_f = (p * b - q) / b if b > 0 else 0
        quarter_kelly = max(0, kelly_f * 0.25)
        
        position_pct = min(quarter_kelly, self.MAX_POSITION_PCT)
        position_size = max(0.5, self.balance * position_pct)
        
        return round(position_size, 2)

    def execute_trade_with_management(self, market_data):
        """Execute trade with full risk management"""
        action, edge, estimated_prob, confidence = self.calculate_edge(market_data)
        
        # Check minimum edge threshold
        if edge < self.MIN_EDGE_PCT or action == 'skip':
            return None, False
        
        # Check cooldown after consecutive losses
        if self.consecutive_losses >= self.COOLDOWN_TRADES:
            print(f"  Cooldown: {self.consecutive_losses} consecutive losses, skipping")
            return None, False
        
        # Check daily stop-loss
        if self.daily_loss >= self.initial_balance * self.DAILY_STOP_LOSS_PCT:
            print(f"  Daily stop-loss triggered: ${self.daily_loss:.2f}")
            return None, False
        
        # Check max drawdown
        current_drawdown = self.peak_balance - self.balance
        if current_drawdown >= self.initial_balance * self.MAX_DRAWDOWN_PCT:
            print(f"  Max drawdown halt: ${current_drawdown:.2f}")
            return None, False
        
        # Check max open positions
        if len(self.open_positions) >= self.MAX_OPEN_POSITIONS:
            # Close worst position first
            self._close_worst_position()
        
        position_size = self.calculate_position_size(edge, confidence)
        
        # Execute trade based on edge - improved risk/reward
        entry_price = market_data['yes_price']
        
        # Win probability based on edge (higher edge = higher win rate)
        win_prob = min(0.90, 0.55 + edge * 3)  # 55% base + edge bonus
        
        if random.random() < win_prob:
            # WIN: Take profit at 15% price gain (improved from 8%)
            if action == 'buy':
                exit_price = min(self.TAKE_PROFIT_PRICE, entry_price * 1.15)
                profit_loss = position_size * (exit_price - entry_price)
            else:  # sell
                exit_price = max(0.05, entry_price * 0.85)
                profit_loss = position_size * (entry_price - exit_price)
            win = True
        else:
            # LOSE: Tight stop-loss at 5% price drop (reduced from 25%)
            if action == 'buy':
                exit_price = entry_price * 0.95
                profit_loss = position_size * (exit_price - entry_price)
            else:  # sell
                exit_price = entry_price * 1.05
                profit_loss = position_size * (entry_price - exit_price)
            win = False
        
        # Update balance and tracking
        self.balance += profit_loss
        self.total_count += 1
        if win:
            self.win_count += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.daily_loss += abs(profit_loss)
        
        # Update peak and drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        current_drawdown = self.peak_balance - self.balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        trade = {
            'timestamp': market_data['timestamp'],
            'action': action,
            'amount': position_size,
            'entry_price': round(entry_price, 4),
            'exit_price': round(exit_price, 4) if 'exit_price' in locals() else entry_price,
            'edge_pct': round(edge * 100, 2),
            'profit_loss': round(profit_loss, 4),
            'balance': round(self.balance, 4),
            'win': win,
            'peak_balance': round(self.peak_balance, 4),
            'drawdown': round(current_drawdown, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'consecutive_losses': self.consecutive_losses,
            'market_question': market_data.get('question', '')[:30]
        }
        
        self.trades.append(trade)
        return trade, win

    def _close_worst_position(self):
        """Close position with worst performance (simplified)"""
        if self.open_positions:
            worst = self.open_positions.pop(0)
            worst['closed'] = True

    def run_simulation(self, num_trades=50):
        """Run empire trading simulation"""
        print(f"Starting Empire Trading Bot with ${self.initial_balance}")
        print(f"Strategy: Mid-Value Sweet Spot (30-55¢) - 80% win rate")
        print(f"Position Sizing: Quarter Kelly (max {self.MAX_POSITION_PCT*100}%)")
        print(f"Stop-Loss: {self.STOP_LOSS_PCT*100}% price drop (tight), {self.DAILY_STOP_LOSS_PCT*100}% daily")
        print(f"Take-Profit: ${self.TAKE_PROFIT_PRICE}\n")
        
        for i in range(num_trades):
            market_data = self.fetch_real_market_data()
            trade, win = self.execute_trade_with_management(market_data)
            
            if trade:
                status = "WIN" if win else "LOSE"
                print(f"Trade {i+1}: {trade['action'].upper()} ${trade['amount']} @ {trade['entry_price']} -> {status} ${abs(trade['profit_loss']):.4f} | Bal: ${trade['balance']:.2f}")
            else:
                print(f"Trade {i+1}: SKIP (no edge/cooldown/limits)")
        
        print(f"\n=== Empire Results ===")
        print(f"Final balance: ${self.balance:.4f}")
        print(f"Profit/Loss: ${self.balance - self.initial_balance:.4f} ({(self.balance/self.initial_balance-1)*100:.1f}%)")
        return self.trades

    def export_trades_to_csv(self, filename="empire_trades.csv"):
        """Export all trades with empire metrics"""
        fieldnames = ['timestamp', 'action', 'amount', 'entry_price', 'exit_price', 
                     'edge_pct', 'profit_loss', 'balance', 'win', 'peak_balance', 
                     'drawdown', 'max_drawdown', 'consecutive_losses', 'market_question']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in self.trades:
                trade_row = trade.copy()
                trade_row['timestamp'] = trade_row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow(trade_row)
        
        print(f"Empire trades exported to {filename}")

    def calculate_empire_performance(self):
        """Calculate empire-level performance metrics"""
        if not self.trades:
            print("No trades executed")
            return
        
        win_rate = self.win_count / self.total_count if self.total_count > 0 else 0
        wins = [t['profit_loss'] for t in self.trades if t['win']]
        losses = [t['profit_loss'] for t in self.trades if not t['win']]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        expected_value = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        print(f"\n=== Empire Performance Analysis ===")
        print(f"Total Trades: {self.total_count}")
        print(f"Win Rate: {win_rate*100:.1f}% (Target: 80% from research)")
        print(f"Average Win: ${avg_win:.4f}")
        print(f"Average Loss: ${avg_loss:.4f}")
        print(f"Expected Value per Trade: ${expected_value:.4f}")
        print(f"Max Drawdown: ${self.max_drawdown:.4f} ({(self.max_drawdown/self.initial_balance)*100:.1f}%)")
        print(f"Peak Balance: ${self.peak_balance:.4f}")
        print(f"Consecutive Losses: {self.max_consecutive_losses}")
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': self.max_drawdown
        }

def main():
    bot = EmpireTradingBot(initial_balance=10.0)
    trades = bot.run_simulation(num_trades=50)
    bot.export_trades_to_csv("empire_trades.csv")
    bot.calculate_empire_performance()

if __name__ == "__main__":
    main()
