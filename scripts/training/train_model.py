import json
import csv
from collections import defaultdict

class SimpleModelTrainer:
    def __init__(self):
        self.weights = {
            'price_weight': 0.5,
            'edge_weight': 0.3,
            'confidence_weight': 0.2,
        }
        self.trade_history = []

    def load_training_data(self, filepath='data/results/training_trades.csv'):
        trades = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append({
                    'price': float(row['price']),
                    'edge': float(row['edge']),
                    'confidence': int(row['confidence']),
                    'won': row['won'] == 'True',
                    'payout': float(row['payout'])
                })
        self.trade_history = trades
        return trades

    def train(self, iterations=100):
        print(f"Training model on {len(self.trade_history)} trades...")

        # Analyze winning patterns
        wins = [t for t in self.trade_history if t['won']]
        losses = [t for t in self.trade_history if not t['won']]

        print(f"Wins: {len(wins)}, Losses: {len(losses)}")

        # Calculate average characteristics for wins vs losses
        win_avg_price = sum(t['price'] for t in wins) / len(wins) if wins else 0.5
        loss_avg_price = sum(t['price'] for t in losses) / len(losses) if losses else 0.5

        win_avg_edge = sum(t['edge'] for t in wins) / len(wins) if wins else 0
        loss_avg_edge = sum(t['edge'] for t in losses) / len(losses) if losses else 0

        win_avg_conf = sum(t['confidence'] for t in wins) / len(wins) if wins else 0
        loss_avg_conf = sum(t['confidence'] for t in losses) / len(losses) if losses else 0

        print(f"\nWin patterns: price={win_avg_price:.3f}, edge={win_avg_edge:.3f}, conf={win_avg_conf:.0f}")
        print(f"Loss patterns: price={loss_avg_price:.3f}, edge={loss_avg_edge:.3f}, conf={loss_avg_conf:.0f}")

        # Update weights based on what predicts wins
        price_diff = win_avg_price - loss_avg_price
        edge_diff = win_avg_edge - loss_avg_edge
        conf_diff = win_avg_conf - loss_avg_conf

        # Normalize and update weights
        total_diff = abs(price_diff) + abs(edge_diff) + abs(conf_diff)
        if total_diff > 0:
            self.weights['price_weight'] = 0.3 + 0.4 * (abs(price_diff) / total_diff)
            self.weights['edge_weight'] = 0.2 + 0.4 * (abs(edge_diff) / total_diff)
            self.weights['confidence_weight'] = 0.2 + 0.4 * (abs(conf_diff) / total_diff)

        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}

        # Find optimal thresholds
        sorted_by_edge = sorted(self.trade_history, key=lambda x: x['edge'], reverse=True)
        for threshold in [0.1, 0.15, 0.2, 0.25, 0.3]:
            subset = [t for t in sorted_by_edge if t['edge'] >= threshold]
            if subset:
                win_rate = sum(1 for t in subset if t['won']) / len(subset)
                avg_payout = sum(t['payout'] for t in subset) / len(subset)
                print(f"Edge >= {threshold}: win_rate={win_rate:.1%}, avg_payout=${avg_payout:.2f}")

        return self.weights

    def predict(self, price, edge, confidence):
        score = (
            self.weights['price_weight'] * (1 - abs(price - 0.5) * 2) +
            self.weights['edge_weight'] * min(edge, 1.0) +
            self.weights['confidence_weight'] * (confidence / 100)
        )
        return score

    def save_model(self, filepath='data/results/trained_model.json'):
        model_data = {
            'weights': self.weights,
            'trained_on_trades': len(self.trade_history),
            'recommendations': {
                'min_edge': 0.03,
                'min_confidence': 50,
                'max_position_pct': 0.20
            }
        }
        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)
        print(f"Model saved to {filepath}")
        return model_data


if __name__ == "__main__":
    trainer = SimpleModelTrainer()
    trades = trainer.load_training_data()
    print(f"Loaded {len(trades)} trades from training data")

    weights = trainer.train()
    print(f"\nOptimized weights: {weights}")

    model = trainer.save_model()

    # Test predictions
    print("\nTest predictions:")
    test_cases = [
        (0.3, 0.2, 60),
        (0.7, 0.4, 80),
        (0.5, 0.1, 40),
        (0.2, 0.35, 70),
    ]
    for price, edge, conf in test_cases:
        score = trainer.predict(price, edge, conf)
        action = "TRADE" if score > 0.5 else "SKIP"
        print(f"  price={price}, edge={edge}, conf={conf} -> score={score:.2f} ({action})")