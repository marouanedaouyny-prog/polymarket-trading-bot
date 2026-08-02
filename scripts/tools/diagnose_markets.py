"""
Diagnostic script to see why the bot is not trading.
Prints analysis for all current crypto markets.
"""
import os
import sys
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
from src.risk.dynamic_risk import DynamicRiskManager

def diagnose():
    predictor = MarketPredictor()
    predictor.load_model()
    
    risk_config = {
        'max_position_pct': 0.12,
        'min_edge': 0.60,
        'min_confidence': 60,
    }
    risk_manager = DynamicRiskManager(risk_config)
    
    print(f"--- DIAGNOSING CRYPTO MARKETS ---")
    markets = fetch_crypto_section_markets(locale="fr")
    print(f"Found {len(markets)} markets in section.")
    
    if not markets:
        print("ERROR: Could not fetch any markets. Scraper might be blocked or page layout changed.")
        return

    approved_count = 0
    for m in markets:
        question = m.get('question', 'N/A')
        prices = _extract_binary_prices(m)
        volume = _extract_volume(m)
        
        if not prices:
            print(f"SKIP: {question[:40]}... (No binary prices)")
            continue
            
        price = prices['yes']
        
        # Analyze
        edge = 0.90 if price < 0.05 else 0.85 if price < 0.10 else 0.80
        confidence = min(max(volume / 50000.0, 0.0), 1.0) * 100
        
        if predictor.model:
            try:
                edge = predictor.predict_win_probability(price, volume, edge/100, confidence, True)
            except: pass
            
        # Check filters
        reasons = []
        if not (0.01 <= price <= 0.40): reasons.append(f"Price ${price:.2f} out of range (0.01-0.40)")
        if volume < 10000: reasons.append(f"Volume ${volume:,.0f} too low (<10k)")
        
        approved, risk_reason = risk_manager.should_trade(edge, confidence, 100)
        if not approved:
            reasons.append(f"Risk: {risk_reason} (Edge:{edge:.1%}, Conf:{confidence:.1f})")
            
        if not reasons:
            print(f"✅ APPROVED: {question[:50]}...")
            print(f"   Price: ${price:.2f} | Volume: ${volume:,.0f} | Edge: {edge:.1%} | Conf: {confidence:.1f}")
            approved_count += 1
        else:
            print(f"❌ REJECTED: {question[:50]}...")
            print(f"   Reasons: {', '.join(reasons)}")

    print(f"\nSummary: {approved_count} approved out of {len(markets)} total.")

if __name__ == "__main__":
    diagnose()
