const axios = require('axios');
const fs = require('fs');

async function fetchPublicMarkets() {
 try {
 console.log("Fetching public Polymarket data...")
 const response = await axios.get('https://clob.polymarket.com/markets');

 // Save to JSON file for LLM training
 fs.writeFileSync('public_markets.json', JSON.stringify(response.data, null, 2));
 console.log("✅ Public markets saved to public_markets.json");
 } catch (error) {
 console.error("❌ Error fetching public markets:", error.message);
 }
}

fetchPublicMarkets();