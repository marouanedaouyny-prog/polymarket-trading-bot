"""
Advisory risk parameter generator — rule-based (NOT an LLM despite the name).

This module produces suggested risk parameters (position size %, stop loss,
take profit, min edge) as a heuristic pre-filter only. It is NOT execution
authority: position_size_pct is an advisory cap that must be re-validated by
DynamicRiskManager / ApprovalGate before any order reaches the CLOB adapter.
Live execution never sizes trades from this module's output alone.
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class RiskRecommendation:
    position_size_pct: float  # Recommended position size %
    max_position_pct: float   # Max position allowed
    min_edge: float          # Minimum edge threshold
    stop_loss_pct: float     # Stop loss percentage
    take_profit_pct: float   # Take profit target
    confidence: float         # LLM confidence 0-1
    reasoning: str            # Why this recommendation


class LLMRiskAdvisor:
    """Rule-based risk advisor (advisory only — not execution authority)."""
    def __init__(self):
        self.last_recommendation: Optional[RiskRecommendation] = None
        self.cache_duration = 300  # 5 minutes cache
        self.last_update = None
        
    def get_recommendation(self, market_data: Dict) -> RiskRecommendation:
        """Get LLM-based risk recommendation for a market"""
        # Check cache
        if self._is_cache_valid():
            return self.last_recommendation
        
        # Generate recommendation based on market conditions
        recommendation = self._generate_recommendation(market_data)
        
        # Cache result
        self.last_recommendation = recommendation
        self.last_update = datetime.now()
        
        return recommendation
    
    def _is_cache_valid(self) -> bool:
        """Check if cached recommendation is still valid"""
        if not self.last_update or not self.last_recommendation:
            return False
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed < self.cache_duration
    
    def _generate_recommendation(self, market_data: Dict) -> RiskRecommendation:
        """Generate risk recommendation based on market analysis"""
        
        # Extract market features
        price = market_data.get('price', 0.5)
        volume = market_data.get('volume', 0)
        sector = market_data.get('sector', 'other')
        
        # Analyze conditions and determine risk parameters
        if price <= 0.05 and volume > 50000:
            # Low price + high volume = high confidence
            position_pct = 0.15
            min_edge = 0.70
            stop_loss = 0.50
            take_profit = 2.0
            confidence = 0.92
            reasoning = "Low price + high volume = high confidence"
            
        elif price <= 0.15 and volume > 20000:
            # Medium price + decent volume
            position_pct = 0.12
            min_edge = 0.75
            stop_loss = 0.40
            take_profit = 1.5
            confidence = 0.85
            reasoning = "Medium price with decent volume"
            
        elif price <= 0.30:
            # Higher price = more conservative
            position_pct = 0.08
            min_edge = 0.80
            stop_loss = 0.30
            take_profit = 1.2
            confidence = 0.78
            reasoning = "Higher price requires more conservative position"
            
        else:
            # Very high price or low volume = very conservative
            position_pct = 0.05
            min_edge = 0.85
            stop_loss = 0.25
            take_profit = 1.0
            confidence = 0.70
            reasoning = "High price or low volume - reduced exposure"
        
        # Sector adjustments
        if sector in ['crypto', 'bitcoin']:
            # Crypto is more volatile - reduce position
            position_pct *= 0.8
            min_edge += 0.03
            reasoning += ", adjusted for crypto volatility"
        elif sector in ['politics']:
            # Politics can be unpredictable
            position_pct *= 0.9
            reasoning += ", adjusted for political uncertainty"
        
        return RiskRecommendation(
            position_size_pct=position_pct,
            max_position_pct=0.15,  # Hard cap
            min_edge=min_edge,
            stop_loss_pct=stop_loss,
            take_profit_pct=take_profit,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def analyze_market_sentiment(self, markets: List[Dict]) -> Dict:
        """Analyze overall market sentiment across multiple markets"""
        
        total_markets = len(markets)
        if total_markets == 0:
            return {'sentiment': 0.5, 'volatility': 'medium', 'recommendation': 'neutral'}
        
        # Calculate average price and volume
        avg_price = sum(m.get('price', 0.5) for m in markets) / total_markets
        avg_volume = sum(m.get('volume', 0) for m in markets) / total_markets
        
        # Determine sentiment
        if avg_price < 0.15 and avg_volume > 30000:
            sentiment = 0.75
            volatility = 'low'
            overall = 'bullish'
        elif avg_price < 0.30:
            sentiment = 0.55
            volatility = 'medium'
            overall = 'neutral'
        else:
            sentiment = 0.40
            volatility = 'high'
            overall = 'cautious'
        
        return {
            'sentiment': sentiment,
            'volatility': volatility,
            'avg_price': avg_price,
            'avg_volume': avg_volume,
            'overall': overall,
            'market_count': total_markets
        }
    
    def get_global_settings(self, market_sentiment: Dict) -> Dict:
        """Get global risk settings based on market sentiment"""
        
        sentiment = market_sentiment['sentiment']
        volatility = market_sentiment['volatility']
        
        if volatility == 'low' and sentiment > 0.6:
            # Bullish, low volatility - increase exposure
            return {
                'max_positions': 10,
                'session_risk_pct': 0.20,
                'stop_loss_default': 0.40,
                'take_profit_default': 1.5
            }
        elif volatility == 'high' or sentiment < 0.4:
            # Bearish or high volatility - reduce exposure
            return {
                'max_positions': 5,
                'session_risk_pct': 0.10,
                'stop_loss_default': 0.25,
                'take_profit_default': 1.0
            }
        else:
            # Normal conditions
            return {
                'max_positions': 7,
                'session_risk_pct': 0.15,
                'stop_loss_default': 0.35,
                'take_profit_default': 1.2
            }


def get_llm_risk_recommendation(market: Dict) -> RiskRecommendation:
    """Convenience function to get risk recommendation"""
    advisor = LLMRiskAdvisor()
    return advisor.get_recommendation(market)


def get_market_sentiment(markets: List[Dict]) -> Dict:
    """Convenience function to analyze market sentiment"""
    advisor = LLMRiskAdvisor()
    return advisor.analyze_market_sentiment(markets)


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("LLM RISK ADVISOR TEST")
    print("=" * 60)
    
    advisor = LLMRiskAdvisor()
    
    # Test cases
    test_markets = [
        {'price': 0.03, 'volume': 100000, 'sector': 'crypto'},
        {'price': 0.15, 'volume': 25000, 'sector': 'politics'},
        {'price': 0.35, 'volume': 5000, 'sector': 'sports'},
    ]
    
    print("\n[1] Individual Market Recommendations:")
    for i, m in enumerate(test_markets):
        rec = advisor.get_recommendation(m)
        print(f"\n   Market {i+1}: price=${m['price']}, vol={m['volume']}, sector={m['sector']}")
        print(f"   -> Position: {rec.position_size_pct:.1%}, Min Edge: {rec.min_edge:.0%}")
        print(f"   -> Stop Loss: {rec.stop_loss_pct:.0%}, Take Profit: {rec.take_profit_pct:.1f}x")
        print(f"   -> Confidence: {rec.confidence:.0%}")
        print(f"   -> Reason: {rec.reasoning}")
    
    print("\n[2] Market Sentiment Analysis:")
    sentiment = advisor.analyze_market_sentiment(test_markets)
    print(f"   Sentiment: {sentiment['sentiment']:.0%}")
    print(f"   Volatility: {sentiment['volatility']}")
    print(f"   Overall: {sentiment['overall']}")
    
    print("\n[3] Global Risk Settings:")
    settings = advisor.get_global_settings(sentiment)
    for key, value in settings.items():
        print(f"   {key}: {value}")
    
    print("\n[OK] LLM Risk Advisor working!")
    print("\nNote: This is rule-based simulation.")
    print("For real LLM, integrate with OpenAI/Anthropic API.")