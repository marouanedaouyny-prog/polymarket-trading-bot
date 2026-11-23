import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))

from app.services.local_graph_store import extract_entities_from_text

text = "Bitcoin is the leading cryptocurrency. Ethereum enables smart contracts."
ontology = {
    "entity_types": [
        {"name": "Cryptocurrency", "description": "A digital currency"},
        {"name": "BlockchainPlatform", "description": "A blockchain network"},
        {"name": "Person", "description": "Any person"},
        {"name": "Organization", "description": "Any organization"},
    ],
    "edge_types": [{"name": "BUILT_ON", "description": "Built on blockchain"}],
}

result = extract_entities_from_text(text, ontology)
print("Entities:", len(result.get("entities", [])))
for e in result.get("entities", []):
    print(f"  - {e.get('name')} ({e.get('entity_type')})")
print("Edges:", len(result.get("edges", [])))
