# brain_core/global_workspace.py
"""
Global Workspace Theory (GWT) implementation for Kato.
Based on Baars (1988), Dehaene (2014), Minsky (1986).

Core ideas:
- Multiple specialized processors (unconscious) compete for access to global workspace
- Winning coalition gets broadcast to all processors → conscious access
- Workspace capacity is limited (1-4 items) → attention bottleneck
- Integration: information in workspace is globally available for report, memory, action
"""
from __future__ import annotations
import asyncio
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from collections import deque
import math

@dataclass
class WorkspaceContent:
    """Item in global workspace - the 'conscious' content"""
    id: str
    source: str                    # which processor submitted it
    content: Dict[str, Any]        # the actual information
    activation: float              # current activation strength (0-1)
    timestamp: float
    broadcast_count: int = 0       # how many times re-broadcast
    coalition: List[str] = field(default_factory=list)  # supporting processors
    metadata: Dict = field(default_factory=dict)

@dataclass
class Processor:
    """Specialized unconscious processor"""
    name: str
    priority: float = 1.0          # baseline priority
    threshold: float = 0.3         # activation needed to enter competition
    last_output: Optional[WorkspaceContent] = None
    expertise: List[str] = field(default_factory=list)  # what domains it handles

class GlobalWorkspace:
    """
    Global Workspace - the 'theater of consciousness'.
    
    Architecture:
    - Multiple processors submit candidates
    - Competition via activation dynamics (winner-take-all with coalition formation)
    - Winner gets broadcast to ALL processors
    - Broadcast enables: working memory, long-term memory encoding, verbal report, flexible action
    """
    
    def __init__(self, agent_id: str, max_capacity: int = 3, decay_rate: float = 0.15):
        self.agent_id = agent_id
        self.max_capacity = max_capacity          # conscious capacity limit (Miller's 7±2 → 3-4 for focused attention)
        self.decay_rate = decay_rate              # activation decay per tick
        
        # Workspace state
        self.contents: List[WorkspaceContent] = []  # current conscious contents
        self.history: deque = deque(maxlen=200)     # recent broadcast history
        self.pending_broadcast: Optional[WorkspaceContent] = None
        
        # Processors (unconscious specialists)
        self.processors: Dict[str, Processor] = {}
        self._register_default_processors()
        
        # Metrics for monitoring (observer only - Kato doesn't see these)
        self.metrics = {
            "total_submissions": 0,
            "total_broadcasts": 0,
            "coalition_formations": 0,
            "capacity_overflows": 0,
            "avg_broadcast_duration": 0.0,
        }
        
        # Integration with brain_server
        self._brain = None
    
    def _register_default_processors(self):
        """Register core unconscious processors"""
        defaults = [
            Processor("perception", priority=1.2, threshold=0.2, 
                      expertise=["visual", "spatial", "object_recognition"]),
            Processor("interoception", priority=1.0, threshold=0.15,
                      expertise=["body_state", "energy", "comfort", "needs"]),
            Processor("emotion", priority=1.1, threshold=0.25,
                      expertise=["valence", "arousal", "mood", "feelings"]),
            Processor("memory", priority=0.9, threshold=0.3,
                      expertise=["episodic_recall", "semantic_association", "pattern_match"]),
            Processor("goal_management", priority=1.0, threshold=0.2,
                      expertise=["priority", "planning", "intent"]),
            Processor("social", priority=0.8, threshold=0.3,
                      expertise=["npc_interaction", "relationship", "communication"]),
            Processor("predictive", priority=1.0, threshold=0.25,
                      expertise=["expectation", "surprise", "prediction_error"]),
            Processor("metacognition", priority=0.7, threshold=0.35,
                      expertise=["uncertainty", "confidence", "error_monitoring"]),
            Processor("narrative", priority=0.6, threshold=0.4,
                      expertise=["autobiographical", "meaning", "identity"]),
        ]
        for p in defaults:
            self.processors[p.name] = p
    
    def set_brain_ref(self, brain_server_module):
        """Set reference to brain_server for state access"""
        self._brain = brain_server_module
    
    def submit(self, source: str, content: Dict[str, Any], activation: float = None) -> WorkspaceContent:
        """Processor submits candidate for conscious access"""
        if source not in self.processors:
            # Dynamic processor registration
            self.processors[source] = Processor(source, threshold=0.3)
        
        proc = self.processors[source]
        if activation is None:
            activation = proc.priority * random.uniform(0.7, 1.0)
        
        # Only enter competition if above threshold
        if activation < proc.threshold:
            return None
        
        item = WorkspaceContent(
            id=f"{source}_{int(time.time()*1000)}_{random.randint(100,999)}",
            source=source,
            content=content,
            activation=min(1.0, activation),
            timestamp=time.time(),
            metadata={"processor_priority": proc.priority}
        )
        
        self.metrics["total_submissions"] += 1
        return item
    
    def competition_step(self, new_items: List[WorkspaceContent]) -> List[WorkspaceContent]:
        """
        Global Workspace competition dynamics.
        Winner-take-all with coalition formation (Dehaene's 'ignition').
        """
        # Add new candidates
        for item in new_items:
            if item:
                self.contents.append(item)
        
        # Decay all activations
        for item in self.contents:
            item.activation *= (1.0 - self.decay_rate)
        
        # Remove items below consciousness threshold
        self.contents = [c for c in self.contents if c.activation > 0.15]
        
        # Coalition formation: similar items boost each other
        self._form_coalitions()
        
        # Capacity limit: only top items stay conscious
        self.contents.sort(key=lambda c: c.activation, reverse=True)
        if len(self.contents) > self.max_capacity:
            self.metrics["capacity_overflows"] += 1
            self.contents = self.contents[:self.max_capacity]
        
        # Check for ignition (broadcast trigger)
        broadcast_items = []
        for item in self.contents:
            if item.activation > 0.6 and item.broadcast_count == 0:
                broadcast_items.append(item)
                item.broadcast_count = 1
                self.metrics["total_broadcasts"] += 1
                self.history.append({
                    "id": item.id,
                    "source": item.source,
                    "content": item.content,
                    "activation": item.activation,
                    "coalition": item.coalition.copy(),
                    "timestamp": time.time()
                })
        
        return broadcast_items
    
    def _form_coalitions(self):
        """Items with similar content form coalitions, boosting activation"""
        for i, a in enumerate(self.contents):
            for b in self.contents[i+1:]:
                similarity = self._content_similarity(a.content, b.content)
                if similarity > 0.7:
                    # Mutual boost
                    boost = 0.05 * similarity
                    a.activation = min(1.0, a.activation + boost)
                    b.activation = min(1.0, b.activation + boost)
                    if b.source not in a.coalition:
                        a.coalition.append(b.source)
                    if a.source not in b.coalition:
                        b.coalition.append(a.source)
                    self.metrics["coalition_formations"] += 1
    
    def _content_similarity(self, a: Dict, b: Dict) -> float:
        """Simple content similarity for coalition formation"""
        # Check for overlapping keys with similar values
        common_keys = set(a.keys()) & set(b.keys())
        if not common_keys:
            return 0.0
        matches = 0
        for k in common_keys:
            va, vb = a[k], b[k]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                if abs(va - vb) < 0.2:  # close numerical values
                    matches += 1
            elif va == vb:
                matches += 1
        return matches / len(common_keys)
    
    def broadcast(self, item: WorkspaceContent) -> Dict[str, Any]:
        """
        Broadcast to all processors - the moment of 'conscious access'.
        Returns broadcast packet for each processor to receive.
        """
        packet = {
            "workspace_id": item.id,
            "source": item.source,
            "content": item.content,
            "activation": item.activation,
            "coalition": item.coalition,
            "timestamp": item.timestamp,
            "broadcast_id": len(self.history)
        }
        return packet
    
    def get_conscious_state(self) -> Dict[str, Any]:
        """Current conscious contents - what Kato 'knows she knows'"""
        return {
            "contents": [
                {
                    "id": c.id,
                    "source": c.source,
                    "content": c.content,
                    "activation": c.activation,
                    "coalition": c.coalition,
                    "age": time.time() - c.timestamp
                }
                for c in self.contents
            ],
            "capacity_used": len(self.contents),
            "capacity_max": self.max_capacity,
            "recent_broadcasts": list(self.history)[-10:]
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Observer-only metrics"""
        return self.metrics.copy()


# Integration helper for brain_server
def create_global_workspace(agent_id: str) -> GlobalWorkspace:
    """Factory function"""
    return GlobalWorkspace(agent_id)