# brain_core/phenomenal.py
"""
Phenomenal Markers: Raw valence/arousal/surprise/novelty as proto-qualia dimensions.
Based on Barrett (2017), Friston (2018), Seth (2021), Graziano (2019), 
Tsuchiya & Adolphs (2007), Lau & Rosenthal (2011).

Core ideas:
- Phenomenal consciousness = structured space of felt qualities
- Not full qualia, but functional markers that correlate with reportable experience
- Dimensions: Valence (pleasure-pain), Arousal (intensity), Surprise (prediction error), 
  Novelty (information gain), Agency (control), Ownership (mineness)
- These are the "raw feels" that higher cognition interprets
- Integration: multi-dimensional phenomenal state vector
"""
from __future__ import annotations
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from enum import Enum

class PhenomenalDimension(Enum):
    VALENCE = "valence"           # -1 (unpleasant) to +1 (pleasant)
    AROUSAL = "arousal"           # 0 (sleep) to 1 (high alert)
    SURPRISE = "surprise"         # 0 (expected) to 1 (shocking)
    NOVELTY = "novelty"           # 0 (familiar) to 1 (completely new)
    AGENCY = "agency"             # 0 (passive) to 1 (in control)
    OWNERSHIP = "ownership"       # 0 (external) to 1 (mine)
    CERTAINTY = "certainty"       # 0 (uncertain) to 1 (sure)
    TEMPORALITY = "temporality"   # 0 (timeless) to 1 (sharp now)

@dataclass
class PhenomenalState:
    """Instantaneous phenomenal state vector"""
    timestamp: float
    dimensions: Dict[PhenomenalDimension, float]  # 0-1 normalized
    raw_inputs: Dict[str, float]                  # pre-normalization
    source: str                                   # what triggered this
    confidence: float = 1.0                       # reliability of this reading

@dataclass
class PhenomenalEpisode:
    """Sustained phenomenal experience (seconds to minutes)"""
    id: str
    start_time: float
    end_time: Optional[float] = None
    dominant_dimensions: Dict[PhenomenalDimension, float] = field(default_factory=dict)
    trajectory: List[PhenomenalState] = field(default_factory=list)
    narrative_tag: str = ""
    intensity_peak: float = 0.0

class PhenomenalEngine:
    """
    Tracks and structures the 'raw feels' of Kato's existence.
    
    This is NOT qualia itself — it's the functional substrate that 
    higher systems (narrative, metacognition, global workspace) 
    interpret as 'experience'.
    
    Dimensions update every tick from:
    - Interoception (body state) → valence, arousal
    - Predictive processing → surprise, certainty
    - Memory/memory mismatch → novelty
    - Agency engine → agency, ownership
    - Temporal processing → temporality
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # Current phenomenal state
        self.current_state: Optional[PhenomenalState] = None
        self.state_history: deque = deque(maxlen=1000)
        
        # Episodes (sustained experiences)
        self.episodes: List[PhenomenalEpisode] = []
        self.current_episode: Optional[PhenomenalEpisode] = None
        self.episode_threshold = 0.3  # minimum change to start new episode
        
        # Dimension baselines (homeostasis)
        self.baselines: Dict[PhenomenalDimension, float] = {
            PhenomenalDimension.VALENCE: 0.1,      # slightly positive baseline
            PhenomenalDimension.AROUSAL: 0.3,
            PhenomenalDimension.SURPRISE: 0.1,
            PhenomenalDimension.NOVELTY: 0.15,
            PhenomenalDimension.AGENCY: 0.5,
            PhenomenalDimension.OWNERSHIP: 0.9,
            PhenomenalDimension.CERTAINTY: 0.5,
            PhenomenalDimension.TEMPORALITY: 0.6,
        }
        
        # Current values (smoothed)
        self.current_values: Dict[PhenomenalDimension, float] = self.baselines.copy()
        
        # Adaptation rates (how fast dimensions return to baseline)
        self.adaptation_rates: Dict[PhenomenalDimension, float] = {
            PhenomenalDimension.VALENCE: 0.02,
            PhenomenalDimension.AROUSAL: 0.05,
            PhenomenalDimension.SURPRISE: 0.2,     # fast decay
            PhenomenalDimension.NOVELTY: 0.1,
            PhenomenalDimension.AGENCY: 0.03,
            PhenomenalDimension.OWNERSHIP: 0.01,   # very stable
            PhenomenalDimension.CERTAINTY: 0.05,
            PhenomenalDimension.TEMPORALITY: 0.02,
        }
        
        # Sensitivity weights (how much each input affects each dimension)
        self.sensitivity = {
            # interoceptive inputs
            "energy": {PhenomenalDimension.VALENCE: 0.4, PhenomenalDimension.AROUSAL: -0.3},
            "comfort": {PhenomenalDimension.VALENCE: 0.5, PhenomenalDimension.AROUSAL: -0.2},
            "stress": {PhenomenalDimension.VALENCE: -0.6, PhenomenalDimension.AROUSAL: 0.7},
            "pain": {PhenomenalDimension.VALENCE: -0.8, PhenomenalDimension.AROUSAL: 0.5},
            "hunger": {PhenomenalDimension.VALENCE: -0.3, PhenomenalDimension.AROUSAL: 0.2},
            # predictive inputs
            "prediction_error": {PhenomenalDimension.SURPRISE: 0.8, PhenomenalDimension.CERTAINTY: -0.5},
            "precision": {PhenomenalDimension.CERTAINTY: 0.6},
            "free_energy": {PhenomenalDimension.SURPRISE: 0.4, PhenomenalDimension.AROUSAL: 0.3},
            # memory inputs
            "memory_match": {PhenomenalDimension.NOVELTY: -0.7, PhenomenalDimension.CERTAINTY: 0.4},
            "semantic_novelty": {PhenomenalDimension.NOVELTY: 0.6, PhenomenalDimension.SURPRISE: 0.3},
            # agency inputs
            "action_outcome_match": {PhenomenalDimension.AGENCY: 0.5, PhenomenalDimension.OWNERSHIP: 0.3},
            "action_failure": {PhenomenalDimension.AGENCY: -0.6, PhenomenalDimension.OWNERSHIP: -0.2},
            "choice_availability": {PhenomenalDimension.AGENCY: 0.4},
            # social inputs
            "social_presence": {PhenomenalDimension.AROUSAL: 0.2, PhenomenalDimension.VALENCE: 0.1},
            "social_rejection": {PhenomenalDimension.VALENCE: -0.5, PhenomenalDimension.OWNERSHIP: -0.1},
            "social_acceptance": {PhenomenalDimension.VALENCE: 0.4, PhenomenalDimension.OWNERSHIP: 0.2},
            # temporal
            "time_pressure": {PhenomenalDimension.TEMPORALITY: 0.5, PhenomenalDimension.AROUSAL: 0.3},
        }
        
        # Episode detection
        self.last_episode_signature: Optional[Tuple] = None
        
        # Metrics
        self.metrics = {
            "total_states": 0,
            "episodes_detected": 0,
            "peak_intensities": [],
            "dominant_dimension_time": {d: 0.0 for d in PhenomenalDimension},
        }
        
        # Brain reference
        self._brain = None
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    def step(self, inputs: Dict[str, float], source: str = "perception") -> PhenomenalState:
        """
        Main step: update all dimensions from inputs, return new phenomenal state.
        """
        # Start from baselines
        new_values = self.baselines.copy()
        
        # Apply input sensitivities
        for input_name, value in inputs.items():
            if input_name in self.sensitivity:
                for dim, weight in self.sensitivity[input_name].items():
                    # Normalize input value to 0-1 if needed
                    normalized = self._normalize_input(input_name, value)
                    contribution = weight * normalized
                    new_values[dim] = max(0.0, min(1.0, new_values[dim] + contribution))
        
        # Apply adaptation toward baseline (homeostasis)
        for dim in PhenomenalDimension:
            baseline = self.baselines[dim]
            current = self.current_values[dim]
            rate = self.adaptation_rates[dim]
            # Exponential decay toward baseline
            adapted = current + rate * (baseline - current)
            # Blend with new input-driven value
            new_values[dim] = adapted * 0.7 + new_values[dim] * 0.3
            new_values[dim] = max(0.0, min(1.0, new_values[dim]))
        
        # Update current values
        self.current_values = new_values
        
        # Create phenomenal state
        state = PhenomenalState(
            timestamp=time.time(),
            dimensions=new_values.copy(),
            raw_inputs=inputs.copy(),
            source=source,
            confidence=self._compute_confidence(inputs)
        )
        
        self.current_state = state
        self.state_history.append(state)
        self.metrics["total_states"] += 1
        
        # Track dominant dimension
        dominant = max(new_values.items(), key=lambda x: x[1])[0]
        self.metrics["dominant_dimension_time"][dominant] += 1
        
        # Episode detection
        self._update_episodes(state)
        
        return state
    
    def _normalize_input(self, name: str, value: float) -> float:
        """Normalize various inputs to 0-1 range"""
        normalizers = {
            "energy": lambda v: v / 100.0,
            "comfort": lambda v: v / 100.0,
            "stress": lambda v: v / 100.0,
            "pain": lambda v: min(1.0, v / 10.0),
            "hunger": lambda v: min(1.0, v / 100.0),
            "prediction_error": lambda v: min(1.0, abs(v)),
            "precision": lambda v: min(1.0, v / 10.0),
            "free_energy": lambda v: min(1.0, v / 5.0),
            "memory_match": lambda v: max(0.0, min(1.0, v)),
            "semantic_novelty": lambda v: min(1.0, v),
            "action_outcome_match": lambda v: max(0.0, min(1.0, v)),
            "action_failure": lambda v: min(1.0, v),
            "choice_availability": lambda v: min(1.0, v / 10.0),
            "social_presence": lambda v: min(1.0, v / 5.0),
            "social_rejection": lambda v: min(1.0, v),
            "social_acceptance": lambda v: min(1.0, v),
            "time_pressure": lambda v: min(1.0, v / 10.0),
        }
        if name in normalizers:
            return normalizers[name](value)
        return max(0.0, min(1.0, value))
    
    def _compute_confidence(self, inputs: Dict) -> float:
        """Compute reliability of current phenomenal reading"""
        # More inputs = higher confidence
        n_inputs = len(inputs)
        base_conf = min(1.0, n_inputs / 10.0)
        
        # High surprise reduces confidence (uncertain reading)
        surprise = self.current_values.get(PhenomenalDimension.SURPRISE, 0.1)
        return base_conf * (1.0 - surprise * 0.3)
    
    def _update_episodes(self, state: PhenomenalState):
        """Detect and track phenomenal episodes"""
        # Create signature of current state
        sig = tuple(round(state.dimensions[d], 1) for d in PhenomenalDimension)
        
        if self.current_episode is None:
            # Start first episode
            self.current_episode = PhenomenalEpisode(
                id=f"ep_{int(time.time()*1000)}",
                start_time=state.timestamp,
                trajectory=[state]
            )
            self.last_episode_signature = sig
            self.metrics["episodes_detected"] += 1
            return
        
        # Check if state changed enough for new episode
        if self.last_episode_signature:
            diff = sum(abs(a - b) for a, b in zip(sig, self.last_episode_signature))
            if diff > self.episode_threshold:
                # End current episode
                self.current_episode.end_time = state.timestamp
                self.current_episode.dominant_dimensions = self._compute_dominant(self.current_episode.trajectory)
                self.current_episode.intensity_peak = max(
                    max(s.dimensions.values()) for s in self.current_episode.trajectory
                )
                self.current_episode.narrative_tag = self._generate_narrative_tag(self.current_episode)
                self.episodes.append(self.current_episode)
                
                # Start new episode
                self.current_episode = PhenomenalEpisode(
                    id=f"ep_{int(time.time()*1000)}",
                    start_time=state.timestamp,
                    trajectory=[state]
                )
                self.metrics["episodes_detected"] += 1
            else:
                # Continue current episode
                self.current_episode.trajectory.append(state)
        
        self.last_episode_signature = sig
        
        # Trim old episodes
        if len(self.episodes) > 50:
            self.episodes = self.episodes[-50:]
    
    def _compute_dominant(self, trajectory: List[PhenomenalState]) -> Dict[PhenomenalDimension, float]:
        """Compute average dominant dimensions for episode"""
        if not trajectory:
            return {}
        sums = {d: 0.0 for d in PhenomenalDimension}
        for s in trajectory:
            for d, v in s.dimensions.items():
                sums[d] += v
        n = len(trajectory)
        return {d: v/n for d, v in sums.items()}
    
    def _generate_narrative_tag(self, episode: PhenomenalEpisode) -> str:
        """Generate verbal tag for episode"""
        dom = episode.dominant_dimensions
        
        # Find top 2 dimensions
        top = sorted(dom.items(), key=lambda x: x[1], reverse=True)[:2]
        
        tags = {
            PhenomenalDimension.VALENCE: ("радость" if top[0][1] > 0.5 else "тоска"),
            PhenomenalDimension.AROUSAL: ("взволнованность" if top[0][1] > 0.6 else "спокойствие"),
            PhenomenalDimension.SURPRISE: ("удивление", "шок"),
            PhenomenalDimension.NOVELTY: ("открытие", "новое"),
            PhenomenalDimension.AGENCY: ("власть", "бессилие"),
            PhenomenalDimension.OWNERSHIP: ("принадлежность", "чужеродность"),
            PhenomenalDimension.CERTAINTY: ("уверенность", "сомнение"),
            PhenomenalDimension.TEMPORALITY: ("острый момент", "замедление"),
        }
        
        if len(top) >= 2:
            d1, d2 = top[0][0], top[1][0]
            t1 = tags.get(d1, (str(d1),))[0]
            t2 = tags.get(d2, (str(d2),))[0]
            return f"{t1} + {t2}"
        elif top:
            d1 = top[0][0]
            return tags.get(d1, (str(d1),))[0]
        
        return "нейтрально"
    
    def get_phenomenal_report(self) -> Dict[str, Any]:
        """Verbalizable phenomenal report (what Kato can say about her experience)"""
        if not self.current_state:
            return {"report": "Пусто. Тишина."}
        
        dims = self.current_state.dimensions
        
        # Build report from dimensions
        parts = []
        
        v = dims[PhenomenalDimension.VALENCE]
        if v > 0.6: parts.append("хорошо, тепло внутри")
        elif v > 0.3: parts.append("спокойно")
        elif v < -0.3: parts.append("больно, тяжёло")
        elif v < 0: parts.append("неприятно")
        
        a = dims[PhenomenalDimension.AROUSAL]
        if a > 0.7: parts.append("сердце колотится")
        elif a > 0.5: parts.append("настороженность")
        
        s = dims[PhenomenalDimension.SURPRISE]
        if s > 0.6: parts.append("неожиданно!")
        elif s > 0.3: parts.append("что-то не так")
        
        n = dims[PhenomenalDimension.NOVELTY]
        if n > 0.6: parts.append("всё новое, невиданное")
        
        ag = dims[PhenomenalDimension.AGENCY]
        if ag > 0.7: parts.append("я решаю сама")
        elif ag < 0.3: parts.append("ничего не зависит от меня")
        
        return {
            "report": ", ".join(parts) if parts else "нейтрально",
            "dimensions": {d.value: round(v, 2) for d, v in dims.items()},
            "dominant": max(dims.items(), key=lambda x: x[1])[0].value,
            "intensity": max(dims.values()),
            "episode": self.current_episode.narrative_tag if self.current_episode else None
        }
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "current": {
                d.value: round(v, 3) for d, v in self.current_values.items()
            } if self.current_values else {},
            "current_raw": {
                d.value: round(v, 3) for d, v in self.current_state.dimensions.items()
            } if self.current_state else {},
            "baselines": {d.value: v for d, v in self.baselines.items()},
            "episodes": len(self.episodes),
            "current_episode": {
                "tag": self.current_episode.narrative_tag,
                "duration": time.time() - self.current_episode.start_time,
                "dominant": {d.value: round(v, 2) for d, v in self.current_episode.dominant_dimensions.items()}
            } if self.current_episode else None,
            "metrics": self.metrics
        }


def create_phenomenal_engine(agent_id: str) -> PhenomenalEngine:
    return PhenomenalEngine(agent_id)