const fs = require('fs');

// Load public markets data
const markets = JSON.parse(fs.readFileSync('public_markets.json', 'utf8'));

// Demo balance
let balance = 10.0;

// Simulate a trade
function simulateTrade(marketId, outcome, amount) {
 const market = markets.find(m => m.id === marketId);
 if (!market) {
 console.log("❌ Market not found.");
 return;
 }

 const outcomeData = market.outcomes.find(o => o.name === outcome);
 if (!outcomeData) {
 console.log("❌ Outcome not found.");
 return;
 }

 // Simulate trade result (random for demo)
 const win = Math.random() < outcomeData.price; // Price = probability of winning
 const payout = win ? amount / outcomeData.price : 0;
 const profit = win ? payout - amount : -amount;

 // Update balance
 balance += profit;

 // Log trade
 const tradeLog = {
 timestamp: new Date().toISOString(),
 marketId,
 question: market.question,
 outcome,
 amount,
 price: outcomeData.price,
 win,
 profit,
 balance,
 };

 // Save trade to JSON for LLM training
 const trades = JSON.parse(fs.readFileSync('trade_logs.json', 'utf8') || '[]');
 trades.push(tradeLog);
 fs.writeFileSync('trade_logs.json', JSON.stringify(trades, null, 2));

 console.log("📊 Trade Simulated:", tradeLog);
}

// Example usage
console.log("Available Markets:");
markets.slice(0, 5).forEach(m => {
 console.log(`- ${m.id}: ${m.question} (${m.outcomes.map(o => `${o.name}: ${o.price}`).join(', ')})`);
});

// Simulate a trade (replace marketId and outcome with your choices)
// simulateTrade("0x123...", "Yes", 1.0);