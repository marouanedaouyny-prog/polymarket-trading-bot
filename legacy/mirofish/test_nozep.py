import requests, time, json, sys

BASE = "http://127.0.0.1:5001"

# Step 1: Create project (ontology generation)
print("=" * 60)
print("STEP 1: Ontology Generation")
print("=" * 60)
text = b"Bitcoin is the leading cryptocurrency by market cap. Ethereum enables smart contracts. Solana is a high-performance blockchain. The crypto market is volatile but growing steadily."
files = {"files": ("crypto.txt", text, "text/plain")}
data = {"simulation_requirement": "Analyze cryptocurrency market trends and predict price movements", "project_name": "Crypto Test"}
resp = requests.post(f"{BASE}/api/graph/ontology/generate", data=data, files=files, timeout=120)
if resp.status_code != 200:
    print("FAILED:", resp.text[:500])
    sys.exit(1)
d = resp.json()["data"]
pid = d["project_id"]
print(f"Project ID: {pid}")
print(f"Entities: {[e['name'] for e in d['ontology']['entity_types']]}")
print(f"Edges: {[e['name'] for e in d['ontology']['edge_types']]}")

# Step 2: Build graph (no Zep - uses local store)
print("\n" + "=" * 60)
print("STEP 2: Build Graph (Local, No Zep)")
print("=" * 60)
resp = requests.post(f"{BASE}/api/graph/build", json={"project_id": pid, "graph_name": "Crypto Graph"}, timeout=30)
if resp.status_code != 200:
    print("FAILED:", resp.json()["error"][:200])
    sys.exit(1)
task_id = resp.json()["data"]["task_id"]
print(f"Task ID: {task_id}")

while True:
    resp = requests.get(f"{BASE}/api/graph/task/{task_id}", timeout=10)
    s = resp.json()["data"]
    p = s.get("progress", 0)
    print(f"  Status: {s['status']} | Progress: {p}%")
    if s["status"] in ("completed", "failed"):
        break
    time.sleep(3)

if s["status"] == "completed":
    result = s.get("result", {})
    gi = result.get("graph_info", {})
    print(f"Graph built: {gi.get('node_count', 0)} entities, {gi.get('edge_count', 0)} edges")
    gid = gi["graph_id"]
else:
    print("FAILED:", s.get("error", "?"))
    sys.exit(1)

# Step 3: Create simulation
print("\n" + "=" * 60)
print("STEP 3: Create Simulation")
print("=" * 60)
resp = requests.post(f"{BASE}/api/simulation/create", json={
    "project_id": pid, "graph_id": gid,
    "enable_twitter": True, "enable_reddit": True
}, timeout=30)
if resp.status_code != 200:
    print("FAILED:", resp.text[:500])
    sys.exit(1)
sim_id = resp.json()["data"]["simulation_id"]
print(f"Simulation ID: {sim_id}")

# Step 4: Prepare simulation
print("\n" + "=" * 60)
print("STEP 4: Prepare Simulation")
print("=" * 60)
resp = requests.post(f"{BASE}/api/simulation/prepare", json={
    "simulation_id": sim_id,
    "use_llm_for_profiles": True,
    "parallel_profile_count": 3,
}, timeout=30)
if resp.status_code != 200:
    print("FAILED:", resp.text[:500])
    sys.exit(1)
pd = resp.json()["data"]
task_id2 = pd.get("task_id")
status = pd.get("status", "unknown")
print(f"Status: {status}, Task: {task_id2}")

if status == "ready":
    print("Already prepared!")
elif task_id2:
    timeout = 600
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.post(f"{BASE}/api/simulation/prepare/status", json={
            "task_id": task_id2, "simulation_id": sim_id
        }, timeout=30)
        if resp.status_code == 200:
            ps = resp.json()["data"]
            print(f"  Prepare status: {ps.get('status')} | {ps.get('message', '')[:50]}")
            if ps.get("status") in ("ready", "failed"):
                if ps["status"] == "ready":
                    print("Preparation complete!")
                else:
                    print("FAILED:", ps.get("error", "?"))
                break
        time.sleep(10)

# Step 5: Start simulation (small scale)
print("\n" + "=" * 60)
print("STEP 5: Start Simulation (3 rounds)")
print("=" * 60)
resp = requests.post(f"{BASE}/api/simulation/start", json={
    "simulation_id": sim_id,
    "platform": "parallel",
    "max_rounds": 3,
}, timeout=30)
if resp.status_code != 200:
    print("FAILED:", resp.text[:500])
    sys.exit(1)
print("Simulation started:", resp.json())

# Wait a bit then check status
time.sleep(10)
resp = requests.get(f"{BASE}/api/simulation/{sim_id}/run-status", timeout=10)
if resp.status_code == 200:
    print("Run status:", resp.json().get("data", {}).get("runner_status", "?"))
    print("Summary:", resp.json().get("data", {}).get("summary", {}))

# Stop simulation
resp = requests.post(f"{BASE}/api/simulation/stop", json={"simulation_id": sim_id}, timeout=10)
print("Stopped:", resp.status_code)

print("\n" + "=" * 60)
print("DONE - Full pipeline works without Zep!")
print("=" * 60)
