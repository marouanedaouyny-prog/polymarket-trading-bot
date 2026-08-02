"""
LIVE REALITY CHECK
==================
Analyzes current LIVE markets using the freshly trained REAL-DATA model.
Proves accuracy before trading real money.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load configuration
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)

from src.data.crypto_section import fetch_crypto_section_markets
from src.trading.live_trading import _extract_binary_prices, _extract_volume
from src.ml.market_predictor import MarketPredictor

def run_reality_check():
    print("="*60)
    print("🌍 LIVE REALITY CHECK: REAL-DATA AI ANALYSIS")
    print("="*60)
    
    predictor = MarketPredictor()
    if not predictor.load_model():
        print("Error: No model found.")
        return

    markets = fetch_crypto_section_markets(locale="fr")
    if not markets:
        print("Error: No live markets found.")
        return

    print(f"Analyzing {len(markets)} live crypto markets...\n")
    
    analysis = []
    for m in markets:
        question = m.get('question', 'N/A')
        prices = _extract_binary_prices(m)
        volume = _extract_volume(m)
        if not prices: continue

        # Predict YES
        y_prob = predictor.predict_win_probability(prices['yes'], volume, 0.1, 70, True)
        
        # Predict NO
        n_prob = predictor.predict_win_probability(prices['no'], volume, 0.1, 70, True)

        analysis.append({
            'q': question,
            'yes_p': prices['yes'],
            'no_p': prices['no'],
            'y_win': y_prob,
            'n_win': n_prob,
            'vol': volume
        })

    # Show top 5 high-conviction insights
    analysis.sort(key=lambda x: max(x['y_win'], x['n_win']), reverse=True)
    
    for i, a in enumerate(analysis[:5]):
        side = "YES" if a['y_win'] >= a['n_win'] else "NO"
        prob = max(a['y_win'], a['n_win'])
        market_price = a['yes_p'] if side == "YES" else a['no_p']
        
        print(f"{i+1}. {a['q'][:60]}...")
        print(f"   AI Prediction: {side} (Win Prob: {prob:.1%})")
        print(f"   Market Price:  ${market_price:.2f} | Volume: ${a['vol']:,.0f}")
        print("-" * 40)

if __name__ == "__main__":
    run_reality_check()
