import random
import csv
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
import itertools

@dataclass
class TestConfig:
    name: str
    initial_balance: float
    max_position_pct: float
    min_position_pct: float
    stop_loss_pct: float
    take_profit_mult: float
    polymarket_fee: float
    min_edge_threshold: float
    confidence_threshold: int
    num_trades: int

@dataclass
class TestResult:
    config_name: str
    total_trades: int
    win_rate: float
    final_balance: float
    profit: float
    return_pct: float
    max_drawdown: float
    fees_paid: float
    avg_win: float
    avg_loss: float
    timestamp: str

class TradingSimulator:
    def __init__(self, config: TestConfig):
        self.config = config
        self.balance = config.initial_balance
        self.peak_balance = config.initial_balance
        self.trades = []
        self.win_count = 0
        self.total_trades = 0
        
    def run(self) -> TestResult:
        for _ in range(self.config.num_trades):
            if self.balance < 1.0:
                break
                
            market = {
                'yes_price': random.uniform(0.15, 0.85),
                'volume': random.uniform(3000, 250000)
            }
            
            edge = abs(market['yes_price'] - 0.5)
            
            if edge < self.config.min_edge_threshold:
                continue
            
            confidence = self._calculate_confidence(edge, market['volume'])
            
            if confidence < self.config.confidence_threshold:
                continue
            
            position_size = self._calculate_position(confidence)
            win_prob = self._calculate_win_prob(confidence)
            
            risk = position_size * self.config.stop_loss_pct
            reward = risk * self.config.take_profit_mult
            
            won = random.random() < win_prob
            
            if won:
                gross = reward
                net = gross * (1 - self.config.polymarket_fee)
                self.balance += net
                self.win_count += 1
            else:
                self.balance -= risk
            
            self.total_trades += 1
            
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
        
        return self._generate_result()
    
    def _calculate_confidence(self, edge, volume):
        if edge >= 0.20:
            conf = 90
        elif edge >= 0.12:
            conf = 75
        elif edge >= 0.08:
            conf = 60
        else:
            conf = 40
        
        if volume > 50000:
            conf = min(99, conf + 8)
        return conf
    
    def _calculate_position(self, confidence):
        if confidence >= 85:
            pct = self.config.max_position_pct
        elif confidence >= 70:
            pct = self.config.max_position_pct * 0.7
        elif confidence >= 50:
            pct = self.config.max_position_pct * 0.5
        else:
            pct = self.config.min_position_pct
        return max(0.10, self.balance * pct)
    
    def _calculate_win_prob(self, confidence):
        if confidence >= 85:
            return random.uniform(0.60, 0.78)
        elif confidence >= 70:
            return random.uniform(0.50, 0.65)
        elif confidence >= 50:
            return random.uniform(0.40, 0.55)
        else:
            return random.uniform(0.30, 0.45)
    
    def _generate_result(self):
        wins = [t for t in self.trades if t.get('win')]
        losses = [t for t in self.trades if not t.get('win')]
        
        avg_win = sum(t.get('net', 0) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.get('loss', 0) for t in losses) / len(losses) if losses else 0
        
        gross = sum(t.get('gross', 0) for t in self.trades)
        fees = gross * self.config.polymarket_fee
        
        return TestResult(
            config_name=self.config.name,
            total_trades=self.total_trades,
            win_rate=(self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0,
            final_balance=self.balance,
            profit=self.balance - self.config.initial_balance,
            return_pct=((self.balance / self.config.initial_balance) - 1) * 100,
            max_drawdown=((self.peak_balance - self.balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0,
            fees_paid=fees,
            avg_win=avg_win,
            avg_loss=avg_loss,
            timestamp=datetime.now().isoformat()
        )

def run_test_suite():
    configs = [
        TestConfig("Conservative", 10.0, 0.05, 0.01, 0.03, 2.0, 0.07, 0.05, 50, 200),
        TestConfig("Balanced", 10.0, 0.10, 0.02, 0.05, 2.0, 0.07, 0.05, 40, 200),
        TestConfig("Aggressive", 10.0, 0.20, 0.03, 0.08, 1.5, 0.07, 0.03, 30, 200),
        TestConfig("High_Frequency", 10.0, 0.15, 0.02, 0.04, 2.5, 0.07, 0.02, 20, 300),
        TestConfig("Low_Fee_Sensitive", 10.0, 0.08, 0.01, 0.03, 3.0, 0.07, 0.08, 60, 150),
        TestConfig("High_Confidence", 10.0, 0.12, 0.02, 0.05, 2.0, 0.07, 0.10, 70, 200),
        TestConfig("Small_Positions", 10.0, 0.03, 0.01, 0.02, 4.0, 0.07, 0.05, 40, 400),
        TestConfig("Large_Positions", 10.0, 0.25, 0.05, 0.10, 1.5, 0.07, 0.03, 25, 150),
    ]
    
    results = []
    
    print("Running test suite...")
    print("=" * 60)
    
    for config in configs:
        print(f"\nTesting: {config.name}")
        sim = TradingSimulator(config)
        result = sim.run()
        results.append(result)
        
        print(f"  Trades: {result.total_trades} | Win: {result.win_rate:.1f}% | Balance: ${result.final_balance:.2f} | Return: {result.return_pct:.1f}%")
    
    return results

def save_results(results: List[TestResult]):
    os.makedirs("data/tests", exist_ok=True)
    
    # Save as JSON
    with open("data/tests/all_test_results.json", "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    
    # Save as CSV
    with open("data/tests/test_comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(results[0]).keys())
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))
    
    print(f"\nResults saved to data/tests/")

def analyze_results(results: List[TestResult]):
    best = max(results, key=lambda x: x.profit)
    safest = min(results, key=lambda x: x.max_drawdown)
    most_trades = max(results, key=lambda x: x.total_trades)
    
    print(f"\n{'='*60}")
    print("=== TEST ANALYSIS ===")
    print(f"{'='*60}")
    print(f"Best Profit:        {best.config_name} (${best.profit:.2f})")
    print(f"Safest (Lowest DD): {safest.config_name} ({safest.max_drawdown:.1f}%)")
    print(f"Most Active:        {most_trades.config_name} ({most_trades.total_trades} trades)")
    
    # Rank by different metrics
    print(f"\n--- Rankings ---")
    print("\nBy Profit:")
    for i, r in enumerate(sorted(results, key=lambda x: x.profit, reverse=True), 1):
        print(f"  {i}. {r.config_name}: ${r.profit:.2f}")
    
    print("\nBy Win Rate:")
    for i, r in enumerate(sorted(results, key=lambda x: x.win_rate, reverse=True), 1):
        print(f"  {i}. {r.config_name}: {r.win_rate:.1f}%")
    
    print("\nBy Risk-Adjusted Return (Return/MaxDD):")
    for i, r in enumerate(sorted(results, key=lambda x: x.return_pct/max(x.max_drawdown,0.1), reverse=True), 1):
        ratio = r.return_pct / max(r.max_drawdown, 0.1)
        print(f"  {i}. {r.config_name}: {ratio:.1f}x")

if __name__ == "__main__":
    results = run_test_suite()
    save_results(results)
    analyze_results(results)
    
    print(f"\nTotal tests run: {len(results)}")
    print("Next: Use LLM to analyze these results for strategy improvements")