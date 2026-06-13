import csv

def create_performance_chart_text():
    """Create a text-based performance chart from the CSV data"""
    # Read the CSV data
    trades = []
    with open('improved_trading_demo_results.csv', 'r') as file:
        reader = csv.reader(file)
        headers = next(reader)
        for row in reader:
            trades.append({
                'timestamp': row[0],
                'action': row[1],
                'amount': row[2],
                'price': row[3],
                'profit_loss': row[5],
                'balance': row[6],
                'win': row[7] == 'True'
            })

    # Read data from the results file
    with open('improved_trading_demo_results.csv', 'r') as file:
        lines = file.readlines()

    # Extract balances
    balances = []
    for i, line in enumerate(lines[1:], 1):
        data = line.strip().split(',')
        if len(data) > 6:
            balance = float(data[6])
            balances.append(balance)

    # Create simple text chart
    print("Performance over time:")
    print("Starting balance: $10.00")
    print("Trade # | Balance")
    print("--------|--------")

    for i, line in enumerate(lines[1:], 1):
        data = line.strip().split(',')
        if len(data) > 6:
            balance = float(data[6])
            print(f"{i:6d}  | ${balance:.4f}")

    print("\nBalance progression:")
    # Show every 5th trade to keep output reasonable
    for i in range(0, len(balances), 5):
        print(f"  Trade {i+1:2d}: ${balances[i]:.2f}")

    print(f"\nFinal result: ${balances[-1] if balances else 10.00:.2f}")

if __name__ == "__main__":
    create_performance_chart_text()