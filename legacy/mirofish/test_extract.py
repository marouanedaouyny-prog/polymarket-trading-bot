import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from app.services import local_graph_store as store

# Test entity extraction
text = "Bitcoin is the leading cryptocurrency by market cap. Ethereum enables smart contracts. Solana is a high-performance blockchain."
ontology = {
    "entity_types": [
        {"name": "Cryptocurrency", "description": "A digital currency"},
        {"name": "BlockchainPlatform", "description": "A blockchain network"},
        {"name": "Investor", "description": "Someone who invests"},
        {"name": "Person", "description": "Any person"},
        {"name": "Organization", "description": "Any organization"},
    ],
    "edge_types": [
        {"name": "INVESTS_IN", "description": "Invests in"},
    ]
}

result = store.extract_entities_from_text(text, ontology)
print("Entities found:", len(result.get("entities", [])))
for e in result.get("entities", []):
    print(f"  {e.get('name')} ({e.get('entity_type')}): {e.get('summary', '')[:80]}")
print("Edges found:", len(result.get("edges", [])))
for edge in result.get("edges", []):
    print(f"  {edge.get('source')} -> {edge.get('target')}: {edge.get('relation_type')}")
