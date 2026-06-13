const { GraphQLClient, gql } = require('graphql-request');
const fs = require('fs');
const dotenv = require('dotenv');

dotenv.config();

const API_URL = process.env.POLYMARKET_API_URL;
const API_KEY = process.env.POLYMARKET_API_KEY;

const client = new GraphQLClient(API_URL, {
 headers: {
 "Content-Type": "application/json",
 ...(API_KEY && { "Authorization": `Bearer ${API_KEY}` }),
 },
});

// GraphQL query to fetch markets
const query = gql`
 query Markets($limit: Int) {
 markets(limit: $limit) {
 id
 question
 description
 active
 closed
 endDate
 conditionId
 outcomes {
 price
 name
 }
 volume
 }
 }
`;

async function fetchMarkets() {
 try {
 console.log("Fetching Polymarket markets...")
 const data = await client.request(query, { limit: 10 }); // Fetch 10 markets

 // Save to JSON file for LLM training
 fs.writeFileSync('markets_data.json', JSON.stringify(data.markets, null, 2));
 console.log("✅ Markets saved to markets_data.json");
 } catch (error) {
 console.error("❌ Error fetching markets:", error.message);
 }
}

fetchMarkets();