"""
NVIDIA NIM LLM Client - OpenAI-compatible API
Free tier: build.nvidia.com (no credit card required)
Models: Llama-3.1, Mistral, Nemotron, Gemma, DeepSeek, Qwen
"""
import os
import requests
import json
from typing import Optional, Dict, Any, List

class NVIDIAClient:
    """OpenAI-compatible client for NVIDIA NIM APIs"""
    
    # Popular free models on NVIDIA NIM
    MODELS = {
        'llama3-8b': 'meta/llama-3.1-8b-instruct',
        'llama3-70b': 'meta/llama-3.1-70b-instruct',
        'mistral-7b': 'mistralai/mistral-7b-instruct-v0.3',
        'nemotron-70b': 'nvidia/nemotron-4-340b-instruct',  # Actually 340B but free
        'gemma-7b': 'google/gemma-7b-it',
        'deepseek-7b': 'deepseek-ai/deepseek-coder-v2-lite-instruct',
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NVIDIA_API_KEY')
        self.base_url = "https://integrate.api.nvidia.com/v1"  # Correct NIM endpoint
        
    def set_api_key(self, api_key: str):
        """Set API key (get free from build.nvidia.com)"""
        self.api_key = api_key
        
    def chat(self, 
             messages: List[Dict[str, str]], 
             model: str = 'llama3-8b',
             temperature: float = 0.3,
             max_tokens: int = 500) -> Optional[str]:
        """
        Send chat request to NVIDIA NIM (OpenAI-compatible)
        
        Args:
            messages: List of {role: 'user'/'system', content: '...'}
            model: Model key from MODELS dict
            temperature: Randomness (0.0-1.0)
            max_tokens: Max response length
            
        Returns:
            Response text or None if failed
        """
        if not self.api_key:
            print("Warning: No NVIDIA API key. Get free key from build.nvidia.com")
            return None
        
        model_id = self.MODELS.get(model, model)
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"NVIDIA API Error: {e}")
            return None
    
    def analyze_market(self, market_question: str, yes_price: float) -> Dict[str, Any]:
        """
        Use LLM to analyze a market and provide trading signal
        
        Returns:
            Dict with: action ('buy'/'sell'), confidence (0-1), reasoning (str)
        """
        messages = [
            {
                "role": "system",
                "content": """You are a professional prediction market trader. 
Analyze the market and provide a trading decision.
Output JSON only: {"action": "buy" or "sell", "confidence": 0.0-1.0, "estimated_prob": 0.0-1.0, "reasoning": "brief explanation"}"""
            },
            {
                "role": "user", 
                "content": f"Market: {market_question}\nCurrent YES price: ${yes_price:.4f}\nWhat's your trading decision?"
            }
        ]
        
        response = self.chat(messages, model='llama3-8b', temperature=0.2)
        
        if not response:
            return {"action": "skip", "confidence": 0.0, "estimated_prob": yes_price, "reasoning": "API failed"}
        
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except:
            pass
        
        # Fallback: parse text response
        action = 'buy' if 'buy' in response.lower() else 'sell'
        return {"action": action, "confidence": 0.6, "estimated_prob": yes_price, "reasoning": response[:100]}


class TradingAgent:
    """Base class for LLM-powered trading agents"""
    
    def __init__(self, name: str, nvidia_client: NVIDIAClient, model: str = 'llama3-8b'):
        self.name = name
        self.client = nvidia_client
        self.model = model
        self.history = []
    
    def think(self, context: str) -> str:
        """Use LLM to analyze and respond"""
        messages = [
            {"role": "system", "content": f"You are {self.name}, a trading agent."},
            {"role": "user", "content": context}
        ]
        return self.client.chat(messages, model=self.model) or "No response"


class MarketAnalystAgent(TradingAgent):
    """Analyzes markets using LLM to find trading opportunities"""
    
    def __init__(self, nvidia_client: NVIDIAClient):
        super().__init__("Market Analyst", nvidia_client, model='llama3-8b')
    
    def analyze(self, market_data: Dict) -> Dict[str, Any]:
        """Analyze a single market"""
        return self.client.analyze_market(
            market_data.get('question', 'Unknown market'),
            market_data['yes_price']
        )


class RiskManagerAgent(TradingAgent):
    """Manages position sizing and risk using LLM"""
    
    def __init__(self, nvidia_client: NVIDIAClient):
        super().__init__("Risk Manager", nvidia_client, model='llama3-8b')
    
    def calculate_position_size(self, balance: float, edge: float, confidence: float) -> float:
        """Use LLM to calculate safe position size"""
        context = f"""Current balance: ${balance:.2f}
Trading edge: {edge*100:.1f}%
Confidence: {confidence*100:.0f}%
What percentage of balance should I risk? Reply with just the number (e.g., 2 for 2%)."""
        
        response = self.think(context)
        
        try:
            # Extract number from response
            import re
            numbers = re.findall(r'\d+\.?\d*', response)
            if numbers:
                pct = float(numbers[0])
                return max(0.5, min(balance * pct / 100, balance * 0.05))
        except:
            pass
        
        # Fallback: quarter Kelly
        return max(0.5, balance * 0.02)


class StrategyAgent(TradingAgent):
    """Decides overall strategy using LLM"""
    
    def __init__(self, nvidia_client: NVIDIAClient):
        super().__init__("Strategy Agent", nvidia_client, model='llama3-70b')
    
    def should_trade(self, market_data: Dict, recent_performance: Dict) -> bool:
        """Decide if we should trade this market"""
        context = f"""Market: {market_data.get('question', '')[:50]}
YES price: ${market_data.get('yes_price', 0):.4f}
Recent win rate: {recent_performance.get('win_rate', 0)*100:.0f}%
Recent P&L: ${recent_performance.get('pnl', 0):.2f}
Should we trade this market? Reply YES or NO."""
        
        response = self.think(context)
        return 'yes' in response.lower()


def main():
    """Test NVIDIA client"""
    client = NVIDIAClient()
    
    # Check if API key is set
    if not client.api_key:
        print("=" * 50)
        print("NVIDIA API Key Required (FREE)")
        print("=" * 50)
        print("1. Go to: https://build.nvidia.com")
        print("2. Sign up (no credit card required)")
        print("3. Get API key from dashboard")
        print("4. Add to .env: NVIDIA_API_KEY=your_key_here")
        print("=" * 50)
        return
    
    # Test market analysis
    analyst = MarketAnalystAgent(client)
    result = analyst.analyze({
        'question': 'Will Bitcoin exceed $100k by end of 2026?',
        'yes_price': 0.45
    })
    print(f"Analysis: {result}")


if __name__ == "__main__":
    main()
