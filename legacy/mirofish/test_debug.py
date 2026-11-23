import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from app.services import local_graph_store as store

base = os.path.join("backend", "app", "uploads", "local_graphs")
if os.path.exists(base):
    for gid in os.listdir(base):
        meta = store.get_graph_meta(gid)
        if meta:
            print(f"Graph: {gid}")
            print(f"  Name: {meta.get('name')}")
            print(f"  Entity count: {meta.get('entity_count', 0)}")
            entities = store.get_all_entities(gid)
            print(f"  Entities ({len(entities)}):")
            for e in entities[:5]:
                print(f"    - {e.get('name')} ({e.get('entity_type')})")
