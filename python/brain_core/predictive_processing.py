# brain_core/predictive_processing.py
"""
Predictive Processing / Active Inference / Free Energy Principle implementation.
Based on Friston (2010), Clark (2013), Hohwy (2013), Parr et al. (2022).

Core ideas:
- Brain is a prediction machine minimizing variational free energy (surprise)
- Hierarchical generative model: top-down predictions, bottom-up prediction errors
- Precision weighting: attention = precision of prediction errors
- Action = making sensory input match predictions (active inference)
- Learning = updating generative model to reduce future surprise
"""
from __future__ import annotations
import time
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import numpy as np

@dataclass
class PredictionLevel:
    """One level in the predictive hierarchy"""
    level: int                          # 0 = sensory, higher = more abstract
    name: str
    prediction: Dict[str, float]        # top-down prediction
    prediction_error: Dict[str, float]  # bottom-up error (surprise)
    precision: Dict[str, float]         # precision (inverse variance) = attention
    prior: Dict[str, float]             # prior belief
    posterior: Dict[str, float]         # updated belief after evidence
    
    # Learning
    learning_rate: float = 0.1
    precision_learning_rate: float = 0.05

@dataclass
class SurpriseEvent:
    """Record of a surprise/minimization event"""
    timestamp: float
    level: int
    modality: str
    prediction: float
    actual: float
    error: float
    precision: float
    free_energy: float
    action_taken: Optional[str] = None
    error_reduced: bool = False

class PredictiveProcessor:
    """
    Hierarchical Predictive Processing for Kato.
    
    Architecture:
    Level 3: Abstract concepts, goals, self-model, narrative
    Level 2: Objects, agents, situations, affordances
    Level 1: Features, patterns, spatial relations
    Level 0: Raw sensory (vision, interoception, proprioception)
    
    Each level predicts the level below. Errors propagate up, predictions down.
    Precision (attention) gates error propagation.
    """
    
    def __init__(self, agent_id: str, n_levels: int = 4):
        self.agent_id = agent_id
        self.n_levels = n_levels
        
        # Hierarchy levels
        self.levels: List[PredictionLevel] = []
        self._init_hierarchy()
        
        # Surprise tracking (for metacognition)
        self.surprise_history: deque = deque(maxlen=500)
        self.total_free_energy = 0.0
        
        # Precision/attention dynamics
        self.global_precision = 1.0
        self.precision_adaptation_rate = 0.02
        
        # Active inference: action to minimize prediction error
        self.action_proposals: List[Dict] = []
        
        # Metrics
        self.metrics = {
            "total_surprise_events": 0,
            "free_energy_trend": [],
            "precision_changes": 0,
            "actions_from_inference": 0,
            "model_updates": 0,
        }
        
        # Brain reference
        self._brain = None
    
    def _init_hierarchy(self):
        """Initialize predictive hierarchy levels"""
        level_configs = [
            {"level": 0, "name": "sensory", "lr": 0.15, "plr": 0.08},
            {"level": 1, "name": "features", "lr": 0.1, "plr": 0.05},
            {"level": 2, "name": "objects_situations", "lr": 0.08, "plr": 0.03},
            {"level": 3, "name": "abstract_self", "lr": 0.05, "plr": 0.02},
        ]
        
        for cfg in level_configs[:self.n_levels]:
            level = PredictionLevel(
                level=cfg["level"],
                name=cfg["name"],
                prediction={},
                prediction_error={},
                precision={},
                prior={},
                posterior={},
                learning_rate=cfg["lr"],
                precision_learning_rate=cfg["plr"]
            )
            self.levels.append(level)
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    def predict(self, modality: str, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Generate top-down predictions for a modality.
        Higher levels predict lower levels.
        """
        predictions = {}
        
        # Start from highest level (abstract) down to sensory
        for level in reversed(self.levels):
            level_key = f"{level.name}_{modality}"
            
            # Prior from this level's model
            prior = level.prior.get(level_key, 0.5)
            
            # Top-down prediction from level above (if not top)
            if level.level < self.n_levels - 1:
                higher = self.levels[level.level + 1]
                top_down = higher.prediction.get(level_key, prior)
            else:
                top_down = prior
            
            # Combined prediction (precision-weighted)
            prec_prior = level.precision.get(level_key, 1.0)
            prec_top = 1.0  # would come from higher level precision
            
            if prec_prior + prec_top > 0:
                prediction = (prior * prec_prior + top_down * prec_top) / (prec_prior + prec_top)
            else:
                prediction = 0.5
            
            level.prediction[level_key] = prediction
            predictions[level.name] = prediction
        
        return predictions
    
    def compute_prediction_error(self, modality: str, actual: Dict[str, float]) -> Dict[str, float]:
        """
        Compute bottom-up prediction errors (surprise).
        Error = actual - prediction, precision-weighted.
        """
        errors = {}
        
        for level in self.levels:
            level_key = f"{level.name}_{modality}"
            prediction = level.prediction.get(level_key, 0.5)
            actual_val = actual.get(level_key, 0.5)
            
            # Raw error
            raw_error = actual_val - prediction
            
            # Precision-weighted error (this IS the prediction error signal)
            precision = level.precision.get(level_key, 1.0)
            weighted_error = raw_error * precision
            
            level.prediction_error[level_key] = weighted_error
            errors[level.name] = weighted_error
            
            # Compute variational free energy for this level
            # F = -ln p(actual) + KL(q||p) ≈ 0.5 * precision * error^2 + complexity
            free_energy = 0.5 * precision * (raw_error ** 2)
            self.total_free_energy += free_energy
            
            # Record surprise event if significant
            if abs(weighted_error) > 0.3:
                self._record_surprise(level.level, modality, prediction, actual_val, 
                                    weighted_error, precision, free_energy)
        
        return errors
    
    def _record_surprise(self, level: int, modality: str, prediction: float, 
                        actual: float, error: float, precision: float, free_energy: float):
        """Record significant surprise for metacognition"""
        event = SurpriseEvent(
            timestamp=time.time(),
            level=level,
            modality=modality,
            prediction=prediction,
            actual=actual,
            error=error,
            precision=precision,
            free_energy=free_energy
        )
        self.surprise_history.append(event)
        self.metrics["total_surprise_events"] += 1
    
    def update_beliefs(self, modality: str):
        """
        Update posterior beliefs (learning) using prediction errors.
        This is the 'perceptual inference' step.
        """
        for level in self.levels:
            level_key = f"{level.name}_{modality}"
            error = level.prediction_error.get(level_key, 0.0)
            precision = level.precision.get(level_key, 1.0)
            
            # Update posterior (belief) using prediction error
            prior = level.prior.get(level_key, 0.5)
            lr = level.learning_rate
            
            # Gradient descent on free energy: posterior = prior + lr * precision * error
            posterior = prior + lr * precision * error
            posterior = max(0.0, min(1.0, posterior))  # clamp
            
            level.posterior[level_key] = posterior
            
            # Update prior for next cycle (slow learning)
            level.prior[level_key] = prior + lr * 0.1 * (posterior - prior)
            
            self.metrics["model_updates"] += 1
    
    def update_precision(self, modality: str, performance_feedback: float = None):
        """
        Precision learning: adjust attention based on prediction accuracy.
        High precision when predictions are reliable, low when noisy.
        This implements 'attention as precision weighting'.
        """
        for level in self.levels:
            level_key = f"{level.name}_{modality}"
            error = level.prediction_error.get(level_key, 0.0)
            current_prec = level.precision.get(level_key, 1.0)
            
            # Precision should track inverse variance of errors
            # If errors are consistently small → increase precision (trust this channel)
            # If errors are large/unpredictable → decrease precision
            error_magnitude = abs(error)
            
            # Target precision: inverse of recent error variance
            target_prec = 1.0 / (0.1 + error_magnitude)
            target_prec = max(0.1, min(10.0, target_prec))
            
            # Smooth adaptation
            plr = level.precision_learning_rate
            new_prec = current_prec + plr * (target_prec - current_prec)
            level.precision[level_key] = new_prec
            
            # Also adjust global precision
            self.global_precision = 0.99 * self.global_precision + 0.01 * target_prec
            self.metrics["precision_changes"] += 1
    
    def propose_actions(self, modality: str, goal_predictions: Dict[str, float]) -> List[Dict]:
        """
        Active Inference: propose actions to minimize expected free energy.
        Action makes sensory input match predictions.
        """
        proposals = []
        
        for level in self.levels:
            level_key = f"{level.name}_{modality}"
            prediction = level.prediction.get(level_key, 0.5)
            goal = goal_predictions.get(level_key, prediction)
            
            # Expected free energy if we act to achieve goal
            # G = risk (divergence from goal) + ambiguity (expected uncertainty)
            risk = abs(prediction - goal)
            ambiguity = 1.0 / (level.precision.get(level_key, 1.0) + 0.1)
            
            expected_fe = risk + 0.3 * ambiguity
            
            if expected_fe > 0.3:  # Worth acting
                proposals.append({
                    "level": level.level,
                    "level_name": level.name,
                    "modality": modality,
                    "current_prediction": prediction,
                    "goal": goal,
                    "expected_free_energy": expected_fe,
                    "risk": risk,
                    "ambiguity": ambiguity,
                    "suggested_action": f"act_to_match_{level_key}",
                    "confidence": level.precision.get(level_key, 1.0) / 10.0
                })
        
        # Sort by expected free energy reduction potential
        proposals.sort(key=lambda p: p["expected_free_energy"], reverse=True)
        self.action_proposals = proposals[:3]  # Top 3
        self.metrics["actions_from_inference"] += len(self.action_proposals)
        
        return self.action_proposals
    
    def step(self, perception: Dict[str, Any], goals: Dict[str, Any] = None):
        """
        Main predictive processing step:
        1. Predict (top-down)
        2. Compute errors (bottom-up)
        3. Update beliefs (perceptual inference)
        4. Update precision (attention learning)
        5. Propose actions (active inference)
        """
        modalities = ["visual", "interoceptive", "social", "spatial"]
        
        for modality in modalities:
            actual = self._extract_actual(perception, modality)
            if not actual:
                continue
            
            # 1. Predict
            self.predict(modality, perception)
            
            # 2. Compute prediction errors
            self.compute_prediction_error(modality, actual)
            
            # 3. Update beliefs
            self.update_beliefs(modality)
            
            # 4. Update precision
            self.update_precision(modality)
            
            # 5. Propose actions (active inference)
            if goals:
                self.propose_actions(modality, goals)
        
        # Track free energy trend
        self.metrics["free_energy_trend"].append(self.total_free_energy)
        if len(self.metrics["free_energy_trend"]) > 100:
            self.metrics["free_energy_trend"] = self.metrics["free_energy_trend"][-100:]
        
        # Reset for next step
        self.total_free_energy = 0.0
        
        # Return results for consciousness integration
        return {
            "recent_surprises": list(self.surprise_history)[-20:],
            "levels": [
                {
                    "name": l.name,
                    "predictions": l.prediction,
                    "errors": l.prediction_error,
                    "precision": l.precision,
                }
                for l in self.levels
            ],
            "action_proposals": self.action_proposals,
            "global_precision": self.global_precision,
        }
    
    def _extract_actual(self, perception: Dict, modality: str) -> Dict[str, float]:
        """Extract actual sensory values for a modality from perception"""
        actual = {}
        
        if modality == "visual":
            # Objects in view
            objects = perception.get("nearby_objects", [])
            actual["sensory_objects"] = min(1.0, len(objects) / 10.0)
            # Specific object predictions
            for obj in objects[:3]:
                actual[f"sensory_{obj.get('id', 'unknown')}"] = 1.0
            
        elif modality == "interoceptive":
            body = perception.get("agent", {})
            actual["intero_energy"] = body.get("energy", 50) / 100.0
            actual["intero_comfort"] = body.get("comfort", 50) / 100.0
            actual["intero_stress"] = body.get("stress", 50) / 100.0
            
        elif modality == "social":
            npcs = perception.get("nearby_npcs", [])
            actual["social_presence"] = min(1.0, len(npcs) / 5.0)
            for npc in npcs[:2]:
                actual[f"social_{npc.get('id', 'unknown')}"] = 1.0
                
        elif modality == "spatial":
            pos = perception.get("agent", {}).get("position", [0, 0])
            actual["spatial_x"] = pos[0] / 50.0
            actual["spatial_y"] = pos[1] / 30.0
        
        return actual
    
    def get_conscious_access_candidates(self) -> List[Dict]:
        """
        Items with high prediction error (surprise) compete for global workspace access.
        This links PP to GWT: surprise → attention → conscious access.
        """
        candidates = []
        
        for event in list(self.surprise_history)[-20:]:
            if abs(event.error) > 0.4:
                candidates.append({
                    "source": f"predictive_{event.modality}_L{event.level}",
                    "content": {
                        "modality": event.modality,
                        "level": event.level,
                        "prediction": event.prediction,
                        "actual": event.actual,
                        "surprise": event.error,
                        "free_energy": event.free_energy
                    },
                    "activation": min(1.0, abs(event.error) * event.precision),
                    "metadata": {"type": "surprise", "precision": event.precision}
                })
        
        return candidates
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "levels": [
                {
                    "name": l.name,
                    "predictions": l.prediction,
                    "errors": l.prediction_error,
                    "precision": l.precision,
                    "priors": l.prior,
                    "posteriors": l.posterior
                }
                for l in self.levels
            ],
            "global_precision": self.global_precision,
            "total_free_energy": self.total_free_energy,
            "recent_surprises": len(self.surprise_history),
            "action_proposals": self.action_proposals,
            "metrics": self.metrics
        }


def create_predictive_processor(agent_id: str) -> PredictiveProcessor:
    return PredictiveProcessor(agent_id)