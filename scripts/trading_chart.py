import csv
import matplotlib.pyplot as plt
from datetime import datetime

def create_performance_chart():
    """Create a performance chart from the CSV data"""
    # Read the CSV data
    trades = []
    with open('improved_trading_demo_results.csv', 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)
        for row in reader:
            trades.append({
                'timestamp': row[0],
                'action': row[1],
                'amount': float(row[2]),
                'price': float(row[3]),
                'profit_loss': float(row[5]),
                'balance': float(row[6]),
                'win': row[7] == 'True'
            })

    # Extract data for plotting
    balances = []
    for trade in trades:
        balances.append(trade['balance'])

    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(balances, marker='o', linestyle='-', color='b')
    plt.title('Account Balance Over Time')
    plt.xlabel('Trade Number')
    plt.ylabel('Account Balance ($)')
    plt.grid(True)
    plt.savefig('trading_performance.png')
    plt.close()

    print("Performance chart saved as 'trading_performance.png'")

if __name__ == "__main__":
    create_performance_chart()