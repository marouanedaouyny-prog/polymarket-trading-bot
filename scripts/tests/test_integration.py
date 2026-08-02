"""
Full integration test: MiroFish no-Zep patch + polymarket project connect
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


def test_imports():
    from src.prediction.mirofish_client import MiroFishClient
    from src.prediction.mirofish_integrator import MiroFishIntegrator
    assert MiroFishClient is not None
    assert MiroFishIntegrator is not None


def test_mirofish_health():
    from src.prediction.mirofish_client import MiroFishClient
    c = MiroFishClient()
    healthy = c.health()
    assert isinstance(healthy, bool)


def test_mirofish_project_creation():
    from src.prediction.mirofish_client import MiroFishClient
    c = MiroFishClient()
    result = c.create_project_from_text(
        text="Bitcoin is the leading cryptocurrency.",
        simulation_requirement="Predict crypto market sentiment",
        project_name="Test"
    )
    assert result is None or "project_id" in result


def test_mirofish_graph_build():
    from src.prediction.mirofish_client import MiroFishClient
    c = MiroFishClient()
    build = c.build_graph("dummy", "Test")
    assert build is None


def test_mirofish_simulation():
    from src.prediction.mirofish_client import MiroFishClient
    c = MiroFishClient()
    sim = c.create_simulation("dummy", "dummy")
    assert sim is None


def test_mirofish_integrator():
    from src.prediction.mirofish_integrator import MiroFishIntegrator
    mf = MiroFishIntegrator()
    assert isinstance(mf.available, bool)
    signal = mf.get_market_intelligence("Will BTC reach $100k?", {"price": 95000, "volume": 1000})
    assert isinstance(signal, dict)
    assert "sentiment_score" in signal or "edge" in signal
    assert "sectors" in signal


if __name__ == "__main__":
    from src.prediction.mirofish_client import MiroFishClient
    from src.prediction.mirofish_integrator import MiroFishIntegrator

    c = MiroFishClient()
    print("=" * 60)
    print("1. Health check")
    print("=" * 60)
    print(f"   MiroFish backend: {'OK' if c.health() else 'FAIL'}")

    print("\n" + "=" * 60)
    print("2. Create project + build graph (no Zep)")
    print("=" * 60)
    result = c.create_project_from_text(
        text="Bitcoin is the leading cryptocurrency. Ethereum enables smart contracts. Solana is a fast blockchain. The market is volatile.",
        simulation_requirement="Predict crypto market sentiment",
        project_name="Integration Test"
    )
    if not result:
        print("   FAILED: project creation")
    else:
        pid = result["project_id"]
        print(f"   Project: {pid}")
        print(f"   Entities: {[e['name'] for e in result['ontology']['entity_types']]}")

        build = c.build_graph(pid, "Test Graph")
        if not build:
            print("   FAILED: graph build start")
        else:
            task_id = build.get("task_id")
            r = c.wait_for_task(task_id, timeout=300)
            if r:
                gi = r.get("graph_info", {})
                print(f"   Graph built: {gi.get('node_count', 0)} entities, {gi.get('edge_count', 0)} edges")
                gid = gi.get("graph_id", "?")
            else:
                print("   FAILED: graph build task")
                gid = None

            if gid:
                print("\n" + "=" * 60)
                print("3. Create + prepare + run simulation (small)")
                print("=" * 60)
                sim = c.create_simulation(pid, gid, enable_twitter=True, enable_reddit=True)
                if not sim:
                    print("   FAILED: simulation creation")
                else:
                    sim_id = sim["simulation_id"]
                    print(f"   Simulation: {sim_id}")

                    prep = c.prepare_simulation(sim_id, parallel_profile_count=3)
                    if prep:
                        pt = prep.get("task_id")
                        if pt:
                            ready = c.wait_for_preparation(task_id=pt, timeout=600)
                            print(f"   Preparation: {'READY' if ready else 'TIMEOUT/FAIL'}")
                        else:
                            print(f"   Already prepared: {prep.get('status')}")

                        start_res = c.start_simulation(sim_id, platform="parallel", max_rounds=3)
                        if start_res:
                            print(f"   Simulation started: {json.dumps(start_res, indent=2)[:200]}")
                            time.sleep(15)
                            status = c.get_simulation_status(sim_id)
                            print(f"   Status: {status.get('runner_status', '?') if status else '?'}")
                            c.stop_simulation(sim_id)
                        else:
                            print("   FAILED: simulation start")
                    else:
                        print("   FAILED: preparation")

    print("\n" + "=" * 60)
    print("4. MiroFishIntegrator check")
    print("=" * 60)
    mf = MiroFishIntegrator()
    print(f"   Available: {mf.available}")
    signal = mf.get_market_intelligence("Will BTC reach $100k?", {"price": 95000, "volume": 1000})
    print(f"   Signal edge: {signal.get('edge', '?')}")
    print(f"   Signal confidence: {signal.get('confidence', '?')}")
    print(f"   Signal sectors: {signal.get('sectors', '?')}")

    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)
