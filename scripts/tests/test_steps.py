import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from src.prediction.mirofish_client import MiroFishClient

c = MiroFishClient(timeout=120)
print("Connected to MiroFish:", c.health())

result = c.create_project_from_text(
    text="Bitcoin is the leading cryptocurrency. Ethereum enables smart contracts. Solana is a fast blockchain.",
    simulation_requirement="Predict crypto market sentiment",
    project_name="Test"
)
if not result:
    print("FAIL: project creation")
    sys.exit(1)
pid = result["project_id"]
print(f"Project: {pid}")
print(f"Entities: {len(result['ontology']['entity_types'])}")

build = c.build_graph(pid, "Test")
if not build:
    print("FAIL: graph build start")
    sys.exit(1)
task_id = build["task_id"]
print(f"Build task: {task_id}")

r = c.wait_for_task(task_id, timeout=300)
if r:
    gi = r.get("graph_info", {})
    nc = gi.get("node_count", 0)
    gid = gi.get("graph_id", "?")
    print(f"Graph built: {nc} entities, graph_id={gid}")
else:
    print("FAIL: graph build task")
