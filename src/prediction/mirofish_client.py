"""
Low-level REST client for MiroFish API.
Handles all HTTP communication with the MiroFish backend.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests


class MiroFishClient:
    """HTTP client for MiroFish backend API."""

    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or os.getenv("MIROFISH_URL", "http://localhost:5001")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": "PolymarketTrader/1.0"})

    def health(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def create_project(self, files: list, simulation_requirement: str,
                       project_name: str = None, additional_context: str = None) -> Optional[dict]:
        url = f"{self.base_url}/api/graph/ontology/generate"
        data = {"simulation_requirement": simulation_requirement}
        if project_name:
            data["project_name"] = project_name
        if additional_context:
            data["additional_context"] = additional_context

        upload_files = []
        for fp in files:
            upload_files.append(("files", (Path(fp).name, open(fp, "rb"), "application/octet-stream")))

        try:
            resp = self.session.post(url, data=data, files=upload_files, timeout=self.timeout)
            for _, f in upload_files:
                f[1].close()
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException as e:
            pass
        return None

    def create_project_from_text(self, text: str, simulation_requirement: str,
                                  project_name: str = None) -> Optional[dict]:
        tmp_path = Path("data/mirofish_temp_seed.txt")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(text, encoding="utf-8")
        try:
            return self.create_project(
                files=[str(tmp_path)],
                simulation_requirement=simulation_requirement,
                project_name=project_name,
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def build_graph(self, project_id: str, graph_name: str = None,
                    force: bool = False) -> Optional[dict]:
        url = f"{self.base_url}/api/graph/build"
        payload = {"project_id": project_id, "force": force}
        if graph_name:
            payload["graph_name"] = graph_name
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def wait_for_task(self, task_id: str, poll_interval: float = 2.0,
                      timeout: float = 300.0) -> Optional[dict]:
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self.session.get(
                    f"{self.base_url}/api/graph/task/{task_id}", timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    status = data.get("status")
                    if status == "completed":
                        return data.get("result")
                    elif status == "failed":
                        return None
            except requests.RequestException:
                pass
            time.sleep(poll_interval)
        return None

    def get_project(self, project_id: str) -> Optional[dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/graph/project/{project_id}", timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def list_projects(self, limit: int = 20) -> list:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/graph/project/list",
                params={"limit": limit}, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except requests.RequestException:
            pass
        return []

    def create_simulation(self, project_id: str, graph_id: str = None,
                          enable_twitter: bool = True,
                          enable_reddit: bool = True) -> Optional[dict]:
        payload = {
            "project_id": project_id,
            "enable_twitter": enable_twitter,
            "enable_reddit": enable_reddit,
        }
        if graph_id:
            payload["graph_id"] = graph_id
        try:
            resp = self.session.post(
                f"{self.base_url}/api/simulation/create",
                json=payload, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def prepare_simulation(self, simulation_id: str,
                           entity_types: list = None,
                           parallel_profile_count: int = 5) -> Optional[dict]:
        payload = {
            "simulation_id": simulation_id,
            "use_llm_for_profiles": True,
            "parallel_profile_count": parallel_profile_count,
        }
        if entity_types:
            payload["entity_types"] = entity_types
        try:
            resp = self.session.post(
                f"{self.base_url}/api/simulation/prepare",
                json=payload, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def wait_for_preparation(self, task_id: str = None, simulation_id: str = None,
                              poll_interval: float = 3.0,
                              timeout: float = 300.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                payload = {}
                if task_id:
                    payload["task_id"] = task_id
                if simulation_id:
                    payload["simulation_id"] = simulation_id
                resp = self.session.post(
                    f"{self.base_url}/api/simulation/prepare/status",
                    json=payload, timeout=self.timeout
                )
                if resp.status_code == 200:
                    status = resp.json().get("data", {}).get("status")
                    if status == "ready":
                        return True
                    elif status == "failed":
                        return False
            except requests.RequestException:
                pass
            time.sleep(poll_interval)
        return False

    def start_simulation(self, simulation_id: str, platform: str = "parallel",
                          max_rounds: int = 50) -> Optional[dict]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/simulation/start",
                json={
                    "simulation_id": simulation_id,
                    "platform": platform,
                    "max_rounds": max_rounds,
                },
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def get_simulation_status(self, simulation_id: str) -> Optional[dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/simulation/{simulation_id}/run-status",
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def wait_for_simulation(self, simulation_id: str, poll_interval: float = 5.0,
                             timeout: float = 3600.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            try:
                data = self.get_simulation_status(simulation_id)
                if data:
                    status = data.get("runner_status")
                    if status in ("completed", "stopped"):
                        return True
                    elif status == "failed":
                        return False
            except requests.RequestException:
                pass
            time.sleep(poll_interval)
        return False

    def stop_simulation(self, simulation_id: str) -> bool:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/simulation/stop",
                json={"simulation_id": simulation_id},
                timeout=self.timeout
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def generate_report(self, simulation_id: str,
                        force_regenerate: bool = False) -> Optional[dict]:
        try:
            resp = self.session.post(
                f"{self.base_url}/api/report/generate",
                json={"simulation_id": simulation_id, "force_regenerate": force_regenerate},
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def wait_for_report(self, simulation_id: str = None, task_id: str = None,
                         poll_interval: float = 2.0,
                         timeout: float = 600.0) -> Optional[str]:
        start = time.time()
        payload = {}
        if task_id:
            payload["task_id"] = task_id
        if simulation_id:
            payload["simulation_id"] = simulation_id
        while time.time() - start < timeout:
            try:
                resp = self.session.post(
                    f"{self.base_url}/api/report/generate/status",
                    json=payload, timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    status = data.get("status")
                    if status == "completed":
                        result = data.get("result", {})
                        return result.get("report_id")
                    elif status == "failed":
                        return None
            except requests.RequestException:
                pass
            time.sleep(poll_interval)
        return None

    def get_report(self, report_id: str) -> Optional[dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/report/{report_id}", timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def get_report_by_simulation(self, simulation_id: str) -> Optional[dict]:
        try:
            resp = self.session.get(
                f"{self.base_url}/api/report/by-simulation/{simulation_id}",
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data")
        except requests.RequestException:
            pass
        return None

    def get_simulation_posts(self, simulation_id: str, platform: str = None,
                              limit: int = 50, offset: int = 0) -> list:
        params = {"limit": limit, "offset": offset}
        if platform:
            params["platform"] = platform
        try:
            resp = self.session.get(
                f"{self.base_url}/api/simulation/{simulation_id}/posts",
                params=params, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except requests.RequestException:
            pass
        return []

    def get_simulation_actions(self, simulation_id: str, limit: int = 100,
                                offset: int = 0) -> list:
        params = {"limit": limit, "offset": offset}
        try:
            resp = self.session.get(
                f"{self.base_url}/api/simulation/{simulation_id}/actions",
                params=params, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except requests.RequestException:
            pass
        return []

    def list_simulations(self, project_id: str = None) -> list:
        params = {}
        if project_id:
            params["project_id"] = project_id
        try:
            resp = self.session.get(
                f"{self.base_url}/api/simulation/list",
                params=params, timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except requests.RequestException:
            pass
        return []
