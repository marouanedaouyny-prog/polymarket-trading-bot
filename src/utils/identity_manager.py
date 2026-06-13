"""
Identity Manager for Polymarket Entities
Resolves markets, outcomes, and sessions across disparate data sources.
Follows the 'identity-graph-operator' methodology.
"""

import json
import os
import hashlib
import re
from typing import Dict, List, Optional, Tuple
import logging

# Simple fuzzy matching
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class MarketIdentityManager:
    """
    Manages the canonical identity of prediction markets.
    Maps: market_id, condition_id, question_id, slug, question_text -> Canonical Entity
    """

    def __init__(self, data_dir: str = 'data/identity'):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.graph_path = os.path.join(self.data_dir, 'market_graph.json')
        self.proposals_path = os.path.join(self.data_dir, 'resolution_proposals.json')
        self.batch_mode = False
        
        # In-memory graph
        self.graph = self._load_graph()
        self.proposals = self._load_proposals()
        
        # Indices for fast lookup
        self.id_index = {} # id -> canonical_id
        self.text_index = {} # question_hash -> canonical_id
        self._rebuild_indices()

    def _load_graph(self) -> Dict:
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _load_proposals(self) -> List:
        if os.path.exists(self.proposals_path):
            try:
                with open(self.proposals_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_graph(self):
        if self.batch_mode: return
        try:
            with open(self.graph_path, 'w', encoding='utf-8') as f:
                json.dump(self.graph, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")

    def _save_proposals(self):
        if self.batch_mode: return
        try:
            with open(self.proposals_path, 'w', encoding='utf-8') as f:
                json.dump(self.proposals, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save proposals: {e}")

    def _rebuild_indices(self):
        self.id_index = {}
        self.text_index = {}
        for canon_id, entity in self.graph.items():
            for key, val in entity.get('identifiers', {}).items():
                if val:
                    self.id_index[f"{key}:{val}"] = canon_id
            
            # Index normalized question
            q = entity.get('metadata', {}).get('question', '')
            if q:
                h = self._normalize_and_hash(q)
                self.text_index[h] = canon_id

    def _normalize_and_hash(self, text: str) -> str:
        # Strip dates, times, and extra whitespace
        text = text.lower().strip()
        text = re.sub(r'\d{4}-\d{2}-\d{2}', '', text) # Remove YYYY-MM-DD
        text = re.sub(r'\d{2}/\d{2}/\d{4}', '', text) # Remove MM/DD/YYYY
        text = re.sub(r'\s+', ' ', text).strip()
        return hashlib.md5(text.encode()).hexdigest()

    def resolve_market(self, market_data: Dict) -> Tuple[str, float, bool]:
        """
        Resolves a market record to a canonical ID.
        Returns: (canonical_id, confidence, is_new)
        """
        # 1. Direct ID Match
        identifiers = {
            'id': str(market_data.get('id', '')),
            'conditionId': str(market_data.get('conditionId', market_data.get('condition_id', ''))),
            'questionID': str(market_data.get('questionID', market_data.get('question_id', ''))),
            'slug': str(market_data.get('slug', market_data.get('market_slug', '')))
        }
        
        for key, val in identifiers.items():
            if val and val != 'None' and f"{key}:{val}" in self.id_index:
                return self.id_index[f"{key}:{val}"], 1.0, False

        # 2. Normalized Text Match
        question = str(market_data.get('question', ''))
        if question:
            q_hash = self._normalize_and_hash(question)
            if q_hash in self.text_index:
                return self.text_index[q_hash], 0.95, False

        # 3. Fuzzy Match (If high confidence)
        best_match = None
        best_score = 0.0
        # Only fuzzy match if we have a reasonable amount of data
        if len(self.graph) > 0 and len(question) > 10:
            for canon_id, entity in self.graph.items():
                stored_q = entity.get('metadata', {}).get('question', '')
                if not stored_q: continue
                
                score = SequenceMatcher(None, question.lower(), stored_q.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = canon_id

        if best_match and best_score > 0.85:
            return best_match, best_score, False

        # 4. Create New Canonical Identity
        safe_q = question or f"Unknown-{hashlib.md5(str(identifiers).encode()).hexdigest()[:8]}"
        canonical_id = f"PM-{hashlib.md5(safe_q.encode()).hexdigest()[:8].upper()}"
        self.graph[canonical_id] = {
            'identifiers': identifiers,
            'metadata': {
                'question': question,
                'description': str(market_data.get('description', ''))[:500],
                'created_at': '2026-06-13'
            },
            'resolved_outcome': market_data.get('outcome', None)
        }
        
        self._save_graph()
        self._rebuild_indices()
        return canonical_id, 1.0, True

    def commit(self):
        """Force save in batch mode."""
        old_batch = self.batch_mode
        self.batch_mode = False
        self._save_graph()
        self._save_proposals()
        self.batch_mode = old_batch

    def update_outcome(self, canonical_id: str, outcome: str):
        if canonical_id in self.graph:
            self.graph[canonical_id]['resolved_outcome'] = outcome
            self._save_graph()
