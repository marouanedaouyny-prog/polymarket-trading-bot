"""
Local graph building service.
Replaces Zep Cloud entirely — stores graph data as local JSON,
extracts entities from text via LLM.
"""

import os
import uuid
import json
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale
from .text_processor import TextProcessor
from . import local_graph_store as store

logger = get_logger('mirofish.graph_builder')


@dataclass
class GraphInfo:
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    def __init__(self, api_key: Optional[str] = None):
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3,
    ) -> str:
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )
        current_locale = get_locale()

        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, current_locale)
        )
        thread.daemon = True
        thread.start()
        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        locale: str = 'zh',
    ):
        set_locale(locale)
        try:
            self.task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING, progress=5,
                message=t('progress.startBuildingGraph')
            )

            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id, progress=10,
                message=t('progress.graphCreated', graphId=graph_id)
            )

            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id, progress=15,
                message=t('progress.ontologySet')
            )

            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id, progress=20,
                message=t('progress.textSplit', count=total_chunks)
            )

            def progress_cb(msg, prog):
                self.task_manager.update_task(
                    task_id, progress=20 + int(prog * 60),
                    message=msg
                )

            extracted = store.extract_entities_batch(chunks, ontology, progress_cb)

            if extracted["entities"]:
                store.store_extracted_data(graph_id, extracted)

            entity_count = len(extracted.get("entities", []))
            edge_count = len(extracted.get("edges", []))

            self.task_manager.update_task(
                task_id, progress=90,
                message=t('progress.fetchingGraphInfo')
            )

            entity_types = set()
            for e in extracted.get("entities", []):
                et = e.get("entity_type")
                if et:
                    entity_types.add(et)

            graph_info = GraphInfo(
                graph_id=graph_id,
                node_count=entity_count,
                edge_count=edge_count,
                entity_types=list(entity_types),
            )

            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        return store.create_local_graph(name)

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        store.set_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        meta = store.get_graph_meta(graph_id)
        ontology = meta.get("ontology", {}) if meta else {}
        extracted = store.extract_entities_batch(chunks, ontology, progress_callback)
        if extracted["entities"]:
            store.store_extracted_data(graph_id, extracted)
        return []

    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600
    ):
        if progress_callback:
            progress_callback(t('progress.noEpisodesWait'), 1.0)

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        data = store.get_graph_data(graph_id)
        entity_types = set()
        for node in data.get("nodes", []):
            for label in node.get("labels", []):
                if label not in ["Entity", "Node"]:
                    entity_types.add(label)
        return GraphInfo(
            graph_id=graph_id,
            node_count=data["node_count"],
            edge_count=data["edge_count"],
            entity_types=list(entity_types),
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        return store.get_graph_data(graph_id)

    def delete_graph(self, graph_id: str):
        store.delete_local_graph(graph_id)
