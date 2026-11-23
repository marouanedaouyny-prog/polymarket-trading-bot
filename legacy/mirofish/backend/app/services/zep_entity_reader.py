"""
Local entity reader — replaces ZepEntityReader.
Reads entities from the local JSON graph store.
"""

import time
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from ..utils.logger import get_logger
from . import local_graph_store as store

logger = get_logger('mirofish.entity_reader')

T = TypeVar('T')


@dataclass
class EntityNode:
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class ZepEntityReader:
    def __init__(self, api_key: Optional[str] = None):
        pass

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Getting all nodes for local graph {graph_id}")
        entities = store.get_all_entities(graph_id)
        nodes_data = []
        for e in entities:
            nodes_data.append({
                "uuid": e.get("uuid", ""),
                "name": e.get("name", ""),
                "labels": e.get("labels", ["Entity"]),
                "summary": e.get("summary", ""),
                "attributes": e.get("attributes", {}),
            })
        logger.info(f"Got {len(nodes_data)} nodes")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info(f"Getting all edges for local graph {graph_id}")
        edges = store.get_all_edges(graph_id)
        edges_data = []
        for edge in edges:
            edges_data.append({
                "uuid": edge.get("uuid", ""),
                "name": edge.get("relation_type", ""),
                "fact": edge.get("fact", ""),
                "source_node_uuid": edge.get("source_uuid", ""),
                "target_node_uuid": edge.get("target_uuid", ""),
                "attributes": edge.get("attributes", {}),
            })
        logger.info(f"Got {len(edges_data)} edges")
        return edges_data

    def get_node_edges(self, node_uuid: str) -> List[Dict[str, Any]]:
        return []

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True
    ) -> FilteredEntities:
        logger.info(f"Filtering entities for local graph {graph_id}")
        all_nodes = self.get_all_nodes(graph_id)
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            if not custom_labels:
                continue
            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]

            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])
                entity.related_edges = related_edges
                related_nodes = []
                for ruid in related_node_uuids:
                    if ruid in node_map:
                        rn = node_map[ruid]
                        related_nodes.append({
                            "uuid": rn["uuid"],
                            "name": rn["name"],
                            "labels": rn["labels"],
                            "summary": rn.get("summary", ""),
                        })
                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(f"Filtered: {len(filtered_entities)} entities, types: {entity_types_found}")
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=len(all_nodes),
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        all_nodes = self.get_all_nodes(graph_id)
        for node in all_nodes:
            if node["uuid"] == entity_uuid:
                return EntityNode(
                    uuid=node["uuid"],
                    name=node["name"],
                    labels=node["labels"],
                    summary=node["summary"],
                    attributes=node["attributes"],
                )
        return None

    def get_entities_by_type(self, graph_id: str, entity_type: str,
                              enrich_with_edges: bool = True) -> List[EntityNode]:
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities
