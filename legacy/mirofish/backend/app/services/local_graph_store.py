"""
Local graph storage — replaces Zep Cloud entirely.
Stores graph metadata, ontology, entities, and edges as JSON files
under the project's uploads directory.
"""

import json
import os
import uuid
import re
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.locale import t

logger = get_logger('mirofish.local_graph')


def _get_graph_dir(graph_id: str) -> str:
    base = os.path.join(Config.UPLOAD_FOLDER, 'local_graphs')
    return os.path.join(base, graph_id)


def _ensure_graph_dir(graph_id: str) -> str:
    d = _get_graph_dir(graph_id)
    os.makedirs(d, exist_ok=True)
    return d


def _read_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _write_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Entity extraction via LLM ---

ENTITY_EXTRACTION_PROMPT = """You are a knowledge graph entity extractor. Given a text chunk and an ontology definition, extract all named entities mentioned in the text.

For each entity, provide:
- name: The entity's name (e.g., "John Smith", "Apple Inc.")
- entity_type: One of the defined entity types from the ontology
- summary: A 1-2 sentence summary of what this entity is in context of the text

Also extract relationships (edges) between entities:
- source: name of the source entity
- target: name of the target entity
- relation_type: one of the defined edge types
- fact: description of the relationship

Return ONLY valid JSON:
{
    "entities": [
        {"name": "...", "entity_type": "...", "summary": "..."}
    ],
    "edges": [
        {"source": "...", "target": "...", "relation_type": "...", "fact": "..."}
    ]
}

If no entities are found in the chunk, return {"entities": [], "edges": []}."""


def extract_entities_from_text(text: str, ontology: Dict[str, Any]) -> Dict[str, Any]:
    entity_types = [e["name"] for e in ontology.get("entity_types", [])]
    edge_types = [e["name"] for e in ontology.get("edge_types", [])]

    system_prompt = ENTITY_EXTRACTION_PROMPT
    user_prompt = f"""Ontology entity types: {', '.join(entity_types)}
Ontology edge types: {', '.join(edge_types)}

Text chunk:
{text[:8000]}"""

    llm = LLMClient()
    resp_text = None
    try:
        resp_text = llm.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=4096
        )
    except Exception as e:
        logger.warning(f"LLM entity extraction call failed: {e}")
        return {"entities": [], "edges": []}

    import re, json
    cleaned = resp_text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"Entity extraction JSON parse failed: {e}, text={resp_text[:300]}")
        return {"entities": [], "edges": []}

    entities = result.get("entities", [])
    edges = result.get("edges", [])

    # Validate entity types
    valid_entities = []
    for e in entities:
        if e.get("entity_type") in entity_types or not entity_types:
            valid_entities.append(e)
        else:
            valid_entities.append({**e, "entity_type": "Person"})

    return {"entities": valid_entities, "edges": edges}


def extract_entities_batch(chunks: List[str], ontology: Dict[str, Any],
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    all_entities = []
    all_edges = []
    seen_names = set()
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(f"Extracting entities from chunk {i+1}/{total}", (i+1)/total)

        try:
            result = extract_entities_from_text(chunk, ontology)
            for e in result.get("entities", []):
                name = e.get("name", "").strip()
                if name and name not in seen_names:
                    seen_names.add(name)
                    all_entities.append(e)
            all_edges.extend(result.get("edges", []))
        except Exception as ex:
            logger.warning(f"Failed to extract from chunk {i}: {ex}")

    return {"entities": all_entities, "edges": all_edges}


# --- Local graph operations ---

def create_local_graph(name: str) -> str:
    graph_id = f"local_{uuid.uuid4().hex[:16]}"
    gdir = _ensure_graph_dir(graph_id)
    meta = {
        "graph_id": graph_id,
        "name": name,
        "description": "Local MiroFish Graph",
        "created_at": datetime.now().isoformat(),
        "ontology": None,
        "entity_count": 0,
        "edge_count": 0,
    }
    _write_json(os.path.join(gdir, "meta.json"), meta)
    _write_json(os.path.join(gdir, "entities.json"), [])
    _write_json(os.path.join(gdir, "edges.json"), [])
    logger.info(f"Created local graph: {graph_id}")
    return graph_id


def set_ontology(graph_id: str, ontology: Dict[str, Any]):
    gdir = _ensure_graph_dir(graph_id)
    meta = _read_json(os.path.join(gdir, "meta.json")) or {}
    meta["ontology"] = ontology
    _write_json(os.path.join(gdir, "meta.json"), meta)


def store_extracted_data(graph_id: str, extracted: Dict[str, Any]):
    gdir = _ensure_graph_dir(graph_id)
    entities = extracted.get("entities", [])
    edges = extracted.get("edges", [])

    # Deduplicate by name
    existing = _read_json(os.path.join(gdir, "entities.json")) or []
    existing_edges = _read_json(os.path.join(gdir, "edges.json")) or []
    seen = {e["name"] for e in existing}

    for e in entities:
        name = e.get("name", "").strip()
        if name and name not in seen:
            seen.add(name)
            e["uuid"] = str(uuid.uuid4())
            e["labels"] = [e.get("entity_type", "Entity"), "Entity"]
            e["attributes"] = {}
            existing.append(e)

    for edge in edges:
        edge["uuid"] = str(uuid.uuid4())
        existing_edges.append(edge)

    _write_json(os.path.join(gdir, "entities.json"), existing)
    _write_json(os.path.join(gdir, "edges.json"), existing_edges)

    meta = _read_json(os.path.join(gdir, "meta.json")) or {}
    meta["entity_count"] = len(existing)
    meta["edge_count"] = len(existing_edges)
    _write_json(os.path.join(gdir, "meta.json"), meta)


def get_all_entities(graph_id: str) -> List[Dict[str, Any]]:
    gdir = _get_graph_dir(graph_id)
    return _read_json(os.path.join(gdir, "entities.json")) or []


def get_all_edges(graph_id: str) -> List[Dict[str, Any]]:
    gdir = _get_graph_dir(graph_id)
    return _read_json(os.path.join(gdir, "edges.json")) or []


def get_graph_data(graph_id: str) -> Dict[str, Any]:
    entities = get_all_entities(graph_id)
    edges = get_all_edges(graph_id)
    gdir = _get_graph_dir(graph_id)
    meta = _read_json(os.path.join(gdir, "meta.json")) or {}

    nodes_data = []
    for e in entities:
        nodes_data.append({
            "uuid": e.get("uuid", ""),
            "name": e.get("name", ""),
            "labels": e.get("labels", ["Entity"]),
            "summary": e.get("summary", ""),
            "attributes": e.get("attributes", {}),
            "created_at": meta.get("created_at"),
        })

    edges_data = []
    for edge in edges:
        edges_data.append({
            "uuid": edge.get("uuid", ""),
            "name": edge.get("relation_type", ""),
            "fact": edge.get("fact", ""),
            "fact_type": edge.get("relation_type", ""),
            "source_node_uuid": edge.get("source_uuid", ""),
            "target_node_uuid": edge.get("target_uuid", ""),
            "source_node_name": edge.get("source", ""),
            "target_node_name": edge.get("target", ""),
            "attributes": edge.get("attributes", {}),
            "created_at": meta.get("created_at"),
        })

    return {
        "graph_id": graph_id,
        "nodes": nodes_data,
        "edges": edges_data,
        "node_count": len(nodes_data),
        "edge_count": len(edges_data),
    }


def get_graph_meta(graph_id: str) -> Optional[Dict[str, Any]]:
    gdir = _get_graph_dir(graph_id)
    return _read_json(os.path.join(gdir, "meta.json"))


def delete_local_graph(graph_id: str):
    import shutil
    gdir = _get_graph_dir(graph_id)
    if os.path.exists(gdir):
        shutil.rmtree(gdir)
        logger.info(f"Deleted local graph: {graph_id}")

def project_has_graph(project_id: str) -> bool:
    base = os.path.join(Config.UPLOAD_FOLDER, 'local_graphs')
    if not os.path.exists(base):
        return False
    for gid in os.listdir(base):
        meta = _read_json(os.path.join(base, gid, "meta.json"))
        if meta and meta.get("project_id") == project_id:
            return True
    return False

def get_graph_id_for_project(project_id: str) -> Optional[str]:
    base = os.path.join(Config.UPLOAD_FOLDER, 'local_graphs')
    if not os.path.exists(base):
        return None
    for gid in os.listdir(base):
        meta = _read_json(os.path.join(base, gid, "meta.json"))
        if meta and meta.get("project_id") == project_id:
            return gid
    return None
