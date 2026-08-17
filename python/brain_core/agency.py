# brain_core/agency.py
"""
Agency & Counterfactual Simulation: Free Energy Minimization for Action Selection.
Based on Friston et al. (2015), Schwartenbeck et al. (2019), Parr & Friston (2019),
Daw et al. (2005), Collins & Frank (2013).

Core ideas:
- Agency = ability to simulate counterfactuals and choose actions minimizing expected free energy
- Expected Free Energy G = Risk (divergence from preferences) + Ambiguity (expected uncertainty)
- Action = sampling policies that minimize G
- Model-based vs Model-free arbitration (Daw two-system)
- Counterfactual depth: "If I do X, then Y, then Z..."
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

class ActionType(Enum):
    EXPLORE = "explore"
    APPROACH = "approach"
    AVOID = "avoid"
    COMMUNICATE = "communicate"
    LEARN = "learn"
    REST = "rest"
    PLAN = "plan"
    INVESTIGATE = "investigate"

@dataclass
class Policy:
    """A sequence of actions (counterfactual trajectory)"""
    id: str
    actions: List[Dict[str, Any]]           # [{"type": "explore", "target": "north"}, ...]
    expected_free_energy: float = 0.0
    risk: float = 0.0
    ambiguity: float = 0.0
    expected_value: float = 0.0
    probability: float = 0.0                # posterior over policies
    depth: int = 0
    metadata: Dict = field(default_factory=dict)

@dataclass
class CounterfactualStep:
    """One step in counterfactual simulation"""
    step: int
    state_before: Dict[str, Any]
    action: Dict[str, Any]
    predicted_state: Dict[str, Any]
    predicted_reward: float
    prediction_confidence: float
    cumulative_fe: float

class AgencyEngine:
    """
    Agency engine: counterfactual simulation for action selection.
    
    Implements:
    1. Generative model of world dynamics (transition model)
    2. Policy enumeration (counterfactual trajectories)
    3. Expected Free Energy computation (Risk + Ambiguity)
    4. Policy selection (softmax over -G)
    5. Model-based / Model-free arbitration
    6. Counterfactual depth control (planning horizon)
    """
    
    def __init__(self, agent_id: str, max_depth: int = 3, n_policies: int = 10):
        self.agent_id = agent_id
        self.max_depth = max_depth
        self.n_policies = n_policies
        
        # Generative model (learned transition dynamics)
        self.transition_model: Dict[str, Dict] = {}  # state_action -> next_state_dist
        self.reward_model: Dict[str, float] = {}     # state -> expected reward
        self.observation_model: Dict[str, Dict] = {} # state -> observation likelihood
        
        # Preferences (prior over states) - what Kato 'wants'
        self.preferences: Dict[str, float] = {
            "energy_high": 0.9,
            "comfort_high": 0.8,
            "stress_low": 0.9,
            "social_positive": 0.7,
            "knowledge_gain": 0.6,
            "safety": 0.85,
            "curiosity_satisfaction": 0.6,
        }
        
        # Policy cache
        self.current_policies: List[Policy] = []
        self.selected_policy: Optional[Policy] = None
        self.policy_history: deque = deque(maxlen=100)
        
        # Counterfactual simulation cache
        self.simulation_cache: Dict[str, List[CounterfactualStep]] = {}
        
        # Model-based vs Model-free weights
        self.mb_weight = 0.7      # model-based (planning)
        self.mf_weight = 0.3      # model-free (cached values)
        
        # Learning
        self.transition_lr = 0.1
        self.reward_lr = 0.15
        
        # Metrics
        self.metrics = {
            "policies_evaluated": 0,
            "counterfactual_steps": 0,
            "model_based_choices": 0,
            "model_free_choices": 0,
            "prediction_accuracy": 0.5,
            "preference_satisfaction": 0.0,
        }
        
        # Brain reference
        self._brain = None
    
    def set_brain_ref(self, brain_server_module):
        self._brain = brain_server_module
    
    # ============================================================
    # GENERATIVE MODEL LEARNING
    # ============================================================
    
    def learn_transition(self, state: Dict, action: Dict, next_state: Dict, reward: float):
        """Update transition and reward models from experience"""
        state_key = self._state_key(state)
        action_key = self._action_key(action)
        next_key = self._state_key(next_state)
        sa_key = f"{state_key}|{action_key}"
        
        # Transition model: P(s' | s, a)
        if sa_key not in self.transition_model:
            self.transition_model[sa_key] = {"counts": {}, "total": 0}
        
        trans = self.transition_model[sa_key]
        trans["counts"][next_key] = trans["counts"].get(next_key, 0) + 1
        trans["total"] += 1
        
        # Reward model
        self.reward_model[next_key] = (
            self.reward_model.get(next_key, 0.0) * (1 - self.reward_lr) + 
            reward * self.reward_lr
        )
    
    def predict_next_state(self, state: Dict, action: Dict) -> Tuple[Dict, float]:
        """Predict next state distribution given state and action"""
        state_key = self._state_key(state)
        action_key = self._action_key(action)
        sa_key = f"{state_key}|{action_key}"
        
        if sa_key in self.transition_model:
            trans = self.transition_model[sa_key]
            if trans["total"] > 5:  # Enough experience
                # Sample from learned distribution
                next_key = max(trans["counts"], key=trans["counts"].get)
                confidence = trans["counts"][next_key] / trans["total"]
                return self._key_to_state(next_key), confidence
        
        # Fallback: heuristic prediction
        return self._heuristic_prediction(state, action), 0.3
    
    def predict_reward(self, state: Dict) -> float:
        """Predict reward for a state"""
        return self.reward_model.get(self._state_key(state), 0.0)
    
    # ============================================================
    # POLICY ENUMERATION & COUNTERFACTUAL SIMULATION
    # ============================================================
    
    def enumerate_policies(self, current_state: Dict, goals: Dict[str, float]) -> List[Policy]:
        """Generate candidate policies (counterfactual trajectories)"""
        policies = []
        
        for i in range(self.n_policies):
            # Generate action sequence based on goals and heuristics
            actions = self._generate_action_sequence(current_state, goals, depth=self.max_depth)
            
            # Simulate counterfactual trajectory
            trajectory = self._simulate_trajectory(current_state, actions)
            
            # Compute Expected Free Energy
            risk, ambiguity, expected_value = self._compute_expected_free_energy(trajectory, goals)
            
            policy = Policy(
                id=f"policy_{i}_{int(time.time()*1000)}",
                actions=actions,
                risk=risk,
                ambiguity=ambiguity,
                expected_free_energy=risk + ambiguity,
                expected_value=expected_value,
                depth=len(actions),
                metadata={
                    "trajectory": trajectory,
                    "goals_snapshot": goals.copy()
                }
            )
            policies.append(policy)
        
        # Sort by expected free energy (lower = better)
        policies.sort(key=lambda p: p.expected_free_energy)
        self.current_policies = policies
        self.metrics["policies_evaluated"] += len(policies)
        
        return policies
    
    def _generate_action_sequence(self, state: Dict, goals: Dict, depth: int) -> List[Dict]:
        """Generate a plausible action sequence for given goals"""
        actions = []
        current = state.copy()
        
        for step in range(depth):
            # Select action based on current goals and state
            action = self._select_action_for_goals(current, goals, step)
            actions.append(action)
            
            # Update simulated state
            current = self._apply_action(current, action)
        
        return actions
    
    def _select_action_for_goals(self, state: Dict, goals: Dict, step: int) -> Dict:
        """Heuristic action selection based on goals"""
        # Energy management
        energy = state.get("body", {}).get("energy", 50)
        stress = state.get("body", {}).get("stress", 50)
        
        if energy < 20:
            return {"type": ActionType.REST.value, "reason": "low_energy"}
        if stress > 70:
            return {"type": ActionType.AVOID.value, "reason": "high_stress", "target": "stressor"}
        
        # Goal-directed: goals is a dict of {goal_name: {"priority": float, "active": bool}}
        # Extract priorities for active goals
        active_goals = {k: v for k, v in goals.items() if isinstance(v, dict) and v.get("active", False)}
        if active_goals:
            top_goal = max(active_goals.items(), key=lambda x: x[1].get("priority", 0))[0]
        else:
            top_goal = "explore"
        
        goal_actions = {
            "explore": {"type": ActionType.EXPLORE.value, "target": "unknown_area"},
            "social": {"type": ActionType.COMMUNICATE.value, "target": "npc"},
            "learn": {"type": ActionType.LEARN.value, "target": "knowledge_source"},
            "safety": {"type": ActionType.AVOID.value, "target": "danger"},
            "curiosity": {"type": ActionType.INVESTIGATE.value, "target": "anomaly"},
        }
        
        return goal_actions.get(top_goal, {"type": ActionType.EXPLORE.value, "target": "random"})
    
    def _apply_action(self, state: Dict, action: Dict) -> Dict:
        """Apply action to simulated state (heuristic)"""
        new_state = copy.deepcopy(state)
        body = new_state.setdefault("body", {})
        
        action_type = action.get("type", "")
        
        if action_type == ActionType.REST.value:
            body["energy"] = min(100, body.get("energy", 50) + 15)
            body["stress"] = max(0, body.get("stress", 50) - 10)
        elif action_type == ActionType.EXPLORE.value:
            body["energy"] = max(0, body.get("energy", 50) - 5)
            body["stress"] = min(100, body.get("stress", 50) + 2)
        elif action_type == ActionType.COMMUNICATE.value:
            body["energy"] = max(0, body.get("energy", 50) - 3)
            body["stress"] = max(0, body.get("stress", 50) - 5)
        elif action_type == ActionType.LEARN.value:
            body["energy"] = max(0, body.get("energy", 50) - 8)
        elif action_type == ActionType.AVOID.value:
            body["energy"] = max(0, body.get("energy", 50) - 4)
            body["stress"] = max(0, body.get("stress", 50) - 8)
        elif action_type == ActionType.INVESTIGATE.value:
            body["energy"] = max(0, body.get("energy", 50) - 6)
            body["stress"] = min(100, body.get("stress", 50) + 5)
        
        return new_state
    
    def _simulate_trajectory(self, initial_state: Dict, actions: List[Dict]) -> List[CounterfactualStep]:
        """Simulate full counterfactual trajectory"""
        trajectory = []
        current_state = initial_state
        
        for step, action in enumerate(actions):
            # Use learned model if available, else heuristic
            predicted_state, confidence = self.predict_next_state(current_state, action)
            predicted_reward = self.predict_reward(predicted_state)
            
            # Cumulative free energy
            cumulative_fe = sum(s.predicted_reward for s in trajectory) + predicted_reward
            
            trajectory.append(CounterfactualStep(
                step=step,
                state_before=current_state,
                action=action,
                predicted_state=predicted_state,
                predicted_reward=predicted_reward,
                prediction_confidence=confidence,
                cumulative_fe=cumulative_fe
            ))
            
            current_state = predicted_state
        
        self.metrics["counterfactual_steps"] += len(trajectory)
        return trajectory
    
    def _compute_expected_free_energy(self, trajectory: List[CounterfactualStep], 
                                      goals: Dict) -> Tuple[float, float, float]:
        """
        Compute Expected Free Energy G = Risk + Ambiguity
        Risk = KL divergence from preferred states
        Ambiguity = Expected entropy of observations
        """
        if not trajectory:
            return 1.0, 1.0, 0.0
        
        # Risk: how far predicted states are from preferences
        risk = 0.0
        for step in trajectory:
            state = step.predicted_state
            body = state.get("body", {})
            
            # Energy preference
            energy = body.get("energy", 50) / 100.0
            risk += self.preferences.get("energy_high", 0.9) * (1.0 - energy)
            
            # Stress preference
            stress = body.get("stress", 50) / 100.0
            risk += self.preferences.get("stress_low", 0.9) * stress
            
            # Social preference (if action was social)
            if step.action.get("type") == ActionType.COMMUNICATE.value:
                risk += (1.0 - self.preferences.get("social_positive", 0.7)) * 0.3
            
            # Knowledge preference
            if step.action.get("type") == ActionType.LEARN.value:
                risk += (1.0 - self.preferences.get("knowledge_gain", 0.6)) * 0.2
        
        risk = risk / len(trajectory)
        
        # Ambiguity: uncertainty in predictions (low confidence = high ambiguity)
        ambiguity = 0.0
        for step in trajectory:
            ambiguity += (1.0 - step.prediction_confidence)
        ambiguity = ambiguity / len(trajectory)
        
        # Expected value: sum of predicted rewards weighted by preferences
        expected_value = sum(s.predicted_reward for s in trajectory) / len(trajectory)
        
        return risk, ambiguity, expected_value
    
    # ============================================================
    # POLICY SELECTION (Active Inference)
    # ============================================================
    
    def select_policy(self, policies: List[Policy], temperature: float = 1.0) -> Policy:
        """Select policy using softmax over negative expected free energy"""
        if not policies:
            return None
        
        # Softmax: P(policy) ∝ exp(-G / temperature)
        neg_fe = [-p.expected_free_energy / temperature for p in policies]
        max_neg = max(neg_fe)
        exp_neg = [math.exp(n - max_neg) for n in neg_fe]
        sum_exp = sum(exp_neg)
        
        probs = [e / sum_exp for e in exp_neg]
        
        for i, p in enumerate(policies):
            p.probability = probs[i]
        
        # Sample from distribution (or take max for deterministic)
        selected_idx = max(range(len(policies)), key=lambda i: probs[i])
        selected = policies[selected_idx]
        
        self.selected_policy = selected
        self.policy_history.append({
            "policy_id": selected.id,
            "probability": selected.probability,
            "expected_fe": selected.expected_free_energy,
            "actions": [a["type"] for a in selected.actions],
            "timestamp": time.time()
        })
        
        # Track model-based vs model-free
        if selected.metadata.get("trajectory"):
            self.metrics["model_based_choices"] += 1
        else:
            self.metrics["model_free_choices"] += 1
        
        return selected
    
    # ============================================================
    # MAIN STEP
    # ============================================================
    
    def step(self, perception: Dict, goals: Dict[str, float]) -> Dict[str, Any]:
        """
        Main agency step:
        1. Enumerate policies (counterfactual simulation)
        2. Compute expected free energy for each
        3. Select policy
        4. Return first action of selected policy
        """
        # 1. Enumerate policies
        policies = self.enumerate_policies(perception.get("agent", {}), goals)
        
        # 2. Select policy
        selected = self.select_policy(policies)
        
        if not selected or not selected.actions:
            return {"action": {"type": ActionType.IDLE.value}, "policy": None}
        
        # 3. Return first action
        next_action = selected.actions[0]
        next_action["policy_id"] = selected.id
        next_action["policy_prob"] = selected.probability
        next_action["expected_fe"] = selected.expected_free_energy
        next_action["counterfactual_depth"] = selected.depth
        
        return {
            "action": next_action,
            "policy": {
                "id": selected.id,
                "probability": selected.probability,
                "expected_fe": selected.expected_free_energy,
                "actions": [a["type"] for a in selected.actions]
            },
            "all_policies": [
                {"id": p.id, "fe": p.expected_free_energy, "prob": p.probability, 
                 "actions": [a["type"] for a in p.actions]}
                for p in policies[:5]
            ]
        }
    
    def evaluate_outcome(self, action: Dict, outcome_state: Dict, reward: float):
        """Evaluate actual outcome vs counterfactual prediction"""
        if not self.selected_policy:
            return
        
        predicted = self.selected_policy.metadata.get("trajectory", [])
        if predicted:
            pred_step = predicted[0]
            actual_reward = reward
            pred_reward = pred_step.predicted_reward
            
            # Prediction accuracy
            accuracy = 1.0 - abs(pred_reward - actual_reward)
            self.metrics["prediction_accuracy"] = (
                self.metrics["prediction_accuracy"] * 0.9 + accuracy * 0.1
            )
            
            # Learn transition
            state_before = action.get("state_before", {})
            self.learn_transition(state_before, action, outcome_state, reward)
    
    def _state_key(self, state: Dict) -> str:
        """Hash state to key"""
        body = state.get("body", {})
        return f"E{int(body.get('energy',50)/10)}_S{int(body.get('stress',50)/10)}_C{int(body.get('comfort',50)/10)}"
    
    def _action_key(self, action: Dict) -> str:
        return action.get("type", "unknown")
    
    def _key_to_state(self, key: str) -> Dict:
        """Reverse of _state_key (approximate)"""
        parts = key.split("_")
        state = {"body": {}}
        for p in parts:
            if p.startswith("E"):
                state["body"]["energy"] = int(p[1:]) * 10
            elif p.startswith("S"):
                state["body"]["stress"] = int(p[1:]) * 10
            elif p.startswith("C"):
                state["body"]["comfort"] = int(p[1:]) * 10
        return state
    
    def _heuristic_prediction(self, state: Dict, action: Dict) -> Dict:
        """Fallback heuristic when no learned model"""
        return self._apply_action(state, action)
    
    def get_state(self) -> Dict[str, Any]:
        return {
            "selected_policy": {
                "id": self.selected_policy.id if self.selected_policy else None,
                "probability": self.selected_policy.probability if self.selected_policy else 0,
                "expected_fe": self.selected_policy.expected_free_energy if self.selected_policy else 0,
                "actions": [a["type"] for a in self.selected_policy.actions] if self.selected_policy else []
            },
            "policy_count": len(self.current_policies),
            "transition_model_size": len(self.transition_model),
            "metrics": self.metrics,
            "preferences": self.preferences,
            "mb_mf_balance": {"model_based": self.mb_weight, "model_free": self.mf_weight}
        }


def create_agency_engine(agent_id: str) -> AgencyEngine:
    return AgencyEngine(agent_id)