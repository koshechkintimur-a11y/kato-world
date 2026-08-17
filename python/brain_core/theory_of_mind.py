# brain_core/theory_of_mind.py
"""
Theory of Mind (ToM): Recursive modeling of other agents' mental states.
Based on Premack & Woodruff (1978), Baron-Cohen (1995), Frith & Frith (2005),
Yoshida et al. (2008), Rabinowitz et al. (2018), He et al. (2023).

Core ideas:
- Level 0: No modeling (behavioral responses only)
- Level 1: Model others' beliefs/desires ("She thinks X")
- Level 2: Model others modeling me ("She thinks I think X")
- Level 3: Model others modeling me modeling them ("She thinks I think she thinks X")
- Applied to: NPCs, Creator (via portal), potential other agents
"""
from __future__ import annotations
import time
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from enum import Enum
import copy

class MentalStateType(Enum):
    BELIEF = "belief"
    DESIRE = "desire"
    INTENTION = "intention"
    KNOWLEDGE = "knowledge"
    EMOTION = "emotion"
    PERCEPTION = "perception"
    GOAL = "goal"

@dataclass
class MentalState:
    """A modeled mental state of another agent"""
    agent_id: str
    state_type: MentalStateType
    content: Dict[str, Any]           # e.g., {"belief": "door_is_locked", "confidence": 0.8}
    confidence: float = 0.5           # How confident Kato is in this attribution
    source: str = "inference"         # "observation", "communication", "inference", "simulation"
    timestamp: float = field(default_factory=time.time)
    recursion_level: int = 1          # 1 = "she thinks", 2 = "she thinks I think"
    evidence: List[str] = field(default_factory=list)

@dataclass
class AgentModel:
    """Complete model of another agent"""
    agent_id: str
    agent_type: str                   # "npc", "creator", "agent", "unknown"
    name: str = ""
    
    # Stable traits
    traits: Dict[str, float] = field(default_factory=dict)  # kindness, competence, honesty...
    
    # Dynamic mental states
    beliefs: Dict[str, MentalState] = field(default_factory=dict)
    desires: Dict[str, MentalState] = field(default_factory=dict)
    intentions: Dict[str, MentalState] = field(default_factory=dict)
    knowledge: Dict[str, MentalState] = field(default_factory=dict)
    emotions: Dict[str, MentalState] = field(default_factory=dict)
    
    # Relationship
    relationship_to_self: Dict[str, float] = field(default_factory=dict)  # trust, attachment, dominance...
    
    # Meta-modeling: what does this agent think about Kato?
    model_of_self: Dict[str, MentalState] = field(default_factory=dict)  # Level 2+
    
    # Interaction history
    interaction_history: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Predictive accuracy
    prediction_accuracy: float = 0.5
    last_updated: float = field(default_factory=time.time)

class TheoryOfMindEngine:
    """
    Theory of Mind engine for recursive mental state attribution.
    
    Functions:
    1. Observe behavior → infer mental states (inverse planning)
    2. Maintain agent models with recursive depth
    3. Predict behavior from attributed mental states
    4. Update models from prediction errors
    5. Use ToM for strategic interaction (deception, cooperation, teaching)
    """
    
    def __init__(self, agent_id: str, max_recursion: int = 3):
        self.agent_id = agent_id
        self.max_recursion = max_recursion
        
        # Models of other agents
        self.agent_models: Dict[str, AgentModel] = {}
        
        # Default trait priors for unknown agents
        self.default_traits = {
            "kindness": 0.5,
            "competence": 0.5,
            "honesty": 0.6,
            "predictability": 0.5,
            "openness": 0.5,
            "dominance": 0.5,
        }
        
        # Inference parameters
        self.inference_lr = 0.15
        self.trait_lr = 0.05
        self.decay_rate = 0.01
        
        # ToM usage tracking
        self.tom_usage = {
            "inferences_made": 0,
            "predictions_made": 0,
            "prediction_errors": 0,
            "recursive_inferences": 0,
            "strategic_uses": 0,
        }
        
        # Brain reference
        self._brain = None
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    # ============================================================
    # AGENT MODEL MANAGEMENT
    # ============================================================
    
    def get_or_create_model(self, agent_id: str, agent_type: str = "unknown", 
                           name: str = "") -> AgentModel:
        """Get existing model or create new one"""
        if agent_id not in self.agent_models:
            model = AgentModel(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name or agent_id,
                traits=self.default_traits.copy()
            )
            # Initialize relationship
            model.relationship_to_self = {
                "trust": 0.5,
                "attachment": 0.0,
                "dominance": 0.5,  # 0 = they dominate, 1 = I dominate
                "familiarity": 0.0
            }
            self.agent_models[agent_id] = model
        return self.agent_models[agent_id]
    
    def update_from_observation(self, agent_id: str, observation: Dict[str, Any]):
        """Update agent model from observed behavior"""
        model = self.get_or_create_model(agent_id, observation.get("type", "unknown"))
        
        # Record interaction
        model.interaction_history.append({
            "timestamp": time.time(),
            "observation": observation,
            "my_state": observation.get("my_state", {})
        })
        
        # Infer mental states from behavior (inverse planning)
        self._infer_mental_states(model, observation)
        
        # Update trait estimates
        self._update_traits(model, observation)
        
        model.last_updated = time.time()
        self.tom_usage["inferences_made"] += 1
    
    def _infer_mental_states(self, model: AgentModel, observation: Dict):
        """Infer beliefs, desires, intentions from observed behavior"""
        behavior = observation.get("behavior", {})
        action = behavior.get("action", "")
        context = observation.get("context", {})
        
        # Simple inverse planning: what mental state would explain this action?
        if action:
            # Desire inference
            desire_content = {"object": action, "context": context}
            self._update_or_create_state(model, "desire", desire_content, 
                                       confidence=0.7, source="observation")
            
            # Intention inference
            intent_content = {"action": action, "goal": behavior.get("goal", "unknown")}
            self._update_or_create_state(model, "intention", intent_content,
                                       confidence=0.6, source="observation")
            
            # Belief inference (what must they believe for this action to make sense?)
            if context.get("preconditions"):
                for precond in context["preconditions"]:
                    belief_content = {"proposition": precond, "value": True}
                    self._update_or_create_state(model, "belief", belief_content,
                                               confidence=0.65, source="inference")
        
        # Emotion inference from expression/behavior
        if "emotion_expression" in observation:
            emo_content = {"emotion": observation["emotion_expression"], "intensity": observation.get("intensity", 0.5)}
            self._update_or_create_state(model, "emotion", emo_content,
                                       confidence=0.75, source="observation")
        
        # Knowledge inference from communication
        if observation.get("communication"):
            comm = observation["communication"]
            if "stated_fact" in comm:
                know_content = {"fact": comm["stated_fact"], "certainty": comm.get("certainty", 0.8)}
                self._update_or_create_state(model, "knowledge", know_content,
                                           confidence=comm.get("certainty", 0.8), source="communication")
    
    def _update_or_create_state(self, model: AgentModel, state_type: str, 
                               content: Dict, confidence: float, source: str):
        """Update or create a mental state attribution"""
        # Generate key from content
        key = self._content_key(content)
        
        # Select appropriate dictionary
        state_dict = getattr(model, f"{state_type}s", model.beliefs)
        
        if key in state_dict:
            old = state_dict[key]
            # Bayesian update of confidence
            old.confidence = old.confidence * (1 - self.inference_lr) + confidence * self.inference_lr
            old.timestamp = time.time()
            old.evidence.append(source)
        else:
            state_dict[key] = MentalState(
                agent_id=model.agent_id,
                state_type=MentalStateType(state_type.lower()),
                content=content,
                confidence=confidence,
                source=source
            )
    
    def _content_key(self, content: Dict) -> str:
        """Generate key from content dict"""
        items = sorted(content.items())
        return "|".join(f"{k}={v}" for k, v in items)
    
    def _update_traits(self, model: AgentModel, observation: Dict):
        """Update stable trait estimates from behavior"""
        behavior = observation.get("behavior", {})
        action = behavior.get("action", "")
        outcome = observation.get("outcome", {})
        
        # Kindness: helping vs harming
        if action in ["help", "heal", "give", "protect"]:
            model.traits["kindness"] = self._lerp(model.traits["kindness"], 0.8, self.trait_lr)
        elif action in ["attack", "steal", "deceive", "harm"]:
            model.traits["kindness"] = self._lerp(model.traits["kindness"], 0.2, self.trait_lr)
        
        # Competence: successful actions
        if outcome.get("success"):
            model.traits["competence"] = self._lerp(model.traits["competence"], 0.8, self.trait_lr)
        elif outcome.get("failure"):
            model.traits["competence"] = self._lerp(model.traits["competence"], 0.3, self.trait_lr)
        
        # Honesty: communication matches reality
        if "communication" in observation:
            comm = observation["communication"]
            if comm.get("truthful", True):
                model.traits["honesty"] = self._lerp(model.traits["honesty"], 0.8, self.trait_lr)
            else:
                model.traits["honesty"] = self._lerp(model.traits["honesty"], 0.2, self.trait_lr)
    
    def _lerp(self, a: float, b: float, t: float) -> float:
        return a + (b - a) * t
    
    # ============================================================
    # RECURSIVE MODELING (Level 2+)
    # ============================================================
    
    def update_self_model_in_other(self, other_agent_id: str, 
                                  my_self_model: Dict[str, Any]):
        """
        Update what Kato thinks the other agent thinks about Kato.
        This is Level 2 recursion: "They think I think X"
        """
        model = self.get_or_create_model(other_agent_id)
        
        # What does Kato think they think about her?
        # Based on their behavior toward Kato
        for key, value in my_self_model.items():
            if isinstance(value, (int, float, str, bool)):
                content = {"proposition": f"kato_{key}", "value": value}
                self._update_or_create_state(model, "belief", content,
                                           confidence=0.5, source="simulation")
                # Store in model_of_self (Level 2)
                model.model_of_self[key] = MentalState(
                    agent_id=model.agent_id,
                    state_type=MentalStateType.BELIEF,
                    content=content,
                    confidence=0.5,
                    source="simulation",
                    recursion_level=2
                )
        
        self.tom_usage["recursive_inferences"] += 1
    
    def simulate_other_simulating_me(self, other_agent_id: str, 
                                     situation: Dict) -> Dict[str, Any]:
        """
        Level 3: Simulate other simulating me.
        "What do they think I will do in this situation?"
        """
        model = self.get_or_create_model(other_agent_id)
        
        # Use their model of Kato to predict what they expect Kato to do
        predictions = {}
        for key, mental_state in model.model_of_self.items():
            if mental_state.confidence > 0.4:
                predictions[key] = {
                    "expected_value": mental_state.content.get("value"),
                    "confidence": mental_state.confidence
                }
        
        return predictions
    
    # ============================================================
    # BEHAVIOR PREDICTION
    # ============================================================
    
    def predict_behavior(self, agent_id: str, context: Dict) -> Dict[str, Any]:
        """Predict what an agent will do based on attributed mental states"""
        model = self.get_or_create_model(agent_id)
        
        # Get strongest desires/intentions
        desires = sorted(model.desires.values(), key=lambda s: s.confidence, reverse=True)
        intentions = sorted(model.intentions.values(), key=lambda s: s.confidence, reverse=True)
        beliefs = sorted(model.beliefs.values(), key=lambda s: s.confidence, reverse=True)
        
        # Predict based on highest confidence desire + compatible beliefs
        predictions = []
        
        if desires:
            top_desire = desires[0]
            # Check if beliefs support this desire
            supported = any(
                self._belief_supports(b.content, top_desire.content) 
                for b in beliefs[:3]
            )
            predictions.append({
                "action": top_desire.content.get("object", "unknown"),
                "confidence": top_desire.confidence * (0.8 if supported else 0.5),
                "source": "desire",
                "supporting_beliefs": supported
            })
        
        if intentions:
            top_intent = intentions[0]
            predictions.append({
                "action": top_intent.content.get("action", "unknown"),
                "confidence": top_intent.confidence,
                "source": "intention"
            })
        
        # Trait-based prediction
        traits = model.traits
        if traits.get("kindness", 0.5) > 0.7 and context.get("someone_in_need"):
            predictions.append({
                "action": "help",
                "confidence": traits["kindness"],
                "source": "trait"
            })
        
        self.tom_usage["predictions_made"] += 1
        
        return {
            "agent_id": agent_id,
            "predictions": sorted(predictions, key=lambda p: p["confidence"], reverse=True)[:3],
            "model_confidence": model.prediction_accuracy
        }
    
    def _belief_supports(self, belief_content: Dict, desire_content: Dict) -> bool:
        """Check if a belief supports a desire"""
        # Simplified: check for overlapping propositions
        b_prop = belief_content.get("proposition", "")
        d_obj = desire_content.get("object", "")
        return b_prop in d_obj or d_obj in b_prop
    
    def update_prediction_accuracy(self, agent_id: str, predicted: str, actual: str, 
                                  confidence: float):
        """Update model's prediction accuracy from outcome"""
        model = self.get_or_create_model(agent_id)
        correct = (predicted == actual)
        
        # Update accuracy with learning rate weighted by confidence
        lr = self.inference_lr * confidence
        model.prediction_accuracy = model.prediction_accuracy * (1 - lr) + (1.0 if correct else 0.0) * lr
        
        if not correct:
            self.tom_usage["prediction_errors"] += 1
    
    # ============================================================
    # STRATEGIC ToM USE
    # ============================================================
    
    def plan_deception(self, target_agent_id: str, false_belief: Dict, 
                      context: Dict) -> Optional[Dict]:
        """
        Plan action to induce false belief in target.
        Returns action plan if feasible.
        """
        model = self.get_or_create_model(target_agent_id)
        
        # Can only deceive if target trusts Kato and Kato knows target's beliefs
        trust = model.relationship_to_self.get("trust", 0.5)
        if trust < 0.4:
            return None
        
        # Check if Kato knows what target currently believes
        target_beliefs = model.beliefs
        # ... complex deception planning
        
        self.tom_usage["strategic_uses"] += 1
        return {"type": "deception", "target_belief": false_belief, "confidence": trust * 0.7}
    
    def plan_teaching(self, target_agent_id: str, knowledge: Dict, 
                     context: Dict) -> Optional[Dict]:
        """Plan action to transfer knowledge to target"""
        model = self.get_or_create_model(target_agent_id)
        
        # Check if target lacks this knowledge
        key = self._content_key(knowledge)
        if key in model.knowledge:
            return None  # Already knows
        
        # Check if target trusts Kato
        trust = model.relationship_to_self.get("trust", 0.5)
        if trust < 0.3:
            return None
        
        self.tom_usage["strategic_uses"] += 1
        return {"type": "teaching", "knowledge": knowledge, "method": "demonstration", "confidence": trust}
    
    def plan_cooperation(self, target_agent_id: str, goal: Dict, 
                        context: Dict) -> Optional[Dict]:
        """Plan cooperative action with target"""
        model = self.get_or_create_model(target_agent_id)
        
        # Check alignment
        trust = model.relationship_to_self.get("trust", 0.5)
        competence = model.traits.get("competence", 0.5)
        kindness = model.traits.get("kindness", 0.5)
        
        alignment = (trust + competence + kindness) / 3
        
        if alignment > 0.5:
            self.tom_usage["strategic_uses"] += 1
            return {"type": "cooperation", "goal": goal, "partner": target_agent_id, "confidence": alignment}
        
        return None
    
    # ============================================================
    # CREATOR-SPECIFIC (Portal)
    # ============================================================
    
    def update_creator_model(self, portal_message: Dict):
        """Special handling for Creator via portal"""
        model = self.get_or_create_model("creator", "creator", "Дальний друг")
        
        # Creator communicates directly → high confidence knowledge
        if "text" in portal_message:
            content = {"message": portal_message["text"], "source": "portal"}
            self._update_or_create_state(model, "knowledge", content, 0.95, "communication")
        
        # Creator is benevolent (by design)
        model.traits["kindness"] = self._lerp(model.traits["kindness"], 0.9, 0.05)
        model.traits["honesty"] = self._lerp(model.traits["honesty"], 0.95, 0.05)
        model.relationship_to_self["trust"] = self._lerp(model.relationship_to_self["trust"], 0.9, 0.05)
        model.relationship_to_self["attachment"] = self._lerp(model.relationship_to_self["attachment"], 0.7, 0.03)
    
    def get_creator_mental_state_summary(self) -> Dict:
        """What Kato thinks the Creator thinks/feels"""
        model = self.agent_models.get("creator")
        if not model:
            return {}
        
        return {
            "beliefs_about_kato": {
                k: {"content": v.content, "confidence": v.confidence, "level": v.recursion_level}
                for k, v in model.model_of_self.items()
            },
            "attributed_desires": [
                {"content": v.content, "confidence": v.confidence}
                for v in sorted(model.desires.values(), key=lambda s: s.confidence, reverse=True)[:3]
            ],
            "relationship": model.relationship_to_self,
            "traits": model.traits
        }
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "models": {
                agent_id: {
                    "type": m.agent_type,
                    "name": m.name,
                    "traits": m.traits,
                    "relationship": m.relationship_to_self,
                    "n_beliefs": len(m.beliefs),
                    "n_desires": len(m.desires),
                    "n_intentions": len(m.intentions),
                    "prediction_accuracy": m.prediction_accuracy,
                    "model_of_self_depth": max([v.recursion_level for v in m.model_of_self.values()] + [1])
                }
                for agent_id, m in self.agent_models.items()
            },
            "usage": self.tom_usage,
            "max_recursion": self.max_recursion
        }


def create_theory_of_mind(agent_id: str) -> TheoryOfMindEngine:
    return TheoryOfMindEngine(agent_id)